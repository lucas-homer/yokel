"""Frozen full-request attribution and lossless diagnostic evidence codecs. No live path."""
import copy,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('offline network/process guard')
sys.addaudithook(guard)
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def put(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def size(v):return len(enc(v))
def verify_freeze():
    f=ROOT/'execution/freeze-E.json';assert sha(f.read_bytes())=='70815b1749d86ed4b842fdff58755c7d265311c39f820f85ae74ab3572d1ab29';value=json.loads(f.read_bytes())
    for row in value['files']:
        p=(ROOT/row['path']).resolve();assert p.is_relative_to(ROOT.resolve()) and sha(p.read_bytes())==row['sha256'] and p.stat().st_size==row['bytes']
    return {'sha256':sha(f.read_bytes()),'files_verified':len(value['files'])}
freeze=verify_freeze();DOC=ROOT/'execution/run/documents/doc-92211b8c7ba0'
original={s:json.loads((DOC/(s+'-request.json')).read_bytes()) for s in ('jev','stronger')}
payload=original['jev']['state'];wrapper=json.loads(original['stronger']['messages'][1]['content']);assert wrapper['payload']==payload
for stage in ('jev','stronger'):assert enc(original[stage])==(DOC/(stage+'-request.json')).read_bytes()
source=payload['source_text'];source_sha=sha(source.encode());assert source_sha==payload['source_text_sha256']
occurrences=[]
def gather(value,path=()):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='evidence':
                assert isinstance(item,list)
                for e in item:
                    assert set(e)=={'start','end','quote'} and source[e['start']:e['end']]==e['quote'];occurrences.append((path+(key,),e))
            else:gather(item,path+(key,))
    elif isinstance(value,list):
        for n,item in enumerate(value):gather(item,path+(n,))
gather(payload['record'])

def encode_payload(value,mode):
    out=copy.deepcopy(value);table=[];indexes={}
    def walk(node):
        if isinstance(node,dict):
            for key,item in list(node.items()):
                if key=='evidence':
                    encoded=[]
                    for ev in item:
                        entry=copy.deepcopy(ev) if mode=='table' else {'start':ev['start'],'end':ev['end']}
                        if mode=='spans':encoded.append(entry)
                        else:
                            identity=enc(entry)
                            if identity not in indexes:indexes[identity]=len(table);table.append(entry)
                            encoded.append(indexes[identity])
                    node[key]=encoded
                else:walk(item)
        elif isinstance(node,list):
            for item in node:walk(item)
    walk(out['record']);result={'schema_version':'diagnostic.lossless-evidence.'+mode+'.v1','payload':out}
    if mode!='spans':result['evidence_table']=table
    return result

def decode_payload(wire):
    version=wire['schema_version'];mode=version.split('.')[-2]
    if version!='diagnostic.lossless-evidence.'+mode+'.v1' or mode not in ('table','spans','span_table'):raise ValueError('unknown diagnostic codec')
    result=copy.deepcopy(wire['payload']);text=result['source_text']
    if sha(text.encode())!=result['source_text_sha256']:raise ValueError('source hash differs')
    def walk(node):
        if isinstance(node,dict):
            for key,item in list(node.items()):
                if key=='evidence':
                    decoded=[]
                    for value in item:
                        if mode=='spans':ev=copy.deepcopy(value)
                        else:
                            if type(value) is not int or not 0<=value<len(wire['evidence_table']):raise ValueError('invalid evidence reference')
                            ev=copy.deepcopy(wire['evidence_table'][value])
                        if set(ev)!=( {'start','end','quote'} if mode=='table' else {'start','end'}):raise ValueError('invalid evidence entry')
                        if type(ev['start']) is not int or type(ev['end']) is not int or not 0<=ev['start']<=ev['end']<=len(text):raise ValueError('invalid codepoint span')
                        quote=text[ev['start']:ev['end']]
                        if mode=='table' and ev['quote']!=quote:raise ValueError('evidence quote differs from source')
                        ev['quote']=quote;decoded.append(ev)
                    node[key]=decoded
                else:walk(item)
        elif isinstance(node,list):
            for item in node:walk(item)
    walk(result['record']);return result

INSTRUCTIONS={
 'table':' Diagnostic evidence encoding: state/payload is a versioned envelope. Read its payload as the full source and record. Every record evidence list contains integer references into evidence_table; each referenced object is the original exact quote and source codepoint span. Apply all references to the item that contains them; preserve every claim, association and uncertainty. Do not infer missing evidence.',
 'spans':' Diagnostic evidence encoding: state/payload is a versioned envelope containing the full source and record. Every record evidence object is a source span [start,end) using Unicode codepoint offsets. Its exact original quote is source_text[start:end]; read that full span as the evidence for its containing item. Preserve every claim, association and uncertainty. Do not infer missing evidence.',
 'span_table':' Diagnostic evidence encoding: state/payload is a versioned envelope containing the full source and record. Each record evidence list contains integer references into evidence_table. Each table entry is a [start,end) Unicode codepoint span; its exact quote is source_text[start:end]. Apply all references to the containing item, preserving every claim, association and uncertainty. Do not infer missing evidence.'}

def wire_bodies(wire,mode):
    bodies=copy.deepcopy(original);bodies['jev']['state']=wire
    for q in bodies['jev']['questions'].values():q['instructions']+=INSTRUCTIONS[mode]
    user=copy.deepcopy(wrapper);user['payload']=wire;bodies['stronger']['messages'][1]['content']=enc(user).decode();bodies['stronger']['messages'][0]['content']+=INSTRUCTIONS[mode]
    return bodies

def restore_bodies(bodies,mode):
    restored=copy.deepcopy(bodies);restored['jev']['state']=decode_payload(restored['jev']['state'])
    for q in restored['jev']['questions'].values():
        assert q['instructions'].endswith(INSTRUCTIONS[mode]);q['instructions']=q['instructions'][:-len(INSTRUCTIONS[mode])]
    user=json.loads(restored['stronger']['messages'][1]['content']);user['payload']=decode_payload(user['payload']);restored['stronger']['messages'][1]['content']=enc(user).decode();assert restored['stronger']['messages'][0]['content'].endswith(INSTRUCTIONS[mode]);restored['stronger']['messages'][0]['content']=restored['stronger']['messages'][0]['content'][:-len(INSTRUCTIONS[mode])]
    return restored

def measures(bodies):
    j=bodies['jev'];longest=max(size(q) for q in j['questions'].values());return {'jev':{'body_bytes':size(j),'estimate':size(j)+1024,'total_cap':64000,'state_bytes':size(j['state']),'longest_question_bytes':longest,'state_longest_estimate':size(j['state'])+longest+1024,'state_longest_cap':32000,'paired_arm_admitted':size(j)+1024<=64000 and size(j['state'])+longest+1024<=32000},'stronger':{'body_bytes':size(bodies['stronger']),'estimate':size(bodies['stronger'])+1024,'cap':40000,'paired_arm_admitted':size(bodies['stronger'])+1024<=40000,'completion_cap':bodies['stronger']['max_tokens']}}

baseline=measures(original)
for s in ('jev','stronger'):
    old=json.loads((DOC/(s+'-admission.json')).read_bytes());assert old['estimate']==baseline[s]['estimate'] and old['body_utf8_bytes']==baseline[s]['body_bytes']
assert baseline['jev']['state_longest_estimate']==33149 and baseline['stronger']['estimate']==40553
# Additive canonical JSON field attribution: each field carries encoded key, colon, value and comma; one comma subtracted + braces.
def fields(v):return {'fields':{k:len(enc(k))+1+size(x)+1 for k,x in v.items()},'container_adjustment':1,'total':size(v)}
record=payload['record'];evidence_arrays=[]
def array_sizes(v):
    if isinstance(v,dict):
        for key,item in v.items():
            if key=='evidence':evidence_arrays.append(size(item))
            else:array_sizes(item)
    elif isinstance(v,list):
        for item in v:array_sizes(item)
array_sizes(record)
unique={enc(e) for _,e in occurrences};unique_quotes={e['quote'] for _,e in occurrences}
prototypes={}
for mode in ('table','spans','span_table'):
    wire=encode_payload(payload,mode);decoded=decode_payload(wire);assert enc(decoded)==enc(payload)
    bodies=wire_bodies(wire,mode);assert enc(restore_bodies(bodies,mode))==enc(original);assert bodies['jev']['state']==json.loads(bodies['stronger']['messages'][1]['content'])['payload']
    m=measures(bodies);prototypes[mode]={'diagnostic_development_only':True,'observed':False,'provider_compatible':False,'model_correctness_measured':False,'wire_payload_sha256':sha(enc(wire)),'roundtrip_payload_sha256':sha(enc(decoded)),'original_payload_sha256':sha(enc(payload)),'full_bodies_exactly_restored':True,'decoder_instruction_bytes':len(INSTRUCTIONS[mode].encode()),'decoder_instruction_placements':{'jev':len(bodies['jev']['questions']),'stronger':1},'measurements':m,'body_savings_bytes':{s:baseline[s]['body_bytes']-m[s]['body_bytes'] for s in ('jev','stronger')},'paired_mechanical_admission':all(x['paired_arm_admitted'] for x in m.values())}
    put('DIAGNOSTIC-'+mode+'-wire-payload.json',{'diagnostic_development_only':True,'observed':False,'semantic_acceptance':False,'wire':wire})
# Codec rejection controls and exact repeated/Unicode reconstruction.
controls=[]
for mode in ('table','spans','span_table'):
    synthetic={'source_text':'α repeated.\nα repeated.\n','source_text_sha256':sha('α repeated.\nα repeated.\n'.encode()),'record':{'claims':[{'id':'x','evidence':[{'start':0,'end':11,'quote':'α repeated.'},{'start':12,'end':23,'quote':'α repeated.'}]}]}}
    assert enc(decode_payload(encode_payload(synthetic,mode)))==enc(synthetic);controls.append({'name':mode+'-unicode-repeated-spans-exact-roundtrip','passed':True})
    wire=encode_payload(payload,mode);bad=copy.deepcopy(wire);bad['payload']['source_text']+='x'
    try:decode_payload(bad)
    except ValueError:pass
    else:raise AssertionError('changed source accepted')
    controls.append({'name':mode+'-changed-source-rejected','passed':True})
    bad=copy.deepcopy(wire)
    if mode=='spans':bad['payload']['record']['events'][0]['evidence'][0]['end']=len(source)+1
    else:bad['payload']['record']['events'][0]['evidence'][0]=len(bad['evidence_table'])
    try:decode_payload(bad)
    except ValueError:pass
    else:raise AssertionError('invalid reference/span accepted')
    controls.append({'name':mode+'-invalid-reference-or-span-rejected','passed':True})
# Shared question instruction prefix attribution only; no new provider mechanism is assumed.
instructions=[q['instructions'] for q in original['jev']['questions'].values()];common=instructions[0]
for text in instructions[1:]:
    count=0
    for left,right in zip(common,text):
        if left!=right:break
        count+=1
    common=common[:count]
shared_prefix={'codepoints':len(common),'utf8_bytes':len(common.encode()),'copies':len(instructions),'repeated_bytes_beyond_first':(len(instructions)-1)*len(common.encode()),'implemented':False,'reason':'Moving common question instructions into state requires separate provider/semantic contract verification; duplication is retained in all prototypes.'}
# Quote tampering remains rejected, and moving a valid reference changes the canonical payload hash.
wire=encode_payload(payload,'table');bad=copy.deepcopy(wire);bad['evidence_table'][0]['quote']+='x'
try:decode_payload(bad)
except ValueError:pass
else:raise AssertionError('changed table quote accepted')
controls.append({'name':'table-changed-exact-quote-rejected','passed':True})
bad=copy.deepcopy(wire);array=bad['payload']['record']['events'][0]['evidence'];array[0]=(array[0]+1)%len(bad['evidence_table']);assert enc(decode_payload(bad))!=enc(payload)
controls.append({'name':'valid-reference-reassociation-detected-by-original-payload-hash','passed':True})
prior_totals=json.loads((ROOT/'execution/run/completed.json').read_bytes())['totals'];assert abs(prior_totals['budget_charge_usd']-.428936)<1e-12
candidate_budget={'prior_conservative_debit_usd':prior_totals['budget_charge_usd'],'proposed_new_operations':2,'inventory_calls':0,'jev_calls':1,'stronger_calls':1,'guard_max_new_reservation_usd':40000*.000002+4096*.000010+64000*.000000042,'guard_max_aggregate_usd':prior_totals['budget_charge_usd']+40000*.000002+4096*.000010+64000*.000000042,'table_exact_body_new_reservation_usd':prototypes['table']['measurements']['stronger']['estimate']*.000002+4096*.000010+prototypes['table']['measurements']['jev']['estimate']*.000000042,'no_refund_or_reset':True,'authorized':False}
report={'schema_version':'contract-probe.lossless-size-diagnosis.v1','frozen_E':freeze,'input_hashes':{str((DOC/(s+'-request.json')).relative_to(ROOT)):sha((DOC/(s+'-request.json')).read_bytes()) for s in ('jev','stronger')},'baseline':baseline,'payload_fields_additive':fields(payload),'record_fields_additive':fields(record),'record_evidence':{'occurrences':len(occurrences),'unique_evidence_objects':len(unique),'unique_quote_strings':len(unique_quotes),'evidence_arrays_bytes':sum(evidence_arrays),'unique_evidence_objects_bytes':sum(len(x) for x in unique),'all_evidence_objects_bytes':sum(size(e) for _,e in occurrences),'all_quote_values_json_bytes':sum(size(e['quote']) for _,e in occurrences),'unique_quote_values_json_bytes':sum(size(q) for q in unique_quotes)},'stronger_overhead':{'system_content_json_string_bytes':size(original['stronger']['messages'][0]['content']),'user_content_json_string_bytes':size(original['stronger']['messages'][1]['content']),'inner_user_json_bytes':size(wrapper),'response_format_bytes':size(original['stronger']['response_format']),'inner_payload_bytes':size(payload),'double_encoding_user_extra_bytes':size(original['stronger']['messages'][1]['content'])-size(wrapper)},'jev_overhead':{'questions_bytes':size(original['jev']['questions']),'shared_instruction_prefix':shared_prefix,'questions_fields':{k:fields(v) for k,v in original['jev']['questions'].items()}},'prototypes':prototypes,'next_candidate_budget':candidate_budget,'controls':controls,'provider_calls':0,'credentials_read':False,'source_truth_decoded':False,'frozen_artifacts_modified':False,'limitations':['Roundtrip equality proves data preservation, not provider/schema compatibility or model evidence retrieval correctness.','Offsets are Unicode codepoint positions, not UTF-8 byte or token positions.','Bytes+1024 are conservative estimates, not measured verifier provider tokens.','No live schema/request/runtime was changed; diagnostic wire encodings require a new reviewed contract.']}
put('REPORT.json',report);assert verify_freeze()==freeze
print(json.dumps({'frozen_files':freeze['files_verified'],'controls':len(controls),'mechanical_pair_fit':{mode:row['paired_mechanical_admission'] for mode,row in prototypes.items()},'provider_calls':0}))
