# CT owner sheet — proposed, unsigned

The owner decides all 104 items; agent agreement is not a verdict. C1–C16 follow class queue order; K01–K88 follow case queue order. Full item/target IDs and fuller evidence notes are in `proposed-adjudications.jsonl`. No signed log or sealed input was changed. Drafts deliberately use `primary`, `proposed`, `draft:true` and null human fields, outside the signed-adjudication schema; never ingest them as verdicts.

## Part 1 — Class questions

Counts are direct A/B label-record versions / queue instances, with overlap between classes; not unique opportunities. C16 is 25 source completion rows involving 755 linked labels. Every proposed policy awaits owner signature.

**C1. Which cohort for updates on older proceedings?** older_proceeding_update. PROTOCOL §2/brief explicitly define this cohort. **24 records / 12 instances.** Quote: “even if previously closed.” (PROTOCOL §2).

**C2. Do natural ends and passive snapshots count as updates?** Keep explicit closure actions; reject passive snapshots as non_notice. The brief includes actions/NODs; unchanged listings show status only. **73 records / 73 instances.** Quote: “participation changes” (brief Scope).

**C3. Does history alone create a separate notice?** History stays update/proceeding evidence; no extra notice without notice evidence. PROTOCOL §5 forbids blessing unread sources; recover bodies/exceptions separately. **11 records / 11 instances.** Quote: “A missing-source review cannot declare unread evidence harmless” (PROTOCOL §5).

**C4. Can document-backed updates lack before-evidence?** Retain diagnostic updates with missing-before reasons; add supplied opening evidence. PROTOCOL §6 already permits this, without establishing completeness. **114 records / 58 instances.** Quote: “a specific reason and human review.” (PROTOCOL §6).

**C5. Can a history withdrawal lack before-evidence?** Retain diagnostic withdrawal; decide PR2023-031 separately. PROTOCOL §§5–6 require separate target/identity review. **2 records / 1 instances.** Quote: “Do not invent a prior opportunity.” (PROTOCOL §6).

**C6. Can other history actions lack before-evidence?** Retain explicit actions diagnostically; reject passive snapshots under C2. PROTOCOL §6 requires explicit gaps and human review. **59 records / 59 instances.** Quote: “it blocks established completeness until resolved.” (PROTOCOL §6).

**C7. Does an undated conditional hearing count?** Retain opportunity/condition, unknown date and fulfillment. Signed CT Q2/brief already include these, superseding UNIVERSE’s older planning sentence. **20 records / 10 instances.** Quote: “conditional hearings count” (brief Scope; signed CT Q2).

**C8. Is “shall end on” inclusive?** Unknown cutoff; preserve stated date/time. No signed endpoint policy exists; PROTOCOL §5 preserves uncertainty. **14 records / 7 instances.** Quote: “Unresolved dates remain `unknown` or `conflicting`” (PROTOCOL §5).

**C9. Is “no/not later than” inclusive?** Propose inclusive endpoint, at stated precision. Literal wording supports this proposed policy, without adding time/zone. **34 records / 17 instances.** Quote: “no later than 5 pm on September 2, 2025” (PR2025-008 NOI, p2 (queue representative)).

**C10. Is a relative “not later than” inclusive?** Propose inclusive endpoint wording; leave date uncomputed. The brief preserves relative clocks; endpoint wording cannot resolve day counting. **22 records / 11 instances.** Quote: “Relative periods retain literal anchor/counting rule” (brief TEMPORAL FIELDS).

**C11. What cutoff for “within N days”?** Unknown cutoff and uncomputed close. No signed counting policy exists; PROTOCOL §5 forbids fabricated deadlines. **2 records / 1 instances.** Quote: “an unasserted computed close leaves local_value/utc_value null” (brief TEMPORAL FIELDS).

**C12. Is “through” inclusive?** Propose inclusive date endpoint. Literal wording supports this proposal, without adding time/zone. **2 records / 1 instances.** Quote: “through February 17, 2025.” (PR2022-002 NOI, p2 item 4 (queue representative)).

**C13. What cutoff for hearing sessions?** not_applicable. Session roles are not submission cutoffs; retain dates/status (brief). **34 records / 17 instances.** Quote: “every session as applicable.” (brief TEMPORAL FIELDS).

**C14. What cutoff for openings?** not_applicable. Opening roles have no submission cutoff; date/support still need checking. **100 records / 50 instances.** Quote: “not automatically participation deadlines.” (brief TEMPORAL FIELDS).

**C15. Keep explicit opening roles?** Explicit open: supported wording or unknown/null. The brief requires applicable open roles, independently of publication metadata. **36 records / 18 instances.** Quote: “use "not stated"” (brief TEMPORAL FIELDS).

**C16. What do completion candidate counts mean?** Final source-view attribution, corrected append-only. The brief defines attribution; PROTOCOL §4 forbids summing views. Verify the supplement; preserve seals. **755 records / 25 instances.** Quote: “Counts may overlap across views.” (brief INSPECTION AND COMPLETION).

## Part 2 — Cases, grouped by proceeding and impact

**LOOK** requires personal source inspection: gaps, scope/role calls, conflicts, reopening identities, visuals and all low-confidence cases. Other rows need owner confirmation. Confidence rates the proposal only; C-references are unsigned policies.

**Exact entry-ID notation:** under each proceeding heading, “NOI X”, “NOD X” and “extension X” mean `ct-doc-<heading>-noi-X`, `ct-doc-<heading>-nod-X` and `ct-doc-<heading>-ext-X`; slashed suffixes identify both entries. “history” = `ct-json-getrmrhistory-<heading>` (row = RMRID), “notes” = `ct-json-getrmrnotes-<heading>`, “hearing details X” = `ct-json-hearing-<heading>-X`. “open list” = `ct-json-open-comment-periods`, row TrackingNumber = heading. Page numbers are original PDF pages. All are frozen originals mapped by `manifest.pass.jsonl`.

Case / stake | Passes | Checked original | Proposed resolution
---|---|---|---
**CT-source-gaps** | | |
K01 Unread sources; high **LOOK** | A/B: no inspection | ct-gap-law-journal: blocked; ct-xchk-portal-deep-rbcr: invalid_response; no originals | Retain both gaps; completeness not established.
**PR2024-037** | | |
K02 Wrong NOD target; low **LOOK** | A/B flag missing prior-state evidence | NOD 900788930000 p1: header 037/body 035; e0bd88930000 body 037 | Keep misfiled target conflicting; recover correction.
K71 Repost count; high | A duplicate; B notice/update | NOI c04204940300/10dc9f920000 p1: same rule, 11/21/2024 close; repost 12/26 | Duplicate/revised copy; preserve GUID alias, no new round or action.
**PR2025-016** | | |
K03 Missing hearing PDF; low **LOOK** | A extra notice; both scheduling/time conflict | hearing details 000380980000: 9/3/2025 11:31; history row 7 links missing PDF | C3 evidence only; retain 11:30/11:31 conflict.
K51 One-minute conflict; low **LOOK** | A/B conflicting | NOI d0897b980000 p2: 9/3 11:30; hearing details 000380980000: 11:31 | Keep conflict; missing hearing PDF prevents precedence.
K43 Withdrawal targets; high | A/B full withdrawal | history row 18: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K78 Signed duplicate; high | A duplicate; B notice/update | NOI 70a87b980000/d0897b980000 pp1–2: same close/hearing, signature differs | One notice/round; signed copy evidence. K51 time conflict remains.
K26 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 18: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2025-020** | | |
K04 Missing attachments; medium **LOOK** | Both notice/hearing; B extra scheduling update | history row 7; hearing details 3052f1980000: 9/17/2025 12:30 | Retain supported session/action, C3 no extra notice; gap remains.
K79 Scheduling action; medium **LOOK** | A new notice/no update; B update cohort/action | history row 7 + hearing details 3052f1980000: 9/17/2025 12:30 | One initial-scheduling action, unknown enum; C3 no separate history notice; PDFs missing.
K44 Withdrawal targets; high | A/B full withdrawal | history row 24: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K27 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 24: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2025-021** | | |
K05 Two sessions; medium **LOOK** | A/B two history notices and two actions | hearing details 704c16990000 and 604d16990000: 9/11 and 10/2/2025, 5 PM | Keep both sessions on NOI hearing; missing copies cannot add notices.
**PR2026-014** | | |
K06 Missing NOD; medium **LOOK** | Both update; A also history notice | history row 7: NOD posted 10/15/2026; PDF absent | Follow-up-only evidence; decision meaning unknown (C3).
K85 Follow-up cohort; medium **LOOK** | A interval_update; B new_notice | history row 7 NOD 10/15/2026; NOI d09686a00000 posted 9/9 | Inherit new_notice, annotate follow_up_only/unscored; missing body remains gap.
**PR2022-002** | | |
K30 Reopened round; high **LOOK** | A/B reopening | NOI 901171940000 p2: 1/17–2/17/2025; NOD c0a333920000 p1 cites 2022 NOI | Separate 2025 round; earlier closure is before-evidence.
K61 Opportunity cohort; medium **LOOK** | A new_notice; B adds older update | NOI 901171940000 posted header/body: fresh in-interval round | Propose new_notice on opportunities; older-update flag on reopening action.
**PR2023-031** | | |
K07 False carry-in; high **LOOK** | A/B carry-in candidates | history row 6: withdrawn 9/4/2024; NOI 60dfb8910000 p1 closes 10/15 | Remove scored carry-in from both; retain historical evidence.
K31 Withdrawal target; high | A/B full withdrawal | history row 6; NOI 60dfb8910000 p1 supplies prior comments window | Link NOI before/target; pre-start event unscored (K07).
K62 Pre-start cohort; high | A carry_in; B older update | history row 6: 9/4/2024 withdrawal | Neither interval cohort applies; preserve outside-interval evidence (K07).
K21 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 6: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2024-003** | | |
K34 Old/new rounds; high **LOOK** | A/B NOD + reopening | NOD c0888d930000 p2 cites 5/22/2024; NOI 707456980100 p1 closes 8/29/2025 | Separate 2025 round; restore historical target for old NOD.
K63 Opportunity cohort; medium **LOOK** | A new_notice; B adds older update | NOI 707456980100 posted header/body: fresh in-interval round | Propose new_notice on opportunities; older-update flag on reopening action.
**PR2024-023** | | |
K36 Three rounds; high **LOOK** | A/B two reopenings | NOI 904c56900000/d03b96920100/c097cd940100 p1 closes 7/31/2024, 11/18/2024, 3/7/2025 | Keep distinct NOI-guid rounds; link prior evidence and new-round targets.
K65 Latest-round target; medium **LOOK** | A latest; B also prior; B extra cohort | NOD 50418c950100 p1 cites February 3, 2025 NOI | Target February round only; new_notice on opportunities, old-update on reopening.
K48 Missing update close; high | A close; B none | NOI d03b96920100 p1: 11/18/2024 | Retain supported close on reopening and opportunity.
**PR2024-025** | | |
K66 Pre-start hearing; high **LOOK** | A excludes; B includes/adds carry_in | NOI 20c2ef900000 p3 hearing 10/10/2024; NOD 60ab65940000 p1 cites July NOI | Hearing not carry-in; comments may be. NOD only older-proceeding update.
K49 Contradictory close; medium **LOOK** | A supported; B conflicting | NOI 20c2ef900000 pp1–2: 10/24 vs 10/4 5 PM; 6050f0900100 p2: 10/24 5 PM | First version conflicting; propose revised-source precedence, same round.
**PR2024-031** | | |
K08 Withdrawal scope; high **LOOK** | A/B permanent withdrawal | history row 20: permanent; row 19: LRRC withdrawal | Keep permanent action; LRRC-stage withdrawal does not cancel participation.
K38 Withdrawal targets; high | A/B full withdrawal | history row 20: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K22 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 20: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2024-032** | | |
K09 Unfinished watch; high **LOOK** | A no snapshot; B unfinished-watch flag | NOI 70fbcaa00000 p1 closes 10/23/2026 4:30 PM; capture 10/15 | Include future window (§2); follow-up pending.
K58 Scanned close; high **LOOK** | A/B agree | NOI 70fbcaa00000 p1 image: 10/23/2026 4:30 PM; render `.census-passes/CT/review-renders/ct-review-037dfca2a8be4f9b29d8ee1b1d66eb1c7f5c52c6a779e9c70190231617b79c41.png` | Confirm printed close; retain precision and null unstated zone.
K50 Epoch precision; high | A absent; B unknown snapshot | open list row PR2024-032: /Date(1792787400000)/; NOI p1 image 10/23 4:30 PM | C2 reject event; keep printed local close, no invented UTC.
K67 Passive status; high | A absent; B update | open list PR2024-032: current close | C2 reject snapshot event; retain source (K50).
**PR2024-050** | | |
K10 Withdrawal scope; high **LOOK** | A/B permanent withdrawal | history row 55: permanent; row 54: LRRC withdrawal | Keep permanent action; LRRC-stage withdrawal does not cancel participation.
K39 Withdrawal targets; high | A/B full withdrawal | history row 55: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K23 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 55: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2024-053** | | |
K11 Withdrawal scope; high **LOOK** | A/B permanent withdrawal | history row 56: permanent; row 55: LRRC withdrawal | Keep permanent action; LRRC-stage withdrawal does not cancel participation.
K40 Withdrawal targets; high | A/B full withdrawal | history row 56: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K24 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 56: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2024-056** | | |
K74 Different-subject NOD; low **LOOK** | A correction; B unknown | NOD d0281d970000 p1 concerns PR2024-057; c08fa3970000 concerns 056 | Later decision unknown enum; earlier target conflicting, correction unproved.
**PR2024-059** | | |
K41 Separate reopening; high **LOOK** | A/B reopening | NOI 50603d950000/20195ea00000 p1: 2025 and 2026 rounds | Keep distinct NOI-guid rounds; earlier NOI supplies before-evidence.
K75 Hearings/cohorts; medium **LOOK** | A unknown/new; B not_scheduled/+update | NOI 50603d950000 pp2–3 and 20195ea00000 pp3–4: conditional hearings | Keep both offers/unknown fulfillment; new opportunities, linked reopening update.
**PR2025-008** | | |
K12 Duplicate decision; high **LOOK** | A duplicate; B extra notice/update | NOD f0f5e09a0000/f0b2ef9a0000 p1 differ only in 12/2 versus 12/5 dates | One decision, revised posting evidence; no extra action.
K76 NOD duplicate/status; high | A duplicate/unknown; B extra/not_scheduled | NOD f0f5e09a0000/f0b2ef9a0000 p1 differ only dates; NOI 60548a980000 p2 conditional | One decision; preserve repost evidence. Hearing fulfillment unknown.
**PR2025-014** | | |
K77 Meeting role; low **LOOK** | A comments only; B hearing/target | NOI 209aa0990000 p2 item 4: CFPC 10/28 meeting under written submissions; history row 6 withdraws 10/8 | Retain meeting channel; separate hearing unresolved. No safe extra scored hearing yet.
K42 Withdrawal targets; high | A/B full withdrawal | history row 6: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K25 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 6: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2025-027** | | |
K13 Agency/horizon scope; medium **LOOK** | A/B include | NOI 60c1cb9a0000 p1 invokes 4-168; history row 13 withdraws 9/15/2026 | Include UAPA notice and interval withdrawal despite expired watch horizon.
K46 Withdrawal targets; high | A/B full withdrawal | history row 13: explicit agency/permanent withdrawal | One action; link opening NOI/exact round, without inferred cancellation.
K28 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 13: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2025-036** | | |
K47 Withdrawal/reopening; high **LOOK** | A reopening; B also replacement | history row 8 withdraws 5/15; NOI 20501c9e0000/90e9409e0100 p1 posted 5/12/5/19 | Withdrawal plus one reopening; new-round targets, no extra replacement.
K82 Replacement count; high **LOOK** | A reopening/new; B replacement/extra action | history row 8 withdraws 5/15; NOI 90e9409e0100 posted 5/19 after 20501c9e0000 | Fresh NOI/new round; one reopening targeting new comments/hearing; no replacement proved.
K29 Duplicate action IDs; high | A/B withdrawal, different IDs | history row 8: same GUID in both passes | One canonical action; preserve both pass IDs in crosswalk.
**PR2026-001** | | |
K14 Agency scope; medium **LOOK** | A/B include provisionally | NOI b005a49b0000 p1: Criminal Justice Commission, 4-168(a) | Propose UAPA inclusion; owner confirms judicial-body exclusion boundary.
**PR2026-011** | | |
K15 Possible misposting; low **LOOK** | Both notice; B also notes snapshot | NOI 30c421a10000 pp1–2: General Conditions title, certificate body, PR2026-012 reference | Keep distinct candidate, conflicting scope; no merge by identical body.
K53 PDF/portal conflict; medium **LOOK** | A omits event; B flags conflict | NOI 30c421a10000 p1: 11/8/2026; notes CommentsPeriodEndDate: 11/10/2026 midnight | C2 reject event; preserve conflict on opportunity; no proven extension.
K83 Passive notes; high | A absent; B update | notes CommentsPeriodEndDate: 11/10 midnight, 2026; no dated change evidence | C2 reject event; retain conflicts/precision on opportunity (linked date case).
**PR2026-012** | | |
K16 Unfinished watch; high **LOOK** | Both notice; B also notes snapshot | NOI 10c821a10000 p1 closes 11/8/2026; capture 10/15 | Include future window (§2); follow-up pending.
K54 PDF/portal conflict; medium **LOOK** | A omits event; B flags conflict | NOI 10c821a10000 p1: 11/8/2026; notes CommentsPeriodEndDate: 11/11/2026 midnight | C2 reject event; preserve conflict on opportunity; no proven extension.
K84 Passive notes; high | A absent; B update | notes CommentsPeriodEndDate: 11/11 midnight, 2026; no dated change evidence | C2 reject event; retain conflicts/precision on opportunity (linked date case).
**PR2026-018** | | |
K17 Unfinished watch; high **LOOK** | Both notice; B also notes snapshot | NOI 10cb21a10000 p1 closes 11/10/2026; capture 10/15 | Include future window (§2); follow-up pending.
K55 Epoch precision; high | A absent; B unknown snapshot | open list: /Date(1794286800000)/; NOI 10cb21a10000 p1: 11/10/2026 | C2 reject event; date-only close, no inferred midnight cutoff.
K86 Passive notes; high | A absent; B update | notes CommentsPeriodEndDate: 11/10 midnight, 2026; no dated change evidence | C2 reject event; retain conflicts/precision on opportunity (linked date case).
**PR2026-020** | | |
K18 Unfinished watch; high **LOOK** | Both notice; B also notes snapshot | NOI b0cc21a10000 p1 closes 11/8/2026; capture 10/15 | Include future window (§2); follow-up pending.
K56 PDF/portal conflict; medium **LOOK** | A omits event; B flags conflict | NOI b0cc21a10000 p1: 11/8/2026; notes CommentsPeriodEndDate: 11/10/2026 midnight | C2 reject event; preserve conflict on opportunity; no proven extension.
K87 Passive notes; high | A absent; B update | notes CommentsPeriodEndDate: 11/10 midnight, 2026; no dated change evidence | C2 reject event; retain conflicts/precision on opportunity (linked date case).
**PR2026-021** | | |
K19 Boundary extension; high **LOOK** | A/B keep extension | extension 803bcea00000 p1: posted 9/23; 9/25 close becomes 10/12/2026 | Same opportunity; interval update, with 10/12 follow-up unscored.
**PR2026-024** | | |
K20 Unfinished watch; high **LOOK** | A no snapshot; B unfinished-watch flag | NOI 00cccaa00000 p1 closes 10/23/2026; capture 10/15 | Include future window (§2); follow-up pending.
K57 Extra portal time; medium **LOOK** | A absent; B unknown snapshot | open list: /Date(1792813500000)/; NOI 00cccaa00000 p1: 10/23/2026 | C2 reject event; portal time remains unreviewed evidence, not a legal cutoff.
K88 Passive notes; high | A absent; B update | notes CommentsPeriodEndDate: 10/23 11:45 PM, 2026; no dated change evidence | C2 reject event; retain conflicts/precision on opportunity (linked date case).
**PR2025-012** | | |
K59 Scanned close; high **LOOK** | A/B agree | NOI f0c331970000 p1 image: 7/3/2025; render `.census-passes/CT/review-renders/ct-review-e0d0c45bbbaaf698532946ff3f48ef4424391623510cc3125ec499d1dbd5ebc4.png` | Confirm printed close; retain precision and null unstated zone.
**PR2026-005** | | |
K60 Scanned close; high **LOOK** | A/B agree | NOI 20ad4e9c0000 p1 image: 3/16/2026; render `.census-passes/CT/review-renders/ct-review-dc2509d8b03c4b33cb2413cfd6e0a8897572dda33bb42a8db6a46387842e5691.png` | Confirm printed close; retain precision and null unstated zone.
**PR2025-035** | | |
K52 Wrong weekday; medium **LOOK** | A supported; B conflicting | NOI f019459d0000 p2: Monday, April 14, 2026, 5 PM; date is Tuesday | Keep conflicting; do not silently move date to Monday.
**PR2023-034** | | |
K32 Historical target; high | A/B empty target | NOD e0990c930000 p1 cites 4/29/2024 NOI; c0cc2a8f0000 p2 closes 5/31 | Add historical-support target; NOD stays in interval, old window unscored.
**PR2023-056** | | |
K33 Target/status; high | A NOD; B also snapshot | NOD c00cc1930000 p1 cites 6/28/2024 NOI; ct-xchk-portal-deep-pending-regs UST status | Add historical-support target; reject snapshot event (C2).
**PR2024-016** | | |
K35 Historical targets; high | A/B two NODs, empty targets | NOD 30f307930000/f0d485980000c135 p1: 6/4–7/8/2024 round | Link NOI e017e48f0000 as historical support; no new opportunities.
**PR2024-017** | | |
K64 Correction/status; high | A correction/unknown; B unknown/not_scheduled | NOD c08bbc930000/6022e0930000 p1: PR2023-017→PR2024-017; NOI p2 conditional hearing | Correction, as A; hearing fulfillment unknown, condition retained.
**PR2024-024** | | |
K37 Historical target; high | A/B empty target | NOD a095bf920000 p1 cites 8/23 NOI; 105180910000 p1 closes 9/25/2024 | Add historical-support target; no carry-in.
**PR2024-033** | | |
K68 Repost count; high | A duplicate; B notice/update | NOI 703304940200/202ea0920000 p1: same rule, 11/21/2024 close; repost 12/26 | Duplicate/revised copy; preserve GUID alias, no new round or action.
**PR2024-035** | | |
K69 Repost count; high | A duplicate; B notice/update | NOI 903904940200/c0d49f920000 p1: same rule, 11/21/2024 close; repost 12/26 | Duplicate/revised copy; preserve GUID alias, no new round or action.
**PR2024-036** | | |
K70 Repost count; high | A duplicate; B notice/update | NOI 303f04940100/30e99f920000 p1: same rule, 11/21/2024 close; repost 12/26 | Duplicate/revised copy; preserve GUID alias, no new round or action.
**PR2024-038** | | |
K72 Repost count; high | A duplicate; B notice/update | NOI e04504940300/10e39f920000 p1: same rule, 11/21/2024 close; repost 12/26 | Duplicate/revised copy; preserve GUID alias, no new round or action.
**PR2024-054** | | |
K73 Conditional status; high | A unknown; B not_scheduled | NOI 20ff3d950000 p2: 3/19/2025 1:30 PM upon request; later confirmation promised | Retain offer/date, fulfillment unknown; no inferred cancellation.
**PR2025-024** | | |
K45 Supplied target; high | A comments; B empty | NOD a049d09e0000 p2 image cites 5/14/2026 NOI; 80e1269e0000 p1 closes 6/15 | Link existing comments and opening evidence, as A.
K80 Supplied target; high | A comments link; B empty | NOD a049d09e0000 p2 cites 5/14/2026 NOI 80e1269e0000 | Use A target; add opening before-evidence.
**PR2025-026** | | |
K81 Conditional status; high | A unknown; B not_scheduled | NOI 309da6990000 p2: 10/30/2025 upon request; later confirmation promised | Retain offer/date, fulfillment unknown; no inferred cancellation.

## Part 3 — Owner minutes

**Allow about 540 owner minutes (9 hours), plus contingency; full CT scope does not fit 360.** These are planning costs, not measured throughput.

Work | Minutes
---|---:
16 class signatures × 2 | 32
43 high-confidence cases without LOOK × 1 | 43
22 high-confidence LOOK cases × 3 | 66
17 medium-confidence LOOK cases × 4 | 68
6 low-confidence LOOK cases × 6 | 36
110 union opportunity date/role checks × 1 | 110
**Mandatory subtotal** | **355**

PROTOCOL §5 requires all consequential date/role checks because the union has 110 opportunities before proposed exclusions. Reserve full opportunity checks separately from narrower case/class decisions; **no overlap credit** assumed. Missing-source recovery and agent repairs cost extra. Every case still needs an owner decision if a class makes its event inapplicable.

**Audit, §5:** 350 retrieved entries; the 2 gaps are outside the audit population. Union disposition uses both completions and final evidence attribution: 208 ordinary inclusions, 52 exclusions-only, 63 both-empty/no-candidate, 27 scan/partial units (risk precedence prevents double counting). Allow 2 minutes/native unit, 3/scan; long histories may take more. Read selected content units in full. Exact planning strata/IDs are in the progress note.

Scenario, predeclared order | Audit units / minutes | Total
---|---:|---:
Baseline, 152 cycle strata | 245 / 517 | 872
1. Merge cycles within source/process/format/disposition, retain scan strata | 147 / 321 | 676
2. Ordinary max(2, ceil(10% N)), bounded by N | 125 / 277 | 632
3. Risk min(20, max(5, ceil(20% N))), bounded by N | 81 / 184 | **539**

Entries already cover whole documents/history slices; no page collapse assumed. Scenario 3 preserves scan and both-empty/exclusion floors per source/process, with weaker audit sensitivity. These retrospective estimates apply no reduction and draw no sample; the run’s zero seed/hash placeholders are not a usable frozen audit.

Reduced audit leaves **360 − 184 = 176 minutes**, versus 355 mandatory: **179 minutes short**. Add at least 179 minutes (practically budget 540–600 total), or authorize narrower scope and re-freeze/re-enumerate/rescore. A candidate narrowing is NOI written-comment windows only, for a named agency subset or shorter civil interval chosen by volume; hearing/request and lifecycle claims would be explicitly removed. Recalculate populations to remove at least 179 minutes without waiving any mandatory review or risk floor inside the new scope. Nothing here establishes completeness.
