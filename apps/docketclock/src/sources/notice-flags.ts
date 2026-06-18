/**
 * Notice-type flag detection — a minimal keyword pass over a notice's title/type/action text, shared by
 * the FR and Regs.gov adapters so the keyword set lives in ONE place. The 4 keyword patterns now live as
 * DATA in the versioned RuleBox (src/rulebox/rulebook.ts, validated at load) and run through the single
 * deterministic evaluator; this module is a thin, signature-stable delegator so every caller (FR/Regs
 * adapters, backfill) is untouched. The DENY-list (the BLM 2023-27468 land-withdrawal false-positive
 * guard) is NOT applied here — it stays scoped to the chain engine exactly as before (applying it here
 * would change behavior). What is still deferred is the LLM/Gemini ambiguous-tail escalation (the
 * deterministic RuleBox itself has landed); see docs/architecture/docketclock.md.
 *
 * O4 (the clean split): a REOPENING is its own flag, NOT folded into extension. An EXTENSION moves a
 * still-open deadline later (continuous); a REOPENING re-opens an ALREADY-CLOSED comment period (a gap —
 * a fresh reliance window) — distinct legal events. A reopening sets is_reopening (NOT is_extension),
 * else the chain engine mislabels it `extension_chain_unresolved`; a notice titled both fires both flags.
 */
import { noticeFlagsFromRules } from "../rulebox/index.js";

export interface NoticeFlags {
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
}

export function noticeFlags(text: string): NoticeFlags {
  return noticeFlagsFromRules(text);
}
