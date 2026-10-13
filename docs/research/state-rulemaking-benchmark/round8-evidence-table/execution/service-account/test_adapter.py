import contextlib,importlib.util,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r8_adapter',HERE/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class NoEnvironment:
    def __contains__(self,key):raise AssertionError('environment read')
    def get(self,key):raise AssertionError('environment read')
class Runtime:
    def run(self,*args,**kwargs):return dict(documents=1,PDF_pages=2,source_validation=[],state='completed')
class Controls(unittest.TestCase):
    def test_check_never_reads_credentials(self):
        with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'runtime_module',return_value=Runtime()),patch.object(a.os,'environ',NoEnvironment()):
            self.assertFalse(a.check()['credentials_read'])
    def test_existing_run_denied_before_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'RUN',Path(temp)),patch.object(a.os,'environ',NoEnvironment()):
                with self.assertRaises(a.Denied):a.live_initial()
    def test_cli_error_does_not_echo_input(self):
        stream=io.StringIO()
        with patch.object(a.sys,'argv',['adapter','caller-secret']),contextlib.redirect_stderr(stream):self.assertEqual(a.main(),1)
        self.assertNotIn('caller-secret',stream.getvalue())
    def test_preparer_released_manifest_pins_external_source_targets(self):
        spec=importlib.util.spec_from_file_location('probe_preparer',HERE/'prepare_manifest.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        released=json.loads((HERE.parents[1]/'sources/source-inputs.READY.json').read_bytes())
        self.assertEqual(set(released),{'schema_version','documents'})
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=base/'round8-evidence-table';here=root/'execution/service-account';here.mkdir(parents=True);(root/'sources').mkdir();(root/'runtime').mkdir();old=base/'round8';(old/'execution').mkdir(parents=True)
            def put(path,value):path.write_text(json.dumps(value))
            put(root/'sources/source-inputs.READY.json',released);put(root/'runtime/implementation.json',{'code':{}});put(root/'execution/live-authorization.json',{});(here/'adapter.py').write_text('fixture')
            for name in ('A','S'):put(root/'execution'/('freeze-'+name+'.json'),{'files':[]})
            for name in ('B','E'):put(old/'execution'/('freeze-'+name+'.json'),{'files':[]})
            cap=base/'round8-cap-probe/execution';cap.mkdir(parents=True);prior=cap/'prior-intent.json';prior.write_bytes(b'synthetic prior intent');put(cap/'freeze-E.json',{'files':[{'path':'execution/prior-intent.json','sha256':m.digest(prior),'bytes':prior.stat().st_size}]})
            contract=base/'round8-contract-probe/execution';contract.mkdir(parents=True);put(contract/'freeze-E.json',{'files':[]})
            for item in released['documents'][0]['retained_inputs'].values():
                target=base/'retained'/Path(item['path']).name;target.parent.mkdir(exist_ok=True);target.write_bytes(b'synthetic retained input');item['path']=str(target)
            put(root/'sources/source-inputs.READY.json',released)
            targets=[]
            for kind in ('text','pdf'):
                target=(root/'sources'/released['documents'][0][kind+'_path']).resolve();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(('synthetic '+kind).encode());targets.append(target)
            python=base/'bin/python3.12';python.parent.mkdir();python.write_bytes(b'fixture executable');lib=base/'lib';std=lib/'python3.12';site=std/'site-packages';site.mkdir(parents=True)
            with patch.multiple(m,ROOT=root,HERE=here,PYTHON=python,LIB=lib,STD=std,SITE=site):result=m.prepare()
            deps=json.loads((here/'dependencies.json').read_bytes());job=json.loads((here/'native-job.json').read_bytes())
            for target in targets:
                self.assertEqual(deps['files'][str(target)],m.digest(target));self.assertEqual(job['files'][str(target)],m.digest(target))
            self.assertEqual(deps['files'][str(prior.resolve())],m.digest(prior));self.assertEqual(job['files'][str(prior.resolve())],m.digest(prior));self.assertEqual(result['provider_calls'],0);self.assertFalse(result['credentials_read']);self.assertEqual(job['argv'][-1],'--live-initial')
if __name__=='__main__':unittest.main(verbosity=2)
