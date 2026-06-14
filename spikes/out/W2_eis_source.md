# W2 — EPA EIS database machine-readability

**Run:** 2026-06-14 (Eastern)

## Endpoint probes

| source | HTTP | content-type | machine-readable? | note |
| --- | ---: | --- | :---: | --- |
| EPA EIS search app (cdxapps) | 200 | `text/html` | ❌ | the public EIS search UI |
| cdxapps guessed REST backend | 404 | `text/html` | ❌ | common REST path |
| cdxapps guessed JSON API | 404 | `text/html` | ❌ | common API path |
| EPA Envirofacts efservice | 404 | `text/html` | ❌ | REST data service base (is EIS a table?) |

**Finding:** the EPA EIS search app returns **HTML** (a JSF web app); guessed REST/JSON backends 404; Envirofacts has no EIS table. EPA's own EIS database is **scraper-only**.

## Machine-readable spine: Federal Register EIS-notice stream (keyless)

The FR API carries individual agency EIS notices (NOI / Draft / Final) **and** EPA's weekly
consolidated "Notice of Availability." It is keyless, stable, and directly extractable.

| field | directly available? |
| --- | --- |
| title | ✅ (from `title`) |
| link | ✅ (`html_url`) |
| publication date | ✅ (`publication_date`) |
| comment close date | ⚠️ `comments_close_on` present on 17/51 of the sample |
| draft/final stage | ⚠️ parsed from title — 14/51 classified |
| state(s) | ⚠️ parsed from title — 18/51 had a state in the title |

_1-month sample: **51** FR EIS notices (2026-05-15 → 2026-06-14)._

## Decision

**GO (with guardrails) — EPA's EIS DB is **scraper-only**; ship the adapter behind an interface with the FR EIS-notice stream as the machine-readable spine/cross-check.**

- Build the EIS adapter **behind an interface** (`EisSource`) so the EPA scraper and the FR spine are
  swappable; cross-check dates between them. Budget scraper maintenance explicitly and treat EPA DOM
  changes as expected breakage, with FR as the always-on fallback.

## 1-month EIS sample (first 30 of 51)

| published | stage | comment close | state(s) | agency | title |
| --- | --- | --- | --- | --- | --- |
| 2026-06-04 | — | — | Texas | Transportation Departm | Environmental Impact Statement: Waller County, Texas |
| 2026-06-02 | Draft | — | — | National Aeronautics a | Draft Environmental Impact Statement for the Berkeley Space  |
| 2026-05-29 | — | 2026-06-22 | — | Homeland Security Depa | Shipping Safety Fairways and Associated Vessel Routing Measu |
| 2026-05-29 | NOI | 2026-06-29 | Idaho | Interior Department | Notice of Intent To Prepare an Environmental Impact Statemen |
| 2026-06-11 | NOI | 2026-07-13 | — | Nuclear Regulatory Com | Orano Enrichment USA LLC; Uranium Enrichment Facility; Notic |
| 2026-06-15 | — | — | Montana | Agriculture Department | Custer Gallatin National Forest; Montana; Stillwater Mine Co |
| 2026-05-19 | NOI | 2026-07-06 | Alaska | Interior Department | Notice of Intent To Prepare an Environmental Impact Statemen |
| 2026-05-27 | — | — | — | Agriculture Department | White River National Forest; Eagle County, CO; Camp Hale Res |
| 2026-05-19 | NOI | 2026-06-18 | — | Commerce Department | Notice of Intent To Prepare a Supplemental Programmatic Envi |
| 2026-06-05 | Final | — | North Dakota | Defense Department | Notice of Availability of the Record of Decision for the Fin |
| 2026-05-26 | — | — | Oregon | Agriculture Department | Rescission Notice; Owyhee Irrigation District Infrastructure |
| 2026-05-21 | NOI | — | Michigan | Defense Department | Notice of Intent To Prepare an Environmental Impact Statemen |
| 2026-06-01 | NOI | 2026-07-01 | — | Transportation Departm | Notice of Intent To Prepare an Environmental Impact Statemen |
| 2026-06-15 | NOI | 2026-07-15 | — | Nuclear Regulatory Com | Palisades SMR, LLC; Pioneer Units 1 and 2; Phased Constructi |
| 2026-06-01 | — | 2026-07-16 | — | Interior Department | Notice of Realty Action: Calcasieu Pass Non-Competitive Dire |
| 2026-05-29 | — | — | Wyoming | Agriculture Department | Caribou-Targhee National Forest; Wyoming; Amendment to the 1 |
| 2026-05-20 | — | — | — | Nuclear Regulatory Com | Long Mott Energy, LLC; Long Mott Generating Station; Environ |
| 2026-06-10 | — | — | — | Nuclear Regulatory Com | Holtec Decommissioning International, LLC; Oyster Creek Nucl |
| 2026-05-18 | Draft | 2026-06-17 | Louisiana | Commerce Department | Deepwater Horizon Louisiana Trustee Implementation Group Dra |
| 2026-05-29 | — | — | — | Environmental Protecti | Environmental Impact Statements; Notice of Availability |
| 2026-06-05 | — | — | — | Environmental Protecti | Environmental Impact Statements; Notice of Availability |
| 2026-05-29 | — | 2026-06-29 | — | Commerce Department | Marine Mammals; File No. 29749 |
| 2026-05-19 | — | 2026-06-18 | — | Commerce Department | Marine Mammals; File No. 29621 |
| 2026-05-21 | — | — | — | Commerce Department | Marine Mammals and Endangered Species |
| 2026-06-08 | — | 2026-07-08 | Alabama | Interior Department | General Conservation Plan for the Alabama Beach Mouse; Categ |
| 2026-06-10 | — | — | Nebraska | Nuclear Regulatory Com | Nebraska Public Power District; Cooper Nuclear Station; Subs |
| 2026-05-15 | — | 2026-08-13 | — | Energy Department | Proposed Rate Adjustment, Jim Woodruff Project |
| 2026-06-11 | NOI | — | — | Energy Department | City of Spokane; Notice of Intent To File License Applicatio |
| 2026-05-29 | — | — | — | Interior Department | National Environmental Policy Act Implementing Procedures fo |
| 2026-05-29 | NOI | — | — | Energy Department | Lock+TM Hydro Friends Fund X, LLC; Notice of Intent To File  |

_Artifact: `data/w2_eis_sample.json` (51 records + probe results)._
