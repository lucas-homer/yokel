# Expanded comparison: method review and freeze readiness

## Acceptance update

The primary accepted the substantive scoring design and resolved the two
pre-freeze scoring choices. `scoring-contract.json` is now version
expanded-parse-evidence-v1 with accepted status; `acceptance.json` records its
hash and the current readiness state. The earlier proposal discussion below is
retained as methodological history, not a pending approval request.

- The all-scheduled positive-field ratio is **evidence yield**. Operationally
  unusable/nonattempted fields count as unrecovered with separate operational
  counts. **Successful-output content scores** use a separate conditional
  denominator. Neither is automated extraction accuracy.
- Provider failure streaks use **completion order**, combining both Llama tiers.
  At the third consecutive failure, stop new submissions and retain results
  from at most two already in flight. A success resets the provider streak.
- The strict-reference sufficiency recommendation was included in the accepted
  substantive design; insufficient-reference units remain visible in overall
  corpus denominators and cannot produce an unqualified strict pass.
- Reference supplements will be added only in **reviewer-owned adjudicated
  files**. Collectors' required fields remain unchanged; their original
  annotations and hashes will be preserved.

**Source freeze remains pending.** Source A is reportedly nearing completion;
source B is still collecting. Zero units have yet received this reviewer's
complete source-only audit. The primary will freeze only after that audit.

---

## Original pre-acceptance critique

Prepared October 5, 2026 Pacific time, before inspecting any new vendor output.
Owned artifacts: scoring-contract.json and source-annotation-audit.json in this
review directory. The contract is a **proposed scoring definition**, not a claim
that sources are approved or that vendor runs have begun. No protocol or
collector-owned file was edited; no vendor call was made.

**Readiness: not yet ready for source/reference freeze.** Twenty fixture slots
are prepared (A01–A10, B01–B10), but zero units have been independently source
reviewed in this turn. Every annotation and relevant rendered input page must
be reviewed before any vendor-output inspection. The pending audit explicitly
records false/null readiness rather than inventing reference approvals.

## Assessment of the protocol

The design is suitable for a bounded diagnostic comparison: same input bytes,
four fixed parse arms, a 20-unit purposive sample, quotas, operational failures,
retained source evidence, independent agent annotation review, and no vendor
schema-extraction precision claim. Counts can support comparisons among these
selected units; they cannot support national accuracy or discovery estimates.

The primary has accepted and added the two main corrections identified during
review: a safe abstention on a visibly present answer is a safe miss, and a
bounded extra-assertion ledger catches critical incorrect assertions outside
the selected reference fields. Such assertions must fail the document gate.

## Remaining pre-freeze clarifications

1. **Reference sufficiency for a strict document pass.** The protocol asks for
   at least four critical questions "where supported" and excludes uncertain
   references. Do not pad a simple notice with trivia, or let an all-uncertain
   reference set pass vacuously. The proposed contract recommends at least four
   determinate, nonduplicate critical questions and no unresolved critical
   references for the unqualified strict gate. Keep other units in the frozen
   corpus and overall denominator as insufficient_reference; optionally report
   restricted-scope results separately. **This is an additional recommendation
   requiring a primary choice before freeze**, not an already adopted protocol
   requirement. A less restrictive eligible-fields gate is defensible if labeled
   accordingly and its reference gaps remain visible. Choose once, before results.
2. **Scope of absent facts and neighboring notices.** Every not_stated answer
   needs named inspected pages/columns/sections, not just a null value. For
   register excerpts, freeze notice start/end boundaries and physical-page maps.
   A date appearing in a neighboring notice does not support the target notice.
   Blank/unselected controls must preserve their option group and table column;
   the earlier mapper experiment showed that exact substrings alone miss this.
   Absence means absent in retained scope, not in an unseen attachment/package.
3. **Fields are not independent samples.** Date/time/zone facets, repeated rule
   citations and duplicated header/body facts should form one semantic group.
   Keep 6–10 useful questions, but report critical-group counts and never use
   field totals as independent binomial trials. A checked "not scheduled" is a
   determinate explicit-negative fact; merely declining to answer it cannot pass.
4. **Operational censoring and pairs.** Keep provider-stop nonattempts distinct
   from attempted failures and content omissions. Field-quality counts on
   returned output exclude service failures and uncertain references; the
   end-to-end document denominator retains all frozen scheduled units. Show a
   paired table with unusable/reference-limited cells so complete-case filtering
   cannot hide missing pairs. Define the completion order for the three-failure
   stopping rule under concurrency, including both Llama tiers, and freeze call
   order/settings. Already-in-flight calls should remain recorded.
5. **Quota and diversity accounting.** Assign exactly one primary bucket per
   unit; retain separate overlapping layout/event tags. Show distinct source PDF,
   register issue, template family and agency counts. Two notices from the same
   register or template are distinct notices, not independent proof of breadth.
   The 80-page cap is corpus input pages; three cloud arms can process up to
   240 page-runs before allowed upload recovery, with unknown timeout billing.

These are bounded definitions and records, not a request for a production
framework or additional vendor modes. No percentage should pool trivial lexical
recovery with loss of a deadline role or incorrect checkbox selection.

## Proposed scoring contract

`scoring-contract.json` defines the six permitted field outcomes, gate rules by
reference answerability, explicit scope requirements, provider/status reasons,
paired document outcomes, separate positive and negative evidence summaries,
state/bucket/layout denominators, and a deduplicated extra-assertion sweep.
It also requires exact output artifacts/spans or explicit omission scope and
preserves reviewer judgments as reviewer judgments of parsing evidence.

The key asymmetry is deliberate: present/explicit_negative references pass only
when supported; not_stated references pass only with safe abstention **and full
scope preservation**. Uncertain references are not assessable. A missing section
cannot earn a correct negative, and a failed service call cannot earn abstention.
Contradictory renditions elsewhere in the same notice block a supported result.

After source review, retain collector annotations, proposed corrections and
adjudicated annotations separately. Record disagreements about value, date role,
scope, precision, criticality and answerability. Freeze their hashes with the
corpus and scoring contract before vendor calls. Any later source correction
must be logged and applied symmetrically to all arms, never silently fitted to
one vendor output.

## Source-audit handoff

`source-annotation-audit.json` contains a pending row for every collector slot,
with page-review records, notice boundaries, field adjudications, original/input
hashes, uncertain critical counts and freeze status. At the source-freeze stage
the reviewer will inspect **all** annotations against complete relevant rendered
pages, including continuation, columns, footnotes, marks and blank states. No new
parse outputs will be read before that stage is finished.

No remaining claim of automatic extraction precision, independent human gold
labels or national confidence intervals is appropriate. The future report should
lead with paired document critical-evidence gates and explicit operational
coverage, then explain which hard distinctions were preserved or lost.
