# Synthetic stable-executor prototype — handoff

2026-10-11. **27 controls passed. Edits stopped at handoff.** This is a native
Objective-C signature/policy/dispatch prototype, not a production credential runner.
No production source, Keychain item, identity, provider credential or deployment was
changed. No op, network or provider call occurred. Production runner.m remains hash
`b40d294dd46b44a3ced0313d60425863aa3e9fef7c49922869c5d85232e6bcce`.

## Proof delivered

The exact same executor bytes accepted and ran two different signed definitions:

| Job | Manifest SHA-256 |
| --- | --- |
| job-alpha | `223eb435f1d221e02b444d3397624bb24751eb5405bde77f5c1a3f1a90bc0510` |
| job-beta | `d96bfa73f4cbcc1a18ec649cedb7f94f05cec2798a9f2ae2ac1c99004940987d` |

Executor SHA-256 for both:
`96d1f74b2b253a68067fe1f1336fbc406f0ea2048d9ec12ac4549ed922a774ff`.
RESULT.json records every control and the active synthetic artifact directory.

The Python harness generated an ephemeral P-256 key in memory. It never exported or
persisted the private key. Only the public key was embedded into the native executor;
job manifests and detached signatures are public synthetic data. Compiler use was
limited to installed Apple clang and Foundation/Security, with installed bundled
Python/cryptography; no dependency installation or real code-signing identity was used.

Registry files intentionally include mutated/rejected fixtures at final test state;
RESULT records the accepted pre-mutation manifest hashes. These are test artifacts,
not a publication registry or a release of any job.

The executor verifies ECDSA/SHA-256 over a fixed domain prefix plus exact manifest
bytes, rejects unknown/duplicate/noncanonical JSON fields, fixes project and synthetic
provider scope, and admits only a pinned fixture executable with `--fixture alpha|beta`.
It supplies exactly PATH/LANG/SYNTHETIC_PROVIDER, suppresses output, and atomically
creates/fsyncs a one-shot job-ID claim before launch. An expected manifest hash is
checked again at the dispatch boundary. No Keychain API or credential reader exists.

Controls cover unsigned/tampered/wrong-key manifests; real-provider/other-project
scope; timeout/boolean/numeric envelope violations; wrong executable/mode/additional
argv; caller environment/key override fields; missing/mismatched payload integrity;
validly signed manifest substitution at the stage boundary; payload drift; replay
of completed jobs and replay with a changed signed definition under the same ID.
Both accepted payloads verify the exact environment, with synthetic inherited OP/
provider/Python/HOME variables excluded. The executor hash remained unchanged.

The initial acceptance test caught a Python/Foundation float canonicalization mismatch:
0.54 reserialized as 0.54000000000000004. Evidence isolated the failure after successful
signature verification. The prototype uses integer microdollars instead, and the full
suite passes. Production research accounting needs **integer nanodollars** (or rigorously
specified fixed decimals), preserving all nine decimals of current prior debit; do not
round real accounting to this synthetic fixture's microdollar scale.

## Precisely what remains unimplemented

- No Keychain enrollment/read/ACL continuity, service-account identity check, op pinning,
  real reference injection or token-removal bridge is present. Synthetic success proves
  no macOS trust continuity. Production migration still needs a reviewed executor build,
  one-time exact-reader trust authorization and actual prompt-free identity/smoke checks.
- Only one benign fixture executable is admitted. Production fixed Python grammar,
  thousands of code/input/lineage/dependency pins, provider subsets and job releases are
  not implemented. Full path/root/symlink/race hardening and immutable cross-stage
  manifest transport remain production work; this stage-check test is deterministic
  substitution rejection, not a hostile filesystem-race proof.
- The atomic journal prevents ID reuse in this test state, not hostile-user rollback,
  clock manipulation, distributed concurrency, manifest expiry or revocation. It does
  not maintain a shared cumulative monetary ledger. Signed per-manifest synthetic
  budget fields are checked, not billed spend or reservations across arbitrary job IDs.
- Timeout terminates the benign child only. Reliable process-group cleanup, SIGKILL
  fallback, cancellation, descendant handling, core-dump protection and hardened signing
  need the existing production behavior carried across and verified.
- The test signer is not a release authority: it can sign arbitrary synthetic fixture
  inputs and is destroyed at process exit. Production custody, standing delegation,
  release policy, key compromise/rotation, audit receipts and genuine independent
  approval evidence are not supplied by these tests. No hidden real signing key exists.
- Schema/size bounds (1 MiB here), known-answer signature vectors, bad-input fuzzing,
  operational recovery and OS/library availability need production review. Prototype
  check-line diagnostics reveal no values but are not the production error contract.

## Proposed proportional unattended authority

Use a **local, constrained native release signer plus the stable executor**, rather
than remote infrastructure. The owner explicitly delegates bounded release authority
to the primary research operator, while keeping a nonexportable signing key accessible
only to that release signer. Agents must not read/export the private key or invoke an
unrestricted sign-bytes API. The signer admits an exact versioned manifest grammar and
validates release policy, artifact/review digests, and its persistent reservation ledger
before issuing a signature. One initial signer/executor trust setup may be required.
This is proposed custody, not an installed or tested capability.

Owner-approved standing policy for this research should fix:

- Project: only Yokel's state-rulemaking benchmark and explicitly reviewed new experiment
  namespaces; old releases stay immutable and read-only dependencies are exact pinned
  files. Runtime entry is fixed isolated bundled Python, reviewed adapter and initial
  mode, maximum 1800-second timeout, fresh run ID/output namespace, no retry/resume.
- Credentials: only the already enrolled DocketClock Research service identity/vault/
  exact existing OpenRouter and TypeSafe references. Each job receives its necessary
  subset. No new vault/provider/reference or token-export operation is admitted.
- Accounting: shared nominal $2 ceiling, no refunds, all five existing intents/failures/
  results retained. Current debit is $0.542976718. The proposed next release would be
  only one stronger call, zero inventory/Jev, 8192 output allowance and at most
  $0.161920 new reservation, aggregate $0.704896718. These are proposed release bounds,
  not authorization granted by this prototype. Later job shapes/limits need an explicit
  standing-policy amendment or separately authorized release.
- Authority: primary may request signing only after the authorized work is frozen and
  reviewed; release receipts bind exact manifest/code/review digests and the debit-chain
  head. Reserve atomically before signature issuance; do not reset on failure, and reject
  stale/consumed reservations. Narrow allowlisted smoke commands consume no paid budget.

Technically enforced by a future signer/executor: signature integrity, immutable
provider/reference ceiling, fixed command grammar, all pins, bounded timeout, one-shot
admission and local reservation-record arithmetic. Tests here demonstrate only the
synthetic subset above. Project scope and credential count do not prove semantic safety.
Independent review is a **workflow requirement**, not automatically unforgeable evidence
when all agents share files. The delegated primary can approve/release malicious code
within the hard envelope if the signer trusts its review submissions; this is conscious
delegation, not protection from a hostile primary. A genuine separate approval gate
would require separately controlled approval authority and could restore human friction.

Adapter/ledger call limits, no partial-result salvage and actual provider spending still
depend on reviewed job code. Without a network transport broker the stable executor
cannot technically prevent a signed payload from using/exfiltrating injected provider
keys or exceeding declared calls. The owner must approve this precise trust transfer
before production. Local automatic signing can remove per-job macOS prompts only under
that explicit delegation; human/touch-required signing would move the prompt elsewhere.

## Reproduction and artifact hygiene

Run test.py with bundled isolated Python and the reviewed installed cryptography package
available; it compiles only this directory's sources, generates a new synthetic directory
under this prototype, and replaces RESULT.json. Do not rerun after freezing without
reviewing the new receipts. Earlier failed synthetic directories contain only test
public keys/manifests/binaries; no private key was serialized. They are diagnostic
artifacts, not deployed identities. HANDOFF.json binds the final source/report/result
and successful synthetic directory. No further edit or test is needed for this handoff.
