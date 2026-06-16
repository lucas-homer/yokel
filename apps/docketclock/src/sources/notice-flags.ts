/**
 * Notice-type flag detection — a minimal keyword pass over a notice's title/type/action text, shared by
 * the FR and Regs.gov adapters so the keyword set AND the documented false-positive caveat live in ONE
 * place. Kept deliberately simple; the real classifier (RuleBox deny-list + Haiku escalation) lands later.
 */
const RE_EXTENSION = /\bextension\b|\bextend(?:ed|ing)?\b|\breopen/i;
const RE_CORRECTION = /\bcorrection\b|\bcorrect(?:ed|ing)?\b/i;
const RE_WITHDRAWAL = /\bwithdraw(?:al|n|ing)?\b/i;

export interface NoticeFlags {
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
}

// TODO(rulebox): route these flags through the RuleBox deny-list before trusting them. The BLM
// 2023-27468 "land-withdrawal extension" title is a keyword false-positive (a land withdrawal, NOT a
// comment-period extension/withdrawal) and must be suppressed here; genuinely-ambiguous titles escalate
// to a single Haiku call, not the hot path (docs/architecture/docketclock.md).
export function noticeFlags(text: string): NoticeFlags {
  return {
    is_extension: RE_EXTENSION.test(text),
    is_correction: RE_CORRECTION.test(text),
    is_withdrawal: RE_WITHDRAWAL.test(text),
  };
}
