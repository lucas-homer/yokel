"""Q6/Q7: draft proposals vs INTERFACE.md + Manifest.h, canonical bytes, and the multi-cell --gate trap.

check-job is NOT run. An independent canonicalizer modelled on Manifest.h's CanonicalJSON (strcmp
key order, compact, slashes unescaped) is compared byte for byte with the three drafts.
"""
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _load as L
mp = L.load('r4_make_proposals', L.R17 / 'release-prep-a4/make_proposals.py')
st = mp.st
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('ok   ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


def manifest_h_canonical(v):
    """Independent port of Manifest.h CanonicalJSON for the value types a proposal uses."""
    if isinstance(v, dict):
        keys = sorted(v, key=lambda k: k.encode('utf-8'))  # strcmp on UTF-8 bytes
        return b'{' + b','.join(manifest_h_canonical(k) + b':' + manifest_h_canonical(v[k]) for k in keys) + b'}'
    if isinstance(v, list):
        return b'[' + b','.join(manifest_h_canonical(x) for x in v) + b']'
    if isinstance(v, bool):
        return b'true' if v else b'false'
    if isinstance(v, int):
        assert -4503599627370495 <= v <= 4503599627370495
        return str(v).encode()
    if isinstance(v, str):
        # NSJSONSerialization: escapes " \\ and control chars; WithoutEscapingSlashes; non-ASCII raw UTF-8
        out = ['"']
        for ch in v:
            if ch == '"': out.append('\\"')
            elif ch == '\\': out.append('\\\\')
            elif ch == '\n': out.append('\\n')
            elif ch == '\r': out.append('\\r')
            elif ch == '\t': out.append('\\t')
            elif ord(ch) < 0x20: out.append('\\u%04x' % ord(ch))
            else: out.append(ch)
        out.append('"')
        return ''.join(out).encode('utf-8')
    if v is None:
        return b'null'
    raise TypeError(type(v))


core = json.loads(st.read_regular(st.CORE))
drafts = sorted((L.R17 / 'release-prep-a4/proposals-draft').glob('*.json'))
check('three drafts', len(drafts) == 3)
ids = []
for path in drafts:
    raw = path.read_bytes()
    m = json.loads(raw)
    ids.append(m['job_id'])
    check(path.name + ': bytes == Manifest.h-style canonical JSON (strcmp order, compact)', manifest_h_canonical(m) == raw)
    check(path.name + ': no duplicate keys, parses strictly', json.loads(raw, object_pairs_hook=lambda p: (_ for _ in ()).throw(ValueError('dup')) if len({k for k, _ in p}) != len(p) else dict(p)) == m)
    check(path.name + ': exact top-level keys', set(m) == {'schema_version', 'job_id', 'scope_id', 'project', 'expires_unix', 'provider_variables', 'job', 'budget', 'review'})
    check(path.name + ': job_id ^[a-z][a-z0-9-]{0,63}$ and equals file stem', re.fullmatch(r'[a-z][a-z0-9-]{0,63}', m['job_id']) is not None and path.stem == m['job_id'])
    check(path.name + ': OpenRouter-only provider subset', m['provider_variables'] == ['OPENROUTER_API_KEY'])
    argv = m['job']['argv']
    check(path.name + ': argv = [python_path,-I,-S,-B,<adapter_root>/.../adapter.py,--live-initial]',
          len(argv) == 6 and argv[0] == core['python_path'] and argv[1:4] == ['-I', '-S', '-B'] and argv[5] == '--live-initial'
          and argv[4].endswith('/adapter.py') and any(argv[4].startswith(r + '/') for r in core['adapter_roots']))
    files = m['job']['files']
    check(path.name + ': files pin python and the shim; every path within dependency roots; 64-hex lowercase',
          argv[0] in files and argv[4] in files and all(any(p.startswith(r + '/') for r in core['dependency_roots']) for p in files)
          and all(re.fullmatch(r'[a-f0-9]{64}', h) for h in files.values()) and 0 < len(files) <= 10000)
    check(path.name + ': timeout 1800 within core max', m['job']['timeout_seconds'] == 1800 <= core['timeout_max_seconds'])
    b = m['budget']
    check(path.name + ': budget ints, prior+reservation<=ceiling, reservation $0.27, ceiling $2.00',
          all(type(x) is int for x in b.values()) and b['prior_nanousd'] + b['reservation_nanousd'] <= b['ceiling_nanousd']
          and b['reservation_nanousd'] == 270_000_000 and b['ceiling_nanousd'] == 2_000_000_000)
    check(path.name + ': review path is a file pin with the same hash', files.get(m['review']['path']) == m['review']['sha256'])
    check(path.name + ': review pin is adapter-r1-4/SPEC.md (the implementer\'s spec, NOT an independent review) - NOTE',
          m['review']['path'].endswith('/adapter-r1-4/SPEC.md'))
    now = int(time.time())
    print('   expiry %d = now%+d s (drafts were written with +86400; must be (now, now+7d] at check-job AND at every run stage)' % (m['expires_unix'], m['expires_unix'] - now))
    check(path.name + ': arguments.json for this job is pinned', any(p.endswith('/native-jobs/' + m['job_id'] + '/arguments.json') for p in files))
    check(path.name + ': offline validate() accepts (check_files=False; prospective paths do not exist yet)',
          mp.validate(m, core, now=m['expires_unix'] - 3600, check_files=False))
    try:
        mp.validate(m, core, now=now, check_files=True)
        check(path.name + ': check_files=True accepted?!', False)
    except (ValueError, OSError):
        check(path.name + ': with check_files=True the draft fails (stage absent) - as documented, drafts are not signable', True)
check('job ids unique and per cell', len(set(ids)) == 3 and sorted(i.split('-')[1] for i in ids) == ['s1', 's2', 's3'])
check('S1 has no --staged-gate; S2/S3 point at run/gates/<cell>.json', all(
    ('--staged-gate' in json.loads((L.R17 / 'release-prep-a4/proposals-draft/native-jobs' / i / 'arguments.json').read_text())['args']) == (not i.startswith('r17-s1'))
    for i in ids))

# Manifest.h also requires every files[] path and argv[4] to be a *canonical existing* path (realpath == path);
# a draft therefore cannot pass check-job until staged. And prior must be the verified ledger aggregate.
print('   NOTE: drafts use scope_id "r17-paid-comparison" and priors 0/0.27/0.54 as placeholders (README says so).')

# ---- the multi-cell --gate trap (Q7): one --gate applied to S2 AND S3 when --cell is omitted ----
with L.tempdir('gate-trap') as tmp:
    root = Path(tmp)
    source = root / 'source'
    m = {'schema_version': 'r17.stage.v1', 'files': {}}
    def put(name, raw):
        p = source / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        m['files'][name] = st.digest(raw)
    put(mp.ADAPTER + '/native_entry.py', st.read_regular(st.BENCH / mp.ADAPTER / 'native_entry.py'))
    put(mp.ADAPTER + '/host_driver.py', b'# synthetic host\n')
    put(mp.ADAPTER + '/SPEC.md', b'synthetic review\n')
    put(mp.R17 + '/evidence.json', b'{"files":{}}')
    core2 = dict(core, adapter_roots=[str(root)], dependency_roots=[str(root), str(Path(core['python_path']).parent.parent)])
    stage = st.stage(source, root / 'allowed/.r17-stage', m, allowed_roots=[str(root)])
    evidence = {'path': mp.R17 + '/evidence.json', 'sha256': m['files'][mp.R17 + '/evidence.json']}
    roles = {'protocol', 'budget', 'reference_spec', 'adjudication_spec', 'scorer', 'recon', 'cases', 'cases_src', 'check',
             'A1_fixture_gate', 'A2_fixture_gate', 'sources_ready', 'reference_ready', 'scoring_manifest', 'policy_evidence',
             'key_attestation', 'machine_check', 'roles_auth', 'adapter', 'tests', 'adapter_ready', 'design_ready', 'design_primary', 'host_driver'}
    release = stage / mp.R17 / 'run/RELEASE.json'
    release.parent.mkdir()
    release.write_bytes(st.canonical({'schema_version': 'r17.release.v1', 'required_calls': mp.CELLS, 'typed_testable': False,
                                      'release_policy': 'P-ACCEPT', 'artifacts': {r: evidence for r in roles}}))
    gate = release.parent / 'S2-gate.json'
    gate.write_bytes(st.canonical({'files': {'RELEASE.json': st.digest(release.read_bytes())}}))
    paths = mp.generate(stage, root / 'out', m, core2, draft=False, scope='r17-test', batch='trap-20261014',
                        expires=int(time.time()) + 86400, prior=0, release=release, gate=gate, review=stage / mp.ADAPTER / 'SPEC.md')
    args = {p.stem: json.loads((stage / mp.R17 / 'native-jobs' / p.stem / 'arguments.json').read_text())['args'] for p in paths}
    s2 = args['r17-s2-opq-trap-20261014']
    s3 = args['r17-s3-opq-trap-20261014']
    check('TRAP: omitting --cell with one --gate generates all three proposals in one batch', len(paths) == 3)
    check('TRAP: S3\'s signed arguments.json points at the SAME gate file as S2',
          s2[s2.index('--staged-gate') + 1] == s3[s3.index('--staged-gate') + 1] == str(gate))
    print('   (the adapter refuses a gate whose call set differs from the completed calls: staged_gate_call_set; see repro_r4_readme_values.py)')
    # generate refuses an existing output directory and an existing per-job dir
    try:
        mp.generate(stage, root / 'out', m, core2, draft=False, scope='r17-test', batch='trap-20261014', expires=int(time.time()) + 86400,
                    prior=0, release=release, gate=gate, review=stage / mp.ADAPTER / 'SPEC.md')
        check('existing output dir accepted?!', False)
    except FileExistsError:
        check('existing output directory refused', True)
    try:
        mp.generate(stage, root / 'out2', m, core2, draft=False, scope='r17-test', batch='trap-20261014', expires=int(time.time()) + 86400,
                    prior=0, cells=['S1-OPQ'], release=release, review=stage / mp.ADAPTER / 'SPEC.md')
        check('existing native-jobs/<job-id> accepted?!', False)
    except FileExistsError:
        check('re-using a batch id: existing native-jobs/<job-id> in the stage refused', True)
    # budget: 3 cells with prior that overflows the ceiling
    try:
        mp.generate(stage, root / 'out3', m, core2, draft=True, scope='r17-test', batch='b2', expires=int(time.time()) + 86400, prior=1_200_000_000)
        check('prior overflow accepted?!', False)
    except ValueError as exc:
        check('prior 1.20 + 3 x 0.27 > 2.00 refused (%s)' % exc, 'exceed' in str(exc))
    try:
        mp.generate(stage, root / 'out4', m, core2, draft=False, scope='r17-test', batch='b3', expires=int(time.time()) + 86400, prior=0,
                    cells=['S2-OPQ'], release=release, review=stage / mp.ADAPTER / 'SPEC.md')
        check('S2 without gate accepted?!', False)
    except ValueError as exc:
        check('non-draft S2 without --gate refused', 'gate' in str(exc))
    try:
        mp.generate(stage, root / 'out5', m, core2, draft=False, scope='r17-test', batch='b4', expires=int(time.time()) + 8 * 86400, prior=0,
                    cells=['S1-OPQ'], release=release, review=stage / mp.ADAPTER / 'SPEC.md')
        check('expiry > 7 d accepted?!', False)
    except ValueError as exc:
        check('expiry beyond 7 days refused by the offline validator', 'expiry' in str(exc))

print('SUMMARY proposals:', sum(results), 'of', len(results), 'checks held')
sys.exit(0 if all(results) else 1)
