# Author notes — 26-19-041 (WSR 26-19-041, DOH hospital price transparency)

Spec r17.ref.v3. 6 targets, 10 relations. Offsets computed from the packet's
`source_text`; every quote, occurrence and clause partition was mechanically
self-checked before writing.

## Segmentation choices a reviewer should weigh

1. **R2 `as long as` → COND, not RESTRICT.** "data … may meet the current or
   historical CMS requirements, as long as CMS has not removed reporting
   requirements." Semantically `as long as` is close to "provided that", but
   the spec reserves RESTRICT for explicit exclusive wording (only, solely,
   limited to…). I kept COND and said so in the rationale. If the reviewer
   reads `as long as` as exclusive wording, this flips to RESTRICT with the
   same clause/PART.

2. **Implied targets (rule 6.2).** Two bare noun phrases are targets:
   - T3 `analysis` in "exempt from analysis" (cost-benefit analysis). The
     preceding "A cost-benefit analysis is not required under RCW 34.05.328"
     is a negation, not the governed assertion, so rule 6.1 does not apply.
   - T4 `requirements of the Regulatory Fairness Act`.

3. **Per-subsection exemptions are separate relations (R4–R6).** "The entire
   proposed rule is exempt from analysis: Subsection (1) is exempt …;
   subsection (2) is exempt …; and subsection (3) is exempt …". Each `is
   exempt` is a separately introduced clause (rule 3), so each gets its own
   EXCEPT on T3. The declared clause for each is just "subsection (n) is
   exempt"; the statutory citations and the `as it …` grounds are treated as
   reasons/authority, not conditions, and left **outside** the clause rather
   than excluded. Same treatment for R8. If the reviewer wants the grounds
   inside the clause they would have to be `excluded` (`citation` / `aside`),
   which seemed less faithful since they are trailing, not interrupting.

4. **R8 attaches to T4 rather than UNRESOLVED under rule 6.3.** "The entire
   proposed rule is exempt under RCW 19.85.025(4)" does not itself name the
   thing exempted from, but it sits directly under "Explanation of exemptions"
   after the sentence that does. A strict 6.3 reading would make the target
   `is exempt` and the class UNRESOLVED; I judged that the restatement of the
   same exemption and attached it to T4. Flagged in the rationale.

5. **R9 RESTRICT inside a reason clause.** "…as it only applies to licensed
   acute care hospitals which do not meet the definition of 'small business'
   under RCW 19.85.020." The `only` is genuine exclusive wording about the
   rule's scope, so it gets a RESTRICT on target `applies to` (modelled on
   X09: target "must register", introducer "Only", PART = whole population).
   The clause is discontinuous around the target words. The relative-clause
   `not` is treated as a negator of the component's own predicate (PART
   marker, quotes split around it) rather than a NOT node. Marked critical
   because it states who the rule applies to.

6. **`not less than` split around `not` (R10).** Mechanically follows X03
   (negator of the component's own predicate → PART marker). Semantically
   "not less than" = "at least"; a reviewer may prefer keeping it unsplit,
   but rule 4 says a negator must be either a NOT node or a PART marker.

7. **Not recorded (see `out_of_scope_notes`):**
   - "is not required under RCW …" sentences (school district fiscal impact
     statement; cost-benefit analysis): plain negations naming neither an
     exempted population nor a governing assertion.
   - "because the proposal: Is exempt under RCW 19.85.025(4)." and "Scope of
     exemption … Is fully exempt.": form fragments with no subject text to
     put in a PART.
   - "To meet the requirements of subsection (1)" purpose clause in WAC (2).
   - WAC (3) "a hospital that fails to comply with this section": object
     qualifier under rule 7, no relation.
   - "have only added data reporting elements": focus adverb, not a
     restriction on application.
   - "interpret if the hospitals have met them or not": embedded question.

## Critical flags

True: R1 (how to get webinar joining info), R2 and R10 (which CMS
requirement version satisfies the state rule), R9 (which hospitals the rule
applies to). False: R3–R8 (agency's own analysis / Regulatory Fairness Act
exemptions; no effect on what the public may or must do).
