"""Answer-blind local Docling collection over exact frozen diagnostic inputs."""
import os
from pathlib import Path
ENVROOT=Path('/private/tmp/docling-round2-20261006')
for key,folder in [('HF_HOME','hf-cache'),('TORCH_HOME','torch-cache'),('XDG_CACHE_HOME','cache')]:os.environ[key]=str(ENVROOT/folder)
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
os.environ['OMP_NUM_THREADS']='4';os.environ['TOKENIZERS_PARALLELISM']='false'
import argparse,hashlib,json,time,datetime,resource,platform,importlib.metadata

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):path.write_text(json.dumps(value,indent=2,default=str)+'\n')
p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=a.artifacts.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
freeze=Path(__file__).resolve().parent/'freeze.json';before=sha(freeze);manifest=json.loads(freeze.read_text())
assert manifest['status']=='adjudicated_frozen_before_parser_execution'
for rel,rec in manifest['files'].items():assert sha(root/rel)==rec['sha256'],rel
units=[]
import subprocess
assert len(manifest['units'])==8 and sum(u['input_page_count'] for u in manifest['units'])==22
for f in manifest['units']:
 fid=f['fixture_id'];path=root/'heldout'/fid/'input.pdf';assert sha(path)==f['input_sha256'] and path.stat().st_size==f['input_bytes']
 assert not (out/fid).exists(),'Refuse existing captures'
 nd=out/'native';nd.mkdir(exist_ok=True);native=nd/(fid+'.txt')
 subprocess.run(['/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',str(Path(__file__).with_name('extract_native.py')),str(path),str(native)],check=True)
 units.append({**f,'input_path':str(path),'native_path':str(native),'native_sha256':sha(native),'native_bytes':native.stat().st_size})
save(out/'input-plan.json',{'freeze_sha256':before,'units':units,'expected_pages':22,'input_bytes_unchanged':True,'native_command':'bundled Python extract_native.py INPUT OUTPUT','native_version':'pdftotext26.05.0'})
from docling.datamodel.pipeline_options import PdfPipelineOptions,OcrMacOptions
from docling.datamodel.accelerator_options import AcceleratorOptions,AcceleratorDevice
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter,PdfFormatOption
from docling_core.types.doc import ContentLayer
from docling.datamodel.settings import settings
settings.cache_dir=ENVROOT/'docling-cache'
assert importlib.metadata.version('docling')=='2.134.0'
options=PdfPipelineOptions(do_ocr=True,do_table_structure=True,ocr_options=OcrMacOptions(lang=['en-US'],recognition='accurate',force_full_page_ocr=False),accelerator_options=AcceleratorOptions(num_threads=4,device=AcceleratorDevice.CPU),document_timeout=300)
converter=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)})
save(out/'runtime.json',{'prepared_at_utc':utc(),'docling_version':importlib.metadata.version('docling'),'python':platform.python_version(),'platform':platform.platform(),'machine':platform.machine(),'local_hardware':{'memory_bytes':34359738368,'physical_cpus':10,'model':'Mac16,10'},'pipeline_options':options.model_dump(mode='json'),'markdown_layers':[x.value for x in ContentLayer],'environment_root':str(ENVROOT),'docling_cache':str(settings.cache_dir),'inference':'Local Docling standard PDF pipeline; layout/table models CPU4threads, OCR Apple Vision via ocrmac; Vision internal accelerator choice not controlled','remote_parse_services':False,'custom_prompts':False,'reference_answers_used':False,'timing_limitations':['First conversion may include public model download, lazy initialization and OCR warmup; later calls reuse in-process converter','One run per unit, no isolated speed benchmark; process cumulative peak RSS on macOS reported in bytes','Native baseline freshly extracted after heldout freeze']})
records=[];failures=0;stop=False
order=units
for position,f in enumerate(order):
 if stop:break
 fid=f['fixture_id'];d=out/fid;d.mkdir();assert sha(Path(f['input_path']))==f['input_sha256'];native=Path(f['native_path']).read_bytes();(d/'native.txt').write_bytes(native)
 start=utc();tick=time.monotonic();cpu=resource.getrusage(resource.RUSAGE_SELF);capture={'fixture_id':fid,'input_sha256':f['input_sha256'],'input_bytes':f['input_bytes'],'input_pages':f['input_page_count'],'started_at_utc':start,'pilot':position<2,'native_baseline':{'source':str(Path(f['native_path'])),'sha256':f['native_sha256'],'bytes':f['native_bytes'],'method':'Fresh pdftotext26.05.0 extraction after heldout freeze; no OCR'},'outputs':[]}
 try:
  result=converter.convert(Path(f['input_path']),raises_on_error=False,max_num_pages=f['input_page_count'])
  doc=result.document;md=doc.export_to_markdown(included_content_layers=set(ContentLayer));(d/'output.md').write_bytes(md.encode())
  doc.save_as_json(d/'output.json')
  status=result.status.value;page_count=len(doc.pages);success=status=='success' and page_count==f['input_page_count'] and bool(md.strip())
  capture.update(status=status,converted_page_count=page_count,operational_success=success,errors=[e.model_dump(mode='json') for e in result.errors],confidence=result.confidence.model_dump(mode='json'))
  for name in ['output.md','output.json']:path=d/name;capture['outputs'].append({'path':fid+'/'+name,'sha256':sha(path),'bytes':path.stat().st_size})
 except Exception as error:
  capture.update(status='exception',operational_success=False,error_class=type(error).__name__,error_message=str(error))
 after=resource.getrusage(resource.RUSAGE_SELF);capture.update(ended_at_utc=utc(),wrapper_wall_ms=round((time.monotonic()-tick)*1000),process_cpu_user_seconds=after.ru_utime-cpu.ru_utime,process_cpu_system_seconds=after.ru_stime-cpu.ru_stime,process_peak_rss_bytes=after.ru_maxrss)
 save(d/'capture.json',capture);records.append(capture);failures=0 if capture['operational_success'] else failures+1
 print(json.dumps({'fixture_id':fid,'success':capture['operational_success'],'wall_ms':capture['wrapper_wall_ms'],'status':capture['status']}),flush=True)
 if failures>=3:stop=True
 if position==1 and not all(c['operational_success'] for c in records):stop=True
 save(out/'progress.json',{'completed':len(records),'successes':sum(c['operational_success'] for c in records),'consecutive_failures':failures,'stopped':stop})
assert sha(freeze)==before
for rel,rec in manifest['files'].items():assert sha(root/rel)==rec['sha256'],rel
models=[]
for cache in [ENVROOT/'docling-cache',ENVROOT/'hf-cache',ENVROOT/'torch-cache']:
 if cache.exists():
  for path in cache.rglob('*'):
   if path.is_file() and not path.is_symlink():models.append({'path':str(path.relative_to(ENVROOT)),'bytes':path.stat().st_size,'sha256':sha(path)})
save(out/'model-cache-manifest.json',models)
save(out/'results.json',{'freeze_sha256':before,'docling_version':'2.134.0','expected_units':8,'expected_pages':22,'completed':len(records),'operational_successes':sum(c['operational_success'] for c in records),'operational_failures':sum(not c['operational_success'] for c in records),'stopped':stop,'not_attempted':[f['fixture_id'] for f in units if f['fixture_id'] not in {r['fixture_id'] for r in records}],'completion_order':[r['fixture_id'] for r in records],'frozen_files_unchanged':True,'model_files_hashed':len(models),'captures':[r['fixture_id']+'/capture.json' for r in records]})
print('COMPLETE '+json.dumps({'completed':len(records),'successes':sum(c['operational_success'] for c in records),'stopped':stop}),flush=True)
