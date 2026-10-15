# Round 12 independent operational postrun review

**Operational audit passed; pilot PARTIAL and evaluation INCOMPLETE.** D and A each reached OpenAI successfully (HTTP 200), then exhausted the 8,192-completion-token cap. Both returned `finish_reason: length` / `native_finish_reason: max_output_tokens` and invalid, incomplete JSON. The adapter correctly rejected them. C and B were never attempted. No retry, repair, prefix salvage or additional call is authorized by this report.

The frozen execution receipt records native runner exit 1. The retained successful HTTP responses and reproduced adapter rejection identify downstream invalid-completion handling, not a credential-access failure. D's safe failed receipt allowed the independent A attempt; A's failure stopped C/B as designed. Neither arm produced a validated result. No discovery, scope-classification, matching, accuracy or relative-arm conclusion can be drawn from the truncated prefixes.

| Stage | HTTP | Prompt tokens | Completion tokens | Reasoning tokens within completion | Content UTF-8 bytes | Reported cost |
|---|---:|---:|---:|---:|---:|---:|
| D | 200 | 5,559 | 8,192 | 38 | 33,009 | $0.095816 |
| A | 200 | 1,845 | 8,192 | 63 | 30,283 | $0.086531 |
| C | not attempted | — | — | — | — | — |
| B | not attempted | — | — | — | — | — |

D contains 33,007 content characters; A contains 30,283. Raw native responses are 40,914 and 37,190 bytes respectively. Both report `provider: OpenAI`, `model: openai/gpt-6.1-sol`. Request hashes match the reviewed fixed requests and native intents exactly; guarded request sizes remain D 28,441 and A 10,205 bytes, below the unchanged 40,000-byte guard. This was output truncation, not input-guard overflow. Successful routing is observed; successful structured completion is not established.

## Release, integrity and no-retry evidence

The registry's canonical manifest exactly equals the actual proposal and matches release/primary receipt hashes and the one-shot native claim: `41b7909515a5ced14598fd69c63c8ecadc6e259dc513b94e670ec0c53ed2f579`. Its detached P-256 signature was independently verified with the frozen public key using a public-only verifier; no signer, executor, private key or credential operation was invoked. The primary release receipt reports native check success. The unchanged pure release validator also accepted the actual proposal at its recorded pre-release verification time.

All **8,606 actual release file pins**, scope/authorization/dependency bindings, exact review pin and native executor bytes still match. All **6,829 baseline files** and **46 canonical PDF alias targets** remain unchanged. All **23 runtime owner artifacts** match runtime READY `572124980bb9793d34c22902f83c32e5850f96c53dd861b7084051d41712c29c`.

Execution READY `4a416ee8366e169404285624b659c8aa3f737318013713013b6c0807de045aa2` exhaustively pins the 15 retained run files. They contain exactly D/A stage directories, requests, intents, safe response/status/stop receipts and the final ledger/stop. No C/B preflight or intent, validated content, successful stage freeze, completed run or retry is present. Ledger recomputation matches exactly. This evidence supports two attempts within the released four-call maximum and correct dependency stopping.

## Costs and price-cap caveat

Reported provider total is **$0.182347**. The frozen 2/10 rate estimate is **$0.178648**. Each retained **$0.161920** reservation exceeds both observed cost measures, so the unchanged conservative ledger correctly charges **$0.323840 new**, for **$1.505990718 cumulative** under the **$2.000000000 ceiling**. Remaining arithmetic headroom is $0.494009282; it grants no retry or new-run authorization. Invoice verification remains false.

Both requests contain `max_price.prompt=2` and `completion=10`, but reported prompt components average about **$2.50 per million input tokens**. D reports $0.013896 input cost with 5,556 cache-write tokens; A reports $0.004611 with 1,842 cache-write tokens. These amounts exactly fit **$2.50/M for cache-write tokens plus $2/M for the three remaining prompt tokens in each call**. This is an arithmetic inference from raw usage, not verified provider pricing policy or invoice evidence. The $0.003699 excess over the frozen estimate equals that inferred cache-write premium. Completion components exactly fit $10/M. Do not interpret the requested nominal prompt cap as proof of an all-in billed input ceiling. No raw observation, frozen rate, reservation or ledger was changed.

## Evidence and scope

`checks.py` and `check-results.json`: **97/97 checks passed**, covering actual release/signature/bindings, all dependency and baseline pins, response/request hashes, truncation, planned outcomes, rejected completion parsing, no-retry evidence and cost reconciliation. Only new review/postrun artifacts were written. No reference or candidate-audit contents, credentials, live APIs, paid calls, signer/executor actions or implementation changes occurred. Semantic status, whole-source completeness, whole-record fidelity and production/action readiness remain unverified/false.
