# D3 — Extension/correction/reopening volume & deny-list precision

**Run:** 2026-06-14 (Eastern) · detector `lower(title) ~ '(extension|reopen|correction|withdraw)'`
**Window:** 2026-03-16 → 2026-06-14 (90 days) · source: Federal Register NOTICE/PRORULE/RULE (keyless)

## Keyword-candidate volume (pre-labeling, upper bound)

| metric | value |
| --- | ---: |
| docs scanned in window | 6666 |
| **keyword candidates** (title hit) | **427** |
| …per keyword | extension 305 · reopen 8 · correction 69 · withdraw 45 |
| flagged by FP heuristic (hint only) | 209 |
| **candidate volume / day** | **4.7** |

> Per-keyword counts double-count titles that hit two stems (e.g. "extension" + "correction");
> the candidate total counts each document once. The "FP heuristic" column is an *advisory hint*
> for the labeler (e.g. the BLM land-withdrawal trap), not a label.

## Decision (finalize after labeling the 50-row sheet)

Compute **precision = genuine deadline-movers / 50**, then read off:

- `precision ≥ 0.7` → deterministic deny-list + keywords is enough for v1; the LLM adjudicates the rest.
- `precision < 0.5` → the LLM chain-classifier is **load-bearing from day 1**; tighten the deny-list with the labeled FPs.
- **Projected genuine movers/day = 4.7 × precision.**
  Worked: at precision 0.7 → **3.3/day**; at 0.5 → **2.4/day**; at 0.3 → **1.4/day**.
  If that projection exceeds **~15/day**, the review console is a *staffed line*, not a 20-min chore — flag it.

## 50-row sample — label each: does it MOVE a comment deadline?

`mover?` = does this notice actually extend/reopen/correct/withdraw a **comment-period deadline**
(vs. a land withdrawal, an editorial correction, an unrelated "extension of a program", etc.)?

| published | type | keyword | agency | title | FP hint | mover? (y/n) |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-03-16 | Notice | extension | Consumer Product Safety  | Agency Information Collection Activities; Extension of Collection; Virginia Gr | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-03-18 | Notice | withdraw | Health and Human Service | Determination That METHERGINE (Methylergonovine Maleate) Injection, 0.2 Millig | withdrawal — confirm it touches a comment period |   |
| 2026-03-20 | Notice | extension | Securities and Exchange  | Agency Information Collection Activities; Submission for OMB Review; Comment R |  |   |
| 2026-03-20 | Notice | extension | Surface Transportation B | 60-Day Notice of Intent To Seek Extension of Approval of Collection: Statutory |  |   |
| 2026-03-23 | Notice | extension | Energy Department | Agency Information Collection Extension | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-03-25 | Notice | extension | Labor Department | Proposed Extension of Information Collection: Health Standards for Diesel Part | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-03-26 | Notice | correction+withdraw | Health and Human Service | Elite Laboratories, Inc., et al.; Withdrawal of Approval of 72 Abbreviated New | likely approval/application withdrawal (not a comment deadline) |   |
| 2026-03-30 | Notice | extension | Federal Trade Commission | Agency Information Collection Activities; Proposed Collection; Comment Request |  |   |
| 2026-04-01 | Notice | extension | Securities and Exchange  | Agency Information Collection Activities; Proposed Collection; Comment Request |  |   |
| 2026-04-02 | Notice | extension | Commerce Department | Fresh Tomatoes From Mexico: Extension of Deadline To Certify |  |   |
| 2026-04-03 | Notice | extension | Health and Human Service | Determination of Regulatory Review Period for Purposes of Patent Extension; VY |  |   |
| 2026-04-06 | Notice | extension | Energy Department | Agency Information Collection Extension | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-04-07 | Notice | extension | Agriculture Department | Notice of Request for Revision to and Extension of Approval of an Information  | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-04-09 | Notice | withdraw | Health and Human Service | Proposed Information Collection Activity; Office of Refugee Resettlement Unacc | withdrawal — confirm it touches a comment period |   |
| 2026-04-10 | Notice | extension | Securities and Exchange  | Agency Information Collection Activities; Submission for OMB Review; Comment R |  |   |
| 2026-04-13 | Notice | extension | Securities and Exchange  | Agency Information Collection Activities; Submission for OMB Review; Comment R |  |   |
| 2026-04-13 | Notice | extension | Energy Department | Saguaro Connector Pipeline, LLC; Notice of Request for Extension of Time |  |   |
| 2026-04-16 | Notice | withdraw | Securities and Exchange  | Self-Regulatory Organizations; Miami International Securities Exchange, LLC; N | likely approval/application withdrawal (not a comment deadline) |   |
| 2026-04-16 | Notice | withdraw | Health and Human Service | Determination That CHEWTADZY (Tadalafil) Chewable Tablets, 5 Milligrams, 10 Mi | withdrawal — confirm it touches a comment period |   |
| 2026-04-17 | Proposed Rule | extension | Treasury Department | Increase in Threshold for Requiring Information Reporting With Respect to Cert |  |   |
| 2026-04-17 | Rule | correction | State Department | Schedule of Fees for Consular Services-Fee for Administrative Processing of Re | likely editorial/technical correction |   |
| 2026-04-20 | Notice | extension | Homeland Security Depart | Agency Information Collection Activities: Extension, Without Change, of a Curr | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-04-23 | Notice | extension | Health and Human Service | Notice of Funding Extension for the Rural Communities Opioid Response Program- |  |   |
| 2026-04-24 | Notice | correction | Commerce Department | Common Alloy Aluminum Sheet From India: Final Results of Countervailing Duty A | likely editorial/technical correction |   |
| 2026-04-27 | Notice | correction | Commerce Department | New England Fishery Management Council; Public Meeting; Correction | likely editorial/technical correction |   |
| 2026-04-28 | Notice | extension | Commerce Department | Crystalline Silicon Photovoltaic Cells, Whether or Not Assembled Into Modules, |  |   |
| 2026-04-29 | Notice | correction | Nuclear Regulatory Commi | Accelerated Decommissioning Partners Crystal River Unit 3, LLC; Crystal River  | likely editorial/technical correction |   |
| 2026-04-30 | Notice | extension | Labor Department | The Standard on the Storage and Handling of Anhydrous Ammonia; Extension of th | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-01 | Notice | extension | Labor Department | Fire Brigades Standard; Extension of the Office of Management and Budget's (OM | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-04 | Notice | extension | Agriculture Department | Almonds Grown in California; Notice of Request for Extension and Revision of a | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-05 | Notice | extension | Justice Department | Agency Information Collection Activities; Proposed eCollection, eComments Requ | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-06 | Notice | extension | Homeland Security Depart | Agency Information Collection Activities; Extension; Report of Diversion | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-07 | Notice | correction | Securities and Exchange  | Order Making Fiscal Year 2026 Annual Adjustments to Transaction Fee Rates; Cor | likely editorial/technical correction |   |
| 2026-05-08 | Notice | extension | Labor Department | Proposed Extension of Information Collection: Qualification and Certification  | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-08 | Notice | extension | Treasury Department | Extension of a Currently Approved Information Collection: Request To Reissue U | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-11 | Notice | extension | Securities and Exchange  | Proposed Collection; Comment Request; Extension: Rule 15b6-1 and Form BDW |  |   |
| 2026-05-13 | Notice | extension | Transportation Departmen | Notice of Petition for Extension of Waiver of Compliance |  |   |
| 2026-05-14 | Notice | extension+withdraw | Interior Department | Application for Withdrawal Extension for Fort Carson and Pinon Canyon Maneuver | withdrawal — confirm it touches a comment period |   |
| 2026-05-18 | Notice | extension | Homeland Security Depart | Agency Information Collection Activities; Extension, Without Change, of a Curr | likely PRA/info-collection extension (not a docket comment deadline) |   |
| 2026-05-19 | Notice | withdraw | Energy Department | New England Hydropower Company, LLC; Notice of Effectiveness of Withdrawal of  | likely approval/application withdrawal (not a comment deadline) |   |
| 2026-05-21 | Rule | correction | Interior Department | Revisions to Regulations Regarding Oil and Gas Leasing; Fees, Rentals, and Roy | likely editorial/technical correction |   |
| 2026-05-22 | Notice | extension | Transportation Departmen | Notice of Petition for Extension of Waiver of Compliance |  |   |
| 2026-05-26 | Proposed Rule | extension | Federal Reserve System | Regulation A: Extensions of Credit by Federal Reserve Banks |  |   |
| 2026-05-27 | Notice | extension | Commerce Department | High Purity Dissolving Pulp From Brazil: Preliminary Affirmative Determination |  |   |
| 2026-05-28 | Proposed Rule | extension | Education Department | Proposed Waiver and Extension of the Project Period With Funding for Arts in E |  |   |
| 2026-05-29 | Notice | extension | Homeland Security Depart | Extension of Lebanon Designation for Temporary Protected Status |  |   |
| 2026-06-01 | Rule | correction | Securities and Exchange  | Holding Foreign Insiders Accountable Act Disclosure; Correction | likely editorial/technical correction |   |
| 2026-06-03 | Notice | extension | Securities and Exchange  | Agency Information Collection Activities; Proposed Collection; Comment Request |  |   |
| 2026-06-04 | Notice | extension | Securities and Exchange  | Agency Information Collection Activities; Submission for OMB Review; Comment R |  |   |
| 2026-06-08 | Notice | withdraw | Health and Human Service | Determination That Protamine Sulfate (Protamine Sulfate) Intravenous; Solution | withdrawal — confirm it touches a comment period |   |

_Sample is a stride of 8 across 427 candidates (deterministic, representative
of the full window). After labeling, count the `y`s → that's the numerator over 50._

_Artifacts: `data/fr_90day.json` (6666 docs), `data/d3_candidates.json` (427 candidates)._
