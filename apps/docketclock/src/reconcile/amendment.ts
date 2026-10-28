/**
 * amendment.ts — the PURE amendment close resolver (FR amendment linking; ADR 0016,
 * docs/plans/fr-amendment-linking.md part 4). No DB, no clock.
 *
 * THE GAP IT CLOSES. Every window's FR side comes from its OWN latest federal_register observation. An
 * extension or correction is a SEPARATE FR document with its own ocd_id, so the chain pass could link it
 * (a cross_window ConflictRecord) but nothing ever fed its new date back into the original's derivation:
 * window A kept the superseded FR close forever and sat CONFLICTING against a portal that had already
 * moved (Census 2026-18481, USDA 2026-18531, IRS 2026-18574).
 *
 * THE RULE (conservative by construction — "don't publish fake certainty"): only a DETERMINISTICALLY
 * linked amendment (linkBasis; an LLM-only link is never evidence) whose new close is STATED in text we
 * hold and VERIFIED by the predicates below may move A's FR side. Everything else is `none` or
 * `ambiguous`, and both leave A byte-identical to what it was before this module existed — the
 * cross_window conflict stays visible either way. Reopenings and withdrawals never move a date. FR's own
 * `comments_close_on` on an amendment is NOT trusted on its face (USDA 2026-19710 says 2026-09-11 — A's
 * publication date), and FR's `dates` field can be truncated, so the published GovInfo text is preferred.
 *
 * Each rule is a named, exported predicate so it is tested on its own.
 */
import type { LinkBasis } from "./chain.js";

/** One deterministically linked amendment B of an original A — everything the resolver may read. */
export interface AmendmentEvidence {
  ocd_id: string;
  fr_document_number: string;
  fr_observation_id: string;
  govinfo_observation_id: string | null;
  publication_date: string; // B's FR publication_date
  is_extension: boolean;
  is_correction: boolean;
  is_reopening: boolean;
  is_withdrawal: boolean;
  fr_comments_close_on: string | null; // B's own FR value, validated calendar date or null
  fr_dates_text: string | null; // B's FR JSON `dates` (may be truncated)
  govinfo_text: string | null; // B's govinfo raw_dates_text (DATES section / correction body)
  basis: LinkBasis; // deterministic only — LLM-only links are never evidence
  /**
   * When B's FR / govinfo observations were FETCHED (ISO). The freshness rule for a human verdict on A
   * compares them with the verdict's fetched_at (ADR 0016 §7). Optional so evidence built by hand reads
   * as "unknown" — which the rule treats as newer than any verdict (the conservative direction).
   */
  fr_fetched_at?: string | null;
  govinfo_fetched_at?: string | null;
}

export type AmendmentOutcome =
  | { kind: "none" }
  | {
      kind: "amended";
      date: string /* YYYY-MM-DD Eastern */;
      amendment: AmendmentEvidence;
      change: "extension" | "correction";
      observation_ids: string[];
      /**
       * Non-fatal notes behind an amended outcome — e.g. B's own FR comments_close_on ignored as an FR
       * extraction error. Present only when non-empty (an outcome with nothing to note has no key).
       */
      reasons?: string[];
    }
  | { kind: "ambiguous"; reasons: string[] };

/** The original window A as the resolver sees it (its own latest FR observation). */
export interface AmendmentOriginal {
  fr_close: string | null;
  publication_date: string | null;
  fr_document_number: string | null;
}

// ── dates ───────────────────────────────────────────────────────────────────────────────────────────

const MONTHS: Record<string, number> = {
  january: 1,
  february: 2,
  march: 3,
  april: 4,
  may: 5,
  june: 6,
  july: 7,
  august: 8,
  september: 9,
  october: 10,
  november: 11,
  december: 12,
  jan: 1,
  feb: 2,
  mar: 3,
  apr: 4,
  jun: 6,
  jul: 7,
  aug: 8,
  sep: 9,
  sept: 9,
  oct: 10,
  nov: 11,
  dec: 12,
};

/**
 * A "Month D, YYYY" date (full month names, plus the usual abbreviations with an optional period — so an
 * abbreviated SECOND date can never hide from the "two dates ⇒ ambiguous" rule). Recognizing MORE forms
 * only ever makes the resolver more ambiguous, never more confident.
 */
const DATE_SRC =
  "(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\\.?\\s+(\\d{1,2}),?\\s+(\\d{4})";

/** "YYYY-MM-DD" when (month, day, year) is a REAL calendar date (round-trip — no 2026-02-30 rollover). */
function isoDate(month: string, day: string, year: string): string | null {
  const m = MONTHS[month.toLowerCase()];
  if (!m) return null;
  const y = Number(year);
  const d = Number(day);
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (
    dt.getUTCFullYear() !== y ||
    dt.getUTCMonth() !== m - 1 ||
    dt.getUTCDate() !== d
  )
    return null;
  return `${year}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

/** Parse a string that IS a date ("October 26, 2026", optional trailing . or ,) → "YYYY-MM-DD" | null. */
export function parseLongDate(s: string): string | null {
  const m = new RegExp(`^\\s*${DATE_SRC}\\s*[.,]?\\s*$`, "i").exec(s);
  return m ? isoDate(m[1]!, m[2]!, m[3]!) : null;
}

/** A real "YYYY-MM-DD" calendar date, else null. */
export function validCalendarDate(s: string | null | undefined): string | null {
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return dt.getUTCFullYear() === y &&
    dt.getUTCMonth() === mo - 1 &&
    dt.getUTCDate() === d
    ? s
    : null;
}

/**
 * The deadline phrases whose date is a comment close. A date counts only when one of these IMMEDIATELY
 * precedes it — and (resolver rule, ADR 0016 round-1 review) only inside a COMMENT clause; every other
 * date in the text (a meeting, a publication, a hearing) is ignored here.
 */
const DEADLINE_PHRASES = [
  "on or before",
  "on or by",
  "no later than",
  "(?:(?:extended|reopened)\\s+)?(?:to|until|through)",
  "must be (?:received|submitted|postmarked) (?:by|on or before|on or by|no later than)",
  "(?:closes?|ends?) on",
];
const DEADLINE_RE = new RegExp(
  `\\b(?:${DEADLINE_PHRASES.join("|")})\\s+${DATE_SRC}`,
  "gi",
);
const ANY_DATE_RE = new RegExp(DATE_SRC, "gi");

/**
 * A date is excluded from the deadline reading ONLY by explicit HISTORICAL grammar that marks it as a
 * citation or a past / replaced close — never by its VALUE (round 3), and never by a loose keyword nearby
 * (round 4: "The electronic comment docket will be closed on October 16", "Previously submitted
 * comments must be resubmitted by October 16", "As originally announced, electronic comments remain due
 * October 16" and "Electronic comments must be dated October 16" are all LIVE deadlines). The grammar,
 * read from the text right before the date (and, for the replaced-due-date form, right after it):
 *   • a citation: "published (in the Federal Register (FR)) (at 91 FR N) (on|of) (D)";
 *   • a signature line: "Dated: D" at the START of a sentence, or "dated D" continuing a "published …"
 *     citation in the same sentence;
 *   • "(originally|previously) (published|scheduled|set|announced|established) (to close|end|expire)
 *     (on|for) D" — the keyword DIRECTLY governs the date;
 *   • "(was|were|had been) (scheduled|set|due|expected) to (close|end|expire) (on) D" (present perfect counts),
 *     "would have (closed|ended|expired) (on) D";
 *   • past-tense "closed / ended / expired (on) D" only with the comment period as its subject ("the
 *     (original) comment period (that|which) closed on D") — "will be closed on D" is live;
 *   • "extend(s|ed|ing) (the comment period) from D", and "the D due date … is extended".
 * When in doubt the date COUNTS — over-detection can only add ambiguity.
 */
const PAST_OR_CITED_BEFORE = [
  /\bpublished(?:\s+(?:in\s+the\s+Federal\s+Register(?:\s+\(FR\))?|on|at|of|\d+\s+FR\s+\d+,?))*\s*\(?\s*$/i,
  /(?:^|[.!?;]\s+)Dated:\s*$/,
  // "dated D" continuing a citation of the published document in the same sentence: "originally published
  // on September 11, 2026, dated September 10, 2026" / "Published on …; dated …". A bare "must be dated D"
  // is a live requirement and counts.
  /\bpublished\b[^.!?]*?[,;]\s*dated\s*$/i,
  /\b(?:originally|previously)\s+(?:published|scheduled|set|announced|established)(?:\s+to\s+(?:close|end|expire))?(?:\s+(?:on|for))?\s*$/i,
  // Simple past / pluperfect only. Present perfect ("has/have been scheduled to close on D") can describe
  // the CURRENT schedule — a live competing deadline — so it counts (adversary round 5).
  /\b(?:was|were|had\s+been)\s+(?:scheduled|set|due|expected)\s+to\s+(?:close|end|expire)(?:\s+on)?\s*$/i,
  /\bwould\s+have\s+(?:closed|ended|expired)(?:\s+on)?\s*$/i,
  /\bcomment\s+period\s+(?:that\s+|which\s+)?(?:closed|ended|expired)(?:\s+on)?\s*$/i,
  /\bextend(?:s|ed|ing)?(?:\s+the\s+(?:comment\s+period|deadline))?\s+from\s*$/i,
];

/**
 * The date the sentence itself says is being REPLACED: "The August 21, 2026, due date for comments … is
 * extended" — the date is followed (same clause) by the deadline it names and that deadline "is / has
 * been extended".
 */
const REPLACED_AFTER_RE =
  /^\s*,?\s*(?:comment\s+)?(?:due\s+date|deadline|closing\s+date|close\s+date)\b[^.;]*?\b(?:is|are|was|were|has\s+been|have\s+been)\s+(?:being\s+)?extended\b/i;

function isPastOrCitedDate(textBefore: string, textAfter: string): boolean {
  return (
    PAST_OR_CITED_BEFORE.some((re) => re.test(textBefore)) ||
    REPLACED_AFTER_RE.test(textAfter)
  );
}

/**
 * Every DISTINCT date that appears in a deadline phrase, in first-seen order ("YYYY-MM-DD"). A date whose
 * context marks it as a citation or a past / replaced close (isPastOrCitedDate) is skipped.
 * Context-free: the raw phrase extractor. The resolver applies it per COMMENT clause (commentDeadlines).
 */
export function deadlineDates(text: string | null | undefined): string[] {
  if (!text) return [];
  const t = text.replace(/\s+/g, " ");
  const out: string[] = [];
  for (const m of t.matchAll(DEADLINE_RE)) {
    const dateAt = m.index! + m[0].length - matchedDateLength(m);
    if (isPastOrCitedDate(t.slice(0, dateAt), t.slice(m.index! + m[0].length)))
      continue;
    const d = isoDate(m[1]!, m[2]!, m[3]!);
    if (d && !out.includes(d)) out.push(d);
  }
  return out;
}

/** Length of the trailing date inside a DEADLINE_RE match (the part after the phrase). */
function matchedDateLength(m: RegExpMatchArray): number {
  const tail = new RegExp(`${DATE_SRC}$`, "i").exec(m[0]);
  return tail ? tail[0].length : 0;
}

// ── clause roles ────────────────────────────────────────────────────────────────────────────────────

/** A clause about comments / the comment period. */
const COMMENT_RE = /\bcomment(?:s|ed|er|ers|ing)?\b/i;
/**
 * A clause about something that is NOT the comment deadline: a hearing, meeting or registration, a
 * request to speak / for a hearing, an effective date. Real cases: EPA 2026-20982 ("requesting a public
 * hearing on or before October 19"), IRS 2026-18574 ("Requests to speak and outlines … must be received
 * by October 13"), the reviewer's "Public hearings will run November 18 through November 20".
 */
const NON_COMMENT_RE =
  /\b(?:hearings?|meetings?|meets?|(?<!Federal\s)register|registering|registration|request(?:s|ing|ed)?\s+(?:to\s+(?:speak|present|appear|testify)|(?:a|for)\s+(?:a\s+)?(?:public\s+|virtual\s+)?hearing)|speakers?|testify|testimony|attend|attendance|webinars?|workshops?|listening\s+sessions?|conference|outlines?|effective)\b/i;

/**
 * A clause about comments on an INFORMATION COLLECTION (the Paperwork Reduction Act stream, sent to OMB
 * on its own clock — ICE 2026-20660, Interior 2026-14450, and ~20 SEC-style "Comments on the collection
 * of information are due …" lines in the 717-page corpus). Its dates are comment dates (they feed the
 * second-deadline guard) but never the rule's close (never a candidate): such a clause is UNRESOLVED.
 */
const COLLECTION_RE =
  /\b(?:information\s+collection|collections?\s+of\s+information|paperwork\s+reduction|OMB)\b/i;

/**
 * comment — about comments / the comment period (a candidate source);
 * unresolved — comments mixed with another role, or an information-collection (PRA) comment clause:
 *   its dates are competing comment dates, never candidates;
 * noncomment — an ESTABLISHED other role (hearing, meeting, registration, request to speak, effective
 *   date …): its dates are excluded entirely;
 * neutral — no role words at all ("Therefore, they should be submitted … by September 15"): its role is
 *   NOT established, so its dates still count against the candidate (round-2 finding 3).
 */
export type ClauseRole = "comment" | "unresolved" | "noncomment" | "neutral";

/**
 * Split text into SENTENCES (a period / ! / ? — optionally after closing quotes — followed by space and
 * an upper-case letter, a digit-dot list marker or an opening parenthesis/quote). A sentence that mixes
 * comment and non-comment vocabulary is split further at ";" so "comments by Nov 2; the hearing runs
 * Nov 18 through Nov 20" separates; a ";" clause inherits its sentence's comment context unless it has
 * non-comment vocabulary of its own.
 */
export function deadlineClauses(
  text: string,
): { text: string; role: ClauseRole }[] {
  const t = text.replace(/\s+/g, " ").trim();
  if (!t) return [];
  const sentences = t.split(
    /(?<=[.!?](?:''|”|")?)\s+(?=(?:\d+\.\s+)?[A-Z(“"`])/,
  );
  const out: { text: string; role: ClauseRole }[] = [];
  for (const sentence of sentences) {
    const comment = COMMENT_RE.test(sentence);
    const nonComment = NON_COMMENT_RE.test(sentence);
    if (!comment) {
      out.push({ text: sentence, role: nonComment ? "noncomment" : "neutral" });
      continue;
    }
    if (!nonComment) {
      out.push({
        text: sentence,
        role: COLLECTION_RE.test(sentence) ? "unresolved" : "comment",
      });
      continue;
    }
    // Mixed sentence: decide clause by clause.
    for (const clause of sentence.split(/;\s*/)) {
      const c = COMMENT_RE.test(clause);
      const n = NON_COMMENT_RE.test(clause);
      out.push({
        text: clause,
        // A clause with only non-comment vocabulary is about that event; one with both is unresolved; a
        // bare clause inherits the sentence's mixed context and stays unresolved (never a candidate).
        role: n
          ? c
            ? "unresolved"
            : "noncomment"
          : c && !COLLECTION_RE.test(clause)
            ? "comment"
            : "unresolved",
      });
    }
  }
  return out;
}

/** Every date in a text whose context does not mark it as a citation or a past / replaced close. */
function nonCitedDates(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(ANY_DATE_RE)) {
    if (
      isPastOrCitedDate(
        text.slice(0, m.index!),
        text.slice(m.index! + m[0].length),
      )
    )
      continue;
    const d = isoDate(m[1]!, m[2]!, m[3]!);
    if (d && !out.includes(d)) out.push(d);
  }
  return out;
}

export interface DeadlineReading {
  /** distinct deadline-phrase dates found in COMMENT clauses — the close candidates. */
  candidates: string[];
  /** every other date in comment or unresolved clauses that could be a second comment deadline. */
  others: string[];
}

/**
 * Read a DATES text for the comment close (round-1 review, findings 2–3):
 *   • CANDIDATES — deadline-phrase dates inside COMMENT clauses only (a hearing / meeting / registration /
 *     request-to-speak / effective-date clause never supplies one; a clause whose role is unresolved
 *     never supplies one either);
 *   • OTHERS — the independent guard: EVERY date in any clause whose non-comment role is not
 *     ESTABLISHED (comment, unresolved and neutral clauses — round 2: "Therefore, they should be
 *     submitted to the Service by September 15" names no role at all), whatever phrase introduces it
 *     ("comments should be submitted to the Service by September 15" has none we recognize). The only
 *     exclusions: explicitly hearing / meeting / registration / effective-date clauses (noncomment) and
 *     dates whose TEXT marks them as a citation or a past / replaced close (isPastOrCitedDate) — never
 *     a date's value (round 3). Any OTHER date that differs from the single candidate makes the
 *     reading ambiguous — over-detection only ever adds ambiguity, never confidence.
 */
export function commentDeadlines(
  text: string | null | undefined,
): DeadlineReading {
  const candidates: string[] = [];
  const others: string[] = [];
  if (!text) return { candidates, others };
  for (const c of deadlineClauses(text)) {
    if (c.role === "noncomment") continue;
    if (c.role === "comment")
      for (const d of deadlineDates(c.text))
        if (!candidates.includes(d)) candidates.push(d);
    for (const d of nonCitedDates(c.text))
      if (!others.includes(d)) others.push(d);
  }
  return {
    candidates,
    others: others.filter((d) => !candidates.includes(d)),
  };
}

/**
 * The correction instructions ``X'' should read ``Y'' (GPO doubled backticks/apostrophes; straight and
 * curly double quotes accepted too) — every (X, Y) pair, verbatim.
 */
const SHOULD_READ_RE =
  /(?:``|"|“)\s*([^`'"”“]+?)\s*(?:''|"|”)\s*,?\s+should\s+read\s+(?:``|"|“)\s*([^`'"”“]+?)\s*(?:''|"|”)/gi;

export function shouldReadPairs(
  text: string | null | undefined,
): { from: string; to: string }[] {
  return shouldReadInstructions(text).map(({ from, to }) => ({ from, to }));
}

/**
 * The GPO correction HEADER, stripped before the allowlist is applied (it is structure, not a qualifier):
 * "In [proposed rule|rule|notice|presidential] document <docnum> beginning on page <N> [in the issue of
 * <Weekday>, <Month D, YYYY>,] make the following correction(s):".
 */
const GPO_CORRECTION_HEADER_RE = new RegExp(
  `^\\s*In\\s+(?:(?:proposed\\s+rule|rule|notice|presidential)\\s+)?document\\s+\\S+\\s+beginning\\s+on\\s+page\\s+[\\w-]+,?(?:\\s+in\\s+the\\s+issue\\s+of\\s+\\w+,\\s+${DATE_SRC},?)?\\s*(?:make\\s+the\\s+following\\s+corrections?)?\\s*:?\\s*`,
  "i",
);

/**
 * The CLOSED-WORLD allowlist for a correction instruction's own sentence (round 3, finding 3 — the third
 * round of vocabulary escapes, so no blocklist): once the quoted strings and the GPO header are removed,
 * EVERY remaining word must be
 *   (a) location vocabulary — page / column / line / paragraph / section / heading / DATES, ordinals,
 *       numbers (and document numbers), top / bottom / from …;
 *   (b) explicit comment-period vocabulary — comment(s), comment period, deadline, date, close, must be
 *       received / submitted …;
 *   (c) connective / correction boilerplate — in, of, the, and, should read, make the following
 *       correction …
 * Any other word ("public symposium", "oral presentations", "public inspection", "petitions for
 * reconsideration", "hearing", "effective" …) is a qualifier we do not understand: the instruction binds
 * nothing (`none`). The real IRS C1-2026-18574 sentence binds.
 */
const CORRECTION_ALLOWED = new Set([
  // (a) location
  "on",
  "page",
  "pages",
  "column",
  "columns",
  "line",
  "lines",
  "paragraph",
  "paragraphs",
  "section",
  "sections",
  "heading",
  "caption",
  "dates",
  "under",
  "top",
  "bottom",
  "from",
  "last",
  "first",
  "second",
  "third",
  "fourth",
  "fifth",
  "sixth",
  "seventh",
  "eighth",
  "ninth",
  "tenth",
  "eleventh",
  "twelfth",
  "thirteenth",
  "fourteenth",
  "fifteenth",
  "sixteenth",
  "seventeenth",
  "eighteenth",
  "nineteenth",
  "twentieth",
  "st",
  "nd",
  "rd",
  "th",
  // (b) comment period
  "comment",
  "comments",
  "period",
  "deadline",
  "date",
  "close",
  "closing",
  "received",
  "receive",
  "submitted",
  "which",
  "submit",
  "must",
  "be",
  "by",
  // (c) connective / correction boilerplate
  "in",
  "of",
  "the",
  "and",
  "a",
  "an",
  "to",
  "at",
  "is",
  "are",
  "for",
  "should",
  "read",
  "reads",
  "make",
  "following",
  "correction",
  "corrections",
  "corrected",
  "as",
  "follows",
  "same",
]);

/**
 * The words of an instruction sentence that are NOT on the allowlist. Removed first, and nothing else:
 *   • the GPO correction header (structure);
 *   • the should-read OPERANDS themselves — the quoted X and Y of each pair (round 4: every OTHER quoted
 *     text is read like any word, so 'for the "public hearing"' is a qualifier);
 *   • numbers inside strict structural forms only (round 4): "page N" / "pages N and N", "[[Page N]]",
 *     "column N" / "line N" / "paragraph N", an ordinal "Nth line|column|paragraph", "paragraph (x)",
 *     "N FR N".
 * Any other digit-bearing token ("Form-1", "PM2.5", "PM2-5") is itself a qualifier.
 */
export function correctionQualifiers(sentence: string): string[] {
  const body = sentence
    .replace(/\s+/g, " ")
    .replace(GPO_CORRECTION_HEADER_RE, " ")
    .replace(new RegExp(SHOULD_READ_RE.source, "gi"), " should read ")
    .replace(/\[\[\s*Page\s+\d+\s*\]\]/gi, " ")
    .replace(/\bpages?\s+\d+(?:\s*(?:,|and|-|–|through)\s*\d+)*\b/gi, " page ")
    .replace(/\b(?:column|line|paragraph)s?\s+\d+\b/gi, " line ")
    .replace(/\b\d+(?:st|nd|rd|th)\s+(?=(?:line|column|paragraph)s?\b)/gi, " ")
    .replace(/\bparagraphs?\s+\([a-z0-9]+\)/gi, " paragraph ")
    .replace(/\b\d+\s+FR\s+\d+\b/g, " ");
  return (body.match(/[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]|[A-Za-z0-9]/g) ?? [])
    .map((w) => w.toLowerCase())
    .filter((w) => !CORRECTION_ALLOWED.has(w));
}

/**
 * Every ``X'' should read ``Y'' pair with the SENTENCE that carries it (its instruction). A sentence ends
 * at a period / ! / ? (optionally after closing quotes) followed by a space and a capital, a list
 * marker ("2.") or an opening quote/parenthesis; a ";" does NOT end it, so "In DATES, ``A'' should read
 * ``B''; ``C'' should read ``D''" is one instruction with two pairs.
 */
function shouldReadInstructions(
  text: string | null | undefined,
): { from: string; to: string; sentence: string }[] {
  if (!text) return [];
  const t = text.replace(/\s+/g, " ");
  const bounds: number[] = [0];
  for (const m of t.matchAll(
    /(?<=[.!?](?:''|”|")?)\s+(?=(?:\d+\.\s+)?[A-Z(“"`])/g,
  ))
    bounds.push(m.index!);
  bounds.push(t.length);
  return [...t.matchAll(SHOULD_READ_RE)].map((m) => {
    const at = m.index!;
    let lo = 0;
    let hi = t.length;
    for (const b of bounds) {
      if (b <= at) lo = b;
      else {
        hi = b;
        break;
      }
    }
    // The pair itself may contain a sentence-ending period inside its quotes ("…, 2026.''"); extend the
    // sentence to cover the whole match.
    hi = Math.max(hi, at + m[0].length);
    return { from: m[1]!, to: m[2]!, sentence: t.slice(lo, hi) };
  });
}

// ── the per-amendment predicates ────────────────────────────────────────────────────────────────────

/** Rule 1: a reopening or a withdrawal is never a close change (O4: a post-lapse reopening is its own legal event). */
export function isNonMovingAmendment(e: AmendmentEvidence): boolean {
  return e.is_reopening || e.is_withdrawal;
}

/** A per-amendment verdict: no date from this one, a candidate date, or a reason it is unsafe. */
type Single =
  | { kind: "none"; reasons: string[] }
  | {
      kind: "date";
      date: string;
      change: "extension" | "correction";
      usedGovinfo: boolean;
      reasons: string[];
    }
  | { kind: "ambiguous"; reasons: string[] };

/**
 * Post-lapse guard: an amendment published AFTER the close it would extend is a reopening in substance
 * (a fresh reliance window after a gap — O4), never a continuous move of a still-open deadline. The
 * close is the EFFECTIVE one at that point of the chain (the original's, or the latest verified
 * extension's — round-1 finding 5).
 */
export function publishedAfterOriginalClose(
  e: AmendmentEvidence,
  originalClose: string,
): boolean {
  return e.publication_date > originalClose;
}

/**
 * Rule 2 — CORRECTION: only the published correction text (govinfo_text) is read. A ``X'' should read
 * ``Y'' instruction whose OWN sentence places it in the DATES section (and names no other section, nor
 * an effective date), with X and Y both "Month D, YYYY" dates and X the close in force, yields Y. A
 * correction touching other text yields no date (`none`, not ambiguous); two qualifying instructions
 * naming different Ys is ambiguous. ("DATES" appearing elsewhere in the body binds nothing — round-1
 * finding 4: an effective-date correction in SUPPLEMENTARY INFORMATION must never move the close.)
 */
export function correctionClose(
  e: AmendmentEvidence,
  original: { fr_close: string },
): Single {
  const text = e.govinfo_text;
  if (!text)
    return {
      kind: "none",
      reasons: [`${e.fr_document_number}: correction without published text`],
    };
  const ys = new Set<string>();
  for (const p of shouldReadInstructions(text)) {
    // The instruction's own sentence must place it in DATES (round 1) and carry no qualifier outside the
    // closed-world allowlist (round 3): "the date for oral presentations ``October 16'' should read …"
    // corrects something we do not understand, never the comment close.
    if (
      !/\bDATES\b/.test(p.sentence) ||
      correctionQualifiers(p.sentence).length > 0
    )
      continue;
    const x = parseLongDate(p.from);
    const y = parseLongDate(p.to);
    if (x && y && x === original.fr_close && y !== x) ys.add(y);
  }
  if (ys.size === 0)
    return {
      kind: "none",
      reasons: [
        `${e.fr_document_number}: no DATES-section correction of the close ${original.fr_close}`,
      ],
    };
  if (ys.size > 1)
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: correction names several new closes (${[...ys].join(", ")})`,
      ],
    };
  return {
    kind: "date",
    date: [...ys][0]!,
    change: "correction",
    usedGovinfo: true,
    reasons: [],
  };
}

/**
 * Rule 3 — EXTENSION (is_extension && !is_reopening): read the published DATES text when we hold it;
 * otherwise the FR `dates`, but only when its date equals a valid FR comments_close_on (two FR signals,
 * since that field can be truncated). The text is read by commentDeadlines: exactly one distinct
 * comment-deadline candidate, and no OTHER comment date that differs from it (findings 2–3); none is
 * `none`; several is ambiguous (the rule + PRA comment pattern, ICE 2026-20660; Interior 2026-14450's
 * Aug 17 written comments + Sep 15 information-collection comments). The candidate must move the close in
 * force LATER, and B's own comments_close_on — when it is a plausible close (after B's publication) — must
 * agree; when it is null or not after B's publication (USDA 19710's 2026-09-11) it is an FR extraction
 * error and is ignored, noted in reasons.
 */
export function extensionClose(
  e: AmendmentEvidence,
  original: { fr_close: string; fromAmendment?: boolean },
): Single {
  const reasons: string[] = [];
  const frClose = validCalendarDate(e.fr_comments_close_on);
  const frClosePlausible = frClose !== null && frClose > e.publication_date;
  const usedGovinfo = !!e.govinfo_text;
  const text = usedGovinfo ? e.govinfo_text : e.fr_dates_text;
  const reading = commentDeadlines(text);
  const where = usedGovinfo ? "published DATES" : "FR dates";
  if (reading.candidates.length > 1)
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: several comment deadlines in ${where} text (${reading.candidates.join(", ")})`,
      ],
    };
  if (reading.candidates.length === 0)
    // A date-bearing extension whose comment date we cannot attribute (round 2, finding 4: "Comments
    // should reach the agency by November 20") is not "no date" — it may well move the close, so it
    // poisons the chain: ambiguous. Only a text with no competing date at all is `none`.
    return reading.others.length > 0
      ? {
          kind: "ambiguous",
          reasons: [
            `${e.fr_document_number}: ${where} text has comment date(s) ${reading.others.join(", ")} but no recognized deadline`,
          ],
        }
      : {
          kind: "none",
          reasons: [
            `${e.fr_document_number}: no comment deadline in ${where} text`,
          ],
        };
  const date = reading.candidates[0]!;
  if (reading.others.length > 0)
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: ${where} text has another comment date (${reading.others.join(", ")}) besides ${date}`,
      ],
    };
  if (!usedGovinfo && date !== frClose) {
    // FR `dates` alone is ONE signal; it must agree with FR comments_close_on to count.
    if (frClosePlausible)
      return {
        kind: "ambiguous",
        reasons: [
          `${e.fr_document_number}: FR dates text says ${date} but comments_close_on says ${frClose}`,
        ],
      };
    return {
      kind: "none",
      reasons: [
        `${e.fr_document_number}: FR dates text not corroborated by comments_close_on and no published text`,
      ],
    };
  }
  if (publishedAfterOriginalClose(e, original.fr_close))
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: published ${e.publication_date}, after the close in force ${original.fr_close} (a reopening in substance)`,
      ],
    };
  // The FR cross-check runs BEFORE a restatement is accepted (round 2, finding 5): a document repeating
  // Nov 2 while its own plausible comments_close_on says Nov 20 is a contradiction, not a confirmation.
  if (frClosePlausible && frClose !== date)
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: published text says ${date} but FR comments_close_on says ${frClose}`,
      ],
    };
  // A second document restating the close an EARLIER verified amendment already set confirms it — it
  // neither moves nor contradicts it (no change). Restating the ORIGINAL close stays ambiguous below:
  // an "extension" that extends nothing is not understood.
  if (original.fromAmendment && date === original.fr_close)
    return {
      kind: "none",
      reasons: [
        `${e.fr_document_number}: restates the close in force ${date} set by an earlier amendment`,
      ],
    };
  if (!(date > original.fr_close))
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: extension date ${date} does not move the close in force ${original.fr_close} later`,
      ],
    };
  if (!frClosePlausible)
    reasons.push(
      `${e.fr_document_number}: FR comments_close_on ${frClose ?? "null"} ignored (not after publication ${e.publication_date}; FR extraction error)`,
    );
  return { kind: "date", date, change: "extension", usedGovinfo, reasons };
}

/** One amendment's verdict (rules 1–3) against the close IN FORCE when it was published. */
function resolveOne(
  e: AmendmentEvidence,
  inForce: { fr_close: string; fromAmendment?: boolean },
): Single {
  if (isNonMovingAmendment(e))
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: ${e.is_withdrawal ? "withdrawal" : "reopening"} never moves a close`,
      ],
    };
  const ext = e.is_extension ? extensionClose(e, inForce) : null;
  let cor = e.is_correction ? correctionClose(e, inForce) : null;
  // A correction PUBLISHED after the close in force has the post-lapse shape too (ADR 0016: the guard
  // applies to every date-bearing amendment, not only extensions).
  if (cor?.kind === "date" && publishedAfterOriginalClose(e, inForce.fr_close))
    cor = {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: correction published ${e.publication_date}, after the close in force ${inForce.fr_close}`,
      ],
    };
  const verdicts = [ext, cor].filter((v): v is Single => v !== null);
  if (verdicts.length === 0)
    return {
      kind: "none",
      reasons: [`${e.fr_document_number}: not a date-bearing amendment`],
    };
  const amb = verdicts.filter((v) => v.kind === "ambiguous");
  if (amb.length > 0)
    return { kind: "ambiguous", reasons: amb.flatMap((v) => v.reasons) };
  const dated = verdicts.filter(
    (v): v is Extract<Single, { kind: "date" }> => v.kind === "date",
  );
  if (dated.length === 0)
    return { kind: "none", reasons: verdicts.flatMap((v) => v.reasons) };
  if (new Set(dated.map((d) => d.date)).size > 1)
    return {
      kind: "ambiguous",
      reasons: [
        `${e.fr_document_number}: extension and correction readings disagree (${dated.map((d) => d.date).join(", ")})`,
      ],
    };
  return dated[0]!;
}

/**
 * resolveAmendedClose — the original's FR close as amended by its deterministically linked amendments.
 *
 *   1. any linked reopening / withdrawal ⇒ ambiguous (never a close move);
 *   2. corrections ⇒ correctionClose; 3. extensions ⇒ extensionClose;
 *   4. CHRONOLOGICAL (round-1 finding 5): amendments are evaluated in publication order against the close
 *      IN FORCE — the original's, then each verified amendment's. Each must be published on or before the
 *      close it amends (else a gap ⇒ ambiguous) and an extension must move it later. Amendments published
 *      the same day are judged against the same close and must agree. ANY ambiguous amendment ⇒ the whole
 *      outcome is ambiguous; an amendment with no date (`none`) leaves the close in force unchanged;
 *   5. `amendment` / `change` are the LAST verified amendment's; observation_ids are every verified
 *      amendment's FR observation id, plus its govinfo observation id when that text was used, in order.
 *
 * `none` and `ambiguous` both mean "the FR side stays the original's own value" — reconcile() treats
 * them identically; the distinction is diagnostic. Deterministic: input order never matters.
 */
export function resolveAmendedClose(
  original: AmendmentOriginal,
  amendments: AmendmentEvidence[],
): AmendmentOutcome {
  if (amendments.length === 0) return { kind: "none" };
  const sorted = [...amendments].sort(
    (x, y) =>
      x.publication_date.localeCompare(y.publication_date) ||
      x.fr_document_number.localeCompare(y.fr_document_number) ||
      x.fr_observation_id.localeCompare(y.fr_observation_id),
  );

  // Rule 1 first: a reopening / withdrawal anywhere in the linked set parks the whole window.
  const nonMoving = sorted.filter(isNonMovingAmendment);
  if (nonMoving.length > 0)
    return {
      kind: "ambiguous",
      reasons: nonMoving.map(
        (e) =>
          `${e.fr_document_number}: ${e.is_withdrawal ? "withdrawal" : "reopening"} never moves a close`,
      ),
    };

  const originalClose = validCalendarDate(original.fr_close);
  if (originalClose === null) return { kind: "none" };

  const candidates = sorted.filter(
    (e) =>
      !(
        original.fr_document_number &&
        e.fr_document_number === original.fr_document_number
      ), // a document never amends itself
  );
  // Ordering (B published after A) is the LOADER's rule (loadAmendmentEvidence / chain rule 3); every
  // evidence item handed in is judged on its own terms here, so nothing is silently dropped.

  let inForce = originalClose;
  const chain: {
    e: AmendmentEvidence;
    v: Extract<Single, { kind: "date" }>;
  }[] = [];
  for (let i = 0; i < candidates.length; ) {
    const pub = candidates[i]!.publication_date;
    const sameDay: AmendmentEvidence[] = [];
    while (i < candidates.length && candidates[i]!.publication_date === pub)
      sameDay.push(candidates[i++]!);
    const dated: {
      e: AmendmentEvidence;
      v: Extract<Single, { kind: "date" }>;
    }[] = [];
    for (const e of sameDay) {
      const v = resolveOne(e, {
        fr_close: inForce,
        fromAmendment: chain.length > 0,
      });
      if (v.kind === "ambiguous")
        return { kind: "ambiguous", reasons: v.reasons };
      if (v.kind === "date") dated.push({ e, v });
    }
    if (dated.length === 0) continue;
    if (new Set(dated.map((d) => d.v.date)).size > 1)
      return {
        kind: "ambiguous",
        reasons: [
          `amendments published ${pub} disagree (${dated.map((d) => `${d.e.fr_document_number}=${d.v.date}`).join(", ")})`,
        ],
      };
    chain.push(...dated);
    inForce = dated[0]!.v.date;
  }
  if (chain.length === 0) return { kind: "none" };

  const win = chain.at(-1)!;
  const observationIds: string[] = [];
  for (const { e, v } of chain) {
    if (!observationIds.includes(e.fr_observation_id))
      observationIds.push(e.fr_observation_id);
    if (
      v.usedGovinfo &&
      e.govinfo_observation_id &&
      !observationIds.includes(e.govinfo_observation_id)
    )
      observationIds.push(e.govinfo_observation_id);
  }
  return {
    kind: "amended",
    date: win.v.date,
    amendment: win.e,
    change: win.v.change,
    observation_ids: observationIds,
    ...(win.v.reasons.length > 0 ? { reasons: win.v.reasons } : {}),
  };
}

// ── freshness against a human verdict (round-1 finding 1) ──────────────────────────────────────────

/** The inputs resolveAmendedClose ran on — what reconcile() needs to judge a verdict's freshness. */
export interface AmendmentInputs {
  original: AmendmentOriginal;
  amendments: AmendmentEvidence[];
  /**
   * The linked evidence set AS IT STOOD after each fetch time of any candidate amendment's FR or govinfo
   * row, ascending (round 2, finding 1 — the ADR 0010 way: history, not only the current rows). A state
   * applies from its `at` until the next one; before the first, there was no evidence. Linkage is
   * re-decided per state, so a document that becomes linked — or stops being one — later is a change
   * like any other. When present, the honor-the-verdict rule reads THIS, not `amendments` + fetch times.
   */
  timeline?: { at: string; amendments: AmendmentEvidence[] }[];
}

/**
 * The amendment evidence as it STOOD at `cutoffMs` (a verdict's fetched_at): an amendment whose FR
 * observation was fetched after the cutoff did not exist yet; a govinfo text fetched after it was not
 * yet known (the amendment stays, read from its FR fields). An UNKNOWN fetch time counts as after the
 * cutoff — the conservative direction: it can only make a later outcome look new.
 */
export function amendmentsAsOf(
  amendments: readonly AmendmentEvidence[],
  cutoffMs: number,
): AmendmentEvidence[] {
  const known = (iso: string | null | undefined) =>
    iso ? new Date(iso).getTime() <= cutoffMs : false;
  return amendments
    .filter((e) => known(e.fr_fetched_at))
    .map((e) =>
      e.govinfo_text !== null && !known(e.govinfo_fetched_at)
        ? {
            ...e,
            govinfo_text: null,
            govinfo_observation_id: null,
            govinfo_fetched_at: null,
          }
        : e,
    );
}

/**
 * §8 — THE STRUCTURAL BACKSTOP (round 4; the primary's decision after four rounds of wording escapes —
 * the tail of DATES phrasing is long, and a text parse alone must never move a published close). An
 * amended date may move the original window's FR side only when an INDEPENDENT signal corroborates it:
 *   (a) the window's own latest portal close (Regulations.gov commentEndDate, as an Eastern calendar
 *       date) equals it, or
 *   (b) the amendment that set it (the LAST verified one in the chain) carries its own FR
 *       comments_close_on, plausible (after that document's publication) and equal to it.
 * Otherwise the outcome is `ambiguous` (the reason recorded) and the window derives exactly as without
 * the amendment. Intermediate chain steps still pass every resolver check; only the FINAL effective date
 * needs corroboration. Pure; applied by reconcile() — the derivation — not by the resolver, which stays
 * correct on its own.
 */
export function corroborateAmendedClose(
  outcome: AmendmentOutcome | undefined,
  portalClose: string | null,
): AmendmentOutcome | undefined {
  if (outcome?.kind !== "amended") return outcome;
  const e = outcome.amendment;
  const frClose = validCalendarDate(e.fr_comments_close_on);
  const frPlausible = frClose !== null && frClose > e.publication_date;
  if (portalClose === outcome.date || (frPlausible && frClose === outcome.date))
    return outcome;
  return {
    kind: "ambiguous",
    reasons: [
      ...(outcome.reasons ?? []),
      `uncorroborated: ${outcome.date} (read from ${e.fr_document_number}'s text) matches neither the portal close (${portalClose ?? "none"}) nor ${e.fr_document_number}'s own FR comments_close_on (${frPlausible ? frClose : "none plausible"})`,
    ],
  };
}

/**
 * What an outcome DOES to the window's derivation: the amended FR close (with its kind of change), or
 * nothing. `none` and `ambiguous` are the same effect — both leave the FR side the original's own.
 */
export function amendmentEffect(o: AmendmentOutcome | undefined): string {
  return o?.kind === "amended" ? `amended:${o.date}:${o.change}` : "unchanged";
}

/**
 * Has the amendment evidence changed what the window derives SINCE `cutoffMs`? (The v2.4 freshness rule
 * for linked amendments, ADR 0016 §7.) With the inputs: re-resolve them as they stood at the cutoff and
 * compare the effect — a new extension that moves the close, a new reopening that un-amends it, or newly
 * fetched published text that turns "no date" into a date all count; a GovInfo copy of an extension the
 * reviewer already saw, confirming the same date, does not. Without the inputs (a caller that holds only
 * the outcome): an amended outcome whose amendment was fetched after the cutoff — or at an unknown time —
 * counts as new.
 */
export function amendmentChangedSince(
  cutoffMs: number,
  outcome: AmendmentOutcome | undefined,
  inputs: AmendmentInputs | undefined,
): boolean {
  if (inputs?.timeline) {
    // The history rule: the effect at the verdict (the last state at or before it — the v2 tie policy:
    // equal is not newer) must hold through EVERY later state. A material change followed by a reversion
    // still supersedes; a re-fetch that derives the same outcome never does.
    let base: AmendmentEvidence[] = [];
    for (const st of inputs.timeline)
      if (new Date(st.at).getTime() <= cutoffMs) base = st.amendments;
    const baseEffect = amendmentEffect(
      resolveAmendedClose(inputs.original, base),
    );
    return inputs.timeline.some(
      (st) =>
        new Date(st.at).getTime() > cutoffMs &&
        amendmentEffect(resolveAmendedClose(inputs.original, st.amendments)) !==
          baseEffect,
    );
  }
  if (inputs) {
    const now =
      outcome ?? resolveAmendedClose(inputs.original, inputs.amendments);
    const then = resolveAmendedClose(
      inputs.original,
      amendmentsAsOf(inputs.amendments, cutoffMs),
    );
    return amendmentEffect(now) !== amendmentEffect(then);
  }
  if (outcome?.kind !== "amended") return false;
  const e = outcome.amendment;
  const after = (iso: string | null | undefined) =>
    !iso || new Date(iso).getTime() > cutoffMs;
  return (
    after(e.fr_fetched_at) ||
    (e.govinfo_observation_id !== null &&
      outcome.observation_ids.includes(e.govinfo_observation_id) &&
      after(e.govinfo_fetched_at))
  );
}
