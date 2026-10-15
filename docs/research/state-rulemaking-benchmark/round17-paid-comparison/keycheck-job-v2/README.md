# Primary handoff: metadata-only signed keycheck v2

Offline candidate only. Nothing in this implementation was signed, staged
outside this directory or run with a credential. V1 (`../keycheck-job/`) is frozen
live evidence: the reported native run reached adapter initialization but rejected
metadata without identifying the cause. Masked labels remain an unverified live
hypothesis. V2 has no live receipt yet. It diagnoses the next authorized attempt
without persisting body/headers/exception text. This implementation made no
network calls and touched no credential, signing key, Keychain or native command.
See SPEC.md for exact boundaries, field types and limits; READY.json pins this
handoff and test evidence. The generator creates a proposal only after the
primary supplies a permitted staged copy and accepted independent review.

## Reproduce offline tests

```sh
PY=/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12
KC=/Users/home/.t3/worktrees/yokel/research-state-rulemaking/docs/research/state-rulemaking-benchmark/round17-paid-comparison/keycheck-job-v2
"$PY" -I -S -B "$KC/test_keycheck.py"
```

## Future primary commands, in order

These commands are **not executed by this implementation task**. Run them on the
installed-runner host. The primary first reviews the candidate and obtains a
nonempty **fresh v2** accepted independent review file. The copied
`primary-review/REVIEW.md` is historical v1 acceptance and must not be used as
v2 acceptance. These future commands require the primary's live-run authorization;
the implementation task does not execute them. Run the shell steps with
`set -eu` and stop on any failure. Set `ACCEPTED_REVIEW` to its absolute
path, `SCOPE_ID` to the owner-authorized scope, and `PRIOR_NANOUSD` /
`CEILING_NANOUSD` to that scope's verified values. Do not reset benchmark spend;
the reservation is zero. No key value is needed in any shell variable.

1. Stage two files under the permitted root. The basename `adapter.py` is required
   by native Manifest.h, so copy keycheck.py without changing its bytes. Choose a
   fresh directory and proposal output on every attempt:

   ```sh
   set -eu
   BENCH=/Users/home/.t3/worktrees/yokel/research-state-rulemaking/docs/research/state-rulemaking-benchmark
   CORE="$BENCH/runner-stability-review/deployment/core.json"
   EXECUTOR=/Users/home/.local/libexec/yokel/research-credentials-stable-v1
   RELEASE_TOOLS=/Users/home/.t3/worktrees/yokel/research-state-rulemaking/tools/research-credentials-stable
   BATCH=$("$PY" -I -S -B -c 'import datetime,uuid; print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:12])')
   STAGE="/Users/home/dev/yokel/.r17-stage/keycheck-v2-$BATCH"
   # The .r17-stage parent must already be permitted by the installed core.
   # If it is not, stop; do not change runner policy as part of this job.
   PROPOSALS="$KC/proposals-$BATCH"
   EVIDENCE="$KC/evidence-$BATCH"
   umask 077
   mkdir "$STAGE"
   cp "$KC/keycheck.py" "$STAGE/adapter.py"
   cp "$ACCEPTED_REVIEW" "$STAGE/REVIEW.md"
   EXPIRES_UNIX=$("$PY" -I -S -B -c 'import time; print(int(time.time())+86400)')
   JOB_ID=$("$PY" -I -S -B "$KC/make_keycheck_proposal.py" \
     --core "$CORE" --stage "$STAGE" --output "$PROPOSALS" \
     --scope-id "$SCOPE_ID" --expires-unix "$EXPIRES_UNIX" \
     --prior-nanousd "$PRIOR_NANOUSD" --ceiling-nanousd "$CEILING_NANOUSD")
   ```

   Record the fresh `$BATCH`, `$STAGE`, `$PROPOSALS`, `$EVIDENCE`, and `$JOB_ID`
   in primary session notes without any credentials. The generator uses a fresh
   `r17-keycheck-v2-<UTC>-<uuid>` ID; never reuse any v1 or consumed ID.
   `LIVE-VARS.txt` from v1 is excluded and must not be sourced. Each attempt needs
   a new stage/batch/proposal/job ID even if the prior attempt failed.

   Inspect `STAGE-MANIFEST.json` and `UNSIGNED-ZERO-COST-PROPOSAL.json`. The exact
   invocation is fixed Python plus `-I -S -B $STAGE/adapter.py --live-initial`,
   OpenRouter-only provider subset, 30-second native timeout and zero reservation.
   Stage contents must not change after proposal/signing. The pinned review may
   refer to other evidence; primary reviews that closure. It cannot be this SPEC.

2. Sign and check. `SIGNING_KEY_FILE` is the existing primary-protected signing
   file path; this task never inspects it. The release wrapper also performs
   check-job after publication. Never overwrite partially published registry files.

   ```sh
   /bin/sh "$RELEASE_TOOLS/release_job.sh" \
     --core "$CORE" --proposal "$PROPOSALS/UNSIGNED-ZERO-COST-PROPOSAL.json" \
     --key-file "$SIGNING_KEY_FILE" --executor "$EXECUTOR"
   "$EXECUTOR" check-job "$JOB_ID"
   ```

   Signing/check-job have no provider or Keychain calls. **Human presence:** the
   previously authorized temporary key-slot change belongs to the human/primary.
   Confirm the DocketClock key is installed in the runner's fixed reference during
   the approved window without showing its value here. An unlocked, already
   enrolled Keychain is required for run. Current native runtime disables UI;
   it fails instead of prompting when trust/unlock is unavailable. If separate
   enrollment/migration is needed, the human may need to handle its real-TTY or
   Keychain authorization prompt under the existing runbook. This job does not
   initiate enrollment, migration, rotation or fallback authentication.

3. Capture one native run and outer boundaries on the **same host and boot**.
   The native one-shot claim is consumed even on failure. Do not rerun this ID.
   The wrapper opens fresh evidence files before invoking the runner, supplies no
   provider environment, and writes only native generic output plus timestamps:

   ```sh
   mkdir "$EVIDENCE"
   "$PY" -I -S -B - "$EXECUTOR" "$JOB_ID" "$EVIDENCE" "$STAGE" <<'PRIMARY'
   import json,os,subprocess,sys,time
   from pathlib import Path
   executor,job_id,out=sys.argv[1],sys.argv[2],Path(sys.argv[3])
   # Primary has confirmed these clocks and the adapter are on one host/boot.
   with (out/'native-run-receipt.txt').open('xb') as receipt, \
        (out/'RUN-BOUNDARIES.json').open('x') as boundaries:
       start_mono=time.monotonic_ns(); start_wall=time.time_ns()
       result=subprocess.run([executor,'run',job_id],stdin=subprocess.DEVNULL,
           stdout=receipt,stderr=subprocess.STDOUT,
           env={'HOME':str(Path.home()),'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'})
       end_mono=time.monotonic_ns(); end_wall=time.time_ns()
       receipt.flush(); os.fsync(receipt.fileno())
       json.dump({'job_id':job_id,'before_run_monotonic_ns':start_mono,
           'before_run_wall_ns':start_wall,'after_run_monotonic_ns':end_mono,
           'after_run_wall_ns':end_wall,'returncode':result.returncode,
           'same_host_boot_and_monotonic_clock_confirmed_by_primary':True},boundaries,
           sort_keys=True,indent=2)
       boundaries.write('\n'); boundaries.flush(); os.fsync(boundaries.fileno())
   # Preserve available adapter receipts even when the native return is nonzero.
   # The stage is the pinned adapter's parent; pass it explicitly to this wrapper.
   stage=Path(sys.argv[4])
   for name in ('BOOTSTRAP-TIMING.json','KEY-MACHINE.json','FAILURE.json'):
       source=stage/name
       if source.is_file():
           with source.open('rb') as src, (out/name).open('xb') as dst:
               dst.write(src.read()); dst.flush(); os.fsync(dst.fileno())
   fd=os.open(out,os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
   raise SystemExit(result.returncode)
   PRIMARY
   ```

   No shell success should be inferred from running several commands together.
   Stop on nonzero return, absent receipts, FAIL metadata, interrupted wrapper or
   partial writes. The wrapper copies available sanitized stage receipts before
   returning nonzero: inspect `FAILURE.json` for `stage` and only its allowlisted
   extras. Never inspect/dump the key, response body, request or headers to debug.
   If FAILURE is absent, retain timing/outer receipts and report the gap; a killed
   process or filesystem/preflight error cannot guarantee a failure receipt.
   Preserve evidence and the consumed claim; a new attempt needs
   a new reviewed stage, proposal and job ID. No automatic retry is provided.

4. Only after a zero exit, no FAILURE receipt and machine PASS, join the original
   adapter timing with the outer measurement, preserving it. The wrapper already
   copied the raw adapter timing and KEY-MACHINE; the joined receipt gets a fresh
   `BOOTSTRAP-TIMING-JOINED.json` name.
   This helper is offline and does not run any native command:

   ```sh
   "$PY" -I -S -B "$KC/measure_bootstrap.py" \
     --timing "$STAGE/BOOTSTRAP-TIMING.json" \
     --boundaries "$EVIDENCE/RUN-BOUNDARIES.json" \
     --receipt "$EVIDENCE/native-run-receipt.txt" \
     --output "$EVIDENCE/BOOTSTRAP-TIMING-JOINED.json"
   ```

   The joined `bootstrap_seconds` is an exact decimal string expressing a
   conservative outer-run-to-adapter-ready bound. It includes op resolution and
   all pre-exec hashing plus work before the native deadline. Exact native start
   is still unknown. Require `positive_native_reserve=true` before accepting N29;
   `native_reserve_seconds = 60 - bootstrap_seconds`. Adapter entry-to-ready alone
   cannot satisfy N29. Review the bound, clock confirmation and receipt hashes.

5. Primary reviews KEY-MACHINE v2 (`status=PASS`, all four financial checks true,
   exact values, optional-field flags, endpoint/timestamps/hashes, and USD
   units/field-documentation confirmation). A plain label or separate name must
   match `DocketClock`. For `label_check=not_machine_verifiable`, obtain the user's
   explicit key-name attestation; machine PASS alone cannot verify that name.
   A masked label is never included in evidence. Review timing evidence before
   flipping `accepted_by_primary` in the final accepted
   evidence copies. Keep original machine receipts immutable. Feed these final
   evidence files/hashes into the release-prep-a4-r2 runbook. Neither metadata PASS
   nor a positive reserve authorizes the paid run by itself. Human key disable /
   prior-slot restoration follows that existing approved window/runbook.

Only the staged adapter and accepted review are copied for this job. Runtime
dependencies are pinned in place; no install, runner rebuild or credential UI is
part of staging. No releaseable proposal is fabricated for nonexistent staged
paths or an unaccepted review during offline implementation.
