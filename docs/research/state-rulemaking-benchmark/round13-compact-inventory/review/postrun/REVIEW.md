# Round 13 independent operational postrun review

**PASSED — one structurally valid, frozen inventory completion. No operational discrepancy found.** This establishes bounded serialization feasibility for this exact outcome-exposed request, not semantic accuracy, atomicity or source completeness. No additional call is authorized.

OpenAI/Sol returned HTTP 200, `finish_reason: stop`, native finish `completed`; the execution freeze records runner exit 0. The complete response validates against the frozen protocol without repair or prefix salvage. It contains **91 units**, uses **5,728 of 8,192 completion tokens (69.92%)**, and leaves **2,464 tokens** of observed headroom. Usage reports **3,601 prompt tokens** and **87 reasoning tokens within completion**.

| Artifact | Bytes |
|---|---:|
| Full request / guarded request | 14,668 / 15,692 |
| Native response | 24,410 |
| Original content = canonical compact output | 17,827 |
| Expanded inventory | 55,377 |

The original content is exactly the retained canonical compact output. Re-running the approved validator, expansion and source-checked inverse reproduces exact objects, bytes, hashes, evidence, codes, explicit empty values and unit order. The complete source and **37** host spans reconstruct exactly. Neither 91 units, valid evidence IDs, END nor the exact inverse proves exhaustive discovery or entailment. Production/action readiness and semantic completeness remain false/unverified. Provider acceptance and completion are observed for this exact request only; the earlier byte-ratio estimates are not thereby guaranteed for future outputs.

## Release and accounting

The actual published manifest equals the canonical proposal and matches both primary receipts and the one-shot native claim: `0382365c60424f67be44bb430473211f5cb16163e4a1d1d6b6eee0a105659cd9`. Independent public-key verification passed for its detached signature. All **8,704 release file pins**, exact authorization/dependency/review bindings and native executor bytes match. The unchanged pure release validator accepts the actual proposal at its recorded release-verification time. No signer or executor was invoked by this review.

All **6,981 baseline rows**, including **46 canonical PDF alias targets**, and all **16 runtime owner artifacts** remain unchanged. Execution READY `dcda1a2bc6d93dd0bd3af20c4dd271462855287a31c91bef32f9bb46f7226409` exhaustively pins the 11 run files. Completion pins all 10 preceding receipts, including the neutral `charge_recorded` ledger. There is exactly one claimed attempt, no stop receipt and no retry/substage artifacts. The completion, result and recomputed ledger agree.

Provider-reported cost is **$0.066281**; the frozen nominal rate estimate is **$0.064482**. The **$0.200000** reservation dominates both and is retained unchanged, giving **$1.705990718 cumulative** under the **$2 ceiling**. Arithmetic headroom is $0.294009282; it grants no new authorization. Invoice verification remains false.

Raw usage reports $0.009001 prompt cost with 3,598 cache-write tokens and three other prompt tokens. That exactly fits **$2.50/M cache-write tokens plus $2/M remaining input**, a **$0.001799** difference from the nominal estimate. Completion cost $0.057280 exactly fits $10/M. The cache-write explanation is an inference from reported components, not verified pricing policy or invoice evidence. Requested nominal 2/10 caps are not proof of an all-in billing ceiling. Raw observations, rate assumptions and ledger were preserved.

## Evidence

**89/89 actual-receipt checks passed** in checks.py/check-results.json. No unrelated test suite was rerun. No evaluation/reference semantic contents were consumed; prior artifacts were hash-verified only for required integrity checks. Only new review/postrun artifacts were written. No provider APIs, credentials, signing, executor actions or implementation/receipt edits occurred.
