"""Verify every A4 READY pin after full offline suites on the invoking interpreter."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
R17 = HERE.parent
BENCH = R17.parent
spec = importlib.util.spec_from_file_location('a4_pinning', HERE / 'pin_ready.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def verify():
    p.verify_frozen()
    hashes = {}
    for folder in p.FOLDERS:
        root = R17 / folder
        ready = json.loads((root / 'READY.json').read_bytes())
        assert p.payload(root) == ready['files'], folder + ': payload inventory drift'
        assert ready['sha256'] == {n: v['sha256'] for n, v in ready['files'].items()}
        for name, expected in ready['dependencies'].items():
            assert not p.forbidden(name), name
            assert p.pin(BENCH / name) == expected, name
        for item in ready['tests'].values():
            assert p.pin(root / item['output']) == item['output_pin'], item['output']
        hashes[folder] = p.pin(root / 'READY.json')['sha256']
    return hashes


def main():
    before = verify()
    commands = [
        ('recon-a4', [sys.executable, '-I', '-S', '-B', str(R17 / 'recon-a4/test_recon.py')]),
        ('adapter-r1-4', ['sh', str(HERE / 'run_tests.sh')]),
        ('release-prep-a4', [sys.executable, '-I', '-S', '-B', str(R17 / 'release-prep-a4/test_release_prep.py')])]
    for folder, command in commands:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env={'PATH': '/usr/bin:/bin', 'R17_TEST_PYTHON': sys.executable}, check=False)
        (R17 / folder / '_out' / ('verify-' + Path(sys.executable).name + '-tests.txt')).write_bytes(result.stdout)
        assert result.returncode == 0, result.stdout.decode()
    assert verify() == before, 'READY hash drift after suites'
    print(json.dumps(dict(interpreter=sys.executable, flags=['-I', '-S', '-B'],
                          suites={'recon':3, 'adapter':200, 'release_prep':13},
                          full_suites_passed=True, frozen_inputs_unchanged=True,
                          all_payload_dependency_and_READY_pins_unchanged=True, ready_sha256=before), sort_keys=True))


if __name__ == '__main__':
    main()
