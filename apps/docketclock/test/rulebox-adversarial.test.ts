/**
 * rulebox-adversarial.test.ts — ADVERSARIAL differential lock for the RuleBox Slice-1 refactor.
 *
 * This is the skeptic's test: it does NOT trust the rulebook's hand-typed {source,flags} strings. It
 * reconstructs the ORACLE from the ORIGINAL inline RegExp LITERALS (verbatim from pre-refactor
 * notice-flags.ts + chain.ts DENY_PATTERNS, lifted from git HEAD) and proves byte-for-byte equivalence:
 *
 *   A. SOURCE/FLAGS identity — the compiled RegExp the evaluator builds has the SAME .source and .flags
 *      as the original literal (catches a dropped flag or a `\\b`-vs-`\b` escaping mistake in the literal).
 *   B. CLASSIFY differential — a large adversarial corpus through noticeFlagsFromRules vs the original 4
 *      regexes. ANY divergence fails.
 *   C. DENY differential — the original 5 DENY_PATTERNS vs isDenied over (i) the adversarial corpus and
 *      (ii) ALL 427 real D3 spike candidate titles from spikes/data/d3_candidates.json.
 *   D. STATEFULNESS — no rule carries g/y; repeated and interleaved .test() calls are stable.
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  noticeFlagsFromRules,
  isDenied,
  ruleBox,
} from "../src/rulebox/index.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// ── THE ORACLE: original inline literals, verbatim from git HEAD (pre-refactor). ────────────────────
const ORIG_CLASSIFY = {
  extension: /\bextension\b|\bextend(?:ed|ing)?\b/i,
  correction: /\bcorrection\b|\bcorrect(?:ed|ing)?\b/i,
  withdrawal: /\bwithdraw(?:al|n|ing)?\b/i,
  reopening: /\breopen(?:ed|ing|s)?\b/i,
};
const ORIG_DENY: RegExp[] = [
  /\bpublic\s+lands?\s+orders?\b/i,
  /\bland[\s-]?withdrawal\b/i,
  /\bwithdraw(?:al\s+of|s|ing)?\s+(?:(?:certain|public|national|forest|system)\s+)*lands?\b/i,
  /\bnational\s+forest\b[^.]*\bwithdrawal\b|\bwithdrawal\b[^.]*\bnational\s+forest\b/i,
  /\bnotice\s+of\s+(?:proposed\s+)?withdrawal\b/i,
];
function origFlags(t: string) {
  return {
    is_extension: ORIG_CLASSIFY.extension.test(t),
    is_correction: ORIG_CLASSIFY.correction.test(t),
    is_withdrawal: ORIG_CLASSIFY.withdrawal.test(t),
    is_reopening: ORIG_CLASSIFY.reopening.test(t),
  };
}
function origDenied(h: string): boolean {
  return ORIG_DENY.some((re) => re.test(h));
}

// ── A. SOURCE/FLAGS IDENTITY (the escaping / dropped-flag trap). ─────────────────────────────────────
{
  const classifyRules = ruleBox.rules.filter(
    (r): r is Extract<typeof r, { kind: "classify" }> => r.kind === "classify",
  );
  // Map by the flag it sets so we compare like-for-like, independent of rule order.
  const bySet = new Map(
    classifyRules.map((r) => [
      r.sets,
      new RegExp(r.pattern.source, r.pattern.flags),
    ]),
  );
  for (const [key, orig] of Object.entries(ORIG_CLASSIFY)) {
    const compiled = bySet.get(key as never);
    assert(
      `A classify "${key}" .source identical`,
      !!compiled && compiled.source === orig.source,
      compiled
        ? `rulebook=${compiled.source} | orig=${orig.source}`
        : "MISSING",
    );
    assert(
      `A classify "${key}" .flags identical`,
      !!compiled && compiled.flags === orig.flags,
      compiled ? `rulebook=${compiled.flags} | orig=${orig.flags}` : "MISSING",
    );
  }

  const denyRules = ruleBox.rules.filter(
    (r): r is Extract<typeof r, { kind: "deny" }> => r.kind === "deny",
  );
  assert(
    "A deny rule count == 5 (original DENY_PATTERNS count)",
    denyRules.length === ORIG_DENY.length,
    `${denyRules.length}`,
  );
  // Order-sensitive: the refactor claims patterns carried "verbatim ... and their order".
  for (let i = 0; i < ORIG_DENY.length; i++) {
    const orig = ORIG_DENY[i]!;
    const compiled = denyRules[i]
      ? new RegExp(denyRules[i]!.pattern.source, denyRules[i]!.pattern.flags)
      : null;
    assert(
      `A deny[${i}] .source identical (same order)`,
      !!compiled && compiled.source === orig.source,
      compiled
        ? `rulebook=${compiled.source} | orig=${orig.source}`
        : "MISSING",
    );
    assert(
      `A deny[${i}] .flags identical`,
      !!compiled && compiled.flags === orig.flags,
      compiled ? `rulebook=${compiled.flags} | orig=${orig.flags}` : "MISSING",
    );
  }
  // No stateful flags anywhere.
  const stateful = [...classifyRules, ...denyRules].filter(
    (r) => r.pattern.flags.includes("g") || r.pattern.flags.includes("y"),
  );
  assert(
    "A no rule carries the stateful g/y flag",
    stateful.length === 0,
    stateful.map((r) => r.id).join(","),
  );
}

// ── B + C(i). ADVERSARIAL CORPUS through BOTH classify and deny. ─────────────────────────────────────
const CORPUS = [
  // word-boundary edge cases the prompt called out
  "reopener",
  "reopenings",
  "reopened",
  "reopens",
  "reopen",
  "reopen the comment period",
  "extensions",
  "extensible architecture",
  "extensively",
  "extended deadline",
  "extending",
  "extension",
  "correctional facility siting",
  "incorrect assumptions",
  "corrected",
  "correcting",
  "correction",
  "withdrawing",
  "withdrawn from sale",
  "withdrawal of proposed rule",
  "withdraws",
  "withdrew",
  "land withdrawal",
  "land-withdrawal",
  "national forest system lands withdrawal",
  "Public Land Order No. 7963",
  "Public Lands Orders",
  "notice of proposed withdrawal",
  "withdrawal of certain public lands",
  // unicode / casing
  "EXTENSION OF COMMENT PERIOD",
  "Reopening of the Comment Period",
  "Doña Ana County withdrawal of public land",
  "café reopening",
  "Ｅxtension", // fullwidth E — must NOT match \bextension\b
  "exténsion", // accented e — must NOT match
  // multi-keyword
  "Extension and Reopening of the Comment Period; Correction; Withdrawal",
  "correction and extension and withdrawal and reopening",
  // empties / whitespace
  "",
  " ",
  "\n",
  "a.withdrawal of national forest lands", // the [^.]* alternation boundary
  "national forest. withdrawal", // period BREAKS the [^.]* — must match legacy exactly
  "withdrawal. national forest", // reverse, period in middle
];
{
  let allEq = true;
  for (const t of CORPUS) {
    const a = JSON.stringify(noticeFlagsFromRules(t));
    const b = JSON.stringify(origFlags(t));
    if (a !== b) {
      allEq = false;
      out.push(
        `       CLASSIFY DIVERGENCE ${JSON.stringify(t)}: rules=${a} orig=${b}`,
      );
    }
    if (isDenied(t) !== origDenied(t)) {
      allEq = false;
      out.push(
        `       DENY DIVERGENCE ${JSON.stringify(t)}: rules=${isDenied(t)} orig=${origDenied(t)}`,
      );
    }
  }
  assert(
    "B+Ci corpus: classify AND deny identical to original literals",
    allEq,
  );
}

// ── C(ii). ALL 427 real D3 spike candidate titles through the deny differential. ────────────────────
{
  const here = dirname(fileURLToPath(import.meta.url));
  const dataPath = join(here, "../../../spikes/data/d3_candidates.json");
  let cands: Array<{ title?: string | null }> = [];
  try {
    const j = JSON.parse(readFileSync(dataPath, "utf8")) as {
      candidates?: Array<{ title?: string | null }>;
    };
    cands = j.candidates ?? [];
  } catch (e) {
    assert("Cii spike data loaded", false, String(e));
  }
  assert(
    "Cii spike candidate corpus is non-trivial",
    cands.length > 100,
    `${cands.length}`,
  );

  let divergences = 0;
  let deniedCount = 0;
  for (const c of cands) {
    const t = c.title ?? "";
    const r = isDenied(t);
    const o = origDenied(t);
    if (r !== o) {
      divergences++;
      out.push(
        `       SPIKE DENY DIVERGENCE ${JSON.stringify(t.slice(0, 80))}: rules=${r} orig=${o}`,
      );
    }
    if (r) deniedCount++;
  }
  assert(
    "Cii deny differential over ALL real D3 titles: zero divergence",
    divergences === 0,
    `${cands.length} titles, ${deniedCount} denied, ${divergences} divergent`,
  );

  // Also run classify over the same real titles (catches a regression that no curated corpus would).
  let classifyDiv = 0;
  for (const c of cands) {
    const t = c.title ?? "";
    if (
      JSON.stringify(noticeFlagsFromRules(t)) !== JSON.stringify(origFlags(t))
    )
      classifyDiv++;
  }
  assert(
    "Cii classify differential over ALL real D3 titles: zero divergence",
    classifyDiv === 0,
    `${classifyDiv} divergent of ${cands.length}`,
  );

  // The 3 institutional spike titles MUST still be denied (under-suppression guard).
  const spike3 = cands
    .map((c) => c.title ?? "")
    .filter((t) =>
      /Public Land Order No\. 7963|Flathead National Forest|Camp Hale/.test(t),
    );
  assert(
    "Cii the documented D3 spike titles are present and DENIED",
    spike3.length >= 1 && spike3.every((t) => isDenied(t)),
    `${spike3.length} matched: ${spike3.map((t) => `${t.slice(0, 24)}=${isDenied(t)}`).join("; ")}`,
  );
}

// ── D. STATEFULNESS: repeated + interleaved calls are stable (no lastIndex drift). ──────────────────
{
  const probe = "Extension and Reopening of the Comment Period";
  const f1 = JSON.stringify(noticeFlagsFromRules(probe));
  const f2 = JSON.stringify(noticeFlagsFromRules(probe));
  const f3 = JSON.stringify(noticeFlagsFromRules(probe));
  assert("D classify stable across repeated calls", f1 === f2 && f2 === f3, f1);

  const denyProbe = "Notice of Proposed Withdrawal";
  const d1 = isDenied(denyProbe);
  // interleave a non-matching call then re-test
  isDenied("Extension of Comment Period");
  const d2 = isDenied(denyProbe);
  const d3 = isDenied(denyProbe);
  assert("D deny stable across repeated + interleaved calls", d1 && d2 && d3);
}

console.log("\n=== rulebox-adversarial results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL ADVERSARIAL EXPECTATIONS MET" : `${failures} ADVERSARIAL EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
