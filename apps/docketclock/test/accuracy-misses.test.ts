/**
 * accuracy-misses.test.ts — replay every committed accuracy-miss fixture through the PURE verdict
 * path (slice V, PR-V2: "every miss becomes a regression test").
 *
 * Fixtures live in eval/accuracy-misses/*.json, written by scripts/export-accuracy-miss.ts: each
 * holds the EXACT computeVerdict input the verifier assembled for one real window (the at-close
 * claim, the drifted current close/status, every post-close observation via both linkage paths)
 * plus an `expected` GOLD verdict block — initialized from the live record and HAND-CORRECTED when
 * the fixture pins a bug. The replay asserts computeVerdict(input) matches `expected` on every
 * Verdict field (was_correct, basis, contradicting_observation_ids — the full shape; stray extra
 * keys in a gold block are ignored, not compared), so:
 *   • a fixture whose `expected` was corrected FAILS here until the verdict/reconcile fix lands
 *     (the fail-before / pass-after loop the plan requires), and
 *   • once green, every future rule change is regression-guarded by the real-world chain that
 *     once fooled us — same discipline as eval/chain-gold.json, no live calls, CI-runnable.
 *
 * Every expected verdict is ALSO revalidated through the frozen 0.9.0 AccuracyVerdict contract —
 * a hand-edited gold block that violates the refinements (lapsed⇔null, miss-names-evidence,
 * only-a-miss-carries-ids) is a broken fixture, not a passing test.
 *
 * No fixtures committed is a PASS (the directory ships empty until the first find) — but a fixture
 * that fails to parse is a FAILURE, never a skip.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { AccuracyVerdict } from "@yokel/contracts";
import {
  computeVerdict,
  type VerdictInput,
  type Verdict,
} from "../src/verify/verdict.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const FIXTURE_DIR = fileURLToPath(
  new URL("../eval/accuracy-misses/", import.meta.url),
);

const files = existsSync(FIXTURE_DIR)
  ? readdirSync(FIXTURE_DIR)
      .filter((f) => f.endsWith(".json"))
      .sort()
  : [];

out.push(`accuracy-miss replay: ${files.length} committed fixture(s)`);

for (const file of files) {
  let fixture: {
    meta?: { ocd_id?: string };
    input: VerdictInput;
    expected: Verdict;
  };
  try {
    fixture = JSON.parse(readFileSync(resolve(FIXTURE_DIR, file), "utf8"));
  } catch (err) {
    assert(`${file}: parses as JSON`, false, String(err));
    continue;
  }

  const ok =
    fixture.input !== undefined &&
    fixture.expected !== undefined &&
    typeof fixture.input.publishedCloseUtc === "string" &&
    Array.isArray(fixture.input.observationsSinceClose);
  assert(`${file}: carries input + expected blocks`, ok);
  if (!ok) continue;

  // The gold block itself must be a contract-legal verdict — a hand-edit that breaks the
  // refinements is a broken fixture.
  const gold = AccuracyVerdict.safeParse(fixture.expected);
  assert(
    `${file}: expected verdict is contract-legal (0.9.0 refinements)`,
    gold.success,
    gold.success ? "" : gold.error.issues[0]?.message,
  );

  const actual = computeVerdict(fixture.input);
  const match =
    actual.was_correct === fixture.expected.was_correct &&
    actual.basis === fixture.expected.basis &&
    JSON.stringify(actual.contradicting_observation_ids) ===
      JSON.stringify(fixture.expected.contradicting_observation_ids);
  assert(
    `${file}: computeVerdict replay matches the gold verdict`,
    match,
    match
      ? ""
      : `expected ${JSON.stringify(fixture.expected)}, got ${JSON.stringify(actual)}`,
  );
}

console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("\nALL EXPECTATIONS MET");
