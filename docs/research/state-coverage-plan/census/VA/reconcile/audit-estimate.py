#!/usr/bin/env python3
"""Retrospective, unsampled §5 review-cost scenarios; no run/audit mutation."""
import collections
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics

OUT=Path(__file__).resolve().parent
STATE=OUT.parent
INPUTS=OUT.parents[5]/'.census-passes/VA/inputs'
def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
class Visible(HTMLParser):
 def __init__(self):super().__init__();self.hidden=0;self.words=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','head'):self.hidden+=1
 def handle_endtag(self,tag):
  if tag in ('script','style','head'):self.hidden=max(0,self.hidden-1)
 def handle_data(self,text):
  if not self.hidden:self.words+=len(re.findall(r'\S+',text))

def main():
 manifest={r['entry_id']:r for r in read(STATE/'manifest.jsonl') if r['retrieval']['result']=='retrieved'}
 pm={r['entry_id']:r for r in read(INPUTS/'manifest.pass.jsonl')}
 completion={(r['pass'],r['manifest_entry_id']):r for r in read(STATE/'completion.jsonl')}
 assert all({mid for side,mid in completion if side=='pass_'+s}==set(manifest) for s in 'AB')
 direct_accept=set(); direct_reject=set()
 for side in 'AB':
  for r in read(STATE/f'pass-{side}.jsonl'):
   target=direct_reject if r['record_type']=='rejected_candidate' else direct_accept
   target.update(e['manifest_entry_id'] for e in r['evidence'])
 units=[]
 for mid,m in sorted(manifest.items()):
  co=[completion[('pass_'+s,mid)] for s in 'AB']
  accepted=mid in direct_accept or any(r['candidate_count'] for r in co)
  rejected=mid in direct_reject or any(r['rejected_count'] for r in co)
  disposition='inclusion' if accepted else 'exclusions_only' if rejected else 'no_candidates'
  both_empty=all(r['candidate_count']==r['rejected_count']==0 for r in co)
  partial=m['text_layer'] in ('partial','none')
  flags=pm[mid].get('text_failure_locators',[])
  marked=sorted({int(p) for x in flags for p in re.findall(r'\bpage\s+(\d+)',x)})
  words=0
  if m['kind']=='issue':
   # Contents/page/attachment accounting, plus complete known scan-page reads;
   # never cost this as a full issue read or count it as a second body audit.
   minutes=5+3*len(marked)
   operation='issue_accounting_and_complete_marked_pages' if marked else 'issue_accounting_only'
  elif m['kind']=='index':
   minutes=2;operation='listing_accounting_only'
  else:
   b=(INPUTS/pm[mid]['original_path']).read_bytes()
   assert hashlib.sha256(b).hexdigest()==m['retrieval']['sha256']
   visible=Visible();visible.feed(b.decode(errors='replace'));words=visible.words
   # Full selected content views are read, including excluded items; a massive
   # regulations section is not represented as a two-minute filing.
   minutes=max(2,math.ceil(words/250)+1)+(3 if partial else 0)
   operation='full_content_view_plus_gap_review' if partial else 'full_content_view'
  units.append({'unit_id':mid,'covered_entry_ids':[mid], 'source_id':m['source_id'],
    'process_id':m['process_id'],'format':m['format'],'publication_cycle':m['publication_cycle'],
    'disposition':disposition,'both_empty':both_empty,'scan_or_partial':partial,
    'text_layer':m['text_layer'],'high_risk':partial or both_empty or disposition!='inclusion',
    'minutes':minutes,'operation':operation,'visible_word_count':words,'marked_full_pages':marked})
 checks=json.loads((OUT/'case-source-checks.json').read_text())['cases']
 queue=read(OUT/'review-queue.jsonl')
 mandatory_rows=[{'work':'class signatures','N':sum(i['item_kind']=='class' for i in queue),'minutes_each':2}]
 for confidence,look,cost in [('high',False,1),('high',True,3),('medium',True,4),('low',True,6)]:
  mandatory_rows.append({'work':confidence+(' LOOK' if look else ' without LOOK'),'N':sum(c['confidence']==confidence and c['look']==look for c in checks),'minutes_each':cost})
 mandatory=sum(r['N']*r['minutes_each'] for r in mandatory_rows)
 # Coarsen overlapping PDF/TOC accounting into one issue unit. Keep all source
 # entries in its exact coverage list. Content section pages remain full reads.
 merged=[];absorbed=set();original={u['unit_id']:u for u in units}
 for u in units:
  if u['unit_id'].endswith('-pdf'):
   toc=u['unit_id'][:-3]+'toc'
   if toc in original:
    other=original[toc];v=dict(u);v['covered_entry_ids']=sorted(u['covered_entry_ids']+other['covered_entry_ids'])
    v['format']='issue_pdf_with_toc';v['disposition']='inclusion' if 'inclusion' in (u['disposition'],other['disposition']) else 'exclusions_only' if 'exclusions_only' in (u['disposition'],other['disposition']) else 'no_candidates'
    v['both_empty']=u['both_empty'] and other['both_empty'];v['high_risk']=v['scan_or_partial'] or v['both_empty'] or v['disposition']!='inclusion'
    merged.append(v);absorbed.add(toc);continue
  merged.append(dict(u))
 merged=[u for u in merged if u['unit_id'] not in absorbed]
 def scenario(level,initial=None,coarsened=None):
  pop=(initial if initial is not None else units) if level==0 else (coarsened if coarsened is not None else merged)
  groups=collections.defaultdict(list)
  for u in pop:
   key=[u['source_id'],u['process_id'],u['format'],u['disposition'],u['scan_or_partial'],u['both_empty']]
   if level==0:key.append(u['publication_cycle'])
   groups[canonical(key)].append(u)
  strata=[]
  for key,uu in sorted(groups.items()):
   n=len(uu);risk=any(u['high_risk'] for u in uu)
   sample=min(n,min(20,max(5,math.ceil(.20*n)))) if risk and level>=3 else min(n,20) if risk else min(n,max(2,math.ceil(.10*n))) if level>=2 else min(n,max(5,math.ceil(.20*n)))
   cost=math.ceil(sum(u['minutes'] for u in uu)/n)
   strata.append({'stratum_id':key,'unit_ids':sorted(u['unit_id'] for u in uu),'disposition':uu[0]['disposition'],
     'high_risk':risk,'scan_or_partial':uu[0]['scan_or_partial'],'both_empty':uu[0]['both_empty'],
     'N':n,'planned_sample_size':sample,'minutes_per_unit':cost,'estimated_minutes':sample*cost})
  coverage={u['unit_id']:u['covered_entry_ids'] for u in sorted(pop,key=lambda u:u['unit_id'])}
  flat=[e for cc in coverage.values() for e in cc]
  assert len(flat)==len(set(flat))==len(manifest) and set(flat)==set(manifest)
  frame=[{k:r[k] for k in ('stratum_id','unit_ids','disposition','high_risk')} for r in strata]
  frame_hash=hashlib.sha256(canonical({'strata':frame,'unit_coverage':coverage}).encode()).hexdigest()
  audit=sum(r['estimated_minutes'] for r in strata)
  return {'level':level,'stratum_count':len(strata),'unit_count':len(pop),'sample_units':sum(r['planned_sample_size'] for r in strata),
    'audit_minutes':audit,'mandatory_minutes':mandatory,'total_minutes':mandatory+audit,'strata':strata,
    'unit_coverage':coverage,'planning_frame_hash':frame_hash}
 scenarios=[scenario(i) for i in range(4)]
 data={'status':'retrospective planning estimate only; not a frozen or completed audit','review_budget_minutes':360,
  'seed':None,'selected_unit_ids':[],'mandatory_rows':mandatory_rows,'mandatory_minutes':mandatory,
  'overlap_credit_minutes':0,'retrieved_entries':len(manifest),'nonretrieved_gaps':4,
  'base_dispositions':dict(collections.Counter(u['disposition'] for u in units)),
  'both_empty_units':sum(u['both_empty'] for u in units),'scan_or_partial_units':sum(u['scan_or_partial'] for u in units),
  'cost_method':'Planning, not measured throughput: whole selected HTML content at 250 visible words/minute + 1 minute check (minimum 2); partial HTML +3 gap review. Issue accounting 5 minutes, plus 3 per named complete marked page; TOC/index listing accounting 2. Coarsened issue+TOC charged once. Stratum cost rounds up mean unit cost; seed-dependent actual selections may cost more. Additional image pages or recovered material add work.',
  'coarsening_history':scenarios,'initial_units':units,'reduced_units':merged}
 inventory_path=OUT/'container-inventory.json'
 if inventory_path.exists():
  inventory=json.loads(inventory_path.read_text())
  container_units=[]
  for u in units:
   v=dict(u);source=inventory['containers'].get(u['unit_id'])
   if source:
    count=source['item_count'];median=source['median_item_words']
    accounting=5+.5*count
    full_item=max(2,math.ceil(median/250)+1)
    max_reg=max(2,math.ceil(source['max_regulation_action_words']/250)+1) if source['max_regulation_action_words'] else 0
    v.update({'operation':'container_accounting_plus_one_complete_item',
      'minutes':accounting+full_item,'container_kind':source['container_kind'],
      'listed_item_count':count,'read_item_count':source['read_item_count'],
      'accounting_minutes':accounting,'median_item_words':median,
      'one_item_minutes_at_median':full_item,'max_regulation_action_words':source['max_regulation_action_words'],
      'one_longest_regulation_minutes':max_reg,
      'median_item_read_dominates':full_item>accounting,
      'long_regulation_draw_would_dominate':source['max_regulation_action_words']>=2500 and max_reg>accounting})
   container_units.append(v)
  container_by_id={u['unit_id']:u for u in container_units}
  container_merged=[]
  for u in merged:
   v=dict(u);new=container_by_id[u['unit_id']]
   # Same strata, dispositions and exact entry partition as the original
   # model. A merged PDF/TOC receives one expanded issue inventory, not two.
   for key,value in new.items():
    if key not in ('covered_entry_ids','format','disposition','both_empty','high_risk'):
     v[key]=value
   container_merged.append(v)
  container_scenarios=[scenario(i,container_units,container_merged) for i in range(4)]
  dominance=[{'unit_id':u['unit_id'],**{k:u[k] for k in ('container_kind','listed_item_count','accounting_minutes',
       'median_item_words','one_item_minutes_at_median','max_regulation_action_words','one_longest_regulation_minutes',
       'median_item_read_dominates','long_regulation_draw_would_dominate')}}
       for u in container_units if 'container_kind' in u and (u['long_regulation_draw_would_dominate'] or u['median_item_read_dominates'])]
  ids=[u for u in container_units if 'container_kind' in u]
  summary={**inventory['item_count_summary'],'all_containers':{
    'containers':len(ids),'median_item_count':statistics.median(u['listed_item_count'] for u in ids),
    'max_item_count':max(u['listed_item_count'] for u in ids)}}
  data['costings']={
   'full_content_views':{'label':'Original full-content-view interpretation','coarsening_history':scenarios,
    'protocol_section':'PROTOCOL §5, Review budget and random audit',
    'protocol_sentences':['An issue audit checks contents/page/attachment accounting; it does not read the issue cover to cover.',
     'Pages, filings and history slices selected for content are read in full.'],
    'interpretation':'Issue PDFs/TOCs receive accounting; a selected HTML issue section is treated as a full content view. The section-as-content choice is an interpretation, not an explicit protocol sentence.'},
   'container_accounting':{'label':'Alternative container-accounting interpretation (user requested)',
    'protocol_section':'PROTOCOL §5, Review budget and random audit',
    'protocol_sentences':['An issue audit checks contents/page/attachment accounting; it does not read the issue cover to cover.',
     'Pages, filings and history slices selected for content are read in full.'],
    'interpretation':'Extend issue-style accounting to HTML issue sections. Check every listed item against the accepted/rejected union, then read ONE complete source item per sampled container. The nested one-item draw is this requested alternative, not an already frozen protocol amendment.',
    'cost_method':'Per container: 5 + 0.5 × listed items, plus max(2, ceil(median full-item words / 250) + 1). No additional whole-section read or old marked-page surcharge is added; existing scan/partial strata and floors remain. Non-containers retain the original rule. Stratum means round up; actual one-item draws can exceed the median allowance.',
    'item_inventory_ref':'container-inventory.json','item_inventory_sha256':hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
    'container_item_count_summary':summary,'coarsening_history':container_scenarios,
    'initial_units':container_units,'reduced_units':container_merged,'long_item_dominance':dominance,
    'non_container_units':len(units)-len(ids),'seed':None,'selected_container_ids':[],'selected_item_ids':[],
    'inventory_limitations':inventory['limitations']}}
  participation_units=[]
  for u in container_units:
   v=dict(u);source=inventory['containers'].get(u['unit_id'])
   if source:
    reading=source['participation_read']
    v.update({'operation':'container_accounting_plus_one_item_participation_read',
     'minutes':u['accounting_minutes']+reading['median_b_minutes'],
     'participation_read':reading})
    for key in ('one_item_minutes_at_median','one_longest_regulation_minutes','median_item_read_dominates','long_regulation_draw_would_dominate'):
     v.pop(key,None)  # Whole-item dominance belongs to costing C only.
   participation_units.append(v)
  by_id={u['unit_id']:u for u in participation_units}
  participation_merged=[]
  for u in merged:
   v=dict(u)
   for key,value in by_id[u['unit_id']].items():
    if key not in ('covered_entry_ids','format','disposition','both_empty','high_risk'):v[key]=value
   participation_merged.append(v)
  eligible=[{'unit_id':mid,'item_ordinal':it['item_ordinal'],'doc_numbers':it['doc_numbers'],
     'kind':it['kind'],**it['participation_read']}
    for mid,source in inventory['containers'].items() for it in source['items'] if 'participation_read' in it]
  allowances=[u['participation_read']['median_b_minutes'] for u in participation_units if 'participation_read' in u]
  max_b=max(it['minutes'] for it in eligible)
  data['costings']['container_accounting_participation_read']={
   'label':'Alternative container-accounting + participation read (user requested; owner approval required)',
   'protocol_section':'PROTOCOL §5, Review budget and random audit',
   'protocol_sentences':data['costings']['container_accounting']['protocol_sentences'],
   'interpretation':'Extend issue-style accounting to HTML issue sections, as in container-accounting. ONE future seeded complete notice/action supplies the participation passages and remaining-body native search. This weakens "Pages, filings and history slices selected for content are read in full." It is not protocol compliance under that sentence without owner approval.',
   'owner_approval_required':True,
   'cost_method':'Same accounting (5 + 0.5 × listed items), same complete-item pool and non-container costs. Item (b): max(2, ceil(preamble/participation words / 250) + 1) + 1 minute per residual native-text search occurrence + 2 overhead. Per-container allowance is median of eligible individual item (b) costs. Same predeclared coarsening order, strata, floors, rounded-up stratum means and 271 mandatory minutes. Context reading is charged through hit minutes, not counted a second time as passage words.',
   'passage_and_search_method':inventory['participation_read_method'],
   'item_inventory_ref':'container-inventory.json','item_inventory_sha256':hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
   'container_item_count_summary':summary,
   'b_cost_summary':{'containers':len(allowances),'median_container_b_allowance_minutes':statistics.median(allowances),
    'max_container_b_allowance_minutes':max(allowances),
    'max_container_b_allowance_ids':[u['unit_id'] for u in participation_units if u.get('participation_read',{}).get('median_b_minutes')==max(allowances)],
    'eligible_item_instances':len(eligible),'median_item_b_minutes':statistics.median(it['minutes'] for it in eligible),
    'max_item_b_minutes':max_b,
    'instance_weighting':'Unselected displayed item instances across all 229 containers; overlapping HTML/PDF/TOC representations repeat here. Not a seeded distribution. Planning uses each container median, not this pooled median.',
    'max_item_instances':[it for it in eligible if it['minutes']==max_b]},
   'coarsening_history':[scenario(i,participation_units,participation_merged) for i in range(4)],
   'initial_units':participation_units,'reduced_units':participation_merged,
   'non_container_units':len(units)-len(ids),'seed':None,'selected_container_ids':[],'selected_item_ids':[],
   'inventory_limitations':inventory['limitations']+[
    'Native passage selection is deterministic, conservative sizing, not a completed participation read. Non-regulation items and bodies without reliable section boundaries are costed as full reads plus overhead.',
    'Search includes standalone 19xx/20xx years; legislative citations can inflate the hit allowance. Citation-like VAC hyphen strings are excluded from numeric-date recognition. Every occurrence is charged; actual item draws may exceed the container median.',
    'The participation-only content rule weakens the protocol read-in-full sentence and requires owner approval before any future audit. No approval, freeze, seed or selection is implied.']}
  def concentration(initial,reduced,history):
   components=[]
   for sc in history:
    pop={u['unit_id']:u for u in (initial if sc['level']==0 else reduced)}
    totals=collections.Counter({'accounting_minutes':0.,'participation_read_minutes':0.,'non_container_minutes':0.})
    for st in sc['strata']:
     weight=st['planned_sample_size']/st['N']
     for uid in st['unit_ids']:
      u=pop[uid]
      if 'container_kind' in u:
       totals['accounting_minutes']+=weight*u['accounting_minutes']
       totals['participation_read_minutes']+=weight*u['participation_read']['median_b_minutes']
      else:totals['non_container_minutes']+=weight*u['minutes']
    rounding=sc['audit_minutes']-sum(totals.values())
    components.append({'level':sc['level'],**{k:round(v,6) for k,v in totals.items()},
     'stratum_rounding_minutes':round(rounding,6),'audit_minutes':sc['audit_minutes'],
     'mandatory_minutes':mandatory,'total_minutes':sc['total_minutes']})
   final_weights={uid:st['planned_sample_size']/st['N'] for st in history[-1]['strata'] for uid in st['unit_ids']}
   def top(pop,weights=None):
    result=[]
    for u in sorted(pop,key=lambda x:(-x['minutes'],x['unit_id']))[:10]:
     row={'unit_id':u['unit_id'],'covered_entry_ids':u['covered_entry_ids'],'minutes':u['minutes'],
      'listed_item_count':u.get('listed_item_count'),'accounting_minutes':u.get('accounting_minutes',0),
      'participation_read_minutes':u.get('participation_read',{}).get('median_b_minutes',0),
      'non_container_minutes':0 if 'container_kind' in u else u['minutes']}
     if 'unaccounted_rows' in u:row.update({k:u[k] for k in ('accounted_rows','unaccounted_rows','verification_rows')})
     if weights is not None:row['level3_weighted_minutes_before_rounding']=round(weights[u['unit_id']]*u['minutes'],6)
     result.append(row)
    return result
   return {'basis':'Top units use raw per-unit allowances, ties by unit ID. Coarsened units pair PDF/TOC once. No sample was drawn. Scenario components weight each unit by stratum sample/N; ceiling-of-stratum-mean residual is reported separately, not charged twice.',
    'scenario_components':components,'baseline_top10_units':top(initial),'coarsened_top10_units':top(reduced,final_weights)}
  pmodel=data['costings']['container_accounting_participation_read']
  pmodel['concentration']=concentration(participation_units,participation_merged,pmodel['coarsening_history'])
  crosswalk_path=OUT/'container-crosswalk-summary.json'
  if crosswalk_path.exists():
   crosswalk=json.loads(crosswalk_path.read_text())
   assert crosswalk['crosswalk_sha256']==hashlib.sha256((OUT/'container-crosswalk.jsonl').read_bytes()).hexdigest()
   for filename,digest in crosswalk['input_versions'].items():assert hashlib.sha256((OUT.parents[5]/filename).read_bytes()).hexdigest()==digest
   scripted=[]
   for u in participation_units:
    v=dict(u);row=crosswalk['containers'].get(u['unit_id'])
    if row:
     assert row['listed_rows']==u['listed_item_count']
     v.update({k:row[k] for k in ('accounted_rows','unaccounted_rows','verification_rows')})
     v['accounting_minutes']=row['owner_accounting_minutes']
     v['minutes']=v['accounting_minutes']+u['participation_read']['median_b_minutes']
     v['operation']='scripted_accounting_plus_sampled_verification_and_participation_read'
    scripted.append(v)
   script_by_id={u['unit_id']:u for u in scripted};script_merged=[]
   for u in merged:
    v=dict(u)
    for key,value in script_by_id[u['unit_id']].items():
     if key not in ('covered_entry_ids','format','disposition','both_empty','high_risk'):v[key]=value
    script_merged.append(v)
   script_scenarios=[scenario(i,scripted,script_merged) for i in range(4)]
   data['costings']['scripted_accounting_sampled_verification']={
    'label':'scripted accounting + sampled verification (PROTOCOL amendment and owner approval required)',
    'protocol_section':'PROTOCOL §5, Review budget and random audit',
    'protocol_sentences':pmodel['protocol_sentences']+['The human checks boundaries, accepted labels, exclusions and overlooked candidates in originals.'],
    'protocol_amendment_required':True,'owner_approval_required':True,
    'interpretation':'A primary-produced scripted crosswalk supplies every listed item to a latest union notice/rejection record or unaccounted. Scripting is agent work, zero owner minutes. Owner checks every unaccounted row plus min(accounted rows,5) future seeded accounted-row verifications and performs the same one-item participation read as costing P. This replaces full human item accounting and weakens content read-in-full; it requires a PROTOCOL amendment and owner approval. No amendment is applied here.',
    'cost_method':'Per sampled container: (a) 3 base + unaccounted rows + min(accounted rows,5), at 1 minute per checked row; (b) same per-container median participation-read item cost as P. All non-containers, coarsening order, strata, sample sizes, floors, stratum-mean ceilings and 271 mandatory minutes unchanged. No overhead for agent scripting is charged to owner.',
    'unaccounted_method':'Conservative scripted source/union-label matching, not a zero-unaccounted assumption; ambiguous/unmatched rows cost one minute each. Explicit whole-agency catalogue rejection spans can cover many source rows; boundary-crossing rows remain unaccounted. Accounted means pointer coverage, not label correctness. See crosswalk method and row-level reasons.',
    'crosswalk_ref':'container-crosswalk.jsonl','crosswalk_sha256':crosswalk['crosswalk_sha256'],
    'crosswalk_summary_ref':crosswalk_path.name,'crosswalk_summary_sha256':hashlib.sha256(crosswalk_path.read_bytes()).hexdigest(),
    'unaccounted_counts':{'baseline':{k:sum(u.get(k,0) for u in scripted) for k in ('listed_item_count','accounted_rows','unaccounted_rows','verification_rows')},
     'coarsened':{k:sum(u.get(k,0) for u in script_merged) for k in ('listed_item_count','accounted_rows','unaccounted_rows','verification_rows')}},
    'coarsening_history':script_scenarios,'initial_units':scripted,'reduced_units':script_merged,
    'concentration':concentration(scripted,script_merged,script_scenarios),
    'non_container_units':len(units)-len(ids),'seed':None,'selected_container_ids':[],'selected_item_ids':[],'selected_verification_rows':[],
    'inventory_limitations':pmodel['inventory_limitations']+crosswalk['method']}
 (OUT/'audit-estimate.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
 # This is source-coverage bookkeeping, not a legal deadline calculation or a
 # claim that all intervening lifecycle changes were found.
 issue_dates={}
 for mid,m in manifest.items():
  match=re.match(r'va-(\d+)-(\d+)-(?:pdf|toc|s\d+)$',mid)
  date=re.search(r'\d{4}-\d\d-\d\d',m['publication_cycle'])
  if match and date:
   issue_dates[f'va-{match[1]}-{int(match[2]):02d}-pdf']=date[0]
 record_index={r['record_id']:r for side in 'AB' for r in read(STATE/f'pass-{side}.jsonl')}
 horizon=[]
 for pair in read(OUT/'pairs.jsonl'):
  if pair['record_type']!='opportunity':continue
  rr=[record_index[rid] for side in 'AB' for rid in pair[side+'_record_ids']]
  tt=[t for r in rr for t in r['payload']['temporal'] if t['role'] in ('close','hearing_start','hearing_end')]
  values=sorted({t['local_value'][:10] for t in tt if isinstance(t.get('local_value'),str) and re.match(r'^\d{4}-\d\d-\d\d',t['local_value'])})
  endpoint=max(values) if values else None
  following=sorted([(date,mid) for mid,date in issue_dates.items() if endpoint and date>endpoint])[:2]
  flagged=any(t['status'] in ('unknown','conflicting') for t in tt)
  horizon.append({'pair_id':pair['pair_id'],'record_ids':{s:pair[s+'_record_ids'] for s in 'AB'},
    'asserted_endpoint_dates':values,'planning_latest_endpoint':endpoint,
    'following_supplied_issues':[mid for date,mid in following],
    'source_coverage':'two_supplied_issues' if len(following)==2 else 'unknown_endpoint' if endpoint is None else 'unfinished',
    'endpoint_unknown_or_conflicting':flagged,'multiple_endpoint_assertions':len(values)>1})
 (OUT/'horizon-recheck.json').write_text(json.dumps({'status':'conditional source-coverage index only; no legal/owner verdict',
  'universal_date_rule_current_candidate_N':len(horizon),'opportunities':horizon,
  'source_coverage_counts':dict(collections.Counter(r['source_coverage'] for r in horizon)),
  'unknown_or_conflicting_endpoints':sum(r['endpoint_unknown_or_conflicting'] for r in horizon)},indent=2)+'\n')
 print(json.dumps({'mandatory':mandatory,'population':data['base_dispositions'],'scenarios':[{k:s[k] for k in ('level','stratum_count','unit_count','sample_units','audit_minutes','total_minutes')} for s in scenarios]},indent=2))
 if 'costings' in data:
  print(json.dumps({'container_accounting':[{k:s[k] for k in ('level','stratum_count','unit_count','sample_units','audit_minutes','total_minutes')} for s in data['costings']['container_accounting']['coarsening_history']]},indent=2))
  print(json.dumps({'container_accounting_participation_read':[{k:s[k] for k in ('level','stratum_count','unit_count','sample_units','audit_minutes','total_minutes')} for s in data['costings']['container_accounting_participation_read']['coarsening_history']]},indent=2))
  if 'scripted_accounting_sampled_verification' in data['costings']:
   print(json.dumps({'scripted_accounting_sampled_verification':[{k:s[k] for k in ('level','stratum_count','unit_count','sample_units','audit_minutes','total_minutes')} for s in data['costings']['scripted_accounting_sampled_verification']['coarsening_history']]},indent=2))
if __name__=='__main__':main()
