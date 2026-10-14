import hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent
BENCH = R.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def load(name, p):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
screen = load('screen', R / 'screen.py'); wire = load('wire', BENCH / 'round16-wire-compat/protocol-w2-1/wire.py')
ids = ['26-19-039','26-19-041','26-19-106','26-19-116','26-19-123','26-19-135']
orig_extract = (BENCH / 'round14-semantic-contract/source/extract_source.py').read_bytes()
out = []
for i in ids:
    d = R / i
    rec = {'id': i, 'official_url': f'https://lawfilesext.leg.wa.gov/law/wsr/2026/19/{i}.htm', 'attempts': []}
    for ln in (d / 'attempts.log').read_text().splitlines():
        n, ts, rc, st, eu, ct, sz = ln.split('|')
        b = (d / f'attempt-{n}.body').read_bytes(); h = (d / f'headers-{n}.txt').read_bytes()
        rec['attempts'].append(dict(attempt=int(n), started_utc=ts, curl_exit=int(rc), http_status=st, effective_url=eu, content_type=ct,
            body_file=f'attempt-{n}.body', body_bytes=len(b), body_sha256=sha(b), headers_file=f'headers-{n}.txt', headers_sha256=sha(h)))
    ok = rec['attempts'][-1]['curl_exit'] == 0 and rec['attempts'][-1]['http_status'] == '200'
    rec['retrieval'] = 'ok' if ok else 'fail'
    ex = (d / 'extract_source.py').read_bytes()
    rec['extract_script_byte_identical_to_round14'] = ex == orig_extract
    if not ok:
        rec['pass'] = False; out.append(rec); continue
    body = (d / f'attempt-{rec["attempts"][-1]["attempt"]}.body').read_bytes()
    (d / 'original.htm').write_bytes(body)
    r = subprocess.run([sys.executable, '-I', '-S', '-B', str(d / 'extract_source.py')], capture_output=True, text=True, check=True)
    text = (d / 'parsed-body.txt').read_text(encoding='utf-8')
    rec['original_sha256'] = sha(body); rec['original_bytes'] = len(body)
    rec['text_sha256'] = sha(text.encode('utf-8')); rec['text_chars'] = len(text)
    rec['len_pass'] = len(text) <= 6500
    s = screen.screen(text); rec['keyword'] = s
    for p in ('full', 'opaque'):
        try:
            m = wire.measure(text, p); rec[f'measure_{p}'] = m
        except Exception as e:
            rec[f'measure_{p}'] = {'error': repr(e)}
        try:
            wire.build(text, p); rec[f'build_{p}'] = 'ok'
        except Exception as e:
            rec[f'build_{p}'] = 'raise:' + repr(e)
    gb = [rec[f'measure_{p}'].get('guarded_bytes') for p in ('full', 'opaque')]
    rec['guarded_bytes'] = dict(full=gb[0], opaque=gb[1])
    rec['guard_pass'] = all(g is not None and g <= 32000 for g in gb)
    rec['build_pass'] = rec['build_full'] == 'ok' and rec['build_opaque'] == 'ok'
    rec['pass'] = rec['len_pass'] and s['pass'] and rec['guard_pass'] and rec['build_pass']
    out.append(rec)
sel = [r['id'] for r in out if r['pass']][:3]
(R / 'SCREEN.json').write_text(json.dumps(dict(schema_version='r17.screen.r2.v1', screen_script='screen.py', screen_script_sha256=sha((R/'screen.py').read_bytes()),
    wire_path='round16-wire-compat/protocol-w2-1/wire.py', wire_sha256=sha((BENCH/'round16-wire-compat/protocol-w2-1/wire.py').read_bytes()),
    guard_limit_applied=32000, candidates=out, selected=sel), indent=2) + '\n')
for r in out:
    k = r.get('keyword', {})
    print(r['id'], r['retrieval'], r.get('text_chars'), r.get('len_pass'), k.get('pass'), k.get('exception_hit_total'), k.get('total_hits'), r.get('guarded_bytes'), r.get('build_full'), r.get('build_opaque'), r['pass'])
print('selected', sel)
