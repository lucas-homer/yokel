#!/usr/bin/env python3
"""Offline R6 scoring from independently frozen truth and independently audited mappings. No providers."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
CATEGORIES=('fact','relationship','instruction','disclosure','ancillary','identity','uncertainty')
ARMS=('jev','stronger')
STATUSES=('accepted_complete','review','failed','not_started')
HASH=re.compile(r'[0-9a-f]{64}')

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def index(rows,key,allowed=None):
    require(isinstance(rows,list),'expected list');out={}
    for r in rows:
        require(isinstance(r,dict) and isinstance(r.get(key),str) and r[key] and r[key] not in out,'missing/duplicate ID')
        require(allowed is None or r[key] in allowed,'unscheduled ID');out[r[key]]=r
    return out

def hash_or_none(value):return value is None or isinstance(value,str) and bool(HASH.fullmatch(value))

def ratio(n,d,available=True):
    return {'numerator':n,'denominator':d,'value':n/d if d and available else None,'undefined_reason':None if d and available else 'reference_or_audit_incomplete' if not available else 'zero_denominator'}

def validate_truth(truth,scheduled):
    require(truth.get('schema_version')=='round6.truth.v1','truth version')
    docs=index(truth.get('documents'),'document_id',scheduled)
    for id,n in docs.items():
        require(n.get('pdf_sha256')==scheduled[id]['pdf_sha256'],'truth PDF mismatch')
        require(n.get('scope_status')in ('complete','incomplete','uncertain'),'scope status')
        require(type(n.get('all_pages_viewed'))is bool and type(n.get('universe_complete'))is bool,'truth completeness booleans')
        require(isinstance(n.get('reviewer'),str) and n['reviewer'] and isinstance(n.get('exclusions'),list),'truth reviewer/exclusions')
        units=index(n.get('units'),'id');domains=n.get('domains',{})
        require(set(domains)==set(CATEGORIES) and all(v in ('present','absent','uncertain')for v in domains.values()),'truth domains')
        for u in units.values():
            require(u.get('category')in CATEGORIES and isinstance(u.get('subtype'),str) and isinstance(u.get('description'),str),'truth unit category/description')
            require('raw_value'in u and (u['raw_value']is None or isinstance(u['raw_value'],str)),'truth raw value')
            require(u.get('modality')in ('mandatory','optional','conditional','descriptive','uncertain','not_applicable'),'truth modality')
            require(isinstance(u.get('targets'),list) and len(u['targets'])==len(set(u['targets'])) and set(u['targets'])<=set(units)|{'$notice'},'truth target reference')
            require(isinstance(u.get('evidence'),list) and u['evidence'],'truth evidence required')
            for ev in u['evidence']:
                require(type(ev.get('page'))is int and 1<=ev['page']<=scheduled[id]['pdf_pages'] and isinstance(ev.get('region'),str) and isinstance(ev.get('quote'),str) and ev['quote'],'image evidence')
        for category,status in domains.items():
            count=sum(u['category']==category for u in units.values())
            require((status!='present' or count>0) and (status!='absent' or count==0),'domain/unit inconsistency')
        blockers=n.get('acceptance_blockers')
        require(isinstance(blockers,list) and len(blockers)==len(set(blockers)) and set(blockers)<=set(units),'acceptance blockers')
        require(all(units[x]['category']=='uncertainty'for x in blockers),'blocker must be uncertainty unit')
    return docs

def source_complete(n):return bool(n and n['scope_status']=='complete' and n['all_pages_viewed'] and n['universe_complete'] and all(v!='uncertain'for v in n['domains'].values()))

def assessment(value,expected_hash,truth):
    """A mapping audit supplies semantic judgments; no self-scoring or string inference."""
    empty={'complete':False,'matched':set(),'claims':[],'audit_complete':False}
    if value is None:return empty
    require(expected_hash is not None and value.get('sha256')==expected_hash,'audit artifact hash mismatch')
    require(truth is not None,'audit requires reference truth')
    require(type(value.get('review_complete'))is bool,'audit completeness boolean')
    claims=index(value.get('claims'),'id');units=index(truth['units'],'id');matches=index(value.get('source_matches'),'source_unit_id',units)
    for c in claims.values():
        require(isinstance(c.get('categories'),list) and c['categories'] and len(c['categories'])==len(set(c['categories'])) and set(c['categories'])<=set(CATEGORIES),'claim categories')
        require(c.get('status')in ('correct','incorrect','unknown') and c.get('evidence_status')in ('matched','invalid','unknown'),'claim status')
        require(c.get('literal_kind')in ('date','email','other','none') and c.get('literal_status')in ('correct','incorrect','unknown','not_applicable'),'literal status')
        require((c['literal_kind']=='none')==(c['literal_status']=='not_applicable'),'literal applicability')
        require(isinstance(c.get('basis'),str) and c['basis'],'claim audit basis')
        if c['status']=='correct':require(c['evidence_status']=='matched' and c['literal_status']in ('correct','not_applicable'),'inconsistent correct claim')
    if value['review_complete']:require(set(matches)==set(units),'complete audit must account for every source unit')
    matched=set()
    for id,m in matches.items():
        require(m.get('status')in ('matched','omitted','mismatched','unknown'),'match status')
        refs=m.get('claim_ids');require(isinstance(refs,list) and len(refs)==len(set(refs)) and set(refs)<=set(claims),'claim references')
        require(isinstance(m.get('basis'),str) and m['basis'],'matching basis')
        require(m['status']!='omitted' or not refs,'omitted unit has claims')
        require(m['status']not in ('matched','mismatched')or refs,'matched/mismatched unit requires claim')
        if m['status']=='matched':
            require(all(claims[x]['status']=='correct'for x in refs),'matched unit relies on incorrect/unknown claim')
            require(any(units[id]['category']in claims[x]['categories']for x in refs),'matched category absent from claims')
            matched.add(id)
    for id in matched:
        require(set(units[id]['targets'])-{'$notice'}<=matched,'matched applicability/relationship has missing endpoint')
    complete=value['review_complete'] and matched==set(units) and all(c['status']=='correct'for c in claims.values())
    return {'complete':complete,'matched':matched,'claims':list(claims.values()),'audit_complete':value['review_complete']}

def evaluate(schedule,truth,audit,observed):
    require(schedule.get('schema_version')=='round6.schedule.v1','schedule version')
    scheduled=index(schedule.get('documents'),'document_id');require(scheduled,'empty schedule')
    for d in scheduled.values():
        require(isinstance(d.get('pdf_sha256'),str)and HASH.fullmatch(d['pdf_sha256']),'schedule PDF hash')
        require(type(d.get('pdf_pages'))is int and d['pdf_pages']>0 and isinstance(d.get('state'),str)and d['state'],'schedule pages/state')
        require(d.get('stratum')in ('general','control'),'schedule stratum')
    sources=validate_truth(truth,scheduled)
    require(audit.get('schema_version')=='round6.matching-audit.v1','audit version');audits=index(audit.get('documents'),'document_id',scheduled)
    require(observed.get('schema_version')=='round6.observed.v1','observed version');obs=index(observed.get('documents'),'document_id',scheduled)
    require(isinstance(audit.get('reviewer'),str)and audit['reviewer'],'independent reviewer identity required')
    views={};reference_complete=len(sources)==len(scheduled) and all(source_complete(n)for n in sources.values())
    for id in scheduled:
        o=obs.get(id)
        if o is None:o={'inventory_sha256':None,'record_sha256':None,'payload_sha256':None,'arms':{a:{'status':'not_started','payload_sha256':None,'source_coverage_complete':False}for a in ARMS}}
        require(all(hash_or_none(o.get(k))for k in ('inventory_sha256','record_sha256','payload_sha256')),'observed hashes')
        require(set(o.get('arms',{}))==set(ARMS),'both arms required')
        for arm,v in o['arms'].items():
            require(v.get('status')in STATUSES and type(v.get('source_coverage_complete'))is bool and hash_or_none(v.get('payload_sha256')),'terminal state')
            if v['status']in ('accepted_complete','review'):
                require(o['record_sha256']is not None and o['payload_sha256']is not None and v['payload_sha256']==o['payload_sha256'],'paired payload/record missing or mismatched')
            elif v.get('payload_sha256')is not None:require(v['payload_sha256']==o['payload_sha256'],'failed arm payload mismatch')
        a=audits.get(id,{})
        views[id]={'source_complete':source_complete(sources.get(id)),'source':sources.get(id),'observed':o,
                   'inventory':assessment(a.get('inventory'),o['inventory_sha256'],sources.get(id)),
                   'record':assessment(a.get('record'),o['record_sha256'],sources.get(id))}
    quality={}
    for artifact in ('inventory','record'):
        stats={};all_claims=[c for v in views.values()for c in v[artifact]['claims']];claims_complete=all(v[artifact]['audit_complete'] or v['observed'][artifact+'_sha256']is None for v in views.values())
        for cat in CATEGORIES:
            denominator=sum(u['category']==cat for n in sources.values()for u in n['units']);numerator=sum(u['category']==cat and u['id']in v[artifact]['matched']for v in views.values()if v['source']for u in v['source']['units']);stats[cat]=ratio(numerator,denominator,reference_complete and claims_complete)
        subtypes=sorted({u['subtype']for n in sources.values()for u in n['units']if u['category']=='fact'})
        subtype_stats={t:ratio(sum(u['category']=='fact'and u['subtype']==t and u['id']in v[artifact]['matched']for v in views.values()if v['source']for u in v['source']['units']),sum(u['category']=='fact'and u['subtype']==t for n in sources.values()for u in n['units']),reference_complete and claims_complete)for t in subtypes}
        literal={k:ratio(sum(c['literal_kind']==k and c['literal_status']=='correct'for c in all_claims),sum(c['literal_kind']==k for c in all_claims),claims_complete)for k in ('date','email','other')}
        category_precision={cat:ratio(sum(cat in c['categories'] and c['status']=='correct'for c in all_claims),sum(cat in c['categories']for c in all_claims),claims_complete)for cat in CATEGORIES}
        quality[artifact]={'claim_precision_by_category':category_precision,'source_coverage_by_category':stats,'source_fact_coverage_by_subtype':subtype_stats,'literal_accuracy':literal,'claimed_semantic_units':len(all_claims),'incorrect_claims':sum(c['status']=='incorrect'for c in all_claims),'unknown_claims':sum(c['status']=='unknown'for c in all_claims),'claim_precision':ratio(sum(c['status']=='correct'for c in all_claims),len(all_claims),claims_complete),'complete_records':sum(v['source_complete']and v[artifact]['complete']for v in views.values()),'missing_or_incomplete_audits':sum(not v[artifact]['audit_complete']for v in views.values())}
    n=len(scheduled);states=Counter(x['state']for x in scheduled.values());strata=Counter(x['stratum']for x in scheduled.values());cohort_ok=n==8 and strata=={'general':6,'control':2} and len(states)>=6 and max(states.values())<=2 and sum(x['pdf_pages']for x in scheduled.values())<=40
    arms={};per_notice=[]
    for arm in ARMS:
        accepted=correct=0;reasons=Counter();outcomes={};status_counts=Counter()
        for id,v in views.items():
            x=v['observed']['arms'][arm];status_counts[x['status']]+=1;accept=x['status']=='accepted_complete';accepted+=accept
            safe=v['source_complete']and v['record']['complete']and not v['source']['acceptance_blockers'] and x['source_coverage_complete']
            good=accept and safe;correct+=good
            outcomes[id]='correct_accepted'if good else'unsafe_accepted'if accept else x['status']
            if accept and not safe:
                if not v['source_complete']:reasons['reference_scope_or_truth_incomplete']+=1
                if not v['record']['complete']:reasons['record_audit_incomplete_or_incorrect']+=1
                if v['source']and v['source']['acceptance_blockers']:reasons['source_acceptance_blocker']+=1
                if not x['source_coverage_complete']:reasons['source_coverage_pass_incomplete']+=1
        arms[arm]={'status_counts':dict(status_counts),'accepted_records':accepted,'correct_complete_accepted':correct,'unsafe_accepted':accepted-correct,'unsafe_acceptance_fraction':ratio(accepted-correct,accepted),'useful_coverage':ratio(correct,n,reference_complete),'review_or_unserved_fraction':ratio(n-accepted,n),'unsafe_reason_counts':dict(reasons),'outcomes':outcomes,'gate_passed':cohort_ok and reference_complete and accepted==correct and correct>=2}
    for id,v in views.items():per_notice.append({'document_id':id,'source_complete':v['source_complete'],'record_complete':v['source_complete']and v['record']['complete'],'acceptance_blockers':v['source']['acceptance_blockers']if v['source']else None,'jev':arms['jev']['outcomes'][id],'stronger':arms['stronger']['outcomes'][id]})
    paired=Counter((x['jev'],x['stronger'])for x in per_notice)
    costs=observed.get('costs',{});require(not(set(costs)-{'extraction',*ARMS}),'unknown cost stage');cost_report={}
    for stage in ('extraction',*ARMS):
        c=costs.get(stage,{})
        for k in ('usage_estimate_usd','conservative_charge_usd','provider_reported_usd'):
            v=c.get(k);require(v is None or type(v)in (int,float)and v>=0 and v<float('inf'),'invalid cost')
        cost_report[stage]={k:c.get(k)for k in ('usage_estimate_usd','conservative_charge_usd','provider_reported_usd')}
    def total(stages,key):
        values=[cost_report[s][key]for s in stages];return sum(values)if all(v is not None for v in values)else None
    cost_report['experiment_total']={k:total(('extraction',*ARMS),k)for k in ('usage_estimate_usd','conservative_charge_usd','provider_reported_usd')}
    for arm in ARMS:
        denom=arms[arm]['correct_complete_accepted'];cost_report[arm]['scenario_cost_per_correct_complete_record']={k:(total(('extraction',arm),k)/denom if denom and total(('extraction',arm),k)is not None else None)for k in ('usage_estimate_usd','conservative_charge_usd','provider_reported_usd')}
    return {'schema_version':'round6.evaluation.report.v1','scheduled_notices':n,'source_truth_complete':reference_complete,'missing_truth_ids':sorted(set(scheduled)-set(sources)),'cohort_adequacy':cohort_ok,'quality':quality,'arms':arms,'paired_notice_outcomes':[{'jev':a,'stronger':b,'count':c}for(a,b),c in sorted(paired.items())],'notices':per_notice,'costs':cost_report,'limitations':['Semantic judgments come from independent audit, never model self-scores.','Eight-notice pilot; atoms/relations are clustered descriptive counts.','Matching audit completeness and pre-extraction blinding require external source/runtime evidence.','Unknown costs are not zero; runtime enforces reservation/stop policy.','Human review time and population accuracy are unmeasured.'],'production_eligible':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('schedule','truth','audit','observed','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();result=evaluate(*[json.loads(getattr(a,k).read_text())for k in ('schedule','truth','audit','observed')]);result['input_hashes']={k:digest(getattr(a,k))for k in ('schedule','truth','audit','observed')}
    with a.output.open('x')as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
