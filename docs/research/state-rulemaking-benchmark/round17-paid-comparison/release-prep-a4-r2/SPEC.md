# A4-r2 dispositions

Copied release-prep-a4 in full; all subsequent writes are confined to this folder.
Inherited _out and proposals-draft are historical snapshots. Only
proposals-draft-r2 reflects this revision, and remains unsigned/prospective.
Frozen release-prep-a4, adapter-r1-4 and recon-a4 retain every byte.

- S7 fixed: README is the authoritative ordered r1.4/A4 runbook, superseding the
  stale r1.3 order. Includes DocketClock, non-resetting $50, zero initial usage,
  exact recorded 1Password item, P-ACCEPT, three OPQ calls, amended recon hash,
  exact commands and human responsibilities. release_records.py provides
  exclusive canonical INIT/RELEASE/BIND commands for the future primary.
- S8 fixed: normalize_evidence.py maps existing statements to validated fields,
  retains entire original records and exact original bytes (base64), records
  source SHA256, and is deterministic/idempotent even after primary installation.
  creation_date derives from the recorded newly-created affirmation date and is
  explicitly not a verified timestamp. accepted_by_primary maps the existing
  primary-recorded ACCEPTED status; no new authorization or machine check is
  invented. Historical residual-risk/$3/A4 text is preserved verbatim.
  prepare_manifest uses normalized run hashes; --require-installed checks exact
  installation before real staging. Primary owns installation outside this task.
- S9 fixed: non-draft CLI and generate API require one cell before output writes;
  S1 forbids a gate; S2/S3 require separately accepted gates with exact completed
  call sets and RELEASE binding. An S2 gate cannot prepare an S3 proposal.
- S10 fixed: runbook documents owner-death proof, retained-lock preservation,
  --lock-evidence outside the runner, pre-mark zero-debit re-admission via a
  newly signed fresh job, post-mark FLOOR-or-higher/HALT and reporting, new
  authorization for a new namespace, and per-signed-job claim consumption.
- N33 fixed: signed cell args reject --lock-evidence/--opq-freeze and equals forms.
- N36 documented: primary must check and record live label in metadata-only
  KEY-MACHINE before release. Adapter itself remains frozen and does not check it.
- N29 documented with honest limitation: 1590 s transport, 150 s shim margin,
  native reserve 60 minus measured bootstrap. Actual bootstrap measurement is
  pending the primary's approved smoke step; no offline measurement is fabricated.

Validation: 21 tests using the specified Python 3.12 -I -S -B. The frozen
adapter's full release_gate accepts both normalized files in a synthetic complete
P-ACCEPT three-call release; originals fail K3_attestation/policy_evidence with
zero POST/GET. Every original string is compared as UTF-8 bytes; original JSON
bytes recover exactly. Remaining tests cover manifest pins/installation refusal,
normalization idempotence, single-cell/CLI refusal, gates/recovery args, synthetic
staging symlinks/drift/exclusivity, full closure imports and native proposal
schema/budget validation. No runner/executor/release/check-job command was run.
Stage functions ran only against temporary synthetic trees inside this folder.
No real source body or reference content was opened. No credentials/signing key,
Keychain, provider/network calls or commit. READY is offline preparation only.

Final pin verification: pin_ready.py --verify checks exact payload inventory,
current test log and pre-copy frozen baseline against all three frozen folders.
Primary must re-pin selected release-design/evidence copies, regenerate the
manifest with --require-installed plus all added evidence, stage in an allowed
root, and regenerate each live proposal after applicable accepted cell gates.
