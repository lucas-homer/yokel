# Primary handoff: metadata-only signed keycheck

Offline candidate only. Nothing was signed, staged outside this directory or run
with a credential. There is no live KEY-MACHINE or measured native bootstrap yet.
See SPEC.md for exact boundaries, field types and limits; READY.json pins this
handoff and test evidence. The generator creates a proposal only after the
primary supplies a permitted staged copy and accepted independent review.

## Reproduce offline tests

```sh
PY=/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12
KC=/Users/home/.t3/worktrees/yokel/research-state-rulemaking/docs/research/state-rulemaking-benchmark/round17-paid-comparison/keycheck-job
"$PY" -I -S -B "$KC/test_keycheck.py"
```

## Future primary commands, in order

These commands are **not executed by this implementation task**. Run them on the
installed-runner host. The primary first reviews the candidate and obtains a
nonempty accepted independent review file. Set `ACCEPTED_REVIEW` to its absolute
path, `SCOPE_ID` to the owner-authorized scope, and `PRIOR_NANOUSD` /
`CEILING_NANOUSD` to that scope's verified values. Do not reset benchmark spend;
the reservation is zero. No key value is needed in any shell variable.

1. Stage two files under the permitted root. The basename `adapter.py` is required
   by native Manifest.h, so copy keycheck.py without changing its bytes. Choose a
   fresh directory and proposal output on every attempt:

   ```sh
   BENCH=/Users/home/.t3/worktrees/yokel/research-state-rulemaking/docs/research/state-rulemaking-benchmark
   CORE="$BENCH/runner-stability-review/deployment/core.json"
   EXECUTOR=/Users/home/.local/libexec/yokel/research-credentials-stable-v1
   RELEASE_TOOLS=/Users/home/.t3/worktrees/yokel/research-state-rulemaking/tools/research-credentials-stable
   BATCH=$("$PY" -I -S -B -c 'import datetime,uuid; print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:12])')
   STAGE="/Users/home/dev/yokel/docs/research/state-rulemaking-benchmark/round17-paid-comparison/keycheck-staged-$BATCH"
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
   "$PY" -I -S -B - "$EXECUTOR" "$JOB_ID" "$EVIDENCE" <<'PRIMARY'
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
   fd=os.open(out,os.O_RDONLY)
   try: os.fsync(fd)
   finally: os.close(fd)
   raise SystemExit(result.returncode)
   PRIMARY
   ```

   No shell success should be inferred from running several commands together.
   Stop on nonzero return, absent receipts, FAIL metadata, interrupted wrapper or
   partial writes. Preserve evidence and the consumed claim; a new attempt needs
   a new reviewed stage, proposal and job ID. No automatic retry is provided.

4. Join the original adapter timing with the outer measurement, preserving it.
   This helper is offline and does not run any native command:

   ```sh
   "$PY" -I -S -B "$KC/measure_bootstrap.py" \
     --timing "$STAGE/BOOTSTRAP-TIMING.json" \
     --boundaries "$EVIDENCE/RUN-BOUNDARIES.json" \
     --receipt "$EVIDENCE/native-run-receipt.txt" \
     --output "$EVIDENCE/BOOTSTRAP-TIMING.json"
   cp "$STAGE/KEY-MACHINE.json" "$EVIDENCE/KEY-MACHINE.json"
   ```

   The joined `bootstrap_seconds` is an exact decimal string expressing a
   conservative outer-run-to-adapter-ready bound. It includes op resolution and
   all pre-exec hashing plus work before the native deadline. Exact native start
   is still unknown. Require `positive_native_reserve=true` before accepting N29;
   `native_reserve_seconds = 60 - bootstrap_seconds`. Adapter entry-to-ready alone
   cannot satisfy N29. Review the bound, clock confirmation and receipt hashes.

5. Primary reviews KEY-MACHINE (`status=PASS`, five checks true, exact values,
   endpoint, timestamps, response hash, USD units/field-documentation confirmation)
   and timing evidence before flipping `accepted_by_primary` in the final accepted
   evidence copies. Keep original machine receipts immutable. Feed these final
   evidence files/hashes into the release-prep-a4-r2 runbook. Neither metadata PASS
   nor a positive reserve authorizes the paid run by itself. Human key disable /
   prior-slot restoration follows that existing approved window/runbook.

Only the staged adapter and accepted review are copied for this job. Runtime
dependencies are pinned in place; no install, runner rebuild or credential UI is
part of staging. No releaseable proposal is fabricated for nonexistent staged
paths or an unaccepted review during offline implementation.
