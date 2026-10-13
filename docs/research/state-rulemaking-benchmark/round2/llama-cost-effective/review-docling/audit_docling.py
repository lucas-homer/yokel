"""Read-only Docling artifact verification; schema/export only, no PDF conversion."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,statistics,math,platform,importlib.metadata
from docling_core.types.doc import DoclingDocument,ContentLayer
import pypdfium2
BASE=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-benchmark');P=BASE/'artifacts';D=BASE/'round2/docling';O=BASE/'round2/llama-cost-effective/review-docling';O.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
checks=[];captures=[];inventory=[];limitations=[];nonfinite=[];secret=[]
def ck(i,ok,d,paths=[]):checks.append({'check_id':i,'status':'pass' if ok else 'fail','details':d,'evidence_paths':paths})
expected='900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946';freeze=read(P/'corpus-freeze.json');units={u['fixture_id']:u for u in freeze['units']};plan=read(D/'input-plan.json');result=read(D/'results.json');runtime=read(D/'runtime.json');validation=read(D/'validation.json');source=(D/'run_docling.py').read_text();before={str(p.relative_to(D)):sha(p) for p in D.rglob('*') if p.is_file()}
ck('child-final-report', (D/'README.md').exists() and result['completed']==20 and result['operational_successes']==20 and result['operational_failures']==0 and not result['not_attempted'] and validation['passed'],'Final child report/validation/result present; pipeline completion distinct from content quality')
ck('frozen-manifest',sha(P/'corpus-freeze.json')==expected==plan['freeze_sha256']==result['freeze_sha256'],expected)
changed=[n for n,m in freeze['files'].items() if sha(P/n)!=m['sha256'] or (P/n).stat().st_size!=m['bytes']];ck('141-frozen-files',not changed,{'files':len(freeze['files']),'changed_paths':changed})
ret=read(P/'retention-manifest.json');changedold=[x['path'] for x in ret['files'] if sha(P/x['path'])!=x['sha256'] or (P/x['path']).stat().st_size!=x['bytes']];ck('629-baseline-files',not changedold,{'files':len(ret['files']),'changed_paths':changedold})
ck('20-unit-plan',len(plan['units'])==20 and {x['fixture_id'] for x in plan['units']}==set(units) and sum(x['input_page_count'] for x in plan['units'])==34 and plan['parser_metadata_sha256']==sha(P/'parser-inputs.json'),'Unique 20 frozen parser inputs and34pages')
ck('runtime-versions',runtime['docling_version']==result['docling_version']==importlib.metadata.version('docling')=='2.134.0' and runtime['python']==platform.python_version(),'Retained runtime Docling/Python versions match available isolated runtime')
versions={};mismatch=[]
for line in (D/'requirements.lock.txt').read_text().splitlines():
 if '==' not in line:continue
 name,version=line.split('==',1);versions[name]=version
 try:actual=importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:actual=None
 if actual!=version:mismatch.append(name)
ck('resolved-package-lock',not mismatch,{'locked_packages':len(versions),'mismatch_packages':mismatch,'key_versions':{k:versions[k] for k in ['docling','docling-core','docling-parse','ocrmac','torch']}})
opts=runtime['pipeline_options'];ck('runtime-pipeline-provenance',opts['do_ocr'] and opts['do_table_structure'] and opts['accelerator_options']['device']=='cpu' and opts['accelerator_options']['num_threads']==4 and not opts['enable_remote_services'] and not opts['allow_external_plugins'] and not runtime['remote_parse_services'] and not runtime['custom_prompts'] and not runtime['reference_answers_used'] and runtime['markdown_layers']==[c.value for c in ContentLayer],'Local CPU4 layout/table, OCR and table structure, all content layers, no configured remote services/plugins/prompts')
ck('configured-ocr-backend-source','OcrMacOptions' in source and "recognition='accurate'" in source and "lang=['en-US']" in source and 'force_full_page_ocr=False' in source and "HF_HUB_DISABLE_IMPLICIT_TOKEN" in source,'Retained source explicitly selects Apple Vision/ocrmac accurate en-US adaptive OCR; runtime option JSON omits subtype recognition/kind fields')
ck('serial-stop-source','if failures>=3:stop=True' in source and 'for position,f in enumerate(order):' in source and 'raises_on_error=False' in source,'Serial conversion and three-failure stop implemented; no failures exercise stop')
planunits={x['fixture_id']:x for x in plan['units']};comparisons=[]
for fid,u in units.items():
 folder=D/fid;c=read(folder/'capture.json');pu=planunits[fid];inputp=P/u['directory']/'input.pdf';nativep=P/u['directory']/'native.txt';pdf=pypdfium2.PdfDocument(inputp);actualpages=len(pdf);pdf.close();
 ck('input-'+fid,sha(inputp)==u['input_sha256']==pu['input_sha256']==c['input_sha256'] and inputp.stat().st_size==u['input_bytes']==pu['input_bytes']==c['input_bytes'] and actualpages==u['input_page_count']==c['input_pages'],'Exact frozen input hash, bytes and independent physical PDF page count',[str(inputp.relative_to(P))])
 native=(folder/'native.txt').read_bytes();ck('native-'+fid,native==nativep.read_bytes() and sha(folder/'native.txt')==pu['native_sha256']==c['native_baseline']['sha256'] and len(native)==pu['native_bytes']==c['native_baseline']['bytes'],'Native text copy is byte-identical to frozen embedded-text baseline; not new OCR output')
 ck('status-'+fid,c['fixture_id']==fid and c['status']=='success' and c['operational_success'] and c['converted_page_count']==u['input_page_count'] and not c['errors'],'Recorded successful complete conversion, not evidence accuracy')
 for item in c['outputs']:
  p=D/item['path'];ck('output-hash-'+fid+'-'+p.suffix,p.parent==folder and sha(p)==item['sha256'] and p.stat().st_size==item['bytes'],'Retained output hash/byte count agree',[item['path']])
 doc=DoclingDocument.model_validate_json((folder/'output.json').read_bytes());md=(folder/'output.md').read_bytes();export=doc.export_to_markdown(included_content_layers=set(ContentLayer)).encode();
 ck('structured-schema-pages-'+fid,len(doc.pages)==u['input_page_count'] and set(doc.pages)==set(range(1,u['input_page_count']+1)),'DoclingDocument schema validates and pages cover complete input')
 ck('full-markdown-export-'+fid,md==export and bool(md.strip()),'Retained bytes exactly equal independent full-content-layer export from validated document JSON')
 wall=(dt(c['ended_at_utc'])-dt(c['started_at_utc'])).total_seconds()*1000;ck('timing-'+fid,0<=wall and abs(wall-c['wrapper_wall_ms'])<=2 and c['process_cpu_user_seconds']>=0 and c['process_cpu_system_seconds']>=0,'Recorded wrapper elapsed/CPU values consistent; RSS is cumulative process high-water mark')
 nf=[]
 def walk(x,path=''):
  if isinstance(x,dict):
   for k,v in x.items():walk(v,path+'/'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+'/'+str(i))
  elif isinstance(x,float) and not math.isfinite(x):nf.append(path)
 walk(c)
 if nf:nonfinite.append({'path':fid+'/capture.json','json_paths':nf})
 comparisons.append({'fixture_id':fid,'native_bytes':len(native),'docling_markdown_bytes':len(md),'native_equals_docling_markdown_bytes':native==md,'not_quality_score':True});captures.append(c)
ordered=sorted(captures,key=lambda c:dt(c['started_at_utc']));ck('serial-observed-order', [c['fixture_id'] for c in ordered]==result['completion_order'] and all(dt(ordered[i-1]['ended_at_utc'])<=dt(ordered[i]['started_at_utc']) for i in range(1,len(ordered))),'Recorded conversion intervals do not overlap; sequence matches result ledger')
ck('pilot-operational-gate',[c['fixture_id'] for c in ordered[:2]]==['A01','A06'] and all(c['pilot'] and c['operational_success'] for c in ordered[:2]) and all(not c['pilot'] for c in ordered[2:]),'Scanned A01 and native-text A06 pilots succeed before18 remaining units; quality not a gate')
warm=[c['wrapper_wall_ms'] for c in ordered[1:]];timing={'first_A01_wrapper_ms':ordered[0]['wrapper_wall_ms'],'remaining19_median_ms':statistics.median(warm),'remaining19_min_ms':min(warm),'remaining19_max_ms':max(warm),'peak_cumulative_rss_bytes':max(c['process_peak_rss_bytes'] for c in ordered),'not_isolated_benchmark':True};ck('reported-timing-summary',timing['first_A01_wrapper_ms']==validation['cold_A01_wall_ms'] and timing['remaining19_median_ms']==validation['warm_wall_ms']['median'] and timing['peak_cumulative_rss_bytes']==validation['process_peak_rss_bytes'],timing)
models=read(D/'model-cache-manifest.json');cache=Path(runtime['environment_root']);modelbad=[]
for x in models:
 p=cache/x['path']
 if not p.is_file() or sha(p)!=x['sha256'] or p.stat().st_size!=x['bytes']:modelbad.append(x['path'])
ck('model-cache-manifest',len(models)==result['model_files_hashed']==42 and not modelbad,{'model_files':len(models),'changed_paths':modelbad})
ck('model-revisions',all(Path(r['path']).read_text().strip()==r['resolved_revision'] for r in validation['model_revisions']),'Retained resolved model refs agree with available cache; main alias was not pre-download immutable')
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 inventory.append({'path':str(p.relative_to(D)),'sha256':sha(p),'bytes':p.stat().st_size})
 if p.suffix in ['.json','.md','.log']:
  s=p.read_text()
  if re.search(r'https?://[^\s"<>]*(?:X-Amz-Signature|X-Goog-Signature|X-Amz-Credential)=|Bearer\s+[A-Za-z0-9._-]{12,}',s,re.I):secret.append({'path':str(p.relative_to(D)),'category':'signed URL or bearer token pattern'})
ck('artifact-secret-pattern-scan',not secret,{'findings':secret})
after={str(p.relative_to(D)):sha(p) for p in D.rglob('*') if p.is_file()};ck('docling-files-stable-during-audit',before==after,'No Docling child artifact changed during this read-only review')
limitations=['All20pipeline completions are operational results, not content quality or deadline correctness; no scoring performed.','Capture confidence metadata has non-finite NaN values: strict JSON parsers reject these files. Use tolerant parsing or derive a separate strict-JSON confidence sidecar with explicit null/unknown values; do not silently rewrite original captures.','Runtime pipeline_options serialization omits OCR subtype recognition/kind fields; retained source supplies configuration evidence for OcrMac accurate en-US.','Exact Markdown re-export verifies consistency with retained DoclingDocument; not independent proof of semantic fidelity to source.','First conversion includes possible cold model download/init/OCR warmup; later converter reuse means one-run wrapper times do not establish comparative speed. Install/model acquisition, energy and full-machine load are not measured.','Peak RSS is cumulative macOS process high-water mark; Apple Vision internal accelerator selection is not controlled by CPU layout/table options.','Models/local isolated runtime remain in temporary storage. Hashed revisions support provenance while available; main alias was not pinned before initial download.','No conversion rerun, model inference, credential access, network/provider calls or Docling artifact mutation by this audit.']
report={'schema_version':'docling-operations-audit-v1','audited_at_utc':datetime.now(timezone.utc).isoformat(),'status':'complete_operational_evidence_with_json_portability_limitation','checks':checks,'failed_checks':[c['check_id'] for c in checks if c['status']=='fail'],'units':20,'input_pages':34,'operational_successes':20,'runtime_versions':{k:versions[k] for k in ['docling','docling-core','docling-parse','ocrmac','torch']},'timing':timing,'native_byte_comparisons':comparisons,'nonfinite_capture_json':nonfinite,'content_scoring_performed':False,'secret_findings':secret,'limitations':limitations}
(O/'audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');(O/'artifact-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n');(O/'audit_docling.py').write_bytes(Path(__file__).read_bytes());print(json.dumps({'checks':len(checks),'failed_checks':report['failed_checks'],'units':20,'pages':34,'nonfinite_capture_files':len(nonfinite),'native_equal_docling_markdown':sum(c['native_equals_docling_markdown_bytes'] for c in comparisons),'model_files_verified':len(models)}))
