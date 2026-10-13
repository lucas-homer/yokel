"""Offline operational audit of the exact primary-frozen two-stage execution."""
import base64,hashlib,importlib.util,json,sys
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
HERE=Path(__file__).resolve().parent;REVIEW=HERE.parent;ROOT=REVIEW.parent;BENCH=ROOT.parent;RUN=ROOT/'execution/run';PROTO=ROOT/'protocol'
EXPECTED_FREEZE='d6d3d600146539f9ac0abe3c7a3eae6d78b682cf4425017ab54919ae922ce15a'
EXPECTED_MANIFEST='62c0477283ed6f757facc07bee31b67601702d90c4cc9daf233d9b92e63bbd86'
EXPECTED_RUNTIME='27452c46ba92d766a485acfb299d3a08c7418c69e64afd1db72217bf9d67ec66'
EXPECTED_REVIEW='aae0d321a935c2c826e466427c0a10809b9ffbbc7b43365c82c0de4f2d591d1a'
EXPECTED_EXE='821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e'
sys.dont_write_bytecode=True;sys.path.insert(0,str(REVIEW/'runtime'));import review_support as r
r.install_guard(HERE)
def private_guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)) and Path(args[0]).suffix in ('.pem','.key'):raise AssertionError('private signing/credential file forbidden')
sys.addaudithook(private_guard)
checks=[]
def read(p):return r.strict(Path(p).read_bytes())
def sha(p):return r.sha(Path(p).read_bytes())
def ck(name,ok,detail=None):
 checks.append({'name':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name)
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
freeze_path=ROOT/'execution/freeze.json';ck('Primary freeze exact bytes',sha(freeze_path)==EXPECTED_FREEZE);freeze=read(freeze_path);paths=[]
for row in freeze['files']:
 p=(ROOT/row['path']).resolve();paths.append(p);ck('Frozen '+row['path'],p.is_relative_to(RUN) and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'])
ck('Exactly20 frozen execution files',len(paths)==len(set(paths))==20 and set(paths)=={p for p in RUN.rglob('*') if p.is_file()})
ck('Signed runtime review READY unchanged',sha(REVIEW/'runtime/READY.json')==EXPECTED_REVIEW)
for name,h in read(REVIEW/'runtime/READY.json')['artifacts'].items():ck('Runtime review artifact '+name,sha(REVIEW/'runtime'/name)==h)
ck('Runtime READY unchanged',sha(ROOT/'runtime/READY.json')==EXPECTED_RUNTIME)
for name,h in read(ROOT/'runtime/READY.json')['artifacts'].items():ck('Runtime artifact '+name,sha(ROOT/'runtime'/name)==h)
for name,h in read(REVIEW/'BARRIER-READY.json')['files'].items():ck('Barrier artifact '+name,sha(REVIEW/name)==h)
core=read(BENCH/'runner-stability-review/deployment/core.json');job='round10-source-first-initial';manifest_path=Path(core['registry_dir'])/(job+'.json');raw_manifest=manifest_path.read_bytes();manifest=r.strict(raw_manifest)
ck('Canonical signed manifest',sha(manifest_path)==EXPECTED_MANIFEST and r.encode(manifest)==raw_manifest)
ck('Manifest equals reviewed unsigned proposal',manifest==read(ROOT/'runtime/UNSIGNED-JOB-PROPOSAL.json'))
ck('Primary release exact manifest',read(ROOT/'release-receipt.json')['manifest_sha256']==read(ROOT/'primary-release-verification.json')['manifest_canonical_sha256']==EXPECTED_MANIFEST)
ck('Fixed argv and single provider variable',manifest['provider_variables']==['OPENROUTER_API_KEY'] and manifest['job']['argv']==[core['python_path'],'-I','-S','-B',str(ROOT/'runtime/adapter.py'),'--live-initial'])
ck('Manifest budget exact',manifest['budget']=={'prior_nanousd':r.PRIOR,'reservation_nanousd':2*r.RESERVE,'ceiling_nanousd':r.CEILING})
files=manifest['job']['files'];bad=[p for p,h in files.items() if sha(p)!=h];ck('All6755 signed pins unchanged',len(files)==6755 and not bad,{'count':len(files),'mismatches':bad})
ck('Final review path signed',manifest['review']=={'path':str(REVIEW/'runtime/FINAL-REVIEW.md'),'sha256':sha(REVIEW/'runtime/FINAL-REVIEW.md')})
sys.path.insert(0,str(Path(core['python_path']).parent.parent/'lib/python3.12/site-packages'))
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
public=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),base64.b64decode(core['public_key_base64'],validate=True))
public.verify((Path(core['registry_dir'])/(job+'.sig')).read_bytes(),b'yokel.research-job.v1\0'+raw_manifest,ec.ECDSA(hashes.SHA256()));ck('Public-only signature verifies',True)
ck('Consumed native claim binds manifest',(Path(core['journal_dir'])/job).read_text()==EXPECTED_MANIFEST)
ck('Installed executor unchanged',sha(Path('/Users/home/.local/libexec/yokel/research-credentials-stable-v1'))==EXPECTED_EXE)
deployment=read(BENCH/'runner-stability-review/deployment/FREEZE.json')['files'];ck('Deployment pins unchanged',all(sha(p)==h for p,h in deployment.items()),{'count':len(deployment)})
prior=read(ROOT/'prior-baseline.json')['files'];bad=[x['path'] for x in prior if sha(BENCH/x['path'])!=x['sha256'] or (BENCH/x['path']).stat().st_size!=x['bytes']];ck('All5114 prior files unchanged',len(prior)==5114 and not bad)
a=load('postrun_r10_adapter',ROOT/'runtime/adapter.py');k=a.k;c=a.c
text,record,planned,prior_report=a.preflight();a.verify_live_bindings();ck('Actual late bindings and authorization pass',True)
settings=read(PROTO/'request-settings.json');a_request=read(RUN/'stage-a/request.json');ck('Exact approved source-only A request',a_request==read(PROTO/'stage-a.offline-request.json')==planned['body'])
ck('A source-only user',r.strict(a_request['messages'][1]['content'])=={'source_text':text,'source_text_sha256':r.sha(text.encode())})
results={};values={};envelopes={};costs=[];current=r.PRIOR
for stage in ('stage-a','stage-b'):
 folder=RUN/stage;request=read(folder/'request.json');request_raw=(folder/'request.json').read_bytes();intent=read(folder/'intent.json');raw=(folder/'response.body').read_bytes();native=r.strict(raw);status=read(folder/'status.json');result=read(folder/'result.json');done=read(folder/'completed.json')
 ck(stage+' canonical request/hash/guard',request_raw==r.encode(request) and sha(folder/'request.json')==intent['request_sha256']==result['request_sha256'] and len(request_raw)+1024==intent['guarded_bytes']<=40000)
 ck(stage+' settings exact',all(request[k0]==v for k0,v in settings.items()) and request['max_tokens']==intent['output_cap']==8192)
 ck(stage+' intent scope and debit',intent['stage']==stage and intent['reserved_nanousd']==r.RESERVE and intent['prior_stage_debit_nanousd']==current and intent['ceiling_nanousd']==r.CEILING and intent['automatic_retry'] is False and intent['protocol_ready_sha256']==c.READY_SHA and intent['runtime_input_pins_sha256']==sha(ROOT/'runtime/input-pins.json'))
 ck(stage+' successful HTTP/raw binding',status=={'http_status':200,'response_sha256':sha(folder/'response.body')} and result['response_sha256']==sha(folder/'response.body'))
 ck(stage+' native identity/envelope',native.get('model')=='openai/gpt-6.1-sol' and native.get('provider')=='OpenAI' and not native.get('error') and len(native['choices'])==1)
 choice=native['choices'][0];msg=choice['message'];ck(stage+' completed without refusal/tools',choice['finish_reason']=='stop' and choice.get('native_finish_reason') in (None,'completed') and not choice.get('error') and not msg.get('refusal') and not msg.get('tool_calls'))
 content=msg['content'].encode();value=r.strict(content);values[stage]=value;envelopes[stage]=native
 ck(stage+' original content and canonical value preserved',content==(folder/'content.body').read_bytes() and r.encode(value)==(folder/'validated.json').read_bytes() and r.sha(content)==result['content_sha256'] and r.sha(r.encode(value))==result['canonical_value_sha256'])
 checked=k.validate_a(text,value) if stage=='stage-a' else k.validate_b(text,record,values['stage-a'],value)
 ck(stage+' exact validator reproduction',checked==result['validation'] and checked['structural_valid'] is True)
 parsed_content,meta=a.native(raw);ck(stage+' exact native metadata reproduction',parsed_content==content and all(result[x]==y for x,y in meta.items()))
 invhash=r.sha(r.encode(value if stage=='stage-a' else values['stage-a']));recordhash=None if stage=='stage-a' else r.sha(r.encode(record))
 ck(stage+' source/inventory/record bindings',result['source_text_sha256']==r.sha(text.encode()) and result['inventory_sha256']==invhash and result['record_sha256']==recordhash and intent['record_sha256']==recordhash and intent['inventory_sha256']==(None if stage=='stage-a' else invhash))
 ck(stage+' completed receipt exact',done=={'state':'validated_frozen','result_sha256':sha(folder/'result.json'),'validated_sha256':sha(folder/'validated.json'),'response_sha256':sha(folder/'response.body')})
 usage=json.loads(raw,parse_float=Decimal)['usage'];reported=usage['cost'];prompt=usage['prompt_tokens'];completion=usage['completion_tokens'];rate=prompt*2000+completion*10000;reported_nano=int((reported*10**9).to_integral_value(rounding=ROUND_CEILING));charge=max(r.RESERVE,reported_nano,rate)
 ck(stage+' usage internally consistent',type(prompt) is int and type(completion) is int and min(prompt,completion)>=0 and usage['total_tokens']==prompt+completion and completion<=8192)
 ck(stage+' independent accounting',result['budget_charge_nanousd']==charge and result['usage_rate_estimated_nanousd']==rate and result['cumulative_budget_charge_nanousd']==current+charge and Decimal(str(result['reported_cost_usd']))==reported)
 ck(stage+' semantic flags not promoted',result['semantic_status']=='unverified' and result['production_eligible'] is False and result['action_ready'] is False and result['invoice_verified'] is False)
 costs.append({'stage':stage,'reported_usd':str(reported),'reported_nanousd':reported_nano,'frozen_rate_estimated_nanousd':rate,'conservative_charge_nanousd':charge,'prompt_tokens':prompt,'completion_tokens':completion,'reasoning_tokens':usage['completion_tokens_details']['reasoning_tokens']});current+=charge;results[stage]=result
inv=values['stage-a'];units=inv['units'];ids=[u['id'] for u in units]
ck('46 unique frozen inventory IDs',len(ids)==len(set(ids))==46)
freeze_value,freeze_result=a.freeze_a(RUN,planned,text);ck('A durable freeze revalidation',freeze_value==inv and freeze_result==results['stage-a'])
# Independently regenerate selectors using overlapping codepoint positions.
independent_wire=r.span_encode(inv,text)
for u,row in zip(units,independent_wire['units']):ck('Independent A selectors '+u['id'],row[8]==results['stage-a']['validation']['evidence_spans'][u['id']])
b_request=read(RUN/'stage-b/request.json');user=r.strict(b_request['messages'][1]['content'])
ck('B exact approved user envelope',set(user)=={'source_text','source_text_sha256','record_sha256','operative_record','operative_record_sha256','inventory_wire','inventory_sha256'})
ck('B full identical source and record binding',user['source_text']==text and user['source_text_sha256']==r.sha(text.encode()) and user['record_sha256']==r.sha(r.encode(record)))
ck('B full operative record projection',user['operative_record']==r.projection(record) and user['operative_record_sha256']==r.sha(r.encode(r.projection(record))))
ck('310 fields and70 identity contexts intact',r.fields(user['operative_record'])==r.fields(record) and len(r.fields(record))==310 and r.identities(user['operative_record'])==r.identities(record) and len(r.identities(record))==70)
ck('Every B span exact and whole A invertible',user['inventory_wire']==independent_wire and r.span_restore(user['inventory_wire'],text,inv)==inv and user['inventory_sha256']==r.sha(r.encode(inv)))
schema=read(PROTO/'stage-b.schema.template.json');schema['properties']['inventory_sha256']['enum']=[r.sha(r.encode(inv))];schema['properties']['mappings']={'type':'object','properties':{i:{'$ref':'#/$defs/m'} for i in ids},'required':ids,'additionalProperties':False}
independent_user={'source_text':text,'source_text_sha256':r.sha(text.encode()),'record_sha256':r.sha(r.encode(record)),'operative_record':r.projection(record),'operative_record_sha256':r.sha(r.encode(r.projection(record))),'inventory_wire':independent_wire,'inventory_sha256':r.sha(r.encode(inv))}
independent_b={**settings,'messages':[{'role':'system','content':(PROTO/'stage-b.system.txt').read_text()},{'role':'user','content':r.encode(independent_user).decode()}],'response_format':{'type':'json_schema','json_schema':{'name':'source_mapping','strict':True,'schema':schema}}}
ck('Independent entire B request reconstruction',independent_b==b_request and r.encode(independent_b)==(RUN/'stage-b/request.json').read_bytes())
ck('Runtime B request reproduction',k.build_b(text,record,inv)['body']==b_request)
pre=read(RUN/'stage-b-preflight.json');expected_pre={'request_sha256':sha(RUN/'stage-b/request.json'),'body_bytes':len(r.encode(b_request)),'guarded_bytes':len(r.encode(b_request))+1024,'fits':len(r.encode(b_request))+1024<=40000,'current_debit_nanousd':r.PRIOR+costs[0]['conservative_charge_nanousd'],'admission_with_reservation_nanousd':r.PRIOR+costs[0]['conservative_charge_nanousd']+r.RESERVE,'within_ceiling':r.PRIOR+costs[0]['conservative_charge_nanousd']+r.RESERVE<=r.CEILING,'inventory_sha256':r.sha(r.encode(inv)),'source_text_sha256':r.sha(text.encode()),'record_sha256':r.sha(r.encode(record)),'stage_a_freeze_sha256':sha(RUN/'stage-a-freeze.json')}
ck('Exact B admission/gating receipt',pre==expected_pre and pre['fits'] and pre['within_ceiling'] and pre['guarded_bytes']==36326)
value=values['stage-b'];mappings=value['mappings'];ck('Exactly46 B mapping IDs',len(mappings)==46 and set(mappings)==set(ids))
allow=r.fields(record)
for i,m in mappings.items():
 expected_values=[{'pointer':p,'value':allow[p],'value_sha256':r.sha(r.encode(allow[p]))} for p in m['operative_pointers']]
 ck('Independent B operative values '+i,len(m['operative_pointers'])==len(set(m['operative_pointers'])) and results['stage-b']['validation']['operative_values'][i]==expected_values)
# Independently aggregate effective dispositions and preserve raw model judgments.
index={u['id']:u for u in units};effective={};active=set()
def visit(i):
 if i in effective:return effective[i]
 if i in active:raise AssertionError('dependency cycle')
 active.add(i);u=index[i];m=mappings[i]['disposition'];deps=[visit(d) for d in u['required_unit_ids']];active.remove(i)
 if m=='matched':assert u['uncertainty']=='none' and u['modality']!='unknown' and all(mappings[d]['disposition']=='matched' for d in u['required_unit_ids'])
 status='unknown' if m=='unknown' or u['uncertainty']!='none' or u['modality']=='unknown' or 'unknown' in deps else 'incomplete' if any(d!='matched' for d in deps) else m
 effective[i]=status;return status
for i in index:visit(i)
statuses=set(effective.values());summary='unverified' if 'unknown' in statuses else 'not_complete' if statuses-{'matched'} else 'all_inventoried_units_matched';checked=results['stage-b']['validation']
ck('Independent dependency aggregation',effective==checked['effective_dispositions'] and summary==checked['mapping_status'] and checked['known_defects']==[i for i,m in mappings.items() if m['disposition'] in ('missing','mismatched')])
ledger=read(RUN/'ledger.json');expected_ledger={'prior_nanousd':r.PRIOR,'operations':[{'stage':x['stage'],'budget_charge_nanousd':x['conservative_charge_nanousd'],'reserved_nanousd':r.RESERVE,'state':'validated_frozen'} for x in costs],'new_budget_charge_nanousd':sum(x['conservative_charge_nanousd'] for x in costs),'cumulative_budget_charge_nanousd':current,'ceiling_nanousd':r.CEILING,'invoice_verified':False}
ck('Independent exact aggregate ledger',ledger==expected_ledger==a.ledger(RUN) and current==1182150718<=r.CEILING)
ck('Reported charges sum exactly',sum(Decimal(x['reported_usd']) for x in costs)==Decimal('.115117'))
completed=read(RUN/'completed.json');ck('Completion receipt honest',completed=={'state':'two_stages_completed','mapping_status':summary,'source_inventory_completeness':'unverified','whole_record_fidelity':'unverified','semantic_status':'unverified','production_eligible':False,'action_ready':False,'ledger_sha256':sha(RUN/'ledger.json')})
ck('Exactly two attempts and no stop/retry artifacts',len(list(RUN.rglob('intent.json')))==2 and len(list(RUN.rglob('response.body')))==2 and not list(RUN.rglob('stop.json')) and {p.name for p in RUN.iterdir() if p.is_dir()}=={'stage-a','stage-b'})
ck('Sequential intent times',read(RUN/'stage-a/intent.json')['started_utc']<read(RUN/'stage-b/intent.json')['started_utc'])
ck('Distinct response identifiers',bool(envelopes['stage-a'].get('id')) and bool(envelopes['stage-b'].get('id')) and envelopes['stage-a']['id']!=envelopes['stage-b']['id'])
ck('Final freeze unchanged',sha(freeze_path)==EXPECTED_FREEZE and all(sha(ROOT/x['path'])==x['sha256'] for x in freeze['files']))
ck('Signed pins still unchanged',all(sha(p)==h for p,h in files.items()))
report={'schema_version':'round10.postrun-operational-audit.v1','state':'passed','checks':checks,'check_count':len(checks),'freeze_sha256':EXPECTED_FREEZE,'manifest_sha256':EXPECTED_MANIFEST,'signature_verified':True,'native_consumed_claim_verified':True,'retained_attempts':2,'frozen_files':20,'source_inventory_units':46,'mapping_keys':46,'stage_a_guarded_bytes':len(r.encode(a_request))+1024,'stage_b_guarded_bytes':pre['guarded_bytes'],'stage_a_request_sha256':sha(RUN/'stage-a/request.json'),'stage_b_request_sha256':sha(RUN/'stage-b/request.json'),'costs':costs,'total_reported_usd':str(sum(Decimal(x['reported_usd']) for x in costs)),'total_frozen_rate_estimated_nanousd':sum(x['frozen_rate_estimated_nanousd'] for x in costs),'new_conservative_nanousd':ledger['new_budget_charge_nanousd'],'cumulative_conservative_nanousd':current,'ceiling_nanousd':r.CEILING,'mapping_status':summary,'source_inventory_completeness':'unverified','semantic_status':'unverified','whole_record_fidelity':'unverified','production_eligible':False,'action_ready':False,'provider_calls_by_auditor':0,'credentials_read':False,'runner_invoked':False,'limits':['Two retained intents/responses, signed consumed claim and reviewed one-shot control flow support two sequential attempts; no independent network capture.','Structural compatibility observed in these two responses, not general provider compatibility.','Source discovery/mapping semantic correctness is outside this operational audit.','Provider-reported charges and frozen-rate estimates are not verified invoices.','Native exit0/no-auth-prompt report is a primary observation.']}
(HERE/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('checks','limits')}))
