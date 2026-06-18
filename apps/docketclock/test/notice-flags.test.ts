/**
 * notice-flags.test.ts — the #O4 "clean split": `reopen…` moved OUT of the extension regex into its own
 * is_reopening flag. A REOPENING (a previously-CLOSED comment period re-opened) is a distinct legal event
 * from an EXTENSION (a still-open deadline moved later), so a reopening must set is_reopening=true and
 * is_extension=FALSE — otherwise the chain engine mislabels it `extension_chain_unresolved`. A notice
 * titled BOTH legitimately carries both flags.
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { noticeFlags } from "../src/sources/notice-flags.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// 1. A pure reopening → is_reopening ONLY (NOT is_extension). The headline O4 fix.
{
  for (const title of [
    "Reopening of the Comment Period",
    "Proposed Rule; Reopening of Comment Period",
    "Notice; comment period reopened",
    "The agency reopens the comment period",
  ]) {
    const f = noticeFlags(title);
    assert(
      `1 "${title}" → is_reopening=true, is_extension=false`,
      f.is_reopening === true && f.is_extension === false,
      `reopen=${f.is_reopening} ext=${f.is_extension}`,
    );
  }
}

// 2. A pure extension → is_extension ONLY (the split must not have broken extension detection).
{
  for (const title of [
    "Extension of Comment Period",
    "Comment period extended",
    "Notice; extending the comment deadline",
  ]) {
    const f = noticeFlags(title);
    assert(
      `2 "${title}" → is_extension=true, is_reopening=false`,
      f.is_extension === true && f.is_reopening === false,
      `ext=${f.is_extension} reopen=${f.is_reopening}`,
    );
  }
}

// 3. A notice titled BOTH → both flags fire honestly (a reopening that also extends).
{
  const f = noticeFlags("Extension and Reopening of the Comment Period");
  assert(
    "3 both extension AND reopening → both flags true",
    f.is_extension === true && f.is_reopening === true,
    `ext=${f.is_extension} reopen=${f.is_reopening}`,
  );
}

// 4. Reopening does not falsely trip correction or withdrawal.
{
  const f = noticeFlags("Reopening of the Comment Period");
  assert(
    "4 reopening does not trip correction/withdrawal",
    f.is_correction === false && f.is_withdrawal === false,
    `corr=${f.is_correction} wd=${f.is_withdrawal}`,
  );
}

// 5. A benign notice with none of the keywords → all four false.
{
  const f = noticeFlags("Notice of Proposed Rulemaking; Request for Comments");
  assert(
    "5 benign notice → all four flags false",
    !f.is_extension && !f.is_correction && !f.is_withdrawal && !f.is_reopening,
    JSON.stringify(f),
  );
}

console.log("\n=== notice-flags results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
