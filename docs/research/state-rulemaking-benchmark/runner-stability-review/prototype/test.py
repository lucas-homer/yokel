"""Synthetic-only harness. Ephemeral P-256 private key stays in memory; no real identity."""
import base64,copy,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes,serialization

HERE=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def build(argv):subprocess.run(argv,check=True,capture_output=True)
def main():
    folder=Path(tempfile.mkdtemp(prefix='synthetic-',dir=HERE));registry=folder/'registry';journal=folder/'journal';registry.mkdir();journal.mkdir()
    key=ec.generate_private_key(ec.SECP256R1()) # Never exported, serialized or persisted.
    public=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    payload=folder/'fixture-payload';executor=folder/'executor'
    header='\n'.join('static NSString *const '+name+' = @'+json.dumps(value)+';' for name,value in [('Registry',str(registry)),('Journal',str(journal)),('Payload',str(payload)),('PublicKey',base64.b64encode(public).decode())])+'\n'
    (folder/'FixturePolicy.h').write_text(header)
    build(['/usr/bin/xcrun','clang','-O2',str(HERE/'payload.c'),'-o',str(payload)])
    build(['/usr/bin/xcrun','clang','-fobjc-arc','-O2','-Wno-deprecated-declarations','-framework','Foundation','-framework','Security','-I',str(folder),str(HERE/'executor.m'),'-o',str(executor)])
    before=digest(executor);tests=[]
    environment={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','HOME':'/synthetic-untrusted','OP_SERVICE_ACCOUNT_TOKEN':'ops_synthetic-inherited','OPENROUTER_API_KEY':'synthetic-inherited','TYPESAFE_API_KEY':'synthetic-inherited','PYTHONPATH':'/synthetic-untrusted'}
    def invoke(mode,job,want,extra=None):
        args=[str(executor),mode,job]+([] if extra is None else [extra])
        result=subprocess.run(args,env=environment,capture_output=True,timeout=10)
        assert (result.returncode==0)==want,(mode,job,result.returncode,result.stderr.decode())
    def manifest(job,tag='alpha'):
        return dict(schema_version='synthetic.fixed-job.v1',job_id=job,project='synthetic-research',provider_scope=['SYNTHETIC_PROVIDER'],argv=[str(payload),'--fixture',tag],files={str(payload):digest(payload)},timeout_seconds=3,prior_microusd=540000,reservation_microusd=100000,shared_budget_microusd=2000000)
    def publish(job,value,raw=None,signer=key):
        data=encode(value) if raw is None else raw;(registry/(job+'.json')).write_bytes(data)
        (registry/(job+'.sig')).write_bytes(signer.sign(b'yokel.synthetic.jobs.v1\0'+data,ec.ECDSA(hashes.SHA256())))
        return hashlib.sha256(data).hexdigest()
    def rejected(name,value=None,raw=None):
        job='reject-'+str(len(tests));v=manifest(job) if value is None else value;v['job_id']=job;publish(job,v,raw)
        invoke('check',job,False);tests.append(dict(name=name,passed=True))
    accepted=[]
    for job,tag in [('job-alpha','alpha'),('job-beta','beta')]:
        h=publish(job,manifest(job,tag));invoke('check',job,True);invoke('run',job,True);accepted.append(dict(job_id=job,manifest_sha256=h,executor_sha256=digest(executor)));tests.append(dict(name=job+'-accepted-fixed-environment',passed=True))
        invoke('run',job,False);tests.append(dict(name=job+'-replay-rejected',passed=True))
    v=manifest('unused');v['provider_scope']=['OPENROUTER_API_KEY'];rejected('real-provider-scope-rejected',v)
    for name,field,value in [('project','project','other'),('timeout','timeout_seconds',6),('timeout-bool','timeout_seconds',True),('reservation','reservation_microusd',170000),('prior-debit','prior_microusd',0),('budget','shared_budget_microusd',3000000),('mode','schema_version','unknown')]:
        v=manifest('unused');v[field]=value;rejected(name+'-out-of-envelope',v)
    for name,args in [('executable',['/bin/sh','--fixture','alpha']),('extra-argv',[str(payload),'--fixture','alpha','extra']),('mode-argv',[str(payload),'--arbitrary','alpha'])]:
        v=manifest('unused');v['argv']=args;rejected(name,v)
    v=manifest('unused');v['caller_environment']={'TOKEN':'synthetic'};rejected('unknown-environment-field',v)
    v=manifest('unused');v['verification_key']='synthetic-override';rejected('manifest-key-override',v)
    v=manifest('unused');v['files'][str(payload)]='0'*64;rejected('wrong-payload-pin',v)
    v=manifest('unused');v['files']={};rejected('missing-payload-pin',v)
    v=manifest('unused');v['files'][str(payload)+'-extra']='0'*64;rejected('extra-unapproved-code-pin',v)
    job='unsigned';publish(job,manifest(job));(registry/(job+'.sig')).unlink();invoke('check',job,False);tests.append(dict(name='unsigned-rejected',passed=True))
    job='tampered';publish(job,manifest(job));(registry/(job+'.json')).write_bytes((registry/(job+'.json')).read_bytes()+b' ');invoke('check',job,False);tests.append(dict(name='tampered-rejected',passed=True))
    job='wrong-key';publish(job,manifest(job),signer=ec.generate_private_key(ec.SECP256R1()));invoke('check',job,False);tests.append(dict(name='untrusted-signing-key-rejected',passed=True))
    job='duplicate';v=manifest(job);raw=encode(v);raw=b'{"project":"synthetic-research",'+raw[1:];publish(job,v,raw);invoke('check',job,False);tests.append(dict(name='signed-duplicate-JSON-field-rejected',passed=True))
    job='substitution';old=publish(job,manifest(job));invoke('stage-check',job,True,old);publish(job,manifest(job,'beta'));invoke('check',job,True);invoke('stage-check',job,False,old);tests.append(dict(name='valid-manifest-substitution-rejected-at-boundary',passed=True))
    job='payload-drift';publish(job,manifest(job));original=payload.read_bytes();payload.write_bytes(original+b'synthetic-drift');invoke('check',job,False);payload.write_bytes(original);tests.append(dict(name='payload-file-drift-rejected',passed=True))
    job='job-alpha';publish(job,manifest(job,'beta'));invoke('run',job,False);tests.append(dict(name='changed-signed-job-ID-replay-rejected',passed=True))
    assert before==digest(executor) and len({x['manifest_sha256'] for x in accepted})==2
    receipt=dict(schema_version='synthetic.stable-executor-proof.v1',state='passed',tests=tests,test_count=len(tests),accepted_jobs=accepted,executor_sha256=before,executor_bytes_unchanged=True,synthetic_public_key_sha256=hashlib.sha256(public).hexdigest(),private_key_persisted=False,keychain_access=False,op_calls=0,provider_calls=0,real_credentials=False,production_ready=False,keychain_continuity_tested=False,artifacts_directory=str(folder))
    (HERE/'RESULT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:receipt[k] for k in ('state','test_count','executor_bytes_unchanged','private_key_persisted','keychain_access','provider_calls','keychain_continuity_tested')}))
if __name__=='__main__':main()
