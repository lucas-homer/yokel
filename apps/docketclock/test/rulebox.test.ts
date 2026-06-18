/**
 * rulebox.test.ts — Slice 1b: the two regex stopgaps (notice-flags 4 classify regexes; chain.ts
 * DENY_PATTERNS deny regexes) are now a VERSIONED, Zod-validated RuleBox behind ONE deterministic
 * evaluator. This is a BEHAVIOR-PRESERVING refactor: the bar is byte-identical classification.
 *
 * Three batteries:
 *   • LOAD/VALIDATION — the shipped rulebook parses via RuleBox.parse; a deliberately malformed box
 *     (bad regex flags, un-compilable source, OR a duplicate id) is REJECTED at parse time.
 *   • CLASSIFY equivalence — noticeFlagsFromRules(t) === the legacy 4-regex noticeFlags(t) for a corpus
 *     of ~20 titles (the notice-flags.test cases + edge cases). The evaluator is the source of truth and
 *     notice-flags.ts now delegates to it, so notice-flags.test.ts is also a free regression lock.
 *   • DENY equivalence — the 3 real D3 spike land-withdrawal titles are DENIED; genuine comment-period
 *     notices (extension/reopening/correction) are NOT denied. chain.test.ts (BLM trap) is the other lock.
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { RuleBox } from "@yokel/contracts";
import {
  ruleBox,
  noticeFlagsFromRules,
  isDenied,
} from "../src/rulebox/index.js";
import type { NoticeFlags } from "../src/sources/notice-flags.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// ── LOAD + VALIDATION ────────────────────────────────────────────────────────────────────────────

// 1. The shipped rulebook is a valid RuleBox (already parsed at module load; re-parse here as a probe).
{
  const res = RuleBox.safeParse(ruleBox);
  assert(
    "1 shipped rulebook parses via RuleBox.parse",
    res.success,
    res.success ? ruleBox.version : JSON.stringify(res.error?.issues),
  );
  assert(
    "1 rulebook is versioned + carries 4 classify + 5 deny rules",
    ruleBox.version.length > 0 &&
      ruleBox.rules.filter((r) => r.kind === "classify").length === 4 &&
      ruleBox.rules.filter((r) => r.kind === "deny").length === 5,
    `${ruleBox.version}: ${ruleBox.rules.length} rules`,
  );
}

// 2. A malformed box is REJECTED at parse time (illegal flag, un-compilable source, duplicate id).
{
  const badFlags = RuleBox.safeParse({
    version: "bad",
    rules: [
      {
        kind: "deny",
        id: "x",
        pattern: { source: "a", flags: "Q" },
        rationale: "r",
      },
    ],
  });
  assert("2 illegal regex flag rejected at load", !badFlags.success);

  const badSource = RuleBox.safeParse({
    version: "bad",
    rules: [
      {
        kind: "deny",
        id: "x",
        pattern: { source: "(", flags: "" },
        rationale: "r",
      },
    ],
  });
  assert("2 un-compilable source rejected at load", !badSource.success);

  const dupId = RuleBox.safeParse({
    version: "bad",
    rules: [
      {
        kind: "deny",
        id: "dup",
        pattern: { source: "a", flags: "" },
        rationale: "r",
      },
      {
        kind: "deny",
        id: "dup",
        pattern: { source: "b", flags: "" },
        rationale: "r",
      },
    ],
  });
  assert("2 duplicate rule id rejected at load", !dupId.success);
}

// ── CLASSIFY EQUIVALENCE (the behavior-preservation bar) ───────────────────────────────────────────

// The legacy regexes, inlined here as the GOLDEN oracle (verbatim from the pre-refactor notice-flags.ts).
const LEGACY = {
  extension: /\bextension\b|\bextend(?:ed|ing)?\b/i,
  correction: /\bcorrection\b|\bcorrect(?:ed|ing)?\b/i,
  withdrawal: /\bwithdraw(?:al|n|ing)?\b/i,
  reopening: /\breopen(?:ed|ing|s)?\b/i,
};
function legacyFlags(t: string): NoticeFlags {
  return {
    is_extension: LEGACY.extension.test(t),
    is_correction: LEGACY.correction.test(t),
    is_withdrawal: LEGACY.withdrawal.test(t),
    is_reopening: LEGACY.reopening.test(t),
  };
}

const CORPUS = [
  // from notice-flags.test.ts
  "Reopening of the Comment Period",
  "Proposed Rule; Reopening of Comment Period",
  "Notice; comment period reopened",
  "The agency reopens the comment period",
  "Extension of Comment Period",
  "Comment period extended",
  "Notice; extending the comment deadline",
  "Extension and Reopening of the Comment Period",
  "Notice of Proposed Rulemaking; Request for Comments",
  // real D3 spike titles + edge cases
  "Agency Information Collection Activities; Extension of Collection; Virginia Graeme Baker Pool and Spa Safety Act Verification of Compliance Form",
  "General and Plastic Surgery Devices: ...; Withdrawal of Proposed Rule",
  "Administrative Declaration Amendment of a Disaster for the State of Washington; Correction",
  "Correction of Public Land Order No. 7963; National Defense Operating Area Withdrawal, Doña Ana, Luna, and Hidalgo Counties, NM",
  "Flathead National Forest; Montana; Mid-Swan Landscape Restoration & Wildland Urban Interface Fuels Project; Withdrawal",
  "White River National Forest; Eagle County, CO; Camp Hale Restoration and Enhancement Project EIS; Withdrawal",
  // tricky word-boundary cases (must match legacy exactly, incl. NON-matches)
  "corrected", // correct(ed) → correction true
  "withdrawn from sale", // withdraw(n) → withdrawal true
  "reopens", // reopen(s) → reopening true
  "extensible architecture", // \bextension\b? no; extend? no — must be FALSE
  "incorrect assumptions", // \bcorrect\b inside 'incorrect' — boundary; both must agree
  "", // empty
];

{
  let allEqual = true;
  for (const t of CORPUS) {
    const a = noticeFlagsFromRules(t);
    const b = legacyFlags(t);
    if (JSON.stringify(a) !== JSON.stringify(b)) {
      allEqual = false;
      out.push(
        `       DIVERGENCE "${t}": rules=${JSON.stringify(a)} legacy=${JSON.stringify(b)}`,
      );
    }
  }
  assert(
    "3 classify: noticeFlagsFromRules === legacy regexes for the whole corpus",
    allEqual,
  );
}

// 4. Spot-check the documented expected flags (independent of the oracle, so a bug in BOTH is caught).
{
  const reopen = noticeFlagsFromRules("Reopening of the Comment Period");
  assert(
    "4 reopening → is_reopening only",
    reopen.is_reopening && !reopen.is_extension,
  );
  const ext = noticeFlagsFromRules("Extension of Comment Period");
  assert(
    "4 extension → is_extension only",
    ext.is_extension && !ext.is_reopening,
  );
  const both = noticeFlagsFromRules(
    "Extension and Reopening of the Comment Period",
  );
  assert("4 both → both flags", both.is_extension && both.is_reopening);
  const benign = noticeFlagsFromRules(
    "Notice of Proposed Rulemaking; Request for Comments",
  );
  assert(
    "4 benign → all four false",
    !benign.is_extension &&
      !benign.is_correction &&
      !benign.is_withdrawal &&
      !benign.is_reopening,
  );
}

// ── DENY EQUIVALENCE ──────────────────────────────────────────────────────────────────────────────

// 5. The 3 real D3 spike land-withdrawal titles are DENIED (the BLM 2023-27468 trap family).
{
  const spikeTitles = [
    "Correction of Public Land Order No. 7963; National Defense Operating Area Withdrawal, Doña Ana, Luna, and Hidalgo Counties, NM",
    "Flathead National Forest; Montana; Mid-Swan Landscape Restoration & Wildland Urban Interface Fuels Project; Withdrawal",
    "White River National Forest; Eagle County, CO; Camp Hale Restoration and Enhancement Project EIS; Withdrawal",
  ];
  assert(
    "5 all 3 real D3 spike land-withdrawal titles are DENIED",
    spikeTitles.every((t) => isDenied(t)),
    spikeTitles.map((t) => `${t.slice(0, 20)}=${isDenied(t)}`).join("; "),
  );
}

// 5b. dates_text-borne land-withdrawal variants are denied too (vehicle phrase in the haystack).
{
  const variants = [
    "This order provides for a withdrawal of certain public land of approximately 4,000 acres.",
    "Notice of Proposed Withdrawal and opportunity for public meeting under the Public Lands Order process.",
  ];
  assert(
    "5b dates_text land-withdrawal variants denied",
    variants.every((t) => isDenied(t)),
  );
}

// 6. Genuine comment-period notices are NOT denied (the under-suppression guard).
{
  const genuine = [
    "Extension of Comment Period",
    "Reopening of the Comment Period",
    "Administrative Declaration Amendment of a Disaster for the State of Washington; Correction",
    "Accidental Release Prevention Requirements; Risk Management Programs; Extension of Comment Period",
    "Notice of Proposed Rulemaking; Request for Comments",
  ];
  assert(
    "6 genuine comment-period notices are NOT denied",
    genuine.every((t) => !isDenied(t)),
    genuine.map((t) => `${t.slice(0, 18)}=${isDenied(t)}`).join("; "),
  );
}

console.log("\n=== rulebox results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
