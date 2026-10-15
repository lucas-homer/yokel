# TN — access and rights check (Phase 1, step 1)

Retrieved 2026-10-15. Terms, legal, robots and two index pages (Administrative Register landing,
first page of the rulemaking hearings table). No notices or PDFs collected.
Confidence: **stated** / **inferred** / **unknown**. Nothing here is a legal conclusion.

## Surfaces

1. **Tennessee Administrative Register (T.A.R.) landing**, `sos.tn.gov/publications/services/administrative-register`.
   Declares the register "an official publication compiled and published electronically by the
   Secretary of State".
2. **T.A.R. database pages on `tnsos.org/rules/`**: `RulemakingHearings.php` (hearing notices
   table, paginated), `PendingRules.php` (proposed and rulemaking hearing rules — the surface for
   comment windows without a hearing), `EmergencyRules.php`, `Announcements.php`, archives.
3. **Filing PDFs** on `publications.tnsosfiles.com/rules_filings/*.pdf` (an S3-style bucket).
4. **Agency pages on `tn.gov`** (e.g. agency calendar entries for rulemaking hearings). Not core.

### 1–3. T.A.R. (landing, tnsos.org tables, filing PDFs) — Department of State

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | No terms of use, copyright licence or reuse statement on the Department of State "Web and Social Media Policies" page. It covers privacy, public records, linking and accessibility. Information collected becomes "public record". Footer copyright on tnsos.org. Hearing notices are themselves "official notice". | "Permission to link to the Department of State site is not required, but such links may not present state Web pages within frames." (https://sos.tn.gov/web-and-social-media-policies, linked as "Policies" from tnsos.org). "Rulemaking Hearings are official notice for a rulemaking hearing." and "Copyright © 2010 Tennessee Department of State" (https://tnsos.org/rules/RulemakingHearings.php). "The Tennessee Administrative Web site is a register of filings pursuant to the Uniform Administrative Procedures Act and is an official publication compiled and published electronically by the Secretary of State pursuant to Tennessee Code Annotated, Title 4 Chapter 5." (https://sos.tn.gov/publications/services/administrative-register) | stated |
| Collection method and rate | Public HTTP, no login. `sos.tn.gov` robots.txt is a stock Drupal file (blocks admin/search/login paths; publication pages allowed). `tnsos.org/robots.txt` returned a **CloudFront 403 "Request blocked"** to curl (WAF) while the hearings page itself loaded — so a WAF is in front and its rules are unknown. `publications.tnsosfiles.com/robots.txt` → 403 AccessDenied (bucket with no robots file). Hearings table is server-rendered HTML, paginated (`?page=N`), with filing links to `publications.tnsosfiles.com/rules_filings/MM-NN-YY.pdf`. No API, feed or rate guidance. | https://sos.tn.gov/robots.txt; https://tnsos.org/robots.txt (403 CloudFront); https://publications.tnsosfiles.com/robots.txt (403) | stated (observed); WAF thresholds **unknown** |
| Retain originals | Not addressed. Statute requires the T.A.R. to be published and archived (Public Chapter 566 note on the landing page). | "Beginning July 2, 2009, all filings included in the Tennessee Administrative Register will be published and archived according to Public Chapter 566." (landing page) | inferred (no restriction found) |
| Third-party processing | Not addressed. | — | unknown |
| Public display | Linking expressly allowed, but **not inside frames**. Nothing on quoting or republishing. | policies page above | stated (linking); unknown (republishing) |

### 4. Agency pages on tn.gov

| Field | Finding | Evidence | Confidence |
|---|---|---|---|
| Terms | Web-policies index lists privacy, accessibility, DMCA, COPPA, Title VI. No reuse or scraping terms seen on the index; sub-pages other than the index were not read. | https://www.tn.gov/web-policies.html | stated (index); unknown (sub-pages) |
| Collection method and rate | robots.txt: `User-agent: * / Allow: /`. (First request was reset; second succeeded.) | https://www.tn.gov/robots.txt | stated |
| Retain / third-party / display | Not addressed on the index. | — | unknown |

## Questions for the reviewer

1. With no reuse terms and an "official publication" statement, may we collect, retain and quote
   T.A.R. hearing notices and filing PDFs? (yes/no)
2. The `tnsos.org` WAF blocked a plain robots.txt request. Should we ask the Division of
   Publications for an allowed rate or an allow-listed user agent before scheduled collection?
   (yes/no)
3. Does the "no frames" linking rule matter for our UI (we would link out, not embed)? (confirm
   no embedding / embedding needed)
4. May T.A.R. PDFs be sent to third-party processors (cloud PDF parser, LLM API)? (yes / no /
   local extraction only)
5. Is `PendingRules.php` the agreed surface for comment windows without a hearing, to be mapped in
   the census? (yes/no)

## Provisional collection rule

- **Safe to begin now:** `tnsos.org/rules/*.php` table pages and the linked filing PDFs,
  sequential, identifying user agent, at least 5 seconds between requests; stop on any 403/429.
  Retain bytes and hashes internally. Display = plain link to the filing (never framed).
- **Blocked pending reviewer:** scheduled/unattended polling until Q2 is settled; third-party
  processing (Q4); public republishing of full filings (Q1).
