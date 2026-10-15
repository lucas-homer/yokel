# Consolidated final pre-freeze fix list

**Final disposition: resolved.** The final runtime READY receipt passes focused verification of this list. See `IMPLEMENTATION-REVIEW.md` and `implementation-review-final-verification.json`. The requirements below remain the historical bounded acceptance checklist.

This supersedes the rolling open-findings lists for deciding the remaining implementation work. No broader extraction features, scope expansion or new provider experiments are requested. The primary’s conservative merge proposal is approved. After the changes below, the reviewer will perform focused verification against the final owner receipt, rather than restart exploratory review.

## 1. Block date components crossing context boundaries

In runtime `local_gate`, before emitting a Jev request, require the complete value span to lie inside its declared context span, and require both spans to match retained source bytes/characters. A cross-block value is a deterministic review result; Jev cannot clear it. A runtime guard avoids modifying the proposer’s READY artifact.

Required cases: `Written comments close October 31\n\n2026 Legislative Calendar` and its form-feed equivalent must not call Jev or accept a date. A normal date and a single-line-wrapped `October 31,\n2026` within one paragraph may remain eligible. No more aggressive date parser is needed.

## 2. Apply the conservative field-level merge rule

When fallback exists, any unresolved candidate for a field in either channel blocks terminal acceptance for that field, even if its value equals the supported value in the other channel. A candidate is exempt only if a completed valid verifier result positively classifies its role as mismatched. Incompatible supported values also block. A channel with no candidate has missing evidence and may permit recovery from the other channel; it does not establish absence.

Retain `raw_literal` in every result row, including deterministic abstentions and null normalized dates. Null values must never erase unresolved candidates from the blocking decision. The working runtime now copies this field; preserve that change and test the actual `verify_record` path, not only a manually constructed merge row.

On a merge downgrade, keep every outward acceptance indicator consistent: `shadow_status=review`, `disposition=review` and action-readiness not ready. Provider verdicts remain in the immutable operation result. Document/case records before the terminal merge are provisional; evaluation must score only the final terminal observations and separately disclose earlier provisional results.

Required cases: empty native → supported OCR can pass; different supported values cannot; same-value native condition/lifecycle blocker → clean OCR cannot; null normalized native candidate cannot vanish; positively mismatched incidental email may be ignored; unknown/failed/unprocessed email competitor blocks; two matched email destinations block. Apply symmetrically to avoid OCR uncertainty silently disappearing behind native acceptance. The stricter two-role-only Jev soft list remains authoritative.

## 3. Freeze and report the existing accounting accurately

The per-operation budget fix is accepted: sum `max(reserve_i, observed/accounted_i)` and admit the next reservation against that sum. Unknown operation billing remains reserved. No new billing API or cost estimator is required.

For results, report OpenRouter `reported_cost_usd` as provider-reported charge, Jev input-usage times pinned rate as an estimate, and `budget_charge_usd` as conservative admission accounting. The OCR page-fee allowance currently added to `observed_cost_usd` is conservative accounting and may double-count the provider-reported fee; it must not be labeled an observed provider charge. This can be settled by clear frozen documentation plus evaluator use of the already retained separate fields; a schema rename is optional. Do not present the mixed `observed_accounted_usd` total as total actual charge.

## 4. Final handoff evidence, without new features

Update the stale integration note to the actual published manifest and override policy. Retain the final no-network test receipt, exact code/config hashes, Python/pypdf versions and native extraction command/version. Primary must bind the real source-label Freeze B to live authorization externally; the current runtime boolean is an attestation, not proof that labels were frozen. Runtime need not read labels or implement a new evaluator interface.

All 12 scheduled notices must remain in the evaluation accounting even if paused or failed. The primary may derive not-started/partial/completed states from the frozen manifest and retained operation/document records; a new runtime state-machine feature is unnecessary. Source isolation is code/data separation unless an actual filesystem boundary is enforced. OCR backend exact version remains unknown, and source-fidelity/notice-completeness remain unverified at runtime.

After these bounded fixes, owner returns READY plus final receipt/hash and stops edits. Reviewer verifies those bytes, records its own READY and stops edits; only then does the primary create Freeze A and authorize collection. No fresh sources or provider calls have been used in this review.
