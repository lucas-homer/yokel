/**
 * verify-adversary.test.ts — adversarial verification of PR-V1 (slice V): every assertion here
 * states the SPEC-mandated behavior (plans/verification-accuracy.md "Decisions locked" + the 0.9.0
 * contract comments). Assertions tagged [REAL-BUG] FAIL against the shipped implementation — each
 * is a demonstrated way the accuracy loop publishes fake certainty or silently drops a miss. They
 * are written spec-side ON PURPOSE: after the fixes land they flip green and stay as regressions.
 * Assertions tagged [REGRESSION] pass today and pin edge behavior the adversary confirmed correct.
 *
 * REAL BUGS demonstrated (see the per-section headers for the concrete breaking input):
 *   RB-1  verdict.ts: the reopening suppression of rule 4 is DIRECTION-INSENSITIVE — a post-close
 *         is_reopening flag (or status 'reopened') launders a close that retro-moved EARLIER into
 *         was_correct=true. A reopening can only explain a LATER close; an earlier operative close
 *         means buyers who relied on the published date missed the real deadline — the exact lie
 *         the product exists to prevent.
 *   RB-2  poll.ts/run.ts: stampChecked runs BEFORE parseRegsObservation, so a fetch whose payload
 *         FAILED to parse (schema drift — precisely the payloads that carry changes) still counts
 *         as a "confirmed check", and verifyOnce writes was_correct=true off a check whose content
 *         was never read.
 *   RB-3  migration 0010: contract refinements (3)/(4) and the horizon ordering are NOT mirrored
 *         as DB checks — a direct-SQL (manual-basis — the documented operator path!) insert can
 *         permanently (append-only!) write incoherent rows: was_correct=true naming contradictions,
 *         a lapsed abstention naming contradictions, verified_at before closed_at.
 *   RB-4  run.ts snapshot filter (status <> 'withdrawn' on CURRENT status): a withdrawal that
 *         reconciles between close and the FIRST snapshot (same-cycle ordering: stage 2 ingests the
 *         withdrawal before stage 4 snapshots; downtime widens the race arbitrarily) means the
 *         window is NEVER snapshotted — the revealed-withdrawal MISS is silently suppressed and the
 *         headline gauge inflates.
 *
 * Requires a throwaway Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock exec tsx test/verify-adversary.test.ts
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { verifyOnce } from "../src/verify/run.js";
import { computeVerdict } from "../src/verify/verdict.js";
import { classifyHorizon } from "../src/verify/select.js";
import { pollRegsOnce, type PollDeps } from "../src/poll/poll.js";

let failures = 0;
let bugFailures = 0;
const out: string[] = [];
function assert(
  tag: "REAL-BUG" | "REGRESSION",
  name: string,
  cond: boolean,
  detail = "",
) {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  [${tag}] ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) {
    failures++;
    if (tag === "REAL-BUG") bugFailures++;
  }
}

const DAY = 24 * 3_600_000;
const NOW = new Date("2026-07-13T12:00:00.000Z");
const LATER = new Date(NOW.getTime() + 5 * DAY);
const at = (offsetDays: number) =>
  new Date(NOW.getTime() + offsetDays * DAY).toISOString();
const clock = { now: () => NOW };
const laterClock = { now: () => LATER };

const OCD = (slug: string) => `ocd-participation-window/federal/${slug}`;

const sql = createClient();

async function insertWindow(w: {
  slug: string;
  close: string | null;
  status: string;
  confidence: string;
  version?: number;
  regsDocId?: string | null;
}) {
  await sql`
    insert into participation_windows (
      ocd_id, fr_document_number, regs_document_id, window_type,
      resolved_close_utc, resolved_close_display, confidence, status, version
    ) values (
      ${OCD(w.slug)}, ${w.slug}, ${w.regsDocId ?? null}, 'comment',
      ${w.close}, ${w.close ? "11:59 p.m. ET" : null}, ${w.confidence}, ${w.status}, ${w.version ?? 1}
    )
  `;
}

let obsSeq = 0;
async function insertObservation(o: {
  primarySlug: string; // observations.ocd_id
  targetSlug?: string; // observation_targets.ocd_id (defaults to primary)
  fetchedAt: string;
  flags?: Partial<
    Record<
      "is_extension" | "is_correction" | "is_withdrawal" | "is_reopening",
      boolean
    >
  >;
}): Promise<string> {
  const id = `adv-obs-${++obsSeq}`;
  await sql`
    insert into observations (
      observation_id, ocd_id, source, fr_document_number, payload_hash, fetched_at,
      parser_version, is_extension, is_correction, is_withdrawal, is_reopening, raw
    ) values (
      ${id}, ${OCD(o.primarySlug)}, 'federal_register', ${o.primarySlug},
      ${String(obsSeq).padStart(2, "0").repeat(32)}, ${o.fetchedAt}, 'adv-v1',
      ${o.flags?.is_extension ?? false}, ${o.flags?.is_correction ?? false},
      ${o.flags?.is_withdrawal ?? false}, ${o.flags?.is_reopening ?? false}, '{}'::jsonb
    )
  `;
  await sql`
    insert into observation_targets (observation_id, ocd_id)
    values (${id}, ${OCD(o.targetSlug ?? o.primarySlug)})
  `;
  return id;
}

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // ═══ PURE — RB-1: reopening suppression must be DIRECTION-SCOPED ═════════════════════════════════
  // A reopening explains a LATER close (a fresh reliance window). It can never explain a close that
  // retro-moved EARLIER: an earlier operative close means the published close was wrong when
  // published (buyers relying on it missed the real deadline). Rule 4 must still convict.
  out.push("PURE — verdict rules (RB-1 + confirmed-correct combinations):");
  {
    const CLOSE = at(0);
    const mkObs = (
      id: string,
      d: number,
      f: Partial<
        Record<
          "is_extension" | "is_correction" | "is_withdrawal" | "is_reopening",
          boolean
        >
      > = {},
    ) => ({
      observation_id: id,
      fetched_at: at(d),
      is_extension: f.is_extension ?? false,
      is_correction: f.is_correction ?? false,
      is_withdrawal: f.is_withdrawal ?? false,
      is_reopening: f.is_reopening ?? false,
    });

    const reopenEarlier = computeVerdict({
      publishedCloseUtc: CLOSE,
      currentCloseUtc: at(-5), // the operative close turned out EARLIER than we published
      currentStatus: "closed",
      observationsSinceClose: [mkObs("o-re", 2, { is_reopening: true })],
      lapsed: false,
    });
    assert(
      "REAL-BUG",
      "RB-1a is_reopening + close moved EARLIER → MISS (a reopening never explains an earlier close)",
      reopenEarlier.was_correct === false,
      JSON.stringify(reopenEarlier),
    );

    const statusReopenEarlier = computeVerdict({
      publishedCloseUtc: CLOSE,
      currentCloseUtc: at(-5),
      currentStatus: "reopened", // stale/previous-lifecycle status, not time-scoped to this movement
      observationsSinceClose: [mkObs("o-x", 2)],
      lapsed: false,
    });
    assert(
      "REAL-BUG",
      "RB-1b status 'reopened' + unflagged obs + close moved EARLIER → MISS (status is not time-scoped; it cannot explain an earlier close)",
      statusReopenEarlier.was_correct === false,
      JSON.stringify(statusReopenEarlier),
    );

    // Confirmed-correct nasty combinations (pass today — pinned as regressions):
    const reopenLater = computeVerdict({
      publishedCloseUtc: CLOSE,
      currentCloseUtc: at(30),
      currentStatus: "reopened",
      observationsSinceClose: [mkObs("o-re", 5, { is_reopening: true })],
      lapsed: false,
    });
    assert(
      "REGRESSION",
      "reopening + close moved LATER → correct (the locked decision: reopening is not a miss)",
      reopenLater.was_correct === true,
    );

    const extAndReopenSameObs = computeVerdict({
      publishedCloseUtc: CLOSE,
      currentCloseUtc: at(30),
      currentStatus: "closed",
      observationsSinceClose: [
        mkObs("o-er", 2, { is_extension: true, is_reopening: true }),
      ],
      lapsed: false,
    });
    assert(
      "REGRESSION",
      "ONE obs flagged extension+reopening, close later → correct (rule 3 defers to the reopening reading; rule 4 suppressed)",
      extAndReopenSameObs.was_correct === true,
    );

    const reopenPlusCorrection = computeVerdict({
      publishedCloseUtc: CLOSE,
      currentCloseUtc: at(30),
      currentStatus: "closed",
      observationsSinceClose: [
        mkObs("o-re", 2, { is_reopening: true }),
        mkObs("o-corr", 3, { is_correction: true }),
      ],
      lapsed: false,
    });
    assert(
      "REGRESSION",
      "reopening + a correction in the same post-close set, close moved → the correction STILL convicts via rule 2 (reopened only suppresses rule 4)",
      reopenPlusCorrection.was_correct === false &&
        reopenPlusCorrection.contradicting_observation_ids.join(",") ===
          "o-corr",
      JSON.stringify(reopenPlusCorrection),
    );

    const withdrawalOnReopened = computeVerdict({
      publishedCloseUtc: CLOSE,
      currentCloseUtc: at(30),
      currentStatus: "reopened",
      observationsSinceClose: [mkObs("o-wd", 2, { is_withdrawal: true })],
      lapsed: false,
    });
    assert(
      "REGRESSION",
      "is_withdrawal on a 'reopened' window → still a MISS (rule 1 is unconditional; a withdrawal is never explained by a reopening)",
      withdrawalOnReopened.was_correct === false &&
        withdrawalOnReopened.contradicting_observation_ids.join(",") === "o-wd",
      JSON.stringify(withdrawalOnReopened),
    );

    // Horizon boundary pins (all pass today):
    const facts = (checkAt: string | null) => ({
      publishedCloseUtc: CLOSE,
      confirmedCheckAt: checkAt,
    });
    const closeMs = Date.parse(CLOSE);
    assert(
      "REGRESSION",
      "exactly close+7d, no check → in_horizon (inclusive boundary; verdict only strictly past the horizon)",
      classifyHorizon(facts(null), new Date(closeMs + 7 * DAY)) ===
        "in_horizon",
    );
    assert(
      "REGRESSION",
      "exactly close+14d, no check → awaiting_check (cap boundary inclusive; lapse only strictly past it)",
      classifyHorizon(facts(null), new Date(closeMs + 14 * DAY)) ===
        "awaiting_check",
    );
    assert(
      "REGRESSION",
      "close+14d+1ms, no check → due_lapsed",
      classifyHorizon(facts(null), new Date(closeMs + 14 * DAY + 1)) ===
        "due_lapsed",
    );
    assert(
      "REGRESSION",
      "a check 1ms after close counts (strictly-after at ms precision)",
      classifyHorizon(
        facts(new Date(closeMs + 1).toISOString()),
        new Date(closeMs + 8 * DAY),
      ) === "due_verdict",
    );
    assert(
      "REGRESSION",
      "a check landing PAST the cap (verifier was down at day 14) still converts to due_verdict — evidence beats abstention",
      classifyHorizon(facts(at(16)), new Date(closeMs + 17 * DAY)) ===
        "due_verdict",
    );
  }

  // ═══ DB scenario setup for RB-1 (end-to-end), RB-4, and the multi-target regression ═════════════
  // rb1: closes at(-3) (inside horizon at NOW) so the drift can land BEFORE the verdict.
  await insertWindow({
    slug: "rb1-reopen-earlier",
    close: at(-3),
    status: "closed",
    confidence: "high",
    version: 2,
  });
  // rb4: reconcile flipped the window to withdrawn (keeping the close — reconcile.ts:224 preserves
  // it) BEFORE the first verify snapshot: the same-cycle stage-2-before-stage-4 ordering, or any
  // downtime, produces exactly this state.
  await insertWindow({
    slug: "rb4-withdrawn-race",
    close: at(-8),
    status: "withdrawn",
    confidence: "high",
  });
  const rb4Obs = await insertObservation({
    primarySlug: "rb4-withdrawn-race",
    fetchedAt: at(-6),
    flags: { is_withdrawal: true },
  });
  // mt: the EPA-2025-02910 shape — the amendment's PRIMARY ocd_id is a different window; it reaches
  // this window only through observation_targets. Closes at(-3) so the drift lands pre-verdict.
  await insertWindow({
    slug: "mt-target",
    close: at(-3),
    status: "closed",
    confidence: "high",
    version: 1,
  });
  await insertWindow({
    slug: "mt-primary",
    close: at(40),
    status: "open",
    confidence: "high",
  });

  // cycle 1 @ NOW — snapshots rb1 + mt-target (rb4 MUST be snapshotted per spec; impl skips it).
  const s1 = await verifyOnce(sql, clock);

  assert(
    "REAL-BUG",
    "RB-4 a window withdrawn between close and first snapshot IS snapshotted (else its revealed-withdrawal miss is unrecordable)",
    (
      await sql<{ n: string }[]>`
        select count(*) as n from verification_watch where ocd_id = ${OCD("rb4-withdrawn-race")}
      `
    )[0]?.n === "1",
    `snapshot summary: ${JSON.stringify(s1)}`,
  );

  // rb1 drift: a post-close reopening-flagged obs lands, and the re-derived close moves EARLIER.
  const rb1Obs = await insertObservation({
    primarySlug: "rb1-reopen-earlier",
    fetchedAt: at(-2),
    flags: { is_reopening: true },
  });
  await sql`
    update participation_windows
      set resolved_close_utc = ${at(-6)}, version = 3
    where ocd_id = ${OCD("rb1-reopen-earlier")}
  `;

  // mt drift: the multi-target correction (primary = mt-primary, target = mt-target) moves mt-target.
  const mtObs = await insertObservation({
    primarySlug: "mt-primary",
    targetSlug: "mt-target",
    fetchedAt: at(-2),
    flags: { is_correction: true },
  });
  await sql`
    update participation_windows
      set resolved_close_utc = ${at(7)}, version = 2
    where ocd_id = ${OCD("mt-target")}
  `;

  // cycle 2 @ LATER (past rb1/mt horizons) — verdicts land.
  const s2 = await verifyOnce(sql, laterClock);

  const rb1Row = (
    await sql<
      { was_correct: boolean | null; contradicting_observation_ids: string[] }[]
    >`
      select was_correct, contradicting_observation_ids
      from accuracy_records where ocd_id = ${OCD("rb1-reopen-earlier")}
    `
  )[0];
  assert(
    "REAL-BUG",
    "RB-1c END-TO-END: post-close reopening flag + close re-derived EARLIER → was_correct=false (impl launders it to true)",
    rb1Row !== undefined && rb1Row.was_correct === false,
    JSON.stringify({ rb1Row, s2, expectedEvidence: rb1Obs }),
  );

  const rb4Row = (
    await sql<
      { was_correct: boolean | null; contradicting_observation_ids: string[] }[]
    >`
      select was_correct, contradicting_observation_ids
      from accuracy_records where ocd_id = ${OCD("rb4-withdrawn-race")}
    `
  )[0];
  assert(
    "REAL-BUG",
    "RB-4 END-TO-END: the revealed-withdrawal miss is RECORDED even when reconcile flipped status→withdrawn before the first snapshot",
    rb4Row !== undefined &&
      rb4Row.was_correct === false &&
      JSON.stringify(rb4Row.contradicting_observation_ids) ===
        JSON.stringify([rb4Obs]),
    JSON.stringify(
      rb4Row ??
        "NO RECORD — window was never snapshotted, miss suppressed, gauge inflated",
    ),
  );

  const mtRow = (
    await sql<
      {
        was_correct: boolean | null;
        basis: string;
        contradicting_observation_ids: string[];
      }[]
    >`
      select was_correct, basis, contradicting_observation_ids
      from accuracy_records where ocd_id = ${OCD("mt-target")}
    `
  )[0];
  assert(
    "REGRESSION",
    "EPA-multi-docket shape: an amendment whose PRIMARY ocd_id is another window convicts THIS window via observation_targets (and counts as its confirmed check)",
    mtRow !== undefined &&
      mtRow.was_correct === false &&
      mtRow.basis === "late_amendment" &&
      JSON.stringify(mtRow.contradicting_observation_ids) ===
        JSON.stringify([mtObs]),
    JSON.stringify(mtRow),
  );

  // ═══ RB-2 — a fetch whose payload FAILED to parse must not count as a confirmed check ═══════════
  // poll.ts stamps regs_poll_watch BEFORE parseRegsObservation; a schema-drifted payload (exactly
  // the kind that carries a changed close) throws AFTER the stamp — and verifyOnce then writes
  // was_correct=true off a "check" whose content was never read.
  await insertWindow({
    slug: "rb2-stamp-parse",
    close: at(-8),
    status: "closed",
    confidence: "high",
    regsDocId: "DOC-RB2-0001",
  });
  const s3 = await verifyOnce(sql, laterClock); // snapshot; no check yet → awaiting (past 7d horizon)
  assert(
    "REGRESSION",
    "rb2 setup: past horizon with zero checks → awaiting_check, no record (never correctness-by-default)",
    s3.awaitingCheck >= 1 &&
      (
        await sql<{ n: string }[]>`
          select count(*) as n from accuracy_records where ocd_id = ${OCD("rb2-stamp-parse")}
        `
      )[0]?.n === "0",
    JSON.stringify(s3),
  );

  const deps: Partial<PollDeps> = {
    listPage: async () => [],
    // fetch SUCCEEDS, parse THROWS (no attributes → no frDocNum/objectId): the content was never read.
    fetchDetail: async () => ({ data: { id: "DOC-RB2-0001" } }),
    now: () => LATER,
  };
  await pollRegsOnce(sql, deps); // stampChecked lands before the parse failure

  const s4 = await verifyOnce(sql, laterClock);
  const rb2Records = await sql<
    { was_correct: boolean | null; basis: string }[]
  >`
    select was_correct, basis from accuracy_records where ocd_id = ${OCD("rb2-stamp-parse")}
  `;
  assert(
    "REAL-BUG",
    "RB-2 a fetch that could NOT be parsed/ingested is not a confirmed check → still NO record (impl writes was_correct=true off the poisoned stamp)",
    rb2Records.length === 0,
    JSON.stringify({ rb2Records, s4 }),
  );

  // ═══ RB-3 — DB checks must mirror ALL contract refinements (append-only makes bad rows permanent) ═
  // The documented operator path ('manual' basis) is direct SQL — the DB is the ONLY validator there,
  // and the append-only trigger means an incoherent row can never be corrected or deleted.
  out.push("RB-3 — DB-check parity with the 0.9.0 refinements:");
  async function insertRejected(
    name: string,
    row: {
      slug: string;
      version: number;
      was_correct: boolean | null;
      basis: string;
      ids: string;
      closedAt: string;
      verifiedAt: string;
    },
  ) {
    let rejected = false;
    let detail =
      "insert SUCCEEDED — incoherent row is now PERMANENT (append-only)";
    try {
      await sql`
        insert into accuracy_records (
          ocd_id, window_version, confidence_at_close, published_close_utc,
          was_correct, basis, contradicting_observation_ids, closed_at_utc, verified_at_utc
        ) values (
          ${OCD(row.slug)}, ${row.version}, 'high', ${row.closedAt},
          ${row.was_correct}, ${row.basis}, ${row.ids}::jsonb, ${row.closedAt}, ${row.verifiedAt}
        )
      `;
    } catch (e) {
      rejected = true;
      detail = e instanceof Error ? e.message : String(e);
    }
    return { rejected, detail };
  }

  {
    // Refinement (3): was_correct=true must carry EMPTY contradicting ids.
    const r3 = await insertRejected("true+ids", {
      slug: "rb3-true-with-ids",
      version: 1,
      was_correct: true,
      basis: "manual",
      ids: '["obs-lie"]',
      closedAt: at(-2),
      verifiedAt: at(0),
    });
    assert(
      "REAL-BUG",
      "RB-3a DB rejects was_correct=true WITH contradicting ids (contract refinement 3 — 'lying in one direction or the other')",
      r3.rejected,
      r3.detail,
    );

    // Refinement (4): a lapsed abstention must carry EMPTY contradicting ids.
    const r4 = await insertRejected("lapsed+ids", {
      slug: "rb3-lapsed-with-ids",
      version: 1,
      was_correct: null,
      basis: "unverified_lapsed",
      ids: '["obs-x"]',
      closedAt: at(-2),
      verifiedAt: at(0),
    });
    assert(
      "REAL-BUG",
      "RB-3b DB rejects a lapsed record naming contradictions (contract refinement 4 — a contradiction in hand is a verdict, not an abstention)",
      r4.rejected,
      r4.detail,
    );

    // Horizon ordering: verified_at_utc >= closed_at_utc (AccuracyHorizon refinement).
    const rh = await insertRejected("verified<closed", {
      slug: "rb3-horizon-backwards",
      version: 1,
      was_correct: true,
      basis: "manual",
      ids: "[]",
      closedAt: at(-2),
      verifiedAt: at(-5),
    });
    assert(
      "REAL-BUG",
      "RB-3c DB rejects verified_at_utc < closed_at_utc (verification is post-close by definition)",
      rh.rejected,
      rh.detail,
    );

    // Two-directional lapsed⇔null — the direction the existing suite did NOT probe:
    const rm = await insertRejected("manual+null", {
      slug: "rb3-manual-null",
      version: 1,
      was_correct: null,
      basis: "manual",
      ids: "[]",
      closedAt: at(-2),
      verifiedAt: at(0),
    });
    assert(
      "REGRESSION",
      "DB rejects basis='manual' with was_correct NULL (lapsed⇔null holds in BOTH directions)",
      rm.rejected,
      rm.detail,
    );
  }

  // ═══ Snapshot-guard lifecycle pins (documented behavior, pass today) ═════════════════════════════
  out.push(
    "snapshot-guard lifecycle (pins — see verdict notes for the SPEC-GAP questions):",
  );
  {
    // f1 — post-verdict correction moving the close EARLIER: guard blocks forever (no second
    // snapshot/verdict). Pinned as CURRENT behavior; flagged as a spec gap in the verdict notes
    // (the corrected earlier close is a retroactive claim nobody relied on prospectively).
    await insertWindow({
      slug: "f1-earlier-after-verdict",
      close: at(-10),
      status: "closed",
      confidence: "high",
      regsDocId: "DOC-F1-0001",
    });
    await sql`insert into regs_poll_watch (regs_document_id, last_checked_at) values ('DOC-F1-0001', ${at(-2)})`;
    await verifyOnce(sql, laterClock); // snapshot + immediate verdict (checked, past horizon)
    await sql`
      update participation_windows set resolved_close_utc = ${at(-12)}, version = 2
      where ocd_id = ${OCD("f1-earlier-after-verdict")}
    `;
    const sf1 = await verifyOnce(sql, laterClock);
    const f1Watches = await sql<{ n: string }[]>`
      select count(*) as n from verification_watch where ocd_id = ${OCD("f1-earlier-after-verdict")}
    `;
    assert(
      "REGRESSION",
      "post-verdict close moved EARLIER → NO re-snapshot, ever (guard admits only strictly-later closes) [pinned; SPEC-GAP question raised]",
      f1Watches[0]?.n === "1" && sf1.snapshotted === 0,
      JSON.stringify({ f1Watches, sf1 }),
    );

    // f2 — post-verdict correction moving the close LATER (still past): the reopened-and-closed-again
    // admission fires → second snapshot at the new version → second FINAL record.
    await insertWindow({
      slug: "f2-later-after-verdict",
      close: at(-10),
      status: "closed",
      confidence: "high",
      regsDocId: "DOC-F2-0001",
    });
    await sql`insert into regs_poll_watch (regs_document_id, last_checked_at) values ('DOC-F2-0001', ${at(-2)})`;
    await verifyOnce(sql, laterClock); // first verdict at v1
    await sql`
      update participation_windows set resolved_close_utc = ${at(-8)}, version = 2
      where ocd_id = ${OCD("f2-later-after-verdict")}
    `;
    await verifyOnce(sql, laterClock); // guard admits (later close) → snapshot v2 → second verdict
    const f2Records = await sql<
      { window_version: number; was_correct: boolean | null }[]
    >`
      select window_version, was_correct from accuracy_records
      where ocd_id = ${OCD("f2-later-after-verdict")} order by window_version
    `;
    assert(
      "REGRESSION",
      "post-verdict close moved LATER (still past) → a SECOND snapshot+record at the new version (each lifecycle judged once)",
      f2Records.length === 2 &&
        f2Records[0]?.window_version === 1 &&
        f2Records[1]?.window_version === 2,
      JSON.stringify(f2Records),
    );
  }

  // ═══ Migration 0010 idempotency — the raw DDL re-runs cleanly on an already-migrated schema ═════
  {
    const dir = join(
      dirname(fileURLToPath(import.meta.url)),
      "..",
      "migrations",
    );
    const ddl = await readFile(join(dir, "0010_accuracy_records.sql"), "utf8");
    let clean = true;
    let detail = "";
    try {
      await sql.unsafe(ddl);
    } catch (e) {
      clean = false;
      detail = e instanceof Error ? e.message : String(e);
    }
    assert(
      "REGRESSION",
      "0010 DDL is idempotent (re-run on a live schema is a no-op)",
      clean,
      detail,
    );
  }
} finally {
  await sql.end({ timeout: 5 });
}

console.log(out.join("\n"));
if (failures > 0) {
  console.error(
    `\n${failures} FAILURE(S) — ${bugFailures} of them are [REAL-BUG] demonstrations (spec-side assertions that flip green when the bugs are fixed).`,
  );
  process.exit(1);
}
console.log("\nALL EXPECTATIONS MET");
