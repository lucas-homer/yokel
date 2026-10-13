# R8 independent postrun audit

**Audit passed. The experiment produced no validated inventory, normalized record or verifier judgment.** One inventory request received HTTP 200, but generation ended at the 6,144-token cap with finish_reason=length. The frozen parser rejected the incomplete structured response and latched the run. The remaining four notices never started; Jev and stronger were uncalled for all five. This is an incomplete-response failure, not evidence of a provider outage or comparative verifier quality.

[A/S/B/E integrity and operational audit](audit.json) verifies 69/927/9/20 frozen files, their sizes/hashes, all 2,590 service dependency files, implementation/source/label/authorization bindings, durable intent/request/response/status/stop links and the adapter's stopped receipts. Freeze and intent timestamps are consistent with image-reference freezing before model outputs; the recorded labeler access provenance is not an independent proof of every access. No frozen files were edited and no new provider/network/credential actions were taken.

## Costs

| Cost basis | Extraction | Jev | Stronger |
| --- | ---: | ---: | ---: |
| Provider response-reported | $0.0688185 | $0 | $0 |
| Pinned usage-rate estimate | $0.067344 | $0 | $0 |
| Conservative reservation/accounting | $0.100166 | $0 | $0 |

These are not invoice-verified charges. The simple usage estimate uses 2,952 prompt and 6,144 completion tokens at frozen rates; the retained response reports separate cache-write accounting. The frozen ledger's observed_accounted_usd=0 reflects the absence of a successfully parsed result.json, **not free execution**. The raw response still reports its charge, and the conservative reservation covers it. Zero verifier costs are established by the absence of any verifier intent/operation, not by missing usage alone. [cost-audit.json](cost-audit.json) retains the exact usage, rates, hashes, parser rejection and accounting basis.

## Artifacts and scoring

[artifact-absence.json](artifact-absence.json) proves that all five observed inventory/record/payload hashes are null; no parsed operation result, assembled record, verifier request or common payload exists. The first document has only the failed inventory operation and source/request/failure artifacts. No partial response text is scored as a valid inventory.

[matching-audit.json](matching-audit.json) therefore assigns null inventory and record assessments to all five documents. [source-unit-dispositions.json](source-unit-dispositions.json) explicitly retains all **178 frozen source units** as unserved because artifacts are absent. They are not counted as extracted omissions or selectively removed.

The frozen R8 evaluator ran unchanged against the original schedule/truth and [observed-with-costs.json](observed-with-costs.json). This derivative adds only top-level costs; every document state, judgment, hash and reason is unchanged. [observation-derivative.json](observation-derivative.json) records original/derived hashes and exact provenance.

[evaluation-report.json](evaluation-report.json) yields, for each arm: 0 accepted, 0 useful complete accepted, 5/5 unserved, null unsafe-acceptance fraction and null cost per correct complete accepted record. Source-unit recovery is 0/178 because no artifact exists. Claim accuracy is unavailable with no validated claims. The evaluator's missing_or_incomplete_audits=5 for both inventory and record is the prescribed consequence of absent artifacts, not unfinished review of existing outputs.

The actual cohort is **five notices, five states and 17 pages** (three general/two controls), short of the planned eight notices/six states. It is a **protocol-deviation corrected development cohort**, not a pristine preregistered cohort. Mechanical cohort adequacy is false; no gate-success, model-accuracy or population claim is supported. The 178-unit reference is independent AI image labeling, not human-adjudicated gold.

Reproduce with bundled Python, PYTHONDONTWRITEBYTECODE=1, and `audit.py` in this directory. The audit writes only this postrun-audit directory and verifies frozen inputs before and after its work.
