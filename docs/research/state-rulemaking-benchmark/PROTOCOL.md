# Expanded document comparison protocol

Frozen design before any new vendor parsing; October 5, 2026 Pacific time.

## Question and scope

Does specialist PDF parsing improve recovery of the evidence DocketClock needs,
and which critical distinctions remain missing, ambiguous, or wrong? This is a
purposive diagnostic sample, not a probability sample of all states. Do not
estimate national accuracy, claim human gold labels, or treat fields from one
document/template as independent documents.

Target: **20 new notice units, at least six states, no more than four units per
state and two from one register issue**. The previously tested Mississippi
00027305a notice is calibration only and excluded. Four allocation buckets,
five units each: clean standalone PDFs; scanned/filled forms; dense register
layouts; lifecycle changes (withdrawal, extension, correction, or final action).
Buckets are sampling allocations; also record layout and event type separately,
because content and layout characteristics overlap. Record any unmet quota.

One unit is a complete notice or a clearly bounded, continuous notice excerpt
from a larger publication. Aim for 1–3 pages, maximum 4; at most 80 input pages
total. Retain original full document and physical-page mapping. Excerpts are
derived PDFs, not publisher originals or evidence of package completeness.
Both services receive identical retained parser-input bytes. Never cherry-pick
units because one parser performs well. Record source listings, eligibility,
selection order, inaccessible attempts and replacements before vendor outputs.

## Source and reference stage

Two collectors own ten units each. Use official public sources and recent
available notices; historical examples are allowed when needed for scans or
lifecycle cases. Describe the selection as diagnostic. No authentication or
paywall bypass, purchases, new credentials, installations, production changes,
or broad source crawling. Research processing uses existing bundled tools.

Each fixture directory contains `original.pdf`, `input.pdf`, `native.txt`,
rendered input-page images, and `fixture.json`. Copy an unmodified short original
to input.pdf where possible; otherwise use pypdf page extraction, keeping pages
unaltered. Preserve SHA256s and byte lengths for both. Verify the complete
relevant rendered pages, including columns, footnotes, marks and continuation.

fixture.json must contain:

- `fixture_id`, `state`, `bucket`, `layout_features`, `event_type`, `source_url`,
  `discovery_url`, `retrieved_at`, `source_title`, `selection_reason`;
- `original_sha256`, `input_sha256`, `original_page_count`, `input_page_count`,
  `original_physical_pages` (1-based, in input order), `package_limitations`;
- `reference_fields`: 6–10 independent questions answerable from the retained
  input, each with `field_id`, `question`, `expected_value`, `answerability`
  (`present`, `explicit_negative`, `not_stated`, `uncertain`), `critical`
  (boolean), `original_page`, `input_page`, `region`, `source_quote`, and `basis`
  (`source_text`, `visual_mark`, or `full_scope_absence`).

Useful fields: agency, source-native ID, rule citations, lifecycle/action,
comment closing date and time precision, hearing date/time, submit/filing/
publication/effective date roles, relative duration/anchor, selected checkbox
state, conditional eligibility, withdrawal target/scope. Include at least four
critical questions per notice where supported. Do not inflate the score with
contact details or repeated fields. Negative cases must identify inspected scope;
unreadable evidence is uncertain, not proof of absence. No legal deadline
calculation, unstated timezone, or outside research may supply a reference value.

References are agent annotations, independently checked against original page
images by the reviewer before comparison. Preserve collector and adjudicated
versions and record disagreements. Freeze file hashes for the corpus/reference
set before vendor calls; no outcome-driven replacements after that point.

## Paired parsing

Run native embedded-text extraction, Firecrawl local-document markdown parsing,
LlamaParse Agentic markdown, and LlamaParse Agentic Plus markdown on all retained
units. Native extraction is a baseline; cloud parse output is not itself typed
vendor schema extraction. Use the same input PDF for every service, full input
page count, no custom hints or expected answers. Firecrawl uses hosted upload +
parse (not a URL fetch of potentially different bytes). LlamaParse uses the
same local-byte upload, both tiers, version `latest` unless an actual released
version can be verified and selected before the first call. Record version limits.

Keep immutable raw requests/responses, local input hash, remote file/reference
IDs (excluding upload bearer URLs), settings, UTC start/end times, measured
wall time, returned job/version IDs, and actual reported usage. Unknown usage
stays unknown. Do not store signed upload tokens. Preserve operational failures
in the denominator. No blind retry of timed-out potentially billed calls.
One recovery for a proven pre-job upload/network failure is allowed and logged.
Maximum two concurrent parsing calls per provider; stop that provider after
three consecutive operational failures and report rather than silently switching.

No schema-extraction trial in this primary comparison: the earlier timed-out
call is not evidence of field accuracy. This experiment isolates parsing and
evidence preservation. Do not attribute agent-authored normalized answers to a
vendor extraction product.

## Independent evaluation and metrics

For each reference field, evaluate every returned parser representation using:
`supported`, `partial_ambiguous`, `missing`, `incorrect`, `safe_abstention`, or
`not_assessable`. `supported` requires the decisive relationship (selection,
date role, scope) in the output, not merely the right words somewhere. For
not-stated fields, silence is safe only if the relevant source scope survives;
otherwise it is missing. Uncertain references are excluded from accuracy
denominators and counted separately. Service failures are reported separately
and as unusable document results, never converted to successful abstention.

A safe abstention on a field whose answer is visibly present is a safe miss,
not recovered evidence and not a document-gate pass. Only a correctly supported
negative/absence can pass through abstention. Separately record critical false
assertions outside the 6–10 reference questions in an `extra_assertions` ledger;
an unannotated invented date or selected action must still fail the strict gate.
Do not call a service error a missing field or include an uncertain reference
in the scored-field denominator.

Every judgment cites the retained output and exact span or explicit omission
scope, plus the reference field. Keep raw text recovery separate from semantic
mapping. Scores are reviewer judgments of evidence preservation, not an actual
automated downstream extractor's precision. No national confidence intervals
from a nonrandom sample.

Report paired document-level results, critical-field supported/eligible counts,
false assertions, safe abstentions, missing/ambiguous evidence, and operational
success. Show per-state, per-bucket and per-layout results, with denominators.
Count each notice once for document success; separately report distinct original
PDFs/templates/issues so repeated templates do not inflate coverage. A document
passes the strict evidence gate only if all eligible critical fields are supported
or correctly abstained, no critical incorrect assertion occurs, and parsing
completed. Report agentic-plus gains/regressions against agentic on the same units.

Timing summaries use successful calls only with failure counts beside them;
include median/range and page counts, with a one-run-per-unit caveat. Published
prices and consumed credits are different quantities. Reviewer labor is not
measured unless actually timed; do not invent a cost or error-rate claim.

The primary verifies retained hashes, paired denominators, rubric application,
aggregation and representative disagreements before reporting conclusions.
The sample cannot establish discovery recall, complete attachments, temporal
policy correctness, production readiness, or coverage behind inaccessible sources.
