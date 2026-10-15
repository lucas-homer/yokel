# Candidate amendment for review — not live authorization

Recommended first change: a separately versioned **output-cap development experiment on at most the five already scheduled notices**, with the inventory ceiling increased from 6,144 to 12,288 tokens. Retain the existing model/provider/reasoning settings, full-source inventory/record schemas, exact evidence, role-purpose groups, all semantic domains, Jev probes and stronger 4,096-token cap. Change no parser acceptance guard: length/native truncation still rejects, invalid JSON/schema/evidence still fails closed, and no retry, continuation, stitching or repair is allowed.

This isolates the measured output-cap bottleneck without changing extraction representation or adding segmentation. Doubling is a bounded headroom probe, not a claim that 12,288 is sufficient; the missing tail and future output sizes are unknown. An 8,192-token ceiling is the smallest conventional alternative shown here, but its 2,048 extra tokens are not proven adequate. Run neither automatically. Any later length failure becomes another retained development outcome; do not stepwise retry that notice under successive ceilings.

## Budget/call admission

With the existing conservative input ceilings/rates and one inventory + one Jev + one stronger call per notice:

`N × [2 × 35,000 × $0.000002 + inventory_cap × $0.000010 + 4,096 × $0.000010 + 64,000 × $0.000000042]`.

| Cohort / inventory ceiling | Maximum calls | Nominal worst-case reservation |
| --- | ---: | ---: |
| Eight / 6,144 (original design) | 24 | $1.960704 |
| Eight / 8,192 | 24 | $2.124544 — exceeds $2 |
| Eight / 12,288 | 24 | $2.452224 — exceeds $2 |
| Five / 8,192 | 15 | $1.327840 |
| Five / 12,288 (candidate) | 15 | $1.532640 |
| One / 12,288 (smaller development probe) | 3 | $0.306528 |

The actual R8 cohort was five notices; keep the original five-notice failure and unmet eight-notice gate unchanged. Explicitly cap the new experiment at five notices, five calls per stage and fifteen total, so the 12,288 ceiling genuinely fits. Merely raising a constant while retaining the eight-notice worst-case claim would be false. This does not claim an adequate original eight-notice cohort.

Budget authorization must say whether the ceiling is shared with R8 or newly authorized; no unused reservation is silently transferred. A shared $2 ceiling can conservatively count the old $0.100166 charge plus the new five-notice worst-case $1.532640 = **$1.632806**. Combined calls would be at most sixteen (six inventory, five Jev, five stronger). Preserve the old ledger and record its charge as an immutable prior-budget debit in a new authorization/ledger; do not reset or refund it. If a separate new budget is explicitly authorized, state it separately. Both options still stop before any next operation when nominal/response-reported charge violates the authorized aggregate cap; invoice certainty remains unavailable.

## Alternatives and risks

**Formatting-only compact output:** requesting compact JSON within the same schema is a small prompt change and preserves data if the entire response is complete. Visible outside-string whitespace is measurable, but its token reduction and the missing tail are not. It could be tested separately at the existing ceiling; do not combine it with the higher-cap probe if the goal is isolating which change mattered. Postresponse minification cannot recover the paid truncated response.

**Evidence registry / compact structural schema:** deduplicating exact selectors and referencing them by IDs could reduce transport repetition while retaining semantic claims, but requires new extraction/record schemas, deterministic expansion, global references/ID/assessment coverage, source hash checks, paired-payload compatibility and independent completeness controls. Selector whitespace/newlines/occurrences/context must stay exact. Eliminating route/group relationship evidence or shortening source context merely to fit risks wrong ownership, qualification and interchangeability. This is a larger new representation experiment; the partial diagnostics do not establish that it is necessary.

**Segmentation:** defer unless output/request size repeatedly remains a measured bottleneck after a bounded transport probe. It changes the unit of extraction, introduces extra calls and needs cross-segment event/route/group/requirement reconciliation, whole-source coverage, duplicate/contradictory fact handling and shared identity/evidence provenance before paid execution. Splitting only the failed tail or selecting participation-looking chunks would hide omissions. A segmented design needs its own schema, preregistration, budgets and semantic controls; it is not a safe continuation of this response.

## Required preflight and decision gate

1. Create a new version/namespace and preserve all R8 source/response/labels/code and Freeze E. No new response is appended to the latched operation. Retain the failed notice and later unstarted notices in R8's denominator.
2. Freeze the amended output ceiling, actual five-notice/max-call bound, prior-budget debit if shared, code/schema/prompts, protocol and model/provider/rates before paid output. New authorization must bind source/label hashes and explicitly permit the chosen development probe; native service/job/dependencies must reflect the new pins.
3. Offline public controls must show 12,288 on the final inventory request and corresponding reservation; >cap/finish_reason length and invalid JSON still reject; no per-stage budget/call or source clipping bypass; identical paired payload and complete new-ID verdict assessment; both verifier requests admit before dispatch; reported-cost overrun preserves paid result and stops later calls; durable uncertain POST remains latched. Measure final requests and realistic full **authored development** inventory envelopes, not the truncated prefix repaired to JSON.
4. If reusing these five sources/labels, label the outcome reused-source development reachability, not new unseen generalization or repaired R8 model success. Keep source truth out of inventory/verifier inputs; original independent AI image reference is not human gold. A later accuracy/paired comparison requires a separately frozen unseen cohort with complete independent audit and adequate denominators.
5. Report admitted inventories, structurally assembled records, verifier dispatch/completion and independently correct complete acceptance separately. Zero verifier calls cannot yield comparative quality. Paid extraction completion alone is not correctness/completeness.

Decision for primary: approve the five-notice 12,288-cap development amendment and its explicit budget scope, select a one-notice narrower probe instead, or prioritize a separately specified compact transport. No implementation or live action is authorized by this document.
