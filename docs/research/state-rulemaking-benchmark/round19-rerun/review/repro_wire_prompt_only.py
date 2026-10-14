"""Offline repro (R19 review Q1): the R19 wire r16.w2.3 differs from frozen R18 r16.w2.2 only in
version labels and the opaque system prompt. For the three real sources-r2 (039/041/106), both
profiles: every body key, user message, response_format, span table and plan metadata are equal,
the FULL prompt is byte-identical, and the OPAQUE prompt equals R18's + the A7 sentence + '\n',
where the sentence is taken from the normative amendments/A7.md, not from wire.py. Also checks the
40000 byte guard and that the wire.py source transformation is exactly the three allowed hunks."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
R18 = BENCH / 'round18-rerun/wire/wire.py'
R19 = BENCH / 'round19-rerun/wire/wire.py'
SOURCES = BENCH / 'round17-paid-comparison/sources-r2'
IDS = ('26-19-039', '26-19-041', '26-19-106')


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def a7_sentence():
    lines = (BENCH / 'round19-rerun/amendments/A7.md').read_text(encoding='utf-8').splitlines()
    quoted = [l[3:-1] for l in lines if l.startswith('> "') and l.endswith('"')]
    assert len(quoted) == 1
    return quoted[0]


def main():
    assert hashlib.sha256(R18.read_bytes()).hexdigest() == '0f8e44476b509a28b68739f83c0e557198a9990079bf8c108ff00071ecd56bef'
    assert hashlib.sha256(R19.read_bytes()).hexdigest() == 'f17af0190dbc35eeeeeb1df00afe594f555f0a4df80aa9cb842083d9713c0ffb'
    w18, w19 = load('wire_r18_w2_2', R18), load('wire_r19_w2_3', R19)
    assert (w18.R15_READY_SHA256, w18.COMMON_SHA256) == (w19.R15_READY_SHA256, w19.COMMON_SHA256)
    assert (w18.VERSION, w19.VERSION) == ('r16.w1', 'r16.w1')
    assert (w18.REVISION, w18.ENVELOPE_VERSION) == ('r16.w2.2', 'r16.e3')
    assert (w19.REVISION, w19.ENVELOPE_VERSION) == ('r16.w2.3', 'r16.e4')
    # Exact allowed source transformation (independent of the implementer's test).
    sentence = a7_sentence()
    src18 = R18.read_text(encoding='utf-8')
    expected = src18.replace('r16.w2.2', 'r16.w2.3').replace('r16.e3', 'r16.e4')
    assert expected.count('    return prompt\n') == 1
    expected = expected.replace('    return prompt\n',
        "    if profile == 'opaque':\n        prompt += " + repr(sentence + '\n') + '\n    return prompt\n')
    assert R19.read_text(encoding='utf-8') == expected, 'wire.py differs from the allowed transformation'
    # Prompt-level equality.
    assert w19._system_prompt('full').encode() == w18._system_prompt('full').encode()
    assert w19._system_prompt('opaque').encode() == w18._system_prompt('opaque').encode() + (sentence + '\n').encode()
    assert w18._system_prompt('opaque').endswith('Never emit two links of the same role on one unit.\n')  # after A5
    delta_utf8 = len((sentence + '\n').encode())
    # Real sources, both profiles.
    ready = json.loads((SOURCES / 'READY.json').read_bytes())
    assert ready['selected'] == list(IDS)
    sizes = []
    for sid in IDS:
        raw = (SOURCES / sid / 'parsed-body.txt').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ready['files'][sid + '/parsed-body.txt']['sha256']
        source = raw.decode('utf-8')
        for profile in ('opaque', 'full'):
            p18, p19 = w18.build(source, profile), w19.build(source, profile)
            b18, b19 = p18['body'], p19['body']
            assert list(b18) == list(b19), 'body key set/order'
            for key in b18:
                if key != 'messages':
                    assert b18[key] == b19[key], key
            assert len(b18['messages']) == len(b19['messages']) == 2
            assert b18['messages'][1] == b19['messages'][1], 'user message'
            assert b18['messages'][0]['role'] == b19['messages'][0]['role'] == 'system'
            if profile == 'full':
                assert b19['messages'][0]['content'] == b18['messages'][0]['content']
                assert w19.common.encode(b19) == w18.common.encode(b18), 'full body bytes'
            else:
                assert b19['messages'][0]['content'] == b18['messages'][0]['content'] + sentence + '\n'
            assert p18['table'] == p19['table']
            for key in ('profile', 'guard_limit', 'schema_bytes', 'spans', 'source_bytes'):
                assert p18[key] == p19[key], key
            assert p19['guard_limit'] == 40000 and p19['under_guard'] and p19['guarded_bytes'] <= 40000
            assert p19['guarded_bytes'] == p19['body_bytes'] + 1024
            body_delta = p19['body_bytes'] - p18['body_bytes']
            assert body_delta == (len(w19.common.encode(sentence + '\n')) - 2 if profile == 'opaque' else 0)
            sizes.append(dict(source=sid, profile=profile, r18_body=p18['body_bytes'], r19_body=p19['body_bytes'],
                              guarded=p19['guarded_bytes'], residual=40000 - p19['guarded_bytes'], delta=body_delta))
    for s in sizes:
        print(json.dumps(s))
    print('A7 sentence utf8 bytes (with newline):', delta_utf8, 'encoded delta:', len(w19.common.encode(sentence + '\n')) - 2)
    print('OK: prompt-only change; FULL byte-identical; OPAQUE = R18 + A7; all six under the 40000 guard')


if __name__ == '__main__':
    main()
