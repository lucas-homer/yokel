"""Read-only targeted review reproduction; no fixture writes or provider calls."""
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'protocol'
sys.path.insert(0, str(root))
from compact import validate, span_table
from fictional_controls import SOURCE, envelope, unit, node, link, fixture

def outcome(name, value):
    try:
        validate(value, SOURCE, span_table(SOURCE))
        print(name, 'accepted')
    except Exception as exc:
        print(name, type(exc).__name__, str(exc))

chain = envelope(SOURCE, [unit()], [node(f'c{i}', 'NOT', [f'c{i+1}'], []) for i in range(1, 399)] + [node('c399')], [link(1, 'c1', 'obj')])
default = sys.getrecursionlimit()
outcome('chain399_default', chain)
try:
    sys.setrecursionlimit(600)
    outcome('chain399_limit600', chain)
finally:
    sys.setrecursionlimit(default)
v = fixture(); v['u'][3].update(q=0, r=''); outcome('masked_deadline', v)
v = fixture(); v['u'][5].update(q=0, r=''); outcome('intended_deadline', v)
v = fixture(); v['u'][0].update(p=0); outcome('masked_applicability', v)
outcome('intended_applicability', envelope(SOURCE, [unit(p=0)], [node('c1')], [link(1, 'c1', 'if')]))
