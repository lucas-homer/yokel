# Census scope decisions (signed by the owner as proposed, 2026-10-15)

The four `UNIVERSE.md` files raise 38 reviewer questions. Five are strategic and go to the owner
directly (marked **owner**). For the rest, the primary proposes the answers below. Unless the owner
edits a line, signing this file signs these answers. Question numbers refer to each state's
`UNIVERSE.md`.

Principle for the defaults: count what a member of the public could act on, as the source states
it. Don't manufacture opportunities from statute alone. Keep every excluded class visible as a
labelled exclusion that the audit inspects.

## Cross-state (owner, decided 2026-10-15; see `../rights/DECISIONS.md` items 5–9)

- Cross-checks: **allowed** (agency pages, read-only). Statute lookups: **allowed**. CT JSON: **allowed**.
- TN: owner to send outreach; ADR 0013 amended for one backup hard candidate.
- Review budget: 4 h/state, 6 h for VA and CT.

The questions as originally raised:

- **Independent-lineage cross-checks.** Every process in every state is currently single-lineage,
  so completeness is "not established" everywhere and no state could make a statewide claim.
  Affects WA Q7, VA Q8, CT Q5 and TN Q5.
- **Statute and code lookups.** Read-only, non-retained lookups to verify cited sections and to
  enumerate agency rosters. Affects WA Q10 and VA Q10.
- **CT history JSON routes.** Affects CT Q3.
- **TN access.** Affects TN Q1 and Q7.
- **Review budget.** Affects VA Q12 and CT Q8.

## WA

| Q | Proposed answer |
| --- | --- |
| 1 | Include a CR-101 only when its body states a dated comment deadline or a scheduled public meeting on the rule, labelled `early_stage`. |
| 2a | Exclude local clean-air agencies as local government (labelled exclusion). |
| 2b | Exclude the Columbia River Gorge Commission for v1 (bi-state compact; labelled exclusion). |
| 3 | Yes: a supplemental notice is an independently reopened round. |
| 4 | Yes: CR-105 objection windows count, subtype `objection`. |
| 5 | Yes: inspect every MISC body; include those that open or change a window or hearing. |
| 6 | One hearing opportunity per notice. Each date or session is recorded on it and every one is checked for date accuracy. |
| 8 | 13-week interval `[2026-06-03, 2026-09-02)` America/Los_Angeles. |
| 9a, 9b | Yes, yes. |

## VA

| Q | Proposed answer |
| --- | --- |
| 1 | Yes, include NOIRA comment windows and any hearing-request offer. |
| 2 | Yes, include APA-exempt agencies that publish proposals with deadlines; yes, SCC "hearing upon request" is a hearing-request window. |
| 3 | Yes, subtype `periodic_review`, deduped against a NOIRA it piggybacks on. |
| 4 | Yes, exclude the final-adoption request window; record finals as rejects. |
| 5 | Yes, `early_stage` when a deadline is dated (symmetric with WA Q1). |
| 6 | Yes, exclude DMAS State Plan notices (labelled exclusion). |
| 7 | Option (a): 26 weeks `[2026-01-26, 2026-07-27)` America/New_York, with the predeclared backward extension. |
| 9 | Yes, a named coverage gap until Town Hall is cleared. |
| 11 | Yes, non-authoritative early signal only; publication = issue date. |

## CT

| Q | Proposed answer |
| --- | --- |
| 1 | No: count only notice-stated hearing-request windows. Statutory-only windows are recorded as an annotation, not scored. |
| 2 | Yes, conditional hearings count, with the condition retained. |
| 4 | No for v1, labelled exclusion. |
| 6 | Yes, subscribe to the eRegulations e-mail notifications as a same-lineage timeliness probe (owner signs up). |
| 7 | Yes, accept the excluded-entity list. |
| 8 | Option A: `[2024-10-14, 2026-10-12)`, about 107 projected; state the shortfall honestly. |
| 9 | Yes: NODs are lifecycle updates; "will not proceed" is a withdrawal-type event. |

## TN

| Q | Proposed answer |
| --- | --- |
| 2 | Yes, `PendingRules.php` once access returns. |
| 3 | Yes, a separate written-comment opportunity with a relative close. |
| 4 | Yes, the volume-based month-extension rule, capped at 12 months. |
| 6 | No for v1 (TPUC and other agency dockets are a labelled exclusion). |

## MS (signed by the owner as proposed, 2026-10-15)

Questions refer to `MS/UNIVERSE.md`.

| Q | Proposed answer |
| --- | --- |
| 1 | Option A: `[2026-05-18, 2026-08-17)` America/Chicago, 13 weeks, about 246–285 projected. The interval rule was set after the weekly volumes had been seen, as the file discloses. |
| 2 | Relative closes anchored to the FILED stamp. The stamp + N days date is kept as a non-asserted annotation only. |
| 3 | Yes: agency-stated closes are separate-lineage evidence; the role is `conflicting` until human precedence review. |
| 4 | Yes: count a comment window only where some source states one. |
| 5 | Yes: the hearing-request window is its own opportunity, conditional on "not scheduled". Forms ticking neither box are mandatory review cases. |
| 6 | Yes, and yes: separate hearing notices count, linked to their proposal; temporary rules are a labelled, inspected exclusion. |
| 7 | Yes: finals are closure evidence only; "Withdrawn" forms are withdrawal updates. |
| 8a, 8b | Yes; no for Phase 1. |
| 9 | **Primary override: full coverage**, about 3,310 credits plus a 150-credit hold for retries. This is funded from WA, VA and CT, whose scoping estimates (0–300, 0–200, 220–540) leave most of their 2,000 each unused. The Phase 1 cap stays 12,000 credits in total. |
| 10a, 10b | Yes, yes. |
| 11 | Yes. |
| 12 | **Owner:** MS gets 6 hours, and every decisive visual mark (hearing checkbox, filing stamp) is human-reviewed, as the protocol requires. |
| 13 | **Owner:** yes, read-only non-retained statute lookups (see `../rights/DECISIONS.md` item 15). |
| 14 | Yes: the FILED stamp is the publication-time proxy, and posting lag is recorded as unmeasured. |
