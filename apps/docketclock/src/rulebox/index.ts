/**
 * rulebox/index.ts — the PURE, deterministic RuleBox evaluator. ONE place compiles the rulebook's
 * SerializableRegex data into live RegExp objects (ONCE, at module load — never per call) and dispatches
 * on rule `kind`:
 *   • noticeFlagsFromRules(text) — runs the CLASSIFY rules → the 4 notice-type booleans (the byte-
 *     identical replacement for the legacy 4-regex notice-flags pass).
 *   • isDenied(haystack)         — runs the DENY rules → true if ANY matches (the byte-identical
 *     replacement for chain.ts isKeywordFalsePositive's DENY_PATTERNS.some(...)).
 *
 * PURE + deterministic: no clock, no IO beyond the single module-load parse in rulebook.ts. The same
 * input ALWAYS yields the same output. The `ambiguous` ClassifyRule marker is RESERVED for a later
 * LLM-escalation slice and is intentionally IGNORED here (today's rules are all unambiguous).
 */
import type { NoticeFlagKey } from "@yokel/contracts";
import { ruleBox } from "./rulebook.js";

export { ruleBox, RULEBOOK_VERSION } from "./rulebook.js";

/** The 4 notice-type booleans, keyed by their is_<key> name. Mirrors NoticeFlags in notice-flags.ts. */
export interface NoticeFlags {
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
}

/** A classify rule's compiled regex + the notice flag it sets. */
interface CompiledClassify {
  re: RegExp;
  sets: NoticeFlagKey;
}

// Compile ONCE at construction (module load). The rulebook already passed RuleBox.parse, so every
// pattern is guaranteed to compile — but we keep the construction here so the regexes are built a single
// time and the evaluator stays a pure function of `text`.
const CLASSIFY_RULES: CompiledClassify[] = ruleBox.rules
  .filter(
    (r): r is Extract<typeof r, { kind: "classify" }> => r.kind === "classify",
  )
  .map((r) => ({
    re: new RegExp(r.pattern.source, r.pattern.flags),
    sets: r.sets,
  }));

const DENY_RULES: RegExp[] = ruleBox.rules
  .filter((r): r is Extract<typeof r, { kind: "deny" }> => r.kind === "deny")
  .map((r) => new RegExp(r.pattern.source, r.pattern.flags));

/**
 * noticeFlagsFromRules — run every classify rule over `text` and OR each match into the flag it `sets`.
 * Byte-identical to the legacy 4-regex pass: the 4 rules carry the exact same {source,flags} as the
 * original RE_* constants, and OR-ing per-flag reproduces the original 4 independent `.test()` calls
 * (a notice titled both extension and reopening sets both, exactly as before).
 *
 * NOTE: the DENY rules are deliberately NOT applied here. The deny-list is scoped to the chain engine
 * (isKeywordFalsePositive) exactly as today — folding it into the notice-flag pass would CHANGE behavior
 * (it would newly suppress is_withdrawal on a land-withdrawal title at the source adapter level).
 */
export function noticeFlagsFromRules(text: string): NoticeFlags {
  const flags: NoticeFlags = {
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
  };
  for (const rule of CLASSIFY_RULES) {
    if (rule.re.test(text)) {
      // map the bare NoticeFlagKey → the is_<key> boolean (the contract's documented mapping).
      flags[`is_${rule.sets}` as keyof NoticeFlags] = true;
    }
  }
  return flags;
}

/**
 * isDenied — true if ANY deny rule matches the haystack. Byte-identical to the legacy
 * DENY_PATTERNS.some((re) => re.test(haystack)). The caller (chain.ts isKeywordFalsePositive) builds the
 * haystack ([title, dates_text].filter(Boolean).join(" ")) exactly as before; the patterns and their
 * order are carried verbatim from DENY_PATTERNS into the rulebook.
 */
export function isDenied(haystack: string): boolean {
  return DENY_RULES.some((re) => re.test(haystack));
}
