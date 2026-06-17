/**
 * fr-poll.test.ts — proves the Federal Register discovery poll core (pollFrOnce) and the FR list
 * adapter (frListUrl) + the Eastern date-only helper (todayEastern).
 *
 * Matches poll.test.ts style: hand-rolled assert, out[] accumulator, failures counter, process.exit;
 * a DB section guarded by a THROWAWAY Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * The poll core is fully deterministic here — the network and the clock are INJECTED (FrPollDeps fakes),
 * so NOTHING hits the wire. Detail payloads are built from the captured real FR fixture
 * (fr-2025-02910.json), overlaid per case.
 *
 * The list fake is SERVER-HONORING: it models the real FR contract. Given a backing fixture set of docs
 * (each with a comments_close_on + publicationDate), one `listPage` call returns ONLY the docs whose
 * comment is still open (comments_close_on >= commentOpenOnOrAfter), paginated by perPage/page, with NO
 * publication_date cursor (there is none anymore). It enforces FR's page * per_page <= 10,000 by
 * THROWING like FR's HTTP 400 — so a test proves the cycle never requests past the cap and that the
 * maxPages guard prevents reaching it.
 *
 * Coverage:
 *   - UNIT: todayEastern; frListUrl (comment_date][gte] present, NO publication_date param, order=newest,
 *     per_page default 1000, fields present);
 *   - B1 BACK-CATALOG: an open doc published ~18 months ago IS listed → fetched → ingested → window
 *     (the regression that the old publication_date cursor would have silently buried);
 *   - HANDOFF: an FR doc carrying regulations_dot_gov_info.document_id lands regs_document_id on its window;
 *   - DIFFERENTIAL-BY-LOG: a second cycle skips already-ingested docs (fetchDetail NOT called), fetched=0,
 *     no new rows, windows still present;
 *   - GROWTH: a brand-new doc appearing in a later cycle is fetched while the old ones are skipped;
 *   - FAILURE RETRIED VIA RE-LIST: a doc whose fetchDetail throws stays unseen and IS ingested next cycle;
 *   - TRUNCATION: open set > perPage*maxPages → truncated=true + warn, NO page beyond maxPages requested.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { frListUrl, todayEastern } from "../src/sources/federal-register.js";
import { pollFrOnce, type FrPollDeps } from "../src/poll/fr-poll.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const HERE = dirname(fileURLToPath(import.meta.url));
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;

const SOURCE = "federal_register";

/**
 * Build an FR detail payload from the fixture: deep-clone, override the document_number (so each doc
 * lands on its own ocd_id), and overlay field overrides per case.
 */
function frDetail(
  documentNumber: string,
  overrides: Record<string, unknown> = {},
): unknown {
  const raw = JSON.parse(JSON.stringify(frFixture)) as Record<string, unknown>;
  raw.document_number = documentNumber;
  Object.assign(raw, overrides);
  return raw;
}

/** One doc in the SERVER-HONORING fake's backing set: list metadata + the detail it would return. */
interface FakeDoc {
  documentNumber: string;
  publicationDate: string; // immutable print date (the B1 trap: can be far in the past)
  commentsCloseOn: string; // the open-comment cutoff the fake filters on
  regsDocumentId?: string | null; // override the fixture's regulations_dot_gov_info.document_id
}

/**
 * A server-honoring FrPollDeps fake. `set` is the WHOLE backing corpus; `listPage` returns only the
 * docs whose comment is open (commentsCloseOn >= commentOpenOnOrAfter), sorted newest-first (matching
 * order=newest), then paginated by perPage/page. It does NOT filter by any publication_date cursor.
 * It THROWS like FR's HTTP 400 if page * perPage > 10,000. `fetchDetail` counts calls (per doc) so we
 * can prove the differential skip never fetches a seen doc; `failOn` throws for chosen docs.
 */
function serverFake(opts: {
  now: Date;
  set: FakeDoc[];
  failOn?: Set<string>;
  maxRequestedPage?: { value: number };
  fetchCalls?: Map<string, number>;
  sleeps?: { count: number; totalMs: number };
}): Partial<FrPollDeps> {
  return {
    now: () => opts.now,
    // No-op sleep so the cold-start throttle never makes a test actually wait; record calls so a test
    // can assert the throttle fires once per FR fetch beyond the first (and never for skipped docs).
    sleep: async (ms: number) => {
      if (opts.sleeps) {
        opts.sleeps.count++;
        opts.sleeps.totalMs += ms;
      }
    },
    listPage: async (req) => {
      const { commentOpenOnOrAfter, perPage, page } = req;
      if (page * perPage > 10_000)
        throw new Error(
          `FR 400: page * per_page (${page * perPage}) exceeds 10,000 ceiling`,
        );
      if (opts.maxRequestedPage)
        opts.maxRequestedPage.value = Math.max(
          opts.maxRequestedPage.value,
          page,
        );
      // Server-honoring: model the real FR contract. If a caller EVER passes the publication_date
      // cursor (the OLD, buggy code path did via `sinceDate`), the server applies it — which is exactly
      // how the back-catalog hole manifests, so the B1 test genuinely exercises the fix. The new code
      // never sends it (there is no such field), so it sees the FULL open set.
      const sinceDate = (req as { sinceDate?: string }).sinceDate;
      const open = opts.set
        .filter((d) => d.commentsCloseOn >= commentOpenOnOrAfter)
        .filter((d) => !sinceDate || d.publicationDate >= sinceDate)
        .sort((a, b) => b.publicationDate.localeCompare(a.publicationDate)); // newest first
      const start = (page - 1) * perPage;
      return open.slice(start, start + perPage).map((d) => ({
        documentNumber: d.documentNumber,
        publicationDate: d.publicationDate,
      }));
    },
    fetchDetail: async (documentNumber: string) => {
      if (opts.fetchCalls)
        opts.fetchCalls.set(
          documentNumber,
          (opts.fetchCalls.get(documentNumber) ?? 0) + 1,
        );
      if (opts.failOn?.has(documentNumber))
        throw new Error(`synthetic fetch failure for ${documentNumber}`);
      const doc = opts.set.find((x) => x.documentNumber === documentNumber);
      if (!doc) throw new Error(`serverFake: no detail for ${documentNumber}`);
      const overrides: Record<string, unknown> = {
        comments_close_on: doc.commentsCloseOn,
      };
      // Only OVERRIDE the fixture's regulations_dot_gov_info when the FakeDoc opts in. undefined =
      // keep the fixture's link (Object.assign of an explicit undefined would clobber it — so omit it).
      if (doc.regsDocumentId !== undefined) {
        overrides.regulations_dot_gov_info =
          doc.regsDocumentId === null
            ? null
            : { document_id: doc.regsDocumentId };
      }
      return frDetail(documentNumber, overrides);
    },
  };
}

const NOW = new Date("2026-06-01T12:00:00Z"); // Eastern: 2026-06-01

// ── UNIT: todayEastern (date-only, Eastern) ──────────────────────────────────────────────────────────
{
  assert(
    "todayEastern: a UTC instant after midnight UTC but before midnight Eastern reads the PRIOR Eastern day",
    todayEastern(new Date("2026-06-01T03:00:00Z")) === "2026-05-31",
    todayEastern(new Date("2026-06-01T03:00:00Z")),
  );
  assert(
    "todayEastern: a mid-day UTC instant reads the same Eastern day",
    todayEastern(new Date("2026-06-01T16:00:00Z")) === "2026-06-01",
    todayEastern(new Date("2026-06-01T16:00:00Z")),
  );
}

// ── UNIT: frListUrl (full-open-set discovery — NO publication_date cursor) ──────────────────────────────
{
  const base = "https://fr.example/api/v1";
  const u1 = new URL(frListUrl({ commentOpenOnOrAfter: "2026-06-01", base }));
  assert(
    "frListUrl: always sets conditions[comment_date][gte] to the open cutoff",
    u1.searchParams.get("conditions[comment_date][gte]") === "2026-06-01",
    u1.searchParams.get("conditions[comment_date][gte]") ?? "missing",
  );
  assert(
    "frListUrl: NEVER sets conditions[publication_date][gte] (immutable — not a change cursor, B1)",
    u1.searchParams.get("conditions[publication_date][gte]") === null,
  );
  assert(
    "frListUrl: order=newest (keep newest open docs IF truncation ever occurs)",
    u1.searchParams.get("order") === "newest",
    u1.searchParams.get("order") ?? "missing",
  );
  assert(
    "frListUrl: per_page defaults to 1000 (FR max)",
    u1.searchParams.get("per_page") === "1000",
    u1.searchParams.get("per_page") ?? "missing",
  );
  assert(
    "frListUrl: fields[] includes document_number and publication_date",
    u1.searchParams.getAll("fields[]").includes("document_number") &&
      u1.searchParams.getAll("fields[]").includes("publication_date"),
    u1.searchParams.getAll("fields[]").join(","),
  );
}

const sql = createClient();
try {
  // ── B1 BACK-CATALOG + HANDOFF + DIFFERENTIAL-BY-LOG + GROWTH + FAILURE-RETRY (one evolving corpus) ───
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    // OLD: an open doc published ~18 months ago. THIS is the B1 trap — under the old publication_date
    // cursor (initialLookbackDays ~ 12) a fresh deploy would never list it, and the cursor would bury it
    // forever. With full-open-set discovery it MUST be listed/fetched/ingested.
    const docOld = "2024-OLD01"; // pub 2024-12-15 (~18mo before 2026-06), comment still open
    const docNew = "2026-NEW01"; // pub recently
    const docCarriesRegs = "2024-OLD02"; // also old, carries the fixture's regs_document_id

    const fetchCalls = new Map<string, number>();
    const set: FakeDoc[] = [
      {
        documentNumber: docOld,
        publicationDate: "2024-12-15",
        commentsCloseOn: "2026-07-15",
        regsDocumentId: null,
      },
      {
        documentNumber: docCarriesRegs,
        publicationDate: "2024-12-20",
        commentsCloseOn: "2026-07-20",
        // undefined → keep the fixture's regulations_dot_gov_info (document_id EPA-HQ-OW-2024-0454-0022)
      },
    ];

    // CYCLE 1: only the two OLD (back-catalog) docs are open. Both must be discovered.
    const s1 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }),
      {
        perPage: 1000,
      },
    );
    assert(
      "B1 BACK-CATALOG: an 18-month-old open doc IS listed (full-open-set discovery)",
      s1.listed === 2,
      String(s1.listed),
    );
    assert(
      "B1 BACK-CATALOG: both back-catalog docs fetched + ingested",
      s1.fetched === 2 && s1.ingested === 2,
      `fetched=${s1.fetched} ingested=${s1.ingested}`,
    );
    assert(
      "B1 BACK-CATALOG: nothing skipped on first sight",
      s1.skipped === 0,
      String(s1.skipped),
    );
    const rows1 = await sql<
      { ocd_id: string; status: string; regs_document_id: string | null }[]
    >`select ocd_id, status, regs_document_id from participation_windows order by ocd_id`;
    assert(
      "B1 BACK-CATALOG: the 18-month-old doc produced an OPEN window",
      rows1.some(
        (r) =>
          r.ocd_id === `ocd-participation-window/federal/${docOld}` &&
          r.status === "open",
      ),
      rows1.map((r) => `${r.ocd_id}:${r.status}`).join(", "),
    );
    const winRegs = rows1.find(
      (r) => r.ocd_id === `ocd-participation-window/federal/${docCarriesRegs}`,
    );
    assert(
      "HANDOFF: the FR-discovered window carries regs_document_id (→ Regs re-poll handoff)",
      winRegs?.regs_document_id === "EPA-HQ-OW-2024-0454-0022",
      String(winRegs?.regs_document_id),
    );

    // CYCLE 2: SAME open set → differential-by-log must SKIP both (no fetchDetail), fetched=0, no new rows.
    const fetchedBefore = new Map(fetchCalls);
    const s2 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }),
      {
        perPage: 1000,
      },
    );
    assert(
      "DIFFERENTIAL: cycle2 still LISTS both open docs",
      s2.listed === 2,
      String(s2.listed),
    );
    assert(
      "DIFFERENTIAL: cycle2 SKIPS both already-in-log docs (no fetch, no ingest)",
      s2.skipped === 2 && s2.fetched === 0 && s2.ingested === 0,
      `skipped=${s2.skipped} fetched=${s2.fetched} ingested=${s2.ingested}`,
    );
    assert(
      "DIFFERENTIAL: fetchDetail was NOT called for the skipped docs (call counts unchanged)",
      (fetchCalls.get(docOld) ?? 0) === (fetchedBefore.get(docOld) ?? 0) &&
        (fetchCalls.get(docCarriesRegs) ?? 0) ===
          (fetchedBefore.get(docCarriesRegs) ?? 0),
      `old=${fetchCalls.get(docOld)} regs=${fetchCalls.get(docCarriesRegs)}`,
    );
    const [obsCnt2] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations
    `;
    assert(
      "DIFFERENTIAL: no new observation rows on the all-skipped re-run (idempotent)",
      obsCnt2!.count === "2",
      obsCnt2!.count,
    );
    const [winCnt2] = await sql<{ count: string }[]>`
      select count(*)::text as count from participation_windows where status = 'open'
    `;
    assert(
      "DIFFERENTIAL: both windows still present + open after the skip-only re-run",
      winCnt2!.count === "2",
      winCnt2!.count,
    );

    // CYCLE 3: open set GROWS by one new doc; old ones still skipped, new one fetched.
    set.push({
      documentNumber: docNew,
      publicationDate: "2026-05-29",
      commentsCloseOn: "2026-08-01",
      regsDocumentId: null,
    });
    const s3 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }),
      {
        perPage: 1000,
      },
    );
    assert(
      "GROWTH: a brand-new open doc is discovered (listed=3, fetched=1, ingested=1, skipped=2)",
      s3.listed === 3 &&
        s3.fetched === 1 &&
        s3.ingested === 1 &&
        s3.skipped === 2,
      `listed=${s3.listed} fetched=${s3.fetched} ingested=${s3.ingested} skipped=${s3.skipped}`,
    );
    assert(
      "GROWTH: fetchDetail was called for the NEW doc",
      (fetchCalls.get(docNew) ?? 0) === 1,
      String(fetchCalls.get(docNew)),
    );

    // CYCLE 4 + 5: FAILURE RETRIED VIA RE-LIST. Add a doc whose fetchDetail throws → stays unseen; next
    // cycle (no failOn) it IS ingested. Proves the re-list retry replaces the old contiguous cursor.
    const docFail = "2026-FAIL1";
    set.push({
      documentNumber: docFail,
      publicationDate: "2026-05-30",
      commentsCloseOn: "2026-08-02",
      regsDocumentId: null,
    });
    const fetchedBeforeFail = fetchCalls.get(docFail) ?? 0;
    const s4 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls, failOn: new Set([docFail]) }),
      { perPage: 1000 },
    );
    assert(
      "FAILURE: fetchDetail WAS attempted for the unseen failing doc",
      (fetchCalls.get(docFail) ?? 0) === fetchedBeforeFail + 1,
      String(fetchCalls.get(docFail)),
    );
    assert(
      "FAILURE: the throw is isolated — nothing fetched-counted, nothing ingested this cycle",
      s4.fetched === 0 && s4.ingested === 0,
      `fetched=${s4.fetched} ingested=${s4.ingested}`,
    );
    const [failObs4] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where fr_document_number = ${docFail}
    `;
    assert(
      "FAILURE: the failed doc wrote NO observation (stays unseen → re-listed next cycle)",
      failObs4!.count === "0",
      failObs4!.count,
    );
    const s5 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }), // fake now SUCCEEDS for docFail
      { perPage: 1000 },
    );
    const [failObs5] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where fr_document_number = ${docFail}
    `;
    assert(
      "FAILURE RETRIED: the once-failed doc IS ingested on the next cycle (re-list retry, no permanent skip)",
      failObs5!.count === "1" && s5.ingested === 1,
      `obs=${failObs5!.count} ingested=${s5.ingested}`,
    );
  }

  // ── #21 FR DEAD-LETTER + SKIP + RETRY SWEEP ──────────────────────────────────────────────────────────
  // A persistently-failing FR doc is dead-lettered after N consecutive failed cycles; from then on it is
  // NOT re-fetched on the hot path (assert via the fetchDetail spy); the slow retry sweep re-attempts it
  // once deadLetterRetryStaleAfterMs has elapsed, and a now-succeeding fetch recovers + clears it.
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const docFail = "2026-DLFAIL1";
    const maxFailAttempts = 3;
    const retryMs = 6 * 3_600_000;
    const set: FakeDoc[] = [
      {
        documentNumber: docFail,
        publicationDate: "2026-05-29",
        commentsCloseOn: "2026-08-01",
        regsDocumentId: null,
      },
    ];
    const fetchCalls = new Map<string, number>();

    // Cycles 1..N at NOW: fetchDetail always FAILS → after N consecutive failures the doc is dead-lettered.
    let dlSummary;
    for (let cycle = 1; cycle <= maxFailAttempts; cycle++) {
      dlSummary = await pollFrOnce(
        sql,
        serverFake({
          now: NOW,
          set,
          failOn: new Set([docFail]),
          fetchCalls,
        }),
        {
          perPage: 1000,
          maxFailAttempts,
          deadLetterRetryStaleAfterMs: retryMs,
        },
      );
    }
    assert(
      "#21 FR DEAD-LETTER: the doc is dead-lettered on the Nth consecutive failure",
      dlSummary!.deadLettered === 1,
      String(dlSummary!.deadLettered),
    );
    const fetchesAtDeadLetter = fetchCalls.get(docFail) ?? 0;
    assert(
      "#21 FR DEAD-LETTER: it was fetch-attempted exactly N times across the N failing cycles",
      fetchesAtDeadLetter === maxFailAttempts,
      String(fetchesAtDeadLetter),
    );
    const [dlRow] = await sql<
      { attempts: number; dead_lettered_at: Date | null }[]
    >`
      select attempts, dead_lettered_at from poll_dead_letter
      where source = ${SOURCE} and document_key = ${docFail}
    `;
    assert(
      "#21 FR DEAD-LETTER: a ledger row exists with dead_lettered_at set and attempts >= N",
      !!dlRow &&
        dlRow.dead_lettered_at !== null &&
        dlRow.attempts >= maxFailAttempts,
      `attempts=${dlRow?.attempts} dl=${dlRow?.dead_lettered_at}`,
    );

    // A subsequent cycle SOON after (within retryMs): the doc is now SKIPPED from the hot path (NOT
    // re-fetched), and the sweep is NOT yet due → fetchDetail call count is UNCHANGED.
    const soon = new Date(NOW.getTime() + 60 * 60 * 1000); // +1h < 6h
    const sSoon = await pollFrOnce(
      sql,
      serverFake({ now: soon, set, fetchCalls }), // fetchDetail would SUCCEED now (no failOn)
      { perPage: 1000, maxFailAttempts, deadLetterRetryStaleAfterMs: retryMs },
    );
    assert(
      "#21 FR SKIP: a dead-lettered doc is SKIPPED on the hot path (folded into skipped, fetched=0)",
      sSoon.skipped === 1 && sSoon.fetched === 0,
      `skipped=${sSoon.skipped} fetched=${sSoon.fetched}`,
    );
    assert(
      "#21 FR SKIP: fetchDetail was NOT called (hot-path skip) and the sweep was not yet due",
      (fetchCalls.get(docFail) ?? 0) === fetchesAtDeadLetter &&
        sSoon.deadLetterRetried === 0,
      `calls=${fetchCalls.get(docFail)} retried=${sSoon.deadLetterRetried}`,
    );

    // A cycle PAST retryMs: the slow sweep re-attempts it; fetchDetail now succeeds → recovered + cleared.
    const later = new Date(NOW.getTime() + 7 * 3_600_000); // +7h > 6h
    const sLater = await pollFrOnce(
      sql,
      serverFake({ now: later, set, fetchCalls }),
      { perPage: 1000, maxFailAttempts, deadLetterRetryStaleAfterMs: retryMs },
    );
    assert(
      "#21 FR SWEEP: the slow sweep re-attempts the dead-lettered doc once due (deadLetterRetried=1)",
      sLater.deadLetterRetried === 1,
      String(sLater.deadLetterRetried),
    );
    assert(
      "#21 FR SWEEP: the now-succeeding doc is recovered + ingested by the sweep",
      sLater.recovered === 1 && sLater.ingested === 1,
      `recovered=${sLater.recovered} ingested=${sLater.ingested}`,
    );
    assert(
      "#21 FR SWEEP: fetchDetail WAS called by the sweep (call count advanced past the skip phase)",
      (fetchCalls.get(docFail) ?? 0) === fetchesAtDeadLetter + 1,
      String(fetchCalls.get(docFail)),
    );
    const [cleared] = await sql<{ count: string }[]>`
      select count(*)::text as count from poll_dead_letter where source = ${SOURCE} and document_key = ${docFail}
    `;
    assert(
      "#21 FR SWEEP: the dead-letter row is CLEARED after the successful sweep retry",
      cleared!.count === "0",
      cleared!.count,
    );
    const [obs] = await sql<{ count: string }[]>`
      select count(*)::text as count from observations where fr_document_number = ${docFail}
    `;
    assert(
      "#21 FR SWEEP: the previously-doomed FR doc finally has an observation",
      obs!.count === "1",
      obs!.count,
    );
  }

  // ── TRUNCATION + 10k-CEILING — open set > perPage*maxPages → truncated, no page past the cap requested ─
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const perPage = 2;
    const maxPages = 2; // cap reachable at 4 docs; the fake throws if page*perPage > 10,000 (not hit here)
    const set: FakeDoc[] = [];
    for (let i = 1; i <= 5; i++) {
      set.push({
        documentNumber: `2026-TR00${i}`,
        publicationDate: `2026-05-0${i}`,
        commentsCloseOn: "2026-08-01",
        regsDocumentId: null,
      });
    }
    const maxRequestedPage = { value: 0 };
    const s = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, maxRequestedPage }),
      { perPage, maxPages },
    );
    assert(
      "TRUNCATION: stopped at maxPages",
      s.pagesFetched === maxPages,
      String(s.pagesFetched),
    );
    assert(
      "TRUNCATION: reports truncated=true on a full last page at the cap",
      s.truncated === true,
    );
    assert(
      "TRUNCATION: NO page beyond maxPages was ever requested (the fake would have thrown otherwise)",
      maxRequestedPage.value === maxPages,
      String(maxRequestedPage.value),
    );
  }

  // ── THROTTLE — the cold-start politeness gate fires once per FR fetch beyond the first, never on skips ─
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const set: FakeDoc[] = [
      {
        documentNumber: "2026-30001",
        publicationDate: "2026-06-10",
        commentsCloseOn: "2026-07-10",
        regsDocumentId: null,
      },
      {
        documentNumber: "2026-30002",
        publicationDate: "2026-06-11",
        commentsCloseOn: "2026-07-11",
        regsDocumentId: null,
      },
    ];
    const sleeps1 = { count: 0, totalMs: 0 };
    const s1 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, sleeps: sleeps1 }),
      { interFetchDelayMs: 300 },
    );
    assert(
      "THROTTLE: 2 fetches → sleep fires exactly ONCE (before the 2nd; not the 1st)",
      s1.fetched === 2 && sleeps1.count === 1 && sleeps1.totalMs === 300,
      `fetched=${s1.fetched} sleeps=${sleeps1.count} ms=${sleeps1.totalMs}`,
    );
    // CYCLE 2: both now in the log → all SKIPPED → zero FR fetches → throttle never fires.
    const sleeps2 = { count: 0, totalMs: 0 };
    const s2 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, sleeps: sleeps2 }),
      { interFetchDelayMs: 300 },
    );
    assert(
      "THROTTLE: skipped (already-in-log) docs never sleep",
      s2.fetched === 0 && s2.skipped === 2 && sleeps2.count === 0,
      `fetched=${s2.fetched} skipped=${s2.skipped} sleeps=${sleeps2.count}`,
    );
    // ESCAPE HATCH: interFetchDelayMs=0 disables the throttle entirely (fresh schema → both docs fetched).
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const sleeps0 = { count: 0, totalMs: 0 };
    const s0 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, sleeps: sleeps0 }),
      { interFetchDelayMs: 0 },
    );
    assert(
      "THROTTLE: interFetchDelayMs=0 disables the throttle (2 fetches, 0 sleeps)",
      s0.fetched === 2 && sleeps0.count === 0,
      `fetched=${s0.fetched} sleeps=${sleeps0.count}`,
    );
  }

  // ── EMPTY OPEN SET — no docs open → no fetch, polled stamp written, no throw ─────────────────────────
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const s = await pollFrOnce(sql, serverFake({ now: NOW, set: [] }), {});
    assert(
      "EMPTY: nothing listed/fetched/ingested when no comment period is open",
      s.listed === 0 && s.fetched === 0 && s.ingested === 0 && s.skipped === 0,
      `listed=${s.listed} fetched=${s.fetched}`,
    );
    const [polled] = await sql<{ count: string }[]>`
      select count(*)::text as count from poll_cursor where source = ${SOURCE} and last_polled_at is not null
    `;
    assert(
      "EMPTY: a 'we ran' stamp (last_polled_at) is still written for observability",
      polled!.count === "1",
      polled!.count,
    );
  }

  // ── LIST-PHASE FAILURE — a listPage throw STILL stamps last_polled_at (try/finally), error propagates ──
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);
    const boom = new Error("FR 400: synthetic list-phase failure");
    let threw: unknown = null;
    try {
      await pollFrOnce(
        sql,
        {
          now: () => NOW,
          listPage: async () => {
            throw boom;
          },
          fetchDetail: async () => {
            throw new Error("should never fetch when listing failed");
          },
        },
        {},
      );
    } catch (err) {
      threw = err;
    }
    assert(
      "LIST-FAILURE: the list-phase error PROPAGATES (run.ts isolates it per-pass)",
      threw === boom,
      String(threw),
    );
    const [polled] = await sql<{ count: string }[]>`
      select count(*)::text as count from poll_cursor where source = ${SOURCE} and last_polled_at is not null
    `;
    assert(
      "LIST-FAILURE: last_polled_at is STILL stamped (finally) so monitoring never goes dark",
      polled!.count === "1",
      polled!.count,
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== fr-poll results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
