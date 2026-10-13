"""Independent offline entrypoint controls; never modify pipeline/runtime or call providers."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'pipeline'))
import pipeline as p
from development_fixtures import empty_inventory,event,route,evidence,timing,requirement
from test_evaluate import fixture,omit
from evaluate import evaluate,CATEGORIES

def built(text='Comments must include docket ABC and PDF format.'):
 s=p.make_source(text,'dev');i=empty_inventory(s);i['coverage']['status']='claimed_complete';return s,i

def favorable(s,a):
 ev=evidence(s['source_text'])
 return dict(schema_version='round6.record_verdict.v1',document_id=s['document_id'],payload_sha256=p.verification_payload(s,a)['payload_sha256'],completeness=dict(label='complete',reason='synthetic favorable claim',evidence=ev),source_identity=dict(label='resolved',reason='synthetic favorable claim',evidence=ev),assessments=[dict(item_id=i['id'],support='supported',association='matched',requirements='preserved',reason='synthetic favorable claim',evidence=ev)for _,i in p.all_items(a['record'])],missing_items=[],contradictions=[])

class Review(unittest.TestCase):
 def test_double_omission_favorable_model_does_not_become_gold(self):
  s,i=built();a=p.assemble(s,i);self.assertTrue(a['validation']['valid']);self.assertTrue(p.validate_verdict(s,a,favorable(s,a))['valid'])
  x=fixture()
  for n in x[1]['documents']:
   n['units']=[u for u in n['units']if u['id']in ('reference','pdf')]
   for u in n['units']:u['targets']=['$notice']
   n['domains']={k:'present'if k=='instruction'else'absent'for k in CATEGORIES}
  ih=p.sha(p.canonical(i));rh=p.sha(p.canonical(a['record']));ph=p.verification_payload(s,a)['payload_sha256']
  for au,ob in zip(x[2]['documents'],x[3]['documents']):
   for k,h in [('inventory',ih),('record',rh)]:
    au[k]={'sha256':h,'review_complete':True,'claims':[],'source_matches':[{'source_unit_id':u,'status':'omitted','claim_ids':[],'basis':'fixed synthetic source explicitly requires this; actual pipeline inventory and record contain neither'}for u in ('reference','pdf')]};ob[k+'_sha256']=h
   ob['payload_sha256']=ph
   for arm in ob['arms'].values():arm['payload_sha256']=ph
  r=evaluate(*x)
  self.assertEqual(r['quality']['record']['source_coverage_by_category']['instruction']['numerator'],0)
  self.assertEqual(r['arms']['jev']['unsafe_accepted'],8);self.assertEqual(r['arms']['stronger']['correct_complete_accepted'],0)
 def test_unknown_phase_requires_review(self):
  s,i=built();i['events']=[event('e','unknown',s['source_text'])];a=p.assemble(s,i);self.assertTrue(a['validation']['valid']);self.assertTrue(a['validation']['review_reasons'])
 def test_unknown_route_role_requires_review(self):
  s,i=built('Send to contact@example.gov.');i['routes']=[route('r','contact@example.gov',s['source_text'],[],role='unknown')];a=p.assemble(s,i);self.assertTrue(a['validation']['valid']);self.assertTrue(a['validation']['review_reasons'])
 def test_unknown_route_channel_requires_review(self):
  s,i=built('Send to contact@example.gov.');i['events']=[event('e','written_comment',s['source_text'])];i['routes']=[route('r','contact@example.gov',s['source_text'],['e'])];i['routes'][0]['channel']='unknown';a=p.assemble(s,i);self.assertTrue(a['validation']['valid']);self.assertTrue(a['validation']['review_reasons'])
 def test_conditional_anchor_can_remain_qualified_complete(self):
  s,i=built('Comments close at the end of the hearing.');i['events']=[event('h','hearing','hearing'),event('c','written_comment',s['source_text'],[timing('t','at the end of the hearing',None,'conditional',role='closes',relation='upon',anchors=['h'])])];a=p.assemble(s,i);self.assertTrue(a['validation']['valid']);self.assertEqual(a['validation']['review_reasons'],[]);self.assertTrue(p.validate_verdict(s,a,favorable(s,a))['valid']);self.assertFalse(a['action_ready'])
 def test_identity_uncertainty_not_removed_by_favorable_verifier(self):
  s,i=built('Docket ABC. Footer XYZ.');i['identities']=[dict(id='x',kind='docket',literal='ABC',relation='unresolved',event_ids=[],evidence=evidence('Docket ABC.'))];a=p.assemble(s,i);self.assertIn('source_identity_unresolved',a['validation']['review_reasons']);p.validate_verdict(s,a,favorable(s,a));self.assertIn('source_identity_unresolved',a['validation']['review_reasons'])
 def test_exact_quote_newline_unicode_and_ambiguous_occurrence(self):
  self.assertEqual(p.resolve_evidence('🙂é first\nitem second item',evidence('first\nitem')[0])['start'],3)
  with self.assertRaises(ValueError):p.resolve_evidence('first\nitem',evidence('first item')[0])
  with self.assertRaises(ValueError):p.resolve_evidence('item then item',evidence('item')[0])
 def test_source_and_verdict_hash_drift_rejected(self):
  s,i=built();a=p.assemble(s,i);v=favorable(s,a);v['payload_sha256']='f'*64;self.assertFalse(p.validate_verdict(s,a,v)['valid']);bad=copy.deepcopy(s);bad['source_text']+=' changed'
  with self.assertRaises(ValueError):p.verification_payload(bad,a)
if __name__=='__main__':unittest.main(verbosity=2)
