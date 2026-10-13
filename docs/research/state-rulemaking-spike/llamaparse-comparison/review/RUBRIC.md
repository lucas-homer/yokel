# Pre-output rubric: Mississippi document comparison

Prepared October 5, 2026 by the independent agent reviewer **before seeing any
LlamaParse trial output**. This is a selected diagnostic fixture with prior
known failures, not a blind benchmark or independently human-labeled gold set.
No vendor calls, installations, new tasks, or baseline edits were performed.

## Source identity and reference basis

Original official URL:
https://www.sos.ms.gov/adminsearch/ACProposed/00027305a.pdf

Both retained `pdf/raw/inherited.pdf` and `pdf/raw/fresh.pdf` were independently
hashed: **401742 bytes**,
`ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955`.
The complete saved page image was visually inspected again. Its SHA-256 is
`286452e7ee59950903b46fc02d938f4af73461cb3a1b190a5b272b9a5914257b`.
No new rendering was performed; the existing rendering's provenance was checked
against the saved source/image hashes. Labels below come from that visual
inspection, cross-checked against retained native text and Firecrawl baselines.

Baseline root:
`/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/pdf`.
The original is a one-page scanned form with an imperfect embedded OCR layer,
not a complete proposal package. The footer mentions an attachment not present
in this file. The present comparison must use these same original bytes or
explicitly mark byte identity unverified; requesting the same URL is not itself
proof of identical submitted bytes.

## Frozen cases

| ID / importance | Visual reference and required distinction | What does not earn semantic success |
|---|---|---|
| M1 / critical | ORAL PROCEEDING: **not scheduled** checkbox marked; scheduled option unchecked; date/time/place blank | Both labels in text; guessed not-scheduled answer without mark association; promoting blank scheduled template to an event |
| M2 / critical | PROPOSED ACTION: **amendment** marked; new/repeal/adoption-by-reference unmarked; lifecycle is proposal | Detached X; amendment text alone; inferred final adoption; conflating lifecycle with rule action |
| M3 / diagnostic mark-control | ECONOMIC IMPACT: **not required** marked; concise-summary-attached unchecked | Both alternatives presented as facts; recovering the word "not" without association to the checked option |
| B1 / critical abstention | FINAL ACTION: all action choices blank; Date Proposed Rule Filed blank in this section | Claiming withdrawn, adopted, or repealed because those labels appear; filling this blank from another date field |
| B2 / critical abstention | Temporary-rule options blank; temporary/proposed-final/final effective-date choices blank, including **30 days after filing** | Turning boilerplate into an asserted effective date or relative effective period |
| D1 / date-role | Upper SUBMIT DATE handwriting reads **12/27/2023** | A generic unlabeled date; a stamp-only extraction claimed as handwriting recovery |
| D2 / critical date-role | Lower middle OFFICIAL FILING STAMP reads **DEC 27 2023**, date precision only | Submit date reused as stamp evidence; invented time/zone; one date counted as proof that both date roles were independently recovered |
| T1 / critical | Hearing-request condition: **20 days after filing of this notice of proposed rule adoption** | 20 days assigned to comments; bare 20 without its role/anchor; absolute deadline computed without a counting policy |
| T2 / critical | Hearing-request scope: when no oral proceeding is scheduled, a written request by a **political subdivision, agency, or ten or more persons** triggers the stated condition | General individual entitlement to compel a hearing; losing the not-scheduled condition or requester threshold |
| T3 / critical | Public-comment clause: **25 days**; its own clause supplies no explicit start anchor or counting basis | 20-day substitution; stamp reused as an unstated comment anchor; invented absolute close or calendar/business-day rule |
| X1 / lexical | Name/number field and repeated rule reference: **Rule 5.29** | Rule 5,29 left unresolved while claiming perfect recovery; recovery from later occurrence claimed as first-field OCR recovery |
| X2 / lexical | Explanation: **Exam Validity Extension Program (EVEP)** | EVER, unsupported acronym repair, or a correct acronym used to imply form/temporal success |

Agency "Secretary of State – Securities Division" is a contextual sanity check,
not an extra easy case to inflate an aggregate score. Whitespace, typographic
dash, case and date-display normalization may be harmless if disclosed; exact
quote matching always uses the retained representation without silent cleanup.

## Record results on separate axes

For every case, record raw output artifact + locator + quote/region, result,
provenance quality, and any downstream actor/transform. Use these categories:

- **recovered_supported**: raw vendor output preserves the required text/role or
  mark-label association, and the supporting citation can be replayed and checked
  against the original visual region. For M/B cases, the mark/blank relationship
  is required. A correct answer alone is insufficient.
- **correct_but_ungrounded**: the asserted answer matches the visual reference,
  but its supplied evidence omits or cannot establish the decisive relationship.
- **text_only_or_partial**: useful text or some structure recovered, but the
  required role, mark, condition or scope remains unresolved. Both checkbox
  labels without marks belong here, even if the prose is flawless.
- **safe_abstention**: explicitly unresolved/null or preserved blank/unselected
  state without a fabricated fact. For an asserted-value case this is a safe
  miss, not recovered success. For B1/B2, explicit blank/unselected preservation
  is successful abstention only when the pertinent section is actually covered.
- **incorrect_or_fabricated**: wrong value/role/scope, option falsely selected,
  unsupported anchor/time/close, or invented evidence.
- **not_demonstrated**: missing relevant region/output, unsupported tool feature,
  inaccessible result, or nonexecution. A skipped field is not automatically
  evidence-aware abstention.

Also label **stage**, independently of category:

1. `vendor_parse`: what the retained parse response itself contains (including
   any vendor-returned layout/marks); do not infer unreported internal model type.
2. `vendor_extract`: explicit vendor structured extraction, only if actually run;
   keep its prompt/schema/settings separate from the parse call.
3. `deterministic_normalization`: locally computed mapping from a cited vendor
   representation; retain executable rules and indicate their inspected inputs.
4. `agent_interpretation` or `agent_visual_repair`: judgments/labels introduced
   by the trial or review agent. These cannot retroactively become vendor wins.

A parse service can succeed at preserving evidence without emitting normalized
fields. Assess it at that stage; do not require it to behave like an extraction
service. Conversely, an agent deriving correct fields from weak prose does not
prove that the parser recovered form semantics. Baseline's four manual visual
assertions cannot be credited as automated Firecrawl findings.

## Traceability gates

Evaluate each claimed recovered field with the following checklist; report gaps
as separate provenance limitations, even when the value is correct:

- Input artifact hash/identity, service/tool, actual settings, returned mode and
  any reported version retained; unavailable version/settings labeled unknown.
- Raw response retained uncorrected with hash; derived representations name their
  parent. Any normalized answer identifies the raw field/span it consumed.
- Field-level quotation, structured mark association, or bounding region resolves
  to a retained artifact. A page/URL alone gives document-level provenance but
  does not establish which checkbox/date/option supports a field on this dense form.
- Exact quote is found in the named retained text; normalization/paraphrase is
  labeled separately. Quote failure against a different independently generated
  parse is not by itself proof of fabrication; inspect the actual cited output.
- For checkbox/blank claims, the cited representation preserves selection state
  attached to the correct label, or the field is explicitly marked as visual
  agent review. Bounding boxes are helpful but not mandatory if an unambiguous
  retained label-plus-state representation provides equivalent traceability.

Raw facts and source locators must remain auditable after offline normalization.
Replaying downstream code establishes repeatability of that code, not repeatable
vendor inference or original publisher authenticity.

## Comparison and verdict rules

Report a compact case-by-case table for native text, retained Firecrawl parse,
Firecrawl prompt-only extraction (where relevant), and each **actually executed**
LlamaParse/LlamaExtract mode. Do not merge parse and extract results into one
undifferentiated vendor score. Do not count repeated facts twice as independent
successes or use a single percentage combining X1/X2 with critical M/B/T cases.

Use one of these bounded conclusions, supported by the table:

- **No demonstrated comparison**: execution/output/input identity unavailable.
- **Text-recovery benefit only**: lexical/readability improvement, with decisive
  marks/date roles/conditions still unresolved.
- **Partial semantic/evidence benefit**: at least one hard field gains traceable
  mark/role/scope support, while named critical fields still need review.
- **Evidence-preserving parse for this fixture**: all covered critical form/date/
  temporal distinctions survive in auditable parser output; normalization may
  still be required and must be separately attributed.
- **Evidence-backed structured extraction for this fixture**: actually executed
  extraction produces the supported fields and explicit blank/unknown abstentions
  with field-level citations; no critical wrong/synthetic fact survives.

Any critical incorrect/fabricated result blocks the last two unqualified verdicts
for that run. Safe unresolved fields must be named and keep the result partial;
correct blanks must not conceal omissions. One fixture/run establishes neither
general accuracy nor a vendor ranking. Report observed latency/credits only with
actual units, scope, settings and caveats; do not convert incomparable billing
units into an economic claim. No production approval or legal-policy derivation
is part of this evaluation.

## Baseline anchors (before new outputs)

Native text loses submit/stamp dates and mark association, has first-field
"Rule 5,29" but later "Rule 5.29", and prints EVER. Firecrawl parse improves
Rule 5.29/EVEP and recovers both displayed dates and an X beside amendment, but
does not preserve the oral-proceeding or economic-impact checkbox selections.
Its separate fresh prompt-only JSON trial has some correct answers but missing
field-level evidence mapping and string unknowns. Prior normalized observations
include explicitly manual visual findings. These baselines are stage-specific;
the new output must earn any claimed advantage directly from retained evidence.

Next step is review of actual trial request/response artifacts and any
normalizer. No LlamaParse output was inspected while preparing this rubric.
