#!/usr/bin/env python3
"""A1 allowances and level-0/1 tail-risk dry runs. No entropy or run mutation."""
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

OUT=Path(__file__).resolve().parent
STATE=OUT.parent
C=STATE.parent
ROOT=OUT.parents[5]
INPUTS=ROOT/'.census-passes/WA/inputs'
PDF=Path('/private/tmp/wa-reconcile-tools/native-text')
sys.path.insert(0,str(C))
import audit_freeze as af
import container_rows as wa


def read(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def tail_risk(strata,units,mandatory):
    """Without replacement; one costliest container forced in each active stratum.

    Also give the unrestricted top-k upper cost under these same allowances.
    Container item (b) uses the maximum, not median, for the full tail scenario.
    Cost-ranked IDs are hypothetical sensitivity examples, never audit selections.
    """
    byid={u['unit_id']:u for u in units}
    detail=[]
    for s in strata:
        k=s['sample_size']
        uu=[byid[uid] for uid in s['unit_ids']]
        containers=[u for u in uu if 'accounting_minutes' in u]
        def cost(u,maximum):return u['accounting_minutes']+u['item_read_max_minutes'] if maximum and 'accounting_minutes' in u else u['minutes']
        row={'stratum_id':s['stratum_id'],'sample_size':k,'container_count':len(containers),'mean_allowance_audit_minutes':k*s['minutes_per_unit']}
        for maximum,prefix in [(False,'median_item'),(True,'max_item')]:
            order=sorted(uu,key=lambda u:(-cost(u,maximum),u['unit_id']))
            most=max(containers,key=lambda u:(cost(u,maximum),u['unit_id'])) if containers and k else None
            forced=([most]+[u for u in order if u is not most][:k-1]) if most else order[:k]
            row[prefix+'_forced_most_expensive_container']=most['unit_id'] if most else None
            row[prefix+'_forced_audit_minutes']=sum(cost(u,maximum) for u in forced)
            row[prefix+'_unrestricted_worst_audit_minutes']=sum(cost(u,maximum) for u in order[:k])
            row[prefix+'_forced_cost_allowances']=[{'unit_id':u['unit_id'],'minutes':cost(u,maximum)} for u in forced]
        detail.append(row)
    totals={prefix+'_'+metric:sum(r[prefix+'_'+metric] for r in detail)
            for prefix in ('median_item','max_item') for metric in ('forced_audit_minutes','unrestricted_worst_audit_minutes')}
    return {'method':'Force one most expensive container in each allocated stratum; fill remaining seats with costliest DISTINCT other units. Strata with no container use their costliest distinct units. Median-item scenario isolates unit-draw risk; max-item scenario also takes the costliest eligible item per container. No overlap credit.',
        'within_cost_allowances_only':True,'audit_minutes':totals['max_item_forced_audit_minutes'],
        'total_minutes':mandatory+totals['max_item_forced_audit_minutes'],
        'over_budget_minutes':mandatory+totals['max_item_forced_audit_minutes']-240,
        **totals,'strata':detail}


def main():
    manifest=read(STATE/'manifest.jsonl');pm={r['entry_id']:r for r in read(INPUTS/'manifest.pass.jsonl')}
    completion=read(STATE/'completion.jsonl');rows=read(OUT/'container-crosswalk.jsonl')
    grouped=collections.defaultdict(list)
    for r in rows:grouped[r['container_id']].append(r)
    queue=read(OUT/'review-queue.jsonl');notes=json.loads((OUT/'case-source-checks.json').read_text())['roots']
    confidence=collections.Counter(notes[i['proceeding']]['confidence'] for i in queue if i['item_kind']=='case')
    mandatory_rows=[{'work':'class policy signatures','N':sum(i['item_kind']=='class' for i in queue),'minutes_each':2}]
    mandatory_rows += [{'work':c+' LOOK cases','N':confidence[c],'minutes_each':cost} for c,cost in [('high',3),('medium',4),('low',6)]]
    mandatory=sum(r['N']*r['minutes_each'] for r in mandatory_rows)
    units=[]
    for m in sorted(manifest,key=lambda m:m['entry_id']):
        if m['retrieval']['result']!='retrieved':continue
        mid=m['entry_id'];r={'unit_id':mid,'covered_entry_ids':[mid]}
        if mid in grouped:
            rr=grouped[mid];owner=[x for x in rr if x.get('owner_accounting_eligible',True)]
            a=sum(x['accounting_status']=='accounted' for x in owner);u=sum(x['accounting_status']=='unaccounted' for x in owner)
            b=[x['participation_read']['minutes'] for x in rr if x['complete_item']];assert b,(mid,'empty item pool')
            r.update({'operation':'A1_container_accounting_plus_item_read','listed_row_count':len(rr),'owner_row_count':len(owner),'pointer_rows':len(rr)-len(owner),
                'accounted_rows':a,'unaccounted_rows':u,'accounting_minutes':3+u+min(a,5),
                'item_read_median_minutes':statistics.median(b),'item_read_max_minutes':max(b),
                'whole_original_verification':any(x['item_kind']=='whole_original_verification_span' for x in rr),
                'minutes':3+u+min(a,5)+statistics.median(b)})
        elif m['format'] in ('text_pdf','scan_pdf'):
            pages=json.loads((PDF/(mid+'.json')).read_text());wc=sum(wa.words(p) for p in pages)
            minutes=3*len(pages) if m['format']=='scan_pdf' else wa.W(wc)+(3 if m['text_layer']!='native' else 0)
            r.update({'operation':'full_original_PDF_read','word_count':wc,'page_count':len(pages),'minutes':minutes})
        elif m['format']=='html':
            p=wa.DOM();p.feed((INPUTS/pm[mid]['original_path']).read_text(errors='replace'));wc=wa.words(p.root.text())
            r.update({'operation':'full_original_HTML_read','word_count':wc,'minutes':wa.W(wc)+(3 if m['text_layer']!='native' else 0)})
        else:r.update({'operation':'full_original_image_verification','minutes':3})
        units.append(r)
    costs={u['unit_id']:u['minutes'] for u in units}
    frames=af.build_frames(rows,manifest)
    levels=[]
    for level in (0,1):
        audit,scenarios=af.plan(manifest,completion,level,2,3,mandatory,10**9,'fixed_sample_v1',30,costs)
        strata=[{**s,'N':len(s['unit_ids']),'estimated_minutes':s['sample_size']*s['minutes_per_unit']} for s in audit['strata']]
        levels.append({'level':level,'N':len(audit['unit_coverage']),'strata':strata,
            'allocation':{'high_risk_units':sum(s['sample_size'] for s in strata if s['high_risk']),
                          'ordinary_units':sum(s['sample_size'] for s in strata if not s['high_risk'])},
            'audit_minutes':sum(s['estimated_minutes'] for s in strata),'total_minutes':audit['estimate_minutes'],
            'over_budget_minutes':audit['estimate_minutes']-240,'unit_coverage':audit['unit_coverage'],
            'planning_frame_hash':af.digest(af.canonical(af.frame(audit))),
            'tail_risk':tail_risk(strata,units,mandatory)})
    for level in levels:
        affected=[s for s in level['strata'] if any(uid.endswith(('-TABLE','-INDEX')) for uid in s['unit_ids'])]
        level['TABLE_INDEX_strata_allocated_units']=sum(s['sample_size'] for s in affected)
    counts=[];metadata={}
    for mid,rr in sorted(grouped.items()):
        filing=[r for r in rr if r['accounting_role']=='filing_reference']
        pointers=[r for r in rr if r['accounting_role']=='pointer']
        unaccounted=sum(r['accounting_status']=='unaccounted' for r in rr)
        counts.append({'container_id':mid,'rows':len(rr),'filing_rows':len(filing),
            'pointer_rows':len(pointers),'pointer_unresolved':sum(r['pointer_status']=='pointer_unresolved' for r in pointers),
            'unaccounted_rows':unaccounted,'unaccounted_filing_rows':sum(r['accounting_status']=='unaccounted' for r in filing),
            'unaccounted_document_verifications':sum(r['accounting_status']=='unaccounted' for r in rr if r['accounting_role']=='document_verification')})
        mm=rr[0].get('container_frame_metadata')
        if mm:metadata[mid]=mm
    top=sorted(counts,key=lambda r:(-r['unaccounted_rows'],r['container_id']))[:10]
    data={'status':'Primary issue-ownership ruling applied; A1 dry run only, no freeze, seed, draw or completed review',
        'row_frame_version':'WA-own-issue-WSR-v3','method':'fixed_sample_v1','sample_total':30,'high_risk_share':.4,
        'review_budget_minutes':240,'mandatory_minutes':mandatory,'mandatory_rows':mandatory_rows,
        'case_confidence':dict(confidence),'LOOK_cases':sum(confidence.values()),'overlap_credit_minutes':0,
        'seed':None,'frame_hash':None,'frozen_before_seed':False,'selected_unit_ids':[],
        'retrieved_entries':len(units),'nonretrieved_entries':len(manifest)-len(units),
        'crosswalk_sha256':sha(OUT/'container-crosswalk.jsonl'),
        'crosswalk_summary':{'containers':len(grouped),'rows':len(rows),
            'accounted':sum(r['accounting_status']=='accounted' for r in rows),
            'unaccounted':sum(r['unaccounted_rows'] for r in counts),
            'owner_rows':sum(r['rows']-r['pointer_rows'] for r in counts),
            'pointer_rows':sum(r['pointer_rows'] for r in counts),
            'pointer_unresolved':sum(r['pointer_unresolved'] for r in counts),
            'pointer_unresolved_distinct_filings':len({n for r in rows if r['pointer_status']=='pointer_unresolved' for n in r['doc_numbers']}),
            'pointer_unresolved_rows':[{'container_id':r['container_id'],'item_ordinal':r['item_ordinal'],'doc_numbers':r['doc_numbers'],'source_spans':r['source_spans']} for r in rows if r['pointer_status']=='pointer_unresolved'],
            'unaccounted_filing_rows':sum(r['unaccounted_filing_rows'] for r in counts),
            'unaccounted_document_verifications':sum(r['unaccounted_document_verifications'] for r in counts),
            'verification_spans':[r['container_id'] for r in rows if r['item_kind']=='whole_original_verification_span'],
            'non_row_line_count':sum(v['non_row_line_count'] for v in metadata.values()),
            'top_10_unaccounted_containers':top,'largest_single_container_unaccounted':top[0],
            'per_container_counts':counts,'per_container_line_metadata':metadata},
        'cost_method':'VA rates retained: W(w)=max(2,ceil(w/250)+1). Container (a)=3+owner-unaccounted+min(owner-accounted,5); pointers contribute zero owner rows and cannot enter the item pool; (b)=median complete-item W(participation words)+residual search hits+2. Full-original verification costs W(entire source). Noncontainers: W(full words), +3 partial/none, or 3 per image/scan page. Mean unit costs round up per stratum. Tail costs use distinct units without replacement and separately replace item medians with maxima. No overlap credit.',
        'limitations':['Planning allowances, not measured throughput; omission expansion and slower reads can cost more.',
            'TABLE/INDEX and HTML filing listings have one row per distinct normalized WSR; source_spans retains every citing line; non-row lines are counted in each frame.',
            'Non-filing verification spans are separately typed and counted, never alleged missing WSR filings. All retained pointer/empty-view lines are part of full-document verification.',
            'Primary issue-ownership ruling: all other-issue references are retained pointers, resolved against any manifest filing entry or latest union label; pointer_unresolved is a source-gap signal, not an owner accounting row.',
            'Tail scenarios are hypothetical cost-ranked sensitivity calculations, not seed-ranked audit selections or elapsed-time guarantees.',
            'A diagnostic ceiling prints the scenarios only; the real budget remains 240 and mandatory work alone exceeds it.'],
        'input_versions':{n:sha(STATE/n) for n in ['manifest.jsonl','completion.jsonl','pass-A.jsonl','pass-B.jsonl','run.json','adjudications.jsonl']},
        'costings':{'scripted_accounting_sampled_verification':{'initial_units':units},
            'fixed_sample_v1':{**levels[1],'levels':levels,
                'scenarios':[{'level':l['level'],'strata':len(l['strata']),'sample':sum(s['sample_size'] for s in l['strata']),
                    'audit_minutes':l['audit_minutes'],'estimate_minutes':l['total_minutes']} for l in levels],
                'planning_container_frame_hash':af.digest(af.canonical(frames))}}}
    path=OUT/'audit-estimate.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    runs=[]
    for level in (0,1):
        for budget in (240,10**9):
            cmd=[sys.executable,str(C/'audit_freeze.py'),str(STATE),'--dry-run','--level',str(level),
                '--minutes-native','2','--minutes-scan','3','--mandatory',str(mandatory),'--method','fixed_sample_v1',
                '--sample-total','30','--costing-file',str(path),'--review-budget',str(budget)]
            result=subprocess.run(cmd,text=True,capture_output=True)
            runs.append({'level':level,'review_budget':budget,'command':cmd,'exit_code':result.returncode,
                'scenarios':json.loads(result.stdout) if result.returncode==0 else None,
                'error':result.stderr.strip().splitlines()[-1:] if result.stderr else []})
    data['dry_runs']=runs;path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'mandatory':mandatory,'unaccounted':data['crosswalk_summary']['unaccounted'],
        'unaccounted_filings':data['crosswalk_summary']['unaccounted_filing_rows'],'top_10':top,'pointers':data['crosswalk_summary']['pointer_rows'],'pointer_unresolved':data['crosswalk_summary']['pointer_unresolved'],
        'levels':[{'level':l['level'],'allocation':l['allocation'],'audit':l['audit_minutes'],'total':l['total_minutes'],
            'median_item_tail':l['tail_risk']['median_item_forced_audit_minutes'],
            'max_item_tail':l['tail_risk']['audit_minutes'],'tail_total':l['tail_risk']['total_minutes'],
            'unrestricted_worst':l['tail_risk']['max_item_unrestricted_worst_audit_minutes']} for l in levels],
        'dry_run_exit_codes':[r['exit_code'] for r in runs]},indent=2))

if __name__=='__main__':main()
