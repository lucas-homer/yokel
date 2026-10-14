"""Offline repro: the R18 wire differs from the frozen R16 w2.1 wire only in the system prompt
and version labels; schema, user message, settings and byte-guard are identical."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
R16 = BENCH / 'round16-wire-compat/protocol-w2-1/wire.py'
R18 = BENCH / 'round18-rerun/wire/wire.py'
SENTENCE = ('If a unit has several conditions of the same role (if, onlyif, unless or obj), emit a '
            'single link of that role to one L leaf whose fragments cover each condition in source '
            'order (up to 8). Never emit two links of the same role on one unit.\n')


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main():
    assert hashlib.sha256(R16.read_bytes()).hexdigest() == '662268ba0774d7ef5a121ec4af90003a3836c07e4ce5a5ae551a413fe8375ab1'
    assert hashlib.sha256(R18.read_bytes()).hexdigest() == '0f8e44476b509a28b68739f83c0e557198a9990079bf8c108ff00071ecd56bef'
    w16, w18 = load('wire_r16_w2_1', R16), load('wire_r18_w2_2', R18)
    assert (w16.R15_READY_SHA256, w16.COMMON_SHA256) == (w18.R15_READY_SHA256, w18.COMMON_SHA256)
    assert (w16.VERSION, w18.VERSION) == ('r16.w1', 'r16.w1')
    assert (w16.REVISION, w16.ENVELOPE_VERSION) == ('r16.w2.1', 'r16.e2')
    assert (w18.REVISION, w18.ENVELOPE_VERSION) == ('r16.w2.2', 'r16.e3')
    source = ('A permittee shall file the report within 30 days if the facility discharges, '
              'if the discharge exceeds the limit, unless the director waives the requirement.')
    for profile in ('opaque', 'full'):
        p16, p18 = w16.build(source, profile), w18.build(source, profile)
        b16, b18 = p16['body'], p18['body']
        assert set(b16) == set(b18)
        for key in b16:
            if key == 'messages':
                continue
            assert b16[key] == b18[key], key
        assert b16['messages'][1] == b18['messages'][1]          # user message (source + span table)
        assert b16['response_format'] == b18['response_format']  # schema bytes identical
        assert b18['messages'][0]['content'] == b16['messages'][0]['content'] + SENTENCE
        assert p16['table'] == p18['table']
        for key in ('profile', 'guard_limit', 'schema_bytes', 'spans', 'source_bytes'):
            assert p16[key] == p18[key], key
        prompt_delta = (len(w18.common.encode(b18['messages'][0]['content']))
                        - len(w16.common.encode(b16['messages'][0]['content'])))
        assert prompt_delta > 0 and p18['body_bytes'] - p16['body_bytes'] == prompt_delta
        print(profile, 'identical except system prompt; delta bytes =', p18['body_bytes'] - p16['body_bytes'],
              'under_guard =', p18['under_guard'])
    print('OK: prompt-only change; schema/validator/settings pins unchanged')


if __name__ == '__main__':
    main()
