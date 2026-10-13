"""Bounded static protocol/fixture checks only. No request builder or provider runtime."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text())

rows = []
def check(name, condition):
    rows.append({'name': name, 'pass': bool(condition)})

boundaries = load('boundaries.json')
fixtures = load('offline-fixtures.json')
for case in fixtures['boundary_cases']:
    expected = boundaries['exact_user_fields'][case['stage']]
    actual = len(case['input_fields']) == len(set(case['input_fields'])) and set(case['input_fields']) == set(expected)
    check(case['id'], actual == case['expected_valid'])

for stage in ['a','b','c','d']:
    schema = load('stage-' + stage + '.schema.template.json')
    refs = set(schema['$defs'])
    def walk(node):
        if isinstance(node, dict):
            if node.get('type') == 'object':
                check(stage + '_closed_object', node.get('additionalProperties') is False and set(node.get('required', [])) == set(node.get('properties', {})))
            if '$ref' in node:
                check(stage + '_local_ref', len(node) == 1 and node['$ref'].startswith('#/$defs/') and node['$ref'][8:] in refs)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(schema)
    check(stage + '_source_placeholder', schema['properties']['source_text_sha256']['enum'] == ['__SOURCE_SHA256__'])
    check(stage + '_prompt_present', (ROOT / ('stage-' + stage + '.system.txt')).stat().st_size > 0)

p = load('policy.json')
check('scope_basis_bijection', len(set(p['scope_basis_by_category'].values())) == 4)
check('uncertain_scope_basis', p['scope_basis_by_category']['unresolved_scope'] == 'uncertain_source_function')
check('no_human_scope_or_gold', p['human_scope_input'] is False and p['gold_input'] is False)
check('raw_losses_retained', p['known_raw_defects_preserved'] is True)
settings = load('request-settings.json')
check('same_model', settings['model'] == 'openai/gpt-6.1-sol' and settings['reasoning']['effort'] == 'low')
check('fixed_max_tokens', settings['max_tokens'] == 8192)
check('routing', settings['provider']['only'] == ['openai'] and settings['provider']['allow_fallbacks'] is False)
plan = load('evaluation-plan.json')
budget = plan['budget']
check('four_calls', plan['maximum_calls'] == 4 and plan['planned_order'] == ['D','A','C','B'])
check('reserve_arithmetic', budget['four_call_reserve_nanodollars'] == 4 * budget['per_attempt_reserve_nanodollars'])
check('ceiling', budget['maximum_prospective_debit_nanodollars'] == budget['prior_debit_nanodollars'] + budget['four_call_reserve_nanodollars'] < budget['ceiling_nanodollars'])
check('no_retry', plan['retries'] == 0 and plan['repairs'] == 0 and plan['clipping'] is False)
wire = load('inventory-wire-contract.json')
check('nine_columns', wire['columns'] == ['id','kind','assertion','modality','applicability','uncertainty','uncertainty_reason','required_unit_ids','evidence'])
check('C_B_empty_template_schedule', all(load('stage-' + s + '.schema.template.json')['properties'][key]['properties'] == {} for s,key in [('c','scopes'),('b','mappings')]))
result = {'interpretation':'Static authoring and field-set isolation checks only; semantic fixtures and runtime checks remain unexecuted', 'passed':sum(r['pass'] for r in rows), 'total':len(rows), 'rows':rows}
print(json.dumps(result, indent=2))
if not all(r['pass'] for r in rows):
    raise SystemExit(1)
