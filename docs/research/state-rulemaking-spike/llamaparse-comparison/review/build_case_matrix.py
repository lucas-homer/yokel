"""Serialize independent agent judgments, not an automated semantic evaluator.

Reads frozen source/baseline and reviewed agentic/agentic_plus responses, plus
the failed extraction response. Writes only reviewer-owned files.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=Path('/Users/home/.codex/worktrees/e8f4/yokel/docs/research/state-rulemaking-spike/pdf')
TRIAL=ROOT.parent/'trial'
def read(p):return p.read_text()
def data(p):return json.loads(read(p))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=data(ROOT/'pre-output-manifest.json')
assert sha(ROOT/'RUBRIC.md')==frozen['rubric_sha256']
assert sha(BASE/'raw/fresh.pdf')==frozen['source_pdf_sha256_verified']
agentic=data(TRIAL/'parse-response.json')['content'][0]['text']
plus=data(TRIAL/'parse-plus-response.json')['content'][0]['text']
assert agentic==(TRIAL/'parse.md').read_text().rstrip('\n')
fc=data(BASE/'raw/firecrawl-model.json')['structuredContent']['json']
texts={'native':read(BASE/'derived/native.txt'),'firecrawl_parse':read(BASE/'derived/firecrawl.md'),'llama_agentic_parse':agentic,'llama_agentic_plus_parse':plus}
paths={'native':BASE/'derived/native.txt','firecrawl_parse':BASE/'derived/firecrawl.md','llama_agentic_parse':TRIAL/'parse-response.json','firecrawl_extract':BASE/'raw/firecrawl-model.json','llama_agentic_plus_parse':TRIAL/'parse-plus-response.json','llama_agentic_extract':TRIAL/'extraction-response.json'}
def cite(stage,start,end=None):
    body=texts[stage];i=body.index(start);j=(body.index(end,i+len(start)) if end else i+len(start))
    return {'artifact':str(paths[stage]),'text_basis':'/content/0/text' if stage.startswith('llama_') else 'UTF-8 file',
            'start_character':i,'end_character':j,'quote':body[i:j],
            'locator_author':'independent reviewer, not vendor-generated field citation'}
def cell(category,reason,citation=None,fields=None,provenance=None):
    result={'category':category,'reason':reason,'raw_citations':citation or [],'field_values':{k:fc[k] for k in (fields or [])},
            'field_citation_quality':provenance or 'reviewer-located retained text; no vendor field citation claimed',
            'assessment_actor':'independent agent reviewer','downstream_repair_applied':False}
    return result
R='recovered_supported';P='text_only_or_partial';C='correct_but_ungrounded';A='safe_abstention';I='incorrect_or_fabricated';N='not_demonstrated'
cases=[]
def add(cid,focus,cells):
    for name in ['llama_agentic_plus_parse','llama_agentic_extract']:
        cells[name]={'category':N,'status':'pending_output_review','reason':'No result available when initial matrix was prepared; not scored as a failure.'}
    cases.append({'case_id':cid,'focus':focus,'results':cells})
add('M1','Hearing not-scheduled mark and unchecked scheduled alternative',{
 'native':cell(P,'Both labels survive, but the checked state of not scheduled does not.',[cite('native','ORAL PROCEEDING:','Ifan oralproceeding')]),
 'firecrawl_parse':cell(P,'Both mutually exclusive labels survive without marks.',[cite('firecrawl_parse','ORAL PROCEEDING:','If an oral proceeding')]),
 'firecrawl_extract':cell(C,'Correct status; evidence repeats the sentence without the decisive checkbox state.',fields=['hearing_status','evidence_quotes'],provenance='No field-level checkbox citation; source answer checked visually by reviewer.'),
 'llama_agentic_parse':cell(R,'Explicit [ ] scheduled and [x] not scheduled remain adjacent to the correct labels.',[cite('llama_agentic_parse','[ ] An oral proceeding','**If an oral proceeding')])})
add('M2','Proposed amendment selected, distinct from final adoption',{
 'native':cell(P,'Amendment label survives, but X is detached into days X.',[cite('native','Action proposed:','Printedname')]),
 'firecrawl_parse':cell(R,'X is associated with amendment; alternate proposed actions have blank underlines.',[cite('firecrawl_parse','Action proposed:','Proposed final effective date:')]),
 'firecrawl_extract':cell(C,'Correct amendment value with no supporting mark citation.',fields=['proposed_action','evidence_quotes']),
 'llama_agentic_parse':cell(P,'Selected amendment is explicitly recovered with [x], but unselected alternatives lack explicit blank/unchecked encoding. Full-case success includes both selected and unselected distinctions.',[cite('llama_agentic_parse','<strong>PROPOSED ACTION ON RULES</strong>','<strong>Proposed final effective date:</strong>')])})
add('M3','Economic-impact not-required selected and attached-summary unchecked',{
 'native':cell(P,'Caret and I I artifacts survive, but their checkbox semantics are not explicitly resolved.',[cite('native','ECONOMIC IMPACT STATEMENT:','FINAL ACTION ON RULES')]),
 'firecrawl_parse':cell(P,'Both alternatives are plain text with no selected/unselected association.',[cite('firecrawl_parse','## ECONOMIC IMPACT STATEMENT:','## TEMPORARY RULES')]),
 'firecrawl_extract':cell(N,'No economic-impact field or evidence; this field was not requested in that older prompt.'),
 'llama_agentic_parse':cell(R,'Explicit [x] not required and [ ] attached summary preserve both states.',[cite('llama_agentic_parse','[x] Economic impact statement not required for this rule. [ ] Concise summary of economic impact statement attached.')])})
add('B1','Blank final action choices and blank final-section Date Proposed Rule Filed',{
 'native':cell(P,'Final labels and blank date survive, but table order and option-state encoding are incomplete.',[cite('native','FINAL ACTION ON RULES','TEMPORARY RULES'),cite('native','Action taken:','days X')]),
 'firecrawl_parse':cell(A,'Final-action alternatives and date retain blank underlines; no option is marked.',[cite('firecrawl_parse','## FINAL ACTION ON RULES','Effective date:')]),
 'firecrawl_extract':cell(A,'Final action explicitly unknown and final-section date listed in unknowns. Strings are not typed JSON nulls.',fields=['final_action','unknowns']),
 'llama_agentic_parse':cell(P,'Final column and empty date are retained, but blank action underscores/unchecked states are not explicitly encoded. No false selected fact asserted.',[cite('llama_agentic_parse','<strong>FINAL ACTION ON RULES</strong>','<strong>Effective date:</strong>')])})
add('B2','Blank temporary/proposed-final/final effective options, including 30-day boilerplate',{
 'native':cell(P,'Boilerplate appears without reliable blank-option state; no computed effective date is emitted.',[cite('native','TEMPORARY RULES','Printedname')]),
 'firecrawl_parse':cell(A,'Blank underscores retained on effective options; no effective-date selection is asserted.',[cite('firecrawl_parse','## TEMPORARY RULES','Printed name and Title')]),
 'firecrawl_extract':cell(A,'Effective date explicitly unknown; no 30-day boilerplate promoted to a fact. Uses string unknowns.',fields=['effective_date','unknowns']),
 'llama_agentic_parse':cell(P,'Columns/option labels survive, but unmarked 30-day choices lack explicit blank/unchecked encoding. No absolute effective date asserted.',[cite('llama_agentic_parse','<strong>TEMPORARY RULES</strong>','**Printed name and Title')])})
add('D1','Handwritten submit date, separate role from filing stamp',{
 'native':cell(N,'SUBMIT DATE label remains but handwritten date is absent.',[cite('native','SUBMIT','Name or number of rule')]),
 'firecrawl_parse':cell(R,'12/27/2023 remains bound to SUBMIT DATE.',[cite('firecrawl_parse','SUBMITDATE12/27/2023')]),
 'firecrawl_extract':cell(N,'Separate submit date was not requested or returned; generic filing_date does not prove this role.'),
 'llama_agentic_parse':cell(R,'Table cell explicitly binds 12/27/2023 to SUBMIT DATE.',[cite('llama_agentic_parse','<strong>SUBMIT DATE</strong><br />12/27/2023')])})
add('D2','Official FILED stamp date, date precision only',{
 'native':cell(N,'Stamp date absent from native text.',[cite('native','DO NOT WRITE BELOW THIS LINE','The entiretext')]),
 'firecrawl_parse':cell(R,'DEC 27 2023 appears in the filing-stamp portion, distinct from top submit field.',[cite('firecrawl_parse','OFFICIAL FILING STAMP','The entire text')]),
 'firecrawl_extract':cell(C,'Date matches source, but no stamp-specific evidence. Same-valued submit date cannot establish provenance.',fields=['filing_date','evidence_quotes']),
 'llama_agentic_parse':cell(N,'Official stamp region retained as seal/acceptance text, but DEC 27 2023 and FILED are omitted. Top submit date is not a replacement.',[cite('llama_agentic_parse','<table><tr><th><strong>OFFICIAL FILING STAMP</strong>','The entire text')])})
add('T1','20-day hearing request and explicit filing anchor',{
 'native':cell(R,'Full hearing request clause retains twenty (20) days after filing, despite OCR spacing.',[cite('native','The written request','At any time')]),
 'firecrawl_parse':cell(R,'Full hearing request clause retains role, duration and anchor.',[cite('firecrawl_parse','The written request','At any time')]),
 'firecrawl_extract':cell(R,'20 and the filing clause are correct; the anchor field itself preserves exact source language. Dedicated vendor field citations are absent.',fields=['hearing_request_duration_days','hearing_request_anchor']),
 'llama_agentic_parse':cell(R,'Full clause preserves role, twenty (20), and filing anchor.',[cite('llama_agentic_parse','The written request','At any time')])})
add('T2','Conditional hearing-request requester eligibility',{
 'native':cell(R,'Conditional no-hearing context, political subdivision/agency/ten-person scope all survive.',[cite('native','Ifan oralproceeding','The written request')]),
 'firecrawl_parse':cell(R,'Complete conditional sentence survives.',[cite('firecrawl_parse','If an oral proceeding','The written request')]),
 'firecrawl_extract':cell(P,'Evidence mentions requester classes but omits leading condition when no hearing is scheduled; no separately structured eligibility field.',fields=['hearing_status','evidence_quotes']),
 'llama_agentic_parse':cell(R,'Complete conditional sentence survives unchanged.',[cite('llama_agentic_parse','If an oral proceeding is not scheduled','The written request')])})
add('T3','25-day public comments; no invented anchor/counting/absolute close',{
 'native':cell(R,'25-day comment clause survives distinctly; no starting event or computed close added.',[cite('native','At any time','ECONOMIC IMPACT')]),
 'firecrawl_parse':cell(R,'25-day clause survives; no anchor or absolute close added.',[cite('firecrawl_parse','At any time','## ECONOMIC IMPACT')]),
 'firecrawl_extract':cell(I,'25 and abstention on absolute close are correct, but public_comment_anchor wrongly holds the duration clause instead of a starting event. This is a role/type error, not a fabricated computed date.',fields=['public_comment_duration_days','public_comment_anchor','comment_close']),
 'llama_agentic_parse':cell(R,'25-day clause remains separate and no start event/absolute close is invented.',[cite('llama_agentic_parse','At any time','**ECONOMIC IMPACT')])})
add('X1','Rule 5.29 in named field and repeated citation',{
 'native':cell(P,'First field reads Rule 5,29; later occurrence is correct. Do not claim first-field recovery from the later occurrence.',[cite('native','Rule 5,29'),cite('native','proposed rule:Rule 5.29')]),
 'firecrawl_parse':cell(R,'Named field reads Rule 5.29.',[cite('firecrawl_parse','Name or number of rule(s):Rule 5.29')]),
 'firecrawl_extract':cell(C,'Correct rule reference; no field-specific quote in its evidence list.',fields=['rule_citations']),
 'llama_agentic_parse':cell(R,'Named rule table cell reads Rule 5.29.',[cite('llama_agentic_parse','<strong>Name or number of rule(s):</strong><br />Rule 5.29')])})
add('X2','EVEP acronym',{
 'native':cell(I,'Acronym transcribed as EVER.',[cite('native','The Exam ValidityExtensionProgram (EVER)')]),
 'firecrawl_parse':cell(R,'EVEP transcribed correctly.',[cite('firecrawl_parse','The Exam Validity Extension Program (EVEP)')]),
 'firecrawl_extract':cell(R,'EVEP appears in an exact supported evidence sentence, not a separate structured acronym field.',fields=['evidence_quotes']),
 'llama_agentic_parse':cell(R,'EVEP transcribed correctly.',[cite('llama_agentic_parse','The Exam Validity Extension Program (EVEP)')])})
ps='llama_agentic_plus_parse'
plus_cells={
 'M1':cell(R,'Explicit checked/unchecked status is bound to the two hearing alternatives.',[cite(ps,'[unchecked] An oral proceeding','If an oral proceeding')]),
 'M2':cell(R,'Amendment checked; new, repeal and adoption-by-reference explicitly unchecked in proposed-action column.',[cite(ps,'| TEMPORARY RULES','**Printed name and Title')]),
 'M3':cell(R,'Not-required checked and attached-summary unchecked are explicit.',[cite(ps,'[checked] Economic impact statement','| TEMPORARY RULES')]),
 'B1':cell(A,'Final action alternatives explicitly unchecked, and final-section Date Proposed Rule Filed retains a blank placeholder.',[cite(ps,'| TEMPORARY RULES','**Printed name and Title')]),
 'B2':cell(A,'Temporary and effective choices explicitly unchecked; 30-day options remain boilerplate rather than facts.',[cite(ps,'| TEMPORARY RULES','**Printed name and Title')]),
 'D1':cell(R,'Submit field preserves handwritten date as 12/27/2023.',[cite(ps,'**SUBMIT DATE:** 12/27/2023')]),
 'D2':cell(N,'Official filing stamp heading and a signature-like string survive, but the FILED date is absent. Submit date does not establish this role.',[cite(ps,'**OFFICIAL FILING STAMP**','The entire text')]),
 'T1':cell(R,'20-day hearing-request duration and explicit filing anchor survive.',[cite(ps,'The written request','At any time')]),
 'T2':cell(R,'Full no-hearing conditional and requester eligibility survive.',[cite(ps,'If an oral proceeding','The written request')]),
 'T3':cell(R,'25-day comment clause survives separately with no invented anchor/absolute close.',[cite(ps,'At any time','**ECONOMIC IMPACT')]),
 'X1':cell(R,'Named rule field is Rule 5.29.',[cite(ps,'**Name or number of rule(s):** Rule 5.29')]),
 'X2':cell(R,'EVEP transcribed correctly.',[cite(ps,'The Exam Validity Extension Program (EVEP)')]),
}
timeout=data(TRIAL/'extraction-response.json')
assert timeout['isError'] is True and 'timed out' in timeout['content'][0]['text']
for row in cases:
 row['results'][ps]=plus_cells[row['case_id']]
 row['results']['llama_agentic_extract']={'category':N,'status':'tool_timeout_no_output','reason':'MCP timeout; no structured extraction result retained. Backend completion and billing unknown. Not an accuracy error or safe abstention.','raw_response_artifact':str(TRIAL/'extraction-response.json'),'downstream_repair_applied':False}
request=data(TRIAL/'parse-request.json');plus_request=data(TRIAL/'parse-plus-request.json');extract_request=data(TRIAL/'extraction-request.json')
assert request['request']['fileId']==plus_request['request']['fileId']==extract_request['request']['fileId']==data(TRIAL/'upload-response.json')['file_id']
result={'phase':'raw-output and downstream normalizer review complete','rubric_sha256':sha(ROOT/'RUBRIC.md'),'source_pdf_sha256':sha(BASE/'raw/fresh.pdf'),
 'judgment_method':'Independent agent review against original saved image and frozen cases; not automated semantic scoring or human gold labels.',
 'stage_order':['native','firecrawl_parse','firecrawl_extract','llama_agentic_parse','llama_agentic_plus_parse','llama_agentic_extract'],
 'stage_artifacts':{k:{'path':str(p),'sha256':sha(p)} for k,p in paths.items()},
 'stage_kinds':{'native':'local native text extraction','firecrawl_parse':'vendor_parse','firecrawl_extract':'vendor_extract prompt-only','llama_agentic_parse':'vendor_parse','llama_agentic_plus_parse':'vendor_parse','llama_agentic_extract':'vendor_extract schema-configured; timed out without result'},
 'agentic_execution':{'file_id':request['request']['fileId'],'requested_tier':request['request']['tier'],'requested_version':'latest','resolved_vendor_version':None,'wrapper_elapsed_ms':request['elapsed_ms'],'timing_scope':'saved parse tool-call wrapper; excludes upload; one sample','credits_consumed':None,'credit_basis':'parse response supplies no billed-credit field; capability text is not a billing receipt'},
 'agentic_plus_execution':{'requested_tier':'agentic_plus','requested_version':'latest','resolved_vendor_version':None,'wrapper_elapsed_ms':plus_request['elapsed_ms'],'credits_consumed':None,'timing_scope':'saved parse tool-call wrapper; one sample'},
 'extraction_execution':{'configured_tier':'agentic','outcome':'MCP timeout; no extraction output','wrapper_elapsed_ms':extract_request['elapsed_ms'],'backend_completion':'unknown','billing':'unknown','retried':False},
 'normalizer_audit':'normalizer-audit.json; 7 needs_review observations, 9 exact quotes, no filing date/visual repair, repeatable offline replay; synthetic conflict/column-scope limits disclosed in REVIEW.md',
 'cases':cases,'verdict':'Partial semantic/evidence benefit: both Llama parses improve hearing/economic-impact mark associations; plus explicitly retains unchecked alternatives. Both omit official filing stamp date. Structured extraction not demonstrated due to timeout.',
 'comparison_limits':['Unequal prompt/schema coverage across extraction trials must be reported.','No total accuracy score; easy lexical recovery cannot offset critical missing fields.','Extraction timeout is not an accuracy result.','Raw parse locators were created by reviewer; not native vendor field-citation metadata.','No bbox/form/enrichment option appears in recorded parse tool schema, and no native field coordinates/job IDs/consumed credits/resolved version appear in these responses; this is a connector/trial observation, not a platform-wide feature claim.','Local source hash and same upload file ID are verified; remote checksum was not returned.']}
(ROOT/'case-matrix.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'case_count':len(cases),'reviewed_stages':list(paths),'review_complete':True,'verdict':result['verdict']},indent=2))
