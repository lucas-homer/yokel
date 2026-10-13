# Planned independent adversarial probes

These are review obligations, not a competing contract or provider-visible expectations.
Concrete tests will follow the keeper's approved interface without editing implementation.

Structural probes:
1. Same-count duplicate-one/drop-another, with different reasons/evidence on duplicate rows.
2. Extra metadata pseudo-item plus otherwise complete assessments; missing nested timing or
   route component; unknown ID; case/Unicode/whitespace variation; duplicate input-record ID.
3. Reorder assessments without changing IDs (set semantics unless contract explicitly says
   order is meaningful); legal record ID that resembles metadata, if input contract allows it.
4. Missing global coverage/source-identity section, malformed/null/type-confused assessment,
   additional unknown properties, duplicate JSON keys, mismatched document/payload identity.
5. Valid-looking quoted evidence that is absent, ambiguously repeated or wrong occurrence.
6. Source/record/schedule mutation after request construction; no trust in caller-supplied
   expected IDs, fixture labels or fabricated request-schema digest.

Semantic probes, using fixture inputs rather than accepting supplied expected labels:
7. Exact supporting quote includes detail, but actual assertion field omits it; add assertion
   only in the positive pair. Keep evidence constant so evidence-presence cannot solve the test.
8. Both routes exist and phone-only alternatives are correct, but full Zoom/phone relation
   is absent; add full relation in positive pair without conflating registration with access.
9. Correct evidence with unclear, wrong, or wrongly scoped requirement modality versus a
   correct resolved field. Genuine source ambiguity must remain uncertain rather than fail
   factual preservation automatically or claim complete preservation.
10. A structural pass with all semantic targets failing; a structural failure with plausible
    semantic findings; correct response IDs do not confer semantic acceptance.
11. Rename IDs consistently and reorder unrelated record items; test behavior must not rely
    on historical item names, fixture IDs, expected-output presence or fixture ordering.
12. A positive local target does not certify whole-source completeness, other target families,
    the historical record, source truth, production eligibility, confidence or accuracy.

Leakage/provenance probes:
13. Poison evaluation-only expected/reviewer labels with unmistakable canaries. Request
    construction must never contain those values or target-specific reference conclusions.
14. Remove or modify evaluation expectations without changing source/record input; provider
    request must remain identical. Same constraints apply to explanations and fixture names.
15. Preserve source labels and all historical files. Record generated fixtures as reused
    development regressions, not a held-out or human-gold sample. No live execution surface.
