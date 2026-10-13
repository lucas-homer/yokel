"""Read-only independent checks of stopped synthetic artifacts; never builds/runs jobs."""
import base64, hashlib, json, re, subprocess
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
ROOT = Path(__file__).resolve().parent.parent / 'prototype'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    handoff=json.loads((ROOT/'HANDOFF.json').read_text())
    result=json.loads((ROOT/'RESULT.json').read_text())
    active=Path(result['artifacts_directory'])
    checks=[]
    def check(name, ok):
        checks.append({'name':name, 'passed':bool(ok)})
        assert ok, name
    check('all-handoff-files-exact', all((ROOT/p).stat().st_size==v['bytes'] and sha(ROOT/p)==v['sha256'] for p,v in handoff['files'].items()))
    check('27-owner-controls-recorded', len(result['tests'])==result['test_count']==handoff['test_count']==27 and all(t['passed'] for t in result['tests']))
    check('executor-hash-binds-both-accepted-jobs', sha(active/'executor')==handoff['executor_sha256']==result['executor_sha256'] and all(j['executor_sha256']==result['executor_sha256'] for j in result['accepted_jobs']))
    check('both-journal-claims-bind-original-manifests', all((active/'journal'/j['job_id']).read_text()==j['manifest_sha256'] for j in result['accepted_jobs']))
    header=(active/'FixturePolicy.h').read_text()
    public=base64.b64decode(re.search(r'PublicKey\s*=\s*@"([^"]+)"',header).group(1))
    check('public-key-fingerprint', hashlib.sha256(public).hexdigest()==result['synthetic_public_key_sha256'])
    key=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),public)
    for name, expected in [('job-alpha',True),('job-beta',True),('duplicate',True),('wrong-key',False),('tampered',False)]:
        raw=(active/'registry'/f'{name}.json').read_bytes()
        sig=(active/'registry'/f'{name}.sig').read_bytes()
        try:
            key.verify(sig,b'yokel.synthetic.jobs.v1\0'+raw,ec.ECDSA(hashes.SHA256()))
            valid=True
        except InvalidSignature: valid=False
        check('independent-signature-'+name, valid==expected)
    executable=str(active/'executor')
    before={p:sha(p) for p in active.rglob('*') if p.is_file()}
    def probe(name,args,expected):
        p=subprocess.run([executable,*args],env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        check(name,(p.returncode==0)==expected)
    probe('native-check-valid-beta',['check','job-beta'],True)
    for name in ['duplicate','wrong-key','tampered','unsigned',*[f'reject-{n}' for n in range(4,20)]]:
        probe('native-reject-'+name,['check',name],False)
    probe('native-reject-substitution-with-original-hash',['stage-check','substitution','0'*64],False)
    for name in ['../job-beta','/job-beta','job-beta/../job-beta','JOB-beta','job-beta\n']:
        probe('native-reject-id-'+repr(name),['check',name],False)
    probe('native-reject-arbitrary-command',['exec','job-beta'],False)
    check('artifact-files-remained-unchanged', before=={p:sha(p) for p in active.rglob('*') if p.is_file()})
    print(json.dumps({'status':'passed','independent_checks':len(checks),'builds':0,'job_dispatches':0,'keychain_access':False,'provider_calls':0,'handoff_sha256':sha(ROOT/'HANDOFF.json'),'checks':checks},indent=2))
if __name__=='__main__': main()
