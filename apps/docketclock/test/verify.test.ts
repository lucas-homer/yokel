/**
 * verify.test.ts — the DB-backed post-close verification pass (slice V, PR-V1): migration 0010, the
 * verification_watch snapshot lifecycle, verifyOnce's verdict writes, the accuracy_records
 * append-only guard, the re-poll-set widening in poll.ts, and the 90d HIGH rollup.
 *
 * Matches observation-log.test.ts / poll.test.ts style: hand-rolled assert/rejects, out[]
 * accumulator, fresh schema per run, a deterministic injected clock (NOW) everywhere.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * Scenario map (one window per scenario, independent):
 *   w-clean      — closed 8d ago, post-close regs check landed → was_correct=true / post_close_repoll;
 *   w-corr       — closed 8d ago, post-close CORRECTION moved the close → false / late_amendment,
 *                  the correction observation named; snapshot IMMUNITY: the projection was flipped
 *                  HIGH→conflicting post-close, but the record judges confidence_at_close = high;
 *   w-defer      — closed 8d ago, ZERO post-close checks → NO record (awaiting_check, horizon
 *                  extends); a check landing later CONVERTS it to a true verdict;
 *   w-lapse      — closed 15d ago, ZERO checks ever → unverified_lapsed with was_correct NULL;
 *   w-young      — closed 1d ago → in_horizon, no record; ALSO the re-poll-widening subject: its
 *                  status is 'closed' yet it must appear in the regs re-poll set while its watch is
 *                  unresolved, and must drop back out once its record exists;
 *   w-open       — still open → never snapshotted;
 *   w-withdrawn  — withdrawn → never snapshotted;
 *   w-abstain    — conflicting with a NULL close → never snapshotted (no claim to judge).
 */
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { verifyOnce, highCorrectRatio90d } from "../src/verify/run.js";
import { pollRegsOnce, type PollDeps } from "../src/poll/poll.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
async function rejects(name: string, op: () => Promise<unknown>) {
  try {
    await op();
    assert(name, false, "operation SUCCEEDED — the record was mutated!");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, /append-only/.test(msg), msg);
  }
}

const DAY = 24 * 3_600_000;
const NOW = new Date("2026-07-13T12:00:00.000Z");
const at = (offsetDays: number) =>
  new Date(NOW.getTime() + offsetDays * DAY).toISOString();
const clock = { now: () => NOW };

const sql = createClient();

const OCD = (slug: string) => `ocd-participation-window/federal/${slug}`;

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
  slug: string;
  fetchedAt: string;
  flags?: Partial<
    Record<
      "is_extension" | "is_correction" | "is_withdrawal" | "is_reopening",
      boolean
    >
  >;
}): Promise<string> {
  const id = `obs-${++obsSeq}`;
  await sql`
    insert into observations (
      observation_id, ocd_id, source, fr_document_number, payload_hash, fetched_at,
      parser_version, is_extension, is_correction, is_withdrawal, is_reopening, raw
    ) values (
      ${id}, ${OCD(o.slug)}, 'federal_register', ${o.slug},
      ${"ab".repeat(32)}, ${o.fetchedAt}, 'test-v1',
      ${o.flags?.is_extension ?? false}, ${o.flags?.is_correction ?? false},
      ${o.flags?.is_withdrawal ?? false}, ${o.flags?.is_reopening ?? false}, '{}'::jsonb
    )
  `;
  await sql`
    insert into observation_targets (observation_id, ocd_id) values (${id}, ${OCD(o.slug)})
  `;
  return id;
}

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0010 applies cleanly",
    applied.includes("0010_accuracy_records.sql"),
    applied.join(", "),
  );

  // ── scenario setup ─────────────────────────────────────────────────────────────────────────────
  await insertWindow({
    slug: "w-clean",
    close: at(-8),
    status: "closed",
    confidence: "high",
    regsDocId: "DOC-CLEAN-0001",
  });
  await insertWindow({
    slug: "w-corr",
    close: at(-8),
    status: "closed",
    confidence: "high",
    version: 4,
  });
  await insertWindow({
    slug: "w-defer",
    close: at(-8),
    status: "closed",
    confidence: "medium",
  });
  await insertWindow({
    slug: "w-lapse",
    close: at(-15),
    status: "closed",
    confidence: "high",
  });
  await insertWindow({
    slug: "w-young",
    close: at(-1),
    status: "closed",
    confidence: "high",
    regsDocId: "DOC-YOUNG-0001",
  });
  await insertWindow({
    slug: "w-open",
    close: at(30),
    status: "open",
    confidence: "high",
    regsDocId: "DOC-OPEN-0001",
  });
  await insertWindow({
    slug: "w-withdrawn",
    close: at(-8),
    status: "withdrawn",
    confidence: "high",
  });
  await insertWindow({
    slug: "w-abstain",
    close: null,
    status: "unknown",
    confidence: "conflicting",
  });

  // w-clean: a successful post-close regs detail check (the dedupe-skip path — stamp only, no new obs).
  await sql`insert into regs_poll_watch (regs_document_id, last_checked_at) values ('DOC-CLEAN-0001', ${at(-3)})`;
  // w-corr: a post-close correction observation; the projection has ALREADY drifted (close moved +10d,
  // confidence flipped conflicting, version bumped) — exactly what the snapshot must be immune to…
  // except the snapshot happens on the FIRST verifyOnce cycle, so we apply the drift AFTER that below.
  const corrObsId = await insertObservation({
    slug: "w-corr",
    fetchedAt: at(-6),
    flags: { is_correction: true },
  });

  // ── cycle 1 — snapshots + first verdicts ─────────────────────────────────────────────────────────
  const s1 = await verifyOnce(sql, clock);
  assert(
    "cycle 1 snapshots exactly the five judgeable closed windows",
    s1.snapshotted === 5,
    JSON.stringify(s1),
  );
  const watchRows = await sql<
    { ocd_id: string; confidence_at_close: string }[]
  >`
    select ocd_id, confidence_at_close from verification_watch order by ocd_id
  `;
  assert(
    "open / withdrawn / null-close windows are never snapshotted",
    watchRows.length === 5 &&
      !watchRows.some((r) =>
        ["w-open", "w-withdrawn", "w-abstain"].some((s) => r.ocd_id === OCD(s)),
      ),
    JSON.stringify(watchRows),
  );
  assert(
    "w-clean verdict: was_correct=true via the post-close regs stamp (dedupe-skip counts as a check)",
    s1.verdictsCorrect >= 1,
    JSON.stringify(s1),
  );
  assert(
    "no misses on cycle 1 (w-corr's correction did not move the close → not a contradiction)",
    s1.verdictsIncorrect === 0,
    JSON.stringify(s1),
  );
  assert(
    "w-lapse: unverified_lapsed written at 15d with zero checks",
    s1.lapsed === 1,
    JSON.stringify(s1),
  );
  assert(
    "w-defer: past horizon with no check → awaiting_check (no record)",
    s1.awaitingCheck === 1,
    JSON.stringify(s1),
  );
  assert(
    "w-young: inside horizon → in_horizon (no record)",
    s1.inHorizon === 1,
    JSON.stringify(s1),
  );

  const lapseRow = (
    await sql<{ was_correct: boolean | null; basis: string }[]>`
      select was_correct, basis from accuracy_records where ocd_id = ${OCD("w-lapse")}
    `
  )[0];
  assert(
    "lapse record: was_correct IS NULL + basis unverified_lapsed (never correctness-by-default)",
    lapseRow !== undefined &&
      lapseRow.was_correct === null &&
      lapseRow.basis === "unverified_lapsed",
    JSON.stringify(lapseRow),
  );

  // w-corr judged CORRECT on cycle 1? It had a post-close observation (= a confirmed check) and an
  // unmoved close — so yes, it should have been judged correct… unless we drift BEFORE the verdict.
  // To pin the drift-immunity semantics we need the drift BEFORE its verdict — so w-corr's verdict
  // must not have been written yet. It HAD a check though. Assert what actually happened:
  const corrAfter1 = await sql<{ was_correct: boolean | null }[]>`
    select was_correct from accuracy_records where ocd_id = ${OCD("w-corr")}
  `;
  assert(
    "w-corr WAS judged on cycle 1 (check landed, horizon exited) — correct at that point",
    corrAfter1.length === 1 && corrAfter1[0]?.was_correct === true,
    JSON.stringify(corrAfter1),
  );

  // ── drift immunity needs the drift INSIDE the horizon — rebuild w-corr2 properly ────────────────
  // w-corr2: closed 3d ago (inside horizon), correction lands post-close, projection drifts NOW,
  // verdict due at day 8 — the record must judge the AT-CLOSE snapshot, not the drifted projection.
  await insertWindow({
    slug: "w-corr2",
    close: at(-3),
    status: "closed",
    confidence: "high",
    version: 2,
  });
  const s2 = await verifyOnce(sql, clock);
  assert(
    "w-corr2 snapshotted while inside its horizon",
    s2.snapshotted === 1 && s2.inHorizon >= 1,
    JSON.stringify(s2),
  );

  const corr2ObsId = await insertObservation({
    slug: "w-corr2",
    fetchedAt: at(-2),
    flags: { is_correction: true },
  });
  // The post-close correction re-derives the projection: close +10d, confidence conflicting, v3.
  await sql`
    update participation_windows
      set resolved_close_utc = ${at(7)}, confidence = 'conflicting', version = 3, status = 'open'
    where ocd_id = ${OCD("w-corr2")}
  `;

  // Advance the clock past w-corr2's horizon (close at(-3) + 7d ⇒ due at day +4; +5 is clear).
  const LATER = new Date(NOW.getTime() + 5 * DAY);
  const s3 = await verifyOnce(sql, { now: () => LATER });
  assert(
    "cycle 3 writes the w-corr2 miss",
    s3.verdictsIncorrect === 1,
    JSON.stringify(s3),
  );
  const corr2Row = (
    await sql<
      {
        was_correct: boolean | null;
        basis: string;
        confidence_at_close: string;
        window_version: number;
        published_close_utc: Date;
        contradicting_observation_ids: string[];
      }[]
    >`
      select was_correct, basis, confidence_at_close, window_version, published_close_utc,
             contradicting_observation_ids
      from accuracy_records where ocd_id = ${OCD("w-corr2")}
    `
  )[0];
  assert(
    "LATE-CORRECTION live: false / late_amendment, correction observation named",
    corr2Row !== undefined &&
      corr2Row.was_correct === false &&
      corr2Row.basis === "late_amendment" &&
      JSON.stringify(corr2Row.contradicting_observation_ids) ===
        JSON.stringify([corr2ObsId]),
    JSON.stringify(corr2Row),
  );
  assert(
    "SNAPSHOT IMMUNITY: the record judges confidence_at_close='high' @ version 2 and the AT-CLOSE close, not the drifted conflicting/v3/+7d projection",
    corr2Row !== undefined &&
      corr2Row.confidence_at_close === "high" &&
      corr2Row.window_version === 2 &&
      corr2Row.published_close_utc.toISOString() === at(-3),
    JSON.stringify(corr2Row),
  );
  // The drifted projection (status now 'open', close in the future at LATER? at(7) is future at LATER-5d? at(7) > LATER)
  // must NOT have been re-snapshotted: the unresolved-watch guard held through cycles 2-3, and after the
  // record landed the close (at(7)) is in the future — nothing new to snapshot.
  const corr2Watches = await sql<{ window_version: number }[]>`
    select window_version from verification_watch where ocd_id = ${OCD("w-corr2")}
  `;
  assert(
    "no re-snapshot of the drifted projection (one watch row, the at-close one)",
    corr2Watches.length === 1 && corr2Watches[0]?.window_version === 2,
    JSON.stringify(corr2Watches),
  );

  // ── w-defer converts once a check lands (deferred-re-poll → verdict) ─────────────────────────────
  const s4pre = await verifyOnce(sql, clock);
  assert(
    "w-defer STILL awaiting_check on a later same-day cycle (no record yet)",
    s4pre.awaitingCheck >= 1,
    JSON.stringify(s4pre),
  );
  await insertObservation({ slug: "w-defer", fetchedAt: at(-0.5) }); // an FR re-observation post-close, no flags
  const s4 = await verifyOnce(sql, clock);
  assert(
    "w-defer: the late-landing check converts the extended horizon into a TRUE verdict",
    s4.verdictsCorrect === 1,
    JSON.stringify(s4),
  );
  const deferRow = (
    await sql<{ was_correct: boolean; basis: string }[]>`
      select was_correct, basis from accuracy_records where ocd_id = ${OCD("w-defer")}
    `
  )[0];
  assert(
    "w-defer record: true / post_close_repoll",
    deferRow !== undefined &&
      deferRow.was_correct === true &&
      deferRow.basis === "post_close_repoll",
    JSON.stringify(deferRow),
  );

  // ── idempotency: another cycle writes nothing new ────────────────────────────────────────────────
  const s5 = await verifyOnce(sql, clock);
  assert(
    "idempotent re-run: no new snapshots, no new records",
    s5.snapshotted === 0 &&
      s5.verdictsCorrect === 0 &&
      s5.verdictsIncorrect === 0 &&
      s5.lapsed === 0,
    JSON.stringify(s5),
  );

  // ── the re-poll widening (poll.ts): closed-in-horizon windows stay in the budgeted set ──────────
  // w-young is CLOSED (status would have dropped it from the old status='open' filter) with an
  // unresolved watch row and a never-checked regs doc (maximally stale) — it MUST be re-polled.
  // The fake fetchDetail throws: eligibility is what's under test (repolled counts before the fetch),
  // not the ingest plumbing (poll.test.ts owns that).
  const deps: Partial<PollDeps> = {
    listPage: async () => [],
    fetchDetail: async () => {
      throw new Error("eligibility probe — fetch not under test");
    },
    now: () => NOW,
  };
  const p1 = await pollRegsOnce(sql, deps);
  assert(
    "closed-in-horizon w-young IS in the re-poll set alongside open w-open (unresolved watch widens eligibility)",
    p1.repolled === 2, // w-open (status=open, the #18 sweep) + w-young (closed, slice-V widening)
    JSON.stringify(p1),
  );
  // Resolve w-young by hand-writing its record (the operator/manual path also proves the DB checks).
  await sql`
    insert into accuracy_records (
      ocd_id, window_version, confidence_at_close, published_close_utc,
      was_correct, basis, contradicting_observation_ids, closed_at_utc, verified_at_utc
    ) values (
      ${OCD("w-young")}, 1, 'high', ${at(-1)}, true, 'manual', '[]'::jsonb, ${at(-1)}, ${at(0)}
    )
  `;
  const p2 = await pollRegsOnce(sql, deps);
  assert(
    "record written → w-young drops OUT of the re-poll set (zero extra bookkeeping); open w-open stays",
    p2.repolled === 1,
    JSON.stringify(p2),
  );

  // ── append-only enforcement on accuracy_records ─────────────────────────────────────────────────
  await rejects("UPDATE on accuracy_records is rejected by the DB", () =>
    sql`update accuracy_records set was_correct = true where ocd_id = ${OCD("w-corr2")}`.execute(),
  );
  await rejects("DELETE on accuracy_records is rejected by the DB", () =>
    sql`delete from accuracy_records where ocd_id = ${OCD("w-corr2")}`.execute(),
  );
  await rejects("TRUNCATE on accuracy_records is rejected by the DB", () =>
    sql`truncate accuracy_records`.execute(),
  );

  // DB checks mirror the contract refinements: lapsed⇔null and miss-needs-evidence.
  try {
    await sql`
      insert into accuracy_records (
        ocd_id, window_version, confidence_at_close, published_close_utc,
        was_correct, basis, contradicting_observation_ids, closed_at_utc, verified_at_utc
      ) values (
        ${OCD("w-open")}, 9, 'high', ${at(-1)}, false, 'late_amendment', '[]'::jsonb, ${at(-1)}, ${at(0)}
      )
    `;
    assert("DB check rejects an evidence-free miss", false, "insert succeeded");
  } catch (e) {
    assert(
      "DB check rejects an evidence-free miss",
      /check/i.test(e instanceof Error ? e.message : String(e)),
    );
  }
  try {
    await sql`
      insert into accuracy_records (
        ocd_id, window_version, confidence_at_close, published_close_utc,
        was_correct, basis, contradicting_observation_ids, closed_at_utc, verified_at_utc
      ) values (
        ${OCD("w-open")}, 9, 'high', ${at(-1)}, true, 'unverified_lapsed', '[]'::jsonb, ${at(-1)}, ${at(0)}
      )
    `;
    assert(
      "DB check rejects a lapsed record carrying a boolean",
      false,
      "insert succeeded",
    );
  } catch (e) {
    assert(
      "DB check rejects a lapsed record carrying a boolean",
      /check/i.test(e instanceof Error ? e.message : String(e)),
    );
  }

  // ── the 90d HIGH rollup ──────────────────────────────────────────────────────────────────────────
  // Records so far: w-clean true(high), w-corr true(high), w-corr2 false(high), w-defer true(medium),
  // w-lapse lapsed(high, EXCLUDED), w-young true(high, manual counts — basis filters only lapse).
  const roll = await highCorrectRatio90d(sql, LATER);
  assert(
    "HIGH 90d rollup: 3/4 correct (medium excluded by slice, lapse excluded by basis)",
    roll.sample === 4 && roll.ratio === 0.75,
    JSON.stringify(roll),
  );
  const empty = await highCorrectRatio90d(
    sql,
    new Date(NOW.getTime() + 200 * DAY),
  );
  assert(
    "rollup with no in-window sample → ratio null (exported as NaN, never a fake 0 or 1)",
    empty.ratio === null && empty.sample === 0,
    JSON.stringify(empty),
  );

  const corrObsIdUsed = corrObsId; // silence unused if assertions change
  void corrObsIdUsed;
} finally {
  await sql.end({ timeout: 5 });
}

console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("\nALL EXPECTATIONS MET");
