# Authoritative R17 r1.4 / A4 release runbook

This ordered runbook supersedes the r1.3 order in release-prep/README.md and the
release-prep-a4 README. This folder is an OFFLINE preparation artifact, not a
release authorization. Commands below that stage real data, contact a provider,
sign or execute are future primary-owned steps, **not performed by this task**.

Exactly S1-OPQ → S2-OPQ → S3-OPQ: three calls, no FULL, no retry. Policy P-ACCEPT.
Key label `DocketClock`, non-resetting **$50.00** limit, usage expected **$0**.
CAP 2000000000, OPERATING 1800000000, FLOOR 270000000 nanoUSD; KEY_MAX 50000000000.
The $50 provider ceiling does not enforce the $2 design cap. Historical acceptance
text remains verbatim, including its prior amounts; A4 supplies the amendment.

Set these variables in the primary's authorized live checkout (allowed roots:
/Users/home/dev/yokel or /Users/home/.codex/worktrees; never this .t3 checkout):

```sh
R17_SOURCE="$PWD/docs/research/state-rulemaking-benchmark/round17-paid-comparison"
PREP="$R17_SOURCE/release-prep-a4-r2"
PY=/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12
CORE="$PWD/docs/research/state-rulemaking-benchmark/runner-stability-review/deployment/core.json"
EXECUTOR=/Users/home/.local/libexec/yokel/research-credentials-stable-v1
```

1. **Normalize (offline primary).**
   `"$PY" -I -S -B "$PREP/normalize_evidence.py"`
   Compare evidence/ source_sha256 with the two original run files. Normalization
   maps recorded authorization, not a new human acceptance. Full source records,
   every string, and base64 exact source bytes are retained. creation_date is the
   date of the recorded newly-created affirmation, not a machine timestamp.
2. **Install normalized evidence (primary, only after reviewing this copy).**
   This implementation did not modify run/. At release the primary installs:
   ```sh
   cp "$PREP/evidence/KEY-ATTESTATION.json" "$R17_SOURCE/run/KEY-ATTESTATION.json"
   cp "$PREP/evidence/CAP-ACCEPTANCE.json" "$R17_SOURCE/run/CAP-ACCEPTANCE.json"
   ```
   **Human:** confirm the approved temporary key swap in the immutable 1Password
   vault `aaf4zqgqwi6vtlcxnkfyuvipxa`, item `2yi6d5ymf5qoy55ixnju3r5ayu`, field
   `credential`, as recorded in the original KEY-ATTESTATION.json. Retain the
   prior value in its backup; nothing else may use the item until R17 is done.
   No proposal may override this reference or include a credential value.
   **Primary:** through the approved credential path, check only metadata at
   `GET https://openrouter.ai/api/v1/key`. Record returned **label** DocketClock,
   USD limit 50.00, limit_remaining 50.00, limit_reset null and usage 0 in the
   sanitized KEY-MACHINE.json; record endpoint, response SHA256, retrieval time,
   units/field documentation confirmation and accepted_by_primary. Integer
   adapter evidence limit/remaining are 50000000000 nanoUSD. The adapter does
   not verify label: primary must explicitly compare and record it before release.
   Any mismatch stops preparation. Never store the key or authorization headers.
3. **Re-pin (primary).** Finalize separately authorized release-design copies for
   P-ACCEPT, all evidence and independent review acceptance first. Verify the
   frozen adapter-r1-4 and recon-a4 READY payload/dependency hashes; do not re-pin
   or modify those frozen folders. Re-pin this preparation after testing:
   ```sh
   "$PY" -I -S -B -m unittest discover -s "$PREP" -p 'test_*.py' -v > "$PREP/_out/r2-tests.txt" 2>&1
   "$PY" -I -S -B "$PREP/pin_ready.py"
   ```
   After manifest/draft regeneration in step 4, repeat this local pin command to
   include their final bytes. Preserve the resulting READY hash externally.
   A changed release-design copy needs its own reviewed freeze, never an edit to
   frozen design-r3-1. Any later evidence change restarts steps 3–4 and proposals.

## Exact primary release order (future actions, not executed here)

Use the exact bundled Python above with `-I -S -B` for every Python command.
Let `PREP` be this directory, `STAGE` the printed staging directory, `R17`
`$STAGE/round17-paid-comparison`, and `CORE` the reviewed deployment/core.json.
These are illustrative task variables, not inherited credential environment.
All artifact paths in RELEASE.json are **relative to STAGE**, which acts as BENCH.

4. **Regenerate manifest and stage (primary).** Complete the evidence checklist below. Run `"$PY" -I -S -B "$PREP/prepare_manifest.py" --require-installed` with explicit
   `--evidence path=hash` additions. Review STAGE-MANIFEST.json, then run
   `"$PY" -I -S -B "$PREP/stage.py"`. Record printed STAGE and content ID; set `STAGE=<printed-absolute-path>` and `R17="$STAGE/round17-paid-comparison"`.
   Do not mutate any staged immutable file afterward. Fresh stage required on
   drift. Primary obtains any extra filesystem permission for the allowed root. The .t3 checkout is not an allowed live root.
   **Human:** place/confirm the R17-only, nonresetting $50 key in the existing
   fixed-reference slot during the approved window, retaining the prior value
   for restoration; credential values are never handled by this prep tooling.
   K3 sanitized machine evidence must establish zero usage and matching limit.
   Credential/bootstrap verification is primary-owned and outside this offline task.

5. **INIT ledger.** Create `$R17/run/ledger.jsonl` exclusively with one canonical
   JSON line plus newline; fsync file and directory. Use adapter.encode, not a
   floating-point serializer. INIT fields are exactly: `type:'INIT'`,
   `namespace:'r17.paid-comparison.v1'`, `CAP:2000000000`,
   `OPERATING:1800000000`, `FLOOR:270000000`, `KEY_MAX:50000000000`,
   `key_label:'DocketClock'`, verified integer `key_limit`,
   `key_limit_reset:null`, `key_initial_usage:0`, `release_policy:'P-ACCEPT'`,
   `required_calls:['S1-OPQ','S2-OPQ','S3-OPQ']`, `budget_sha256` of the
   selected/frozen staged BUDGET (key_limit = 50000000000 nanoUSD), `recon_sha256` equal to
   `8c98fabdc73fad10336698fa695869966a631d5a7d99b797725f2c711b1b6bb0`.
   There is no prev_sha256 on INIT. Pin sha256(adapter.encode(INIT)), excluding
   its JSONL newline. Refuse an existing ledger; do not reset prior history. Exact helper:
   `"$PY" -I -S -B "$PREP/release_records.py" --stage "$STAGE" init --budget <absolute-staged-selected-BUDGET.md>`.
   Primary confirms KEY-MACHINE before running this helper.

6. **C6 release record.** Primary writes `$R17/run/RELEASE.json` exclusively as
   adapter.encode of `r17.release.v1`. Include selected policy, required_calls,
   typed_testable=false, INIT hash, model `openai/gpt-6.1-sol`, provider `OpenAI`,
   and all artifacts from adapter.REQUIRED_ARTIFACTS plus host_driver. Each is
   `{path:<STAGE-relative>, sha256:<exact hash>}`. Map recon to recon-a4/r17recon.py, leaving the original design fixture/check pair frozen. Map adapter/tests/adapter_ready
   to adapter-r1-4, host_driver to its host_driver.py, and design roles to the
   staged selected design. Read the staged source texts **only at this later
   primary step**; for each OPQ cell use wire.build(source,'opaque') and bind
   `plan_request_sha256` plus sha256(adapter.dispatched(plan)). Derive threshold
   table from the accepted scoring manifest using the exact formula at
   r17_adapter.py release_gate; do not invent E8 counts. Include driver_sha256
   as the host bytes' hash. Pin this exact release record and all required evidence. Primary authors the
   specified record in a fresh nonsecret release-input.json (including calls and
   thresholds); exact exclusive canonical publication command:
   `"$PY" -I -S -B "$PREP/release_records.py" --stage "$STAGE" release --input <absolute-primary-release-input.json>`.
   Helper verifies all artifact bytes and inserts INIT hash; it never invents
   source plans or semantic acceptance.

7. **BIND_RELEASE.** Under adapter.Ledger(run_root).lock('primary-bind'), load the
   initialized ledger and append `BIND_RELEASE` with selected release_policy and
   sha256(RELEASE.json exact bytes). Ledger.append adds prev_sha256 and fsyncs.
   There must be exactly one binding. Exact command:
   `"$PY" -I -S -B "$PREP/release_records.py" --stage "$STAGE" bind`. Validate ledger shapes and recon.admit for
   S1-OPQ. Primary performs an offline semantic `release_gate` check against
   this staged source/release, with no host callbacks invoked:
   ```sh
   "$PY" -I -S -B - "$STAGE" <<'PRIMARY'
   import importlib.util, sys
   from pathlib import Path
   stage = Path(sys.argv[1]); r17 = stage/'round17-paid-comparison'
   spec = importlib.util.spec_from_file_location('primary_gate', r17/'adapter-r1-4/r17_adapter.py')
   a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
   meta = a.read(r17/'sources-r2/READY.json')
   source = (r17/'sources-r2'/meta['selected'][0]/'parsed-body.txt').read_text()
   ledger = a.Ledger(r17/'run')
   with ledger.lock('primary-semantic-gate'):
       ledger.load()
       a.release_gate(ledger, r17/'run/RELEASE.json', 'S1-OPQ', source, root=stage)
       assert a.recon.admit(ledger.entries, 'S1-OPQ', a.last_usage(ledger.entries)) == (True, None)
   PRIMARY
   ```
   This source read is a future primary step, not this offline task. Do not sign while
   any release gate is false. Any reference read here is primary-owned work.

8. **Generate S1 unsigned proposal.** Run
   `"$PY" -I -S -B "$PREP/make_proposals.py" --stage "$STAGE" --output <fresh-proposal-dir> --cell S1-OPQ --scope <authorized-scope-id> --batch <fresh-utc-and-unique-suffix> --expires-unix <future-unix-second-within-7-days> --prior-nanousd <verified-ledger-aggregate> --release "$R17/run/RELEASE.json" --review <absolute-staged-accepted-review>`.
   Review exact files/arguments/budget/expiry and verify unchanged payload pins.
   Never sign proposals-draft: it intentionally lacks final release/evidence,
   actual scope and actual on-release aggregate. Proposal and per-job dirs refuse
   overwrite; on a partial preparation failure inspect state and choose new IDs.

9. **Sign, then check-job.** Primary, under existing release delegation, uses
   `/bin/sh tools/research-credentials-stable/release_job.sh --core "$CORE" --proposal <new-job.json> --key-file <primary-protected-signing-key> --executor /Users/home/.local/libexec/yokel/research-credentials-stable-v1`.
   The wrapper invokes native check-job after exclusive publication. If primary
   additionally checks explicitly, use that same executor `check-job <job-id>`.
   This is the first signing-key access; it is primary-owned, never performed
   by this implementation task. No human key-reading or secret-pasting step is
   required. A failed publication/check must be inspected; never overwrite it.

10. **Run S1-OPQ exactly once.** Primary runs that same installed executor
   `run <S1-job-id>`. The one-shot native claim is consumed per signed job before dispatch; never re-run a consumed job id;
   failure does not authorize replay. Retain receipts/ledger. Any watchdog,
   uncertainty, retained lock or HALT requires the exact accounting recovery procedure below;
   do not simply launch the next cell. **Human:** maintain the approved key
   window; interact only if a separately authorized native enrollment/migration
   requires it. No credential UI is called by the prep tooling.

11. **Adjudicate and release S2, then S3.** Perform the protocol's staged
   adjudication and primary acceptance after each completed cell; honor the
   applicable A1 batching amendment without bypassing adapter.staged_gate.
   Prepare its accepted gate/report closure. Recheck ledger admission, final
   release/evidence hashes, budget and expiry. Repeat steps 8–10 with
   `--cell S2-OPQ` and then `--cell S3-OPQ`, each fresh batch/job ID and
   `--gate <absolute-staged-accepted-prior-cell-gate>`; update prior_nanousd
   from the verified ledger. Signing later cells before the required gate
   exists is intentionally refused. Never run a FULL cell under these proposals.

12. **Close and restore.** Primary reconciles aggregate debit, preserves the
   frozen outputs/adjudication/report and reports invoice-verification status
   honestly. **Human:** disable DocketClock, then restore the approved prior fixed-reference key from its
   backup after the R17 window. No restoration, credential lookup, commit,
   provider call or native command occurs in this implementation task.


## Required evidence before step 4

Supply every added immutable nonsecret file via
`--evidence <BENCH-relative-path>=<sha256>` to prepare_manifest.py, including
selected release-design copies and their READY files, A1/A2 accepted fixture
gates, scoring manifest (typed_testable=false), KEY-MACHINE, role/auth evidence,
accepted independent adapter-review-r4/REVIEW.md and its acceptance, A1/A2
amendment receipts, clock/CA/durability and bootstrap timing evidence. Include
all referenced evidence closure. Do not use the implementer's SPEC as the live
independent review. Original design fixture/check layout remains intact.

The candidate STAGE-MANIFEST pins normalized evidence both in evidence/ and at
run/ runtime paths. `--require-installed` refuses staging preparation until
installation is exact. This task's manifest is prospective: current run/ bytes
remain original. Never use copied historical drafts. Regenerate a draft only:

```sh
"$PY" -I -S -B "$PREP/make_proposals.py" --draft --output "$PREP/proposals-draft-r2" --batch draft-a4-r2-20261014
```

Live generation requires **exactly one --cell**. S1 forbids a gate; S2 requires
an accepted gate listing exactly S1; S3 requires its own accepted gate listing
exactly S1 and S2. Both bind the exact RELEASE hash. Generate/sign a later cell
only after its predecessor completes and both adjudicators are accepted. Cell
arguments are checked to exclude --lock-evidence and --opq-freeze, including
`=value` forms. The offline validator does not establish native signature,
custody, claim or invoice enforcement; primary's live check-job remains required.

## Kill/expiry recovery — before any next job

A claim is consumed **per signed job**, even if dispatch never occurred. Never
re-run a consumed job id. Stop launches on native kill, shim expiry, retained
lock, torn ledger or unknown state. Preserve receipts and lock bytes. On the
same host, primary proves the lock PID is dead (`os.kill(pid, 0)` must raise
ProcessLookupError; EPERM is not proof), confirms host identity and absence of
any remaining process-group worker, records owner_gone=true, pid, host and the
SHA256 of the exact lock in a fresh nonsecret LOCK-EVIDENCE.json. Preserve the
lock outside ledger.lock, then remove **only** the proven-dead ledger.lock;
fsync the run directory. No automatic stale-lock guessing.

Run this accounting-only route **outside the runner**, on the staged host,
using the frozen host driver (it injects the pinned driver identity). The
required cell/job/attempt args identify the interrupted attempt; the recovery
branch returns before dispatch and does not replay it:

```sh
env -u OPENROUTER_API_KEY "$PY" -I -S -B "$R17/adapter-r1-4/host_driver.py" \
  --cell "$INTERRUPTED_CELL" --release "$R17/run/RELEASE.json" \
  --run-root "$R17/run" --attempt-dir "$R17/run/$INTERRUPTED_JOB" \
  --job-id "$INTERRUPTED_JOB" --lock-evidence "$LOCK_EVIDENCE"
```

Here R17 is the staged round17 directory defined in the ordered steps;
LOCK_EVIDENCE is the preserved fresh evidence path. This route neither accesses
1Password nor supplies a key. Do not put --lock-evidence in signed cell args.

- **Before DISPATCH_MARK:** recovery resolves the unmarked reservation with
  dispatched=false, debit=0, no key GET and no POST. Verify hash chain, no pending
  reservation, no HALT and admission for the same cell. Re-admit by repeating
  steps 8–10 for that cell with a **fresh batch/job id, fresh attempt dir and new
  signed job**, current ledger aggregate, and its required prior-cell gate.
- **After DISPATCH_MARK (or uncertainty about it):** no resend. Keyless recovery
  records failed remaining reads, resolves at FLOOR ($0.27) or greater retained
  evidence debit, then HALT (`recovered_possibly_dispatched`). The run is over.
  If the primary separately authorizes metadata-only keyed recovery, its GETs
  use the existing pinned route outside a signed cell job; it still HALTs and
  performs no POST. Already claimed read slots are never repeated.
  Primary reports interrupted cell/job, possible dispatch, receipt availability,
  recovery debit/aggregate, failed or successful usage reads, HALT reason and
  unverified invoice status. Preserve the original ledger and namespace; a new
  namespace/run would require **new authorization**, not automatic continuation.
- **Already resolved/completed:** recovery is accounting-only; inspect completion
  and HALT state, then use normal adjudication gates if admission permits.
  Never reset, truncate or recreate the original ledger.

## A3 bootstrap margin (N29)

Transport arithmetic is 1590 s; shim deadline 1740 s; native timeout 1800 s.
Python margin is 150 s and native reserve is **60 s minus measured bootstrap**.
Bootstrap includes op provider resolution and all pre-exec pin hashing. Primary
must measure it at the already authorized smoke/metadata step, record seconds,
measurement boundaries and receipt hash in BOOTSTRAP-TIMING.json, and compute
`native_reserve_seconds = 60 - bootstrap_seconds`. Require positive measured
reserve before promising clean completion. This offline task has **no measured
bootstrap value**: deployment's 0.05 s identity observation is outside the job
clock and is not bootstrap evidence. No fabricated measured margin is supplied.
A stall still ends fail-closed in kill/accounting/HALT. See A3-TIMEOUT.md.

All live steps remain primary-owned. Human involvement is confined to the
approved temporary key window and final disable/restore (disable DocketClock
before restoring the backup item). This implementation made no network/provider,
credential, signing, runner/executor/release/check-job calls and did not commit.
