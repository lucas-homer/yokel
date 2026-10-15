# State universe: TN / v0.1-proposed (2026-10-15)

Status: **draft, blocked on access. Not frozen.** Completeness: not established.
Owner: primary (research child draft). Human reviewer: owner. Decision date: _pending owner signature_.
Protocol/schema versions: PROTOCOL v1.1; rights `tn-register-tables`, `tn-filing-pdfs`,
`tn-register-landing` (all `allowed_watched_only`) and `tn-agency` (`on_hold`), all at version
`2026-10-15.1` (owner decision `owner-2026-10-15`).
Proposed scope label: "Tennessee rulemaking notices filed with the Secretary of State
(Administrative Register) under the UAPA. Agency-only notices are not covered."
Statewide claim justified? **No.** The surfaces are currently refusing our identifying client, no
volume could be measured, and every process is single-lineage under current rights.

**Attended run attestation:** this scoping task was an attended, watched run by the research child
on 2026-10-15, with no scheduled polling. **Result: the first request to `tnsos.org`
(RulemakingHearings.php) returned CloudFront 403 "Request blocked". Per the binding rule we stopped
on that host with no retry. One request to the other allowed host, `sos.tn.gov/publications/…`,
also returned CloudFront 403 "Request blocked". We then stopped all TN collection.** We did not
probe `publications.tnsosfiles.com`: the stop-on-403 rule applies, and the bucket can only be
reached by known file names, which would have to come from the blocked table. No workaround was
attempted (same UA, plain HTTP, no browser, no proxy). CloudFront request IDs:
`ONiJLm2qTMBS_4bk9iYRVIbXz9EKTmmi1GrByNZ6CmcxCw8V7YW6gg==` (tnsos.org) and
`SUQ4VgBfxwowHXI5ajxHzrOZ9rMizscknVoykOfTaVCyb4pSirEOaA==` (sos.tn.gov, POP SFO53-P9).
History: the rights check earlier on 2026-10-15 loaded the hearings page but got a 403 on
`tnsos.org/robots.txt`. Round-2 benchmarking recorded a TN 403, and the July audit hit a 403 on
direct PDF access. **The block is persistent and spans several clients. It is a finding, not a
transient error.**

Everything below therefore rests on repo evidence (`rights/TN.md`, audit fixture
`state-rulemaking-audit/fixtures/tn-pdf.md`, audit findings) and on statute summaries from
search-engine results, not primary text (marked **[secondary]**). It is a scoping skeleton to be
verified on the first permitted attended run.

## Agency and process universe

Roster authority: UAPA agencies (T.C.A. § 4-5-102 "agency"; § 4-5-202 et seq.). Their rules are
compiled as numbered chapters in the *Rules and Regulations of the State of Tennessee* (agency
numbers in chapter IDs, e.g. `1320-08-19` = Revenue). The roster should be enumerated from the
Secretary of State's effective-rules chapter index, with every filing's agency number in the
interval added to it. **Not retrieved: host blocked.** Roster version: _none yet_.

| Agency ID/name | Roster authority, version, evidence locator | Process/stage | Included? | Reason/authority | Authoritative publication(s) | Gaps / single_lineage + human ref |
|---|---|---|---|---|---|---|
| All UAPA agencies, boards, commissions (incl. UT/TBR systems that file in T.A.R.) | § 4-5-102; SOS rules chapter index (not retrieved) | **Notice of Rulemaking Hearing** (§ 4-5-204; form SS-7037): the hearing | **Yes** | Hearing opportunity. Fixture: "Hearing Date: 12/08/2026 … 1:00 p.m. _X_CST/CDT" | Filing PDF `publications.tnsosfiles.com/rules_filings/MM-NN-YY.pdf`, listed in `tnsos.org/rules/RulemakingHearings.php` | single_lineage pending Q5; access blocked (Q1) |
| same | fixture tn-pdf.md | Hearing notice: written comments "may be submitted prior to the hearing" or by a stated date | **Yes, as a separate written-comment window** when the notice invites written comments. Close = stated date, or "prior to the hearing" kept as a relative/anchored close | In-scope comment window. **The hearings table does not carry these dates; they are only in the PDF** | Filing PDF | Labels must keep the hearing-anchored close relative (no computed date) |
| same | fixture | ADA/accommodation request ("at least 10 days prior to the hearing") | **No.** Negative fixture | Not a participation opportunity. Earlier extraction wrongly used this as the comment deadline | Filing PDF | Keep as rejected candidate |
| same | **[secondary]** § 4-5-202(a)(2): proposed rule without hearing, posted to the register website within 7 days of filing; hearing required if within **90 days** of filing a petition comes from **10** affected persons, an association of ≥10 members, a municipality, or a standing legislative committee (threshold lowered from 25 by a later Public Chapter) | **Proposed rules (no hearing)**: hearing-request (petition) window | **Yes** | In-scope hearing-request window. **This is the comment-only/no-hearing class the hearings table misses** | `tnsos.org/rules/PendingRules.php` (proposed + rulemaking-hearing rules) + filing PDF | Q2 asks whether this is the agreed surface. Whether proposed-rule notices also state a written-comment period is **unknown**; verify on the first run |
| same | proposed-rule filing (unknown) | Written-comment window on a proposed rule (if stated) | **Yes, if stated** | In-scope | Filing PDF | unknown |
| same | `tnsos.org/rules/Announcements.php` (named in rights/TN.md, not read) | Hearing reschedule/cancellation, corrected or amended hearing notice, withdrawal of a hearing notice or proposed rule | **Yes (lifecycle)** | In-scope lifecycle | Announcements and/or new filings (exact route **unknown**) | The update route is unmapped. Update recall stays unmeasured until it is mapped |
| same | rights/TN.md | Emergency rules (`EmergencyRules.php`) | **No** as an opportunity (effective on filing; **[secondary]** up to 180 days). A follow-on permanent rulemaking is captured through the processes above | No participation stage | — | — |
| same | — | Final rules filed for effectiveness, Government Operations Committee review | **No** | Post-participation / legislative | — | — |
| Tennessee Public Utility Commission and other bodies with own rulemaking dockets | search result showing TPUC rulemaking docket filings (`tpucdockets.tn.gov`, not fetched) | Docket comment schedules outside the T.A.R. | **Undecided (Q6)** | May set comment windows only in agency dockets | agency docket (host not in surfaces.json) | gap if included |
| Agencies posting comment periods only on `tn.gov` pages (e.g. board meeting/rule pages) | `tn-agency` record (on_hold) | Agency-only comment/hearing notices | **Out of the declared universe, labelled** (Q5) | Not register-published; rights on hold | tn.gov | Explicit coverage gap |
| Local governments, permits (e.g. TDEC permit notices), legislation | plan scope | — | **No** | Plan exclusions | — | — |

NOIRA/early-stage: no TN NOIRA stage is known. Any pre-proposal "stakeholder meeting" notices are
excluded.

**What the public table surfaces likely miss (the pilot's hard-state issues):** (1) proposed rules
with no hearing, which carry the 90-day petition window, are not in the hearings table; (2) written
comment closes are given only inside PDFs, sometimes "prior to the hearing", sometimes a later
date; (3) the accommodation deadline looks like a comment deadline; (4) reschedules, cancellations
and withdrawals sit on an unmapped route (Announcements or new filings); (5) table pagination and
retention are unproven; (6) agency-only and docket-only windows (tn.gov, TPUC) sit outside the
register; (7) **today, every register surface refuses our identifying client.**

## Interval and cohorts

- **Proposed provisional interval:** `[2026-07-01, 2026-10-01)`, i.e. three complete calendar months
  (13 weeks). Boundary zone America/Chicago (the Nashville seat). Accounting only; hearing notices
  carry their own CST/CDT vs EST/EDT tick-box. Cycle rationale: filing IDs are `MM-NN-YY` (month,
  sequence, year), so the calendar month is the natural publication/accounting cycle. A per-month
  sequence also gives an **expected-unit manifest**: every number 01…max in a month either resolves
  or is a named gap.
- **Pre-committed extension rule (volume-based, decided before any count or adapter output):** once
  access is restored, count in-scope filings for the provisional months. If the projected total is
  under 149, add whole earlier months, newest first, to a maximum of 12 months
  (`[2025-10-01, 2026-10-01)`). Report any shortfall. If 3 months already exceed ~300 opportunities,
  keep 3 months (Q4).
- **Expected opportunities/week: unknown.** No count could be taken today, and the earlier rights
  check recorded no row count. No number is projected rather than inventing one. Arithmetic
  template: opportunities = (hearing notices × [1 hearing + p_wc written-comment windows]) +
  (proposed rules × [1 petition window + p_pc comment windows]) + carry-ins. p_wc ≈ 1 on the one
  fixture (n = 1).
- **Publication-time authority:** the "Filed with the Department of State on" date and the
  "RECEIVED … 3:14 pm" stamp on the filing (fixture: Sep 25 2026, 3:14 pm). Web posting can lag
  filing (**[secondary]** ≤7 days for proposed rules). Because the earliest evidenced *publication*
  is the web posting, which the PDF does not show, filing-vs-posting near boundaries become review
  cases.
- **Carry-in rule and backward boundary:** proposed rules filed in the 90 + 7 days before start
  (petition window still open at start) and hearing notices filed before start whose hearing or
  stated comment close is on or after start. Proposed backward boundary: **6 complete months before
  start** (`[2026-01-01, 2026-07-01)`), extended by months until a month yields no active item.
  Authority: the 90-day petition window **[secondary]**. The hearing lead-time maximum is unknown
  (the fixture's hearing is 74 days after filing). Archive reach of `tnsos.org` tables is
  **unverified**. Filing PDFs are archived permanently (Public Chapter 566 note, rights/TN.md).
- **Older-proceeding updates:** any announcement or new filing in the interval that targets an older
  hearing or proposed rule. The history universe is unknown until the Announcements/withdrawal route
  is mapped.
- **Post-close follow-up:** hearings run to the hearing date + 14 days; petition windows to close + 30
  days (a petition triggers a new hearing notice); comment windows to close + 14 days. To be
  re-justified after observing posting lag.

## Authority, access and source map

| Source ID/lineage | Agencies/processes covered | Authority/precedence evidence | Rights record/version; collection allowed? | Method/rate | Retain originals? | Third-party/public-evidence limits | Cadence/retention | Gaps |
|---|---|---|---|---|---|---|---|---|
| L1 `tn-sos` / `tnsos.org/rules/RulemakingHearings.php` (paginated) | hearing notices | "Rulemaking Hearings are official notice" (rights/TN.md) | `tn-register-tables` 2026-10-15.1, allowed **watched only** | attended, 1 req/5 s | yes | public notices ok; link out, never frame | continuous; history reach unknown | **403 today** |
| L1 / `PendingRules.php`, `Announcements.php`, `EmergencyRules.php`, archives | proposed rules, lifecycle, emergency | T.A.R. official publication (§ 4-5 Title 4 Ch. 5) | same | same | yes | same | unknown | **403 host**; contents unverified |
| L1 / filing PDFs `publications.tnsosfiles.com/rules_filings/` | all filings | official filing | `tn-filing-pdfs`, watched only | same | yes | same | permanent archive | not probed (stop rule) |
| L1 / `sos.tn.gov/publications/…` landing | references, chapter index | — | `tn-register-landing`, watched only | same | yes | same | — | **403 today** |
| L2 agency pages `tn.gov` | some hearings/comment notices | agency-published | `tn-agency` **on_hold** | none | no | — | — | Only plausible independent lineage (Q5) |
| L3 TPUC docket | TPUC rulemakings | agency docket | no record | none | — | — | — | Q6 |

Cross-check: table ↔ filing PDF ↔ month filing-number sequence are all **L1 (same lineage)**. They
can expose omissions but cannot corroborate. **Independent lineage: none lawful today.** All
processes are `single_lineage: true` pending Q5, so the completeness ceiling is "not established".

## Expected publications and surface tests

| Source/process | Expected units | Expectation evidence | Filters/pagination/terminal proof | Full-body cross-check | Agency/history cross-check | Missing units/reviewer decision |
|---|---|---|---|---|---|---|
| Filings by month sequence | every `MM-NN-YY` for 3–12 months + 6-month carry-in | fixture ID pattern (rights/TN.md) | Terminal proof = the highest number in the month seen on any table page, plus the first missing number. **Unverified** | each PDF | none | all `not_attempted` while 403 persists |
| Hearings / Pending / Announcements tables | all pages | rights/TN.md (`?page=N`) | last-page proof unknown | — | — | same |

Unknown counts: everything. Not assumed zero.

## Enumeration, labels and review

Not started. Temporal notes already seen (fixture): a hearing time with a CST/CDT vs EST/EDT tick-box
(preserve the box state); "at least 10 days prior to the hearing" (accommodation; not an
opportunity); "written comments may be submitted prior to the hearing" (relative close); filing
date ≠ effective date (an earlier extraction made this error); "RECEIVED Sep 25 2026, 3:14 pm"
stamp vs typed filing date.

## Sizing and freeze

- Volume, format mix and templates: **unknown**. Fixture template SS-7037 (Feb 2025) is a filled
  form with typed fields plus a received stamp. Rule text follows the notice pages.
- **LlamaParse estimate (scenario, not measured):** parse only the notice pages (≈3 per filing), not
  the full rule text. Scenario at 150 filings × 3 pages = 450 pages. If 30% lack a usable text layer
  (stamps/scans; earlier visual checks failed through other clients): 135 pages × 10 ≈ **1,350
  credits**. Worst case 100% scanned: 4,500 credits, **over the 4,000 allocation**. Measure the
  text-layer rate on the first permitted run before reserving credits.

## Questions for the reviewer

1. TN register hosts refuse our identifying client (CloudFront 403). Send the TN outreach now,
   revised to cite the 403 and these request IDs and to ask for an allow-listed UA or a preferred
   route (feed, e-mail list, bulk files)? (yes/no)
2. Is `PendingRules.php` (proposed rules with a 90-day petition window) the agreed surface for windows
   without a hearing, once access returns? (yes/no)
3. Should a TN hearing notice's "written comments … prior to the hearing" count as a separate
   written-comment opportunity with a relative close? (yes: recommended / no, hearing only)
4. Accept the volume-based interval rule: start at `[2026-07-01, 2026-10-01)` and extend by whole
   months to at most 12, before counting? (yes / choose fixed 12 months)
5. May `tn.gov` agency pages be read as an independent-lineage cross-check? (yes, read-only / no,
   accept single_lineage and "not established")
6. Are agency-docket rulemakings outside the T.A.R. (e.g. TPUC) in the TN universe? (no, labelled
   exclusion: recommended for v1 / yes, needs a rights record)
7. If access is not restored by the Phase 1 selection decision, should TN be recorded as "hard state
   without a credible collection route" and trigger the bounded substitution or scope decision in
   the plan? (yes/no)

## Request log (attended run, 2026-10-15, UA `DocketClock-research/0.1 (github.com/lucas-homer/yokel)`)

| # | URL | Time (UTC) | Status |
|---|---|---|---|
| 19 | https://tnsos.org/rules/RulemakingHearings.php | 16:28:41 | **403** CloudFront "Request blocked" → stopped on host |
| 20 | https://sos.tn.gov/publications/services/administrative-register | 16:28:48 | **403** CloudFront "Request blocked" → stopped all TN collection |

(The numbering continues the shared run log; requests 1–18 were CT.) Not requested:
`publications.tnsosfiles.com`, `tn.gov`, statute hosts. Statute points marked [secondary] come from
a search-engine summary (syfert.com mirror of T.C.A. § 4-5-202; Public Chapter 502 text on
publications.tnsosfiles.com, seen only as a search result). Verify against official text.
