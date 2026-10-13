"""Read-only verification by default; --record writes only this owned folder."""
import hashlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(tests):
    paths = {tests.wire.COMMON_PATH,
             tests.BENCH / 'round14-semantic-contract/source/parsed-body.txt',
             tests.SIZING / 'authored-profiles.json',
             tests.SIZING / 'revised/authored-controls.json',
             ROOT.parent / 'inventory/INVENTORY.md',
             ROOT.parent / 'inventory/READY.json'}
    for directory in [tests.PROTO, ROOT.parent / 'design']:
        manifest = json.loads((directory / 'READY.json').read_bytes())
        paths.add(directory / 'READY.json')
        paths.update(directory / name for name in manifest['sha256'])
    return {str(p.relative_to(tests.BENCH)): digest(p) for p in sorted(paths)}


def main():
    if sys.argv[1:] not in ([], ['--record']):
        raise SystemExit('Usage: python3 -I -S -B verify.py [--record]')
    spec = importlib.util.spec_from_file_location('test_wire', ROOT / 'test_wire.py')
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    before = inputs(tests)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(tests))
    output = stream.getvalue()
    print(output, end='')
    if not result.wasSuccessful():
        raise SystemExit(1)
    report = tests.receipt()
    if inputs(tests) != before:
        raise SystemExit('Read-only input changed during verification')
    report.update(tests_run=result.testsRun, tests_passed=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors),
                  input_sha256=before, frozen_inputs_unchanged=True,
                  invocation='python3 -I -S -B protocol/verify.py')
    if sys.argv[1:] == ['--record']:
        (ROOT / 'test-output.txt').write_text(output, encoding='utf-8')
        (ROOT / 'receipt.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        pins = {str(p.relative_to(ROOT)): digest(p) for p in sorted(ROOT.rglob('*'))
                if p.is_file() and p.name != 'READY.json'}
        ready = dict(status='READY_OFFLINE_IMPLEMENTATION', version=tests.wire.VERSION,
                     tests_passed=result.testsRun, provider_calls=0,
                     credentials_accessed=False, dispatch_authorized=False,
                     schema_depth_root_zero=8, sha256=pins,
                     dependency_pins=dict(r15_READY=tests.wire.R15_READY_SHA256,
                                          r14_common=tests.wire.COMMON_SHA256),
                     sizing=report['sizing'])
        (ROOT / 'READY.json').write_text(json.dumps(ready, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    else:
        ready = json.loads((ROOT / 'READY.json').read_bytes())
        actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
                  if p.is_file() and p.name != 'READY.json'}
        if actual != set(ready['sha256']):
            raise SystemExit('Owned payload file set differs from READY')
        for name, expected in ready['sha256'].items():
            if digest(ROOT / name) != expected:
                raise SystemExit('Owned payload pin mismatch: ' + name)
        recorded = json.loads((ROOT / 'receipt.json').read_bytes())
        if recorded != report:
            raise SystemExit('Recorded receipt differs from verification')
    print(json.dumps({key: report[key] for key in ['tests_run', 'corpus', 'schema', 'sizing', 'frozen_inputs_unchanged']},
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
