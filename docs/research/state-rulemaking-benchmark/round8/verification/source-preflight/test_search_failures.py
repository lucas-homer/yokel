"""Independent empty/failed-search audit controls; no actual search or network."""
import contextlib,importlib.util,io,json,shutil,sys,tempfile,unittest
from pathlib import Path
S=Path(__file__).resolve().parents[2]/'sources'
class SearchFailureControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='r8-search-failure-')
        target=Path(self.tmp.name)/'sources';shutil.copytree(S,target)
        spec=importlib.util.spec_from_file_location('preflight_search',target/'collect-native.py');self.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.c);self.c.gate=lambda:None
        self.root=target
    def tearDown(self):self.tmp.cleanup()
    def test_explicit_complete_zero_result_registration_advances_without_requery(self):
        c=self.c;c.request('Q01')
        record={'submitted_query':c.query('Q01')['query'],'raw_tool_result':'No search results found.','executed_at_utc':'synthetic','returned_result_count':0,'results':[]}
        path=self.root/'empty.json';path.write_text(json.dumps(record))
        c.register('Q01',path)
        self.assertEqual(c.events()[-1]['bounded_candidates'],[])
        self.assertEqual(c.request('Q02')['query_id'],'Q02')
    def test_query_request_persists_one_shot_intent_before_external_search(self):
        c=self.c;c.request('Q01')
        # A query invocation which fails before registration still consumes its
        # single permitted search. Reissuing request must fail pending resolution.
        with self.assertRaises((AssertionError,ValueError)):c.request('Q01')
    def test_unknown_raw_response_must_hold_without_registration(self):
        c=self.c;c.request('Q01')
        record={'submitted_query':c.query('Q01')['query'],'raw_tool_result':'unknown response format','executed_at_utc':'synthetic','returned_result_count':0,'results':[]}
        path=self.root/'unknown.json';path.write_text(json.dumps(record))
        with self.assertRaises(AssertionError):c.register('Q01',path)
        self.assertFalse(any(x['event']=='query_registered' for x in c.events()))
        self.assertEqual((self.root/'search-results/Q01.json').read_bytes(),path.read_bytes())
        with self.assertRaises(AssertionError):c.request('Q01')
        with self.assertRaises(AssertionError):c.request('Q02')
if __name__=='__main__':
    def guard(event,args):
        if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('Offline only')
    sys.addaudithook(guard)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SearchFailureControls))
    Path(__file__).with_name('search-failure-results.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':[(str(t),trace) for t,trace in result.failures+result.errors],'provider_calls':0,'network_calls':0},indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
