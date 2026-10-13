"""Offline protocol probes only. No transport, environment/credential access or writes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent.parent

def enc(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def sha(value):
    return hashlib.sha256(value).hexdigest()

def read(name):
    return json.loads((HERE / name).read_text())

def starts(source, quote):
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError('empty quote')
    return [i for i in range(len(source)) if source.startswith(quote, i)]

def encode_selector(source, selector):
    if set(selector) != {'quote', 'occurrence'}:
        raise ValueError('selector keys')
    positions = starts(source, selector['quote'])
    occurrence = selector['occurrence']
    if type(occurrence) is not int or not 1 <= occurrence <= len(positions):
        raise ValueError('occurrence')
    start = positions[occurrence - 1]
    return [start, start + len(selector['quote']), occurrence]

def decode_selector(source, row):
    if not isinstance(row, list) or len(row) != 3 or any(type(v) is not int for v in row):
        raise ValueError('row types')
    start, end, occurrence = row
    if not 0 <= start < end <= len(source):
        raise ValueError('span')
    selector = {'quote': source[start:end], 'occurrence': occurrence}
    if encode_selector(source, selector) != row:
        raise ValueError('occurrence span mismatch')
    return selector

def run():
    contract = read('inventory-wire-contract.json')
    cols = contract['columns']
    assert len(cols) == 9 and contract['evidence_columns'] == ['start', 'end', 'occurrence']
    tested = 0
    for source, quote, occurrence in [('aaaa', 'aa', 1), ('aaaa', 'aa', 2), ('aaaa', 'aa', 3), ('😀e\u0301😀e\u0301', 'e\u0301', 2), ('x\r\nx\r\n', 'x\r\n', 2)]:
        selector = {'quote': quote, 'occurrence': occurrence}
        assert decode_selector(source, encode_selector(source, selector)) == selector
        tested += 1
    for row in ([True, 2, 1], [0, False, 1], [0, 2, True], [-1, 2, 1], [2, 1, 1], [0, 0, 1], [0, 5, 1], [0, 2, 0], [0, 2, 2], [0, 2, 4], [0, 2], [0, 2, 1, 7], [0.0, 2, 1]):
        try:
            decode_selector('aaaa', row)
        except ValueError:
            tested += 1
        else:
            raise AssertionError('bad row accepted')
    assembly = json.loads((BENCH / 'round8-stronger-cap-probe/execution/run/documents/doc-92211b8c7ba0/assembled.json').read_text())
    source, record = assembly['source']['source_text'], assembly['record']
    source_hash = sha(source.encode())
    operative = read('stage-b.operative-record.json')
    def identities(node, pointer=''):
        found = {}
        if isinstance(node, dict):
            if 'id' in node:
                found[node['id']] = pointer
            for key, value in node.items():
                child = identities(value, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
                assert not (found.keys() & child.keys())
                found.update(child)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                child = identities(value, pointer + '/' + str(i))
                assert not (found.keys() & child.keys())
                found.update(child)
        return found
    original_ids, projected_ids = identities(record), identities(operative)
    assert original_ids == projected_ids and len(original_ids) == 70
    rows = []
    for n, heavy in ((16, False), (32, False), (48, False), (50, False), (64, False), (32, True), (48, True), (64, True)):
        units = []
        for i in range(n):
            # Artificial relationships/dependencies and distinct source-local spans;
            # semantic assertions are deliberate placeholders, never live fixtures.
            quote_length = 160 if heavy else 80
            offset = (i * 37) % (len(source) - quote_length)
            quote = source[offset:offset + quote_length]
            occurrence = starts(source, quote).index(offset) + 1
            units.append({'id': f'u{i+1:03}', 'kind': 'relationship' if heavy and i > 1 else 'fact', 'assertion': 'x' * (140 if heavy else 100), 'modality': 'informational', 'applicability': 'unconditional', 'uncertainty': 'none', 'uncertainty_reason': '', 'required_unit_ids': [f'u{j+1:03}' for j in range(max(0, i-2), i)] if heavy else [], 'evidence': [{'quote': quote, 'occurrence': occurrence}]})
        inventory = {'schema_version': 'round10.source-inventory.v1', 'source_text_sha256': source_hash, 'units': units}
        wire = {'schema_version': contract['schema_version'], 'source_text_sha256': source_hash, 'columns': cols, 'evidence_columns': contract['evidence_columns'], 'units': [[u[c] if c != 'evidence' else [encode_selector(source, e) for e in u[c]] for c in cols] for u in units]}
        restored_units = [dict(zip(cols, row)) for row in wire['units']]
        for unit in restored_units:
            unit['evidence'] = [decode_selector(source, e) for e in unit['evidence']]
        restored = {'schema_version': 'round10.source-inventory.v1', 'source_text_sha256': source_hash, 'units': restored_units}
        assert enc(restored) == enc(inventory) and sha(enc(restored)) == sha(enc(inventory))
        schema = read('stage-b.schema.template.json')
        schema['properties']['inventory_sha256']['enum'] = [sha(enc(inventory))]
        keys = [u['id'] for u in units]
        schema['properties']['mappings'] = {'type': 'object', 'properties': {k: {'$ref': '#/$defs/m'} for k in keys}, 'required': keys, 'additionalProperties': False}
        user = {'source_text': source, 'source_text_sha256': source_hash, 'record_sha256': sha(enc(record)), 'operative_record': operative, 'operative_record_sha256': sha(enc(operative)), 'inventory_wire': wire, 'inventory_sha256': sha(enc(inventory))}
        request = {**read('request-settings.json'), 'messages': [{'role': 'system', 'content': (HERE / 'stage-b.system.txt').read_text()}, {'role': 'user', 'content': enc(user).decode()}], 'response_format': {'type': 'json_schema', 'json_schema': {'name': 'source_mapping', 'strict': True, 'schema': schema}}}
        size = len(enc(request))
        rows.append({'unit_count': n, 'scenario': '140-char assertion,160-char quote,relationship units with2 dependencies where available' if heavy else '100-char assertion,80-char quote,no dependencies', 'body_bytes': size, 'guarded_bytes': size + 1024, 'headroom_bytes': 40000 - size - 1024, 'fits': size + 1024 <= 40000, 'canonical_inventory_roundtrip': True})
    return {'id_container_bindings_verified': len(original_ids), 'selector_probes_passed': tested, 'inventory_roundtrips_passed': len(rows), 'stage_b_probes': rows, 'provider_calls': 0, 'runtime_tests_run': False}

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
