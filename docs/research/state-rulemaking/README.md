# State Rulemaking Landscape: How the 50 States Publish Regulations & Comment Periods

> **Why this exists:** a CARB (California Air Resources Board) staffer's first reaction to
> DocketClock was *"this is great — do you have this for state level?"* This research answers
> whether a state-level DocketClock is feasible: how every state publishes rulemaking notices and
> comment periods, what's machine-readable, and which states are easy or hard to ingest.
>
> **Files:** this synthesis · [`state-by-state.md`](state-by-state.md) (51-jurisdiction reference
> table + full per-state findings) · [`california-deep-dive.md`](california-deep-dive.md)
> (OAL/Z Register/CARB).
>
> Researched July 2026 by parallel web-research agents against official .gov sources. The research
> sandbox's egress proxy blocked direct fetches of most state .gov hosts, so many facts were
> verified via search-engine retrieval of official page content; flagged items need re-verification
> from an unrestricted network.

## TL;DR

1. **There is no state Federal Register API. Anywhere.** Not one of the 50 states (or DC) offers a
   documented public API for its rulemaking notice stream. The federal
   `federalregister.gov/api` + `api.regulations.gov` combination DocketClock ingests today is
   *categorically* better than what any state offers. A state-level DocketClock is therefore a
   **scraping-and-email-parsing product, not an API-integration product** — which is exactly why
   the niche is open and why a CARB analyst reacts the way she did.
2. **But ~90% of states have a scrapeable chokepoint.** Almost every state funnels notices through
   one register/bulletin/portal with stable URL conventions. Only a handful (GA, HI, and
   arguably NE/NV/TN) genuinely fragment across agencies.
3. **Machine-readable feeds are rare but real:** true RSS exists in ~4–5 states (UT, VA, AK, ND,
   arguably WI's notification system); ~25 states offer email subscriptions (several
   agency-filterable); 2 states have *de facto* undocumented REST endpoints (SD's `mylrc` API, AL's
   `/api/` document store). Everything else is polling.
4. **A dozen states have some form of centralized online comment portal** — CT (best-in-class
   "Comment Now"), VA (Regulatory Town Hall), IA (rules.iowa.gov), WY, SD, WI (via legislature
   site), MN (OAH eComments, partial), AK (OPN, partial), CO (discovery only). The rest are
   per-agency mail/email/hearing — meaning a "one-click comment" feature can't generalize, but
   deadline *monitoring* can.
5. **Comment-period law varies 3×:** statutory floors run from ~17–21 days (SD, FL, ID, MA, OR) to
   60 days (NY, VA, NC, KS). Several states anchor deadlines to hearings rather than fixed windows
   (MI, WI, NE, HI, CO, NH, VT), so the *notice text* — not the statute — is the source of truth
   for any given deadline. DocketClock's observation-log + confidence model transfers cleanly; the
   state statutes just change the priors.
6. **California specifically:** weekly PDF-only "Z Register" from OAL, no feed, no index, no
   central portal, 45-day statutory minimum — but **CARB itself is EASY** (HTML rulemaking
   listings, a comment-docket app with a deadline column, GovDelivery bulletins). A CARB-only
   adapter is a shippable first answer to the contact's question. See
   [`california-deep-dive.md`](california-deep-dive.md).

## The landscape in one view

Distribution of the 51 jurisdictions (details and per-state citations in
[`state-by-state.md`](state-by-state.md)):

| Dimension | Count | Jurisdictions |
|---|---|---|
| Documented public API for notices | **0** | — |
| De facto / undocumented structured endpoints | ~4 | SD (mylrc REST), AL (`/api/aam`, `/api/filing`), OH (parameterized servlet), IN (modern SPA, probe-worthy) |
| True RSS/Atom feeds | ~5 | UT, VA (register RSS), AK (saved-search RSS), ND (rules RSS), + WI legislature notifications |
| Email notification service (state-run, rulemaking-specific) | ~25 | KS, MO, NE, IA, FL, MI, WY, CO, MT, ID, LA, TX, OK, NY, PA (+IRRC), CT, RI, VA, AK, WI, UT, MN (paid), MD (paid), NJ/GA (per-agency only)… |
| Centralized/partial online comment portal | ~10 | CT, VA, IA, WY, SD, WI, MN (partial), AK (partial), CO (discovery), NE (optional per-agency) |
| Register is structured HTML (not just PDF) | ~15 | WA, WI, KS, TX, IN, PA, DE, MD, CT, RI, OR, NM (partial), FL, OH (DB), CO (eDocket) |
| PDF-only or PDF-dominant register | ~25 | NY, IL, CA, MN, KY, LA, ID, AZ, MT, SC, WV, NC, NH, MS, UT, OK, MO, IA, MI, SD, AK(supp)… |
| No register at all (continuous portal / newspaper regime) | ~8 | NE, ND, WY, HI, + continuous-portal states CT, RI, VT, AK |
| Paywalled or vendor-locked primary stream | 3 | MA ($225/yr), NJ (LexisNexis viewer), MD (only ~15 issues free) |
| Genuinely fragmented (no single chokepoint) | ~4 | GA, HI, TN, (NV borderline) |

### Ingestion difficulty tiers (from the per-state assessments)

- **EASY (12):** WA, TX, UT, KS, PA, VA, DE, RI, ME, IN, WI, FL*(if bot-blocking solved)*
- **EASY–MODERATE (5):** CT, AK, ID, CO, AZ
- **MODERATE (22):** NY, IL, OH, MI, MN, IA, MO, ND, SD, KY, SC, WV, NC, OK, LA, MT, NM, WY, NH, VT, DC, CA
- **MODERATE–HARD (1):** AR
- **HARD (7):** GA, HI, NE, NV, TN, MS, MA, NJ

Roughly: **17 states are cheap wins, 22 are routine scraper work, 8 are genuinely painful.** The
painful ones share three failure modes: no chokepoint (GA, HI, TN), image-scan PDFs (NE, ND
partially, MS), or paywalled/vendor-locked streams (MA, NJ).

## What "state Regulations.gov" looks like where it exists

Four systems are worth studying as the best-of-breed state patterns:

1. **Virginia Regulatory Town Hall** (townhall.virginia.gov) — the strongest overall: every
   executive-branch regulatory action tracked by stage with per-stage comment windows, public
   comment forums, nightly scoped email digests, per-document XML views, and ID-keyed URLs. This is
   the closest thing in the US to a state Regulations.gov, and it *coexists* with a PDF register —
   proof that register-plus-database is the natural end state.
2. **Connecticut eRegulations System** (eregulations.ct.gov) — continuous posting replaced the
   register entirely; every open regulation has a "Comment Now" button writing into the official
   record; explicit deadline fields in HTML listings.
3. **Washington State Register** (lawfilesext.leg.wa.gov) — no portal, but the most
   scraper-friendly register: fully deterministic URLs, HTML TOCs categorized by filing type
   (CR-101 preproposal / CR-102 proposal / CR-103 adoption — a built-in lifecycle state machine),
   permanent `YY-II-NNN` identifiers.
4. **Utah OAR** (rules.utah.gov) — RSS feeds plus per-filing metadata that includes explicit
   comment open/close dates; the register PDF is almost an afterthought.

Notable negative case: **Florida** brands flrules.org as "eRulemaking" and publishes *daily*, but
comments still go per-agency — branding ≠ portal.

## Why the systems look alike (and where they don't)

Most state APAs descend from the Uniform Law Commission's **Model State Administrative Procedure
Act** (1961/1981, revised 2010). The 2010 MSAPA recommends: notice of a proposed rule published in
a state "administrative bulletin" at least **30 days** before adoption (§ 304), a **≥30-day**
public-comment period (§ 306, bracketed as a fill-in value states may adjust), an
at-least-monthly bulletin (§ 201), and web publication defined only as "a searchable archival
database" — **no format mandate and no API/feed requirement**. That explains both the convergence
(30 days is the modal floor; nearly every state has *some* bulletin) and the heterogeneity
(HTML vs PDF vs paywalled print all satisfy the model act). States enacted it selectively, so
per-state statutory verification stays necessary. *(Source: MSAPA 2010 text; extracted by the
research harness but not adversarially verified — see verification note below.)*

One timeliness caveat surfaced by aggregator marketing and worth testing empirically: **registers
lag agency activity** — agencies often post rulemaking material on their own sites weeks before
the register issue appears, so register-only ingestion trades completeness for latency. Per-agency
monitoring (or agency email lists) is the early-warning layer where latency matters.

## Cross-cutting aggregators & prior art

- **Commercial trackers own this space today:** LexisNexis **State Net** and **StateScape** both
  advertise full 50-state regulatory tracking (StateScape claims monitoring of 150+ register
  publications/month across all states + territories; its RegsTrack product structures comment
  deadlines and hearing dates as searchable fields, delivered via analyst-curated email alerts and
  a proprietary platform — **no public API**, so not ingestible without a partnership).
  **FiscalNote/CQ** plays in the same market. These are expensive enterprise tools aimed at
  lobbyists and compliance teams — none serve citizens or small orgs, which is DocketClock's
  wedge. Their existence *validates* that the scraping problem is tractable at 50-state scale, and
  that comment-period metadata can be systematically extracted from state notices.
- **LexisNexis is also a publisher**, not just an aggregator: it publishes the official NJ Register,
  prints the VA Register, and sells the unofficial GA Government Register. Vendor-hosted registers
  (NJ, GA/Fastcase-vLex, AR/NIC, VT/NIC-Tyler, PA/Fry Communications, MN comments/Granicus) are a
  recurring pattern — and vendor platforms churn, so adapters should treat hosting domains as
  replaceable.
- **Open States** (openstates.org, Plural) covers *legislation* — bills and legislators — via
  scrapers + API, and is the closest open-source cultural analogue, but it does **not** cover
  administrative rulemaking. There is no "Open States for regulations." That gap is the
  civic-tech opportunity this research keeps confirming.
- **NASS Administrative Codes & Registers (ACR) section** — the professional association of
  register editors (many SOS offices). Useful as a directory of who runs each register and as a
  standards venue; publishes a periodic Administrative Rules directory/survey.
- **Third-party single-state efforts exist where officials fail hardest:** nh-rulemaking.app
  (NH Register search + alerts), flrules.elaws.us (FL mirror). Nothing found for CA (open niche).
- **Law-library research guides** (Cornell LII state listings, law-school libguides) are the best
  free maps of each state's system and were heavily used in this research.

## Implications for a DocketClock state substrate

*(assessment, not a build plan)*

1. **The contract already fits.** `ParticipationWindow` + observation log + chain links map
   directly: state 15-day modified-text periods (CA), post-hearing comment windows (VT, ND, NH,
   ME), extensions, and legislative-review kill-steps (SC, WV, IL JCAR, PA IRRC) are all instances
   of the cross-window semantics DocketClock already classifies for FR notices. OCD-IDs already
   encode state jurisdictions.
2. **Adapters are the unit of work, and they're wildly heterogeneous:** ~17 cheap (HTML/stable-URL
   states), ~22 routine (PDF-parsing states), ~8 expensive (fragmented/paywalled/OCR states). A
   pdftotext-plus-regex pipeline with per-state templates covers the middle tier; the easy tier is
   plain HTML scraping; the hard tier should be deferred or served via email-subscription parsing.
3. **Email subscriptions are load-bearing infrastructure**, not a fallback: in ~25 states the
   state-run email service is the only push channel, and in several (NE statewide docket alerts,
   KS agency-filterable, MO account-based) it's the most reliable change signal. A state substrate
   wants a first-class inbound-email ingestion path (unique address per state subscription →
   parser → observation log).
4. **Deadline extraction is a text problem even in easy states.** Only a few systems expose
   comment-close dates as structured fields (UT filings, CT/RI listings, VA Town Hall, CARB
   dockets, MD's PertinentDates.pdf). Everywhere else the deadline lives in notice prose — the
   RuleBox + LLM-adjudicator pattern (deterministic first, model for borderline) is the right
   shape, and the gold-corpus eval approach ports state-by-state.
5. **Volume is manageable.** State registers are weekly/biweekly/monthly documents with dozens
   (not thousands) of notices per issue; 51 jurisdictions at full coverage is plausibly a few
   hundred notices/week — of the same order as the federal stream DocketClock already handles.
6. **Sequencing suggestion from the data:** (a) **CARB-only adapter** — answers the actual
   prospect, EASY-rated, days not weeks; (b) **CA Z Register** — generalizes to all CA agencies,
   MODERATE; (c) **the EASY tier** (WA, TX, UT, KS, PA, VA, DE, RI, ME, IN, WI) — 11 states that
   are mostly HTML with stable URLs, several with RSS/portals to cross-check; (d) the MODERATE
   PDF tier by demand; defer GA/HI/NE/NV/TN/MS/MA/NJ until there's a paying reason.
7. **Two-source reconciliation has state analogues.** Several states naturally provide the
   FR + Regulations.gov dual-source pattern: register + portal (VA, IA, SD, CO, WI, MI), register +
   review-body tracker (PA Bulletin + IRRC, IL Register + JCAR/Flinn Report), register + agency
   docket (CA Z Register + CARB). Confidence scoring carries over unchanged.

## Verification status & follow-ups

- **Method:** five parallel regional research agents (each verifying against official .gov sources
  via web search) produced the per-state findings; a separate deep-research workflow ran a
  search→fetch→adversarial-verify pipeline for the cross-cutting claims. The workflow's
  verification phase failed on API rate limits, so its claims (MSAPA details, StateScape
  mechanics, register-lag) are extracted-but-unverified; where they overlap the regional agents'
  findings they are independently corroborated.
- Statutory citations were verified to search-snippet level, not always full-text; cite-level
  flags are inline in [`state-by-state.md`](state-by-state.md). Highest-value re-checks: WV
  § 29A-3-5, NC 150B-21.2(f), AL § 41-22-5, TN § 4-5-203/204.
- The sandbox egress proxy 403'd most state .gov hosts, so **bot-blocking observations (FL, TN,
  MS, AL, OAL) may be proxy artifacts** — re-test scrapeability from an unrestricted network
  before finalizing EASY/MODERATE/HARD ratings.
- Unverified leads worth one manual check each: AR bulk-data-download contents; exact feed list at
  rules.utah.gov/rssfeeds/; DE Notification Service register coverage; NC OAH email list; MS
  adminsearch email signup; DC on-site notification signup; whether rulemaking.colorado.gov
  accepts comments directly.
- Live-status caveat: WI's legacy adminrules.wisconsin.gov failed DNS in July 2026; the
  legislature-site comment links are the operative path.
