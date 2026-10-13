"""Primary-owned offline binding/dependency/job preparation, after all evidence-table freezes. No credentials/build/live."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12');LIB=PYTHON.parent.parent/'lib';STD=LIB/'python3.12';SITE=STD/'site-packages'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with path.open('xb') as f:f.write(raw)
def prepare():
    # Future label content is only hashed by freeze references; never decoded as source truth.
    implementation=ROOT/'runtime/implementation.json';manifest=ROOT/'sources/source-inputs.READY.json';authorization=ROOT/'execution/live-authorization.json'
    paths={PYTHON.resolve(),HERE/'adapter.py',implementation,manifest,authorization}
    for name in ('A','S'):
        freeze=ROOT/'execution'/('freeze-'+name+'.json');paths.add(freeze)
        for row in json.loads(freeze.read_bytes())['files']:
            rel=Path(row['path']);path=(ROOT/rel).resolve()
            if rel.is_absolute() or not path.is_relative_to(ROOT):raise ValueError('freeze escape')
            paths.add(path)
    old=ROOT.parent/'round8'
    for freeze in (old/'execution/freeze-B.json',old/'execution/freeze-E.json',ROOT.parent/'round8-cap-probe/execution/freeze-E.json',ROOT.parent/'round8-contract-probe/execution/freeze-E.json'):
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
    put(HERE/'dependencies.json',dict(schema_version='round8-evidence-table.service-dependencies.v1',files=files,dependency_scope='All evidence-table code/source/label-freeze references, executable, complete Python stdlib/extensions/dylibs and pypdf dependencies; OS/network trust external; native -I -S -B skips site startup hooks.'))
    binding=dict(schema_version='round8-evidence-table.service-binding.v1',implementation_sha256=digest(implementation),manifest_sha256=digest(manifest),authorization_sha256=digest(authorization),dependencies_sha256=digest(HERE/'dependencies.json'))
    binding.update({'freeze_'+name+'_sha256':digest(ROOT/'execution'/('freeze-'+name+'.json')) for name in ('A','S')});binding['freeze_B_sha256']=digest(ROOT.parent/'round8/execution/freeze-B.json');put(HERE/'binding.json',binding)
    files.update({str(HERE/name):digest(HERE/name) for name in ('binding.json','dependencies.json')})
    put(HERE/'native-job.json',dict(argv=[str(PYTHON),'-I','-S','-B',str(HERE/'adapter.py'),'--live-initial'],files=files,timeout_seconds=1800))
    return dict(dependency_files=len(files),provider_calls=0,credentials_read=False)
if __name__=='__main__':print(json.dumps(prepare(),sort_keys=True))
