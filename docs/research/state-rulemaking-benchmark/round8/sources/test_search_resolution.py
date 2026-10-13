"""Offline one-shot query lifecycle controls. No source access."""
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
class SearchResolutionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'sources';shutil.copytree(SOURCE,self.root)
  spec=importlib.util.spec_from_file_location('test_collector',self.root/'collect-native.py');self.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.c);self.c.gate=lambda:None
 def tearDown(self):self.tmp.cleanup()
 def record(self,raw,count=0,results=None):
  p=self.root/'response.json';p.write_text(json.dumps({'submitted_query':self.c.query('Q01')['query'],'raw_tool_result':raw,'executed_at_utc':'offline synthetic','returned_result_count':count,'results':results or []}));return p
 def test_empty_response_advances_after_consumed_intent(self):
  self.c.request('Q01');self.c.register('Q01',self.record('No search results found.'))
  self.assertEqual(self.c.query_events('Q01')[-1]['bounded_candidates'],[])
  self.assertEqual(self.c.query_events('Q01')[-1]['search_disposition'],'recognized_zero_results')
  self.assertEqual(self.c.request('Q02')['query_id'],'Q02')
 def test_one_shot_request_and_unrequested_registration(self):
  with self.assertRaises(AssertionError):self.c.register('Q01',self.record('No search results found.'))
  self.c.request('Q01');self.assertEqual(self.c.events()[0]['event'],'query_invocation_intent')
  with self.assertRaises(AssertionError):self.c.request('Q01')
  with self.assertRaises(AssertionError):self.c.request('Q02')
 def test_unknown_preserved_held_and_primary_hash_bound_resolution(self):
  self.c.request('Q01');p=self.record('Unknown or interrupted search response')
  with self.assertRaises(AssertionError):self.c.register('Q01',p)
  retained=self.root/'search-results/Q01.json';self.assertEqual(retained.read_bytes(),p.read_bytes())
  with self.assertRaises(AssertionError):self.c.request('Q01')
  with self.assertRaises(AssertionError):self.c.request('Q02')
  receipt=self.root/'primary-resolution.json';r={'authorized_resolution':True,'primary_review_message':'Offline synthetic primary resolution; no real authorization.','timestamp_utc':'offline synthetic','query_id':'Q01','retained_search_record_sha256':'0'*64,'decision':'failed_or_unavailable_no_candidates','raw_response_interpretation':'No ordered results available; query consumed; never rerun.'};receipt.write_text(json.dumps(r))
  with self.assertRaises(AssertionError):self.c.resolve_search('Q01',receipt)
  r['retained_search_record_sha256']=self.c.sha(retained);receipt.write_text(json.dumps(r));self.c.resolve_search('Q01',receipt)
  self.assertEqual(self.c.request('Q02')['query_id'],'Q02')
  with self.assertRaises(AssertionError):self.c.resolve_search('Q01',receipt)
 def test_unknown_cannot_be_overwritten_by_fake_empty(self):
  self.c.request('Q01');p=self.record('Unknown response')
  with self.assertRaises(AssertionError):self.c.register('Q01',p)
  p=self.record('No search results found.')
  with self.assertRaises(AssertionError):self.c.register('Q01',p)
  self.assertIn('Unknown response',(self.root/'search-results/Q01.json').read_text())
 def test_recognized_results_and_primary_unknown_ordered_resolution(self):
  self.c.request('Q01');row={'display_order':1,'title':'Synthetic notice','url':'https://mn.gov/synthetic.pdf','direct_pdf_candidate':True,'pdf_candidate_basis':'offline extension'}
  self.c.register('Q01',self.record('Synthetic notice (https://mn.gov/synthetic.pdf)\n\ue200cite\ue202synthetic\ue201',1,[row]))
  self.assertEqual(self.c.query_events('Q01')[-1]['bounded_candidates'][0]['candidate_order'],1)
  with self.assertRaises(AssertionError):self.c.request('Q02')
  self.c.exclude('Q01',1,'offline synthetic resolution, no acquisition')
  self.c.request('Q02')
 def test_raw_metadata_mismatch_is_retained_and_held(self):
  self.c.request('Q01');p=self.record('Synthetic notice (https://mn.gov/synthetic.pdf)\n\ue200cite\ue202synthetic\ue201')
  with self.assertRaises(AssertionError):self.c.register('Q01',p)
  self.assertTrue((self.root/'search-results/Q01.json').exists())
  self.assertFalse(any(e['event']=='query_registered' for e in self.c.events()))
 def test_failed_search_cannot_register_as_empty_without_primary_review(self):
  self.c.request('Q01');p=self.record('No search results found.');record=json.loads(p.read_text());record['response_status']='failed';record['search_error']='offline synthetic failure';p.write_text(json.dumps(record))
  with self.assertRaises(AssertionError):self.c.register('Q01',p)
  self.assertFalse(any(e['event']=='query_registered' for e in self.c.events()))
 def test_primary_review_can_resolve_exact_unknown_ordered_response(self):
  self.c.request('Q01');p=self.record('Unknown raw layout with a synthetic notice URL https://mn.gov/synthetic.pdf')
  with self.assertRaises(AssertionError):self.c.register('Q01',p)
  retained=self.root/'search-results/Q01.json';receipt=self.root/'primary-resolution.json';row={'display_order':1,'title':'Synthetic notice','url':'https://mn.gov/synthetic.pdf','direct_pdf_candidate':True,'pdf_candidate_basis':'offline extension'}
  receipt.write_text(json.dumps({'authorized_resolution':True,'primary_review_message':'Offline synthetic only.','timestamp_utc':'offline synthetic','query_id':'Q01','retained_search_record_sha256':self.c.sha(retained),'decision':'reviewed_ordered_results','raw_response_interpretation':'Offline review explicitly recovers the single ordered result.','reviewed_result_count':1,'reviewed_results':[row]}));self.c.resolve_search('Q01',receipt)
  self.assertEqual(self.c.query_events('Q01')[-1]['bounded_candidates'][0]['url'],row['url'])
if __name__=='__main__':unittest.main()
