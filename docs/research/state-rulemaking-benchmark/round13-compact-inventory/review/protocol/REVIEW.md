# Round 13 independent protocol review

**APPROVED FOR RUNTIME IMPLEMENTATION. No material protocol blocker found.** A one-call serialization diagnostic is reasonable under the declared engineering assumptions. This is not paid-release approval, a guarantee of output fit, or evidence of source completeness. Primary must freeze the stated sizing/admission policy before paid release and complete runtime review.

Reviewed protocol READY SHA256: `ea8675ff9ad1e7400aebfc0ea49e64bae194ccf2ef22e207f8c7f9ff48b57843`. All 17 protocol artifact pins verified. The existing review checklist remains unchanged. The consulted R12 reference/postrun report was deliberately neither read nor hash-verified because the review excludes reference/gold; its author-declared pin is recorded as an explicit verification exclusion. Other consulted-input pins were checked without consuming their prose. The protocol and this reviewer have prior R12 exposure; this is the disclosed outcome-exposed engineering case, not a blind evaluation. No truncated R12 prefix was reread or used as a fixture in this review.

## Source, reconstruction and validation

The four-field user input contains only complete source text/hash and the host span table/hash. The frozen 3,876-byte source is exactly preserved in **37** ordered host-generated line spans, with exact text adjacent to every ID. Source reconstruction from row texts matches the original UTF-8 bytes; table validation independently binds order, offsets, text, version and source. IDs are stable for identical source/version, not global identities. The model selects IDs rather than generating offsets. Independent checks cover CR/LF/CRLF, blank lines, nonterminated text, all Python line-separator forms, repeated lines, astral characters and combining Unicode without normalization.

All ten short unit fields are required. Empty conditions/dependencies and q0/r-empty are explicit model reports, not inferred eligibility or independent certainty. Unknown modality requires reported uncertainty. Endpoint-role first prerequisites must be endpoint units; prerequisite edges are total and acyclic. Relationship-member edges are distinct, total, unique and nonself, with at least two members; member cycles are intentionally permitted. Unknown/duplicate references, omitted fields, bad types, stale hashes, malformed graphs, contradictions, duplicate JSON keys, numeric overflow and non-stop/truncated responses reject. ID gaps are permitted. A 159-unit inventory can validate, while exactly 160 triggers the documented capacity stop even though the response schema permits the sentinel boundary; this is deliberate fail-closed behavior, not permission to abbreviate discovery.

Expansion preserves assertion, actor/purpose prose, force, conditions, prerequisites, members, uncertainty and evidence order. The public inverse verifies source-derived quotes, offsets and occurrences, including canonical distinctions such as boolean versus integer or float versus integer. Compact/expanded round trips reproduced exactly. The inverse does not prove model-authored prose is entailed by its evidence; freezing and comparing the original compact object remains a runtime obligation.

Whole-line evidence can contain several claims. Syntactic validation, an END marker, all span IDs cited, or a successful inverse cannot establish atomicity, exhaustive discovery, or semantic correctness. Synthetic semantic controls expose these limitations; they are not model observations. Proposed regulated duties, current participation, background and unresolved functions remain in discovery. No scope classification or candidate mapping call is added. Expanded completeness stays unverified and production/action readiness false.

## Sizing decision and limits

The exact full request reproduces at **14,668 body bytes / 15,692 guarded bytes**, including source, row texts, schema, prompt and settings. Short closed named fields and homogeneous arrays avoid tuple-schema assumptions. Provider acceptance remains unverified; local tests do not establish support for every schema constraint.

| Complete synthetic output | Bytes | At 3 bytes/token +256 | At 2 bytes/token +256 |
|---|---:|---:|---:|
| Representative64 | 8,691 | 3,153 (38.5%) | 4,602 (56.2%) |
| Stressed96 | 15,410 | 5,393 (65.8%) | 7,961 (97.2%) |
| Stressed128 | 24,674 | 8,481 (103.5%) | 12,593 (153.7%) |

The primary's proposed **3 bytes/token +256** policy meets representative64 <=70% and stressed96 <=85%. It is acceptable as a disclosed admission assumption for this one-call engineering diagnostic. It is not model-matched tokenization or a reliable upper bound. At 2 bytes/token, stressed96 fails the headroom target and leaves only **231** tokens. Stressed128 exceeds the entire cap by **289** tokens even at 3 bytes/token. Canonical synthetic fixtures also do not bound actual formatting whitespace, reasoning use, assertion lengths, uncertainty, member counts or inventory cardinality.

Keep these adverse sensitivities in the release record. Do not translate 64/96 fixture counts into discovery caps, drop units, shorten away meaning, salvage a prefix or change the representation after an outcome. An actual length/capacity/schema/refusal failure must remain a failed single attempt. No assertion that all legal schema outputs can fit is warranted.

## Next runtime/release gate

Preserve one inventory call, Sol low/OpenAI only, 8,192 output tokens, 40,000 guarded request bytes and nominal 2/10 routing caps. Prior debit **1,505,990,718** plus the **200,000,000** reservation gives **1,705,990,718 nanodollars**, leaving **294,009,282** under the unchanged 2,000,000,000 ceiling. Retain higher observed costs and the cache-write premium caveat; no nominal routing cap guarantees all-in billing. No retry, repair, fallback, second call, candidate/reference/gold input or scope/mapping stage is approved.

Runtime review must verify exact source/table/schema/request pins, complete raw/canonical output freezes, inverse equality, strict native finish/refusal handling, durable one-shot admission, failed-attempt accounting and immutable prior baseline. This receipt approves implementation only; actual authorization and native release remain primary-owned.

## Evidence

**197/197 independent checks passed; 13/13 owner tests reproduced.** The writing `offline_checks.py` was executed only in a temporary copy; its table, schema, request, four complete fixtures and result file regenerated byte-for-byte. All frozen owner artifacts were checked again afterward and remain unchanged. No evaluation gold/reference contents, prior truncated-prefix fixture, live API, credentials, signer/executor or provider call was used. Only new review/protocol artifacts were written.
