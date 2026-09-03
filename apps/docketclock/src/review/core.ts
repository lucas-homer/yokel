/**
 * review/core.ts — the operator review path's DB-aware core (Slice R, PR-R3; plans/review-resolve.md).
 * The CLI (cli.ts) is a thin arg/format wrapper over these three functions so tests drive the real
 * logic without spawning a process.
 *
 * WRITE PATH DISCIPLINE: resolveWindow writes a human_review OBSERVATION through the exact ingest
 * machinery source data uses (ingestObservation → append-only log → reconcileOcdId). There is no
 * UPDATE anywhere — a resolution accretes, and reconcile-v2's supersedence gate decides whether it is
 * honored. The two adversary guards from #116 are enforced here:
 *   • REFUSE an ocd_id with no projection row AND refuse one with no SOURCE observations — a typo'd
 *     ocd-id must never mint a source-less window that a pin would publish at HIGH (adversary S3j).
 *   • reviewed_payload_hashes is filled AT RESOLVE TIME from the latest per-source observations —
 *     "the human has seen everything the machine has" recorded as the actual payload hashes on the
 *     table when the verdict was written, not whatever the operator typed.
 *
 * CONCURRENCY: this runs host-side (or via exec in the poller pod) while the poller cycle may be
 * mid-write. That is a second writer, accepted at operator scale: the observation log is append-only
 * (no mutation to race), the human_review dedupe keys on ocd_id (a key the poller never writes), and
 * participation_windows is a re-derivable projection whose upsert runs in its own transaction — the
 * worst interleaving is a redundant re-derivation next cycle, never corruption. KNOWN NARROW GAP
 * (#117 review): the reviewed-hashes SELECT and the verdict insert are separate statements, so a
 * source observation landing in between (with fetched_at still earlier than the verdict's stamp)
 * would be honored by the time gate yet absent from reviewed_payload_hashes — the audit list would
 * under-claim by one hash. Milliseconds wide, interactive-scale, and the derivation itself stays
 * correct (reconcile re-reads everything fresh); tighten to a single transaction if this path ever
 * becomes non-interactive.
 */
import { createHash } from "node:crypto";
import {
  HumanReviewVerdict,
  type HumanReviewVerdictKind,
} from "@yokel/contracts";
import type { Sql } from "../db/client.js";
import { ingestObservation } from "../ingest/observe.js";
import {
  reconcileOcdId,
  type ReconcileOcdIdResult,
} from "../reconcile/persist.js";
import { extractFr, extractRegs } from "../reconcile/extract.js";

/** One queue row — everything the operator needs to pick what to work next. */
export interface QueueRow {
  ocd_id: string;
  confidence: string;
  conflict_flags: string[];
  status: string;
  resolved_close_utc: string | null;
  resolved_close_display: string | null;
  derived_at: string;
}

/**
 * The v1 queue (locked decision): windows whose confidence already DEMANDS a human — conflicting or
 * stale — ordered closing-soonest (null closes last: nothing to miss, but still wrong). Chain-ambiguous
 * pairs and dead-letter triage are explicit follow-ups, not v1 members.
 */
export async function reviewQueue(sql: Sql): Promise<QueueRow[]> {
  const rows = await sql<
    {
      ocd_id: string;
      confidence: string;
      conflict_flags: string[];
      status: string;
      resolved_close_utc: Date | null;
      resolved_close_display: string | null;
      derived_at: Date;
    }[]
  >`
    select ocd_id, confidence, conflict_flags, status,
           resolved_close_utc, resolved_close_display, derived_at
    from participation_windows
    where confidence in ('conflicting', 'stale')
    order by resolved_close_utc asc nulls last, ocd_id asc
  `;
  return rows.map((r) => ({
    ...r,
    resolved_close_utc: r.resolved_close_utc?.toISOString() ?? null,
    derived_at: r.derived_at.toISOString(),
  }));
}

/** Per-cycle queue observability (PR-R4) — the numbers the gauge + rot alert are built from. */
export interface QueueStats {
  /** windows per queue reason (confidence tier). Both keys always present so gauges never go stale. */
  byReason: { conflicting: number; stale: number };
  /**
   * Age (seconds) of the oldest LIVE cross_source conflict — the queue's rot signal. detected_at is
   * the FIRST-detection stamp, preserved across re-derivations (persist.ts), so a re-deriving window
   * can never launder its age. null when no live conflict exists. NOTE: anchored on conflicts, which
   * every conflicting-confidence window carries by engine invariant; if something starts emitting
   * confidence=stale (reserved, nothing does today), those items age invisibly until this learns a
   * second anchor — extend then, not speculatively.
   */
  oldestAgeSeconds: number | null;
}

/**
 * Compute queue depth + rot age. Runs in the poll cycle tail; cheap — the depth aggregate rides
 * participation_windows_confidence_idx (0003), the rot aggregate rides the partial
 * conflict_records_live_detected_idx (0012), whose predicate matches this query exactly.
 */
export async function reviewQueueStats(
  sql: Sql,
  now: Date = new Date(),
): Promise<QueueStats> {
  const depths = await sql<{ confidence: string; n: string }[]>`
    select confidence, count(*) as n from participation_windows
    where confidence in ('conflicting', 'stale')
    group by confidence
  `;
  const byReason = { conflicting: 0, stale: 0 };
  for (const d of depths) {
    if (d.confidence === "conflicting") byReason.conflicting = Number(d.n);
    if (d.confidence === "stale") byReason.stale = Number(d.n);
  }
  const [oldest] = await sql<{ min: Date | null }[]>`
    select min(detected_at) as min from conflict_records
    where resolved_at is null and conflict_scope = 'cross_source'
  `;
  const oldestAgeSeconds = oldest?.min
    ? Math.max(0, (now.getTime() - oldest.min.getTime()) / 1000)
    : null;
  return { byReason, oldestAgeSeconds };
}

/** Per-source summary for `review show` — the values a reviewer actually compares. */
export interface SourceSummary {
  source: string;
  observation_id: string;
  fetched_at: string;
  payload_hash: string;
  /** FR comments_close_on / Regs commentEndDate — the raw close each source asserts. */
  close_value: string | null;
  withdrawn: boolean | null;
  open_for_comment: boolean | null;
  is_withdrawal: boolean;
  is_extension: boolean;
  is_reopening: boolean;
}

export interface PriorVerdict {
  observation_id: string;
  fetched_at: string;
  verdict: HumanReviewVerdict | { unparseable: true };
}

export interface ShowResult {
  window: Record<string, unknown> | null;
  sources: SourceSummary[];
  priorVerdicts: PriorVerdict[];
  liveConflicts: number;
  retiredConflicts: number;
  chainLinks: {
    ocd_id: string;
    ocd_id_b: string;
    resolved_at: string | null;
  }[];
}

/** Everything a reviewer needs in one screen: the window, latest-per-source, verdicts, conflicts. */
export async function reviewShow(sql: Sql, ocdId: string): Promise<ShowResult> {
  const [window] = await sql<Record<string, unknown>[]>`
    select * from participation_windows where ocd_id = ${ocdId}
  `;
  const latest = await sql<
    {
      source: string;
      observation_id: string;
      fetched_at: Date;
      payload_hash: string;
      raw: unknown;
      is_withdrawal: boolean;
      is_extension: boolean;
      is_reopening: boolean;
    }[]
  >`
    select distinct on (source)
      source, observation_id, fetched_at, payload_hash, raw,
      is_withdrawal, is_extension, is_reopening
    from observations
    where ocd_id = ${ocdId}
    order by source, fetched_at desc, observation_id desc
  `;

  const sources: SourceSummary[] = [];
  const priorVerdicts: PriorVerdict[] = [];
  for (const o of latest) {
    if (o.source === "human_review") continue; // verdicts listed separately, ALL of them, below
    let close: string | null = null;
    let withdrawn: boolean | null = null;
    let open: boolean | null = null;
    if (o.source === "federal_register") {
      close = extractFr(o.raw).commentsCloseOn;
    } else if (o.source === "regulations_gov") {
      const f = extractRegs(o.raw);
      close = f.commentEndDate;
      withdrawn = f.withdrawn ?? null;
      open = f.openForComment ?? null;
    }
    sources.push({
      source: o.source,
      observation_id: o.observation_id,
      fetched_at: o.fetched_at.toISOString(),
      payload_hash: o.payload_hash,
      close_value: close,
      withdrawn,
      open_for_comment: open,
      is_withdrawal: o.is_withdrawal,
      is_extension: o.is_extension,
      is_reopening: o.is_reopening,
    });
  }

  const verdictRows = await sql<
    { observation_id: string; fetched_at: Date; raw: unknown }[]
  >`
    select observation_id, fetched_at, raw from observations
    where ocd_id = ${ocdId} and source = 'human_review'
    order by fetched_at desc, observation_id desc
  `;
  for (const v of verdictRows) {
    const parsed = HumanReviewVerdict.safeParse(v.raw);
    priorVerdicts.push({
      observation_id: v.observation_id,
      fetched_at: v.fetched_at.toISOString(),
      verdict: parsed.success ? parsed.data : { unparseable: true },
    });
  }

  const [conflictCounts] = await sql<{ live: string; retired: string }[]>`
    select count(*) filter (where resolved_at is null) as live,
           count(*) filter (where resolved_at is not null) as retired
    from conflict_records
    where ocd_id = ${ocdId} and conflict_scope = 'cross_source'
  `;
  const chainLinks = await sql<
    { ocd_id: string; ocd_id_b: string; resolved_at: Date | null }[]
  >`
    select ocd_id, ocd_id_b, resolved_at from conflict_records
    where conflict_scope = 'cross_window' and (ocd_id = ${ocdId} or ocd_id_b = ${ocdId})
  `;

  return {
    window: window ?? null,
    sources,
    priorVerdicts,
    liveConflicts: Number(conflictCounts?.live ?? 0),
    retiredConflicts: Number(conflictCounts?.retired ?? 0),
    chainLinks: chainLinks.map((c) => ({
      ...c,
      resolved_at: c.resolved_at?.toISOString() ?? null,
    })),
  };
}

export interface ResolveInput {
  ocdId: string;
  kind: HumanReviewVerdictKind;
  /** ISO calendar date (YYYY-MM-DD). Required for pin_close, forbidden otherwise (contract-enforced). */
  close?: string;
  note: string;
  operator: string;
}

export interface ResolveOutcome {
  inserted: boolean;
  reviewedHashes: string[];
  result: ReconcileOcdIdResult;
}

/**
 * Write a verdict through the sanctioned path and return the re-derived window as confirmation.
 * Throws (writes NOTHING) when: the ocd_id has no projection row; it has no source observations
 * (adversary S3j — a pin on a source-less window would publish HIGH with zero evidence); or the
 * verdict fields fail the HumanReviewVerdict contract (pin⇔date, non-empty note, …).
 */
export async function resolveWindow(
  sql: Sql,
  input: ResolveInput,
  now: Date = new Date(),
): Promise<ResolveOutcome> {
  const [win] = await sql<{ ocd_id: string }[]>`
    select ocd_id from participation_windows where ocd_id = ${input.ocdId}
  `;
  if (!win)
    throw new Error(
      `review resolve: no participation_window for "${input.ocdId}" — refusing to mint a window from a verdict (check the ocd-id for typos)`,
    );

  // Latest per SOURCE observation — the evidence set the verdict is recorded against. Empty = refuse.
  const latestSources = await sql<{ source: string; payload_hash: string }[]>`
    select distinct on (source) source, payload_hash
    from observations
    where ocd_id = ${input.ocdId} and source <> 'human_review'
    order by source, fetched_at desc, observation_id desc
  `;
  if (latestSources.length === 0)
    throw new Error(
      `review resolve: "${input.ocdId}" has no source observations — a verdict here would assert evidence that does not exist (adversary S3j guard)`,
    );
  const reviewedHashes = latestSources.map((s) => s.payload_hash);

  // Contract-validate BEFORE touching the log (pin⇔date, note non-empty after trim, operator, hashes).
  const verdict = HumanReviewVerdict.parse({
    kind: input.kind,
    ...(input.close !== undefined ? { pinned_close_date: input.close } : {}),
    note: input.note,
    operator: input.operator,
    reviewed_payload_hashes: reviewedHashes,
  });

  const raw = { ...verdict };
  const ingest = await ingestObservation(sql, {
    ocd_id: input.ocdId,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: createHash("sha256")
      .update(JSON.stringify(raw))
      .digest("hex"),
    fetched_at: now.toISOString(),
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
  });

  const result = await reconcileOcdId(sql, input.ocdId, now);
  return { inserted: ingest.inserted, reviewedHashes, result };
}
