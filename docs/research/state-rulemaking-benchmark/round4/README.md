# Automated state notice routing results

The frozen pipeline completed all 12 inputs but accepted no fields. Within the five independently complete notices, it recovered **0 of 7 eligible facts: 0 of 3 dates and 0 of 4 submission emails**. The research progression gate was not met. Our deterministic routing policy blocked every candidate before Jev, so this experiment diagnoses the router rather than comparing classifier accuracy.

The live run completed October 7, 2026, after the previous evening's 1Password authorization timed out before any provider request. Code, evaluation rules, source bytes and independent image-only labels were frozen before execution and remained unchanged.

## Measured results

| Measure | Result |
|---|---|
| Scheduled and terminal inputs | 12 of 12, across 10 states |
| Retained input pages | 52 |
| Complete single-notice inputs | 5; remaining 5 unknown scope and 2 slices |
| Genuine publisher scans | 4, all carrying embedded publisher OCR |
| Native candidates | 16 |
| Native plus fallback terminal observations | 23, all review |
| Automatically accepted fields | 0 |
| Jev requests | 0 |
| Mistral OCR requests through OpenRouter | 5, covering 14 pages |
| OpenRouter reported usage cost | $0.02865504 |
| Runtime conservative budget charge | $0.153; this is not billed spend |

The independent labels contain seven visible in-scope dates and five exact submission emails across all inputs. Global recovery remains undefined because incomplete and mixed inputs cannot establish an exhaustive denominator. The complete-notice subset provides the narrower 0/7 recovery result. Zero accepted errors among zero accepted claims does not establish safe acceptance.

The evaluator's one complete outcome is Idaho, which has no eligible date or literal email for these narrowly defined fields. That is an evaluator-confirmed negative case, not successful positive extraction or a runtime declaration that the notice is actionable. All runtime outputs remain research-only and not ready for action.

Evidence: [terminal evaluation](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/evaluation-report.json), [completed run](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/run/completed.json), [independent source labels](protocol/source-labels/README.md), [acceptance audit](protocol/acceptance-audit/).

## What the route did

Seven partial or uncertain-scope inputs went directly to source review. The five full-notice inputs received OCR fallback. None of the four scans received provider OCR in this run because their scope required source review first. This therefore does not measure Mistral's ability to recover those scans.

Every emitted candidate carried a deterministic condition blocker. Broad textual cues were being treated as unresolved conditions on the candidate, and the runtime treated those flags as hard stops rather than questions the semantic verifier could assess. Other blocks included lifecycle language, multiple notice scopes, unsupported date grammar and input-size limits. OCR preserved enough of the same language that it did not clear the policy blocks. The extra parse could not resolve the underlying semantic or scope problem.

Concrete traces make the problem clear. Arkansas's phrase “following email address” triggered the temporal-condition detector, blocking both its email and an explicit comment-close date. South Carolina's statement that regulation language was superseded by statute triggered whole-document lifecycle review. Its “on or before” deadline also fell outside the candidate finder's narrow closing-language grammar. In contrast, Hawaii contains genuine relative timing and a possible comment-period extension; those qualifications cannot simply be discarded. See the [exact text spans and hashes](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/routing-diagnosis/evidence.json).

The [routing diagnosis](execution/routing-diagnosis/README.md) found identical candidate-value multisets, issues and routes before and after all five OCR acquisitions. None was triggered by the frozen low-text or image-sparse thresholds. This is evidence of unproductive escalation in these cases, not a general verdict on OCR quality.

Jev was never reached. This result neither confirms nor refutes its usefulness; it shows that our integration prevented the intended comparison. Likewise, five successful OCR transports do not establish parsing accuracy. There was no independent stage-by-stage parser-fidelity or candidate-recall score in this experiment.

## Cost and collection limits

OpenRouter's retained usage responses sum to $0.02865504. The runtime additionally accounts for $0.028 of possible OCR fees, yielding $0.05665504 of conservative accounting, which may double-count fees already included in the reported charges. Its admission reservation totals $0.153. These figures must not be presented as three separate bills. Jev usage and cost are zero. Cost per correctly recovered fact is undefined because recovery is zero.

Collection used 48 prepared searches and 21 recorded download attempts: 17 succeeded, two returned HTTP 403, one HTTP 404, and one failed TLS connection. The selected original PDFs contain 2,438 pages; reviewer-guided boundary selection retained 52 pages. Discovery and segmentation costs were not measured, so the small API charge is not an end-to-end operating-cost estimate. See the [source operations audit](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/source-operations-audit.json).

The sample is purposive rather than representative. Its four scans come from two related state filing families and have embedded OCR; it contains no established image-only test cohort. Only five inputs achieve complete single-notice scope, below the original twelve-complete-notice target. All 48 planned searches finished before queued candidate processing ended; the disclosed collection-order deviation was accepted for diagnostic use before the run. No inputs were replaced based on parser outcomes. See the [collection decision](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/collection-decision.json).

## Consequence for the solution design

Escalation should depend on the unresolved problem, rather than sending every uncertainty to a more expensive parser:

| Unresolved problem | Next appropriate capability |
|---|---|
| Missing or corrupted text, reading order or layout | OCR or specialized document parsing |
| Legible text with uncertain date, destination, role or qualification | Semantic verification of an evidence-linked candidate |
| Mixed notices, missing continuation or uncertain proceeding identity | Boundary recovery, source retrieval or review |
| Invalid date, mismatched literal or broken provenance | Deterministic rejection or review |

The next implementation should preserve hard integrity checks while treating candidate-specific semantic questions as verifier inputs. It should also avoid OCR when the remaining blocker is one that OCR cannot repair. Actual conditional deadlines must remain conditional; removing a broad lexical block is not permission to ignore qualifications.

Use these now-exposed inputs for development and regression tests. First test a revised native-only route that can actually reach semantic verification, with positive controls paired against real conditions, conflicting windows and incidental contacts. Freeze that route before evaluating new complete notices. A subsequent OCR cohort should include genuine image-only notices whose complete boundaries are independently verified. Measure extraction fidelity, candidate recall, semantic decisions and final acceptance separately. The existing research progression gate still applies; this run does not justify production adoption or state ingestion into DocketClock.

## Reproducibility

The experiment retains [implementation Freeze A](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/freeze-A.json), [evaluator Freeze E](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/freeze-E.json), [source Freeze S](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/freeze-S.json), [source-label Freeze B](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/freeze-B.json), and the [authorization binding](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/authorization-binding.json). The [dry run](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/round4/execution/dry-run.json) and live operation ledger bind the manifest, code and provider requests. No frozen implementation was changed in response to fresh outcomes. Production code, contracts and cluster configuration were untouched.

The independent [execution audit](execution/postrun-audit/REPORT.md) passed 285 checks, verified five completed HTTP 200 responses and matching request/decision hashes, and found no recorded retries, stops or unknown-cost operations. These are execution-integrity checks, not source-accuracy measurements.
