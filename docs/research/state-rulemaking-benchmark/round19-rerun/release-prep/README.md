# Ordered R19 runbook (future primary-owned steps)

This is offline preparation, not live release evidence. Use the bundled Python
3.12 with `-I -S -B`. Exactly S1-OPQ → S2-OPQ → S3-OPQ, no FULL, no retry.
P-ACCEPT; namespace `r19.paid-rerun.v1`; scope
`docketclock-research-r19-authorized-20261014`. FLOOR $0.27, OPERATING $1.80,
design CAP $2, accepted spend tolerance $3. Non-resetting key limit $50.

Let PREP be this folder; STAGE the new content-addressed stage; R19 be
`$STAGE/round19-rerun`; BENCH be the source benchmark. Live stage roots must
come from the reviewed deployment core; this .t3 checkout is not a live root.

1. **Keycheck v3.** Independently review/freeze `../keycheck`, prepare its
   metadata-only unsigned proposal through make_keycheck_proposal.py, then have
   the primary sign/check/run it through the established native workflow. PASS
   requires masked-or-DocketClock label, limit 50, null reset, finite usage ≥ 0,
   and remaining = limit − usage. Keep masked-name limitations visible. Verify
   sanitized receipts and measured bootstrap reserve; no paid call yet.
2. **Baseline.** Record the freshly checked usage as U0, integer nanoUSD (ceil
   exact USD × 10^9). The example 59408500 is R17 spend, not a fresh observation.
   Author fresh KEY-MACHINE.json with endpoint/response hash, confirmed USD
   usage field documentation, accepted_by_primary=true, usage=U0,
   limit=50000000000, remaining=50000000000−U0, reset=null. Install the unchanged
   evidence/KEY-ATTESTATION.json and CAP-ACCEPTANCE.json under the new R19 run/;
   A6, rather than the historical zero-use assertion, governs key reuse.
   Supply fresh baseline, bootstrap, accepted cross-provider implementation
   review and required evidence as `--evidence BENCH-relative-path=sha256`.
3. **Stage.** Verify every READY pin. Run prepare_manifest.py --require-installed
   with the explicit fresh evidence pins; inspect STAGE-MANIFEST.json, then
   stage.py --parent <approved-root>. Record the printed stage content ID.
   Selected design is frozen R17 design-r3-1-paccept; reuse original sources,
   references, scoring manifest, thresholds and fixture gates. No R17 paid
   output or old zero-usage KEY-MACHINE is a stage release input. Any drift
   requires a fresh stage and fresh proposals.
4. **INIT.** Use the staged helper, exclusively:
   `release_records.py --stage "$STAGE" init --budget <staged-P-ACCEPT-BUDGET.md> --key-initial-usage <U0>`.
   Pin canonical INIT without its JSONL newline. The ledger is new R19 history;
   never reset/truncate R17 or an existing R19 ledger.
5. **Release.** Author a fresh release-input.json (r17.release.v1 compatibility
   grammar). Map adapter/tests/adapter_ready/host_driver to R19 adapter; wire
   is imported from R19 wire; recon artifact to frozen R18 recon. Map design roles to
   frozen P-ACCEPT design, and other frozen gates/manifests to their R17 paths.
   K3 machine_check must use the fresh R19 baseline evidence. For each new OPQ
   cell build its plan from the frozen source with the R19 wire and recompute
   plan_request_sha256 and sha256(adapter.dispatched(plan)); derive unchanged
   thresholds from the scoring manifest. Do not reuse R17 call hashes. Publish
   through release_records.py --stage "$STAGE" release --input <fresh-input>.
6. **Bind.** release_records.py --stage "$STAGE" bind, under exclusive lock.
   Preserve INIT and exact RELEASE hashes and their append-only chain.
7. **Gate.** Primary invokes adapter.release_gate offline against the staged
   source/release and recon.admit with adapter.last_usage (initially U0).
   Check K3 usage=U0, remaining=limit−U0, capacity for all remaining calls,
   accepted review closure and positive measured bootstrap reserve before signing.
8. **S1 sign/check/run.** Generate exactly one fresh unsigned proposal using
   make_proposals.py --stage "$STAGE" --output <fresh-dir> --cell S1-OPQ
   --scope docketclock-research-r19-authorized-20261014 --batch <unique-id>
   --expires-unix <within-7-days> --prior-nanousd <R19-ledger-aggregate>
   --release "$R19/run/RELEASE.json" --review <staged-accepted-review>.
   Primary reviews, signs, checks and runs once using the existing native
   workflow. The budget prior is R19's conservative aggregate, not account U0.
9. **Adjudicate.** A1 Fable and A2 Opus, one fresh session each, followed by
   primary acceptance of the protocol gate. No repair/re-score of R17 S1.
10. **S2.** Repeat gate/proposal/sign/check/run for S2-OPQ with --gate naming
    accepted S1 adjudication; adjudicate and accept it. Fresh ID/expiry/prior.
11. **S3.** Repeat with accepted S1+S2 gate; adjudicate, decide and retain final
    accounting/results. No later cell is signed without its required gate.

HALT, kill, retained lock, torn ledger or dispatch uncertainty stops launches.
Preserve all evidence; use the frozen R17 recovery procedure with R19 paths.
Before a proven-unmarked dispatch, only a fresh authorized job may re-admit;
after a mark/uncertainty, accounting recovery halts without resend. Never infer
a dead lock owner or replay a consumed job. A usage drop or unexplained excess
above U0 plus reported cost halts. A3 bounds remain GET 15 s, POST 600 s,
transport arithmetic 1590 s, shim 1740 s, native 1800 s, measured reserve
60 s minus bootstrap. No bootstrap measurement or live acceptance is fabricated.

This implementation performs none of the future provider, signing or native
steps. Review/metadata proposals, credentials and release custody remain primary-owned.
