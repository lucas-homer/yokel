#!/usr/bin/env python3
"""No network, fresh source, evaluator, or credential access. Neutral synthetic fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_pipeline as r
from operations import Ledger,Pause,Stop,put,sha
j=r.j
PIPELINE=Path(__file__).resolve().parents[1]/'pipeline/pipeline.py'


def jresponse(payload,role='matched'):
    labels={'support':'supported','role':role,'condition':'preserved','conflict':'absent'}
    return j.encode({'model':j.JEV_MODEL,'answers':{k:{'type':'choice','choice':labels[k],'confidence':1,
                 'probabilities':{v:float(v==labels[k]) for v in rubrics}} for k,rubrics in j.RUBRICS.items()},
                 'usage':{'input_tokens':100,'output_tokens':100}})


def oresponse(text):
    return j.encode({'model':r.OCR_MODEL,'provider':'FakeProvider','choices':[{'finish_reason':'stop',
          'message':{'content':'Completion deliberately contradicts annotation, never source.',
                     'annotations':[{'type':'file','file':{'content':[{'type':'text','text':text},
                                   {'type':'image_url','image_url':{'url':'data:fake'} } ]}}]}}],
          'usage':{'prompt_tokens':100,'completion_tokens':8,'cost':.002}})


def synthetic_setup(root,text='Written comments must be received by October 31, 2026.\n\nWritten comments may be emailed to comments@example.gov.'):
    root=Path(root);(root/'input.pdf').write_bytes(b'%PDF-1.7\nneutral offline fake PDF\n%%EOF')
    (root/'native.txt').write_text(text)
    u={'document_id':'doc-0123456789ab','channel':'native','text_path':'native.txt','text_sha256':sha(text.encode()),
       'pdf_path':'input.pdf','pdf_sha256':sha((root/'input.pdf').read_bytes()),'pdf_pages':1,
       'scope':'full_notice','native_page_map_known':False}
    manifest=root/'manifest.json';manifest.write_text(json.dumps({'schema_version':'round4.sources.v1','documents':[u]}))
    freeze=root/'implementation.json';put(freeze,r.code_pins(PIPELINE))
    auth=root/'authorization.json';put(auth,{'schema_version':'round4.live-authorization.v1',
      'implementation_sha256':sha(freeze.read_bytes()),'manifest_sha256':sha(manifest.read_bytes()),
      'source_labels_frozen_before_outputs':True,'nominal_budget_usd':1.0})
    return manifest,freeze,auth


def signals(_):return [{'pdf_page':1,'embedded_nonspace_characters':300,'image_xobject_present':False}]


class Tests(unittest.TestCase):
    def test_frozen_model_rubrics_only_scope_prefix_changed(self):
        self.assertEqual(sha(Path(r.__file__).with_name('jev_frozen.py').read_bytes()),r.FROZEN_JEV_SHA)
        self.assertTrue(j.POLICY.startswith(r.NOTICE_PREFIX));self.assertNotIn(r.OLD_PREFIX,j.POLICY)
        self.assertEqual(j.JEV_MODEL,'jev-1.13.0')
    def test_dry_no_env_no_artifact_output_or_transport(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td);out=Path(td)/'out'
            with patch.dict('os.environ',{},clear=True):p=r.run(m,td,f,out,signals=signals,transport=lambda *a:self.fail('network'))
            self.assertEqual(p['native_candidates'],2);self.assertFalse(out.exists());self.assertFalse(p['live'])
    def test_bad_manifest_extra_labels_path_escape_and_hash(self):
        for mode in ('label','path','hash'):
            with tempfile.TemporaryDirectory() as td:
                m,f,a=synthetic_setup(td);x=json.loads(m.read_text())
                if mode=='label':x['documents'][0]['correct']=True
                if mode=='path':x['documents'][0]['text_path']='../../elsewhere'
                if mode=='hash':x['documents'][0]['text_sha256']='a'*64
                m.write_text(json.dumps(x))
                with self.assertRaises((Stop,ValueError)):r.run(m,td,f,Path(td)/'out',signals=signals)
    def test_implementation_drift_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td);x=json.loads(f.read_text());x['policy_sha256']='a'*64;f.write_text(json.dumps(x))
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',signals=signals)
    def test_source_pages_actual_check_and_budget_caps(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td)
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',signals=lambda _:[{},{}])
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',budget=1.01,signals=signals)
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',max_new=133,signals=signals)
    def test_role_issue_soft_only_and_unknown_hard(self):
        p=r.module_at(PIPELINE);rec=p.propose('Contact comments@example.gov for more information.','doc-0123456789ab')
        item=rec['candidates'][0];self.assertIn('submission_role_unverified',item['issues'])
        self.assertIsNotNone(r.local_gate(item)[0])
        for issue in ['condition_scope_requires_semantic_verification','lifecycle_scope_unresolved','novel_unknown_issue','multiple_same_role_values_scope_unresolved']:
            c=copy.deepcopy(item);c['issues'].append(issue);self.assertIsNone(r.local_gate(c)[0])
    def test_source_value_literal_guard(self):
        p=r.module_at(PIPELINE);rec=p.propose('Written comments may be emailed to comments@example.gov.','doc-0123456789ab')
        item=rec['candidates'][0];item['case']['candidate']['value']='wrong@example.gov';item['case']['candidate']['claim']='Written comments may go to wrong@example.gov.'
        self.assertIn('destination_value_literal_mismatch',r.local_gate(item)[1]['blocking_issues'])
    def test_full_context_no_truncation_overlimit_review(self):
        p=r.module_at(PIPELINE);u={'document_id':'doc-0123456789ab','scope':'full_notice','pdf_pages':1,'native_page_map_known':False}
        doc={'unit':u};text='Written comments close October 31, 2026.\n\nOther event is November 2, 2026.'
        rec=r.propose_channel(p,doc,text,'native');self.assertTrue(all(c['case']['source_text']==text for c in rec['candidates']))
        rec=r.propose_channel(p,doc,'x'*30001,'native');self.assertEqual(rec['candidates'],[]);self.assertEqual(rec['full_source_context_map']['end'],30001)
    def test_mechanical_fallback_low_text_and_images(self):
        rec={'document_id':'doc-0123456789ab','routes':[]};doc={'unit':{'scope':'full_notice'},'page_signals':[{'embedded_nonspace_characters':30,'image_xobject_present':True}]}
        d=r.fallback_decision(doc,rec,[]);self.assertEqual(d['decision'],'acquire_mistral_ocr');self.assertFalse(d['fallback_text_read_before_decision'])
        doc['page_signals'][0]['embedded_nonspace_characters']=150
        self.assertIn('native_image_page_sparse_text',r.fallback_decision(doc,rec,[])['reasons'])
        doc['unit']['scope']='slice';self.assertEqual(r.fallback_decision(doc,rec,[])['decision'],'source_review')
    def test_annotations_only_and_unknown_pdf_page_mapping(self):
        parsed=r.parse_ocr(oresponse('😀 Written comments close October 31, 2026.'),1)
        self.assertNotIn('Completion deliberately',parsed['text']);self.assertFalse(parsed['image_parts_to_Jev'])
        self.assertIsNone(parsed['serialization_map'][0]['pdf_page'])
        self.assertEqual(parsed['serialization_map'][0]['end'],len(parsed['text']))
    def test_ocr_missing_usage_cost_model_annotation_rejected(self):
        for mode in ('usage','cost','model','annotation'):
            obj=j.loads(oresponse('text'))
            if mode=='usage':del obj['usage']
            if mode=='cost':del obj['usage']['cost']
            if mode=='model':obj['model']='other/model'
            if mode=='annotation':obj['choices'][0]['message']['annotations']=[]
            with self.assertRaises(Stop):r.parse_ocr(j.encode(obj),1)
    def test_resume_per_case_no_rePOST(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td);calls=[];out=Path(td)/'out'
            def fake(provider,payload,key):calls.append(provider);return 200,jresponse(payload)
            keys={'jev':'OFFLINE-TEST-SECRET','openrouter':'OFFLINE-TEST-OR-SECRET'}
            first=r.run(m,td,f,out,live=True,authorization=a,max_new=1,signals=signals,transport=fake,keys=keys)
            self.assertEqual(first['state'],'paused_at_operation_boundary');self.assertEqual(len(calls),1)
            second=r.run(m,td,f,out,live=True,authorization=a,max_new=1,signals=signals,transport=fake,keys=keys)
            self.assertEqual(second['state'],'completed');self.assertEqual(len(calls),2)
            third=r.run(m,td,f,out,live=True,authorization=a,max_new=0,signals=signals,transport=fake,keys=keys)
            self.assertEqual(third['state'],'completed');self.assertEqual(len(calls),2)
            for p in out.rglob('*'):
                if p.is_file():self.assertNotIn(b'OFFLINE-TEST-SECRET',p.read_bytes())
    def test_uncertain_stop_no_resume_or_retry(self):
        with tempfile.TemporaryDirectory() as td:
            calls=[]
            def bad(*a):calls.append(1);raise TimeoutError('secret-bearing exception')
            ledger=Ledger(Path(td)/'out',{'pin':'x'},transport=bad,keys={'jev':'OFFLINE-TEST-SECRET'})
            with self.assertRaises(Stop):ledger.operation('c','jev',{'x':1},lambda _:None,identity={},reserve=.001)
            with self.assertRaises(Stop):Ledger(Path(td)/'out',{'pin':'x'},transport=bad,keys={'jev':'OFFLINE-TEST-SECRET'})
            self.assertEqual(len(calls),1)
    def test_invalid_response_latches_missing_usage_before_next(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/'out',{},transport=lambda *a:(200,b'{}'),keys={'jev':'OFFLINE-TEST-SECRET'})
            with self.assertRaises(Stop):ledger.operation('c','jev',{},lambda raw:r.parse_jev(raw,{}),identity={},reserve=.001)
            self.assertEqual(len(list((Path(td)/'out/operations').glob('*/stop.json'))),1)
            with self.assertRaises(Stop):Ledger(Path(td)/'out',{})
    def test_budget_and_call_caps_reserve_before_POST(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/'out',{},max_new=0,transport=lambda *a:self.fail('network'),keys={'jev':'fake'})
            with self.assertRaises(Pause):ledger.operation('c','jev',{},lambda _:None,identity={},reserve=.001)
            self.assertFalse(list((Path(td)/'out/operations').glob('*/intent.json')))
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/'out',{},budget=.01,transport=lambda *a:self.fail('network'),keys={'jev':'fake'})
            with self.assertRaises(Pause):ledger.operation('c','jev',{},lambda _:None,identity={},reserve=.02)
    def test_complete_fallback_decision_precedes_OCR_and_resume(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td,text='');out=Path(td)/'out';calls=[]
            def fake(provider,payload,key):
                calls.append(provider)
                if provider=='openrouter':
                    decision=out/'documents/doc-0123456789ab/fallback-decision.json';self.assertTrue(decision.exists())
                    self.assertEqual(json.loads(decision.read_text())['decision'],'acquire_mistral_ocr')
                    return 200,oresponse('Written comments must be received by October 31, 2026.\n\nWritten comments may be emailed to comments@example.gov.')
                return 200,jresponse(payload)
            keys={'jev':'OFFLINE-TEST-SECRET','openrouter':'OFFLINE-TEST-OR-SECRET'}
            result=r.run(m,td,f,out,live=True,authorization=a,max_new=3,signals=signals,transport=fake,keys=keys)
            self.assertEqual(result['state'],'completed');self.assertEqual(calls,['openrouter','jev','jev'])
            raw=j.loads(next((out/'operations').glob('ocr-*/response.body')).read_bytes())
            self.assertIn('Completion deliberately',raw['choices'][0]['message']['content'])
            final=j.loads((out/'documents/doc-0123456789ab/shadow-observations.json').read_bytes())
            self.assertFalse(final['action_ready']);self.assertEqual(final['channel_disagreement_fields'],[]);self.assertTrue(all(x['shadow_status']=='text_supported' for x in final['observations']));self.assertEqual(final['source_fidelity'],'not_verified')
    def test_channel_disagreement_and_shadow_never_verified(self):
        native=[{'field':'submission_email','candidate_value':'a@example.gov','shadow_status':'text_supported'}]
        fallback=[{'field':'submission_email','candidate_value':'b@example.gov','shadow_status':'text_supported'}]
        merged=r.merge_shadow(native,fallback,'full_notice');self.assertTrue(all(x['shadow_status']=='review' for x in merged['observations']))
        self.assertFalse(merged['production_eligible']);self.assertFalse(merged['action_ready'])
    def test_unresolved_native_competitor_blocks_OCR_acceptance(self):
        native=[{'field':'submission_email','candidate_value':'old@example.gov','shadow_status':'review','operation_status':'not_attempted'}]
        fallback=[{'field':'submission_email','candidate_value':'new@example.gov','shadow_status':'text_supported','operation_status':'completed'}]
        merged=r.merge_shadow(native,fallback,'full_notice')
        self.assertEqual(merged['channel_disagreement_fields'],['submission_email'])
        self.assertTrue(all(x['shadow_status']=='review' for x in merged['observations']));self.assertEqual(len(merged['observations']),2)
        native[0].update(operation_status='completed',dimensions={'role':{'label':'mismatched'}})
        merged=r.merge_shadow(native,fallback,'full_notice');self.assertEqual(merged['channel_disagreement_fields'],[])
        self.assertEqual(merged['observations'][1]['shadow_status'],'text_supported')
        native[0].update(candidate_value=None,raw_literal='unparsed-date',dimensions={'role':{'label':'insufficient'}})
        self.assertEqual(r.merge_shadow(native,fallback,'full_notice')['channel_disagreement_fields'],['submission_email'])
    def test_same_value_lost_condition_or_null_normalization_stays_review(self):
        fallback=[{'field':'comment_deadline','candidate_value':'2026-10-31','shadow_status':'text_supported','operation_status':'completed'}]
        for value,literal in [('2026-10-31','October 31, 2026'),(None,'October 31')]:
            native=[{'field':'comment_deadline','candidate_value':value,'raw_literal':literal,'shadow_status':'review',
                    'operation_status':'not_attempted','pipeline_issues':['condition_scope_requires_semantic_verification']}]
            result=r.merge_shadow(native,fallback,'full_notice')
            self.assertEqual(result['channel_unresolved_fields'],['comment_deadline'])
            self.assertTrue(all(x['shadow_status']=='review' for x in result['observations']))
            self.assertEqual(result['observations'][0]['raw_literal'],literal)
        native[0].update(operation_status='completed',dimensions={'role':{'label':'mismatched'}})
        result=r.merge_shadow(native,fallback,'full_notice');self.assertEqual(result['channel_unresolved_fields'],[])
        self.assertEqual(result['observations'][1]['shadow_status'],'text_supported')
    def test_value_cannot_borrow_year_from_next_context(self):
        proposer=r.module_at(PIPELINE)
        for separator in ('\n\n','\f'):
            record=proposer.propose('Written comments close October 31'+separator+'2026 Legislative Calendar','doc-0123456789ab')
            self.assertEqual(len(record['candidates']),1)
            request,gate=r.local_gate(record['candidates'][0]);self.assertIsNone(request)
            self.assertIn('value_crosses_context_or_invalid_context_span',gate['blocking_issues'])
        for literal in ('October 31, 2026','October 31,\n2026'):
            item=proposer.propose('Written comments close '+literal+'.','doc-0123456789ab')['candidates'][0]
            self.assertIsNotNone(r.local_gate(item)[0])
            item['context_span']['quote']='altered context'
            self.assertIsNone(r.local_gate(item)[0])
    def test_actual_verify_record_preserves_null_raw_and_terminal_indicators(self):
        proposer=r.module_at(PIPELINE)
        for source in ('Written comments close October 32, 2026.','Written comments close October 31, 2026 if a hearing is requested.'):
            with tempfile.TemporaryDirectory() as td:
                record=proposer.propose(source,'doc-0123456789ab')
                ledger=Ledger(Path(td)/'ledger',{},max_new=0,transport=lambda *a:self.fail('network'))
                results=r.verify_record(ledger,record,Path(td)/'native',{})
                row=results[0];self.assertTrue(row['raw_literal']);self.assertEqual(row['shadow_status'],'review')
                if '32' in source:self.assertIsNone(row['candidate_value'])
                fallback=[{'field':'comment_deadline','candidate_value':'2026-10-31','shadow_status':'text_supported',
                           'disposition':'accept_shadow','action_readiness':'requires_source_verification','operation_status':'completed'}]
                merged=r.merge_shadow(results,fallback,'full_notice')
                for final in merged['observations']:
                    self.assertEqual(final['shadow_status'],'review');self.assertEqual(final['disposition'],'review');self.assertEqual(final['action_readiness'],'not_ready')
                self.assertEqual(merged['observations'][0]['raw_literal'],row['raw_literal'])
    def test_authorization_label_attestation_false_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td);obj=j.loads(a.read_bytes());obj['source_labels_frozen_before_outputs']=False;a.write_text(json.dumps(obj))
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',live=True,authorization=a,signals=signals,transport=lambda *a:self.fail('network'))
    def test_mixed_budget_reserves_and_observed_per_operation(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/'out',{},max_new=3,budget=.1,keys={'jev':'fake','openrouter':'otherfake'},transport=lambda *a:(200,b'{}'))
            ledger.operation('OCR','ocr',{'x':1},lambda _:{'observed_cost_usd':.06},identity={},reserve=.02,pages=1)
            ledger.operation('JEV','jev',{'x':2},lambda _:{'observed_cost_usd':None},identity={},reserve=.035)
            self.assertAlmostEqual(ledger.totals()['budget_charge_usd'],.095)
            self.assertAlmostEqual(ledger.totals()['nominal_reserved_usd'],.055)
            with self.assertRaises(Pause):ledger.operation('next','jev',{'x':3},lambda _:{},identity={},reserve=.01)
    def test_email_multiplicity_unique_positive_role_resolution(self):
        good={'field':'submission_email','candidate_value':'submit@example.gov','shadow_status':'text_supported',
              'pipeline_issues':[r.EMAIL_MULTIPLICITY],'operation_status':'completed','dimensions':{'role':{'label':'matched'}}}
        other={'field':'submission_email','candidate_value':'info@example.gov','shadow_status':'review',
               'pipeline_issues':[r.EMAIL_MULTIPLICITY],'operation_status':'completed','dimensions':{'role':{'label':'mismatched'}}}
        resolved=r.resolve_email_multiplicity(copy.deepcopy([good,other]));self.assertTrue(resolved[0]['email_multiplicity_resolved']);self.assertTrue(resolved[1]['classified_non_submission_role'])
        for uncertain in ('insufficient','matched'):
            competitor=copy.deepcopy(other);competitor['dimensions']['role']['label']=uncertain
            result=r.resolve_email_multiplicity(copy.deepcopy([good,competitor]));self.assertEqual(result[0]['shadow_status'],'review')
        competitor=copy.deepcopy(other);competitor['operation_status']='not_attempted'
        self.assertEqual(r.resolve_email_multiplicity(copy.deepcopy([good,competitor]))[0]['shadow_status'],'review')
    def test_positive_cap_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/'out',{},keys={'jev':'fake','openrouter':'otherfake'},transport=lambda *a:self.fail('network'))
            for index in range(120):
                folder=ledger.root/'operations'/str(index);folder.mkdir()
                put(folder/'intent.json',{'kind':'jev','pages':0,'reserved_nominal_usd':0,'created_utc':'2026-10-07T00:00:00+00:00'})
                put(folder/'response.body',b'{}');put(folder/'status.json',{'http_status':200})
            with self.assertRaises(Pause):ledger.operation('extra','jev',{},j.loads,identity={},reserve=.001)
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(Path(td)/'out',{},keys={'openrouter':'fake'},transport=lambda *a:self.fail('network'))
            folder=ledger.root/'operations'/'prior';folder.mkdir();put(folder/'intent.json',{'kind':'ocr','pages':60,'reserved_nominal_usd':0,'created_utc':'2026-10-07T00:00:00+00:00'});put(folder/'response.body',b'{}');put(folder/'status.json',{'http_status':200})
            with self.assertRaises(Pause):ledger.operation('extra','ocr',{},j.loads,identity={},reserve=.001,pages=1)
    def test_OCR_transport_timeout_and_retention_limit(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):self.n=n;return b'{}'
        response=Response();seen={}
        class Opener:
            def open(self,request,timeout):seen['timeout']=timeout;return response
        with patch.object(r.urllib.request,'build_opener',return_value=Opener()):
            self.assertEqual(r.provider_post_once('openrouter',{'x':1},'offline'),(200,b'{}'))
        self.assertEqual(seen['timeout'],180);self.assertEqual(response.n,25_000_001)
    def test_OCR_pacing_uses_prior_durable_start(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as td:
            sleeps=[];clock=lambda:dt.datetime.now(dt.timezone.utc).timestamp()
            ledger=Ledger(Path(td)/'out',{},max_new=2,keys={'openrouter':'fake'},transport=lambda *a:(200,b'{}'),clock=clock,sleeper=sleeps.append)
            ledger.operation('a','ocr',{'x':1},j.loads,identity={},reserve=.001,pages=1)
            ledger.operation('b','ocr',{'x':2},j.loads,identity={},reserve=.001,pages=1)
            self.assertEqual(len(sleeps),1);self.assertTrue(21<sleeps[0]<=22)
    def test_real_neutral_blank_PDF_mechanical_signals(self):
        import io
        from pypdf import PdfWriter
        stream=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=200,height=200);writer.write(stream)
        rows=r.page_signals(stream.getvalue());self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['embedded_nonspace_characters'],0);self.assertFalse(rows[0]['image_xobject_present'])
    def test_12_document_bound_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=synthetic_setup(td);obj=j.loads(m.read_bytes());unit=obj['documents'][0]
            obj['documents']=[{**unit,'document_id':f'doc-{index:012x}'} for index in range(13)];m.write_text(json.dumps(obj))
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',signals=signals)
    def test_ledger_pin_and_response_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'out';ledger=Ledger(root,{'pin':'x'},keys={'jev':'fake'},transport=lambda *a:(200,b'{"valid":true}'))
            ledger.operation('c','jev',{'x':1},j.loads,identity={},reserve=.001)
            with self.assertRaises(Stop):Ledger(root,{'pin':'y'})
            next((root/'operations').glob('*/response.body')).write_bytes(b'{"valid":false}')
            with self.assertRaises(Stop):ledger.operation('c','jev',{'x':1},j.loads,identity={},reserve=.001)

if __name__=='__main__':unittest.main(verbosity=2)
