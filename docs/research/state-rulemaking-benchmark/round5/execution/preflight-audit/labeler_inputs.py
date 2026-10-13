#!/usr/bin/env python3
"""Whitelist collector provenance/images after primary READY; never read native or labels."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from pypdf import PdfReader

B=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCE=B/'sources'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--collector-ready',action='store_true')
if not p.parse_args().collector_ready:p.exit(0,'Prepared only: awaiting collector READY; no fresh files read.\n')


def unique(pairs):
    value={}
    for k,v in pairs:
        if k in value:raise ValueError('duplicate metadata key')
        value[k]=v
    return value


def load(path):
    return json.loads(Path(path).read_bytes(),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def checked_file(rel,expected):
    if not isinstance(rel,str) or Path(rel).is_absolute():raise ValueError('nonrelative inventory path')
    path=(SOURCE/rel).resolve()
    if not path.is_relative_to(SOURCE):raise ValueError('inventory path escapes source root')
    if not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{64}',expected) or sha(path)!=expected:
        raise ValueError('inventory file hash differs')
    return {'path':str(path),'sha256':expected,'bytes':path.stat().st_size}


manifest=load(SOURCE/'source-inputs.json')
manifest_sha=sha(SOURCE/'source-inputs.json')
if manifest_sha!='e6999e15c1b060399bc1b62a3e71ca2d606c061b79812d2b6d01f1052a09033b':raise ValueError('manifest differs from primary READY signal')
ready_path=SOURCE/'source-collection.READY.json'
if sha(ready_path)!='985417da5816324ba7dcef8f5bc482925104da6b159f3afec5bd4efa749e2cda':raise ValueError('collector READY differs from primary signal')
ready=load(ready_path)
metadata_path=SOURCE/'source-metadata.READY.json'
if sha(metadata_path)!=ready['metadata_sha256']:raise ValueError('collector metadata READY binding differs')
metadata=load(metadata_path)
if not isinstance(metadata,dict) or not isinstance(metadata.get('documents'),list):raise ValueError('unsupported collector metadata')
required={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
if set(manifest)!={'schema_version','documents'} or manifest['schema_version']!='round4.sources.v1':raise ValueError('manifest schema differs')
if not 0<len(manifest['documents'])<=8 or sum(u['pdf_pages'] for u in manifest['documents'])>40:raise ValueError('manifest caps exceeded')
by_id={x['document_id']:x for x in metadata['documents']}
if len(by_id)!=len(metadata['documents']) or set(by_id)!={x['document_id'] for x in manifest['documents']}:raise ValueError('metadata IDs differ')
rows=[]
for u in manifest['documents']:
    if set(u)!=required or u['channel']!='native' or not re.fullmatch(r'doc-[a-f0-9]{12}',u['document_id']):raise ValueError('invalid manifest record')
    m=by_id[u['document_id']];url=m['publisher_url']
    if not isinstance(url,str) or urlsplit(url).scheme not in ('http','https'):raise ValueError('missing official source URL')
    artifacts={x['path']:x for x in m['artifact_files']}
    provenance_file=checked_file(m['provenance_path'],artifacts[m['provenance_path']]['sha256'])
    provenance=load(provenance_file['path'])
    original_paths=[x for x in artifacts if Path(x).name=='original.pdf']
    if len(original_paths)!=1:raise ValueError('original PDF path missing/ambiguous')
    original_rel=provenance.get('original_path',original_paths[0])
    if original_rel!=original_paths[0]:raise ValueError('original provenance/artifact path differs')
    original=checked_file(original_rel,provenance['original_sha256'])
    if original['sha256']!=artifacts[original_rel]['sha256']:raise ValueError('original artifact/provenance hash differs')
    input_pdf=checked_file(u['pdf_path'],u['pdf_sha256'])
    original_pages=len(PdfReader(original['path']).pages)
    input_pages=len(PdfReader(input_pdf['path']).pages)
    if input_pages!=u['pdf_pages'] or input_pdf['sha256']!=provenance['input_sha256']:raise ValueError('input PDF identity/page mismatch')
    # Exact original/input byte identity proves page-order identity; no semantic boundary assumption.
    identical=original['sha256']==input_pdf['sha256']
    if not identical:raise ValueError('original/input differ with no explicit physical mapping; do not guess')
    physical=list(range(1,input_pages+1))
    images=[];numbers=[]
    for im in m['rendered_pages']:
        page=im['page'];numbers.append(page)
        if type(page) is not int or not 1<=page<=input_pages:raise ValueError('image page outside input range')
        images.append({'input_page':page,'original_physical_page':physical[page-1],**checked_file(im['path'],im['sha256'])})
    if sorted(numbers)!=list(range(1,input_pages+1)):raise ValueError('missing/duplicate image page coverage')
    command=provenance.get('diagnostics',{}).get('pdftotext')
    command_hash=hashlib.sha256(command.encode()).hexdigest() if isinstance(command,str) else None
    rows.append({'document_id':u['document_id'],'official_url':url,'official_url_independently_verified_by_this_audit':False,
        'original_pdf':{**original,'page_count':original_pages},'input_pdf':{**input_pdf,'page_count':input_pages},
        'physical_original_pages':physical,'physical_mapping_basis':'original/input SHA256 byte identity',
        'images':sorted(images,key=lambda x:x['input_page']),
        'native_extraction_provenance':{'tool':'pdftotext','tool_version':metadata.get('tools',{}).get('pdftotext'),
            'exact_command_sha256':command_hash,'exact_command_retained_by_collector':command_hash is not None,
            'native_contents_omitted':True,'command_text_omitted':True},
        'scan_mechanical_facts':{'scan_status_independently_checked':False}})
output={'schema_version':'round5.labeler-inputs.v1','documents':rows,
        'source_manifest_sha256':manifest_sha,
        'boundaries':{'native_text_included':False,'labels_read':False,'proposer_executed':False,'provider_calls':0,
                      'collector_substantive_assertions_included':False,'image_content_inspected':False},
        'limitations':['URL identity and physical mapping are collector provenance, not independent substantive notice verification.',
                       'All image files are hash checked and cover each input page; visual fidelity and boundaries are not established here.',
                       'Scan/degradation classification is omitted; collector prose/strata/comment-term/expected-value signals are never copied.',
                       'Exact extraction command retained externally; only its tool, exit and hash enter this inventory.']}
(OUT/'labeler-inputs.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({'documents':len(rows),'images':sum(len(x['images']) for x in rows),'output':str(OUT/'labeler-inputs.json'),
                  'native_text_included':False,'collector_substantive_assertions_included':False},indent=2))
