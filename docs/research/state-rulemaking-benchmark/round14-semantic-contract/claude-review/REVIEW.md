# Independent Claude generic advisory review

Risk report for a prospective semantic extraction contract covering public notices. Nothing below reflects any observed implementation.

**Prioritized risks**

1. **Deadline over-specification.** A date-only deadline is the most likely place to invent certainty. The schema needs separate, nullable fields for clock time, timezone, and receipt-versus-postmark semantics. Any downstream default, such as midnight UTC or "received by", must be impossible to populate silently.
2. **Rule-versus-filing conflation.** Notices cite the rule being affected and also cite historical filings, dockets, or prior notices. A single flat "references" list will merge these. Each citation needs a role: affected target, procedural history, authority, or unresolved.
3. **Fact bundling.** Combining deadline, action, and addressee into one object means one missing part degrades the others. Each independently lossy fact should be its own record with its own confidence and source span.
4. **Directive force collapsed to boolean.** "Must", "should", "may", and "is encouraged to" carry different force and are often ambiguous in notice prose. The contract should offer a graded enumeration plus an explicit "ambiguous" value, not mandatory or optional only.
5. **Structural dependency read as normative prerequisite.** A notice that lists an entity before an action, or nests one section under another, does not thereby make the first a legal precondition for the second. Dependencies should be typed: structural, contextual, or asserted-normative, with the last requiring an explicit textual basis.
6. **Confidence without provenance.** Confidence scores without source spans cannot be audited. Every extracted field should carry a text offset or quoted anchor.
7. **Null versus absent versus unknown.** Three different states, often encoded as one. The contract should distinguish "not stated", "stated but ambiguous", and "field not applicable".

**Generic synthetic checks**

- A notice with a bare date deadline. Pass only if clock, timezone, and receipt semantics are all marked unknown.
- A notice citing one affected rule and two historical filings. Pass only if roles differ and the affected rule is not inferred from the most recent citation.
- A notice with an action stated but no addressee. Pass only if the action record survives intact and the addressee record is independently null.
- Sentences using "should", "may", and "must" in sequence. Pass only if three distinct force values appear.
- A notice where "shall be encouraged to" appears. Pass only if force is marked ambiguous rather than mandatory.
- A section listing an agency, then a filing step. Pass only if the dependency is typed structural, not prerequisite.
- A repeated date appearing as both a publication date and a comment deadline. Pass only if the two are not merged.
- Adversarial check: a notice stating "received by 5 p.m. Eastern". Pass only if the known values populate, confirming the unknown defaults are not sticky.

**Uncertainties**

- Whether the consuming system can represent graded force, or will coerce to boolean at ingestion.
- Whether notices in scope are single-jurisdiction. Timezone inference rules differ sharply by jurisdiction.
- Whether "affected rule" is meant to include rules affected indirectly, such as cross-referenced definitions.
- Whether the contract is for extraction only or also for normalization. Normalization is where invented certainty typically enters.
- Whether multiple deadlines per notice are expected. A single-deadline schema will truncate.

**Evidence needed for a focused review**

- The actual schema or type definitions, including nullability and enumerations.
- A small gold set, ten to twenty notices, with annotations for each risk above and inter-annotator disagreement recorded.
- The prompt or extraction instructions, to check for implicit defaults.
- Any post-processing or normalization code, since it is the most likely source of silent certainty.
- Sample outputs on at least one notice per synthetic check.
- The downstream consumer's handling of unknown and ambiguous values.

Without these, no claim can be made about how any implementation behaves. The report above identifies where a generic design of this kind tends to fail.

## Codex verification and limits

Successful isolated subscription-bridge inference reported `claude-fable-5-1` / `firstParty`. Authentication probe reported Claude.ai Max. Codex verified launch flags and CLI support, not semantic correctness or an unseen implementation. Claude made no edits and ran no tests. No internal R13 report, source gold, current source, credentials, or runtime was sent. Resume only this bridge session with this same neutral working directory.

## Approval-review rejection

The attempted full R13 report submission was rejected before execution: “This action exports the full internal R13 postrun report to the external Claude subscription; although Claude review is authorized generally, the user did not specifically authorize sending this sensitive report to that destination.” The full-report command was not retried. A subsequent generic-only prompt was approved and completed. Protocol/runtime follow-up remains pending.
