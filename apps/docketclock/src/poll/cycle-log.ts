/**
 * cycle-log.ts — the durable per-cycle record (migrations/0014_poll_cycles.sql).
 *
 * Traces expire from Grafana Cloud after 14 days; this row is what stays for long-term trends (cycle
 * duration, pass failure rate, documents per pass). run.ts builds one `PollCycleRecord` per cycle and
 * writes it after the cycle has released its lock. A failed write is the caller's to log: it must never
 * fail the cycle it describes.
 */
import type { Sql } from "../db/client.js";

export type PollCycleOutcome = "ok" | "pass_failed" | "skipped" | "failed";

export interface PassRecord {
  name: string;
  ok: boolean;
  ms: number;
  /** The pass summary's top-level numbers and booleans (the same fields its span carries). */
  summary: Record<string, number | boolean>;
  /** The failure message (first 300 chars) when `ok` is false. */
  error?: string;
}

export interface PollCycleRecord {
  startedAt: Date;
  finishedAt: Date;
  outcome: PollCycleOutcome;
  runOnce: boolean;
  traceId: string | null;
  passes: PassRecord[];
}

/** Keep only a summary's top-level numbers and booleans: small, stable, and what trends are made of. */
export function scalarSummary(
  summary: unknown,
): Record<string, number | boolean> {
  const out: Record<string, number | boolean> = {};
  if (!summary || typeof summary !== "object") return out;
  for (const [k, v] of Object.entries(summary as Record<string, unknown>)) {
    if ((typeof v === "number" && Number.isFinite(v)) || typeof v === "boolean")
      out[k] = v;
  }
  return out;
}

/** The cycle's outcome from what happened: skipped and failed win, then any failed pass. */
export function cycleOutcome(opts: {
  failed: boolean;
  skipped: boolean;
  passes: readonly PassRecord[];
}): PollCycleOutcome {
  if (opts.failed) return "failed";
  if (opts.skipped) return "skipped";
  return opts.passes.every((p) => p.ok) ? "ok" : "pass_failed";
}

export async function recordPollCycle(
  sql: Sql,
  r: PollCycleRecord,
): Promise<void> {
  const durationMs = Math.max(
    0,
    Math.round(r.finishedAt.getTime() - r.startedAt.getTime()),
  );
  await sql`
    insert into poll_cycles (started_at, finished_at, duration_ms, outcome, run_once, trace_id, passes)
    values (${r.startedAt}, ${r.finishedAt}, ${durationMs}, ${r.outcome}, ${r.runOnce}, ${r.traceId},
            ${sql.json(r.passes as never)})
  `;
}
