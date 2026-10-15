# R17 P3 dispatch adapter r1.2 and host driver — offline candidate

This directory implements one invocation / one cell / at most one POST. It grants no
paid-release authority. The actual frozen policy is **UNSET**, so the real release
remains refused. No native runner, job, release script, credential lookup or network
operation was used in implementation or testing. Only synthetic source text is used
in tests; R17 source hashes come from `sources-r2/READY.json` without opening its texts.

The executable semantic authority is **the exact design-r3.1 `fixtures/r17recon.py`**:
SHA-256 `5295a66700fee54b2e03344003e5638a5728b1949eedf0945062950cc40e33ff`.
`dependencies()` verifies it against `READY.primary.json`, checks the pinned wire hash
against `sources-r2/READY.json` `upstream.wire.sha256`, and executes verified bytes by path. Admission, pending
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
python3 -I -S -B adapter-r1-2/r17_adapter.py --cell S1-OPQ \
  --release run/RELEASE.json --run-root run --attempt-dir run/S1-OPQ-claim1 \
  --job-id unique-native-job-id --driver reviewed-host-driver.py \
  --driver-sha256 <release-pinned-sha256>
```

Subsequent calls also need `--staged-gate`; FULL calls need `--opq-freeze`.
Paths above are examples, not prepared or authorized jobs. `host_driver.py` is now
provided as uninvoked production code, tested with fake HTTPS connections and real http.client over fake sockets and
a replaced synthetic environment mapping. Its required exports are `source(cell)`, `post_once(url, exact_bytes)`
and `key_info(url)`. Its SHA-256 must match the release's `driver_sha256`.
Importing the driver and obtaining source must perform no provider/credential I/O;
only its callbacks may perform the explicitly authorized operations, after the gate.

`post_once` receives the exact immutable serialized request bytes. It returns a dict
with `status` (integer), `raw` (bytes), `headers` (sanitized dict), and
`tls_ca_sha256` (the SHA-256 of the explicitly loaded CA bundle). Legacy synthetic
callbacks may omit only this metadata field; the production host driver always returns it. It must
perform exactly one POST to `/api/v1/chat/completions`, with no redirect following,
HTTP client retry, streaming, fallback, repair or provider substitution. The adapter
has **one POST call site**, outside all polling/recovery loops. Callback exceptions
become transport-uncertain; they cannot invoke that call site again.

`key_info` performs one GET `/api/v1/key`, returning:

```text
{fields: exact JSON bytes containing only usage, limit, limit_remaining, limit_reset,
 response_sha256: SHA-256 of the original endpoint response bytes,
 tls_ca_sha256: SHA-256 of the explicitly loaded CA bundle}
```

These are a **normalized callback contract**, not a claim that the live endpoint's
usage field/units have been established. Values for money are JSON numeric USD
tokens, parsed exactly and rounded upward by `r17recon.parse_usd`. Key-identifying
fields are dropped **before** crossing into the adapter. Header sanitization now occurs independently in both driver and adapter; no authorization, key-identifying or cookie header may
be returned. Only explicit host callbacks may use
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
The native release pins `driver_sha256` and an artifact named `host_driver`; the CLI
verifies its bytes, hash and resolved path before importing the verified bytes. The
release must cover the driver in its signed dependency manifest. Tests use a private synthetic artifact root under this
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

Run `sh adapter-r1-2/run_tests.sh`. Every Python test is a script launched with
`python3 -I -S -B`; temporary artifacts stay under excluded `adapter-r1-2/_out/` and are removed. `_out/test-output.txt` retains the verbose final run; READY
records its count/result and all payload/dependency hashes. READY does not embed its
own hash, which would create a hash cycle; **the P7 release pins READY's exact file
hash externally**. No benchmark source bodies are hashed/opened to generate READY.


## r1.1 deltas and review disposition

The frozen `../adapter/` and `../adapter-r1-1/` are unchanged. This r1.2 directory
was copied from r1.1; the following round-1 changes are inherited.
The exact recon/wire authority, request derivation, dual hashes, integer accounting,
one adapter POST site, no retry, and release policy UNSET remain as in r1.
Implementation and tests were entirely offline. No real environment credential was
read: tests replace `os.environ` itself with a synthetic mapping (never copy the
real mapping), and replace `http.client.HTTPSConnection` before invoking callbacks.
No native runner, real job, provider call, source body or reference file was opened.
The original L01–L25 tests remain pinned-engine tests, **not adapter coverage**.

| Finding | Disposition and evidence |
| --- | --- |
| S1 | Fixed. Both `filter_headers` implementations permit only content-type, date, x-request-id, x-openrouter-request-id, x-openai-request-id, openai-request-id, and valid x-ratelimit-* names. Names lower-case; values capped at 1,024 characters; CR/LF and bearer/sk-or-/authorization/set-cookie values dropped. All other names, including authorization/cookie/set-cookie, are dropped. Per this revision brief, dropped headers do not by themselves change a valid response's row; the review's optional packet-HALT suggestion is not adopted. Driver additionally rejects a raw body or permitted header containing its synthetic/current key before returning. `test_s1_allowlist_receipts` scans every receipt; H3 tests compare both filters. |
| S2 | Fixed. `Ledger.load` records byte offset and last-line hash. `assert_tail` checks fstat size plus the exact last-line hash on the append descriptor before **every** append, and immediately before attempting DISPATCH_MARK. A stale writer refuses rather than adding RESOLVE to someone else's tail. `verify` restores all cached state on failure. Review interleaving gives exactly one POST and a clean chain; same-size mutation and size-change tests included. The lock remains the exclusivity boundary: this is a stale-writer check, not an atomic multi-process compare-and-swap under deliberate lock violation. |
| S3 | Fixed. Staged-gate hash enters RESERVE and is checked on pending gate reads and immediately before the mark; referenced report/adjudicator pins are reverified. `staged_gate` cannot append SKIP while any RESERVE is pending. A changed gate causes a zero-debit not-dispatched RESOLVE, with no SKIP. Regression proves recovery succeeds and a corrected reachable gate plus fresh job can dispatch. |
| N1 | Fixed. `recovery_calls` is shared by execute/recover/CLI. A marked call without a structurally complete completion/stop/recovered receipt refuses dispatch, including valid JSON `{}`. Recovery finishes conservative accounting and HALTs. |
| N2 | Fixed. Mark uncertainty is set before append; append tracks bytes after flush before fsync. A failed mark fsync never produces RESOLVE(dispatched=false) on a marked chain. Tests establish zero POSTs, a loadable chain, FLOOR-or-greater recovery debit, and idempotent subsequent recovery. |
| N3 | Fixed. Normally stopped or fully recovered resolved calls are excluded even without RECONCILED. Recovery adds no duplicate HALT, GET, or misleading recovered receipt to a normally stopped call. |
| N4 | Fixed for torn/malformed status, reconciliation, read-claim and final receipt JSON. `receipt` retains exact damaged bytes in a hash-named .torn-*.bin sidecar, fsyncs it, and consumes a damaged GET receipt/claim as an uncertain failed slot. No repeat of that GET. Recovery safely defaults a torn status timestamp and can write recovered.json. IO unavailability and corrupt interior ledger remain refused; fsync is not a hardware power-loss guarantee. |
| N5 | Fixed. Every production-clock sleep argument is clamped to [0,60]; deadline-crossing repro now completes without negative sleep. |
| N6 | Deferred. Reconciliation still uses the wall-clock contract shared with r1's persisted resolved_at and fake clock. A monotonic redesign would need persisted restart semantics and fresh review. Forward/backward wall-clock changes can shorten/lengthen real waits. H10 NTP evidence remains a pre-run responsibility. |
| N7 | Deferred reporting-only vocabulary issue. FULL mechanical stops still use D1/D5 in ledger SKIP entries; interpret these as FULL T1/headroom mechanical futility with outcome O1 as PROTOCOL §8 specifies. Execution correctly stops FULL. Expanding the frozen reporting vocabulary needs primary agreement/review. |
| N8 | Fixed. MAX_RAW is checked before decoding/parsing in response classification and accounting recovery. Oversized fake transport bodies never reach strict JSON parsing; HTTP 200 is row 8. Driver has its independent read cap. |
| N9 | Fixed. Non-UTF-8 HTTP 200 is explicitly malformed row 8; raw_usage decoding errors cannot escape as an unexpected post-mark exception. Original raw bytes remain retained by adapter. No UTF-16/32 auto-detected response is scored. |
| N10 | Deferred. Library `hook` remains an offline test seam. Neither CLI supplies it; importing callers must leave it None in production. It has no command-line flag. |
| N11 | Deferred. os.fsync plus directory fsync remain portable semantics; Darwin F_FULLFSYNC is not implemented or claimed. Mini hardware durability remains unverified. |
| N12 | Fixed documentation: dependencies() checks `sources-r2/READY.json` upstream.wire.sha256, not the r16 READY directly. READY also lists and verifies the r16 READY dependency. |
| N13 | Fixed. CLI output distinguishes fixed refusal codes from existing lock/claim and generic internal failure. Arbitrary exception strings and artifact names never print. Exit 0 valid cell; 1 retained stopped/failed response; 2 refusal (also argparse syntax error); 3 lock/claim exists; 4 unexpected internal failure. |
| Test-quality note | Retained 77 original adapter tests and 25 pinned-engine L fixtures separately. Added revision/CLI, host and eight behavioral repro checks plus one copy-integrity check; final exact counts are in _out/test-output.txt and READY.json. |

Append detects a stale on-disk tail but cannot stop an external actor who removes
locks or writes concurrently after the comparison. Never break a live lock, mutate
ledger bytes, or rewrite gate/report/freeze/release files during an invocation.
The implementation itself never breaks a lock. The repros deliberately simulate
the review's forbidden lock removal solely inside synthetic temporary directories.

## Host driver H1–H10 mapping

| Requirement | Implementation / offline evidence / remaining host work |
| --- | --- |
| H1 | `_request` makes one `http.client.HTTPSConnection` and one request, POSTing the same bytes object, explicit Content-Length and JSON content type. No redirect handling, retry, pool, streaming request, fallback host or serializer. Connection closes on all paths. Tests cover object identity, 302 return, fresh connections and end-to-end durable mark ordering. |
| H2 | Connect/write/response/read/close failures become fixed DriverError messages without retained exception context. No resend; timeout tests at write, response and read seams, plus adapter row-2 integration. |
| H3 | Exact status/raw/headers packet; lower-case capped shared allowlist at driver and adapter boundaries. Unknown/sensitive headers never reach receipts. Driver status must be int 100..599. |
| H4 | OPENROUTER_API_KEY is read only in post_once/key_info; no import-time lookup, other variable, file, keychain, label or argv source. Missing/invalid key refuses before creating a connection. Stdlib direct connection ignores proxy variables, host is pinned, TLS uses PROTOCOL_TLS_CLIENT with the explicit `/etc/ssl/cert.pem` bundle, CERT_REQUIRED and hostname checking, without SSLKEYLOGFILE handling. Generic exceptions and key-echo rejection keep the key out of results/receipts/errors. Tests never consult the real environment. |
| H5 | One bounded response.read(MAX_RAW+1) sentinel read; greater than 2,000,000 refuses, discards the response and closes without another request/read. At most one sentinel byte beyond the cap is consumed; no oversized packet reaches adapter. Tests cover exactly cap and both over-cap cases, POST and key GET. |
| H6 | One GET /api/v1/key. _key_fields unwraps data, rejects duplicate/nonfinite/malformed JSON, returns only usage/limit/limit_remaining/limit_reset, and preserves original integer/decimal/exponent numeric tokens through Token, never float. response_sha256 hashes original raw bytes. Live usage meaning/units remain P1's documentation gate and were not checked online. |
| H7 | Import is inert (stdlib imports/function/constants only). source(cell) chooses the selected ascending slot from sources-r2/READY.json, reads only that slot's parsed-body.txt and UTF-8 decodes exact bytes without newline translation. It does not parse original.htm or read references. Only a synthetic sources-r2 tree is exercised by tests. Adapter verifies source hash against the accepted scoring manifest, refusing an inconsistent selection/replacement. |
| H8 | `host_driver.main` routes exactly one required --cell to adapter CLI, deriving its own driver path/hash and enabling recovery-first. Under exclusive locks the CLI probes, calls recover if required, then rechecks admission; marked recovery HALTs/refuses before source or another POST. Plain adapter CLI refuses recovery-required state. Every execution rechecks under its lock. Existing locks remain intact (exit 3); neither CLI ever breaks one. Unique job/attempt path and no re-admission are enforced by adapter. An externally removed stale lock requires primary-recorded evidence via `--lock-evidence FILE`; this invocation only recovers accounting and returns without dispatch. It checks a matching local host, positive PID, owner_gone true, a recorded lock SHA-256, and os.kill(pid, 0) reporting ProcessLookupError. A live PID, EPERM, unknown error, foreign host or extant lock refuses. The CLI does not invent evidence or remove a lock. Operational serialization and owner-death judgment remain external. |
| H9 | CLI enforces driver_sha256 and artifact host_driver hash/path, then executes verified driver bytes. READY pins candidate payload files and dependencies; `_out/**` is excluded. Primary must sign the complete release and pin READY's own exact SHA externally (self-hash cycle excluded); no paid release or signature was produced here. |
| H10 | External pre-run requirement: retain Mini NTP-sync evidence. Not attempted offline. N5 fixed; N6 remains explicitly deferred. No live-clock accuracy or hardware durability claim. |

Example future host CLI (illustration only, **never invoked in this task**):

```text
python3 -I -S -B adapter-r1-2/host_driver.py --cell S1-OPQ \
  --release run/RELEASE.json --run-root run --attempt-dir run/S1-OPQ-fresh \
  --job-id fresh-unique-id
```

## Repro evidence and readiness

`repros/` contains all eight original review repros and run_all.sh unchanged.
Only _load.py's adapter import path and temporary-output location are changed
to this copied directory and its excluded _out folder. The final
suite invokes `sh repros/run_all.sh` and retains `_out/repro-r1-2.txt`, then asserts each
fixed behavior from its output. Their original convention is exit 0 = bug reproduced:
all eight now exit 1. N1 exits on the new recovery_required refusal; N3's obsolete
print of the spurious recovered.json raises FileNotFoundError after showing identical
ledger before/after and zero recovered calls. These are expected artifacts of keeping
the original repros intact, not suite failures. Strong regression tests separately
assert the intended receipts, chain, recoverability and idempotence.

S1 drops token/cookie/unknown headers; S2 produces one POST and clean chain; S3 has no
SKIP while pending and recover succeeds; N1 refuses the next cell; N2 makes no POST
and remains recoverable; N3 makes recovery a no-op; N4 recovers a torn receipt; N5
has no negative-sleep error. repro-baseline.txt retains the eight reproduced r1
findings from the initial copied bytes; no frozen adapter file was modified.

READY is an offline implementation candidate, **not release authorization**. Remaining
items: primary independent re-review/P7 pin and signature; unchanged P0/P1/P5/P6/P8
release gates; live field/units confirmation and dedicated-key verification; Mini NTP
and durability evidence; the explicitly deferred N6/N7/N10/N11 limitations above.


## r1.2 round-2 disposition

The full round-2 REVIEW.md was read. This revision makes targeted changes to the
copied adapter and host; recon/wire authorities and release policy UNSET are unchanged.
No network/provider calls, real connections, credential access, original source-body
reads, reference reads, installs, commits, or writes outside this directory occurred.

| Finding | Disposition / regression evidence |
| --- | --- |
| S4 | Fixed: TIMEOUT_S = 900 seconds, including the POST response/read wait. The same envelope applies to connect/write and GET operations; no retry or timeout recovery resend. Fake-socket regression models 300 seconds of silence without sleeping and verifies one exact POST; beyond-envelope timeout remains transport-uncertain, FLOOR/HALT. Provider/CDN idle-limit documentation remains the primary's external P1 gate. |
| S5 | Fixed: both CLIs accept --lock-evidence FILE using the same release-pinned callbacks. This route verifies evidence/PID before recover(lock_evidence=...), then returns without source lookup, admission, attempt creation or POST. Unmarked recovery resolves zero debit; marked recovery is conservatively terminal. Tests cover dead/live PID, EPERM/unknown error, foreign host, malformed evidence and retained lock. |
| S6 | Fixed: generated logs and temporary fixtures go to excluded _out. pin_ready.py excludes _out/** and READY itself. verify_ready.py runs the entire suite, asserts every payload/dependency pin, unchanged READY bytes and unchanged payload membership before/after. The known stale r1.1 repro pin is left untouched; dependencies record its actual frozen bytes. |
| N14 | Fixed: PROTOCOL_TLS_CLIENT + load_verify_locations(cafile='/etc/ssl/cert.pem') explicitly bypasses SSL_CERT_FILE/SSL_CERT_DIR and default-root discovery. CERT_REQUIRED, check_hostname and no keylog remain. Missing/unreadable bundle, zero x509_ca or bytes changing while loading refuses before connect. The bundle's SHA-256 enters key-preflight, status and each performed reconciliation-GET receipt, including transport failures after context construction. It is never a READY/release CA pin: OS updates may change it. Fake-socket tests exercise real context construction; a separate mock verifies the exact cafile argument and empty-store refusal. |
| N15 | Fixed (trivial): derive self path from __file__; catch import/pin/file failures in host main with key-free host_driver_failure and exit 4. Renamed-copy and failed-import tests pass. |
| N16 | Fixed: del key in both callbacks; del key/headers/connection/response/raw/safe_headers in request finally. Drop original exception traceback/args/context; raise fresh key-free errors or BaseExceptions outside handlers. KeyboardInterrupt/SystemExit preserve interruption semantics and retained-lock handling. Tests inspect every driver traceback frame on transport/TLS/key-GET failures and interrupts. A caller that independently holds a key can still expose its own locals. |
| N17 | Documented/deferred: frozen recon Decimal precision >28 significant digits is unchanged; no recon re-pin. Primary must keep usage evidence within the documented precision range. |
| N18 | Fixed (trivial): explicit allowlist of pinned recon admission reasons is printable. Arbitrary/untrusted reasons still map to gate_refused. |
| N19 | Addressed by validation and runbook: spaces/newlines/controls in keys refuse before any connect with key-free errors. No trimming or repair. |
| N20 | The brief's key-validation request is fixed: reject every ASCII control (0..31 and 127) and whitespace, including leading/trailing characters. The review's distinct N20 interruption note is documented: BaseException after DISPATCH_MARK conservatively ends the experiment after recovery; run detached and avoid Ctrl-C during generation or reconciliation. |
| N21 | Fixed: pinned fake_http.py adopts Fable's real-http.client/fake-socket seam; regressions cover exact framing, one Host/Content-Length, 100 Continue, redirects, disconnect/timeouts, bounded chunked/close-delimited reads, TLS context and per-call CA receipts. |

Evidence schema for the accounting-only CLI route:

```json
{"owner_gone": true, "pid": 12345, "host": "recorded-local-host", "lock_sha256": "<64 lowercase hex>"}
```

The operator preserves the removed lock's exact hash, PID and host in this evidence
file and removes only the proven-dead lock. The adapter never removes it. Hash
authenticity is the operator's evidence responsibility; a removed file cannot be
rehashed by the CLI. os.kill(pid, 0) is rechecked at invocation time; PID reuse
refuses. All normal release/driver pin requirements and existing required CLI
arguments remain in force. Add --lock-evidence FILE to the host CLI example above.
Successful recovery exits 0 and prints that no dispatch occurred. Existing lock on
this explicit route refuses with exit 2; normal invocation still reports exit 3.
A competing owner winning the recover lock still causes exit 3.

### Round-2 repro disposition (unchanged repro assertions)

All seven Fable repros and the eight originals were copied under
_out/round2-repros. Only the two _load.py adapter import paths were adapted; copy
integrity is tested. Raw output is _out/round2-repro-output.txt.

| Repro | Exit | Interpretation |
| --- | --- | --- |
| repro_3call_plan.py | 0 | All good-behavior checks pass. |
| repro_hd_wire.py | 0 | All good-behavior checks pass, timeout now 900 and roots 128. Its unasserted capture_locals note still says True because the repro caller itself holds synthetic key/transport objects; driver-frame regressions independently prove removal. |
| repro_hd_key_fields.py | 0 | All good-behavior checks pass; N17 informational precision limit unchanged. |
| repro_hd_trust_store.py | 1 | Finding does not reproduce: 128 roots before/after synthetic SSL_CERT_FILE; synthetic CA is not trusted. |
| repro_hd_sigint_cli.py | 1 | Only obsolete assertion 'CLI exposes no lock-evidence option' fails. Interrupt, one-send, retained-lock, accounting recovery and terminal refusal checks pass. New tests exercise the actual evidence CLI route. |
| repro_hd_cli_misc.py | 1 | Its two obsolete expectations fail: renamed copy now returns normally; import error is caught. New regressions assert corrected behavior. |
| repro_hd_timeout_row2.py | 0 | Deliberately times out beyond TIMEOUT_S (now 900), so required one-send/FLOOR/HALT still holds. Its static closing text about 60 seconds is obsolete; the new 300-second silent-peer test proves S4 fixed. |
| Eight original repros | all 1 | None of the round-1 findings reproduces; behavioral tests remain passing. |

### Verification

180 suite tests pass: 102 inherited base tests (77 adapter + 25 pinned-engine
fixtures), 26 r1.1 revision/CLI tests, 23 host tests, 9 round-1 repro checks and
20 round-2 targeted tests. The 25 engine fixtures are not adapter coverage.
An additional verify_ready.py integrity test re-runs all 180 and verifies every
payload/dependency hash plus READY.json after that full run (181 distinct tests).

```text
sh adapter-r1-2/run_tests.sh > adapter-r1-2/_out/test-output.txt 2>&1
python3 -I -S -B adapter-r1-2/pin_ready.py
python3 -I -S -B adapter-r1-2/verify_ready.py
```

No CA-bundle bytes/hash are pinned. Logs, repro copies/results and setup helpers
under _out are excluded. The frozen adapter-r1-1 directory is never written.
Remaining primary gates are unchanged, with external CDN idle-limit validation
and Mini trust-bundle availability also requiring confirmation before a paid run.
