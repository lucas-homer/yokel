#!/usr/bin/env python3
"""Local prior-source inventory and static plan only. No new source access."""
import ast,datetime,hashlib,json,re,subprocess,unicodedata
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
ROOT=Path(__file__).resolve().parent; BENCH=ROOT.parent.parent; R6=BENCH/'round6/sources'
POP=Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):(ROOT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def normalized_text(t):return ' '.join(unicodedata.normalize('NFKC',t).casefold().split())
def urlkey(u):
 p=urlsplit(u);return urlunsplit(('',p.netloc.lower(),p.path,p.query,''))
assert not (ROOT/'preparation.READY.json').exists()
rows=[
 ('Minnesota','mn.gov','general_comment'),('Wisconsin','wisconsin.gov','general_comment'),
 ('Illinois','illinois.gov','general_comment'),('Oregon','oregon.gov','general_comment'),
 ('Massachusetts','mass.gov','general_comment'),('Maine','maine.gov','general_comment'),
 ('Kentucky','apps.legislature.ky.gov','conditional_control'),('Tennessee','tn.gov','conditional_control'),
 ('Alaska','alaska.gov','conditional_control'),('Montana','mt.gov','conditional_control'),
 ('New Hampshire','gc.nh.gov','conditional_control'),('Utah','utah.gov','conditional_control'),
 ('Colorado','sos.state.co.us','general_comment'),('Ohio','registerofohio.state.oh.us','general_comment'),
 ('Georgia','georgia.gov','general_comment'),('New Mexico','nm.gov','general_comment'),
 ('Connecticut','ct.gov','general_comment'),('Indiana','in.gov','general_comment'),
 ('Pennsylvania','pa.gov','general_comment'),('North Carolina','nc.gov','general_comment'),
 ('South Dakota','sd.gov','general_comment'),('Washington','wa.gov','general_comment'),
 ('Nevada','nv.gov','general_comment'),('North Dakota','nd.gov','general_comment')]
queries=[]
for i,(state,domain,stratum) in enumerate(rows,1):
 terms='notice proposed rule public comment public hearing' if stratum=='general_comment' else 'notice proposed rule public hearing "if" "requested"'
 queries.append({'query_id':f'Q{i:02d}','state':state,'official_domain':domain,'planned_stratum':stratum,'query':f'site:{domain} {state} {terms} 2026 filetype:pdf'})
put('selection-plan.json',{'schema_version':'round8.selection-plan.v1','status':'STATIC_PRECOLLECTION','queries':queries,'max_queries':24,'official_pdf_candidates_per_query':3,'query_mutation_allowed':False,'candidate_order':'First three distinct direct official PDF/document URLs in displayed result order; citation IDs are not ranks. Full raw response and all metadata preserved and independently reconciled before registration. No HTML-link expansion, rerun, alternate query, or replacement search. A known prior URL still consumes its bounded slot and is excluded without reacquisition.','search_year':'2026 is a literal search term, not a publication-date eligibility requirement. Fresh means unseen in rounds 1–7, including development and excluded candidates.','state_spread':'At most one retained notice per state until six distinct states have been retained, then at most two. This frozen chronological rule applies before search; no performance-based substitution.','stop':'Stop immediately at eight retained notices, exactly six general and two conditional/hearing controls, at least six states and <=40 pages. Otherwise resolve Q24 bounded candidates and stop with honest shortfall.','planning_basis':'Prior platform experience only: broader official agency domains rather than whole-register-only endpoints; no fresh source content, platform query or download used to form this rotation. Domain availability and search yields remain unverified.'})
# Hash every historical PDF regardless of folder, including development, exclusions,
# copied inputs and rejected HTTP response bodies named .pdf. Do not read labels.
pdfs=[]; texts=[]; seen_hash=set()
for p in sorted(BENCH.rglob('*')):
 if not p.is_file() or 'round8' in p.relative_to(BENCH).parts:continue
 if p.suffix.lower()!='.pdf':continue
 h=sha(p);pdfs.append({'path':str(p.relative_to(BENCH)),'sha256':h,'bytes':p.stat().st_size,'pdf_magic':p.read_bytes()[:5]==b'%PDF-'})
 if h in seen_hash:continue
 seen_hash.add(h)
 if p.read_bytes()[:5]!=b'%PDF-':continue
 proc=subprocess.run([str(POP/'pdftotext'),'-layout','-enc','UTF-8',str(p),'-'],capture_output=True,timeout=60)
 rec={'pdf_path':str(p.relative_to(BENCH)),'pdf_sha256':h,'extraction_returncode':proc.returncode}
 try:
  t=proc.stdout.decode('utf-8');rec.update(native_sha256=hashlib.sha256(proc.stdout).hexdigest(),native_codepoints=len(t),normalized_text_sha256=hashlib.sha256(normalized_text(t).encode()).hexdigest(),nonempty=bool(t.strip()))
 except UnicodeError:rec['strict_utf8']=False
 texts.append(rec)
# Existing native source bytes catch historical extraction differences. No expected
# records, labels, provider responses, evaluation outputs or authored fixtures read.
for p in sorted(BENCH.rglob('native.txt')):
 if 'round8' in p.relative_to(BENCH).parts:continue
 raw=p.read_bytes();rec={'native_path':str(p.relative_to(BENCH)),'native_sha256':sha(p)}
 try:
  t=raw.decode('utf-8');rec.update(native_codepoints=len(t),normalized_text_sha256=hashlib.sha256(normalized_text(t).encode()).hexdigest(),nonempty=bool(t.strip()))
 except UnicodeError:rec['strict_utf8']=False
 texts.append(rec)
previous=json.loads((R6/'dedup-inventory.json').read_text()); identities=previous['notice_records'][:]
for p in sorted((R6/'documents').glob('*/provenance.json')):
 x=json.loads(p.read_text());identities.append({'prior_round':'round6','source_metadata_path':str(p.relative_to(BENCH)),'source_metadata_sha256':sha(p),'state':x['state'],'source_url':x['url'],'original_sha256':x['original_sha256'],'notice_identity':x['notice_identity'],'identity_evidence':x['boundary_evidence']})
# All URLs displayed in prior source searches are conservatively seen. Parsing
# source metadata only, and retaining paths/hashes makes inventory reviewable.
metadata=[]; urls=set(); url_entries=[]
allowed=[BENCH/'artifacts/source-a',BENCH/'round2/heldout',BENCH/'round4/sources',BENCH/'round5/sources',R6]
files=set()
for folder in allowed:
 if folder.exists():
  for p in folder.rglob('*'):
   if p.is_file() and p.suffix in ['.json','.jsonl'] and ('round2' not in p.parts or p.name in ['source-inventory.json','candidate-selection-ledger.json']):files.add(p)
for p in [BENCH/'round3/protocol/sources.json']:
 if p.exists():files.add(p)
for p in sorted(files):
 raw=p.read_text(); metadata.append({'path':str(p.relative_to(BENCH)),'sha256':sha(p)})
 found=set(re.findall(r'https?://[^\s<>"\\)]+',raw))
 for u in sorted(found):
  k=urlkey(u);urls.add(k);url_entries.append({'url':u,'normalized_url':k,'metadata_path':str(p.relative_to(BENCH))})
put('dedup-inventory.json',{'schema_version':'round8.prior-source-inventory.v1','notice_records':identities,'historical_pdf_files':pdfs,'blocked_original_hashes':sorted(set(previous['blocked_original_hashes'])|{x['sha256'] for x in pdfs}),'historical_native_fingerprints':texts,'blocked_native_hashes':sorted({x['native_sha256'] for x in texts if x.get('nonempty') and x.get('extraction_returncode',0)==0}),'blocked_normalized_text_hashes':sorted({x['normalized_text_sha256'] for x in texts if x.get('nonempty') and x.get('extraction_returncode',0)==0}),'blocked_url_keys':sorted(urls),'url_records':url_entries,'source_metadata_inputs':metadata,'prior_inventory_path':'round6/sources/dedup-inventory.json','prior_inventory_sha256':sha(R6/'dedup-inventory.json'),'policy':'Exclude any previously seen PDF hash, source URL, exact native bytes, NFKC+casefold+whitespace-normalized text, or underlying notice identity, including development, exclusions and candidates. URL scheme/fragment ignored; host lowercased, path/query preserved. Rehosted/modified bytes of the same issuer/rule/docket/proceeding/issuance identity remain duplicates. Unknown identity or coverage => exclude with uncertainty. Publication recency alone does not establish novelty. All PDF files through round7 inventoried; round7 reuses round6 sources and has no new source PDF tree. No semantic labels or runtime outputs read.'})
protocol=json.loads((R6/'collection-protocol.json').read_text());protocol['schema_version']='round8.collection-protocol.v1'
protocol['source_strata']={'general_comment':'Complete proposed rulemaking notice inviting comments, without qualifying conditional/event-relative participation or hearing timing. Fixed dates and absent fields both allowed.','conditional_control':'Natural source condition on comment submission timing or hearing availability/request threshold, conditional cancellation of a proposed-rule hearing, or event-relative participation timing. A generic submission-format practicability qualifier, accessibility request, possible later rule modification or incidental quoted statute alone does not qualify. Fixed written-comment dates may coexist with a conditional hearing. No negative lifecycle-only controls in this round.','precedence':'Actual source category governs quota, regardless of query planned stratum. These are sampling categories, not reference answers.'}
protocol['target']['controls']=2
protocol['quota_rule']='At most one retained notice per state until six distinct states are retained, then at most two. Before acceptance require current 6-general/2-control capacity, total<8, aggregate pages<=40 and six-state feasibility. First qualifying chronological candidate wins. No imagined future-source reservation or output-based replacement.'
protocol['discovery']=json.loads((ROOT/'selection-plan.json').read_text())['candidate_order']
protocol['mime_policy']='Accept application/pdf or application/octet-stream only when bytes begin %PDF- and strict pypdf parsing succeeds with >=1 page; both are eligible MIME types, not proof of full notice. HTML, redirects outside official query domain, corrupt PDFs, other MIME types and access failures are excluded honestly. Preserve originals/headers/errors without access bypass.'
protocol['body_coverage']='Nonempty captions/headers do not establish body coverage. Before retention record per-page substantive body presence in exact native text, compare native text with a full source-only visual check of every original page at150DPI, and affirm all substantive body/table/footnote/continuation/end matter is represented. Images/scans with missing substantive native body fail even if captions exist. No OCR, repair, truncation or reconstruction. Blank/decorative pages may be recorded explicitly. If material coverage is uncertain, exclude.'
protocol['dedup']='Use frozen historical hash, URL, exact native and normalized-text inventories; manual underlying notice identity comparison against prior source identities required even when mechanical tests pass. A register containing a previously seen individual notice may not supply that notice under new bytes. New publication date alone is insufficient. Unknown novelty => exclude.'
protocol['runtime_manifest']['schema_version']='round8.sources.v1';protocol['blinded_image_inventory']['schema_version']='round8.blinded-images.v1'
protocol['access']='Public web search and ordinary HTTP only; no paid Firecrawl/API source access. Maximum two60-second ordinary attempts per bounded candidate; retain both attempts including partial bytes, HTTP headers/errors/timestamps. No retry after success, bypass, alternate URLs or hidden retrieval. Prior URL/hash exclusions consume slots. No application/benchmark parser, model/provider API, OCR or labels calls, and no credentials. Mechanical local native PDF tools (strict pypdf parsing, Poppler diagnostics/extraction/rendering) are allowed.'
protocol['control_definition_change_from_round6']='Stricter source sampling rule: the Round6 New Hampshire alternative electronic submission-format practicability qualifier alone is not sufficient. Only actual conditional/event-relative participation timing or hearing availability qualifies. This precollection change is independent of model performance and does not revise any prior-round artifact.'
put('collection-protocol.json',protocol)
put('native-toolchain.json',json.loads((R6/'native-toolchain.json').read_text()))
put('runtime-manifest.template.json',{'schema_version':'round8.sources.v1','documents':[]});put('blinded-image-inventory.template.json',{'schema_version':'round8.blinded-images.v1','documents':[]})
note=json.loads((R6/'source-notes.template.json').read_text());note['body_coverage_verified']=False;note['body_coverage_evidence']=[];note['source_stratum']='general_comment';note['stratum_basis']=protocol['source_strata']['conditional_control'];put('source-notes.template.json',note)
(ROOT/'search-access-ledger.jsonl').write_text('')
print(json.dumps({'queries':len(queries),'states':len(set(x['state'] for x in queries)),'historical_pdf_files':len(pdfs),'blocked_pdf_hashes':len(set(previous['blocked_original_hashes'])|{x['sha256'] for x in pdfs}),'prior_notice_records':len(identities),'blocked_url_keys':len(urls),'native_fingerprint_records':len(texts),'fresh_queries':0,'fresh_downloads':0}))
