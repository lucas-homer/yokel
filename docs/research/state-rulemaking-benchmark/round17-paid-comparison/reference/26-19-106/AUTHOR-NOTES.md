# Author notes — 26-19-106 (WSR 26-19-106, Lower Columbia College, public records officer)

Spec r17.ref.v3. Draft: `draft-1.json`. 5 targets, 5 relations. Self-checked: every quote
resolves with the right occurrence, each relation's quotes partition its declared clause with no
overlap, no clause contains its target's words, every OR node has a marker.

## Segmentation choices a reviewer should weigh

1. **Procedural exemptions recorded as rule-6.2 EXCEPT relations (R1–R4).** The notice has no
   public-facing conditions at all; every condition-like clause is an agency procedural exemption
   ("is not required", "is not mandated to comply with", "is exempt from"). §5 explicitly names
   "an analysis the agency is excused from preparing" as a critical:false relation, so I recorded
   them rather than treating them as flat negative statements. All are `critical: false`.

2. **Bare "X is not required under RCW …" (R1, R2).** The sentence names the thing exempted from
   (the fiscal impact statement / the cost-benefit analysis) but no exempted population. Rule 6.2
   makes the noun phrase the implied target. The only remaining clause content is the statutory
   frame "under RCW …". I put it in the PART (scope of the non-requirement) rather than excluding
   it as `citation`, because it is not interrupting and excluding it would leave the PART empty.
   Alternative a reviewer may prefer: treat these two sentences as plain statements with no
   relation at all.

3. **"Pursuant to RCW 34.05.328 (5)(a)(i)" excluded as `citation` (R3).** This leading phrase is
   the authority for the exemption, not the exempted population ("the college"). Including it in
   the clause and excluding it seemed more faithful than declaring a clause that starts
   mid-sentence. Note the asymmetry with item 2, where the statutory frame is the PART: in R3 a
   real population exists, in R1/R2 none does.

4. **T2 vs T3 are kept as two targets.** "A cost-benefit analysis is not required under RCW
   34.05.328" and "the college is not mandated to comply with RCW 34.05.328" name different
   exempted-from things (the analysis vs the statute). A reviewer could argue they are one
   assertion restated; I followed rule 6.2 literally (the named noun phrase is the target).

5. **Regulatory Fairness Act (R4).** Clause stops at "is exempt from"; the trailing "because the
   proposal: Is exempt under RCW 19.85.025(3) as … Is exempt under RCW 19.85.025(4)." gives
   statutory grounds, not conditions, and is broken across paragraphs with a colon. The two
   "Is exempt under …" items and "Is fully exempt." are treated as restatements of the same
   exemption and not given their own relations (see out_of_scope_notes). "This rule proposal, or
   portions of the proposal" is an explicit OR over the exempted population (rule 4).

6. **"the rules relate only to internal governmental operations that are not subject to violation
   by a nongovernment party" (R5, RESTRICT).** The only exclusive wording in the text. Target is
   "the rules relate"; the PART includes the preposition "to" since it has nowhere else to go
   in the partition and belongs to the restricted phrase. "not" negates only the relative-clause
   predicate of this single component, so it is a PART marker with the quotes split around it.
   It is a reason for a procedural exemption, hence not critical.

7. **Not recorded (no conditional wording).** Comment window and deadlines ("beginning October 7
   … by November 17"), hearing alternatives ("or join Zoom"), "rather than identifying a specific
   administrator", the WAC (2) subject qualifier "Any person wishing to request access …, or
   seeking assistance …" (rule 7), WAC (3) "but another college staff member may process
   requests" (contrasting permission, not a carve-out), and the (5)(a)(ii) / rules-committee
   sentences (factual grounds). All listed in `out_of_scope_notes`.

8. **Text quirks.** Statute cites have doubled spaces ("RCW  34.05.328"); quotes reproduce them
   exactly. Register strike/insert markup survives as "((…))".
