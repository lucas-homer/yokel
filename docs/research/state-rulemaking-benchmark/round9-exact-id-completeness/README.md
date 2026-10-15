# Exact record assessments and completeness checks

This offline research revision addresses two failures from the preceding Wisconsin diagnostic: a response with an extra assessment ID, and a completeness claim that overlooked information missing from the normalized record. The prior response and its rejected verdict remain unchanged.

The response schema now requires one keyed assessment for each actual record item, including nested timings and route components. Coverage belongs in the global completeness section. Strict parsing rejects duplicate JSON keys before they can be overwritten, and the existing host checks remain after lossless conversion to the existing verdict format.

Completeness is evaluated separately. The offline checker consumes a reviewed source-unit audit bound to the exact source and record, including checks of every operative record field. Evidence quotes and the extractor’s own coverage rationale cannot substitute for a missing assertion. Missing or unapproved audits, incomplete source scope, unresolved relationships and unclear modality remain unverified. These checks aggregate supplied judgments; they do not automatically discover source omissions or establish that a reviewer is correct.

The development set contains ten variants across rule detail, full participation alternatives and requirement modality. Primary and independent review approved three positive, five incomplete and two unverified expected outcomes. These synthetic cases are regression tests, not held-out accuracy measurements or human gold.

The compact request is 38,432 UTF-8 bytes; with the existing 1,024-byte allowance it remains below the unchanged 40,000-byte guard. Source, record, model and output limit are unchanged. Provider support for the compact schema is not yet tested. No provider calls, credential changes or production-schema changes are part of this round.

Implementation and independent verification are complete. All 15 unit tests and 244 independent checks pass. Review caught and the builder fixed a malformed-input exception; the initial finding and results are preserved. Primary verification confirmed all 4,995 prior artifacts unchanged, plus the protocol, runtime and review hashes. See [independent findings](review/IMPLEMENTATION-FINDINGS.md) and [primary verification](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round9-exact-id-completeness/primary-verification.json).

The next experiment should test provider compatibility with this exact compact schema and compare the resulting assessments against the retained source audit. Passing these offline checks does not establish that a model will return accurate or complete judgments. Protocol details are in [SPEC.md](protocol/SPEC.md) and [SEMANTIC-AUDIT-CONTRACT.md](protocol/SEMANTIC-AUDIT-CONTRACT.md).
