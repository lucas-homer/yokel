#!/usr/bin/env python3
"""Synthetic integration/ledger checks; no fresh corpus, labels, secrets or providers."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_pipeline as r
from operations import Ledger,Pause,Stop,put,sha
j=r.j
PIPELINE=Path(__file__).resolve().parents[1]/'pipeline/pipeline.py'
LABEL_SHA='b'*64
POSITIVE='Written comments must be received by October 31, 2026.\n\nWritten comments may be emailed to comments@example.gov.\n\nIf accommodation is needed for accessibility, contact access@example.gov.'


def response(payload,labels=None):
    labels={'support':'supported','role':'matched','condition':'preserved','conflict':'absent',**(labels or {})}
    return j.encode({'model':j.JEV_MODEL,'answers':{k:{'type':'choice','choice':labels[k],'confidence':1,
        'probabilities':{v:float(v==labels[k]) for v in rubric}} for k,rubric in j.RUBRICS.items()},
        'usage':{'input_tokens':100,'output_tokens':100}})


def signals(_):return [{'pdf_page':1}]


def setup(root,text=POSITIVE,scope='full_notice'):
    root=Path(root)
    from pypdf import PdfWriter
    writer=PdfWriter();writer.add_blank_page(width=100,height=100);pdf=io.BytesIO();writer.write(pdf)
    (root/'input.pdf').write_bytes(pdf.getvalue());(root/'native.txt').write_text(text)
    unit={'document_id':'doc-0123456789ab','channel':'native','text_path':'native.txt','text_sha256':sha(text.encode()),
          'pdf_path':'input.pdf','pdf_sha256':sha((root/'input.pdf').read_bytes()),'pdf_pages':1,'scope':scope,'native_page_map_known':False}
    manifest=root/'manifest.json';put(manifest,{'schema_version':'round4.sources.v1','documents':[unit]})
    freeze=root/'implementation.json';put(freeze,r.code_pins(PIPELINE))
    auth=root/'authorization.json';put(auth,{'schema_version':'round5.live-authorization.v1','implementation_sha256':sha(freeze.read_bytes()),
        'manifest_sha256':sha(manifest.read_bytes()),'source_labels_frozen_before_outputs':True,'source_labels_freeze_sha256':LABEL_SHA,'nominal_budget_usd':.1})
    return manifest,freeze,auth


def execute(root,text=POSITIVE,scope='full_notice',max_new=80,fake=None):
    m,f,a=setup(root,text,scope);calls=[]
    def transport(provider,payload,key):
        calls.append(copy.deepcopy(payload));assert provider=='jev'
        labels={'role':'mismatched'} if payload['state']['candidate']['value']=='access@example.gov' else {}
        return fake(payload) if fake else (200,response(payload,labels))
    result=r.run(m,root,f,Path(root)/'out',live=True,authorization=a,max_new=max_new,
                 transport=transport,keys={'jev':'OFFLINE-TEST-SECRET'},source_labels_freeze_sha256=LABEL_SHA)
    final=j.loads((Path(root)/'out/documents/doc-0123456789ab/shadow-observations.json').read_bytes()) if result['state']=='completed' else None
    return result,final,calls,(m,f,a,transport)


class Tests(unittest.TestCase):
    def test_frozen_adapter_rubrics_full_notice_projection_policy(self):
        self.assertEqual(sha(Path(r.__file__).with_name('jev_frozen.py').read_bytes()),r.FROZEN_JEV_SHA)
        self.assertEqual(j.JEV_MODEL,'jev-1.13.0');self.assertTrue(j.POLICY.startswith(r.NOTICE_PREFIX))
        self.assertIn('actual unconditional absolute',j.POLICY);self.assertNotIn(r.OLD_PREFIX,j.POLICY)
    def test_pipeline_issue_policy_is_explicit_and_unknown_hard(self):
        p=r.module_at(PIPELINE);soft,hard=r.routing_policy(p)
        self.assertFalse(soft & hard)
        item=p.propose('Written comments close October 31, 2026.','doc-0123456789ab')['candidates'][0]
        self.assertIsNotNone(r.local_gate(item,soft)[0])
        bad=copy.deepcopy(item);bad['issues'].append('new_unknown_issue');self.assertIsNone(r.local_gate(bad,soft)[0])
        for issue in ('conditional_deadline_unresolved','participation_lifecycle_unresolved','relative_participation_window_unresolved'):
            bad=copy.deepcopy(item);bad['issues'].append(issue);self.assertIsNone(r.local_gate(bad,soft)[0])
    def test_positive_actual_entrypoint_reaches_model_with_incidental_condition(self):
        with tempfile.TemporaryDirectory() as td:
            result,final,calls,_=execute(td)
            self.assertEqual(result['state'],'completed');self.assertGreaterEqual(len(calls),2)
            self.assertTrue(all(c['state']['source_text']==POSITIVE for c in calls))
            supported={o['field']:o['candidate_value'] for o in final['observations'] if o['shadow_status']=='text_supported'}
            self.assertEqual(supported,{'comment_deadline':'2026-10-31','submission_email':'comments@example.gov'})
            self.assertFalse(final['action_ready']);self.assertFalse(final['production_eligible'])
            self.assertEqual(final['source_fidelity'],'not_verified')
            self.assertEqual(final['document_completeness'],'requires_independent_source_audit')
            self.assertFalse(list((Path(td)/'out').rglob('fallback*')))
    def test_real_applicable_condition_blocks_even_fake_always_favorable(self):
        for text in ('Written comments close October 31, 2026 if a hearing is requested.',
                     'If a hearing is requested, written comments close October 31, 2026.',
                     'Written comments close October 31, 2026 unless the hearing is cancelled.'):
            with self.subTest(text=text),tempfile.TemporaryDirectory() as td:
                result,final,calls,_=execute(td,text)
                self.assertEqual(calls,[]);self.assertTrue(final['observations'])
                self.assertTrue(all(o['shadow_status']=='review' for o in final['observations']))
                self.assertTrue(all(o['disposition']=='review' and o['action_readiness']=='not_ready' for o in final['observations']))
    def test_clock_absolute_date_reachability_and_date_precision(self):
        with tempfile.TemporaryDirectory() as td:
            result,final,calls,_=execute(td,'Written comments must be received by 5:00 p.m. Pacific Time on October 31, 2026.')
            self.assertTrue(calls);self.assertEqual(final['observations'][0]['candidate_value'],'2026-10-31')
            self.assertEqual(final['observations'][0]['shadow_status'],'text_supported')
            p=r.module_at(PIPELINE);item=p.propose(calls[0]['state']['source_text'],'doc-0123456789ab')['candidates'][0]
            self.assertEqual(item['precision'],'date');self.assertIsNone(item['timezone'])
    def test_hearing_context_retained_without_making_it_comment_deadline(self):
        text='The hearing begins November 2, 2026.\n\nWritten comments close October 31, 2026.'
        with tempfile.TemporaryDirectory() as td:
            _,final,calls,_=execute(td,text)
            self.assertEqual(len(calls),1);self.assertEqual(calls[0]['state']['source_text'],text)
            self.assertEqual(final['observations'][0]['candidate_value'],'2026-10-31')
            self.assertEqual(final['observations'][0]['shadow_status'],'text_supported')
        for other_role in ('mismatched','insufficient'):
            good={'field':'comment_deadline','candidate_value':'2026-10-31','shadow_status':'text_supported','operation_status':'completed','dimensions':{'role':{'label':'matched'}}}
            other={'field':'comment_deadline','candidate_value':'2026-11-02','shadow_status':'review','operation_status':'completed','dimensions':{'role':{'label':other_role}}}
            out=r.resolve_email_multiplicity([good,other])
            self.assertEqual(out[0]['shadow_status'],'text_supported' if other_role=='mismatched' else 'review')
    def test_two_favorable_distinct_values_force_review(self):
        for field,one,two in [('comment_deadline','2026-10-31','2026-11-02'),('submission_email','a@example.gov','b@example.gov')]:
            rows=[{'field':field,'candidate_value':v,'shadow_status':'text_supported','operation_status':'completed','dimensions':{'role':{'label':'matched'}}} for v in (one,two)]
            self.assertTrue(all(x['shadow_status']=='review' for x in r.resolve_email_multiplicity(rows)))
    def test_unknown_unprocessed_same_value_and_null_competitors_block(self):
        for field,value in [('comment_deadline','2026-10-31'),('submission_email','a@example.gov')]:
            for competitor_value in (value,None,'other'):
                for state in ('not_attempted','completed'):
                    good={'field':field,'candidate_value':value,'shadow_status':'text_supported','operation_status':'completed','dimensions':{'role':{'label':'matched'}}}
                    bad={'field':field,'candidate_value':competitor_value,'raw_literal':'retained','shadow_status':'review','operation_status':state,'dimensions':{'role':{'label':'insufficient'}}}
                    out=r.resolve_email_multiplicity([good,bad]);self.assertEqual(out[0]['shadow_status'],'review')
    def test_duplicate_supported_fact_can_group(self):
        rows=[{'field':'comment_deadline','candidate_value':'2026-10-31','shadow_status':'text_supported','operation_status':'completed','dimensions':{'role':{'label':'matched'}}} for _ in range(2)]
        self.assertTrue(all(x['shadow_status']=='text_supported' for x in r.resolve_email_multiplicity(rows)))
    def test_actual_multiple_windows_relative_missingyear_and_scope_stay_review(self):
        texts=['Written comments close October 31, 2026. Written comments close November 2, 2026.',
               'Written comments close October 31.', 'Written comments close within 30 working days after publication.',
               'The original comment deadline October 31, 2026 has been extended.', '']
        for text in texts:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as td:
                _,final,calls,_=execute(td,text);self.assertFalse(calls)
                self.assertTrue(all(o['shadow_status']=='review' for o in final['observations']))
        for scope in ('unknown','slice'):
            with self.subTest(scope=scope),tempfile.TemporaryDirectory() as td:
                _,final,calls,_=execute(td,scope=scope);self.assertFalse(calls)
                self.assertTrue(all(o['shadow_status']=='review' for o in final['observations']))
    def test_relative_window_does_not_block_independent_email(self):
        with tempfile.TemporaryDirectory() as td:
            _,final,calls,_=execute(td,'Written comments are due within 30 days after publication.\n\nSubmit written comments to comments@example.gov.')
            self.assertEqual(len(calls),1);self.assertEqual(calls[0]['state']['candidate']['field'],'submission_email')
            self.assertEqual(final['observations'][0]['shadow_status'],'text_supported')
    def test_exact_literal_context_and_condition_span_guards(self):
        p=r.module_at(PIPELINE);soft,_=r.routing_policy(p)
        item=p.propose('Written comments may be emailed to comments@example.gov.','doc-0123456789ab')['candidates'][0]
        for mode in ('literal','context','offset','condition','field'):
            bad=copy.deepcopy(item)
            if mode=='literal':bad['case']['candidate'].update(value='wrong@example.gov',claim='Submit written comments to wrong@example.gov.')
            if mode=='context':bad['context_span']['quote']='altered'
            if mode=='offset':bad['value_span']['end']+=1
            if mode=='condition':bad['condition_spans']=[{'start':0,'end':2,'quote':'XX'}]
            if mode=='field':bad['field']='unexpected'
            self.assertIsNone(r.local_gate(bad,soft)[0])
    def test_calendar_normalization_no_year_borrow_or_repair(self):
        good={'October 31, 2026':'2026-10-31','Oct. 31, 2026':'2026-10-31','October 31,\n2026':'2026-10-31','2024-02-29':'2024-02-29'}
        for raw,expected in good.items():self.assertEqual(r.normalize_literal_date(raw),expected)
        for raw in ('October 31','Oct 31, 26','2026-02-29','October 32, 2026','10/31/2026','October 31\n\n2026','October 31\f2026'):
            self.assertIsNone(r.normalize_literal_date(raw))
        p=r.module_at(PIPELINE);item=p.propose('Written comments close October 31, 2026.','doc-0123456789ab')['candidates'][0]
        item['case']['candidate'].update(value='2026-11-01',claim='Written comments close 2026-11-01.')
        self.assertIsNone(r.local_gate(item,r.routing_policy(p)[0])[0])
    def test_full_context_and_limits_never_clip(self):
        p=r.module_at(PIPELINE);doc={'unit':{'document_id':'doc-0123456789ab','scope':'full_notice','pdf_pages':1,'native_page_map_known':False}}
        for n in (30000,30001):
            text='x'*n;rec=r.propose_channel(p,doc,text,'native')
            self.assertEqual(rec['full_source_context_map'],{'start':0,'end':n,'truncated':False})
            if n==30001:self.assertEqual(rec['candidates'],[])
    def test_request_and_source_size_guards_keep_whole_context(self):
        for size in (19000,30001):
            text='Written comments close October 31, 2026.\n\n'+'z'*size
            with self.subTest(size=size),tempfile.TemporaryDirectory() as td:
                _,final,calls,_=execute(td,text)
                self.assertFalse(calls);self.assertTrue(all(o['shadow_status']=='review' for o in final['observations']))
                record=j.loads((Path(td)/'out/documents/doc-0123456789ab/native/pipeline-record.json').read_bytes())
                self.assertFalse(record['full_source_context_map']['truncated']);self.assertEqual(record['full_source_context_map']['end'],len(text))
    def test_dry_run_no_env_transport_or_output(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=setup(td);out=Path(td)/'out'
            with patch.dict('os.environ',{},clear=True):result=r.run(m,td,f,out,signals=signals,transport=lambda *a:self.fail('provider'))
            self.assertFalse(result['live']);self.assertFalse(out.exists())
    def test_manifest_extra_labels_paths_hash_and_channel_rejected(self):
        for mode in ('labels','path','hash','channel'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                m,f,a=setup(td);obj=j.loads(m.read_bytes());u=obj['documents'][0]
                if mode=='labels':u['expected']='label'
                if mode=='path':u['text_path']='../../elsewhere'
                if mode=='hash':u['text_sha256']='a'*64
                if mode=='channel':u['channel']='fallback'
                m.write_bytes(j.encode(obj))
                with self.assertRaises((Stop,ValueError)):r.run(m,td,f,Path(td)/'out',signals=signals)
    def test_implementation_and_external_label_freeze_binding(self):
        for mode in ('implementation','false','labelhash','manifest'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                m,f,a=setup(td)
                if mode=='implementation':x=j.loads(f.read_bytes());x['policy_sha256']='a'*64;f.write_bytes(j.encode(x))
                else:
                    x=j.loads(a.read_bytes())
                    if mode=='false':x['source_labels_frozen_before_outputs']=False
                    if mode=='labelhash':x['source_labels_freeze_sha256']='a'*64
                    if mode=='manifest':x['manifest_sha256']='a'*64
                    a.write_bytes(j.encode(x))
                with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',live=True,authorization=a,signals=signals,source_labels_freeze_sha256=LABEL_SHA,transport=lambda *a:self.fail('provider'))
    def test_mechanical_pdf_pages_and_document_budget_caps(self):
        with tempfile.TemporaryDirectory() as td:
            m,f,a=setup(td)
            for kwargs in ({'signals':lambda _:[{},{}]},{'budget':.10001},{'max_new':81}):
                with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',**{'signals':signals,**kwargs})
            original=j.loads(m.read_bytes());overpages=copy.deepcopy(original);overpages['documents'][0]['pdf_pages']=41
            m.write_bytes(j.encode(overpages))
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',signals=signals)
            m.write_bytes(j.encode(original))
            x=j.loads(m.read_bytes());x['documents']=[]
            for i in range(9):u=copy.deepcopy(j.loads(m.read_bytes())['documents'][0]);u['document_id']='doc-'+format(i,'012x');x['documents'].append(u)
            m.write_bytes(j.encode(x))
            with self.assertRaises(Stop):r.run(m,td,f,Path(td)/'out',signals=signals)
    def test_resume_exact_completed_without_rePOST(self):
        with tempfile.TemporaryDirectory() as td:
            result,_,calls,context=execute(td,max_new=1);self.assertEqual(result['state'],'paused_at_operation_boundary');self.assertEqual(len(calls),1)
            m,f,a,transport=context
            kwargs={'live':True,'authorization':a,'signals':signals,'transport':transport,'keys':{'jev':'OFFLINE-TEST-SECRET'},'source_labels_freeze_sha256':LABEL_SHA}
            result=r.run(m,td,f,Path(td)/'out',max_new=80,**kwargs);count=len(calls);self.assertEqual(result['state'],'completed')
            self.assertEqual(r.run(m,td,f,Path(td)/'out',max_new=0,**kwargs)['state'],'completed');self.assertEqual(len(calls),count)
            for p in (Path(td)/'out').rglob('*'):
                if p.is_file():self.assertNotIn(b'OFFLINE-TEST-SECRET',p.read_bytes())
    def test_uncertain_HTTP_invalid_usage_latch_without_retry(self):
        for mode in ('uncertain','HTTP','usage'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                calls=[]
                def fake(*args):
                    calls.append(1)
                    if mode=='uncertain':raise TimeoutError('secret-bearing exception')
                    return (429,b'{"error":"rate"}') if mode=='HTTP' else (200,b'{}')
                ledger=Ledger(td,{},transport=fake,keys={'jev':'OFFLINE-TEST-SECRET'})
                with self.assertRaises(Stop):ledger.operation('c','jev',{},lambda raw:r.parse_jev(raw,{}),identity={},reserve=.001)
                with self.assertRaises(Stop):Ledger(td,{},transport=fake,keys={'jev':'OFFLINE-TEST-SECRET'})
                self.assertEqual(len(calls),1)
    def test_received_response_reparse_without_POST(self):
        with tempfile.TemporaryDirectory() as td:
            calls=[];raw=b'{"ok":true}'
            def fake(*a):calls.append(1);return 200,raw
            ledger=Ledger(td,{},transport=fake,keys={'jev':'OFFLINE-TEST-SECRET'})
            ledger.operation('c','jev',{},lambda _:{'observed_cost_usd':.001},identity={},reserve=.001)
            next((Path(td)/'operations').glob('*/result.json')).unlink()
            ledger=Ledger(td,{},transport=fake,keys={'jev':'OFFLINE-TEST-SECRET'})
            ledger.operation('c','jev',{},lambda _:{'observed_cost_usd':.001},identity={},reserve=.001)
            self.assertEqual(len(calls),1)
    def test_native_only_ledger_identity_drift_and_caps(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(td,{},max_new=80,keys={'jev':'fake'},transport=lambda *a:(200,b'{}'))
            with self.assertRaises(Stop):ledger.operation('x','ocr',{},j.loads,identity={},reserve=0,pages=1)
            ledger.operation('c','jev',{},lambda _:{'observed_cost_usd':0},identity={},reserve=0)
            with self.assertRaises(Stop):ledger.operation('c','jev',{'different':1},j.loads,identity={},reserve=0)
            for i in range(79):ledger.operation(str(i),'jev',{},lambda _:{'observed_cost_usd':0},identity={},reserve=0)
            with self.assertRaises(Pause):ledger.operation('81','jev',{},j.loads,identity={},reserve=0)
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(td,{},max_new=0,transport=lambda *a:self.fail('provider'),keys={'jev':'fake'})
            with self.assertRaises(Pause):ledger.operation('c','jev',{},j.loads,identity={},reserve=.001)
            self.assertFalse(list((Path(td)/'operations').glob('*/intent.json')))
    def test_mixed_reserves_usage_and_observed_budget_overrun_stop(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(td,{},max_new=3,keys={'jev':'fake'},transport=lambda *a:(200,b'{}'))
            ledger.operation('a','jev',{},lambda _:{'observed_cost_usd':.06},identity={},reserve=.02)
            ledger.operation('b','jev',{},lambda _:{'observed_cost_usd':None},identity={},reserve=.035)
            self.assertAlmostEqual(ledger.totals()['budget_charge_usd'],.095)
            with self.assertRaises(Pause):ledger.operation('c','jev',{},j.loads,identity={},reserve=.01)
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(td,{},keys={'jev':'fake'},transport=lambda *a:(200,b'{}'))
            with self.assertRaises(Stop):ledger.operation('a','jev',{},lambda _:{'observed_cost_usd':.11},identity={},reserve=.001)
            self.assertEqual(ledger.totals()['observed_accounted_usd'],.11)
    def test_model_usage_schema_and_raw_response_drift(self):
        payload={'unused':True};raw=j.loads(response(payload))
        for mode in ('model','usage','nonfinite','answer'):
            x=copy.deepcopy(raw)
            if mode=='model':x['model']='jev-latest'
            if mode=='usage':del x['usage']
            if mode=='nonfinite':x['usage']['input_tokens']=-1
            if mode=='answer':x['answers']['support']['choice']='unknown'
            with self.assertRaises(ValueError):r.parse_jev(j.encode(x),{})
        with tempfile.TemporaryDirectory() as td:
            ledger=Ledger(td,{},keys={'jev':'fake'},transport=lambda *a:(200,b'{}'))
            ledger.operation('c','jev',{},lambda _:{'observed_cost_usd':0},identity={},reserve=0)
            next((Path(td)/'operations').glob('*/response.body')).write_bytes(b'changed')
            with self.assertRaises(Stop):ledger.operation('c','jev',{},lambda _:{'observed_cost_usd':0},identity={},reserve=0)
    def test_real_neutral_blank_pdf_pagecount(self):
        import io
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=100,height=100);out=io.BytesIO();writer.write(out)
        self.assertEqual(r.page_signals(out.getvalue()),[{'pdf_page':1}])


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    with contextlib.redirect_stdout(io.StringIO()):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    Path(__file__).with_name('validation.json').write_text(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'success':result.wasSuccessful(),'failure_details':[trace for _,trace in result.failures+result.errors],'providers_called':0,'fresh_sources_read':False,'labels_read':False},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
