#!/usr/bin/env python3
"""Independent metadata/hash/page-tree-only readiness audit. No proposer/runtime import."""
import argparse
import collections
import datetime as dt
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import re
from pypdf import PdfReader

B=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCE=B/'sources'
checks=[]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate metadata JSON key')
        d[k]=v
    return d

def load(path):return json.loads(Path(path).read_bytes(),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite metadata JSON')))
def ck(name,condition,detail=None):checks.append({'check':name,'pass':bool(condition),'detail':detail})

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--collector-ready',action='store_true',help='Primary signal received; permitted mechanical source check')
if not parser.parse_args().collector_ready:parser.exit(0,'Prepared only: awaiting primary collector READY signal; no fresh files read.\n')

manifest=load(SOURCE/'source-inputs.json')
ck('primary-manifest-READY-binding',sha(SOURCE/'source-inputs.json')=='e6999e15c1b060399bc1b62a3e71ca2d606c061b79812d2b6d01f1052a09033b')
ck('primary-collector-READY-binding',sha(SOURCE/'source-collection.READY.json')=='985417da5816324ba7dcef8f5bc482925104da6b159f3afec5bd4efa749e2cda')
pins=load(B/'runtime/implementation-pins.READY.json')
a=load(B/'execution/freeze-A.json')
source_freeze_path=B/'execution/freeze-S.json'
s=load(source_freeze_path) if source_freeze_path.exists() else None
freezes=[('A',a)]+([('S',s)] if s is not None else [])
exception_path=B/'execution/freeze-A-ledger-exception.json'
exception=load(exception_path) if exception_path.exists() else None
if exception is not None:
    ck('A-ledger-exception-receipt-binding',exception['freeze_A_sha256']==sha(B/'execution/freeze-A.json'))
    ck('A-ledger-exception-only-append-ledger',exception['path']=='sources/search-access-ledger.jsonl' and exception['original_bytes']==0 and exception['original_sha256']==hashlib.sha256(b'').hexdigest())
frozen_inventory=[];authorized_exceptions=[];A_byte_matches=0
for label,freeze in freezes:
    seen=set()
    for entry in freeze['files']:
        path=(B/entry['path']).resolve()
        ck(label+'-confined-'+entry['path'],path.is_relative_to(B))
        if not path.is_relative_to(B):raise ValueError('freeze path escapes authorized round5 root')
        ck(label+'-unique-'+entry['path'],entry['path'] not in seen);seen.add(entry['path'])
        actual=sha(path);size=path.stat().st_size
        byte_match=actual==entry['sha256'] and size==entry['bytes']
        allowed=label=='A' and exception is not None and entry['path']==exception['path'] and entry['sha256']==exception['original_sha256'] and entry['bytes']==exception['original_bytes'] and actual==exception['current_sha256'] and size==exception['current_bytes']
        if allowed:
            ck('A-ledger-current-pinned-by-S',s is not None and any(x['path']==entry['path'] and x['sha256']==actual and x['bytes']==size for x in s['files']))
            authorized_exceptions.append({'path':entry['path'],'original_sha256':entry['sha256'],'original_bytes':entry['bytes'],'current_sha256':actual,'current_bytes':size,'exception_receipt_sha256':sha(exception_path)})
        if label=='A' and byte_match:A_byte_matches+=1
        ck(label+'-hash-size-or-authorized-exception-'+entry['path'],byte_match or allowed)
        frozen_inventory.append({'freeze':label,'path':entry['path'],'sha256':actual,'bytes':size,'original_freeze_byte_match':byte_match,'authorized_append_exception':allowed})

if s is not None:
    ck('freeze-A-precedes-S',dt.datetime.fromisoformat(a['created_utc'])<dt.datetime.fromisoformat(s['created_utc']))
receipt_path=SOURCE/'freeze-receipt.json'
receipt=load(receipt_path) if receipt_path.exists() else None
if receipt is not None:
    ck('collector-receipt-A-binding',receipt.get('freeze_sha256')==sha(B/'execution/freeze-A.json'))
    ck('collector-receipt-READY-binding',receipt.get('runtime_pin_sha256')==sha(B/'runtime/implementation-pins.READY.json'))
    if isinstance(receipt.get('timestamp_utc'),str):
        timestamp=dt.datetime.fromisoformat(receipt['timestamp_utc'])
        ck('collector-receipt-after-A',dt.datetime.fromisoformat(a['created_utc'])<=timestamp)
        if s is not None:ck('collector-receipt-before-S',timestamp<dt.datetime.fromisoformat(s['created_utc']))
for path,expected in pins['code'].items():
    if not Path(path).resolve().is_relative_to(B):raise ValueError('implementation pin outside round5')
    ck('implementation-code-'+Path(path).name,sha(path)==expected)
ck('Python-version',platform.python_version()==pins['python_version'],platform.python_version())
ck('pypdf-version',importlib.metadata.version('pypdf')==pins['pypdf_version'],importlib.metadata.version('pypdf'))
ck('native-only-provider-pins',pins['provider']=='jev' and pins['runtime_channels']==['native'])
ck('round5-limit-pins',pins['limits']['documents']==8 and pins['limits']['pdf_pages']==40 and pins['limits']['jev_cases']==80 and pins['limits']['nominal_total_usd']==0.10)
ck('research-only-pins',pins['production_eligible'] is False)
ck('manifest-top-keys',set(manifest)=={'schema_version','documents'} and manifest['schema_version']=='round4.sources.v1')
required={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
seen=set();docs=[]
for u in manifest['documents']:
    if not isinstance(u,dict) or set(u)!=required:raise ValueError('manifest record includes missing/extra fields')
    ident=u['document_id'];ck('schema-exact-'+ident,set(u)==required)
    ck('opaque-unique-ID-'+ident,bool(re.fullmatch(r'doc-[a-f0-9]{12}',ident)) and ident not in seen);seen.add(ident)
    ck('native-channel-'+ident,u['channel']=='native')
    ck('scope-enum-'+ident,u['scope'] in ('full_notice','slice','unknown'))
    ck('positive-integral-pages-'+ident,type(u['pdf_pages']) is int and u['pdf_pages']>0)
    ck('boolean-page-map-'+ident,type(u['native_page_map_known']) is bool)
    paths={}
    for kind in ('pdf','text'):
        rel=u[kind+'_path'];path=(SOURCE/rel).resolve();paths[kind]=path
        confined=not Path(rel).is_absolute() and path.is_relative_to(SOURCE)
        ck('relative-confined-'+kind+'-'+ident,confined)
        if not confined:raise ValueError('source path escapes source root')
        ck('hash-format-'+kind+'-'+ident,bool(re.fullmatch(r'[a-f0-9]{64}',u[kind+'_sha256'])))
        ck('identity-'+kind+'-'+ident,sha(path)==u[kind+'_sha256'])
        if s is not None:ck('Freeze-S-binds-'+kind+'-'+ident,any(x['path']==str(path.relative_to(B)) and x['sha256']==u[kind+'_sha256'] for x in s['files']))
    ck('PDF-byte-limit-'+ident,paths['pdf'].stat().st_size<=pins['limits']['pdf_max_bytes'])
    ck('text-byte-limit-'+ident,paths['text'].stat().st_size<=2_000_000)
    # Parse the PDF page tree only: no text extraction, page render, images, or content inspection.
    actual_pages=len(PdfReader(str(paths['pdf'])).pages)
    ck('PDF-page-count-'+ident,actual_pages==u['pdf_pages'],actual_pages)
    # Native is opaque bytes. Count only mechanical form-feed delimiters; never decode/inspect notice text.
    ff=0;last=None;native_bytes=0
    with paths['text'].open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            native_bytes+=len(block);ff+=block.count(b'\x0c');last=block[-1:]
    mapped=ff+(1 if native_bytes and last!=b'\x0c' else 0)
    if u['native_page_map_known']:
        ck('native-formfeed-pages-'+ident,mapped==actual_pages,{'formfeeds':ff,'mechanical_pages':mapped})
    docs.append({'document_id':ident,'pdf_pages':actual_pages,'scope':u['scope'],'native_page_map_known':u['native_page_map_known'],
                 'pdf_bytes':paths['pdf'].stat().st_size,'native_bytes':native_bytes,'native_formfeed_pages':mapped,
                 'native_content_inspected':False})
count=len(docs);pages=sum(d['pdf_pages'] for d in docs);scopes=collections.Counter(d['scope'] for d in docs)
ck('nonempty-scheduled',0<count<=8)
ck('document-cap',count<=pins['limits']['documents'])
ck('page-cap',pages<=pins['limits']['pdf_pages'])
max_jev=pins['limits']['jev_cases']*pins['limits']['jev_request_estimated_tokens']*.000000042
ck('nominal-envelope-under-cap',max_jev<=pins['limits']['nominal_total_usd'],max_jev)
if s is not None:
    ck('manifest-is-exact-frozen-source-input',any(x['path']=='sources/source-inputs.json' and x['sha256']==sha(SOURCE/'source-inputs.json') for x in s['files']))
metadata=load(SOURCE/'source-metadata.READY.json')
ready=load(SOURCE/'source-collection.READY.json')
ck('collector-metadata-READY-binding',sha(SOURCE/'source-metadata.READY.json')==ready['metadata_sha256'])
versions=metadata.get('tools',{})
ck('native-extractor-version-retained',isinstance(versions.get('pdftotext'),str) and bool(versions['pdftotext']))
ck('A-exact-byte-match-count-with-exception',A_byte_matches+len(authorized_exceptions)==len(a['files']))
# Verify frozen files again to certify the audit didn't mutate any input or frozen implementation.
for x in frozen_inventory:ck('unchanged-'+x['freeze']+'-'+x['path'],sha(B/x['path'])==x['sha256'])
failed=[c for c in checks if not c['pass']]
result={'status':'mechanically_ready_with_scope_limitations' if not failed else 'mechanical_checks_failed',
        'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'checks_passed':len(checks)-len(failed),'checks_total':len(checks),'failed_checks':failed,
        'freeze_file_counts':{'A':len(a['files']),'S':len(s['files']) if s is not None else None},'documents':docs,'scope_counts':dict(scopes),
        'scheduled_documents':count,'actual_pdf_pages':pages,'total_native_bytes':sum(d['native_bytes'] for d in docs),
        'budget':{'jev_max_cases':80,'jev_max_input_estimate_per_case':20000,'jev_nominal_max_usd':max_jev,
                  'cap_usd':0.10,'OCR_calls':0,'actual_invoice_verified':False},
        'versions':{'Python':platform.python_version(),'pypdf':importlib.metadata.version('pypdf'),
                    'collector_tool_versions':versions},
        'freeze_A_exact_byte_matches':A_byte_matches,'freeze_A_authorized_append_exceptions':authorized_exceptions,
        'source_freeze_binding_verified':s is not None,'collector_implementation_receipt_present':receipt is not None,
        'boundaries':{'runtime_imported':False,'proposer_executed':False,'native_text_decoded_or_inspected':False,'source_truth_or_labels_read':False,
                      'page_content_extracted_or_rendered':False,'provider_calls':0,'label_keys_in_runtime_manifest':False,
                      'candidate_counts_or_accuracy_inferred':False,'source_scope_truth_verified':False},
        'pins':{'freeze_A_sha256':sha(B/'execution/freeze-A.json'),'freeze_S_sha256':sha(source_freeze_path) if s is not None else None,
                'runtime_READY_sha256':sha(B/'runtime/implementation-pins.READY.json'),'source_manifest_sha256':sha(SOURCE/'source-inputs.json')},
        'caveats':['Scope labels are collector declarations, not independently verified source truth; slice/unknown scope remains review.',
                   'No candidate count/context-length/Jev reachability or accuracy is established without running the proposer.',
                   'Fresh labels/Freeze B must be externally bound before live authorization; this audit does not read or establish those labels.',
                   'No scan/degradation status or source-page content is inspected.',
                   'Native form-feed agreement establishes page delimiter plumbing, not complete or faithful extraction.',
                   'Nominal budget envelope is an estimate, not a verified provider invoice.',
                   'Freeze A contains an authorized initially-empty access ledger; its current bytes are governed by the explicit primary exception and pinned by Freeze S. The other implementation files must match Freeze A exactly.',
                   'If Freeze S or collector implementation receipt is absent, those external bindings remain unverified.',
                   'Native UTF-8 decoding is deferred to runtime; this audit counts opaque bytes without decoding.',
                   'Source isolation remains code/data separation, not an enforced OS boundary.']}
(OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(OUT/'frozen-hash-inventory.json').write_text(json.dumps(frozen_inventory,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','checks_passed','checks_total','failed_checks','scope_counts','budget','pins')},indent=2))
