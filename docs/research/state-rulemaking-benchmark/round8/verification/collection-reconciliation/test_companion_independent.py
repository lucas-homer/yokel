"""Independent bounded companion controls, with no network/acquisition."""
import copy,importlib.util,json,shutil,sys,tempfile,unittest
from pathlib import Path
V=Path(__file__).resolve().parent;S=V.parents[1]/'sources';C=S/'reconciliation'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class IndependentCompanion(unittest.TestCase):
    def setUp(self):self.c=load('independent_companion',C/'companion.py')
    def test_real_bounds_collision_and_pending_without_amendment(self):
        c=self.c;view=c.replay();by={(x['query_id'],x['display_order']):x for x in view['decisions']}
        self.assertEqual(view['pending_candidate']['query_id'],'Q05');self.assertEqual(view['pending_candidate']['display_order'],2)
        self.assertEqual([x['state'] for x in view['selected']],['Wisconsin','Illinois'])
        self.assertEqual(by['Q03',5]['candidate_order'],2);self.assertIsNone(by['Q03',5]['physical_observation'])
        self.assertEqual(by['Q03',6]['candidate_order'],3);self.assertIsNotNone(by['Q03',6]['physical_observation'])
        self.assertEqual([(x['query_id'],x['display_order']) for x in view['out_of_corrected_bound_observations']],[('Q03',13)])
        with self.assertRaises(FileNotFoundError):c.acquire('Q05',1)
        with self.assertRaises(FileNotFoundError):c.request('Q15')
    def test_source_first_MA_quota_cases(self):
        c=self.c;bounded=c.bounds();original=c.observations()
        for stratum,pages,expected in [('general_comment',28,['Wisconsin','Illinois','Massachusetts','Kentucky']),('general_comment',29,['Wisconsin','Illinois','Massachusetts']),('conditional_control',1,['Wisconsin','Illinois','Massachusetts'])]:
            with self.subTest(stratum=stratum,pages=pages):
                obs=copy.deepcopy(original);candidate=bounded['Q05'][0]
                obs[c.key('Q05',candidate)]={'eligible':True,'document_id':'doc-abcdef123456','state':'Massachusetts','stratum':stratum,'pdf_pages':pages,'artifact_folder':'reconciliation/documents/doc-abcdef123456','physical_event':{'path':'authored synthetic','line':1},'original_status':'candidate_retained'}
                view=c.replay(obs,bounded);self.assertEqual([x['state'] for x in view['selected']],expected)
                self.assertIsNone(view['pending_candidate']);self.assertFalse(view['physical_access_order_restored']);self.assertEqual(view['cohort_classification'],'protocol-deviation corrected')
                self.assertTrue(all(x['logical_status']=='excluded' for x in view['decisions'] if x['query_id']=='Q14'))
                ky=next(x for x in view['decisions'] if x['query_id']=='Q07' and x['display_order']==bounded['Q07'][2]['display_order'])
                self.assertEqual(ky['physical_observation']['original_status'],'candidate_retained')
    def isolated(self):
        c=self.c;tmp=tempfile.TemporaryDirectory(prefix='independent-companion-');target=Path(tmp.name)/'reconciliation';shutil.copytree(C,target)
        c.ROOT=target;c.gate=lambda operation='catchup':None;c.install_adapter();c.frozen.previous_queries_complete=lambda q:None
        q=c.frozen.query('Q15');c.append(target/'access-ledger.jsonl',{'event':'query_invocation_intent','query_id':'Q15','submitted_query':q['query']})
        return tmp,c,target,q
    def test_repeat_converter_failure_retains_raw_and_hash_bound_hold(self):
        tmp,c,target,q=self.isolated()
        try:
            record={'submitted_query':q['query'],'raw_tool_result':'Independent PDF (https://georgia.gov/notice.pdf)\ncite synthetic','executed_at_utc':'synthetic','returned_result_count':1,'results':[{'display_order':1,'title':'Independent PDF','url':'https://georgia.gov/notice.pdf','direct_pdf_candidate':False,'pdf_candidate_basis':None,'source_route_review':{'classification':'not_direct_document','reviewed_from_saved_metadata':True,'basis':'wrong synthetic converter result'}}]}
            p=target/'response.json';p.write_text(json.dumps(record,indent=1))
            with self.assertRaises(AssertionError):c.register('Q15',p)
            retained=target/'search-results/Q15.json';self.assertEqual(retained.read_bytes(),p.read_bytes())
            held=[x for x in c.access_events() if x['event']=='query_response_held'];self.assertTrue(held);self.assertEqual(held[-1]['search_record_sha256'],c.sha(retained))
            self.assertFalse(any(x['event']=='query_registered' for x in c.access_events()))
            with self.assertRaises(AssertionError):c.request('Q15')
            record['results'][0]['direct_pdf_candidate']=True;p.write_text(json.dumps(record))
            with self.assertRaises(AssertionError):c.register('Q15',p)
            self.assertNotEqual(retained.read_bytes(),p.read_bytes())
        finally:tmp.cleanup()
    def test_all_row_review_does_not_reduce_original_document_criterion_to_regex(self):
        tmp,c,target,q=self.isolated()
        try:
            row={'display_order':1,'title':'Individual file','url':'https://georgia.gov/retrieve-notice?document=73','direct_pdf_candidate':True,'pdf_candidate_basis':'authored saved-result evidence of direct retrieval','source_route_review':{'classification':'direct_document','basis':'authored direct route evidence','reviewed_from_saved_metadata':True}}
            self.assertIsNone(c.direct_basis(row))
            record={'submitted_query':q['query'],'raw_tool_result':'Individual file (https://georgia.gov/retrieve-notice?document=73)\ncite synthetic','executed_at_utc':'synthetic','returned_result_count':1,'results':[row]}
            p=target/'response.json';p.write_text(json.dumps(record));c.register('Q15',p)
            registered=[x for x in c.access_events() if x['event']=='query_registered'];self.assertEqual(registered[0]['bounded_candidates'][0]['url'],row['url'])
        finally:tmp.cleanup()
    def test_manifest_preserves_exact_cohort_and_source_root_resolution(self):
        c=self.c;prior=sys.modules.get('companion');sys.modules['companion']=c
        try:m=load('independent_export',C/'export_bundle.py')
        finally:
            if prior is None:sys.modules.pop('companion',None)
            else:sys.modules['companion']=prior
        view=c.replay();manifest=m.manifest_for(view)
        self.assertEqual([x['document_id'] for x in manifest['documents']],[x['document_id'] for x in view['selected']])
        expected={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
        for row in manifest['documents']:
            self.assertEqual(set(row),expected)
            self.assertEqual(c.sha(S/row['text_path']),row['text_sha256']);self.assertEqual(c.sha(S/row['pdf_path']),row['pdf_sha256'])
        self.assertFalse((S/'source-inputs.READY.json').exists(),'Top-level promotion must occur only after final source freeze, not during held preparation')
    def test_frozen_503_sources_and_69_implementation_pins(self):
        baseline=self.c.verify_baseline();self.assertEqual(len(baseline['source_files']),503);self.assertEqual(len(baseline['freeze_A_files']),69)
if __name__=='__main__':
    def guard(event,args):
        if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('Independent offline guard')
        if event=='open' and isinstance(args[0],(str,bytes)) and any(s in str(args[0]).lower() for s in ('/.env','/library/keychains/','/.aws/')):raise RuntimeError('Credentials forbidden')
    sys.addaudithook(guard)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentCompanion))
    (V/'companion-test-results.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':[(str(t),failure) for t,failure in result.errors+result.failures],'provider_calls':0,'fresh_access':0},indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
