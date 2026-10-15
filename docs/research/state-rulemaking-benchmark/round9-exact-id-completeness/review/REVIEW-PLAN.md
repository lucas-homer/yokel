# Independent round9 review

Scope: offline research contract barrier, then independent implementation/adversarial review.
Own only this review directory. No provider calls, credentials, live state, production/shared
schema changes, new source labels, rewrites of historical artifacts, or other-task messages.

Contract acceptance:
- Expected IDs derive from a validated record, including nested timings/components; duplicate
  record IDs cannot collapse silently. Coverage metadata stays in global sections.
- Generated schema constrains legal IDs and exact count; host validation independently rejects
  extras, omissions, duplicates, malformed shape, mismatched source/payload bindings and
  unsupported/ambiguous evidence. It never drops, pads, salvages or repairs a result.
- Source-led semantic cases distinguish asserted content from attached evidence; whole alternative
  groups from locally correct subgroups; required/optional/conditional/unclear modality and scope.
- Meaningful positive/negative minimal pairs prevent trivial always-reject and literal-keyword
  implementations. Structural valid, semantic complete and accepted are distinct states.
- Unknowns fail closed without inventing certainty. Synthetic positives are local target controls,
  not proof that the full historical record is complete or that a verifier is accurate.
- Fixture expectations/reference assessments remain outside provider request builders. Generic
  instructions and exact record-derived schedules may be transmitted; tailored expected findings
  must not leak. No new production schema, paid invocation or automatic retry is authorized.
- Old files are preserved by the baseline; barrier decision binds exact protocol file hashes.

Implementation review will add adversarial cases in this directory, validate meaningful behavior,
inspect request construction for leakage and compare the prior baseline before final handoff.
