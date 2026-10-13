# Round six: source-grounded participation records — early contract

Research only. The unit is a bounded participation record for one complete notice, not a bare DATE/email pair. Prior-round sources and failures are development evidence only. No fresh collection, model extraction or paid call is authorized by this document. Primary freezes the full implementation/protocol before collection and independent image truth before any fresh model extraction.

## Record semantics

Represent event phases and alternatives explicitly: initial comments, response comments, hearing, hearing-request/registration, record close and other relevant participation events remain distinct. A date can be correct for one phase and wrong for another. Do not choose a single first/last overall deadline, infer chronology/precedence or silently merge overlapping windows. Conditional/relative timing is retained as a source-grounded expression and dependency, never converted to a bare absolute deadline by arithmetic or assumed hearing time.

Represent direct routes as alternatives with their supported phase/target association. Two valid email destinations are both retained. Distinguish comment delivery from hearing registration, questions, copies and accessibility contacts. Preserve case and exact literal destination strings; do not repair source text or infer an email from a hyperlink target not present in the authorized native input.

Keep three explicit semantic classes and their relationships:

1. Source facts: phases/events, dates or temporal expressions, routes/destinations, and their association to the notice or another target.
2. Applicable instructions/requirements: required docket/reference, format, recipient, method, arrival/postmark rule, prerequisites and conditional applicability. Each attaches to the affected phase, route, action or entire notice, with quoted evidence. Preserve mandatory, optional and unclear modality; do not convert “may” to “must.” A required filing reference does not alter the calendar DATE, but it is necessary for a complete filing record.
3. Disclosures: public posting, confidentiality/public-record treatment and similar source statements affecting participation. Keep these separate from deadline conditions while retaining them in the record and completeness evaluation.

Also preserve source conflicts, uncertainty, lifecycle changes, source identity discrepancies and relative dependencies. Conflicting docket identities are not cosmetic metadata to be corrected. Every semantic atom and relationship needs exact source evidence (immutable source hash, quote deterministically resolved to character spans; mechanical page locator when reliable). Prefer extractor exact quote plus explicit disambiguating context/occurrence to asking a model to count Unicode offsets. Code resolves unique exact matches; ambiguous repeats fail closed unless a frozen explicit occurrence/context rule disambiguates them. No fuzzy matching, whitespace rewriting or guessed selection. Deterministic source line IDs may aid referencing while preserving original spans and bytes. IDs identify records; they do not establish correctness. Duplicate identical mentions can group with all evidence; different phase, modality, target or applicability requires distinct identity. A copied paragraph is evidence, not a substitute for structured association.

## Independent inventory and anti-circular verification

Freeze two separate artifacts before verification: (a) a source-only requirements inventory produced without access to the proposed record or any verifier response, and (b) the proposed record. Inventory can help construction, but then its independence is only from the proposal-generation input/output timing stated in the execution trace; do not claim independent corroboration. An extractor-generated inventory is an untrusted hypothesis, never ground truth.

Both verifier arms receive identical whole native source bytes, the same frozen inventory and the same frozen proposed record. They must perform two logically separate checks: validate every listed atom/relationship, and search the whole source for participation facts, requirements, disclosures or conflicts absent from BOTH inventory and record. In particular, dropping PDF format and docket reference from both artifacts must be detectable. “Everything in the inventory is covered” is not record completeness. Independent source-image labels—not model self-attestation—measure completeness.

The common decision dimensions must expose component/relationship support, applicability/modality preservation, unresolved conflicts, and source omissions. Jev is non-generative: use bounded categorical judgments over supplied units/source blocks. Do not require it to generate arbitrary missing-item text or spans. The stronger verifier may additionally return evidence-backed omission diagnostics; those are asymmetric diagnostic capability, not a shared output requirement or repair input. A source-omission finding is a verifier diagnostic, not an automatic record repair or extra accepted field. Empty omission lists or a favorable overall score cannot override an unknown/missing component, incomplete source scope or deterministic failure. Retain disagreement between arms; no best-of-two selection, consensus repair, fallback to stronger output or feedback into the shared record.

The stronger verifier and Jev compare verification of the SAME record. Freeze model identifiers, prompts, output schema, structured-record serialization, source limits, categorical acceptance policy, token/cost reservations and per-stage call counts. Confidence is reported diagnostically and must not be tuned on fresh outputs. If the providers cannot implement comparable judgments, disclose that and resolve the comparison contract before freeze.

## Deterministic and operational boundaries

Native only, complete source context without clipping. Validate source identity, UTF-8 bytes, exact quotes/spans, supported date-only normalization and exact email strings before dispatch. Unnormalizable dates can remain faithfully quoted unresolved expressions; invalid/missing-year literals cannot become invented ISO values. Native text does not certify PDF fidelity. Collector full_notice is a claim to audit, not independent proof.

All scheduled inputs and both arms remain in accounting, including source-scope failures, empty records, too-large requests, provider errors and budget stops. No replacement after labels. Preserve provisional responses and terminal decisions separately. `action_ready=false` and `production_eligible=false` always; a complete shadow record is not permission to file or a legal-certainty claim. Use durable requests, pre-POST reservation, raw response/status/usage, no automatic POST retries and drift-bound resume. Uncertain calls stop before later calls; an absent response is not an abstention-quality success.

## Bounded controls required before READY

Use the actual entry point with fake transport for positive record reachability and bounded malformed/negative cases. Include:

- Two phases with separate dates; two valid alternative emails; preserve both rather than treating multiplicity as conflict.
- Correct deadline plus missing filing reference: fact accuracy can pass, instruction coverage and record completeness must fail. Correct email plus missing PDF format must similarly fail.
- Required reference and PDF format missing from BOTH inventory and record: source-first verifier prompt/response path must support detecting the double omission, and evaluator image truth must count it as missing even if both arms say complete.
- Public-posting disclosure missing, independently of route/date correctness.
- Hearing-bound close or conditional extension versus an ordinary close with incidental accessibility wording; qualified record may be supported only with its actual dependency preserved, never as an unconditional flattened date.
- Conflicting footer/notice identity; incomplete scope; same date used in different event roles; wrong route recipient; modality reversal; unsupported extra requirement.
- Exactness mutations, split-line phrases, empty/oversize source, unresolved relationship, duplicate grouping and source-inventory drift.
- Paired-arm identical-input hashes, per-stage/total caps, unknown-call stop, resume without rePOST, and no label access before dispatch.

These are implementation controls, not evidence that a real model finds omissions. Publish the actual tests, policy and code hashes at READY, then stop edits. Primary sets a conservative total experiment ceiling of $2, covering extraction and both verifier arms together. Runtime must prove the full reservation fits before implementation freeze and stop on unknown/over-budget cost. Freeze exact extraction/comparator models and per-stage caps before live execution; do not inherit round-five limits implicitly.

## Whole-source coverage with narrow questions

Model-specific transport adapters may differ, but canonical source/inventory/record payload hashes and semantic decisions must be comparable. A blockwise source-omission pass is allowed only if deterministic coverage intervals account for every source character/page, including headers, footers, continuation lines and apparently irrelevant text. No lexical relevance filter may remove text from the coverage pass. Both arms use the same frozen block schedule and relationship context. Overlap, boundary-crossing relationships and unresolved references need a frozen reconciliation rule; mere interval coverage proves transmission, not comprehension. Per-unit checks can point directly to exact supporting text while the separate all-source omission check covers what the inventory missed. If a block is skipped, over limit, failed or not judged, completeness remains unresolved and terminal record acceptance is blocked. Do not concatenate only positive/filter-selected blocks and call that full-source verification.

TypeSafe's documented indirection/large-state limitations motivate direct narrow questions, not a claim that filtering preserves source requirements. Documentation reviewed October7,2026: https://docs.typesafe.ai/model-jaggedness/jev-1.13 . No cookbook confidence threshold is imported.
