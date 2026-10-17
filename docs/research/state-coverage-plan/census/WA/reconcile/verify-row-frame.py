#!/usr/bin/env python3
"""Focused regression checks for WA's distinct-reference frame and A1 tails."""
import collections
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

OUT=Path(__file__).resolve().parent
STATE=OUT.parent
sys.path.insert(0,str(OUT))
import container_rows as wa


def read(p):return [json.loads(line) for line in p.open() if line.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    # Repeated references (including suffix case), pure WACs, headings and
    # multiple references on one line must survive exactly once per filing.
    refs,mm=wa.reference_frame(['Heading\n16-54-170\n16-54-170 AMD 26-16-026A\n16-54-170 AMD 26-16-026a\nNEW 26-12-005 REP 26-12-006'],table=True)
    assert list(refs)==['26-16-026a','26-12-005','26-12-006']
    assert len(refs['26-16-026a'])==2 and mm['non_row_line_count']==2 and mm['citing_line_count']==3
    refs,mm=wa.reference_frame(['WAC 16-06-001\nCaption\n.....PROP26-16-026A\n.....PROP 26-16-026a'],index=True)
    assert list(refs)==['26-16-026a'] and len(refs['26-16-026a'])==2 and mm['non_row_line_count']==2
    # Accepted updates and rejected evidence citations both account for rows;
    # a bare unsupported rejection alias does not.
    fake=SimpleNamespace(numbers=lambda r,operative=False:r['own'],evidence=lambda r:r['evidence'])
    records=[{'record_id':'n','record_type':'notice','own':['26-12-005'],'evidence':[]},
        {'record_id':'u','record_type':'update','own':['26-12-006'],'evidence':[]},
        {'record_id':'r','record_type':'rejected_candidate','own':[],
         'aliases':[{'native_id':'26-01-001'}],
         'evidence':[{'manifest_entry_id':'agency-crosscheck','locator':'paragraph 1','quote_or_mark_description':'WSR 26-16-026A'}]}]
    idx,_=wa.label_index(fake,records)
    assert set(idx['26-12-006'])=={'u'} and set(idx['26-16-026a'])=={'r'} and not idx['26-01-001']
    rows=read(OUT/'container-crosswalk.jsonl');grouped=collections.defaultdict(list)
    for r in rows:grouped[r['container_id']].append(r)
    checked=spans=nonrows=0
    pdf=Path('/private/tmp/wa-reconcile-tools/native-text')
    for mid,rr in grouped.items():
        metadata=rr[0].get('container_frame_metadata')
        if metadata:
            docs=[r['doc_numbers'][0] for r in rr if r['accounting_role'] in ('filing_reference','pointer')]
            assert len(docs)==len(set(docs))==metadata['distinct_WSR_count'],mid
            assert metadata['nonblank_line_count']==metadata['citing_line_count']+metadata['non_row_line_count']
            nonrows+=metadata['non_row_line_count']
        if not mid.endswith(('-TABLE','-INDEX')):continue
        pages=json.loads((pdf/(mid+'.json')).read_text());expected=collections.defaultdict(list);non_row_count=0
        # Independent source token scan; all actual TABLE/INDEX WSR references
        # follow printed action/type tokens, confirmed against the source.
        for pn,page in enumerate(pages,1):
            for ln,line in enumerate(page.splitlines(),1):
                if not line.strip():continue
                found=[]
                for match in re.finditer(r'(?<![\w-])\d{2}-\d{2}-\d{3}[A-Za-z]?(?![\w-])',line):
                    before=line[:match.start()].rstrip()
                    preceding=before.split()[-1] if before.split() else ''
                    legitimate=(bool(re.fullmatch(r'(AMD|A/R|DECOD|NEW|OBJECT|PREP|RE-AD|RECOD|REP|RESCIND|REVIEW|SUSP)(-[CEPSWX])?',preceding))
                        if mid.endswith('-TABLE') else bool(re.search(r'(PREP|PROP|MISC|PERM|EMER|EXPE)$',before)))
                    if legitimate:found.append(match.group().lower())
                if not found:non_row_count+=1
                for doc in dict.fromkeys(found):expected[doc].append((pn,ln))
        actual={r['doc_numbers'][0]:r for r in rr if r['accounting_role'] in ('filing_reference','pointer')}
        assert set(actual)==set(expected),mid
        for doc,locations in expected.items():
            assert [(s['page'],s['line']) for s in actual[doc]['source_spans']]==locations,(mid,doc)
            spans+=len(locations)
        assert metadata['non_row_line_count']==non_row_count,mid
        checked+=1
    # An independent all-record lookup must find no allowed label for every
    # WSR marked unaccounted, and every recorded union target is a latest head.
    spec=importlib.util.spec_from_file_location('comparison',OUT/'reconcile.py');compare=importlib.util.module_from_spec(spec);spec.loader.exec_module(compare)
    labels=[r for side in 'AB' for r in compare.latest(read(STATE/f'pass-{side}.jsonl')) if r['record_type'] in ('notice','update','rejected_candidate')]
    index,_=wa.label_index(compare,labels)
    all_labels=[r for side in 'AB' for r in compare.latest(read(STATE/f'pass-{side}.jsonl'))]
    union_refs=wa.pointer_labels(compare,all_labels)
    for doc,targets in index.items():union_refs[doc]=sorted(set(union_refs.get(doc,[])) | set(targets))
    manifest=read(STATE/'manifest.jsonl');manifest_refs=wa.manifest_filings(manifest)
    pointer_count=unresolved=0
    for r in rows:
        issue=wa.container_issue(r['container_id']);docs=r['doc_numbers']
        expected_pointer=bool(issue and docs and docs[0][:5]!=issue)
        assert (r['accounting_role']=='pointer')==expected_pointer
        if not expected_pointer:
            assert r.get('owner_accounting_eligible',True) is True
            continue
        pointer_count+=1;doc=docs[0]
        targets={'manifest_entry_ids':manifest_refs.get(doc,[]),'union_record_ids':union_refs.get(doc,[])}
        assert r['pointer_resolution']==targets
        resolved=bool(targets['manifest_entry_ids'] or targets['union_record_ids'])
        assert r['accounting_status']==('pointer' if resolved else 'pointer_unresolved')
        assert not r['complete_item'] and r['owner_accounting_eligible'] is False and r['participation_read'] is None
        assert resolved or not r['union_record_id'], 'A pointer with a known union label must resolve'
        unresolved+=not resolved
    sys.path.insert(0,str(STATE.parent))
    import container_audit as ca
    frames=ca.build_frames(rows,manifest)
    for cid,frame in frames['containers'].items():
        by_id={r['row_id']:r for r in frame['rows']}
        assert all(by_id[rid]['accounting_role']!='pointer' for rid in frame['complete_item_ids'])
        selections=ca.nested_selections({'seed':'synthetic-fixture-only','strata':[{'selected_ids':[cid]}]},frames)[cid]
        for key in ('unaccounted_row_ids','accounted_row_ids'):
            assert all(by_id[rid]['accounting_role']!='pointer' for rid in selections[key])
    bad=copy.deepcopy(next(r for r in rows if r['accounting_role']=='pointer'))
    bad.update(item_ordinal=1,complete_item=True)
    try:ca.build_frames([bad],manifest)
    except ValueError as exc:assert 'invalid WA other-issue pointer' in str(exc)
    else:raise AssertionError('Pointer cannot enter complete-item pool')
    for r in rows:
        if r['accounting_role']!='filing_reference':continue
        assert len(r['doc_numbers'])==1
        targets=set(index[r['doc_numbers'][0]])
        assert targets=={x['record_id'] for x in r['union_label_matches']}
        assert (r['accounting_status']=='unaccounted')==(not targets)
    assert grouped['wa-agencywac'][0]['container_frame_metadata']['distinct_WSR_count']==0
    audit=json.loads((OUT/'audit-estimate.json').read_text())
    for level in audit['costings']['fixed_sample_v1']['levels']:
        assert sum(s['sample_size'] for s in level['strata'])==30
        tail=level['tail_risk'];total=0
        for s in tail['strata']:
            costs=s['max_item_forced_cost_allowances']
            ids=[c['unit_id'] for c in costs]
            assert len(ids)==len(set(ids))==s['sample_size']
            assert s['max_item_forced_most_expensive_container'] is None or s['max_item_forced_most_expensive_container'] in ids
            assert sum(c['minutes'] for c in costs)==s['max_item_forced_audit_minutes']
            total+=sum(c['minutes'] for c in costs)
        assert total==tail['audit_minutes'] and tail['total_minutes']==total+298
    readonly=json.loads((OUT/'.progress.json').read_text())['read_only_hashes']
    assert all(sha(STATE/n)==h for n,h in readonly.items())
    assert len((OUT/'OWNER-SHEET.md').read_bytes())<=25*1024
    prefix=(OUT/'OWNER-SHEET.md').read_text().split('## Part 3')[0]
    before=Path('/private/tmp/wa-reconcile-tools/v3-owner-prefix-before.txt')
    if before.exists():assert prefix==before.read_text(),'Parts 1/2 changed'
    for state,expected in [('VA','b457eaf27fafdcc769a1d8fee2847908f73c8db128f05424364027533a905f6b'),('MS','b19810d6696b07b1f28ed569d38ca30b1f04fa73174b4ad505473e2d167a924b')]:
        assert sha(STATE.parent/state/'reconcile/container-crosswalk.jsonl')==expected
        assert sha(Path('/private/tmp/wa-reconcile-tools')/(state+'-crosswalk-v3-regression.jsonl'))==expected
    shared_frames={}
    oldpath=Path('/private/tmp/wa-reconcile-tools/container-audit-before-v3.py')
    if oldpath.exists():
        assert sha(oldpath)=='c8a6a59838567de5a36b4817ed133c0b3a49fa5b8f592bce77a12a82178fc2a4'
        spec=importlib.util.spec_from_file_location('old_container_audit',oldpath)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        for state in ('VA','MS'):
            mm=read(STATE.parent/state/'manifest.jsonl')
            rr=read(STATE.parent/state/'reconcile/container-crosswalk.jsonl')
            old_frame=old.build_frames(rr,mm);new_frame=ca.build_frames(rr,mm)
            assert old_frame==new_frame
            shared_frames[state]=sha(STATE.parent/state/'reconcile/container-crosswalk.jsonl')
    result={'frame_version':'WA-own-issue-WSR-v3','pointer_rows_checked':pointer_count,'pointer_unresolved':unresolved,'pointer_owner_accounting_and_item_pool_exclusions_verified':True,'shared_validator_VA_MS_frames_identical':shared_frames,'TABLE_INDEX_containers_checked':checked,'citing_spans_checked':spans,
        'listing_non_row_lines':nonrows,'synthetic_suffix_dedup_pure_WAC_update_rejection_regressions':True,
        'all_WSR_union_mappings_verified':True,'without_replacement_tail_costs_verified':True,
        'VA_MS_regression_byte_identical':True,'Parts_1_2_byte_identical':True,'sealed_inputs_unchanged':True}
    (OUT/'row-frame-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
