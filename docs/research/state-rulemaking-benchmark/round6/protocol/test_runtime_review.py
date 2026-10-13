"""Independent fake-only runtime review; all ledger writes are temporary."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(R/'runtime'))
import run_pipeline as r
import provider_adapters as a
from operations import Ledger,Stop,Pause,put,sha
from pypdf import PdfWriter
from test_pipeline_review import built,favorable,p

class RuntimeReview(unittest.TestCase):
 def test_all_loaded_schemas_are_implementation_pinned(self):
  pins=r.code_pins(R/'pipeline/pipeline.py')
  for name in ('inventory.schema.json','record.schema.json','verdict.schema.json'):
   self.assertIn(str(R/'pipeline'/name),pins['code'])
 def test_approved_caps(self):
  self.assertEqual(a.LIMITS['OR_input_estimate'],35000);self.assertEqual(a.LIMITS['Jev_calls'],8);self.assertAlmostEqual(a.MAX_RESERVATION,1.960704)
 def test_success_replay_never_reposts(self):
  calls=[]
  def transport(*args):calls.append(args);return 200,b'{"cost":0.01}'
  def parse(raw):return {'observed_cost_usd':json.loads(raw)['cost']}
  with tempfile.TemporaryDirectory()as td:
   l=Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport)
   kw={'identity':{'document_id':'dev'},'reserve':.1}
   first=l.operation('x','jev',{'test':1},parse,**kw)
   again=Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport).operation('x','jev',{'test':1},parse,**kw)
   self.assertEqual(first,again);self.assertEqual(len(calls),1)
 def test_retained_intent_reservation_drift_rejected(self):
  def transport(*args):return 200,b'{}'
  def parse(raw):return {'observed_cost_usd':.01}
  with tempfile.TemporaryDirectory()as td:
   l=Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport)
   l.operation('x','jev',{'test':1},parse,identity={'document_id':'dev'},reserve=.1)
   intent=next(Path(td).glob('operations/*/intent.json'));v=json.loads(intent.read_text());v['reserved_nominal_usd']=0;intent.write_text(json.dumps(v))
   with self.assertRaises(Stop):
    Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport).operation('x','jev',{'test':1},parse,identity={'document_id':'dev'},reserve=.1)
 def test_retained_intent_identity_drift_rejected(self):
  def transport(*args):return 200,b'{}'
  def parse(raw):return {'observed_cost_usd':.01}
  with tempfile.TemporaryDirectory()as td:
   l=Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport);l.operation('x','jev',{'test':1},parse,identity={'document_id':'dev'},reserve=.1)
   intent=next(Path(td).glob('operations/*/intent.json'));v=json.loads(intent.read_text());v['identity']={'document_id':'changed'};intent.write_text(json.dumps(v))
   with self.assertRaises(Stop):Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport).operation('x','jev',{'test':1},parse,identity={'document_id':'dev'},reserve=.1)
 def test_incomplete_jev_batch_rejected(self):
  questions={k:{'type':'choice','instructions':'test','criteria':{'pass':'yes','fail':'no'}}for k in ('support','completeness')}
  raw=json.dumps({'model':a.j.JEV_MODEL,'answers':{},'usage':{'input_tokens':1,'output_tokens':1}}).encode()
  with self.assertRaises(Stop):a.parse_jev(raw,questions)
 def test_uncertain_post_latches_without_retry(self):
  calls=[]
  def transport(*args):calls.append(args);raise OSError('fake timeout')
  with tempfile.TemporaryDirectory()as td:
   l=Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport)
   with self.assertRaises(Stop):l.operation('x','jev',{'test':1},lambda raw:{},identity={},reserve=.1)
   with self.assertRaises(Stop):Ledger(td,{},max_new=2,keys={'jev':'fake-key'},transport=transport)
   self.assertEqual(len(calls),1)
 def test_full_runner_pairing_and_operation_boundary_resume(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td);source,inventory=built('Notice accepts public comments.');source['document_id']='doc-000000000001';inventory['document_id']=source['document_id']
   writer=PdfWriter();writer.add_blank_page(width=100,height=100)
   with (root/'source.pdf').open('wb')as stream:writer.write(stream)
   (root/'source.txt').write_text(source['source_text'])
   manifest={'schema_version':'round4.sources.v1','documents':[dict(document_id=source['document_id'],channel='native',text_path='source.txt',text_sha256=sha((root/'source.txt').read_bytes()),pdf_path='source.pdf',pdf_sha256=sha((root/'source.pdf').read_bytes()),pdf_pages=1,scope='full_notice',native_page_map_known=False)]}
   put(root/'sources.json',manifest);put(root/'freeze.json',r.code_pins(R/'pipeline/pipeline.py'));label='a'*64
   put(root/'authorization.json',dict(schema_version='round6.live-authorization.v1',implementation_sha256=sha((root/'freeze.json').read_bytes()),manifest_sha256=sha((root/'sources.json').read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256=label,nominal_budget_usd=2.0))
   calls=[];payloads={}
   def transport(provider,body,key):
    calls.append(provider)
    if provider=='jev':
     payloads['jev']=body['state'];answers={q:{'type':'choice','choice':'pass','probabilities':{k:1.0 if k=='pass'else 0.0 for k in spec['criteria']},'confidence':1.0}for q,spec in body['questions'].items()}
     return 200,json.dumps({'model':a.j.JEV_MODEL,'answers':answers,'usage':{'input_tokens':100,'output_tokens':5}}).encode()
    name=body['response_format']['json_schema']['name']
    if name=='round6_inventory':value=inventory
    else:
     inner=json.loads(body['messages'][1]['content']);payloads['stronger']=inner['payload'];value=favorable(source,p.assemble(source,inventory))
    return 200,json.dumps({'model':a.MODEL,'provider':'OpenAI','choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}],'usage':{'prompt_tokens':100,'completion_tokens':100,'cost':.001}}).encode()
   kwargs=dict(live=True,authorization=root/'authorization.json',source_labels_freeze_sha256=label,max_new=1,keys={'jev':'fake-jev','openrouter':'fake-or'},transport=transport)
   args=(root/'sources.json',root,root/'freeze.json',root/'out')
   states=[r.run(*args,**kwargs)['state']for _ in range(3)]
   self.assertEqual(states,['paused_at_operation_boundary','paused_at_operation_boundary','completed']);self.assertEqual(calls,['openrouter','jev','openrouter']);self.assertEqual(payloads['jev'],payloads['stronger'])
   terminal=json.loads((root/'out/documents/doc-000000000001/terminal.json').read_text());self.assertTrue(all(arm['complete_record_shadow_accepted']for arm in terminal['arms'].values()));self.assertFalse(terminal['action_ready'])
   self.assertEqual(r.run(*args,**kwargs)['state'],'completed');self.assertEqual(len(calls),3)
if __name__=='__main__':unittest.main(verbosity=2)
