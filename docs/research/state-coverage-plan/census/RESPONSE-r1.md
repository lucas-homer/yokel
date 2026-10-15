# Response to census review r1

Revised 2026-10-15. All 2 Blockers, 12 Shoulds and 7 Nits addressed; none rejected.
Owner decisions in rights/DECISIONS.md govern this revision. Active census: WA, CT, VA, TN;
MA remains in the template and machine rights record as deferred/blocked. REVIEW-r1.md is unchanged.
Line references below refer to revised files, relative to this directory.

| Finding | Change and evidence |
|---|---|
| 1 (Blocker) | Represent denied/unresolved collection and denied retention; require not_attempted + gap and human reference. Rights/source gaps prohibit established completeness. `manifest.schema.json:94`, `validate.py:114`, `validate.py:348` |
| 2 (Blocker) | Every agency/process needs a resolved different-lineage check or human-reviewed single_lineage flag. A single-lineage process caps completeness at not established. `PROTOCOL.md:117`, `run.schema.json:49`, `validate.py:165` |
| 3 (Should) | Use the preferred deterministic-ID option; compare evidence/aliases, then record every pass-to-canonical mapping. Merge/split requires identity adjudication; crosswalk coverage is executable. `PROTOCOL.md:250`, `run.schema.json:137`, `validate.py:194` |
| 4 (Should) | Add completion schema and enforce exact coverage of retrieved manifest entries per pass, modes, zero reasons, counts and active minutes. `completion.schema.json:4`, `validate.py:175` |
| 5 (Should) | Manifest now carries agency/process, format/cycle/text layer. Union disposition defines no-candidate units; both-empty, exclusion and scan strata receive all-up-to-20 priority and protected floors. `manifest.schema.json:326`, `PROTOCOL.md:209` |
| 6 (Should) | Owner reviewer; 240 minutes/state, 960 total. Worked estimate precedes seed; ordered grouping/reduction preserves min(N,5) exclusion/empty and scan floors. Over-budget mandatory work stops/narrows claims; actual minutes logged. `PROTOCOL.md:185`, `run.schema.json:336`, `../scorecards/TEMPLATE.md:70` |
| 7 (Should) | Freeze identical brief text/hash before either dispatch; prefer concurrent passes; attest and verify freeze/dispatch/seal times. `PROTOCOL.md:131`, `validate.py:188` |
| 8 (Should) | Require cohorts and opportunity close/hearing-start temporal entry. Allow empty update targets only with unresolved reason and mandatory human review, preserving evidence instead of inventing an opening notice. `labels.schema.json:657`, `PROTOCOL.md:258` |
| 9 (Should) | Add primary role and phase/author/status conditions; human task/provider nullable. Cross-record author/provider/task checks remain active without jsonschema. `labels.schema.json:63`, `validate.py:225` |
| 10 (Should) | Add completeness_verdict/scope triggers and established/not_established/narrowed decisions; gap links resolve to human records; final verdict checked against all limitations. `labels.schema.json:824`, `validate.py:344` |
| 11 (Should) | Empty before evidence requires nonempty missing reason plus unresolved state or human reference in schema, and an actual human review in final validation. `labels.schema.json:606`, `validate.py:260` |
| 12 (Should) | Create authoritative-decision-derived versioned surfaces registry and rights schema. Map holds/blocks into manifest, check URL/state/version/retention, include MA deferred and watched-only TN. `rights-surface.schema.json:4`, `PROTOCOL.md:30` |
| 13 (Should) | Move text-layer testing/failure locators into acquisition. Both pass completions require image/both inspection for none/partial; feed risk into sampling. `PROTOCOL.md:113`, `validate.py:179` |
| 14 (Should) | Provide offline stdlib validator with optional jsonschema, explicit numbered checks and stage-specific zero-error gates; external-byte checking mandatory for real runs. `validate.py:29`, `PROTOCOL.md:350` |
| 15 (Nit) | Duplicate rejection requires nonempty resolvable duplicate_of. `labels.schema.json:764`, `validate.py:249` |
| 16 (Nit) | Seed is exactly 64 lower-case hexadecimal characters in labels/run schemas and cross-record checks. `labels.schema.json:900`, `validate.py:335` |
| 17 (Nit) | Replace inline evidence/temporal definitions with $ref to shared definitions (including temporal evidence). `labels.schema.json:179` |
| 18 (Nit) | Remove supersedes_log_id; top-level supersedes_record_id is the only supersession link. `labels.schema.json:32` |
| 19 (Nit) | Add sidecar schema with append-only captures array for shared hashes; external-byte mode checks saved digest, length and capture linkage. `sidecar.schema.json:15`, `validate.py:131` |
| 20 (Nit) | Cite observed benchmark 340 Agentic credits/34 pages, dated assumption; freeze WA/CT/VA 2,000 each, TN 4,000, primary reserve 2,000 within 12,000. `PROTOCOL.md:311`, `../scorecards/TEMPLATE.md:69` |
| 21 (Nit) | Mark all research entity prefixes migratable by contract-keeper in Phase 2, with crosswalk migration; rejects use census-candidate. `PROTOCOL.md:243`, `labels.schema.json:745` |

## Validation evidence

Command: `python3 docs/research/state-coverage-plan/census/validate.py`

```text
SKIP schema validation: jsonschema not importable; cross-record checks still run.
PASS cross-record checks C01–C10; consistency only, not a completeness claim.
Storage bytes not checked; real run gates require --verify-bytes.
```

Exit 0. `--stage manifest` and `--stage passes` also exit 0 on the synthetic run.
The fixture includes a rights-held source, single-lineage process, adjudicated disagreement,
rejected duplicate, carry-in and update. Original bytes were not collected or stored.
Schema execution is skipped honestly; no packages installed. External-byte validation remains
required for real census gates and was not claimed for synthetic metadata.

Deliberately broken copy (reproducible command in examples/README.md):

```text
$ python3 docs/research/state-coverage-plan/census/validate.py /var/folders/7w/yjwplnp54dlcwbkwfmh7pygh0000gn/T/census-completeness-i599weeb
SKIP schema validation: jsonschema not importable; cross-record checks still run.
FAIL C09: established forbidden: rights/source/scope/lineage/review gap
1 error(s).
exit: 1
```

The copy changes only review-completeness.decision to established. Further isolated mutations
also exit 1: remove the reviewed single-lineage flag → C03; null duplicate_of → C06;
mark the rights-held source accounted → C02 and C03. Originals remain untouched.

## Files and remaining work

Updated PROTOCOL.md, manifest.schema.json, labels.schema.json, STATE-UNIVERSE-TEMPLATE.md and
../scorecards/TEMPLATE.md. Added completion.schema.json, rights-surface.schema.json,
sidecar.schema.json, run.schema.json, validate.py, examples/ and this response; the only rights/
write is ../rights/surfaces.json. No network, installs, databases, commits or pushes.

No design decision remains open. Source outreach remains open where the registry says so;
MA is deferred, CT JSON and VA listings held, TN attended-only. Before a real census, the primary
must supply actual process rosters, lawful independent-lineage evidence (or explicit caps),
measured review estimates and external-byte checks. Human truth/signature/access-isolation
attestations require review; consistency checks cannot establish them.
