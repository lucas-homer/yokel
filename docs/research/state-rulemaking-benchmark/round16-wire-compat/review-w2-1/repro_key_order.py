"""Round-3 review repro (N-W2-2): from_compact / to_compact key order under w1, w2, w2.1 for reordered input."""
import copy
import importlib.util
import json
from pathlib import Path

ROUND = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mods = {v: load('ko_' + v, ROUND / d / 'wire.py') for v, d in (('w1', 'protocol'), ('w2', 'protocol-w2'), ('w2.1', 'protocol-w2-1'))}
r15 = mods['w2.1'].r15
positive = json.loads((mods['w2.1'].R15_ROOT / 'fixtures/positive.json').read_bytes())
reordered = {k: positive[k] for k in reversed(list(positive))}
for unit in reordered['u']:
    unit['y'] = unit.pop('y')  # move y to the end
out = {}
for v, m in mods.items():
    wire = m.from_compact(copy.deepcopy(reordered))
    back = m.to_compact(copy.deepcopy(wire))
    out[v] = (list(wire), list(wire['u'][0]), list(back), list(back['u'][0]), r15.canonical(wire))
    print(f'{v:5} from_compact top keys {out[v][0]}  unit keys {out[v][1]}')
    print(f'{"":5} to_compact   top keys {out[v][2]}  unit keys {out[v][3]}')
print('w2.1 non-canonical serialization == w1:', json.dumps(mods['w2.1'].from_compact(copy.deepcopy(reordered))) == json.dumps(mods['w1'].from_compact(copy.deepcopy(reordered))))
print('w2   non-canonical serialization == w1:', json.dumps(mods['w2'].from_compact(copy.deepcopy(reordered))) == json.dumps(mods['w1'].from_compact(copy.deepcopy(reordered))))
print('canonical bytes identical across all three:', len({o[4] for o in out.values()}) == 1)
