"""Read-only retained-search audit and logical quota scenarios; no acquisition."""
import hashlib,importlib.util,json,re,sys
from pathlib import Path
from urllib.parse import urlparse
R8=Path(__file__).resolve().parents[2];S=R8/'sources';V=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('Offline reconciliation prohibits network/process dispatch')
    if event=='open' and isinstance(args[0],(str,bytes)) and any(x in str(args[0]).lower() for x in ('/.env','/library/keychains/','/.aws/')):raise RuntimeError('Credential access blocked')
sys.addaudithook(guard)
before={str(f.relative_to(S)):sha(f) for f in S.rglob('*') if f.is_file()}
spec=importlib.util.spec_from_file_location('reconciliation_collector',S/'collect-native.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
plan={x['query_id']:x for x in json.loads((S/'selection-plan.json').read_text())['queries']}
inv=json.loads((S/'dedup-inventory.json').read_text());events=c.events();registrations={x['query_id']:x for x in events if x['event']=='query_registered'}
assert len(registrations)==14
# Explicit review decisions from retained title+URL only. Candidate eligibility is
# not a claim about successful PDF response, source scope, controls or completeness.
overrides={'Q03':{5,7,8},'Q05':{2,4,6,8,10,11},'Q14':{2,3,4,5,6}}
queries=[];all_rows=0
for number in range(1,15):
    q=f'Q{number:02d}';path=S/'search-results'/f'{q}.json';record=json.loads(path.read_text());rows=record['results'];all_rows+=len(rows)
    headers=re.findall(r'(?m)^([^\n]*?) \((https?://[^\n]+)\)\n[^\n]*cite',record['raw_tool_result'])
    assert headers==[(x['title'],x['url']) for x in rows]
    assert [x['display_order'] for x in rows]==list(range(1,len(rows)+1))
    assert sha(path)==registrations[q]['search_record_sha256']
    corrected=[];seen=set();omitted=[]
    for row in rows:
        official=urlparse(row['url']).hostname or '';domain=plan[q]['official_domain'];official=official==domain or official.endswith('.'+domain)
        accepted=official and (row['direct_pdf_candidate'] or row['display_order'] in overrides.get(q,set()))
        if row['display_order'] in overrides.get(q,set()):
            assert not row['direct_pdf_candidate'];omitted.append({**row,'correction_basis':'Direct publisher document View/Get endpoint' if q=='Q03' else 'Direct mass.gov/doc/.../download endpoint' if q=='Q05' else 'PDF filename title plus publisher direct hearing/document-result endpoint'})
        if accepted and row['url'] not in seen:
            seen.add(row['url'])
            if len(corrected)<3:corrected.append({'candidate_order':len(corrected)+1,'display_order':row['display_order'],'title':row['title'],'url':row['url'],'historical_url_block':c.urlkey(row['url']) in inv['blocked_url_keys']})
    old=registrations[q]['bounded_candidates']
    queries.append({'query_id':q,'rows_audited':len(rows),'record_sha256':sha(path),'raw_text_sha256':hashlib.sha256(record['raw_tool_result'].encode()).hexdigest(),'metadata_omissions':omitted,'original_bounded_display_orders':[x['display_order'] for x in old],'corrected_bounded_candidates':corrected,'bounded_set_changed':[x['url'] for x in corrected]!=[x['url'] for x in old]})
assert [q['query_id'] for q in queries if q['bounded_set_changed']]==['Q03','Q05','Q14']
for q,expected in [('Q03',[2,5,6]),('Q05',[2,4,6]),('Q14',[1,2,3])]:assert [x['display_order'] for x in next(x for x in queries if x['query_id']==q)['corrected_bounded_candidates']]==expected
assert all(x['historical_url_block'] for x in queries[-1]['corrected_bounded_candidates'])
retained=c.selected();assert [(x['state'],x['stratum'],x['pdf_pages']) for x in retained]==[('Wisconsin','general_comment',2),('Illinois','conditional_control',1),('Kentucky','conditional_control',9)]
base=retained[:2]
assert 'one-per-state until six states spread rule' in c.quota(base,'Illinois','general_comment',1)
scenarios=[]
for stratum,pages,expected_ky in [('general_comment',1,True),('general_comment',28,True),('general_comment',29,False),('general_comment',37,False),('conditional_control',1,False),('conditional_control',37,False)]:
    reasons=c.quota(base,'Massachusetts',stratum,pages);assert not reasons
    state=base+[{'state':'Massachusetts','stratum':stratum,'pdf_pages':pages}]
    ky_reasons=c.quota(state,'Kentucky','conditional_control',9)
    assert (not ky_reasons)==expected_ky
    scenarios.append({'MA_stratum':stratum,'MA_pages':pages,'MA_admitted':True,'KY_remains':expected_ky,'KY_reasons':ky_reasons,'other_MA_routes_reject_same_state':bool(c.quota(state,'Massachusetts',stratum,1))})
assert 'aggregate page cap' in c.quota(base,'Massachusetts','general_comment',38)
assert before=={str(f.relative_to(S)):sha(f) for f in S.rglob('*') if f.is_file()}
report={'status':'APPEND_ONLY_CORRECTION_AND_LOGICAL_REPLAY_REQUIRED_BEFORE_COLLECTION_RESUMES','queries_audited':14,'rows_audited':all_rows,'queries':queries,'retained_before_correction':[{'document_id':x['document_id'],'state':x['state'],'stratum':x['stratum'],'pages':x['pdf_pages']} for x in retained],'logical_MA_scenarios':scenarios,'MA_unknowns':'Actual endpoint response, PDF/body/identity/native eligibility, stratum and pages remain unobserved. No retained search snippet is used as a source classification or completeness answer.','source_bytes_unchanged':True,'source_files_checked':len(before),'pins':{'preparation_READY':sha(S/'preparation.READY.json'),'ledger':sha(S/'search-access-ledger.jsonl'),'hold':sha(S/'source-selection-hold-Q05-Q14.json'),'selection_plan':sha(S/'selection-plan.json'),'collection_protocol':sha(S/'collection-protocol.json'),'collector':sha(S/'collect-native.py'),'dedup_inventory':sha(S/'dedup-inventory.json')},'fresh_queries':0,'fresh_downloads':0,'provider_calls':0,'credential_reads':0,'limitations':['Metadata audit finds concrete direct-document omissions only in Q03/Q05/Q14; it cannot prove endpoint content without acquisition. HTML listings/news/statute/rule-detail pages are not promoted solely because their snippets discuss hearings.','Corrected logical selection order cannot restore actual chronological access; that deviation must remain disclosed.','Source controls and page/body coverage require independent source-only review after authorized bounded correction acquisition.']}
(V/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'queries':14,'rows':all_rows,'affected_queries':['Q03','Q05','Q14'],'logical_scenarios_passed':len(scenarios),'source_files_unchanged':len(before),'Q14_all_three_blocked':True}))
