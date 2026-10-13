#!/usr/bin/env python3
"""Mechanical-only preflight. No extraction, runtime imports, model calls or labels."""
import argparse,datetime,hashlib,importlib.metadata,json,math,platform,re,subprocess
from pathlib import Path
from urllib.parse import urlparse
from pypdf import PdfReader
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
FREEZE_A_SHA='d2acd7aaed9d08298809aeda03f25ddecf5df28913b753512fdc7fe0edfabe9f'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def confined(root,rel):
    if not isinstance(rel,str) or Path(rel).is_absolute():raise ValueError('relative path required')
    path=(root/rel).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():raise ValueError('path missing or escapes root')
    return path

def native_metrics(data):
    text=data.decode('utf-8',errors='strict')
    return {'bytes':len(data),'codepoints':len(text),'formfeeds':text.count('\f'),'replacement_characters':text.count('\ufffd'),'nonempty':bool(text.strip())}

def minimal_document(doc,unit,prov,pages,sources):
    folder=sources/'documents'/doc
    return {'document_id':doc,'pdf_pages':unit['pdf_pages'],'official_url':prov['url'],
      'original_pdf_path':str(folder/'original.pdf'),'original_pdf_sha256':digest(folder/'original.pdf'),
      'input_pdf_path':str(folder/'input.pdf'),'input_pdf_sha256':unit['pdf_sha256'],
      'pages':[{'page':x['page'],'image_path':str(confined(sources,x['image_path'])),'image_sha256':x['image_sha256']} for x in pages]}

def write_new(path,value):
    data=(json.dumps(value,indent=2)+'\n').encode()
    with path.open('xb') as f:f.write(data)

def run(release_path):
    sources=ROOT/'sources';checks=[]
    def check(name,ok,document_id=None):
        checks.append({'check':name,'passed':bool(ok),**({'document_id':document_id} if document_id else {})})
        if not ok:raise ValueError(name)
    release=read(release_path);ready_path=sources/'source-collection.READY.json'
    check('explicit primary source-audit release',set(release)=={'schema_version','authorized_mechanical_source_audit','primary_release_message','freeze_A_sha256','source_READY_sha256'} and release['schema_version']=='round6.preflight-release.v1' and release['authorized_mechanical_source_audit'] is True and isinstance(release['primary_release_message'],str) and bool(release['primary_release_message']) and release['freeze_A_sha256']==FREEZE_A_SHA and release['source_READY_sha256']==digest(ready_path))
    check('Freeze A receipt pin',digest(ROOT/'execution/freeze-A.json')==FREEZE_A_SHA)
    freeze=read(ROOT/'execution/freeze-A.json')
    for item in freeze['files']:
        path=confined(ROOT,item['path']);check('Freeze A exact hash: '+item['path'],digest(path)==item['sha256'] and path.stat().st_size==item['bytes'])
    freeze_s_path=ROOT/'execution/freeze-S.json';freeze_s=read(freeze_s_path)
    for item in freeze_s['files']:
        path=confined(ROOT,item['path']);check('Freeze S exact hash: '+item['path'],digest(path)==item['sha256'] and path.stat().st_size==item['bytes'])
    ready=read(ready_path);check('source collection edits complete',ready['collection_edits_complete'] is True)
    acceptance=read(ROOT/'execution/Q01-correction-acceptance.json');correction=read(sources/'Q01-metadata-correction-review.json')
    check('Q01 accepted correction receipt bound',acceptance['review_receipt_sha256']==digest(sources/'Q01-metadata-correction-review.json') and acceptance['original_record_sha256']==correction['original_record_sha256'] and acceptance['corrected_record_sha256']==correction['corrected_record_sha256'])
    original_record=confined(sources,correction['original_record']);corrected_record=confined(sources,correction['corrected_record'])
    check('Q01 preserved original and corrected metadata hashes',digest(original_record)==correction['original_record_sha256'] and digest(corrected_record)==correction['corrected_record_sha256'])
    check('Q01 same retained raw response',read(original_record)['raw_tool_result']==read(corrected_record)['raw_tool_result'])
    deviation={'primary_acceptance_path':str(ROOT/'execution/Q01-correction-acceptance.json'),'primary_acceptance_sha256':digest(ROOT/'execution/Q01-correction-acceptance.json'),'source_correction_path':str(sources/'Q01-metadata-correction-review.json'),'source_correction_sha256':digest(sources/'Q01-metadata-correction-review.json'),'original_metadata_incomplete':True,'appended_correction_canonical':True,'manual_acquisition_deviation_retained':True,'original_result_count':correction['returned_results_initial_metadata'],'corrected_result_count':correction['returned_results_actual'],'same_raw_response_verified':True}

    for rel,want in ready['artifacts'].items():check('source READY artifact: '+rel,digest(confined(sources,rel))==want)
    index=read(sources/'source-files.READY.json');expected=set()
    for item in index['files']:
        path=confined(sources,item['path']);expected.add(item['path']);check('source file exact hash: '+item['path'],digest(path)==item['sha256'] and path.stat().st_size==item['bytes'])
    actual={str(path.relative_to(sources)) for path in sources.rglob('*') if path.is_file() and '__pycache__' not in path.parts and str(path.relative_to(sources)) not in index['excluded_paths']}
    check('source complete file inventory',actual==expected and len(expected)==len(index['files']))
    manifest=read(sources/'source-inputs.READY.json') if (sources/'source-inputs.READY.json').exists() else {'schema_version':'round4.sources.v1','documents':[]}
    images=read(sources/'blinded-image-inventory.READY.json');metadata=read(sources/'source-metadata.READY.json');selection=read(sources/'selection-plan.json');toolchain=read(sources/'native-toolchain.json')
    check('strict runtime manifest',set(manifest)=={'schema_version','documents'} and manifest['schema_version']=='round4.sources.v1' and len(manifest['documents'])<=8)
    check('minimal collector image inventory',set(images)=={'schema_version','documents'} and images['schema_version']=='round6.blinded-images.v1' and all(set(d)=={'document_id','pdf_pages','pages'} and all(set(x)=={'page','image_path','image_sha256'} for x in d['pages']) for d in images['documents']))
    check('same opaque document sets',len({d['document_id'] for d in manifest['documents']})==len(manifest['documents'])==len(images['documents'])==len(metadata['documents']) and {d['document_id'] for d in manifest['documents']}=={d['document_id'] for d in images['documents']}=={d['document_id'] for d in metadata['documents']})
    query={q['query_id']:q for q in selection['queries']};blocked=set(read(sources/'dedup-inventory.json')['blocked_original_hashes']);inventory=[];metrics=[];total_pages=0
    required={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
    for unit in manifest['documents']:
        doc=unit['document_id'];check('opaque identity and exact native unit',set(unit)==required and re.fullmatch(r'doc-[a-f0-9]{12}',doc) is not None and unit['channel']=='native' and unit['scope']=='full_notice' and unit['native_page_map_known'] is True and type(unit['pdf_pages']) is int and unit['pdf_pages']>0,doc)
        folder=sources/'documents'/doc;prov=read(folder/'provenance.json');text_path=confined(sources,unit['text_path']);pdf_path=confined(sources,unit['pdf_path']);original=folder/'original.pdf'
        check('original=input=provenance hashes',digest(original)==digest(pdf_path)==unit['pdf_sha256']==prov['original_sha256'] and doc=='doc-'+unit['pdf_sha256'][:12] and unit['pdf_sha256'] not in blocked,doc)
        check('native exact byte identity',digest(text_path)==unit['text_sha256']==prov['native_sha256'],doc)
        metric=native_metrics(text_path.read_bytes());check('native size and existing page map',metric['nonempty'] and metric['codepoints']<=30000 and metric['replacement_characters']==0 and metric['formfeeds']==unit['pdf_pages'] and metric['bytes']<=2000000 and original.stat().st_size<=25000000,doc)
        pdf=PdfReader(str(pdf_path));check('physical PDF pages',len(pdf.pages)==unit['pdf_pages'],doc);total_pages+=len(pdf.pages)
        domain=query[prov['query_id']]['official_domain'];url=prov['url'];host=urlparse(url).hostname or '';response=prov['response_metadata'];finalhost=urlparse(response[1]).hostname or ''
        check('recorded official URL and redirect provenance',urlparse(url).scheme in ('https','http') and (host==domain or host.endswith('.'+domain)) and (finalhost==domain or finalhost.endswith('.'+domain)) and response[2].lower().startswith('application/pdf'),doc)
        image_doc=next(d for d in images['documents'] if d['document_id']==doc);page_list=image_doc['pages'];check('image document page count',image_doc['pdf_pages']==unit['pdf_pages'],doc);check('all pages image map',len(page_list)==len(pdf.pages) and [x['page'] for x in page_list]==list(range(1,len(pdf.pages)+1)),doc)
        for row,page in zip(page_list,pdf.pages):
            png=confined(sources,row['image_path']);check('image hash page '+str(row['page']),digest(png)==row['image_sha256'],doc)
            with Image.open(png) as image:size=image.size;image.verify()
            width,height=float(page.mediabox.width),float(page.mediabox.height)
            if page.rotation in (90,270):width,height=height,width
            expected_size=[math.ceil(width/72*150),math.ceil(height/72*150)]
            check('150 DPI dimensions page '+str(row['page']),all(abs(a-b)<=1 for a,b in zip(size,expected_size)),doc)
        check('recorded native/render tool versions',prov['render_dpi']==150 and set(prov['tools'])=={'pdfinfo','pdffonts','pdfimages','pdftotext','pdftoppm'} and all(toolchain['version'] in value for value in prov['tools'].values()),doc)
        inventory.append(minimal_document(doc,unit,prov,page_list,sources));metrics.append({'document_id':doc,**metric,'pdf_pages':len(pdf.pages)})
    check('aggregate source caps',len(inventory)<=8 and total_pages<=40)
    check('pinned Python and pypdf versions',platform.python_version()==toolchain['python'] and importlib.metadata.version('pypdf')==toolchain['pypdf'])
    tools={};pop=Path(toolchain['extractor']).parent
    for name in ('pdfinfo','pdffonts','pdfimages','pdftotext','pdftoppm'):
        command=subprocess.run([str(pop/name),'-v'],capture_output=True,check=True);value=command.stderr.decode().splitlines()[0];tools[name]=value;check('local tool version: '+name,toolchain['version'] in value)
    report={'schema_version':'round6.mechanical-preflight.v1','passed':True,'collection_target_achieved':ready['target_achieved'],'collection_status':ready['status'],'recorded_collection_counts':ready['counts'],'collection_shortfall_blockers':['eight-notice target not achieved','six-state target not achieved','six-general/two-control cohort not achieved'] if not ready['target_achieved'] else [],'accepted_procedural_deviation':deviation,'freeze_S_sha256':digest(freeze_s_path),'freeze_A_files_checked':len(freeze['files']),'freeze_S_files_checked':len(freeze_s['files']),'checks':len(checks),'documents':len(inventory),'PDF_pages':total_pages,'source_READY_sha256':digest(ready_path),'freeze_A_sha256':FREEZE_A_SHA,'release_sha256':digest(release_path),'metrics':metrics,'tools':tools,'python_pypdf':importlib.metadata.version('pypdf'),'provider_calls':0,'native_extractions':0,'labels_read':False,'semantic_source_fidelity_or_notice_completeness_verified':False,'limitations':'Existing native bytes/hash/page separators only; no semantic content inspection, extraction replay, source selection assertions, truth or model outputs. Official provenance is recorded metadata, not fresh network validation.'}
    write_new(OUT/'checks.json',checks);write_new(OUT/'audit.json',report);write_new(OUT/'labeler-inputs.json',{'schema_version':'round6.provenance-images.v1','documents':inventory})
    write_new(OUT/'audit.READY.json',{'artifacts':{n:digest(OUT/n) for n in ('checks.json','audit.json','labeler-inputs.json')},'passed':True});return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--primary-release',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(run(args.primary_release)))
