# The Hard Eight: What Actually Breaks Ingestion (GA, HI, NE, NV, TN, MS, MA, NJ)

> Companion to [`README.md`](README.md) and [`state-by-state.md`](state-by-state.md). The first-pass
> survey rated these eight jurisdictions HARD. This deep dive establishes *specifically* what
> breaks in each, with evidence, and a least-bad ingestion path. Researched July 2026 by three
> parallel agents; the sandbox egress proxy blocked all direct .gov fetches (CONNECT 403 at the
> gateway, including web.archive.org), so evidence comes from search-indexed content of official
> pages and PDFs — which is itself probative (e.g., a search engine displaying a PDF's extracted
> first line proves a text layer exists; displaying mojibake proves a scan). Verified-vs-inferred
> is flagged per state.

## Headline: the hard eight is really a hard two

The deep dive found workable seams in six of the eight. Revised ratings:

| State | Was | Now | What changed |
|---|---|---|---|
| **GA** | HARD | **HARD** | Confirmed structural: no consolidated source of proposals exists at any price with guaranteed completeness |
| **HI** | HARD | **HARD** | Confirmed: no chronological index anywhere; the statute lets the central site be incomplete |
| **NE** | HARD | **MOD-HARD** | Statewide email trigger + stable sequential document IDs found; OCR still mandatory |
| **MS** | HARD | **MOD-HARD** | Stable sequential PDF URLs + 2-business-day publication SLA make ID-polling near-real-time; OCR still mandatory |
| **NJ** | HARD | **MOD-HARD** | OAL posts free PDFs of the Register's rulemaking sections with machine-parseable filenames; completeness unproven |
| **MA** | HARD | **MODERATE** | The Secretary *freely publishes the Register's notice section* — the paywall doesn't cover the part we need |
| **TN** | HARD | **MODERATE** | The "register" is a clean sortable GET-param HTML table with enumerable text-PDF filings |
| **NV** | HARD | **MODERATE** | A dated Daily Updates index with typed filename suffixes classifies documents for free; notice PDFs are text |

The two failure modes that survive scrutiny: **structural fragmentation** (GA, HI — there is no
chokepoint to fix) and **OCR debt** (NE, MS — the clock-starting documents are scans). Paywalls
turned out to be the *least* durable barrier: in both MA and NJ, the state itself leaks the notice
stream for free.

---

## Georgia — HARD (confirmed): the no-source state

**What breaks:** Georgia's APA (O.C.G.A. § 50-13-4(a)) requires only that each agency mail notice
to persons on its own request list and transmit a copy to legislative counsel (an internal
legislative channel, not a publication). Nothing consolidates *proposed* rules:

- **rules.sos.ga.gov** (Fastcase-published) is the compiled code of *filed/adopted* rules only.
  Its "Georgia Monthly Bulletin" — verified from the April 2025 issue's indexed TOC — contains
  final rules filed during the month (columns: Rules List / Action / Filed / Effective / Page).
  Post-hoc; no proposals, no deadlines.
- **The paid option isn't complete either.** GSU Law's research guide states there is "no free
  access version" of the LexisNexis Georgia Government Register *and* "there is no requirement
  that a rule be published in the Georgia Government Register"
  ([libguides.law.gsu.edu](https://libguides.law.gsu.edu/c.php?g=253390&p=7491196)). Paying
  LexisNexis buys latency (monthly) without a completeness guarantee.
- **georgiapublicnotice.com** (press association) doesn't help — the GA APA doesn't require
  newspaper publication of rulemaking notices.
- The actual notice surface is **per-agency, one CMS at a time** (all verified with live
  examples): EPD's Drupal proposed-rules table ([epd.georgia.gov](https://epd.georgia.gov/public-announcements-0/proposed-rules),
  PFAS rules w/ comments due Dec 17 2025); DPH's NPRM PDF list ([dph.georgia.gov](https://dph.georgia.gov/about-dph/regulationsrule-making),
  food-service rules w/ comments due Jan 15 2026); DCH's notices page where rulemaking is
  **co-mingled with Medicaid rate notices** (a classification problem on top of scraping); Dept.
  of Agriculture's HTML legal notices; the PSC, where rule changes run as **dockets in the FACTS
  e-filing system** with no rules page at all; DOE's new site + still-live legacy SharePoint. One
  bright spot: the SOS Joint Secretary page consolidates ~40 licensing boards, and the
  Professional Standards Commission publishes a monthly consolidated notice PDF at a predictable
  URL.

**Least-bad path:** ~8–10 per-agency scrapers against the (stable) listing pages; join each major
agency's statutory § 50-13-4 notice mailing list by email as a redundant push channel; use the
SOS Monthly Bulletin (predictable `Download_pdf.aspx` URL pattern) as a monthly completeness
backstop — any final rule that was never seen as a proposal flags a coverage gap and names the
next agency to onboard.

**Volume estimate:** ~4–5 departments filed finals in the one sampled month → order-of-magnitude
40–80 distinct agencies/boards filing per year *(1-month sample; inference)*.

---

## Hawaii — HARD (confirmed): the no-index state

**What breaks:**

1. **No dated, chronological, machine-readable index exists anywhere.** The Lt. Governor's
   proposed-changes page ([ltgov.hawaii.gov](https://ltgov.hawaii.gov/the-office/administrative-rules/proposed-changes/))
   is a WordPress page organized **by department**, not by date — no date-sorted view, no RSS, no
   pagination metadata. Comment deadlines exist only *inside* the PDF hearing-notice packets
   (Notice of Public Hearing + Ramseyer-format rule text). The Lt. Gov's "Monthly Update Reports"
   are post-adoption filing logs (`DOC NO | DEPT | TITLE-CH-SEC | EFF. DATE` — verified from
   indexed PDF text) — a lagging indicator, useless for deadlines.
2. **The central site is legally allowed to be incomplete.** HRS § 91-3 says *inadvertent failure
   to post on the Lt. Governor's site does not invalidate the rule*
   ([capitol.hawaii.gov](https://www.capitol.hawaii.gov/hrscurrent/Vol02_Ch0046-0115/HRS0091/HRS_0091-0003.htm)).
   The legally required channel is **newspaper publication** (§ 91-3, § 92-41). So the only
   "official" aggregation is the Star-Advertiser's legal-notices site
   ([statelegals.staradvertiser.com](https://statelegals.staradvertiser.com/category/public-notices/public-hearings/)) —
   full-text HTML at stable dated URLs, no paywall observed, but **post titles are bare ad numbers**
   ("0001524270-01"), so classification requires fetching every body in the category.
3. Fragmentation with a silver lining: agency pages are the real surface, and some are *good* —
   DOH branch pages expose comment deadlines in HTML (e.g., the Clean Water Branch's
   "[comment period open until May 11, 2026](https://health.hawaii.gov/cwb/active-public-notices-and-upcoming-public-hearings/20260410-har-11-55-public-comment-period-and-public-hearing/)");
   DLNR and DCCA maintain structured rulemaking pages; BOE is a document dump.

**Least-bad path:** poll the Star-Advertiser Public Hearings category as the primary event signal
(it's the statutory channel; WordPress means `/feed/` likely exists *(inferred)*), regex bodies
for HAR chapter/hearing/deadline; diff-scrape the Lt. Gov page for the authoritative Ramseyer
packets; layer DOH/DLNR/DCCA agency adapters. No statewide e-notification exists; the eHawaii
Sunshine-Law calendar covers board meetings only (partial rule-hearing coverage).

---

## Nebraska — downgraded to MODERATE-HARD: OCR debt with a good trigger

**What breaks:** the comment clock lives in heterogeneous, affidavit-style attachment PDFs, and a
nontrivial fraction are image scans. Direct evidence: the Google-indexed title of regtrack
proposal [`0000000000001667.pdf`](https://www.nebraska.gov/nesos/rules-and-regs/regtrack/proposals/0000000000001667.pdf)
is mojibake (`$'ehraøh a ffirfuhr...`) — garbage OCR of a scanned Public Service Commission
blackletter letterhead. Of six sampled attachments, one was an unusable scan and five had
extractable text of varying (sometimes OCR-of-scan) quality. The docket's HTML tracks *approval
stages* (an explicit "AG Approved" column), not comment deadlines. And the canonical store is
2000s-era CGI plumbing: `details.cgi?proposal_id=` with **two inconsistent ID formats**
(zero-padded 16-digit and bare), fronted cosmetically by rules.nebraska.gov.

**What saves it:** Nebraska has the best event trigger of the eight — a **statewide official email
subscription** (verified from [rules.nebraska.gov/about](https://rules.nebraska.gov/about)): a
single rule, all of one agency's rules, or *all proposed rules statewide*, firing on any
tracking-document update. And all attachments live at stable
`regtrack/proposals/{id}.pdf` paths.

**Least-bad path:** route the statewide subscription into a dedicated inbox as the event trigger;
on each event scrape `details.cgi` for stage dates and pull the PDF with a mandatory OCR
(Tesseract-class) fallback; poll DHHS's structured
"[Upcoming Public Hearings](https://dhhs.ne.gov/Pages/Upcoming-Public-Hearings.aspx)" HTML page
for the state's highest-volume rulemaker.

---

## Mississippi — downgraded to MODERATE-HARD: discovery-hostile portal, exploitable document store

**What breaks:** the Administrative Bulletin is an ASP.NET WebForms postback portal
([sos.ms.gov/adminsearch](https://www.sos.ms.gov/adminsearch/default.aspx?current_page=Bulletin))
organized agency-by-agency — the SOS's own FAQ describes access as "by knowing the issuing
agency." No consolidated open-proposals list, no stable result URLs, no feed, no confirmed
notification service. Worse, the clock-starting document — the Form 001 filing notice — is
frequently a **stamped scan** (the indexed title of
[`00027305a.pdf`](https://www.sos.ms.gov/adminsearch/ACProposed/00027305a.pdf)'s sibling is OCR
garbage: "DEC 2 7 2023 \*—^"), and the 25-day deadline (§ 25-43-3.106) must be **computed from
the filing date**, not read from a stated field.

**What saves it:** the portal's underlying documents have **stable, sequential, directly
addressable URLs**: `sos.ms.gov/adminsearch/ACProposed/{8-digit-id}{letter}.pdf`, where `a` =
filing notice, `b` = rule text (Word-origin, text layer), `c` = code compilation — confirmed
against the MDAH digital archive's mirror of Bulletin filings. Combined with the codified
**2-business-day publication SLA** (1 Miss. Code R. § 1-2.1), incrementing IDs from the current
high-water mark is a near-real-time feed the portal never intended to offer. (IDs are
Google-crawled, hence publicly fetchable; enumeration untested from the sandbox.)

**Least-bad path:** poll `ACProposed/{id}{a,b}.pdf` by ID; OCR each new `a` for agency/filing
date/contact; deadline = filing date + 25 days (flag the +20-day oral-proceeding trigger);
monthly headless-browser Bulletin sweep for completeness; subscribe to key boards on the statutory
[MS Public Meeting Notices](https://www.ms.gov/dfa/pmn/) portal for hearing corroboration.

---

## New Jersey — downgraded to MODERATE-HARD: vendor lock with a state-side leak

**What breaks:** the official journal's only free full-text home is LexisNexis's Advance
"container" app (the successor to lexisnexis.com/hottopics/njoal) — base64 config blobs,
per-session `crid`/`prid` GUIDs, no stable deep links, no feed, ToS-encumbered. The statutory
active-proposals database (N.J.S.A. **52:14B-7.1**, P.L. 2017 c.262) runs on a Microsoft Dynamics
365 GCC portal ([oalrulesproduction.dynamics365portals.us](https://oalrulesproduction.dynamics365portals.us/))
whose documented schema — proposing entity, publication date, summary, impacts, N.J.R. citation —
**lacks an explicit comment-deadline field**, and whose uptime/anonymous-access scope couldn't be
confirmed from the sandbox (host didn't resolve; standard Dynamics OData endpoints are plausible
but unprobed).

**What saves it:** OAL itself posts **free PDFs of the Register's rulemaking sections** at
[nj.gov/oal/rules/proposals/](https://www.nj.gov/oal/rules/proposals/) across the full notice
taxonomy (Proposals, Adoptions, Readoptions, Pre-Proposals, Hearing Notices, Emergency,
Petitions), with **machine-parseable filenames** — `PRN YYYY-NNN (VV NJR PPPP(a)).pdf` /
`R.YYYY d.NNN (…)` — that yield the proposal number and Register citation without opening the
file. A published [2026 publication schedule](https://www.nj.gov/oal/rules/schedule/) (twice-monthly
Mondays) gives the polling cadence. Department pages are strong: DEP has per-proposal HTML pages,
a comment web form, an archive, and a **rulemaking email listserv**
([dep.nj.gov/rules](https://dep.nj.gov/rules/notice-of-rule-proposals/) — e.g., PRN 2026-028,
comments due 7/31/2026); DOBI maintains a literal "Proposed New Rules — **Comment Period
Remaining**" page; DOH emails rulemaking notices and issues a press release per proposal. Comment
law: 30-day statutory minimum (N.J.S.A. 52:14B-4), 60 days customary because it exempts the
rulemaking from calendar requirements.

**Least-bad path:** anchor on OAL's free PDF postings, polled on the published twice-monthly
schedule, parsing filenames for PRN + citation and PDF text for deadlines; probe the Dynamics
portal's OData endpoints from an unrestricted network as the structured cross-check; layer
DEP/DOBI/DOH adapters and their email lists as tripwires; use the LexisNexis viewer only for
manual verification/backfill. **Open question:** whether OAL's postings are complete against the
Register (category breadth suggests yes; unproven).

---

## Massachusetts — downgraded to MODERATE: the paywall doesn't cover the notices

**What breaks (and why it's legal):** the Register itself is $225/yr online / $300 print, login
portal, electronic edition legally "unofficial." That's durable: M.G.L. c.30A **§ 6** gives the
Secretary open-ended fee discretion ("may be set without reference to the statutory charges for
public documents"), free copies go only to legislative officers and the State Librarian, and
Massachusetts has **not adopted UELMA** (repeated bills died), so nothing mandates free
authenticated electronic legal material. No case law challenges the paywall — it persists by
statute plus inaction, not litigation.

**What saves it — the key finding of this whole deep dive:** the Secretary **freely publishes the
Register's notice section**. "Notices of Public Review of Prospective Regulations" at
[sec.state.ma.us/divisions/pubs-regs/public-hearings.htm](https://www.sec.state.ma.us/divisions/pubs-regs/public-hearings.htm)
lists agencies with notice dates, hearing times, and written-comment deadlines; **per-issue archive
pages** (`hearings/html/pdf-M-DD-YY.htm`, verified instances 2023–2025 tracking the biweekly
Register cadence) and **individual notice PDFs** whose filenames already encode date + CMR number
(verified examples through April 2026, e.g.
`4-10-26-NPH-SBIS-101-CMR-361_filed-2026-03-27-.pdf`). Since § 6 requires *all* §§ 2–3 notices to
appear in the Register, this page should be near-complete for c.30A rulemaking *(completeness
inferred from the statute; not diffed against a paid issue)*. On top of that, the high-volume
agencies post proposals with deadlines on free Mass.gov pages (DPH, EOHHS/MassHealth — which has
an **email notification list** for proposed regulations — MassDEP, DOR, DESE, EOPSS), and DPU
hearings live in the EEA Fileroom app. The State Library's archive lags ~months (its sibling
Central Register collection's newest search-visible issue was ~3.5 months old) — backfill, not
currency. masspublicnotices.org (press association) exists as a noisy safety net; newspaper
publication is agency-discretionary, not mandated.

**Least-bad path:** poll the Secretary's free notice page + biweekly archive on the Register
cadence and parse the notice PDFs (filenames carry date + CMR; bodies carry hearing date and
comment deadline) — effectively the Register's notice section without the paywall. Layer
high-volume agency watchers and the MassHealth email list. Buy one $225 subscription only if
authoritative completeness/full rule text is ever needed.

---

## Tennessee — downgraded to MODERATE: the register is a website, and it's scrapeable

**What changed:** the first pass saw rolling PDF filings and bot-blocking and rated it HARD. The
deep dive found the structure underneath:

- The monthly print Tennessee Administrative Register was **discontinued July 2, 2009** (Public
  Chapter 566); since then the rolling "Tennessee Administrative Web Site" *is* the official
  register under T.C.A. Title 4, ch. 5.
- The live index is a **server-rendered, sortable, paginated HTML table driven by plain GET
  params**: [`tnsos.org/rules/RulemakingHearings.php?sort=NoticeFileDate&direction=desc&page=N`](https://tnsos.org/rules/RulemakingHearings.php),
  with companions `PendingRules.php` and `ArchivedRulemakingHearings.php`. **Still updated in
  2026** (verified filings `01-11-26.pdf` … `05-07-26.pdf`, including a notice with a July 28,
  2026 hearing).
- Filing documents are **enumerable**: `publications.tnsosfiles.com/rules_filings/MM-SS-YY.pdf`
  (month, per-month sequence, 2-digit year; ≥38 filings in Dec 2025) and are **text-based
  standardized forms** (SS-7037; agencies file Word electronically since ~2019) — deadline and
  hearing metadata is in the text layer.
- Official posting SLAs: notices within 7 days of acceptance; hearings ≥45 days after filing;
  emergency rules within 4 days.

**Residual risk:** no feed or email service (negative finding), and a fragile three-domain split
(sos.tn.gov / tnsos.org / *.tnsosfiles.com, plus a new sos-prod file host) with a Drupal
migration visibly underway — the PHP endpoints could break without notice. Build a 404/redirect
tripwire into the poller.

---

## Nevada — downgraded to MODERATE: the index existed all along

**What changed:** the first pass saw a directory of per-regulation PDFs and no feed. The deep dive
found the LCB's **[Daily Updates index](https://www.leg.state.nv.us/Register/indexes/DailyUpdates.htm)** —
a plain HTML page listing each Register document **with the date it was posted**, plus a
documented filename-suffix legend that classifies documents for free: `I` initial agency draft,
`P` LCB proposed draft, `RP` revised, **`NW` notice of workshop, `NH` notice of hearing**, `A`
adopted, `W` withdrawn. Per-file URLs are stable
(`leg.state.nv.us/Register/2026Register/R009-26I.pdf`, verified 2026 examples), yearly cumulative
numerical indexes exist (2024/2025 confirmed), and the notice PDFs are **text, not scans**
(extracted first lines visible in search across 2014–2025 samples). Separately, the Legislature
runs an "[Administrative Regulation Notices](https://www.leg.state.nv.us/App/Notice/A/)"
application where agencies must file workshop/hearing/intent notices (2026 content verified) —
useful for workshops that precede LCB file assignment.

**Residual friction:** still no feed/API anywhere; deadlines are inside the PDFs; and the three
systems (Register directory, App/Notice, notice.nv.gov) share no exposed identifier — joining
them requires parsing PDF text. notice.nv.gov (NRS 232.2175) has no regulation category, no RSS —
audit backstop only. Statutory per-agency mailing lists (NRS 233B.0603) require writing to each
of ~100+ agencies; skip.

**Least-bad path:** diff-scrape DailyUpdates.htm; treat new `NW`/`NH`/`I`/`P` rows as trigger
events; fetch and text-extract the PDF; scrape App/Notice as the second source.

---

## Revised implications for the roadmap

1. **Only GA and HI are structurally hard** — both need per-agency adapter fleets plus a
   completeness backstop, and neither has a fix short of the state building something. Defer both.
2. **NE and MS are OCR projects with good bones** — each has a reliable trigger (NE statewide
   email; MS sequential-ID polling with a 2-day SLA) and stable document URLs. Once the OCR
   fallback exists in the shared pipeline, these graduate to routine.
3. **TN, NV, MA move into the standard MODERATE queue** — pollable indexes with text documents;
   MA's free notice pages remove the paywall from the critical path entirely.
4. **NJ is a filename-parsing exercise plus one off-sandbox probe** — check the Dynamics portal's
   OData endpoints from a normal network before writing any HTML scraper.
5. **Recurring pattern worth institutionalizing:** in every "hard" state the breakthrough was a
   *secondary* surface (a legacy index page, a document CDN with sequential IDs, a free notice
   subset, a press-association site). Adapter research should always ask "where do the documents
   physically live?" separately from "what does the front door look like?"
6. **Sandbox caveat:** all bot-blocking observations remain unconfirmable from this environment
   (the proxy 403'd everything, including archive.org). Re-test fetchability from an unrestricted
   network before finalizing any adapter plan.
