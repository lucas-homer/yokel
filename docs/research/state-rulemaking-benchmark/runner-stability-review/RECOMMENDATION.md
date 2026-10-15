# Stable research runner: architecture review

2026-10-11. Review/specification only. Existing runner/build/runbook/ADR were read;
public Apple documentation was consulted. No builds, key/Keychain access, signing
identity/private-key inventory, credential retrieval, ACL changes or implementation
occurred. Nonsecret `codesign --display -r -` metadata was inspected.

## Answer and existing capability

The current design can require another native Keychain authorization whenever a
new policy is compiled into a new runner. `build.py` embeds policy bytes and signs
ad hoc (`--sign -`); `Enroll` trusts SelfPath through SecTrustedApplication and
replaces the item's access object. Apple explains that ad-hoc designated requirements
are tied to the specific code version. Changed bytes therefore cannot be assumed
to retain trust merely because the filename, install directory or identifier matches.
[Apple TN3127](https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements).

Read-only inspection of installed v6 confirmed its actual requirement:
`designated => cdhash H"691cd655aae540caf887bff777bd48c9ef192326"`.
This is concrete per-build identity evidence, not merely a general hypothesis.

This is native macOS Keychain authorization for the bootstrap token. It is distinct
from 1Password desktop approval: runtime already uses service-account authentication,
disables desktop integration process-locally, checks the service identity, and disables
Keychain interaction. The research vault's read-only permission authorizes credential
reads; it neither admits arbitrary local jobs nor limits spending by retrieved keys.
An unlocked logged-in Keychain remains necessary even with stable executable trust.

There is **no implemented safe new-job capability in today's binary that avoids this
transition**. Policy is embedded, and run accepts only compiled jobs and matching pins.
There is no external job loader, signature verifier, token-export API or ACL-only
upgrade command. Reusing an old completed job, changing frozen pins/files, renaming a
new ad-hoc build, or trusting a shell/interpreter would not implement this capability.
Current new binaries should fail closed if not trusted. `rotate-local` can authorize
the new build with hidden token reentry; it is not remote token rotation and its data/
ACL writes are nonatomic. This review did not establish any current binary's ACL state.

## Recommended durable design

Keep **one small native credential executor byte-stable**, move per-experiment job
data into **externally signed immutable manifests**, and retain narrowly scoped
Keychain trust for that executor. New experiment artifacts change the manifest, not
the Keychain reader. One migration trust step is expected; ordinary manifest releases
then need job approval/signing, not another macOS credential-reader enrollment.
Core executor changes or embedded verification-key changes may still need a trust step
while ad-hoc signed. This removes per-experiment rebuilds, not all future maintenance.

Immutable executor policy contains the Keychain item identity; exact service-account
and vault IDs; maximum provider reference map; fixed public verification key; schema/
algorithm/domain version; registry/runtime path constraints; maximum timeout; and
allowed interpreter/argument template. Keep the existing two credential references
as the maximum scope. A job may select a subset, never substitute a vault/item/field
or add a provider. A stronger-only job should receive only OpenRouter; old references
must not be changed to broaden scope under the guise of a new job.

Initial invocation is `run JOB_ID`, with registry path derived by the executor.
No caller-provided argv, manifest path, key, environment or reference override.
The signed job fixes canonical Python path, `-I -S -B`, canonical reviewed adapter,
fixed mode, all dependency/input/freeze/auth hashes, timeout, output namespace, unique
run ID and expiry. Allow only this interpreter/argument grammar in the initial design;
new executable types require executor-policy review. Published manifests are data
authority to execute their exact reviewed code, not an arbitrary-command interface.

Use detached signatures over exact UTF-8 manifest bytes with a protocol/domain prefix.
For example, P-256 ECDSA/SHA-256 via Security.framework is a concrete native candidate;
verify support and known-answer vectors on the Mini during implementation. Apple's
[algorithm documentation](https://developer.apple.com/documentation/security/seckeyalgorithm/ecdsasignaturemessagex962sha256)
and [signature verification API](https://developer.apple.com/documentation/security/seckeyverifysignature(_:_:_:_:_:))
provide the API basis; no algorithm/key was installed or tested here.

Bound signature/document size (proposed 4 MiB, sufficient for the reviewed ~1700–2600
pins), reject duplicate JSON keys/unknown fields/type ambiguity, verify the signature
with only the embedded key, then parse the exact signed bytes. Never allow a manifest
to supply its own trusted verification key. Pin op's canonical path/digest in the
signed runtime binding within the executor's allowed installation family; this permits
reviewed CLI upgrades without recompiling account/vault scope. Check op and every job
pin before Keychain lookup, again before dispatch, and at the payload boundary.

Preserve existing identity check, environment sanitation, process-local integration
flags, token removal before actual payload, output suppression, timeout/process-group
cleanup, no desktop fallback and no daemonization. Pass the manifest identity/hash
through stages; every stage must verify the same signed bytes/hash, not accept a
substituted valid manifest between credential resolution and exec. Child internal
entry points must not read Keychain. Direct calls to them must not create a token
export or extra credential-resolution route.

Claim a unique run ID atomically in a persistent owner-only journal before credential
resolution/paid launch; a consumed or changed ID fails closed. Keep adapter output/
intent guards too. Failures do not automatically clear the claim or retry; a reviewed
replacement authorization is needed. Expiry, revocation and deletion should be
specified, but a same-user attacker can roll back local journal/clock/state: this is
the existing accidental-misuse boundary, not hostile-user replay protection. Shared
import paths and filesystem check/exec races also remain unless separately hardened.

Budget/operation fields bind approval to reviewed adapter/ledger behavior; a simple
executor cannot prove arbitrary signed Python respects them or cap network bills.
Native-enforced limits are signature/scope/argv/pins/launch count/timeout. Claiming
independent per-provider spending enforcement would require a separately designed
transport broker, beyond this minimal migration.

## Approval authority and signing-key custody

The manifest private key is **execution authority over jobs receiving provider keys**.
Keep it outside runner/adapter/experiment checkout and outside the research service
account. Embed only the public key. Do not put the private key in the same writable
agent environment or grant its use to an unrestricted local signing command: that
would let an agent admit unreviewed credential-bearing code, defeating the purpose.

Default release authority is the human owner or a separately protected release signer
acting under explicit owner delegation. Human-reviewed signing is simple but still
requires a release action per job; it removes OS trust churn, not human involvement.
For unattended approved work, the owner must authorize a standing signer workflow
with concrete project/provider/budget/job-type bounds. That signer validates the exact
reviewed artifact digests and approval evidence before signing and records receipts.
It must not sign arbitrary inputs on request. A second agent's prose review alone is
not an independent cryptographic approval mechanism.

A hardware/user-presence key could require a touch every job, replacing rather than
solving the user's interaction burden. Protected CI/another-host release signing can
avoid that touch but adds service availability and custody/policy work. No such signer,
key or standing release delegation has been verified as available here. Establish
that boundary before describing future launches as fully autonomous. If the owner
instead entrusts the primary agent with unrestricted signing, disclose that it can
authorize any job within the executor's hard envelope; signatures then provide artifact
integrity/provenance, not independent approval from that agent.

## Alternative: stable macOS signing identity

The shorter change is to retain embedded policies but sign every reviewed build using
the same controlled certificate/private key, explicit code identifier and appropriate
stable designated requirement. Apple documents identity continuity across versions;
it also describes self-signed identities for local Keychain-related use. Developer ID
is a distribution choice, not a demonstrated requirement for this private Mini tool.
[Apple code-signature explanation](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/AboutCS/AboutCS.html),
[Apple signing/update procedure](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Procedures/Procedures.html).

Apple's [TN2206](https://developer.apple.com/library/archive/technotes/tn2206/) also
describes Keychain identity tracking through designated requirements and local
self-signed identities. It warns that self-signed identities lack normal certificate
revocation. Plan explicit ACL migration/removal and executor replacement on compromise;
do not assume deleting the private key or certificate revokes previously signed code.

This can preserve narrow application identity across rebuilt policies, but changes
trust from one reviewed code version to whoever can sign that identity. Signing-key
custody is therefore at least as consequential as manifest custody. Do not use an
identifier-only/ad-hoc requirement or broadly trust a team/all applications. Pin the
actual signer/identifier; plan certificate renewal/revocation; retain hardened flags
and no permissive entitlements. Custom ACL behavior and two successive builds must
be verified on the actual Mini before promising continuity. Existing certificates,
private-key permissions and availability are unknown; none was enumerated.

Choose this alternative if a suitable protected code-signing release identity already
exists and minimizing code changes is the priority. Prefer the stable executor plus
signed manifests for the durable experiment workflow: it separates executor updates
from job approval and keeps per-job code/pins reviewable without a rebuild. Stable
certificate signing can later complement it for infrequent executor updates.

## Migration and validation specification

1. Primary selects approval/signing custody and owner-approved hard scope. Record an
   ADR amendment/new ADR for the consequential shift from embedded per-build policy.
   No ACL or credential change is required during specification and synthetic work.
2. Implement/review the native loader and release format, preserving frozen experiments.
   Test bad signatures/keys, duplicate fields, scope expansion, wrong service identity,
   drifted op/job/dependency pins, manifest substitution, expiry/consumed run IDs,
   token/environment/output boundaries and cancellation with synthetic data only.
3. Build the concrete hardened executor side by side, publish its digest/public key
   and exact manifest review evidence. Test releases under a synthetic signing key;
   production key enrollment/custody is a distinct controlled action.
4. One user-controlled Mini terminal trust migration to that exact executor is expected.
   Existing hidden `rotate-local` is the available pattern; a future metadata-only ACL
   migration must be separately reviewed and is not implemented today. Never route
   the token through chat, files, environment assignments or generic readers.
5. Validate identity/smoke with runtime interaction disabled; then add a second signed
   synthetic non-provider job without altering the executor and verify no repeated
   Keychain approval. Confirm consumed-job and unsigned-job rejection. Validate locked
   1Password desktop separately from screen lock/logout/reboot/locked-Keychain states.
6. New job releases thereafter require frozen reviewed manifests and signer approval,
   not a new reader binary. Token rotation, new credential scope, signing-key migration,
   core executor updates and OS availability changes remain separate maintenance events.

No immediate no-prompt workaround is recommended for today's newly compiled runner.
Primary can choose the durable design before building another experimental binary;
this report changes no current execution authority or security setting.
