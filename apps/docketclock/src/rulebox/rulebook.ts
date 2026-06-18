/**
 * rulebook.ts — the DocketClock keyword RuleBox as DATA (rules-as-data), the single home for the two
 * regex stopgaps that used to live inline in two files:
 *   • the 4 CLASSIFY rules ⇐ src/sources/notice-flags.ts (one per notice flag → is_extension /
 *     is_correction / is_withdrawal / is_reopening), and
 *   • the 5 DENY rules     ⇐ src/reconcile/chain.ts DENY_PATTERNS (the BLM 2023-27468 land-withdrawal
 *     keyword-false-positive trap — these mark an amendment candidate's signal a false positive so it is
 *     never linked).
 *
 * The literal below is validated by RuleBox.parse() at MODULE LOAD (fail-fast: an un-compilable regex
 * source or illegal flag, or a duplicate rule id, throws ZodError before the app serves a request). The
 * compiled RegExp objects are built ONCE in the evaluator (index.ts), not per call.
 *
 * Every rationale is carried VERBATIM from the original inline comments — this is institutional knowledge
 * (the BLM 2023-27468 trap, the 3 real D3 spike titles) and must not be lost in the data migration.
 *
 * The deterministic RuleBox is HERE now (it replaces both stopgaps). What is STILL deferred is the
 * LLM/Gemini AMBIGUOUS-tail adjudicator (a provider-agnostic port, consulted for <5% of records, never
 * touching confidence or deadline resolution) — the `ambiguous` ClassifyRule marker reserves that future
 * escalation hook but carries NO LLM payload in this slice.
 */
import { RuleBox } from "@yokel/contracts";

/**
 * The rulebook version is the RULEBOOK's OWN version (independent of the @yokel/contracts package
 * version); it is stamped into verdict provenance in a later slice, so keep it human-meaningful.
 */
export const RULEBOOK_VERSION = "rulebox-2026-06-18";

/**
 * ruleBox — the loaded, VALIDATED rulebook. RuleBox.parse throws at module load on any malformed rule, so
 * a successful import guarantees every pattern compiles and every id is unique. Frozen for callers.
 */
export const ruleBox: RuleBox = RuleBox.parse({
  version: RULEBOOK_VERSION,
  rules: [
    // ── CLASSIFY rules ⇐ notice-flags.ts (one rule per notice flag) ────────────────────────────────
    // O4 (the clean split): `reopen…` lives in its OWN rule (sets `reopening`), NOT folded into the
    // extension rule. An EXTENSION moves a still-open deadline later (continuous); a REOPENING re-opens
    // an ALREADY-CLOSED comment period (a gap — a fresh reliance window). They are distinct legal events,
    // so a reopening must set is_reopening (NOT is_extension); a notice titled both fires both honestly.
    {
      kind: "classify",
      id: "extension",
      pattern: {
        source: "\\bextension\\b|\\bextend(?:ed|ing)?\\b",
        flags: "i",
      },
      sets: "extension",
      rationale:
        "Comment-period EXTENSION: moves a still-open deadline later (continuous). Matches 'extension' / 'extend(ed|ing)'. Reopen… is deliberately a SEPARATE rule (O4 split) so a reopening does not falsely set is_extension.",
    },
    {
      kind: "classify",
      id: "correction",
      pattern: {
        source: "\\bcorrection\\b|\\bcorrect(?:ed|ing)?\\b",
        flags: "i",
      },
      sets: "correction",
      rationale: "CORRECTION notice. Matches 'correction' / 'correct(ed|ing)'.",
    },
    {
      kind: "classify",
      id: "withdrawal",
      pattern: { source: "\\bwithdraw(?:al|n|ing)?\\b", flags: "i" },
      sets: "withdrawal",
      rationale:
        "WITHDRAWAL of a notice. Matches 'withdraw(al|n|ing)'. NOTE: a public-lands 'land withdrawal' also trips this keyword — that false positive is suppressed downstream by the DENY rules (BLM 2023-27468 trap), which are scoped to the chain engine, NOT to this notice-flag pass.",
    },
    {
      kind: "classify",
      id: "reopening",
      pattern: { source: "\\breopen(?:ed|ing|s)?\\b", flags: "i" },
      sets: "reopening",
      rationale:
        "REOPENING: a previously-CLOSED comment period re-opened (a gap + fresh reliance window) — distinct from an extension (O4). Matches 'reopen(ed|ing|s)'.",
    },

    // ── DENY rules ⇐ chain.ts DENY_PATTERNS (the BLM 2023-27468 land-withdrawal keyword-false-positive
    // trap). The headline trap: a 'land withdrawal' (a public-lands action) trips is_withdrawal/
    // is_extension even though it is NOT a comment-period action. Real BLM/USFS land-withdrawal notices
    // carry `dates: None` (null DATES text) and put the withdrawal SIGNAL in the TITLE — so the chain
    // engine's haystack is BOTH title and DATES text. Each pattern targets the land-withdrawal LEGAL
    // VEHICLE, not a bare incidental word — verified to match the 3 real D3 spike titles (Public Land
    // Order No. 7963; Flathead National Forest … Withdrawal; White River National Forest … Camp Hale …
    // Withdrawal) WITHOUT eating genuine comment-period notices. Do NOT add bare /\bland\b/ or
    // /\bnational forest\b/ alone — every pattern must require the withdrawal/land-order vehicle. ──────
    {
      kind: "deny",
      id: "public-land-order",
      pattern: { source: "\\bpublic\\s+lands?\\s+orders?\\b", flags: "i" },
      rationale:
        "Public Land Order / Public Lands Order — the PLO vehicle (matches the '…Public Land Order No. 7963…' title).",
    },
    {
      kind: "deny",
      id: "land-withdrawal-phrase",
      pattern: { source: "\\bland[\\s-]?withdrawal\\b", flags: "i" },
      rationale:
        "'land withdrawal' as one phrase (the BLM 2023-27468 headline trap).",
    },
    {
      kind: "deny",
      id: "withdraw-of-lands",
      pattern: {
        source:
          "\\bwithdraw(?:al\\s+of|s|ing)?\\s+(?:(?:certain|public|national|forest|system)\\s+)*lands?\\b",
        flags: "i",
      },
      rationale:
        "withdrawal of … land(s) / withdraws lands / withdrawing public land. Allow STACKED qualifiers ('certain public land', 'national forest system lands') via a repeatable qualifier group.",
    },
    {
      kind: "deny",
      id: "national-forest-withdrawal",
      pattern: {
        source:
          "\\bnational\\s+forest\\b[^.]*\\bwithdrawal\\b|\\bwithdrawal\\b[^.]*\\bnational\\s+forest\\b",
        flags: "i",
      },
      rationale:
        "National Forest … Withdrawal in EITHER order (Flathead/Camp Hale '…National Forest…; Withdrawal' titles).",
    },
    {
      kind: "deny",
      id: "notice-of-withdrawal",
      pattern: {
        source: "\\bnotice\\s+of\\s+(?:proposed\\s+)?withdrawal\\b",
        flags: "i",
      },
      rationale:
        "Notice of (proposed) Withdrawal — the BLM withdrawal-notice vehicle.",
    },
  ],
});
