#!/usr/bin/env python3
"""Render unsigned owner artifacts from the queue and checked-original notes."""
import collections
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
STATE = OUT.parent
ROOT = OUT.parents[5]

def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

CLASS_NOTES = {
 'explicit-opening': ('Record open/close/hearing_start and every session as applicable.', 'brief.txt, TEMPORAL FIELDS'),
 'fallback-key-crosswalk': ('Public comment period begins January 12, 2026, and ends February 2, 2026.', 'va-42-11-pdf p8; the two chapter-specific notices remain separate'),
 'issue-42-19-date': ('May 4, 2026', 'va-42-19-pdf p1 cover; p7 footer instead prints May 6'),
 'issue-42-25-boundary': ('July 25, 2026', 'va-42-25-pdf p1 cover image; p5–6 footers print July 27'),
 'on-or-before-cutoff': ('on or before December 31, 2025', 'va-42-08-pdf p120, order paragraph (1)'),
 'petition-disposition-enum': ('Agency Decision: Request denied.', 'va-42-08-pdf p5, PFR26-13'),
 'publication-copy': ('VOL. 42 ISS. 7', 'va-42-07-pdf p1 cover; November 17, 2025'),
 'stale-horizon-notes': ('through the second issue published after close or last hearing', 'brief.txt, Follow-up; verify the final horizon ledger, not interim boilerplate'),
 'completion-attribution': ('Counts may overlap across views.', 'brief.txt, INSPECTION AND COMPLETION; 18 B completion/final-direct-evidence discrepancies'),
}

def write_part1(items):
    classes = [i for i in items if i['item_kind'] == 'class']
    md = ['# VA owner sheet — proposed, unsigned', '',
          'The owner decides every item. Agent agreement is not a verdict. Full immutable target IDs, item IDs and class membership are in `review-queue.jsonl` and `proposed-adjudications.jsonl`. '
          'The drafts use `author.role=primary`, `review_status=proposed`, `draft:true` and null human fields; never ingest them as signed verdicts. No sealed input or adjudication log is changed.', '',
          '## Part 1 — Class questions', '',
          'Counts are A/B label-record versions / comparison instances, with overlap across classes; they are not unique opportunities. Every policy awaits owner signature. Classes settle policy only; concrete target/date/source questions remain in Part 2.', '']
    for i in classes:
        quote, cite = CLASS_NOTES[i['policy_key']]
        assert len(quote) <= 200
        md += [f'**{i["owner_ref"]}. {i["question"]}** {i["proposed_answer"]} '
               f'{i["rationale"]} **{sum(map(len, i["record_ids"].values()))} records / {i["affected_instance_count"]} instances.** '
               f'Quote: “{quote}” ({cite}).', '']
    (OUT/'OWNER-SHEET.md').write_text('\n'.join(md)+'\n')


def write_part2(items):
    checks = json.loads((OUT/'case-source-checks.json').read_text())['cases']
    by_item = {i['item_id']: i for i in items}
    boundary_ref=next(i['owner_ref'] for i in items if i.get('policy_key')=='issue-42-25-boundary')
    assert {i['item_id'] for i in items if i['item_kind'] == 'case'} == {c['item_id'] for c in checks}
    groups = collections.defaultdict(list)
    for c in checks:
        groups[c['review_bundle']].append(c)
    md = ['## Part 2 — Cases, bundled by Doc. No. and impact', '',
          '**LOOK** means personal owner inspection is required for scope, crosswalks, source gaps, conflicting dates, visuals and low-confidence proposals. '
          'Confidence rates the proposal, not source completeness. Every K-reference below is a distinct queue item and has its own draft. '
          'Cases sharing a source question are bundled in one row; all affected immutable IDs remain enumerated in the queue.', '',
          'All entry IDs below are exact `manifest.pass.jsonl` entries; pages are original PDF pages. '
          'Original bytes were hash-checked before inspection. HTML-only locators are named explicitly. '
          'Primary inspection is not the owner signature.', '',
          'Case / stake | Passes | Checked original | Proposed resolution',
          '---|---|---|---']
    for bundle, cc in groups.items():
        refs = ', '.join(c['owner_ref'] for c in cc)
        confidence = min((c['confidence'] for c in cc), key=lambda x: {'low':0, 'medium':1, 'high':2}[x])
        look = any(c['look'] for c in cc)
        triggers = ', '.join(sorted({c['trigger'].replace('_', ' ') for c in cc}))
        sources = sorted({(r['entry_id'], r['page']) for c in cc for r in c['checked_originals']})
        cite = '; '.join(f'`{mid}` p{p}' for mid, p in sources) or 'Four manifest gaps; no originals (IDs below)'
        proposals = list(dict.fromkeys(c['proposed_resolution'] for c in cc))
        claims = []
        rr = [by_item[c['item_id']] for c in cc]
        # Concise factual pass treatment, without pretending source agreement
        # certifies eligibility or printing unwieldy hashes in the owner sheet.
        if any(i['trigger'] == 'disagreement' for i in rr):
            claims.append('A/B differ on inclusion, ownership or cohorts')
        elif any(i['trigger'] == 'date_ambiguity' for i in rr):
            claims.append('A/B date/condition ambiguity')
        else:
            claims.append('A/B source-backed candidates; review remains')
        if any(i['trigger'] == 'visual_mark' for i in rr):
            render_items = [i for i in rr if i['trigger'] == 'visual_mark']
            cite += '; image ' + ', '.join(f'`{i["item_id"]}.png`' for i in render_items)
        md.append(f'**{bundle}** — {refs}; **{confidence}**' + (' **LOOK**' if look else '') +
                  ' | ' + '; '.join(claims) + ' | ' + cite + ' | ' + ' '.join(proposals))
    confidence = collections.Counter(c['confidence'] for c in checks)
    md += ['', 'Visual files are in `.census-passes/VA/review-renders/` (outside git), named by the exact visual item ID above. '
           f'All four case images and the {boundary_ref} cover image were actually viewed one per tool call. '
           'The nutrient-load formulas in R24-8010 are reference figures, not decisive participation marks.', '',
           '**Gap IDs:** `va-xa-deq-home`, `va-xa-mrc-home`, `va-xa-doe-home`, `va-xa-gov-webpolicy`. '
           'The first three are inaccessible; the fourth is missing. K78 also covers nine partial HTML views with unretained external images; PDF counterparts do not silently erase those gaps. '
           'Missing old participation originals are listed in their proceeding rows.', '',
           '**Shared problems:** both passes count the non-participation R24-7851 text erratum as an update. '
           'Both leave the supplied PFR26-03 initial period without an accepted target for its PFR26-13 decision. '
           f'Both retain unresolved 42:25 date-boundary candidates; {boundary_ref} proposes an accounting correction, not an already established error. '
           'No completeness claim follows from agreement.', '',
           f'Case confidence: {confidence["high"]} high / {confidence["medium"]} medium / {confidence["low"]} low; '
           f'**{sum(c["look"] for c in checks)} LOOK items** among {len(checks)} cases. '
           'The C04 cover additionally needs owner LOOK. Part 3 records budget overlap explicitly.', '']
    with (OUT/'OWNER-SHEET.md').open('a') as f:
        f.write('\n'.join(md)+'\n')


def write_drafts(items):
    checks = {c['item_id']: c for c in json.loads((OUT/'case-source-checks.json').read_text())['cases']}
    progress = json.loads((OUT/'.progress.json').read_text())
    if 'draft_created_at' not in progress:
        progress['draft_created_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        (OUT/'.progress.json').write_text(json.dumps(progress, indent=2)+'\n')
    refs = [STATE/'pass-A.jsonl', STATE/'pass-B.jsonl', STATE/'completion.jsonl', STATE/'manifest.jsonl',
            STATE/'brief.txt', STATE/'UNIVERSE.md', STATE/'attestations/pass-A.json', STATE/'attestations/pass-B.json',
            STATE/'supplements/pass-B/preseal-output-quality.json', STATE.parent/'PROTOCOL.md',
            STATE.parent/'SCOPE-DECISIONS.md', STATE.parent.parent/'rights/DECISIONS.md',
            ROOT/'.census-passes/VA/inputs/manifest.pass.jsonl', OUT/'review-queue.jsonl', OUT/'case-source-checks.json']
    refs += [p for p in (OUT/'audit-estimate.json', OUT/'horizon-recheck.json') if p.exists()]
    versions = [str(p.relative_to(ROOT))+'@sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in refs]
    universe = read(STATE/'pass-A.jsonl')[0]['universe_version']
    drafts=[]
    for i in items:
        if i['item_kind']=='class':
            proposal, rationale = i['proposed_answer'], i['rationale']
        else:
            c=checks[i['item_id']]
            proposal=c['proposed_resolution']
            rationale='Checked frozen original(s): '+('; '.join(f'{r["entry_id"]} p{r["page"]}' for r in c['checked_originals']) or 'No originals for the named manifest gaps')+f'. Proposal confidence {c["confidence"]}; LOOK={c["look"]}. No owner decision applied.'
        targets=sorted({rid for s in 'AB' for rid in i['record_ids'][s]} |
                       {x['detail']['manifest_entry_id'] for x in i['sub_issues'] if x['detail'].get('manifest_entry_id')})
        d={'schema_version':'1.0.0','draft':True,'record_id':'draft-owner:'+i['item_id']+':v1',
           'entity_id':i['item_id'],'state':'VA','universe_version':universe,'label_version':1,
           'supersedes_record_id':None,'record_type':'adjudication','phase':'adjudicated',
           'author':{'role':'primary','task_id':None,'provider':'openai','model':'gpt-6.1-sol'},
           'created_at':progress['draft_created_at'],'cohorts':[],'aliases':[],'evidence':[],
           'review_status':'proposed','unresolved':['Draft proposal only; owner decision required.'],
           'payload':{'trigger':i['trigger'],'target_record_ids':targets,'input_versions':versions,
                      'finding':f'{i["owner_ref"]}: {i["question"]} Proposed answer: {proposal}',
                      'decision':'not_established' if i['trigger']=='missing_source' else 'revise',
                      'rationale':rationale,'reviewer_id':None,'started_at':None,'ended_at':None,'minutes':None,
                      'result_versions':[],'rescore_required':True,'rescore_refs':[],'audit':None}}
        drafts.append(d)
    (OUT/'proposed-adjudications.jsonl').write_text(''.join(canonical(d)+'\n' for d in drafts))


def write_part3(items):
    plan=json.loads((OUT/'audit-estimate.json').read_text())
    keys=['full_content_views','container_accounting','container_accounting_participation_read','scripted_accounting_sampled_verification']
    f,c,p,s=[plan['costings'][k] for k in keys]
    histories=[x['coarsening_history'] for x in (f,c,p,s)]
    b=p['b_cost_summary'];counts=s['unaccounted_counts'];pc=p['concentration']['scenario_components'];sc=s['concentration']['scenario_components']
    md=['## Part 3 — Owner minutes: four labelled costings', '',
        '**Mandatory 271**, no overlap: 7×2 +2×1 +73×3 +6×4 +2×6 (classes/cases). '
        '203 opportunities >150: no every-date check; recount after decisions. Mandatory cases remain.', '',
        '**PROTOCOL §5:** “An issue audit checks contents/page/attachment accounting; it does not read the issue cover to cover.” '
        '“Pages, filings and history slices selected for content are read in full.” '
        '**Full-content-view (F):** first for PDF/TOCs, second for HTML sections. '
        '**Container-accounting (C):** extend first to HTML; read one whole item. '
        '**Container-accounting + participation read (P):** first, weakening “read in full”; owner approval required. '
        '**Scripted accounting + sampled verification (S)** also weakens “The human checks boundaries, accepted labels, exclusions and overlooked candidates in originals.” '
        '**S requires a PROTOCOL amendment and owner approval.**', '',
        'Coverage/strata/floors: step 1 pairs PDF/TOCs and merges cycles by source/process/format/disposition; '
        'step 2 ordinary max(2,ceil(10% N)); step 3 risk min(20,max(5,ceil(20% N))), bounded by N; scan/exclusion floor min(N,5). '
        'Columns: audit / total including 271.', '',
        'Level | Frame/units | F | C | P | S', '---|---:|---:|---:|---:|---:']
    for level,rows in enumerate(zip(*histories)):
        md.append(f'{level if level else "Baseline"} | {rows[0]["unit_count"]}/{rows[0]["sample_units"]} | '+ ' | '.join(f'{r["audit_minutes"]:,}/{r["total_minutes"]:,}' for r in rows))
    md += ['', 'Let W(w)=max(2,ceil(w/250)+1). C/P accounting is 5+0.5×listed rows; C reads W(median whole-item words). '
           'P/S (b)=W(preamble/participation words)+search hits+2, median per container. '
           'Read heading/preamble/summary and participation sections/paragraphs in full; search remaining dates/comment/hearing/objection with context. '
           'Year-like citations count conservatively. S accounting=3+unaccounted+min(accounted,5), 1 min/row. '
           'Script: zero owner minutes. Row/item draws would be seeded. 34 non-containers unchanged; stratum means round up.', '',
           f'(b) median/max: containers **{b["median_container_b_allowance_minutes"]:g}/{b["max_container_b_allowance_minutes"]:g}**; items **{b["median_item_b_minutes"]:g}/{b["max_item_b_minutes"]:g}**. '
           'Items median/max: HTML 3/44; PDFs/TOCs 38.5/2,550; all 229 containers 7/2,550. '
           'Catalogue pointers: accounting only, linked texts unsupplied. C: 85 long-body-risk containers (`long_item_dominance`).', '',
           f'S crosswalk: coarsened **{counts["coarsened"]["accounted_rows"]:,}/{counts["coarsened"]["listed_item_count"]:,} accounted**; '
           f'unaccounted **{counts["baseline"]["unaccounted_rows"]} baseline/{counts["coarsened"]["unaccounted_rows"]} coarsened**. '
           'Latest union labels, exact identity/unique text, explicit whole-agency catalogue spans; boundary-crossing rows stay unaccounted (42:14: 31). '
           'Unaccounted does not prove omission. '
           'Rows/method: `container-crosswalk.jsonl`, `container-crosswalk-summary.json`.', '',
           'Level 3 audit components, weighted by sample/N; mandatory 271 additional:', '',
           'Cost | Accounting | Reading | Non-container | Rounding', '---|---:|---:|---:|---:']
    for label,comp in [('P',pc[-1]),('S',sc[-1])]:
        md.append(label+' | '+ ' | '.join(f'{comp[k]:.1f}' for k in ('accounting_minutes','participation_read_minutes','non_container_minutes','stratum_rounding_minutes')))
    md += ['', '**Top 10 raw unit minutes; PDF includes TOC; IDs omit `va-`.** '
           'Unselected; minutes=accounting+reading. Baseline/weighted lists: `audit-estimate.json`.', '',
           'P unit | Items | Minutes', '---|---:|---:']
    def short(uid):
        a=uid.split('-');return f'{a[1]}:{a[2]} {a[3]}'
    for row in p['concentration']['coarsened_top10_units']:
        md.append(f'{short(row["unit_id"])} | {row["listed_item_count"]} | {row["accounting_minutes"]:g}+{row["participation_read_minutes"]:g}={row["minutes"]:g}')
    md += ['', 'S unit | Items/unaccounted | Minutes', '---|---:|---:']
    for row in s['concentration']['coarsened_top10_units']:
        md.append(f'{short(row["unit_id"])} | {row["listed_item_count"]}/{row["unaccounted_rows"]} | {row["accounting_minutes"]:g}+{row["participation_read_minutes"]:g}={row["minutes"]:g}')
    md += ['', f'S level 3 total **{histories[-1][-1]["total_minutes"]:,} versus 360 ({histories[-1][-1]["total_minutes"]-360:,} over)**. '
           'No freeze, seed, amendment or verdict. Unmeasured/provisional; validation/expansion adds work.', '']
    with (OUT/'OWNER-SHEET.md').open('a') as out:out.write('\n'.join(md)+'\n')

if __name__ == '__main__':
    import sys
    if '--part3-only' in sys.argv:
        sheet=OUT/'OWNER-SHEET.md'
        prefix=sheet.read_text().split('## Part 3 — Owner minutes')[0]
        sheet.write_text(prefix)
        current=read(OUT/'review-queue.jsonl')
        write_part3(current)
        write_drafts(current)
        raise SystemExit(0)
    items = read(OUT/'review-queue.jsonl')
    write_part1(items)
    if (OUT/'case-source-checks.json').exists():
        write_part2(items)
        write_drafts(items)
        if (OUT/'audit-estimate.json').exists():
            write_part3(items)
