"""Produce UNSIGNED native proposals; never sign, launch, inspect secrets or invoke op.

Draft mode uses only metadata hashes and creates job/config bytes under its output.
Release preparation mode requires an actual verified stage and pinned release evidence.
"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import re
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r17_staging', HERE / 'stage.py')
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
R17 = 'round17-paid-comparison'
ADAPTER = R17 + '/adapter-r1-4'
CELLS = ['S1-OPQ', 'S2-OPQ', 'S3-OPQ']
SAFE = 2**52 - 1


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', value) is not None


def validate(m, core, *, now, check_files=True):
    """Offline Manifest.h LoadJob/ValidatePolicy admission semantics, without signature.

    Native signature/registry custody/op integrity/claim/execution are deliberately
    outside this check. No installed native executable or signing helper is invoked.
    """
    require(set(m) == {'schema_version', 'job_id', 'scope_id', 'project', 'expires_unix',
                      'provider_variables', 'job', 'budget', 'review'}, 'manifest keys')
    require(m['schema_version'] == 'yokel.research-job.v1' and identifier(m['job_id'])
            and identifier(m['scope_id']) and m['project'] == 'yokel.docketclock.research', 'identity')
    require(type(m['expires_unix']) is int and now < m['expires_unix'] <= now + 7*86400, 'expiry')
    require(m['provider_variables'] == ['OPENROUTER_API_KEY'] and
            'OPENROUTER_API_KEY' in core['base_policy']['references'], 'OpenRouter-only subset')
    j = m['job']
    require(set(j) == {'argv', 'files', 'timeout_seconds'}, 'job keys')
    a = j['argv']
    require(isinstance(a, list) and len(a) == 6 and all(isinstance(v, str) for v in a)
            and a[:4] == [core['python_path'], '-I', '-S', '-B'] and a[5] == '--live-initial'
            and a[4].endswith('/adapter.py'), 'argv grammar')
    require(type(j['timeout_seconds']) is int and 1 <= j['timeout_seconds'] <= core['timeout_max_seconds'], 'timeout')
    def path_ok(s, roots):
        p = Path(s)
        require(p.is_absolute() and str(p) == s and '\x00' not in s and '\n' not in s and '\r' not in s
                and '..' not in p.parts and st.inside(p, roots), 'path roots')
        if check_files:
            st.no_symlinks(p)
            require(p.resolve() == p, 'canonical path')
    path_ok(a[4], core['adapter_roots'])
    f = j['files']
    require(isinstance(f, dict) and 0 < len(f) <= 10000 and a[0] in f and a[4] in f, 'file pins')
    for p, h in f.items():
        path_ok(p, core['dependency_roots'])
        require(isinstance(h, str) and re.fullmatch(r'[a-f0-9]{64}', h) is not None, 'sha256')
        if check_files:
            require(st.digest(st.read_regular(p)) == h, 'file drift')
    b = m['budget']
    require(set(b) == {'prior_nanousd', 'reservation_nanousd', 'ceiling_nanousd'}, 'budget keys')
    require(all(type(v) is int and 0 <= v <= SAFE for v in b.values()) and b['ceiling_nanousd'] > 0
            and b['prior_nanousd'] + b['reservation_nanousd'] <= b['ceiling_nanousd'], 'budget arithmetic')
    require(b['reservation_nanousd'] == 270_000_000 and b['ceiling_nanousd'] == 2_000_000_000, 'R17 metadata budget')
    r = m['review']
    require(set(r) == {'path', 'sha256'} and f.get(r['path']) == r['sha256'], 'review pin')
    require(len(st.canonical(m)) <= 4*1024*1024, 'size')
    return True


def release_pins(stage, release, *, cell, gate):
    """Collect finalized release artifact closure; no ledger/output pins (they mutate)."""
    out = {}
    def add(path, expected=None):
        path = st.no_symlinks(path)
        require(path.is_relative_to(stage), 'release dependency outside stage')
        raw = st.read_regular(path)
        h = st.digest(raw)
        require(expected is None or h == expected, 'release artifact drift')
        out[str(path)] = h
        return raw
    d = json.loads(add(release))
    require(d.get('schema_version') == 'r17.release.v1' and d.get('required_calls') == CELLS
            and d.get('typed_testable') is False and d.get('release_policy') in ('P-HARD', 'P-ACCEPT'), 'final release identity')
    artifacts = d['artifacts']
    required = {'protocol', 'budget', 'reference_spec', 'adjudication_spec', 'scorer', 'recon',
        'cases', 'cases_src', 'check', 'A1_fixture_gate', 'A2_fixture_gate', 'sources_ready',
        'reference_ready', 'scoring_manifest', 'policy_evidence', 'key_attestation', 'machine_check',
        'roles_auth', 'adapter', 'tests', 'adapter_ready', 'design_ready', 'design_primary', 'host_driver'}
    require(required <= artifacts.keys(), 'missing release evidence')
    for role, item in artifacts.items():
        path = stage / st.relative(item['path'])
        raw = add(path, item['sha256'])
        if role in ('reference_ready', 'adapter_ready'):
            freeze = json.loads(raw)
            for name, pin in freeze.get('sha256', freeze.get('files', {})).items():
                add(path.parent / st.relative(name), pin['sha256'] if isinstance(pin, dict) else pin)
        if role == 'policy_evidence':
            evidence = json.loads(raw)
            for item2 in evidence.get('documentation', []) + ([evidence['review']] if 'review' in evidence else []):
                add(stage / st.relative(item2['path']), item2['sha256'])
    if cell != 'S1-OPQ':
        require(gate is not None, 'prior-cell accepted adjudication gate required')
        gd = json.loads(add(gate))
        for name, h in gd['files'].items():
            add(gate.parent / st.relative(name), h)
    return out


def generate(stage, output, manifest, core, *, draft, scope, batch, expires, prior,
             cells=CELLS, release=None, gate=None, review=None):
    stage = st.no_symlinks(stage)
    require(identifier(scope) and identifier('r17-s1-opq-' + batch), 'scope/batch')
    require(cells and len(set(cells)) == len(cells) and all(c in CELLS for c in cells), 'cells')
    if not draft:
        st.verify_stage(stage, manifest)
        require(release is not None and review is not None, 'final release and independent review required')
        require(cells == ['S1-OPQ'] or gate is not None, 'prior-cell accepted adjudication gate required')
    # Atomic freshness: refuse existing output and per-job directory.
    output = st.no_symlinks(output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    require(type(prior) is int and prior >= 0 and prior + len(cells)*270_000_000 <= 2_000_000_000, 'aggregate reservations exceed ceiling')
    template = st.read_regular(st.BENCH / ADAPTER / 'native_entry.py')
    require(st.digest(template) == manifest['files'][ADAPTER + '/native_entry.py'], 'entry template drift')
    base = {str(stage / name): h for name, h in manifest['files'].items()}
    python = core['python_path']
    base[python] = st.digest(st.read_regular(python))
    release = release or stage / R17 / 'run/RELEASE.json'
    review = review or stage / ADAPTER / 'SPEC.md'
    created = []
    for cell in cells:
        job_id = 'r17-' + cell.lower() + '-' + batch
        job_rel = R17 + '/native-jobs/' + job_id
        job_final = stage / job_rel
        job_write = (output / 'native-jobs' / job_id) if draft else job_final
        job_write = st.no_symlinks(job_write)
        job_write.mkdir(parents=True, exist_ok=False, mode=0o700)
        args = ['--cell', cell, '--release', str(release), '--run-root', str(stage / R17 / 'run'),
                '--attempt-dir', str(stage / R17 / 'run' / job_id), '--job-id', job_id]
        effective_gate = gate
        if cell != 'S1-OPQ':
            effective_gate = gate or stage / R17 / 'run/gates' / (cell + '.json')
            args += ['--staged-gate', str(effective_gate)]
        config = st.canonical({'schema_version': 'r17.native-args.v1',
            'host_sha256': manifest['files'][ADAPTER + '/host_driver.py'], 'args': args})
        for name, raw in (('adapter.py', template), ('arguments.json', config)):
            path = job_write / name
            with path.open('xb') as f:
                f.write(raw)
            path.chmod(0o600)
        files = dict(base)
        files[str(job_final / 'adapter.py')] = st.digest(template)
        files[str(job_final / 'arguments.json')] = st.digest(config)
        if not draft:
            files.update(release_pins(stage, release, cell=cell, gate=effective_gate))
            files[str(review)] = st.digest(st.read_regular(review))
        proposal = {'schema_version': 'yokel.research-job.v1', 'job_id': job_id, 'scope_id': scope,
            'project': 'yokel.docketclock.research', 'expires_unix': expires,
            'provider_variables': ['OPENROUTER_API_KEY'],
            'job': {'argv': [python, '-I', '-S', '-B', str(job_final / 'adapter.py'), '--live-initial'],
                    'files': files, 'timeout_seconds': 1800},
            'budget': {'prior_nanousd': prior, 'reservation_nanousd': 270_000_000, 'ceiling_nanousd': 2_000_000_000},
            'review': {'path': str(review), 'sha256': files[str(review)]}}
        validate(proposal, core, now=int(time.time()), check_files=not draft)
        path = output / (job_id + '.json')
        with path.open('xb') as f:
            f.write(st.canonical(proposal))
        path.chmod(0o600)
        created.append(path)
        prior += 270_000_000  # conservative sequential reservations, NOT actual ledger authority
    (output / 'UNSIGNED.txt').write_text('UNSIGNED ' + ('DRAFT: prospective stage paths; missing release/evidence; scope and expiry require primary review.\n' if draft else 'PROPOSALS: primary review/signing required. No executor invoked.\n'))
    return created


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--draft', action='store_true')
    p.add_argument('--scope', default='r17-paid-comparison')
    p.add_argument('--batch', default=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S'))
    p.add_argument('--expires-unix', type=int, default=int(time.time()) + 86400)
    p.add_argument('--prior-nanousd', type=int, default=0)
    p.add_argument('--cell', choices=CELLS, action='append')
    p.add_argument('--release', type=Path)
    p.add_argument('--gate', type=Path)
    p.add_argument('--review', type=Path)
    args = p.parse_args()
    m = st.load_manifest()
    core = json.loads(st.read_regular(st.CORE))
    target = args.stage or Path.home() / 'dev/yokel/.r17-stage' / st.content_id(m)
    for path in generate(target, args.output, m, core, draft=args.draft, scope=args.scope,
            batch=args.batch, expires=args.expires_unix, prior=args.prior_nanousd,
            cells=args.cell or CELLS, release=args.release, gate=args.gate, review=args.review):
        print(path)


if __name__ == '__main__':
    main()
