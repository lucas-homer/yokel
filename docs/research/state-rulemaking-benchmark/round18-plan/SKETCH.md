# R18 sketch: fix the same-role-condition gap and rerun the clause-only comparison (lean)

**Why.** R17 ended O3 on a single mechanical failure. S1-OPQ's output had unit 51 carrying two `if` links. Role cardinality allows one per unit, and the clause-only profile forbids the AND node that would combine them. The rules never say that one L leaf may hold 1–8 discontinuous source fragments. Offline check (2026-10-14, no cost): merging unit 51's two `if` leaves into one two-fragment leaf makes the entire S1 output valid under the unchanged r15.1/r16 validator. The gap is a missing instruction, not a missing capability.

**Change (one amendment, A5).** Add one sentence to the clause-only prompt in a new wire revision, r16.w2.2:
> "If a unit has several conditions of the same role (if, onlyif, unless or obj), emit a single link of that role to one L leaf whose fragments cover each condition in source order (up to 8). Never emit two links of the same role on one unit."

Nothing else changes in the schema, the validator, the scoring rules or the thresholds. Also check the full-profile prompt for the same gap. It has AND/OR nodes available, but should get the matching sentence anyway.

**Reuse unchanged:**
- the R17 sources (039, 041, 106);
- the frozen references and contested record;
- the P5 gate (140/140);
- the scoring manifest and thresholds;
- the runner path and staging and release tooling;
- adapter r1.4 logic.

The adapter changes only in its pinned wire hash. The request bytes change, so the release record's per-cell plan hashes are recomputed.

**Key and budget (A6).**
- Keep the DocketClock key. It's the same account, and its $50 cap remains a useful guardrail.
- Replace the "usage must be $0 at INIT" rule with "record the usage at INIT as the baseline". Reconcile against baseline plus debits, and keep the rule that a usage drop halts the run.
- Budget: three OPQ calls. R17's actual cost was $0.059 per call, so expect about $0.18. Keep the $0.27 floor and the $1.80 operating limit, so the reservations total $0.81.
- New R18 ledger namespace, under the user's $3 tolerance.

**Process (deliberately lighter than R17):**
1. One implementer task: wire r16.w2.2 (prompt sentence), adapter r1.5 (wire pin plus baseline usage), and tests. Include a regression fixture built from the merged S1 unit.
2. One focused cross-provider review of that diff. No new protocol review rounds; the protocol is unchanged apart from A5 and A6.
3. Stage, init, release, then run S1 → S2 → S3. Adjudicate each valid output: A1 Fable and A2 Opus, one fresh session each. Then `decide`.

Expected wall time: a few hours, versus R17's days.

**Not allowed.** Re-scoring R17's S1 output after the merge. That would be a post-hoc repair of a paid output, and the protocol forbids it. R18 reruns S1 fresh.

**What R18 can and can't conclude.** It can show whether clause-only meets its pre-registered bar (O1-untestable or O3) on three sources. It still can't test the typed layer: 4 compounds against the 5 required. Testing that needs sources chosen for compound structure, which belongs to a separate round.
