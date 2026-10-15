# R17 offline native release preparation

**UNSIGNED, OFFLINE implementation candidate. No release/executor/provider command
has been run.** adapter-r1-2 remains frozen. Only adapter-r1-3 and this directory
were written. Source bodies were not opened; reference READY/E8 were used only
for their hash metadata. No signing key, Keychain, credential value or network
was accessed. Production staging is deliberately not performed here.

## Installed contract and integration

Verified public files: tools/research-credentials-stable/INTERFACE.md, README.md,
Manifest.h and runner.m, plus runner-stability-review/deployment/core.json.
Installed executable and core match the public deployment FREEZE SHA-256 pins.
Installed executable exists at
`/Users/home/.local/libexec/yokel/research-credentials-stable-v1` (not invoked).

- Immutable OpenRouter reference: jobs request **only** `OPENROUTER_API_KEY` via
  `provider_variables`. Never put an op reference, vault/item override or key
  value into a proposal. The native runner owns that fixed reference.
- Exact interpreter:
  `/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`.
- Exact argv grammar: `[python, '-I', '-S', '-B', '/.../adapter.py', '--live-initial']`.
  Per-cell arguments therefore live in separately pinned `arguments.json`; the
  native shim template is copied as `native-jobs/<job-id>/adapter.py`.
- Adapter roots: `/Users/home/.codex/worktrees`, `/Users/home/dev/yokel`.
  Dependency roots add the bundled Python directory. `.t3/worktrees` is excluded.
- Native timeout maximum 1800; A3 POST read timeout 600. See A3-TIMEOUT.md for
  1590-second transport arithmetic, 1740-second local deadline, recovery bounds
  and the unproved native-bootstrap/filesystem completion margin.
- Exactly three OPQ cells. No FULL jobs are prepared. Due to the instruction to
  read E8 only for hashes, the three-cell semantic decision is treated as the
  primary's supplied plan; E8's exact bytes are hash-bound, not re-adjudicated here.

`prepare_manifest.py` derives STAGE-MANIFEST.json using existing READY hashes,
not source/reference body reads. It includes the complete adapter freeze,
r17recon/design pins, wire and its pinned runtime closure, three selected
source texts, the entire reference freeze (its verifier checks every member),
and available CAP-ACCEPTANCE. `_out` and historical adapter dependency evidence
that the live job does not read are not staged. The six wire-runtime entries
include wire.py itself; the immutable interpreter is pinned separately in jobs.

`stage.py` preserves BENCH-relative layout under a content-addressed fresh root,
verifies source hashes and every destination SHA-256, and refuses an existing
file/directory/symlink target. Every directory is traversed with openat and
O_NOFOLLOW; files are regular-only, opened O_NOFOLLOW and copied exclusively.
No recursive unreviewed copy or symlink following. Partial failed stages remain
for primary inspection and are never silently reused. Test fixtures are entirely
inside release-prep/_out and removed after tests.

`~/dev/yokel/.r17-stage` **needs a `.gitignore` entry**: `git check-ignore
.r17-stage/probe` did not report it ignored, and the checkout .gitignore contains
no r17-stage rule. Add `.r17-stage/` later under primary repository authority,
or use the other allowed root outside a checkout. No ignore file was changed here.
Stages include frozen reference material and must not be accidentally committed.

`make_proposals.py` emits exact canonical unsigned `yokel.research-job.v1`
JSON, without extra draft/status keys the native schema would reject. Sibling
UNSIGNED.txt marks draft status. Each proposal pins Python, shim, arguments,
all staged static files, exact release, accepted review and release-evidence
closure; S2/S3 additionally pin the prior-cell gate/report closure. Mutable
ledger and future output files are not static pins. Reservations are integer
270000000 nanoUSD per job, ceiling 2000000000. Draft priors are conservative
0/270000000/540000000; at actual release use the verified current ledger
aggregate, not these placeholders. Budget metadata never enforces invoices.

Native test.py is **not safe for this task**: it compiles/invokes synthetic
executors and calls release helpers. No repo-only nonexecuting validator was
found. `make_proposals.validate` ports Manifest.h's unsigned schema/argv/roots/
pins/expiry/budget/review semantics and is tested against temporary real files.
It does not claim native signature, registry custody, op integrity or claim
validation. Primary's later native check-job remains mandatory.

## Release blockers to resolve before staging

Primary must review r1.3 and authorize the exact release scope. Current design
BUDGET/READY/READY.primary are still **UNSET**. Select the already authorized
P-ACCEPT policy in primary-owned release design copies and re-freeze all changed
pins; do not change frozen r1.2/recon/wire authorities. Keep the original
design-r3-1 import layout intact; include each selected release-design copy
through explicit --evidence path=hash entries, then map release artifacts to
that selected copy. Import-time recon and wire pins remain unchanged. Regenerate the staging
manifest after any authorized design/evidence changes.

The existing CAP-ACCEPTANCE record preserves the user's statements, but the
adapter requires additional normalized fields: `accepted_by_primary: true`,
`verbatim_acceptance`, `residual_risk_accepted: true`, and `date`. Primary must
map the recorded residual-risk affirmation with provenance, keeping the original
statements; this task supplies no human affirmation. No new permission question
is implied when the existing user authorization covers that normalization.

The final release also needs actual K3 KEY-ATTESTATION/KEY-MACHINE evidence,
P5 A1/A2 accepted fixture gates, P8 role/auth evidence, the frozen scoring
manifest and accepted reference freeze, P7 independent review and exact READY
hash, Mini NTP/CA/durability evidence, external provider-field/units/idle-limit
confirmation and applicable A1/A2 amendment receipts. None is fabricated here.
Use `prepare_manifest.py --evidence <BENCH-relative-path>=<sha256>` for each
additional immutable nonsecret evidence file and any referenced evidence files
before staging. The accepted scoring manifest must have `typed_testable=false`
and agree with the primary's three-cell decision. Final semantic gates remain
in r17_adapter.release_gate; this prep tool does not replace them.

## Exact primary release order (future actions, not executed here)

Use the exact bundled Python above with `-I -S -B` for every Python command.
Let `PREP` be this directory, `STAGE` the printed staging directory, `R17`
`$STAGE/round17-paid-comparison`, and `CORE` the reviewed deployment/core.json.
These are illustrative task variables, not inherited credential environment.
All artifact paths in RELEASE.json are **relative to STAGE**, which acts as BENCH.

1. **Finalize and stage.** Complete the blockers above and re-pin r1.3 if payload
   bytes change. Run `python -I -S -B "$PREP/prepare_manifest.py"` with explicit
   `--evidence path=hash` additions. Review STAGE-MANIFEST.json, then run
   `python -I -S -B "$PREP/stage.py"`. Record printed STAGE and content ID.
   Do not mutate any staged immutable file afterward. Fresh stage required on
   drift. Primary obtains any extra filesystem permission for the allowed root.
   **Human:** place/confirm the R17-only, nonresetting $1.73 key in the existing
   fixed-reference slot during the approved window, retaining the prior value
   for restoration; credential values are never handled by this prep tooling.
   K3 sanitized machine evidence must establish zero usage and matching limit.
   Credential/bootstrap verification is primary-owned and outside this offline task.

2. **INIT ledger.** Create `$R17/run/ledger.jsonl` exclusively with one canonical
   JSON line plus newline; fsync file and directory. Use adapter.encode, not a
   floating-point serializer. INIT fields are exactly: `type:'INIT'`,
   `namespace:'r17.paid-comparison.v1'`, `CAP:2000000000`,
   `OPERATING:1800000000`, `FLOOR:270000000`, `KEY_MAX:1730000000`,
   `key_label:'yokel-r17-paid-comparison'`, verified integer `key_limit`,
   `key_limit_reset:null`, `key_initial_usage:0`, `release_policy:'P-ACCEPT'`,
   `required_calls:['S1-OPQ','S2-OPQ','S3-OPQ']`, `budget_sha256` of the
   selected/frozen staged BUDGET, `recon_sha256` equal to
   `5295a66700fee54b2e03344003e5638a5728b1949eedf0945062950cc40e33ff`.
   There is no prev_sha256 on INIT. Pin sha256(adapter.encode(INIT)), excluding
   its JSONL newline. Refuse an existing ledger; do not reset prior history.

3. **C6 release record.** Primary writes `$R17/run/RELEASE.json` exclusively as
   adapter.encode of `r17.release.v1`. Include selected policy, required_calls,
   typed_testable=false, INIT hash, model `openai/gpt-6.1-sol`, provider `OpenAI`,
   and all artifacts from adapter.REQUIRED_ARTIFACTS plus host_driver. Each is
   `{path:<STAGE-relative>, sha256:<exact hash>}`. Map adapter/tests/adapter_ready
   to adapter-r1-3, host_driver to its host_driver.py, and design roles to the
   staged selected design. Read the staged source texts **only at this later
   primary step**; for each OPQ cell use wire.build(source,'opaque') and bind
   `plan_request_sha256` plus sha256(adapter.dispatched(plan)). Derive threshold
   table from the accepted scoring manifest using the exact formula at
   r17_adapter.py release_gate; do not invent E8 counts. Include driver_sha256
   as the host bytes' hash. Pin this exact release record and all required evidence.

4. **BIND_RELEASE.** Under adapter.Ledger(run_root).lock('primary-bind'), load the
   initialized ledger and append `BIND_RELEASE` with selected release_policy and
   sha256(RELEASE.json exact bytes). Ledger.append adds prev_sha256 and fsyncs.
   There must be exactly one binding. Validate ledger shapes and recon.admit for
   S1-OPQ. Primary performs an offline semantic `release_gate` check against
   this staged source/release, with no host callbacks invoked. Do not sign while
   any release gate is false. Any reference read here is primary-owned work.

5. **Generate S1 unsigned proposal.** Run
   `python -I -S -B "$PREP/make_proposals.py" --stage "$STAGE" --output <fresh-proposal-dir> --cell S1-OPQ --scope <authorized-scope-id> --batch <fresh-utc-and-unique-suffix> --expires-unix <future-unix-second-within-7-days> --prior-nanousd <verified-ledger-aggregate> --release "$R17/run/RELEASE.json" --review <absolute-staged-accepted-review>`.
   Review exact files/arguments/budget/expiry and verify unchanged payload pins.
   Never sign proposals-draft: it intentionally lacks final release/evidence,
   actual scope and actual on-release aggregate. Proposal and per-job dirs refuse
   overwrite; on a partial preparation failure inspect state and choose new IDs.

6. **Sign, then check-job.** Primary, under existing release delegation, uses
   `/bin/sh tools/research-credentials-stable/release_job.sh --core "$CORE" --proposal <new-job.json> --key-file <primary-protected-signing-key> --executor /Users/home/.local/libexec/yokel/research-credentials-stable-v1`.
   The wrapper invokes native check-job after exclusive publication. If primary
   additionally checks explicitly, use that same executor `check-job <job-id>`.
   This is the first signing-key access; it is primary-owned, never performed
   by this implementation task. No human key-reading or secret-pasting step is
   required. A failed publication/check must be inspected; never overwrite it.

7. **Run S1-OPQ exactly once.** Primary runs that same installed executor
   `run <S1-job-id>`. The one-shot native claim is consumed before dispatch;
   failure does not authorize replay. Retain receipts/ledger. Any watchdog,
   uncertainty, retained lock or HALT requires primary-led recovery/stop review;
   do not simply launch the next cell. **Human:** maintain the approved key
   window; interact only if a separately authorized native enrollment/migration
   requires it. No credential UI is called by the prep tooling.

8. **Adjudicate and release S2, then S3.** Perform the protocol's staged
   adjudication and primary acceptance after each completed cell; honor the
   applicable A1 batching amendment without bypassing adapter.staged_gate.
   Prepare its accepted gate/report closure. Recheck ledger admission, final
   release/evidence hashes, budget and expiry. Repeat steps 5–7 with
   `--cell S2-OPQ` and then `--cell S3-OPQ`, each fresh batch/job ID and
   `--gate <absolute-staged-accepted-prior-cell-gate>`; update prior_nanousd
   from the verified ledger. Signing later cells before the required gate
   exists is intentionally refused. Never run a FULL cell under these proposals.

9. **Close and restore.** Primary reconciles aggregate debit, preserves the
   frozen outputs/adjudication/report and reports invoice-verification status
   honestly. **Human:** restore the approved prior fixed-reference key from its
   backup after the R17 window. No restoration, credential lookup, commit,
   provider call or native command occurs in this implementation task.

## Offline evidence

Adapter suite: 190 tests under each interpreter (25 inherited engine fixtures,
not adapter coverage). Pin-stability verification runs that full suite again.
Release-prep suite: 12 tests under each interpreter, using synthetic temporary
staging/proposals only. See adapter-r1-3/_out and release-prep/_out outputs.
Python 3.12 explicit CA context loads **128 CA anchors** without a connection.
Both suites use `-I -S -B`; inherited repro subprocesses use sys.executable.
Draft proposals are shape/root/budget/expiry validated only; prospective files
are absent and no claim of native check-job success is made.
