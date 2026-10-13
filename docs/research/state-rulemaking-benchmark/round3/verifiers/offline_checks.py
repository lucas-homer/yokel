#!/usr/bin/env python3
"""Source-neutral offline checks; all transports are fakes and incur zero spend."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import verifier as v


def fixture():
    s='😀 Rule R1. Written comments close October 31, 2026, if a hearing is requested. Rule R2 hearing is November 2, 2026.'
    q='Written comments close October 31, 2026, if a hearing is requested.'
    a=s.index(q)
    return {'case_id':'fake-01','source_text':s,
            'candidate':{'field':'comment_deadline','value':'2026-10-31',
                         'claim':'Written comments for Rule R1 close October 31, 2026 if a hearing is requested.',
                         'target':'Rule R1','role':'written_comment_close','conditions':['if a hearing is requested']},
            'evidence':[{'quote':q,'start':a,'end':a+len(q)}]}


def response(provider,overrides=None):
    labels={'support':'supported','role':'matched','condition':'preserved','conflict':'absent'}
    labels.update(overrides or {})
    if provider=='jev':
        obj={'model':v.JEV_MODEL,'answers':{k:{'type':'choice','choice':labels[k],
             'probabilities':{option:float(option==labels[k]) for option in options},'confidence':1.0}
             for k,options in v.RUBRICS.items()},'usage':{'input_tokens':100,'output_tokens':20}}
    else:
        obj={'model':v.OR_MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(labels)}}],
             'usage':{'prompt_tokens':100,'completion_tokens':20,'cost':0.000018}}
    return obj


class Checks(unittest.TestCase):
    def test_exact_unicode_offsets_and_no_normalization(self):
        c=fixture(); self.assertFalse(v.deterministic(c)['blocking_issues'])
        c['evidence'][0]['start']+=1
        self.assertEqual(v.deterministic(c)['blocking_issues'],['invalid_citation'])
    def test_structured_values_preserved_and_not_forced_to_strings(self):
        for value in (['2026-10-31','2026-11-02'],{'count':20,'unit':'working days','anchor':'hearing close'},20):
            c=fixture();c['candidate']['value']=value
            j,gate=v.build_request(c,'jev');g,_=v.build_request(c,'openrouter')
            self.assertEqual(j['state']['candidate']['value'],value)
            self.assertEqual(v.loads(g['messages'][1]['content'])['candidate']['value'],value)
            self.assertEqual(gate['value_claim_consistency'],'unresolved')
        c=fixture();c['candidate']['value']={'x':'a'*4001}
        with self.assertRaises(ValueError):v.state_for(c)
    def test_example_offsets(self):
        c=json.loads(Path(__file__).with_name('INPUT-CONTRACT.json').read_text())['example']
        self.assertFalse(v.deterministic(c)['blocking_issues'])
    def test_reject_gold_and_unknown_runtime_keys(self):
        for where in ('case','candidate','evidence'):
            c=fixture()
            target=c if where=='case' else c['candidate'] if where=='candidate' else c['evidence'][0]
            target['expected_judgment']='supported'
            with self.assertRaises(ValueError): v.state_for(c)
    def test_shared_semantic_state_and_full_context(self):
        c=fixture();j,_=v.build_request(c,'jev');g,_=v.build_request(c,'openrouter')
        self.assertEqual(v.encode(j['state']),g['messages'][1]['content'].encode())
        self.assertIn('Rule R2',j['state']['source_text'])
        self.assertEqual(j['state']['candidate'],c['candidate'])
        self.assertIn('candidate.value',j['questions']['support']['criteria']['contradicted'])
    def test_value_claim_disagreement_blocks(self):
        c=fixture();c['candidate']['value']='2026-10-30'
        for provider in v.ENDPOINTS:
            req,gate=v.build_request(c,provider)
            self.assertIsNone(req);self.assertIn('value_claim_mismatch',gate['blocking_issues'])
    def test_email_claim_disagreement_blocks(self):
        c=fixture();c['candidate'].update(value='Coments@example.gov',claim='Comments go to Comments@example.gov.')
        self.assertIn('value_claim_mismatch',v.deterministic(c)['blocking_issues'])
    def test_missing_evidence_and_null_abstain(self):
        c=fixture();c['evidence']=[];self.assertIn('missing_evidence',v.deterministic(c)['blocking_issues'])
        c=fixture();c['candidate']['value']=None;self.assertIn('candidate_abstained',v.deterministic(c)['blocking_issues'])
    def test_invalid_offsets_and_path_ids(self):
        c=fixture();c['evidence'][0]['start']=True
        with self.assertRaises(ValueError):v.state_for(c)
        c=fixture();c['case_id']='../other'
        with self.assertRaises(ValueError):v.state_for(c)
    def test_oversize_rejects_not_truncates(self):
        c=fixture();c['source_text']+='x'*30000
        with self.assertRaises(ValueError):v.build_request(c,'jev')
    def test_valid_responses_preserve_probabilities_and_usage(self):
        gate=v.deterministic(fixture())
        for provider in v.ENDPOINTS:
            obj=response(provider);r=v.parse_response(v.encode(obj),provider,gate)
            self.assertEqual(r['usage'],obj['usage']);self.assertFalse(r['abstained'])
            if provider=='jev':self.assertIn('probabilities',r['dimensions']['support'])
            else:self.assertNotIn('probabilities',r['dimensions']['support'])
    def test_conflict_and_unknown_labels_preserved(self):
        for provider in v.ENDPOINTS:
            r=v.parse_response(v.encode(response(provider,{'support':'insufficient','conflict':'present'})),provider,v.deterministic(fixture()))
            self.assertTrue(r['abstained']);self.assertEqual(r['dimensions']['conflict']['label'],'present')
    def test_categorical_shadow_gate_no_confidence_cutoff(self):
        for provider in v.ENDPOINTS:
            good=v.parse_response(v.encode(response(provider)),provider,v.deterministic(fixture()))
            self.assertEqual(good['disposition'],'accept_shadow')
            self.assertEqual(good['action_readiness'],'requires_source_verification')
            for axis,label in [('support','contradicted'),('role','mismatched'),('condition','omitted_or_changed'),('conflict','present')]:
                bad=v.parse_response(v.encode(response(provider,{axis:label})),provider,{})
                self.assertEqual(bad['disposition'],'review')
        obj=response('jev');obj['answers']['support'].update(choice='supported',confidence=.1,probabilities={'supported':.4,'contradicted':.3,'insufficient':.3})
        self.assertEqual(v.parse_response(v.encode(obj),'jev',{})['disposition'],'accept_shadow')
    def test_missing_usage_stops_before_next_case(self):
        for provider in v.ENDPOINTS:
            obj=response(provider);del obj['usage']
            with self.assertRaises(ValueError):v.parse_response(v.encode(obj),provider,{})
            calls=[];c2=fixture();c2['case_id']='fake-02'
            def fake(*a):calls.append(1);return 200,v.encode(obj)
            with tempfile.TemporaryDirectory() as td:
                out=Path(td)/'run'
                with self.assertRaises(RuntimeError):v.run_cases([fixture(),c2],provider,out,live=True,key='FAKE-SECRET-ONLY',transport=fake)
                self.assertEqual(len(calls),1);self.assertFalse((out/'fake-02').exists())
                self.assertIn('missing_or_invalid_usage',(out/'fake-01/result.json').read_text())
    def test_invalid_distribution_model_and_answer_reject(self):
        for change in ('sum','nan','missing','model','choice'):
            obj=response('jev')
            if change=='sum':obj['answers']['support']['probabilities']['supported']=.5
            if change=='nan':obj['answers']['support']['confidence']=float('nan')
            if change=='missing':del obj['answers']['role']
            if change=='model':obj['model']='jev-latest'
            if change=='choice':obj['answers']['support']['choice']='contradicted'
            with self.assertRaises(ValueError):v.parse_response(json.dumps(obj),'jev',{})
    def test_tied_choices_abstain_no_threshold_claim(self):
        obj=response('jev');obj['answers']['support'].update(choice='supported',confidence=.25,
          probabilities={'supported':.5,'contradicted':.5,'insufficient':0})
        r=v.parse_response(v.encode(obj),'jev',{})
        self.assertEqual(r['dimensions']['support']['label'],'insufficient')
        self.assertEqual(r['dimensions']['support']['confidence'],.25)
    def test_invalid_general_responses_not_repaired(self):
        for change in ('fence','extra','refusal','length','missing','model'):
            obj=response('openrouter');m=obj['choices'][0]['message']
            if change=='fence':m['content']='```json\n'+m['content']+'\n```'
            if change=='extra':m['content']=json.dumps({'support':'supported','invented_value':'2026-10-31'})
            if change=='refusal':m['refusal']='no'
            if change=='length':obj['choices'][0]['finish_reason']='length'
            if change=='missing':obj['choices']=[]
            if change=='model':obj['model']='other/model'
            with self.assertRaises((ValueError,KeyError)):v.parse_response(v.encode(obj),'openrouter',{})
    def test_duplicate_keys_and_nonfinite_json_reject(self):
        for s in ('{"a":1,"a":2}','{"a":NaN}'):
            with self.assertRaises(ValueError):v.loads(s)
    def test_caps_and_duplicates_preflight_no_calls(self):
        def forbidden(*a):self.fail('network attempted')
        for kwargs in ({'max_cases':21},{'max_input_tokens':1},{'max_estimated_cost':.000001},{'output_tokens':1025}):
            with self.assertRaises(ValueError):v.run_cases([fixture()],'openrouter',None,transport=forbidden,**kwargs)
        with self.assertRaises(ValueError):v.run_cases([fixture(),fixture()],'jev',None,transport=forbidden)
    def test_dry_run_no_env_or_network(self):
        with patch.dict('os.environ',{},clear=True):
            plan=v.run_cases([fixture()],'openrouter',None,transport=lambda *a:self.fail('network'))
        self.assertFalse(plan['live']);self.assertLess(plan['estimated_max_cost_usd'],.25)
    def test_raw_bytes_intent_retained_and_replay_blocks(self):
        raw=json.dumps(response('openrouter'),indent=3).encode();calls=[]
        def fake(*a):calls.append(a[0]);return 200,raw
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            v.run_cases([fixture()],'openrouter',out,live=True,key='FAKE-SECRET-ONLY',transport=fake)
            self.assertEqual((out/'fake-01/response.body').read_bytes(),raw)
            self.assertEqual(json.loads((out/'fake-01/intent.json').read_text())['status'],'pending_single_POST')
            with self.assertRaises(FileExistsError):v.run_cases([fixture()],'openrouter',out,live=True,key='FAKE-SECRET-ONLY',transport=fake)
            self.assertEqual(len(calls),1)
            self.assertFalse(any(b'FAKE-SECRET-ONLY' in p.read_bytes() for p in out.rglob('*') if p.is_file()))
    def test_uncertain_transport_stops_batch_without_retry(self):
        calls=[]; c2=fixture();c2['case_id']='fake-02'
        def fake(*a):calls.append(1);raise TimeoutError('secret-bearing URL not logged')
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with self.assertRaises(RuntimeError):v.run_cases([fixture(),c2],'jev',out,live=True,key='FAKE-SECRET-ONLY',transport=fake)
            self.assertEqual(len(calls),1);self.assertTrue((out/'fake-01/intent.json').exists())
            self.assertFalse((out/'fake-02').exists())
            self.assertNotIn('secret-bearing',(out/'fake-01/status.json').read_text())
    def test_bad_http_stops_no_retry(self):
        calls=[]
        def fake(*a):calls.append(1);return 429,b'{"error":"rate limit"}'
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with self.assertRaises(RuntimeError):v.run_cases([fixture()],'jev',out,live=True,key='FAKE-SECRET-ONLY',transport=fake)
            self.assertEqual(len(calls),1);self.assertEqual((out/'fake-01/response.body').read_bytes(),b'{"error":"rate limit"}')
    def test_echoed_credential_never_retained(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with self.assertRaises(RuntimeError):v.run_cases([fixture()],'jev',out,live=True,key='FAKE-SECRET-ONLY',transport=lambda *a:(200,b'FAKE-SECRET-ONLY'))
            self.assertFalse((out/'fake-01/response.body').exists())
    def test_secret_in_input_blocked_before_writes(self):
        c=fixture();c['source_text']+=' FAKE-SECRET-ONLY'
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            with self.assertRaises(ValueError):v.run_cases([c],'jev',out,live=True,key='FAKE-SECRET-ONLY',transport=lambda *a:self.fail('network'))
            self.assertFalse(out.exists())
    def test_blocked_citation_no_provider_calls(self):
        c=fixture();c['evidence'][0]['quote']='made up'
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            v.run_cases([c],'jev',out,live=True,key='FAKE-SECRET-ONLY',transport=lambda *a:self.fail('network'))
            result=json.loads((out/'fake-01/result.json').read_text())
            self.assertTrue(result['abstained']);self.assertEqual(result['case_id'],'fake-01')
            self.assertFalse((out/'fake-01/intent.json').exists())

if __name__=='__main__':
    unittest.main(verbosity=2)
