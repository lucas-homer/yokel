# Cap-probe credential integration: required prebuild checks

2026-10-09. Scope reviewed against `execution/PRIMARY-SCOPE.md` and the existing
native/R8 service architecture. **Preparation review only; no v4 build approval
yet.** Implementation is in progress and generated policy/job/bindings are absent.
No runtime edits, source/reference truth inspection, credentials, enrollment,
Keychain/op/provider calls, or builds were performed. Changed only this report.

## Current adapter snapshot: pending integration changes

The adapter observed during implementation is still the R8 copy, hash
`9f6f5363d583f2269bce0c47aef2f64b414a516370779c9f05b23aec0eae2d80`.
It expects `round8.live-authorization.v1`, passes/records `max_new=24`, and checks
up to eight documents / forty pages. This does not match the new documented
cap-probe authorization or fixed three-attempt scope; do not build this snapshot.
This is an in-progress observation, not a claim about the implementer's final code.

The preparation script snapshot hash is
`fc27a620bc71731e682e36e020a0d33d8b0dd3b660ba68077f8d874d49f07a3f`.
Its inherited A/S/B entries are confined to the new ROOT. The final integration
must distinguish local freeze records from the reused original R8 B hash and
canonical read-only source dependencies outside the new ROOT. No external label
entry may be interpreted as truth by this review or the live adapter.

## Concrete final review gates

1. Final adapter binds the new implementation, canonical one-source manifest,
   authorization and prior debit with exact hashes. Its authorization shape agrees
   with the released cap-probe interface: new schema, shared $2 budget, immutable
   $0.100166 debit and debit hash, three new operations, one call per stage, inventory
   completion 12288, and original opaque R8 B hash. Binding local freeze B must not
   silently substitute a different hash for the original source-label release.
   Check and live argv/receipts must identify the new probe namespace and limits.
2. Fixed paths resolve only to this cap-probe adapter and `execution/run` output.
   Reused input dependencies resolve to the reviewed original R8 source files for
   `doc-92211b8c7ba0` and its pre-existing reference. Pin those exact file bytes and
   opaque reference/freeze records without reopening original R8 execution output.
   Review explicit runtime/implementation code dependencies, lineage, source pin,
   prior-debit evidence and every external file consumed for these checks; merely
   pinning the new source-manifest JSON does not pin its external file targets.
3. Generated dependencies include all final code/lineage/input/auth/debit/freeze
   files and the fixed Python executable, complete enumerated stdlib/extensions,
   top-level bundled dylibs, pypdf/PIL/cryptography/cffi, `_cffi_backend` and pypdf
   distribution metadata. Native job map must equal dependencies plus binding and
   dependencies JSON themselves. Every path must be canonical, present and hash
   matched. Compare hashes again after offline adapter check and before build.
   Earlier synthetic R8 import/native-library checks found no concrete missing
   package/library on this same runtime; any new imports require a bounded concrete
   closure check. Shared SITE additions, OS/network trust and same-user races remain
   the existing documented limits, not grounds for speculative whole-site hashing.
4. Exact argv is fixed bundled Python `-I -S -B`, this adapter, `--live-initial`;
   fixed timeout within native 1–3600 seconds, no shell/extra caller arguments,
   retry/resume/repair job, or environment overrides. Refuse existing probe run or
   intent before paid work; no automatic retry after uncertain dispatch. Offline
   `--check` reads no keys and makes zero provider calls. Primary's independent
   runtime reviewer owns extraction, paired-verifier and budget-ledger semantics.
5. V4 policy inherits the hash-verified installed policy's exact service-account,
   vault, op path/digest and two credential references. Its only job is the approved
   cap-probe initial invocation, exactly equal to generated native-job JSON; no
   round6/R8/generic jobs or broader vault/key scope. Record policy, binding, job
   and implementation hashes in final credential review before side-by-side build.

## Native trust and validation

Native source remains unchanged. It checks pins before Keychain lookup and before
payload exec, authenticates the service identity, suppresses output and removes
the service token before the actual Python payload. Keep those boundaries intact.
No new account/vault/key setup is implied.

The embedded-policy change creates a new ad-hoc binary identity; prior v3 trust
cannot be assumed. Primary first prepares the reviewed concrete v4 binary. If a
trust step is needed, the user runs that exact binary's `rotate-local` in a real
Mini terminal, entering the existing token directly at the hidden prompt and
authorizing only that binary. Successful ACL replacement trusts the new build;
older-binary trust should not be assumed to remain. Data/ACL replacement is not
atomic, so failure does not imply rollback. Validate identity and smoke with runtime
interaction disabled before the approved job. No remote token/provider-key rotation
is required merely for this local upgrade.

Final generated-artifact and policy-v4 review is pending the primary's ready signal.
