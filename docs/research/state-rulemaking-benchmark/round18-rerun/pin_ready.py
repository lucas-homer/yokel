"""Pin R18 payloads and verify frozen inputs; no execution or credential access."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
FOLDERS = ('wire', 'recon', 'adapter', 'keycheck', 'release-prep')
REVISIONS = dict(wire='r16.w2.2', recon='A6', adapter='r1.5', keycheck='v3', **{'release-prep':'R18'})

def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def payload(root):
    return {p.relative_to(root).as_posix(): pin(p) for p in sorted(root.rglob('*'))
        if p.is_file() and p.name != 'READY.json' and '__pycache__' not in p.parts
        and ('_out' not in p.relative_to(root).parts or
             ('round2-repros' in p.parts and p.suffix in ('.py','.sh')))}

def frozen():
    return {p.relative_to(BENCH).as_posix(): pin(p)['sha256']
        for root in (BENCH/'round16-wire-compat', BENCH/'round17-paid-comparison')
        for p in sorted(root.rglob('*')) if p.is_file()}

def verify_frozen():
    before = json.loads((HERE/'_out/frozen-before.json').read_bytes())
    assert frozen() == before, 'frozen R16/R17 bytes or file inventory changed'

def dependencies(folder):
    names = []
    if folder in ('wire', 'adapter'):
        names += ['round14-semantic-contract/runtime/common.py']
        prefix = 'round15-condition-preservation/protocol-revised/'
        names += [prefix+n for n in ('READY.json','compact.py','request-settings.json','stage-a.system.txt')]
    if folder == 'adapter':
        names += ['round18-rerun/wire/wire.py', 'round18-rerun/wire/READY.json',
                  'round18-rerun/recon/r17recon.py','round18-rerun/recon/READY.json',
                  'round17-paid-comparison/design-r3-1/READY.primary.json',
                  'round17-paid-comparison/sources-r2/READY.json']
    if folder == 'release-prep':
        names += ['round18-rerun/'+f+'/READY.json' for f in ('wire','recon','adapter')]
        names += ['round18-rerun/amendments/A5-A6.md', 'round18-rerun/DESIGN-NOTE.md']
    return {n:pin(BENCH/n) for n in names}

def manifest():
    path = HERE/'release-prep/prepare_manifest.py'
    s = importlib.util.spec_from_file_location('r18_build_manifest',path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    value = m.build()
    (HERE/'release-prep/STAGE-MANIFEST.json').write_bytes(m.st.canonical(value))

def write(bootstrap=False):
    verify_frozen()
    results = {} if bootstrap else {k:json.loads((HERE/'_out'/ (k+'-results.json')).read_bytes()) for k in ('python312','system')}
    if not bootstrap:
        assert all(r['all_passed'] for r in results.values()), 'tests must pass on both interpreters'
    for folder in FOLDERS:
        if folder == 'release-prep':
            manifest()
        root = HERE/folder
        files = payload(root)
        tests = {}
        for k, r in results.items():
            item = r['suites'][folder]
            tests[k] = dict(run=item['run'], passed=item['run'], failed=0,
                executable=r['interpreter'], flags=r['flags'], output='_out/'+k+'-tests.txt',
                output_pin=pin(root/'_out'/ (k+'-tests.txt')))
        ready = dict(schema_version='r18.offline-ready.v1', revision=REVISIONS[folder],
            status='PRELIMINARY_UNTESTED' if bootstrap else 'READY_OFFLINE_IMPLEMENTATION',
            files=files, sha256={n:p['sha256'] for n,p in files.items()},
            dependencies=dependencies(folder), tests=tests, frozen_inputs_unchanged=True,
            provider_calls=0, network_calls=0, credentials_accessed=False,
            signing_key_accessed=False, native_commands_run=False, committed=False,
            dispatch_authorized=False, production_eligible=False,
            self_pin='READY excludes itself; primary pins exact hash externally')
        if folder=='wire':
            ready.update(version='r16.w1', envelope_version='r16.e3',
                independent_suite={k:r['suites']['independent'] for k,r in results.items()})
        if folder=='adapter':
            ready.update(namespace='r18.paid-rerun.v1', scope='docketclock-research-r18-authorized-20261014',
                FLOOR=270000000, OPERATING=1800000000, CAP=2000000000, required_calls=['S1-OPQ','S2-OPQ','S3-OPQ'])
        if folder=='release-prep':
            ready.update(manifest_status='prospective; baseline/review/bootstrap extras and run evidence installation pending',
                design='round17-paid-comparison/design-r3-1-paccept', fresh_machine_evidence=False)
        (root/'READY.json').write_text(json.dumps(ready,indent=2,sort_keys=True)+'\n')
    if not bootstrap:
        roots = {p.name:pin(p) for p in HERE.iterdir() if p.is_file() and p.name!='READY.json'}
        roots.update({f+'/READY.json':pin(HERE/f/'READY.json') for f in FOLDERS})
        roots.update({'amendments/A5-A6.md':pin(HERE/'amendments/A5-A6.md')})
        roots.update({'_out/'+p.name:pin(p) for p in (HERE/'_out').iterdir() if p.is_file()})
        (HERE/'READY.json').write_text(json.dumps(dict(status='READY_OFFLINE_IMPLEMENTATION',
            files=roots, tests=results, provider_calls=0, credentials_accessed=False,
            frozen_inputs_unchanged=True, paid_release_authorized=False),indent=2,sort_keys=True)+'\n')

def verify():
    verify_frozen()
    hashes = {}
    for folder in FOLDERS:
        root=HERE/folder
        r=json.loads((root/'READY.json').read_bytes())
        assert r['status']=='READY_OFFLINE_IMPLEMENTATION', folder
        assert payload(root)==r['files'], folder+': payload inventory/pin drift'
        assert r['sha256']=={n:v['sha256'] for n,v in r['files'].items()}, folder
        for name, expected in r['dependencies'].items():
            assert pin(BENCH/name)==expected, name
        for item in r['tests'].values():
            assert pin(root/item['output'])==item['output_pin'], folder
        hashes[folder]=pin(root/'READY.json')['sha256']
    m=json.loads((HERE/'release-prep/STAGE-MANIFEST.json').read_bytes())
    aliases={n:'round18-rerun/release-prep/evidence/'+Path(n).name
             for n in m['files'] if n.startswith('round18-rerun/run/')}
    for name, expected in m['files'].items():
        assert pin(BENCH/aliases.get(name,name))['sha256']==expected, name
    r=json.loads((HERE/'READY.json').read_bytes())
    for name, expected in r['files'].items():
        assert pin(HERE/name)==expected, name
    print(json.dumps(dict(all_pins_verified=True, frozen_R16_R17_unchanged=True,
        prospective_run_aliases=aliases, READY_sha256=hashes),sort_keys=True))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bootstrap',action='store_true')
    p.add_argument('--verify',action='store_true')
    args=p.parse_args()
    if not args.verify:
        write(args.bootstrap)
    if not args.bootstrap:
        verify()

if __name__=='__main__':
    main()
