"""Primary-owned offline binding/dependency/job preparation, after stronger-cap freezes. No credentials/build/live."""
import argparse,hashlib,json,re,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12');LIB=PYTHON.parent.parent/'lib';STD=LIB/'python3.12';SITE=STD/'site-packages'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with path.open('xb') as f:f.write(raw)
JOB_ID='round8-stronger-cap-initial'
STABLE_INTERFACE=ROOT.parents[3]/'tools/research-credentials-stable/INTERFACE.md'
def prepare(*,scope_id,expires_unix,review_path):
    # Validate release metadata before any exclusive outputs. Candidate release bounded to 24 hours.
    if not isinstance(scope_id,str) or not re.fullmatch('[a-z][a-z0-9-]{0,63}',scope_id) or type(expires_unix) is not int or not int(time.time())<expires_unix<=int(time.time())+86400:raise ValueError('scope/future bounded expiry required')
    review_path=Path(review_path).resolve()
    if not review_path.is_file() or not STABLE_INTERFACE.is_file():raise ValueError('final review receipt/stable interface required')
    # Future label content is only hashed by freeze references; never decoded as source truth.
    implementation=ROOT/'runtime/implementation.json';manifest=ROOT/'sources/source-inputs.READY.json';authorization=ROOT/'execution/live-authorization.json'
    paths={PYTHON.resolve(),HERE/'adapter.py',implementation,manifest,authorization,review_path}
    for name in ('A','S'):
        freeze=ROOT/'execution'/('freeze-'+name+'.json');paths.add(freeze)
        for row in json.loads(freeze.read_bytes())['files']:
            rel=Path(row['path']);path=(ROOT/rel).resolve()
            if rel.is_absolute() or not path.is_relative_to(ROOT):raise ValueError('freeze escape')
            paths.add(path)
    old=ROOT.parent/'round8'
    for freeze in (old/'execution/freeze-B.json',old/'execution/freeze-E.json',ROOT.parent/'round8-cap-probe/execution/freeze-E.json',ROOT.parent/'round8-contract-probe/execution/freeze-E.json',ROOT.parent/'round8-evidence-table/execution/freeze-E.json'):
        paths.add(freeze)
        base=freeze.parent.parent
        for row in json.loads(freeze.read_bytes())['files']:
            rel=Path(row['path']);path=(base/rel).resolve()
            if rel.is_absolute() or not path.is_relative_to(base.resolve()) or digest(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise ValueError('prior freeze escape or drift')
            paths.add(path)
    source_units=json.loads(manifest.read_bytes())['documents']
    for unit in source_units:
        paths.update((manifest.parent/unit[key]).resolve() for key in ('text_path','pdf_path'))
        paths.update(Path(item['path']).resolve() for item in unit['retained_inputs'].values())
    paths.update(Path(x) for x in json.loads(implementation.read_bytes())['code'])
    paths.update(p for p in STD.rglob('*') if p.is_file() and 'site-packages' not in p.parts)
    paths.update(p for p in LIB.glob('*.dylib') if p.is_file())
    for name in ('pypdf','cryptography','PIL','cffi'):
        folder=SITE/name
        if folder.is_dir():paths.update(p for p in folder.rglob('*') if p.is_file())
    for pattern in ('_cffi_backend*.so','pypdf-*.dist-info','pillow.libs','cryptography.libs'):
        for folder in SITE.glob(pattern):
            paths.update(p for p in folder.rglob('*') if p.is_file()) if folder.is_dir() else paths.add(folder)
    files={str(p.resolve()):digest(p) for p in sorted(paths)}
    put(HERE/'dependencies.json',dict(schema_version='round8-stronger-cap-probe.service-dependencies.v1',files=files,dependency_scope='All stronger-cap code/source/label-freeze references, executable, complete Python stdlib/extensions/dylibs and pypdf dependencies; OS/network trust external; native -I -S -B skips site startup hooks.'))
    binding=dict(schema_version='round8-stronger-cap-probe.service-binding.v1',implementation_sha256=digest(implementation),manifest_sha256=digest(manifest),authorization_sha256=digest(authorization),dependencies_sha256=digest(HERE/'dependencies.json'))
    binding.update({'freeze_'+name+'_sha256':digest(ROOT/'execution'/('freeze-'+name+'.json')) for name in ('A','S')});binding['freeze_B_sha256']=digest(ROOT.parent/'round8/execution/freeze-B.json');put(HERE/'binding.json',binding)
    files.update({str(HERE/name):digest(HERE/name) for name in ('binding.json','dependencies.json')})
    proposal=dict(schema_version='yokel.research-job.v1',job_id=JOB_ID,scope_id=scope_id,project='yokel.docketclock.research',expires_unix=expires_unix,provider_variables=['OPENROUTER_API_KEY'],job=dict(argv=[str(PYTHON),'-I','-S','-B',str(HERE/'adapter.py'),'--live-initial'],files=files,timeout_seconds=1800),budget=dict(prior_nanousd=542976718,reservation_nanousd=161920000,ceiling_nanousd=2000000000),review=dict(path=str(review_path),sha256=digest(review_path)))
    put(HERE/'UNSIGNED-JOB-PROPOSAL.json',proposal)
    return dict(dependency_files=len(files),provider_calls=0,credentials_read=False,signed_job_created=False,approval_status='unapproved_pending_final_credential_review_and_primary_release_signing')
if __name__=='__main__':
    cli=argparse.ArgumentParser(description='Unsigned job proposal only; primary releases/signs externally.')
    cli.add_argument('--scope-id',required=True);cli.add_argument('--expires-unix',required=True,type=int);cli.add_argument('--review',required=True,type=Path)
    args=cli.parse_args();print(json.dumps(prepare(scope_id=args.scope_id,expires_unix=args.expires_unix,review_path=args.review),sort_keys=True))
