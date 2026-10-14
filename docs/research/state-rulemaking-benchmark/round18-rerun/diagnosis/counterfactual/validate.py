"""Offline proof; run with python3 -B. All writes are confined to diagnosis/."""
import sys
sys.dont_write_bytecode = True
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
DIAG = HERE.parent
R18 = DIAG.parent
BENCH = R18.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def read(path):
    return json.loads(path.read_text())

def write(path, obj):
    assert path.resolve().is_relative_to(DIAG)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

wire = load('diagnosis_wire', R18 / 'wire/wire.py')
score = load('diagnosis_score', BENCH / 'round17-paid-comparison/design-r3-1-paccept/fixtures/r17score.py')
packet = read(R18 / 'adjudication/S1-OPQ/PACKET.json')
source = packet['source']
original = read(R18 / 'adjudication/S1-OPQ/output.expanded.json')
plan = wire.build(source, 'opaque')
run = next((R18 / 'run-live/stage-run').glob('r18*/request.json')).parent
request = read(run / 'request.json')
assert request['messages'] == plan['body']['messages']
assert request['response_format'] == plan['body']['response_format']
assert plan['request_sha256'] == read(run / 'plan.json')['request_sha256']
(DIAG / 'exact-system-prompt.txt').write_text(request['messages'][0]['content'])
value = wire.from_compact(wire.r15.contract(original, source, plan['table']))
wire.validate_response(json.dumps(value), 'stop', source, plan['table'], 'opaque', plan=plan)
before = copy.deepcopy(value)
# Only the two linked leaves change; assertions, evidence, roles and uncertainty stay fixed.
for node in value['g']:
    if node['i'] == 'c9':
        node['x'] = [dict(a='s39', h='This rule', ho=1, z='s39', t='is exempt from', to=1)]
        node['g'] = 'Exempted rule and exemption wording'
    elif node['i'] == 'c10':
        node['x'] = [dict(a='s41', h='This rule proposal', ho=1, z='s41', t='is exempt from', to=1),
                     dict(a='s47', h='rule proposal:', ho=1, z='s49', t='Is fully exempt', to=1)]
        node['g'] = 'Exempted proposal or portions, and full exemption scope'
assert before['u'] == value['u'] and before['l'] == value['l']
write(HERE / 'output.wire.json', value)
expanded = wire.validate_response((HERE / 'output.wire.json').read_text(), 'stop', source, plan['table'], 'opaque', plan=plan)
write(HERE / 'output.expanded.json', expanded)
results = {}
for who in ['A1', 'A2']:
    mappings = read(R18 / f'adjudication/S1-OPQ/S1-OPQ.{who}.json')['mappings']
    base = score.score(packet['reference'], source, original, mappings, 'OPQ')
    changed = score.score(packet['reference'], source, expanded, mappings, 'OPQ')
    assert all(base['relations'][r]['verdict'] == 'absent' for r in ['R2','R3','R4'])
    assert all(changed['relations'][r]['verdict'] == 'correct' for r in ['R2','R3','R4'])
    results[who] = changed
write(HERE / 'scores.json', results)
summary = dict(validates=True, validator='unchanged r16.w2.2 validate_response and pinned r15.1 validate/expand/contract',
               baseline_validates=True, exact_request_messages_and_schema_match=True,
               changed_nodes=['c9','c10'], units_and_links_unchanged=True,
               scores={a:{r:s['relations'][r]['verdict'] for r in ['R2','R3','R4']} for a,s in results.items()},
               qualification='Offline mechanical scoring with original mappings; no new adjudication or provider call.')
write(HERE / 'validator-output.json', summary)
print(json.dumps(summary, indent=2))
