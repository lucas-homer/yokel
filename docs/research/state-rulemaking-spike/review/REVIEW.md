# Independent correctness review — final integrated verdict

## Phase 3 integrated verdict: pass, no remaining blockers

Independently reviewed the integrated root at
`/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike`,
including README.md, SPEC.md, observation.schema.json, replay.py, the combined
outputs, and corrected lanes. The earlier two remaining findings are resolved:
WA expectations now explicitly say agent-inspected; the PDF hearing-request
assertion includes the exact conditional eligibility sentence and a scope
warning. Removing that sentence causes a nonzero exit and an explicit review
outcome. Eligibility remains untyped, as the README accurately discloses.

Final verified totals: **41 observations, 37 artifacts, 37 deterministic
normalizations, 4 agent-manual visual observations, 39 exact-text evidence
items, and 4 visual evidence items**. The extra exact quote since Phase 2 is the
hearing-request eligibility sentence. The combined observation array exactly
equals the three lane arrays. All normalizers replay identically in isolated
copies. The current `lane-audit-results.json` records **44/44 bounded checks
passing**, plus four mutation runs that all fail explicitly as intended (missing
WA comment label, PDF comment-duration clause, PDF hearing-request clause, and
PDF eligibility sentence).

The three README commands were executed from a complete isolated copy using
only the existing Python standard library:

```sh
python3 -B replay.py
python3 -B review/audit_lanes.py . ./validate.py
python3 -B review/adversarial.py ./validate.py
```

All exit successfully. Replay reproduces `observations.json`, `artifacts.json`
and `validation-report.json` byte-for-byte. `integration-verification.json`
records commands, outputs and hashes of the reviewed narrative/schema/code.
Fresh `adversarial-results.json` still reproduces the disclosed validator holes;
those probes intentionally demonstrate boundaries rather than a clean negative
test pass rate. The actual integrated records do not exhibit those mutations.

The formal schema was read in full. Its predicate dispatch, temporal definitions,
canonical vocabularies, required fields and property restrictions match the
selected output shapes. Targeted required-property and regex checks pass for
all 41 actual records. **A full JSON Schema engine was not executed**; this is
static/targeted inspection, not a substitute claim of standards-conformant
schema validation. README correctly identifies the replay's purpose-built
checker and makes no such full-engine claim. No installation was performed.

The README's material factual narrative agrees with retained evidence: CT's
separate cycles and unresolved rendered timezone, WA's partial target/scope and
distinct date roles, PDF manual marks and distinct relative periods, and the
corrections made during integration. The earlier September fixtures support the
historical CT-list and duration-confusion comparisons. Eight retained Firecrawl
responses sum to **16 reported credits**. Their internal parser/model/version is
not established, and deterministic downstream code is not described as making
vendor parsing deterministic. Model-trial outputs remain outside the candidate
stream. Task model selections are consistent with the supplied delegation and
coordination record; this is not an independent inference-service model audit.

The common-envelope conclusion is appropriately limited. README explicitly
discloses validator/provenance/locator limitations, non-human inspection,
provisional identities, untested coverage and policy, single-call economics,
and unavailable LlamaParse execution. No remaining actual-record error or
material overstatement was found. No source refetch, primary/lane edit,
production change, install, or new task was performed by this review.

Primary integration action: replace the earlier copied review files with this
final review, refreshed `audit_lanes.py`, `lane-audit-results.json`,
`adversarial-results.json`, and `integration-verification.json`. Earlier review
phases below are historical and their open findings are superseded here.

---

# Phase 2 record (historical lane audit)

## Phase 2 result

The corrected temporary lanes support the bounded conclusion that these selected
sources can produce the same candidate-observation envelope with inspectable
evidence. They do **not** establish fully reconciled data, legal truth, unattended
ingestion, coverage, or independent human accuracy measurement.

Final inspected counts: **CT 23, WA 10, PDF 8 = 41 observations**; 37 deterministic
normalization observations and 4 agent-manual visual observations. Shared
validation passes on all three lanes: 37 artifacts, 38 exact-text evidence items,
4 visual evidence items. Each normalizer was inspected and replayed twice in
isolated reviewer-owned copies; observations and derived files stayed identical.
`lane-audit-results.json` records normalizer/manifest/validator hashes and **42/42
bounded checks passing**. This count is a diagnostic check count, not accuracy.

### Corrections independently verified

- **CT Posted Date bug resolved.** Five rendered-history boundary assertions
  were removed. Repeating the synthetic October 2 → October 4 Posted Date change
  now leaves both historical deadline observations unchanged. Original reproduction
  is in `ct-posted-date-baseline-results.json`; corrected reproduction is in
  `ct-posted-date-results.json`.
- **Canonical vocabulary resolved.** WA emits proposal/withdrawal, and PDF emits
  proposal plus rule_action=amendment and hearing_status=not_scheduled. The PDF's
  four assertions based on visual review remain explicitly manual_visual.
- **PDF missing-clause behavior resolved.** In isolated copies, changing either
  duration clause while updating its fixture hash now yields a nonzero exit,
  an explicit missing-predicate diagnostic and seven partial needs_review
  observations. Baseline code had returned success with six observations and
  no explicit abstention. WA also rejects a missing comment-field label.

### Two small remaining reporting/evidence gaps

1. **P2: unsupported human-label claim remains.**
   `/private/tmp/docketclock-three-path-2026-10-05/wa/expectations.json:2` still
   says Human-inspected. Correct to agent-inspected unless separate human review
   evidence exists. Its old source-event strings may be retained as pretrial
   labels, but distinguish them from the new canonical expected values.
2. **P2: hearing-request condition is retained in source but omitted from its
   normalized evidence.** `pdf/results.json:119` says to preserve the conditional
   request scope (political subdivision, agency, or ten or more persons), but
   `pdf/normalize.py:23-24` extracts only the duration/anchor fragment and
   `pdf/observations.json:80-96` contains neither the condition nor a scope warning.
   The 20-day number itself is correct. A small correction is to add the complete
   conditional source sentence as evidence and a scope note, or explicitly state
   in results that eligibility remains unnormalized. This does not require a
   production eligibility schema. Do not present the 20-day item as a universal
   individual entitlement to compel a hearing.

No other material semantic defect was found in the selected assertions. The
Phase 1 validator holes below remain bounded **check limitations**, not evidence
that these final outputs contain invalid dates or corrupted hashes. Fixing every
synthetic validator weakness is not necessary to report this diagnostic result
honestly; do not imply those checks are performed automatically.

### Semantic and lineage verification

- Independently resolved all 16 native CT observation JSON pointers and checked
  every native epoch conversion. Two historical cycles have distinct period
  GUID identities. PR2024-059 is absent from the open list; no withdrawal or
  closure is inferred from absence. The explicit rendered Taxi deadline remains
  October 11 at 23:45 with no inferred zone or UTC instant. Its native timestamp
  remains October 12 at 03:45Z. No generic hearing widget becomes an assertion.
- Reviewed WA body text: withdrawal targets 26-15-113 and only its CR-102 portion;
  later filing/hearing promises have no asserted dates. Written comments close
  October 9, date only; hearing is October 15 at 09:00, unresolved zone. Filing,
  accommodation, intended adoption and historical amendment effective dates are
  not substituted for those facts. Notice source IDs match retained bodies.
- Visually inspected the complete saved MS page image: amendment is marked,
  hearing not scheduled is checked, filing stamp is December 27, 2023, and final
  action/effective-date choices are blank. The 20-day hearing-request clause and
  25-day comment clause are distinct. Neither produces an absolute close. Manual
  review notes hash-link to both image and original; the fresh and inherited PDF
  bytes match. No independent PDF rerender was performed in this stdlib-only
  review, so image-generation lineage is inspected retained provenance.
- Verified each Firecrawl Markdown artifact against its retained response. CT
  adds only a final newline; WA and PDF preserve exact response Markdown.
  All checked response sourceURLs match their lane source and report HTTP 200.
  The first CT response's missing content is correctly distinguished from HTTP
  failure. PDF native text has imperfect pre-existing OCR; this is not a strictly
  image-only PDF. Hashes prove retention, not publisher authenticity.
- Normalizers do not consume expectations or model answers as extracted facts.
  PDF deliberately consumes an agent's saved visual labels and reports them as
  manual. Deterministic normalization of Firecrawl text is not a claim that the
  vendor's underlying parsing is deterministic. LlamaParse remains unexecuted
  and unassessed; no vendor ranking follows from single-call timings/credits.

Final integration into the repository and any final narrative are owned by the
primary and have not been re-audited here. The reproducible script accepts a new
lane root and validator path for that check. No primary or lane file was edited.

---

# Phase 1 record (historical; superseded where noted above)

Reviewed October 5, 2026. This is an independent **agent** review, not an
independent human gold standard. Inputs were the shared SPEC.md, EVALUATION.md,
validate.py and provisional lane files. Lane outputs may still change. No child
or primary files were modified. No web calls, installs, builds, or messages were
used. Phase 2 integrated-output audit remains pending.

## Overall assessment

The common envelope is adequate for this bounded question: can selected JSON,
HTML and scanned-document examples produce **candidate assertions in the same
representation**, retaining inspectable evidence and unresolved precision?
It does not establish equivalent extraction reliability or semantic correctness.
The evaluation plan makes that distinction correctly. No production schema or
large framework is needed to complete the spike.

The validator is useful but cannot alone support the claim that every assertion
is evidence-backed. Explicit source review is essential. The final report should
say which assertions were checked semantically and preserve the acquisition /
parsing / interpretation distinction. A deterministic parser of model-produced
OCR does not make the complete PDF collection path deterministic.

## Findings requiring primary attention

### P1 — CT Posted Date is promoted to a comment-window boundary

Affected provisional path:
`/private/tmp/docketclock-three-path-2026-10-05/ct/normalize.py:79-88`.
Source header: `ct/captures/fc059retry.md:65`; example row at line 80.
The source column is explicitly **Posted Date**. Lines 86-87 emit that date as
`comment_open` / `comment_close`, while line 88 acknowledges it may be a posting
date. The warning does not change the asserted predicate. These candidate dates
may happen to align with native deadlines, but the retained column alone does
not establish that equivalence.

Reproduction: `ct_posted_date_probe.py` copies only inspected code and needed
fixtures into temporary directories within review/, then changes the closed
event's Posted Date from October 2 to October 4. It leaves native timestamp
fields unchanged. Both executions succeed, and the rendered `comment_close`
changes to October 4 while the native close remains `2026-10-03T03:00:00Z`.
Evidence: `ct-posted-date-baseline-results.json` (includes normalizer hash).

Bounded correction: abstain from those rendered boundary assertions, or represent
them explicitly as event-posting dates with a distinct research predicate. Keep
the unambiguous native CommentPeriodStartDate / CommentPeriodEndDate observations
and the explicit rendered Comments Period Ends field. Update expectations/counts
so a posting date is not counted as independently supported deadline evidence.

### P2 — Washington expectation provenance says human-inspected

`/private/tmp/docketclock-three-path-2026-10-05/wa/expectations.json:2` says
"Human-inspected examples". No human labeling evidence is present in the
delegation or supplied artifacts; this collection was assigned to an agent.
Use agent-inspected / researcher-inspected with the actor identified, unless
there is separate evidence of human review. This matters to any accuracy claim;
the shared evaluation plan already correctly disclaims an independent panel.

### P2 — validator pass exceeds the actual provenance/precision checks

Shared path:
`/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/validate.py`.

- Lines 175-189 check that provenance keys exist but do not validate
  `source_url`, `retrieved_at`, `media_type`, or `collector` values. Numeric URL,
  object retrieval time, null collector, empty media type, and a fresh capture
  with null retrieval time all pass. SPEC.md:28-32 requires timestamp provenance.
- Lines 58-73 accept an asserted UTC instant with both timezone fields null,
  and accept a resolved local time/zone that contradicts its UTC instant.
  SPEC.md:78-79 requires unresolved zone/instant values to remain null.
- Lines 151-155 enforce manual method and PDF/image representation but cannot
  verify a saved review note exists or is tied to that artifact. A synthetic
  visual assertion with no saved note passes, contrary to SPEC.md:89-92.

These are limitations of the shared check, not proof that the integrated
artifacts have faulty provenance. Small checks or an explicit review ledger
covering these fields are sufficient. Do not describe them as automatically
verified until that is true.

### P3 — bounded validator robustness gaps

`validate.py:76` accepts infinite durations (Python JSON accepts nonstandard
Infinity); `validate.py:178` and `:205` crash on null manifest/observation entries
instead of producing validation failures. Worth small hardening, but neither
invalidates a manually inspected finite, well-formed dataset. No production
fuzzing framework is needed.

## Adversarial check results

`adversarial.py` uses only Python stdlib and synthetic reviewer-owned fixtures.
`adversarial-results.json` records every outcome and the exact validator hash.

- Six controls behave correctly: valid baseline passes; missing quote, altered
  hash, invalid date, duplicate observation ID and escaped path are rejected.
- Four deliberately unsupported semantic mutations pass: wrong date role,
  nonexistent locator, 20-vs-25-day swap, and full withdrawal substituted for
  partial scope. This is **expected evidence of the boundary**, not a request
  to build a legal-truth validator. Final source review must catch them.
- Six provenance/precision/finite-number cases pass as detailed above.
- Two malformed-entry cases crash as detailed above.

Re-run with `python3 review/adversarial.py /absolute/path/to/validate.py`.
The CT probe accepts an optional absolute CT lane directory.

## Required Phase 2 bounded checks

1. Inspect final normalizers, replay isolated copies twice, compare all generated
   observations and derived evidence, then run shared validation. Confirm
   expectations/model answers are not substituted for extraction inputs.
2. Review the actual MS page image and retained PDF lineage: 20-day hearing
   requests vs 25-day public comments, blank effective-date choices, checked
   boxes, filing stamp, manual-note identity. Check no absolute close is inferred.
3. Review WA withdrawal body/target/scope, and proposal hearing vs written-comment
   dates. Check header filing time and intended adoption are not effective dates.
4. Verify CT native epochs against quoted raw JSON fields, distinct historical
   window IDs, precise local timezone abstention, and no lifecycle conclusion
   from absence in the open list. Provisional open-list IDs are a disclosed
   research limitation, not stable longitudinal identities.
5. Check manifest hashes and transformation chains back to retained originals,
   distinguish inherited snapshots from fresh fetches, and inspect any claimed
   model extraction failures against retained request/response artifacts.
6. Report LlamaParse as untested if it was not executed. Vendor documentation or
   availability is not a comparative result. Single-call latency and credits
   cannot establish rankings or general accuracy.

Untested in Phase 1: final integrated outputs, full replay, source-document visual
review, source-locator correctness for every observation, end-to-end tool lineage,
cross-lane ID uniqueness and any final comparative narrative. No conclusion about
legal authority, coverage completeness or production readiness is established.
