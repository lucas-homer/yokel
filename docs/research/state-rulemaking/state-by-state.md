# State-by-State Rulemaking Publication Reference (50 states + DC)

> Companion to [`README.md`](README.md) (synthesis + ingestion strategy) and
> [`california-deep-dive.md`](california-deep-dive.md). Researched July 2026 via parallel
> web-research agents verifying against official .gov sources. **Verification caveat:** the research
> sandbox's egress proxy blocked direct fetches of most state .gov hosts, so many facts were
> verified through search-engine retrieval of official-page content rather than raw page fetches.
> Items the researchers could not confirm at page level are marked *[unverified]*. Re-verify URL
> patterns and feed availability from an unrestricted network before building adapters.

## Master reference table

Ingestion rating is for automated extraction of comment-deadline notices (EASY / MODERATE / HARD).
"Portal" = centralized state-run online comment submission (the state's Regulations.gov analogue).

| Jurisdiction | Publication (publisher) | Cadence | Format | Feed / notify | Portal | Min. comment period (statute) | Ingest |
|---|---|---|---|---|---|---|---|
| AL | Alabama Administrative Monthly (Legislative Services Agency) | Monthly (last business day) | PDF via `/api/aam/YYYY-MM` | None found; undocumented HTTP API endpoints | No | ~35 days (Code of Ala. § 41-22-5) *[unverified]* | MODERATE |
| AK | Online Public Notice System (Lt. Governor); quarterly Admin. Register = adopted rules only | Continuous | HTML + PDF attachments | **RSS + daily email, saved-search scoped** | Partial (OPN comment links) | 30 days (AS 44.62.190(a)) | EASY-MOD |
| AZ | Arizona Administrative Register (SOS) | Weekly (Fri) | PDF, deterministic URLs | Code-update email only | No | 30 days to close of record (A.R.S. § 41-1023(B)) | EASY-MOD |
| AR | Arkansas Register (SOS) | Monthly | PDF + vendor DB (ark.org/NIC) | Bulk-data download page *[contents unverified]* | No | 30 days (ACA § 25-15-204) | MOD-HARD |
| CA | CA Regulatory Notice Register "Z Register" (OAL) | Weekly (Fri) | PDF + monthly HTML TOCs | None; manual email list; CARB GovDelivery | No — per agency | **45 days** (Gov. Code § 11346.4); 15 days modified text (§ 11346.8(c)) | MODERATE |
| CO | Colorado Register (SOS) + real-time **eDocket** | 2×/mo (10th/25th) + continuous | PDF + eDocket DB | Per-agency email + rulemaking.colorado.gov notices | Partial (discovery) | Hearing ≥20 days after notice (C.R.S. § 24-4-103) | EASY-MOD |
| CT | **eRegulations System** (Secretary of the State) — no periodical register | Continuous | HTML portal (FileNet docs) | eRegs email alerts | **Yes — "Comment Now"** | 30 days (CGS § 4-168) | EASY-MOD |
| DE | Delaware Register of Regulations (Registrar of Regulations, Gen. Assembly) | Monthly (1st) | **HTML notices** + PDF issues; per-issue comment calendar | No register feed; statewide DE Notification Service *[unverified]* | No | 30 days (29 Del. C. § 10118(a)); ≥15 days post-hearing | EASY |
| DC | DC Register (ODAI, Office of the Secretary) | Weekly (Fri) | Notice DB + Word/PDF | None documented | No | 30 days default (D.C. Code § 2-505(a)), good-cause waiver | MODERATE |
| FL | **Florida Administrative Register** (Dept. of State) | **Daily** (business days) | HTML DB (flrules.org) | **Free email subscription** | No (despite "eRulemaking" branding) | 21 days (§ 120.54(3)(c)1, F.S.) | MOD (EASY past bot-blocking) |
| GA | **No official register** — per-agency notices; GA Government Register is unofficial LexisNexis | Per-agency | Agency sites + mailing lists | Per-agency lists only | No | 30 days (O.C.G.A. § 50-13-4(a)) | HARD |
| HI | **None** — Lt. Gov. "Proposed Changes" page + newspaper notices | Rolling | PDF packets on WordPress | None | No | 30 days' hearing notice (HRS § 91-3(a)(1)) | HARD |
| ID | Idaho Administrative Bulletin (DFM, Governor's office) | Monthly (1st Wed) | PDF, predictable `bulletin/YYYY/MM.pdf` | Email list | No | 21 days (Idaho Code § 67-5222) | EASY-MOD |
| IL | Illinois Register (SOS Index Dept.) | Weekly (Fri) | PDF, predictable paths | None; JCAR "Flinn Report" weekly PDF digest | No | 45 days First Notice (5 ILCS 100/5-40(b)) | MODERATE |
| IN | Indiana Register (LSA) — IARP platform | Continuous (weekly Wed batches) | **HTML** with DIN identifiers | None found; possible undocumented JSON XHR | No | ~30 days (IC 4-22-2-23/-26, post-HEA 1623) | EASY |
| IA | Iowa Administrative Bulletin (LSA) + **rules.iowa.gov** portal | Biweekly | PDF (dated URLs) + HTML portal | "Bills & Rules Watch" email | **Yes — rules.iowa.gov** | 20 days written (Iowa Code § 17A.4(1)(b)) | MODERATE |
| KS | Kansas Register (SOS) | Weekly (Thu) | **HTML per-notice pages** + PDF | Agency-filterable email subscription | No (in-process index = discovery only) | **60 days** (K.S.A. 77-421 — notice period *is* the comment period) | EASY |
| KY | Administrative Register of Kentucky (LRC) | Monthly (1st) | PDF, patterned URLs | None found | No | Hearing + comments through end of month following publication (KRS 13A.270) | MODERATE |
| LA | Louisiana Register (Office of the State Register, Div. of Administration) | Monthly (20th) | PDF | Email listserv | No | Deadline set per notice; ≥90-day action bar (La. R.S. 49:961 et seq.) | MODERATE |
| ME | Weekly consolidated rulemaking notices (SOS) | Weekly (Wed) | **Static HTML**, deterministic URLs | None | No | 17–24 days pre-hearing / ≥30 days no-hearing; +10 days post-hearing (5 M.R.S. § 8052–53) | EASY |
| MD | Maryland Register (Division of State Documents) | Biweekly (Fri) | HTML "Assembled" pages (SharePoint); only ~15 issues free | None; paid print/PDF subs; **PertinentDates.pdf** lists every comment-close date | No | 30 days (SG § 10-111(a)) | MODERATE |
| MA | Massachusetts Register (Secretary of the Commonwealth) | Biweekly (Fri) | **Paywalled** ($225/yr online) | None | No | 21 days' notice (M.G.L. c.30A §§ 2–3) | HARD |
| MI | Michigan Register (MOAHR/LARA) + **ARS** rules portal | 2×/mo (1st & 15th) | PDF + ARS HTML DB | GovDelivery email alerts | No | ≥10-day hearing notice; no fixed comment floor (MCL 24.241–.242) | MODERATE |
| MN | Minnesota State Register (Dept. of Administration) | Weekly (Mon) | PDF (Revisor archive has stable URLs) | Paid email sub (~$180/yr) | Partial — **OAH/CAH eComments** (Granicus; mandatory post-hearing) | 30 days (§ 14.22); 60-day RFC (§ 14.101) | MODERATE |
| MS | Mississippi Administrative Bulletin (SOS) | Event-driven (≤2 business days after filing) | ASP.NET search portal + PDFs | None found *[email signup unverified]* | No | 25 days (Miss. Code Ann. § 25-43-3.106) | HARD |
| MO | Missouri Register (SOS Administrative Rules Div.) | Semi-monthly (1st & 15th) | PDF + searchable DB | **Account-based email notifications** | No | 30 days (RSMo § 536.021) | MODERATE |
| MT | Montana Administrative Register (SOS) | 2×/mo | PDF + rules.mt.gov notices gateway | Email updates; per-agency interested-persons lists | No | 28 days (MCA § 2-4-302) | MODERATE |
| NE | **No register** — SOS Proposed Rules Docket + newspaper notice | Continuous | CGI HTML + PDFs (**many image scans**) | Docket email subscription (incl. statewide) | Optional per-agency in tracking system | 30 days' hearing notice (Neb. Rev. Stat. § 84-907) | HARD |
| NV | Nevada Register of Administrative Regulations (Legislative Counsel Bureau) | Monthly (≥10×/yr) | Per-regulation PDFs, rolling | None from LCB; notice.nv.gov aggregates hearings | No | 30 days' notice (NRS 233B.060) | HARD |
| NH | NH Rulemaking Register (Office of Legislative Services) | Weekly (Thu) | PDF | None official (3rd-party nh-rulemaking.app) | No | 20 days' notice; comments ≥5 business days post-hearing (RSA 541-A:6, :11) | MODERATE |
| NJ | New Jersey Register (OAL, **published by LexisNexis**) | Semimonthly (1st & 3rd Mon) | LexisNexis viewer + OAL PDFs + Dynamics 365 proposals DB | None official | No | 30 days statutory, 60 days customary (N.J.S.A. 52:14B-4) | HARD |
| NM | New Mexico Register (Commission of Public Records) | 2×/mo | PDF + **per-notice HTML pages** | None central; NM Sunshine Portal hearing search | No | 30 days (NMSA § 14-4-5.2) | MODERATE |
| NY | New York State Register (DOS Division of Administrative Rules) | Weekly (Wed) | PDF, deterministic `{MMDDYY}.pdf` URLs | Email alert on posting | No | **60 days** (SAPA § 202(1)) | MODERATE |
| NC | North Carolina Register (OAH Rules Division) | Semimonthly | PDF (`files.nc.gov` + VersionId tokens) | Historical email list *[unverified]* | No | **60 days** (G.S. 150B-21.2(f)) | MODERATE |
| ND | **No register** — Legislative Council posts notice PDFs; quarterly Code Supplements | Continuous / quarterly | PDF (**some image scans**) + HTML events calendar | **RSS for rules notices** | No | ≥20 days notice-to-hearing + ≥10 days post-hearing (N.D.C.C. 28-32-10/-11) | MODERATE |
| OH | Register of Ohio (Legislative Service Commission) | Continuous | Servlet DB + PDF filings (stable parameterized URLs) | None; per-agency e-notification; CSI comment track | No | ~30 days to hearing (ORC 119.03) | MODERATE |
| OK | Oklahoma Register (OAR, SOS) — rules.ok.gov | Semi-monthly | PDF (Azure blob) + portal HTML | Portal email subscription (account) | No (portal lists open-comment rules) | 30 days (75 O.S. § 303) | MODERATE |
| OR | Oregon Bulletin (SOS Archives Div.) — **OARD database** | Monthly (1st business day) | **HTML database** | None; per-agency lists (ORS 183.335(8)) | No | ~21-day notice floor (ORS 183.335); no fixed count | MODERATE |
| PA | Pennsylvania Bulletin (Legislative Reference Bureau / Fry Communications) | Weekly (Sat issue, posted Fri) | **HTML + PDF**, stable URLs | Weekly Bulletin email; **IRRC subscriber service** + open-for-comment list | No (+ IRRC comment intake by email) | 30 days (Regulatory Review Act, 71 P.S. § 745.1 et seq.) | EASY |
| RI | **RICR portal** (Secretary of State) — no periodical register | Continuous | **HTML database**, citation-stable URLs | Email notifications | Notices centralized; submission per notice | 30 days (§ 42-35-2.8(b)) | EASY |
| SC | South Carolina State Register (Legislative Council) | Monthly | PDF, deterministic `Sr{vol}-{iss}.pdf` (20+ yrs stable) | None (legislation-only email tools) | No | 30 days (S.C. Code § 1-23-110, **verified**) | MODERATE |
| SD | South Dakota Register (LRC) + **rules.sd.gov** | Weekly | PDF via mylrc API + rules.sd.gov notices | mylrc de facto REST API; My LRC+ email | **Yes — rules.sd.gov online comments** | 20-day notice; written comments cut off 72h pre-hearing (SDCL 1-26-4) | MODERATE |
| TN | Rolling SOS filings (Division of Publications); legacy monthly Administrative Register | Rolling | PDF on file-CDN domains | None found | No | 45-day hearing notice window (T.C.A. § 4-5-203/204) *[cite unverified]* | HARD |
| TX | Texas Register (SOS) | Weekly (Fri, 5pm CT) | **HTML + PDF**, archive to 2000 (UNT portal to 1976 w/ OAI-PMH) | Email list (register@sos.texas.gov) | No | 30 days (Gov't Code § 2001.029/.023) | EASY |
| UT | Utah State Bulletin (Office of Administrative Rules) | 2×/mo (1st & 15th) | PDF `bYYYYMMDD.pdf` + RTF w/ MD5 | **RSS feeds (rules.utah.gov/rssfeeds/)** + Digest email | No (central discovery of every open period) | 30 days, max 113 (Utah Code § 63G-3-301) | EASY |
| VT | SOS Rules Service (secure.vermont.gov, NIC/Tyler-hosted) — no register | Continuous + newspapers | DB + PDF filings | None documented | No (+ LCAR during legislative review) | Hearing ≥30 days post-notice; ≥7 days post-hearing; 14 days if no hearing (3 V.S.A. § 840) | MODERATE |
| VA | Virginia Register of Regulations (Code Commission/DLS) + **Regulatory Town Hall** | Biweekly + continuous Town Hall | PDF register (deterministic URLs) + Town Hall HTML/XML | **Register RSS; Town Hall nightly emails; per-doc XML views** | **Yes — Town Hall Public Comment Forums** | **60 days** proposed (§ 2.2-4007.03); 30 days NOIRA | EASY |
| WA | Washington State Register (Office of the Code Reviser) | 2×/mo (24 issues/yr) | **HTML issue TOCs + per-filing PDFs, fully deterministic URLs** | None official; per-agency GovDelivery | No | 20 days publication-to-hearing (RCW 34.05.320(1)) | EASY |
| WV | West Virginia State Register (SOS Administrative Law Div.) | Weekly (Fri) | PDF via `readpdf.aspx?did=` + Rule Monitor table | None found *[unverified]* | No | 30 days (W. Va. Code § 29A-3-5) *[text unverified]* | MODERATE |
| WI | Wisconsin Administrative Register (Legislative Reference Bureau) | Weekly + monthly "B" edition | **Structured HTML** (docs.legis.wisconsin.gov) | Free legislature email notifications | **Yes-ish — comment links on docs.legis rule pages** | ≥10-day hearing notice; no fixed comment floor (Wis. Stat. § 227.17) | EASY |
| WY | **rules.wyo.gov** database (SOS as Registrar) — no periodical register | Continuous | Web DB + PDF/Word attachments | GovDelivery subscriptions | **Yes — "Provide Public Comment" links** | 45 days (W.S. § 16-3-103) | MODERATE |

## Notes on the table

- **Comment-period figures are floors, not typical values.** Many states' APAs anchor timing to the
  *hearing* rather than a written-comment window (MI, WI, NE, HI, CO, NH, VT), so the practical
  deadline is notice-specific. Statutes were verified to varying depth — cite-level flags are in the
  per-state findings below.
- **"No register" states** (NE, ND, WY, HI, and functionally CT/RI/VT/AK) publish through
  continuous-posting portals or newspaper notice instead of a periodical. These need event-driven
  polling rather than issue-cadence polling.
- **Legislative-branch publishers** are common (AL, IA, IN, KY, NH, NV, OH, SD, SC, WI, ND, PA):
  the register is often run by a legislative service agency, not the Secretary of State. This
  matters for who to contact about data access.
- **Post-comment legislative review** exists in several states (WV Legislative Rule-Making Review
  Committee, SC General Assembly approval, IL JCAR, PA IRRC, NC Rules Review Commission, OH JCARR,
  VT LCAR): windows can reopen or rules can die after the comment phase — relevant to DocketClock's
  cross-window chain semantics (extensions/withdrawals have state analogues).

## Per-state detail

The full per-state findings (fields: register, format, machine-readability, comment submission,
comment period, ingestion assessment — each with source URLs) are preserved verbatim from the
research agents below, grouped by region.

<!-- Per-state details appended from regional research batches -->

### Northeast: CT, ME, MA, NH, RI, VT, NY, NJ, PA


### CONNECTICUT
1. **No periodical register.** Since 2013–2017 transition, rulemaking notices, proposed regs, regulation-making record, final regs posted continuously to the **Connecticut eRegulations System**, administered by the **Secretary of the State**. Since July 1, 2017 eRegs is the *official* version of the Regulations of CT State Agencies and official electronic repository (launched July 1, 2013). Cadence: continuous per-filing. (eregulations.ct.gov/eRegsPortal/; CGS § 4-168)
2. Searchable HTML database/portal: browse views for Proposed Regulations, Regulations Open for Comment, Emergency Regulations, RCSA. Documents served through GUID-keyed `getDocument` links (FileNet back end). Proposed: eregulations.ct.gov/eRegsPortal/Browse/ProposedRegulations.
3. **Email alerts** — "eRegs Alerts" signup sends automatic email when agencies post documents. **No public API or RSS.** Back-end vendor: Fairfax Data Systems maintaining IBM FileNet (per OPM IT brief); CT's own portal.
4. **YES — centralized online comment portal.** Every regulation "Open for Public Comments" has a **"Comment Now" button** on its Regulation-Making Record page; commenters enter info, comments, attachments directly into the record. Closest state analogue to Regulations.gov among the nine.
5. **Minimum 30 days.** CGS § 4-168(a): notice posted on eRegs ≥30 days before adoption, must specify comment period "of not less than thirty days."
6. **Ingestion: EASY–MODERATE.** Proposed/open-for-comment listings are structured HTML tables with per-rule tracking numbers (PR2019-004) linking to stable record pages; comment deadlines explicit fields. GUID FileNet doc URLs less friendly but deadline metadata is in HTML listings; eRegs alerts as change signal. No API — scrape the ASP.NET portal.

### MAINE
1. No formally named register; SOS (Bureau of Corporations, Elections & Commissions) publishes **consolidated weekly rulemaking notices, every Wednesday**, plus newspaper publication (5 M.R.S. § 8053). (maine.gov/sos/rulemaking/notices)
2. **Plain static HTML** — one page per weekly notice, highly predictable URLs: `maine.gov/sos/cec/rules/notices/YYYY/MMDDYY.html`, annual indexes, multi-year archive. Each entry lists agency, chapter, hearing date, **comment deadline**, agency contact with email.
3. **No API, no RSS, no documented SOS rulemaking listserv.** (Generic maine.gov email subscription service exists.) State-hosted static HTML, no vendor.
4. **Per-agency.** Comments to contact in each notice or at hearing; hearing required if 5+ persons request.
5. Maine APA (5 M.R.S. §§ 8052–8053): notice **17–24 days before hearing**, or **≥30 days before comment deadline if no hearing**; if hearing held, written comments accepted **≥10 days after hearing** (§ 8052(3)). Extensions noticed within 14 days.
6. **Ingestion: EASY.** Weekly date-stamped static HTML, deterministic URL pattern, consistent per-notice fields — trivially scrapeable with Wednesday cron. No feed; risks: host aliasing (www vs www1), free-text drift.

### MASSACHUSETTS
1. **Massachusetts Register** — official publication of new/amended regs, hearing/comment notices, EOs, AG opinions — **Secretary of the Commonwealth, Publications and Regulations Division**. **Biweekly (Fridays).**
2. **PAYWALLED** — online annual sub **$225/yr** (login), print $300/yr, single issues $15; electronic version expressly "unofficial." No free current-issue web version. Free alternatives: unofficial CMR text on Mass.gov; archived Register PDFs in State Library digital repository (DSpace archives.lib.state.ma.us; AM Quartex platform June 2026).
3. **None.** No API, RSS, or statewide e-notification. Agencies individually notify persons filing an annual written request (renewed each December, M.G.L. c.30A § 2) — paper-era mechanism.
4. **Per-agency** — written comments to agency address in each notice or hearing testimony; notices in newspapers and agency Mass.gov pages. No centralized portal.
5. No fixed statutory comment length. M.G.L. c.30A **§ 2/§ 3**: notice **≥21 days** before hearing or action — 21 days effective minimum.
6. **Ingestion: HARD.** Consolidated stream behind $225/yr login, no feed; free signals fragmented across per-agency Mass.gov pages and newspaper notices; State Library archive lags. Realistically: pay for Register + parse subscriber PDFs, or scrape dozens of heterogeneous agency pages.

### NEW HAMPSHIRE
1. **New Hampshire Rulemaking Register**, compiled/published by **Office of Legislative Services (OLS), Administrative Rules Division** (legislative branch). **Weekly, every Thursday.** (gc.nh.gov/rules/register/)
2. **PDF.** Weekly issues + individual notice PDFs in per-year/per-issue folders, e.g. `gc.nh.gov/rules/register/2026/0326/2026-72 IP Notice Env-Wq 1500 various.pdf` (spaces in filenames). Separate **OLS Rules database search**: gc.nh.gov/nholsrulesdbsearch/.
3. **No API/RSS from state.** Distribution = posted PDF (adminrules@gc.nh.gov). RSA 541-A:6 per-agency advance-notice lists. **Third-party portal nh-rulemaking.app ("NH Rules Portal")** offers search + email alerts over Register content — evidence official stream is unstructured.
4. **Per-agency** — written/electronic comments to agency contact by cutoff in each notice, or testimony at mandatory hearing (RSA 541-A:11 requires hearing on all proposed rules). No central portal.
5. No single fixed minimum. RSA **541-A:6**: ≥**20 days' notice** of hearing and written-testimony cutoff. RSA **541-A:11**: hearing on every rule; written/electronic submissions accepted **≥5 business days after hearing**; expedited repeals: hearing ≥7 days after Register publication (541-A:19-a).
6. **Ingestion: MODERATE.** Weekly cadence, predictable folders, but text-layer PDFs (inconsistently named, spaces in filenames) → PDF parsing; no feed → Thursday polling. Third-party app confirms parseable but nontrivial.

### RHODE ISLAND
1. **No periodical register.** Under rewritten RI APA (ch. 42-35), all proposed and final rules filed with **Secretary of State** and posted continuously to the **Rhode Island Code of Regulations (RICR)** portal, rules.sos.ri.gov. Continuous per-filing.
2. **Searchable HTML database/portal.** Proposed-rule index at rules.sos.ri.gov/regulations/Index/Proposed; regulations as structured HTML "parts" with stable citation URLs (`/regulations/part/216-10-05-4`), full rulemaking record attached (notices, concise explanatory statements).
3. **Email notifications** for pending and final regulatory actions (signup at rules.sos.ri.gov). **No public API or RSS.** Some agencies layer own feeds (RIDOH "Regulatory News" page). Department of State system, no vendor branding.
4. Notices centralized on RICR; § 42-35-2.7 requires each notice to state where/when/how to comment; comments submitted **to the promulgating agency** per notice (email/mail/hearing) — Regulations.gov-style collection built into portal NOT confirmed.
5. **Minimum 30 days** after notice publication — § **42-35-2.8(b)**; hearing on request of 25 persons/agency/25-member association within 10 days; hearing ≥5 days before comment close.
6. **Ingestion: EASY.** Single statewide proposed-rules index in structured HTML, per-rule pages, citation-stable URLs, explicit comment-window dates, plus official email channel. No API/RSS — scrape the index on schedule; modern, consistent portal.

### VERMONT
1. **No periodical register.** Filings with **Secretary of State** (3 V.S.A. ch. 25); SOS posts notices online (within one week of receipt) and publishes in designated **newspapers of record** two weeks from receipt (e.g. Seven Days "Proposed State Rules"). Continuous.
2. **Searchable online database** — **Vermont SOS Rules Service** at secure.vermont.gov/SOS/rules/ (proposed and adopted filings; documents as PDFs), plus SOS "Notices of Rulemaking" HTML page listing current notices with hearing/comment info and contacts.
3. **No API, RSS, or statewide email subscription.** secure.vermont.gov run by **Vermont Information Consortium (NIC Vermont)** — NIC acquired by **Tyler Technologies** 2021 — vendor-hosted digital-government contract.
4. **Per-agency** — via agency contact in each notice; comments on rules under legislative review may also go to **LCAR** (Legislative Committee on Administrative Rules). No central portal.
5. 3 V.S.A. **§ 840**: submissions accepted **≥ through 7th day after last hearing**; first hearing **no sooner than 30 days** after § 839 notice; SOS Rule on Rulemaking: if no hearing, comment deadline **≥14 calendar days** after newspaper publication. (Effective window with hearing: ≥37 days from notice.)
6. **Ingestion: MODERATE.** Centralized notices in SOS database + HTML notices page with deadlines/contacts, but no feed/API, PDF attachments, vendor-hosted form-driven search app. Low volume helps.

### NEW YORK
1. **New York State Register** (ISSN 0197-2472), **Department of State, Division of Administrative Rules (DAR)**. **Weekly (Wednesday-dated issues)** + quarterly indexes. (dos.ny.gov/state-register)
2. **Weekly PDF**, highly stable URL pattern: `dos.ny.gov/system/files/documents/{YYYY}/{MM}/{MMDDYY}.pdf` (e.g. /2026/07/070826.pdf). No HTML edition. Paid print subs still exist ($80/yr).
3. **Email alerts** on posting (signup on State Register page). **No API, RSS, or bulk data.** State-hosted Drupal.
4. **Per-agency.** Each Notice of Proposed Rule Making prints agency contact ("Data, views or arguments may be submitted to:"). No centralized portal. (DAR rulemaking manual.)
5. **Minimum 60 days** after Register publication — SAPA **§ 202(1)**; if statute requires hearing, comments close ≥**5 days after last hearing**. (Raised 45→60 days by 2012 amendment.)
6. **Ingestion: MODERATE.** One predictable date-stamped text-layer PDF per week, deterministic URL, rigid section format ("PUBLIC COMMENT will be received until: 60 days after publication...") → weekly fetch + regex extraction reliable. PDF-only, multi-column layout is main friction.

### NEW JERSEY
1. **New Jersey Register** — official journal of agency rulemaking — issued by **Office of Administrative Law (OAL), Division of Administrative Rules**, **published by LexisNexis**. **Semimonthly — first and third Monday** (~24 issues/yr; twice-monthly since Nov 1981). Publication schedule: nj.gov/oal/rules/schedule/.
2. Vendor-hosted. **Free public online access** to current Register (back to July 3, 1995) via OAL/LexisNexis portal (lexisnexis.com/hottopics/njoal); paid via advance.lexis.com. OAL posts individual proposal PDFs (`nj.gov/oal/rules/pdf/PRN 2018-031 (50 N.J.R. 1015(a)).pdf`) and maintains **searchable database of all active rule proposals** on Microsoft **Dynamics 365 Government portals**: oalrulesproduction.dynamics365portals.us (fields: proposing entity, publication date, summary, impacts, N.J.R. citation).
3. **No official API, RSS, or statewide email list.** Dynamics 365 proposals DB = most structured official source (web forms, no documented API). Register inside LexisNexis viewer (hostile to scraping). Departments run own notice pages/listservs (DOH, DCA).
4. **Per-agency** — comments to contact in each notice of proposal (increasingly agency web forms or email). **No centralized portal.**
5. Statutory minimum **30 days** (N.J.S.A. 52:14B-4; +30 days if sufficient public interest shown). **In practice most proposals carry 60-day comment period** (60 days exempts from rulemaking-calendar requirements of 52:14B-3, per N.J.A.C. 1:30); substantial changes on adoption require fresh 60-day period (52:14B-4.10).
6. **Ingestion: HARD.** Authoritative stream locked in LexisNexis viewer; workable sources are the Dynamics 365 DB (structured but session/form-driven) and scattered per-agency PDF/HTML pages, no feeds. Expect brittle scraping + PDF parsing.

### PENNSYLVANIA
1. **Pennsylvania Bulletin** — official gazette (proposed/final rulemakings, notices, proclamations, court rules) — produced by **Legislative Reference Bureau** (Joint Committee on Documents), printed/distributed by **Fry Communications**. **Weekly; Saturday-dated issues posted online Friday ~9 a.m.** (pacodeandbulletin.gov; published schedule PDF.)
2. **Both HTML and PDF.** Per-document **HTML** with stable URLs (`pacodeandbulletin.gov/Display/pabull?file=/secure/pabulletin/data/vol56/56-XX/NNNN.html`), full-text search, whole-issue PDFs at deterministic paths (`/secure/pabulletin/data/vol56/56-17/56-17.pdf`). Hosted by Fry Communications with LRB.
3. **Email** — free "Register for Weekly Bulletin Email" (pacodeandbulletin.gov/Account/PARegister). **No documented API or RSS.** Plus **IRRC** (Independent Regulatory Review Commission) regulation-tracking site: per-regulation pages, regulation search, "Open for Comment" homepage list, **IRRC Subscriber Service** (email per agency/regulation): irrc.state.pa.us/regulations/subscribe.cfm.
4. **Per-agency**, to contact in each proposal's Preamble; comments may also go to **IRRC** (irrc@irrc.state.pa.us, mail, fax — no web comment form), and IRRC posts received comments on each regulation's page. No statewide portal.
5. **Minimum 30 days** from publication of proposed rulemaking in the Bulletin — Regulatory Review Act (Act 181 of 1982, 71 P.S. § 745.1 et seq.); IRRC: comment period "lasts for a minimum of 30 days."
6. **Ingestion: EASY.** Weekly on published schedule, per-document structured HTML at stable URLs with "Proposed Rulemaking" sections containing explicit deadline language, whole-issue PDFs as fallback, two email channels (Bulletin + IRRC); IRRC per-regulation pages = second cross-checkable deadline source. Best-in-class among these nine alongside CT and RI.

### Summary table
| State | Publication | Cadence | Format | Feeds/alerts | Central portal | Min. comment | Ingestion |
|---|---|---|---|---|---|---|---|
| CT | eRegulations System | Continuous | HTML portal | eRegs email; no API | **Yes — "Comment Now"** | 30 d | EASY–MODERATE |
| ME | Weekly Rulemaking Notices | Weekly Wed | Static HTML | None | No | 17–24 d pre-hearing / ≥30 d no-hearing | EASY |
| MA | Massachusetts Register | Biweekly Fri | Paywalled ($225/yr) | None | No | 21 d notice | HARD |
| NH | NH Rulemaking Register | Weekly Thu | PDF | None (3rd-party app) | No | 20 d notice; ≥5 bd post-hearing | MODERATE |
| RI | RICR portal | Continuous | HTML DB | Email; no API | Notices centralized | 30 d | EASY |
| VT | SOS Rules Service | Continuous | DB + PDF | None; NIC/Tyler | No (+LCAR) | ≥7 d post-hearing; hearing ≥30 d | MODERATE |
| NY | NYS Register | Weekly Wed | PDF | Email alert | No | **60 d** (SAPA §202) | MODERATE |
| NJ | NJ Register | Semimonthly Mon | LexisNexis + Dynamics DB | None | No | 30 d statutory / 60 d customary | HARD |
| PA | PA Bulletin | Weekly Sat | HTML + PDF | Bulletin email; IRRC subs | No (+IRRC email) | 30 d | EASY |

Caveats: (a) RI portal comment-submission mechanics unconfirmed page-level. (b) CT vendor attribution from OPM IT brief. (c) NH hearing-timing subsections partially verified.

### Mid-Atlantic: DE, MD, VA


### DELAWARE
1. **Register:** *Delaware Register of Regulations* — official, **monthly** (first of each month). Publisher: **Registrar of Regulations**, Division of Research of Legislative Council (General Assembly). Sources: https://regulations.delaware.gov/ ; legis.delaware.gov Registrar page.
2. **Format:** **Both HTML and PDF on a modern portal.** Current issue: regulations.delaware.gov/register/current_issue; per-issue landing slugs like /register/May2026. Individual notices are **structured HTML pages** (e.g. `/register/september2021/final/25 DE Reg 288 09-01-21.htm`). Full-issue PDFs via `/api/register/{Month}{Year}/{GUID}`. Legacy archive: archive.regulations.delaware.gov. Per-issue **Calendar of Events / hearing–comment calendar**, e.g. /register/June2026/calendar.
3. **Machine-readability:** `/api/register/...` shows an API-backed site but **no documented public API**. No register-specific RSS confirmed. Statewide **Delaware Notification Service** (email + statewide RSS feeds) at delaware.gov/guides/subscribe/ — Register-specific list [unverified]. Paid print $135/yr. State-run.
4. **Comments:** **No centralized portal.** Per-agency via mail/email/fax contact in each notice (e.g. DHSS_DMMA_Publiccomment@Delaware.gov; DOE runs its own comment page).
5. **Comment period:** **Minimum 30 days** after publication — **29 Del. C. § 10118(a)**; with hearings, written comment stays open ≥ **15 days after final hearing**. Sources: delcode.delaware.gov title29 c101.
6. **Ingestion: EASY.** Monthly cadence, predictable issue-landing URLs, per-notice structured HTML (not image PDFs), and the per-issue hearing/comment **calendar page is effectively a ready-made comment-deadline feed**. Friction: full-issue PDF GUIDs not guessable (scrape off issue page); 2023-era migration shows URL churn.

### MARYLAND
1. **Register:** *Maryland Register* — **biweekly (every other Friday)**, publisher: **Division of State Documents (DSD)**, Office of the Secretary of State. Confirmed 2026: Vol. 53 Iss. 1 – Jan 9, 2026. Sources: dsd.maryland.gov/Pages/MDRegister.aspx.
2. **Format:** Issues publish as **HTML "Assembled" pages** on SharePoint with predictable scheme `dsd.maryland.gov/MDRIssues/{VVII}/Assembled.aspx` (5310 = Vol 53 Iss 10). Free online but only **~15 most recent issues freely available** — older must be purchased. Paid: print $225/yr; annual "E-Version" emailed PDF sub. Companion free COMAR site: regs.maryland.gov. Legacy: dsd.state.md.us, 2019-dsd.maryland.gov.
3. **Machine-readability:** **No public API, no RSS/Atom/JSON, no bulk download.** Only paid subscription channels (phone-ordered). Useful structured artifact: **"Pertinent Dates for Each Issue" PDF** listing per issue the issue date and the date the 30-day comment period ends — https://dsd.maryland.gov/PDF/PertinentDates.pdf. State-run SharePoint.
4. **Comments:** **No centralized portal.** Oral/written to the proposing agency via the "Opportunity for Public Comment" contact block at the head of each notice in Proposed Action on Regulations.
5. **Comment period:** **Minimum 30 days** — Md. Code, State Government **§ 10-111(a)**: comment ≥ 30 days of the 45-day period following first publication (adoption not earlier than 45 days after publication); § 10-112 governs submission. APA-Regulations = SG Title 10, Subtitle 1.
6. **Ingestion: MODERATE.** Predictable `MDRIssues/{VVII}/Assembled.aspx` scheme, real HTML text, and PertinentDates.pdf hands you every issue's comment-close date in advance; but SharePoint markup is messy/unsemantic, only ~15 issues stay free (archive crawls), no feed/API, and DSD has re-platformed at least twice → poor URL stability over years.

### VIRGINIA
1. **Register:** *Virginia Register of Regulations* — **biweekly**, published by the **Virginia Code Commission** through the **Registrar of Regulations**, staffed by the **Division of Legislative Services (DLS)**; print edition produced under contract by Matthew Bender/LexisNexis. Statutory basis: Va. Code § 2.2-4031, Virginia Register Act (Title 2.2 ch. 41).
2. **Format:** Primary: **https://register.dls.virginia.gov/**. Issues as **PDF** ("the official Virginia Register is the PDF version") under fully predictable scheme `register.dls.virginia.gov/volXX/issYY/vXXiYY.pdf`, with HTML section/detail pages alongside (details.aspx?id=NNNN); volumes back to Vol 15. Companion: **Virginia Regulatory Town Hall, https://townhall.virginia.gov/** (Dept. of Planning and Budget) — DB of every executive-branch regulatory action, stage, meeting, comment.
3. **Machine-readability: BEST-IN-CLASS.**
   - **RSS 2.0 feed announcing each new Register issue** — subscribe page register.dls.virginia.gov/subscribe.aspx (exact feed XML URL [unverified]).
   - **Free Town Hall registration → nightly emails** on regulatory actions/meetings, scoped by secretariat, agency/board, or VAC chapter (townhall.virginia.gov/L/Register.cfm).
   - **Town Hall per-document XML views** (e.g. townhall.virginia.gov/L/ViewXML.cfm?textid=10951); no documented general public API.
4. **Comments: YES — CENTRALIZED PORTAL.** Town Hall hosts online **Public Comment Forums** (townhall.virginia.gov/L/Forums.cfm) — public submits comments directly on regulatory stages and guidance docs during open windows; comments post publicly. Closest state analogue of Regulations.gov. Written submittals to agency remain available per § 2.2-4007.03.
5. **Comment period:** **Minimum 60 days** for proposed regulations — **Va. Code § 2.2-4007.03** (Register publication ≥ 60 days in advance of last date for submittals). NOIRA stage carries a **30-day** comment period (§ 2.2-4007.01).
6. **Ingestion: EASY.** Town Hall is a stable DB-driven site with ID-keyed URLs (viewstage.cfm?stageid=NNNN), per-stage comment windows, nightly digests, XML views — track every action and deadline without touching the Register. Register adds issue-announcement RSS + fully predictable volXX/issYY PDF archive (text PDFs). Caution: Register official only in PDF; extract deadlines from Town Hall HTML instead.

**Summary:** DE = monthly, HTML+PDF, no portal, 30 days, EASY. MD = biweekly, free HTML (~15 issues) + paid PDF e-sub, no portal/feeds, 30 days, MODERATE. VA = biweekly PDF register + Town Hall portal with online comments, RSS + nightly email + XML, 60 days proposed / 30 NOIRA, EASY.

### Southeast: WV, NC, SC


**Constraint note:** egress proxy blocked direct fetches of state .gov hosts; facts verified via WebSearch retrieval of official-page content; unconfirmed items marked **[unverified]**.

### WEST VIRGINIA

**1. Register/bulletin:** **West Virginia State Register** (statutorily established 1982, repository of filings under W. Va. Code § 29A-2-3). Published by **WV Secretary of State, Administrative Law Division**. Cadence: **weekly, every Friday** (last business day in holiday weeks). Each issue includes the **Rule Monitor**, a table of all rules currently moving through promulgation.
Sources: https://sos.wv.gov/administrative-law/state-register/west-virginia-state-register ; https://sos.wv.gov/admin-law/Pages/StateRegister.aspx

**2. Format:** **PDF issues** listed by year in SOS "Online Data Services". Primary: **https://apps.sos.wv.gov/adlaw/registers/** (issues served via `apps.sos.wv.gov/adlaw/registers/readpdf.aspx?did=NNNN`, numeric doc-ID pattern, e.g. did=1523, did=30694). Companion searchable DBs: Code of State Rules at https://apps.sos.wv.gov/adlaw/csr/ ; Executive Journal at /adlaw/executivejournal/. In-house SOS platform, no vendor identified.

**3. Machine-readability:** **No public API, bulk-download, or RSS/Atom/JSON feed found.** `readpdf.aspx?did=` numeric IDs suggest enumerable doc store but no documented interface. Email subscription **[unverified]**; treat "no feed" as probable but unconfirmed.

**4. Comment submission:** **No centralized comment portal.** Comments **per-agency** (written to address/email in each notice, or at public hearing). WV wrinkle: most agency "legislative rules" cannot take effect without Legislature authorization after review by the **Legislative Rule-Making Review Committee** (W. Va. Code § 29A-3-9 et seq.) — comment phase precedes a legislative-approval phase. **[subsections unverified]**

**5. Comment period:** WV APA **W. Va. Code ch. 29A**; proposed-rule notice/comment provision **§ 29A-3-5** (code.wvlegislature.gov/29A-3-5/): comment period **not fewer than 30 days** after notice filed in State Register. **[30-day figure needs final text-check]**

**6. Ingestion assessment:** **MODERATE.** One predictable weekly Friday PDF behind stable numeric `did=` URLs, year-index page as discovery surface; text-based PDFs but deadlines live in Rule Monitor table and per-notice blocks → PDF table extraction. apps.sos.wv.gov ASP.NET app stable for years (URL scheme unchanged since early 2010s).

### NORTH CAROLINA

**1. Register/bulletin:** **North Carolina Register**, published by **NC Office of Administrative Hearings (OAH), Rules Division**. Cadence: **semimonthly (twice a month)** — confirmed by OAH 2026 publication schedule (https://www.oah.nc.gov/documents/rules/2026-publication-schedule/open); issue numbering e.g. Volume 40, Issue 13, Jan 2, 2026.

**2. Format:** **PDF issues.** Landing: **https://www.oah.nc.gov/rules-division/nc-register** (Drupal-based). Issue files hosted on state CDN at `files.nc.gov/oah/documents/{YYYY-MM}/Volume-NN-Issue-NN-Month-D-YYYY.pdf` **with S3-style `?VersionId=` query token**. NC Administrative Code separately browsable at http://reports.oah.state.nc.us/ncac.asp. Annual Rulemaking Calendar e.g. https://www.oah.nc.gov/2026-rulemaking-calendar/open.

**3. Machine-readability:** **No public API or RSS/Atom feed found.** `files.nc.gov` links carry `VersionId` tokens (break if re-uploaded) — hazard for hard-coded URLs. OAH has historically offered an **email distribution list for the NC Register** **[unverified]**. State Drupal + files.nc.gov CDN, no vendor.

**4. Comment submission:** **No centralized statewide portal.** Each Notice of Text names the agency rulemaking coordinator's mail/email and hearing details; comments **per-agency**. (Some large agencies, e.g., DEQ/DHHS, run their own comment pages **[unverified]**.) Post-comment: **Rules Review Commission** + G.S. 150B objection/legislative-review mechanics.

**5. Comment period:** NC APA **G.S. Chapter 150B**. **G.S. 150B-21.2(f)**: agency must accept comments **for at least 60 days** after publication of proposed text in the NC Register. **[confirm text at ncleg.gov]**

**6. Ingestion assessment:** **MODERATE.** Predictable cadence (published schedule PDF gives exact issue dates); text-based, consistently structured PDFs with standing "Notices of Text" section containing explicit comment-deadline lines — good for regex extraction after pdftotext. Pain points: VersionId-suffixed file URLs (scrape the index each cycle, don't construct URLs) and PDF parsing; oah.nc.gov Drupal index itself is clean HTML.

### SOUTH CAROLINA

**1. Register/bulletin:** **South Carolina State Register**, official publication and temporary update vehicle for the SC Code of Regulations. Published **monthly** by the **Legislative Council** (https://www.scstatehouse.gov/council.php). Filing deadline: 5:00 PM second Friday of each month. Sequence: **Notice of Drafting** → **Notice of Proposed Regulation** (with economic-impact estimate) → comment → final/legislative steps.
Sources: https://www.scstatehouse.gov/state_register.php ; /registerandregs.php ; 2025 Revised Standards Manual for Regulations PDF.

**2. Format:** **PDF issues**, free via SC Legislature Online. Primary: **https://www.scstatehouse.gov/state_register.php**. Highly regular query pattern: `state_register.php?first=FILE&pdf=1&file=Sr{volume}-{issue}.pdf` — e.g. Sr42-1.pdf (Vol 42 Iss 1, Jan 26 2018), Sr50-1.pdf (Vol 50, 2026 volume). Print also exists.

**3. Machine-readability:** **No public API, bulk download, or RSS/Atom/JSON feed found.** scstatehouse.gov email/tracking services cover *legislation* [Register coverage unverified]. No vendor platform. Third-party aggregators (e.g., StateScape, services.statescape.com) mirror issue PDFs — confirming no first-party feed practitioners rely on.

**4. Comment submission:** **No centralized comment portal.** Written comments **per-agency** to the address in the Notice of Drafting / Notice of Proposed Regulation; public hearings per § 1-23-110/§ 1-23-111. SC's unusual feature: most permanent regulations must be **submitted through the Legislative Council to the General Assembly for review/approval** (S.C. Code § 1-23-120, 120-day legislative review) before taking effect.

**5. Comment period:** SC APA **S.C. Code Title 1, Ch. 23 (§ 1-23-110 et seq.)**. **§ 1-23-110**: published notice must provide **not less than 30 days** for written comments; any public hearing **no sooner than 30 days** after notice appears (hearing required on request of 25 persons, a subdivision/agency, or association of 25+ members). **Verified** via statute-content search results (law.justia.com; scstatehouse.gov/code/t01c023.php).

**6. Ingestion assessment:** **MODERATE (leaning EASY).** Deterministic `Sr{vol}-{issue}.pdf` URL scheme stable 20+ years (volumes 25–50 observed live) + fixed monthly cadence → discovery trivial, pollable without scraping an index; work is parsing one text-based PDF per month whose Notices of Proposed Regulation contain 30-day comment deadlines in standardized preamble language. Low volume, no JS or session tokens; only fragility is PDF-layout drift.

**Cross-cutting:** none of the three has an API, feed, or centralized comment portal; all are PDF-register states (WV weekly, NC semimonthly, SC monthly) with per-agency comments. Statutory minimums: WV 30 days (§ 29A-3-5, confirm), NC 60 days (150B-21.2(f), confirm), SC 30 days (§ 1-23-110, verified).

### Southeast: GA, FL, KY


**Research constraint disclosure:** Direct fetches of rules.sos.ga.gov, flrules.org, legislature.ky.gov, and dos.fl.gov were blocked by the sandbox egress proxy (gateway 403 on CONNECT). Findings marked [verified] were confirmed via web-search result content; [unverified] items are from background knowledge and should be re-checked.

### GEORGIA

**1. Register/bulletin:** Georgia has **no official, state-published rulemaking register**. Compiled Rules and Regulations of the State of Georgia maintained online by the Secretary of State (rules.sos.ga.gov). The "**Georgia Government Register**" is an **unofficial LexisNexis publication** (monthly compilation of proposed/adopted rules, executive orders, AG opinions). Proposed-rule notices are distributed **per-agency**: under the Georgia APA, each agency mails/emails notice to persons who requested notice, posts on its own site, files with legislative counsel. **[unverified this session]**
- Sources: https://rules.sos.ga.gov/ ; https://sos.ga.gov/page/georgia-administrative-rules-regulations ; LexisNexis Georgia Government Register.

**2. Format:** rules.sos.ga.gov is searchable HTML database of compiled rules, historically **Lawriter/Casemaker** vendor platform (Casemaker merged into Fastcase/vLex). Publishes *codified* rules, not a notice stream. Proposed-rule notices on individual agency websites and mailing lists. **[unverified]**

**3. Machine-readability:** No public API, RSS/Atom feed, or bulk download known. Notification via **per-agency email/postal mailing lists** (APA requires agencies to maintain such lists). **[unverified]**

**4. Comment submission:** **No centralized comment portal.** Comments to each agency by email/mail or at hearings. **[unverified]**

**5. Comment period:** **30 days minimum** — O.C.G.A. § 50-13-4(a)(1): at least 30 days' notice of intended rulemaking before adoption, opportunity for written comment (oral hearing on request of 25+ persons under § 50-13-4(a)(2)). **[cite consistent with lead; text not fetched]**

**6. Ingestion assessment: HARD.** No single notice stream — deadlines live on dozens of separate agency sites/email lists with heterogeneous formats; SOS database covers only final codified rules on a vendor platform. A Georgia pipeline realistically means per-agency adapters or subscribing to agency mailing lists and parsing email.

### FLORIDA

**1. Register/bulletin:** **Florida Administrative Register (FAR)** — published **DAILY** (business days) by the **Florida Department of State** (Administrative Code and Register section). Carries proposed rules, emergency rules, notices of change/correction/withdrawal, hearings, petitions. **[verified via search-result content]**
- Sources: https://flrules.org/ ; https://dos.fl.gov/offices/administrative-code-and-register/ ; FAQ: https://flrules.org/Help/newHelp.asp

**2. Format:** **Searchable database/portal** at flrules.org (combined FAC/FAR "e-rulemaking" site). Notices/rules render as HTML under stable classic-ASP gateway URLs (e.g., `https://www.flrules.org/gateway/ruleno.asp?id=62-257.301` [verified pattern]). Daily FAR issues browsable by date; issue-download details **[unverified]**.

**3. Machine-readability:** **Free email notification subscription** for agency-submitted notices at **https://www.flrules.org/subscriber/signup.asp** **[verified via FAQ content]**. No public API, RSS, or documented XML feed found **[absence unverified by page-source inspection]**. flrules.org is state-run (not vendor-branded); unofficial mirror at flrules.elaws.us (eLaws vendor) [verified exists].

**4. Comment submission:** **No true centralized comment portal** — despite "eRulemaking" branding, comments go to the agency contact person named in each FAR notice (email/mail/hearing). **[unverified]**

**5. Comment period:** Florida APA **ch. 120, F.S.**; under **§ 120.54(3)(c)1** written comments within **21 days** after publication of notice of proposed rule (public hearing may be requested within 21 days); rule may be filed for adoption no sooner than 28 days after notice (§ 120.54(3)(e)2). **[cites consistent with lead; text not fetched]**

**6. Ingestion assessment: MODERATE (leaning EASY if past bot-blocking).** Best-structured stream of the three: daily, centralized, HTML notice database with stable query-string URLs and a proposed-rules section — highly scrapeable in principle. Caveats: 403s to non-browser fetchers this session (may require realistic headers/browser automation); classic-ASP table-heavy HTML. The free email subscription is a solid fallback channel (parse notification emails).

### KENTUCKY

**1. Register/bulletin:** **Administrative Register of Kentucky** — published **MONTHLY, 1st of each month**, by the **Legislative Research Commission (LRC)**. Contains regulations filed before prior month's deadline; official public notice of proposed regulations. Print subscription $120/yr (12 issues, July–June volume year). **[verified via legislature.ky.gov search content]**
- Source: https://legislature.ky.gov/Law/kar/Pages/Registers.aspx

**2. Format:** **PDF issues** with predictable URL pattern, e.g. `https://apps.legislature.ky.gov/law/kar/registers/51Ky_R_2024-25/12_June.pdf` (pattern: `/law/kar/registers/{volume}Ky_R_{yy-yy}/{issueNo}_{Month}.pdf`) **[verified from search results]**. PDF scans back to 1995 [verified]. LRC also maintains per-regulation HTML status pages under the KAR section **[unverified]**.

**3. Machine-readability:** **No public API, RSS/Atom feed, or bulk-download found**; distribution is the monthly PDF plus paid print. No rulemaking-specific e-notification confirmed **[unverified]**. LRC self-hosts, no vendor platform.

**4. Comment submission:** **No centralized comment portal.** Written comments to the agency contact person in each regulation's Register notice (email/mail), plus public hearing mechanism under KRS ch. 13A. **[unverified]**

**5. Comment period:** Kentucky APA **KRS ch. 13A**. Under **KRS 13A.270**, public hearing held during the calendar month following publication (no earlier than 21st day after publication), and **written comments accepted through the end of the calendar month following the month of publication** — effective window roughly 30–60 days. **[KRS 13A.270 amended recently; re-verify]**

**6. Ingestion assessment: MODERATE.** Centralized, low-frequency stream (one predictable PDF/month at a stable patterned URL) — easy to poll; hard part is text-extracting deadlines/hearings/contacts from a multi-hundred-page PDF (recent issues are born-digital text PDFs; pre-~2000 are image scans). Supplement with LRC per-regulation HTML status pages if they expose deadlines.

**Cross-cutting note:** every attempted direct fetch was 403'd at the egress gateway, so bot-blocking of flrules.org/rules.sos.ga.gov specifically could not be distinguished from proxy policy. Re-test scrapeability from an unrestricted network before finalizing EASY/MODERATE/HARD ratings.

### Southeast: TN, AL, MS


**Research note on verification limits:** The sandbox's egress proxy denied direct connections (CONNECT 403) to most state .gov hosts, and WebFetch received HTTP 403 (bot protection) from `sos.tn.gov`, `sos.ms.gov`, and `admincode.legislature.state.al.us`. Findings below are verified via web-search results quoting the official pages where possible; items not confirmed against a live page are marked **[unverified]**.

### TENNESSEE

**1. Register/bulletin:** Rulemaking filings are published by the **Tennessee Secretary of State, Division of Publications**. The historical **Tennessee Administrative Register** (monthly) has a page at https://sos.tn.gov/publications/services/administrative-register; current practice is that **Notices of Rulemaking Hearing** and rule filings are posted individually to the SOS website as filed, not in a periodical issue **[cadence of the legacy Register vs. current rolling notices: partially unverified]**. Verified: notices of rulemaking hearings "are posted to the website to give official notice for the time, date, and location of a hearing," with the text of proposed rules included in the notice (source: https://sos.tn.gov/publications/services/file-rules-and-notices and https://sos.tn.gov/publications).

**2. Format:** Individual notice/rule filings posted as **PDF documents**; file hosting on `publications.tnsosfiles.com` and `sos-tn-gov-files.tnsosfiles.com`. A legacy HTML listing of rulemaking-hearing announcements exists at **https://tnsos.org/rules/RulemakingHearings.php**. Primary URLs: https://sos.tn.gov/publications and https://sos.tn.gov/publications/services/administrative-register. **[Exact current listing-page structure unverified — 403.]**

**3. Machine-readability:** **No public API, bulk download, or RSS/Atom feed found**. Filings accepted by email (publications.information@tnsos.gov); no public e-notification subscription confirmed. **[Absence checks incomplete due to 403s.]**

**4. Comment submission:** **No centralized comment portal**. Comments go **per-agency** — via the rulemaking hearing itself or contact information listed in each notice.

**5. Comment period:** TN APA is **T.C.A. § 4-5-201 et seq.** Verified via SOS filing guidance: **rulemaking-hearing notice must be posted at least 45 days before the hearing**; SOS requires filing 52 days prior (45 statutory + 7 processing). The 45-day notice window functions as the public-input period. **[Exact statutory cite — T.C.A. § 4-5-203/204 — unverified.]**

**6. Ingestion assessment:** **HARD.** SOS site blocks non-browser fetchers (403), notices are unstructured PDF filings on a separate file-CDN domain (`tnsosfiles.com`), no feed or API; legacy `tnsos.org` PHP listing may be more scrapeable but currency unconfirmed. Expect headless-browser scraping plus PDF parsing.

### ALABAMA

**1. Register/bulletin:** **Alabama Administrative Monthly**, published by the **Legislative Services Agency (LSA)** (moved from SOS to LSA), **monthly — last business day of each month**. Each notice "includes a description of the substance of the proposed rule changes, specifies a comment period, and provides the manner in which a member of the public may submit comments to the agency." Also lists adopted rules certified during the prior month. (Source: https://admincode.legislature.state.al.us/administrative-monthly.)

**2. Format:** Monthly issues as **PDF** served from the site's API with predictable URL pattern: **`https://admincode.legislature.state.al.us/api/aam/YYYY-MM`** (verified: /api/aam/2026-04 — "VOLUME XLIV, ISSUE NO. 7, April 30, 2026"; /api/aam/2025-09). Landing: https://admincode.legislature.state.al.us/administrative-monthly. Individual filings at `https://admincode.legislature.state.al.us/api/filing/{id}/filing` (verified example: /api/filing/689e16196eab826bcf3c9232/filing); resources at `/api/resource/...`.

**3. Machine-readability:** Modern web app with **undocumented but publicly reachable backend HTTP API (`/api/aam/`, `/api/filing/{mongo-style-id}/filing`, `/api/resource/`)**, stable guessable per-month issue URLs. **No documented public API, RSS/Atom feed, or email subscription found.** **[Feed absence unverified — 403 bot protection on direct fetch.]** Platform appears LSA-run, no vendor branding.

**4. Comment submission:** **No centralized portal.** Each notice specifies its own comment period and manner of submitting comments **directly to the proposing agency**.

**5. Comment period:** Alabama APA: **Code of Ala. § 41-22-1 et seq.**; intended-action notice/comment provision **§ 41-22-5**, commonly summarized as at least a **35-day** window. **[35 days is the known lead, statute text unverified.]**

**6. Ingestion assessment:** **MODERATE.** `/api/aam/YYYY-MM` URL pattern stable and enumerable (one PDF per month, fixed schedule) — polling trivial — but issues are PDFs requiring text extraction for per-notice comment deadlines, and the site fronts requests with bot protection (may require realistic headers or headless browser). Undocumented `/api/filing/` endpoints hint at structured per-filing data worth probing.

### MISSISSIPPI

**1. Register/bulletin:** **Mississippi Administrative Bulletin**, published by the **Mississippi Secretary of State** (official registrar of all state-agency rules). Cadence **event-driven**: updated "as needed within two (2) business days of the filing of notice of a proposed rule adoption, notice of adoption of an emergency rule, or notice of adoption of final rule." (Sources: https://www.sos.ms.gov/regulation-enforcement/administrative-code/administrative-bulletin; SOS Administrative Procedures FAQs.) Bulletin organization codified at 1 Miss. Code R. § 1-2.1 and § 1-2.3 (Cornell LII).

**2. Format:** **Searchable online database/portal** (ASP.NET): **https://www.sos.ms.gov/adminsearch/default.aspx?current_page=Bulletin** — search proposed-for-comment and adopted-not-yet-effective rules. Underlying filings are PDFs **[inferred, unverified]**.

**3. Machine-readability:** **No public API, RSS/Atom feed, or bulk download found.** Classic ASP.NET WebForms app. **[Prior-knowledge lead, unverified: adminsearch has offered email-notification signup for rule filings by agency.]** No vendor platform identified.

**4. Comment submission:** **No centralized comment portal.** Comments submitted **to the proposing agency** as specified in each notice; APA provides for public-comment hearings (agency must wait 20 full calendar days after hearing notice published in Bulletin).

**5. Comment period:** MS APA: **Miss. Code Ann. § 25-43-1.101 et seq.** (Model APA-based). Verified via SOS FAQ: agency "must wait **twenty-five (25) days** from the time notice of your proposed rules is filed in the Administrative Bulletin to file your rules as final" — **25-day minimum**, per **Miss. Code Ann. § 25-43-3.106** **[section number is known lead; FAQ confirms 25-day figure]**.

**6. Ingestion assessment:** **HARD.** Notice stream lives inside an ASP.NET WebForms search portal (postback-driven, session-state-heavy, unstable result URLs), SOS domain blocks non-browser clients (403), filings are PDFs; event-driven "within 2 business days" cadence means frequent polling via headless browser plus PDF parsing to capture the 25-day comment clocks.

**Sources:** TN SOS Publications | TN Administrative Register page | TN File Rules and Notices | TN legacy hearing announcements (tnsos.org/rules/RulemakingHearings.php) | TN Rulemaking Guidelines PDF | Alabama Administrative Monthly | AL AAM 2026-04, 2025-09 issues | AL APA overview resource | UA Law guide | MS Administrative Bulletin portal | MS SOS Administrative Procedures + FAQs | MS Bulletin rule, Cornell LII

### Midwest: OH, IN, IL


**Constraint note:** outbound proxy denies CONNECT to state .gov hosts (registerofohio.state.oh.us, iar.iga.in.gov, ilsos.gov, ilga.gov all 403 at gateway); facts verified via web-search snippets of official pages; direct page-internal verification (e.g., RSS link tags) not possible.

### OHIO

**1. Register/bulletin:** **Register of Ohio**, published by the **Ohio Legislative Service Commission (LSC)** since July 3, 2000 ("Register of Ohio Act"). Electronic-only "gazette" — **continuously updated** as agencies e-file rules (no periodic issues). Source: https://www.registerofohio.state.oh.us/about/about-the-register

**2. Format:** Online searchable database at https://www.registerofohio.state.oh.us/ (paths like /rules/search). Rule filings (proposed text, public-hearing notices, RSFAs, Business Impact Analyses) served as **PDFs via stable servlet endpoints**: `https://www.registerofohio.state.oh.us/servlet/RooBusinessPDF?ruleActionId=NNNNNN&docTypeId=NN`. Agencies file through Electronic Rule Filing (ERF) at erf.registerofohio.state.oh.us / filers.registerofohio.state.oh.us.

**3. Machine-readability:** **No public API, RSS/Atom feed, or bulk download found** (searched specifically). State-run (LSC), not vendor-hosted. E-notification only per-agency (e.g., ODH draft-rule e-notification under OAC 3701-51-01). CSI posts rules open for comment on the Governor's site. [Homepage feed-link inspection not possible — proxy block.]

**4. Comment submission:** No centralized Regulations.gov-style portal. Comments **per-agency** (hearing testimony/email per ORC 119.03 notice). Parallel business-impact track: **Common Sense Initiative (CSI)** under Governor/Lt. Governor posts BIA'd rules for comment; comments to CSIPublicComments@governor.ohio.gov (https://governor.ohio.gov/priorities/common-sense-initiative). JCARR does legislative review, not public comment intake.

**5. Comment period:** **ORC 119.03**: public notice in Register of Ohio ≥ 30 days before hearing; hearing must fall on 31st–40th day after filing — effectively minimum ~30-day comment window before hearing. Cite: ORC 119.03(A),(C), https://codes.ohio.gov/ohio-revised-code/section-119.03

**6. Ingestion assessment:** **MODERATE** — database-driven site with stable parameterized PDF endpoints (ruleActionId/docTypeId) and a single statewide chokepoint, but no feed/API: ingestion means scraping the POST-driven servlet/JSP search interface and parsing PDFs for hearing dates.

### INDIANA

**1. Register/bulletin:** **Indiana Register**, published by the Indiana Register and Administrative Code Division, Office of Code Revision, **Legislative Services Agency (LSA)**. Print monthly 1978–2006; **electronic-only since July 2, 2006**. Effectively continuous/weekly: documents get dated DINs (e.g., 20250625-IR-760250322NRA) with Wednesday dates — weekly Wednesday posting batch.
Sources: https://iar.iga.in.gov/register ; legacy http://iac.iga.in.gov/iac/irtoc.htm

**2. Format:** **HTML database portal.** New LSA platform "Indiana Administrative Rules and Policies" (IARP) at https://iar.iga.in.gov/ — register list at /register, individual docs at /register/{DIN} (HTML). Legacy archive at iac.iga.in.gov/iac/irtoc.htm. Some agencies mirror filings as PDFs on in.gov.

**3. Machine-readability:** **No RSS/Atom feed, public API, or bulk download found.** No statewide e-notification; agencies file by emailing register@iga.in.gov. State-run (LSA/IGA IT). [IARP is a modern web app and may have undocumented JSON XHR endpoints worth probing from an unblocked network.]

**4. Comment submission:** No centralized portal. Post-HEA 1623 process: agency's **Notice of First Public Comment Period** (published in the Register) solicits comments directly to the agency, plus public hearing under IC 4-22-2-26. OMB coordinates executive-branch review dashboards, not public comments.

**5. Comment period:** **IC 4-22-2-23** (Notice of First Public Comment Period, rewritten by HEA 1623-2023) with IC 4-22-2-26: publication ≥ 30 days before public hearing — minimum ~30-day first comment period. Interim rules: 30-day comment period, IC 4-22-2-37.2(e). HEA 1623 (2023) eliminated old Notice of Intent and newspaper publication; applies to filings after June 30, 2023.

**6. Ingestion assessment:** **EASY** (best-in-group): native HTML with globally unique, date-prefixed DIN identifiers and predictable per-document URLs (iar.iga.in.gov/register/{DIN}); notice types encoded in DIN suffix (…NRA, …FNA) → a weekly scrape of the register list can classify first-comment-period notices without PDF parsing. Risk: 2024-era platform migration (iac.iga.in.gov → iar.iga.in.gov) shows URLs can churn.

### ILLINOIS

**1. Register/bulletin:** **Illinois Register**, published **weekly (Fridays)** by the **Illinois Secretary of State, Index Department** (Administrative Code Division, Springfield). Volume 50 (2026).
Sources: https://www.ilsos.gov/departments/index/register.html

**2. Format:** **Weekly PDF issues.** Current + archive at ilsos.gov/departments/index/register.html and /archive.html, issue PDFs at predictable paths like `https://www.ilsos.gov/content/dam/departments/index/register/volume50/register_volume50_20.pdf`. Complementary HTML: **JCAR** (Joint Committee on Administrative Rules, https://www.ilga.gov/agencies/jcar) maintains searchable IL Administrative Code / rulemaking database on ilga.gov.

**3. Machine-readability:** **No API, RSS feed, or bulk-data service found.** Paid print/mail subscription via Index Department; generic ilsos.gov newsletter-subscribe app but no Register-specific e-notification confirmed. Best notice stream: **JCAR's Flinn Report** — free weekly PDF newsletter summarizing each week's Register rulemakings, posted Fridays at ilga.gov (kept online ~6 months). All state-run (SOS + ILGA).

**4. Comment submission:** No centralized portal. Each First Notice names an agency contact for written comments during the 45-day period; comments per-agency by mail/email, optional hearings. JCAR receives Second Notice filings for legislative review, not public comments.

**5. Comment period:** **5 ILCS 100/5-40(b)** (Illinois APA): **at least 45 days' First Notice**, commencing the day notice appears in the Illinois Register; rulemaking lapses if not adopted within one year of First Notice. Cite: ilga.gov fulltext 000501000K5-40.

**6. Ingestion assessment:** **MODERATE** — reliable weekly cadence and predictable volume/issue URL paths, but the Register is a large weekly text-based PDF; comment deadlines must be extracted from PDF section text (or computed as First Notice date + 45 days). Flinn Report PDF is a cleaner weekly digest but PDF and only ~6-month retention; JCAR's ilga.gov database offers HTML for proposed rulemakings.

**Verdict all three:** no APIs, no RSS, no bulk data; ingestion = scheduled scraping (OH: servlet DB + PDFs; IN: clean HTML w/ DIN IDs; IL: weekly PDFs).

### Midwest: MI, WI, MN


### MICHIGAN
1. **Register:** *Michigan Register*, publisher: Administrative Rules Division (ARD) of Michigan Office of Administrative Hearings and Rules (MOAHR), within LARA. **Cadence: twice monthly** (1st & 15th; confirmed 2026 issues). Contains all proposed rules, hearing notices, rules filed with SOS. Source: michigan.gov/lara/bureau-list/moahr/admin-rules/publications/michigan-register
2. **Format:** **PDF issues**, predictable naming `MR{issue}_{MMDDYY}.pdf` e.g. .../ARD/2026-Michigan-Register/MR12_071526.pdf (text-based). Complementary **ARS portal** — searchable DB of every active rule set/transaction with per-rule-set pages and downloadable docs (hearing notices, RFRs, written-comment packets): https://ars.apps.lara.state.mi.us/ (doc endpoint `Transaction/DownloadFile?FileName=...&TransactionID=...`).
3. **Machine-readability:** No public API, no RSS/JSON/XML feed. **GovDelivery email alerts** for rulemaking (content.govdelivery.com/MIEOG). ARS is state-built ASP.NET; Register PDFs on michigan.gov Sitecore media CDN.
4. **Comments:** No centralized portal. Per-agency — written comments to address/email in each Notice of Public Hearing, or orally at hearing; ARS publishes notices and received comment packets but doesn't accept comments.
5. **Comment period:** APA of 1969, MCL 24.201 et seq. MCL 24.241 (opportunity to present views), MCL 24.242 (hearing notice **not less than 10, not more than 60 days** before hearing; must appear in Register before hearing). **No standalone statutory minimum written-comment window** — floor is the ≥10-day hearing notice; deadline set per notice.
6. **Ingestion: MODERATE.** Twice-monthly text PDF with predictable URL pattern but Sitecore paths have shifted on redesigns. Better stream: ARS server-rendered HTML queryable by department/status with per-transaction hearing/comment dates — scrapeable but query-parameter-heavy, undocumented. GovDelivery email as change trigger.

### WISCONSIN
1. **Register:** *Wisconsin Administrative Register*, publisher: **Legislative Reference Bureau (LRB)** under Wis. Stat. § 35.93. **Cadence: weekly**, plus end-of-month "B" Register with final rulemaking orders and updated Code chapters (monthly numbering with lettered parts, e.g. 844A1, 844B; 2026 = registers 841–852). Source: https://docs.legis.wisconsin.gov/code/register
2. **Format:** **Structured HTML** on the Legislature's document site with PDF renditions; stable URL scheme `docs.legis.wisconsin.gov/code/register/{year}/{issue}/register/...`. Search: docs.legis.wisconsin.gov/search/register.
3. **Machine-readability:** No documented public API or bulk download. **Free email notifications** of rulemaking activity via the Legislature's site (per Marquette Law guide). State-run (LRB/LTSB); consistent URL conventions = de facto structured source.
4. **Comments: CENTRALIZED-ish (unusual).** Statewide "Wisconsin Administrative Rules Website" (historically adminrules.wisconsin.gov) built to route comments to agency rule coordinators; current practice: each proposed rule/hearing entry on docs.legis.wisconsin.gov/code carries a "Submit Electronic Feedback / public comment" link+form (Marquette guide: "Comments on proposed administrative rules are accepted through the Legislature's website"). Caveat: adminrules.wisconsin.gov failed DNS from this environment July 2026 — treat docs.legis links as operative portal. Agencies also accept comments directly.
5. **Comment period:** Wis. Stat. ch. 227. Hearings generally required (§ 227.16); **hearing notice ≥ 10 days before hearing**, deemed given on Register publication date (§ 227.17(1)). **No fixed statutory minimum for written-comment window**; deadline set in each hearing notice. Preliminary comment at scope-statement stage under § 227.135/227.136.
6. **Ingestion: EASY.** Weekly Register in clean stable predictable HTML on a legislative platform with a decade-stable URL scheme; hearing notices and comment deadlines as structured HTML; per-rule tracking pages (clearinghouse rule numbers CR YY-NNN) give durable identifiers. Poll weekly issue index + free email notifications.

### MINNESOTA
1. **Register:** *Minnesota State Register*, publisher: **Minnesota Department of Administration** (mandated by Minn. Stat. § 14.46). **Cadence: weekly — every Monday** (Tuesday on holidays). Contains proposed/adopted/exempt/expedited-emergency/withdrawn rules, Requests for Comments, official notices, executive orders, contracts/grants. Source: https://mn.gov/admin/bookstore/register.jsp
2. **Format:** **Weekly PDF issues** (accessible/tagged, text-based, e.g. SR46_35), free at mn.gov/admin/bookstore/register.jsp (asset URLs like /assets/SR46_35%20-%20Accessible_tcm36-519638.pdf — unpredictable). **Full historical archive with stable URL scheme** at the Revisor: `https://www.revisor.mn.gov/state_register/{volume}/{issue}/`. No HTML edition.
3. **Machine-readability:** No public API, no RSS/JSON feed. **Email delivery is a PAID subscription** (~$180/yr "State Register Online", Friday-afternoon early view). Comment platform vendor-hosted on **Granicus** ("Granicus Ideas"): https://minnesotaoah.granicusideas.com/ — per-discussion HTML pages, no documented API.
4. **Comments: SEMI-CENTRALIZED.** **Rulemaking eComments** run by the Office of Administrative Hearings (**renamed Court of Administrative Hearings (CAH) as of 2026**) at minnesotaoah.granicusideas.com (info: mn.gov/oah/forms-and-filing/ecomments/). Agencies **must** use eComments for post-hearing comment periods; **may** (increasingly do) use it for the 60-day RFC period and 30-day proposed-rule comment period; comments also accepted by mail/eFiling/delivery/fax. Otherwise comments go to the agency contact in the State Register notice.
5. **Comment period:** Minn. Stat. ch. 14. **Request for Comments: ≥ 60 days** before notice of intent to adopt (§ 14.101). **Rules without hearing (dual notice): 30-day minimum** comment after notice of intent to adopt; 25+ hearing requests force a hearing (§ 14.22, § 14.25). Rules with hearing: notice ≥30 days before hearing + post-hearing comment/rebuttal (§§ 14.14–14.20). Practical minimum: **30 days**.
6. **Ingestion: MODERATE.** Single weekly PDF, reliable cadence, consistent section headings with explicit comment-end dates; Revisor archive gives stable enumerable URLs, but current-issue asset URLs (_tcm36-…) unpredictable → scrape index page. Text-based PDFs, tractable extraction; supplement by scraping Granicus eComments discussion list (simple HTML with open/close dates).

**Env note:** sandbox egress proxy blocks direct HTTPS to many state .gov hosts — adapter dev needs allowlisting for michigan.gov, docs.legis.wisconsin.gov, mn.gov, revisor.mn.gov, ars.apps.lara.state.mi.us, minnesotaoah.granicusideas.com.

### Midwest: IA, MO, NE


**Caveat:** egress proxy denied CONNECT to state .gov hosts; facts verified via WebSearch result content. **[MC]** = medium confidence.

### IOWA
1. **Register:** **Iowa Administrative Bulletin (IAB)** — **biweekly**, published by the **Administrative Code Office of the Legislative Services Agency (LSA)**. Current in 2026 (Vol. XLVIII, 2026-04-15 issue). Post-EO 10 (Reynolds, Jan 2023 red-tape review), executive branch also runs **rules.iowa.gov** ("State of Iowa Administrative Rules Website") — rule-tracking and public-comment portal under Dept. of Management / Administrative Rules Coordinator [MC]. Both coexist: IAB is official publication; rules.iowa.gov is comment/tracking front-end.
2. **Format:** Dual. IAB = **PDF issues at stable date-patterned URLs** (`legis.iowa.gov/docs/aco/bulletin/MM-DD-YYYY.pdf`); index at /law/administrativerules/bulletinsupplementlistings; IAC at /law/administrativeRules/agencies. rules.iowa.gov = HTML portal listing open-comment rulemakings.
3. **Machine-readability:** No public API. **Email: "Bills & Rules Watch"** at legis.iowa.gov/subscribe — subscribe by agency to rulemaking actions and IAC chapter publications, selectable frequency. No RSS. State-hosted.
4. **Comments: CENTRALIZED portal — rules.iowa.gov** accepts online comments on all rules in the Notice process ("20 days to comment from date of publication"). Written comments/oral presentation requests to agencies also remain.
5. **Comment period:** Minimum **20 days** written submissions after Notice of Intended Action publication — **Iowa Code § 17A.4(1)(b)**; notice ≥ **35 days** before contemplated action (§ 17A.4(1)(a)).
6. **Ingestion: MODERATE (leaning easy).** Biweekly text-based PDFs at fully predictable dated URLs — trivial to poll; rules.iowa.gov lists open-comment rulemakings with deadlines in HTML (likely best deadline source; markup uninspected). Complexity: reconciling two parallel sources.

### MISSOURI
1. **Register:** **Missouri Register** — **semi-monthly** (~1st and 15th/16th, business-day adjusted; Vol. 51 No. 3 = Feb 2, 2026) by the **Secretary of State, Administrative Rules Division**. Publication schedule: sos.mo.gov/adrules/pubsched.
2. **Format:** **PDF issues** (whole + per-section) indexed from sos.mo.gov/adrules/moreg/moreg, files under `sos.mo.gov/CMSImages/AdRules/moreg/YYYY/vXXnY.../`. Plus **searchable Register database**: sos.mo.gov/adrules/search/queryReg. CSR at /adrules/csr/csr. Paper copy remains official.
3. **Machine-readability:** No API, no RSS. **Account-based email notification system: "Administrative Rules Notifications"** — sos.mo.gov/adrules/notifications (app at s1.sos.mo.gov/adrules/notifications/). State-hosted.
4. **Comments:** **No centralized portal.** Per-agency: each Notice of Proposed Rulemaking specifies place, manner (mail/email to agency contact), deadline, hearing details. (RSMo 536.021.)
5. **Comment period:** **Not less than 30 days** after publication — **RSMo § 536.021** (statements filed ≥ 30 days after publication; hearings ≥ 30 days after publication).
6. **Ingestion: MODERATE.** Predictable semi-monthly cadence, text-based PDFs; `CMSImages` paths vary in casing/naming → scrape index rather than construct URLs. Deadlines parsed from per-notice PDF text; search DB form-driven, no query API. Email notifications = usable change trigger.

### NEBRASKA
1. **Register:** **No traditional register/bulletin exists.** Notice = (a) newspaper legal notice statewide + (b) continuous posting to the **SOS Proposed Rules & Regulations Docket** (rules tracking system), run by SOS Regulations Division. Cadence: continuous.
2. **Format:** **rules.nebraska.gov** — searchable HTML library (Search, Browse by Agency, Proposed Docket). Legacy tracking system is **CGI-generated HTML** at nebraska.gov/nesos/rules-and-regs/regtrack/ (detail pages `details.cgi?proposal_id=NNNN`), hearing notices and proposed text as **PDFs** under `/regtrack/proposals/NNNN.pdf` — **a meaningful share are scanned/image PDFs** (OCR-garbage text confirmed).
3. **Machine-readability:** No API, no RSS. **Email subscription built into the docket**: single rule, all of one agency's, or **all proposed rules statewide**. Portal operated by Nebraska Interactive (NIC/Tyler Technologies) [MC].
4. **Comments:** **No mandatory central portal.** Primary input at the statutorily required **public hearing**; agencies **may optionally enable online comments** in the tracking system; otherwise written comments direct to agency.
5. **Comment period:** No standalone written-comment minimum — operative requirement is **30 days' advance notice of the public hearing** (Neb. Rev. Stat. § 84-907; § 84-907.06 hearing notice + draft to Legislative Council Exec Board and SOS ≥ 30 days before hearing). Post-hearing: AG review, Governor policy review/approval (§§ 84-133, 84-135); rules effective 5 days after filing with SOS.
6. **Ingestion: HARD.** No register to poll; deadline signal is a hearing date in CGI HTML detail pages and attached notice PDFs, many image scans needing OCR; comment mechanics vary by agency. Statewide docket email subscription = most reliable trigger; scraping docket index + details.cgi pages feasible but brittle.

### Midwest: ND, SD, KS


### NORTH DAKOTA
1. **Register:** **No traditional register.** Hearing/comment notices published in official county newspapers and filed with the **Legislative Council**, which posts them online (N.D.C.C. 28-32-10; AG Administrative Rules Manual). Adopted changes appear in the **North Dakota Administrative Code Supplement**, published **QUARTERLY** by Legislative Council (Supplement 400 = July 2026; ndlegis.gov/administrative-rules-supplements).
2. **Format:** Notice PDFs at `ndlegis.gov/sites/default/files/rule-changes/notices/{agency}{date}notice.pdf`; adopted-changes PDFs under /files/rule-changes/changes/; hearings also as HTML event pages and an Agency Rules Calendar. Primary URL: https://ndlegis.gov/agency-rules.
3. **Machine-readability:** **RSS feeds exist, including one for rules notices/proposed changes** (ndlegis.gov/legislative-branch-rss-feed). No API or bulk download. Agencies must also mail/email notice on request (28-32-10). Self-hosted.
4. **Comments:** No central portal; per-agency mail/email/hearing, addresses in each notice PDF (e.g. omb020926notice.pdf — hearing Feb 9, 2026, comments due Feb 19, 2026).
5. **Comment period:** N.D.C.C. ch. 28-32: **28-32-10(5)** — ≥ 20 days between last notice publication and hearing; **28-32-11** — comment stays open ≥ 10 days after hearing (effective minimum ~30 days).
6. **Ingestion: MODERATE.** Stable guessable notice-PDF URL pattern + RSS, but **many notices are scanned image PDFs (OCR needed)**; HTML events calendar cleaner secondary signal for hearing dates.

### SOUTH DAKOTA
1. **Register:** **South Dakota Register**, **WEEKLY**, **Legislative Research Council**, per SDCL 1-26A-1 (mastheads confirm; e.g. mylrc.sdlegislature.gov/api/Documents/Register/304540.pdf?Year=2026).
2. **Format:** PDF issues listed at https://sdlegislature.gov/Rules/Register, served from `mylrc.sdlegislature.gov/api/Documents/Register/{docId}.pdf?Year={YYYY}`. Current proposed-rule notices also on **https://rules.sd.gov** (PDFs at `rules.sd.gov/Uploads/{id}_PublicNotice.pdf`; **removed after deadline**; archive at /archive.aspx).
3. **Machine-readability:** sdlegislature.gov is an SPA on the open (undocumented) **mylrc.sdlegislature.gov/api REST endpoint — de facto document API**. Email delivery of Register via My LRC+ accounts. No RSS on rules.sd.gov; no documented public API.
4. **Comments:** Closest to a Regulations.gov equivalent of the three: **rules.sd.gov accepts written comments ONLINE** on proposed rules (Register notices direct commenters there; name/city/state required). Agencies also take mail/email + hearings.
5. **Comment period:** SDCL ch. 1-26: **1-26-4** — notice ≥ 20 days before hearing (published per 1-26-4.1 incl. the Register); **written comments must arrive ≥ 72 hours before the hearing** — effective written window ~17 days. Register mandated by SDCL 1-26A-1.
6. **Ingestion: MODERATE.** rules.sd.gov is the best live feed of open comment windows (small HTML list + predictable Upload PDF URLs) but **deletes notices after deadlines — continuous polling required**; Register PDFs text-based but docIds unpredictable without scraping the SPA/API.

### KANSAS
1. **Register:** **Kansas Register**, official state newspaper, **WEEKLY every Thursday** (52 issues/yr), published by the **Secretary of State** under K.S.A. 75-430.
2. **Format:** **BOTH HTML and PDF** — full-issue PDFs plus **each notice as its own HTML page** with stable volume/issue URLs, e.g. `sos.ks.gov/publications/Register/Volume-45/Issues/Issue-20/05-14-26-54174.html`. "In-process" regs open for comment: https://sos.ks.gov/publications/pubs_kar_inprocess.aspx.
3. **Machine-readability:** No API, no RSS. **Official email subscription for proposed-regulation/hearing notices, filterable by agency**: sos.ks.gov/publications/pubs_kar_subscription.aspx. Self-hosted ASP.NET. Editor: kansasregister@ks.gov.
4. **Comments:** No central portal — K.S.A. 77-421 notice gives the agency address for written comments; per-agency mail/email + public hearing. In-process page centralizes discovery only.
5. **Comment period:** **K.S.A. 77-421**: ≥ **60 days' notice** in the Kansas Register, and that 60-day notice period **expressly constitutes the public comment period** — statutory minimum **60 days**.
6. **Ingestion: EASY.** Individual dated HTML notice pages under predictable /publications/Register/Volume-{v}/Issues/Issue-{n}/ hierarchy plus a single always-current in-process index. Caveats: no feed/API (scrape index or email sub); hostname historically alternated sos.ks.gov ↔ kssos.org.

### South-Central & Mountain: TX, OK, AR, LA, MT, ID, WY, CO, NM, UT, AZ, NV


### TEXAS
1. *Texas Register* — Texas Secretary of State (Texas Register Division), Gov't Code ch. 2002. **Weekly, every Friday**, posted online by 5 p.m. CST. (sos.state.tx.us/texreg/index.shtml)
2. **Both HTML and PDF.** HTML archive back to Jan 28, 2000 (/texreg/archive/), PDF back issues (/texreg/pdf/backview/). Complete historical run to 1976 on UNT's Portal to Texas History (texashistory.unt.edu — has OAI-PMH/API as bonus archival source).
3. No official API or RSS. **Email notification**: register@sos.texas.gov — notified when each issue posts; can cover open meetings, RFPs, hearing notices, filtered by agency.
4. **No central portal.** Comments to the agency contact named in each proposal preamble (HHSC, TEA run their own comment pages).
5. Minimum **30 days** — no adoption earlier than 30 days after Register publication; Tex. Gov't Code § 2001.029 with § 2001.033/2001.023 (TEA describes ~31 calendar days).
6. **Ingestion: EASY.** Weekly, stable predictable URLs, structured HTML issues (preambles contain deadlines) 25+ years back, parallel PDFs. No feed — Friday-evening poller of issue index; HTML old-school but consistent.

### OKLAHOMA
1. *The Oklahoma Register* — **Office of Administrative Rules (OAR), Oklahoma SOS**, 75 O.S. §§ 250 et seq. **Semi-monthly**: first working day of month and first working day after the 14th.
2. PDF issues + searchable portal. Primary: **https://rules.ok.gov** (Registers at /registers; Code in HTML at /code). Issue PDFs on Azure blob: `oklahomarules.blob.core.windows.net/publicregister/Volume-42_Issue-5.pdf`.
3. No public API or RSS. Portal **email subscription** (rules.ok.gov/subscriptionLogin) for agency rulemaking activity. State-built modernization (e-filing to Governor/Legislature/SOS).
4. No true central comment portal; rules.ok.gov lists proposed rules open for comment but comments submitted **per-agency** per each Notice of Rulemaking Intent ("COMMENT PERIOD:" block).
5. Minimum **30 days** from NRI publication — 75 O.S. § 303.
6. **Ingestion: MODERATE.** Semi-monthly text PDFs, predictable blob URLs; portal "open for comment" listing scrapeable HTML but deadlines inside NRI text. No feed/API; email sub needs account.

### ARKANSAS
1. *Arkansas Register* — **monthly**, **Arkansas SOS**. ACA § 25-15-218: SOS publishes all rule notices, emergency/proposed/adopted rules + financial impact statements online.
2. Monthly PDF compilations (2001–present, full-text search of final rules) + searchable rules DB at **sos-rules-reg.ark.org/rules/search** (ark.org platform, Information Network of Arkansas/NIC — vendor-hosted). Proposed filings as scattered individual PDFs.
3. SOS advertises **Bulk Data Download** page (sos.arkansas.gov/rules-regulations/bulk-data-download — existence confirmed; contents/format UNVERIFIED). No RSS/API; no statewide e-notification (agencies keep own advance-notice mailing lists under § 25-15-204).
4. **Per-agency.** Notice states time/place/manner; oral hearing on request of 25 persons. No central portal.
5. Minimum **30 days** — ACA § 25-15-204: ≥30 days' notice from first publication; final rule not filed until 30-day comment period expires; SOS posts notice online 30 days.
6. **Ingestion: MODERATE-HARD.** No single dated notice stream: scattered PDF uploads + vendor search app (session-y URLs); monthly Register is a backward-looking compilation of adopted rules. Bulk-download endpoint could upgrade to MODERATE if it covers proposed filings.

### LOUISIANA
1. *Louisiana Register* — **Office of the State Register (OSR), Division of Administration**. **Monthly, on the 20th**; all Notices of Intent, final rules, emergency rules, executive orders from prior month.
2. PDF issues at doa.la.gov/doa/osr/louisiana-register/ (free; OSR certifies each issue). LAC online at /louisiana-administrative-code/.
3. No API or RSS. **Email listserv**: "Subscribe" to osr-reg-subscribe-request@listserv.doa.la.gov.
4. **Per-agency.** Each Notice of Intent names agency contact, address, deadline; oral presentation/hearing if requested within 20 days of publication. No central portal.
5. APA (La. R.S. 49:961 et seq., post-2022 renumbering of 49:953): **≥90 days' notice before agency action** on the rule; hearing 35–45 days after publication; written comment deadline set in Notice of Intent (effectively ≥30–45 days in practice; no single fixed comment-days number beyond the 90-day action bar).
6. **Ingestion: MODERATE.** One large text-PDF/month at a stable site — low-frequency, reliable, but Notices of Intent parsed from several-hundred-page PDF; monthly cadence means deadlines can be tight when issue drops. Listserv = publication trigger.

### MONTANA
1. *Montana Administrative Register (MAR)* — **Montana SOS, Administrative Rules Services**, **twice monthly** (schedule set annually, posted each Sept 1). (sosmt.gov/arm/, ARM 1.4.103)
2. MAR issues as PDFs (e.g. sosmt.gov/docs/118/2024/63937/issue-9-may-10-2024); individual proposal/adoption notices as PDFs via **rules.mt.gov** (searchable ARM DB; notices at `rules.mt.gov/gateway/ShowNoticeFile.asp?TID=xxxxx` — classic-ASP app).
3. No API/RSS. **Email updates** via sosmt.gov/rules.mt.gov; statutory **interested-persons mailing lists** per agency (each proposal notice includes join instructions).
4. **Per-agency** — written comments to address/email in each proposal notice; hearings per notice. No central portal.
5. MCA § 2-4-302: at least **28 days from original notice** to submit comments (≥20 days' hearing notice; proposal published ≥30 days before proposed action).
6. **Ingestion: MODERATE.** Twice-monthly text PDFs + queryable notices gateway with numeric TIDs (enumerable), but ASP app fragile/opaque and deadlines in PDF text. Publication schedule posted a year ahead helps polling.

### IDAHO
1. *Idaho Administrative Bulletin* — **monthly (first Wednesday)**, **Office of the Administrative Rules Coordinator, Division of Financial Management** (Governor's office), Idaho Code § 67-5203. (adminrules.idaho.gov)
2. Electronic-only **PDF** with clean URL pattern: `adminrules.idaho.gov/bulletin/YYYY/MM.pdf`; archive to 1995. Current rules HTML/PDF at /current-rules/. (Mirrored on Azure blob proddfmmainsa.)
3. No API/RSS. **Email mailing list** — alerted when each Bulletin publishes.
4. **Per-agency** — comments to contact in each Notice of Proposed Rulemaking; negotiated-rulemaking notices also in Bulletin. No central portal.
5. Minimum **21 days** after Bulletin publication — Idaho Code § 67-5222; oral presentation if requested by 25 persons within 14 days.
6. **Ingestion: EASY-MODERATE.** Single monthly text-PDF, fully predictable URL; standardized notice templates (deadline in each notice header). Low volume, very stable.

### WYOMING
1. **No traditional register.** **Wyoming SOS** as Registrar of Rules (W.S. 16-3-101 et seq.) runs a centralized rules database serving the register function; *Wyoming Register* listing of intended-rulemaking notices. **Continuous/rolling publication.**
2. Searchable web DB at **https://rules.wyo.gov** — current, proposed, emergency, superseded, repealed; "Proposed Rules Open for Comment" at rules.wyo.gov/Search.aspx?mode=5. Rule text/notices as PDF/Word attachments.
3. **GovDelivery email subscriptions** — notified when emergency/proposed/final rules filed, filterable by agency/program. No public API/RSS; .aspx search endpoints query-parameterized and enumerable.
4. **CENTRALIZED online commenting** — each proposed rule has a **"Provide Public Comment" link**; alternatively to agency contact by email. One of the few states with a Regulations.gov-style central comment mechanism.
5. Minimum **45 days'** notice of intended action; no hearing earlier than 45 days after notice — W.S. § 16-3-103.
6. **Ingestion: MODERATE.** "Open for Comment" search view is effectively a structured deadline feed (agency, filing date, comment link) with predictable query URLs; but ASP.NET viewstate/postback quirks, attachments are PDFs. GovDelivery = reliable secondary trigger.

### COLORADO
1. *Colorado Register* — **Colorado SOS**, **twice monthly on the 10th and 25th**; notices of proposed rulemaking, adopted rules, AG opinions.
2. Register at **coloradosos.gov/CCR/RegisterHome.do** (PDF docs), plus **eDocket** — real-time searchable log of all agency rulemaking filings at /CCR/eDocketCriteria.do (search by tracking number/agency/date; detail pages `eDocketDetails.do?trackingNum=2022-00603`). CCR at /CCR/Welcome.do.
3. No public API. **Colorado Register E-Mail Notification Service** (sos.state.co.us/CCR/EmailSubscription.do, per-agency). Plus statewide **Colorado Rulemaking Portal (rulemaking.colorado.gov)** — subject-matter "Regulatory Notice" email signups + Calendar of Rulemaking Hearings.
4. Hybrid. No single mandatory comment portal: comments in writing to agency and/or hearing testimony per Notice (§ 24-4-103). rulemaking.colorado.gov centralizes discovery/notifications/calendar; eDocket is filing-tracking not comment-taking.
5. C.R.S. § 24-4-103: hearing **≥20 days** after Register publication (comment runs at least until hearing); adopted rules effective 20 days after publication. No longer fixed minimum beyond the 20-day hearing rule.
6. **Ingestion: EASY-MODERATE.** eDocket is the best target: near-real-time queryable filing log with stable tracking-number detail URLs — much better than parsing Register PDFs. Java/.do endpoints stable. Hearing dates may still require reading attached notice PDFs.

### NEW MEXICO
1. *New Mexico Register* — **twice monthly**, **Commission of Public Records — State Records Center & Archives (Administrative Law Division)** under the State Rules Act. (srca.nm.gov/nmac-home/new-mexico-register/)
2. Both PDF issue compilations (`srca.nm.gov/nmac/nmregister/pdf/{roman-volume}{issue}.pdf`, e.g. xxxv10.pdf) and **per-notice HTML pages** (e.g. /nmac/nmregister/xxxv/RLD-SLPAHADnotice_xxxv10.html). NMAC in HTML at /parts/.
3. No API/RSS/central email list for the Register (contact staterules@srca.nm.gov). **NM Sunshine Portal** carries a Rule Hearing Search listing proposed rules/hearings (statutory, 2017 reforms). Individual agencies (DoIT "Rulemaking Omni Alert", NMED) run own lists.
4. **Per-agency** — § 14-4-5.2 notice specifies how to comment "in an electronic or written format or at a public rule hearing." No central portal.
5. Minimum **30 days** after Register publication; notice ≥30 days before hearing — NMSA 1978 § 14-4-5.2.
6. **Ingestion: MODERATE.** Predictable-but-quirky roman-numeral URL patterns; per-notice HTML pages a genuine advantage for deadline parsing, but naming agency-dependent, no feed — scrape volume index pages. Sunshine Portal hearing search useful cross-check.

### UTAH
1. *Utah State Bulletin* — **Office of Administrative Rules** (Dept. of Government Operations), Utah Code § 63G-3-402. **Twice monthly, 1st and 15th.** Companion summary: *Utah State Digest*.
2. PDF issues at predictable URLs — `rules.utah.gov/wp-content/uploads/bYYYYMMDD.pdf` (e.g. b20260701.pdf); each filing includes comment start/end dates, contact, fiscal impacts, rule text. **RTF source files with MD5 hashes** also produced. Searchable current code at adminrules.utah.gov (eRules). Primary: **rules.utah.gov**.
3. **Best-in-class among these states.** Dedicated **RSS feeds page at rules.utah.gov/rssfeeds/**; Digest by email; WordPress feeds (/rulesnews/feed/); RTF + MD5. No formal REST API, but filing-level structure (explicit comment open/close dates per filing) unusually regular.
4. Comments to agency contact in each rule analysis; no single statewide portal, but rules.utah.gov centralizes discovery of every open comment period.
5. Minimum **30 days** (max 113) after Bulletin publication; agency designates close date; rule effective ≥7 days after comment close — Utah Code § 63G-3-301.
6. **Ingestion: EASY.** Fixed cadence, deterministic PDF URLs, RSS feeds, standardized per-filing metadata with explicit comment start/end dates. Main work is PDF/RTF parsing.

### ARIZONA
1. *Arizona Administrative Register* — **Arizona SOS, Administrative Rules Division**. **Weekly, each Friday**; authenticated electronic version is official.
2. PDF issues, highly predictable scheme: `apps.azsos.gov/public_services/register/YYYY/WW/contents.pdf` + per-section PDFs (proposed, final, docket-opening, public-information); yearly archive index pages. Historical archive on Arizona Memory Project.
3. No API/RSS. **Code Update E-mail Service** (A.R.S. § 41-1012(C)) — covers *Code* codifications, not proposed-rule notices per se. GRRC (grrc.az.gov/rulemaking) separately tracks rulemakings.
4. **Per-agency** — NPR names agency contact for written comments and oral proceeding; no central portal.
5. Minimum **30 days** before agency may close the rulemaking record — A.R.S. § 41-1023(B); supplemental proposals reopen 30 days.
6. **Ingestion: EASY-MODERATE.** Weekly, fully deterministic URLs, per-issue contents.pdf indexes notice types — trivial to poll. Authenticated text PDFs. No feed; close-of-record dates parsed from NPR preambles.

### NEVADA
1. *Nevada Register of Administrative Regulations* — **Legal Division of the Legislative Counsel Bureau** (legislative-branch — unusual) under NRS 233B.0653; **monthly** (statute: ≥10×/year, ≤every 2 weeks). (leg.state.nv.us/register/)
2. Web page by year with **per-regulation PDFs** (proposed `R0xx-yyP.pdf`, notices `R0xx-yyN.pdf`/`NH.pdf`, adopted) under `leg.state.nv.us/Register/YYYYRegister/`, plus annual numerical/keyword HTML indexes. Online 1997–current.
3. **No API/RSS/email from LCB.** Statutory per-agency mailing lists (NRS 233B.0603) — request in writing per agency. Workshop/hearing notices centrally aggregated on **Nevada Public Notices Website (notice.nv.gov)** and the Legislature's meeting-notice system — practical central discovery points.
4. **Per-agency** — comments at workshops/hearings or in writing to agency contact in Notice of Intent (NRS 233B.0603). No central portal.
5. At least **30 days' notice** of intended action before adoption (NRS 233B.060); NRS 233B.061 requires workshop(s) with ≥15 days' notice before hearing.
6. **Ingestion: HARD.** No periodic issue stream — directory of per-regulation PDFs on rolling dates, deadlines buried in individually formatted notice PDFs; no feed. Scrape yearly Register directory for new R###-## files + monitor notice.nv.gov; URL patterns stable but discovery and deadline extraction are manual-parse problems.

### Summary table
| State | Cadence | Format | Feed/notify | Central portal | Min. comment |
|---|---|---|---|---|---|
| TX | Weekly (Fri) | HTML + PDF | Email list | No | 30 days |
| OK | Semi-monthly | PDF + portal | Portal email subs | No | 30 days |
| AR | Monthly | PDF + vendor DB | Bulk download (unverified) | No | 30 days |
| LA | Monthly (20th) | PDF | Listserv | No | ~90-day action bar; per notice |
| MT | Twice monthly | PDF + DB | Email | No | 28 days |
| ID | Monthly (1st Wed) | PDF | Email | No | 21 days |
| WY | Rolling DB | Web DB + PDF | GovDelivery | **Yes** | 45 days |
| CO | 2x/mo + real-time eDocket | PDF + eDocket | Email + rulemaking.colorado.gov | Partial (discovery) | Hearing ≥20 days |
| NM | Twice monthly | PDF + per-notice HTML | None central | No | 30 days |
| UT | 2x/mo (1st/15th) | PDF (+RTF) | **RSS + email** | No (central discovery) | 30 days |
| AZ | Weekly (Fri) | PDF | Code-update email only | No | 30 days |
| NV | Monthly | Per-reg PDFs | None; notice.nv.gov | No | 30 days' notice |

Ratings: EASY: TX, UT; EASY-MODERATE: ID, CO, AZ; MODERATE: OK, LA, MT, WY, NM; MODERATE-HARD: AR; HARD: NV.
Follow-ups needing manual verification: AR bulk-data-download contents; exact feed list at rules.utah.gov/rssfeeds/; whether rulemaking.colorado.gov accepts comments directly.

### West & DC: OR, WA, AK, HI, DC (California in california-deep-dive.md)


### CALIFORNIA (EXTRA DEPTH)
1. **Register:** **California Regulatory Notice Register** ("Z Register", issues numbered N-Z). Publisher: **Office of Administrative Law (OAL)**. **Weekly, every Friday.** Agencies must deliver Notice of Proposed Action to OAL ≥10 calendar days before publication. (oal.ca.gov/publications/notice_register/)
2. **Format:** **PDF issues only** — one PDF per weekly issue, exact copy of print. Online access: oal.ca.gov/california_regulatory_notice_online/. Issues organized under **monthly HTML TOC landing pages** (e.g. oal.ca.gov/february-2026-california-regulatory-notice-registers/). PDF URL pattern: `/wp-content/uploads/sites/166/{YYYY}/{MM}/{YYYY}-Notice-Register-No.-{N}-Z-{Month}-{D}-{YYYY}.pdf` — **filenames hand-typed and inconsistent** (stray `-1` suffixes, "Volume Number N-Z" variants, metadata errors). URLs stable once posted but **not reliably predictable in advance**. **Back issues from Jan 1, 2018 only** — in 2019 OAL deleted all pre-2018 Registers for accessibility compliance (Gov. Code § 11546.7); 2002–2017 survive only in California State Web Archive (Archive-It collection 5763).
3. **Machine-readability:** **No API, no RSS/JSON/XML, no bulk download, no structured index** ("does not include an indexing system for search and retrieval" — GGU libguide). **Email:** manual mailing list — email **oalproposedrulemakings@oal.ca.gov** to be added. Adjacent: OAL "Proposed Regulations Under Review" HTML page (oal.ca.gov/proposed-regulations/) — post-comment stage.
4. **Comments:** **NO centralized portal — confirmed.** Each agency runs its own docket; Notice of Proposed Action in Z Register names agency contact and deadline.
   - **CARB:** Rulemaking hub ww2.arb.ca.gov/rulemaking; annual listings of all Section-100 filings 2018–present at **ww2.arb.ca.gov/rulemaking-activity** (per-year list → each rulemaking's formal documents page); archive at /rulemaking-archive. Formal docs under `ww2.arb.ca.gov/sites/default/files/barcu/regact/{YYYY}/{slug}/…` (e.g. …/regact/2026/cap_invest/nc_notice.pdf). **Electronic comment docket:** ww2.arb.ca.gov/applications/public-comments (web form + attachment); legacy app still live at www.arb.ca.gov/lispub/comm/bclist.php ("Choose Comment Item"). Dockets open through 45-day period, 15-day supplemental periods, and until Chair closes record for Board items; submissions public, browsable via per-docket Comment Logs. **CARB e-notification:** GovDelivery listserv (public.govdelivery.com/accounts/CARB/subscriber/new) — all rulemaking notices, 15-day modified-text notices, workshop announcements as bulletins (archived at content.govdelivery.com/accounts/CARB/bulletins/…). **Most machine-adjacent CA notice stream.**
   - **CPUC** (separate regime): Docket Card at apps.cpuc.ca.gov/apex/f?p=401:1:0 — per-proceeding "PUBLIC COMMENTS" tab with "ADD PUBLIC COMMENTS" web form (4,000-word/2-page limit; published online). Documents at docs.cpuc.ca.gov.
5. **Comment period:** **45-day minimum** — Gov. Code **§ 11346.4(a)** (notice ≥45 days before hearing and close of comment; notice lapses after one year). **15-day minimum for substantively modified text** — Gov. Code **§ 11346.8(c)**, implemented by **1 CCR § 44** (15 calendar days' mailed notice to hearing participants/commenters/requesters).
   **Third-party efforts:** No public open-data/open-source project parses the Z Register (no GitHub scrapers, no data.ca.gov dataset). Commercial only: LexisNexis State Net; StateScape (claims 150+ register publications/month, ML + attorney review).
6. **Ingestion: MODERATE (register) / EASY (CARB).** Z Register is weekly text-based PDF with consistent internal layout ("TITLE — DEPARTMENT — Notice published…" digest per action), but no HTML, no feed, hand-typed filenames → reliable enumeration is scraping monthly TOC pages for anchor links. Pre-2018 needs Archive-It. For CARB alone, skip the register: rulemaking-activity HTML listings, predictable barcu/regact/{year}/{slug} document tree, GovDelivery bulletins, and lispub comment-docket list (each open docket = one comment period with machine-readable deadline column).

### OREGON
1. **Oregon Bulletin**, **Oregon SOS, Archives Division**, **monthly, first business day**. Notices of Proposed Rulemaking, permanent/temporary filings, corrections from prior month (agency filing deadline: last day of month). ORS 183.360.
2. Since **Oct/Nov 2017** the Bulletin is generated inside the **Oregon Administrative Rules Database (OARD)** as **HTML database pages**: index at secure.sos.state.or.us/oard/displayBulletins.action, individual bulletins via `displayBulletin.action?bulltnRsn={N}`. Public "Search Filings" by chapter/date range. Pre-2017 archived as documents.
3. **No public API, RSS, or bulk download.** No central SOS subscription — **each agency maintains its own notice mailing list** (ORS 183.335(8), (15)). Caveat: OARD URLs carry `;JSESSIONID_OARD=…` tokens but underlying `.action?param=` endpoints resolve without them.
4. **Per-agency, no central portal.** Notice form names agency rules coordinator; oral hearing if requested by **10+ persons or association of 10+** (ORS 183.335(3)).
5. **No fixed comment-day count**; notice ≥**21 days** before intended action (Bulletin publication), **28 days** to requesters, **49 days** to legislators — ORS 183.335(1)/(8)/(15) + "reasonable opportunity" to comment. Practical floor **~21 days**.
6. **Ingestion: MODERATE.** OARD server-rendered HTML with numeric-parameter .action URLs; monthly Bulletin aggregates every NPR with hearing dates and deadlines in structured HTML (no PDFs required). Downsides: monthly lag (deadlines can be tight by publication), session-URL noise, no feed → poll displayBulletins.action.

### WASHINGTON
1. **Washington State Register (WSR)**, **Office of the Code Reviser** (Statute Law Committee), **twice monthly** — 24 issues/yr (dated 1st and 16th; distributed 7th and 21st). Preproposal (CR-101), proposed (CR-102), permanent (CR-103), emergency, expedited filings + public-meeting notices.
2. **Both structured HTML and PDF, fully predictable URLs — best-organized register in this set:**
   - Issue index: lawfilesext.leg.wa.gov/law/wsr/wsrbyissue.htm
   - Per-issue HTML TOC: `lawfilesext.leg.wa.gov/law/wsr/{YYYY}/{II}/{YY}-{II}.htm`
   - Per-filing PDF: `lawfilesext.leg.wa.gov/law/wsrpdf/{YYYY}/{II}/{YY}-{II}-{NNN}.pdf`
   - Grouped-by-type PDFs per issue, e.g. `25-01PROP.pdf` (all proposed rules in issue).
   - WSR citation `YY-II-NNN` is a stable permanent identifier.
3. **No official API or RSS.** Filing electronic (EFILEWSR@leg.wa.gov) but no public feed. Per-agency e-notification: RCW 34.05.320(2) requires mail/email of CR-102 to rulemaking lists within 3 days of publication; most large agencies (Ecology, L&I, DOL, ESD) run GovDelivery/listserv lists.
4. **No centralized portal.** Each CR-102 specifies where to send comments (email/mail/agency web form); Ecology, L&I, LCB host per-rulemaking online comment pages. Comments accepted through stated deadline — RCW 34.05.325(1); Concise Explanatory Statement required (34.05.325(6)).
5. **RCW 34.05.320(1)**: hearing ≥**20 days** after CR-102 publication in WSR; written comments run at least until hearing. Statutory minimum **20 days**.
6. **Ingestion: EASY** — easiest here: deterministic URL scheme, HTML issue TOCs categorized by filing type, text PDFs, permanent WSR numbers. Enumerate `wsr/{year}/{issue}/{yy}-{ii}.htm` semimonthly, pull CR-102s whose standardized form fields (hearing date, comment deadline, contact) are consistent.

### ALASKA
1. **No register of proposed-rule notices**; statutory vehicle is the **Alaska Online Public Notice System (OPN)** — AS 44.62.175 — supervised by **Office of the Lieutenant Governor**, notices posted continuously: aws.state.ak.us/OnlinePublicNotices/. Separately, **Alaska Administrative Register** (**quarterly** — Jan/Apr/Jul/Oct, Lt. Governor, 1 AAC 05.010) contains **adopted** regulations only.
2. OPN is ASP.NET web app: Browse.aspx, Search.aspx (filterable by category — regulations have own category — and department). Notices are HTML with stable numeric IDs `Notices/View.aspx?id={NNNNNN}`, attachments (typically PDF) at `Notices/Attachment.aspx?id={NNNNNN}`.
3. **Yes — genuine RSS + email.** "Subscribe" offers **RSS feeds and daily email digests**, for all notices or **scoped to saved search criteria** (e.g. only Regulations-category from one department). Documented in system help. No JSON API or bulk download.
4. Historically per-notice: comments to agency contact before deadline. **OPN now supports commenting via a comment link; submitted comments viewable online for periods ending after June 2024.** Some agencies run own e-comment apps (DEC Air Quality). [Exact scope of OPN native commenting — all notices vs agency-opt-in — unconfirmed.]
5. **AS 44.62.190(a)**: notice published (newspaper + OPN) ≥**30 days** before adoption — **30-day minimum**.
6. **Ingestion: EASY-MODERATE.** Saved-search RSS scoped to regulations = ready-made notice stream (the only true feed among these six); stable numeric-ID URLs. Work is downstream: deadlines in notice body/PDF attachments, formats vary by agency.

### HAWAII
1. **No state register or bulletin of any kind** — only US state-level jurisdiction in this set with none. **HRS § 91-2.6** (eff. 2000): agencies post full text of proposed rules online **through the Office of the Lieutenant Governor**; final rules filed with Lt. Gov (§ 91-4). Notice by **newspaper publication** (statewide) + mailing to requesters (§ 91-3, § 92-41).
2. Lt. Governor's **"Proposed Changes to Administrative Rules"** page — ltgov.hawaii.gov/the-office/administrative-rules/proposed-changes/ — rolling WordPress list, each linking a **PDF** packet (ramseyed text, hearing notice). HAR chapters posted per-department. Newspaper hearing notices aggregated (privately) at statelegals.staradvertiser.com. [Listing structure not directly inspected.]
3. **None found.** No API, RSS, bulk data, or central e-notification. HRS § 91-3(a): agencies mail notice to written requesters — **per-agency mailing lists only**.
4. **Per-agency, hearing-centric.** Public hearing required; comments orally at hearing or in writing to agency (HRS § 91-3(a)(2)). No portal.
5. **HRS § 91-3(a)(1)**: ≥**30 days' notice** of public hearing. **30-day minimum.**
6. **Ingestion: HARD.** No canonical machine-readable stream: scrape hand-maintained WordPress list (irregular conventions, PDF-only, occasionally scanned PDFs) and/or Star-Advertiser legal notices (paginated, non-.gov), parse hearing dates from free-text PDFs. URL stability at mercy of WordPress uploads. Expect per-agency special-casing.

### DISTRICT OF COLUMBIA
1. **District of Columbia Register (DCR)**, **Office of Documents and Administrative Issuances (ODAI)** (Office of the Secretary), **weekly, every Friday**, at dcregs.dc.gov. Agency filing deadline: Thursday noon of prior week. Official legal bulletin + temporary DCMR supplement; proposed/emergency/final rulemakings, Council actions, hearing notices. D.C. Code § 2-553.
2. **Hybrid database + PDF** (ASP.NET): searchable by rule number, Notice ID, agency, full text; notice detail pages `dcregs.dc.gov/Common/NoticeDetail.aspx?NoticeId=N{NNNNNNN}` with Word and/or PDF docs. Weekly issues by category: `Common/DCR/Issues/IssueCategoryList.aspx?CategoryID={N}&IssueID={N}` (proposed rulemakings separated); GUID download links. Full-issue PDFs circulate. Coverage **Oct 2, 2009–present**; older at dcregisterarchives.dc.gov.
3. **No API or documented RSS.** DC.gov has general RSS/subscribe infrastructure but nothing register-specific. Contact: dcdocuments@dc.gov. [On-site email signup unverified.]
4. **No centralized portal.** Each NPR states where to send comments (agency email/address). Register submission (agency-side) electronic via dcregs accounts; public comments to issuing agency.
5. **D.C. Code § 2-505(a)**: notice published in DCR **≥30 days prior to effective date**, waivable for good cause; emergency rules immediate up to 120 days. **30-day default minimum.**
6. **Ingestion: MODERATE.** Enumerable: stable NoticeDetail URLs, per-issue category pages isolating "Proposed Rulemaking", weekly cadence → poller feasible without PDF-diffing. Frictions: ViewState-heavy search pages, GUID download links, docs split Word/PDF requiring dual parsers.

### Summary table
| Juris | Publication | Cadence | Format | Feed/API | Central portal | Min. comment | Ingestion |
|---|---|---|---|---|---|---|---|
| CA | Z Register (OAL) | Weekly Fri | PDF + HTML TOCs | None; manual email list; CARB GovDelivery | No — per agency | 45 d (§ 11346.4); 15 d mod text | MODERATE / EASY (CARB) |
| OR | Oregon Bulletin (OARD) | Monthly | HTML DB | None; per-agency lists | No | 21-day notice floor | MODERATE |
| WA | WSR (Code Reviser) | 2x/mo | HTML TOCs + PDFs, deterministic | None official; agency GovDelivery | No | 20 d pub→hearing | EASY |
| AK | OPN (notices) | Continuous | HTML + PDF attach | **RSS + daily email, saved-search** | Partial (OPN comment links) | 30 d | EASY-MODERATE |
| HI | None — Lt. Gov page + newspapers | Rolling | PDF on WordPress | None | No | 30 d hearing notice | HARD |
| DC | DC Register (ODAI) | Weekly Fri | DB + Word/PDF | None documented | No | 30 d | MODERATE |
