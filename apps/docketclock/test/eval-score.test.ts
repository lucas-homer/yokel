/**
 * eval-score.test.ts — PR-D2 (observability slice D): the PURE eval scorer, proven with NO I/O. Pins the
 * metric semantics the regression gate depends on:
 *
 *   • PRIMARY binary "amends?" accuracy collapses {reject, uncertain} → not-amends on gold AND prediction.
 *   • A reject↔uncertain disagreement moves ONLY the 3-way exact number, NOT the binary headline.
 *   • TP/FP/FN/TN, precision/recall/F1, and the 3×3 confusion totals are correct.
 *   • Empty input is degenerate-safe (zeros, no NaN, no throw).
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { scoreEval, type EvalResult } from "../src/adjudicator/eval-score.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
const approx = (a: number, b: number): boolean => Math.abs(a - b) < 1e-9;

function r(gold: string, predicted: string): EvalResult {
  return {
    contentHash: "h",
    kind: "chain",
    gold: gold as EvalResult["gold"],
    predicted: predicted as EvalResult["predicted"],
  };
}

// 1. Perfect predictions → everything 1.
{
  const s = scoreEval([r("affirm", "affirm"), r("reject", "reject")]);
  assert(
    "perfect: amends & exact accuracy = 1, precision/recall/f1 = 1",
    s.amendsAccuracy === 1 &&
      s.exactAccuracy === 1 &&
      s.precision === 1 &&
      s.recall === 1 &&
      s.f1 === 1,
  );
}

// 2. reject↔uncertain disagreement moves ONLY the 3-way exact number, not the binary headline.
{
  const s = scoreEval([
    r("affirm", "affirm"),
    r("reject", "uncertain"), // both are "not-amends" → binary-correct, but exact-wrong
  ]);
  assert(
    "binary headline unaffected by reject↔uncertain disagreement",
    s.amendsAccuracy === 1,
    `amendsAccuracy=${s.amendsAccuracy}`,
  );
  assert(
    "3-way exact accuracy DOES drop on reject↔uncertain disagreement",
    s.exactAccuracy === 0.5,
    `exactAccuracy=${s.exactAccuracy}`,
  );
}

// 3. False positive (gold not-amends, predicted affirm) and false negative (gold affirm, predicted not).
{
  const s = scoreEval([
    r("affirm", "affirm"), // tp
    r("reject", "affirm"), // fp — a fabricated link
    r("affirm", "reject"), // fn — a missed link
    r("uncertain", "uncertain"), // tn (gold not-amends, pred not-amends)
  ]);
  const c = s.amendsConfusion;
  assert(
    "amends confusion counts tp/fp/fn/tn correctly",
    c.tp === 1 && c.fp === 1 && c.fn === 1 && c.tn === 1,
    JSON.stringify(c),
  );
  assert("amendsAccuracy = (tp+tn)/n", approx(s.amendsAccuracy, 0.5));
  assert("precision = tp/(tp+fp)", approx(s.precision, 0.5));
  assert("recall = tp/(tp+fn)", approx(s.recall, 0.5));
  assert("f1 = harmonic mean", approx(s.f1, 0.5));
}

// 4. 3×3 confusion matrix totals sum to n; cells land where expected.
{
  const results = [
    r("affirm", "affirm"),
    r("affirm", "reject"),
    r("reject", "reject"),
    r("uncertain", "affirm"),
  ];
  const s = scoreEval(results);
  let sum = 0;
  for (const g of Object.keys(s.confusion))
    for (const p of Object.keys(s.confusion[g]!)) sum += s.confusion[g]![p]!;
  assert("confusion totals sum to n", sum === results.length && s.n === 4);
  assert(
    "confusion cells: gold=affirm row split 1 affirm / 1 reject",
    s.confusion["affirm"]!["affirm"] === 1 &&
      s.confusion["affirm"]!["reject"] === 1,
  );
  assert(
    "confusion cell: gold=uncertain predicted=affirm (an FP) recorded",
    s.confusion["uncertain"]!["affirm"] === 1,
  );
}

// 5. Empty input is degenerate-safe.
{
  const s = scoreEval([]);
  assert(
    "empty: n=0, all metrics 0, no NaN, no throw",
    s.n === 0 &&
      s.amendsAccuracy === 0 &&
      s.exactAccuracy === 0 &&
      s.precision === 0 &&
      s.f1 === 0 &&
      !Number.isNaN(s.f1),
  );
}

console.log("\n=== eval-score results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
