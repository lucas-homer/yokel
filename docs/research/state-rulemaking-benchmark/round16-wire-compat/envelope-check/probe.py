"""Offline reconstruction and rows-only request-size probe for r16.w1."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
REPO = BENCH.parents[2]
WIRE_PATH = BENCH / 'round16-wire-compat/protocol/wire.py'
R15 = BENCH / 'round15-condition-preservation/protocol-revised'


def load_wire():
    spec = importlib.util.spec_from_file_location('envelope_probe_wire', WIRE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def first_byte_mismatch(left, right):
    upto = min(len(left), len(right))
    for offset in range(upto):
        if left[offset] != right[offset]:
            return offset
    return upto if len(left) != len(right) else None


def source_records():
    exposed = (BENCH / 'round14-semantic-contract/source/parsed-body.txt').read_bytes().decode('utf-8')
    authored_path = BENCH / 'round15-condition-preservation/sizing/authored-profiles.json'
    authored = json.loads(authored_path.read_text(encoding='utf-8'))
    by_id = {profile['id']: profile['source'] for profile in authored['profiles']}
    result = [
        ('prior_source_R14_parsed_body', exposed),
        ('disjoint600-u24', by_id['disjoint600-u24']),
    ]
    fixture_dir = R15 / 'fixtures'
    for path in sorted(fixture_dir.glob('*source.txt')):
        result.append(('r15_fixture:' + path.name, path.read_bytes().decode('utf-8')))
    return result


def check_source(wire, label, source):
    table = wire.r15.span_table(source)
    joined = ''.join(row[3] for row in table['rows'])
    expected_bytes = source.encode('utf-8')
    actual_bytes = joined.encode('utf-8')
    mismatch = first_byte_mismatch(expected_bytes, actual_bytes)
    try:
        wire.r15.reconstruct(source, table)
        reconstruct = 'passed'
    except Exception as exc:  # record the actual offline verifier outcome
        reconstruct = 'failed:' + str(exc)
    row_offsets_contiguous = all(
        row[1] == (table['rows'][index - 1][2] if index else 0)
        for index, row in enumerate(table['rows'])
    ) and (not table['rows'] or table['rows'][-1][2] == len(source))
    return dict(
        label=label,
        source_utf8_bytes=len(expected_bytes),
        source_sha256=hashlib.sha256(expected_bytes).hexdigest(),
        span_rows=len(table['rows']),
        row_offsets_contiguous_and_cover_source=row_offsets_contiguous,
        concatenation_exact=(mismatch is None),
        first_differing_utf8_byte_offset=mismatch,
        reconstruct_verifier=reconstruct,
    )


def request_sizes(wire, label, source):
    plan = wire.build(source, 'full')
    original_body = plan['body']
    rows_only_body = copy.deepcopy(original_body)
    inner = wire.r15.strict_load(rows_only_body['messages'][1]['content'])
    del inner['source_text']
    rows_only_body['messages'][1]['content'] = wire.r15.canonical(inner).decode('utf-8')
    full_bytes = len(wire.common.encode(original_body))
    rows_only_bytes = len(wire.common.encode(rows_only_body))
    return dict(
        label=label,
        full_body_bytes=full_bytes,
        full_guarded_bytes=full_bytes + 1024,
        rows_only_body_bytes=rows_only_bytes,
        rows_only_guarded_bytes=rows_only_bytes + 1024,
        bytes_saved=full_bytes - rows_only_bytes,
        under_40000_guard_without_source_text=(rows_only_bytes + 1024 <= 40000),
        only_modified_in_memory=True,
    )


def main():
    wire = load_wire()
    records = source_records()
    output = dict(
        mode='offline_only',
        provider_calls=0,
        credentials_read=False,
        reconstruction=[check_source(wire, label, source) for label, source in records],
        sizing=[request_sizes(wire, label, source) for label, source in records[:2]],
    )
    target = HERE / 'probe-output.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(target)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
