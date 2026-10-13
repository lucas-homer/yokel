#!/usr/bin/env python3
"""Local preparation only: no searches, retrievals, runtime, models or labels."""
import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BENCH=ROOT.parent.parent
R5=BENCH/'round5/sources'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,x):(ROOT/name).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
assert not (ROOT/'preparation.READY.json').exists()
old=json.loads((R5/'search-plan.json').read_text())['queries']
# Fixed precollection rotation: six general, six conditional, six general, six negative.
order=[3,4,5,6,10,12,13,14,15,16,17,18,1,2,7,8,9,11,19,20,21,22,23,24]
queries=[]
for i,k in enumerate(order,1):
 q=old[k-1]
 # Literal year term improves recency; it is not an eligibility requirement or adaptive search.
 query=q['query'].replace(' PDF filetype:pdf',' 2026 PDF filetype:pdf')
 queries.append({'query_id':f'Q{i:02d}','state':q['state'],'planned_stratum':q['stratum'],'official_domain':q['official_source_domain'],'query':query})
put('selection-plan.json',{'schema_version':'round6.selection-plan.v1','status':'STATIC_PRECOLLECTION','queries':queries,'max_queries':24,'official_pdf_candidates_per_query':3,'query_mutation_allowed':False,'query_year_term':'2026 is fixed search text only; source publication year is not an acceptance criterion.','candidate_order':'First three distinct direct official PDF result URLs in displayed order, not tool reference IDs. Preserve all returned metadata and raw tool result. HTML links are not expanded.','stop':'Stop immediately upon eight eligible notices with 6 general/2 controls, >=6 states, <=2/state, <=40 pages. Otherwise stop after Q24 first-three candidate set. No substitution searches or queue after hard cap.'})
previous=json.loads((R5/'dedup-inventory.json').read_text())
records=previous['records'][:]
for p in sorted((R5/'documents').glob('*/provenance.json')):
 x=json.loads(p.read_text())
 records.append({'prior_round':'round5','source_metadata_path':str(p.relative_to(BENCH)),'source_metadata_sha256':sha(p),'state':x['state'],'source_url':x['retrieval_url'],'original_sha256':x['original_sha256'],'notice_identity':x.get('notice_identity',x['boundary_evidence']),'identity_evidence':x['boundary_evidence'],'retained_in_round5':p.parent.name!='doc-cdc84f3180fe'})
# All historical PDF bytes, including rejected candidate originals, copied inputs, and development PDFs,
# are conservatively blocked. No label/evaluator/reference files are inspected.
pdfs=[]
for p in sorted(BENCH.rglob('*.pdf')):
 if 'round6' in p.relative_to(BENCH).parts:continue
 pdfs.append({'path':str(p.relative_to(BENCH)),'sha256':sha(p),'bytes':p.stat().st_size})
known=sorted({x['original_sha256'] for x in previous['records'] if x.get('original_sha256')}|{x['sha256'] for x in pdfs})
put('dedup-inventory.json',{'schema_version':'round6.prior-source-inventory.v1','notice_records':records,'prior_notice_record_count':len(records),'blocked_original_hashes':known,'blocked_pdf_hash_count':len(known),'historical_pdf_files':pdfs,'prior_inventory_path':'round5/sources/dedup-inventory.json','prior_inventory_sha256':sha(R5/'dedup-inventory.json'),'policy':'Reject original hash or underlying notice already seen in earlier rounds, including preserved excluded originals. Compare issuer/title/rule/docket/source/date/page identity. Changed/rehosted PDFs of same notice remain duplicates. Unknown identity => source-review exclusion; no assumption of novelty. Distinct notice template recurrence allowed but disclosed.'})
put('collection-protocol.json',{
 'schema_version':'round6.collection-protocol.v1','status':'PREPARED_COLLECTION_ON_HOLD',
 'release_gate':{'required':'Explicit primary code/protocol-freeze release before any fresh query, candidate inspection or acquisition. Primary release receipt must bind preparation.READY SHA256, verbatim release message/locator, implementation and policy freeze hashes, and timestamp/timezone.','receipt_path':'freeze-release.json','receipt_created':False},
 'target':{'notices':8,'minimum_states':6,'max_per_state':2,'max_total_pages':40,'general_comment':6,'controls':2},
 'source_strata':{'general_comment':'Complete proposed rulemaking notice inviting public comment, without explicit conditional/relative participation terms or negative lifecycle.','conditional_control':'Source expressly conditions/extends comment or hearing participation, or supplies event-relative participation timing. Routine generic possible rule modification after comments, accessibility-request timing, or statutes quoted incidentally do not alone establish a control.','negative_lifecycle_control':'Source notice expressly records cancellation, withdrawal, termination, or comparable negative rulemaking lifecycle.','precedence':'Actual source stratum overrides planned query stratum. First qualifying control of either type fills available control slot; no minimum of each subtype. Strata are source sampling categories, not reference answers.'},
 'selection':'Sequential bounded displayed-result order. Do not select for substantive deadline/email/channel/clock/timezone field presence, exact values, ease of parsing, outputs or verifier behavior. Missing fields remain eligible; only predeclared control stratum may depend on participation/lifecycle terms.',
 'scope':'Accept only complete unchanged official publisher individual notice PDFs or a single complete publisher regulation filing that includes its notice and required integrated filing sections. A coherent individual proposed rule order is eligible including judicial rulemaking. Publisher labeling alone does not establish completeness: record mechanical opening/continuation/end boundaries for one proceeding. Reject multi-notice register issues, mixed packets, unrelated attachments, scans without native text, slice/unknown scopes. Several coordinated rules within one single notice are allowed. Never invent notice boundaries or remove pages.',
 'native_caps':{'max_codepoints':30000,'max_pdf_bytes':25000000,'render_dpi':150,'utf8':'strict nonempty UTF-8; no replacement characters or material native-text damage; FF count must equal all PDF pages','extractor':'pdftotext -layout -enc UTF-8; exact bytes; no OCR, repair, reflow, truncation or excerpt','validation_order':'Check all native/PDF/page budgets and dedup before any retention. Native acquisition is not provisional selection. Serialized case-size eligibility remains for primary runtime freeze; no runtime case generation in collector.'},
 'quota_rule':'Before acceptance require current stratum capacity, total <8, per-state <2, aggregate pages<=40, and new distinct-state count + remaining slots >=6. Reject candidate if any condition fails. Do not reserve or skip a feasible earlier source for an imagined future distribution. After success stop immediately even within a query; log unprocessed bounded candidates as skipped_success_stop.',
 'discovery':'Exactly 24 predeclared query strings; sequential; at most first 3 distinct direct official PDF candidates each, fixed from that one full response. Preserve raw result and all ordered title/URL/reference metadata before candidate resolution. Candidate URL must be direct PDF/document route under official query domain; dynamic PDF routes qualify when verified application/pdf and PDF magic. No HTML-link expansion, follow-on discovery, rank reconstruction, or altered/repeated queries.',
 'access':'At most one ordinary retry per candidate, including prior failed inspection/access attempts. Preserve every attempt headers/status/final URL/content-type/errors. No bypass. No tools/providers/credentials for parsing/verification/labels.',
 'stopping':'Success at exact eight, six general plus two controls, >=six states, <=two/state and <=40 pages. Otherwise after Q24 bounded candidates stop and disclose shortfall. No replacements after source freeze.',
 'artifacts':'Preserve all exclusions and acquired originals/diagnostics/native bytes. Retained input PDF byte-identical to original. Render every retained page at150DPI. Hash all artifacts and each PNG; preserve versions, acquisition timestamps UTC, official URL, HTTP, identity/boundary/dedup evidence and source anomalies. Keep selection audit outside runtime and blind inventory.',
 'runtime_manifest':{'schema_version':'round4.sources.v1','exact_keys':['document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'],'document_id':'doc- plus first12 original SHA256','channel':'native','scope':'full_notice','paths':'relative to sources root','labels':'none'},
 'blinded_image_inventory':{'schema_version':'round6.blinded-images.v1','document_keys':['document_id','pdf_pages','pages'],'page_keys':['page','image_path','image_sha256'],'excludes':'native text, URLs, titles, source categories, candidate decisions, expected fields, evidence hints, decisive spans, labels and runtime outputs. All pages only; IDs match opaque runtime IDs.'},
 'audit_limits':['Native-only, individual-publisher-PDF and frozen-search-ranking coverage biases disclosed.','No representative-sample claim.','Natural controls only; no synthetic controls or provider-assisted collection.'],
 'prior_rounds':'Immutable; dedup includes all known originals and excluded bytes; no labels consulted.'})
( ROOT/'search-access-ledger.jsonl').write_text('')
put('native-toolchain.json',json.loads((BENCH/'round5/execution/native-acquisition-config.json').read_text()))
put('runtime-manifest.template.json',{'schema_version':'round4.sources.v1','documents':[]})
put('blinded-image-inventory.template.json',{'schema_version':'round6.blinded-images.v1','documents':[]})
print(json.dumps({'queries':len(queries),'states':len({q['state'] for q in queries}),'prior_notice_records':len(records),'blocked_pdf_hashes':len(known),'historical_pdf_files':len(pdfs),'fresh_searches':0,'fresh_downloads':0}))
