"""Independent synthetic checks of the release utility. No native builds/dispatch."""
import copy, hashlib, importlib.util, json, os, tempfile, time
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
SOURCE=Path(__file__).resolve().parents[5]/'tools/research-credentials-stable/release.py'
spec=importlib.util.spec_from_file_location('candidate_release',SOURCE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
def main():
    checks=[]
    def check(name,ok):
        checks.append({'name':name,'passed':bool(ok)});assert ok,name
    def rejected(name,fn):
        try:fn()
        except Exception:check(name,True)
        else:check(name,False)
    with tempfile.TemporaryDirectory(prefix='yokel-independent-release-') as temp:
        root=Path(temp).resolve();deps=root/'deps';custody=root/'custody';registry=root/'registry'
        for p in (deps,custody,registry):p.mkdir(mode=0o700)
        for name in ('python','adapter.py','review.md'):(deps/name).write_text('synthetic fixture '+name)
        key=ec.generate_private_key(ec.SECP256R1())
        pub=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
        import base64
        core={'python_path':str(deps/'python'),'adapter_roots':[str(deps)],'dependency_roots':[str(deps)],'registry_dir':str(registry),'public_key_base64':base64.b64encode(pub).decode(),'timeout_max_seconds':1800,'base_policy':{'references':{'OPENROUTER_API_KEY':'synthetic-only','TYPESAFE_API_KEY':'synthetic-only'}}}
        pins={str(p):r.digest(p) for p in deps.iterdir()}
        m={'schema_version':'yokel.research-job.v1','job_id':'review-one','scope_id':'review-fixture','project':'yokel.docketclock.research','expires_unix':int(time.time())+3600,'provider_variables':['OPENROUTER_API_KEY'],'job':{'argv':[str(deps/'python'),'-I','-S','-B',str(deps/'adapter.py'),'--live-initial'],'files':pins,'timeout_seconds':10},'budget':{'prior_nanousd':542976718,'reservation_nanousd':161920000,'ceiling_nanousd':2000000000},'review':{'path':str(deps/'review.md'),'sha256':pins[str(deps/'review.md')]}}
        r.validate(core,m);check('valid-stronger-only-metadata',True)
        pem=custody/'synthetic.pem';pem.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));pem.chmod(0o600)
        loaded=r.read_key(core,pem);check('synthetic-owner-only-key-accepted',loaded.public_key().public_numbers()==key.public_key().public_numbers())
        pem.chmod(0o644);rejected('world-readable-key-rejected',lambda:r.read_key(core,pem));pem.chmod(0o600)
        custody.chmod(0o755);rejected('public-custody-directory-rejected',lambda:r.read_key(core,pem));custody.chmod(0o700)
        link=custody/'link.pem';link.symlink_to(pem);rejected('symlink-key-rejected',lambda:r.read_key(core,link))
        misplaced=deps/'synthetic.pem';misplaced.write_bytes(pem.read_bytes());misplaced.chmod(0o600);rejected('key-in-dependency-roots-rejected',lambda:r.read_key(core,misplaced));misplaced.unlink()
        mutations=[('unknown-field',lambda x:x.update(extra=1)),('scope-traversal',lambda x:x.update(scope_id='../x')),('wrong-project',lambda x:x.update(project='other')),('expired',lambda x:x.update(expires_unix=1)),('expiry-bool',lambda x:x.update(expires_unix=True)),('extra-provider',lambda x:x.update(provider_variables=['LLAMA_CLOUD_API_KEY'])),('duplicate-provider',lambda x:x.update(provider_variables=['OPENROUTER_API_KEY']*2)),('no-provider',lambda x:x.update(provider_variables=[])),('generic-argv',lambda x:x['job']['argv'].append('--extra')),('missing-isolation',lambda x:x['job']['argv'].__setitem__(2,'-c')),('timeout-bool',lambda x:x['job'].update(timeout_seconds=True)),('budget-overflow',lambda x:x['budget'].update(reservation_nanousd=2000000000)),('budget-bool',lambda x:x['budget'].update(prior_nanousd=True)),('budget-float',lambda x:x['budget'].update(prior_nanousd=542976718.0)),('wrong-review-pin',lambda x:x['review'].update(sha256='0'*64)),('missing-python-pin',lambda x:x['job']['files'].pop(str(deps/'python')))]
        for name,change in mutations:
            x=copy.deepcopy(m);change(x);rejected(name,lambda:r.validate(core,x))
        higher=copy.deepcopy(m);higher['budget']={'prior_nanousd':542976718,'reservation_nanousd':2500000000,'ceiling_nanousd':4000000000};r.validate(core,higher);check('future-signed-ceiling-without-core-budget-rebuild',True)
        limit=4503599627370495
        boundary=copy.deepcopy(m);boundary['budget']={'prior_nanousd':limit-1,'reservation_nanousd':1,'ceiling_nanousd':limit};r.validate(core,boundary);check('safe-integer-boundary-accepted',True)
        boundary['budget']['ceiling_nanousd']=limit+1;rejected('unsafe-integer-boundary-rejected',lambda:r.validate(core,boundary))
        boundary['budget']={'prior_nanousd':limit,'reservation_nanousd':limit,'ceiling_nanousd':limit};rejected('large-sum-over-ceiling-rejected',lambda:r.validate(core,boundary))
        duplicate=root/'duplicate.json';duplicate.write_text('{"x":1,"x":2}');rejected('duplicate-json-rejected',lambda:r.read_json(duplicate))
        result=r.publish(core,m,loaded);raw=(registry/'review-one.json').read_bytes();sig=(registry/'review-one.sig').read_bytes()
        check('published-exact-canonical-digest',result==hashlib.sha256(raw).hexdigest() and raw==r.encode(m))
        key.public_key().verify(sig,r.DOMAIN+raw,ec.ECDSA(hashes.SHA256()));check('published-signature-valid',True)
        check('published-files-owner-only',all(p.stat().st_mode&0o777==0o600 for p in registry.iterdir()))
        rejected('immutable-release-refuses-overwrite',lambda:r.publish(core,m,loaded));check('overwrite-refusal-preserves-bytes',raw==(registry/'review-one.json').read_bytes() and sig==(registry/'review-one.sig').read_bytes())
    print(json.dumps({'status':'passed','checks':checks,'independent_checks':len(checks),'source_sha256':r.digest(SOURCE),'native_builds':0,'job_dispatches':0,'real_key_access':False,'keychain_access':False,'provider_calls':0},indent=2))
if __name__=='__main__':main()
