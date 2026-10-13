"""Independent offline controls; authored cases and callback spies, never provider calls."""
import copy,hashlib,importlib.util,io,json,sys,unittest,contextlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'review'
def guard(event,args):
 if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('review disables network/processes')
 if event=='open' and isinstance(args[0],(str,bytes)):
  s=str(args[0]).lower()
  if '/.env' in s or '/library/keychains/' in s or '/.aws/' in s or Path(s).name in ('credentials','credentials.json'):raise RuntimeError('review disables credential files')
sys.addaudithook(guard)
sys.path.insert(0,str(ROOT))
import candidate as c
import fixtures as f
import test_candidate as owner

def timing(i,id='asap'):return next(t for e in i['events'] for t in e['timing'] if t['id']==id)
class Independent(unittest.TestCase):
 def test_frozen_request_plus_exact_append_only(self):
  source,inv=c.observed();old=json.loads((c.BASE/'round8-cap-probe/execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d/request.json').read_bytes());new=c.inventory_body(source);delta=(ROOT/'prompt-delta.txt').read_text();expected=copy.deepcopy(old);expected['messages'][0]['content']+=delta
  self.assertEqual(new,expected);self.assertEqual(new['messages'][1],old['messages'][1]);self.assertEqual(new['response_format'],old['response_format']);self.assertEqual(c.p.INVENTORY_SCHEMA,new['response_format']['json_schema']['schema'])
  self.assertIn('Do not turn it into a calculated date',delta);self.assertIn('Details present only inside evidence quotes do not count as structured assertions',delta)
  self.assertEqual(c.a.LIMITS['inventory_completion'],6144);self.assertEqual(new['max_tokens'],12288)
 def test_unsupported_asap_date_and_dangling_binding_reject(self):
  source,inv=f.accessibility()
  cases=[];bad=copy.deepcopy(inv);timing(bad).update(kind='absolute_date',value='2026-07-12');cases.append(bad)
  bad=copy.deepcopy(inv);timing(bad)['value']='2026-07-12';cases.append(bad)
  bad=copy.deepcopy(inv);timing(bad)['condition_requirement_ids']=['missing'];cases.append(bad)
  bad=copy.deepcopy(inv);timing(bad)['evidence'][0]['quote']='as soon as feasible';cases.append(bad)
  for n,bad in enumerate(cases):
   with self.subTest(case=n):
    before=c.a.encode(bad);out=c.p.assemble(source,bad);self.assertFalse(out['validation']['valid']);self.assertIsNone(out['record']);self.assertEqual(c.a.encode(bad),before)
 def test_supported_accessibility_structure_preserved(self):
  source,inv=f.accessibility();before=c.a.encode(inv);out,bodies=c.paired_bodies(source,inv);record=out['record'];self.assertEqual(c.a.encode(inv),before)
  self.assertEqual(timing(record)['dependency_relation'],'other');self.assertEqual(timing(record)['condition_requirement_ids'],['aid']);self.assertEqual(timing(record)['anchor_event_ids'],[]);self.assertIsNone(timing(record)['value']);self.assertEqual(timing(record)['raw'],'as soon as possible')
  req=next(q for q in record['requirements'] if q['id']=='aid');self.assertEqual(req['modality'],'conditional');self.assertEqual(req['route_ids'],['help']);self.assertEqual(req['event_ids'],['access']);self.assertIn('interpreter',req['text']);self.assertIn('large-print documents',req['text'])
  route=next(q for q in record['routes'] if q['id']=='help');self.assertEqual(route['role'],'information_contact');self.assertEqual(route['event_ids'],['access'])
  for body in bodies.values():self.assertIn('help@example.org',c.a.encode(body).decode())
  self.assertEqual(bodies['jev']['state']['record'],record);self.assertEqual(json.loads(bodies['stronger']['messages'][1]['content'])['payload'],bodies['jev']['state']);self.assertEqual(out['validation']['source_completeness'],'unverified')
 def test_structural_coverage_claim_cannot_prove_semantics(self):
  source,inv=f.accessibility();inv['coverage']['status']='claimed_complete';inv['requirements'][0]['text']='Aids are offered.'
  out=c.p.assemble(source,inv);self.assertTrue(out['validation']['valid']);self.assertFalse(out['action_ready']);self.assertFalse(out['production_eligible']);self.assertEqual(out['validation']['source_completeness'],'unverified');self.assertEqual(out['validation']['source_correctness'],'unverified')
  # Evidence retains aid names, while structured description omits them; unchanged structural code intentionally cannot certify completeness.
  self.assertNotIn('interpreter',out['record']['requirements'][0]['text'])
 def test_unicode_byte_boundary_policy_keeps_bodies(self):
  source,inv=f.accessibility();_,bodies=c.paired_bodies(source,inv)
  for cap in (35000,40000):
   body=copy.deepcopy(bodies['stronger']);body['messages'][0]['content']+='é';missing=cap-c.a.estimate_input(body);self.assertGreater(missing,0);body['messages'][0]['content']+='x'*missing
   raw=c.a.encode(body);self.assertEqual(len(raw)+1024,cap);self.assertGreater(len(raw),len(raw.decode()));self.assertTrue(c.admission(body,'stronger',cap)['admitted']);self.assertEqual(c.a.encode(body),raw)
   body['messages'][0]['content']+='x';self.assertFalse(c.admission(body,'stronger',cap)['admitted'])
  body=copy.deepcopy(bodies['stronger']);body['messages'][0]['content']+='x'*(35001-c.a.estimate_input(body));self.assertFalse(c.admission(body,'stronger',35000)['admitted']);self.assertTrue(c.admission(body,'stronger',40000)['admitted'])
 def test_gate_finishes_both_checks_before_callback(self):
  source,inv=f.accessibility();_,bodies=c.paired_bodies(source,inv);original=c.admission
  for rejected in (None,'jev','stronger'):
   with self.subTest(rejected=rejected):
    events=[];before=c.a.encode(bodies)
    def admission(body,stage,stronger_guard=35000):
     events.append('check:'+stage);receipt=original(body,stage,stronger_guard)
     if stage==rejected:receipt={**receipt,'admitted':False,'reason':'independent denial'}
     return receipt
    def callback(stage,body):
     self.assertEqual(events[:2],['check:jev','check:stronger']);events.append('call:'+stage);body.clear()
    try:c.admission=admission;result=c.paired_gate(bodies,40000,callback)
    finally:c.admission=original
    self.assertEqual(events,['check:jev','check:stronger']+([] if rejected else ['call:jev','call:stronger']));self.assertEqual(c.a.encode(bodies),before)
 def test_prior_budget_is_conservative_sum(self):
  from decimal import Decimal
  old=c.BASE/'round8/execution/run/operations/inventory-82b41c219e64bc9c63a0ed61';new=c.BASE/'round8-cap-probe/execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d';prior=Decimal(0)
  for folder in (old,new):
   intent=json.loads((folder/'intent.json').read_bytes());response=json.loads((folder/'response.body').read_bytes());prior+=max(Decimal(str(intent['reserved_nominal_usd'])),Decimal(str(response['usage']['cost'])))
  self.assertLess(abs(prior-Decimal(str(c.PRIOR_DEBIT))),Decimal('1e-15'));self.assertAlmostEqual(c.budget(40000)['aggregate_nominal_usd'],.578302)
  self.assertFalse(c.budget_admitted(0,1.75));self.assertTrue(c.budget_admitted(0,1.738226));self.assertFalse(c.budget_admitted(0,1.738227))
if __name__=='__main__':
 paths=[ROOT/n for n in ('candidate.py','prompt-delta.txt','fixtures.py','test_candidate.py','input-pins.json')];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};log=io.StringIO();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(owner),unittest.defaultTestLoader.loadTestsFromTestCase(Independent)])
 with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
 after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};(OUT/'independent-test-output.txt').write_text(log.getvalue());report={'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'candidate_unchanged_during_tests':before==after,'reviewed_files':before,'provider_calls':0,'credential_reads':False,'scope':'Synthetic offline controls; no new model output or semantic quality evidence'};(OUT/'independent-test-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='reviewed_files'}))
