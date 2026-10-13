"""Frozen output-cap diagnosis. Complete assessment-prefix objects are forensic data, never a verdict."""
import copy,hashlib,importlib.util,json,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('offline: network/process disabled')
sys.addaudithook(guard)
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def verify_freeze():
    path=ROOT/'execution/freeze-E.json';assert sha(path.read_bytes())=='db895208c9f7573517be057a58ec6126e793024caf6a532fe2e2a72dd391c53c';f=json.loads(path.read_bytes())
    for row in f['files']:
        p=(ROOT/row['path']).resolve();assert p.is_relative_to(ROOT.resolve()) and sha(p.read_bytes())==row['sha256'] and p.stat().st_size==row['bytes']
    return {'sha256':sha(path.read_bytes()),'entries':len(f['files'])}
freeze=verify_freeze();spec=importlib.util.spec_from_file_location('frozen_evidence_table_diagnosis',ROOT/'runtime/run_pipeline.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);r.verify_implementation(ROOT/'runtime/implementation.json')
d=r.load_sources(ROOT/'sources/source-inputs.READY.json',ROOT/'sources')[0];op=ROOT/'execution/run/operations/stronger-089be69dd81d8b0468fa2052';native=json.loads((op/'response.body').read_bytes());text=native['choices'][0]['message']['content'];usage=native['usage'];status=json.loads((op/'status.json').read_bytes());request=json.loads((op/'request.json').read_bytes());assert status['http_status']==200 and native['choices'][0]['finish_reason']=='length' and request['max_tokens']==4096 and usage['completion_tokens']==4096 and not (op/'result.json').exists()
try:r.a.parse_or((op/'response.body').read_bytes())
except r.a.Stop as error:parser_error=str(error)
else:raise AssertionError('incomplete response accepted')
try:json.loads(text)
except json.JSONDecodeError as error:json_error={'message':error.msg,'pos':error.pos,'line':error.lineno,'column':error.colno}
else:raise AssertionError('partial content unexpectedly valid JSON')
# Forensic prefix only: independently parse complete objects from the first assessments array; never close/repair it.
assert text.lstrip().startswith('{') and '"assessments"' in text[:100]
pos=text.index('[')+1;decoder=json.JSONDecoder();prefix=[];spans=[]
while True:
    while pos<len(text) and text[pos] in ' \t\r\n,':pos+=1
    try:value,end=decoder.raw_decode(text,pos)
    except json.JSONDecodeError:break
    assert isinstance(value,dict) and set(value)=={'item_id','support','association','requirements','reason','evidence'};prefix.append(value);spans.append((pos,end));pos=end
ids=[item['id'] for _,item in r.p.all_items(d['assembled']['record'])];prefix_ids=[x['item_id'] for x in prefix];assert len(ids)==len(set(ids))==70 and len(prefix_ids)==len(set(prefix_ids))==53 and set(prefix_ids)<=set(ids)
prefix_schema_errors=r.p.schema_errors(prefix,r.p.VERDICT_SCHEMA['properties']['assessments']);prefix_evidence_errors=[];r.p.resolve_all({'assessments':prefix},d['source']['source_text'],prefix_evidence_errors);assert not prefix_schema_errors and not prefix_evidence_errors
# A possible diagnostic response wire codec: positional assessments and a shared exact evidence-selector table.
# It preserves full reasons/labels and allows new omission evidence; it is not an implemented provider schema.
FIELDS=('item_id','support','association','requirements','reason','evidence')
def compact(value):
    out=copy.deepcopy(value);table=[];index={}
    def visit(node):
        if isinstance(node,dict):
            for key,item in list(node.items()):
                if key=='evidence':
                    refs=[]
                    for ev in item:
                        keybytes=enc(ev)
                        if keybytes not in index:index[keybytes]=len(table);table.append(copy.deepcopy(ev))
                        refs.append(index[keybytes])
                    node[key]=refs
                else:visit(item)
        elif isinstance(node,list):
            for item in node:visit(item)
    visit(out);rows=[]
    for assessment in out.pop('assessments'):
        assert set(assessment)==set(FIELDS);rows.append([assessment[key] for key in FIELDS])
    return {'wire_version':'diagnostic.verdict-evidence-table.v1','metadata':out,'assessment_columns':list(FIELDS),'assessments':rows,'evidence_table':table}
def restore(wire):
    assert wire['wire_version']=='diagnostic.verdict-evidence-table.v1' and wire['assessment_columns']==list(FIELDS)
    out=copy.deepcopy(wire['metadata']);out['assessments']=[]
    for row in wire['assessments']:
        if not isinstance(row,list) or len(row)!=len(FIELDS):raise ValueError('assessment tuple shape')
        out['assessments'].append(dict(zip(FIELDS,copy.deepcopy(row))))
    def visit(node):
        if isinstance(node,dict):
            for key,item in list(node.items()):
                if key=='evidence':
                    rows=[]
                    for ref in item:
                        if type(ref) is not int or not 0<=ref<len(wire['evidence_table']):raise ValueError('reference bounds/type')
                        rows.append(copy.deepcopy(wire['evidence_table'][ref]))
                    node[key]=rows
                else:visit(item)
        elif isinstance(node,list):
            for item in node:visit(item)
    visit(out);return out
forensic={'assessments':prefix};wire=compact(forensic);assert enc(restore(wire))==enc(forensic)
# Independent authored all-ID sizing fixture, never filled-in/repaired paid output. All judgments explicitly uncertain.
quote='Notice of Hearing';assert d['source']['source_text'].count(quote)==1
ev=[{'quote':quote,'occurrence':None,'context':None}]
def authored(reason):return dict(schema_version='round7.record_verdict.v1',document_id=d['source']['document_id'],payload_sha256=d['common']['payload_sha256'],completeness={'label':'uncertain','reason':reason,'evidence':ev},source_identity={'label':'uncertain','reason':reason,'evidence':ev},assessments=[{'item_id':item,'support':'uncertain','association':'uncertain','requirements':'uncertain','reason':reason,'evidence':ev} for item in ids],missing_items=[],contradictions=[])
fixtures={}
for name,reason in [('schema-short-reason','x'),('authored-explicit-uncertain','Authored offline sizing row only; no semantic finding.')]:
    fixture=authored(reason);validated=r.p.validate_verdict(d['source'],d['assembled'],fixture);assert validated['valid'];cw=compact(fixture);assert enc(restore(cw))==enc(fixture)
    fixtures[name]={'authored_development_only':True,'observed':False,'semantic_acceptance':False,'schema_structurally_valid':True,'complete_ID_count':len(ids),'full_json_bytes':len(enc(fixture)),'compact_wire_bytes':len(enc(cw)),'savings_bytes':len(enc(fixture))-len(enc(cw)),'roundtrip_exact':True}
controls=[]
for badkind in ('duplicate_ID','missing_ID','invalid_reference','missing_tuple_field'):
    bad=compact(authored('Authored uncertain control.'))
    if badkind=='duplicate_ID':bad['assessments'][1][0]=bad['assessments'][0][0]
    elif badkind=='missing_ID':bad['assessments'].pop()
    elif badkind=='invalid_reference':bad['assessments'][0][-1]=[len(bad['evidence_table'])]
    else:bad['assessments'][0].pop()
    try:expanded=restore(bad)
    except ValueError:assert badkind in ('invalid_reference','missing_tuple_field')
    else:assert not r.p.validate_verdict(d['source'],d['assembled'],expanded)['valid']
    controls.append({'name':badkind,'passed':True})
# Prefix field attribution is nested; totals are reported separately to avoid pretending evidence+quotes are additive.
array_bytes=len(enc(prefix));evidence_bytes=sum(len(enc(x['evidence'])) for x in prefix);reason_bytes=sum(len(enc(x['reason'])) for x in prefix);quotes=[e for item in prefix for e in item['evidence']];unique_evidence={enc(e) for e in quotes};unique_reasons={x['reason'] for x in prefix};visible_tokens=usage['completion_tokens']-usage['completion_tokens_details']['reasoning_tokens']
cap_candidates={str(cap):{'new_nominal_max_usd':40000*.000002+cap*.000010,'aggregate_nominal_max_usd':.542976718+40000*.000002+cap*.000010,'exact_current_input_reservation_usd':r.a.estimate_input(request)*.000002+cap*.000010,'inventory_calls':0,'jev_calls':0,'stronger_calls':1,'authorized':False} for cap in (4096,6144,8192)}
report={'schema_version':'evidence-table.stronger-output-diagnosis.v1','frozen_E':freeze,'implementation_sha256':sha((ROOT/'runtime/implementation.json').read_bytes()),'input_hashes':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (op/'request.json',op/'response.body',op/'status.json',op/'stop.json')},'provider':{'http_status':200,'model':native['model'],'finish_reason':'length','usage':usage,'observed_valid_verdict':False,'parsed_result_exists':False},'requested_response_schema_property_order':list(request['response_format']['json_schema']['schema']['properties']),'strict_parser_error':parser_error,'content_json_error':json_error,'content_utf8_bytes':len(text.encode()),'content_codepoints':len(text),'expected_all_item_ids':ids,'expected_ID_count':len(ids),'expected_ID_categories':{kind:sum(cat==kind for cat,_ in r.p.all_items(d['assembled']['record'])) for kind in sorted({cat for cat,_ in r.p.all_items(d['assembled']['record'])})},'forensic_assessment_prefix':{'valid_verdict':False,'complete_objects':len(prefix),'IDs':prefix_ids,'expected_IDs_not_completed_in_prefix':[x for x in ids if x not in prefix_ids],'next_partial_object_start_codepoint':pos,'partial_tail_bytes':len(text[pos:].encode()),'complete_objects_canonical_bytes':array_bytes,'exact_original_complete_object_text_bytes':sum(end-start for start,end in spans),'reason_values_json_bytes':reason_bytes,'evidence_arrays_json_bytes':evidence_bytes,'unique_evidence_objects':len(unique_evidence),'evidence_occurrences':len(quotes),'unique_evidence_objects_bytes':sum(len(e) for e in unique_evidence),'unique_reason_strings':len(unique_reasons),'outer_row_fields_other_than_reason_evidence_json_bytes':sum(len(enc({k:v for k,v in x.items() if k not in ('reason','evidence')})) for x in prefix),'compact_prefix_wire_bytes':len(enc(wire)),'compact_prefix_exact_roundtrip':True,'global_verdict_sections_completed':[],'individual_object_schema_errors':prefix_schema_errors,'exact_evidence_selector_errors':prefix_evidence_errors,'not_semantically_scored':True},'rough_observed_rate_projection':{'visible_completion_tokens':visible_tokens,'prefix_complete_ID_fraction':len(prefix)/len(ids),'visible_tokens_scaled_to_70_rows_before_global_sections':visible_tokens*len(ids)/len(prefix),'completion_tokens_including_observed_reasoning_scaled_to_70_rows':visible_tokens*len(ids)/len(prefix)+usage['completion_tokens_details']['reasoning_tokens'],'method':'Linear extrapolation from this truncated prefix includes header and partial-row overhead, excludes missing global verdict sections; not tokenizer-measured or a capacity guarantee.'},'authored_full_verdict_sizing':fixtures,'diagnostic_codec_controls':controls,'next_cap_only_candidates':cap_candidates,'prior_cumulative_conservative_debit_usd':.542976718,'provider_calls':0,'credentials_read':False,'paid_artifacts_repaired_or_modified':False,'partial_JSON_accepted':False,'local_exact_tokenizer_available':importlib.util.find_spec('tiktoken') is not None,'limitations':['Prefix objects are forensic raw-text structure only, not accepted model judgments or source verification.','No global completeness/source-identity/omission/contradiction conclusion can be inferred from the truncated prefix.','Byte measurements and observed token extrapolation cannot establish universal 4096-token feasibility or future generation length.','Compact diagnostic response representation changes the output contract/presentation; exact expansion does not prove model correctness.']}
write('REPORT.json',report);assert verify_freeze()==freeze
print(json.dumps({'expected_ids':len(ids),'forensic_complete_rows':len(prefix),'strict_invalid':True,'controls':len(controls),'provider_calls':0,'freeze_entries':freeze['entries']}))
