import contextlib,importlib.util,io,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class Controls(unittest.TestCase):
    def test_distinct_identity_boolean_only_and_no_secret_derivation(self):
        for job in ('job-alpha','job-beta'):
            a=load(job,ROOT/job/'adapter.py')
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'receipt.json';value=a.check_and_record({'OPENROUTER_API_KEY':'synthetic-sensitive-value'},path);self.assertEqual(value['job_id'],job);self.assertTrue(all(type(v) is bool for k,v in value.items() if k!='job_id'));self.assertNotIn('synthetic-sensitive-value',path.read_text());self.assertEqual(set(value),{'job_id','openrouter_nonempty','service_account_token_absent','typesafe_key_absent','network_called','provider_called'});self.assertFalse(value['network_called']);self.assertFalse(value['provider_called']);self.assertEqual(path.stat().st_mode&0o777,0o600)
                with self.assertRaises(a.Denied):a.check_and_record({'OPENROUTER_API_KEY':'different'},path)
    def test_missing_or_forbidden_environment_never_creates_receipt(self):
        for job in ('job-alpha','job-beta'):
            a=load(job,ROOT/job/'adapter.py')
            for env in ({},{'OPENROUTER_API_KEY':' '},{'OPENROUTER_API_KEY':'dummy','OP_SERVICE_ACCOUNT_TOKEN':'dummySA'},{'OPENROUTER_API_KEY':'dummy','TYPESAFE_API_KEY':'dummyJev'}):
                with tempfile.TemporaryDirectory() as temp:
                    path=Path(temp)/'receipt.json'
                    with self.assertRaises(a.Denied):a.check_and_record(env,path)
                    self.assertFalse(path.exists())
    def test_symlink_receipt_no_overwrite_and_generic_error(self):
        a=load('alpha',ROOT/'job-alpha/adapter.py')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=root/'target';target.write_bytes(b'unchanged');path=root/'receipt.json';path.symlink_to(target)
            with self.assertRaises(a.Denied):a.check_and_record({'OPENROUTER_API_KEY':'dummy'},path)
            self.assertEqual(target.read_bytes(),b'unchanged')
        output=io.StringIO()
        with patch.object(a.sys,'argv',['adapter','sensitive-invalid-arg']),contextlib.redirect_stdout(output):self.assertEqual(a.main(),1)
        self.assertNotIn('sensitive-invalid-arg',output.getvalue())
    def test_unsigned_proposals_exact_zero_no_fabricated_spend(self):
        m=load('smoke_preparation',HERE/'prepare_jobs.py')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            for job in ('job-alpha','job-beta'):(root/job).mkdir();(root/job/'adapter.py').write_bytes((ROOT/job/'adapter.py').read_bytes())
            python=root/'bin/python3.12';python.parent.mkdir();python.write_bytes(b'synthetic executable');lib=root/'lib';std=lib/'python3.12';std.mkdir(parents=True);review=root/'review.md';review.write_bytes(b'synthetic smoke review')
            with patch.multiple(m,ROOT=root,PYTHON=python,LIB=lib,STD=std):result=m.prepare(scope_id='synthetic-smoke',expires_unix=int(time.time())+3600,review=review)
            self.assertFalse(result['signing_attempted']);self.assertTrue(result['zero_native_reservation']);self.assertFalse(result['benchmark_ledger_modified'])
            proposals=[json.loads((root/job/'UNSIGNED-ZERO-COST-PROPOSAL.json').read_bytes()) for job in ('job-alpha','job-beta')]
            self.assertEqual([p['job_id'] for p in proposals],['job-alpha','job-beta']);self.assertEqual(proposals[0]['job']['argv'][0],proposals[1]['job']['argv'][0]);self.assertNotEqual(proposals[0]['job']['argv'][4],proposals[1]['job']['argv'][4])
            for p in proposals:self.assertEqual(p['provider_variables'],['OPENROUTER_API_KEY']);self.assertEqual(p['budget'],{'prior_nanousd':0,'reservation_nanousd':0,'ceiling_nanousd':2000000000});self.assertEqual(p['job']['argv'][1:4],['-I','-S','-B']);self.assertEqual(p['job']['argv'][-1],'--live-initial');self.assertEqual(p['job']['files'][str(review)],m.sha(review))
if __name__=='__main__':unittest.main(verbosity=2)
