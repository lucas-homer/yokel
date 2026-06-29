/**
 * adjudicator/eval-score.ts — PURE scoring for the chain-adjudicator eval (Slice D, PR-D2). Given the
 * model's predicted classification vs the human gold label for each item, compute the metrics. No I/O —
 * the runner (scripts/eval-chain.ts) does the live calls + Langfuse push; this module just does the math,
 * so it is fully unit-tested.
 *
 * PRIMARY metric = BINARY "amends?" accuracy (affirm vs not-affirm). Downstream only `affirm` promotes a
 * cross_window link; `reject` and `uncertain` are downstream-IDENTICAL (no link — chain-adjudicate.ts), so
 * the operationally-meaningful decision is amends-vs-not. Collapsing {reject, uncertain} → "not-amends" on
 * BOTH gold and prediction means a gold label of reject vs uncertain never moves the headline number, and a
 * model that conservatively abstains (`uncertain`) is not punished for the correct no-link outcome.
 *
 * SECONDARY = the full 3×3 confusion matrix over {affirm, reject, uncertain} (rows = gold, cols = predicted)
 * and the exact 3-way accuracy, which surface reject↔uncertain disagreement for inspection.
 */
import {
  AdjudicationClassification,
  type AdjudicationClassification as Classification,
} from "@yokel/contracts";

const CLASSES = AdjudicationClassification.options;

/** One scored item: the model's predicted classification vs the human gold for a given input. */
export interface EvalResult {
  contentHash: string;
  kind: string;
  gold: Classification;
  predicted: Classification;
}

/** 2×2 confusion on the binary "amends" (affirm) decision. */
export interface AmendsConfusion {
  /** gold amends & predicted amends. */
  tp: number;
  /** predicted amends & gold does not (a false link — the worst error for this conservative system). */
  fp: number;
  /** gold amends & predicted does not (a missed link). */
  fn: number;
  /** neither amends. */
  tn: number;
}

export interface ScoreSummary {
  n: number;
  /** PRIMARY: (tp+tn)/n on the binary amends-vs-not decision. */
  amendsAccuracy: number;
  amendsConfusion: AmendsConfusion;
  /** precision/recall/F1 on "amends" (affirm) — informative when the classes are imbalanced. */
  precision: number;
  recall: number;
  f1: number;
  /** SECONDARY: exact 3-way classification accuracy. */
  exactAccuracy: number;
  /** SECONDARY: 3×3 confusion, confusion[gold][predicted]. */
  confusion: Record<string, Record<string, number>>;
}

const isAmends = (c: Classification): boolean => c === "affirm";
/** division that yields 0 (not NaN) for an empty denominator — keeps an empty/degenerate run printable. */
const ratio = (num: number, den: number): number => (den === 0 ? 0 : num / den);

export function scoreEval(results: EvalResult[]): ScoreSummary {
  const n = results.length;
  let tp = 0;
  let fp = 0;
  let fn = 0;
  let tn = 0;
  let exact = 0;

  // zero-init the full grid so empty strata still appear in the matrix.
  const confusion: Record<string, Record<string, number>> = {};
  for (const g of CLASSES) {
    confusion[g] = {};
    for (const p of CLASSES) confusion[g]![p] = 0;
  }

  for (const r of results) {
    // gold/predicted are Classification (∈ CLASSES) and the grid is fully zero-initialized above, so the
    // cell always exists — the non-null assertion is safe and no `?? 0` fallback is needed.
    confusion[r.gold]![r.predicted] = confusion[r.gold]![r.predicted]! + 1;
    if (r.predicted === r.gold) exact++;
    const goldAmends = isAmends(r.gold);
    const predAmends = isAmends(r.predicted);
    if (goldAmends && predAmends) tp++;
    else if (!goldAmends && predAmends) fp++;
    else if (goldAmends && !predAmends) fn++;
    else tn++;
  }

  const precision = ratio(tp, tp + fp);
  const recall = ratio(tp, tp + fn);
  const f1 = ratio(2 * precision * recall, precision + recall);

  return {
    n,
    amendsAccuracy: ratio(tp + tn, n),
    amendsConfusion: { tp, fp, fn, tn },
    precision,
    recall,
    f1,
    exactAccuracy: ratio(exact, n),
    confusion,
  };
}
