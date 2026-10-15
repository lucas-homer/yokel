<!-- PILOT-ADOPTION.md governs the currently adopted scope; later stages below remain proposed. -->
# Developmental routing and normalization protocol

Compare deterministic evidence checks with the same checks plus Jev or an inexpensive general model. The immediate result is a bounded development experiment on the 28 previously reviewed notices. All 28, including the former eight held-out notices, are now development data. This protocol does not reopen round-two scores, authorize production ingestion, or establish a validated automatic router. Production remains federal-only.

## Experimental units and stages

The retained corpus contains 28 selected notices, 56 input pages and four common parser representations: native, Docling, Llama cost-effective and OpenRouter Mistral annotations. At most 112 notice–representation pairs are available for local replay. Earlier Agentic/Plus/Firecrawl outputs may supply separately labeled historical challenges but do not expand the common paired cohort.

Use three distinct stages. First, build and test candidate extraction, scope handling and deterministic normalization on all retained representations without paid inference. Second, run a paired semantic-verification pilot of at most 20 frozen claim cases per provider. Third, replay a frozen routing policy over retained outputs, revealing a fallback representation only after the recorded decision to request it. A larger paid run requires a separately recorded scope and budget; the 112 available representations are not authorization for 112 model calls.

A claim case is one proposed field value or relation, its literal evidence and relevant context, tied to one notice and parser artifact. A document can contain several correlated cases. Count claims, semantic groups, notices, original PDFs and families separately. A hand-selected evidence window is a challenge case; it cannot establish automated retrieval or segmentation performance.

## Three paired verifier arms

Use one frozen proposer and one deterministic normalizer to generate the same claims, strings, evidence spans, role proposals and context for all arms. The adopted first run is the 16-case reviewer-authored challenge; automated proposals are separate baseline development. Its paired comparison measures verification of common proposals, not unrestricted extraction quality.

| Arm | Decision mechanism | Shared controls |
| --- | --- | --- |
| D | Deterministic rules only | Same proposals, context, exact-span checks, type/date checks and policy |
| D plus J | D plus four narrow Jev judgments | Same hard checks; Jev cannot override a hard failure |
| D plus G | D plus the same four judgments from a cheap general model | Same text-only evidence, labels, thresholds and output validation |

Both model arms use the implemented four independent dimensions: support (supported/contradicted/insufficient), role (matched/mismatched/insufficient), condition (preserved/omitted_or_changed/insufficient), and conflict (present/absent/insufficient). Do not ask either to repair a date, email or citation by generating a replacement. Code copies observed strings and performs declared normalization. A model-assisted proposer would be a separate experiment and must run with both verifier arms or be explicitly reported as a confounded comparison.

Pin Jev to the documented version `jev-1.13.0` if available; record requested and returned IDs. The primary selects and freezes a catalog-verified general model before calls, with structured-output settings and a fixed prompt. Do not choose that model using the held-out outcome of the later fresh evaluation. Jev is text-only; give the general model the same text-only state in this comparison. [TypeSafe model documentation](https://docs.typesafe.ai/models).

Jev's published limitations include exact-number/date comparisons and sensitivity to option order and irrelevant context. Use code for arithmetic and comparison, concise complete contexts, an explicit insufficient option, and one coherent question. These are design constraints to test, not assumed accuracy claims. [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

## Separate fidelity from support

Keep three labels per scored claim. **Source truth** asks whether the proposed claim, role, precision, condition and destination match the original source within the target notice. **Parser fidelity** asks whether the parser retained the relevant source evidence and association. **Normalization support** asks whether the typed claim is justified by the parser text actually available to the runtime. A fluent wrong email can be supported by the parse and false to the PDF. A source conflict can be faithfully parsed and must remain unresolved.

Reviewers assign source truth as valid, invalid, or unresolved; parser fidelity as faithful, missing, changed, ambiguous, or unresolved; and the four parser-text judgments using the adapter label sets. Keep nonunique dimension labels explicit; never force uncertain reference judgments into a single allegedly correct label. Review every automatically accepted critical claim against the original page images. Source review and parser-text review retain exact locations and hashes. Neither supplies runtime answers. No text-only verifier receives credit for inspecting a stamp or restoring letters that its input does not contain.

The initial claim scope includes notice identity, lifecycle, date/time/zone roles, stated precision, relative anchors and conditions, selected/unselected states, withdrawal/change scope, and **direct participation destinations and their roles**. Destinations include comment email addresses, submission URLs, postal addresses and relevant hearing-access instructions. Incidental staff contacts remain distinct. Complete rule-body fidelity is outside this experiment unless separately declared; do not imply that normalization certifies the entire regulation.

## Prevent reference leakage

Create separate runtime and evaluation bundles. The runtime bundle contains original input hashes, captured parser text and mechanical page/layout metadata, proposed candidates, algorithmically selected context and fixed policy. The evaluator holds round-two references, new source annotations, correctness labels, reviewer-selected windows, error catalogues, original fixture names and scoring decisions.

Generate opaque runtime case IDs and neutral channel IDs; retain the mapping outside model state. Neither fixture names, parser vendor names, old pass/fail outcomes, reference questions, expected values, criticality derived from case-specific gold, nor human-written decisive-evidence notes enter model state or router features. Generic field definitions and criticality policy are allowed. Copying a source quote from a gold answer is still leakage if it substitutes for automated retrieval.

Stage an allowlisted runtime directory and execute the runtime without read access to evaluation files. Log and hash the bundle, candidate generator, context selector, normalizer, rules, prompts and route policy before inference. Test that shuffling, deleting or changing evaluation labels leaves runtime requests and outputs unchanged; hash comparisons and sandboxed file access are stronger evidence than an assertion that code does not use labels. Development authors already know these examples: disclose that human development leakage cannot be undone. Do not hard-code known fixture IDs, dates, correct email strings or known error locations as fixes.

The current PDFs are already curated notice excerpts. Give every arm the same bounded packet. Runtime target boundaries must be mechanically derived or supplied by an explicitly declared common task selector; reviewer-adjudicated boundaries are evaluator-only. A run using manually selected boundaries is a segmentation-controlled diagnostic, not a complete ingestion test.

## Candidate generation and normalization

Find candidate strings in the observable parser text, retain their offsets and surrounding headings/conditions, and propose roles using one fixed algorithm. Keep multiple plausible values. Track how many required source fields never became candidates; an accurate verifier cannot recover candidates it never sees. A no-candidate result is not a not-stated finding.

Validate exact substrings, hashes, page locators, schema, duplicate claims and incompatible same-role values in code. Parse explicit date components and validate calendar existence in code. Preserve unknown year/time/zone, anticipated versus actual dates, and date-only precision. Keep relative deadlines as structured literal quantities, units and anchors; do not compute legal deadlines, holiday rules, business-day calendars or unstated timezones. Do not silently resolve numeric date ambiguity. Normalization must retain the source form and a reversible transformation log.

For email addresses preserve the local part exactly; case-fold only the domain in a separate comparison key. For URLs preserve the original, path, query and fragment; restrict automatic comparison normalization to declared syntax-preserving operations. Do not autocorrect near matches, strip substantive query parameters, follow links, send email, test delivery, or assume a syntactically valid address is the right destination. Cross-channel disagreement is a review trigger; agreement is corroboration, not independent proof. A sole-channel fluent corruption remains a declared blind spot.

Absence requires adequate retained target scope, not just an empty regex result or missing context window. If a context pack is truncated, boundary-ambiguous or missing required pages, the affected claim cannot be accepted. A parser page count alone does not establish preserved visual selections or complete text.

## Routing and conflict policy

Runtime routes are accept_shadow, request_fallback, or review. Shadow acceptance publishes nothing and performs no civic action. A hard validation failure, missing decisive evidence, observed contradictory role/value, unverified actionable destination or uncertain scope prevents automatic action-readiness, regardless of model confidence. Record normalization acceptance and action-readiness separately; a well-supported parsed claim may still need original-source verification.

Start the primary replay with native text, then request the retained OpenRouter representation when the frozen policy says so, then review if unresolved. Record a deterministic-only router and both model-assisted routers. Docling as a selective intermediate step is an explicit secondary replay, with separate cost/quality results; it must not be inserted into every path based on hindsight. Keep always-native, always-fallback and always-review policies as anchors. An oracle choosing the best known parser may be displayed only as a labeled unreachable upper bound.

Before each route decision, the runtime can access only outputs already acquired on that path. Hidden fallback text, its scores and future outcomes cannot influence the earlier decision. Retained-output replay estimates which parser would be requested; it does not observe new parser latency, present availability or actual future charges. Allocate historical cost only with clear replay assumptions, and report parser replay cost separately from new verifier usage.

A07 and H06 are known development conflict examples, not runtime special cases. Preserve competing passages and their roles. Conflicting evidence must route to review; no vote across parsers, high model score or apparent later date settles source precedence. A correctly preserved conflict is not a parser failure, and accepting one disputed claim as settled is unsafe. Measure conflict detection among source conflicts separately from ordinary error detection.

## Labels and paired metrics

Freeze the pilot case manifest and labels before round-three provider outputs. Retain natural errors, naturally correct controls, unresolved source conflicts and controlled synthetic mutations as separate strata. Select cases before seeing candidate-arm scores and report the selection rule and source-family counts. Enriched challenge proportions are not deployment prevalence. Synthetic mutations never enter headline natural-error rates. An original and its mutations remain one correlated family group.

Use the definitions in metrics.json. Report at least: bad-claim detection recall and precision, false acceptance among accepted claims, escaped-error fraction among erroneous claims, correct acceptance coverage, unnecessary escalation, unresolved acceptance, source-conflict routing, support accuracy, candidate coverage, and full-notice action-readiness. Give every numerator and denominator. Count operational failures separately while retaining them in scheduled-system yield. A provider failure that sends everything to review is protective operational fallback, not demonstrated model error detection. Zero acceptances yields undefined acceptance precision, not 100 percent.

The primary pilot policy is a fixed conjunction, adopted before seeing responses: accept text support only when deterministic blocking issues are empty, the operation/schema checks pass, and support=supported, role=matched, condition=preserved, conflict=absent. Every other tuple escalates. A tied Jev distribution becomes insufficient as the adapter specifies. No probability or confidence threshold controls the primary pilot; both arms receive the same categorical rule. Text acceptance is not verified action-readiness or a source-fidelity pass. Preserve probabilities and confidence as diagnostics only; no post-output cutoff shopping. Any later threshold grid is explicitly secondary developmental analysis, not the primary result. [TypeSafe confidence semantics](https://docs.typesafe.ai/confidence).

Pilot provider eligibility is mechanical and fixed: valid runtime schema, candidate.value non-null and valid under the bounded JSON adapter, nonempty exact evidence, and no deterministic blocking issues. Null candidate values and empty evidence are recorded abstentions and remain in scheduled denominators without a call. Invalid schemas prevent execution until corrected and re-frozen; they are not silently dropped. Freeze the exact eligible case list and per-provider request counts before calls. Score primary gate discrimination on cases whose source-text expected accept/escalate outcome is independently unambiguous; retain ambiguous cases in the scheduled table and report bounds/sensitivity separately. A dimension may have multiple defensible labels but still have an unambiguous escalation gate. Source-fidelity blind spots such as a wrong email faithfully copied in the supplied text stay in the source-fidelity safety denominator even when their text-support outcome is unambiguous.

For provider signals that genuinely supply a defined probability, report a descriptive reliability table and Brier score on resolved natural cases; also show decision coverage and error counts. Do not claim calibration from 20 selected cases. Match comparisons by case and compare paired accepted-correct gains and newly unsafe acceptances at comparable coverage. Never let all-review appear superior without displaying its zero automatic yield. No binomial significance or national accuracy claim follows from correlated, selected development examples.

## Pilot limits and records

Honor the primary's existing first-pilot cap: at most 20 frozen cases per provider, at most one attempt per case, nominal estimated spend at most $0.25 per provider. Dry runs and local replay do not call providers. Setup probes, reordered-option checks and synthetic cases consume the same cap; no hidden extra retries. A request may batch independent cases only when its accounting still counts every evaluated case and neither arm gains extra context.

Disable SDK automatic retries. Preserve a durable intent and exact request hash before every call, retain response IDs, requested/returned model, usage, elapsed time, operational status and raw structured result. Use one in-flight request per provider for this pilot. Freeze timeout and response-size limits in the runner. Stop new calls after an uncertain POST, missing usage requiring reconciliation, an authorization error or the estimated/observed stop limit. Do not equate missing billing with zero. Price estimates, reported token/credit usage and invoice charges are separate. Actual authorization and resolved credentials remain the primary's responsibility; this protocol makes no calls.

TypeSafe's API accepts state, a model ID and typed questions; Choice returns a selection and probability distribution. Default SDK retries must be overridden for this bounded experiment. Do not assume arbitrary free-text extraction from Jev. The pilot wire contract is ../verifiers/INPUT-CONTRACT.json. The schemas here mirror its input and define an evaluation wrapper around its four-dimensional result. Provenance and routing metadata belong in sidecars, not extra fields passed to the frozen adapter. [TypeSafe API](https://docs.typesafe.ai/api), [Choice primitive](https://docs.typesafe.ai/primitives/choice).

## Later independent fresh evaluation

Freeze the implementation, candidate retrieval, role ontology, transformations, prompts, model versions, thresholds, route policy and evaluation scope before selecting or parsing the fresh test set. Any calibration subset must be separate from the final test and split by original PDF and template family. Do not retune after final-test outputs. A changed policy starts a new evaluation version.

Proposed next small fresh cohort: 24 notices from at least eight states, at most three per state, 24 distinct original PDFs and template families disjoint from all development and calibration families; at least six actual image-only or degraded scans and deliberate coverage of forms, lifecycle changes, multiple dates and direct submission channels. Independently document accessibility/selection failures and any quota shortfall before inference. These are proposed planning targets, not a claim that the corpus exists. A source-only team prepares complete notice boundaries, destinations, critical fields and uncertainty; model/runtime developers cannot use those labels during execution.

Audit 100 percent of automatically accepted critical claims and their destinations against original page images in this small fresh phase, plus every selected notice's required-field completeness and conflicts. Retain random acceptance sampling as a requirement for any subsequent larger shadow deployment, chosen independently of model confidence; record sampling probabilities and weighted estimates where appropriate. A zero-error result on a small set still does not establish a rare-error rate.

Before the fresh run, primary must adopt explicit minimum correct-acceptance coverage, tolerated unsafe accepts, conflict handling, provider availability and cost bounds. Recommended research progression requires zero observed unsafe critical acceptances, no accepted unresolved conflicts or unverified destinations, and nonzero useful coverage with no unexplained regression against D. This is eligibility for further monitored testing, not production certification. Development results choose what to evaluate; they do not satisfy this fresh gate.

## Deliverables and integration

Keep immutable runtime inputs, evaluator labels, candidate coverage report, pilot selection ledger, provider artifacts, decision traces, source-support-fidelity labels, exact normalized claims, per-arm metrics, paired comparisons, cost ledger and correction history. Link every finding to source and output evidence. Do not copy round-two strict passes into a normalization metric.

This directory provides protocol.md, metrics.json, runtime-input.schema.json, runtime-output.schema.json, runtime-contract.md and a hash manifest. The implementer should use the published adapter wire contract; freeze its hash and the protocol mapping before calls. Primary must freeze the concrete model IDs, eligible pilot manifest, shared label-conjunction rule, rubric/label corrections and actual runner limits. Any extension beyond the initial 20-case cap requires a separate scope record. No fresh corpus or provider execution is authorized by this draft alone.

The current 16-case challenge uses reviewer-authored candidates and reviewer-selected retained text. Report it as a semantic challenge, not automated candidate extraction or end-to-end routing. Natural parser defects projected into these authored claims are distinct from naturally observed extractor errors. The label review in challenge-label-review.json identifies pre-run issues to resolve before the final freeze.
