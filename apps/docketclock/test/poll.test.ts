/**
 * poll.test.ts — proves the Regs.gov differential poll loop (issue #18), the #18 regression included.
 *
 * Matches regs.test.ts / reconcile.test.ts style: hand-rolled assert/rejects, out[] accumulator,
 * failures counter, process.exit; a DB section guarded by a THROWAWAY Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * The poll core is fully deterministic here — the network and the clock are INJECTED (PollDeps fakes),
 * so NOTHING hits the wire. Detail payloads are built from the captured real v4 fixture
 * (regs-FAA-2025-5396-0001.json), overlaid per case; a second synthetic doc exercises multi-doc paging.
 *
 * Coverage:
 *   - cursor read/write roundtrip + default-null + the monotonic forward-only guard;
 *   - differential pass: ingest + reconcile + cursor advances to the MAX *LIST* lastModifiedDate, and
 *     explicitly NOT to the detail payload's modifyDate (the cursor-slice trap);
 *   - paging to completion (full page 1 + partial page 2 → both consumed) + maxPages truncation report;
 *   - dedupe across pages / idempotent same-payload re-run is a no-op;
 *   - #18 REGRESSION: an open window that drops out of the list, re-polled by documentId, flips to
 *     withdrawn — a new is_withdrawal=true observation appended + the window transitions (conflicting
 *     withdrawn_vs_open vs an open FR counterpart, with a live conflict_records row);
 *   - re-poll throttle: a window with a FRESH regs_poll_watch stamp is NOT re-polled;
 *   - per-document failure isolation: a throwing fetchDetail does not abort the cycle;
 *
 *   ADVERSARY REGRESSIONS (#1/#7/#5/#2 — data-loss/correctness fixes in the poll loop):
 *   - #1 contiguous-success cursor: an OLDER-dated doc failing its fetch HOLDS the cursor (does not pass
 *     it); a later cycle where it succeeds re-fetches it + advances — proving no permanent skip;
 *   - #7 reconcile-always self-heal: a withdrawal observation appended-but-not-reconciled (simulated
 *     crash) is healed on the next re-poll even though the re-fetch dedupe-skips (zero new rows);
 *   - #5 watch-table throttle: a stale-unchanged window is re-polled ONCE, then NOT again (within the
 *     throttle) despite no new observation row, then re-polled again once it goes stale;
 *   - #2 FR-only eligibility: an FR-discovered open window (regs_document_id set, ZERO regulations_gov
 *     observations) IS re-polled and a withdrawn detail flips it.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import {
  parseRegsObservation,
  type RegsListItem,
} from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import { readCursor, writeCursor, stampChecked } from "../src/poll/cursor.js";
import { pollRegsOnce, type PollDeps } from "../src/poll/poll.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const HERE = dirname(fileURLToPath(import.meta.url));
const regsFixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as { data: { id: string; attributes: Record<string, unknown> } };
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;

const SOURCE = "regulations_gov";

/**
 * Build a Regs v4 detail payload from the fixture: deep-clone, override the documentId + the join key
 * (frDocNum) so each doc lands on its own ocd_id, and overlay attribute overrides per case.
 */
function regsDetail(
  documentId: string,
  frDocNum: string,
  attrOverrides: Record<string, unknown>,
): unknown {
  const raw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  raw.data.id = documentId;
  raw.data.attributes.frDocNum = frDocNum;
  Object.assign(raw.data.attributes, attrOverrides);
  return raw;
}

/** A fake PollDeps: a fixed clock + a documentId→detail map + per-page list pages (paged in order). */
function fakeDeps(opts: {
  now: Date;
  pages: RegsListItem[][];
  details: Record<string, unknown>;
  failOn?: Set<string>;
}): Partial<PollDeps> {
  const pagesCalled: number[] = [];
  return {
    now: () => opts.now,
    listPage: async ({ pageNumber }) => {
      pagesCalled.push(pageNumber);
      return opts.pages[pageNumber - 1] ?? [];
    },
    fetchDetail: async (documentId: string) => {
      if (opts.failOn?.has(documentId))
        throw new Error(`synthetic fetch failure for ${documentId}`);
      const d = opts.details[documentId];
      if (d === undefined)
        throw new Error(`fakeDeps: no detail for ${documentId}`);
      return d;
    },
  };
}

const NOW = new Date("2026-06-01T00:00:00Z");

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0004 applies (poll_cursor)",
    applied.includes("0004_poll_cursor.sql"),
    applied.join(", "),
  );
  const [tbl] = await sql<{ tablename: string }[]>`
    select tablename from pg_tables where tablename = 'poll_cursor'
  `;
  assert("poll_cursor table exists", !!tbl, tbl?.tablename ?? "missing");

  // ── CURSOR — read/write roundtrip, default-null, monotonic forward-only guard ──────────────────────
  assert(
    "readCursor is null before the first run",
    (await readCursor(sql, SOURCE)) === null,
  );
  await writeCursor(sql, SOURCE, "2026-06-01T00:00:00.000Z", NOW);
  assert(
    "writeCursor → readCursor roundtrips the UTC ISO instant",
    (await readCursor(sql, SOURCE)) === "2026-06-01T00:00:00.000Z",
    String(await readCursor(sql, SOURCE)),
  );
  // Forward write advances.
  await writeCursor(sql, SOURCE, "2026-06-02T00:00:00.000Z", NOW);
  assert(
    "writeCursor advances the cursor forward",
    (await readCursor(sql, SOURCE)) === "2026-06-02T00:00:00.000Z",
    String(await readCursor(sql, SOURCE)),
  );
  // Backward write is IGNORED (monotonic guard).
  await writeCursor(sql, SOURCE, "2026-05-01T00:00:00.000Z", NOW);
  assert(
    "MONOTONIC: a backward write does NOT regress the stored cursor",
    (await readCursor(sql, SOURCE)) === "2026-06-02T00:00:00.000Z",
    String(await readCursor(sql, SOURCE)),
  );

  // Reset the cursor table for the poll cases (drop the row so the first poll seeds a lookback).
  await sql`delete from poll_cursor`;

  // ── DIFFERENTIAL PASS — two changed docs ingested + reconciled; cursor advances to MAX LIST date ───
  // The detail payloads carry modifyDate 2025-12-18 (the fixture); the LIST items carry DISTINCT
  // lastModifiedDate values. The cursor MUST advance to the max LIST date, NOT the detail modifyDate.
  {
    const docA = "DOC-A-0001";
    const docB = "DOC-B-0001";
    const listModA = "2026-05-10T00:00:00Z";
    const listModB = "2026-05-12T00:00:00Z"; // the MAX list date — cursor must land here
    const deps = fakeDeps({
      now: NOW,
      pages: [
        [
          { documentId: docA, lastModifiedDate: listModA },
          { documentId: docB, lastModifiedDate: listModB },
        ],
      ],
      details: {
        [docA]: regsDetail(docA, "2025-A0001", {
          commentEndDate: "2026-07-15T12:00:00Z",
          withinCommentPeriod: true,
          openForComment: true,
          withdrawn: false,
        }),
        [docB]: regsDetail(docB, "2025-B0001", {
          commentEndDate: "2026-07-20T12:00:00Z",
          withinCommentPeriod: true,
          openForComment: true,
          withdrawn: false,
        }),
      },
    });
    const s = await pollRegsOnce(sql, deps, { pageSize: 250 });
    assert("DIFF: listed both changed docs", s.listed === 2, String(s.listed));
    assert("DIFF: ingested both docs", s.ingested === 2, String(s.ingested));
    assert(
      "DIFF: deduped 0 on first sight",
      s.deduped === 0,
      String(s.deduped),
    );
    assert(
      "DIFF: one page fetched",
      s.pagesFetched === 1,
      String(s.pagesFetched),
    );
    assert("DIFF: not truncated", s.truncated === false);
    assert(
      "DIFF: cursor advances to the MAX *LIST* lastModifiedDate",
      s.cursorAdvancedTo === new Date(listModB).toISOString(),
      String(s.cursorAdvancedTo),
    );
    // CURSOR-SLICE TRAP: the detail payload's modifyDate is 2025-12-18 — the cursor must NEVER read it.
    assert(
      "DIFF: cursor did NOT advance to the detail payload's modifyDate (cursor-slice trap)",
      s.cursorAdvancedTo !== "2025-12-18T18:11:29.000Z" &&
        !String(s.cursorAdvancedTo).startsWith("2025-12-18"),
      String(s.cursorAdvancedTo),
    );
    // Both windows reconciled to open.
    const rows = await sql<{ ocd_id: string; status: string }[]>`
      select ocd_id, status from participation_windows order by ocd_id
    `;
    assert(
      "DIFF: both windows reconciled to status=open",
      rows.length === 2 && rows.every((r) => r.status === "open"),
      rows.map((r) => `${r.ocd_id}:${r.status}`).join(", "),
    );

    // Idempotent re-run on the SAME payloads (same cursor → same list) is a no-op (all deduped).
    const s2 = await pollRegsOnce(sql, deps, { pageSize: 250 });
    assert(
      "IDEMPOTENT: re-running on unchanged payloads ingests nothing (all deduped)",
      s2.ingested === 0 && s2.deduped === 2,
      `ingested=${s2.ingested} deduped=${s2.deduped}`,
    );
    const [cnt] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations
    `;
    assert(
      "IDEMPOTENT: no new observation rows on the no-op re-run",
      cnt!.count === "2",
      cnt!.count,
    );
  }

  // ── PAGING TO COMPLETION — full page 1 + partial page 2 → both consumed; pagesFetched === 2 ────────
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const pageSize = 2; // tiny page size so a 2-item page is "full"
    const docs = ["PG-1", "PG-2", "PG-3"]; // 2 on page 1 (full), 1 on page 2 (partial → last)
    const details: Record<string, unknown> = {};
    docs.forEach(
      (id, i) =>
        (details[id] = regsDetail(id, `2025-PG${i}`, {
          commentEndDate: "2026-08-01T12:00:00Z",
          withinCommentPeriod: true,
          openForComment: true,
          withdrawn: false,
        })),
    );
    const deps = fakeDeps({
      now: NOW,
      pages: [
        [
          { documentId: "PG-1", lastModifiedDate: "2026-05-01T00:00:00Z" },
          { documentId: "PG-2", lastModifiedDate: "2026-05-02T00:00:00Z" },
        ],
        [{ documentId: "PG-3", lastModifiedDate: "2026-05-03T00:00:00Z" }],
      ],
      details,
    });
    const s = await pollRegsOnce(sql, deps, { pageSize });
    assert(
      "PAGING: pages fetched to completion (full page 1 + partial page 2)",
      s.pagesFetched === 2,
      String(s.pagesFetched),
    );
    assert("PAGING: all three docs listed", s.listed === 3, String(s.listed));
    assert("PAGING: all three ingested", s.ingested === 3, String(s.ingested));
    assert(
      "PAGING: cursor advances to the newest (last-page) LIST date",
      s.cursorAdvancedTo === new Date("2026-05-03T00:00:00Z").toISOString(),
      String(s.cursorAdvancedTo),
    );
    assert(
      "PAGING: not truncated (last page was short)",
      s.truncated === false,
    );
  }

  // ── MAXPAGES TRUNCATION — a full last page at the cap reports truncation (does not silently swallow) ─
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const pageSize = 2;
    const maxPages = 2;
    // BOTH pages are FULL (2 items each); at maxPages=2 with a full last page → truncated.
    const ids = ["TR-1", "TR-2", "TR-3", "TR-4"];
    const details: Record<string, unknown> = {};
    ids.forEach(
      (id, i) =>
        (details[id] = regsDetail(id, `2025-TR${i}`, {
          commentEndDate: "2026-08-01T12:00:00Z",
          withinCommentPeriod: true,
          openForComment: true,
          withdrawn: false,
        })),
    );
    const deps = fakeDeps({
      now: NOW,
      pages: [
        [
          { documentId: "TR-1", lastModifiedDate: "2026-05-01T00:00:00Z" },
          { documentId: "TR-2", lastModifiedDate: "2026-05-02T00:00:00Z" },
        ],
        [
          { documentId: "TR-3", lastModifiedDate: "2026-05-03T00:00:00Z" },
          { documentId: "TR-4", lastModifiedDate: "2026-05-04T00:00:00Z" },
        ],
      ],
      details,
    });
    const s = await pollRegsOnce(sql, deps, { pageSize, maxPages });
    assert(
      "TRUNCATION: stopped at maxPages",
      s.pagesFetched === maxPages,
      String(s.pagesFetched),
    );
    assert(
      "TRUNCATION: reports truncated=true on a full last page at the cap",
      s.truncated === true,
    );
  }

  // ── #18 REGRESSION — open → withdrawn: re-poll by documentId lands is_withdrawal=true + transitions ─
  // Seed an OPEN window: an FR counterpart reading open (future close) + a Regs obs withinCommentPeriod/
  // openForComment=true, reconcile → status=open. Make the Regs observation STALE (old fetched_at). Then
  // run a poll whose differential list does NOT include the doc (it dropped out, having been withdrawn),
  // and whose fetchDetail returns the SAME doc now withdrawn:true. The re-poll pass must catch it.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const DOC = "WD-DOC-0001";
    const FRNUM = "2025-99918";
    const OCD = `ocd-participation-window/federal/${FRNUM}`;

    // FR counterpart reading OPEN (a future date-only close) so withdrawn-vs-open is CONFLICTING.
    const frRaw = {
      ...frFixture,
      document_number: FRNUM,
      comments_close_on: "2026-07-15",
    };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-01T00:00:00Z",
    });
    // Regs obs reading OPEN — STALE fetched_at (well older than the 6h staleness throttle before NOW).
    const openDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-07-15T12:00:00Z",
      withinCommentPeriod: true,
      openForComment: true,
      withdrawn: false,
    });
    await ingestObservation(sql, {
      ...parseRegsObservation(openDetail),
      fetched_at: "2026-05-20T00:00:00Z", // stale relative to NOW (2026-06-01)
    });
    const seed = await reconcileOcdId(sql, OCD, NOW);
    assert(
      "#18 SEED: window starts status=open",
      seed.window.status === "open",
      seed.window.status,
    );
    const [obsBefore] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations
      where regs_document_id = ${DOC} and is_withdrawal = true
    `;
    assert(
      "#18 SEED: no is_withdrawal observation yet",
      obsBefore!.count === "0",
      obsBefore!.count,
    );

    // The poll: the doc DROPPED OUT of the withinCommentPeriod list (empty differential), but the detail
    // (by documentId) now reads withdrawn:true + openForComment:false (no longer within comment period).
    const withdrawnDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-07-15T12:00:00Z",
      withinCommentPeriod: false,
      openForComment: false,
      withdrawn: true,
    });
    const deps = fakeDeps({
      now: NOW,
      pages: [[]], // differential list is EMPTY — the withdrawn doc is no longer within comment period
      details: { [DOC]: withdrawnDetail },
    });
    const s = await pollRegsOnce(sql, deps, {});
    assert(
      "#18 REGRESSION: the dropped-out open window was re-polled",
      s.repolled === 1,
      String(s.repolled),
    );
    assert(
      "#18 REGRESSION: the re-poll produced a transition (new observation)",
      s.transitions >= 1,
      String(s.transitions),
    );
    const [obsAfter] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations
      where regs_document_id = ${DOC} and is_withdrawal = true
    `;
    assert(
      "#18 REGRESSION: a NEW is_withdrawal=true observation was appended to the log",
      obsAfter!.count === "1",
      obsAfter!.count,
    );
    const [win] = await sql<
      { status: string; confidence: string; conflict_flags: unknown }[]
    >`
      select status, confidence, conflict_flags from participation_windows where ocd_id = ${OCD}
    `;
    assert(
      "#18 REGRESSION: the window TRANSITIONED to status=withdrawn",
      win!.status === "withdrawn",
      win!.status,
    );
    assert(
      "#18 REGRESSION: open FR counterpart → CONFLICTING withdrawn_vs_open",
      win!.confidence === "conflicting" &&
        Array.isArray(win!.conflict_flags) &&
        (win!.conflict_flags as string[]).includes("withdrawn_vs_open"),
      `${win!.confidence} [${JSON.stringify(win!.conflict_flags)}]`,
    );
    const [conf] = await sql<{ count: string }[]>`
      select count(*)::text as count from conflict_records
      where ocd_id = ${OCD} and resolved_at is null
    `;
    assert(
      "#18 REGRESSION: a LIVE conflict_records row exists for the withdrawal conflict",
      conf!.count === "1",
      conf!.count,
    );
  }

  // ── RE-POLL THROTTLE — a window with a FRESH watch stamp is NOT re-polled ──────────────────────────
  // Freshness is now driven by regs_poll_watch.last_checked_at (fix #5/#2), NOT the observation log: a
  // recent stamp (here 2h before NOW, inside the 6h throttle) holds the window off the re-poll sweep.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const DOC = "FRESH-0001";
    const FRNUM = "2025-99919";
    const OCD = `ocd-participation-window/federal/${FRNUM}`;
    const openDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-07-15T12:00:00Z",
      withinCommentPeriod: true,
      openForComment: true,
      withdrawn: false,
    });
    await ingestObservation(sql, {
      ...parseRegsObservation(openDetail),
      fetched_at: "2026-05-31T22:00:00Z",
    });
    await reconcileOcdId(sql, OCD, NOW);
    // Stamp the per-document throttle FRESH (2h before NOW → inside the 6h window) — the new throttle source.
    await stampChecked(sql, DOC, new Date(NOW.getTime() - 2 * 3_600_000));

    let fetched = false;
    const deps: Partial<PollDeps> = {
      now: () => NOW,
      listPage: async () => [],
      fetchDetail: async () => {
        fetched = true;
        return openDetail;
      },
    };
    const s = await pollRegsOnce(sql, deps, {
      repollStaleAfterMs: 6 * 3_600_000,
    });
    assert(
      "THROTTLE: a fresh open window is NOT re-polled",
      s.repolled === 0 && fetched === false,
      `repolled=${s.repolled} fetched=${fetched}`,
    );
  }

  // ── PER-DOCUMENT FAILURE ISOLATION — a throwing fetchDetail does not abort the cycle ──────────────
  // The BAD doc is the OLDER-dated of the two; under the contiguous-success cursor (fix #1) it breaks the
  // prefix, so the cursor must NOT advance past it — but the NEWER good doc is still ingested (isolation).
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const good = "OK-0001";
    const bad = "BAD-0001";
    const deps = fakeDeps({
      now: NOW,
      pages: [
        [
          { documentId: bad, lastModifiedDate: "2026-05-10T00:00:00Z" },
          { documentId: good, lastModifiedDate: "2026-05-12T00:00:00Z" },
        ],
      ],
      details: {
        [good]: regsDetail(good, "2025-OK01", {
          commentEndDate: "2026-08-01T12:00:00Z",
          withinCommentPeriod: true,
          openForComment: true,
          withdrawn: false,
        }),
      },
      failOn: new Set([bad]),
    });
    const s = await pollRegsOnce(sql, deps, {});
    assert(
      "ISOLATION: the good (newer) doc still ingests despite the bad (older) doc throwing",
      s.ingested === 1,
      String(s.ingested),
    );
    assert(
      "ISOLATION: the cursor does NOT advance past the older FAILED doc (fix #1 contiguous prefix)",
      s.cursorAdvancedTo === null,
      String(s.cursorAdvancedTo),
    );
  }

  // ── FIX #1 — contiguous-success cursor: an older-dated failure never permanently skips the change ───
  // A batch of two: the OLDER-dated doc FAILS its fetchDetail, the NEWER succeeds. The cursor must advance
  // to AT MOST just-below the older doc (here: NOT past it → stays null, since older breaks the prefix at
  // index 0). Next cycle the older doc now SUCCEEDS → it is re-fetched/ingested and the cursor advances
  // past it. Proves no permanent skip of the older change.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const older = "OLD-0001"; // older lastModifiedDate, fails on cycle 1
    const newer = "NEW-0001"; // newer lastModifiedDate, succeeds both cycles
    const olderMod = "2026-05-10T00:00:00Z";
    const newerMod = "2026-05-12T00:00:00Z";
    const olderDetail = regsDetail(older, "2025-OLD1", {
      commentEndDate: "2026-08-01T12:00:00Z",
      withinCommentPeriod: true,
      openForComment: true,
      withdrawn: false,
    });
    const newerDetail = regsDetail(newer, "2025-NEW1", {
      commentEndDate: "2026-08-02T12:00:00Z",
      withinCommentPeriod: true,
      openForComment: true,
      withdrawn: false,
    });
    const pages = [
      [
        { documentId: older, lastModifiedDate: olderMod },
        { documentId: newer, lastModifiedDate: newerMod },
      ],
    ];

    // Cycle 1: older FAILS, newer SUCCEEDS.
    const deps1 = fakeDeps({
      now: NOW,
      pages,
      details: { [newer]: newerDetail },
      failOn: new Set([older]),
    });
    const s1 = await pollRegsOnce(sql, deps1, {});
    assert(
      "#1 CONTIGUOUS: cycle1 ingests the newer doc but the older FAILS",
      s1.ingested === 1,
      String(s1.ingested),
    );
    assert(
      "#1 CONTIGUOUS: cycle1 cursor does NOT pass the older FAILED doc (stays null)",
      s1.cursorAdvancedTo === null,
      String(s1.cursorAdvancedTo),
    );
    const [olderObs1] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where regs_document_id = ${older}
    `;
    assert(
      "#1 CONTIGUOUS: cycle1 wrote NO observation for the failed older doc",
      olderObs1!.count === "0",
      olderObs1!.count,
    );

    // Cycle 2: same list (cursor never advanced past the older doc, so it is re-listed), older now SUCCEEDS.
    const deps2 = fakeDeps({
      now: NOW,
      pages,
      details: { [older]: olderDetail, [newer]: newerDetail },
    });
    const s2 = await pollRegsOnce(sql, deps2, {});
    const [olderObs2] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where regs_document_id = ${older}
    `;
    assert(
      "#1 CONTIGUOUS: cycle2 RE-FETCHES + ingests the previously-failed older doc (no permanent skip)",
      olderObs2!.count === "1",
      olderObs2!.count,
    );
    assert(
      "#1 CONTIGUOUS: cycle2 cursor now advances PAST the older doc (to the newest list date)",
      s2.cursorAdvancedTo === new Date(newerMod).toISOString(),
      String(s2.cursorAdvancedTo),
    );
  }

  // ── FIX #7 — reconcile SELF-HEALS on re-poll even with NO new observation row (crash recovery) ──────
  // Simulate the crash: append a withdrawn:true observation but DO NOT reconcile (the projection still
  // reads open). Then run pollRegsOnce — the re-poll re-fetches the SAME (withdrawn) detail → ingest
  // dedupe-skips (inserted=false) → BUT reconcile-always still fires → the window flips. Proves it heals
  // WITHOUT a new row.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const DOC = "HEAL-0001";
    const FRNUM = "2025-99931";
    const OCD = `ocd-participation-window/federal/${FRNUM}`;

    // FR counterpart reading OPEN so the withdrawn re-derive is CONFLICTING withdrawn_vs_open.
    const frRaw = {
      ...frFixture,
      document_number: FRNUM,
      comments_close_on: "2026-07-15",
    };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-01T00:00:00Z",
    });
    // A Regs OPEN obs, reconciled → window status=open.
    const openDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-07-15T12:00:00Z",
      withinCommentPeriod: true,
      openForComment: true,
      withdrawn: false,
    });
    await ingestObservation(sql, {
      ...parseRegsObservation(openDetail),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    await reconcileOcdId(sql, OCD, NOW);

    // THE CRASH: append the withdrawn observation but DO NOT reconcile (process died before projection).
    const withdrawnDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-07-15T12:00:00Z",
      withinCommentPeriod: false,
      openForComment: false,
      withdrawn: true,
    });
    const wIngest = await ingestObservation(sql, {
      ...parseRegsObservation(withdrawnDetail),
      fetched_at: "2026-05-21T00:00:00Z",
    });
    assert(
      "#7 HEAL SEED: the withdrawal observation was appended (the crash happened AFTER this)",
      wIngest.inserted === true,
    );
    const [winBefore] = await sql<{ status: string }[]>`
      select status from participation_windows where ocd_id = ${OCD}
    `;
    assert(
      "#7 HEAL SEED: the projection is STILL open (reconcile never ran — the simulated crash)",
      winBefore!.status === "open",
      winBefore!.status,
    );
    const [obsCntBefore] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where regs_document_id = ${DOC}
    `;

    // The re-poll re-fetches the SAME withdrawn detail. ingest dedupe-skips (no new row), but reconcile
    // runs anyway and HEALS the projection.
    const deps = fakeDeps({
      now: NOW,
      pages: [[]], // empty differential — the withdrawn doc dropped out of the within-comment-period list
      details: { [DOC]: withdrawnDetail },
    });
    const s = await pollRegsOnce(sql, deps, {});
    assert(
      "#7 HEAL: the open window was re-polled",
      s.repolled === 1,
      String(s.repolled),
    );
    assert(
      "#7 HEAL: the re-poll produced NO transition (the withdrawal row already existed → dedupe-skip)",
      s.transitions === 0,
      String(s.transitions),
    );
    const [obsCntAfter] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where regs_document_id = ${DOC}
    `;
    assert(
      "#7 HEAL: NO new observation row was written (heal happened with zero new rows)",
      obsCntAfter!.count === obsCntBefore!.count,
      `${obsCntBefore!.count} -> ${obsCntAfter!.count}`,
    );
    const [winAfter] = await sql<
      { status: string; confidence: string; conflict_flags: unknown }[]
    >`
      select status, confidence, conflict_flags from participation_windows where ocd_id = ${OCD}
    `;
    assert(
      "#7 HEAL: reconcile-always FLIPPED the window to withdrawn despite no new row",
      winAfter!.status === "withdrawn",
      winAfter!.status,
    );
    assert(
      "#7 HEAL: open FR counterpart → CONFLICTING withdrawn_vs_open after heal",
      winAfter!.confidence === "conflicting" &&
        Array.isArray(winAfter!.conflict_flags) &&
        (winAfter!.conflict_flags as string[]).includes("withdrawn_vs_open"),
      `${winAfter!.confidence} [${JSON.stringify(winAfter!.conflict_flags)}]`,
    );
  }

  // ── FIX #5 — the watch-table throttle holds across cycles even with NO new observation row ──────────
  // A stale UNCHANGED open window is re-polled ONCE (cycle 1, which dedupe-skips the unchanged payload but
  // STAMPS regs_poll_watch). On cycle 2 (clock advanced < repollStaleAfterMs) it is NOT re-polled again —
  // the throttle held off the watch stamp, not the (never-advancing) observation log. Then advance the
  // clock past repollStaleAfterMs → it IS re-polled again.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const DOC = "STALE-0001";
    const FRNUM = "2025-99932";
    const OCD = `ocd-participation-window/federal/${FRNUM}`;
    const openDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-09-15T12:00:00Z",
      withinCommentPeriod: true,
      openForComment: true,
      withdrawn: false,
    });
    // Seed an OPEN window whose only Regs obs is STALE (fetched long before NOW), and NO watch stamp yet.
    await ingestObservation(sql, {
      ...parseRegsObservation(openDetail),
      fetched_at: "2026-05-01T00:00:00Z",
    });
    await reconcileOcdId(sql, OCD, new Date("2026-05-01T00:00:00Z"));

    const repollStaleAfterMs = 6 * 3_600_000;
    // fetchDetail always returns the SAME (unchanged) open detail → ingest always dedupe-skips.
    function staleDeps(now: Date): Partial<PollDeps> {
      return {
        now: () => now,
        listPage: async () => [],
        fetchDetail: async () => openDetail,
      };
    }

    // Cycle 1 at NOW: stale (last_checked_at NULL → epoch) → re-polled once; no new row; watch stamped.
    const c1 = await pollRegsOnce(sql, staleDeps(NOW), { repollStaleAfterMs });
    assert(
      "#5 THROTTLE: cycle1 re-polls the stale window once",
      c1.repolled === 1,
      String(c1.repolled),
    );
    assert(
      "#5 THROTTLE: cycle1 wrote NO new observation row (unchanged payload dedupe-skips)",
      c1.transitions === 0,
      String(c1.transitions),
    );
    const [stamp1] = await sql<{ count: string }[]>`
      select count(*)::text as count from regs_poll_watch where regs_document_id = ${DOC}
    `;
    assert(
      "#5 THROTTLE: cycle1 STAMPED regs_poll_watch (throttle source decoupled from the log)",
      stamp1!.count === "1",
      stamp1!.count,
    );

    // Cycle 2 a little later (< repollStaleAfterMs after the cycle-1 stamp): NOT re-polled — throttle holds
    // even though no observation row was ever written.
    const soon = new Date(NOW.getTime() + 60 * 60 * 1000); // +1h, well within the 6h throttle
    const c2 = await pollRegsOnce(sql, staleDeps(soon), { repollStaleAfterMs });
    assert(
      "#5 THROTTLE: cycle2 (within 6h) does NOT re-poll again — the watch throttle holds across cycles",
      c2.repolled === 0,
      String(c2.repolled),
    );

    // Cycle 3 past repollStaleAfterMs after the last stamp: stale again → re-polled once more.
    const later = new Date(NOW.getTime() + 7 * 3_600_000); // +7h > 6h throttle
    const c3 = await pollRegsOnce(sql, staleDeps(later), {
      repollStaleAfterMs,
    });
    assert(
      "#5 THROTTLE: cycle3 (past 6h) re-polls the window again (it went stale again)",
      c3.repolled === 1,
      String(c3.repolled),
    );
  }

  // ── FIX #2 — an FR-ONLY open window (regs_document_id set, ZERO regulations_gov obs) IS re-polled ────
  // An FR observation carries regulations_dot_gov_info.document_id → regs_document_id onto the window via
  // reconcile, with NO regulations_gov observation. The old subquery was NULL → never eligible. Now
  // coalesce(last_checked_at,'epoch') makes it maximally stale → selected. A fetchDetail returning
  // withdrawn:true produces an is_withdrawal observation and flips the window.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const DOC = "FR-ONLY-DOC-0001";
    const FRNUM = "2025-99933";
    const OCD = `ocd-participation-window/federal/${FRNUM}`;

    // FR observation reading OPEN with a regulations_dot_gov_info.document_id linking to DOC, and ZERO
    // regulations_gov observations. The fixture already carries regulations_dot_gov_info; override its id.
    const frRaw = {
      ...frFixture,
      document_number: FRNUM,
      comments_close_on: "2026-07-15",
      regulations_dot_gov_info: {
        ...((frFixture.regulations_dot_gov_info as Record<string, unknown>) ??
          {}),
        document_id: DOC,
      },
    };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-01T00:00:00Z",
    });
    const seed = await reconcileOcdId(sql, OCD, NOW);
    assert(
      "#2 FR-ONLY SEED: window starts status=open",
      seed.window.status === "open",
      seed.window.status,
    );
    assert(
      "#2 FR-ONLY SEED: the window carries regs_document_id from FR (with zero Regs observations)",
      seed.window.regs_document_id === DOC,
      String(seed.window.regs_document_id),
    );
    const [regsObs] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations
      where source = ${SOURCE} and regs_document_id = ${DOC}
    `;
    assert(
      "#2 FR-ONLY SEED: there are ZERO regulations_gov observations for the doc",
      regsObs!.count === "0",
      regsObs!.count,
    );

    // The re-poll: fetchDetail returns the doc now withdrawn:true.
    const withdrawnDetail = regsDetail(DOC, FRNUM, {
      commentEndDate: "2026-07-15T12:00:00Z",
      withinCommentPeriod: false,
      openForComment: false,
      withdrawn: true,
    });
    const deps = fakeDeps({
      now: NOW,
      pages: [[]],
      details: { [DOC]: withdrawnDetail },
    });
    const s = await pollRegsOnce(sql, deps, {});
    assert(
      "#2 FR-ONLY: the FR-discovered open window (no Regs obs) IS re-polled",
      s.repolled === 1,
      String(s.repolled),
    );
    assert(
      "#2 FR-ONLY: the re-poll produced a transition (the first Regs observation)",
      s.transitions === 1,
      String(s.transitions),
    );
    const [wdObs] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations
      where regs_document_id = ${DOC} and is_withdrawal = true
    `;
    assert(
      "#2 FR-ONLY: an is_withdrawal=true observation was appended",
      wdObs!.count === "1",
      wdObs!.count,
    );
    const [win] = await sql<{ status: string }[]>`
      select status from participation_windows where ocd_id = ${OCD}
    `;
    assert(
      "#2 FR-ONLY: the window flipped to status=withdrawn",
      win!.status === "withdrawn",
      win!.status,
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== poll results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
