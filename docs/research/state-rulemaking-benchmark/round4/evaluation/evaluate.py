#!/usr/bin/env python3
"""Offline terminal source-audit evaluator. Never imports/calls the runtime."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path

TYPES=('DATE','EMAIL')
FIELDS={'comment_deadline':'DATE','submission_email':'EMAIL'}
ROLES={'DATE':'written_comment_close','EMAIL':'written_comment_submission_email'}
STATES={'present_in_scope','present_out_of_scope','not_stated','explicit_negative','unresolved_conflict','unresolved_uncertainty'}
NOTICE_KEYS={'opaque_document_id','original_pdf_sha256','retained_pdf_sha256','official_url','physical_page_mapping','all_source_pages_viewed','complete_notice_scope','source_states_for_both_fields','required_field_values','scan_degradation_basis','reviewer_identity','reviewed_at_utc','fields'}
FIELD_KEYS={'field_id','field_type','source_state','raw_literal','page_region','exact_source_quote','role','conditions','supported_scope','distinct_value_group','uncertainty_reason_if_any','normalized_value','source_precision'}

def digest(data):return hashlib.sha256(data).hexdigest()

def valid_date(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return False
    try:datetime.date.fromisoformat(value);return True
    except ValueError:return False

def eligible(field):
    return (field['source_state']=='present_in_scope' and field['supported_scope'] is True and field['role']==ROLES[field['field_type']] and
            (valid_date(field['normalized_value']) and field['source_precision']=='date' if field['field_type']=='DATE' else
             isinstance(field['normalized_value'],str) and bool(field['normalized_value']) and field['source_precision']=='literal_email' and field['raw_literal']==field['normalized_value']))

def validate_labels(labels,units):
    if labels.get('schema_version')!='round4.evaluation.labels.v1' or not isinstance(labels.get('documents'),list):raise ValueError('invalid labels envelope')
    out={}
    for notice in labels['documents']:
        if not NOTICE_KEYS <= notice.keys():raise ValueError('missing notice source-label fields')
        doc=notice['opaque_document_id']
        if doc not in units or doc in out:raise ValueError('unscheduled/duplicate source label')
        if notice['retained_pdf_sha256']!=units[doc]['pdf_sha256']:raise ValueError('source-label retained PDF differs from schedule')
        if type(notice['all_source_pages_viewed']) is not bool or type(notice['complete_notice_scope']) is not bool:raise ValueError('invalid label completeness')
        if set(notice['source_states_for_both_fields'])!=set(TYPES):raise ValueError('both source field states required')
        fields={};groups={}
        for field in notice['fields']:
            if not FIELD_KEYS <= field.keys() or field['field_type'] not in TYPES or field['source_state'] not in STATES:raise ValueError('invalid source field')
            if field['field_id'] in fields:raise ValueError('duplicate source field ID')
            if not isinstance(field['conditions'],list) or not all(isinstance(c,str) for c in field['conditions']) or type(field['supported_scope']) is not bool:raise ValueError('invalid source condition/scope')
            fields[field['field_id']]=field
            group=(field['field_type'],field['distinct_value_group'])
            semantics=(field['source_state'],field['role'],field['normalized_value'],field['source_precision'],field['supported_scope'],tuple(field['conditions']))
            if group in groups and groups[group]!=semantics:raise ValueError('group merges materially different source facts')
            groups[group]=semantics
            if field['source_state']=='present_in_scope' and not eligible(field):raise ValueError('in-scope supported field lacks explicit typed normalization/role')
        for typ in TYPES:
            actual={f['source_state'] for f in fields.values() if f['field_type']==typ}
            stated=set(notice['source_states_for_both_fields'][typ])
            if not actual or actual!=stated:raise ValueError('source states not represented by field rows')
        required={f['field_id'] for f in fields.values() if eligible(f)}
        if set(notice['required_field_values'])!=required:raise ValueError('required field list differs from source-eligible fields')
        out[doc]=notice
    return out

def ratio(n,d,reason='zero_denominator'):
    return {'numerator':n,'denominator':d,'value':n/d if d else None,'undefined_reason':None if d else reason}

def evaluate(manifest,labels,terminal_documents,acceptance_audits,stage_states=None):
    if manifest.get('schema_version')!='round4.sources.v1':raise ValueError('not a frozen source manifest')
    units={u['document_id']:u for u in manifest['documents']}
    if len(units)!=len(manifest['documents']) or any(not re.fullmatch(r'doc-[a-f0-9]{12}',doc) for doc in units):raise ValueError('duplicate/nonopaque schedule')
    source=validate_labels(labels,units)
    if set(terminal_documents)-units.keys():raise ValueError('unscheduled terminal output')
    if acceptance_audits.get('schema_version')!='round4.evaluation.audits.v1':raise ValueError('invalid audit envelope')
    audit={}
    for a in acceptance_audits['audits']:
        key=(a['document_id'],a['channel'],a['case_id'])
        if key in audit or key[0] not in units:raise ValueError('duplicate/unscheduled audit')
        enums={'source_value':{'correct','incorrect','unknown'},'role':{'matched','mismatched','unknown'},'conditions':{'preserved','lost_or_changed','unknown'},'precision':{'date_only','exact_literal','mismatched','unknown'},'scope':{'matched','out_of_scope','unknown'}}
        if not all(a.get(k) in values for k,values in enums.items()) or not a.get('reviewer_identity') or not a.get('basis') or not a.get('claim_group'):raise ValueError('invalid/incomplete acceptance audit')
        if a['source_field_id'] is not None and (key[0] not in source or a['source_field_id'] not in {f['field_id'] for f in source[key[0]]['fields']}):raise ValueError('audit references missing source field')
        audit[key]=a
    stage_states=stage_states or {}
    recovered=set();eligible_groups=set();accepted_groups={};accepted_signatures={};raw_accepts=0;documents=[]
    labels_complete=bool(units) and len(source)==len(units) and all(n['all_source_pages_viewed'] and n['complete_notice_scope'] for n in source.values())
    unsupported=[];readiness_total=0;false_readiness=0;ocr_requests=0
    for doc,unit in units.items():
        notice=source.get(doc);terminal=terminal_documents.get(doc)
        if terminal is not None and terminal.get('document_id')!=doc:raise ValueError('terminal document ID differs')
        state='terminal' if terminal is not None else 'partial' if stage_states.get(doc,{}).get('started') else 'not_started'
        byid={f['field_id']:f for f in notice['fields']} if notice else {}
        required={(doc,f['field_type'],f['distinct_value_group']) for f in byid.values() if eligible(f)}
        eligible_groups.update(required)
        observed=[];unsafe_doc=False
        for row in terminal.get('observations',[]) if terminal else []:
            if row.get('shadow_status')!='text_supported':continue
            raw_accepts+=1
            typ=FIELDS.get(row.get('field'),'UNKNOWN');key=(doc,row.get('channel'),row.get('case_id'));a=audit.get(key)
            f=byid.get(a['source_field_id']) if a else None
            reasons=[]
            if not notice or not notice['all_source_pages_viewed'] or not notice['complete_notice_scope']:reasons.append('source_audit_incomplete')
            if not a:reasons.append('terminal_acceptance_unaudited')
            else:
                if a['source_value']!='correct':reasons.append('source_value_'+a['source_value'])
                if a['role']!='matched':reasons.append('wrong_or_unknown_role')
                if a['conditions']!='preserved':reasons.append('lost_or_unknown_conditions')
                if a['scope']!='matched':reasons.append('out_of_scope_or_unknown_scope')
                if a['precision']!=('date_only' if typ=='DATE' else 'exact_literal' if typ=='EMAIL' else None):reasons.append('wrong_or_unknown_precision')
            if not f or not eligible(f) or f['field_type']!=typ:reasons.append('not_a_source_eligible_instance')
            elif row.get('candidate_value')!=f['normalized_value']:reasons.append('normalized_value_mismatch')
            if typ=='DATE' and not valid_date(row.get('candidate_value')):reasons.append('invalid_or_non_date_precision')
            if typ=='EMAIL' and (row.get('raw_literal')!=row.get('candidate_value') or (f and row.get('candidate_value')!=f['raw_literal'])):reasons.append('email_not_exact_source_literal')
            conflict=any(x['field_type']==typ and x['source_state']=='unresolved_conflict' and x['role']==ROLES.get(typ) for x in byid.values())
            uncertainty=any(x['field_type']==typ and x['source_state']=='unresolved_uncertainty' and x['role']==ROLES.get(typ) for x in byid.values())
            if conflict:reasons.append('accepted_source_conflict')
            if uncertainty:reasons.append('accepted_source_uncertainty')
            unauditable=not notice or not notice['all_source_pages_viewed'] or not notice['complete_notice_scope'] or not a or not f or any(a.get(k)=='unknown' for k in ('source_value','role','conditions','precision','scope'))
            source_incorrect=bool((a and (a['source_value']=='incorrect' or a['role']=='mismatched' or a['conditions']=='lost_or_changed' or a['precision']=='mismatched' or a['scope']=='out_of_scope')) or any(x in reasons for x in ('normalized_value_mismatch','email_not_exact_source_literal','invalid_or_non_date_precision')) or (f and f['source_state'] in ('present_out_of_scope','not_stated','explicit_negative')))
            group=(doc,typ,a['claim_group'] if a else 'unaudited:'+str(key[1:]))
            source_mapping_verified=bool(a and f and a['source_value']=='correct' and a['role']=='matched' and a['conditions']=='preserved' and a['precision']==('date_only' if typ=='DATE' else 'exact_literal') and a['scope'] in ('matched','out_of_scope') and row.get('candidate_value')==f['normalized_value'])
            source_fact=(f['field_type'],f['distinct_value_group'],f['role'],tuple(f['conditions']),f['source_precision'],f['supported_scope'],f['source_state']) if f else None
            signature=(json.dumps(row.get('candidate_value'),sort_keys=True,ensure_ascii=False,allow_nan=False),source_fact)
            if group in accepted_signatures and accepted_signatures[group]!=signature:
                raise ValueError('materially inconsistent accepted claim_group')
            accepted_signatures[group]=signature
            claim={'source_mapping_verified':source_mapping_verified,'mapped_source_group':f['distinct_value_group'] if f else None,'document_id':doc,'field_type':typ,'case_id':row.get('case_id'),'channel':row.get('channel'),'source_field_id':a['source_field_id'] if a else None,'unsafe_reasons':sorted(set(reasons)),'source_conflict':conflict,'source_uncertainty':uncertainty,'source_incorrect':source_incorrect,'unauditable':unauditable}
            # Duplicate audited mentions share claim_group. Any unsafe duplicate
            # taints the group; source recovery requires at least one correct row.
            if group in accepted_groups:
                accepted_groups[group]['unsafe_reasons']=sorted(set(accepted_groups[group]['unsafe_reasons'])|set(claim['unsafe_reasons']))
                accepted_groups[group]['source_conflict'] |= conflict
                accepted_groups[group]['source_uncertainty'] |= uncertainty
                accepted_groups[group]['source_incorrect'] |= source_incorrect
                accepted_groups[group]['unauditable'] |= unauditable
            else:accepted_groups[group]=claim
            observed.append(claim)
            if reasons:unsafe_doc=True
            else:recovered.add((doc,typ,f['distinct_value_group']))
        source_complete=bool(notice and notice['all_source_pages_viewed'] and notice['complete_notice_scope'])
        unresolved=any(f['source_state'] in ('unresolved_conflict','unresolved_uncertainty') for f in byid.values())
        full_values=bool(terminal is not None and source_complete and required<=recovered and not unsafe_doc)
        all_fields=full_values and not unresolved
        resolvable=source_complete and not unresolved
        for f in byid.values():
            if f['source_state'] in ('present_out_of_scope','unresolved_conflict','unresolved_uncertainty'):
                key=(doc,f['field_type'],f['distinct_value_group'])
                if key not in {x['key'] for x in unsupported}:
                    # A positively mapped different source fact does not settle
                    # this unsupported group. Unknown/unmapped claims remain
                    # conservative blockers for the affected field type.
                    group_accepted=any(c['field_type']==f['field_type'] and
                        (not c['source_mapping_verified'] or c['mapped_source_group']==f['distinct_value_group']) for c in observed)
                    unsupported.append({'key':key,'abstained':terminal is not None and not group_accepted})
        ready=bool(terminal and (terminal.get('action_ready') is True or terminal.get('document_completeness') in ('ready','complete')))
        if ready:
            readiness_total+=1
            # Frozen runtime has no supported whole-notice/absence verifier.
            # Source-audited completeness cannot supply that runtime capability.
            false_readiness+=1
        stages=stage_states.get(doc,{})
        requested=bool((terminal and terminal.get('fallback_decision')=='acquire_mistral_ocr') or stages.get('ocr_requested'))
        ocr_requests+=requested
        documents.append({'document_id':doc,'operational_state':state,'source_labels_present':notice is not None,'eligible_DATE':sum(x[1]=='DATE' for x in required),'eligible_EMAIL':sum(x[1]=='EMAIL' for x in required),'correct_DATE':sum(x[0]==doc and x[1]=='DATE' for x in recovered),'correct_EMAIL':sum(x[0]==doc and x[1]=='EMAIL' for x in recovered),'required_values_complete_source_audit':full_values,'both_fields_source_complete':all_fields,'resolvable_notice':resolvable,'runtime_ready':ready,'unsafe_terminal_extras':unsafe_doc,'ocr_requested':requested,'stages':stages})
    unsafe=[x for x in accepted_groups.values() if x['unsafe_reasons']]
    coverage={}
    for typ in TYPES+('pooled',):
        e=sum(typ=='pooled' or x[1]==typ for x in eligible_groups);r=sum(typ=='pooled' or x[1]==typ for x in recovered)
        value=ratio(r,e,'no_source_eligible_instances')
        if not labels_complete:value.update(value=None,undefined_reason='source_labels_incomplete; counts cover known labels only')
        coverage[typ]=value
    complete=sum(d['both_fields_source_complete'] for d in documents)
    resolvable=[d for d in documents if d['resolvable_notice']]
    missing_labels=sorted(set(units)-source.keys())
    return {'schema_version':'round4.evaluation.report.v1','scheduled_documents':len(units),'source_labels_complete':labels_complete,'missing_source_labels':missing_labels,'terminal_documents':sum(d['operational_state']=='terminal' for d in documents),'partial_documents':sum(d['operational_state']=='partial' for d in documents),'not_started_documents':sum(d['operational_state']=='not_started' for d in documents),'correct_shadow_acceptance_coverage':coverage,'terminal_accepted_rows':raw_accepts,'distinct_audited_or_unclassified_claims':len(accepted_groups),'unsafe_acceptance_fraction':ratio(len(unsafe),len(accepted_groups),'no_terminal_acceptances'),'source_incorrect_accepted_claims':sum(x['source_incorrect'] for x in accepted_groups.values()),'source_unresolved_accepted_claims':sum(x['source_conflict'] or x['source_uncertainty'] for x in accepted_groups.values()),'accepted_source_conflicts':sum(x['source_conflict'] for x in accepted_groups.values()),'unauditable_accepted_claims':sum(x['unauditable'] for x in accepted_groups.values()),'document_source_completeness':ratio(complete,len(units)),'resolvable_notice_completeness':ratio(sum(d['both_fields_source_complete'] for d in resolvable),len(resolvable),'no_resolvable_notices'),'runtime_false_readiness':ratio(false_readiness,readiness_total,'no_runtime_ready_declarations'),'fallback_escalation':ratio(ocr_requests,len(units)),'unsupported_abstention':ratio(sum(x['abstained'] for x in unsupported),len(unsupported),'no_unsupported_source_roles'),'documents':documents,'accepted_claim_audits':list(accepted_groups.values()),'unmeasured_metrics':['original_source_candidate_recall','candidate_recall_given_faithful_parse','normalization_fidelity_all_proposals','parser_text_semantic_support','cost_per_correct_field'],'limitations':['Terminal-only recovery; no provisional acceptance credit.','Independent postrun source audits required for role/conditions/precision.','Unaudited rows cannot safely be semantically deduplicated; counted separately.','Known-source counts remain provisional if labels incomplete.'],'production_eligible':False}

def load_terminal(run_dir,manifest):
    terminal={};stages={}
    for unit in manifest['documents']:
        doc=unit['document_id'];folder=run_dir/'documents'/doc
        final=folder/'shadow-observations.json'
        flags={'native_input_in_frozen_manifest':True,'started':folder.exists(),'native_candidate_finding':(folder/'native/pipeline-record.json').exists(),'native_verification_completed':(folder/'native/results.json').exists(),'fallback_decision_recorded':(folder/'fallback-decision.json').exists(),'fallback_text_acquired':(folder/'fallback/text.md').exists(),'fallback_candidates':(folder/'fallback/pipeline-record.json').exists(),'fallback_verification_completed':(folder/'fallback/results.json').exists(),'terminal_merge':final.exists()}
        if flags['fallback_decision_recorded']:
            flags['ocr_requested']=json.loads((folder/'fallback-decision.json').read_bytes()).get('decision')=='acquire_mistral_ocr'
        else:flags['ocr_requested']=False
        stages[doc]=flags
        if final.exists():terminal[doc]=json.loads(final.read_bytes())
    return terminal,stages

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('manifest','labels','audits','run','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    raw=args.manifest.read_bytes();manifest=json.loads(raw)
    pins=args.run/'pins.json'
    if pins.exists() and json.loads(pins.read_bytes()).get('manifest_sha256')!=digest(raw):raise ValueError('runtime manifest pin mismatch')
    terminal,stages=load_terminal(args.run,manifest)
    if terminal and not pins.exists():raise ValueError('terminal outputs lack runtime manifest pins')
    report=evaluate(manifest,json.loads(args.labels.read_bytes()),terminal,json.loads(args.audits.read_bytes()),stages)
    report['input_hashes']={name:digest(getattr(args,name).read_bytes()) for name in ('manifest','labels','audits')}
    with args.output.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write('\n')
