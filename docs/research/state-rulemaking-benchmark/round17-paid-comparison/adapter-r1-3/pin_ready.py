"""Pin this offline candidate without opening source texts or references; stdlib only."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
BENCH = R17.parent


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def forbidden(name):
    return ('reference/' in name or name.endswith('/parsed-body.txt') or name.endswith('/original.htm'))


old = json.loads((R17 / 'adapter/READY.json').read_bytes())
# Check the frozen original payload against its recorded pins, not just our copy.
for name, expected in old['files'].items():
    assert pin(R17 / 'adapter' / name) == expected, 'frozen_adapter_changed:' + name
files = {p.relative_to(HERE).as_posix(): pin(p) for p in sorted(HERE.rglob('*'))
         if '_out' not in p.relative_to(HERE).parts and p.is_file() and p.name != 'READY.json'}
assert not any('__pycache__' in n or '/.review-' in n or '/.offline-' in n for n in files)
assert not any(forbidden(n) for n in files)
deps = dict(old['dependencies'])
for name, expected in deps.items():
    assert not forbidden(name), 'forbidden_dependency'
    assert pin(BENCH / name) == expected, 'frozen_dependency_changed:' + name
for path in sorted((R17 / 'adapter').iterdir()):
    if path.is_file():
        deps[path.relative_to(BENCH).as_posix()] = pin(path)
for path in sorted((R17 / 'adapter-review').iterdir()):
    if path.is_file():
        deps[path.relative_to(BENCH).as_posix()] = pin(path)
# Record actual frozen r1.1 bytes: its known stale repro pin is documented in S6,
# never repaired in place. These dependency pins detect any subsequent mutation.
for path in sorted((R17 / 'adapter-r1-1').rglob('*')):
    if path.is_file():
        deps[path.relative_to(BENCH).as_posix()] = pin(path)
deps['round17-paid-comparison/adapter-review-r2/REVIEW.md'] = pin(R17 / 'adapter-review-r2/REVIEW.md')
for path in sorted((R17 / 'adapter-review-r2').rglob('*')):
    if path.is_file() and path.suffix in ('.py', '.sh'):
        deps[path.relative_to(BENCH).as_posix()] = pin(path)
prior = json.loads((R17 / 'adapter-r1-2/READY.json').read_bytes())
for name, expected in prior['files'].items():
    assert pin(R17 / 'adapter-r1-2' / name) == expected, 'frozen_r1_2_changed:' + name
    deps['round17-paid-comparison/adapter-r1-2/' + name] = expected
deps['round17-paid-comparison/adapter-r1-2/READY.json'] = pin(R17 / 'adapter-r1-2/READY.json')
output = (HERE / '_out/test-output.txt').read_text()
counts = [int(n) for n in re.findall(r'^Ran (\d+) tests', output, re.M)]
assert counts == [102, 26, 23, 9, 20, 10], counts
assert len(re.findall(r'^OK$', output, re.M)) == 6
assert not re.search(r'^FAILED|^ERROR:|^FAIL:', output, re.M)
review_map = {f'S{i}': 'fixed' for i in range(1, 7)}
review_map.update({f'N{i}': ('documented_deferred' if i in (6, 7, 10, 11) else 'fixed')
                   for i in range(1, 14)})
review_map.update({f'N{i}': ('documented_deferred' if i == 17 else 'fixed') for i in range(14, 22)})
ready = dict(schema_version='r17.adapter-ready.v1', revision='r1.3',
    status='READY_OFFLINE_IMPLEMENTATION', release_policy='UNSET',
    files=files, sha256={n: v['sha256'] for n, v in files.items()}, dependencies=deps,
    self_pin='READY.json excludes itself; P7 must pin this exact file hash externally.',
    excluded_paths=['_out/**'],
    output_policy='All generated logs and temporary test artifacts under excluded _out; no CA bundle pin.',
    tests=dict(run=sum(counts), passed=sum(counts), failed=0, result='OK',
        original_adapter_integration_tests=77, revision_adapter_and_cli_tests=26,
        adapter_integration_tests=103, host_driver_tests=23, ledger_fixture_tests=25,
        ledger_fixture_ids='L01-L25 (pin/engine only, not adapter coverage)',
        repro_behavior_checks=8, repro_copy_integrity_tests=1,
        round2_targeted_tests=20, native_integration_tests=10, pin_stability_test='python3 -I -S -B adapter-r1-3/verify_ready.py (1 additional test; reruns all 190)',
        command='sh adapter-r1-3/run_tests.sh', python_flags='python3 -I -S -B <script>',
        temporary_writes='adapter-r1-3/_out; removed except logs/repro copies',
        output='_out/test-output.txt',
        transport='fake HTTPSConnection and real http.client over fake sockets only', environment='replacement synthetic mapping only',
        clock='fake, plus patched production-clock boundary test'),
    repros=dict(baseline_reproduced=8, r1_1_fixed_behavior=8,
        copies_changed_only='round-1 _load.py adapter import and temporary output directory; round-2 _load.py import paths only',
        command='sh adapter-r1-3/repros/run_all.sh',
        original_exit_convention='0 = finding reproduced; all 8 now exit 1',
        output='_out/repro-r1-3.txt', behavioral_assertions='test_repros.py',
        round2_command='sh adapter-r1-3/_out/round2-repros/run_all.sh',
        round2_output='_out/round2-repro-output.txt',
        round2_results={'repro_3call_plan.py': 0, 'repro_hd_cli_misc.py': 1,
            'repro_hd_key_fields.py': 0, 'repro_hd_sigint_cli.py': 1,
            'repro_hd_timeout_row2.py': 0, 'repro_hd_trust_store.py': 1, 'repro_hd_wire.py': 0},
        interpretation='SPEC.md round-2 repro disposition; unchanged assertions sometimes expect old defects'),
    dispositions=review_map,
    H_mapping={f'H{i}': ('external_pre_run_NTP_evidence' if i == 10 else
        'implemented_and_offline_tested_with_external_signature_and_READY_pin' if i == 9 else
        'implemented_and_offline_tested_with_operator_serialization_and_lock_evidence' if i == 8 else
        'implemented_and_offline_tested') for i in range(1, 11)},
    H_mapping_details='SPEC.md Host driver H1-H10 mapping',
    credential_boundary='Only uninvoked production post_once/key_info read OPENROUTER_API_KEY. Tests replace environment and HTTPSConnection; no real credential access.',
    credentials_accessed=False, network_calls=0, provider_calls=0, native_runner_or_jobs_run=False,
    r17_source_texts_read=False, r17_reference_files_read=False, frozen_adapter_unchanged=True,
    committed=False, paid_release_authorized=False, action_ready=False, production_eligible=False,
    invoice_verified=False,
    P7_outstanding=['Independent primary re-review and pin of r1.3 + host driver',
        'P0/P1/P5/P6/P8 evidence and gates; real policy remains UNSET',
        'Live usage field/units confirmation and dedicated-key zero machine check',
        'Signed INIT/C6 release/BIND_RELEASE and externally pinned READY hash',
        'Mini NTP sync evidence and unverified hardware durability',
        'N6 wall clock, N7 FULL reporting vocabulary, N10 library hook, N11 F_FULLFSYNC deferred',
        'Per-call staged adjudication and frozen OPQ pass before FULL'])
ready['A3'] = dict(post_read_seconds=600, connect_write_seconds=15, key_get_total_seconds=15, post_total_seconds=615, conservative_cell_seconds=1590, recovery_only_seconds=960, local_job_deadline_seconds=1740, native_timeout_seconds=1800)
ready['tests']['interpreters'] = json.loads((HERE / '_out/interpreters.json').read_bytes())
ready['repros']['round2_results_provenance'] = 'Inherited r1.2 historic output; round-2 unchanged-repro integrity and behavioral regressions pass under r1.3. Raw round-2 repro scripts were not rerun in r1.3.'
(HERE / 'READY.json').write_text(json.dumps(ready, sort_keys=True, indent=2) + '\n')
# Verify every local/dependency pin after writing, including the pinning script itself.
for name, expected in ready['files'].items():
    assert pin(HERE / name) == expected, name
for name, expected in ready['dependencies'].items():
    assert pin(BENCH / name) == expected, name
print('READY r1.3: 190 tests passed; 25 engine fixtures excluded from adapter coverage; 8/8 round-1 repro fixes.')
print('All payload/dependency pins verified; frozen adapter verified unchanged.')
print('READY.json sha256=' + pin(HERE / 'READY.json')['sha256'])
