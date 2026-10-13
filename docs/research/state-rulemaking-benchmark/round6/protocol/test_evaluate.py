import copy
import unittest
from evaluate import evaluate,CATEGORIES
H='a'*64;I='b'*64;R='c'*64;P='d'*64

def unit(id,category,subtype,targets=None,modality='not_applicable'):
 return {'id':id,'category':category,'subtype':subtype,'description':id,'raw_value':id,'modality':modality,'targets':targets or ['$notice'],'evidence':[{'page':1,'region':'synthetic','quote':id}]}
def fixture():
 schedule={'schema_version':'round6.schedule.v1','documents':[]};truth={'schema_version':'round6.truth.v1','documents':[]};audit={'schema_version':'round6.matching-audit.v1','reviewer':'independent synthetic reviewer','documents':[]};observed={'schema_version':'round6.observed.v1','documents':[],'costs':{k:{'usage_estimate_usd':v,'conservative_charge_usd':v*2,'provider_reported_usd':None}for k,v in [('extraction',.2),('jev',.1),('stronger',.4)]}}
 for i in range(8):
  id='doc-'+format(i,'012x');schedule['documents'].append({'document_id':id,'pdf_sha256':H,'pdf_pages':1,'state':['A','B','C','D','E','F','A','B'][i],'stratum':'general'if i<6 else'control'})
  us=[unit('date','fact','timing_closes'),unit('route','fact','direct_route'),unit('reference','instruction','reference',['route'],'mandatory'),unit('pdf','instruction','format',['route'],'mandatory'),unit('posting','disclosure','public_posting',['route'],'descriptive'),unit('link','relationship','route_event',['date','route']),unit('copies','ancillary','copies_contact')]
  truth['documents'].append({'document_id':id,'pdf_sha256':H,'scope_status':'complete','all_pages_viewed':True,'universe_complete':True,'reviewer':'image reviewer','exclusions':['substantive program text'],'domains':{k:'present'if any(u['category']==k for u in us)else'absent'for k in CATEGORIES},'units':us,'acceptance_blockers':[]})
  claims=[{'id':u['id'],'categories':[u['category']],'status':'correct','literal_kind':'date'if u['id']=='date'else'email'if u['id']=='route'else'none','literal_status':'correct'if u['id']in ('date','route')else'not_applicable','evidence_status':'matched','basis':'independent source comparison'}for u in us]
  matches=[{'source_unit_id':u['id'],'status':'matched','claim_ids':[u['id']],'basis':'independent semantic comparison'}for u in us]
  a={'review_complete':True,'claims':claims,'source_matches':matches};audit['documents'].append({'document_id':id,'inventory':{'sha256':I,**copy.deepcopy(a)},'record':{'sha256':R,**copy.deepcopy(a)}})
  observed['documents'].append({'document_id':id,'inventory_sha256':I,'record_sha256':R,'payload_sha256':P,'arms':{k:{'status':'accepted_complete','payload_sha256':P,'source_coverage_complete':True}for k in ('jev','stronger')}})
 return schedule,truth,audit,observed

def omit(assessment,*ids):
 assessment['claims']=[c for c in assessment['claims']if c['id']not in ids]
 for m in assessment['source_matches']:
  if m['source_unit_id']in ids:m.update(status='omitted',claim_ids=[])

class Tests(unittest.TestCase):
 def test_positive_both_gates_and_pairing(self):
  r=evaluate(*fixture());self.assertTrue(r['arms']['jev']['gate_passed']);self.assertEqual(r['arms']['stronger']['correct_complete_accepted'],8);self.assertEqual(r['paired_notice_outcomes'][0]['count'],8)
 def test_reference_omission_leaves_date_literal_correct(self):
  x=fixture();omit(x[2]['documents'][0]['record'],'reference');r=evaluate(*x);self.assertEqual(r['quality']['record']['literal_accuracy']['date']['value'],1);self.assertEqual(r['arms']['jev']['unsafe_accepted'],1);self.assertFalse(r['arms']['jev']['gate_passed'])
 def test_double_omission_independent_truth_detects_both(self):
  x=fixture()
  for k in ('inventory','record'):omit(x[2]['documents'][0][k],'reference','pdf')
  r=evaluate(*x);self.assertEqual(r['quality']['inventory']['source_coverage_by_category']['instruction']['numerator'],14);self.assertEqual(r['arms']['stronger']['unsafe_accepted'],1)
 def test_disclosure_separate_from_instruction(self):
  x=fixture();omit(x[2]['documents'][0]['record'],'posting');r=evaluate(*x);self.assertEqual(r['quality']['record']['source_coverage_by_category']['instruction']['value'],1);self.assertEqual(r['quality']['record']['source_coverage_by_category']['disclosure']['value'],7/8)
 def test_ancillary_count_separate_and_required(self):
  x=fixture();omit(x[2]['documents'][0]['record'],'copies');r=evaluate(*x);self.assertEqual(r['quality']['record']['source_fact_coverage_by_subtype']['direct_route']['value'],1);self.assertEqual(r['arms']['jev']['unsafe_accepted'],1)
 def test_conditional_record_not_automatically_blocked(self):
  x=fixture()
  for n in x[1]['documents']:n['units'][0]['subtype']='hearing_bound_close';n['units'][0]['modality']='conditional'
  r=evaluate(*x);self.assertTrue(r['arms']['jev']['gate_passed'])
 def test_explicit_relative_no_absolute_date_can_pass(self):
  x=fixture()
  for n in x[1]['documents']:n['units'][0].update(subtype='relative_close',raw_value='within30days after publication')
  for a in x[2]['documents']:
   for k in ('inventory','record'):a[k]['claims'][0].update(literal_kind='none',literal_status='not_applicable')
  self.assertTrue(evaluate(*x)['arms']['jev']['gate_passed'])
 def test_source_identity_blocker_is_review_even_if_disclosed(self):
  x=fixture();n=x[1]['documents'][0];n['units'][0]['category']='uncertainty';n['units'][0]['subtype']='identity_conflict';n['domains']['uncertainty']='present';n['acceptance_blockers']=['date']
  for k in ('inventory','record'):x[2]['documents'][0][k]['claims'][0]['categories']=['uncertainty']
  r=evaluate(*x);self.assertEqual(r['quality']['record']['complete_records'],8);self.assertEqual(r['arms']['jev']['unsafe_accepted'],1)
 def test_wrong_role_can_have_correct_literal(self):
  x=fixture();a=x[2]['documents'][0]['record'];a['claims'][0]['status']='incorrect'
  for m in a['source_matches']:
   if m['source_unit_id']in ('date','link'):m['status']='mismatched'
  r=evaluate(*x);self.assertEqual(r['quality']['record']['literal_accuracy']['date']['value'],1);self.assertEqual(r['quality']['record']['incorrect_claims'],1)
 def test_wrong_modality_unsafe(self):
  x=fixture();a=x[2]['documents'][0]['record'];a['claims'][2]['status']='incorrect';a['source_matches'][2]['status']='mismatched';self.assertEqual(evaluate(*x)['arms']['jev']['unsafe_accepted'],1)
 def test_unsupported_extra_not_hidden(self):
  x=fixture();c=copy.deepcopy(x[2]['documents'][0]['record']['claims'][2]);c.update(id='invented',status='incorrect');x[2]['documents'][0]['record']['claims'].append(c);self.assertEqual(evaluate(*x)['arms']['jev']['unsafe_accepted'],1)
 def test_relation_missing_endpoint_rejected(self):
  x=fixture();omit(x[2]['documents'][0]['record'],'route')
  with self.assertRaisesRegex(ValueError,'endpoint'):evaluate(*x)
 def test_source_matches_cannot_shrink_or_duplicate(self):
  for mode in ('missing','duplicate'):
   x=fixture();ms=x[2]['documents'][0]['record']['source_matches'];ms.pop()if mode=='missing'else ms.append(copy.deepcopy(ms[0]))
   with self.assertRaises(ValueError):evaluate(*x)
 def test_pair_payload_drift_rejected(self):
  x=fixture();x[3]['documents'][0]['arms']['stronger']['payload_sha256']='e'*64
  with self.assertRaisesRegex(ValueError,'payload'):evaluate(*x)
 def test_audit_hash_drift_rejected(self):
  x=fixture();x[2]['documents'][0]['record']['sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'hash'):evaluate(*x)
 def test_missing_audit_is_unsafe_not_vacuous_complete(self):
  x=fixture();x[2]['documents'].pop();r=evaluate(*x);self.assertEqual(r['arms']['jev']['unsafe_accepted'],1);self.assertIsNone(r['quality']['record']['literal_accuracy']['date']['value'])
 def test_missing_truth_keeps_schedule_null_rate(self):
  x=fixture();x[1]['documents'].pop();x[2]['documents'].pop();r=evaluate(*x);self.assertEqual(r['scheduled_notices'],8);self.assertIsNone(r['arms']['jev']['useful_coverage']['value']);self.assertFalse(r['arms']['jev']['gate_passed'])
 def test_incomplete_scope_blocks_wholecohort_rate(self):
  x=fixture();x[1]['documents'][0]['scope_status']='uncertain';r=evaluate(*x);self.assertIsNone(r['arms']['jev']['useful_coverage']['value']);self.assertEqual(r['arms']['jev']['unsafe_accepted'],1)
 def test_fully_known_no_accepts_null_safety(self):
  x=fixture()
  for n in x[3]['documents']:
   for arm in n['arms'].values():arm['status']='review'
  r=evaluate(*x);self.assertEqual(r['arms']['jev']['useful_coverage']['value'],0);self.assertIsNone(r['arms']['jev']['unsafe_acceptance_fraction']['value']);self.assertEqual(r['arms']['jev']['review_or_unserved_fraction']['value'],1)
 def test_missing_observation_and_extraction_failure_count(self):
  x=fixture();x[3]['documents'].pop();x[2]['documents'].pop();r=evaluate(*x);self.assertEqual(r['arms']['jev']['status_counts']['not_started'],1);self.assertEqual(r['arms']['jev']['useful_coverage']['denominator'],8)
 def test_asymmetric_service_failure_no_best_of_two(self):
  x=fixture();x[3]['documents'][0]['arms']['stronger'].update(status='failed',failure_reason='HTTP');r=evaluate(*x);self.assertEqual(r['arms']['jev']['correct_complete_accepted'],8);self.assertEqual(r['arms']['stronger']['correct_complete_accepted'],7)
 def test_skipped_coverage_unsafe(self):
  x=fixture();x[3]['documents'][0]['arms']['jev']['source_coverage_complete']=False;r=evaluate(*x);self.assertEqual(r['arms']['jev']['unsafe_accepted'],1);self.assertEqual(r['arms']['stronger']['unsafe_accepted'],0)
 def test_cost_no_half_split_unknown_invoice_null(self):
  r=evaluate(*fixture());self.assertAlmostEqual(r['costs']['experiment_total']['usage_estimate_usd'],.7);self.assertAlmostEqual(r['costs']['jev']['scenario_cost_per_correct_complete_record']['usage_estimate_usd'],.3/8);self.assertIsNone(r['costs']['experiment_total']['provider_reported_usd'])
 def test_unknown_cost_and_zero_correct_null(self):
  x=fixture();x[3]['costs']['extraction']['usage_estimate_usd']=None
  for n in x[3]['documents']:
   for a in n['arms'].values():a['status']='review'
  r=evaluate(*x);self.assertIsNone(r['costs']['experiment_total']['usage_estimate_usd']);self.assertIsNone(r['costs']['jev']['scenario_cost_per_correct_complete_record']['conservative_charge_usd'])
 def test_zero_category_null(self):
  self.assertIsNone(evaluate(*fixture())['quality']['record']['source_coverage_by_category']['identity']['value'])
 def test_invalid_cost_and_boolean_claim_rejected(self):
  x=fixture();x[3]['costs']['jev']['usage_estimate_usd']=True
  with self.assertRaises(ValueError):evaluate(*x)
 def test_cohort_gate_not_just_accuracy(self):
  x=fixture()
  for d in x[0]['documents']:d['state']='A'
  self.assertFalse(evaluate(*x)['arms']['jev']['gate_passed'])
 def test_confirmed_gate_boundary_two_not_one(self):
  for accepted in (1,2):
   x=fixture()
   for n in x[3]['documents'][accepted:]:
    for a in n['arms'].values():a['status']='review'
   r=evaluate(*x);self.assertEqual(r['arms']['jev']['gate_passed'],accepted==2);self.assertEqual(r['arms']['jev']['useful_coverage']['value'],accepted/8)
 def test_wrong_stratum_fails_cohort(self):
  x=fixture();x[0]['documents'][-1]['stratum']='general';self.assertFalse(evaluate(*x)['cohort_adequacy'])
 def test_existing_artifact_incomplete_audit_has_null_exact_coverage(self):
  x=fixture();x[2]['documents'][0]['record']['review_complete']=False;r=evaluate(*x)
  self.assertIsNone(r['quality']['record']['source_coverage_by_category']['fact']['value'])
  self.assertIsNone(r['quality']['record']['source_fact_coverage_by_subtype']['direct_route']['value'])
  self.assertEqual(r['quality']['record']['source_coverage_by_category']['fact']['numerator'],16)
 def test_uncertain_domain_prevents_complete_truth(self):
  x=fixture();x[1]['documents'][0]['domains']['identity']='uncertain';r=evaluate(*x);self.assertFalse(r['source_truth_complete']);self.assertFalse(r['arms']['jev']['gate_passed']);self.assertIsNone(r['arms']['jev']['useful_coverage']['value'])
 def test_relationship_precision_is_separate_from_literal_accuracy(self):
  x=fixture();a=x[2]['documents'][0]['record'];a['claims'][5]['status']='incorrect';a['source_matches'][5]['status']='mismatched';r=evaluate(*x)
  self.assertEqual(r['quality']['record']['claim_precision_by_category']['relationship']['value'],7/8)
  self.assertEqual(r['quality']['record']['source_coverage_by_category']['relationship']['value'],7/8)
  self.assertEqual(r['quality']['record']['literal_accuracy']['date']['value'],1)
if __name__=='__main__':unittest.main(verbosity=2)
