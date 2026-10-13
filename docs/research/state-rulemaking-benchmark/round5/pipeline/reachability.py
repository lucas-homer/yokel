#!/usr/bin/env python3
"""Development-only native dispatch audit; never calls a provider or reads labels."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import pipeline as p

def runtime_module():
    directory=Path(__file__).resolve().parents[1]/'runtime'
    sys.path.insert(0,str(directory))
    if 'run_pipeline' in sys.modules:
        r=sys.modules['run_pipeline']
        if Path(r.__file__).resolve().parent!=directory:raise ValueError('wrong runtime cached')
        return r
    spec=importlib.util.spec_from_file_location('run_pipeline',directory/'run_pipeline.py')
    r=importlib.util.module_from_spec(spec);sys.modules['run_pipeline']=r;spec.loader.exec_module(r)
    return r

def audit(manifest,source_root):
    r=runtime_module();soft,hard=r.routing_policy(p);p.validate_manifest(manifest)
    documents=[]
    for u in manifest['documents']:
        base=Path(__file__).resolve().parent
        raw=p.contained_path(base,source_root,u['text_path']).read_bytes()
        pdf=p.contained_path(base,source_root,u['pdf_path']).read_bytes()
        assert p.sha(raw)==u['text_sha256'] and p.sha(pdf)==u['pdf_sha256']
        text=raw.decode('utf-8');record=p.propose(text,u['document_id'],scope=u['scope'],pdf_pages=u['pdf_pages'],page_map_known=u['native_page_map_known'])
        rows=[]
        for item in record['candidates']:
            payload,gate=r.local_gate(item,soft)
            for sp in item['case']['evidence']:assert text[sp['start']:sp['end']]==sp['quote']
            assert item['case']['source_text']==text
            rows.append({'case_id':item['case_id'],'field':item['field'],'literal':item['raw_literal'],'value_span':item['value_span'],'context_span':item['context_span'],'condition_spans':item['condition_spans'],'proposal_eligible':item['verifier_eligible'],'actual_runtime_gate_reachable':payload is not None,'runtime_gate':gate,'hard_issues':item['hard_issues'],'soft_issues':item['soft_issues'],'source_text_hash':record['text_sha256'],'full_source_preserved':True})
        documents.append({'document_id':u['document_id'],'scope':u['scope'],'routes':record['routes'],'lifecycle_cues':record['lifecycle_cues'],'qualification_cues':record['qualification_cues'],'candidates':rows})
    return {'developmental_only':True,'source_accuracy_measured':False,'documents':documents,'candidate_rows':sum(len(d['candidates']) for d in documents),'runtime_reachable_rows':sum(i['actual_runtime_gate_reachable'] for d in documents for i in d['candidates']),'by_field':{f:{'candidates':sum(i['field']==f for d in documents for i in d['candidates']),'runtime_reachable':sum(i['field']==f and i['actual_runtime_gate_reachable'] for d in documents for i in d['candidates'])} for f in ('comment_deadline','submission_email')},'provider_calls':0,'OCR_calls':0}

def actual_runtime_controls():
    """Use B's actual production entrypoint with its fake transport fixtures."""
    r=runtime_module()
    spec=importlib.util.spec_from_file_location('round5_runtime_controls',Path(r.__file__).with_name('offline_checks.py'))
    tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
    summaries=[]
    pairs=[('positive_incidental',tests.POSITIVE),('conditional_negative','Written comments close October 31, 2026 if a hearing is requested.'),('relative_email','Written comments are due within 30 days after publication.\n\nSubmit written comments to comments@example.gov.')]
    for name,text in pairs:
        with tempfile.TemporaryDirectory(prefix='round5-proposer-control-') as tmp,contextlib.redirect_stdout(io.StringIO()):
            result,terminal,calls,_=tests.execute(tmp,text,fake=lambda payload:(200,tests.response(payload,{'role':'mismatched'} if payload['state']['candidate']['value']=='access@example.gov' else {})))
        passed=[row for row in terminal['observations'] if row['shadow_status']=='text_supported']
        assert result['state']=='completed' and terminal['action_ready'] is False
        if name=='conditional_negative':assert not calls and not passed
        elif name=='relative_email':assert calls and any(row['field']=='submission_email' for row in passed)
        else:assert calls and {row['field'] for row in passed}=={'comment_deadline','submission_email'}
        summaries.append({'control':name,'fake_transport_requests':len(calls),'terminal_text_supported_fields':[row['field'] for row in passed],'conditional_DATE_stayed_review':name!='conditional_negative' or not passed,'all_full_source_preserved':all(payload['state']['source_text']==text for payload in calls),'action_ready':terminal['action_ready'],'production_eligible':terminal['production_eligible']})
    return {'controls':summaries,'real_provider_calls':0,'warning':'Fake responses test dispatch/terminal policy, not semantic model quality.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    directory=Path(__file__).resolve().parent
    report=audit(json.loads((directory/'development-inputs.json').read_bytes()),directory.parents[1])
    report['actual_runtime_fake_controls']=actual_runtime_controls()
    with args.output.open('x') as file:json.dump(report,file,indent=2,ensure_ascii=False);file.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='documents'},indent=2))
