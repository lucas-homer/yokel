# Stable research credential executor — candidate

2026-10-11. **Candidate for independent review, not installed or enrolled.** Worktree
only; the main checkout and current credential runner are unchanged. Synthetic native
tests passed 32 controls with temporary synthetic signing keys/fake op and zero actual
Keychain/provider access. TEST-RESULT.json is evidence of code behavior, not macOS trust
continuity. Production signing-key creation, finalized core, build/install, migration
and live jobs remain primary-owned after review.

## Authority and custody

The user directly chose **“Primary releases reviewed jobs within my authorized scope
and budgets.”** Primary recorded OWNER-DELEGATION.md and ADR 0012; this candidate does
not amend those. Signed manifests authenticate the delegated primary release, not an
independent signer, human review or semantic correctness. No remote signer or extra
signer Keychain permission loop is added.

Use one primary-controlled P-256 PEM release key in an owner-only file outside the
repo, adapter roots and dependency roots. Proposed location:
`~/.local/share/yokel/research-credentials/release-key.pem`, parent mode0700, file0600.
Actual paths and production key creation are primary decisions. release.py rejects
symlinks, wrong ownership, insecure permissions, a repo/dependency/adapter-root key,
oversized/non-P256 keys and public-key mismatch. It never prints private material,
places it in an argument/environment, copies it into a manifest, or generates a key.
The isolated wrapper strips inherited environment/startup hooks before loading it.

**This is an unencrypted signing-key file accessible to the primary and other processes
under the same OS user.** Ownership/location prevent accidental sharing/commit, not
same-user compromise or theft from backups. FileVault/backup settings are not changed
or asserted. Key theft permits signed jobs within the core envelope and access/spend
with those jobs' injected provider keys. User delegation consciously accepts primary
release authority; do not describe the file as nonexportable or independently protected.
The existing 1Password bootstrap token remains only in native Keychain and human
1Password recovery custody; it is not moved to this signing-key file.

## What is stable and enforced

One hardened native executable embeds immutable account/vault/op/reference policy,
public verification key, fixed registry/claim directories, Python path, adapter/dependency
roots and maximum timeout. New reviewed experiments change signed job manifests only.
The core permits at most the existing OpenRouter/TypeSafe reference envelope and grants
a job its signed nonempty subset. No per-job account/vault/item/field/op/public-key or
environment override. Main Native identity/Keychain/TTY/environment/token/output and
process-group code was adapted from the reviewed runner; no generic credential reader
or export command was added. Header Manifest.h contains only nonsecret admission code.

Manifest interface is in INTERFACE.md. Detached P-256 ECDSA/SHA-256 signatures cover
`yokel.research-job.v1\0` plus exact canonical UTF-8 JSON bytes. Dictionaries use explicit
UTF-8 bytewise lexical key ordering, compact JSON and safe exact integers. This avoids
Foundation's locale-like sorted-key behavior. Re-encoding rejects duplicate fields,
alternate number formats and malformed/noncanonical signed bytes. All fields/schema
are exact, documents <=4 MiB, signature <=128 bytes, at most10000 file pins, depth<=64.

`run JOB_ID` derives filenames from the compiled registry, verifies signature/scope,
expiry (up to7days), canonical roots, review/file pins and fixed argv:
`python3.12 -I -S -B /reviewed/.../adapter.py --live-initial`. Both Python and adapter
are pinned. Owner-only registry/claim directories and manifest/signature files are
required; paths are canonical. Signature/pins/op checks precede Keychain access.
Stages verify the expected original manifest hash again, and payload pins are checked
again before exec. Registry names are constrained identifiers, not caller paths.

An exclusive/fsynced one-shot claim is made before token lookup/paid dispatch. Failures
do not clear it or retry; a new explicit release/run ID is needed. A changed signed
definition under an already consumed ID also fails. This is accidental-replay protection,
not hostile-user rollback, journal deletion or clock protection. Key/file hash checks
do not eliminate filesystem check/exec races. Signed Python is trusted code with HOME
and same-user access; this candidate is not a sandbox.

**Budget is per-signed-release metadata, not a native bill guarantee.** Nanodollars
retain all nine decimal places (current prior542976718). Native/helper reject booleans,
unsafe integers, negatives and prior+reservation exceeding the signed ceiling. There
is no compiled $2 cap requiring a rebuild for future owner-authorized budgets; each
release must stay within actual owner authorization. Only numerical exactness is
hard bounded at2^52-1 per value. Current experiment remains ceiling2000000000,
reservation161920000, aggregate704896718. Zero reservation is permitted for reviewed
credential-smoke payloads that make no provider calls; native code does not block
their networking. Adapter/ledger enforces actual protocol budgets, calls, failed/uncertain
states and conservative debit chain. No cumulative monetary journal or transport broker
was added. Review receipts are signed provenance/file bindings, not unforgeable proof
against the delegated primary.

Changing job budget/namespace/provider subset within the core needs no new executable.
Changing service/reference scope, verifier public key, fixed Python path, op path/digest,
root envelope or executor code remains a reviewed maintenance rebuild and may need
Keychain reauthorization while ad-hoc signed. CLI/interpreter updates are occasional
maintenance; they are not silently accepted. No reboot/locked-Keychain availability
promise is made.

## Commands and release workflow

| Command | Credential/provider behavior |
| --- | --- |
| check-policy | Core/public-key/path validation only. |
| check-job ID | Signature/grammar/current file/op pins; no credentials/op/provider calls. |
| identity | Native token lookup and expected service-account identity; no provider request. |
| smoke | Core's existing reference map injection; no provider request. |
| run ID | Signed provider subset and exact fixed job, one-shot. |
| enroll / rotate-local | Existing hidden real-TTY user flow; not performed here. |
| authorize-existing | Explicit real-TTY ACL-only user migration; no password bytes requested; not performed here. |

Future primary/operator steps, **not actions already performed**:

1. Finalize registry/jobs and claims directories mode0700 outside the repo, exact core
   metadata/public key from the protected primary-created key, and actual existing
   references. config.example.json contains placeholders and cannot be deployed.
2. Build to a new side-by-side absolute path with build.py using reviewed core.json.
   The utility preserves runtime/restrict/kill ad-hoc signing, no permissive entitlements,
   refuses an existing output and runs check-policy. It reads only nonsecret core data.
3. Prepare a frozen proposal with exact argv/pins/review receipt, authorized scope ID,
   expiry, necessary provider subset and conservative budget. Review against the owner's
   instruction and complete adapter/ledger independently. Unsigned proposal is not authority.
4. Run `/bin/sh release_job.sh --core /reviewed/core.json --proposal /reviewed/job.json
   --key-file /owner-only/release-key.pem --executor /reviewed/stable-executor`.
   The utility verifies metadata/current pins before loading the key, checks key/public
   identity, writes registry JSON/signature exclusively, fsyncs and invokes check-job.
   It prints only release ID/hash/state. No overwrites; partial/failed publication is
   fail-closed and requires manual nonsecret publication review. A native check failure
   does not implicitly remove or revise signed files. No secret resolution occurs.
5. Primary presents the one-time real-TTY `authorize-existing` command to the user for
   this exact reader. It requests only the fixed existing item reference, then replaces
   its access object with trust for SelfPath only; no token is retrieved/replaced.
   It requires an unlocked default Keychain and may show macOS authorization. Runtime
   never invokes it automatically. If this untested live path fails, primary reviews
   the actual state and may present manual rotate-local, with direct hidden token
   reentry. Data/ACL rotation is nonatomic. Validate identity/smoke with interaction disabled.
6. Run two newly signed, no-provider-cost smoke adapters sequentially without rebuilding
   the executor; verify no repeat Keychain authorization and necessary provider subset.
   Only actual post-migration checks can establish continuity. No paid job is authorized
   by passing this candidate suite.

Normal new jobs use steps3–4 then `run ID` under prior owner authorization, not a reader
rebuild. Signing-key compromise requires stop/revoke releases, rotate any exposed provider
keys as appropriate and migrate the public-key/executor trust; deletion of the private
key does not invalidate already signed manifests. Keep token/provider rotation separate.

## Synthetic validation and limits

test.py compiles only a temporary **synthetic build** with ephemeral P-256 keys and
fake op; all synthetic Keychain entry paths fail before any Keychain API. Temporary
synthetic private PEM is deleted with its temporary directory. Tests cover inherited
native identity/environment/output/timeout selftest; two provider subsets with same
executor bytes; token removal/output suppression; real enrollment/read denied;
signed zero-reserve smoke; later signed ceiling without rebuild (synthetic only);
the full protected-file release CLI; unsigned/tampered/wrong-key/duplicate fields;
scope/argv/isolation/budget/expiry/key override/missing or drifted pins; zero fake-op
calls on invalid jobs; bound manifest substitution; one-shot replay; cancellation
and descendant timeout cleanup; insecure key permissions and no publication overwrite.
It also proves authorize-existing is rejected in synthetic builds before any Keychain
API. The implementation's NULL-password item-reference lookup is supported by Apple's
[SecKeychainFindGenericPassword documentation](https://developer.apple.com/documentation/security/seckeychainfindgenericpassword(_:_:_:_:_:_:_:_:));
[SecKeychainItemSetAccess](https://developer.apple.com/documentation/security/seckeychainitemsetaccess(_:_:))
replaces the item's access object. The command uses the same exact-application
SecTrustedApplication/SecAccess construction as enrollment, not all applications.
The APIs are deprecated, as in the existing runner. Synthetic tests do not establish
that macOS will accept the ACL mutation, what prompts occur, or continuity; reviewer
must inspect the exact function before primary/user migration. It exposes no general
item selector, password pointer, CLI override or automatic fallback.

Core registry/claims paths are checked each launch; no daemon/install or dependency
install was performed. Tests ran with scoped filesystem escalation solely to write
the new worktree candidate and temporary native test artifacts. Reproduction uses the
installed bundled Python with `-I -S -B`, adding only its reviewed site-packages for
test/release cryptography imports. No actual op/provider call, production key, enrollment
or installed build occurred. Independent review and production-path validation remain.
