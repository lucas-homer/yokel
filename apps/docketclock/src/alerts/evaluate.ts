/**
 * alerts/evaluate.ts — the cloud alert rules as one PURE function over what a poll cycle saw.
 *
 * run.ts gathers the signals (the cycle's pass records, a one-query look back at the last hour of
 * poll_cycles, the accuracy and queue numbers the verify and queue_stats passes already read, and an hourly
 * GET of the API's /readyz) and alerts/report.ts sends what this returns. No I/O here, so every rule is
 * unit-tested (test/alerts-evaluate.test.ts).
 *
 * A check whose input is missing this cycle (its pass failed, or the cycle never ran) gets NO ping rather
 * than a guess: its long timeout keeps it quiet, and the failure itself pages through `passes` or `poller`.
 */
import type { PassRecord, PollCycleOutcome } from "../poll/cycle-log.js";
import { RULES, type CheckKey } from "./checks.js";

export type PingKind = "success" | "fail" | "log";

export interface Ping {
  check: CheckKey;
  kind: PingKind;
  /** Plain text, shown in the healthchecks.io event log and in the page. */
  body: string;
}

export interface PassFailureCount {
  name: string;
  /** Cycles in the look-back window in which this pass failed (the current cycle included). */
  failures: number;
  lastError: string | null;
}

export interface CycleSignals {
  now: Date;
  outcome: PollCycleOutcome;
  passes: readonly PassRecord[];
  /** Per-pass failure counts over the last hour; null when the look-back query could not run. */
  recentPassFailures: readonly PassFailureCount[] | null;
  /** From the verify pass; null when it did not run or failed. */
  accuracy: { ratio: number | null; sample: number } | null;
  /** From the queue_stats pass; null when it did not run or failed. */
  queue: { escalated: number; oldestAgeSeconds: number | null } | null;
  /** The API readiness probe; null when it was not due this cycle. */
  api: { ok: boolean; detail: string } | null;
}

export interface Evaluation {
  pings: Ping[];
}

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
const days = (s: number) => `${(s / 86_400).toFixed(1)}d`;

/** True for the one 15-minute cron slot of the day the hourly/daily jobs run in. */
export function isTopOfHour(now: Date): boolean {
  return now.getUTCMinutes() < 15;
}

export function evaluate(s: CycleSignals): Evaluation {
  const pings: Ping[] = [];
  const passOk = (name: string) =>
    s.passes.find((p) => p.name === name)?.ok === true;

  // poller — the dead-man. A skipped cycle (another process holds the lock) still proves the scheduler
  // and the database are up.
  if (s.outcome === "failed") {
    pings.push({
      check: "poller",
      kind: "fail",
      body: "poll cycle failed before its passes ran (lock or database lost)",
    });
  } else {
    const failed = s.passes.filter((p) => !p.ok).map((p) => p.name);
    pings.push({
      check: "poller",
      kind: "success",
      body:
        s.outcome === "skipped"
          ? "cycle skipped: another process holds the poll-cycle lock"
          : `cycle ${s.outcome}${failed.length ? ` (failed: ${failed.join(", ")})` : ""}`,
    });
  }
  if (s.outcome === "failed" || s.outcome === "skipped") {
    // Nothing else was measured. The API probe does not need the database, so it still reports.
    if (s.api) pings.push(apiPing(s.api));
    return { pings };
  }

  // passes — the same pass failed in N+ cycles of the last hour.
  if (s.recentPassFailures) {
    const bad = s.recentPassFailures.filter(
      (f) => f.failures >= RULES.passFailuresPerHour,
    );
    pings.push(
      bad.length
        ? {
            check: "passes",
            kind: "fail",
            body: bad
              .map(
                (f) =>
                  `${f.name} failed in ${f.failures} cycles in the last hour: ${f.lastError ?? "?"}`,
              )
              .join("\n"),
          }
        : {
            check: "passes",
            kind: "success",
            body: "no pass failing repeatedly",
          },
    );
  }

  // llm — fresh AI Gateway calls that failed in this cycle's chain pass.
  const chain = s.passes.find((p) => p.name === "chain");
  if (chain?.ok) {
    const errors = Number(chain.summary.llmErrors ?? 0);
    const calls = Number(chain.summary.llmCalls ?? 0);
    pings.push({
      check: "llm",
      kind: errors > RULES.llmErrorsPerCycle ? "fail" : "success",
      body: `${errors} of ${calls} LLM calls failed this cycle`,
    });
  }

  // accuracy — HIGH-confidence deadlines correct over 90 days.
  if (s.accuracy && passOk("verify")) {
    const { ratio, sample } = s.accuracy;
    if (ratio === null || sample < RULES.accuracyMinSample) {
      pings.push({
        check: "accuracy",
        kind: "success",
        body: `sample ${sample} < ${RULES.accuracyMinSample}: not judged yet`,
      });
    } else {
      pings.push({
        check: "accuracy",
        kind: ratio < RULES.accuracyBar ? "fail" : "success",
        body: `HIGH correct ${pct(ratio)} over 90d (n=${sample}, bar ${pct(RULES.accuracyBar)})`,
      });
    }
  }

  if (s.api) pings.push(apiPing(s.api));
  if (s.queue && passOk("queue_stats")) pings.push(reviewPing(s.queue));

  return { pings };
}

function apiPing(api: { ok: boolean; detail: string }): Ping {
  return {
    check: "api",
    kind: api.ok ? "success" : "fail",
    body: api.detail,
  };
}

/**
 * The review queue (Mini: "Escalations pending", "Review queue rot"). Pinged every cycle; healthchecks.io
 * notifies only when the state flips, so this pages once when work starts waiting and once when it clears.
 */
function reviewPing(queue: NonNullable<CycleSignals["queue"]>): Ping {
  const lines: string[] = [];
  if (queue.escalated > 0) {
    lines.push(
      `${queue.escalated} escalated window(s) are parked waiting on a human.`,
    );
  }
  if (
    queue.oldestAgeSeconds !== null &&
    queue.oldestAgeSeconds > RULES.reviewRotSeconds
  ) {
    lines.push(
      `The oldest open conflict has waited ${days(queue.oldestAgeSeconds)} (over ${days(RULES.reviewRotSeconds)}).`,
    );
  }
  return lines.length
    ? { check: "review", kind: "fail", body: lines.join("\n") }
    : { check: "review", kind: "success", body: "review queue clear" };
}
