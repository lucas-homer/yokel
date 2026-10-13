"""Final read-only source evidence audit; no labels, providers or fresh access."""
import hashlib,importlib.util,json,math,re,subprocess,sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from pypdf import PdfReader
from PIL import Image
V=Path(__file__).resolve().parent;R=V.parents[1];S=R/'sources';C=S/'reconciliation';POP=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
allowed_pdfs=set()
def guard(event,args):
 if event.startswith('socket.') or event in ('os.system','os.posix_spawn'):raise RuntimeError('Network/process dispatch forbidden')
 if event=='subprocess.Popen':
  command=args[1]
  if not (isinstance(command,list) and len(command)==7 and command[:4]==[str(POP/'pdftotext'),'-layout','-enc','UTF-8'] and command[4] in allowed_pdfs and command[5:] == ['-']):
   # Standard pdftotext command has six elements.
   if not (isinstance(command,list) and len(command)==6 and command[:4]==[str(POP/'pdftotext'),'-layout','-enc','UTF-8'] and command[4] in allowed_pdfs and command[5]=='-'):raise RuntimeError('Only pinned local pdftotext replay permitted')
 if event=='open' and isinstance(args[0],(str,bytes)):
  name=str(args[0]).lower()
  if any(x in name for x in ('/.env','/library/keychains/','/.aws/','/truth','/labels','/labeler-output','/reference-label')):raise RuntimeError('Credential/label/reference access forbidden')
sys.addaudithook(guard)
def get(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,condition):assert condition,name;checks.append(name)
freeze_s=R/'execution/freeze-S.json';check('Requested source freeze identity',sha(freeze_s)=='11714af529a247e31079f82cb30870d7f07c682ad9d4df906a7d030b8909d94f')
for name,count in [('freeze-S.json',927),('freeze-A.json',69)]:
 f=get(R/'execution'/name);check(name+' file count',len(f['files'])==count)
 check(name+' exact content hashes',all(sha(R/x['path'])==x['sha256'] for x in f['files']))
 check(name+' exact byte lengths',all((R/x['path']).stat().st_size==x['bytes'] for x in f['files']))
static_before={x['path']:sha(R/x['path']) for x in get(freeze_s)['files']}
spec=importlib.util.spec_from_file_location('final_source_companion',C/'companion_v2.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
base=c.verify_baseline();check('Original source baseline unchanged',len(base['source_files'])==503)
old=c.original_events();new=c.access_events();all_events=old+new
intents=[x for x in all_events if x['event']=='query_invocation_intent'];registered=[x for x in all_events if x['event']=='query_registered'];plan={x['query_id']:x for x in get(S/'selection-plan.json')['queries']}
check('24 single invocations and registrations',Counter(x['query_id'] for x in intents)==Counter({q:1 for q in plan}) and Counter(x['query_id'] for x in registered)==Counter({q:1 for q in plan}))
check('Original frozen query strings',all(x['submitted_query']==plan[x['query_id']]['query'] for x in intents+registered))
view=c.replay();final=get(C/'logical-selection.FINAL.json');check('Final view equals authoritative replay',view==final)
check('No unresolved logical slots',view['pending_candidate'] is None and len(view['decisions'])==71)
check('Corrected shortfall disclosed',not view['target_achieved'] and view['cohort_classification']=='protocol-deviation corrected' and view['physical_access_order_restored'] is False)
row_count=0;bounds=c.bounds();audited=[]
for reg in registered:
 q=reg['query_id'];root=S if int(q[1:])<=14 else C;p=root/reg['search_record_path'];record=get(p);row_count+=len(record['results'])
 check(q+' retained raw hash',sha(p)==reg['search_record_sha256'])
 headers=re.findall(r'(?m)^([^\n]*?) \((https?://[^\n]+)\)\n[^\n]*cite',record['raw_tool_result']);check(q+' raw ordered rows',headers==[(x['title'],x['url']) for x in record['results']])
 rows=record['results']
 if q=='Q18':
  approved=get(C/'Q18-resolution.APPROVED.json');check('Q18 exact-hash primary resolution',approved['retained_search_record_sha256']==sha(p) and approved['authorized_resolution'] is True)
  rows=approved['reviewed_results'];check('Q18 unchanged title/URL/reference ordering',[(x['title'],x['url'],x['reference_metadata']) for x in rows]==[(x['title'],x['url'],x['reference_metadata']) for x in record['results']])
  check('Q18 reviewed explicit PDFs', [x['display_order'] for x in rows if x['direct_pdf_candidate']]==[1,2,6,9,15])
 if int(q[1:])<=14:
  expected=next(x['corrected_bounded_candidates'] for x in get(C/'plan-amendment.json')['queries'] if x['query_id']==q)
 else:
  direct=[];seen=set();domain=plan[q]['official_domain']
  for row in rows:
   review=row['source_route_review'];check(q+' row review '+str(row['display_order']),review['reviewed_from_saved_metadata'] is True and bool(review['basis']) and (review['classification']=='direct_document')==row['direct_pdf_candidate'])
   host=urlparse(row['url']).hostname or ''
   if row['direct_pdf_candidate'] and (host==domain or host.endswith('.'+domain)) and row['url'] not in seen:
    seen.add(row['url']);direct.append(row)
  expected=[{'url':x['url'],'display_order':x['display_order']} for x in direct[:3]]
 check(q+' bounded order',[(x['url'],x['display_order']) for x in bounds[q]]==[(x['url'],x['display_order']) for x in expected])
 audited.append({'query_id':q,'rows':len(rows),'bounded_display_orders':[x['display_order'] for x in bounds[q]],'record_sha256':sha(p)})
check('413 total displayed results',row_count==413)
check('All logical bounded sets resolved',sum(len(x) for x in bounds.values())==71 and Counter((x['query_id'],x['display_order'],x['url']) for x in view['decisions'])==Counter((q,x['display_order'],x['url']) for q,cs in bounds.items() for x in cs))
logical= [x for x in c.lines(C/'correction-ledger.jsonl') if x['event']=='logical_decision'];check('Append-only correction decisions equal final view',[{k:v for k,v in x.items() if k not in ('timestamp_utc','event')} for x in logical]==view['decisions'])
manifest=get(S/'source-inputs.READY.json');blind=get(S/'blinded-image-inventory.READY.json');metadata=get(S/'source-metadata.READY.json');schedule=get(R/'execution/schedule.json');labeler=get(R/'execution/preflight-audit/labeler-inputs.json')
for filename in ['source-inputs.READY.json','blinded-image-inventory.READY.json','source-metadata.READY.json']:check('Byte identical promotion '+filename,(S/filename).read_bytes()==(C/filename).read_bytes())
ids=[x['document_id'] for x in view['selected']]
check('Five IDs match runtime/images/metadata/schedule/labeler',len(ids)==5 and all([x['document_id'] for x in value['documents']]==ids for value in [manifest,blind,metadata,schedule,labeler]))
check('Five states/17 pages/3 general2 control',len({x['state'] for x in view['selected']})==5 and sum(x['pdf_pages'] for x in view['selected'])==17 and Counter(x['stratum'] for x in view['selected'])=={'general_comment':3,'conditional_control':2})
inv=get(S/'dedup-inventory.json');docs=[];current_original=set();current_native=set();current_normal=set()
for item,row,imgs,sched,labeled in zip(view['selected'],manifest['documents'],blind['documents'],schedule['documents'],labeler['documents']):
 ident=row['document_id'];folder=S/item['artifact_folder'];prov=get(folder/'provenance.json');pdfpath=S/row['pdf_path'];allowed_pdfs.add(str(pdfpath));raw=(S/row['text_path']).read_bytes();text=raw.decode('utf-8');pdf=PdfReader(pdfpath,strict=True);norm=c.frozen.textkey(text)
 check(ident+' runtime exact nine keys',set(row)=={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'})
 check(ident+' original=input/native hashes',sha(folder/'original.pdf')==sha(pdfpath)==row['pdf_sha256']==prov['original_sha256'] and sha(S/row['text_path'])==row['text_sha256']==prov['native_sha256'])
 check(ident+' PDF magic and strict pages',pdfpath.read_bytes().startswith(b'%PDF-') and len(pdf.pages)==row['pdf_pages'])
 check(ident+' unchanged native replay',subprocess.run([str(POP/'pdftotext'),'-layout','-enc','UTF-8',str(pdfpath),'-'],capture_output=True,check=True).stdout==raw)
 check(ident+' native byte/page caps',not c.frozen.native_reasons(text,len(pdf.pages),pdfpath.stat().st_size,get(S/'collection-protocol.json')['native_caps']))
 check(ident+' frozen/current dedup',row['pdf_sha256'] not in inv['blocked_original_hashes'] and row['text_sha256'] not in inv['blocked_native_hashes'] and norm not in inv['blocked_normalized_text_hashes'] and row['pdf_sha256'] not in current_original and row['text_sha256'] not in current_native and norm not in current_normal)
 current_original.add(row['pdf_sha256']);current_native.add(row['text_sha256']);current_normal.add(norm)
 check(ident+' identity/body provenance assertions',prov['prior_notice_identity_duplicate'] is False and prov['body_coverage_verified'] is True and prov['material_native_damage'] is False and bool(prov['notice_identity']) and bool(prov['boundary_evidence']) and bool(prov['dedup_evidence']))
 check(ident+' schedule fields',sched['pdf_sha256']==row['pdf_sha256'] and sched['pdf_pages']==row['pdf_pages'] and sched['state']==item['state'] and sched['stratum']==('general' if item['stratum']=='general_comment' else 'control'))
 check(ident+' minimal blind schemas',set(imgs)=={'document_id','pdf_pages','pages'} and set(labeled)=={'document_id','pdf_sha256','pdf_pages','pages'})
 check(ident+' all-page evidence counts',len(imgs['pages'])==len(labeled['pages'])==len(prov['body_coverage_evidence'])==len(pdf.pages))
 for n,(page,coverage,label,pdfpage) in enumerate(zip(imgs['pages'],prov['body_coverage_evidence'],labeled['pages'],pdf.pages),1):
  path=S/page['image_path'];check(ident+' page'+str(n)+' blind hash/minimal shape',set(page)==set(label)=={'page','image_path','image_sha256'} and page['page']==label['page']==coverage['page']==n and Path(label['image_path']).resolve()==path.resolve() and sha(path)==page['image_sha256']==label['image_sha256']==coverage['image_sha256'])
  with Image.open(path) as image:size=image.size;image.verify()
  w,h=float(pdfpage.mediabox.width),float(pdfpage.mediabox.height)
  if pdfpage.rotation in [90,270]:w,h=h,w
  check(ident+' page'+str(n)+' render dimensions',all(abs(a-b)<=1 for a,b in zip(size,[math.ceil(w/72*150),math.ceil(h/72*150)])))
  check(ident+' page'+str(n)+' body ledger',coverage['native_matches_visual_body'] is True and bool(coverage['evidence']) and (not coverage['substantive_body_present'] or coverage['native_body_present'] is True))
 for attempt in [prov]:check(ident+' bounded HTTP attempts',1<=len(attempt['attempts'])<=2 and (len(attempt['attempts'])==1 or attempt['attempts'][0]['returncode']!=0))
 docs.append({'document_id':ident,'state':item['state'],'stratum':item['stratum'],'pages':row['pdf_pages'],'native_codepoints':len(text),'native_sha256':row['text_sha256'],'PDF_sha256':row['pdf_sha256']})
check('Freeze still matches after read-only audit',all(sha(R/p)==h for p,h in static_before.items()))
report={'disposition':'PASS_READ_ONLY_FINAL_SOURCE_EVIDENCE_AUDIT','checks':len(checks),'query_count':24,'displayed_rows':row_count,'logical_slots':71,'selected_notices':5,'selected_states':5,'selected_pages':17,'strata':{'general':3,'control':2},'shortfall':{'notices':3,'states':1,'general':3,'controls':0},'cohort_classification':'protocol-deviation corrected','physical_access_order_restored':False,'documents':docs,'query_audit':sorted(audited,key=lambda x:x['query_id']),'logical_status_counts':dict(Counter(x['logical_status'] for x in view['decisions'])),'logical_exclusion_reasons':dict(Counter(reason for x in view['decisions'] if x['logical_status']=='excluded' for reason in x['logical_reasons'])),'freeze_S_sha256':sha(freeze_s),'freeze_A_sha256':sha(R/'execution/freeze-A.json'),'source_manifest_sha256':sha(S/'source-inputs.READY.json'),'blinded_manifest_sha256':sha(S/'blinded-image-inventory.READY.json'),'labeler_minimal_input_sha256':sha(R/'execution/preflight-audit/labeler-inputs.json'),'provider_calls':0,'fresh_access':0,'labels_truth_read':False,'native_replays':5,'visual_review_scope':'PNG hashes and image integrity/dimensions checked for all17 pages; body visual comparisons are retained source-owner evidence. This reviewer did not independently inspect all17 page pixels or create/inspect reference labels.','deviations':['Q03/Q05/Q14 converter omissions corrected append-only; Q03 display13 physically accessed outside corrected bounds; Q05 catch-up after Q14; no restored physical chronology.','Q18 metadata correction uses exact-hash primary-approved response with same17 title/URL/reference rows and bounded ranks1/2/6; original held bytes retained.','Q21 own-ledger aggregate exclusion replay bug corrected via v2-only historical path condition; v1 frozen bytes preserved and duplicate retrieval refused before curl.'],'material_concerns':['Sampling adequacy target failed:5/8 notices,5/6 states,3/6 general; original eight-notice model-comparison gate must remain false.','Novelty and substantive body coverage rely on source-only human/AI ledger judgments in addition to verified fingerprints and replay; no independent full-page visual completeness claim here.']}
(V/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['disposition','checks','query_count','displayed_rows','logical_slots','selected_notices','selected_states','selected_pages','strata','logical_status_counts']}))
