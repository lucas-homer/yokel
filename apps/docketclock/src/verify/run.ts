/**
 * run.ts — verifyOnce: the DB-aware post-close verification pass (slice V, PR-V1), stage 4 of the
 * single-writer poll cycle (after fr → regs → chain). The pure rules live in select.ts (horizon state
 * machine) and verdict.ts (as-of-close judgment); this module only assembles their inputs from the
 * spine and persists the result.
 *
 * Two sub-passes, both idempotent:
 *
 *   1. SNAPSHOT — windows whose published close has passed get an at-close snapshot row in
 *      verification_watch (the regs_poll_watch pattern: operational, mutable, NOT a contract shape).
 *      The projection mutates post-close (a late correction bumps version and flips confidence in
 *      place), so the FINAL record must be written from a snapshot taken the first cycle after close
 *      (±1 poll interval, ~15 min) — otherwise a post-close correction that flips a HIGH window to
 *      CONFLICTING would silently remove that window from the HIGH gauge, hiding exactly the miss the
 *      metric exists to count. Scope: non-null close (an abstaining window never published a claim to
 *      judge); withdrawn windows are scoped by EVIDENCE, not status — withdrawn-before-close never had
 *      an operative close to judge, but a POST-close withdrawal observation is the revealed-withdrawal
 *      miss itself and must be snapshotted (adversary RB-4). RE-SNAPSHOT GUARD: a window with an UNRESOLVED watch row (no final
 *      record yet) is never re-snapshotted — post-close drift belongs to the pending verdict, not a
 *      new snapshot. A window whose watches are all resolved re-snapshots ONLY when its current close
 *      moved LATER than every watched close (the reopened-and-closed-again lifecycle: a genuinely new
 *      period earns a new verdict at its new version).
 *
 *   2. EVALUATE — each unresolved watch row is classified by the pure horizon machine. in_horizon /
 *      awaiting_check rows just keep their sources in the budgeted re-poll set (poll.ts widens its
 *      eligibility to "windows with an unresolved watch row" — the record write below is what drops a
 *      window back out, closing the loop with zero extra bookkeeping). due_verdict / due_lapsed rows
 *      get their FINAL AccuracyRecord: validated through the 0.9.0 contract shape (the refinements —
 *      lapsed⇔null, miss-names-evidence — are enforced at this write boundary, then again by the DB
 *      checks), inserted with `on conflict do nothing` (append-only + idempotent under re-runs).
 *
 * CONFIRMED CHECK (the never-correctness-by-default rule): a successful source fetch STRICTLY after
 * the published close — regs_poll_watch.last_checked_at (it advances even on a dedupe-skip, which is
 * exactly "we checked and nothing changed"), OR any post-close observation landing for the window
 * (an observation IS a successful fetch; FR re-serving a doc counts this way).
 *
 * CONCURRENCY(single-writer): same discipline as the other passes — runs inside the one poller
 * process, never overlapping. DETERMINISTIC: the clock is injected via opts.now (tests drive a fake).
 */
import { AccuracyRecord } from "@yokel/contracts";
import type { Sql } from "../db/client.js";
import { componentLogger } from "../log.js";
import {
  classifyHorizon,
  DEFAULT_HORIZON_POLICY,
  type HorizonPolicy,
} from "./select.js";
import { computeVerdict, type PostCloseObservation } from "./verdict.js";

const log = componentLogger("verify");

export interface VerifySummary {
  snapshotted: number; // windows newly snapshotted into verification_watch this cycle
  inHorizon: number; // unresolved watches inside close+horizon (sources stay in the re-poll set)
  awaitingCheck: number; // past horizon with ZERO confirmed checks — horizon extended, still re-polling
  verdictsCorrect: number; // final records written with was_correct = true
  verdictsIncorrect: number; // final records written with was_correct = false (each a future fixture)
  lapsed: number; // unverified_lapsed records written (the starvation signal)
}

export interface VerifyOptions {
  /** Horizon policy (7d horizon / 14d cap by default). Tests compress these. */
  policy?: HorizonPolicy;
  /** The clock. Defaults to () => new Date(). */
  now?: () => Date;
}

interface WatchRow {
  ocd_id: string;
  window_version: number;
  confidence_at_close: string;
  published_close_utc: Date;
  published_close_display: string | null;
  snapshotted_at: Date;
  current_close: Date | null;
  current_status: string;
  last_checked_at: Date | null;
}

export async function verifyOnce(
  sql: Sql,
  opts?: VerifyOptions,
): Promise<VerifySummary> {
  const policy = opts?.policy ?? DEFAULT_HORIZON_POLICY;
  const now = (opts?.now ?? (() => new Date()))();
  const nowIso = now.toISOString();

  const summary: VerifySummary = {
    snapshotted: 0,
    inHorizon: 0,
    awaitingCheck: 0,
    verdictsCorrect: 0,
    verdictsIncorrect: 0,
    lapsed: 0,
  };

  // ── 1. SNAPSHOT — capture at-close state for newly-closed windows ─────────────────────────────────
  // The NOT EXISTS encodes the re-snapshot guard from the header: any UNRESOLVED watch row blocks
  // (post-close drift belongs to the pending verdict); a RESOLVED watch row blocks unless the current
  // close moved strictly LATER than the close it judged (reopened-and-closed-again ⇒ new verdict).
  const snapshotted = await sql<{ ocd_id: string }[]>`
    insert into verification_watch (
      ocd_id, window_version, confidence_at_close,
      published_close_utc, published_close_display, snapshotted_at
    )
    select w.ocd_id, w.version, w.confidence,
           w.resolved_close_utc, w.resolved_close_display, ${nowIso}
    from participation_windows w
    where w.resolved_close_utc is not null
      and w.resolved_close_utc <= ${nowIso}
      and (
        -- WITHDRAWN scoping is evidence-based, not status-based (adversary RB-4): a window withdrawn
        -- BEFORE close never had an operative close to judge (out of scope) — but a withdrawal we
        -- learn of POST-close is the revealed-withdrawal MISS itself, and reconcile flips status to
        -- 'withdrawn' the moment the withdrawal ingests (stage 2, BEFORE this stage-4 snapshot), so a
        -- bare status filter would suppress exactly the misses the gauge exists to count. Include a
        -- withdrawn-status window iff a post-close withdrawal observation exists for it.
        w.status <> 'withdrawn'
        or exists (
          select 1
          from observations o
          left join observation_targets t on t.observation_id = o.observation_id
          where (o.ocd_id = w.ocd_id or t.ocd_id = w.ocd_id)
            and o.is_withdrawal
            and o.fetched_at > w.resolved_close_utc
        )
      )
      and not exists (
        select 1
        from verification_watch vw
        where vw.ocd_id = w.ocd_id
          and (
            not exists (
              select 1 from accuracy_records ar
              where ar.ocd_id = vw.ocd_id and ar.window_version = vw.window_version
            )
            or vw.published_close_utc >= w.resolved_close_utc
          )
      )
    on conflict (ocd_id, window_version) do nothing
    returning ocd_id
  `;
  summary.snapshotted = snapshotted.length;

  // ── 2. EVALUATE — classify every unresolved watch; write due verdicts ────────────────────────────
  const watches = await sql<WatchRow[]>`
    select vw.ocd_id, vw.window_version, vw.confidence_at_close,
           vw.published_close_utc, vw.published_close_display, vw.snapshotted_at,
           w.resolved_close_utc as current_close, w.status as current_status,
           pw.last_checked_at
    from verification_watch vw
    join participation_windows w on w.ocd_id = vw.ocd_id
    left join regs_poll_watch pw on pw.regs_document_id = w.regs_document_id
    where not exists (
      select 1 from accuracy_records ar
      where ar.ocd_id = vw.ocd_id and ar.window_version = vw.window_version
    )
    order by vw.published_close_utc asc, vw.ocd_id asc
  `;

  for (const watch of watches) {
    // Per-window failure isolation, same discipline as every poll pass: one bad window must never
    // abort the cycle (or the remaining verifications).
    try {
      await evaluateWatch(sql, watch, now, policy, summary);
    } catch (err) {
      log.error(
        { err, ocdId: watch.ocd_id, windowVersion: watch.window_version },
        "verify pass failed for window — skipping (retried next cycle)",
      );
    }
  }

  return summary;
}

async function evaluateWatch(
  sql: Sql,
  watch: WatchRow,
  now: Date,
  policy: HorizonPolicy,
  summary: VerifySummary,
): Promise<void> {
  const publishedCloseIso = watch.published_close_utc.toISOString();

  // Every observation for the window fetched STRICTLY after the published close — via BOTH linkage
  // paths (primary ocd_id + the observation_targets M:N fan-out, so an EPA-2025-02910-style
  // multi-target amendment landing post-close is seen by every window it touches).
  const postClose = await sql<
    Array<{
      observation_id: string;
      fetched_at: Date;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
    }>
  >`
    select distinct o.observation_id, o.fetched_at,
           o.is_extension, o.is_correction, o.is_withdrawal, o.is_reopening
    from observations o
    left join observation_targets t on t.observation_id = o.observation_id
    where (o.ocd_id = ${watch.ocd_id} or t.ocd_id = ${watch.ocd_id})
      and o.fetched_at > ${publishedCloseIso}
  `;

  // CONFIRMED CHECK: the latest post-close source check (see header). Pre-/at-close instants prove
  // nothing and are dropped here; classifyHorizon re-guards defensively.
  const closeMs = watch.published_close_utc.getTime();
  let confirmedCheckAt: string | null = null;
  const candidates: Date[] = [
    ...postClose.map((o) => o.fetched_at),
    ...(watch.last_checked_at ? [watch.last_checked_at] : []),
  ];
  for (const c of candidates) {
    if (c.getTime() > closeMs) {
      if (
        confirmedCheckAt === null ||
        c.getTime() > Date.parse(confirmedCheckAt)
      )
        confirmedCheckAt = c.toISOString();
    }
  }

  // COLD-START / STALE-SNAPSHOT GUARD (adversary spec-gap 4): the snapshot is the verdict's ground
  // truth for "the window as published at close", accurate to ±1 poll interval in normal operation.
  // A snapshot taken AFTER close+cap (first deploy over historical windows; extended poller downtime)
  // has no such guarantee — it captured the CURRENT, possibly amendment-drifted projection, and
  // judging from it biases exactly one way: a late amendment folded into the snapshot makes the
  // published close look correct. So a watch born past the cap is never judged — it abstains as
  // unverified_lapsed (honest, gauge-excluded, visible on the starvation counter). Windows whose
  // snapshot landed INSIDE the cap are judged normally; their drift is bounded by capMs.
  const snapshotBornLapsed =
    watch.snapshotted_at.getTime() > closeMs + policy.capMs;

  const state = snapshotBornLapsed
    ? "due_lapsed"
    : classifyHorizon(
        { publishedCloseUtc: publishedCloseIso, confirmedCheckAt },
        now,
        policy,
      );

  if (state === "not_due") return; // defensive: a snapshot exists only once the close has passed
  if (state === "in_horizon") {
    summary.inHorizon++;
    return;
  }
  if (state === "awaiting_check") {
    summary.awaitingCheck++;
    return;
  }

  // due_verdict | due_lapsed — write the FINAL record.
  const observationsSinceClose: PostCloseObservation[] = postClose.map((o) => ({
    observation_id: o.observation_id,
    fetched_at: o.fetched_at.toISOString(),
    is_extension: o.is_extension,
    is_correction: o.is_correction,
    is_withdrawal: o.is_withdrawal,
    is_reopening: o.is_reopening,
  }));

  const verdict = computeVerdict({
    publishedCloseUtc: publishedCloseIso,
    currentCloseUtc: watch.current_close?.toISOString() ?? null,
    currentStatus: watch.current_status,
    observationsSinceClose,
    lapsed: state === "due_lapsed",
  });

  // Validate the assembled record through the 0.9.0 contract at the write boundary — the refinements
  // (lapsed⇔null, miss-names-evidence, only-a-miss-carries-ids) throw HERE, before the row exists.
  const record = AccuracyRecord.parse({
    ocd_id: watch.ocd_id,
    window_version: watch.window_version,
    confidence_at_close: watch.confidence_at_close,
    published_close_utc: publishedCloseIso,
    published_close_display: watch.published_close_display,
    verdict,
    horizon: {
      closed_at_utc: publishedCloseIso,
      verified_at_utc: now.toISOString(),
    },
  });

  const inserted = await sql<{ ocd_id: string }[]>`
    insert into accuracy_records (
      ocd_id, window_version, confidence_at_close,
      published_close_utc, published_close_display,
      was_correct, basis, contradicting_observation_ids,
      closed_at_utc, verified_at_utc
    ) values (
      ${record.ocd_id}, ${record.window_version}, ${record.confidence_at_close},
      ${record.published_close_utc}, ${record.published_close_display},
      ${record.verdict.was_correct}, ${record.verdict.basis},
      ${sql.json(record.verdict.contradicting_observation_ids)},
      ${record.horizon.closed_at_utc}, ${record.horizon.verified_at_utc}
    )
    on conflict (ocd_id, window_version) do nothing
    returning ocd_id
  `;
  if (inserted.length === 0) return; // raced/re-run: the record already exists — idempotent no-op

  if (record.verdict.basis === "unverified_lapsed") {
    summary.lapsed++;
    log.warn(
      { ocdId: record.ocd_id, windowVersion: record.window_version },
      "verification horizon LAPSED with zero confirmed post-close checks — unverified_lapsed recorded (re-poll starvation signal; EXCLUDED from the headline gauge)",
    );
  } else if (record.verdict.was_correct) {
    summary.verdictsCorrect++;
  } else {
    summary.verdictsIncorrect++;
    log.warn(
      {
        ocdId: record.ocd_id,
        windowVersion: record.window_version,
        contradicting: record.verdict.contradicting_observation_ids,
      },
      "published close judged INCORRECT as of close time — accuracy miss recorded (export a regression fixture: plans/verification-accuracy.md PR-V2)",
    );
  }
}

/**
 * The 90d HIGH rollup behind the headline gauge (docketclock_accuracy_high_correct_ratio_90d):
 * share of HIGH-at-close windows whose FINAL record says was_correct=true, over windows that CLOSED
 * in the trailing 90 days, EXCLUDING unverified_lapsed rows (abstentions are not blended into
 * "correct" — they're counted on the starvation metric instead). Returns null when there is no
 * sample (the caller exports NaN so an absent baseline can never satisfy an alert threshold).
 */
export async function highCorrectRatio90d(
  sql: Sql,
  now: Date = new Date(),
): Promise<{ ratio: number | null; sample: number }> {
  const since = new Date(now.getTime() - 90 * 24 * 3_600_000).toISOString();
  const [row] = await sql<{ correct: string; total: string }[]>`
    select
      count(*) filter (where was_correct) as correct,
      count(*) as total
    from accuracy_records
    where confidence_at_close = 'high'
      and basis <> 'unverified_lapsed'
      and closed_at_utc >= ${since}
  `;
  const total = Number(row?.total ?? 0);
  const correct = Number(row?.correct ?? 0);
  return { ratio: total > 0 ? correct / total : null, sample: total };
}
