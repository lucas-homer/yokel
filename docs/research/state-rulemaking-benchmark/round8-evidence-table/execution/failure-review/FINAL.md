# Final failure-analysis reconciliation

2026-10-11. **PASS for freezing the final diagnosis and cap-only recommendation.**
Owner READY is present and edits stopped. All five artifact hashes/sizes in HANDOFF
match current bytes. Analyzer and REPORT hashes equal those independently checked
in REVIEW.md, so the verified facts and qualifications apply to the final artifacts.

- Analyzer: `dc7ea1ab66ffb3d0d7a92a4ae7ca8155638edd906d45019f52814da28fcb5f01`.
- REPORT: `7a6c74b78294bb25fdbc7e65769788627c3609fdda3f4e8baa6ea44e1fc3afd8`.
- HANDOFF: `dc9869b4207160053a79cef110677389f3e330b9567dd2b3dbae919973132a3c`.

Independent checks confirmed 32 unchanged frozen entries, HTTP200/finish length,
4096 completion tokens including 220 reasoning, strict invalid JSON and no parsed
result, 70 unique expected IDs and 53 complete forensic prefix objects. No labels,
reasons or evidence in the prefix were accepted or semantically scored. Raw usage
matches the report, including $0.058736 failed-response reported cost. This reported
charge must remain separate from conservative admission; it cannot replace the
failed call's $0.112454 reserve.

The conservative prior charge independently recomputes to **$0.542976718** from
three earlier debits and two actual evidence-table intent/result records. The
stronger-only 8192 candidate has maximum new reservation **$0.161920**, aggregate
**$0.704896718**; exact retained input implies $0.153414. No prior charge is refunded.
These are nominal pricing/guard arithmetic, not invoice or generation guarantees.

Prefer the separately scoped **output-cap-only 8192** candidate, preserving the exact
request/model/settings/verdict schema and all-ID/global-section acceptance. It isolates
the observed output exhaustion with more headroom than 6144. The approximately 5339
row projection is not a token bound: omitted global sections, partial/header overhead
and variable generation/reasoning prevent a completion guarantee. A compact output
contract is a larger separate change; authored byte savings and structural expansion
do not establish model generation or semantic equivalence. No partial JSON salvage,
retry/continuation, new inventory or new Jev call is recommended.

READY/candidate correctly specify a new namespace/review/freeze and no authorization
or live implementation. Future release must verify supported output allowance, exact
max_tokens-only serialized delta, full debit/usage accounting and strict whole-verdict
validation, followed by independent semantic review. This final review approves only
the offline diagnosis/candidate artifacts, not that future call or a new runner.

Changed only this new failure-review receipt. No owner analyzer execution or owner/
old/frozen writes, keys, provider/network calls, runtime/schema/live changes.
