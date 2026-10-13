"""Bounded offline reconciliation controls; no fresh sources or native subprocesses."""
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class CompanionTests(unittest.TestCase):
 def setUp(self):
  spec=importlib.util.spec_from_file_location('companion_test',ROOT/'companion.py');self.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.c)
 def ma(self,stratum=None,pages=1):
  c=self.c;obs=c.observations();cs=c.bounds()['Q05']
  for candidate in cs:obs[c.key('Q05',candidate)]={'eligible':False,'reasons':['offline source scope exclusion'],'physical_event':{'path':'synthetic only','line':1},'original_status':'candidate_excluded'}
  if stratum:
   obs[c.key('Q05',cs[0])]={'eligible':True,'document_id':'doc-'+'a'*12,'state':'Massachusetts','stratum':stratum,'pdf_pages':pages,'artifact_folder':'reconciliation/documents/offline-synthetic','physical_event':{'path':'synthetic only','line':1},'original_status':'candidate_retained'}
   if pages<=37:
    for candidate in cs[1:]:obs.pop(c.key('Q05',candidate))
  return c.replay(obs=obs)
 def test_corrected_rank_collision_and_original_byte_reuse(self):
  c=self.c;v=c.replay();d={ (x['query_id'],x['display_order']):x for x in v['decisions']}
  self.assertEqual(v['pending_candidate']['display_order'],2);self.assertEqual(v['pending_candidate']['query_id'],'Q05')
  self.assertEqual(d['Q03',5]['candidate_order'],2);self.assertIsNone(d['Q03',5]['physical_observation']);self.assertIn('one-per-state',str(d['Q03',5]['logical_reasons']))
  self.assertEqual(d['Q03',6]['candidate_order'],3);self.assertEqual(d['Q03',6]['physical_observation']['original_status'],'candidate_excluded')
  self.assertEqual([x['document_id'] for x in v['selected']],['doc-92211b8c7ba0','doc-adb9fda35b7c'])
  self.assertEqual([x['display_order'] for x in v['out_of_corrected_bound_observations']],[13])
 def test_MA_none_general_control_and_page_boundaries(self):
  for stratum,pages,ma_in,ky_in in [(None,1,False,True),('general_comment',1,True,True),('general_comment',28,True,True),('general_comment',29,True,False),('general_comment',37,True,False),('general_comment',38,False,True),('conditional_control',1,True,False),('conditional_control',37,True,False)]:
   with self.subTest(stratum=stratum,pages=pages):
    v=self.ma(stratum,pages);states=[x['state'] for x in v['selected']];self.assertEqual('Massachusetts' in states,ma_in);self.assertEqual('Kentucky' in states,ky_in);self.assertEqual(states[:2],['Wisconsin','Illinois']);self.assertIsNone(v['pending_candidate'])
    self.assertTrue(all(x['logical_status']=='excluded' for x in v['decisions'] if x['query_id']=='Q14'))
 def test_missing_amendment_refuses_all_access_and_future_request(self):
  c=self.c
  with self.assertRaises(FileNotFoundError):c.acquire('Q05',1)
  with self.assertRaises(FileNotFoundError):c.request('Q15')
  with self.assertRaises(AssertionError):c.acquire('Q03',2)
 def test_export_manifest_equals_logical_cohort_and_uses_source_root_paths(self):
  c=self.c;spec=importlib.util.spec_from_file_location('export_test',ROOT/'export_bundle.py');m=importlib.util.module_from_spec(spec)
  import sys;sys.modules['companion']=c;spec.loader.exec_module(m)
  view=c.replay();manifest=m.manifest_for(view)
  self.assertEqual([x['document_id'] for x in manifest['documents']],[x['document_id'] for x in view['selected']])
  self.assertNotIn('doc-51759f30a419',[x['document_id'] for x in manifest['documents']]);self.assertEqual(len(manifest['documents']),2)
  self.assertEqual(set(manifest['documents'][0]),{'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'})
  for row in manifest['documents']:self.assertTrue((c.SOURCES/row['text_path']).is_file())
 def isolated_registration(self):
  c=self.c;tmp=tempfile.TemporaryDirectory();target=Path(tmp.name)/'reconciliation';shutil.copytree(ROOT,target);c.ROOT=target;c.gate=lambda operation='catchup':None;c.install_adapter();c.frozen.previous_queries_complete=lambda q:None
  query=c.frozen.query('Q15');c.append(target/'access-ledger.jsonl',{'event':'query_invocation_intent','query_id':'Q15','submitted_query':query['query']})
  return c,tmp,target,query
 def test_future_bad_metadata_is_preserved_held_without_rerun(self):
  c,tmp,target,q=self.isolated_registration()
  try:
   row={'display_order':1,'title':'Synthetic document','url':'https://georgia.gov/synthetic.pdf','direct_pdf_candidate':False,'pdf_candidate_basis':None}
   record={'submitted_query':q['query'],'raw_tool_result':'Synthetic document (https://georgia.gov/synthetic.pdf)\n\ue200cite\ue202synthetic\ue201','executed_at_utc':'offline','returned_result_count':1,'results':[row]};p=target/'bad.json';p.write_text(json.dumps(record))
   with self.assertRaises(AssertionError):c.register('Q15',p)
   retained=target/'search-results/Q15.json';self.assertEqual(retained.read_bytes(),p.read_bytes());events=c.access_events();self.assertTrue(any(x['event']=='query_response_held' and x['search_record_sha256']==c.sha(retained) for x in events));self.assertFalse(any(x['event']=='query_registered' for x in events))
   with self.assertRaises(AssertionError):c.request('Q15')
  finally:tmp.cleanup()
 def test_future_manual_document_basis_outside_known_patterns(self):
  c,tmp,target,q=self.isolated_registration()
  try:
   row={'display_order':1,'title':'Synthetic individual notice','url':'https://georgia.gov/individual-notice-fetch?id=7','direct_pdf_candidate':True,'pdf_candidate_basis':'offline synthetic evidence of individual publisher retrieval endpoint','source_route_review':{'classification':'direct_document','basis':'offline synthetic title/URL/metadata review, not real source evidence','reviewed_from_saved_metadata':True}}
   self.assertIsNone(c.direct_basis(row));record={'submitted_query':q['query'],'raw_tool_result':'Synthetic individual notice (https://georgia.gov/individual-notice-fetch?id=7)\n\ue200cite\ue202synthetic\ue201','executed_at_utc':'offline','returned_result_count':1,'results':[row]};p=target/'manual.json';p.write_text(json.dumps(record));c.register('Q15',p)
   registered=next(x for x in c.access_events() if x['event']=='query_registered');self.assertEqual(registered['bounded_candidates'][0]['url'],row['url'])
  finally:tmp.cleanup()
 def test_original503_and_freeze69_bytes_unchanged(self):self.assertEqual(len(self.c.verify_baseline()['source_files']),503)
if __name__=='__main__':
 import sys
 def guard(event,args):
  if event.startswith(('socket.','subprocess.')) or event in ['os.system','os.posix_spawn']:raise RuntimeError('Offline controls prohibit network/native process dispatch')
 sys.addaudithook(guard);unittest.main()
