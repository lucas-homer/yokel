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
             tests.SIZING / 'revised/authored-controls.json'}
    directories = [tests.PROTO] + [tests.BENCH / 'round16-wire-compat' / name for name in
        ('design', 'inventory', 'envelope-check', 'testing', 'review', 'review-w2', 'protocol')]
    for directory in directories:
        paths.update(p for p in directory.rglob('*') if p.is_file())
    return {str(p.relative_to(tests.BENCH)): digest(p) for p in sorted(paths)}


def check_frozen(tests):
    expected = json.loads((ROOT / 'frozen-inputs.json').read_bytes())
    actual = inputs(tests)
    if actual != expected:
        raise SystemExit('Frozen benchmark payloads changed')
    return dict(payload_files=len(expected), unchanged=True,
                manifest_sha256=digest(ROOT / 'frozen-inputs.json'))


def main():
    # Complete R18 tests are orchestrated by ../offline_tests.py; this is read-only.
    path = ROOT.parent / 'pin_ready.py'
    spec = importlib.util.spec_from_file_location('r18_verify_pins', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify()

if __name__ == '__main__':
    main()
