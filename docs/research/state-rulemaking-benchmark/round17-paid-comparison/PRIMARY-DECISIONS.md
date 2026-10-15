# R17 primary decisions on design open questions (2026-10-13)

- Q1 budget: the user-approved $2.00 is a NEW R17 ledger namespace, separate from the historical R9-R14 $2.00 ceiling ($0.094009282 remaining there, untouched). User approval: "hard cap of $2" for the paid comparison, 2026-10-13.
- Q2 max_tokens: the R17 adapter derives the dispatched body from the unchanged r16.w2.1 plan with max_tokens 16384, records both the plan request_sha256 and the dispatched-body sha256, and recomputes the 40,000-byte guard on the dispatched body immediately before transport. Validation uses the unchanged plan.
- Q3 reference reviewer: GPT-6 Astra (cross-provider vs Fable references).
- Q4 Phase B: not run (would raise reservations to $2.16 > cap).
- Q5 source retrieval: approved; public Washington State Register notices fetched by a child task under prior rounds' freezing conventions. No credentials involved.
- Q6 keyword screen: kept as written (mechanical, pre-registered).

## 2026-10-13 addendum: OpenRouter per-key limit facts (primary web check)
- Official docs (https://openrouter.ai/docs/api-reference/limits) document optional per-key credit caps, GET https://openrouter.ai/api/v1/key returning limit / limit_remaining / limit_reset, and HTTP 402 when a key's cap is exhausted.
- The docs do NOT state whether the cap rejects a charge that exceeds the remaining allowance mid-request (admission-time vs charge-time enforcement). Per design-r2 B1, the R17 key limit must therefore be <= $1.73, not $2.00.
