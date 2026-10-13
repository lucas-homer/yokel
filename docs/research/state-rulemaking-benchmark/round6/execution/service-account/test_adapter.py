import contextlib,importlib.util,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('adapter',HERE/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class NoEnvironment:
    def __contains__(self,key):raise AssertionError('unexpected environment access')
    def get(self,key):raise AssertionError('unexpected environment access')
class FakeRuntime:
    def __init__(self,fail=False):self.calls=[];self.fail=fail
    def run(self,*args,**kwargs):
        self.calls.append(kwargs)
        if kwargs['live']:
            print('SYNTHETIC_KEY_OUTPUT')
            if self.fail:raise RuntimeError('SYNTHETIC_KEY_EXCEPTION')
            return {'state':'completed'}
        return {'documents':4,'PDF_pages':14,'source_validation':[{'errors':[]}],'production_eligible':False}
class Controls(unittest.TestCase):
    def test_all_actual_offline_bindings(self):
        verified=a.verify_inputs();self.assertEqual(verified['freeze_counts'],{'freeze-A.json':58,'freeze-S.json':806,'freeze-B.json':9});self.assertEqual(verified['max_new_operations'],24)
    def test_check_no_environment_read(self):
        runtime=FakeRuntime()
        with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'runtime_module',return_value=runtime),patch.object(a.os,'environ',NoEnvironment()):
            result=a.check();self.assertFalse(result['credentials_read']);self.assertEqual(result['provider_calls'],0)
        self.assertFalse(runtime.calls[0]['live'])
    def test_freeze_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'data';p.write_text('first');f=root/'freeze.json';f.write_text(json.dumps({'created_utc':'synthetic','description':'test','files':[{'path':'data','sha256':a.digest(p),'bytes':5}]}));want=a.digest(f)
            self.assertEqual(a.verify_freeze(root,f,want),1);p.write_text('other')
            with self.assertRaises(a.Denied):a.verify_freeze(root,f,want)
    def test_freeze_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=root/'freeze.json';f.write_text(json.dumps({'created_utc':'synthetic','description':'test','files':[{'path':'../outside','sha256':'0'*64,'bytes':0}]}))
            with self.assertRaises(a.Denied):a.verify_freeze(root,f,a.digest(f))
    def test_preexisting_run_refused_before_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'run';run.mkdir()
            with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'RUN',run),patch.object(a,'HERE',root),patch.object(a.os,'environ',NoEnvironment()):
                with self.assertRaises(a.Denied):a.live_initial()
    def test_live_fixed_schedule_nonsecret_receipts(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'adapter.py').write_text('synthetic');(root/'dependencies.json').write_text('{}');runtime=FakeRuntime(fail);stream=io.StringIO()
                with patch.object(a,'verify_inputs',return_value={'budget_usd':2.0,'max_new_operations':24}),patch.object(a,'HERE',root),patch.object(a,'RUN',root/'run'),patch.object(a,'runtime_module',return_value=runtime),patch.object(a.os,'environ',{'OPENROUTER_API_KEY':'SYNTHETIC_OR_KEY','TYPESAFE_API_KEY':'SYNTHETIC_JEV_KEY'}),contextlib.redirect_stdout(stream):
                    if fail:
                        with self.assertRaises(a.Denied):a.live_initial()
                    else:a.live_initial()
                self.assertEqual(stream.getvalue(),'');self.assertEqual(runtime.calls[-1]['max_new'],24);self.assertEqual(runtime.calls[-1]['budget'],2.0);self.assertTrue(runtime.calls[-1]['live']);self.assertEqual(runtime.calls[-1]['authorization'],a.AUTHORIZATION)
                for path in root.glob('live-*.json'):
                    raw=path.read_text();self.assertNotIn('SYNTHETIC_',raw);self.assertNotIn('exception',raw.replace('exception_text_retained',''))
                self.assertTrue((root/'live-intent.json').exists());self.assertEqual((root/'live-stop.json').exists(),fail)
    def test_invalid_cli_generic_only(self):
        out=io.StringIO()
        with patch.object(a.sys,'argv',['adapter','--caller-override','SYNTHETIC_SECRET']),contextlib.redirect_stderr(out):self.assertEqual(a.main(),1)
        self.assertEqual(out.getvalue(),'Round6 adapter stopped; inspect approved nonsecret receipts.\n')
    def test_no_op_or_subprocess_calls(self):
        import ast
        tree=ast.parse((HERE/'adapter.py').read_text());imports={alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names}
        self.assertNotIn('subprocess',imports)
if __name__=='__main__':unittest.main(verbosity=2)
