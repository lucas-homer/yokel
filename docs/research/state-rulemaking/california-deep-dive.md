# California Deep-Dive: OAL, the Z Register, and CARB

> Companion to [`README.md`](README.md) and [`state-by-state.md`](state-by-state.md). California
> gets extra depth because a CARB (California Air Resources Board) contact asked whether
> DocketClock has a state-level equivalent — making CA both the first prospective user's home state
> and one of the highest-volume rulemaking states.

## The publication pipeline

**Publisher:** Office of Administrative Law (OAL), a small executive-branch agency that reviews all
regular rulemaking for legal sufficiency and publishes the notice stream.

**Vehicle:** The **California Regulatory Notice Register**, universally nicknamed the **"Z
Register"** (issues are numbered `N-Z`, e.g. "2026 Notice Register No. 17-Z"). Published **weekly,
every Friday**. Agencies must deliver a Notice of Proposed Action (NOPA) to OAL **at least 10
calendar days before** the intended publication date.

- Landing: <https://oal.ca.gov/publications/notice_register/>
- Online access: <https://oal.ca.gov/california_regulatory_notice_online/>

## Format and URL mechanics (adapter-relevant)

- **PDF-only issues** — one PDF per week, an exact copy of the print edition. Text-based (not
  scanned), with a consistent internal digest layout per action ("TITLE — DEPARTMENT — Notice
  published…").
- Issues are linked from **monthly HTML table-of-contents landing pages**, e.g.
  `https://oal.ca.gov/february-2026-california-regulatory-notice-registers/`.
- PDF URL pattern (WordPress uploads):
  `https://oal.ca.gov/wp-content/uploads/sites/166/{YYYY}/{MM}/{YYYY}-Notice-Register-No.-{N}-Z-{Month}-{D}-{YYYY}.pdf`
  — **but filenames are hand-typed and inconsistent** (observed: stray `-1` suffixes, "Volume
  Number N-Z" variants, two issues metadata-dated the same day; the naming convention also
  changed between 2023 and 2024). URLs are stable once posted but **not reliably constructible in
  advance** → enumerate by scraping the monthly TOC pages for anchor links, never by URL
  construction. *(Pattern verified 2-1 against 10+ independently indexed OAL PDFs spanning
  2020–2025.)*
- OAL publishes a **Notice Register Publication Schedule** (currently covering Jan 2026–Jul 2027)
  listing every weekly publication date and the 10-day submission deadline — a free lookahead
  calendar for poller scheduling.
- **History cliff:** online back-issues exist **from January 1, 2018 only**. In 2019 OAL deleted
  all pre-2018 Notice Registers from its site for accessibility compliance (Gov. Code § 11546.7).
  2002–2017 issues survive only in the California State Web Archive (Archive-It collection 5763).
- **Anti-bot friction — plausible but unconfirmed:** direct HTTP fetches of oal.ca.gov returned
  403 in our environment, but the adversarial-verification panel refuted (1-2) the claim that OAL
  categorically blocks automated clients — the observed 403s may be a sandbox-proxy artifact.
  Budget for realistic browser headers, but test from a normal network first.
- Print subscription is commercial via Thomson Reuters (~$409/yr) — irrelevant to ingestion but a
  signal that the state has outsourced distribution rather than invested in digital.

## Machine-readability: effectively none

- **No API, no RSS/Atom/JSON/XML feed, no bulk download, no structured index.** Law-library guides
  state flatly that the Register "does not include an indexing system for search and retrieval."
- **Email:** a manual mailing list — email `oalproposedrulemakings@oal.ca.gov` and ask to be added.
- Adjacent (post-comment stage, not notice stage): OAL's "Proposed Regulations Under Review" HTML
  page lists rulemaking files at OAL for final review: <https://oal.ca.gov/proposed-regulations/>.
- **No third-party open-data effort found** that parses the Z Register — no GitHub scrapers, no
  data.ca.gov dataset. Coverage is commercial only (LexisNexis State Net, StateScape). **This is a
  genuinely open niche.**

## Comment mechanics: no central portal, ever

California has **no centralized comment portal** — confirmed. Each agency runs its own docket; the
NOPA printed in the Z Register names the agency contact and deadline. The two big-agency systems a
CA wedge would meet first:

### CARB (the contact's agency) — the easy path

CARB is substantially easier to ingest than the Z Register itself:

- **Rulemaking hub:** <https://ww2.arb.ca.gov/rulemaking> with annual listings of every Section-100
  rulemaking filing 2018–present at <https://ww2.arb.ca.gov/rulemaking-activity> (per-year HTML
  list linking each rulemaking's formal-documents page); older material under `/rulemaking-archive`.
- **Predictable document tree:** formal docs (notice, ISOR/Staff Report, 15-day change packages)
  live under `https://ww2.arb.ca.gov/sites/default/files/barcu/regact/{YYYY}/{slug}/…`
  (e.g. `…/regact/2026/cap_invest/nc_notice.pdf`).
- **Electronic comment docket:** front door
  <https://ww2.arb.ca.gov/applications/public-comments> (web form + attachment upload); the legacy
  application is still live at `https://www.arb.ca.gov/lispub/comm/bclist.php` ("Choose Comment
  Item") — **each open docket is one open comment period with a machine-readable deadline column**.
  Dockets stay open through the 45-day period, any 15-day supplemental periods, and (for Board
  items) until the Chair closes the record. All submissions are public and browsable via per-docket
  Comment Logs.
- **GovDelivery e-notification:** topic-based listserv at
  `https://public.govdelivery.com/accounts/CARB/subscriber/new` — all rulemaking notices, 15-day
  modified-text availability notices, and workshop announcements go out as bulletins (archived at
  `content.govdelivery.com/accounts/CARB/bulletins/…`). **The most machine-adjacent CA notice
  stream.**

### CPUC — a separate regime entirely

CPUC proceedings are quasi-legislative dockets outside OAL rulemaking: Docket Card system at
`https://apps.cpuc.ca.gov/apex/f?p=401:1:0`, per-proceeding "PUBLIC COMMENTS" tab with an "ADD
PUBLIC COMMENTS" form (4,000-word/2-page limit, comments published online); documents at
`docs.cpuc.ca.gov`. If DocketClock ever covers CPUC, it's a separate adapter with different
semantics.

## Comment-period law (deadline semantics)

- **45-day minimum:** Gov. Code **§ 11346.4(a)** — notice must be given at least 45 days before
  the hearing and close of the public comment period.
- **15-day comment period on modified text:** Gov. Code **§ 11346.8(c)** + **1 CCR § 44** —
  sufficiently-related changes must be made available for at least 15 days before adoption, with
  mailed notice to hearing participants/commenters/requesters. → CA natively produces the
  "reopened/extended window" pattern DocketClock's chain-link classifier already models (15-day
  packages are the state analogue of an FR correction/extension notice).
- **One-year clock:** a rulemaking lapses if not completed within one year of NOPA publication —
  a natural window-expiry semantic.

## Ingestion assessment

| Target | Rating | Approach |
|---|---|---|
| Z Register (all CA agencies) | **MODERATE** | Weekly scrape of monthly TOC pages → fetch issue PDF → parse per-action digest blocks for agency, subject, comment deadline, hearing date. Layout is consistent; no feed; filenames irregular. |
| CARB only | **EASY** | Poll `rulemaking-activity` + lispub docket list (deadline column!); subscribe to GovDelivery bulletins as push trigger; documents from the predictable `barcu/regact` tree. |

**Strategic note:** the CARB contact's "do you have this for state level?" can be answered with a
CARB-only adapter well before a general CA adapter: CARB's own systems expose everything a
`ParticipationWindow` needs (open dockets, deadlines, 15-day reopenings, hearing dates) without
touching the Z Register. The Z Register adapter is the generalization, and its per-action digest
is the reconciliation cross-check — the same two-source pattern DocketClock already uses for
FR + Regulations.gov.
