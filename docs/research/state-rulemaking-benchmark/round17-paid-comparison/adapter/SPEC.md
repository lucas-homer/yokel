# R17 P3 dispatch adapter — offline candidate

This directory implements one invocation / one cell / at most one POST. It grants no
paid-release authority. The actual frozen policy is **UNSET**, so the real release
remains refused. No native runner, job, release script, credential lookup or network
operation was used in implementation or testing. Only synthetic source text is used
in tests; R17 source hashes come from `sources-r2/READY.json` without opening its texts.

The executable semantic authority is **the exact design-r3.1 `fixtures/r17recon.py`**:
SHA-256 `5295a66700fee54b2e03344003e5638a5728b1949eedf0945062950cc40e33ff`.
`dependencies()` verifies it against `READY.primary.json`, checks the pinned wire hash
against the source READY, and executes verified bytes by path. Admission, pending
reservations, aggregation, debit, exact USD parsing, reconciliation and close debit
all call that imported module. They are not alternative implementations.

The originating wire is unchanged r16.w2.1 `wire.py`, SHA-256
`662268ba0774d7ef5a121ec4af90003a3836c07e4ce5a5ae551a413fe8375ab1`.
Its own verified r15/common dependencies remain in force. `READY.json` lists the
direct and transitive executable dependencies and the normative input pins.

## Invocation and injection contract

The library entry point is `execute_once(cell=..., source=..., release_path=...,
run_root=..., attempt_dir=..., job_id=..., post=..., key_info=..., ...)`.
`source` is the exact UTF-8 source supplied by the host, verified against the selected
slot's frozen source hash. There is no source clipping, chunking or repair.

The CLI requires isolated Python and a pinned host driver:

```text
python3 -I -S -B adapter/r17_adapter.py --cell S1-OPQ \
  --release run/RELEASE.json --run-root run --attempt-dir run/S1-OPQ-claim1 \
  --job-id unique-native-job-id --driver reviewed-host-driver.py \
  --driver-sha256 <release-pinned-sha256>
```

Subsequent calls also need `--staged-gate`; FULL calls need `--opq-freeze`.
Paths above are examples, not prepared or authorized jobs. The driver is **not
provided here**: this offline task must not implement or invoke native credential
resolution. Its required exports are `source(cell)`, `post_once(url, exact_bytes)`
and `key_info(url)`. Its SHA-256 must match the release's `driver_sha256`.
Importing the driver and obtaining source must perform no provider/credential I/O;
only its callbacks may perform the explicitly authorized operations, after the gate.

`post_once` receives the exact immutable serialized request bytes. It returns a dict
with exactly `status` (integer), `raw` (bytes), and `headers` (sanitized dict). It must
perform exactly one POST to `/api/v1/chat/completions`, with no redirect following,
HTTP client retry, streaming, fallback, repair or provider substitution. The adapter
has **one POST call site**, outside all polling/recovery loops. Callback exceptions
become transport-uncertain; they cannot invoke that call site again.

`key_info` performs one GET `/api/v1/key`, returning exactly:

```text
{fields: exact JSON bytes containing only usage, limit, limit_remaining, limit_reset,
 response_sha256: SHA-256 of the original endpoint response bytes}
```

These are a **normalized callback contract**, not a claim that the live endpoint's
usage field/units have been established. Values for money are JSON numeric USD
tokens, parsed exactly and rounded upward by `r17recon.parse_usd`. Key-identifying
fields are dropped **before** crossing into the adapter. Header sanitization also
belongs at this boundary; no authorization, key-identifying or cookie header may
be returned. Only the native host driver may use the runner-injected
`OPENROUTER_API_KEY`; it must have no credential-reference fallback, other key or
other environment-variable credential source. The adapter never reads the environment
or accepts/prints a credential parameter. P7 must review these host responsibilities.

`clock.now()` supplies wall-clock seconds and `clock.wait_until(deadline)` waits to
the absolute scheduled deadline. Tests use `FakeClock`, never sleep. Production
timestamp metadata uses decimal **strings**; elapsed schedule seconds and money in
the ledger use integers. The default clock's sleeps are at most 60 seconds each.

## Release-record schema and human evidence

The protocol specifies the contents, not a JSON layout. This candidate defines
`schema_version: r17.release.v1` with `release_policy`, `init_sha256`,
`required_calls`, `typed_testable`, `model: openai/gpt-6.1-sol`, `provider: OpenAI`,
`calls`, `thresholds`, and `artifacts`. `calls` maps every required cell to
`{plan_request_sha256, dispatched_body_sha256}`. An artifact is
`{path: BENCH-relative path, sha256: exact file hash}`; paths must stay inside BENCH.
The native release also pins `driver_sha256` and must cover the driver file in its
signed dependency manifest. Tests use a private synthetic artifact root under this
directory; the CLI uses the actual BENCH root.

Required artifact names, as enforced by `REQUIRED_ARTIFACTS`, are:

- `protocol`, `budget`, `reference_spec`, `adjudication_spec`, `scorer`, `recon`,
  `cases`, `cases_src`, `check`, `design_ready`, `design_primary`;
- `A1_fixture_gate`, `A2_fixture_gate`, `sources_ready`, `reference_ready`,
  `scoring_manifest`, `policy_evidence`, `key_attestation`, `machine_check`, `roles_auth`;
- `adapter`, `tests`, `adapter_ready`.

Both design READY policies, BUDGET's literal policy slot, INIT, the release and
BIND_RELEASE must agree. Design primary pins must match all the named design files.
Reference and adapter freezes must enumerate their files via `sha256` or `files`
maps; every enumerated file is rehashed. The release additionally verifies that the
adapter/test bytes are this implementation's bytes.

The policy evidence has `accepted_by_primary: true`. P-HARD uses the required
`ENFORCEMENT-EVIDENCE.json` filename, `enforcement: E-1|E-2`,
`cross_provider_review_accepted: true`, a nonempty `documentation` list of
`{path, sha256, url, retrieved_utc}`, a `{path, sha256}` `review`, and matching
`review_sha256`. Every capture/review is rehashed. E-2 also requires integer
`all_in_upper_bound_nano <= FLOOR` and `established` with all four CN1–CN4 true.
P-ACCEPT uses `CAP-ACCEPTANCE.json`, a date, a nonempty `verbatim_acceptance`, and
`residual_risk_accepted: true`. **The primary must judge the actual documentation and
acceptance wording**; boolean evidence records are not autonomous adjudication.

The key attestation contains `key_label`, integer nanoUSD `limit`, `limit_reset: null`,
`creation_date`, `used_only_for_R17: true`, and the matching policy. The machine-check
record contains the exact key endpoint, `documentation_confirmed: true`,
`usage_field: usage` (the normalized field), `usage_units: USD`, original response
hash, `accepted_by_primary: true`, and permitted values: zero `usage`, attested
`limit`, equal `limit_remaining`, and null reset. The human must retain the confirmed
provider field name/units and normalization documentation with this record and driver.
No invoice verification or charge-time enforcement is inferred from those values.

Fixture-gate records contain `role: A1|A2`, `failures: 0`, `all_gold_packets: true`,
`accepted_by_primary: true`, and hashes of `cases.json` and `check.py`.
The reference READY must say `accepted_by_primary: true`. That acceptance represents
the completed E1–E8 reference-authoring/review/sufficiency procedure. The adapter
does not author references or adjudicate their textual faithfulness.

The scoring manifest retains the normative slot relation/compound IDs and boolean
critical flags. The adapter checks ascending, distinct source IDs and their source
READY hashes, ≥2 live relations per slot, ≥12 pooled, and typed-testability iff ≥5
pooled compounds. `thresholds` must be exactly the computed dict with `N`, `n_s`
(S1/S2/S3 order), `N_c`, `D2`, `D3_correct`, `D3_acceptable`, `D2_source`, `T4`,
`critical`, `critical_per_source`, and `critical_compounds`. Per-source EXCEPT/RESTRICT
presence, reference segmentation/faithfulness and reserve replacement reasons remain
part of the primary's P6 acceptance, rather than being inferred from ID counts.

The roles record contains `authMethod: claude.ai`,
`anthropic_api_key_override: false`, `reference_reviewer: gpt-6-astra`,
`reviewer_provider: codex`, and `accepted_by_primary: true`. The adapter verifies the
record, never runs an auth command or handles a credential.

INIT is prepared by P2, with `type: INIT`, namespace, `CAP`, `OPERATING`, `FLOOR`,
`KEY_MAX`, key label, verified `key_limit`, `key_limit_reset: null`,
`key_initial_usage: 0`, required cells, policy, BUDGET hash and recon hash. It pins no
release hash. The release pins its entry hash; the following BIND_RELEASE entry
contains `release_sha256` and repeats the policy. There is no hash cycle.

## Staged adjudication contract

After each valid response, the primary supplies an accepted staged-gate file with
the release/reference hashes, exactly the dispatched `calls`, and per-call
`result_sha256`, `A1_sha256`, `A2_sha256`. Its `files` map pins both adjudicators and
the scorer report (identified by `scorer_report_sha256`); all these files must remain
under `run/`. It contains `accepted_by_primary: true`.

The primary runs the **pinned scorer's `decide --interim`**, checks its input/output
bindings against those receipts, then accepts this gate. The adapter checks every
completed result's hash, row 13, absence of halt and headroom; it verifies all named
adjudication/report file hashes and consumes the report's phase states. It does
**not** substitute a new target-mapping judgment or recompute scorer results from
raw sources. An accepted primary gate is the trust boundary for the report's
correspondence to its scorer inputs; merely inventing `reachable` is not a P7 gate.

Only both `reachable` (or both `pass` where appropriate) permit the next cell.
An unreachable/failing gate writes SKIP for all remaining required cells and refuses
dispatch, using `OPQ-semantic-futility` or `FULL-semantic-futility` as the §8 rule id.
FULL additionally requires OPQ pass/pass and an accepted OPQ-freeze file containing
the release hash and exact three OPQ call bindings. Its hash enters each FULL intent
and DISPATCH_MARK. Every later FULL gate must preserve that hash and those bindings.
Thus OPQ adjudications cannot be swapped between FULL calls.

## Rule-to-code mapping

| Normative section | Implementation / evidence |
| --- | --- |
| PROTOCOL §4 P0; BUDGET §0 | `release_gate`: allowed policy, literal slot, both READY records, INIT/BIND agreement, accepted policy evidence and transitive documentation pins; real UNSET tested. |
| P1; BUDGET §1 K1–K3 | Dedicated label/attestation, exact zero machine record, non-resetting fundable limit ≤KEY_MAX; fresh sanitized preflight GET before every RESERVE. Host exclusively resolves the R17 credential. |
| P2; BUDGET §4 rules 1–4 | `Ledger`: canonical JSONL chain; INIT/release/BIND order; `ledger_shapes`; `recon.admit` under exclusive lock before RESERVE, reserving all remaining required calls under both operating and key capacity. |
| P3; PRIMARY-DECISIONS Q2; C2–C3 | `dispatched`: deep copy, only max_tokens 8192→16384; plan remains untouched; dual hashes; exact byte length+1024≤40000 immediately before durable DISPATCH_MARK and POST; validation and inverse verification use originating plan. |
| P4, P6, E7–E8 | Frozen source metadata, source input hash, immutable reference freeze, manifest/critical counts and integer thresholds. Primary's accepted P6 record supplies the semantic sufficiency/review evidence. |
| P5; C6 | Frozen scorer/spec/fixture pins, both primary-accepted all-packet fixture reports bound to cases/check; adapter/test freeze. All required release-artifact hashes checked again before send and after response. |
| P7; C6 intents | Release hash equals BIND_RELEASE; INIT entry hash matches release; intent binds release, reference, source, table, both request hashes and unique claim. Exclusive per-attempt dir and unreusable job identity. |
| P8, P9 | Accepted subscription/auth-role record; exactly six cells when testable, otherwise exactly the three OPQ cells. No FULL in the untestable required set. |
| §6 C1; §8 | `staged_gate` enforces next cell, both adjudicators, frozen OPQ pass before FULL; mechanical D1/D5/T6 SKIPs; semantic stops consume accepted interim results. |
| §6 C4; BUDGET §4 rules 6–7 | No POST loop or retry branch. A dispatched cell is completed forever for admission; pre-mark failures debit zero and require a fresh exclusive attempt/job. |
| §6 C5; §7 rows 1–13 | `response_state`, `completion`: ordered rows, raw bytes/hash, status/headers, exact usage substring, decimal cost token, content/native finish/identity, validation or WireError code, result and hash-pinned completion/stop receipts. |
| BUDGET §5 AD1–AD5 | `anomalies`: prompt/guard bound, completion cap, reasoning/cache/total consistency, exact cost/rate/263840000 bound, exact model/provider. A missing provider is refused. |
| AD7 | Full ledger re-read/chain comparison and independently expected aggregate before transport and after resolution/close; post-receipt/inverse/release integrity checks retained. |
| BUDGET §4 rules 5,13–14 | `recover_terms` recovers cost/rate from success and error bodies; exact imported `debit` takes max(FLOOR, reported, rate, attributable key delta); excess debit HALTs; `close_debit` retains highest usage through RECONCILE_UP. |
| BUDGET §5 RECON | `poll`: exact imported `reconcile` on cumulative costs, rising usage floor, reads at 0/60/300/900, first reconciliation stops polling, changed/reset/unlimited/excess/regressing/invalid usage halts; missing/malformed reads consume bounded slots. |
| BUDGET §4 rules 8–11 | `recover`: no transport parameter; unmarked zero-debit recovery; marked/torn uncertainty reconciled and charged then HALT. Torn bytes retained/fsynced, ledger truncated/fsynced; no stale-lock breaking; LOCK_RECOVERED first with human evidence. Every directory/receipt/append is fsynced. |
| P3 fixture equivalence | Twenty-five separately named L01–L25 tests run the pinned checker harness through the adapter's exact recon module. Integration tests cover both policies, 3/6-call plans, exceptions, recovery, receipts and fake-clock polling. |

## Conservative resolutions and limits

- The response table takes precedence over the shorthand “finish != stop halts”.
  Rows 10–12 cause a **profile failure and futility SKIPs**, not an invented terminal
  HALT. OPQ loses D1/O3; FULL loses T1/O1. RECON still runs, and can override either
  with terminal HALT. Every row 2–9 halts; schema rejection is claimed only for row 6.
- Model/provider equality is strict to the pinned values. Unlike R14's permissive
  dated-model/missing-provider path, a dated alias or missing identity is AD5 failure.
- JSON duplicate keys/nonfinite constants are refused. Unparseable HTTP-200 envelopes
  are row 8; a parseable envelope with bad/missing usage/cost is row 9. Decimal number
  tokens are preserved exactly; quoted USD strings are not accepted as numeric evidence.
- An existing attempt directory is never reopened for dispatch. Accounting recovery is
  a separate function and cannot send a POST. Only a proven unmarked zero-debit pause
  permits a new exclusive claim for that cell; marked/torn/incomplete receipt recovery
  always ends with HALT. Recovery reuses durable key-read results and consumes an
  uncertain read claim instead of repeating the GET.
- A crash before final completion, even after RESOLVE/RECONCILED, is recovered
  conservatively as terminal. An unexpected post-mark exception writes a halt sidecar
  and HALT when the chain is writable; explicit recovery completes accounting. A
  corrupt interior chain or unavailable filesystem cannot safely be repaired by this
  adapter: admission stays refused and primary-led evidence recovery is required.
- Hashes establish dependencies, not authenticity or chronology. Accepted primary
  records and the native signed job/claim are external trust boundaries. No hard cap
  or enforcement is claimed by the offline suite. Directory/file fsync ordering is
  exercised on this host; it is not a power-loss hardware guarantee.

## Remaining human work at P7

Select P0 in BUDGET and both design READY records, re-freeze changed policy artifacts,
and supply the accepted E-1/E-2 evidence or explicit P-ACCEPT statement. The frozen
recon/wire code pins cannot change without revising/reviewing this candidate.
Create and attest the dedicated key; confirm the actual usage field and USD units
from current provider documentation; perform/retain the native zero-usage machine
check without retaining identifying fields. Complete P5, P6/E1–E8 (including each
source's EXCEPT/RESTRICT relation, replacement records and P9), P8 and the manifest.

Review/pin a host driver and its no-retry, no-redirect, bounded-response and credential
allowlist behavior on the Mini, using only injected `OPENROUTER_API_KEY`. Prepare INIT,
the complete C6 release record and BIND_RELEASE, and fresh signed native jobs/claims
under the established release route. Pin this directory and the driver into those
jobs. Do not reuse R14's consumed claim or interpret its historical balance as R17's.

After each response, have A1/A2 map every scored target, run the pinned interim scorer,
and accept the staged gate; freeze OPQ pass/pass before FULL. Resolve any stale lock
only after recording owner-death evidence. Finish the final decision/FINAL.json,
skips, scope limitations, margins, sensitivity, local chronology caveat and independent
invoice-status caveat; disable the dedicated key after the experiment.

## Offline verification and manifest convention

Run `python3 -I -S -B adapter/test_adapter.py`. Temporary artifacts stay under
`adapter/` and are removed. `test-output.txt` retains the verbose final run; READY
records its count/result and all payload/dependency hashes. READY does not embed its
own hash, which would create a hash cycle; **the P7 release pins READY's exact file
hash externally**. No benchmark source bodies are hashed/opened to generate READY.
