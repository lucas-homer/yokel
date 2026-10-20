/**
 * review/core.ts — the operator review path's DB-aware core (Slice R, PR-R3; plans/review-resolve.md;
 * extended by the review autopilot's PR-A2, plans/review-autopilot.md + ADR 0015).
 * The CLI (cli.ts) is a thin arg/format wrapper over these functions so tests drive the real logic
 * without spawning a process.
 *
 * WRITE PATH DISCIPLINE: resolveWindow writes a human_review OBSERVATION through the exact ingest
 * machinery source data uses (ingestObservationWithin → append-only log → reconcileOcdId). There is
 * no UPDATE anywhere — a resolution accretes, and reconcile-v2's supersedence gate decides whether it
 * is honored. The two adversary guards from #116 are enforced here:
 *   • REFUSE an ocd_id with no projection row AND refuse one with no SOURCE observations — a typo'd
 *     ocd-id must never mint a source-less window that a pin would publish at HIGH (adversary S3j).
 *   • reviewed_payload_hashes is filled AT RESOLVE TIME from the latest per-source observations —
 *     "the reviewer has seen everything the machine has" recorded as the actual payload hashes on the
 *     table when the verdict was written, not whatever the operator typed.
 *
 * EVIDENCE BINDING (PR-A2): `expect` is the set of latest-per-source payload hashes the investigation
 * (and its independent verifier) actually assessed. The write runs in ONE transaction: read the live
 * hashes → refuse if they differ from `expect` → insert → re-read the live hashes → refuse (rolling
 * the insert back) if they moved. Automation never writes without `expect`; a human may omit it and
 * gets the pre-A2 behaviour (bind to whatever is live now).
 *
 * CONCURRENCY: this runs host-side (or via exec in the poller pod) while the poller cycle may be
 * mid-write. That is a second writer, accepted at operator scale: the observation log is append-only
 * (no mutation to race), the human_review dedupe keys on ocd_id (a key the poller never writes), and
 * participation_windows is a re-derivable projection whose upsert runs in its own transaction — the
 * worst interleaving is a redundant re-derivation next cycle, never corruption. The pre-A2 "known
 * narrow gap" (#117 — a source observation landing between the hash read and the verdict insert)
 * is closed by the post-insert re-read above down to the instant between that re-read and COMMIT.
 * What remains is the time gate's own semantics: a source observation whose fetched_at predates
 * the verdict's stamp but that is inserted after it is "older" to the reconciler and not in the
 * reviewed hashes — seconds wide at the poller's fetch-to-insert latency, and the derivation itself
 * stays correct (reconcile re-reads everything fresh).
 */
import { createHash } from "node:crypto";
import {
  HumanReviewVerdict,
  type HumanReviewVerdictKind,
  type HumanReviewVerdictReviewer,
  type Observation,
} from "@yokel/contracts";
import type { Sql, SqlHandle } from "../db/client.js";
import { ingestObservationWithin } from "../ingest/observe.js";
import {
  loadObservations,
  reconcileOcdId,
  type ReconcileOcdIdResult,
} from "../reconcile/persist.js";
import {
  reconcile,
  selectHonoredVerdict,
  type HonoredVerdict,
} from "../reconcile/reconcile.js";
import { extractFr, extractRegs } from "../reconcile/extract.js";

/** A parked item: the window's latest verdict is an HONORED `escalate` (PR-A2, ADR 0015). */
export interface EscalationMark {
  observation_id: string;
  operator: string;
  reviewer: HumanReviewVerdictReviewer;
  fetched_at: string;
  note: string;
}

/** One queue row — everything the operator needs to pick what to work next. */
export interface QueueRow {
  ocd_id: string;
  confidence: string;
  conflict_flags: string[];
  status: string;
  resolved_close_utc: string | null;
  resolved_close_display: string | null;
  derived_at: string;
  /**
   * Non-null when the item is PARKED: its latest verdict is an honored `escalate`. The window still
   * derives conflicting/stale (an escalation asserts nothing), so it stays in the queue — the mark is
   * what tells the autopilot to skip it and the operator that a decision is owed, not a re-review.
   */
  escalated: EscalationMark | null;
}

function markOf(h: HonoredVerdict): EscalationMark {
  return {
    observation_id: h.observation.observation_id,
    operator: h.verdict.operator,
    reviewer: h.verdict.reviewer,
    fetched_at: h.observation.fetched_at,
    note: h.verdict.note,
  };
}

/**
 * escalationMarks — which of these windows are parked by an HONORED `escalate`. SQL narrows to the
 * windows whose LATEST human_review row says escalate (the only ones that can be parked), then the
 * honoring decision is the ENGINE's over the full chain (selectHonoredVerdict) — never a SQL
 * approximation of the freshness rule, so `queue`, the gauge and the reconciler can never disagree
 * about what "parked" means. A handful of chain reads at most; the candidates are rare by design.
 */
async function escalationMarks(
  sql: Sql,
  ocdIds: string[],
): Promise<Map<string, EscalationMark>> {
  const marks = new Map<string, EscalationMark>();
  if (ocdIds.length === 0) return marks;
  const candidates = await sql<{ ocd_id: string; kind: string | null }[]>`
    select distinct on (ocd_id) ocd_id, raw->>'kind' as kind
    from observations
    where source = 'human_review' and ocd_id = any(${ocdIds}::text[])
    order by ocd_id, fetched_at desc, observation_id desc
  `;
  for (const c of candidates) {
    if (c.kind !== "escalate") continue;
    const honored = selectHonoredVerdict(await loadObservations(sql, c.ocd_id));
    if (honored && honored.verdict.kind === "escalate")
      marks.set(c.ocd_id, markOf(honored));
  }
  return marks;
}

/**
 * The v1 queue (locked decision): windows whose confidence already DEMANDS a human — conflicting or
 * stale — ordered closing-soonest (null closes last: nothing to miss, but still wrong). Chain-ambiguous
 * pairs and dead-letter triage are explicit follow-ups, not v1 members. Parked (escalated) items are
 * listed WITH their mark, never hidden: suppression is never silence.
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
  const marks = await escalationMarks(
    sql,
    rows.map((r) => r.ocd_id),
  );
  return rows.map((r) => ({
    ...r,
    resolved_close_utc: r.resolved_close_utc?.toISOString() ?? null,
    derived_at: r.derived_at.toISOString(),
    escalated: marks.get(r.ocd_id) ?? null,
  }));
}

/** Per-cycle queue observability (PR-R4) — the numbers the gauge + rot alert are built from. */
export interface QueueStats {
  /**
   * Windows per queue reason. conflicting | stale partition the queue (confidence tiers);
   * escalated (PR-A2) is the PARKED SUBSET of the queue — windows whose latest honored verdict is
   * `escalate` — and OVERLAPS the other two (a parked window still derives conflicting). All keys
   * always present so gauges never go stale.
   */
  byReason: { conflicting: number; stale: number; escalated: number };
  /**
   * Age (seconds) of the oldest LIVE cross_source conflict — the queue's rot signal. detected_at is
   * the FIRST-detection stamp, preserved across re-derivations (persist.ts), so a re-deriving window
   * can never launder its age. null when no live conflict exists. NOTE: anchored on conflicts, which
   * every conflicting-confidence window carries by engine invariant; if something starts emitting
   * confidence=stale (reserved, nothing does today), those items age invisibly until this learns a
   * second anchor — extend then, not speculatively. Parked items keep ageing here BY DESIGN: the rot
   * alert is the standing reminder that a human owes a decision; the escalated gauge is the page.
   */
  oldestAgeSeconds: number | null;
}

/**
 * Compute queue depth + rot age. Runs in the poll cycle tail; cheap — the depth aggregate rides
 * participation_windows_confidence_idx (0003), the rot aggregate rides the partial
 * conflict_records_live_detected_idx (0012), whose predicate matches this query exactly; the
 * escalated count reads a few chains at most (see escalationMarks).
 */
export async function reviewQueueStats(
  sql: Sql,
  now: Date = new Date(),
): Promise<QueueStats> {
  const members = await sql<{ ocd_id: string; confidence: string }[]>`
    select ocd_id, confidence from participation_windows
    where confidence in ('conflicting', 'stale')
  `;
  const byReason = { conflicting: 0, stale: 0, escalated: 0 };
  for (const m of members) {
    if (m.confidence === "conflicting") byReason.conflicting++;
    if (m.confidence === "stale") byReason.stale++;
  }
  byReason.escalated = (
    await escalationMarks(
      sql,
      members.map((m) => m.ocd_id),
    )
  ).size;
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

/** The latest verdict IF the engine honors it (selectHonoredVerdict) — what `show` reports as such. */
export interface HonoredSummary {
  observation_id: string;
  kind: HumanReviewVerdictKind;
  reviewer: HumanReviewVerdictReviewer;
  operator: string;
  fetched_at: string;
  /** kind === "escalate": honored for freshness only — the item is PARKED, nothing is derived. */
  parked: boolean;
}

export interface ShowResult {
  window: Record<string, unknown> | null;
  sources: SourceSummary[];
  priorVerdicts: PriorVerdict[];
  /** null when no verdict exists or the latest one is superseded by evidence. Always null when blind. */
  honored: HonoredSummary | null;
  liveConflicts: number;
  retiredConflicts: number;
  chainLinks: {
    ocd_id: string;
    ocd_id_b: string;
    resolved_at: string | null;
  }[];
  /**
   * BLIND (PR-A2, the shadow-gate harness): prior verdicts are hidden and `window` is the machine's
   * OWN derivation of the source chain (human_review rows excluded, computed in memory, nothing
   * persisted), so an agent being measured cannot read the answer off the projection. liveConflicts
   * is then whether that derivation conflicts; retiredConflicts is 0 (the retirement history would
   * leak that a verdict exists).
   */
  blind: boolean;
}

export interface ShowOptions {
  blind?: boolean;
  /** Clock for the blind derivation's status/stamps; defaults to now. */
  now?: Date;
}

/** Everything a reviewer needs in one screen: the window, latest-per-source, verdicts, conflicts. */
export async function reviewShow(
  sql: Sql,
  ocdId: string,
  opts: ShowOptions = {},
): Promise<ShowResult> {
  const blind = opts.blind === true;
  const [stored] = await sql<Record<string, unknown>[]>`
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

  const chainLinks = await sql<
    { ocd_id: string; ocd_id_b: string; resolved_at: Date | null }[]
  >`
    select ocd_id, ocd_id_b, resolved_at from conflict_records
    where conflict_scope = 'cross_window' and (ocd_id = ${ocdId} or ocd_id_b = ${ocdId})
  `;
  const links = chainLinks.map((c) => ({
    ...c,
    resolved_at: c.resolved_at?.toISOString() ?? null,
  }));

  if (blind) {
    // The machine's own view: re-derive from the source chain alone, in memory. Nothing persisted,
    // no verdict visible, no verdict-derived state (flags, retired conflicts) leaked.
    const chain = (await loadObservations(sql, ocdId)).filter(
      (o) => o.source !== "human_review",
    );
    if (chain.length === 0)
      return {
        window: null,
        sources,
        priorVerdicts: [],
        honored: null,
        liveConflicts: 0,
        retiredConflicts: 0,
        chainLinks: links,
        blind: true,
      };
    const derived = reconcile(chain, opts.now ?? new Date());
    return {
      window: stored ? { ...derived.window } : null,
      sources,
      priorVerdicts: [],
      honored: null,
      liveConflicts: derived.conflict ? 1 : 0,
      retiredConflicts: 0,
      chainLinks: links,
      blind: true,
    };
  }

  const verdictRows = await sql<
    { observation_id: string; fetched_at: Date; raw: unknown }[]
  >`
    select observation_id, fetched_at, raw from observations
    where ocd_id = ${ocdId} and source = 'human_review'
    order by fetched_at desc, observation_id desc
  `;
  const priorVerdicts: PriorVerdict[] = [];
  for (const v of verdictRows) {
    const parsed = HumanReviewVerdict.safeParse(v.raw);
    priorVerdicts.push({
      observation_id: v.observation_id,
      fetched_at: v.fetched_at.toISOString(),
      verdict: parsed.success ? parsed.data : { unparseable: true },
    });
  }
  let honored: HonoredSummary | null = null;
  if (verdictRows.length > 0) {
    const h = selectHonoredVerdict(await loadObservations(sql, ocdId));
    if (h)
      honored = {
        observation_id: h.observation.observation_id,
        kind: h.verdict.kind,
        reviewer: h.verdict.reviewer,
        operator: h.verdict.operator,
        fetched_at: h.observation.fetched_at,
        parked: h.verdict.kind === "escalate",
      };
  }

  const [conflictCounts] = await sql<{ live: string; retired: string }[]>`
    select count(*) filter (where resolved_at is null) as live,
           count(*) filter (where resolved_at is not null) as retired
    from conflict_records
    where ocd_id = ${ocdId} and conflict_scope = 'cross_source'
  `;

  return {
    window: stored ?? null,
    sources,
    priorVerdicts,
    honored,
    liveConflicts: Number(conflictCounts?.live ?? 0),
    retiredConflicts: Number(conflictCounts?.retired ?? 0),
    chainLinks: links,
    blind: false,
  };
}

export interface ResolveInput {
  ocdId: string;
  kind: HumanReviewVerdictKind;
  /** ISO calendar date (YYYY-MM-DD). Required for pin_close, forbidden otherwise (contract-enforced). */
  close?: string;
  note: string;
  /** Who executes the write (the audit field; REVIEW_OPERATOR / --operator). */
  operator: string;
  /** Who DECIDED (ADR 0015). Defaults to "human"; an unsupervised autopilot passes "agent". */
  reviewer?: HumanReviewVerdictReviewer;
  /**
   * The latest-per-source payload hashes the investigation assessed. When present the write REFUSES
   * (writing nothing) unless the live set equals it exactly, before AND after the insert, in one
   * transaction. Automation must always pass it; it is what binds a verdict to assessed evidence.
   */
  expect?: string[];
}

export interface ResolveOutcome {
  inserted: boolean;
  /** The observation_id of the row written; null when an identical verdict was already latest. */
  observationId: string | null;
  reviewedHashes: string[];
  result: ReconcileOcdIdResult;
  /**
   * Whether the engine HONORS this verdict after the write (selectHonoredVerdict over the fresh
   * chain) — keyed on the rule itself, not on a window flag: an honored `escalate` leaves no flag.
   */
  honored: boolean;
}

/** Order-insensitive exact equality of two hash sets. */
function sameHashSet(a: readonly string[], b: readonly string[]): boolean {
  const sa = new Set(a);
  const sb = new Set(b);
  if (sa.size !== sb.size) return false;
  for (const x of sa) if (!sb.has(x)) return false;
  return true;
}

/** The latest observation per SOURCE (human_review excluded) — the evidence set a verdict binds to. */
async function latestSourceHashes(
  sql: SqlHandle,
  ocdId: string,
): Promise<{ source: string; payload_hash: string }[]> {
  return sql<{ source: string; payload_hash: string }[]>`
    select distinct on (source) source, payload_hash
    from observations
    where ocd_id = ${ocdId} and source <> 'human_review'
    order by source, fetched_at desc, observation_id desc
  `;
}

/**
 * Write a verdict through the sanctioned path and return the re-derived window as confirmation.
 * Throws (writes NOTHING) when: the ocd_id has no projection row; it has no source observations
 * (adversary S3j — a pin on a source-less window would publish HIGH with zero evidence); the
 * verdict fields fail the HumanReviewVerdict contract (pin⇔date, non-empty note, …); or `expect`
 * is given and the live evidence set differs from it — before the insert, or (rolling the insert
 * back) after it.
 */
export async function resolveWindow(
  sql: Sql,
  input: ResolveInput,
  now: Date = new Date(),
): Promise<ResolveOutcome> {
  const written = await sql.begin(async (tx) => {
    const [win] = await tx<{ ocd_id: string }[]>`
      select ocd_id from participation_windows where ocd_id = ${input.ocdId}
    `;
    if (!win)
      throw new Error(
        `review resolve: no participation_window for "${input.ocdId}" — refusing to mint a window from a verdict (check the ocd-id for typos)`,
      );

    // Latest per SOURCE observation — the evidence set the verdict is recorded against. Empty = refuse.
    const latestSources = await latestSourceHashes(tx, input.ocdId);
    if (latestSources.length === 0)
      throw new Error(
        `review resolve: "${input.ocdId}" has no source observations — a verdict here would assert evidence that does not exist (adversary S3j guard)`,
      );
    const reviewedHashes = latestSources.map((s) => s.payload_hash);

    // EVIDENCE BINDING: the live set must be exactly what was assessed. Refuse BEFORE touching the log.
    if (input.expect !== undefined) {
      const expected = Array.from(new Set(input.expect));
      if (!sameHashSet(expected, reviewedHashes)) {
        const live = new Set(reviewedHashes);
        const exp = new Set(expected);
        const short = (h: string) => h.slice(0, 12);
        const stale = expected.filter((h) => !live.has(h)).map(short);
        const unseen = latestSources
          .filter((s) => !exp.has(s.payload_hash))
          .map((s) => `${s.source}:${short(s.payload_hash)}`);
        throw new Error(
          `review resolve: --expect mismatch — the live evidence is not the set that was assessed` +
            ` (expected ${expected.length} hash(es), live ${reviewedHashes.length};` +
            ` assessed but no longer latest: [${stale.join(", ")}];` +
            ` latest but not assessed: [${unseen.join(", ")}]).` +
            ` Nothing written. Re-run \`review show\` and reassess before writing.`,
        );
      }
    }

    // Contract-validate BEFORE touching the log (pin⇔date, note non-empty after trim, operator, hashes).
    const verdict = HumanReviewVerdict.parse({
      kind: input.kind,
      ...(input.close !== undefined ? { pinned_close_date: input.close } : {}),
      note: input.note,
      operator: input.operator,
      reviewer: input.reviewer ?? "human",
      reviewed_payload_hashes: reviewedHashes,
    });

    const raw = { ...verdict };
    const ingest = await ingestObservationWithin(tx, {
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

    // Re-read AFTER the insert, inside the same transaction. READ COMMITTED sees rows committed since
    // the first read, so a source observation that landed in between means the hashes this verdict
    // carries are not the live set — throw, and postgres.js rolls the insert back with it.
    const after = await latestSourceHashes(tx, input.ocdId);
    if (
      !sameHashSet(
        after.map((s) => s.payload_hash),
        reviewedHashes,
      )
    )
      throw new Error(
        `review resolve: source evidence for "${input.ocdId}" changed while the verdict was being written — nothing written. Re-run \`review show\` and reassess.`,
      );

    return { ingest, reviewedHashes };
  });

  const result = await reconcileOcdId(sql, input.ocdId, now);
  const honoredNow = selectHonoredVerdict(
    await loadObservations(sql, input.ocdId),
  );
  // Honored iff the engine honors the latest verdict AND that verdict is this write (or, when the
  // write deduped, the identical verdict already latest — same payload, same meaning).
  const honored =
    honoredNow !== null &&
    (written.ingest.observationId === null ||
      honoredNow.observation.observation_id === written.ingest.observationId);
  return {
    inserted: written.ingest.inserted,
    observationId: written.ingest.observationId,
    reviewedHashes: written.reviewedHashes,
    result,
    honored,
  };
}

/** Re-exported for callers that reason about honoring without the DB (tests, the autopilot). */
export type { HonoredVerdict, Observation };
