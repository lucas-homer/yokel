# R17 budget, hard-cap enforcement and ledger (design r2)

Status: **design proposal r2**. It authorizes nothing and supersedes `../design/BUDGET.md` (frozen r1, unchanged). No provider call, network access or credential access was used to write it. Paths are relative to `docs/research/state-rulemaking-benchmark/` (BENCH).

Labels: **VERIFIED** (repo file or local offline command), **DERIVED** (arithmetic on verified numbers), **CONDITION** (an unverified premise that a conditional bound depends on), **ESTIMATE** (a forecast only).

The user-approved cap is **$2.00 hard, in a new R17 ledger namespace** (PRIMARY-DECISIONS Q1). The historical R9–R14 ledger and its $0.094009282 remainder are not read for R17 capacity and are never written.

## 1. How the hard cap is actually enforced (B1)

**Post-response checks cannot prevent overspend.** They run after the money is spent. This design therefore does not rest the $2.00 hard cap on the ledger, the byte guard or the anomaly checks. It rests it on **an experiment-isolated provider spending limit**. That is a hard precondition for releasing any paid call (PROTOCOL P1):

- **K1. Dedicated key.** The user creates a new OpenRouter API key used **only** for R17, labelled `yokel-r17-paid-comparison`, with a **credit limit** set on the key. The R17 runner can resolve only this key's credential reference. It cannot resolve the R14 key or any other key. After R17, the user disables the key.
- **K2. Limit value.** Primary decision: **$2.00**. Keep it there if the provider documents that the key limit rejects requests or charges beyond the remaining allowance, so that no in-flight request can push usage past the limit (**K-HARD**). If the documentation says the limit is checked only when a request is admitted, or does not say (**K-ADMIT**), set the limit to **≤ $1.73**. The one call that can be in flight, since calls are sequential, then has $0.27 of room under $2.00. This residual is conditional on §3 (one call ≤ $0.26384) and must be stated in the release record. The user must accept it in writing, or the phase stays unreleased.
- **K3. Verification before release**, all three required and retained (no secret values anywhere):
  1. **User attestation** (`KEY-ATTESTATION.json`): key label, limit, creation date, "used only for R17", and which K2 branch applies, with a link to or a pinned capture of the provider documentation the branch relies on.
  2. **Machine check** by the native runner with the injected R17 key, immediately before the release record is signed: a read of the provider's key-information endpoint. **UNVERIFIED offline:** OpenRouter documents a current-key endpoint returning fields such as `limit`, `usage` and `limit_remaining`. The exact path and fields must be confirmed from current documentation when P1 is prepared. Pass only if `limit` is finite and ≤ the K2 value, `usage` is 0, and `limit_remaining` equals `limit`. Record only those fields and the response hash. Drop any key-identifying field.
  3. **Fail closed.** If the endpoint cannot be confirmed, returns no limit (unlimited), shows prior usage, or disagrees with the attestation, the paid phase **stays unreleased**.
- **K4. Per-call reconciliation** (anomaly detection, AD6 in §5): re-read key usage before each later release.
- **Fallback (binding):** if the user cannot or will not provide such a key, the paid phase **stays unreleased**. A soft budget (ledger plus checks) is **not** a substitute for the approved hard cap.

Residual risks the key does not remove (disclosed, not hidden): the provider could fail to enforce its own documented limit; K-ADMIT overshoot depends on §3; and reported usage is not invoice-verified. None of these has an established bound. They are why the ledger below stays conservative.

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

Labels used from here on: **$0.26384 is a conditional bound per call; $1.62 is a conditional bound for six calls.** Neither is a guarantee. The guarantee is §1.

## 4. Ledger rules (B2), integer nanoUSD only

Constants: `CAP = 2,000,000,000`; `OPERATING = 1,800,000,000`; `FLOOR = 270,000,000` (the reservation per required call, ≥ the conditional bound, rounded up).

1. **Namespace and storage.** The ledger is an append-only JSONL file `round17-paid-comparison/run/ledger.jsonl`, namespace `r17.paid-comparison.v1`. Each entry carries `prev_sha256` (a hash chain). It is written under an exclusive lock created with `O_CREAT|O_EXCL`, and every entry is fsynced before the next action. Entry types: `INIT`, `RESERVE`, `DISPATCH_MARK`, `RESOLVE`, `SKIP`, `HALT`. The aggregate is **recomputed from the log** every time; there is no cached total.
2. **Aggregate** = Σ `RESOLVE.debit` + Σ `FLOOR` for every `RESERVE` with no `RESOLVE` (pending reservations count in full).
3. **Admission (every release).** Let `R` = the number of **required calls not yet resolved or skipped**, including the one being released. `R` starts at 6, or at 3 if typed logic was declared untestable before dispatch (PROTOCOL E8). Release only if `Aggregate + R × FLOOR ≤ OPERATING`. This reserves **all remaining required calls**, not just the next one.
4. **Debit** for every **possibly dispatched** attempt (`DISPATCH_MARK` written) = `max(FLOOR, ceil_nano(reported_cost), p × 2,500 + c × 10,000, ceil_nano(key_usage_delta))`. Any term that is unavailable is omitted, so the minimum is `FLOOR`. `reported_cost` is parsed as a **decimal from the raw JSON number token**, never as a binary float, and rounded up to the nanoUSD. Billing evidence is recovered from **any** response body, including error bodies, that carries usage or cost. The R14 floor is restored; dropping it was the r1 error.
5. **Not dispatched.** A `RESERVE` with no `DISPATCH_MARK` resolves with debit 0. `DISPATCH_MARK` is fsynced immediately before the socket send; the adapter test suite must prove that ordering (PROTOCOL P3).
6. **No retries.** There is no re-release of any call. A contentless or uncertain failure ends the paid phase as **partial/inconclusive** (PROTOCOL §7). Phase B is deleted (PRIMARY-DECISIONS Q4).
7. **Crash recovery.** On restart, a `RESERVE` + `DISPATCH_MARK` with no `RESOLVE` resolves as possibly dispatched, using rule 4 with every evidence term that can be recovered (including the key usage delta), and is followed by `HALT`. Nothing is re-sent.
8. **Futility skips** write `SKIP` (reason, pre-registered rule id). This lowers `R`, never raises it.
9. **Hard stop.** If any debit exceeds `FLOOR` (which implies an AD4 failure), `HALT`.

### Admission arithmetic (DERIVED; holds under §3 conditions, otherwise AD halts first)

| Release | Resolved before | Pending | `R` | Aggregate + R × FLOOR | ≤ 1,800,000,000? |
|---|---:|---:|---:|---:|---|
| OPQ1 | 0 | 0 | 6 | 1,620,000,000 | yes |
| OPQ2 | 1 × FLOOR | 0 | 5 | 1,620,000,000 | yes |
| OPQ3 | 2 × FLOOR | 0 | 4 | 1,620,000,000 | yes |
| FULL1 | 3 × FLOOR | 0 | 3 | 1,620,000,000 | yes |
| FULL2 | 4 × FLOOR | 0 | 2 | 1,620,000,000 | yes |
| FULL3 | 5 × FLOOR | 0 | 1 | 1,620,000,000 | yes |

Headroom to the operating limit is $0.18 and to the cap $0.38. That is not enough for even one extra reserved call: 7 × $0.27 = $1.89 > $1.80. This is why retries are deleted rather than budgeted.

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

## 5. Anomaly detection: fail-closed checks after every response

These are **anomaly detection, not cost prevention**. They run after the provider has billed. They stop further releases and make the receipt fail closed. Each failure writes a receipt with the raw bytes retained, debits per §4 rule 4, and **HALTs** the run.

| Check | Rule | Catches |
|---|---|---|
| AD1 prompt | `usage.prompt_tokens` present, an integer, `1 ≤ p ≤ guarded_bytes(call)` (≤ 40,000) | CN2 violated; this direct check was missing in r1 |
| AD2 completion | `usage.completion_tokens` present, an integer, `0 ≤ c ≤ 16,384` | CN1 violated |
| AD3 nested usage | if present: `reasoning_tokens` an integer with `0 ≤ r ≤ c`; `cached_tokens + cache_write_tokens ≤ p`, each an integer ≥ 0; `total_tokens == p + c` | double-counting, inconsistent usage |
| AD4 cost | `usage.cost` present, finite, ≥ 0; `ceil_nano(cost) ≤ p × 2,500 + c × 10,000 + 1,000`; and `ceil_nano(cost) ≤ 263,840,000` | CN3/CN4 violated (price drift, surcharges) |
| AD5 identity | model and provider equal the pinned values (R14 adapter rule) | routing drift |
| AD6 key reconciliation | before the next release, re-read key usage. Require `0 ≤ usage_after − usage_before ≤ ceil_nano(reported cost) + 1,000`, and require that the limit is unchanged. If usage lags, re-read at most 3 times over 15 minutes, then fail | CN5 under-reporting; key misuse |
| AD7 ledger | the hash chain verifies; the recomputed aggregate equals the expected value | ledger integrity |

A missing or malformed `usage`/`cost` on HTTP 200 is an AD failure, not a free pass: the debit is `FLOOR`, then HALT.

## 6. Alternatives (unchanged reasoning, corrected arithmetic)

| `max_tokens` | Conditional max per call | FLOOR | 6 calls | Verdict |
|---:|---:|---:|---:|---|
| 8,192 (R14) | $0.18192 | $0.19 | $1.14 | Rejected: R16 requires a raise; R14 used 88% |
| 12,288 | $0.22288 | $0.23 | $1.38 | Rejected: weaker FULL headroom for a small saving |
| **16,384** | **$0.26384** | **$0.27** | **$1.62** | **Chosen** (PRIMARY-DECISIONS Q2) |
| 20,480 | $0.30480 | $0.31 | $1.86 | Rejected: over the $1.80 operating limit |

A third (R14-format) arm is excluded for scoring-fairness reasons (PROTOCOL R4). For arithmetic, at FLOOR three more calls are $0.81, so $1.62 + $0.81 = $2.43 > $2.00. The r1 "$0.55 / $2.17" figure is withdrawn.

## 7. Deleted from r1

- "Even if every call hits its ceiling … the protocol cannot exceed $1.62" (unconditional). It is replaced by the conditional labels in §3 and the enforcement in §1.
- The double-price containment example (r1 §6 rule 4). Post-response checks cannot contain a charge that has already happened.
- The rule-2 debit without a floor, the C7 re-release, and the Phase B feasibility rule (r1 §6 rules 2 and 5).
