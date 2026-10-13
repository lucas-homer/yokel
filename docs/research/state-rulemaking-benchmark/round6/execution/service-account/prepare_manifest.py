"""Nonsecret offline pin generator, not part of the paid job."""
import hashlib,json,sysconfig
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PYTHON=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
LIB=PYTHON.parent.parent/'lib';STD=LIB/'python3.12';SITE=STD/'site-packages'
paths={PYTHON,HERE/'adapter.py',ROOT/'execution/live-authorization.json'}
for name in ('freeze-A.json','freeze-S.json','freeze-B.json'):
    p=ROOT/'execution'/name;paths.add(p)
    for row in json.loads(p.read_bytes())['files']:paths.add(ROOT/row['path'])
# All stdlib source/bytecode/extension imports, excluding unrelated third-party packages.
paths.update(p for p in STD.rglob('*') if p.is_file() and 'site-packages' not in p.parts)
paths.update(p for p in LIB.glob('*.dylib') if p.is_file())
# Full imported third-party package roots and supporting extension/metadata files.
for name in ('pypdf','cryptography','PIL','cffi'):
    folder=SITE/name
    if folder.is_dir():paths.update(p for p in folder.rglob('*') if p.is_file())
for pattern in ('_cffi_backend*.so','pypdf-*.dist-info','pillow.libs','cryptography.libs'):
    for p in SITE.glob(pattern):
        if p.is_dir():paths.update(x for x in p.rglob('*') if x.is_file())
        elif p.is_file():paths.add(p)
files={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
value={'schema_version':'round6.service-dependencies.v1','files':files,'dependency_scope':'All freeze A/S/B entries, original authorization, executable, adapter, complete stdlib source/bytecode/extensions, Python dylibs, pypdf/cryptography/PIL/cffi and pypdf metadata. OS libraries/network trust remain external; -I -S -B skips site startup hooks.'}
(HERE/'dependencies.json').write_text(json.dumps(value,indent=2)+'\n')
files={**files,str(HERE/'dependencies.json'):hashlib.sha256((HERE/'dependencies.json').read_bytes()).hexdigest()}
job={'argv':[str(PYTHON),'-I','-S','-B',str(HERE/'adapter.py'),'--live-initial'],'files':files,'timeout_seconds':1800}
(HERE/'native-job.json').write_text(json.dumps(job,indent=2)+'\n');print(json.dumps({'dependency_files':len(value['files']),'native_job_files':len(files)}))
