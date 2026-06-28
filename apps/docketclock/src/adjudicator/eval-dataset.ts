/**
 * adjudicator/eval-dataset.ts — the PURE selection logic behind the Langfuse eval-dataset seed (PR-C3).
 * Extracted from the seed script so it can be unit-tested with NO Postgres and NO Langfuse: given the
 * `adjudications` rows (in the order the script SELECTs them — oldest-first, see below), it produces the
 * stratified, capped, deduped set of dataset items. The script (`scripts/seed-langfuse-dataset.ts`) owns
 * the I/O (DB read + Langfuse upsert); this module owns the decisions.
 *
 * INVARIANTS (all exercised in test/eval-dataset.test.ts):
 *   • Dedup by content_hash — one item per distinct input; the FIRST row seen for a hash wins.
 *   • null-skip never shadows a deciding verdict — a `null:*` abstention is dropped with a `continue` that
 *     never occupies the hash slot, so a later deciding verdict for the same hash is still selected.
 *   • Cap per (kind × classification) stratum — a stratum never exceeds `cap`.
 *   • Stability — because the caller passes rows oldest-first over an append-only table, once a stratum is
 *     full, appending NEWER rows at the tail cannot change the selected set (the cap is reached before they
 *     are reached). That makes a re-run after the cache grows a true no-op.
 *
 * KINDS / CLASSES are DERIVED from @yokel/contracts (not hardcoded), so adding a new AdjudicationInput
 * `kind` or AdjudicationClassification value automatically grows the stratification grid — no silent
 * coverage gap where a new stratum's items would be bucketed but never selected.
 */
import {
  AdjudicationInput,
  AdjudicationVerdict,
  AdjudicationClassification,
  type AdjudicationClassification as Classification,
} from "@yokel/contracts";

/** The notice|chain discriminant, derived from the contract's discriminated union (no hardcoded list). */
export type AdjudicationKind = AdjudicationInput["kind"];

/** All input kinds, from the AdjudicationInput discriminated union's members (each member's `kind` literal). */
export const KINDS = AdjudicationInput.options.map(
  (member) => member.shape.kind.value,
) as AdjudicationKind[];

/** All verdict classifications, straight off the contract enum. */
export const CLASSES = AdjudicationClassification.options;

/** One `adjudications` row as Postgres returns it (input/verdict are jsonb → already-parsed objects). */
export interface AdjudicationRow {
  content_hash: string;
  input: unknown;
  verdict: unknown;
  adjudicator_id: string;
  created_at: Date;
}

/** A validated, selectable candidate item. */
export interface Candidate {
  contentHash: string;
  adjudicatorId: string;
  input: AdjudicationInput;
  verdict: AdjudicationVerdict;
  kind: AdjudicationKind;
  classification: Classification;
}

/** One cell of the kind × classification grid (count after capping); emitted for EVERY cell incl. empties. */
export interface StratumCount {
  kind: AdjudicationKind;
  classification: Classification;
  count: number;
}

export interface SelectOptions {
  /** max items per (kind × classification) stratum. */
  cap: number;
  /** when false (default), drop `null:*` abstentions — they carry no eval signal. */
  includeNull: boolean;
}

export interface SelectionResult {
  /** the chosen items, flattened in grid order (kind-major, then classification). */
  selected: Candidate[];
  /** the full kind × classification grid with post-cap counts (empty strata included, for reporting). */
  grid: StratumCount[];
  /** total rows considered. */
  total: number;
  /** rows dropped as `null:*` abstentions. */
  skippedNull: number;
  /** rows dropped because they no longer satisfy the frozen contract. */
  skippedInvalid: number;
}

const stratumKey = (k: string, c: string): string => `${k}/${c}`;

/**
 * Pure selection: rows (oldest-first) → deduped, null-filtered, contract-validated, stratified, capped set.
 * No I/O. The caller is responsible for passing rows in the desired order (the script uses
 * `order by created_at asc, content_hash asc`).
 */
export function selectDatasetItems(
  rows: AdjudicationRow[],
  opts: SelectOptions,
): SelectionResult {
  // Dedup by content_hash; null-skip; validate. First row seen for a hash wins (oldest-first ⇒ oldest
  // deciding verdict). The null-skip `continue` never sets the slot, so it can't shadow/evict a real verdict.
  const byHash = new Map<string, Candidate>();
  let skippedNull = 0;
  let skippedInvalid = 0;
  for (const row of rows) {
    if (byHash.has(row.content_hash)) continue;
    // `|| ""` guards a NULL adjudicator_id (outside the parse try/catch); the column is NOT NULL, but a
    // deciding verdict missing its provenance is unusable anyway → treat as a skip rather than throw.
    if (!opts.includeNull && (row.adjudicator_id || "").startsWith("null:")) {
      skippedNull++;
      continue;
    }
    let input: AdjudicationInput;
    let verdict: AdjudicationVerdict;
    try {
      input = AdjudicationInput.parse(row.input);
      verdict = AdjudicationVerdict.parse(row.verdict);
    } catch {
      skippedInvalid++; // a row that no longer matches the frozen contract is not a usable eval item
      continue;
    }
    byHash.set(row.content_hash, {
      contentHash: row.content_hash,
      adjudicatorId: row.adjudicator_id,
      input,
      verdict,
      kind: input.kind,
      classification: verdict.classification,
    });
  }

  // Stratify by kind × classification, capping per stratum (stable: candidates are already oldest-first).
  const strata = new Map<string, Candidate[]>();
  for (const cand of byHash.values()) {
    const key = stratumKey(cand.kind, cand.classification);
    const bucket = strata.get(key) ?? [];
    if (bucket.length < opts.cap) bucket.push(cand);
    strata.set(key, bucket);
  }

  // Flatten across the FULL contract-derived grid (so empty strata are reported, and no candidate kind/class
  // can fall outside the grid — KINDS/CLASSES come from the same contract the rows were parsed against).
  const selected: Candidate[] = [];
  const grid: StratumCount[] = [];
  for (const kind of KINDS) {
    for (const classification of CLASSES) {
      const bucket = strata.get(stratumKey(kind, classification)) ?? [];
      grid.push({ kind, classification, count: bucket.length });
      selected.push(...bucket);
    }
  }

  return { selected, grid, total: rows.length, skippedNull, skippedInvalid };
}
