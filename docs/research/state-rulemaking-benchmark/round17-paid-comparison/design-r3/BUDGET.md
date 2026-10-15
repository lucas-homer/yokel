# R17 budget, cap enforcement and ledger (design r3)

Status: **design proposal r3**. It authorizes nothing and supersedes `../design-r2/BUDGET.md` (frozen, unchanged). No provider call, network access or credential access was used to write it. Paths are relative to `docs/research/state-rulemaking-benchmark/` (BENCH). The executable reference semantics for §4–§5 are `fixtures/r17recon.py`, pinned by `fixtures/check.py` (ledger fixtures L01–L18).

Labels: **VERIFIED** (repo file or local offline command), **DERIVED** (arithmetic on verified numbers), **CONDITION** (an unverified premise that a conditional bound depends on), **ESTIMATE** (a forecast only).

The user-approved cap is **$2.00 hard, in a new R17 ledger namespace** (PRIMARY-DECISIONS Q1). The historical R9–R14 ledger and its $0.094009282 remainder are not read for R17 capacity and are never written.

## 0. Release policy slot — USER SELECTION REQUIRED

```text
RELEASE_POLICY = UNSET        allowed values: P-HARD | P-ACCEPT
```

The user replaces `UNSET` with exactly one value here and in `READY.json` (`release_policy`). Nothing else in this design changes with the choice: every mechanism in §1–§5 applies under both variants, and each variant below is complete as written. **While the value is `UNSET`, the paid phase stays unreleased.** An approval of a hard cap is not an acceptance of a conditional budget, and this design does not infer one.

**P-HARD.** Release only if documented charge-time enforcement, or a genuine pre-dispatch all-in upper bound, is established; otherwise the paid phase stays unreleased. "Established" means one of the following, recorded in `run/ENFORCEMENT-EVIDENCE.json` with the exact provider documentation captured (URL, retrieval time, SHA-256 of the captured bytes) and accepted by the cross-provider re-review before release:

- **E-1, charge-time enforcement:** the provider documents that a key's credit limit bounds the charges recorded against that key, so that a request whose charge would exceed the remaining allowance is rejected or cut off and usage cannot pass the limit. Then total R17 spend ≤ the key limit ≤ $1.73 < $2.00.
- **E-2, all-in upper bound:** each of CN1–CN4 (§3) is established before dispatch by current provider documentation or a provider-side pre-dispatch count, not by inference from the R14 receipt, giving a per-call all-in bound `B ≤ $0.27`. Then total R17 spend ≤ $1.73 + B ≤ $2.00.

Inference from silence, from the R14 receipt, or from the limit value alone does not establish either. As of 2026-10-13, the primary's check found that the documentation does not state E-1 (PRIMARY-DECISIONS addendum); E-2 has not been attempted.

**P-ACCEPT.** Release under the dedicated $1.73-limit key, with the user's explicit written acceptance that the bound is conditional, recording the stated residual risk. The acceptance is a verbatim user statement stored in `run/CAP-ACCEPTANCE.json` with its date, pinned in the release record, and it must include this residual-risk statement or one at least as specific:

> "If the key limit is enforced only when a request is admitted, one admitted request can be charged after usage reaches the limit. Spend is then at most $1.73 plus that request's charge. That charge is at most $0.26384, giving at most $1.99384, only if CN1–CN4 hold; if any of them fails, no bound is established and total spend can exceed $2.00. Reported usage is not invoice-verified (CN5)."

Under either variant the dedicated key (§1), the ledger (§4) and fail-closed reconciliation (§5) are mandatory defense in depth.

## 1. The dedicated key (both policies)

**Post-response checks cannot prevent overspend.** They run after the money is spent. The ledger, byte guard and anomaly checks therefore stop further releases; they do not cap a charge already incurred.

- **K1. Dedicated key.** The user creates a new OpenRouter API key used **only** for R17, labelled `yokel-r17-paid-comparison`, with a **credit limit** on the key. The R17 runner can resolve only this key's credential reference. It cannot resolve the R14 key or any other key. After R17, the user disables the key.
- **K2. Limit value and reset policy.** The limit `L` satisfies `R0 × FLOOR ≤ L ≤ $1.73`, where `R0` is the number of required calls (6, or 3 if FULL was omitted under PROTOCOL P9); `$1.73` is recommended. The limit must be **non-resetting**: no daily, weekly or monthly reset. (DERIVED: six floors are $1.62, leaving $0.11 under $1.73. A user-set limit below $1.62 cannot fund six floor reservations and fails K2; ruling 3.)
- **K3. Verification before release**, all three required and retained (no secret values anywhere):
  1. **User attestation** (`KEY-ATTESTATION.json`): key label, limit, reset policy, creation date, "used only for R17", and the selected `RELEASE_POLICY`.
  2. **Machine check** by the native runner with the injected R17 key, immediately before the release record is signed: one read of the provider's key-information endpoint. The primary's documentation check (PRIMARY-DECISIONS addendum) records `GET https://openrouter.ai/api/v1/key` returning `limit`, `limit_remaining` and `limit_reset`; the exact usage field and its units must be confirmed from current documentation when P1 is prepared. Pass only if `limit` is finite and equals the attested `L`, usage is 0, `limit_remaining` equals `limit`, and `limit_reset` shows no reset. Record only those fields, parsed as exact decimals, and the response hash. Drop any key-identifying field.
  3. **Fail closed.** If the endpoint cannot be confirmed, returns no limit (unlimited), shows prior usage, shows a reset policy, or disagrees with the attestation, the paid phase **stays unreleased**.
- **Fallback (binding):** if the user cannot or will not provide such a key, the paid phase **stays unreleased**. A soft budget (ledger plus checks) is **not** a substitute.

Residual risks the key does not remove (disclosed): the provider could fail to enforce its own documented limit; reported usage is not invoice-verified; and, unless E-1 or E-2 holds, an admission-time limit allows the one-request overshoot that P-ACCEPT records.

## 2. Verified inputs

| # | Fact | Source |
|---|---|---|
| V1 | R14 usage: prompt 6,730; completion 7,231 (includes 57 reasoning tokens nested in `completion_tokens_details`); cache-write 6,727; cached 0; `total_tokens` 13,961 = 6,730 + 7,231 | `round14-semantic-contract/execution/run/result.json:1` |
| V2 | R14 reported cost: total $0.0891335; prompt $0.0168235; completion $0.0723100. `invoice_verified: false` | same |
| V3 | R14 finished `stop` at 7,231 of 8,192 output tokens. **The cap was never hit**, so enforcement of `max_tokens` on this route is unobserved | `result.json:1`; `RECOVERY.md:12-13` |
| V4 | R14 body 28,307 B; guarded 29,331 B (= body + 1,024) | `RECOVERY.md:14`; `round16-wire-compat/protocol-w2-1/wire.py:337` |
| V5 | Request settings (frozen r15.1): `max_tokens` 8,192; reasoning low; `provider.max_price` {prompt 2, completion 10}; OpenAI only; no fallbacks. R17 changes only `max_tokens` → 16,384 | `round15-condition-preservation/protocol-revised/request-settings.json`; PRIMARY-DECISIONS Q2 |
| V6 | R14 adapter: rate estimate of 2,000 nanoUSD per prompt token and 10,000 per completion token; debit `max(reservation, reported, estimate)`; reservation $0.20 | `round14-semantic-contract/runtime/adapter.py:9-26,113-125` |
| V7 | Selected sources' guarded request bytes (full / opaque): 26-19-039 20,650 / 20,835; 26-19-041 21,944 / 22,129; 26-19-106 20,376 / 20,561. Reserves 116, 123, 135: 21,145–23,226 | `round17-paid-comparison/sources-r2/SCREEN.json` |

## 3. Derived rates and the conditional per-call bound

- **Completion:** $0.0723100 / 7,231 = **$10.00/M exactly**. Reasoning is inside `completion_tokens`; adding the 57 again would give $0.07288, which contradicts the receipt (DERIVED, one call).
- **Prompt:** $0.0168235 / 6,730 = **$2.499777117/M effective**. If the 3 unwritten tokens cost $2/M, the 6,727 cache-write tokens cost exactly $2.50/M. The receipt cannot separate base and cache-write prices, so that split is an inference (DERIVED).
- `max_price.prompt = 2` was in force while the prompt bill exceeded 6,730 × $2/M. **`max_price` is not an all-in prompt ceiling** (DERIVED). It is left unchanged, because only the output-cap delta is authorized.

**Conditional per-call bound:** 40,000 × $2.50/M + 16,384 × $10/M = **$0.26384** (263,840,000 nanoUSD). It holds **only if all of** the following are true:

- **CN1** (CONDITION): billed completion tokens ≤ `max_tokens` = 16,384, reasoning included. Unobserved (V3).
- **CN2** (CONDITION): billed prompt tokens ≤ 40,000, including any provider template or schema overhead. The byte guard bounds request **bytes**, not tokens, and the overhead is not established. R14's 4.21 B/token is slack in one request, not a proof.
- **CN3** (CONDITION): all-in rates ≤ $2.50/M prompt (cache-write included) and ≤ $10/M completion.
- **CN4** (CONDITION): no other billable component, such as a per-request fee or a tool or search charge.
- **CN5** (CONDITION): reported `usage.cost` approximates the billed amount. It is not invoice-verified.

**$0.26384 is a conditional bound per call; $1.62 is a conditional bound for six calls.** Neither is a guarantee, and the key limit alone is not one either. Whether the cap is hard depends on §0: under P-HARD it is hard by E-1 or E-2; under P-ACCEPT it is conditional, and the user has accepted that in writing.

## 4. Ledger rules, integer nanoUSD only

Constants: `CAP = 2,000,000,000`; `OPERATING = 1,800,000,000`; `FLOOR = 270,000,000` (the reservation per required call, ≥ the conditional bound, rounded up); `KEY_MAX = 1,730,000,000`.

1. **Storage.** An append-only JSONL file `round17-paid-comparison/run/ledger.jsonl`, namespace `r17.paid-comparison.v1`. Entry types: `INIT`, `BIND_RELEASE`, `RESERVE`, `DISPATCH_MARK`, `RESOLVE`, `RECONCILED`, `SKIP`, `RECONCILE_UP`, `RECOVER`, `LOCK_RECOVERED`, `HALT`.
2. **Hashed bytes (defined exactly).** An entry's bytes are `json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")`; the file line is those bytes plus `\n`. An entry's hash is SHA-256 of its bytes (without the newline). Every entry after `INIT` carries `prev_sha256`, the hash of the previous entry. A file hash is SHA-256 of the file's exact bytes on disk. The aggregate is **recomputed from the log** every time; there is no cached total.
3. **No hash cycle (R2-S1).** `INIT` pins only static configuration: namespace, the constants above, key label, verified key limit `L` and reset policy, `required_calls` (the six or three call ids), `RELEASE_POLICY`, and the SHA-256 of `BUDGET.md` and `fixtures/r17recon.py`. The **release record** (PROTOCOL C6) pins the `INIT` entry hash. A `BIND_RELEASE` entry then pins the release record's file hash. No `RESERVE` may precede `BIND_RELEASE`.
4. **Admission (every release), under the exclusive lock, before writing `RESERVE`** (`r17recon.admit`). Refuse if: there is no `BIND_RELEASE`; a `HALT` exists; any `RESERVE` is unresolved; any dispatched attempt lacks `RECONCILED`; or the call already completed (a dispatched `RESOLVE`) or was skipped. Otherwise let `R` = the number of required calls neither completed nor skipped, including this one. Admit only if **both**:
   - `Aggregate + R × FLOOR ≤ OPERATING`, where `Aggregate` = Σ `RESOLVE.debit` + Σ `RECONCILE_UP.debit` (with no pending reservation, by the refusal above); and
   - `U + R × FLOOR ≤ L`, where `U` is the last `RECONCILED` key usage.

   Admission therefore never counts a pending reservation twice (r2's $1.89 false failure; fixture L02) and includes key capacity (ruling 3; L04).
5. **Debit** for every possibly dispatched attempt (`DISPATCH_MARK` written) = `max(FLOOR, ceil_nano(reported_cost), p × 2,500 + c × 10,000, attributable key-usage increase)`. Missing terms are omitted, so the minimum is `FLOOR`. `reported_cost` is parsed as an exact decimal from the raw JSON number token, never a binary float, and rounded up (`r17recon.parse_usd`). Billing evidence is recovered from **any** response body, including error bodies.
6. **Not dispatched.** A `RESERVE` without `DISPATCH_MARK` resolves with debit 0 (`dispatched: false`). `DISPATCH_MARK` is fsynced immediately before the socket send; the adapter tests must prove that ordering (PROTOCOL P3). The call may be re-admitted after the offline fix (L06).
7. **No retries.** A dispatched call is never re-admitted (L05). A contentless or uncertain failure ends the paid phase as partial or inconclusive (PROTOCOL §7).
8. **Crash recovery.** On restart, under the lock: a `RESERVE` without `DISPATCH_MARK` resolves per rule 6 (a resumable pause). A `RESERVE` + `DISPATCH_MARK` without `RESOLVE` resolves as possibly dispatched: run the §5 reconciliation reads, write `RESOLVE` with rule 5 using every recoverable term, then `HALT`. Nothing is re-sent.
9. **Torn tail.** If the last line lacks its `\n` or does not parse, copy its bytes to `run/ledger-torn-<sha256>.bin` (fsync the file and the directory), truncate the ledger to the last complete line (fsync), and append `RECOVER {torn_sha256, torn_length}`. Whether the torn bytes were a `DISPATCH_MARK` cannot be proven, so if a `RESERVE` is unresolved, apply rule 8's dispatched branch: conservative debit, then `HALT` (fail closed).
10. **Lock.** `run/ledger.lock` is created with `O_CREAT|O_EXCL` and holds `{pid, host, started, run_id}`; the file and directory are fsynced. It is never broken automatically. The primary removes a stale lock only after recording evidence that its owner is gone; the next entry is `LOCK_RECOVERED`, followed by crash recovery (rule 8).
11. **Directory durability.** The `run/` directory is fsynced after creating the ledger, the lock, any sidecar and every receipt.
12. **Futility skips** write `SKIP` (reason, pre-registered rule id). This lowers `R`, never raises it.
13. **Hard stop.** If any debit term exceeds `FLOOR`, including an attributable key-usage increase that the response's own cost did not show, `HALT`. (r2's parenthetical "which implies an AD4 failure" was wrong: a key-usage excess can occur while AD4 passes.)
14. **Run close.** Retain `max(Σ debits, highest key usage since zero)` as the run debit, appending `RECONCILE_UP` for any shortfall (`r17recon.close_debit`; L16). Delayed usage is never charged to a later cell.

### Admission arithmetic (DERIVED; holds while every debit is FLOOR, otherwise rule 13 halts first)

| Release | Completed before | `R` | Aggregate + R × FLOOR | ≤ OPERATING 1.80? | `U` (at most) + R × FLOOR | ≤ L = 1.73? |
|---|---:|---:|---:|---|---:|---|
| OPQ1 | 0 | 6 | 1.62 | yes | 1.62 | yes |
| OPQ2 | 1 | 5 | 1.62 | yes | 1.62 | yes |
| OPQ3 | 2 | 4 | 1.62 | yes | 1.62 | yes |
| FULL1 | 3 | 3 | 1.62 | yes | 1.62 | yes |
| FULL2 | 4 | 2 | 1.62 | yes | 1.62 | yes |
| FULL3 | 5 | 1 | 1.62 | yes | 1.62 | yes |

(`U` at most = completed × FLOOR, because rule 13 halts on any larger attributable increase.) Headroom to the operating limit is $0.18 and to the cap $0.38; a seventh reservation (7 × $0.27 = $1.89) does not fit, which is why retries are deleted rather than budgeted. Fixture L01 replays this sequence.

### Spend by stopping point (conditional bounds at FLOOR per dispatched call)

| Stopping point (PROTOCOL §8) | Calls dispatched | Ledger debit (conditional) |
|---|---:|---:|
| OPQ futile after OPQ1 | 1 | $0.27 |
| OPQ futile after OPQ2 | 2 | $0.54 |
| OPQ fails D after OPQ3, or typed untestable | 3 | $0.81 |
| FULL futile after FULL1 | 4 | $1.08 |
| FULL futile after FULL2 | 5 | $1.35 |
| All six | 6 | **$1.62** |

**Expected spend (ESTIMATE, not a bound).** Prompt tokens ≈ guarded bytes / 4.21 ≈ 4.8–5.3k ≈ $0.012–0.013 per call. Completion ≈ 5–14k ≈ $0.05–0.14. That is roughly $0.06–0.15 per call and **$0.4–0.9 for six**. Debits are floor-dominated at $0.27 per call either way.

## 5. After every response: anomaly checks and cumulative reconciliation

These are **anomaly detection, not cost prevention**. They run after the provider has billed. Each failure writes a receipt with the raw bytes retained, debits per §4 rule 5, and **HALTs**.

| Check | Rule | Catches |
|---|---|---|
| AD1 prompt | `usage.prompt_tokens` present, an integer, `1 ≤ p ≤ guarded_bytes(call)` (≤ 40,000) | CN2 violated |
| AD2 completion | `usage.completion_tokens` present, an integer, `0 ≤ c ≤ 16,384` | CN1 violated |
| AD3 nested usage | if present: `reasoning_tokens` an integer with `0 ≤ r ≤ c`; `cached_tokens + cache_write_tokens ≤ p`, each an integer ≥ 0; `total_tokens == p + c` | double-counting, inconsistent usage |
| AD4 cost | `usage.cost` present, finite, ≥ 0; `ceil_nano(cost) ≤ p × 2,500 + c × 10,000 + 1,000`; and `ceil_nano(cost) ≤ 263,840,000` | CN3/CN4 violated (price drift, surcharges) |
| AD5 identity | model and provider equal the pinned values (R14 adapter rule) | routing drift |
| RECON key usage | cumulative, bounded reconciliation below (replaces r2 AD6) | CN5 under-reporting; key misuse; lag |
| AD7 ledger | the hash chain verifies; the recomputed aggregate equals the expected value | ledger integrity |

A missing or malformed `usage`/`cost` on HTTP 200 is an AD failure, not a free pass: the debit is `FLOOR`, then HALT.

**RECON (ruling 4; `r17recon.reconcile`, fixtures L08–L15).**

1. `INIT` pins zero initial usage, the limit `L` and its reset policy. Let `C` = Σ `ceil_nano(reported cost)` over all possibly-dispatched attempts so far, and `U` the provider's cumulative usage, parsed exactly. The comparison is always against `C` from the zero baseline, never a per-call delta from a possibly stale sample.
2. After every possibly-dispatched attempt `i`, including the last one and halted ones, read the key **immediately, then at 60, 300 and 900 seconds** after the attempt resolved, stopping at the first reconciled read: at most four reads. **No paid dispatch happens during reconciliation**; admission refuses until `RECONCILED` is written (L03).
3. Attempt `i` is reconciled when the read is valid, the limit and reset policy are unchanged, `U` has not decreased, and `|U − C| ≤ i × 1,000` nanoUSD. Then write `RECONCILED {call, U}`. The tolerance is an explicit measurement policy; amend it before release if documented reporting granularity requires another value. It cannot prove invoice correctness or replace cap enforcement.
4. `U < C − tolerance` means lag: wait for the next scheduled read. A stale zero is therefore never accepted as proof (L10). A decreased `U`, a changed, reset or unlimited limit, or `U > C + tolerance` halts immediately. After the 900-second read, or when all four reads have failed, write `KEY_USAGE_UNRECONCILED` and **HALT**. A halt during OPQ makes the outcome **P**; a halt during FULL after a frozen OPQ pass makes it **O1-incomplete**.
5. On a halt, the attempt's debit is §4 rule 5 with every recoverable term, including any attributable key usage. The other debit terms may **record** the halted attempt; they never justify another admission.

## 6. Alternatives (unchanged reasoning)

| `max_tokens` | Conditional max per call | FLOOR | 6 calls | Verdict |
|---:|---:|---:|---:|---|
| 8,192 (R14) | $0.18192 | $0.19 | $1.14 | Rejected: R16 requires a raise; R14 used 88% |
| 12,288 | $0.22288 | $0.23 | $1.38 | Rejected: weaker FULL headroom for a small saving |
| **16,384** | **$0.26384** | **$0.27** | **$1.62** | **Chosen** (PRIMARY-DECISIONS Q2) |
| 20,480 | $0.30480 | $0.31 | $1.86 | Rejected: over the $1.80 operating limit |

A third (R14-format) arm is excluded for scoring-fairness reasons (PROTOCOL R4). For arithmetic, at FLOOR three more calls are $0.81, so $1.62 + $0.81 = $2.43 > $2.00.

## 7. Deleted

- r2 §1's K-HARD/K-ADMIT branch and its statement "The guarantee is §1". Replaced by the §0 policy slot: admission-time enforcement is never called a guarantee.
- r2 AD6 (per-call delta with an unspecified lag allowance). Replaced by RECON (§5).
- r2 §4 rule 3's admission after `RESERVE` (double-counted the pending reservation) and rule 9's parenthetical.
- From r1: the unconditional "cannot exceed $1.62", the double-price containment example, the rule-2 debit without a floor, the C7 re-release, and the Phase B feasibility rule.
