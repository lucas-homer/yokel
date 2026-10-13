# Contract-probe credential boundary: initial code review

2026-10-11. **No material credential-boundary code issue found.** Final concrete
binding/dependency/job/policy-v5 approval remains pending primary preparation after
runtime review. Reviewed `execution/SCOPE.md`, service adapter/preparer/runbook,
runtime authorization/debit/import interface, nonsecret lineage and debit metadata,
and existing native runner boundary. No runtime/old-round edits, credentials,
enrollment, native builds, network/provider calls, or source/reference/model-output
interpretation. Changed only this new report.

Reviewed source hashes:

- Adapter: `356a3a1c074e0dbcad549179942a0a30ce64dc8e87f080f177bf335d64049d8f`.
- Preparer: `d131776a4f56f1797480b09c85d9977cae3be37c5fc045fcf5f2d0c2b1632d59`.
- Prior-debit metadata: `2dc9ff194922e02f3b17176e77237a5fa23a5a0b527a373bbf8c0a3ad42e6c61`.
- Native runner source: `b40d294dd46b44a3ced0313d60425863aa3e9fef7c49922869c5d85232e6bcce`.

## Isolation and exact authorization

The fixed adapter requires bundled Python `-I -S -B` and exact executable identity.
It accepts only check/live-initial, uses this probe's fixed implementation, manifest,
authorization, output and intent paths, and rejects existing run/intent before reading
injected keys. Check reads no environment credentials. Live requires absence of the
service token and only the two approved injected provider keys; it invokes no op,
Keychain, enrollment, caller override or retry. Generic errors retain no arbitrary
exception text; live output is suppressed and durable receipts have fixed metadata.

The adapter's expected authorization matches runtime `auth_scope` and INTERFACE:
contract-probe schema; exact implementation/manifest/original-B hashes; $2 budget;
$0.261774 prior debit and debit-file hash; at most three new operations, one per stage;
inventory completion 12288, stronger completion 4096; input guards 35000/40000 for
inventory/stronger and 64000/32000 for Jev total/longest state; fixed prompt delta
`90a6f51531f5e26c9e1530a9b7b6c9feebde3b0742e238303839b8c975bf70b6`.
Check/live calls and receipts consistently use three operations. Check requires one
document/two pages; runtime source admission fixes the reused original R8 WI paths.
Local A/S freezes are distinct from original opaque R8 B, verified under its old root.

## Dependency preparation and both prior debits

The generator uses the current `documents` manifest shape, includes external text/PDF
targets, implementation code/lineage, authorization and local freezes. It explicitly
includes original R8 B/E and cap-probe E with their file targets. External freeze
entries are checked for relative-path confinement, hash and size before inclusion.
The metadata-only membership comparison confirms both E freezes (20 entries each)
cover every prior-debit reference and the respective freeze file: four references for
R8 and five for cap-probe, including the latter's parsed result. This is closure
membership evidence; final review still checks each actual pinned byte/hash.

The prior-debit file is bound in authorization and implementation. Runtime verifies
the exact two old operation identities and their immutable files, and recomputes
max(reservation, reported cost) under the fixed cumulative debit. This reviewer read
that code and nonsecret debit metadata, not response/result contents. Semantic and
budget-ledger correctness are the independent runtime reviewer's responsibility.

The frozen prompt delta is among the 19 lineage file pins, with the same hash as
authorization. It therefore enters the implementation code map and native closure.
Interpreter/std-lib/extensions/dylibs and pypdf/PIL/cryptography/cffi/backend/metadata
enumeration matches the earlier reviewed architecture; no new service import requires
an additional package. Earlier synthetic import/native-library evidence found no
concrete missing dependency on this runtime. Shared SITE additions, OS/network trust
and same-user filesystem races remain the existing documented limits.

## Required final artifact review

Verify canonical paths/current hashes for every generated pin and all local A/S,
original B, both E freezes and their targets. Verify debit references, exact original
WI text/PDF paths, prompt delta and every implementation/lineage file are covered.
Native job must equal dependencies plus binding/dependencies JSON, with fixed bundled
Python `-I -S -B`, this adapter, `--live-initial`, no overrides and reviewed timeout.
V5 must retain the reviewed preceding account/vault/op/reference metadata exactly and
enable only the approved contract-probe initial job. Record exact policy/binding/job
hashes and check the unused output namespace before approving the side-by-side build.

Native credential architecture remains unchanged: pins precede Keychain lookup,
expected service identity is checked, output is suppressed and token is removed
before the actual Python payload. New embedded policy creates a new ad-hoc identity;
do not assume v4 ACL trust. Prepare the reviewed binary before any necessary hidden
TTY `rotate-local` using the existing token and authorization only for that binary.
Then validate identity/smoke with runtime Keychain interaction disabled. No vault,
account or provider-key recreation is implied; local data/ACL replacement remains
nonatomic and logged-in/unlocked-Keychain availability remains required.
