/**
 * chain-pass.ts — the cross-window (chain) reconcile pass as an Effect program (ADR 0018, slice 5).
 *
 * Same work, same order, same result as before; what changes is that each step is a span inside
 * `poll.pass.chain`, so a trace shows where the pass spends its time:
 *
 *   SELECT chain candidates   every window joined to its LATEST federal_register observation
 *   chain.core                the pure rulebook (chain.ts): confident links + the ambiguous tail
 *   chain.adjudicate          cache peeks and fresh LLM consults for the ambiguous tail (chain-adjudicate.ts)
 *   TRANSACTION chain conflicts  upsert the merged live set, retire stale cross_window rows (persist.ts)
 *
 * Failure model: a database failure on the candidate read, a cache peek or the persist transaction is a
 * typed `SqlError` and fails the pass (run.ts isolates it from the other passes). A failed LLM consult is
 * isolated per pair inside chain.adjudicate and never fails the pass.
 *
 * INVARIANT (N1): the candidate read FAILS on any DB error, so it can never silently yield [] and trip the
 * retire-all-cross_window path in persistChainConflicts. Retire-all happens only on a genuinely empty
 * candidate set (no FR-backed windows).
 *
 * `chainReconcileOnce` keeps its Promise signature (re-exported from persist.ts) and rejects with the
 * driver's own error, so existing callers and tests are unchanged.
 */
import { Effect } from "effect";
import { runAmbient } from "../ambient.js";
import { selectAdjudicator } from "../adjudicator/select.js";
import type { Sql } from "../db/client.js";
import { dbQuery, type SqlError } from "../db/effect.js";
import { chainCore, isAmendment, type ChainCandidate } from "./chain.js";
import {
  adjudicateAmbiguous,
  chainMaxEscalations,
} from "./chain-adjudicate.js";
import { derivedIsCorrection, extractFr } from "./extract.js";
import {
  persistChainConflicts,
  type ChainReconcileOnceOptions,
  type ChainReconcileOnceResult,
} from "./persist.js";

interface CandidateRow {
  ocd_id: string;
  fr_observation_id: string;
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
  raw: unknown;
  status: string;
  resolved_close_utc: Date | string | null;
  govinfo_url: string | null;
  govinfo_text: string | null;
}

/**
 * Candidate join: a window contributes a candidate only when it HAS a federal_register observation (the
 * chain conflict is FR-doc ↔ FR-doc). `distinct on (w.ocd_id)` ordered by fetched_at desc picks the
 * freshest FR doc; is_* flags + raw come straight off that row.
 */
const loadCandidateRows = (sql: Sql) =>
  dbQuery(
    "SELECT chain candidates",
    () =>
      sql<CandidateRow[]>`
      select distinct on (w.ocd_id)
        w.ocd_id,
        o.observation_id as fr_observation_id,
        o.is_extension, o.is_correction, o.is_withdrawal, o.is_reopening, o.raw,
        w.status, w.resolved_close_utc, w.govinfo_url,
        (select g.raw_dates_text from observations g
          where g.ocd_id = w.ocd_id and g.source = 'govinfo'
          order by g.fetched_at desc, g.observation_id desc
          limit 1) as govinfo_text
      from participation_windows w
      join observations o
        on o.ocd_id = w.ocd_id and o.source = 'federal_register'
      order by w.ocd_id, o.fetched_at desc, o.observation_id desc
    `,
    (rows) => ({ "db.response.returned_rows": rows.length }),
  );

/**
 * One row → one ChainCandidate. publication_date / docket_ids / rin / dates_text come from the FR raw
 * payload (extractFr) — the same projection reconcile.ts uses, so the chain pass sees identical fields.
 */
function toCandidate(r: CandidateRow): ChainCandidate {
  const fr = extractFr(r.raw);
  return {
    ocd_id: r.ocd_id,
    fr_observation_id: r.fr_observation_id,
    fr_document_number: fr.documentNumber,
    docket_ids: fr.docketIds,
    rin: fr.rin,
    rins: fr.rins,
    is_extension: r.is_extension,
    // fr-v3 rule read off raw, so an fr-v2 correction row (correction_of, no keyword) is a correction.
    is_correction: derivedIsCorrection(r),
    is_withdrawal: r.is_withdrawal,
    is_reopening: r.is_reopening,
    title: fr.title,
    publication_date: fr.publicationDate,
    govinfo_url: r.govinfo_url,
    dates_text: fr.datesText,
    status: r.status,
    resolved_close_utc:
      r.resolved_close_utc instanceof Date
        ? r.resolved_close_utc.toISOString()
        : r.resolved_close_utc,
    citation: fr.citation,
    correction_of: fr.correctionOf,
    corrections: fr.corrections,
    govinfo_text: r.govinfo_text,
  };
}

/** The chain pass as an Effect. */
export const chainReconcile = (
  sql: Sql,
  now: Date = new Date(),
  options: ChainReconcileOnceOptions = {},
): Effect.Effect<ChainReconcileOnceResult, SqlError> =>
  Effect.gen(function* () {
    const adjudicator = options.adjudicator ?? selectAdjudicator();
    const cap = options.cap ?? chainMaxEscalations();

    const rows = yield* loadCandidateRows(sql);

    // The pure engine, CPU only. chainCore computes BOTH the confident links (rules 1–5) and the ambiguous
    // tail in one pass over the pairs that can link (CandidateIndex in chain.ts), once per cycle.
    const { candidates, amendments, confident, ambiguousPairs } =
      yield* Effect.sync(() => {
        const candidates = rows.map(toCandidate);
        // Count amendments by the SAME predicate the engine links on (single source of truth, chain.ts).
        const amendments = candidates.filter(isAmendment).length;
        const { confident, ambiguous } = chainCore(candidates, now);
        return { candidates, amendments, confident, ambiguousPairs: ambiguous };
      }).pipe(
        Effect.tap((r) =>
          Effect.annotateCurrentSpan({
            "docketclock.chain.candidates": r.candidates.length,
            "docketclock.chain.amendments": r.amendments,
            "docketclock.chain.confident": r.confident.length,
            "docketclock.chain.ambiguous": r.ambiguousPairs.length,
          }),
        ),
        Effect.withSpan("chain.core"),
      );

    // AMBIGUOUS tail — escalate to the adjudicator; only an `affirm` promotes a pair (with
    // `llm_corroborated`). A null adapter / outage / reject / uncertain → no promotion (worst case is the
    // confident-only output). Per-pair consult failures are isolated inside.
    const adjudicated = yield* adjudicateAmbiguous(
      sql,
      adjudicator,
      ambiguousPairs,
      now,
      cap,
    );

    // MERGE confident + LLM-affirmed, then RE-SORT with the SAME total order the engine uses so the persisted
    // set is stable regardless of which links were LLM-promoted. (A confident and a promoted pair can never
    // collide on the 4-tuple key: an ambiguous pair fails rule 2, so it is never also a confident link.)
    const merged = [...confident, ...adjudicated.links].sort(
      (x, y) =>
        x.ocd_id.localeCompare(y.ocd_id) ||
        x.ocd_id_b.localeCompare(y.ocd_id_b) ||
        x.observation_a_id.localeCompare(y.observation_a_id) ||
        x.observation_b_id.localeCompare(y.observation_b_id),
    );

    const persisted = yield* dbQuery(
      "TRANSACTION chain conflicts",
      () => persistChainConflicts(sql, merged, now),
      (p) => ({
        "docketclock.chain.live": p.conflictsLive,
        "docketclock.chain.retired": p.retired,
      }),
    );

    return {
      candidates: candidates.length,
      amendments,
      linked: confident.length,
      ambiguous: adjudicated.ambiguous,
      cacheHits: adjudicated.cacheHits,
      llmCalls: adjudicated.llmCalls,
      llmLinked: adjudicated.llmLinked,
      deferred: adjudicated.deferred,
      ...persisted,
    };
  });

/**
 * chainReconcileOnce — the Promise form (ADR 0018 Promise boundary). Rejects with the driver's own error on
 * a database failure, exactly as before.
 */
export function chainReconcileOnce(
  sql: Sql,
  now: Date = new Date(),
  options: ChainReconcileOnceOptions = {},
): Promise<ChainReconcileOnceResult> {
  return runAmbient(
    chainReconcile(sql, now, options).pipe(
      Effect.catch((err) => Effect.die(err.cause)),
    ),
  );
}
