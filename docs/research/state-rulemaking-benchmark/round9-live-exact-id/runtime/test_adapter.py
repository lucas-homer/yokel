"""Offline lifecycle/security checks; synthetic fixtures remain private and never enter request."""
import copy, importlib.util, json, socket, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('live_adapter',HERE/'adapter.py'); a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.planned,cls.request,cls.response,cls.prior=a.preflight()
        cls.fixture=a.read(a.FROZEN.parent/'protocol/response-fixtures.json')['cases'][0]['raw_json']
    def native(self,content=None):
        return dict(model='openai/gpt-6.1-sol',provider='OpenAI',choices=[dict(finish_reason='stop',message=dict(content=self.fixture if content is None else content))],usage=dict(prompt_tokens=100,completion_tokens=100,cost=.0012))
    def run_case(self,native=None,status=200,transport=None):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); run=Path(tmp.name)/'run'; calls=[]
        raw=a.encode(self.native() if native is None else native)
        def fake(body,key): calls.append(body); return status,raw
        try: result=a.execute_once(run,self.planned,self.request,self.response,'synthetic-secret-key',transport or fake)
        except a.Denied: result=None
        return run,calls,raw,result
    def test_check_no_network_or_credentials(self):
        class ForbiddenEnv(dict):
            def get(self,*args): raise AssertionError('credential lookup')
        with patch.object(a.os,'environ',ForbiddenEnv()),patch.object(socket.socket,'connect',side_effect=AssertionError('network')):
            planned,_,_,prior=a.preflight()
        self.assertEqual(prior['prior_nanousd'],696390718)
        self.assertEqual(planned['estimate'],39456)
        self.assertEqual(len(a.encode(planned['body'])),38432)
        fixture=a.read(a.FROZEN.parent/'protocol/wi70-offline-request.fixture.json')
        self.assertEqual(planned['body'],fixture)
    def test_one_call_and_no_resume(self):
        run,calls,raw,result=self.run_case()
        self.assertEqual(len(calls),1); self.assertEqual((run/'response.body').read_bytes(),raw)
        self.assertTrue(result['structural_validation']['structural_valid'])
        self.assertEqual(result['semantic_status'],'unverified'); self.assertEqual(result['independent_audit_agreement'],'unverified')
        self.assertEqual(result['model_completeness_label'],'uncertain'); self.assertFalse(result['production_eligible'])
        with self.assertRaises(FileExistsError): a.execute_once(run,self.planned,self.request,self.response,'synthetic-secret-key',lambda *args: self.fail('second POST'))
    def test_transport_uncertainty_latched(self):
        def fail(*args): raise RuntimeError('synthetic-secret-key must never log')
        run,_,_,result=self.run_case(transport=fail)
        self.assertIsNone(result); self.assertTrue((run/'intent.json').exists()); self.assertFalse((run/'response.body').exists())
        self.assertFalse(a.read(run/'stop.json')['automatic_retry'])
        with self.assertRaises(FileExistsError): a.execute_once(run,self.planned,self.request,self.response,'synthetic-secret-key',lambda *args:self.fail('retry'))
        for p in run.iterdir(): self.assertNotIn(b'synthetic-secret-key',p.read_bytes())
    def test_http_error_preserves_raw_and_cost(self):
        obj=self.native(); obj['usage']['cost']=.3
        run,calls,raw,result=self.run_case(obj,429)
        self.assertIsNone(result); self.assertEqual(len(calls),1); self.assertEqual((run/'response.body').read_bytes(),raw)
        self.assertEqual(a.read(run/'stop.json')['new_budget_charge_nanousd'],300000000)
    def test_invalid_envelopes_preserve_raw(self):
        for kind in ('cost','model','provider','finish','refusal','tool','choices','tokens'):
            obj=self.native()
            if kind=='cost': del obj['usage']['cost']
            elif kind=='model': obj['model']='different'
            elif kind=='provider': obj['provider']='different'
            elif kind=='finish': obj['choices'][0]['finish_reason']='length'
            elif kind=='refusal': obj['choices'][0]['message']['refusal']='yes'
            elif kind=='tool': obj['choices'][0]['message']['tool_calls']=[{}]
            elif kind=='choices': obj['choices']*=2
            else: obj['usage']['prompt_tokens']=True
            with self.subTest(kind=kind):
                run,calls,raw,result=self.run_case(obj)
                self.assertIsNone(result); self.assertEqual(len(calls),1); self.assertEqual((run/'response.body').read_bytes(),raw)
                self.assertTrue((run/'stop.json').exists()); self.assertFalse((run/'completed.json').exists())
    def test_secret_echo_not_retained(self):
        obj=self.native('synthetic-secret-key'); run,calls,_,result=self.run_case(obj)
        self.assertIsNone(result); self.assertEqual(len(calls),1); self.assertFalse((run/'response.body').exists())
        for p in run.iterdir(): self.assertNotIn(b'synthetic-secret-key',p.read_bytes())
    def test_structurally_invalid_is_reported_separately(self):
        obj=self.native('{}'); run,calls,raw,result=self.run_case(obj)
        self.assertFalse(result['structural_validation']['structural_valid']); self.assertEqual(result['semantic_status'],'unverified')
        self.assertTrue((run/'completed.json').exists()); self.assertEqual(len(calls),1)
    def test_duplicate_and_nonfinite_rejected(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":1e999}',b'{"a":NaN}'):
            with self.assertRaises(a.Denied): a.strict(raw)
        obj=self.native(); obj['choices'][0]['message']['content']='{"a":1,"a":2}'
        run,calls,raw,result=self.run_case(obj); self.assertIsNone(result); self.assertEqual((run/'response.body').read_bytes(),raw)
    def test_budget_overrun_retains_paid_result_then_stops(self):
        obj=self.native(); obj['usage']['cost']=1.5
        run,calls,raw,result=self.run_case(obj)
        self.assertIsNone(result); self.assertEqual(len(calls),1); self.assertTrue((run/'result.json').exists()); self.assertFalse((run/'completed.json').exists())
        self.assertEqual(a.read(run/'stop.json')['budget_charge_nanousd'],2196390718)
    def test_missing_release_denies_before_key_or_post(self):
        with patch.object(a,'post_once',side_effect=AssertionError('POST')):
            with self.assertRaises((FileNotFoundError,a.Denied)): a.live_initial()
    def test_estimate_dominates_reported_in_success_and_failure(self):
        obj=self.native(); obj['usage'].update(prompt_tokens=200000,completion_tokens=100,cost=.001)
        run,calls,raw,result=self.run_case(obj)
        self.assertEqual(result['new_budget_charge_nanousd'],401000000)
        del obj['usage']['cost']
        run,calls,raw,result=self.run_case(obj)
        self.assertIsNone(result); self.assertEqual(a.read(run/'stop.json')['new_budget_charge_nanousd'],401000000)
    def test_unsigned_proposal_matches_installed_core_validator(self):
        prep=a.module('offline_preparation',HERE/'prepare_bindings.py')
        release_path=HERE.parents[4]/'tools/research-credentials-stable/release.py'
        release=a.module('offline_release_validation',release_path)
        core=a.read(a.BENCH/'runner-stability-review/deployment/core.json')
        captured={}; original=prep.digest
        def capture(path,value): captured[str(path)]=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
        def digest(path): return a.sha(captured[str(path)]) if str(path) in captured else original(Path(path))
        with patch.object(prep,'put',capture),patch.object(prep,'digest',digest),patch.object(release,'digest',digest),patch.object(release,'read_key',side_effect=AssertionError('signing forbidden')),patch.object(release,'publish',side_effect=AssertionError('publication forbidden')):
            prep.prepare('synthetic-offline-scope',int(prep.time.time())+3600,HERE/'README.md')
            proposal=json.loads(captured[str(HERE/'UNSIGNED-JOB-PROPOSAL.json')])
            release.validate(core,proposal)
        self.assertEqual(proposal['budget'],dict(prior_nanousd=696390718,reservation_nanousd=161920000,ceiling_nanousd=2000000000))
        self.assertEqual(proposal['provider_variables'],['OPENROUTER_API_KEY'])
    def test_rounding_and_caps(self):
        self.assertEqual(a.cost_nano(.0000000001),1)
        for value in (-1,float('nan'),True,None):
            with self.assertRaises(a.Denied): a.cost_nano(value)
        self.assertEqual(a.PRIOR_NANO+a.RESERVE_NANO,858310718)
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('offline network forbidden')): unittest.main(verbosity=2)
