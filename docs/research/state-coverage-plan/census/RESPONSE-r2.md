# Census implementation response r2

2026-10-15. Both gaps implemented offline. References are relative to this directory.

## Design and changed files

- `PROTOCOL.md:117`: require a roster-backed coverage universe of agency/process rows or
  enumerated proceedings, independent source scope and matched/mismatched/unresolved ID sets.
  `independent_full` needs a source expected to cover the whole universe; partial sources
  corroborate only their subsets. Partial coverage always leaves process completeness
  `not_established`; reviewer-approved narrowing requires a new universe and rescore.
- `PROTOCOL.md:163`, `PROTOCOL.md:310`, `PROTOCOL.md:334`: null pre-freeze fields, scoped
  scoring/decision claims and stage-specific freeze requirements.
- `run.schema.json:59`: optional process `coverage` object with explicit mode, unit kind,
  universe/basis, checks/basis, expected/outcome IDs, claim agencies and completeness.
  Optionality preserves legacy **reviewed single-lineage** rows, not independent claims.
  `run.schema.json:210`, `run.schema.json:371`: nullable brief hash/time and audit seed/frame
  hash; audit `frozen_before_seed` accepts false while planning. Pass attestations remain sealed.
- `validate.py:157`: C03 replaces existential lineage acceptance with coverage validation:
  directed retrieved different-lineage manifest edge, unique universe/sets, outcomes partition
  expected scope, whole-source coverage, agency claim bounds and completeness cap. Matching
  IDs require a matching edge. Counts are computed from set unions, so repeated checks do not
  inflate coverage; conflicting checks cannot cancel unresolved/mismatched units. Each process
  with coverage prints its computed counts. Legacy independent rows now fail explicitly.
- `validate.py:232`, `validate.py:352`: C05 requires brief freeze at passes/final; C08 requires
  audit freeze at final. Nulls produce check failures at the required stage, without crashing.
- `examples/run.json:16`: partial 1-of-2 proceeding fixture; `examples/README.md:56` and
  `examples/check_r2.py:1`: reproducible temporary positive/broken fixtures with asserted
  exits and intended messages. No original-byte fixtures or state runs changed.

The existing manifest edge structure is retained: per-process coverage links to it and adds
scope/outcome accounting, avoiding duplication on every same-lineage document check. Schema
version stays 1.0.0 as a compatible optional addition; validator independent-claim requirements
are intentionally stronger. Scope-basis truth still requires source/human review; consistency
checks cannot establish whether a publisher really covers the declared universe.

## Migration notes

### CT

No CT files edited. Add `coverage` to `noi` and `nod`, with mode `independent_partial`,
`single_lineage: false`, completeness `not_established`, and DEEP as the only claim agency.
Use `unit_kind: proceeding`, a complete per-process roster with actual agency mappings,
source/interval locators, and the existing DEEP directed cross-check entry IDs. List five NOI
matches (PR2025-028, PR2025-034, PR2024-054, PR2025-035, PR2025-036) and three NOD status
matches (PR2025-008, PR2025-026, PR2023-056) as supported by acquisition evidence. Scope the
claim to the checked facts: a status match does not independently establish every legal date.
Do not label every DEEP proceeding matched merely because it belongs to DEEP: uninspected
expected units are unresolved. If using the reported common 68-proceeding denominator, five
NOI matches leave 63 uncovered and three NOD matches leave 65; confirm the correct denominator
for each process rather than assuming all 68 qualify for both. Current legacy runs have no
machine roster to compute those counts, so the validator reports missing coverage instead.
Keep `rmr-lifecycle` single-lineage; resolve its human review and the two manifest gap reviews
with actual human adjudications, not pending-reference strings.

Replace the zero brief hash/epoch freeze time with nulls until the common brief is frozen.
Replace zero audit seed/frame hash with nulls and `frozen_before_seed: false` until that stage.
The manifest stage permits these nulls. Later stages still need real hashes/attestations.

### VA

No VA files edited. `regulations` (DWR timeline) and `general-notices` (DPOR radon) also need
explicit `independent_partial` coverage unless additional whole-universe evidence is acquired.
Enumerate per-process proceedings/agency rows; map checked DWR/DPOR subsets, mismatches and
unresolved comparisons. The DWR date conflict must remain unresolved/mismatched rather than
being erased by existence corroboration. Claim agencies/IDs stay within the corroborated subset;
process completeness remains `not_established`. Existing `single_lineage: true` rows can retain
the legacy format, but pending human references still require actual adjudications. Resolve
four manifest pending reviews separately. Use nullable planning fields where hashes/time/seed
are not yet real; no audit freeze is required at passes stage.

### WA, MS, TN

No files inspected or edited for migration. Apply the same independent-claim coverage requirement
when their runs are validated; legacy reviewed single-lineage rows remain supported. Use null
brief/audit freeze fields before their respective stages. No state release or completeness
approval is implied.

## Validation evidence

Commands below ran from `census/`. No network, installs, database, node_modules/.env, commits,
pushes or state-directory edits. Schema execution was skipped because `jsonschema` is not
importable; schema JSON parses, but Draft 2020-12 execution is not claimed. External storage
bytes were not verified in this implementation task.

```text
$ python3 validate.py
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
PASS cross-record checks C01–C10; consistency only, not a completeness claim.
Storage bytes not checked; real run gates require --verify-bytes.
exit: 0
```

```text
$ python3 examples/check_r2.py
$ python3 validate.py <temporary:partial-as-full> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_full; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
FAIL C03: agency-x/rulemaking independent_full requires a whole-universe independent source; partial coverage is insufficient
1 error(s).
$ python3 validate.py <temporary:partial-established> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
FAIL C03: agency-x/rulemaking partial/uncovered or discrepant coverage requires completeness not_established
1 error(s).
$ python3 validate.py <temporary:outside-agency-claim> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
FAIL C03: agency-x/rulemaking claim agencies exceed corroborated subset
1 error(s).
$ python3 validate.py <temporary:missing-outcome> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=0 matched=0 mismatched=0 unresolved=0 uncovered=2
FAIL C03: agency-x/rulemaking coverage outcomes must partition expected subset of universe
FAIL C03: agency-x/rulemaking independent_partial needs a covered subset
FAIL C03: agency-x/rulemaking claim agencies exceed corroborated subset
3 error(s).
$ python3 validate.py <temporary:full-scope-subset> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
FAIL C03: agency-x/rulemaking full source scope must cover whole universe
1 error(s).
$ python3 validate.py <temporary:legacy-independent> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
FAIL C03: agency-x/rulemaking independent claim requires explicit coverage (partial cross-check cannot establish whole process)
1 error(s).
$ python3 validate.py <temporary:same-lineage-edge> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=0 matched=0 mismatched=0 unresolved=0 uncovered=2
FAIL C03: agency-x/rulemaking coverage check lacks retrieved different-lineage manifest edge
FAIL C03: agency-x/rulemaking independent_partial needs a covered subset
FAIL C03: agency-x/rulemaking claim agencies exceed corroborated subset
3 error(s).
$ python3 validate.py <temporary:whole-source> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_full; universe=2 expected=2 matched=2 mismatched=0 unresolved=0 uncovered=0
PASS cross-record checks C01–C03/C10 storage; consistency only, not a completeness claim.
Storage bytes not checked; real run gates require --verify-bytes.
$ python3 validate.py <temporary:unfrozen-manifest> --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
PASS cross-record checks C01–C03/C10 storage; consistency only, not a completeness claim.
Storage bytes not checked; real run gates require --verify-bytes.
$ python3 validate.py <temporary:audit-unfrozen-passes> --stage passes
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
PASS cross-record checks C01–C05/C10 storage; consistency only, not a completeness claim.
Storage bytes not checked; real run gates require --verify-bytes.
$ python3 validate.py <temporary:unfrozen-passes> --stage passes
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
FAIL C05: brief hash/frozen time required at passes/final stage
FAIL C05: brief hash mismatch
FAIL C05: pass_A brief/isolation/times
FAIL C05: pass_B brief/isolation/times
4 error(s).
$ python3 validate.py <temporary:unfrozen-final> --stage final
SKIP schema validation: jsonschema not importable; cross-record checks still run.
C03 coverage agency-x/rulemaking: independent_partial; universe=2 expected=1 matched=1 mismatched=0 unresolved=0 uncovered=1
FAIL C05: brief hash/frozen time required at passes/final stage
FAIL C05: brief hash mismatch
FAIL C05: pass_A brief/isolation/times
FAIL C05: pass_B brief/isolation/times
FAIL C08: audit seed/frame hash/freeze required at final stage
FAIL C08: invalid seed or unfrozen audit plan
FAIL C08: audit frame hash mismatch
7 error(s).
PASS all r2 fixture assertions (7 broken coverage cases, full coverage, and 4 freeze-stage cases).
exit: 0
```

```text
$ python3 validate.py CT --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
FAIL C03: ct-gap-law-journal gap/pending needs human review
FAIL C03: ct-xchk-portal-deep-rbcr gap/pending needs human review
FAIL C03: ct-uapa-agencies/noi independent claim requires explicit coverage (partial cross-check cannot establish whole process)
FAIL C03: ct-uapa-agencies/nod independent claim requires explicit coverage (partial cross-check cannot establish whole process)
FAIL C03: rmr-lifecycle needs independent lineage or reviewed single_lineage
5 error(s).
exit: 1
```

```text
$ python3 validate.py VA --stage manifest
SKIP schema validation: jsonschema not importable; cross-record checks still run.
FAIL C03: va-xa-deq-home gap/pending needs human review
FAIL C03: va-xa-mrc-home gap/pending needs human review
FAIL C03: va-xa-doe-home gap/pending needs human review
FAIL C03: va-xa-gov-webpolicy gap/pending needs human review
FAIL C03: register-issue needs independent lineage or reviewed single_lineage
FAIL C03: noira needs independent lineage or reviewed single_lineage
FAIL C03: va-register-agencies/regulations independent claim requires explicit coverage (partial cross-check cannot establish whole process)
FAIL C03: governor needs independent lineage or reviewed single_lineage
FAIL C03: va-register-agencies/general-notices independent claim requires explicit coverage (partial cross-check cannot establish whole process)
FAIL C03: petitions needs independent lineage or reviewed single_lineage
FAIL C03: periodic-review needs independent lineage or reviewed single_lineage
FAIL C03: errata needs independent lineage or reviewed single_lineage
12 error(s).
exit: 1
```

```text
$ python3 -m unittest test_capture.py
............................
----------------------------------------------------------------------
Ran 28 tests in 0.177s

OK
exit: 0
```

CT has 5 errors: 2 newly rejected unscoped independent claims and 3 unresolved human-review
links. VA has 12 errors: 2 newly rejected unscoped independent claims and 10 unresolved
human-review links. Neither validator invocation crashes. All 28 capture tests pass.
The r2 fixture runner verifies seven broken coverage cases, a valid whole-source case and
four stage/freeze cases; expected broken runs exit 1, runner exits 0.

Remaining work belongs to acquisition/human review: populate real coverage rosters and scopes,
resolve human reviews, and verify external originals. No implementation decision is pending.
