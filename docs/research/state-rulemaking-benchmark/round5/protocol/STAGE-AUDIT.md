# Round-five separate stage audit

Use a small post-run JSON mapping, not a new evaluator. Freeze this contract before collection. It supplements the unchanged round-four terminal evaluator and never supplies runtime inputs or promotes rejected candidates.

One record per frozen eligible source field ID; retain `document_id`, `source_field_id`, `field_type`, `distinct_value_group`, exact source-normalized value and role. Duplicate mentions may each be mapped, but aggregate recovery and recall once per frozen distinct eligible fact group. Include all eligible facts, including failed or unstarted documents. Report DATE, EMAIL and pooled counts separately.

For each fact retain:

- `native_evidence`: faithful, absent_or_corrupt, or unknown, with exact retained native span/hash and source-page basis where available.
- `candidate_mapping`: found, omitted, or unknown. A found candidate must carry the exact eligible value and intended role within matching scope. Record every matching case ID, retained raw literal, candidate role and source scope. A coincidental same value in another role or scope is not a match; unknown scope cannot establish a match.
- `hard_blocked`: true, false, or null; matching case IDs and deterministic reason codes establish the answer.
- `reached_jev`: true, false, or null; durable request/response/status records distinguish POST attempted, successful judgment, failed or uncertain POST, and not attempted. A dry-run plan does not establish a POST.
- `terminal_accepted`: true, false, or null, tied to the terminal record and independent acceptance audit. Provisional favorable scores are insufficient.
- `loss_stage`: recovered, native_omission_or_corruption, candidate_omission, deterministic_block, verifier_nonacceptance, execution_stop, or unmeasured; preserve contributing blockers where several apply. Verifier nonacceptance requires a completed valid judgment, not a failed call.
- Reviewer identity, artifact hashes and concise evidence for the mapping.

Source candidate recall uses the full frozen eligible fact denominator. Conditional recall on faithful native text includes only independently established faithful facts; unknown fidelity is excluded from this conditional metric and disclosed. Later-stage rates must state their denominator explicitly. Do not force unknown facts into an omission category or infer routing/model losses from terminal review alone. Audits are source-grounded and performed after outputs are retained, separately from the image-only reference labels frozen before those outputs.

Cost per correct accepted field is reported only for a positive independently audited correct acceptance count, identifying whether its numerator is provider-reported or conservative accounted spend. With no correct accepts, the ratio is null/not estimable.
