#!/usr/bin/env python3
"""Deterministically render unsigned owner proposals from the reviewed queue."""
import collections
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
STATE=OUT.parent

def read(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    queue=read(OUT/'review-queue.jsonl');summary=json.loads((OUT/'comparison-summary.json').read_text());notes=json.loads((OUT/'case-source-checks.json').read_text())['roots'];audit=json.loads((OUT/'audit-estimate.json').read_text());fixed=audit['costings']['fixed_sample_v1']
    classes=[i for i in queue if i['item_kind']=='class'];cases=[i for i in queue if i['item_kind']=='case']
    progress=json.loads((OUT/'.progress.json').read_text());created=progress.setdefault('draft_created_at',datetime.now(timezone.utc).isoformat().replace('+00:00','Z'));(OUT/'.progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    versions=[f'{p.relative_to(OUT.parents[5])}@sha256:{sha(p)}' for p in [STATE/'pass-A.jsonl',STATE/'pass-B.jsonl',STATE/'completion.jsonl',STATE/'manifest.jsonl',STATE/'brief.txt',STATE/'UNIVERSE.md',OUT/'review-queue.jsonl',OUT/'case-source-checks.json']]
    md=['# WA owner sheet — proposed, unsigned','',f'The owner decides {len(classes)} class items and {len(cases)} cases. Agreement is not a verdict. Full immutable item/record IDs, complete class membership and three instances per class are in `review-queue.jsonl` and `proposed-adjudications.jsonl`. Drafts use `author.role=primary`, `review_status=proposed`, `draft:true` and null human fields; never ingest as signed verdicts. No sealed pass or human log was changed.','',
        '## Part 1 — Class questions','',
        'Counts are A/B latest label versions / comparison instances, with overlap across classes. Policies await owner signature. Class answers settle only the named policy facet; scope, targets and specific conflicting dates stay cases.']
    for i in classes:
        proposal=i['proposed_answer']
        if i['policy_key']=='receipt-condition':proposal+=' In this affected set, explicit received wording occurs in 26-11-038, 26-11-066, 26-16-031 and 26-16-036; the other 20 bare-by conditions stay null. Callback/registration receipts are unrelated.'
        md += ['',f'**{i["owner_ref"]}. {i["question"]}** {proposal} **{sum(map(len,i["record_ids"].values()))} records / {i["affected_instance_count"]} instances.**']
        reps=[]
        for x in i['representative_instances']:
            ev=next((e for e in x['evidence'] if e['manifest_entry_id'].startswith('wa-f-')),x['evidence'][0] if x['evidence'] else None)
            reps.append((f'`{ev["manifest_entry_id"]}`' if ev else x['proceeding']))
        md += ['Instances: '+ '; '.join(reps)+'.']
    md += ['', '## Part 2 — Cases, bundled by WSR chain root','',
        '**LOOK** requires personal inspection of the original and all unresolved scope/date/target facts. Confidence rates the proposal only. Multiple case refs under one root keep their distinct trigger decisions; no overlap credit is assumed. Every listed filing means `wa-f-<WSR>-pdf`, PDF page 1 participation/chain paragraphs, unless noted; full short withdrawal bodies were checked. Source hashes/locators are in the queue and original manifest. Long regulatory bodies were not certified as fully inspected by this comparison.', '']
    grouped=collections.defaultdict(list)
    for i in cases:grouped[i['proceeding']].append(i)
    for root,ii in grouped.items():
        note=notes[root];docs=sorted({n for i in ii for n in i['wsr_numbers']});orig=', '.join(docs) if docs else 'manifest/attestations; no gap originals'
        md.append(f'**WSR {root}** — '+', '.join(i['owner_ref'] for i in ii)+f'; **{note["confidence"]} LOOK** | {orig} | '+note['proposal'])
    conf=audit['case_confidence']
    md += ['',f'Case confidence: {conf.get("high",0)} high / {conf.get("medium",0)} medium / {conf.get("low",0)} low; **{len(cases)} LOOK cases**. No decisive image-only participation mark was identified: the retained image references describe technical formulas/diagrams. There are **0 visual_mark cases**, hence no `<item_id>.png` render is required or claimed as viewed.',
        '', '**Pass anomalies and shared limits:** A’s 26-13-109 missing workshop backlink is derivable and reference-only, pending append-only repair. Its three early image notes remain disclosed ordering anomalies. B’s five approved v2 corrections are selected at chain heads; 55 unrebuildable rejection tuples are not identity disagreements. Both retain unknown/unbounded dates, missing sources and unfinished horizons; no additional shared substantive mislabel was established by these checks. Neither agreement nor this source check establishes completeness. Issues 26-20/21 are unpublished; the 27 unfinished horizons remain unfinished, not disagreements.',
        '', '## Part 3 — Mandatory review and signed A1 dry run','',
        f'**Mandatory {audit["mandatory_minutes"]} minutes versus 240** (WA unset budget → PROTOCOL default; rights decision 9). No overlap credit. The union has {summary["union_opportunities"]} opportunities, above §5’s 150 threshold, so there is no every-date check; mandatory ambiguities remain. Recount after owner decisions.','',
        '| Work | N | Minutes each | Total |','|---|---:|---:|---:|']
    for r in audit['mandatory_rows']:md.append(f'| {r["work"]} | {r["N"]} | {r["minutes_each"]} | {r["N"]*r["minutes_each"]} |')
    cw=audit['crosswalk_summary'];al=fixed['allocation']
    md += ['',f'**A1: {al["high_risk_units"]} risk + {al["ordinary_units"]} ordinary = 30 units at both levels.** Level 0 retains cycles; level 1 merges them. Both retain {fixed["N"]} units and exact retrieved-entry coverage.',
        '',f'**Unaccounted owner checks: {cw["unaccounted_filing_rows"]:,} filing rows + {cw["unaccounted_document_verifications"]} non-filing verification spans = {cw["unaccounted"]:,}.** Frame: {cw["rows"]:,} rows across {cw["containers"]} containers, partitioned into {cw["owner_rows"]:,} owner rows and {cw["pointer_rows"]:,} pointers.',
        '', 'The primary issue-ownership ruling governs issue pages, type indexes, section PDFs, TABLE and INDEX: a WSR is an owner row only when its yy-ii matches the container issue. Other-issue citations remain fingerprinted pointer rows with all citing spans, excluded from both unaccounted/accounted owner checks and the complete-item read pool. Holdover/reprint citations therefore stay with their first issue.',
        '',f'**pointer_unresolved: {cw["pointer_unresolved"]:,} pointer rows / {cw["pointer_unresolved_distinct_filings"]:,} distinct filings.** Each lacks a matching filing entry anywhere in the manifest and lacks any latest union label. All other pointers retain manifest IDs and/or union record IDs. These unresolved pointers are source-gap signals, not owner accounting rows or completeness verdicts.',
        '',f'**Largest single-container unaccounted count: {cw["largest_single_container_unaccounted"]["unaccounted_rows"]}**, `{cw["largest_single_container_unaccounted"]["container_id"]}`. Per-container counts and pointer-resolution references are in the crosswalk and estimate.',
        '',f'Distinct WSR references retain every citing page/line span; **{cw["non_row_line_count"]:,} non-row lines** remain counted per frame. Directories/empty views keep six whole-original verification fallbacks; they do not fabricate filing bodies.',
        '', 'VA rates retained: W(w)=max(2,ceil(w/250)+1); container (a)=3+owner-unaccounted+min(owner-accounted,5). Pointers add zero owner checks. Item (b) uses the median eligible OWN item participation-read W(words)+residual hits+2. Full-original verifications/noncontainers remain full reads; partial/none adds 3; images/scans 3 per page. Round up stratum means; no overlap credit.',
        '', '| Level | Strata | Audit | Total | Over 240 | Tail audit | Tail total |','|---|---:|---:|---:|---:|---:|---:|']
    for l in fixed['levels']:
        tail=l['tail_risk']
        md.append(f'| {l["level"]} | {len(l["strata"])} | {l["audit_minutes"]} | {l["total_minutes"]} | {l["over_budget_minutes"]} | {tail["audit_minutes"]} | {tail["total_minutes"]} |')
    tails=fixed['levels']
    md += ['', 'Mean totals are unchanged: strata containing TABLE/INDEX receive zero allocated units at both levels; remaining changes do not change the rounded total. No skipped drawn sample or per-stratum inspection claim is implied.',
        '',f'Tails force the costliest container per allocated stratum, fill remaining seats with the costliest DISTINCT units without replacement, and use each container’s maximum eligible own-item read. Noncontainer-only strata take their costliest units. Holding item medians fixed, unit-draw tails are **{tails[0]["tail_risk"]["median_item_forced_audit_minutes"]:g} / {tails[1]["tail_risk"]["median_item_forced_audit_minutes"]:g} audit minutes** at levels 0/1. Unrestricted top-k maxima equal the full tails above. These are cost-allowance bounds, not elapsed-time guarantees or selections.',
        '', 'Both real 240-minute dry runs reject the plan; mandatory review alone is 58 over. Diagnostic ceilings print costs only. No freeze, seed, selection, completed human review, verdict or trimmed mandatory work. A1 makes no confidence claim.',
        '', 'Exact allocations, pointer/source-gap counts, unit costs and tail calculations: `audit-estimate.json` → `costings.fixed_sample_v1.levels` and `crosswalk_summary`.']
    text='\n'.join(md)+'\n';assert len(text.encode())<=25*1024,len(text.encode());(OUT/'OWNER-SHEET.md').write_text(text)
    drafts=[]
    for i in queue:
        if i['item_kind']=='class':finding=i['proposed_answer'];confidence='high';rationale=i['rationale']
        else:finding=notes[i['proceeding']]['proposal'];confidence=notes[i['proceeding']]['confidence'];rationale='Agent proposal from retained source checks; owner must inspect originals and resolve the listed trigger facts.'
        drafts.append({'schema_version':'1.0.0','record_id':'draft:'+i['item_id']+':v1','entity_id':i['item_id'],'state':'WA',
            'universe_version':'wa-v0.1+scope-signed-2026-10-15','label_version':1,'supersedes_record_id':None,'record_type':'adjudication',
            'phase':'adjudication','author':{'role':'primary','provider':'openai','model':'gpt-6.1-sol','task_id':None},'created_at':created,
            'cohorts':[],'aliases':[],'evidence':i['evidence'],'review_status':'proposed','draft':True,
            'unresolved':['Unsigned draft; no human approval, scope change, correction or canonical mapping applied.'],
            'payload':{'target_record_ids':sorted(set(i['record_ids']['A']+i['record_ids']['B'])),'trigger':i['trigger'],
                'finding':i['owner_ref']+': '+finding,'decision':'defer' if confidence=='low' or i['trigger']=='missing_source' else 'revise',
                'rationale':rationale,'confidence':confidence,'look':i['item_kind']=='case','reviewer_id':None,'started_at':None,'ended_at':None,
                'minutes':None,'audit':None,'input_versions':versions,'result_versions':[],'rescore_required':True,'rescore_refs':[],
                'item_ref':i['item_id'],'owner_ref':i['owner_ref'],'policy_key':i['policy_key']}})
    (OUT/'proposed-adjudications.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in drafts))
    print(json.dumps({'owner_sheet_bytes':len(text.encode()),'drafts':len(drafts),'mandatory_minutes':audit['mandatory_minutes'],'total_minutes':fixed['total_minutes']}))
if __name__=='__main__':main()
