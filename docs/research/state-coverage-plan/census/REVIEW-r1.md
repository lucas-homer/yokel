# Census protocol review, round 1

Reviewed 2026-10-15 by the Claude review child (read-only). Files reviewed: `PROTOCOL.md`,
`manifest.schema.json`, `labels.schema.json`, `STATE-UNIVERSE-TEMPLATE.md`,
`../scorecards/TEMPLATE.md`, against `docs/plans/state-coverage.md`, ADR 0013 and
`../PLAN-REVIEW.md` (B1, S1–S6). I also looked at the headers of `../rights/*.md` to check the
rights handshake. Line numbers refer to the files as they stand in this worktree.

**Verdict: accept-with-changes.** The design is faithful to B1 and the plan: cohorts are separate,
rejected candidates are kept with evidence, blindness is a real mechanism rather than a filename
convention, the statistics match the plan exactly, and completeness correctly gates the statewide
claim. Two findings are blockers because each lets a state census look complete while a source is
silently absent. Both are small, local edits. No state run should start until they are fixed. The
remaining items tighten enforcement and operability.

## Findings

### 1. Blocker — a rights-blocked source cannot appear in the manifest

`manifest.schema.json:91-96` pins `rights.collection_rule` to the constant `allowed` and
`rights.retention_allowed` to `true`. `PROTOCOL.md:31-32` says blocked essential sources make
completeness *pending, not an empty census*, and `PROTOCOL.md:77-78` requires entries for
inaccessible slices.

Failure scenario: MA Register is denied or unresolved on retention. The only schema-valid
manifest has no MA Register entries at all. Every remaining entry is `accounted`, the §3 exit
("all expected units accounted for") passes mechanically, and the public-page-only census scores
itself at 100% against itself. This is exactly the circularity the plan's MA note forbids
(`docs/plans/state-coverage.md:117-118`).

Fix: make `collection_rule` an enum `allowed | denied | unresolved`, `retention_allowed` a
boolean, and add an `allOf` rule: `retrieval.result == "retrieved"` requires
`collection_rule == "allowed"` and `retention_allowed == true`; any other rule requires
`retrieval.result == "not_attempted"` and `completeness == "gap"`. Then the blocked source is
visible in the manifest as a gap and the completeness verdict has something to point at.

### 2. Blocker — nothing enforces an independent-lineage cross-check, so the manifest can be the adapter's own index

`PROTOCOL.md:95-97` asks for register-versus-history cross-checks and `PROTOCOL.md:202` states the
principle, but no exit criterion or schema rule requires one. `manifest.schema.json:249-277`
allows `cross_checks: []`, and `lineage_id` (`:28-31`) is recorded but never used by any rule.

Failure scenario: a VA manifest is derived entirely from Town Hall's date-filtered listing, the
adapter later reads the same listing, both passes enumerate from it, and recall reads 100%
while non-portal agencies are never counted. PLAN-REVIEW B1 names this as the core failure.

Fix: in §3 exit, require for every (agency, process) row in the universe either (a) at least one
`cross_checks` entry with `result != "unresolved"` whose `against_entry_id` resolves to an entry
with a *different* `lineage_id`, or (b) an explicit `single_lineage: true` flag on the universe
row with a human review ref. Add to §6: a process with `single_lineage` cannot contribute to an
"established" completeness verdict; its recall is reported as not established. Add
`lineage_id` to the cross-check object so the validator can check (a) without a join.

### 3. Should — pass-local IDs contradict the label schema; the crosswalk has no record

`PROTOCOL.md:184-185` says A and B mint only pass-local keys and the primary keeps a sealed
pass-to-canonical crosswalk. `labels.schema.json:424-426, 479-481, 521-523, 757-759` require every
pass-A and pass-B record to carry a canonical `ocd-…/state-xx/…` entity ID, and no record type
represents the crosswalk.

Failure scenario: a child follows the schema and mints `ocd-notice/state-wa/wsr-26-18-042`. The
other child, from the same tuple rule in §6, mints the same string. The primary cannot tell
whether agreement is on evidence or on an ID collision, and the crosswalk lives in an undocumented
file.

Fix: pick one. Preferred: drop "pass-local" and let both passes mint deterministic
tuple-hash IDs from the universe's documented identity tuple, with comparison still done on
evidence and aliases (§5 already says so); then add an `identity` adjudication for every
merge/split. Alternative: add `pass_local_id` to the base record, require it for `pass_A`/`pass_B`
phases, and add a `crosswalk` record type (`pass_local_id`, `canonical_entity_id`,
`adjudication_ref`).

### 4. Should — the pass completion log, the thing that proves coverage of the whole manifest, has no schema

`PROTOCOL.md:15-17, 109-110, 126, 274-275` require per-unit completion logs with zero-candidate
units, counts and reasons, and the §4 exit depends on them covering the entire manifest. No
format is given; "where applicable" (`:17`) means it is free-form.

Failure scenario: pass B logs "read issue 26-18" at issue level; the primary cannot show that
page 143 was opened, and the audit's "no candidates" stratum cannot be built.

Fix: add `completion.schema.json` (or a `completion` record type in the labels schema) with
`manifest_entry_id`, `pass`, `inspection_mode` (`native_text | rendered_image | both | json`),
`candidate_count`, `rejected_count`, `zero_candidate_reason` (nullable), `minutes`. Validator
rule: the set of `manifest_entry_id` values equals the set of retrieved manifest entries, per
pass.

### 5. Should — audit strata cannot be built from the manifest, and the shared-blind-spot stratum gets no extra weight

`PROTOCOL.md:155-156` strata are source/process × format × publication cycle × disposition. The
manifest has `source_id` but no process, no format and no cycle field
(`manifest.schema.json:3-307`). Disposition depends on pass output, but the protocol does not say
whose: if A found a candidate on a page and B found none, the page's stratum is undefined.

Failure scenario: the one stratum where both passes found nothing is the only place a shared
miss can hide (same native-text gap, same template skip). It is sampled at the same 20% as every
other stratum.

Fix: add `process_id`, `format` (`html | json | text_pdf | scan_pdf | mixed`) and
`publication_cycle` to manifest entries; define disposition as the *union* of both passes
(`no_candidates` only when both passes report zero); sample the both-empty stratum and the
`scan_pdf`/no-text-layer stratum at 100% up to a cap, and say so in the sampling record.

### 6. Should — human reviewer load is never estimated or capped

`PROTOCOL.md:146-148` (every consequential date and role for up to 150 opportunities),
`:159` (≥5 or 20% per stratum, union of pages, issues and slices) and `:161-163` (each selected
unit read in full, issues included) together specify the load, but neither the protocol nor the
templates estimate it or say what happens when it exceeds the budget named at §1 entry (`:24`).
`STATE-UNIVERSE-TEMPLATE.md:74` and `../scorecards/TEMPLATE.md:57-58, 66` record hours only after
the fact.

Failure scenario (WA, four-week slice): two register issues, N=2 per issue stratum, so both are
read "in full", plus ~20% of several hundred pages across a dozen strata, plus ~150 × ~3 temporal
entries, plus all disagreements. That is tens of hours per state before adjudication, with five
states in a three-week Phase 1.

Fix: add a "reviewer budget" paragraph to §5 with a worked estimate formula (mandatory items +
Σ per-stratum sample × minutes per unit type), require the estimate in the universe template
before sampling, and state the rule when the estimate exceeds the budget: coarsen the audit unit
(filing/notice instead of page) or reduce strata, recorded before the seed is drawn; never skip
drawn samples. Clarify that an *issue* audit verifies contents/page/attachment accounting, not a
cover-to-cover read.

### 7. Should — brief must be frozen before either pass runs, and passes should be dispatched concurrently

`PROTOCOL.md:105-106` records "exact brief/version" and `STATE-UNIVERSE-TEMPLATE.md:61` has a
brief-hash blank, but nothing requires the brief to exist before pass A starts. Isolation
(`:113-117`) covers A's output reaching B, not the primary's own context.

Failure scenario: A runs first, reports "13 filings, one partial withdrawal" to the primary; the
primary then writes B's brief and, without intending to, mentions withdrawals. B is no longer
blind.

Fix: §4 entry adds "brief text written and hashed before either dispatch; both passes receive
the identical hashed text"; prefer concurrent dispatch; record the hash in both passes'
attestations.

### 8. Should — carry-in, lifecycle and cohort records can be silently incomplete

Three gaps, each in the "silently dropped" family:

- `labels.schema.json:92-103` `cohorts` has no `minItems`; an opportunity with `cohorts: []` is
  valid and falls out of every cohort denominator. Fix: `minItems: 1` for `notice`,
  `opportunity` and `update` records.
- `labels.schema.json:559-561` `opportunity.temporal` has no `minItems`; a comment window with no
  recorded deadline (even `status: unknown`) is valid. Fix: `minItems: 1`, and require one entry
  with role `close` or `hearing_start` (nullable value, `status` may be `unknown`).
- `labels.schema.json:778-785` `update.target_opportunity_ids` requires an existing opportunity
  ID, but an update to a proceeding whose original notice is outside the backward boundary has
  no capturable opportunity record (evidence `minItems: 1` at `:1362-1368` needs a manifest
  entry). Fix: allow a stub opportunity with `review_status: needs_review` whose evidence is the
  update's own text, or add `target_unresolved_reason` and route it to mandatory human review.

### 9. Should — schema does not tie phase, author and review status together

`labels.schema.json:48-87` and the `allOf` at `:1328-1370` only constrain `adjudication` records.
A `pass_B` record authored by `pass_A_child`, or an `adjudicated` notice with
`review_status: candidate` and author `pass_A_child`, is valid. The adjudicated gold snapshot is
assembled by the primary, which is not an `author.role` value at all.

Fix: add `primary` to `author.role`; add rules `phase: pass_A ⇒ role: pass_A_child`,
`phase: pass_B ⇒ role: pass_B_child`, `phase: adjudicated ⇒ role ∈ {primary, human_reviewer}`
and `review_status ≠ candidate`. Make `task_id`/`provider` nullable for `human_reviewer`.

### 10. Should — the completeness verdict and the "gap queued to review" link have no record

`PROTOCOL.md:172` requires a human-signed completeness verdict and `:99` says gaps are queued to
human review, but `labels.schema.json:1183-1193` has no `completeness` or `scope` trigger and
`manifest.schema.json:295-307` allows `completeness: gap` with `human_review_ref: null` (the
example at `:448-449` does exactly that).

Fix: add `completeness_verdict` and `scope` to the adjudication `trigger` enum with a required
`decision` of `established | not_established | narrowed`; in the manifest, `completeness == "gap"
⇒ human_review_ref: string`.

### 11. Should — update before/after rule not enforced

`PROTOCOL.md:276` requires before bytes or a human-reviewed missing-before reason.
`labels.schema.json:805-842` allows `before_evidence: []` with `before_missing_reason: null`.

Fix: `if before_evidence is empty then before_missing_reason: string (minLength 1) and
unresolved or human_review_ref non-empty`.

### 12. Should — rights handshake assumes fields the rights records do not have

`PROTOCOL.md:25-27` expects a versioned rights record with `collection_rule`, method, rate and
retention permission, and `manifest.schema.json:80-118` requires `record_ref` and `version`. The
rights child's files (`../rights/WA.md` etc.) are prose tables with "stated/inferred/unknown"
confidence and a "Blocked pending reviewer" list; they have no version or decision field.

Fix (decision for the primary): either the rights child adds a short decision block per surface
(`surface_id`, `version`, `collection_rule`, `retention`, `third_party`, `public_evidence`,
`reviewer`, `date`) or PROTOCOL §1 says the primary derives that block and stores it as
`rights/<state>-decisions.json`, which `record_ref` then points to. Until one exists, §1 cannot
exit for any state.

### 13. Should — native-text failure logging happens too late to protect the passes

`PROTOCOL.md:229-230` logs native-text failures in §7 (sizing). `PROTOCOL.md:108-109` tells both
passes that "native text aids navigation", so a page whose text layer is empty or garbled is a
shared blind spot across both passes and the same LlamaParse output, if used, would be shared too.

Fix: move native extraction and the per-page failure log into §3 as a manifest attribute
(`text_layer: native | none | partial`); require `inspection_mode: rendered_image` in both
completion logs for `none`/`partial` pages; feed that field into finding 5's stratum.

### 14. Should — validator is specified but has no home

`PROTOCOL.md:269-280` lists cross-record checks that the exit criteria depend on. No script,
location or owner is named, so "checkable by the primary" currently means "re-read by hand".

Fix: name the artifact (for example `tools/census-validate.ts` or a Python script under
`tools/`), list its checks as a numbered table mirroring §Validation, and make "validator passes
with zero errors" the literal exit condition for §3, §4 and §6. Writing it is Phase 1 step 3
work, not this design, but the design should name it.

### 15. Nit — `duplicate` rejection without `duplicate_of`

`labels.schema.json:1141-1160`: `reason_code: duplicate` with `duplicate_of: null` is valid.
Fix: conditional requiring a string.

### 16. Nit — audit seed format

`PROTOCOL.md:154` says a 256-bit hex seed; `labels.schema.json:1270-1273` accepts any non-empty
string. Fix: `pattern: ^[a-f0-9]{64}$`.

### 17. Nit — unused `$defs` and duplicated inline copies

`labels.schema.json:204-417` defines `evidence` and `temporal` but every use is an inline copy
(`:125-163, :354-391, :559-738, :805-881, :927-1106`). Drift risk when one copy is edited. Fix:
`$ref` the definitions.

### 18. Nit — redundant supersession fields

`labels.schema.json:32-37` `supersedes_record_id` and `:1249-1254` `supersedes_log_id` both exist
for adjudication records. Keep the top-level one.

### 19. Nit — sidecar has no schema

`PROTOCOL.md:85-88` lists sidecar fields in prose. A ten-line `sidecar.schema.json` would let the
validator check "hash prefix/path equality and sidecar linkage" (`:273`).

### 20. Nit — credit assumption is unsourced and the per-state split is undefined

`PROTOCOL.md:230-232` and `../scorecards/TEMPLATE.md:64-65` assume ~10 credits per Agentic page.
Nothing in the repo records that figure or its date (`INVENTORY.md:85` has only round-level
credit totals). The cap is correctly shared across five states, but "stop paid work when
actual + reserved would exceed cap" can starve the last state. Fix: cite the price source and
date in the ledger; predeclare per-state reservations before any state submits a page.

### 21. Nit — ID prefixes beyond the plan's

`PROTOCOL.md:178` mints `ocd-notice`, `ocd-proceeding`, `ocd-update` and `ocd-candidate`. The plan
reserves only `ocd-participation-window/state-xx/…` for Phase 2 (`docs/plans/state-coverage.md:187`)
and contract-keeper owns ID minting. Rejected candidates in particular do not need an OCD-style
ID. Fix: keep the four provisional entity prefixes but add a sentence that Phase 2 may rename
them and that the crosswalk is the migration path; use `census-candidate/…` for rejects.

## Checks that passed

- Statistics: `1 - 0.05^(1/n)` values and the 149 figure match the plan and S1 exactly.
- Scope and counting rules match the plan's "Definition of covered" (two opportunities for a
  notice with a window and a hearing; duplicate listing is not a notice; hearing requests in
  scope; lifecycle events include shortened periods, corrections, replacements and reversions
  per S3).
- Per-state notes in the universe template match the plan's S6 scorecard notes for all five
  states, including the WA 14-rows/13-IDs case, CT period GUIDs, VA NOIRA, MA Register
  denominator and literal "EST", and the TN accommodation-versus-comment fixture.
- Rights-first ordering is correct in §1 and in both templates; third-party processing is a
  separate permission, which matches S8.
- Dev-fixture / sealed-historical / live-interval split in §7 is required by the plan's Phase 3
  acceptance, not overreach. "Phase 1 does not pass a release gate" is stated.
- Cap of 12,000 credits is stated as Phase 1 total, not per state, in both protocol and scorecard.
- No federal behaviour is touched; "existing federal ID validators are unchanged" is explicit.
- Both schemas are Draft 2020-12 and the single examples validate (per the brief); this review
  checked coverage, not syntax.

## Compact report

- **Verdict:** accept-with-changes. Fix findings 1 and 2 before any state run; the rest can land
  in the same revision.
- **Blockers:** 2.
- **Top three:**
  1. Manifest schema cannot represent a rights-blocked source, so a blocked essential source
     vanishes from the denominator (finding 1).
  2. No enforced independent-lineage cross-check per process, so the manifest can be the adapter's
     own index and recall becomes circular (finding 2).
  3. Human reviewer load is unbounded and unestimated given 20%-per-stratum audits over pages,
     issues and slices plus full date/role checks (finding 6).
- **Decision needed from the primary:** finding 12, the rights-record format handshake with the
  rights child.
