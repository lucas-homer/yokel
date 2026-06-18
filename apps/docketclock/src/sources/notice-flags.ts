/**
 * Notice-type flag detection — a minimal keyword pass over a notice's title/type/action text, shared by
 * the FR and Regs.gov adapters so the keyword set AND the documented false-positive caveat live in ONE
 * place. Kept deliberately simple; the real classifier (RuleBox deny-list + Haiku escalation) lands later.
 */
// O4 (the clean split): `reopen…` moved OUT of RE_EXTENSION into its own RE_REOPENING. An EXTENSION moves
// a still-open deadline later (continuous); a REOPENING re-opens an ALREADY-CLOSED comment period (a gap —
// a fresh reliance window). They are distinct legal events, so a reopening must set is_reopening (NOT
// is_extension) — otherwise the chain engine mislabels it `extension_chain_unresolved`. The two are
// mutually exclusive in vocabulary but a single notice CAN be titled both ("Extension and Reopening…"),
// in which case both flags fire honestly.
const RE_EXTENSION = /\bextension\b|\bextend(?:ed|ing)?\b/i;
const RE_CORRECTION = /\bcorrection\b|\bcorrect(?:ed|ing)?\b/i;
const RE_WITHDRAWAL = /\bwithdraw(?:al|n|ing)?\b/i;
const RE_REOPENING = /\breopen(?:ed|ing|s)?\b/i;

export interface NoticeFlags {
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
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
    is_reopening: RE_REOPENING.test(text),
  };
}
