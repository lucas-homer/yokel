"""Run design-r3.1's fixtures against the frozen design-r3 scorer and recon modules.
Every new r3.1 expectation should fail there (red); everything else should still hold.
Offline; reads only design-r3/fixtures/*.py and design-r3-1/fixtures. Writes nothing.
Run with python3 -I -S -B."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R31, R3 = HERE.parent / 'fixtures', HERE.parents[1] / 'design-r3' / 'fixtures'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = load('check_r31', R31 / 'check.py')
C.S, C.L = load('score_r3', R3 / 'r17score.py'), load('recon_r3', R3 / 'r17recon.py')
data = json.loads((R31 / 'cases.json').read_bytes())
counts, fails = C.run(data)
print(json.dumps(dict(failures_under_r3=len(fails)), sort_keys=True))
for f in fails:
    print('RED', f)
