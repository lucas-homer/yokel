#!/usr/bin/env python3
"""Offline preparation checks and one-time preparation seal; no network."""
import ast,datetime,hashlib,importlib.util,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parent
assert not (ROOT/'preparation.READY.json').exists(),'Preparation already sealed; do not rewrite.'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,d):(ROOT/n).write_text(json.dumps(d,indent=2)+'\n')
for p in ROOT.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in ROOT.glob('*.json'):json.loads(p.read_text())
spec=importlib.util.spec_from_file_location('r8collector',ROOT/'collect-native.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.selftest()
try:c.request('Q01');raise AssertionError('release gate unexpectedly opened')
except FileNotFoundError as e:assert pathlib.Path(e.filename).name=='preparation.READY.json'
items=[{'state':x,'stratum':'general_comment','pdf_pages':1} for x in ['A','B','C','D','E']]
assert 'one-per-state until six states spread rule' in c.quota(items,'A','general_comment',1)
assert not c.quota(items,'F','general_comment',1)
items.append({'state':'F','stratum':'general_comment','pdf_pages':1})
assert not c.quota(items,'A','conditional_control',1)
old=json.loads((ROOT.parent.parent/'round6/sources/search-submission-Q01.corrected.json').read_text())
headers=re.findall(r'(?m)^([^\n]*?) \((https?://[^\n]+)\)\n[^\n]*cite',old['raw_tool_result'])
assert len(headers)==18 and headers==[(x['title'],x['url']) for x in old['results']]
# Use a disposable local root; lifecycle evidence must not contaminate the actual ledger.
original_gate,original_root=c.gate,c.ROOT
import tempfile
with tempfile.TemporaryDirectory(dir=ROOT) as td:
 tmp=pathlib.Path(td);(tmp/'search-access-ledger.jsonl').write_text('');(tmp/'selection-plan.json').write_bytes((ROOT/'selection-plan.json').read_bytes());c.ROOT=tmp;c.gate=lambda:None;c.request('Q01')
 bad=tmp/'partial.json';partial=dict(old);partial['results']=old['results'][1:];partial['returned_result_count']=17;partial['submitted_query']=c.query('Q01')['query'];bad.write_text(json.dumps(partial))
 try:c.register('Q01',bad);raise AssertionError('partial raw metadata accepted')
 except AssertionError as e:assert 'Raw displayed headers' in str(e)
 assert (tmp/'search-results/Q01.json').read_bytes()==bad.read_bytes()
c.gate,c.ROOT=original_gate,original_root
# Execute one-shot/empty/failed/unknown/primary-review controls on disposable copies.
import unittest
suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_search_resolution.py')
result=unittest.TextTestRunner(verbosity=1).run(suite);assert result.wasSuccessful()
assert c.textkey('BODY\n text')==c.textkey('body text')
assert c.urlkey('https://EXAMPLE.gov/a.pdf#x')==c.urlkey('http://example.gov/a.pdf')
inv=json.loads((ROOT/'dedup-inventory.json').read_text());assert inv['blocked_original_hashes'] and inv['blocked_url_keys'] and inv['blocked_normalized_text_hashes']
for x in inv['historical_pdf_files']:assert sha(ROOT.parent.parent/x['path'])==x['sha256']
assert (ROOT/'search-access-ledger.jsonl').stat().st_size==0 and not (ROOT/'search-results').exists()
put('preparation-verification.json',{'schema_version':'round8.source-preparation-verification.v1','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'syntax_json':'PASS','native_cap_quota_stop_selftests':'PASS','state_spread_before_and_after_six':'PASS','Q01_complete_raw_header_regression':'PASS:18 displayed headers including first and empty title; collector rejects partial metadata before writes; no new search','search_lifecycle_offline_controls':{'passed':True,'tests':result.testsRun,'one_shot_intent':True,'recognized_empty_advances':True,'unknown_failed_response_retained_and_held':True,'primary_resolution_exact_hash_required':True,'rerun_allowed':False},'historical_pdf_inventory_rehashed':'PASS','native_text_and_URL_normalization':'PASS','release_gate_before_preparation_and_release':'PASS: query request refused; no network','body_coverage':'Retention requires true all-page visual/native body evidence and matching image hashes; no semantic coverage inferred from captions. Manual source-only review after release.','MIME':'application/pdf or application/octet-stream + PDF magic + strict pypdf parsing required; prepared only, not fresh endpoint tested.','fresh_queries':0,'fresh_downloads':0,'application_parser_model_provider_OCR_labels_calls':0,'prior_rounds_changed':False})
files=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p not in [ROOT/'preparation.READY.json',ROOT/'search-access-ledger.jsonl']]
put('preparation.READY.json',{'schema_version':'round8.source-preparation-ready.v1','status':'PREPARATION_READY_COLLECTION_HELD','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'static_files':files,'append_only_ledger':'search-access-ledger.jsonl','ledger_initial_sha256':sha(ROOT/'search-access-ledger.jsonl'),'queries':24,'states':24,'prior_notice_records':len(inv['notice_records']),'historical_pdf_files':len(inv['historical_pdf_files']),'blocked_pdf_hashes':len(inv['blocked_original_hashes']),'blocked_URL_keys':len(inv['blocked_url_keys']),'blocked_native_hashes':len(inv['blocked_native_hashes']),'blocked_normalized_text_hashes':len(inv['blocked_normalized_text_hashes']),'fresh_queries':0,'fresh_downloads':0,'release_receipt_missing':True,'collection_requires_primary_freeze_release':True})
try:c.request('Q01');raise AssertionError('release gate unexpectedly opened')
except FileNotFoundError as e:assert pathlib.Path(e.filename).name=='freeze-release.json'
for x in files:assert sha(ROOT/x['path'])==x['sha256']
print(json.dumps({'status':'PREPARATION_READY_COLLECTION_HELD','static_files':len(files),'preparation_sha256':sha(ROOT/'preparation.READY.json'),'selection_plan_sha256':sha(ROOT/'selection-plan.json'),'protocol_sha256':sha(ROOT/'collection-protocol.json'),'dedup_sha256':sha(ROOT/'dedup-inventory.json'),'fresh_queries':0,'fresh_downloads':0}))
