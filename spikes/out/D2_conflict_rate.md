# D2 — FR ↔ Regs.gov Eastern-date conflict rate

**Run:** 2026-06-14 (Eastern) · over the D1 join (`data/fr_open.json` ⋈ `data/regs_open.json`)

## Counts (both dates normalized to America/New_York)

| metric | value |
| --- | ---: |
| joined pairs with both dates present | 932 |
| **true_conflicts** (Eastern dates disagree) | **12** |
| **conflict_pct** | **1.29%** |
| naive UTC conflicts (date-slice the `Z` timestamp) | 932 (100%) |
| **tz_false_positives** suppressed by the Eastern rule | **920** |

> The naive UTC compare would flag **932** conflicts (100%); after Eastern
> normalization only **12** (1.29%) are real. The difference —
> **920** rows — is pure timezone noise the rule removes.

## Decision (positioning, no kill)

**conflict_pct = 1.29% → borderline (1–3%) — conflicts is a real but secondary feature; lean on alerts, keep `/conflicts`.**

- **Eastern-normalization rule: ✅ CONFIRMED NECESSARY.**
  920 pair(s) differ in UTC but agree in Eastern — a naive UTC threshold would have raised 920 false "conflict" alert(s).

## True conflicts — hand-verify these are real (extension/correction), not parse bugs

| frDocNum | FR Eastern | Regs Eastern | Regs UTC (naive) | Regs raw | type | title |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10910 | 2026-07-01 | 2026-08-10 | 2026-08-11 | 2026-08-11 03:59:59 | Notice | Melamine From China; Institution of Five-Year Reviews |
| 2026-10911 | 2026-07-01 | 2026-08-10 | 2026-08-11 | 2026-08-11 03:59:59 | Notice | Potassium Phosphate Salts From China; Institution of Five-Year Reviews |
| 2026-10912 | 2026-07-01 | 2026-08-10 | 2026-08-11 | 2026-08-11 03:59:59 | Notice | Walk-Behind Lawn Mowers From China and Vietnam; Institution of Five-Ye |
| 2026-10914 | 2026-07-01 | 2026-08-10 | 2026-08-11 | 2026-08-11 03:59:59 | Notice | Cut-to-Length Carbon Steel Plate From China, Russia, and Ukraine; Inst |
| 2026-10915 | 2026-07-01 | 2026-08-10 | 2026-08-11 | 2026-08-11 03:59:59 | Notice | Passenger Vehicle and Light Truck Tires From South Korea, Taiwan, Thai |
| 2026-10407 | 2026-06-25 | 2026-07-27 | 2026-07-28 | 2026-07-28 03:59:59 | Proposed Rule | Enhancing Know-Your-Customer Requirements |
| 2026-11353 | 2026-08-04 | 2026-09-03 | 2026-09-04 | 2026-09-04 03:59:59 | Proposed Rule | Reforming the High-Cost Program for an All-IP Future, Connect America  |
| 2026-09821 | 2026-06-15 | 2026-07-14 | 2026-07-15 | 2026-07-15 03:59:59 | Proposed Rule | Promoting the Integrity and Security of Telecommunications Certificati |
| 2026-09819 | 2026-06-15 | 2026-06-29 | 2026-06-30 | 2026-06-30 03:59:59 | Proposed Rule | Accessible Emergency Information, and Apparatus Requirements for Emerg |
| 2026-11157 | 2026-07-27 | 2026-08-03 | 2026-08-04 | 2026-08-04 03:59:59 | Proposed Rule | Periodic Reporting |
| 2026-10115 | 2026-06-22 | 2026-06-20 | 2026-06-21 | 2026-06-21 03:59:59 | Notice | Privacy Act of 1974; Matching Program |
| 2026-07304 | 2026-06-15 | 2026-06-16 | 2026-06-17 | 2026-06-17 03:59:59 | Notice | Agency Information Collection Activities; Comment Request; Foreign Gif |

## Timezone false-positives — the rule working (naive UTC ≠, Eastern =)

| frDocNum | FR Eastern | Regs Eastern | Regs UTC (naive) | Regs raw | type | title |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-23266 | 2026-06-16 | 2026-06-16 | 2026-06-17 | 2026-06-17 03:59:59 | Notice | Notice of Intent To Designate as Abandoned Stephen M. Hill Supplementa |
| 2026-01141 | 2026-06-30 | 2026-06-30 | 2026-07-01 | 2026-07-01 03:59:59 | Rule | Revising Definition of “Unlawful User of or Addicted to Controlled Sub |
| 2026-01446 | 2026-07-27 | 2026-07-27 | 2026-07-28 | 2026-07-28 03:59:59 | Notice | Notice of Intent To Designate as Abandoned R.J. Schroers Supplemental  |
| 2026-01903 | 2026-12-31 | 2026-12-31 | 2027-01-01 | 2027-01-01 04:59:59 | Notice | FDA Rare Disease Innovation Hub Future Programming; Request for Commen |
| 2026-03046 | 2026-08-17 | 2026-08-17 | 2026-08-18 | 2026-08-18 03:59:59 | Notice | Notice of Intent To Designate as Abandoned New Systems Supplemental Ty |
| 2026-03961 | 2026-07-10 | 2026-07-10 | 2026-07-11 | 2026-07-11 03:59:59 | Notice | Fiscal Year 2026 Generic Drug Science and Research Initiatives Worksho |
| 2026-05324 | 2026-09-15 | 2026-09-15 | 2026-09-16 | 2026-09-16 03:59:59 | Notice | Notice of Intent To Designate as Abandoned Century Flight Systems, Inc |
| 2026-05678 | 2026-06-22 | 2026-06-22 | 2026-06-23 | 2026-06-23 03:59:59 | Proposed Rule | Endangered and Threatened Wildlife and Plants; Designation of Critical |

_Eyeball the true-conflict titles above: an extension/correction notice that genuinely moved the
deadline is a real conflict; a same-deadline row that only differs by a day at the UTC boundary is not._
