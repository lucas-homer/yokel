# Evaluation plan

Recorded before integrating the child task outputs, October 5, 2026.

## Questions

1. Can native structured data, HTML notices, and a scanned document all produce
   the same candidate-observation envelope with reproducible source evidence?
2. For each path, what does Firecrawl contribute beyond a direct fetch or native
   text extraction? Separate acquisition, parsing, field extraction and domain
   interpretation in the answer.
3. Which decisions can be shared, and which depend on a source template,
   proceeding type or jurisdiction policy?
4. Which failures should abstain or enter review rather than silently fabricate
   certainty?

## Predeclared critical examples

- Connecticut: explicit source timestamps can be decoded; a record's absence
  from the current open-comment list cannot alone establish withdrawal or a
  completed proceeding. Multiple comment cycles keep distinct identities.
- Washington withdrawal: PROP in the index is not enough to classify the body.
  The CR-102 withdrawal has a target and limited scope. Its filing date must not
  become an effective date or a future comment deadline.
- Washington ordinary proposal: preserve the actual comment and hearing dates
  separately, including explicit times and unresolved timezone wording.
- Mississippi: the 20-day hearing-request condition and 25-day comment period
  are different facts. Blank effective-date options are not asserted dates;
  checked/unchecked form controls require evidence beyond a bag of OCR words.

## Shared checks

Validate envelope types, allowed predicates, temporal representations, artifact
hashes, relative paths, unique IDs, and exact evidence quotes. Run every saved
normalizer offline and check repeatability. Inspect source code before replay.
Use targeted negative cases to test whether the evaluator catches unsupported
shapes and whether normalizers stop safely when source signatures change.

Structural validation and quote matching do **not** prove semantic entailment.
An exact quote can support a different field or be too broad. Review the
critical examples above against the original source representation; record
automated, agent-assisted, and visual judgments separately.

## Reporting boundaries

This is a diagnostic integration spike using inspected examples, including
previously known failures. There is no blind holdout, longitudinal coverage
study, independent human labeling panel, or production approval. Report counts
and individual checks; do not report a national accuracy rate. Single-call
timings/credits may illustrate execution only, not establish vendor cost or
latency rankings. A document tool not actually executed is untested, not worse.

The current session exposes Firecrawl but no LlamaParse connector or LLAMA
credential environment variable. The spike can evaluate native extraction and
Firecrawl. A head-to-head LlamaParse result requires usable access and execution.

## Task ownership

| Child task | Selected configuration | Output boundary |
|---|---|---|
| Connecticut structured data | GPT-6.1 Sol / medium | temporary ct/ lane |
| Washington HTML | GPT-6.1 Sol / medium | temporary wa/ lane |
| Scanned PDF evidence | GPT-6 Astra / medium | temporary pdf/ lane |
| Independent correctness review | GPT-6 Astra / high, after integration | review report and adversarial fixtures only |

The primary owns the format, shared validator, integration, verification and
final report. Separate user-visible Codex tasks are used; the two earlier
in-process subagents were stopped after the user corrected the mechanism.
