# R17 A4 offline release preparation

UNSIGNED drafts only. No staging of real bodies, release, executor, native runner,
network, provider, credential, signing key or Keychain operation was performed.
Frozen adapter-r1-3, release-prep and design-r3-1 are unchanged.

The dedicated key label is DocketClock, non-resetting limit $50.00, initial usage
zero. A4 changes KEY_MAX only in recon-a4; FLOOR $0.27, OPERATING $1.80, CAP $2.00,
three OPQ cells, no retries, anomaly halts and A3 timeouts remain unchanged.
The provider $50 ceiling does not backstop CAP; see the user's A4 acceptance.

Offline update steps (all Python uses `-I -S -B`):

1. Run recon-a4/test_recon.py, adapter-r1-4/run_tests.sh (set R17_TEST_PYTHON),
   and release-prep-a4/test_release_prep.py on bundled Python 3.12 and system
   python3; write current logs in each folder's _out.
2. Use adapter-r1-4/pin_ready.py recon-a4, then adapter-r1-4/pin_ready.py
   adapter-r1-4. These freeze tested payloads; they do not authorize release.
3. Regenerate STAGE-MANIFEST.json with prepare_manifest.py. This reads existing
   nonsecret metadata; reference pins are inherited from the frozen manifest.
4. Regenerate unsigned drafts using make_proposals.py --draft --output
   <fresh directory in release-prep-a4> --batch draft-a4-20261014. Draft paths
   are prospective; no real stage or runner is invoked. Three proposals retain
   270000000 nanoUSD reservations, priors 0/270000000/540000000, ceiling
   2000000000 and timeout 1800. The schema has no key-label field.
5. Pin release-prep-a4, then run adapter-r1-4/verify_ready.py on both interpreters
   to rerun all suites and verify every READY/payload/dependency hash.

Before a later authorized live release, primary must independently review r1.4,
normalize attestation without inventing acceptance, finalize P-ACCEPT policy and
all release evidence, and externally pin READY hashes. Release recon must be
recon-a4/r17recon.py with its new hash; original check.py remains paired with
original design r17recon. Supply amended recon as a separate release artifact,
not an edited frozen design file. Update INIT constants, label and recon hash.

Actual machine key checks are still pending; unsigned drafts do not establish
label/limit/zero usage. Confirm all original gates, role/auth, adjudication,
reference freezes, clocks and durability evidence before any release. Keep
selected release policy in separately authorized design copies. Regenerate
manifest/proposals after evidence changes. Actual staging/signing/native job
validation/execution is outside this task.

Native contract remains fixed: only OPENROUTER_API_KEY via provider_variables,
no secret values or op/vault/item overrides. Interpreter is the bundled
python3.12, argv [python, -I, -S, -B, shim, --live-initial]; per-cell arguments
are separately pinned. Host path targets adapter-r1-4. Allowed eventual roots
are /Users/home/.codex/worktrees and /Users/home/dev/yokel; this .t3 checkout
is not a live adapter root. Stages remain content-addressed, exclusive and
no-symlink copies. Ensure .r17-stage is ignored before staging in a checkout.

Draft expiry and scope are placeholders requiring review/regeneration at the
actual release. Historical copied _out logs are retained; current A4 results
are the system-tests.txt/python312-tests.txt referenced by READY.json.
