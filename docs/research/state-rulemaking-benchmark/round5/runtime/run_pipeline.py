#!/usr/bin/env python3
"""Frozen native-only deterministic→Jev research runtime."""
import argparse
import calendar
import datetime as dt
import fcntl
import importlib.util
import importlib.metadata
import platform
import json
import os
from pathlib import Path
import re
import sys
import jev_frozen as j
from operations import Ledger, Pause, Stop, now, put, sanitize_input, sha

FROZEN_JEV_SHA='8a0069d19f0fda7eaeac690c59749029b3ccea71fc07dfc2f8d311d2d872a59e'
# Only the reviewer-scoped-excerpt prefix changes. All judgment rubrics/gate remain round three.
OLD_PREFIX='For this scoped challenge, source_text is provided as an excerpt of candidate.target; target discovery/segmentation is not being evaluated. Still distinguish other events/targets explicitly mentioned. '
NOTICE_PREFIX='source_text is the entire acquired text of the supplied notice. candidate.target refers to this supplied notice, not a reviewer-selected excerpt. Distinguish other targets and event roles explicitly mentioned within the notice. Acquired text does not independently prove original-source fidelity or notice completeness. For comment_deadline, the actual ISO DATE projection must be an actual unconditional absolute written-comment close for this notice; quoting a conditional paragraph in claim or conditions does not make a conditional, anticipated, hearing-dependent or unresolved extended date acceptable. Printed clock/timezone qualifiers may coexist with date-only precision but are not certified. For submission_email, require an explicit written-comment/testimony route with applicable route limitations preserved; relative timing alone does not invalidate an independently explicit route. '
if not j.POLICY.startswith(OLD_PREFIX):raise Stop('frozen Jev policy mismatch')
j.POLICY=NOTICE_PREFIX+j.POLICY[len(OLD_PREFIX):]
SOFT_ISSUES={'submission_role_unverified','written_comment_role_unverified',
             'condition_scope_requires_semantic_verification','competing_temporal_role_cues',
             'form_association_requires_semantic_verification','multiple_email_candidates_require_role_resolution',
             'multiple_date_candidates_require_role_resolution'}
HARD_ISSUES={'empty_text','source_scope_incomplete_or_unknown','page_count_mismatch','replacement_character',
             'source_overlimit','case_overlimit','multiple_notice_or_rule_scopes',
             'date_year_order_or_range_unresolved','invalid_calendar_date','email_syntax_outside_supported_subset',
             'multiple_same_role_values_scope_unresolved','participation_lifecycle_unresolved',
             'relative_participation_window_unresolved','conditional_deadline_unresolved'}
EMAIL_MULTIPLICITY='multiple_email_candidates_require_role_resolution'
DATE_MULTIPLICITY='multiple_date_candidates_require_role_resolution'
FIELDS=('comment_deadline','submission_email')
LIMITS={'documents':8,'jev_cases':80,'nominal_total_usd':0.10,
        'jev_request_estimated_tokens':20000,'pdf_pages':40,'pdf_max_bytes':25_000_000}


def module_at(path):
    spec=importlib.util.spec_from_file_location('round5_proposer',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def routing_policy(pipeline):
    soft=set(pipeline.SOFT_ISSUES);hard=set(pipeline.HARD_ISSUES)
    allowed=SOFT_ISSUES|{EMAIL_MULTIPLICITY,DATE_MULTIPLICITY}
    if soft-allowed or soft & hard:raise Stop('pipeline issue policy exceeds approved semantic contract')
    return soft,hard


def code_pins(pipeline):
    module=module_at(Path(pipeline).resolve());soft,hard=routing_policy(module)
    root=Path(__file__).resolve().parent
    paths=[root/'run_pipeline.py',root/'operations.py',root/'jev_frozen.py',root/'run_with_1password.sh',Path(pipeline).resolve()]
    for name in ('INTERFACE.md','ROUTING-POLICY.json','SOURCE-INPUT-CONTRACT.md','source-input.schema.json'):
        contract=Path(pipeline).resolve().parent/name
        if contract.exists():paths.append(contract)
    guidance=root.parent/'protocol/CONTRACT-GUIDANCE.md'
    if guidance.exists():paths.append(guidance)
    if sha((root/'jev_frozen.py').read_bytes())!=FROZEN_JEV_SHA:raise Stop('round-three adapter changed')
    return {'schema_version':'round5.implementation.v1','code':{str(p):sha(p.read_bytes()) for p in paths},
            'pipeline_path':str(Path(pipeline).resolve()),'policy_sha256':sha(j.encode({'policy':j.POLICY,'rubrics':j.RUBRICS})),
            'soft_issues':sorted(soft),'hard_issues':sorted(hard),'unknown_issue_policy':'hard review',
            'limits':LIMITS,'python_version':platform.python_version(),
            'pypdf_version':importlib.metadata.version('pypdf'),'candidate_resolution':'per field: one supported value; every competing candidate completed and positively role mismatched',
            'runtime_channels':['native'],'provider':'jev','production_eligible':False}


def verify_implementation(freeze):
    f=j.loads(Path(freeze).read_bytes())
    if f!=code_pins(f['pipeline_path']):raise Stop('implementation pins changed; no execution')
    return f


def page_signals(pdf):
    """Original PDF page tree count only; no OCR or text extraction."""
    import io
    from pypdf import PdfReader
    return [{'pdf_page':i+1} for i in range(len(PdfReader(io.BytesIO(pdf)).pages))]


def load_documents(manifest_path,root,pipeline,signals=page_signals):
    manifest_path=Path(manifest_path).resolve();root=Path(root).resolve()
    if not manifest_path.is_relative_to(root):raise Stop('manifest outside source root')
    if manifest_path.stat().st_size>100000:raise Stop('oversize manifest')
    manifest=j.loads(manifest_path.read_bytes());pipeline.validate_manifest(manifest)
    units=manifest['documents']
    if len(units)>8 or any(u['channel']!='native' for u in units):raise Stop('native manifest cap/channel violation')
    if sum(u['pdf_pages'] for u in units)>LIMITS['pdf_pages']:raise Stop('corpus exceeds frozen PDF-page cap')
    result=[]
    for u in units:
        pdfpath=pipeline.contained_path(manifest_path.parent,root,u['pdf_path'])
        textpath=pipeline.contained_path(manifest_path.parent,root,u['text_path'])
        if pdfpath.stat().st_size>LIMITS['pdf_max_bytes'] or textpath.stat().st_size>2_000_000:raise Stop('source byte cap exceeded')
        pdf=pdfpath.read_bytes();raw=textpath.read_bytes()
        if sha(pdf)!=u['pdf_sha256'] or sha(raw)!=u['text_sha256']:raise Stop('source identity changed')
        rows=signals(pdf)
        if len(rows)!=u['pdf_pages']:raise Stop('actual PDF page count differs from manifest')
        result.append({'unit':u,'pdf':pdf,'text':raw.decode('utf-8'),'page_signals':rows})
    return result


def propose_channel(pipeline,doc,text,channel):
    u=doc['unit']
    if len(text)>30000:
        return {'document_id':u['document_id'],'channel':channel,'pipeline_version':pipeline.VERSION,
                'text_sha256':sha(text.encode()),'source_scope':u['scope'],
                'full_source_context_map':{'start':0,'end':len(text),'truncated':False},
                'routes':['review_source_overlimit_no_truncation'],'candidates':[],
                'production_eligible':False,'source_fidelity':'not_established','document_completeness':'requires_source_audit'}
    record=pipeline.propose(text,u['document_id'],scope=u['scope'],pdf_pages=u['pdf_pages'],
                            page_map_known=u['native_page_map_known'] if channel=='native' else False,channel=channel)
    if record['full_source_context_map']!={'start':0,'end':len(text),'truncated':False}:
        raise Stop('pipeline clipped full notice context')
    if record['document_id']!=u['document_id'] or record['channel']!='native' or record['source_scope']!=u['scope'] or record['text_sha256']!=sha(text.encode()):
        raise Stop('proposal source identity/scope differs')
    ids=[]
    for item in record['candidates']:
        case=item['case'];ids.append(case['case_id'])
        if case['source_text']!=text:raise Stop('case omits full notice text')
        if case.get('source_id')!=u['document_id'] or case['candidate']['target']!=u['document_id'] or case.get('source_locator')!='native':
            raise Stop('candidate provenance/target differs')
    if len(ids)!=len(set(ids)):raise Stop('duplicate candidate operation IDs')

    return record


def normalize_literal_date(raw):
    """Independent complete-literal supported calendar grammar; never infer a year."""
    if re.search(r'\n\s*\n|\f',raw):return None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):
        try:return dt.date.fromisoformat(raw).isoformat()
        except ValueError:return None
    names={m.lower():i for i,m in enumerate(calendar.month_name) if m}
    names.update({m.lower():i for i,m in enumerate(calendar.month_abbr) if m});names['sept']=9
    match=re.fullmatch(r'([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',raw,re.I)
    if not match or match[1].lower() not in names:return None
    try:return dt.date(int(match[3]),names[match[1].lower()],int(match[2])).isoformat()
    except ValueError:return None


def local_gate(item,soft_issues=None):
    if item.get('field') not in FIELDS:return None,{'blocking_issues':['unsupported_field']}
    clearable=set(SOFT_ISSUES if soft_issues is None else soft_issues)
    clearable-={DATE_MULTIPLICITY if item['field']=='submission_email' else EMAIL_MULTIPLICITY}

    hard=sorted(set(item['issues'])-clearable)
    # All unknown issues fail closed. Hard blockers are never overridden by a favorable model.
    if not item.get('emit_case') or hard:
        return None,{'blocking_issues':hard or ['case_not_emitted']}
    try:
        payload,gate=j.build_request(item['case'],'jev')
        if payload and len(j.encode(payload))+1024>20000:
            return None,{'blocking_issues':['request_overlimit_no_truncation']}
        value_span=item['value_span'];context_span=item['context_span'];c=item['case'];source=c['source_text']
        vs,ve,cs,ce=value_span['start'],value_span['end'],context_span['start'],context_span['end']
        if any(type(n) is not int for n in (vs,ve,cs,ce)) or not (0<=cs<=vs<ve<=ce<=len(source)) or source[cs:ce]!=context_span['quote']:
            return None,{'blocking_issues':['value_crosses_context_or_invalid_context_span']}
        if source[value_span['start']:value_span['end']]!=value_span['quote'] or value_span['quote']!=item['raw_literal']:
            return None,{'blocking_issues':['invalid_value_span']}
        if c['candidate']['field']=='submission_email' and c['candidate']['value']!=item['raw_literal']:
            return None,{'blocking_issues':['destination_value_literal_mismatch']}
        if c['candidate']['field']!=item['field']:
            return None,{'blocking_issues':['candidate_field_mismatch']}
        if item['field']=='comment_deadline':
            value=c['candidate']['value'];raw=item['raw_literal']
            if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
                return None,{'blocking_issues':['unsupported_date_projection']}
            try:dt.date.fromisoformat(value)
            except ValueError:return None,{'blocking_issues':['invalid_calendar_date']}
            if normalize_literal_date(raw)!=value:
                return None,{'blocking_issues':['literal_calendar_normalization_mismatch']}
            prefix=f'The actual unconditional absolute written-comment close date in the supplied notice is {raw} (date precision only).'
            if not c['candidate']['claim'].startswith(prefix):
                return None,{'blocking_issues':['unconditional_date_projection_claim_missing']}
        for span in item.get('condition_spans',[]):
            start,end=span['start'],span['end']
            if type(start) is not int or type(end) is not int or not (0<=start<end<=len(source)) or source[start:end]!=span['quote']:
                return None,{'blocking_issues':['invalid_condition_span']}
        return payload,gate
    except (ValueError,KeyError,TypeError):
        return None,{'blocking_issues':['candidate_schema_or_context_limit']}


def parse_jev(raw,gate):
    result=j.parse_response(raw,'jev',gate)
    result['observed_cost_usd']=result['usage']['input_tokens']*j.RATES['jev'][0]
    result['cost_basis']='reported input token usage × pinned Jev rate; output free'
    result['source_fidelity']='unverified';result['notice_completeness']='unverified'
    result['production_eligible']=False
    result['shadow_status']='text_supported' if result['disposition']=='accept_shadow' else 'review'
    return result


def verify_record(ledger,record,out,keys,soft_issues=None):
    out.mkdir(parents=True,exist_ok=True)
    put(out/'pipeline-record.json',sanitize_input(record,keys.values()))
    results=[]
    for item in record['candidates']:
        case=item['case']
        payload,gate=local_gate(item,soft_issues) if record['source_scope']=='full_notice' else (None,{'blocking_issues':['source_scope_incomplete_or_unknown']})
        if payload is None:
            result=j.abstain(','.join(gate['blocking_issues']),gate)
            result.update(shadow_status='review',source_fidelity='unverified',notice_completeness='unverified',production_eligible=False)
        else:
            result=ledger.operation(case['case_id'],'jev',payload,lambda raw,g=gate:parse_jev(raw,g),
                     identity={'case_sha256':sha(j.encode(case)),'document_id':record['document_id'],'channel':record['channel']},
                     reserve=(len(j.encode(payload))+1024)*j.RATES['jev'][0])
        result={**result,'case_id':case['case_id'],'field':item['field'],'candidate_value':case['candidate']['value'],
                'channel':record['channel'],'pipeline_issues':item['issues'],'raw_literal':item['raw_literal'],'stage':'provisional_channel_judgment'}
        results.append(result)
    results=resolve_email_multiplicity(results)
    for result in results:
        put(out/(result['case_id']+'.json'),sanitize_input(result,keys.values()))
    put(out/'results.json',results)
    return results


def resolve_email_multiplicity(results):
    """Same conservative competition policy for both fields, even without an issue flag."""
    for field in FIELDS:
        rows=[r for r in results if r['field']==field]
        winners={j.encode(r['candidate_value']).decode() for r in rows if r['shadow_status']=='text_supported'}
        resolved=False
        if len(winners)==1:
            winner=next(iter(winners))
            resolved=all((r['shadow_status']=='text_supported' if j.encode(r['candidate_value']).decode()==winner else
                          r.get('operation_status')=='completed' and r.get('dimensions',{}).get('role',{}).get('label')=='mismatched') for r in rows)
        for row in rows:
            row['field_competition_resolved']=resolved
            if resolved and row['shadow_status']!='text_supported':row['classified_other_role']=True
            elif not resolved:
                row['shadow_status']='review';row['disposition']='review';row['action_readiness']='not_ready'
    return results


def terminal_shadow(native,scope):
    observations=[]
    for row in native:
        acceptable=row['shadow_status']=='text_supported' and scope=='full_notice'
        observations.append({**row,'shadow_status':'text_supported' if acceptable else 'review',
            'disposition':'accept_shadow' if acceptable else 'review',
            'action_readiness':'requires_source_verification' if acceptable else 'not_ready',
            'stage':'terminal_shadow_observation','channel_disagreement':False,'unresolved_channel_evidence':False,
            'production_eligible':False,'source_fidelity':'unverified','notice_completeness':'unverified'})
    return {'observations':observations,'channel_disagreement_fields':[],'channel_unresolved_fields':[],
        'document_completeness':'requires_independent_source_audit','source_fidelity':'not_verified',
        'production_eligible':False,'action_ready':False}


def provider_post_once(provider,payload,key):
    if provider!='jev':raise Stop('native-only runtime refuses other providers')
    return j.post_once('jev',payload,key)


def run(manifest,source_root,freeze,out,*,live=False,authorization=None,max_new=1,budget=0.10,
        transport=provider_post_once,signals=page_signals,keys=None,source_labels_freeze_sha256=None):
    if not 0<budget<=0.10 or type(max_new) is not int or not 0<=max_new<=80:
        raise Stop('runtime caps exceeded')
    impl=verify_implementation(freeze);pipeline=module_at(impl['pipeline_path']);soft_issues,_=routing_policy(pipeline)
    docs=load_documents(manifest,source_root,pipeline,signals)
    pins={'implementation':impl,'manifest_sha256':sha(Path(manifest).read_bytes()),'source_root':str(Path(source_root).resolve()),
          'limits':LIMITS,'budget':budget,'documents':[d['unit'] for d in docs]}
    records=[propose_channel(pipeline,d,d['text'],'native') for d in docs]
    candidates=sum(len(r['candidates']) for r in records)
    if candidates>80:raise Stop('native proposals exceed 80-case cap')
    plan={'documents':len(docs),'pdf_pages':sum(d['unit']['pdf_pages'] for d in docs),'native_candidates':candidates,
          'manifest_sha256':pins['manifest_sha256'],'production_eligible':False,'live':live,
          'max_nominal_reserved_usd':80*20000*j.RATES['jev'][0]}
    if not live:return plan
    if not authorization:raise Stop('live requires frozen source-label/implementation attestation')
    if not isinstance(source_labels_freeze_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',source_labels_freeze_sha256):
        raise Stop('live requires external source-label freeze hash; no labels read')
    auth=j.loads(Path(authorization).read_bytes())
    required={'schema_version':'round5.live-authorization.v1','implementation_sha256':sha(Path(freeze).read_bytes()),
              'manifest_sha256':pins['manifest_sha256'],'source_labels_frozen_before_outputs':True,'source_labels_freeze_sha256':source_labels_freeze_sha256,'nominal_budget_usd':budget}
    if auth!=required:raise Stop('live authorization differs from pins or labels-freeze attestation')
    pins['authorization_sha256']=sha(Path(authorization).read_bytes())
    pins['source_labels_freeze_sha256']=source_labels_freeze_sha256
    out=Path(out);out.mkdir(parents=True,exist_ok=True);keys=keys or {}
    with (out/'runner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger=Ledger(out,pins,max_new=max_new,budget=budget,transport=transport,keys=keys)
        put(out/'plan.json',sanitize_input(plan,keys.values()))
        document_results=[]
        try:
            for doc,record in zip(docs,records):
                folder=out/'documents'/doc['unit']['document_id'];folder.mkdir(parents=True,exist_ok=True)
                native=verify_record(ledger,record,folder/'native',keys,soft_issues)
                merged=terminal_shadow(native,doc['unit']['scope'])
                merged.update(document_id=doc['unit']['document_id'],fallback_decision='native_only_no_ocr')
                put(folder/'shadow-observations.json',merged);document_results.append(merged)
            put(out/'completed.json',{'documents':document_results,'totals':ledger.totals(),'production_eligible':False})
            return {**plan,'state':'completed','totals':ledger.totals()}
        except Pause as e:
            # Pause is an operation cap/budget boundary, not permission to retry a POST.
            return {**plan,'state':'paused_at_operation_boundary','reason':str(e),'totals':ledger.totals()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pipeline',type=Path,help='only used for --prepare-implementation')
    p.add_argument('--prepare-implementation',type=Path,help='save code-only freeze; never reads source files')
    p.add_argument('--freeze',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--source-root',type=Path)
    p.add_argument('--output',type=Path);p.add_argument('--authorization',type=Path)
    p.add_argument('--source-labels-freeze-sha256',help='externally bound label freeze receipt hash; runtime reads no labels')
    p.add_argument('--live',action='store_true');p.add_argument('--max-new',type=int,default=1)
    p.add_argument('--budget',type=float,default=0.10)
    a=p.parse_args()
    try:
        if a.prepare_implementation:
            if not a.pipeline:raise Stop('pipeline path required')
            put(a.prepare_implementation,code_pins(a.pipeline));print('Implementation pins saved; no sources read.');return
        if not all((a.freeze,a.manifest,a.source_root,a.output)):raise Stop('missing runtime arguments')
        keys={'jev':os.environ.get('TYPESAFE_API_KEY')} if a.live else {}
        result=run(a.manifest,a.source_root,a.freeze,a.output,live=a.live,authorization=a.authorization,
                   max_new=a.max_new,budget=a.budget,keys=keys,source_labels_freeze_sha256=a.source_labels_freeze_sha256)
        print(json.dumps(result,indent=2))
    except (Stop,ValueError,OSError,KeyError,TypeError):
        p.exit(1,'Round-five runtime stopped. Inspect retained artifacts and pins; no automatic provider retry.\n')

if __name__=='__main__':main()
