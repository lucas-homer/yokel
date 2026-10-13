"""Independent offline protocol pin, structure and serialized-size review. No provider/runtime imports."""
import ast
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent.parent
REPO = ROUND.parents[3]
PROTO = ROUND / 'protocol'
rows = []
inputs = {}
def read(path):
    raw = path.read_bytes()
    inputs[str(path.relative_to(REPO))] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes':len(raw)}
    return raw

def load(path): return json.loads(read(path))
def encode(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def digest(x): return hashlib.sha256(encode(x)).hexdigest()
def check(name, truth): rows.append({'name':name,'pass':bool(truth)})
def pins(root, table, embedded=False):
    for name, pin in table.items():
        path = root / (pin['path'] if embedded else name)
        raw = read(path)
        check('pin:'+str(path.relative_to(REPO)), hashlib.sha256(raw).hexdigest()==pin['sha256'] and len(raw)==pin['bytes'])

ready = load(PROTO/'READY.json')
pins(PROTO,ready['files']); pins(REPO,ready['consulted_inputs'])
source_ready=load(ROUND/'source/READY.json');pins(ROUND/'source',source_ready['artifacts'],True)
candidate_ready=load(ROUND/'candidate/READY.json');pins(ROUND/'candidate',candidate_ready['artifacts'])
source_binding=load(PROTO/'SOURCE-BINDING.json');source_release=load(PROTO/'SOURCE-READY.json');pins(PROTO,source_release['files'])
check('binding_generic_ready',hashlib.sha256(read(PROTO/'READY.json')).hexdigest()==source_binding['generic_ready']['sha256'])
check('binding_source_ready',hashlib.sha256(read(ROUND/'source/READY.json')).hexdigest()==source_binding['source_archive_ready']['sha256'])
source=read(ROUND/'source/26-19-016.txt').decode();sh=hashlib.sha256(source.encode()).hexdigest()
check('source_exact_hash', sh==source_binding['source_text_sha256']==candidate_ready['source_text_sha256'])
check('source_exact_bytes',len(source.encode())==source_binding['source_text_bytes']==3876)
check('candidate_source_ready',hashlib.sha256(read(ROUND/'source/READY.json')).hexdigest()==candidate_ready['source_ready_sha256'])
# Execute only the already-reviewed parser definitions, never its write-to-source statements.
parser_tree=ast.parse(read(ROUND/'source/extract_source.py'))
definitions=[]
for node in parser_tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='raw' for t in node.targets): break
    definitions.append(node)
namespace={'__file__':str(ROUND/'source/extract_source.py')}
exec(compile(ast.Module(body=definitions,type_ignores=[]),'<parser-definitions>','exec'),namespace)
parser=namespace['Extractor']();parser.feed(read(ROUND/'source/original.htm').decode('utf-8-sig'));parser.close()
parsed=''.join(parser.parts).strip('\n')
check('archive_parser_exact_reproduction', parsed.encode()==read(ROUND/'source/parsed-body.txt'))
check('archive_all_text_tokens_retained', parsed.split()==source.split())
check('archive_anchors_exact', parser.links==load(ROUND/'source/anchors.json') and len(parser.links)==5)
frame=load(ROUND/'source/FRAME.json')
check('selection_first_eligible',next(c['id'] for c in frame['candidates'] if c['eligible'])==source_ready['selected']['id'])
check('selection_ascending_unique', [c['id'] for c in frame['candidates']]==sorted(set(c['id'] for c in frame['candidates'])))

boundaries=load(PROTO/'boundaries.json');policy=load(PROTO/'policy.json');settings=load(PROTO/'request-settings.json');plan=load(PROTO/'evaluation-plan.json');wirecon=load(PROTO/'inventory-wire-contract.json');fixtures=load(PROTO/'offline-fixtures.json');spec=read(PROTO/'SPEC.md').decode()
schemas={s:load(PROTO/f'stage-{s.lower()}.schema.template.json') for s in 'DACB'}
prompts={s:read(PROTO/f'stage-{s.lower()}.system.txt').decode() for s in 'DACB'}
check('A_exact_source_only',set(boundaries['exact_user_fields']['A'])=={'source_text','source_text_sha256'})
check('C_exact_source_inventory_only',set(boundaries['exact_user_fields']['C'])=={'source_text','source_text_sha256','inventory_wire','inventory_sha256'})
check('D_no_A_schedule',schemas['D']['properties']['units']['type']=='array' and schemas['D']['properties']['units']['items']=={'$ref':'#/$defs/d'})
check('D_shared_source_unit', schemas['D']['$defs']['u']==schemas['A']['$defs']['u'])
check('D_shared_scope',schemas['D']['$defs']['s']==schemas['C']['$defs']['s'])
check('D_shared_mapping',schemas['D']['$defs']['m']==schemas['B']['$defs']['m'])
check('D_missing_pointer_channel', 'missing' in schemas['D']['$defs']['m']['properties']['disposition']['enum'] and schemas['D']['$defs']['m']['properties']['operative_pointers']['minItems']==0)
check('D_discovery_instruction','find source claims absent from the candidate' in prompts['D'] and 'Do not restrict discovery to known record IDs' in prompts['D'])
check('C_B_empty_ID_templates', all(schemas[s]['properties'][k]['properties']=={} and schemas[s]['properties'][k]['required']==[] for s,k in [('C','scopes'),('B','mappings')]))
check('scope_bijection',policy['scope_basis_by_category']==dict(zip(['required_participation','identifying_context','retained_background','unresolved_scope'],['participation_function','identifies_proceeding','substantive_background_only','uncertain_source_function'])))
check('all_kinds_can_be_background',all(set(v)==set(policy['scope_categories']) for v in policy['allowed_scope_by_kind'].values()))
check('kind_keys_exact',set(policy['allowed_scope_by_kind'])==set(schemas['A']['$defs']['u']['properties']['kind']['enum']))
check('function_cases_present',len(fixtures['function_scope_cases'])==4 and {c['expected_category'] for c in fixtures['function_scope_cases']}=={'required_participation','retained_background'})
check('function_cases_not_model_truth','not host keyword classification or observed model performance' in fixtures['function_scope_interpretation'])
check('uncertainty_and_raw_loss_contract',policy['unresolved_scope_blocks_completeness'] and policy['known_raw_defects_preserved'])
check('not_production',not policy['production_eligible'] and not policy['action_ready'] and policy['whole_record_fidelity_default']=='unverified')
check('four_no_retry',plan['maximum_calls']==4 and plan['planned_order']==['D','A','C','B'] and plan['retries']==plan['repairs']==0 and plan['clipping'] is False)
check('price_routing_cap',settings['provider']=={'allow_fallbacks':False,'max_price':{'completion':10,'prompt':2},'only':['openai'],'order':['openai'],'require_parameters':True})
check('output_settings',settings['model']=='openai/gpt-6.1-sol' and settings['reasoning']=={'effort':'low'} and settings['max_tokens']==8192 and not settings['stream'])
budget=plan['budget'];check('exact_budget',budget['prior_debit_nanodollars']==1182150718 and budget['per_attempt_reserve_nanodollars']==161920000 and budget['maximum_prospective_debit_nanodollars']==1182150718+4*161920000==1829830718 and budget['remaining_after_max_reserve_nanodollars']==2000000000-1829830718)
check('reference_forbidden',{'independent_reference','gold','reference_crosswalk','known_defects','human_scope','assessment_notes'}<=set(boundaries['forbidden_all_stages']))
check('design_exposure_disclosed',ready['primary_design_source_exposure']=='disclosed; no blind design claim' and 'Primary read fresh source' in plan['protocol_design_exposure'])
check('scope_full_transport_consistent','no new scope codec' in boundaries['B_scope_transport'] and 'no additional scope codec' in spec)
check('inventory_nine_columns',len(wirecon['columns'])==9 and wirecon['evidence_columns']==['start','end','occurrence'])
# Independently rerun the inspected author script, capturing but not writing to owner paths.
run=subprocess.run([sys.executable,'-B',str(PROTO/'authoring_checks.py')],capture_output=True,text=True,check=True)
author_result=json.loads(run.stdout);check('author_checks_reproduced',author_result==load(PROTO/'authoring-checks.json') and author_result['passed']==author_result['total']==54)

record=load(ROUND/'candidate/candidate.json')
def project(x):
    if isinstance(x,dict):return {k:project(v) for k,v in x.items() if k not in ('evidence','coverage')}
    if isinstance(x,list):return [project(v) for v in x]
    return x
operative=project(record)
def identities(x):
    if isinstance(x,dict):return ([x['id']] if 'id' in x else [])+[v for k,val in x.items() if k not in ('evidence','coverage') for v in identities(val)]
    if isinstance(x,list):return [v for val in x for v in identities(val)]
    return []
check('projection_ID_identity',identities(record)==identities(operative))
base={'source_text':source,'source_text_sha256':sh};candidate_fields={'record_sha256':digest(record),'operative_record':operative,'operative_record_sha256':digest(operative)}
def make_body(stage,user,ids=()):
    schema=copy.deepcopy(schemas[stage]); replacements={'__SOURCE_SHA256__':sh,'__RECORD_SHA256__':digest(record),'__OPERATIVE_SHA256__':digest(operative),'__INVENTORY_SHA256__':user.get('inventory_sha256','0'*64),'__SCOPE_SHA256__':user.get('scope_sha256','0'*64)}
    for key,val in replacements.items():schema=json.loads(json.dumps(schema).replace(key,val))
    if stage in ('B','C'):
        key='mappings' if stage=='B' else 'scopes';ref='m' if stage=='B' else 's'
        schema['properties'][key].update(properties={i:{'$ref':'#/$defs/'+ref} for i in ids},required=list(ids))
    body=copy.deepcopy(settings)
    body.update(messages=[{'role':'system','content':prompts[stage]},{'role':'user','content':encode(user).decode()}],response_format={'type':'json_schema','json_schema':{'name':{'D':'direct_verification','A':'source_inventory','C':'source_scope','B':'source_mapping'}[stage],'strict':True,'schema':schema}})
    raw=encode(body)
    return {'body_bytes':len(raw),'guarded_bytes':len(raw)+1024,'fits':len(raw)+1024<=40000,'request_sha256':hashlib.sha256(raw).hexdigest()}
fixed={stage:make_body(stage,base|(candidate_fields if stage=='D' else {})) for stage in ('A','D')}
check('A_fixed_fits',fixed['A']['fits']);check('D_fixed_fits',fixed['D']['fits'])
profiles=[]
for label, assertion_len, applicability_len, reason_len, quote_len in [('concise',70,20,50,60),('modest',90,30,100,94),('longer',150,60,180,160)]:
    for n in (24,32,40,46,48,64):
        ids=[f'u{i:03}' for i in range(1,n+1)];units=[];scopes={};spans=[]
        for j,i in enumerate(ids):
            start=(j*59)%(len(source)-quote_len);quote=source[start:start+quote_len];occurrence=sum(source.startswith(quote,k) for k in range(start+1));ev={'quote':quote,'occurrence':occurrence}
            units.append(dict(id=i,kind='instruction',assertion='a'*assertion_len,modality='informational',applicability='a'*applicability_len,uncertainty='none',uncertainty_reason='',required_unit_ids=[],evidence=[ev]))
            scopes[i]=dict(category='required_participation',basis='participation_function',reason='r'*reason_len,evidence=[ev]);spans.append([[start,start+quote_len,occurrence]])
        inventory={'schema_version':'round12.source-inventory.v1','source_text_sha256':sh,'units':units}
        scope={'schema_version':'round12.source-scope.v1','source_text_sha256':sh,'inventory_sha256':digest(inventory),'scopes':scopes}
        wire={'schema_version':wirecon['schema_version'],'source_text_sha256':sh,'columns':wirecon['columns'],'evidence_columns':wirecon['evidence_columns'],'units':[[u[k] if k!='evidence' else spans[j] for k in wirecon['columns']] for j,u in enumerate(units)]}
        restored=[]
        for values in wire['units']:
            unit=dict(zip(wirecon['columns'],values));unit['evidence']=[{'quote':source[a:b],'occurrence':o} for a,b,o in unit['evidence']];restored.append(unit)
        check(f'probe_roundtrip_{label}_{n}',encode(restored)==encode(units))
        common=base|{'inventory_wire':wire,'inventory_sha256':digest(inventory)}
        profiles.append({'profile':label,'units':n,'assertion_chars':assertion_len,'applicability_chars':applicability_len,'scope_reason_chars':reason_len,'quote_chars':quote_len,'evidence_per_unit':1,'dependencies_per_unit':0,'C':make_body('C',common,ids),'B':make_body('B',common|candidate_fields|{'scope':scope,'scope_sha256':digest(scope)},ids)})
old=load(ROUND.parent/'round10-source-first/execution/run/stage-a/validated.json')
observed={'units':len(old['units'])}
for key in ('assertion','applicability','uncertainty_reason'):
    values=sorted(len(u[key]) for u in old['units']);observed[key]={'mean':sum(values)/len(values),'median':values[len(values)//2],'maximum':max(values)}
quotes=sorted(len(e['quote']) for u in old['units'] for e in u['evidence']);observed['quote']={'mean':sum(quotes)/len(quotes),'median':quotes[len(quotes)//2],'maximum':max(quotes)}
# No owner inputs changed during this review execution.
check('read_inputs_unchanged',all(hashlib.sha256((REPO/path).read_bytes()).hexdigest()==pin['sha256'] for path,pin in inputs.items()))
result={'schema_version':'round12.independent-protocol-review.v1','status':'TARGETED_BLOCKER','checks_passed':sum(r['pass'] for r in rows),'checks_total':len(rows),'checks':rows,'author_static_checks':54,'reference_contents_read':False,'provider_calls':0,'input_pins':inputs,'source_frame_pin_note':'FRAME.json is referenced but not hash-pinned by source READY; independently pinned here. Carry it into release dependency closure.','sizing':{'method':'Canonical UTF-8 JSON, double serialized user content, complete templates instantiated, complete operative projection, same request envelope as round10, plus 1024 bytes. Synthetic dimensions only; repeated letters are size fillers, not semantic inventory, scope truth, or evidence of source completeness. Response-format names are reviewer assumptions of the existing source_inventory/source_mapping naming convention; final builder must measure actual bodies.','operative_canonical_bytes':len(encode(operative)),'record_canonical_sha256':digest(record),'operative_canonical_sha256':digest(operative),'fixed_requests':fixed,'profiles':profiles,'prior_round10_observed_lengths':observed},'blocking_findings':['B full-scope object predictably overflows at modest32/48-unit profiles; preregister and review bounded lossless transport plus new request feasibility before implementation freeze.'],'nonblocking_findings':['Evaluation wording four calls versus one should be three-stage arm versus one-stage arm (four total).','Include FRAME.json in final immutable source/release pin closure.'],'runtime_validation':'Not performed; implementation absent. Function fixtures reviewed as synthetic semantic controls only.'}
print(json.dumps(result,indent=2))
if any(not r['pass'] for r in rows):sys.exit(1)
