#!/usr/bin/env python3
"""Read-only audit of finished/stopped execution. No source labels or provider calls."""
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

B=Path(__file__).resolve().parents[2]
R=B/'execution/run'
O=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def load(p):return json.loads(Path(p).read_bytes())
def enc(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(b):return hashlib.sha256(b).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stopped',action='store_true',help='primary signaled run stopped; never infer from a transient pause')
    args=parser.parse_args()
    if not (R/'completed.json').exists() and not args.stopped:
        print('Waiting for completed.json or primary stop signal; final totals not emitted.');return
    # Snapshot only execution artifacts, avoiding source labels/reference directories.
    before={str(p.relative_to(R)):sha(p) for p in R.rglob('*') if p.is_file()}
    checks=[]
    def ck(name,ok,detail=None):checks.append({'check':name,'pass':bool(ok),'detail':detail})
    pins=load(R/'pins.json');impl=pins['implementation'];manifest=load(B/'sources/source-inputs.json')
    ck('manifest-pin',sha(B/'sources/source-inputs.json')==pins['manifest_sha256'])
    ck('READY-implementation-equality',impl==load(B/'runtime/implementation-pins.READY.json'))
    for path,h in impl['code'].items():ck('code-'+Path(path).name,sha(path)==h)
    a=load(B/'execution/freeze-A.json')
    for item in a['files']:ck('freeze-A-'+item['path'],sha(B/item['path'])==item['sha256'])
    # Authorization is metadata only; labels themselves are not opened, hashed or evaluated.
    auth_paths=[p for p in (B/'execution').glob('*.json') if sha(p)==pins.get('authorization_sha256')]
    ck('retained-authorization-found',len(auth_paths)==1)
    if auth_paths:
        auth=load(auth_paths[0]);ck('label-freeze-attestation',auth.get('source_labels_frozen_before_outputs') is True)
        ck('authorization-implementation',auth.get('implementation_sha256')==sha(B/'runtime/implementation-pins.READY.json'))
        ck('authorization-manifest',auth.get('manifest_sha256')==pins['manifest_sha256'])
    documents={u['document_id']:u for u in manifest['documents']}
    ck('same-document-set',pins['documents']==manifest['documents'])
    for ident,u in documents.items():
        for kind in ('pdf','text'):
            p=(B/'sources'/u[kind+'_path']).resolve()
            ck('confined-'+ident+'-'+kind,p.is_relative_to((B/'sources').resolve()))
            ck('source-'+ident+'-'+kind,sha(p)==u[kind+'_sha256'])
    ops=[];seen=[];invoice=0.0;jev_estimate=0.0;reserved=0.0;charged=0.0;ocr_starts=[]
    kinds=collections.Counter();result_states=collections.Counter();stop_states=collections.Counter()
    for folder in sorted((R/'operations').iterdir()):
        if not folder.is_dir() or not (folder/'intent.json').exists():continue
        intent=load(folder/'intent.json');identity=load(folder/'identity.json');request=load(folder/'request.json')
        kind=intent['kind'];kinds[kind]+=1;seen.append(intent['operation_id'])
        ck('request-hash-'+folder.name,sha(folder/'request.json')==intent['request_sha256']==identity['request_sha256'])
        ck('operation-pin-'+folder.name,intent['pins_sha256']==sha(R/'pins.json'))
        ck('single-attempt-policy-'+folder.name,intent['automatic_retry'] is False)
        reserved+=intent['reserved_nominal_usd'];accounted=None;actual=None;result=None
        response_present=(folder/'response.body').exists()
        if (folder/'stop.json').exists():stop_states[load(folder/'stop.json')['state']]+=1
        if response_present:
            status=load(folder/'status.json');raw=load(folder/'response.body')
            ck('response-hash-'+folder.name,sha(folder/'response.body')==status['response_sha256'])
            ck('HTTP-200-'+folder.name,status['http_status']==200)
            if (folder/'result.json').exists():
                result=load(folder/'result.json');accounted=result.get('observed_cost_usd');result_states['completed']+=1
                ck('usage-retained-'+folder.name,isinstance(raw.get('usage'),dict) and result.get('usage')==raw['usage'])
                if kind=='ocr':
                    actual=raw['usage'].get('cost');invoice+=actual
                    ck('OCR-reported-cost-'+folder.name,result['reported_cost_usd']==actual)
                    ck('OCR-accounting-'+folder.name,abs(accounted-(actual+intent['pages']*.002))<1e-10)
                    ck('OCR-model-'+folder.name,request['model']==raw['model']=='google/gemma-3-27b-it')
                    ck('explicit-Mistral-'+folder.name,request['plugins']==[{'id':'file-parser','pdf':{'engine':'mistral-ocr'}}])
                    ck('no-provider-retry-'+folder.name,request['provider']['allow_fallbacks'] is False)
                    annotations=raw['choices'][0]['message'].get('annotations',[])
                    files=[x for x in annotations if x.get('type')=='file']
                    text='\n\n'.join(p['text'] for x in files for p in x['file']['content'] if p.get('type')=='text' and isinstance(p.get('text'),str))
                    ck('annotation-only-text-'+folder.name,len(files)==1 and text==result['text'])
                    ck('annotation-text-hash-'+folder.name,digest(text.encode())==result['text_sha256'])
                    ck('no-completion-or-images-as-Jev-source-'+folder.name,result['downstream_completion_used_as_source'] is False and result['image_parts_to_Jev'] is False)
                    decision=load(R/'documents'/intent['identity']['document_id']/'fallback-decision.json')
                    ck('fallback-decision-pin-'+folder.name,digest(enc(decision))==intent['identity']['decision_sha256'])
                elif kind=='jev':
                    estimated=raw['usage']['input_tokens']*.000000042;jev_estimate+=estimated
                    ck('Jev-usage-estimate-'+folder.name,abs(accounted-estimated)<1e-10)
                    ck('Jev-model-'+folder.name,request['model']==raw['model']=='jev-1.13.0')
                    ck('Jev-state-whitelist-'+folder.name,set(request['state'])=={'source_text','candidate','evidence'})
                    ck('four-Choice-questions-'+folder.name,set(request['questions'])=={'support','role','condition','conflict'} and all(q['type']=='choice' for q in request['questions'].values()))
                    ck('raw-Jev-labels-'+folder.name,all(result['dimensions'][k]['raw_label']==raw['answers'][k]['choice'] for k in raw['answers']))
                ck('unverified-source-result-'+folder.name,result.get('source_fidelity')=='unverified')
            else:result_states['response_without_result']+=1
        else:result_states['uncertain_without_response']+=1
        charged+=max(intent['reserved_nominal_usd'],accounted if accounted is not None else 0)
        if kind=='ocr':ocr_starts.append(dt.datetime.fromisoformat(intent['created_utc']).timestamp())
        ops.append({'operation_id':intent['operation_id'],'kind':kind,'document_id':intent['identity']['document_id'],
                    'pages':intent['pages'],'reserved_nominal_usd':intent['reserved_nominal_usd'],
                    'provider_reported_usd':actual,'estimated_or_conservative_accounted_usd':accounted,
                    'response_present':response_present,'result_present':result is not None})
    ck('unique-provider-operation-IDs',len(seen)==len(set(seen)))
    ocr_starts.sort();gaps=[b-a for a,b in zip(ocr_starts,ocr_starts[1:])]
    ck('OCR-start-pacing',all(g>=22 for g in gaps),gaps)
    ck('Jev-case-cap',kinds['jev']<=120);ck('OCR-page-cap',sum(o['pages'] for o in ops if o['kind']=='ocr')<=60)
    ck('conservative-accounting-cap',charged<=pins['budget'],charged)
    document_rows=[];native_reasons=collections.Counter();fallback_reasons=collections.Counter();decisions=collections.Counter();terminal_status=collections.Counter()
    for ident,u in documents.items():
        folder=R/'documents'/ident;row={'document_id':ident,'scope':u['scope'],'pdf_pages':u['pdf_pages'],'scheduled':True}
        for channel in ('native','fallback'):
            c=folder/channel
            if (c/'pipeline-record.json').exists():
                record=load(c/'pipeline-record.json');results=load(c/'results.json') if (c/'results.json').exists() else []
                row[channel+'_proposed_candidates']=len(record['candidates']);row[channel+'_result_count']=len(results)
                ck('untruncated-context-'+ident+'-'+channel,record['full_source_context_map']['truncated'] is False)
                ck('raw-literal-retained-'+ident+'-'+channel,all('raw_literal' in r for r in results))
                reasons=native_reasons if channel=='native' else fallback_reasons
                for r in results:
                    if r.get('operation_status')=='not_attempted':reasons.update(r['deterministic']['blocking_issues'])
                row[channel+'_provider_completed']=sum(r.get('operation_status')=='completed' for r in results)
                row[channel+'_deterministic_reviews']=sum(r.get('operation_status')=='not_attempted' for r in results)
        if (folder/'fallback-decision.json').exists():
            d=load(folder/'fallback-decision.json');row['fallback_decision']=d['decision'];row['fallback_reasons']=d['reasons'];decisions[d['decision']]+=1
            ck('decision-no-prior-fallback-'+ident,d['fallback_text_read_before_decision'] is False)
        if (folder/'shadow-observations.json').exists():
            final=load(folder/'shadow-observations.json');row['state']='completed'
            row['terminal_observations']=len(final['observations']);row['text_supported']=sum(x['shadow_status']=='text_supported' for x in final['observations'])
            row['terminal_review']=sum(x['shadow_status']=='review' for x in final['observations'])
            row['channel_disagreement_fields']=final['channel_disagreement_fields'];row['channel_unresolved_fields']=final['channel_unresolved_fields']
            ck('terminal-research-only-'+ident,final['production_eligible'] is False and final['action_ready'] is False)
            ck('terminal-completeness-unverified-'+ident,final['document_completeness']=='requires_independent_source_audit' and final['source_fidelity']=='not_verified')
            for o in final['observations']:
                terminal_status[o['shadow_status']]+=1
                ck('terminal-indicators-'+ident+'-'+o['case_id'],o['stage']=='terminal_shadow_observation' and (o['shadow_status']!='review' or o['disposition']=='review' and o['action_readiness']=='not_ready'))
        else:row['state']='partial' if folder.exists() else 'not_started'
        document_rows.append(row)
    completed=(R/'completed.json').exists()
    if completed:
        ck('all-scheduled-documents-completed',all(x['state']=='completed' for x in document_rows))
        totals=load(R/'completed.json')['totals'];ck('receipt-operation-count',totals['operations']==len(ops))
        ck('receipt-Jev-count',totals['jev_cases']==kinds['jev']);ck('receipt-reservations',abs(totals['nominal_reserved_usd']-reserved)<1e-10)
        ck('receipt-accounting',abs(totals['budget_charge_usd']-charged)<1e-10)
    after={str(p.relative_to(R)):sha(p) for p in R.rglob('*') if p.is_file()}
    ck('execution-files-unchanged-during-audit',before==after)
    result={'status':'completed_execution_audit' if completed else 'stopped_execution_audit','checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'checks_passed':sum(c['pass'] for c in checks),'checks_total':len(checks),'failed_checks':[c for c in checks if not c['pass']],
            'scheduled_documents':len(documents),'document_states':dict(collections.Counter(r['state'] for r in document_rows)),
            'operations':ops,'provider_counts':dict(kinds),'provider_result_states':dict(result_states),'stop_states':dict(stop_states),
            'OCR_pages':sum(o['pages'] for o in ops if o['kind']=='ocr'),'OCR_start_gaps_seconds':gaps,
            'costs':{'OpenRouter_reported_usd':invoice,'Jev_usage_rate_estimated_usd':jev_estimate,'nominal_reserved_usd':reserved,
                     'conservative_budget_charge_usd':charged,'unknown_cost_operations':sum(o['estimated_or_conservative_accounted_usd'] is None for o in ops),
                     'total_actual_invoice_verified':False},
            'routing':{'decisions':dict(decisions),'native_deterministic_block_reasons':dict(native_reasons),
                       'fallback_deterministic_block_reasons':dict(fallback_reasons),'terminal_statuses':dict(terminal_status)},
            'documents':document_rows,'provider_calls_by_audit':0,'source_labels_read':False,'proposer_executed_by_audit':False,
            'execution_artifacts_unchanged':before==after,'execution_artifact_count':len(before)}
    (O/'audit.json').write_text(json.dumps(result,indent=2)+'\n');(O/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (O/'execution-hashes.json').write_text(json.dumps(before,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','checks_passed','checks_total','failed_checks','provider_counts','OCR_pages','costs','routing','document_states')},indent=2))

if __name__=='__main__':main()
