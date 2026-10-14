"""Freeze A4 offline payloads after both interpreter suites; never reads body/reference files."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
BENCH = R17.parent
FOLDERS = ('recon-a4', 'adapter-r1-4', 'release-prep-a4')


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def forbidden(name):
    return 'reference/' in name or name.endswith(('/parsed-body.txt', '/original.htm'))


def payload(root):
    return {p.relative_to(root).as_posix(): pin(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '_out' not in p.relative_to(root).parts and p.name != 'READY.json'}


def verify_frozen():
    before = json.loads((R17 / 'recon-a4/_out/frozen-before.json').read_bytes())
    actual = {p.relative_to(R17).as_posix(): pin(p)
              for folder in ('adapter-r1-3', 'release-prep', 'design-r3-1')
              for p in sorted((R17 / folder).rglob('*')) if p.is_file()}
    assert actual == before, 'frozen inputs changed'
    return before


def write(folder):
    frozen = verify_frozen()
    root = R17 / folder
    files = payload(root)
    assert not any(forbidden(n) or '__pycache__' in n for n in files)
    dependencies = {'round17-paid-comparison/' + n: v for n, v in frozen.items()}
    prior = json.loads((R17 / 'adapter-r1-3/READY.json').read_bytes())
    dependencies.update(prior['dependencies'])
    for n in ('amendments/A4-key-limit-label/AMENDMENT.md', 'run/KEY-ATTESTATION.json'):
        dependencies['round17-paid-comparison/' + n] = pin(R17 / n)
    if folder != 'recon-a4':
        for n, v in payload(R17 / 'recon-a4').items():
            dependencies['round17-paid-comparison/recon-a4/' + n] = v
        dependencies['round17-paid-comparison/recon-a4/READY.json'] = pin(R17 / 'recon-a4/READY.json')
    if folder == 'release-prep-a4':
        for n, v in payload(HERE).items():
            dependencies['round17-paid-comparison/adapter-r1-4/' + n] = v
        dependencies['round17-paid-comparison/adapter-r1-4/READY.json'] = pin(HERE / 'READY.json')
    expected = {'recon-a4': [3], 'adapter-r1-4': [102, 26, 23, 9, 20, 10, 10], 'release-prep-a4': [13]}[folder]
    interpreters = {}
    paths = {'python312': '/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12',
             'system': '/usr/local/bin/python3'}
    for label, path in paths.items():
        log = '_out/' + label + '-tests.txt'
        output = (root / log).read_text()
        counts = [int(n) for n in re.findall(r'^Ran (\d+) tests', output, re.M)]
        assert counts == expected, (folder, label, counts, expected)
        assert len(re.findall(r'^OK$', output, re.M)) == len(expected)
        assert not re.search(r'^FAILED|^ERROR:|^FAIL:', output, re.M)
        interpreters[label] = dict(executable=path, flags=['-I', '-S', '-B'], counts=counts,
                                   run=sum(counts), passed=sum(counts), failed=0,
                                   output=log, output_pin=pin(root / log))
    ready = dict(schema_version='r17.a4-ready.v1', revision='r1.4' if folder == 'adapter-r1-4' else 'A4',
                 status='READY_OFFLINE_IMPLEMENTATION', files=files,
                 sha256={n: v['sha256'] for n, v in files.items()}, dependencies=dependencies,
                 excluded_paths=['_out/**'], tests=interpreters,
                 amendment='A4-key-limit-label', key_label='DocketClock', key_max_nanousd=50_000_000_000,
                 FLOOR=270_000_000, OPERATING=1_800_000_000, CAP=2_000_000_000,
                 ledger_fixture_changes={'L18-key-limit-bounds': '$1.74 / six calls: False -> True; other 24 unchanged'},
                 release_policy='UNSET (offline candidate; live evidence remains primary-owned)',
                 network_calls=0, provider_calls=0, credentials_accessed=False,
                 source_bodies_read=False, reference_contents_read=False, frozen_inputs_unchanged=True,
                 runner_executor_release_commands_run=False, committed=False,
                 paid_release_authorized=False, action_ready=False, production_eligible=False,
                 self_pin='READY.json excludes itself; pin its exact hash externally before release.',
                 final_verification='adapter-r1-4/verify_ready.py verifies all three READY inventories, dependencies and frozen inputs after full suites')
    for n, v in dependencies.items():
        assert not forbidden(n), n
        assert pin(BENCH / n) == v, n
    (root / 'READY.json').write_text(json.dumps(ready, sort_keys=True, indent=2) + '\n')
    print(folder, 'READY:', sum(expected), 'tests per interpreter; sha256=' + pin(root / 'READY.json')['sha256'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', choices=FOLDERS)
    write(p.parse_args().folder)
