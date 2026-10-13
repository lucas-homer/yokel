#!/usr/bin/env python3
"""Independent metadata/hash/page-tree-only readiness audit. No proposer/runtime import."""
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

def load(path):return json.loads(Path(path).read_bytes(),object_pairs_hook=unique)
def ck(name,condition,detail=None):checks.append({'check':name,'pass':bool(condition),'detail':detail})

manifest=load(SOURCE/'source-inputs.json')
pins=load(B/'runtime/implementation-pins.READY.json')
a=load(B/'execution/freeze-A.json');s=load(B/'execution/freeze-S.json')
frozen_inventory=[]
for label,freeze in [('A',a),('S',s)]:
    seen=set()
    for entry in freeze['files']:
        path=(B/entry['path']).resolve()
        ck(label+'-confined-'+entry['path'],path.is_relative_to(B))
        ck(label+'-unique-'+entry['path'],entry['path'] not in seen);seen.add(entry['path'])
        actual=sha(path);size=path.stat().st_size
        ck(label+'-hash-size-'+entry['path'],actual==entry['sha256'] and size==entry['bytes'])
        frozen_inventory.append({'freeze':label,'path':entry['path'],'sha256':actual,'bytes':size})
ck('freeze-A-precedes-S',dt.datetime.fromisoformat(a['created_utc'])<dt.datetime.fromisoformat(s['created_utc']))
receipt=load(SOURCE/'implementation-freeze-receipt.json')
ck('collector-receipt-A-binding',receipt['freeze_sha256']==sha(B/'execution/freeze-A.json'))
ck('collector-receipt-READY-binding',receipt['runtime_READY_sha256']==sha(B/'runtime/implementation-pins.READY.json'))
ck('collector-receipt-order',dt.datetime.fromisoformat(a['created_utc'])<=dt.datetime.fromisoformat(receipt['timestamp'])<dt.datetime.fromisoformat(s['created_utc']))
for path,expected in pins['code'].items():ck('implementation-code-'+Path(path).name,sha(path)==expected)
ck('Python-version',platform.python_version()==pins['python_version'],platform.python_version())
ck('pypdf-version',importlib.metadata.version('pypdf')==pins['pypdf_version'],importlib.metadata.version('pypdf'))
ck('two-role-only-soft-policy',set(pins['soft_issues'])=={'submission_role_unverified','written_comment_role_unverified'})
ck('research-only-pins',pins['production_eligible'] is False)
ck('manifest-top-keys',set(manifest)=={'schema_version','documents'} and manifest['schema_version']=='round4.sources.v1')
required={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
seen=set();docs=[]
for u in manifest['documents']:
    ident=u['document_id'];ck('schema-exact-'+ident,set(u)==required)
    ck('opaque-unique-ID-'+ident,bool(re.fullmatch(r'doc-[a-f0-9]{12}',ident)) and ident not in seen);seen.add(ident)
    ck('native-channel-'+ident,u['channel']=='native')
    ck('scope-enum-'+ident,u['scope'] in ('full_notice','slice','unknown'))
    ck('positive-integral-pages-'+ident,type(u['pdf_pages']) is int and u['pdf_pages']>0)
    ck('boolean-page-map-'+ident,type(u['native_page_map_known']) is bool)
    paths={}
    for kind in ('pdf','text'):
        rel=u[kind+'_path'];path=(SOURCE/rel).resolve();paths[kind]=path
        ck('relative-confined-'+kind+'-'+ident,not Path(rel).is_absolute() and path.is_relative_to(SOURCE))
        ck('hash-format-'+kind+'-'+ident,bool(re.fullmatch(r'[a-f0-9]{64}',u[kind+'_sha256'])))
        ck('identity-'+kind+'-'+ident,sha(path)==u[kind+'_sha256'])
        ck('Freeze-S-binds-'+kind+'-'+ident,any(x['path']==str(path.relative_to(B)) and x['sha256']==u[kind+'_sha256'] for x in s['files']))
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
ck('exactly-12-scheduled',count==12)
ck('exactly-52-retained-pages',pages==52)
ck('document-cap',count<=pins['limits']['documents'])
ck('page-cap',pages<=pins['limits']['ocr_pages'])
max_jev=120*20000*.000000042
all_corpus_nominal=max_jev+count*.025+pages*.002
eligible=[d for d in docs if d['scope']=='full_notice'];eligible_pages=sum(d['pdf_pages'] for d in eligible)
current_scope_nominal=max_jev+len(eligible)*.025+eligible_pages*.002
ck('nominal-envelope-under-one',all_corpus_nominal<=pins['limits']['nominal_total_usd'],all_corpus_nominal)
ck('manifest-is-exact-frozen-source-input',any(x['path']=='sources/source-inputs.json' and x['sha256']==sha(SOURCE/'source-inputs.json') for x in s['files']))
versions=load(SOURCE/'tool-versions.json')
ck('collector-pypdf-version',versions.get('pypdf')==pins['pypdf_version'])
ck('native-extractor-version-retained',versions.get('pdftotext',{}).get('exit')==0 and '26.05.0' in versions['pdftotext'].get('version_output',''))
# Verify frozen files again to certify the audit didn't mutate any input or frozen implementation.
for x in frozen_inventory:ck('unchanged-'+x['freeze']+'-'+x['path'],sha(B/x['path'])==x['sha256'])
failed=[c for c in checks if not c['pass']]
result={'status':'mechanically_ready_with_scope_limitations' if not failed else 'mechanical_checks_failed',
        'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'checks_passed':len(checks)-len(failed),'checks_total':len(checks),'failed_checks':failed,
        'freeze_file_counts':{'A':len(a['files']),'S':len(s['files'])},'documents':docs,'scope_counts':dict(scopes),
        'budget':{'jev_max_cases':120,'jev_max_input_estimate_per_case':20000,'jev_nominal_max_usd':max_jev,
                  'all_12_document_52page_nominal_max_usd':all_corpus_nominal,'full_notice_only_ocr_documents':len(eligible),
                  'full_notice_only_ocr_pages':eligible_pages,'current_scope_nominal_max_usd':current_scope_nominal,
                  'cap_usd':1.0,'actual_invoice_verified':False},
        'versions':{'Python':platform.python_version(),'pypdf':importlib.metadata.version('pypdf'),'pdftotext':'26.05.0 (retained collector metadata)'},
        'boundaries':{'runtime_imported':False,'proposer_executed':False,'native_text_decoded_or_inspected':False,'source_truth_or_labels_read':False,
                      'page_content_extracted_or_rendered':False,'provider_calls':0,'label_keys_in_runtime_manifest':False,
                      'candidate_counts_or_accuracy_inferred':False,'source_scope_truth_verified':False},
        'pins':{'freeze_A_sha256':sha(B/'execution/freeze-A.json'),'freeze_S_sha256':sha(B/'execution/freeze-S.json'),
                'runtime_READY_sha256':sha(B/'runtime/implementation-pins.READY.json'),'source_manifest_sha256':sha(SOURCE/'source-inputs.json')},
        'caveats':['Five declared full notices may receive shadow observations/OCR; seven slice/unknown notices stay review under frozen policy.',
                   'Manifest scopes are allowed collector declarations, not independently verified source truth.',
                   'No candidate count/context-length/Jev acceptance readiness is established without running the proposer; runtime limits handle these at execution.',
                   'Fresh labels/Freeze B must be externally bound before live authorization; this audit does not read or establish those labels.',
                   'No scan/degradation status is inspected or validated by this metadata audit.',
                   'Native form-feed agreement establishes page delimiter plumbing, not complete or faithful native extraction.',
                   'Nominal allowance and conservative budget admission are not verified provider invoices; OCR backend exact version is unknown.',
                   'Source isolation remains code/data separation, not an enforced OS boundary.']}
(OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(OUT/'frozen-hash-inventory.json').write_text(json.dumps(frozen_inventory,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','checks_passed','checks_total','failed_checks','scope_counts','budget','pins')},indent=2))
