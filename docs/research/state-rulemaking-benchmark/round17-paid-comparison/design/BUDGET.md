# R17 budget arithmetic

Status: design proposal, not authorization. No provider call, network access or credential access was used to write it. Paths are relative to `docs/research/state-rulemaking-benchmark/` (BENCH).

Labels: **VERIFIED** means read from a repo file (file:line) or reproduced by a local offline command. **DERIVED** means arithmetic on verified numbers. **ASSUMPTION** means an unverified premise that the stop rules in PROTOCOL.md guard against. **ESTIMATE** means a forecast and nothing more.

## 1. Verified inputs

| # | Fact | Source |
|---|---|---|
| V1 | R14 usage: `prompt_tokens` 6,730; `completion_tokens` 7,231; `reasoning_tokens` 57; `cache_write_tokens` 6,727; `cached_tokens` 0 | `round14-semantic-contract/execution/run/result.json:1` (`usage`) |
| V2 | R14 provider-reported cost: total $0.0891335; prompt $0.0168235; completions $0.07231. `invoice_verified:false` | same file and line |
| V3 | R14 finish: `stop` (native `completed`); 7,231 of 8,192 output tokens used | `result.json:1`; `RECOVERY.md:12-13` |
| V4 | R14 request body 28,307 bytes; guarded 29,331 (= body + 1,024) | `wc -c execution/run/request.json`; `RECOVERY.md:14`; guard formula `round16-wire-compat/protocol-w2-1/wire.py:337` |
| V5 | R14 content 22,694 bytes for 7,231 tokens | `wc -c execution/run/content.body` |
| V6 | Request settings (frozen r15.1 bytes, reused by r16.w2.1): `max_tokens` 8,192; `reasoning.effort` low; `provider.max_price` {completion: 10, prompt: 2}; `only/order` openai; `allow_fallbacks` false | `round15-condition-preservation/protocol-revised/request-settings.json:4,5-7,8-13,14-19`; loaded by `wire.py:329` |
| V7 | The R14 adapter's rate estimate uses 2,000 nanoUSD per prompt token and 10,000 per completion token, and ignores the cache-write premium | `round14-semantic-contract/runtime/adapter.py:14-16`; flag at `adapter.py:117` |
| V8 | The R14 debit convention is `max(reservation, reported, rate estimate)`; the reservation was $0.20 per call | `adapter.py:9,17-24,117` |
| V9 | The R14 cumulative conservative debit is 1,905,990,718 nanoUSD against a ceiling of 2,000,000,000 | `round14-semantic-contract/execution/run/ledger.json:1` |
| V10 | r16.w2.1 guard: `build()` refuses above 40,000 guarded bytes | `wire.py:337,344,356` |
| V11 | Offline `measure()` (reproduced 2026-10-13 with `python3 -I -S -B`): 26-19-016 (3,876 chars, 37 spans) full/opaque 18,785 / 18,970 guarded bytes; 26-19-023 (7,208 chars, 108 spans) 24,013 / 24,198 | local run; the 26-19-023 figures match `protocol-w2-1/SPEC.md:174-175` |

## 2. Derived per-token rates (single observation)

- **Completion:** $0.07231 / 7,231 = **$10.00 per million tokens**, exact. It matches the adapter rate (V7) and `max_price.completion` (V6). Reasoning tokens are billed inside `completion_tokens`: the completions cost equals 7,231 × $10/M, and 7,231 includes the 57 reasoning tokens.
- **Prompt:** if the 3 uncached, unwritten tokens are billed at the adapter's $2.00/M, then (0.0168235 − 3 × 2e-6) / 6,727 = **$2.50/M for cache-write tokens**, a 1.25× premium. The single-rate alternative is 0.0168235 / 6,730 = $2.4998/M. Either way, **$2.50/M bounds every prompt token observed**.
- Check: 6,730 × $2/M + 7,231 × $10/M = $0.08577, the adapter's `usage_rate_estimated_nanousd` of 85,770,000. Adding 6,727 × $0.50/M = $0.0033635 gives $0.0891335, exactly the reported cost.
- The cache-write rate exceeds `max_price.prompt = 2`, so in R14 `max_price` did not cap cache-write billing. **DERIVED** from V2 and V6.
- Byte/token ratios: input 28,307 B / 6,730 tok = 4.21 B/token; output 22,694 B / 7,231 tok = 3.14 B/token. One observation each; this is not a tokenizer.

These rates are from one October 2026 call. They are not a published price list, and OpenRouter pricing can change. PROTOCOL rule H4 halts the run if the first R17 receipt implies higher rates.

## 3. Assumptions the worst case depends on

- **A1 (ASSUMPTION):** the provider bills no more than `max_tokens` completion tokens, reasoning included. R14 never reached its cap, so this is unproven. Guard: H5 halts if any receipt reports `completion_tokens > max_tokens`.
- **A2 (ASSUMPTION):** prompt tokens ≤ guarded bytes ≤ 40,000, i.e. at least 1 byte per token. R14 observed 4.21 B/token, so the bound has roughly 4× slack over chat-template or schema-injection overhead. Guard: H4 checks the reported prompt tokens.
- **A3 (ASSUMPTION):** rates stay at or below $2.50/M prompt and $10/M completion. Guard: H4, applied after every call; overspend is limited to a single call (§6).
- **A4 (ASSUMPTION):** OpenRouter's reported `usage.cost` is close to the billed amount. It is not invoice-verified (V2). The ledger debits `max(reported, derived bound)`, so under-reporting does not reduce the debit.

## 4. Worst case per call

| Component | Bound | Cost |
|---|---:|---:|
| Completion | 16,384 tok × $10.00/M | $0.16384 |
| Prompt | 40,000 tok × $2.50/M | $0.10000 |
| **Worst case per call** | | **$0.26384** |
| **Reservation per call** (rounded up) | | **$0.27** (270,000,000 nanoUSD) |

R17 requests will be about 19–26 KB guarded (V11 and the source size rule in PROTOCOL S3). The realistic prompt worst case is therefore about $0.065, but the reservation keeps the guard-wide 40,000 bound for simplicity.

## 5. Plan totals against the $2.00 cap

| Plan | Calls | Reserved worst case | Margin to $2.00 |
|---|---:|---:|---:|
| **Phase A (this protocol): 3 sources × 2 arms** | 6 | 6 × $0.27 = **$1.62** (unrounded $1.58304) | **$0.38 (19%)** |
| Operating limit for any further release | — | $1.80 | $0.20 always held back |

Even if every call hits its ceiling at the derived rates, the protocol cannot exceed $1.62. The $0.20 held-back band covers rate error under A3 and A4.

**Expected spend (ESTIMATE, not a bound).** Prompt ≈ 4.5–6.5k tokens × $2.50/M ≈ $0.011–0.016. Completion ≈ 5–14k tokens × $10/M ≈ $0.05–0.14. That is about $0.06–0.16 per call and **about $0.5–0.9 for Phase A**. R14's single comparable call cost $0.089.

### Alternatives rejected

| max_tokens | Worst case/call | Reserve | 6 calls | Verdict |
|---:|---:|---:|---:|---|
| 8,192 (R14) | $0.18192 | $0.19 | $1.14 | Rejected: R16 says it must be raised, R14 already used 88%, and r16.w1 adds about 26 B per fragment |
| 12,288 | $0.22288 | $0.23 | $1.38 | Only 1.5× R14. A typed-profile truncation would waste a source. 8 calls (4 sources) = $1.84 > $1.80 |
| **16,384** | **$0.26384** | **$0.27** | **$1.62** | **Chosen:** 2.27× R14's observed use, under the operating limit with 19% margin |
| 20,480 | $0.30480 | $0.31 | $1.86 | Rejected: over the $1.80 operating limit (7% margin) |
| 24,576 | $0.34576 | $0.35 | $2.10 | Rejected: over the cap |
| 32,768 | $0.42768 | $0.43 | $1.72 for 4 calls | Rejected: only 2 sources |

## 6. Ledger rules (proposal; the dispatcher implements them)

1. Before each release: `cumulative_debit + 0.27 ≤ 1.80`. All six Phase A releases pass this check even at full reservations: 5 × 0.27 + 0.27 = 1.62.
2. After a call that returns `usage`, the debit is `max(reported_cost, prompt_tokens × 2.5e-6 + completion_tokens × 1e-5)`. This is the derived upper-rate bound and includes the cache-write premium; R14's own estimate (V7) omitted it.
3. After a call with no usage (transport failure, timeout, unparseable body), the debit is the full $0.27 reservation, and `provider_calls_may_have_occurred:true`.
4. **Price-drift containment.** H4 stops the run if a receipt implies rates above the derived ones. In the worst case, prices double just before call 1: that call costs at most 2 × $0.26384 = $0.53, and nothing further is released. The total stays under $2.00.
5. Any **extra** release (the PROTOCOL C7 re-release, or optional Phase B) uses the rule-2/3 observed debits plus $0.27 per new call, must stay ≤ $1.80, and needs an explicit release by the primary. Phase B (2 calls) is feasible only if Phase A's observed debit is ≤ $1.26. Under the expected spend it would be about $0.5–0.9, but that is an estimate.
6. **Ledger independence (open question Q1).** This arithmetic assumes R17 has its own ledger starting at $0 under the user's new $2.00 envelope. If the cap is cumulative with R14's 1,905,990,718 nanoUSD (V9), only $0.094 remains, less than one $0.27 reservation, and **R17 cannot run**.
