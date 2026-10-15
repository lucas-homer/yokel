# 0012. Separate research job releases from the trusted credential executable

- Status: Accepted; implementation reviewed and built, owner Keychain migration and live validation pending
- Date: 2026-10-11

## Context

The native Mac Mini service-account runner removed desktop 1Password approval from research execution, but each new compiled-in job changes its ad-hoc signing identity. The installed v6 designated requirement is a specific code hash. Rebuilding for every experiment has therefore recreated the recurring authorization problem at the macOS Keychain layer.

The owner explicitly chose: “Primary releases reviewed jobs within my authorized scope and budgets.” This delegates job release to the primary task; it does not require an independent signing service or per-job owner interaction.

## Decision

Keep a stable native credential executor and release separately signed immutable job manifests. The primary controls release authority for reviewed DocketClock research within owner-authorized scope and budgets. Signatures establish integrity and approved artifact identity; they do not establish independence from the primary.

Keep the existing service-account identity, research vault, limited provider-reference envelope, token isolation, sanitized environments, suppressed subprocess output, bounded execution, and disabled runtime Keychain interaction. A job requests only its needed permitted provider keys. Bind its fixed isolated Python adapter, reviewed dependencies and inputs, expiration, unique execution identity, and timeout. Reject invalid signatures, scope expansion, drift, and consumed execution identities before credential-bearing dispatch.

Keep the bootstrap token in Keychain. Final signer custody and the production implementation must be reviewed before installation. Do not put signing secrets or service/provider credentials in the repository, logs, arguments, or chat. No cluster service, generic credential reader, relaxed OS security setting, or production data deployment is part of this change.

## Consequences

- Ordinary job changes can leave the Keychain-trusted executable unchanged. Verify this with two signed jobs after migration; synthetic tests alone do not prove real no-prompt behavior.
- Installing the replacement may require one owner-mediated trust update. Executor changes, key replacement, OS/session conditions, and maintenance can still require intervention; this is not a promise of permanently prompt-free operation.
- The release authority can authorize code using permitted provider credentials. This is an explicit owner delegation, not a security boundary against the primary or a hostile same-user process.
- Per-job spending and provider-call limits remain enforced by reviewed adapter and ledger code. A manifest budget is not an independent guarantee on provider billing.
- New providers, projects, increased budgets, or production changes still require authorization outside the existing research scope.
- Existing experimental records and failed-attempt reservations remain immutable; this migration does not reset research budgets or authorize reruns.

Evidence and exact delegation: [runner review](../research/state-rulemaking-benchmark/runner-stability-review/RECOMMENDATION.md) and [owner delegation](../research/state-rulemaking-benchmark/runner-stability-review/OWNER-DELEGATION.md).
