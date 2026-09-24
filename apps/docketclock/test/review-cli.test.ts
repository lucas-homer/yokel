/**
 * review-cli.test.ts — the operator review core (Slice R, PR-R3; src/review/core.ts). The CLI is a
 * thin wrapper; these tests drive the real queue/show/resolve logic against a throwaway Postgres.
 *
 * Proves the load-bearing properties:
 *   • QUEUE v1 — lists exactly the windows whose confidence demands a human (conflicting/stale),
 *     closing-soonest first; a healthy window never appears; a resolved window LEAVES the queue.
 *   • SHOW — one screen: latest-per-source values, prior verdicts (latest first), conflict counts.
 *   • RESOLVE happy path — writes the verdict through ingest (typed, audited), fills
 *     reviewed_payload_hashes from the latest source observations AT WRITE TIME, and returns the
 *     re-derived window honored at HIGH with human_resolved.
 *   • REFUSALS (the #116 adversary guards) — unknown ocd_id and source-less windows are rejected
 *     BEFORE anything touches the log; contract violations (pin without close, empty note) likewise.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import {
  resolveWindow,
  reviewQueue,
  reviewQueueStats,
  reviewShow,
} from "../src/review/core.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
async function rejects(name: string, op: () => unknown, re: RegExp) {
  try {
    await op();
    assert(name, false, "did not throw");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, re.test(msg), msg);
  }
}

const HERE = dirname(fileURLToPath(import.meta.url));
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;
const regsFixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as { data: { id: string; attributes: Record<string, unknown> } };

const NOW = new Date("2026-09-02T00:00:00Z");
const OCD_CONFLICT = "ocd-participation-window/federal/2025-02910";
const OCD_CLEAN = "ocd-participation-window/federal/2025-55555";

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // A CONFLICTING window: FR says 09-15, Regs says 09-20 Eastern (explicit stamps — no clock races).
  await ingestObservation(sql, {
    ...parseFrObservation({ ...frFixture, comments_close_on: "2026-09-15" }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  const regsRaw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  Object.assign(regsRaw.data.attributes, {
    frDocNum: "2025-02910",
    commentEndDate: "2026-09-21T03:59:59Z",
    withdrawn: false,
    openForComment: true,
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRaw),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD_CONFLICT, NOW);

  // A clean HIGH window that must never enter the queue.
  await ingestObservation(sql, {
    ...parseFrObservation({
      ...frFixture,
      document_number: "2025-55555",
      comments_close_on: "2026-10-01",
    }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  const regsRawClean = JSON.parse(
    JSON.stringify(regsFixture),
  ) as typeof regsFixture;
  Object.assign(regsRawClean.data.attributes, {
    frDocNum: "2025-55555",
    commentEndDate: "2026-10-02T03:59:59Z", // Eastern 2026-10-01 — agrees
    withdrawn: false,
    openForComment: true,
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRawClean),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD_CLEAN, NOW);

  // ── QUEUE: exactly the conflicting window, not the clean one ────────────────────────────────────────
  const q1 = await reviewQueue(sql);
  assert(
    "QUEUE: lists exactly the conflicting window",
    q1.length === 1 &&
      q1[0]!.ocd_id === OCD_CONFLICT &&
      q1[0]!.confidence === "conflicting",
    JSON.stringify(q1.map((r) => r.ocd_id)),
  );

  // ── STATS (PR-R4): depth by reason + rot age anchored on first detection ────────────────────────────
  const stats1 = await reviewQueueStats(sql, new Date("2026-09-03T00:00:00Z"));
  assert(
    "STATS: depth counts the conflicting window, stale stays 0",
    stats1.byReason.conflicting === 1 && stats1.byReason.stale === 0,
    JSON.stringify(stats1.byReason),
  );
  assert(
    "STATS: rot age = now minus the conflict's FIRST detection (reconciled at 2026-09-02 → 24h)",
    stats1.oldestAgeSeconds !== null &&
      Math.abs(stats1.oldestAgeSeconds - 86400) < 60,
    String(stats1.oldestAgeSeconds),
  );

  // ── SHOW: sources side-by-side, no verdicts yet, one live conflict ──────────────────────────────────
  const s1 = await reviewShow(sql, OCD_CONFLICT);
  assert(
    "SHOW: window present with both sources summarized",
    s1.window !== null &&
      s1.sources.length === 2 &&
      s1.sources.some(
        (x) =>
          x.source === "federal_register" && x.close_value === "2026-09-15",
      ) &&
      s1.sources.some(
        (x) =>
          x.source === "regulations_gov" &&
          x.close_value === "2026-09-21T03:59:59Z",
      ),
    JSON.stringify(s1.sources.map((x) => [x.source, x.close_value])),
  );
  assert(
    "SHOW: one live conflict, zero verdicts",
    s1.liveConflicts === 1 && s1.priorVerdicts.length === 0,
    `live=${s1.liveConflicts} verdicts=${s1.priorVerdicts.length}`,
  );

  // ── REFUSALS: nothing touches the log ───────────────────────────────────────────────────────────────
  await rejects(
    "REFUSE: unknown ocd_id (typo can't mint a window)",
    () =>
      resolveWindow(sql, {
        ocdId: "ocd-participation-window/federal/TYPO-9999",
        kind: "pin_close",
        close: "2026-09-20",
        note: "n",
        operator: "lucas",
      }),
    /no participation_window/,
  );
  await sql`
    insert into participation_windows (ocd_id, window_type, confidence, status)
    values ('ocd-participation-window/federal/ORPHAN-1', 'comment_period', 'unknown', 'open')
  `;
  await rejects(
    "REFUSE: window with no source observations (adversary S3j guard)",
    () =>
      resolveWindow(sql, {
        ocdId: "ocd-participation-window/federal/ORPHAN-1",
        kind: "pin_close",
        close: "2026-09-20",
        note: "n",
        operator: "lucas",
      }),
    /no source observations/,
  );
  await rejects(
    "REFUSE: pin_close without --close (contract superRefine)",
    () =>
      resolveWindow(sql, {
        ocdId: OCD_CONFLICT,
        kind: "pin_close",
        note: "n",
        operator: "lucas",
      }),
    /pinned_close_date/,
  );
  await rejects(
    "REFUSE: whitespace-only note (the why is the point)",
    () =>
      resolveWindow(sql, {
        ocdId: OCD_CONFLICT,
        kind: "dismiss_conflict",
        note: "   ",
        operator: "lucas",
      }),
    /note/,
  );
  const [logCount] = await sql<{ n: string }[]>`
    select count(*) as n from observations where source = 'human_review'
  `;
  assert(
    "REFUSE: zero human_review rows written by any refusal",
    logCount!.n === "0",
    logCount!.n,
  );

  // ── RESOLVE happy path: pin the close, window honored at HIGH, queue empties ───────────────────────
  const resolved = await resolveWindow(
    sql,
    {
      ocdId: OCD_CONFLICT,
      kind: "pin_close",
      close: "2026-09-20",
      note: "Regs value is right; FR DATES text carries the superseded date.",
      operator: "lucas",
    },
    new Date("2026-09-02T01:00:00Z"),
  );
  assert("RESOLVE: verdict inserted", resolved.inserted === true);
  assert(
    "RESOLVE: evidence hashes = the latest per-source payload hashes at write time",
    resolved.reviewedHashes.length === 2,
    String(resolved.reviewedHashes.length),
  );
  assert(
    "RESOLVE: re-derived window honored (HIGH, pinned close, human_resolved)",
    resolved.result.window.confidence === "high" &&
      resolved.result.window.resolved_close_display ===
        "closes 2026-09-20 at 11:59 p.m. ET (pinned by human review)" &&
      resolved.result.window.conflict_flags.includes("human_resolved"),
    `${resolved.result.window.confidence} ${resolved.result.window.resolved_close_display}`,
  );

  const q2 = await reviewQueue(sql);
  assert(
    "QUEUE: resolved window leaves the queue",
    q2.every((r) => r.ocd_id !== OCD_CONFLICT),
    JSON.stringify(q2.map((r) => r.ocd_id)),
  );
  const s2 = await reviewShow(sql, OCD_CONFLICT);
  assert(
    "SHOW: prior verdict now listed; live conflict retired",
    s2.priorVerdicts.length === 1 &&
      !("unparseable" in s2.priorVerdicts[0]!.verdict) &&
      s2.priorVerdicts[0]!.verdict.kind === "pin_close" &&
      s2.liveConflicts === 0 &&
      s2.retiredConflicts === 1,
    `verdicts=${s2.priorVerdicts.length} live=${s2.liveConflicts} retired=${s2.retiredConflicts}`,
  );

  // ── STATS after resolve: queue empty, rot age null (→ NaN gauge, alert can never fire) ─────────────
  const stats2 = await reviewQueueStats(sql, new Date("2026-09-03T00:00:00Z"));
  assert(
    "STATS: resolved queue reads empty with null rot age",
    stats2.byReason.conflicting === 0 &&
      stats2.byReason.stale === 0 &&
      stats2.oldestAgeSeconds === null,
    JSON.stringify(stats2),
  );

  // Metadata still appends to the immutable log, but does not reopen a reviewed conflict.
  const refreshedRaw = {
    ...regsRaw,
    data: {
      ...regsRaw.data,
      attributes: {
        ...regsRaw.data.attributes,
        modifyDate: "2026-09-03T00:00:00Z",
      },
    },
    links: {
      self: `https://api.regulations.gov/v4/documents/${regsRaw.data.id}`,
    },
  };
  const refresh = await ingestObservation(sql, {
    ...parseRegsObservation(refreshedRaw),
    fetched_at: "2026-09-03T00:00:00.000Z",
  });
  assert(
    "REFRESH: distinct metadata payload is still appended",
    refresh.inserted,
  );
  await reconcileOcdId(sql, OCD_CONFLICT, new Date("2026-09-03T01:00:00Z"));
  const s3 = await reviewShow(sql, OCD_CONFLICT);
  assert(
    "REFRESH: original verdict and evidence hashes are unchanged",
    JSON.stringify(s3.priorVerdicts) === JSON.stringify(s2.priorVerdicts),
  );
  assert(
    "REFRESH: verdict remains honored and conflict stays retired",
    s3.window?.confidence === "high" &&
      Array.isArray(s3.window.conflict_flags) &&
      s3.window.conflict_flags.includes("human_resolved") &&
      s3.liveConflicts === 0 &&
      s3.retiredConflicts === 1,
  );
  assert(
    "REFRESH: reviewed window stays out of the queue",
    (await reviewQueue(sql)).every((r) => r.ocd_id !== OCD_CONFLICT),
  );

  // A real deadline change still resurfaces and keeps the prior verdict as audit history.
  const changedRaw = structuredClone(refreshedRaw);
  Object.assign(changedRaw.data.attributes, {
    commentEndDate: "2026-09-23T03:59:59Z",
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(changedRaw),
    fetched_at: "2026-09-04T00:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD_CONFLICT, new Date("2026-09-04T01:00:00Z"));
  const s4 = await reviewShow(sql, OCD_CONFLICT);
  assert(
    "CHANGED: substantive source revision resurfaces in queue",
    s4.window?.confidence === "conflicting" &&
      Array.isArray(s4.window.conflict_flags) &&
      !s4.window.conflict_flags.includes("human_resolved") &&
      s4.liveConflicts === 1 &&
      (await reviewQueue(sql)).some((r) => r.ocd_id === OCD_CONFLICT),
  );
  assert(
    "CHANGED: prior verdict is preserved without adding a new verdict",
    JSON.stringify(s4.priorVerdicts) === JSON.stringify(s2.priorVerdicts),
  );
} finally {
  await sql.end();
}

console.log("\n=== review-cli results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
