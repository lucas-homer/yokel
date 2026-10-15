# Independent review of next-experiment candidate

Reviewed candidate: `../failure-analysis/NEXT-EXPERIMENT-CANDIDATE.md`, SHA-256 `01b2b568e077ab114fe6659c70746f5d3100bf4288b75e72127bdd9ad65ceb69`.

**Recommendation: select the candidate's one-document, 12,288-token cap-only development option first, rather than its five-document default.** The observed failure justifies testing output headroom. One document answers the immediate reachability question with less scope and preserves a clear comparison. No prompt compaction, schema/evidence-registry change, segmentation, parser relaxation or model/settings change should be combined with it. This is a recommendation for a new reviewed authorization, not permission to implement or run it.

## Concrete proposed bound

- Source: only `doc-92211b8c7ba0`, the previously failed two-page Wisconsin notice, using its exact frozen source bytes/hash and source-only prompt. Retain R7 schema/representation, exact evidence, roles/groups, five verifier dimensions, model/provider/reasoning and all input/verifier-output caps.
- Change only the inventory completion ceiling from 6,144 to **12,288**, with its correctly recomputed reservation. New runtime/job namespace, version and hashes describe that change without changing the old R8 artifacts or model-schema semantics.
- **At most three new calls:** one inventory, one Jev batch and one stronger verifier. Never retry, continue, stitch, repair or repeat the inventory at another ceiling. Global/stage limits must actually enforce one per stage, not retain the old eight-stage allowance. Including R8's existing call, the combined ceiling is four attempts: two inventory, one Jev and one stronger.
- Preserve **$0.100166 as an immutable prior-budget debit**. The shared nominal/conservative $2 guard therefore has **$1.899834 available before the probe**. Every next intent must account for prior debit plus new sum(max(reservation, known observed charge)); no refund/reset of the old failed operation.

| Reservation component | Worst case |
| --- | ---: |
| New inventory: 35,000 input estimate + 12,288 output | $0.192880 |
| New stronger: 35,000 input estimate + 4,096 output | $0.110960 |
| New Jev: 64,000 input estimate | $0.002688 |
| New probe total | **$0.306528** |
| Original debit + new probe | **$0.406694** |

The candidate's five-document arithmetic is also correct: $1.532640 new plus $0.100166 old = $1.632806. It is unnecessary for the first diagnostic decision. None of these reservation calculations is an invoice guarantee; preserve any reported overrun, retain completed work and stop before the next call.

## Admission, interpretation and release conditions

The first source-only request must be serialized and admitted under unchanged input limits. Doubling output headroom does not establish that generation will finish. A length-limited response, invalid JSON, schema/evidence failure or other original parser rejection remains a retained development failure; no partial inventory is scored.

A completed response is still only a candidate inventory. Assemble it without repair. If structurally valid, construct the actual common full-source+record payload and **both** final verifier bodies before either verifier call. Keep Jev's 64,000 total and 32,000 state-plus-longest bounds and stronger's 35,000 input/4,096 completion bounds. A larger completed inventory may expose the next bottleneck here. If either request fails admission, retain the record and size receipts with both arms uncalled; no clipping, cap increase or selective fact removal. A successfully admitted Jev judgment does not decide whether the stronger arm runs; normal paired dispatch rules and global failure latches still apply.

Before any call: primary must approve a new fixed one-source authorization that explicitly contains the three-new-call bound, prior debit/shared budget, new cap, code/source/reference hashes and output namespace; independently verify final serialized requests/reservations, stage caps, durable no-retry behavior, prior-debit accounting and truthful postresponse budget stops. Rebind native service/job/dependencies to that reviewed version. Do not reopen the latched R8 operation.

This notice, its reference and observed failure are now development data. The probe can establish extraction/assembly/paired-request reachability and independently audited results for this reused source; it cannot repair R8's result or establish unseen generalization. Original R8 remains five notices/178 units, zero validated outputs and zero verifier calls. Higher cap alone guarantees neither fit, semantic completeness nor useful acceptance. A later accuracy experiment needs a separately frozen unseen cohort and complete independent audit.
