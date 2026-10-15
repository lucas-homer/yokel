# Synthetic census run

This is a tiny WA-shaped synthetic universe, not collected state evidence or a human signoff.
No originals or parser output are included. The external hash paths are illustrative only.
`rights.json` is fixture-only; real runs reference the versioned `rights/surfaces.json` registry.

- `m1` has a carry-in comment opportunity and extension; A/B disagree on the notice title.
- `m2` corroborates only synthetic proceeding `sx-1` of the two-proceeding
  `agency-x/rulemaking` universe. `sx-2` is uncovered: `independent_partial`,
  completeness `not_established`. Both enumeration passes find no candidates in `m2`.
- `m3` is a no-text-layer, single-lineage hearing-request process; both passes reject a duplicate.
- `m4` is an expected source held on rights, never attempted, retained as a reviewed gap.
- The human-shaped review records are synthetic. The completeness decision is `not_established`.

`run.json` freezes process scope, brief/attestations, pass-to-canonical crosswalk, temporal index,
audit frame, reviewer estimates/actuals and four-state credit/reviewer ledger. The fixture brief
is common to both passes; output hashes cover exact JSONL bytes including final newline.
The audit frame is an ordered array of stratum_id, sorted unit_ids, disposition, high_risk and
unit_coverage. Hash sorted-key compact UTF-8 JSON. Unit coverage partitions retrieved manifest
entries; coarsening retains page/attachment IDs under a filing anchor rather than dropping them.
Run schema, manifest, completion, label, sidecar and rights schemas are local Draft 2020-12 files.

From repository root:

```sh
python3 docs/research/state-coverage-plan/census/validate.py
```

A valid synthetic run passes consistency checks while its completeness stays unestablished.
Schema checks clearly skip if jsonschema is unavailable. No installation is needed. Real runs
must also use `--verify-bytes` against their external originals/sidecars; this fixture cannot.

To reproduce a deliberately invalid completeness decision, copy only fixtures to temporary
storage and change the human-shaped decision:

```sh
python3 - <<'PY'
import json, pathlib, shutil, subprocess, tempfile
source = pathlib.Path('docs/research/state-coverage-plan/census/examples')
broken = pathlib.Path(tempfile.mkdtemp(prefix='census-broken-'))
shutil.copytree(source, broken, dirs_exist_ok=True)
p = broken / 'adjudications.jsonl'
rows = [json.loads(line) for line in p.read_text().splitlines()]
next(r for r in rows if r['record_id'] == 'review-completeness')['payload']['decision'] = 'established'
p.write_text(''.join(json.dumps(r) + '\n' for r in rows))
cmd = ['python3', 'docs/research/state-coverage-plan/census/validate.py', str(broken)]
print('$ ' + ' '.join(cmd), flush=True)
result = subprocess.run(cmd)
print('exit:', result.returncode)
assert result.returncode == 1
PY
```

Expected failure: `FAIL C09: established forbidden: rights/source/scope/lineage/review gap`.
Temporary paths vary. Fixture originals and source access are never needed for this check.


R2 coverage and freeze regression fixtures (temporary copies only):

```sh
python3 docs/research/state-coverage-plan/census/examples/check_r2.py
```

The script prints each command/output and asserts exit codes and intended C03/C05/C08 messages.
It breaks partial-as-full, partial-established, agency claim scope, outcome partition,
full-source scope, missing coverage and lineage linkage independently. It also proves a
whole-universe source passes, null freeze fields pass at manifest stage, null audit fields
pass at passes stage, and missing freezes fail at their required stages.
