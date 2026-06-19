/**
 * chain.ts — the PURE, deterministic CROSS-WINDOW (chain) conflict engine (#31, Slice 3).
 *
 * The per-ocd_id reconcile engine (reconcile.ts) only ever sees ONE window's observation chain, so it
 * can detect a CROSS-SOURCE disagreement (FR vs Regs inside one window) but is structurally blind to a
 * CROSS-WINDOW (chain) conflict: an amendment notice (extension / correction / withdrawal) is a SEPARATE
 * FR document that mints its OWN ocd_id (a standalone window B) yet contradicts an ORIGINAL window A's
 * still-open deadline. This engine takes ALL the windows-joined-to-their-FR-observation candidates and
 * emits one cross_window ConflictRecord per genuinely-linked (A, B) pair.
 *
 * THE GOVERNING PRINCIPLE — over-linking is worse than under-linking (AGENTS.md "don't publish fake
 * certainty"). A FALSE chain conflict (claiming two unrelated windows conflict) burns the credibility
 * moat; a MISSED chain conflict is a known, honest gap. So the linkage rulebook is CONSERVATIVE /
 * HIGH-PRECISION: when in doubt, emit NOTHING. Shared docket alone is NEVER enough (dockets accrete many
 * unrelated notices over years) — linkage additionally requires identity corroboration (shared RIN OR an
 * explicit doc-number reference in the amendment's DATES text), strict amendment-after-original ordering,
 * and a live/recent original. A known keyword false-positive (the BLM 2023-27468 "land withdrawal"
 * pattern) is denied outright.
 *
 * PURE + DETERMINISTIC: no DB, no hidden clock. `now` is injected (used only for detected_at), and the
 * output is sorted (by ocd_id, then ocd_id_b, then the observation ids) so the same input ALWAYS yields
 * byte-identical output. Every emitted record is validated against the frozen contract via
 * ConflictRecord.safeParse before it leaves this function — an illegal cross_window record can NEVER be
 * returned (the contract superRefine requires ocd_id_b present AND distinct from ocd_id).
 */
import {
  ConflictRecord,
  type ConflictFlag,
  type OcdId,
} from "@yokel/contracts";
import { isDenied } from "../rulebox/index.js";

/**
 * RECENCY_WINDOW_MS — rule 4's "original is still relevant" threshold. An amendment to a long-DEAD docket
 * is not a LIVE conflict worth surfacing. An original A is in-scope when it is still `open`, OR its
 * resolved close is no earlier than (B.publication_date − this window). 60 days is the defensible default:
 * it comfortably covers the routine "comment period closed last month, agency reopens/corrects it" case
 * (the real chain we want), while excluding an amendment landing on a docket whose original closed a
 * quarter+ ago (far more likely a NEW, unrelated action on a long-lived docket than a live amendment of
 * the old one). Tunable in ONE place.
 */
export const RECENCY_WINDOW_MS = 60 * 24 * 60 * 60 * 1000; // 60 days

// The conservative keyword-false-positive deny-list now lives as DATA in the versioned RuleBox
// (src/rulebox/rulebook.ts, validated at load); isKeywordFalsePositive sources it via the evaluator's
// isDenied(). The headline trap is BLM 2023-27468: a "land withdrawal" (a public-lands action) trips the
// is_withdrawal/is_extension keyword pass even though it is NOT a comment-period action. Real BLM/USFS
// land-withdrawal notices carry `dates: None` (null DATES text) and put the withdrawal SIGNAL in the
// TITLE — so the haystack below checks BOTH title and DATES text. If an amendment candidate's title OR
// DATES text matches ANY deny rule, its amendment signal is a keyword false-positive and the candidate is
// FILTERED (never linked). Each deny rule targets the land-withdrawal LEGAL VEHICLE, not a bare incidental
// word — verified against the 3 real D3 spike titles (Public Land Order No. 7963; Flathead National
// Forest … Withdrawal; White River National Forest … Camp Hale … Withdrawal) WITHOUT eating genuine
// comment-period notices. To extend the deny-list, add a rule to the rulebook (NOT here). The
// deterministic RuleBox has landed; the LLM/Gemini ambiguous-tail escalation is what remains deferred.

/** One window joined with its (latest) federal_register observation — the chain pass's input row. */
export interface ChainCandidate {
  ocd_id: string;
  fr_observation_id: string;
  fr_document_number: string | null;
  docket_ids: string[];
  // rin = the PRIMARY (first) RIN, kept for projection/back-compat. The Rule-2 corroboration logic uses
  // the FULL `rins` array (intersection), so a multi-RIN doc whose first elements differ still links.
  rin: string | null;
  rins: string[];
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean; // a previously-CLOSED comment period re-opened (distinct from an extension) — #O4
  title: string | null; // the FR document title — the land-withdrawal signal often lives ONLY here
  publication_date: string | null; // "YYYY-MM-DD"
  govinfo_url: string | null;
  dates_text: string | null;
  status: string;
  resolved_close_utc: string | null;
}

/** What persistChainConflicts needs to build a contract-valid cross_window ConflictRecord. */
export interface ChainConflict {
  ocd_id: string; // side A (the original)
  ocd_id_b: string; // side B (the amendment)
  observation_a_id: string;
  observation_b_id: string;
  source_a: "federal_register";
  source_b: "federal_register";
  conflict_scope: "cross_window";
  conflict_flags: ConflictFlag[];
  govinfo_url: string | null;
  govinfo_url_b: string | null;
  detected_at: string;
}

/**
 * An AMBIGUOUS (A, B) candidate pair (#31 Slice 3b) — a pair the CONSERVATIVE engine deliberately DROPS:
 * it passes the STRUCTURAL rules (rule 1 shared docket + rule 3 ordering + rule 4 recency + isAmendment +
 * NOT a keyword false-positive) but FAILS rule 2 identity corroboration (NO shared RIN AND NO explicit
 * doc-number reference). These are exactly the borderline pairs the LLM adjudicator is asked to settle.
 *
 * It carries BOTH full candidate sides (a/b) so the async orchestration can build the AdjudicationInput
 * chain payload AND — on an `affirm` verdict — the promoted ChainConflict, via the SAME buildChainConflict
 * builder the confident path uses. By definition, for every ambiguous pair: shared_docket=true,
 * shared_rin=false, explicit_reference=false (those are the rule-2 signals that failed).
 */
export interface AmbiguousPair {
  a: ChainCandidate; // side A — the candidate original
  b: ChainCandidate; // side B — the candidate amendment
}

/**
 * Is this candidate an amendment of SOME original? (extension OR correction OR withdrawal OR reopening).
 * Exported so the chainReconcileOnce summary counts amendments by the SAME definition the engine links on
 * — a new notice type added here updates both the engine and the metric in ONE place (no divergence).
 */
export function isAmendment(c: ChainCandidate): boolean {
  return c.is_extension || c.is_correction || c.is_withdrawal || c.is_reopening;
}

/**
 * Rule 5 — a known keyword false-positive (BLM land-withdrawal trap). Conservative; extensible.
 * The signal lives in the TITLE for real land-withdrawal notices (which carry `dates: None`), so the
 * haystack is BOTH the title and the DATES text — checking only dates_text was structurally blind to the
 * exact trap (BLM 2023-27468) this rule exists to prevent.
 */
function isKeywordFalsePositive(c: ChainCandidate): boolean {
  const haystack = [c.title, c.dates_text].filter(Boolean).join(" ");
  return isDenied(haystack);
}

/** Parse "YYYY-MM-DD" to a UTC instant ms, or null. */
function pubMs(date: string | null): number | null {
  if (!date) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!m) return null;
  const [, y, mo, d] = m;
  const year = Number(y);
  const month = Number(mo);
  const day = Number(d);
  const t = Date.UTC(year, month - 1, day);
  // ROUND-TRIP GUARD (mirrors extract.ts asCalendarDate / reconcile.ts regsCloseToUtc): reject a date that
  // silently rolled over (2026-02-30 -> Mar 2) or is out of range. A FABRICATED publication_date must never
  // satisfy the ordering (rule 3) or recency (rule 4) tests and emit a chain conflict — degrade to "no
  // date" so the conservative engine UNDER-links rather than chaining off malformed data. (extractFr only
  // asStr-validates publication_date, so this is the real validation point.)
  const dt = new Date(t);
  if (
    dt.getUTCFullYear() !== year ||
    dt.getUTCMonth() !== month - 1 ||
    dt.getUTCDate() !== day
  )
    return null;
  return t;
}

/** Rule 1 — A and B share at least one docket_id (non-empty array intersection). */
function shareDocket(a: ChainCandidate, b: ChainCandidate): boolean {
  if (a.docket_ids.length === 0 || b.docket_ids.length === 0) return false;
  const set = new Set(a.docket_ids);
  return b.docket_ids.some((d) => set.has(d));
}

/**
 * Rule 2 (RIN half) — A and B share at least one NON-EMPTY RIN (array intersection, mirrors shareDocket).
 * FR returns RINs as a plural array (`regulation_id_numbers`, see extract.ts), and a doc may carry many.
 * A shared RIN is a strong, unique identity signal, so intersection is high-precision: A and B corroborate
 * iff some non-empty RIN is in BOTH arrays. Empty strings are ignored and EMPTY arrays NEVER corroborate
 * (the common Notice/amendment case has rins=[] — those must fall back to the explicit-reference path).
 */
function shareRin(a: ChainCandidate, b: ChainCandidate): boolean {
  const set = new Set(a.rins.filter((r) => r.length > 0));
  if (set.size === 0) return false;
  return b.rins.some((r) => r.length > 0 && set.has(r));
}

/**
 * Rule 2 — identity corroboration: shared non-empty RIN OR B's DATES text explicitly names A's
 * fr_document_number. Shared docket ALONE is insufficient (dockets accrete unrelated notices for years).
 *
 * Explicit-reference detection is intentionally STRICT to stay high-precision: we look for A's document
 * number as a whole token in B's DATES text, tolerating the FR convention of an embedded space after the
 * year (the EPA 2025-02910 fixture writes "FR 2025- 00734"). A doc number like "2024-30637" is matched
 * literally OR with that single optional space after the first dash group.
 */
function explicitlyReferences(
  b: ChainCandidate,
  aDocNum: string | null,
): boolean {
  if (!aDocNum) return false;
  const text = b.dates_text;
  if (!text) return false;
  // Build a tolerant pattern: escape regex metachars, then allow an optional single space after the
  // first hyphen (the FR "2025- 00734" line-wrap artifact). Require word boundaries so a doc number is
  // never matched as a substring of a longer token.
  const escaped = aDocNum.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const tolerant = escaped.replace(/-/, "-\\s?"); // first dash may be followed by a stray space
  const re = new RegExp(`(?<![\\w-])${tolerant}(?![\\w-])`);
  return re.test(text);
}

/**
 * classify — the conflict_flags for a linked (A, B) pair from B's amendment signals. EXPORTED (#31 Slice
 * 3b) so the async promotion path builds an IDENTICAL flag set for an LLM-affirmed link, then appends the
 * `llm_corroborated` provenance marker alongside (never folds it in here — the confident path must stay
 * byte-identical).
 */
export function classify(
  b: ChainCandidate,
  multiTarget: boolean,
): ConflictFlag[] {
  const flags: ConflictFlag[] = [];
  // B withdraws while A reads open.
  if (b.is_withdrawal) flags.push("withdrawn_vs_open");
  if (b.is_extension) flags.push("extension_chain_unresolved");
  // #O4: reopening is its OWN outcome, not an extension. After the notice-flags split a pure reopening has
  // is_extension=false, so it emits `reopening` alone; a notice titled both ("Extension and Reopening…")
  // honestly carries both flags. This is the mislabel O4 fixes — before, a reopening rode is_extension and
  // emitted only `extension_chain_unresolved`.
  if (b.is_reopening) flags.push("reopening");
  if (b.is_correction) flags.push("correction_pending");
  if (multiTarget) flags.push("multi_target_notice");
  return flags;
}

/**
 * buildChainConflict — the SINGLE record builder shared by the confident path (chainReconcile) AND the
 * async promotion path (chain-adjudicate). Given the two sides, the already-computed flags, and `now`, it
 * assembles the ChainConflict and VALIDATES it against the frozen ConflictRecord contract (the superRefine
 * requires ocd_id_b present AND distinct from ocd_id) before returning. Factoring this guarantees a
 * promoted LLM link is byte-structurally identical to a confident link (only its flags differ).
 */
export function buildChainConflict(
  a: ChainCandidate,
  b: ChainCandidate,
  flags: ConflictFlag[],
  now: Date,
): ChainConflict {
  // Distinct documents guarantee distinct ocd_ids (the superRefine requires A ≠ B); assert it.
  if (a.ocd_id === b.ocd_id)
    throw new Error(
      `buildChainConflict: invariant violated — side A and side B share an ocd_id ("${a.ocd_id}")`,
    );
  const record: ChainConflict = {
    ocd_id: a.ocd_id,
    ocd_id_b: b.ocd_id,
    observation_a_id: a.fr_observation_id,
    observation_b_id: b.fr_observation_id,
    source_a: "federal_register",
    source_b: "federal_register",
    conflict_scope: "cross_window",
    conflict_flags: flags,
    govinfo_url: a.govinfo_url,
    govinfo_url_b: b.govinfo_url,
    detected_at: now.toISOString(),
  };
  // VALIDATE against the frozen contract — never emit an illegal cross_window record.
  const parsed = ConflictRecord.safeParse({
    ...record,
    ocd_id: record.ocd_id as OcdId,
    ocd_id_b: record.ocd_id_b as OcdId,
  });
  if (!parsed.success)
    throw new Error(
      `buildChainConflict: derived cross_window conflict failed the ConflictRecord contract: ${JSON.stringify(
        parsed.error.issues,
      )}`,
    );
  return record;
}

/** The total order used for BOTH confident conflicts and ambiguous pairs (stable, byte-identical output). */
function compareConflict(x: ChainConflict, y: ChainConflict): number {
  return (
    x.ocd_id.localeCompare(y.ocd_id) ||
    x.ocd_id_b.localeCompare(y.ocd_id_b) ||
    x.observation_a_id.localeCompare(y.observation_a_id) ||
    x.observation_b_id.localeCompare(y.observation_b_id)
  );
}

/**
 * chainCore — the shared rule engine producing BOTH outcomes in one pass so the rule logic is never
 * duplicated:
 *   • confident — every (A, B) that passes ALL FIVE rules (the existing chainReconcile output, byte-
 *     identical: same flags incl. multi_target_notice, same sort order, same contract validation).
 *   • ambiguous — every (A, B) that passes the STRUCTURAL rules (1 docket + 3 ordering + 4 recency +
 *     isAmendment + not-a-keyword-FP) but FAILS rule 2 corroboration (no shared RIN AND no explicit ref).
 *     These are the borderline pairs the confident path DROPS — the LLM-escalation candidate set.
 *
 * The multi_target_notice flag is computed over the CONFIDENT targets ONLY (it always was), so surfacing
 * the ambiguous set CANNOT change any confident record's flags. An ambiguous pair carries NO conflict
 * record until/unless the async path promotes it (this function never builds an ambiguous ChainConflict).
 */
function chainCore(
  candidates: ChainCandidate[],
  now: Date,
): { confident: ChainConflict[]; ambiguous: AmbiguousPair[] } {
  // Amendments are the right-hand side B; everything (including other amendments) can be a candidate
  // original A. We compute, for each amendment B, the set of originals A it legitimately targets.
  const amendments = candidates.filter(
    (c) => isAmendment(c) && !isKeywordFalsePositive(c),
  );

  const confident: ChainConflict[] = [];
  const ambiguous: AmbiguousPair[] = [];

  for (const b of amendments) {
    const bMs = pubMs(b.publication_date);
    // Rule 3 needs B's publication date; without it we cannot know B is the amendment → do NOT link.
    if (bMs === null) continue;

    // Find every original A that independently satisfies rules 1–4. A multi-target notice (EPA
    // 2025-02910) legitimately links to MORE than one — each such pair emits, all carrying
    // multi_target_notice. Ambiguity WITHOUT independent satisfaction is never guessed (we only ever
    // keep originals that PASS all rules; we never tie-break among "plausible" ones).
    const targets: ChainCandidate[] = [];
    // Pairs that pass the STRUCTURAL rules (1+3+4) but FAIL rule 2 — the ambiguous tail for THIS b.
    const ambiguousForB: ChainCandidate[] = [];
    for (const a of candidates) {
      if (a.ocd_id === b.ocd_id) continue; // B cannot amend itself
      if (a.fr_observation_id === b.fr_observation_id) continue;

      // Rule 1 — shared docket.
      if (!shareDocket(a, b)) continue;

      // Rule 3 — amendment strictly AFTER the original (both publication dates present).
      const aMs = pubMs(a.publication_date);
      if (aMs === null) continue;
      if (!(bMs > aMs)) continue;

      // Rule 4 — the original is still relevant: open, OR its close is within RECENCY_WINDOW_MS before
      // B's publication. (An amendment to a long-dead docket is not a live conflict.)
      let relevant = a.status === "open";
      if (!relevant && a.resolved_close_utc) {
        const closeMs = new Date(a.resolved_close_utc).getTime();
        if (!Number.isNaN(closeMs) && closeMs >= bMs - RECENCY_WINDOW_MS)
          relevant = true;
      }
      if (!relevant) continue;

      // Rule 2 — identity corroboration (shared non-empty RIN [array intersection] OR explicit
      // doc-number reference). RINs are FR's plural array; intersection links multi-RIN docs that a
      // scalar first-element equality would miss, while empty arrays never corroborate.
      const sharedRin = shareRin(a, b);
      const referenced = explicitlyReferences(b, a.fr_document_number);
      if (!sharedRin && !referenced) {
        // STRUCTURAL rules passed but rule 2 FAILED → this is an ambiguous pair (the confident path drops
        // it). Surfaced for LLM escalation; never auto-linked here.
        ambiguousForB.push(a);
        continue;
      }

      targets.push(a);
    }

    // multi_target_notice is computed over the CONFIDENT targets only — exactly as before. (An ambiguous
    // pair is NOT yet a link, so it never inflates multiTarget; this keeps confident flags byte-identical.)
    const multiTarget = targets.length > 1;
    for (const a of targets) {
      confident.push(buildChainConflict(a, b, classify(b, multiTarget), now));
    }
    for (const a of ambiguousForB) {
      ambiguous.push({ a, b });
    }
  }

  // DETERMINISM: stable total order so identical input ⇒ identical output.
  confident.sort(compareConflict);
  ambiguous.sort(
    (x, y) =>
      x.a.ocd_id.localeCompare(y.a.ocd_id) ||
      x.b.ocd_id.localeCompare(y.b.ocd_id) ||
      x.a.fr_observation_id.localeCompare(y.a.fr_observation_id) ||
      x.b.fr_observation_id.localeCompare(y.b.fr_observation_id),
  );

  return { confident, ambiguous };
}

/**
 * chainReconcile — the CONFIDENT cross_window set (rules 1–5). Signature + output UNCHANGED (#31 Slice 3b
 * surfaces the ambiguous tail via chainAmbiguousPairs WITHOUT touching this path, so the existing chain
 * tests stay byte-identical). It is exactly `chainCore(...).confident`.
 */
export function chainReconcile(
  candidates: ChainCandidate[],
  now: Date,
): ChainConflict[] {
  return chainCore(candidates, now).confident;
}

/**
 * chainAmbiguousPairs — the PURE, deterministic ambiguous candidate set (#31 Slice 3b): every (A, B) that
 * passes the structural rules but fails rule 2 corroboration — precisely the pairs the confident path
 * UNDER-LINKS. Sorted by (a.ocd_id, b.ocd_id, a.fr_observation_id, b.fr_observation_id). The async
 * orchestration escalates these to the adjudicator; on `affirm` it promotes the pair to a cross_window link
 * (with `llm_corroborated`). NO DB / clock / adjudicator here — this stays a pure function of its inputs.
 */
export function chainAmbiguousPairs(
  candidates: ChainCandidate[],
  now: Date,
): AmbiguousPair[] {
  return chainCore(candidates, now).ambiguous;
}
