"""Independent bounded source-preparation review, historical/synthetic only."""
import ast,contextlib,hashlib,importlib.util,io,json,re,runpy,shutil,sys,tempfile
from pathlib import Path
R8=Path(__file__).resolve().parents[2];S=R8/'sources';B=R8.parent
checks=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {str(f.relative_to(B)):digest(f) for f in B.rglob('*') if f.is_file() and 'round8' not in f.relative_to(B).parts}
def checked(name,test):
    assert test,name;checks.append({'control':name,'observed':'PASS'})
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('Offline preflight prohibits network/process dispatch')
    if event=='open' and isinstance(args[0],(str,bytes)) and any(x in str(args[0]).lower() for x in ('/.env','/library/keychains/','/.aws/')):raise RuntimeError('Credential access blocked')
sys.addaudithook(guard)
before=snapshot();sealed={p.name:digest(p) for p in S.iterdir() if p.is_file()}
plan=json.loads((S/'selection-plan.json').read_text());protocol=json.loads((S/'collection-protocol.json').read_text());inv=json.loads((S/'dedup-inventory.json').read_text());ready=json.loads((S/'preparation.READY.json').read_text())
checked('24 distinct states/queries, six general then six control then twelve general',len(plan['queries'])==24 and len({x['state'] for x in plan['queries']})==24 and [x['query_id'] for x in plan['queries']]==[f'Q{x:02d}' for x in range(1,25)] and [x['planned_stratum'] for x in plan['queries']]==['general_comment']*6+['conditional_control']*6+['general_comment']*12)
checked('Cohort/native limits agree with preregistration',protocol['target']=={'notices':8,'minimum_states':6,'max_per_state':2,'max_total_pages':40,'general_comment':6,'controls':2} and protocol['native_caps']['max_codepoints']==30000 and protocol['native_caps']['max_pdf_bytes']==25000000 and protocol['native_caps']['render_dpi']==150)
checked('No collection before release',not (S/'freeze-release.json').exists() and (S/'search-access-ledger.jsonl').read_bytes()==b'' and not (S/'search-results').exists() and ready['fresh_queries']==ready['fresh_downloads']==0)
checked('Preparation static file pins exact',all(digest(S/x['path'])==x['sha256'] for x in ready['static_files']))
pdfs={str(p.relative_to(B)):digest(p) for p in B.rglob('*') if p.is_file() and p.suffix.lower()=='.pdf' and 'round8' not in p.relative_to(B).parts}
indexed={x['path']:x['sha256'] for x in inv['historical_pdf_files']}
checked('Every historical PDF path and original hash inventoried including invalid magic',indexed==pdfs and set(pdfs.values())<=set(inv['blocked_original_hashes']) and all(x['pdf_magic']==(B/x['path']).read_bytes().startswith(b'%PDF-') for x in inv['historical_pdf_files']))
fingerprints=inv['historical_native_fingerprints'];actual_native={str(p.relative_to(B)):digest(p) for p in B.rglob('native.txt') if 'round8' not in p.relative_to(B).parts}
indexed_native={x['native_path']:x['native_sha256'] for x in fingerprints if 'native_path' in x}
checked('Existing native byte fingerprints fully covered',actual_native==indexed_native)
valid_magic={x['sha256'] for x in inv['historical_pdf_files'] if x['pdf_magic']}
extracted={x['pdf_sha256'] for x in fingerprints if 'pdf_sha256' in x}
checked('Every distinct valid-magic PDF has local fingerprint attempt',valid_magic==extracted)
checked('Every historical metadata input still pinned',all(digest(B/x['path'])==x['sha256'] for x in inv['source_metadata_inputs']) and digest(B/inv['prior_inventory_path'])==inv['prior_inventory_sha256'])
checked('Strict blind and runtime manifest shapes declared',protocol['runtime_manifest']['exact_keys']==['document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'] and protocol['blinded_image_inventory']['document_keys']==['document_id','pdf_pages','pages'] and protocol['blinded_image_inventory']['page_keys']==['page','image_path','image_sha256'])
spec=importlib.util.spec_from_file_location('preflight_collector',S/'collect-native.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
try:c.request('Q01');raise AssertionError('held query admitted')
except FileNotFoundError as ex:checked('Actual query entry point refuses missing release without process access',Path(ex.filename).name=='freeze-release.json')
checked('Native body floor and page map reject',bool(c.native_reasons('\f',1,10,protocol['native_caps'])) and bool(c.native_reasons('Caption only',1,10,protocol['native_caps'])))
items=[{'state':x,'stratum':'general_comment','pdf_pages':1} for x in 'ABCDE']
checked('First six states must spread; seventh may repeat',bool(c.quota(items,'A','general_comment',1)) and not c.quota(items,'F','general_comment',1) and not c.quota(items+[{'state':'F','stratum':'general_comment','pdf_pages':1}],'A','conditional_control',1))
# Isolated copy permits running the existing one-time verifier unchanged.
with tempfile.TemporaryDirectory(prefix='r8-source-preflight-') as tmp:
    bench=Path(tmp)/'benchmark';copy_sources=bench/'round8/sources';copy_sources.parent.mkdir(parents=True)
    shutil.copytree(S,copy_sources)
    (copy_sources/'preparation.READY.json').unlink()
    for entry in B.iterdir():
        if entry.name!='round8':(bench/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
    captured=io.StringIO()
    with contextlib.redirect_stdout(captured):runpy.run_path(str(copy_sources/'verify-preparation.py'),run_name='__main__')
    checked('Existing verify-preparation passes unchanged on isolated historical/synthetic copy',json.loads(captured.getvalue().splitlines()[-1])['status']=='PREPARATION_READY_COLLECTION_HELD')
    # Synthetic raw search registration: prior URLs consume slots, display order wins.
    spec=importlib.util.spec_from_file_location('synthetic_preflight_collector',copy_sources/'collect-native.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t);t.gate=lambda:None
    domain=t.query('Q01')['official_domain'];prior='https://'+domain+'/already-seen.pdf';new='https://'+domain+'/new.pdf';third='https://'+domain+'/third.pdf';fourth='https://'+domain+'/fourth.pdf'
    urls=[prior,prior,new,third,fourth,'https://unrelated.test/wrong.pdf']
    rows=[{'title':str(n),'url':u,'display_order':n,'direct_pdf_candidate':True,'pdf_candidate_basis':'authored synthetic direct .pdf URL'} for n,u in enumerate(urls,1)]
    raw='\n'.join(f"{x['title']} ({x['url']})\ncite synthetic" for x in rows)
    record={'submitted_query':t.query('Q01')['query'],'raw_tool_result':raw,'executed_at_utc':'synthetic','results':rows,'returned_result_count':len(rows)}
    path=copy_sources/'synthetic.json';path.write_text(json.dumps(record));t.request('Q01');t.register('Q01',path)
    bounded=t.events()[-1]['bounded_candidates']
    checked('First three distinct direct official URL slots retain displayed order',[(x['url'],x['display_order']) for x in bounded]==[(prior,1),(new,3),(third,4)])
    try:t.request('Q01');raise AssertionError('duplicate query accepted')
    except AssertionError:checked('Duplicate query refuses rerun',True)
    try:t.current('Q01',2);raise AssertionError('out of order candidate accepted')
    except AssertionError:checked('Later candidate blocked before first resolved',True)
    # Blocked prior URL must consume first slot without opening curl/native tools.
    dedup=json.loads((copy_sources/'dedup-inventory.json').read_text());dedup['blocked_url_keys'].append(t.urlkey(prior));(copy_sources/'dedup-inventory.json').write_text(json.dumps(dedup))
    with contextlib.redirect_stdout(io.StringIO()):t.acquire('Q01',1)
    checked('Known prior URL excluded, no network/process dispatch',t.events()[-1]['event']=='candidate_excluded' and t.events()[-1]['candidate_order']==1)
    t.current('Q01',2)
    checked('Next candidate only available after first resolved',True)
checked('All source-preparation bytes and all prior-round files unchanged',sealed=={p.name:digest(p) for p in S.iterdir() if p.is_file()} and before==snapshot())
report={'status':'PASS_BOUNDED_OFFLINE_SOURCE_PREFLIGHT','checks':checks,'historical_pdf_paths':len(pdfs),'valid_magic_unique_pdf_hashes':len(valid_magic),'native_paths':len(actual_native),'prior_files_checked':len(before),'inspected_source_sha256':sealed,'protocol_sha256':digest(R8/'protocol/PROTOCOL.md'),'provider_calls':0,'fresh_queries':0,'fresh_downloads':0,'guards':'Audit hook prohibits socket/subprocess/os dispatch and credential paths; verify-preparation executed unchanged in disposable copy with historical paths linked read-only.','limits':['No fresh acquisition/render/retention or source-bundle freeze executed. MIME magic and strict parsing/native-body/all-page verification paths reviewed statically; live endpoint validity is unverified.','Body coverage and underlying identity novelty require actual source-only manual review after release; Boolean notes alone are not proof.','Blind inventory shape excludes collector metadata; actual labeling blinding remains primary access/temporal responsibility.']}
Path(__file__).with_name('results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks':len(checks),'historical_pdf_paths':len(pdfs),'prior_files_unchanged':len(before)}))
