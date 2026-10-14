"""Re-run the full offline suite and assert every READY pin stays unchanged."""
import hashlib
import json
from pathlib import Path
import subprocess
import os
import sys
import unittest

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent.parent

def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

class ReadyTests(unittest.TestCase):
    def test_full_suite_preserves_every_ready_pin(self):
        ready = json.loads((HERE / 'READY.json').read_bytes())
        self.assertEqual(ready['revision'], 'r1.3')
        self.assertFalse(any(n.startswith('_out/') for n in ready['files']))
        self.assertEqual(ready['sha256'], {n: v['sha256'] for n, v in ready['files'].items()})
        def verify():
            for name, expected in ready['files'].items():
                self.assertEqual(pin(HERE / name), expected, name)
            for name, expected in ready['dependencies'].items():
                self.assertNotIn('reference/', name)
                self.assertFalse(name.endswith(('/parsed-body.txt', '/original.htm')))
                self.assertEqual(pin(BENCH / name), expected, name)
            actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*')
                      if p.is_file() and '_out' not in p.relative_to(HERE).parts and p.name != 'READY.json'}
            self.assertEqual(actual, set(ready['files']))
        verify()
        ready_pin = pin(HERE / 'READY.json')
        result = subprocess.run(['sh', str(HERE / 'run_tests.sh')], cwd=HERE, env={'R17_TEST_PYTHON': sys.executable, 'PATH': '/usr/bin:/bin'},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        (HERE / '_out/test-output.txt').write_bytes(result.stdout)
        verify()
        self.assertEqual(pin(HERE / 'READY.json'), ready_pin)
        self.assertEqual(result.returncode, 0, result.stdout.decode('utf-8'))
        print('Full suite passed; every payload/dependency hash and READY.json unchanged.')

if __name__ == '__main__':
    unittest.main(verbosity=2)
