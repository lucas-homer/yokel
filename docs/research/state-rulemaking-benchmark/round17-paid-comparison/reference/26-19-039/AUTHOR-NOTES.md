# Author notes — 26-19-039 (WSR, State Board of Health, dogs in breweries)

Spec r17.ref.v3. Draft: `draft-1.json`. 3 targets, 3 relations, none critical.

## What was recorded

- **R1 / T1** "Proposal is exempt under RCW 34.05.310(4) or 34.05.330(1)." Rule 6.3: nothing exempted
  *from* is named, so target = "is exempt" (occurrence 1), class UNRESOLVED, empty introducer, PART
  "Proposal". The "under RCW … or …" tail is in the clause as an `excluded` **citation** (it is the
  exempting authority, not a condition). A reviewer could instead want it left outside the clause
  entirely; either way the partition holds. The "or" inside it joins two citations, not components,
  so no OR node.
- **R2 / T2** "This rule is exempt from the requirements of RCW 34.05.328, including a cost-benefit
  analysis, because …". Rule 6.2 implied target = the full exempted-from noun phrase (kept the
  ", including a cost-benefit analysis" apposition as an object qualifier, rule 7). PART "This rule".
  The "because …dictated by statute" clause is a *reason*, not a condition, and is outside the clause.
- **R3 / T3** "This rule proposal, or portions of the proposal, is exempt from requirements of the
  Regulatory Fairness Act because the proposal: Is exempt under RCW 19.85.025(3) …". Rule 6.2 implied
  target = "requirements of the Regulatory Fairness Act". Population has an explicit "or" →
  `OR(PART "This rule proposal", PART "portions of the proposal")`. The "because … Is exempt under
  RCW 19.85.025(3) as …" and the later "Scope of exemption … Is fully exempt." restate the same
  exemption and its authority; treated as restatements (§3), not separate targets or conditions.

## Judgment calls a reviewer may dispute

1. **WAC 246-203-015(1) and (2)** — the operative limit ("that do(es) not provide or subcontract for
   food service subject to a food service permit") appears only as a relative-clause qualifier with
   no exclusive wording ("applies to", not "applies only to"). Under rule 7 / X06 these are part of
   the assertion, so **no RESTRICT relation and no target**. This is the most consequential content
   in the notice for the public, and I flag it in `out_of_scope_notes`. If the reviewer reads
   "This section applies to …" as inherently exclusive, (1) would become a RESTRICT on "This section
   applies" — but the spec says RESTRICT requires exclusive wording, so I did not.
2. **"… is not required under RCW …"** (school-district fiscal impact statement; cost-benefit
   analysis). Treated as plain negated obligations, not rule-6 exemption statements: there is no
   exempted population, the subject *is* the requirement. If the reviewer wants them as rule 6.3
   UNRESOLVED items, they would be two more non-critical relations.
3. **Comment window / hearing alternatives** — "beginning September 28, 2026, by 11:59 p.m.,
   October 23, 2026" and "; or virtual meeting via Zoom" carry no condition introducer; recorded in
   `out_of_scope_notes` only.
4. **Critical flags** — all three relations are agency procedural exemptions (§5 explicitly lists
   "an analysis the agency is excused from preparing"), so `critical: false` throughout.

## Mechanical self-check

Local script verified: every quote resolves with the right occurrence; per relation the introducer,
markers, PART quotes and exclusions partition the declared clause's counted characters exactly with
no overlap; no clause span overlaps its target span.
