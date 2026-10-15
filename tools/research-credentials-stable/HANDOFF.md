# Stable candidate ready for independent review

2026-10-11. Edits stopped at handoff. No installed build, production signing key,
Keychain access/trust mutation, real op or provider call. Main runner unchanged.

Changed only the new worktree `tools/research-credentials-stable` candidate. The earlier
synthetic prototype is frozen under runner-stability-review/prototype with 27 controls.
Candidate native integration now passes **32 controls**, including the actual isolated
release CLI, same executable bytes across two signed provider subsets, credential/token/
environment/output boundaries, signature/policy/file rejection before fake op, replay/
substitution, timeout/cancellation descendants, owner-only synthetic key custody and
explicit authorize-existing rejection before any Keychain API in synthetic builds.
Python syntax, wrapper shell syntax and whitespace checks passed. TEST-RESULT.json
records detailed synthetic evidence; it does not establish live Keychain continuity.

The direct owner delegation authorizes **primary release of reviewed jobs within owner
scope/budgets**. Candidate uses a simple primary-accessible PEM key file outside repo/
eligible dependency roots, mode0600 in mode0700 directory. No separately protected
signer, remote infrastructure, second signing-Keychain loop, or independent-review
claim. Same-user/private-file/backup compromise risk is explicit. Existing service token
stays in native Keychain; no file token bootstrap/export route was added.

Important finalized interface points for primary/adapter reviewer:

- Signed job format in INTERFACE.md. Per-job provider subset, exact fixed isolated
  Python adapter grammar, all dependency/review hashes, fresh scope/job ID and expiry.
- Exact integer **nanodollars**; current paid job retains prior542976718, reserve161920000,
  ceiling2000000000. Zero-reserve reviewed no-provider-cost smoke is permitted. No fixed
  dollar ceiling in core, so future owner-authorized budget changes need no reader rebuild.
  Native checks signature/arithmetic, not billed spend/call-count or a cumulative ledger.
- Explicit real-TTY **authorize-existing** requests itemRef only (NULL length/data),
  replaces ACL with exact SelfPath trusted-app access, returns no token bytes and changes
  no token data. Synthetic guard precedes all Keychain APIs. It never runs automatically.
  Actual prompt/ACL behavior is untested; reviewer must inspect exact function before
  primary presents it to the user. Manual rotate-local remains the nonautomatic fallback.
- Immutable core includes account/vault/op digest/ref envelope, public key, paths/roots,
  fixed Python path and timeout. Changing those is maintenance; job releases alone
  preserve executor bytes. Actual installation/core/public key paths are primary-owned.

Remaining gate: independent review of native parser/admission, signature format,
release-key custody and exact ACL construction, followed by primary-controlled key
creation/core build and user-controlled migration. Then verify identity/smoke and two
different zero-cost signed jobs without rebuilding or another ACL authorization before
any paid run. Do not infer continuity from these synthetic tests.

README documents recovery/no auto-retry, partial publication, claim consumption, key
compromise/rotation, deprecated API/live gaps, filesystem/same-user limits and provider
spend reliance on reviewed adapters. No existing job/frozen pin was repurposed.
