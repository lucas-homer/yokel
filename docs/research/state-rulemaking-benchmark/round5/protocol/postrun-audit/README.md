# Round-five independent postrun audit — READY, gate not met

Eight scheduled inputs reached terminal output:22 candidate rows, nine Jev POSTs, no failed/partial/not-started documents and no OCR. All six accepted rows were audited against frozen image truth and source qualifications. They represent five distinct claims because South Dakota's email is repeated.

Only two distinct fields pass the full audit: South Dakota's written DATE and EMAIL. Three accepted claims are unsafe under the frozen contract. Michigan's correct DATE value and correct EMAIL literal omit the frozen ADM FileNo2021-29 filing qualification from both candidate claim and conditions; the email also omits the public-posting qualification. The New Mexico PRC email omits PDF-format and docket-reference requirements and has unresolved whole-notice scope from the pre-output footer conflict. All accepted calendar/literal values match their local source. Qualification and scope failures drive the unsafe count:3/5 distinct claims, with one also unauditable for incomplete source scope. No source labels or runtime decisions were changed.

The immutable R4 evaluator CLI produced `evaluation-report.json`. It reports whole-cohort DATE, EMAIL and pooled rates as null because one input lacks established complete scope; known counts are1/7 DATE and1/7 EMAIL. `complete-notice-subset.json` uses the same evaluator on the seven notices established complete before outputs, solely as a descriptive subset:

| Measure | Correct / eligible | Recovery |
|---|---:|---:|
| DATE |1/5|20.0%|
| EMAIL |1/6|16.7%|
| Pooled |2/11|18.2%|

The zero-unsafe gate fails. The subset falls below25%; the full-cohort threshold cannot be established. Eight complete notices were required and only seven were independently established. No action-ready declarations were made. Source-audited complete recovery is1/8 inputs (South Dakota); this is retrospective source scoring, not runtime completeness certification. Unsupported abstention25/28 includes other roles and uncertainty groups and must not be presented as classifier accuracy.

## Prespecified stage mapping

`stage-audit.json` maps all14 frozen eligible local facts, including three from the input with unresolved whole-notice identity. All14 values and their relevant role/qualification evidence are present faithfully in native text. This is a local fact audit, not whole-parser accuracy. Thirteen have value/role proposals; the response-comment DATE September8,2025 is omitted despite native evidence. Two proposed facts in the uncertain input cannot establish matching whole-notice scope. Thus11/14 known facts have proven scope-matched candidates, two mappings remain unknown, and one is omitted; exact whole-known-set candidate recall stays null, with11/14 as a conservative lower bound. The same values apply conditional on audited faithful local native evidence. The seven complete notices have11/11 candidate recall (DATE5/5, EMAIL6/6).

All14 known facts reconcile to: six deterministic blocks with established scope; one deterministic block with unresolved whole-notice scope; one candidate omission; one completed verifier nonacceptance; three accepted claims failing source audit; and two correct recoveries. Six distinct eligible value/role facts reached Jev (three DATE, three EMAIL, one of the emails with unresolved source scope). In the complete subset, five of11 facts reached Jev and two recovered.

The prespecified loss-stage vocabulary lacks an unsafe-acceptance category. Those records keep `loss_stage=unmeasured` and explicitly record the measured `terminal_source_audit_rejection` attribution; they receive no recovery credit. This limitation is disclosed rather than silently modifying the frozen taxonomy or misclassifying favorable model judgments as nonacceptance.

`loss-attribution-notes.json` retains bounded evidence for remaining overconservatism and omission. Kentucky's written close is blocked by a relative hearing-intent signal. One Ohio notice is blocked by a heading regex that also matches a continuation line about the same proposed rulemaking. Connecticut's explicit email is blocked by the DATE extension/lifecycle signal. Three eligible email facts hit full-request size limits. New Mexico's missing response candidate has a line break inside the phrase “no later than”; the frozen matcher uses literal spaces. None of these observations authorizes repairing or promoting outputs.

## Costs and integrity

All nine durable operations have200 responses with verified response/request hashes, retained usage and matching parsed labels. Reported usage is26,638 input and1,547 output tokens. Usage times the pinned rate estimates$0.001118796; conservative reserved/accounted budget charge is$0.005140464. No invoice charge was reported. Dividing total run cost by two independently correct distinct fields gives$0.000559398 per correct field on the usage estimate, or$0.002570232 on conservative budget charge. The numerator includes duplicates and unsuccessful cases. These estimates establish neither unit economics nor production reliability.

All run bytes remained unchanged during this audit. Freeze B's seven files and Freeze S's230 files match. Freeze A's181 static files match; its sole growing access ledger is covered by the primary's pre-label documented exception and pinned by S. All22 terminal observations have consistent acceptance/readiness indicators. Frozen sources, labels, implementation and run are read-only; only this new audit directory was written. Reviewer provider calls:zero.

READY means the audit is complete and edits stopped. The progression gate is NOT MET. Any further experiment requires a new, explicitly authorized version and fresh evaluation; no threshold/prompt tuning or source replacement is implied.
