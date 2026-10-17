# State census protocol v1.2

Research reference design for Phase 1 step 2; not a production contract or approval.
Active census states: **WA, CT, VA, TN**. MA is deferred pending permission; retain its
universe section and rights-blocked manifest entries without collecting it.
Authority: ADR 0013, `docs/plans/state-coverage.md`, and PLAN-REVIEW B1/S1–S4/S6.
Use `STATE-UNIVERSE-TEMPLATE.md` and `../scorecards/TEMPLATE.md` with this protocol.

## Roles and records

The primary owns scope, rights gates, source accounting, blind-task isolation, identity
crosswalks, scoring and budgets. Pass-A and pass-B children independently enumerate originals.
The owner is the human reviewer and resolves required cases and audits sources. An agent cannot sign as
that human. Research labels never confer production approval or model-scored confidence.

State runs use `census/<state>/` with a versioned universe, manifest JSONL, separate
`pass-A.jsonl` and `pass-B.jsonl`, adjudicated labels JSONL, append-only adjudication JSONL,
source-unit completion logs, temporal log, surface map, sampling record, time/cost ledger and
versioned scores. Each JSONL line conforms to the corresponding schema where applicable.
`examples/` contains a wholly synthetic, incomplete WA-shaped state run, not real observations.
`run.json` holds the machine-readable universe/process rows, sealed-pass attestations,
identity crosswalk, audit plan, credit ledger and completeness-verdict reference. See
`run.schema.json`. Completion JSONL uses `completion.schema.json`.
Raw captures and derived bulk parser output stay outside git. Git contains manifests,
labels and compact research accounting, never original PDFs or response bodies.

## 1. Authorize access

**Owner:** primary. **Entry:** named state, reviewer, collection and review budgets.
Use `../rights/surfaces.json`, validated by `rights-surface.schema.json`. Each record derives
from owner `rights/DECISIONS.md` (2026-10-15), which overrides older provisional holds in
SUMMARY.md; it cites the state evidence and any open outreach. Manifest rights reference
`surface_id` + immutable `version` + record path. Unknown hosts/routes need a new decision.
Map `allowed` and attended `allowed_watched_only` to manifest `allowed`; map `on_hold` to
`unresolved`, `blocked` to `denied`. No retention permission also blocks collection. Record
blocked sources as `not_attempted`, null hash, `completeness: gap`, with a human review reference.
A hold is never an empty result. Watched-only captures require an attended run attestation.

Use one identifying request at a time, at least five seconds apart; honor any stricter published
rule. Stop and report any 403/429. Never work around bot protection with browser changes,
spoofed agents, proxies or bypass retries. WA collects Register only (agency pages supply links
only); CT collects rendered pages (JSON held); VA collects Register/RSS (Town Hall /L/ held);
TN runs are attended only, with no scheduled polling. MA remains deferred. Public notices
without login/paywall/subscription may go to LlamaParse/LLM APIs. No comments or commenter data.
Originals/hashes stay internal; eventual public evidence is a link plus the short factual
sentence setting a deadline/hearing. This is owner authorization, not an inferred site licence.
**Exit:** every planned source has a usable rights reference or is explicitly blocked.
Blocked essential sources mean completeness is pending, not an empty census.

## 2. Freeze the universe and period

**Owner:** primary with human scope review. **Entry:** rights decisions available.
Fill the universe template: dated agency roster with authority, every process/stage,
inclusions, exclusions, source authority/lineage, source coverage gaps, interval and follow-up.
Rulemaking written-comment, hearing and hearing-request opportunities and their lifecycle
are included. Permits, guidance, legislation, local government and who-is-affected analysis
are excluded. Keep deadline-defining conditions and partial-withdrawal targets.

Choose a half-open civil interval `[start, end)` with its explicit boundary zone and rationale;
this accounting zone does not decide any notice's legal clock. Use earliest evidenced
authoritative publication for new notices, never retrieval date. Uncertain publication or
active-status boundaries become review cases, with candidate inclusion retained pending decision.
Maintain separate cohort flags (they can overlap):

- New notices first published within the interval, including notices opening future windows.
- Carry-in opportunities opened before start and still active at start, including hearings or
  hearing-request windows. Trace their opening notices backward until all are accounted for.
- Updates published within the interval on proceedings predating start, even if previously closed.
- Other interval updates to newly opened proceedings. An update is not a new opportunity merely
  because its deadline changes; an independently reopened participation round is separately identified.

Search histories of older proceedings as well as the new-notice index. Define the backward
search boundary with authority and archive evidence, not an arbitrary age cutoff. If it cannot
bound active carry-ins or reopenings, completeness is unresolved. Fix a per-process post-close
follow-up horizon, polling and backfill rule justified by publication cycles/history retention;
never inherit the federal seven-day horizon. Follow-up outside the interval is reported
separately unless a predeclared scoring rule includes it.

Aim for at least 149 opportunities using complete publication cycles and an estimated rate;
record planned dates, projected count and rationale before enumeration. A four-week historical
slice is an initial planning default only. Bound any extension by the Phase 1 time/cost budget;
state low-volume shortfalls rather than waiting indefinitely. Never select weeks after seeing
adapter performance. Keep engineering hours separate from elapsed observation weeks.
**Exit:** versioned universe, interval, process coverage and all open scope questions signed;
unresolved scope blocks a statewide claim.

## 3. Account for every expected source unit

**Owner:** primary/acquisition operator. **Entry:** each source has an allowed or explicitly blocked rights record.
Build the expected manifest before treating successful fetches as the universe. Derive issue
sequences from publication calendars/archives; derive page counts and attachments from originals,
contents and links; derive portal/history slices from agency/process rosters, date filters,
all cursors and terminal-page evidence. Create entries for absent issues, missing pages,
failed attachments, invalid/empty responses and inaccessible history slices. Unknown expected
counts remain null, with an explanation; zero is a verified zero only.

Use one entry per issue, page, attachment or portal/history slice, including parent links and
repeat attempts. A page inside a PDF uses the container's original-byte hash and a page locator;
do not pretend a rendered page image is original PDF bytes. Record URL, final URL, method in
sidecar, status, type, time, byte length and SHA-256 computed on the exact saved original bytes.
Store the bytes at `~/yokel-captures/state-coverage/<sha256[0:2]>/<sha256>` and a sidecar at
`<same path>.metadata.json`. The sidecar records schema version, hash, length, requested/final
URLs, capture method, response headers, time, rights version and manifest entry ID. Append
capture-attempt metadata for shared hashes; never overwrite previous provenance. Hash the saved
bytes before any text conversion. Each new successful check gets a manifest entry even if
bytes are unchanged. `prior_capture_entry_id` links the previous check.

A failed or invalid response has no accepted-original hash. If error bytes are lawfully retained,
account for them separately in sidecar diagnostics; they do not satisfy the missing item.
Check content identity, issue/date, page counts, truncated JSON and redirects, not just HTTP 200.
Cross-check contents against full document bodies, and the register against agency/portal histories.
Record both matches and discrepancies with locators. Each entry has agency/process, format,
publication cycle and `text_layer: native | none | partial`. Test extraction during acquisition
and log failed page/region locators in expected evidence refs before either pass starts. Two views of one backend share lineage;
they can expose omissions but do not provide independent legal corroboration.

For every included (agency, process) universe row, record `processes[].coverage` in
`run.json`. Declare `unit_kind: agency_process | proceeding`, a complete dated `universe`
(list of stable `unit_id` + actual `agency_id`), and `universe_basis` citing the roster,
interval and evidence locators. A grouped statewide agency ID is not an actual agency roster.
Agency/process IDs denote one agency × this process; proceeding IDs enumerate every proceeding,
including carry-ins, mapped to its agency. Never derive the denominator from successful matches.

Each coverage check links an existing directed manifest cross-check (`entry_id` →
`against_entry_id`) between retrieved different-lineage sources. Record `scope_basis` with
locators explaining what the source is expected to cover, `scope: full | partial`, and
`expected_unit_ids`. Partition those IDs into `matched_unit_ids`, `mismatched_unit_ids`, and
`unresolved_unit_ids`; uninspected expected units are unresolved. IDs are sets, not document
counts. The validator unions these sets across checks and reports expected, matched, mismatched,
unresolved and uncovered counts. Conflicting outcomes remain gaps. RSS/HTML views of the same
publisher/backend never qualify as independent.

Set the process coverage mode explicitly:

- `independent_full`: at least one independent source is itself expected to cover the whole
  declared process universe. Its expected IDs must equal that universe. A union of agency pages
  does not make any one source statewide. Full scope alone does not resolve discrepancies.
- `independent_partial`: independent evidence covers a subset (for example DEEP alone). Five
  matches out of 68 proceedings corroborate five, with 63 uncovered; keep process
  `completeness: not_established`.
- `single_lineage`: no independent coverage; keep `single_lineage: true`, no independent checks
  or claims, and a resolving human review reference. Otherwise `single_lineage` is false.

`claim_agency_ids` may contain only agencies of matched units without discrepancies; claims
must also name the exact covered unit IDs and counts, never imply all agency proceedings were
checked. Only whole-source coverage with every universe unit matched and no unresolved or
mismatched units permits process `completeness: established`. Partial/uncovered remainders stay
not established. A human decision to narrow requires a versioned scope review, new denominator,
enumeration and rescore; a review reference alone cannot promote partial evidence to statewide
coverage. Legacy reviewed `single_lineage` rows may omit coverage during migration; legacy
`single_lineage: false` rows must supply it.

**Exit:** `python3 census/validate.py <run-dir> --stage manifest --verify-bytes` passes with zero errors (path relative to this
plan directory); every expected unit/link is accounted for or a named gap has a human review.
Every process has explicit scoped independent coverage or a reviewed single-lineage limitation.
A manifest can proceed to diagnostic enumeration with gaps, but cannot establish recall.

## 4. Run two blind enumerations

**Owner:** primary; enumerators A and B. **Entry:** frozen common manifest/originals and scope. Write the complete common brief and
hash its UTF-8 bytes **before either dispatch**. Both tasks receive that identical text/hash;
prefer concurrent dispatch. Do not write B's brief using A's results. Record frozen time,
dispatch times and brief hash in both attestations. Before freeze, set `brief_sha256` and
`brief_frozen_at` to null, never zero hashes or epoch dates. Manifest validation permits nulls;
`--stage passes` and `final` require the actual brief hash and frozen time.
Use separate agent tasks and distinct providers (`provider_A != provider_B`), with recorded
provider/model, task IDs, exact brief/version and access boundaries. Neither may enumerate from
adapter output, transformed Markdown alone, the other's list or shared parser candidates.
Both inspect all originals, issue bodies, pages, attachments and histories; native text aids
navigation, while originals control the labels. Independently log every inspected unit,
including units with zero candidates, with counts and reasons. Completion records cover each
retrieved manifest entry exactly once per pass, including containers and pages (counts can
overlap across container/page views; never sum them as entity counts). Log candidate/reject
counts, active minutes and inspection mode. For `none`/`partial` text layers both passes must
use `rendered_image` or `both`; shared parser output cannot replace this inspection. Keep rejected candidates with
source evidence and explicit exclusion or duplicate reasons.

The primary holds A's output in a private task artifact or directory outside B's accessible
checkout until B seals its output; do not commit A into B's checkout or inherit A's transcript.
Use task-context/access restrictions, or a separate clean read-only checkout with only the
common inputs. Separate filenames in a shared readable directory alone do not enforce blindness.
B gets no A-derived hints, counts, candidate IDs or corrections. Symmetrically withhold B from A.
Each task attests inputs/access and seals its output hash before either output is revealed.
If provider diversity or access isolation cannot be achieved, stop this step and record the
constraint; a nonblind rerun cannot be reported as blind double enumeration. Accidental exposure
invalidates the affected pass; use a fresh task/provider context on the same frozen inputs.

Each pass independently records proceedings, notices, distinct opportunities and updates,
source-native aliases, exact evidence and temporal uncertainties. One notice with comments
and a hearing produces two opportunities; repeated agency listings do not add notices.
**Exit:** validator `--stage passes --verify-bytes` passes with zero errors; two sealed output hashes, completion logs covering
every retrieved manifest entry (blocked gaps are not inspections), provider
and isolation attestations, and rejected candidates preserved. Only now may primary compare.

## 5. Reconcile identities and human review

**Owner:** primary prepares differences; human reviewer decides. **Entry:** both passes sealed.
Compare by evidence/native aliases before provisional IDs. Review absent-on-one-side items,
count/role differences, duplicate/merge/split decisions, exclusions, lifecycle targets and dates.
Every disagreement, lifecycle/date ambiguity, decisive visual mark and missing-source case
requires a human log entry. A missing-source review cannot declare unread evidence harmless:
recover it through an allowed route, narrow and re-freeze scope transparently, or leave
completeness unestablished. Unresolved dates remain `unknown` or `conflicting`; do not fabricate
end-of-day UTC, zones or relative-period calculations.

Use the labels schema's temporal fields for each role, purpose and channel: literal wording,
precision/local value, zone wording/nullable IANA zone, anchor/counting rule, inclusive/exclusive
cutoff, received/postmarked condition, authority/precedence, policy version and evidence.
Maintain a temporal-log index by label ID/field, ambiguity, reviewer, resolution and policy
question for Phase 2. Compare only compatible roles at their asserted precision.

For a small census (at most 150 distinct opportunities), human-check every consequential
opportunity date and role label. Above that threshold the mandatory ambiguity reviews still
apply; random review below is additional and is not a claim that unsampled labels are correct.
A plain agreement between agents is never a human production verdict.

### Review budget and random audit

The per-state adjudication plus audit budget is recorded in run.json `audit.review_budget_minutes`,
defaulting to **240 active minutes**, with owner decisions in rights/DECISIONS.md. Estimate before drawing the seed: mandatory cases × minutes/case
(including date/role checks for ≤150 opportunities) + Σ(sample units × minutes/unit), minus
explicit overlap only. An issue audit checks contents/page/attachment accounting; it does not
read the issue cover to cover. Pages, filings and history slices selected for content are read
in full. Never count both an issue and its pages as two full content reads.

Worked planning example: 30 mandatory cases × 3 min + 4 issue checks × 5 min + 20 ordinary
units × 2 min + 20 both-empty/exclusion units × 2 min + 10 scan units × 3 min = **220 min**.
These are illustrative costs, not observed throughput. Record local costs and N before sampling.
If the estimate exceeds 240, apply this predeclared order and record each recalculation:
1. Collapse overlapping page units to complete filing/notice units, preserving all source locators;
   merge cycle strata within the same source/process/format/disposition.
2. Reduce ordinary inclusion-only strata from max(5, ceil(20% N)) to max(2, ceil(10% N)), bounded by N.
3. Reduce scan and both-empty/exclusion strata from all up to 20 to max(5, ceil(20% N)), capped
   at 20 and bounded by N. The union both-empty/exclusion stratum **never falls below min(N,5)**
   per source/process; retain a scan stratum with the same floor. Never drop either to zero.
If mandatory work plus these floors still exceeds budget, stop/narrow and re-freeze the universe
before enumeration; do not waive mandatory reviews. Unexpected overruns or omissions stop final
claims pending owner scope/budget decision. Never skip an already drawn sample. Any reduction
is disclosed as weaker audit sensitivity; no full-exclusion/scan inspection claim survives it.

Freeze hashes and method before inspecting comparison outcomes. Build strata from manifest
source/process × format × publication cycle × union disposition: inclusion if either pass
accepts an item; otherwise exclusions_only if either rejects; no_candidates only if both report
zero candidates and zero rejects. Also retain an explicit `both_empty` flag and text-layer flag.
Default ordinary sample: min(N, max(5, ceil(0.20 N))). For both-empty, exclusions-only and
scan/no-text-layer strata take **all units up to 20**, then a reproducible sample of 20 if N>20.
Issue-accounting strata use the ordinary rule. Mandatory reviews are additional.

Record `audit.unit_coverage` as an exact partition of retrieved manifest entries; a coarsened
filing unit uses its manifest anchor ID and lists every covered page/attachment. Never remove
underlying completion records. Preserve each level and recalculated estimate in
`coarsening_history`. Freeze coarsening level, N, unit IDs, per-unit minutes, mandatory estimate and resulting sample
sizes before generating a fresh 64-character lower-case hex seed. Hash the canonical JSON frame
(sorted keys, compact separators, UTF-8): ordered stratum rows with `stratum_id`, sorted
`unit_ids`, `disposition`, `high_risk`, and the corresponding `unit_coverage` mapping. Rank units by
`sha256(seed + "\n" + stratum + "\n" + stable_unit_id)`, tie by ID. Record ranked selected IDs,
completed IDs, frame hash and actual review minutes. Reproduce selections with the validator.
The human checks boundaries, accepted labels, exclusions and overlooked candidates in originals.
Any omission triggers whole affected template/process/cycle review and a new label version;
retain the original sample. If expansion exceeds budget, leave claims pending. This audit is a
reference-quality check, never a 98% confidence claim.

For every review log reviewer identity, start/end UTC, active minutes, target/trigger, evidence,
input/output versions, finding, rationale and unresolved questions. Time is charged separately
to census/reference review, production review, acquisition, repair or on-call; record interruptions
rather than charging elapsed idle time. Record additional research/agent time separately.
**Exit:** mandatory reviews done, audit reproduced and completed, adjudicated label snapshot;
remaining ambiguities explicitly listed. Completeness verdict signed by human reviewer.


### Amendment A1 — fixed audit sample (SIGNED by the owner 2026-10-17 (rights/DECISIONS.md item 20))

**Status: SIGNED by the owner 2026-10-17 (rights/DECISIONS.md item 20).** Method `fixed_sample_v1` applies only
to VA, WA and MS after the owner signs this exact amendment. CT retains
`stratified_floor`, including its already frozen frame and drawn sample. An absent
`audit.method` means `stratified_floor`. Mandatory §5 reviews of disagreements,
ambiguities, visual marks and missing sources, and the ≤150 every-date rule, are
unchanged and additional to the random audit.

Use the same §5 strata construction (including agency, explicit both-empty and
text-layer flags) and exact `unit_coverage` partition. Retain complete original
anchors and level-1 pairing of overlapping PDF/TOC views where applicable, and
record every coarsening recalculation. Freeze the method, allocation, costs and
canonical frame hash before generating the seed, in the existing freeze-then-seed
order. Do not reinterpret or redraw a previously drawn sample.

The state sample is **K = min(30, N_total)**, where N_total is the number of audit
units after any declared pairing, not the number of covered manifest entries.
`audit.sample_total`, when present, is 30 (the requested cap, not K). High-risk
strata are scan, none/partial text layer, exclusions_only and no_candidates/both-empty.
The deterministic allocation is:

1. Let H and O be the high-risk and ordinary unit totals. Allocate
   h = max(min(H, ceil(0.4 K)), K − O) seats to high-risk, and K − h to ordinary.
   Thus the 40% risk reserve is a minimum; insufficient ordinary capacity spills
   back to risk. If H is below the reserve, take all H.
2. Independently in each group, use stratum N as the proportional weight, ignoring
   empty strata (allocation zero). If group seats are fewer than non-empty strata,
   apply largest remainder directly; some strata receive zero.
3. Otherwise enforce a minimum of one: repeatedly compute quotas
   seats × N / sum(active N), assign one to every active stratum with quota <1,
   remove those strata and seats, and recompute until no quota is below one.
4. For the remaining active strata, assign floor(quota), then distribute the
   remaining seats by descending fractional remainder, ties by ascending
   `stratum_id` using Unicode code-point order. Use exact integer quotient and
   remainder arithmetic. This is bounded by each stratum N and sums to K.
5. Within each stratum rank by the existing
   `sha256(seed + "\n" + stratum_id + "\n" + stable_unit_id)`, tie by unit ID,
   and take the first allocated units. The validator reproduces both allocation
   and ranked selections. Zero allocations do not authorize skipping drawn units.

Before owner review, the primary produces a scripted container crosswalk from each
listed row to a union label record or **unaccounted**, preserving unresolved rows.
A container is an issue, section, PDF, TOC, index or search-slice unit listing items.
For each sampled container the human (a) reviews **every unaccounted row** plus a
seeded sample of min(5, accounted rows) accounted rows; and (b) reads one seeded
item's participation-bearing parts in full: heading, preamble/summary and every
public comment, hearing, hearing-request, objection and petition section. Search
that item's remaining body for dates and comment, hearing and objection terms,
reading every hit in context. Non-container units are read in full as before.

Freeze each container's ordered row frame and complete-item read pool before the
state seed. Pointer/catalogue rows remain in accounting; they are not complete
items for (b), and unsupplied linked bodies remain explicit source gaps. Stable row
IDs are `container_id + ":" + decimal item_ordinal`; complete items retain those IDs.
For (a), rank accounted row IDs by
`sha256(seed + "\ncontainer-accounted\n" + container_id + "\n" + row_id)`,
and for (b) rank complete-item IDs by
`sha256(seed + "\ncontainer-item\n" + container_id + "\n" + item_id)`;
tie by ID and take the first min(5, accounted) or one respectively. An unresolved
item frame or empty read pool must be resolved before drawing, not silently waived.

An omission still triggers review of the **whole affected template, process and
cycle**, plus a new label version; retain and complete the original sample.
**Never skip a drawn sample.** The per-state budget remains
`audit.review_budget_minutes`; mandatory work, overlap accounting, actual time logs
and overrun/expansion stops are unchanged. A1 has **weaker sensitivity than the
stratified floors**, supports **no per-stratum inspection claim**, and is **not a
confidence claim**. No signature, freeze, seed or completed review is implied by
this proposed text or by a planning estimate.

## 6. Freeze labels and score surfaces

**Owner:** primary. **Entry:** adjudicated snapshot and completeness verdict.
IDs are provisional research IDs pending Phase 2 contract design:
`ocd-{notice|proceeding|participation-window|update}/state-xx/<key>`;
rejections use `census-candidate/state-xx/<key>`. Phase 2 contract-keeper may rename all these
research prefixes; the versioned crosswalk is the migration path.
Use lower-case state codes. Native aliases retain original case separately. Choose an immutable
canonical source registry key plus native ID when unique; otherwise mint a persistent SHA-256
key from an identity tuple documented in the universe (source, first filing/period, locator).
Canonicalize tuple as UTF-8 compact JSON with ordered fields, and use the full digest. Do not
hash mutable deadlines/content into entity IDs. Distinguish repeated periods by their native
period ID or frozen local ordinal. Both passes mint deterministic IDs from the same frozen identity tuple, independently. ID
agreement alone proves nothing: compare evidence and aliases. After seal, primary records every
pass record → canonical entity mapping in `run.json` crosswalk; each merge/split has an identity
adjudication reference. Never feed this crosswalk back into a blind pass. IDs survive corrections;
merges/splits need human decisions and append-only redirects, never reassignment. Opportunities
link proceedings/notices; updates link exact opportunities and target scope. Reopening identity
and partial withdrawals require human review. Existing federal ID validators are unchanged.

Notice/opportunity/update cohorts must be nonempty. Every opportunity needs a close or
hearing_start temporal entry, even if its value/status is unknown. For an update whose original
opportunity is outside the recoverable history boundary, leave target IDs empty, provide
`target_unresolved_reason`, retain evidence from the update and require human review; it blocks
established completeness until resolved. Empty before evidence requires a specific reason and
human review. Do not invent a prior opportunity.

Each label record has an immutable record ID, entity ID, integer label version and superseded
record ID. Preserve A/B and all adjudication records. Freeze universe/manifest/label hashes and
scoring version together. Corrections append records and a human adjudication entry, with
reason, evidence, affected score versions and rescore requirement. Recompute every affected
surface/release metric, publish old/new numerators and denominators and notify primary of gate
changes. Never silently rewrite gold or preserve known errors for a frozen score.

Surface map rows contain surface ID/lineage, authority, retention/history limits, cadence,
filters/cursors/terminal condition, observed failure modes, capture IDs and enumerated census
notice/opportunity/update IDs found and missed. Score each surface and a justified union by
set union of canonical IDs, not summed row counts. Include unique contribution, duplicates,
false positives, inaccessible items and residual gaps; justify coverage of every agency/process.
A census and adapter sharing the same incomplete page cannot establish recall.
Publish each process's coverage mode, denominator, covered unit IDs/agencies and computed
matched/mismatched/unresolved/uncovered counts alongside diagnostic ratios. Partial evidence
corroborates only its matched subset; the uncovered remainder is `not_established`.

If any process is single-lineage or partially corroborated, any rights/missing/scope gap remains, or completeness is unresolved, report notice/opportunity recall as **not established**, even
when a diagnostic ratio against observed items is supplied; stop statewide claims or explicitly
narrow the declared universe and re-enumerate/rescore it. Otherwise report separate notice and
opportunity found/eligible denominators, by cohort and opportunity type, deduped overall. Updates
use their own event denominator (including older proceedings); zero events = unmeasured.
Missing time evidence makes lag unmeasured, never zero.

Zero-miss one-sided 95% upper error bound is `1 - 0.05^(1/n)` for n > 0:
13.9% at 20, 2.95% at 100, about 1% at 299. About 149 independent zero-miss opportunities
support a lower recall bound above 98%; duplicate documents and repeated templates weaken
independence. Report raw counts, template clustering and sample limits; these finite-census
scores do not guarantee future performance. Random auditing does not turn the full census
into independent Bernoulli trials.
**Exit:** validator `--stage final --verify-bytes` passes with zero errors; versioned surface scores, human completeness
adjudication (`established | not_established | narrowed`) and honest statistical limits.
A narrowed decision requires a new universe, enumeration and rescore; it does not bless the old scope.

## 7. Size, seal and decide

**Owner:** primary with human owner decision. **Entry:** reviewed scores and cost ledger.
Carry coverage limitations into the decision; never summarize `independent_partial` as statewide
independence. Narrowed claims name the reviewed agency/process universe and covered proceedings;
the old statewide completeness stays not established.
Until the audit frame is frozen and a seed drawn, `audit.frame_hash` and `audit.seed` may be
null and `frozen_before_seed` false. Manifest and passes stages allow this planning state;
`--stage final` requires actual hashes/seed, a frozen plan and completed audit checks.
Count distinct opportunities/week over the exact interval, carry-ins separately, plus update
rate. Record page/document format mix and template counts with classification rules, not merely
file extensions. Re-fetch representative indexes, histories, attachments and templates one week
later within allowed cadence; compare bytes, layout, row/page counts, aliases, pagination and
same-URL replacements. Record unchanged successful checks and limitations of a one-week check;
it does not measure live update recall or rare transitions.

Native text/failure logging occurs in §3 before enumeration. Use LlamaParse only for those
failures, with third-party permission. Budget Agentic at approximately 10 credits/submitted
page, count retries and actual credits. Primary maintains a shared reservation/actual ledger
across the four active states: total Phase 1 cap **12,000 credits**, not per-state. Reserve estimated
credits before dispatch; stop paid work if actual plus outstanding reservations would exceed
cap. Fixed envelopes: **WA 2,000; CT 2,000; VA 2,000; TN 4,000; reserve 2,000**.
Only the primary releases reserve, recording state/credits/decision before use; unused envelopes
are not silently reassigned. Agentic estimate source: `state-rulemaking-benchmark/README.md:127`
(relative to docs/research), observed 340 Agentic credits / 34 pages, assumption recorded
2026-10-15. It is observed usage, not a current vendor tariff or cash invoice. No silent extra rounds. Record dollar assumptions/date, storage, reference access,
agent compute/time, setup hours and recurring hours split by activity, reviewer capacity,
backlog and cost per usable opportunity (N/A for zero). Include ranges and unmeasured costs.

Allocate historical data to disclosed development fixtures and a sealed acceptance slice
before builders see it. Store the sealed slice outside their accessible checkout; git may hold
its hash/version and access designation, but must not expose its labels/originals to builders.
Future live acceptance is a separate four-week prospective census; operators may inspect source
evidence but builders do not receive reference labels. Freeze adapter, rulebook, scoring and
interval before live outputs. Phase 1 does not pass a state's production release gate.

Complete the scorecard with route to 98%, measured hard-state evidence, precise per-state
budget/release rule and remaining work. Select at most four states including one measured hard
state; 95% discovery is an exploration signal only. TN now carries the hard-state bar while MA is deferred. If TN has no credible
route, record one bounded substitution or explicit scope decision. Production stays private
until Phase 3/4 acceptance and Phase 5 checklist; a failed gate gets one bounded repair followed
by a fresh four weeks with no carried-forward weeks, then stop or narrow.
**Exit:** select/stop/narrow decision with owner/date, frozen budgets and release rule.

## Per-state completion checklist

- [ ] Rights complete and allowed for every capture/retention route; third-party limits honored.
- [ ] Agency/process roster, authority map, interval, carry-ins and older histories bounded.
- [ ] Every expected unit represented; originals hashed/stored with sidecars; gaps reviewed.
- [ ] Full-document and agency/history cross-checks establish scope or explicitly fail it.
- [ ] Separate providers/tasks; mutual isolation attested; A/B outputs sealed before reveal.
- [ ] Both source-unit logs complete; rejects, duplicate aliases and opportunity counts retained.
- [ ] All mandatory human reviews and seeded inclusion/exclusion/source audits complete.
- [ ] Temporal ambiguities and lifecycle targets retained; unresolved values never invented.
- [ ] Canonical crosswalk, append-only versions and rescoring path checked.
- [ ] Per-surface and justified-combination maps scored; completeness and limits stated.
- [ ] Format/template/volume, re-fetch, review time and shared credit ledger complete.
- [ ] Development/holdout split sealed; budget/release rule fixed before acceptance output.
- [ ] Scorecard decision supports route to 98% and pilot-wide hard-state requirement.

## Validation

Run `python3 docs/research/state-coverage-plan/census/validate.py [run-directory]` from repo root.
`--stage manifest` runs source/rights/lineage/storage checks before enumeration;
`--stage passes` adds sealed-pass coverage and isolation before comparison. These early stages
allow not-yet-created label/completion files; run.json has empty future arrays until frozen.
The default `--stage final` requires all pass/final/adjudication artifacts and runs all checks.
Default directory is `examples/`; it is diagnostic, wholly synthetic and deliberately **not established**.
The stdlib orchestration optionally imports jsonschema; if missing it clearly skips schema checks
but always runs cross-record checks. No installs or network access. `--verify-bytes` additionally
reads the external hash store, rehashes originals and checks sidecars; required before a real run
exits §3/§4/§6. Synthetic fixtures contain metadata only and cannot prove storage integrity.

| Check | Enforcement |
|---|---|
| C01 | Unique manifest/label IDs, matching state/universe/schema versions; all parent/child/prior, alias source, target and supersession references; monotonic acyclic versions |
| C02 | Rights ID/version and URL match, decision mapping/retention; blocked/held = not_attempted + gap; watched-only attestation |
| C03 | Expected child accounting, terminal proof, gap review links; explicit full/partial process coverage, set-derived counts/claim scope, or human-reviewed single-lineage flag |
| C04 | Completion exactly equals retrieved entries per pass; image inspection for none/partial text; count/reason consistency |
| C05 | Different providers, matching brief frozen before dispatch, sealed hashes and isolation attestations; crosswalk covers every pass label and identity merges/splits have review |
| C06 | Phase/author/status, nonempty cohorts, temporal role, evidence hash/location and reviewed UTC policy; duplicate_of resolves |
| C07 | Update before/after or reviewed missing-before; unresolved targets reviewed; posting/first-seen ordering and measured review latency |
| C08 | Seed/frame hash, frame coverage/disposition and strata size rules, deterministic ranking, selected samples completed, review estimate/actual budget |
| C09 | Human completeness verdict; gaps, unknown scope/history, unresolved cases, single-lineage or unfinished review forbid established |
| C10 | Per-state actual + outstanding credits within envelopes and total cap; primary reserve release; path/hash/sidecar linkage (actual bytes with --verify-bytes) |

Automated checks establish internal consistency, not truth of a roster, legal meaning, blindness
or human signatures. Primary must examine these attestations and source evidence. A validator
pass on an incomplete diagnostic run does not mean completeness is established.
