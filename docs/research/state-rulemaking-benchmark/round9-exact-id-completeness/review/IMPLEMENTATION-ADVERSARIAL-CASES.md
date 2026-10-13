# Independent implementation cases (prepared before builder READY)

Use only in-memory synthetic mutations and review-owned output. Never edit approved
protocol/endorsements/runtime/old evidence. Run only after the builder's stopped READY.
Recompute the protocol and primary-release pins first. Import code behind a network,
subprocess and credential-path guard with bytecode disabled; writes restricted to review.

1. Reproduce the exact full request, 38,432 bytes + 1,024 = 39,456. Use multibyte input to
   prove UTF-8 bytes are measured; allow exactly40,000 and reject40,001 without trimming.
   Verify no change to user source/record/evidence, model or provider constraints.
2. Request API must accept explicit source/record data, not harvest private audit/expected
   values. Poison private inputs with canaries and compare provider-visible bytes; inspect
   import/dependency paths to rule out reading evaluations during request construction.
3. Reject raw duplicate assessment, nested and top-level keys, including escaped Unicode
   spelling of the same key; malformed/trailing JSON, NaN/Infinity and wrong root types.
   Verify a valid permuted keyed object becomes exactly the same legacy field values.
4. Missing nested timing/component key, unknown/extra key, embedded item_id, bad document
   or payload binding, unknown contradiction reference and complete-plus-missing reject.
   Invalid evidence (wrong quote, occurrence, ambiguous repeated text) also rejects.
5. Ref resolver: unknown/external/missing ref, ref with siblings, cycle, definitions changed
   to weaker constraints, illegal schema keyword, excessive reference depth fail closed.
   A invalid assessment value under a reference must actually be rejected. No remote loads.
6. Duplicate or reserved input IDs, cross-category collision, empty or excessive schedules
   reject before producing a request; response order remains irrelevant. Record/source
   modification cannot be hidden by a caller-supplied schedule or stale hash.
7. All ten exact endorsed audits reproduce3 complete_supported,5 not_complete,2 unverified.
   The same audits with absent or original pending approvals are all unverified. No global
   model label or fixture expected result is an input to semantic aggregation.
8. Audit/review/document/source/record/reference/value hash mismatch, duplicate review IDs,
   same reviewer identities, audit-author self-endorsement, empty approvals, missing rows,
   duplicate/extra unit or claim IDs, field pointers or stale field hashes all unverified.
9. Unknown/partial source scope, truncated reviewed range, exclusions/unresolved questions,
   incomplete claim scope or unreviewed pointers all unverified despite positive labels.
10. Matched source mapping to evidence or coverage.rationale, missing reverse claim linkage,
    empty pointers or unsupported claim fails. Null/empty fields cannot discharge a source
    fact. Genuine omission with no pointers remains a known not_complete result.
11. Required endpoint omitted/unknown, missing dependency, self/cyclic dependency, parent
    falsely marked matched: fail closed. Correct phone subgroup still fails full recovery.
12. Unsupported compound-field addition with an explicit unsupported adjudication returns
    not_complete. A new record field without an audit row is unverified, never silently
    ignored. Unknown claims take precedence over defects for the overall semantic status.
13. Supported-label mutations cannot override uncertainty objects, unclear modality,
    unresolved association/channel/identity, or existing host acceptance guards.
14. Expected-label and fixture-ID mutations do not change computation; whole-notice
    production/action flags remain false. Test output must distinguish semantic gate,
    response structural validity and accepted verdict.
15. Recheck all4,995 historical files, final protocol21file manifest, release and primary
    approval hashes after testing. Re-run owner tests without their report writer so no
    runtime file changes; retain independent output in review.

For invariants below approval binding, synthetic tests may recompute an in-memory test
approval binding after a mutation. This simulates an already-reviewed but inconsistent
input and reaches the invariant being tested instead of stopping at a stale hash. Such
objects are explicitly adversarial test inputs, not actual endorsements or semantic
truth. They must never be written over the primary's approval file or exposed as a
runtime approval mechanism. The exact ten real fixture endorsements remain unchanged.
