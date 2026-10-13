import contextlib,hashlib,importlib.util,io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stronger_service_candidate',HERE/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class NoEnvironment:
    def __contains__(self,key):raise AssertionError('environment accessed')
    def get(self,key):raise AssertionError('environment accessed')
class Runtime:
    def __init__(self):self.calls=[]
    def run(self,*args,**kwargs):self.calls.append(kwargs);return dict(documents=1,PDF_pages=2,source_validation=[],state='completed')
class ControlledEnvironment:
    def __init__(self):self.gets=[];self.checks=[]
    def __contains__(self,key):self.checks.append(key);return False
    def get(self,key):self.gets.append(key);return 'dummyOR'
class Controls(unittest.TestCase):
    def test_check_never_reads_environment(self):
        runtime=Runtime()
        with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'runtime_module',return_value=runtime),patch.object(a.os,'environ',NoEnvironment()):result=a.check()
        self.assertFalse(result['credentials_read']);self.assertEqual(runtime.calls[0]['max_new'],1);self.assertFalse(runtime.calls[0]['live'])
    def test_existing_run_or_intent_denied_before_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'RUN',root),patch.object(a.os,'environ',NoEnvironment()):
                with self.assertRaises(a.Denied):a.live_initial()
            (root/'live-intent.json').write_bytes(b'{}')
            with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'RUN',root/'absent'),patch.object(a,'HERE',root),patch.object(a.os,'environ',NoEnvironment()):
                with self.assertRaises(a.Denied):a.live_initial()
    def test_only_openrouter_key_and_one_call_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);runtime=Runtime();environment=ControlledEnvironment();verified={'source_labels_freeze_sha256':'a'*64}
            with patch.object(a,'verify_inputs',return_value=verified),patch.object(a,'runtime_module',return_value=runtime),patch.object(a,'RUN',root/'run'),patch.object(a,'HERE',root),patch.object(a,'receipt'),patch.object(a,'digest',return_value='b'*64),patch.object(a.os,'environ',environment):a.live_initial()
            self.assertEqual(environment.gets,['OPENROUTER_API_KEY']);self.assertEqual(environment.checks,['OP_SERVICE_ACCOUNT_TOKEN']);self.assertEqual(runtime.calls[-1]['keys'],{'openrouter':'dummyOR'});self.assertEqual(runtime.calls[-1]['max_new'],1)
    def test_generic_cli_error_and_no_caller_overrides(self):
        stream=io.StringIO()
        with patch.object(a.sys,'argv',['adapter','caller-secret']),contextlib.redirect_stderr(stream):self.assertEqual(a.main(),1)
        self.assertNotIn('caller-secret',stream.getvalue())
    def test_preparation_dependency_closure_proposal_is_unsigned(self):
        spec=importlib.util.spec_from_file_location('stronger_preparer',HERE/'prepare_manifest.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        released=json.loads((HERE.parents[1]/'sources/source-inputs.READY.json').read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp).resolve();root=base/'round8-stronger-cap-probe';here=root/'execution/service-account';here.mkdir(parents=True);(root/'sources').mkdir();(root/'runtime').mkdir();(here/'adapter.py').write_bytes(b'fixture')
            def put(path,value):path.write_text(json.dumps(value))
            for name in ('A','S'):put(root/'execution'/('freeze-'+name+'.json'),{'files':[]})
            put(root/'runtime/implementation.json',{'code':{}});put(root/'execution/live-authorization.json',{})
            old=base/'round8';(old/'execution').mkdir(parents=True);put(old/'execution/freeze-B.json',{'files':[]})
            prior=[]
            for name in ('round8','round8-cap-probe','round8-contract-probe','round8-evidence-table'):
                folder=base/name/'execution';folder.mkdir(parents=True,exist_ok=True);target=folder/'prior.json';target.write_bytes(name.encode());prior.append(target);put(folder/'freeze-E.json',{'files':[{'path':'execution/prior.json','sha256':m.digest(target),'bytes':target.stat().st_size}]})
            targets=[]
            for kind in ('text','pdf'):
                target=(root/'sources'/released['documents'][0][kind+'_path']).resolve();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(('synthetic '+kind).encode());targets.append(target)
            for key,item in released['documents'][0]['retained_inputs'].items():
                target=base/'retained'/key;target.parent.mkdir(exist_ok=True);target.write_bytes(key.encode());item['path']=str(target);targets.append(target)
            put(root/'sources/source-inputs.READY.json',released)
            python=base/'bin/python3.12';python.parent.mkdir();python.write_bytes(b'fixture executable');lib=base/'lib';std=lib/'python3.12';site=std/'site-packages';site.mkdir(parents=True)
            review=base/'FINAL-REVIEW.md';review.write_bytes(b'synthetic review');interface=base/'STABLE-INTERFACE.md';interface.write_bytes(b'synthetic stable interface')
            with patch.multiple(m,ROOT=root,HERE=here,PYTHON=python,LIB=lib,STD=std,SITE=site,STABLE_INTERFACE=interface):result=m.prepare(scope_id='synthetic-scope',expires_unix=int(time.time())+3600,review_path=review)
            deps=json.loads((here/'dependencies.json').read_bytes());proposal=json.loads((here/'UNSIGNED-JOB-PROPOSAL.json').read_bytes())
            for target in targets+prior:self.assertEqual(deps['files'][str(target)],m.digest(target));self.assertEqual(proposal['job']['files'][str(target)],m.digest(target))
            release_path=HERE.parents[5]/'tools/research-credentials-stable/release.py'
            release_spec=importlib.util.spec_from_file_location('stable_release_shape_only',release_path);release=importlib.util.module_from_spec(release_spec);release_spec.loader.exec_module(release)
            core={'base_policy':{'references':{'OPENROUTER_API_KEY':'synthetic-reference'}},'python_path':str(python),'adapter_roots':[str(root)],'dependency_roots':[str(base)],'timeout_max_seconds':1800,'budget_max_nanousd':2000000000}
            release.validate(core,proposal) # pure validation only: no key, publish, signing or executor.
            self.assertEqual(set(proposal),{'schema_version','job_id','scope_id','project','expires_unix','provider_variables','job','budget','review'});self.assertEqual(proposal['schema_version'],'yokel.research-job.v1');self.assertEqual(proposal['provider_variables'],['OPENROUTER_API_KEY']);self.assertEqual(proposal['job_id'],'round8-stronger-cap-initial');self.assertEqual(proposal['budget'],{'prior_nanousd':542976718,'reservation_nanousd':161920000,'ceiling_nanousd':2000000000});self.assertEqual(proposal['job']['files'][str(review)],m.digest(review));self.assertEqual(proposal['review'],{'path':str(review),'sha256':m.digest(review)});self.assertNotIn('signature',proposal);self.assertFalse(result['signed_job_created']);self.assertFalse((here/'native-job.json').exists());self.assertEqual(result['provider_calls'],0)
    def test_invalid_release_metadata_rejects_before_outputs(self):
        spec=importlib.util.spec_from_file_location('stronger_preparer_metadata',HERE/'prepare_manifest.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);review=root/'review.md';review.write_bytes(b'synthetic')
            for scope,expiry in (('',int(time.time())+3600),('scope',0),('scope',True),('scope',int(time.time())+90000)):
                with patch.object(m,'HERE',root):
                    with self.assertRaises(ValueError):m.prepare(scope_id=scope,expires_unix=expiry,review_path=review)
                self.assertEqual(list(root.iterdir()),[review])
if __name__=='__main__':unittest.main(verbosity=2)
