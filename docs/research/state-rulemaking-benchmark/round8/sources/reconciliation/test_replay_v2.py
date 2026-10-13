"""Focused offline control for historical versus newly observed aggregate exclusions."""
import hashlib,importlib.util,json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('c2',R/'companion_v2.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class ReplayV2Tests(unittest.TestCase):
 def test_historical_review_hold_and_new_definitive_exclusion(self):
  obs=c.observations();first=c.bounds()['Q01'][0];k=c.key('Q01',first)
  historical={**obs[k],'reasons':['would exceed retained aggregate page cap']}
  self.assertEqual(historical['physical_event']['path'],'search-access-ledger.jsonl')
  self.assertEqual(c.replay(obs={**obs,k:historical})['pending_candidate'],c.identity('Q01',first))
  view=c.replay();self.assertEqual(view['pending_candidate'],c.identity('Q21',c.bounds()['Q21'][2]))
  decisions=[d for d in view['decisions'] if d['query_id']=='Q21' and d['candidate_order']==2];self.assertEqual(len(decisions),1)
  d=decisions[0];self.assertEqual(d['logical_status'],'excluded');self.assertEqual(d['logical_reasons'],['would exceed retained aggregate page cap']);self.assertEqual(d['physical_observation']['physical_event']['path'],'reconciliation/access-ledger.jsonl')
  self.assertEqual([x['document_id'] for x in view['selected']],['doc-92211b8c7ba0','doc-adb9fda35b7c','doc-429465fb3aaa','doc-51759f30a419','doc-68b823216790'])
  self.assertEqual(sum(x['pdf_pages'] for x in view['selected']),17)
  with self.assertRaises(AssertionError):c.current('Q21',2)
  self.assertEqual(len(c.verify_baseline()['source_files']),503)
  pins=json.loads((R/'v1-sealed-pins.json').read_text())['files']
  for x in pins:self.assertEqual(c.sha(R/x['path']),x['sha256'],x['path'])
if __name__=='__main__':
 def guard(event,args):
  if event.startswith(('socket.','subprocess.')) or event in ['os.system','os.posix_spawn']:raise RuntimeError('Offline regression prohibits source access/native processes')
 sys.addaudithook(guard);unittest.main()
