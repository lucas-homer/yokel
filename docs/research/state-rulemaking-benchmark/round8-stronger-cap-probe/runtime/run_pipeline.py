#!/usr/bin/env python3
"""One-source cap probe with immutable R7 normalization and R8 failure semantics."""
import argparse,copy,fcntl,hashlib,importlib.util,json,os,platform,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ROUND=ROOT.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ops=load('round8_operations',ROOT/'operations.py')
Ledger,Pause,Stop,put,sha,sanitize_input=ops.Ledger,ops.Pause,ops.Stop,ops.put,ops.sha,ops.sanitize_input
j=ops.j

def verified_r7():
    lineage=j.loads((ROOT/'lineage.json').read_bytes())
    if set(lineage)!={'schema_version','files'} or lineage['schema_version']!='round8-stronger-cap-probe.frozen_lineage.v1':raise Stop('R7 lineage shape/version')
    expected=ROUND.parent/'round7'
    for name,want in lineage['files'].items():
        path=Path(name)
        if not any(path.resolve().is_relative_to((ROUND.parent/name).resolve()) for name in ('round5','round6','round7','round8','round8-offline-contract','round8-contract-probe','round8-evidence-table')) or sha(path.read_bytes())!=want:raise Stop('frozen R7 dependency drift')
    return load('round8_frozen_r7_helpers',expected/'runtime/run_pipeline.py')
normalized=verified_r7();p=normalized.p;a=normalized.a

PRIOR_DEBIT=.542976718
LIMITS={**a.LIMITS,'documents':1,'PDF_pages':2,'inventory_calls':0,'Jev_calls':0,'stronger_calls':1,'inventory_completion':12288,'stronger_input_estimate':40000,'stronger_completion':8192}
MAX_RESERVATION=40000*a.PRICES['prompt']+8192*a.PRICES['completion']
assert abs(MAX_RESERVATION-.16192)<1e-12 and PRIOR_DEBIT+MAX_RESERVATION<2

codec=load('frozen_evidence_table_codec',ROUND.parent/'round8-evidence-table/runtime/codec.py')
INSTRUCTIONS=ROUND.parent/'round8-evidence-table/runtime/decoding-instructions.txt'

def auth_scope():
    input_pin=j.loads((ROOT/'input-pin.json').read_bytes())
    return dict(prior_budget_debit_usd=PRIOR_DEBIT,prior_debit_sha256=sha((ROOT/'prior-debit.json').read_bytes()),max_new_operations=1,inventory_calls=0,jev_calls=0,stronger_calls=1,stronger_completion=8192,stronger_input_guard=40000,jev_total_input_guard=64000,jev_state_longest_guard=32000,wire_version=codec.VERSION,decoding_instructions_sha256=sha(INSTRUCTIONS.read_bytes()),input_pin_sha256=sha((ROOT/'input-pin.json').read_bytes()),original_payload_sha256=input_pin['payload_sha256'],original_record_sha256=input_pin['record_sha256'])

def verify_prior_debit():
    debit=j.loads((ROOT/'prior-debit.json').read_bytes())
    if set(debit)!={'schema_version','prior_budget_debit_usd','operations'} or debit['schema_version']!='round8-stronger-cap-probe.prior_debit.v1' or debit['prior_budget_debit_usd']!=PRIOR_DEBIT or len(debit['operations'])!=5:raise Stop('five conservative debits required')
    expected=[('round8','inventory-82b41c219e64bc9c63a0ed61','inventory','ef9891fca1a9aa6e0eeeafcdfee22d46b7d6dab8c79ff39099c3e00ef4f2c996',False),('round8-cap-probe','inventory-8f69eccb0e19f2d6e43cc72d','inventory','415b294f83b3c093bd623da4cd4369a3c84cf385e6402ad190794e5681b30fb6',True),('round8-contract-probe','inventory-5d2039370e0567529575653a','inventory','70815b1749d86ed4b842fdff58755c7d265311c39f820f85ae74ab3572d1ab29',True),('round8-evidence-table','jev-58a12718be3c9f0448ffce85','jev','db895208c9f7573517be057a58ec6126e793024caf6a532fe2e2a72dd391c53c',True),('round8-evidence-table','stronger-089be69dd81d8b0468fa2052','stronger','db895208c9f7573517be057a58ec6126e793024caf6a532fe2e2a72dd391c53c',False)]
    total=0;reported_total=0;estimated_total=0;parsed_total=0
    for row,(name,opname,kind,freeze_sha,parsed) in zip(debit['operations'],expected):
        old=(ROUND.parent/name).resolve();op=old/'execution/run/operations'/opname;freeze=old/'execution/freeze-E.json'
        if row['round_root']!=str(old) or row['parsed_result_present'] is not parsed or row['kind']!=kind or row['operation_id']!='doc-92211b8c7ba0-'+kind:raise Stop('prior operation identity differs')
        paths=[freeze,op/'intent.json',op/'request.json',op/'response.body',op/'status.json',op/('result.json' if parsed else 'stop.json')]
        if set(row['files'])!={str(x) for x in paths} or row['files'][str(freeze)]!=freeze_sha:raise Stop('prior debit scope differs')
        for path in paths:
            if sha(path.read_bytes())!=row['files'][str(path)]:raise Stop('prior debit artifact drift')
        for item in j.loads(freeze.read_bytes())['files']:
            path=(old/item['path']).resolve()
            if not path.is_relative_to(old) or sha(path.read_bytes())!=item['sha256'] or path.stat().st_size!=item['bytes']:raise Stop('prior freeze drift')
        intent=j.loads((op/'intent.json').read_bytes());native=j.loads((op/'response.body').read_bytes());status=j.loads((op/'status.json').read_bytes());reserve=intent['reserved_nominal_usd'];reported=native['usage'].get('cost');result=j.loads((op/'result.json').read_bytes()) if parsed else None;cost=result.get('observed_cost_usd') if result else None;estimated=result.get('usage_rate_estimated_usd') if result else None
        if status['response_sha256']!=sha((op/'response.body').read_bytes()) or intent['request_sha256']!=sha((op/'request.json').read_bytes()) or intent['operation_id']!=row['operation_id'] or reserve!=row['reserved_nominal_usd'] or reported!=row['recoverable_native_reported_usd'] or cost!=row['parsed_result_accounted_usd'] or estimated!=row['usage_rate_estimated_usd'] or row['conservative_debit_usd']!=max(reserve,reported or 0,cost or 0):raise Stop('prior cost reporting or max debit differs')
        if parsed:
            rebuilt=a.parse_jev((op/'response.body').read_bytes(),j.loads((op/'request.json').read_bytes())['questions']) if kind=='jev' else a.parse_or((op/'response.body').read_bytes())
            if rebuilt!=result:raise Stop('prior parsed result differs')
        elif (op/'result.json').exists():raise Stop('prior invalid response gained a parsed result')
        total+=row['conservative_debit_usd'];reported_total+=reported or 0;parsed_total+=cost or 0
        if kind=='jev':estimated_total+=estimated or 0
    if abs(total-PRIOR_DEBIT)>1e-12:raise Stop('cumulative conservative debit differs')
    return {**debit,'reporting':dict(recoverable_native_reported_usd=reported_total,jev_usage_rate_estimated_usd=estimated_total,parsed_result_accounted_usd=parsed_total,invalid_response_costs_recovered_without_verdict=True,invoice_verified=False)}

def admission(body,source_sha256):
    estimate=a.estimate_input(body);allowed=estimate<=40000 and body.get('max_tokens')==8192
    return dict(schema_version='round8-stronger-cap-probe.admission.v1',stage='stronger',body_sha256=sha(j.encode(body)),body_utf8_bytes=len(j.encode(body)),estimate=estimate,cap=40000,state_longest_estimate=None,state_longest_cap=None,admitted=allowed,reason=None if allowed else 'stronger input/output guard violation; no clipping',reservation_usd=estimate*a.PRICES['prompt']+8192*a.PRICES['completion'] if allowed else None,source_sha256=source_sha256)

def requests(source,assembled):
    common=p.verification_payload(source,assembled);pin=j.loads((ROOT/'input-pin.json').read_bytes());item=pin['files']['wire_stronger_request'];path=Path(item['path'])
    if sha(path.read_bytes())!=item['sha256']:raise Stop('original wire request drift')
    original=j.loads(path.read_bytes());wrapper=j.loads(original['messages'][1]['content']);wire=wrapper['payload'];restored=codec.restore(wire,pin['payload_sha256'])
    if restored!=common['payload'] or wrapper['payload_sha256']!=common['payload_sha256'] or original['max_tokens']!=4096:raise Stop('original wire/source/record differs')
    body=copy.deepcopy(original);body['max_tokens']=8192;receipt=admission(body,source['source_text_sha256'])
    return {'stronger':{'body':body,'admission':receipt}},dict(wire=wire,wire_sha256=sha(j.encode(wire)),restored_payload_sha256=sha(j.encode(restored)),original_payload_sha256=pin['payload_sha256'],original_record_sha256=pin['record_sha256'],exact_restoration=True),original

def code_pins():
    import importlib.metadata
    paths=[ROOT/x for x in ('run_pipeline.py','operations.py','provider_transport.py','offline_checks.py','verify_offline.py','INTERFACE.md','README.md','lineage.json','source-pin.json','prior-debit.json','input-pin.json','observation.py')]
    lineage=j.loads((ROOT/'lineage.json').read_bytes());files={str(path.resolve()):sha(path.read_bytes()) for path in paths}
    files.update(lineage['files'])
    prior=verify_prior_debit()
    return dict(schema_version='round8-stronger-cap-probe.implementation.v1',code=files,limits=LIMITS,models={'inventory':a.MODEL,'stronger':a.MODEL,'jev':a.j.JEV_MODEL},OR_canonical_slug=a.CANONICAL_MODEL,prices=a.PRICES,nominal_max_reservation_usd=MAX_RESERVATION,aggregate_nominal_with_prior_usd=PRIOR_DEBIT+MAX_RESERVATION,prior_debit_sha256=sha((ROOT/'prior-debit.json').read_bytes()),wire_version=codec.VERSION,decoding_instructions_sha256=sha(INSTRUCTIONS.read_bytes()),python_version=platform.python_version(),pypdf_version=importlib.metadata.version('pypdf'),R7_lineage_sha256=sha((ROOT/'lineage.json').read_bytes()),production_eligible=False,action_ready=False)

def verify_implementation(path):
    verified_r7();value=j.loads(Path(path).read_bytes())
    if value!=code_pins():raise Stop('implementation/code/model/schema pins changed')
    return value

def load_sources(manifest,root):
    from pypdf import PdfReader
    root=Path(root).resolve();manifest=Path(manifest).resolve()
    if not manifest.is_relative_to(root) or manifest.stat().st_size>100000:raise Stop('manifest path/size violation')
    value=j.loads(manifest.read_bytes());required={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known','retained_inputs'}
    if set(value)!={'schema_version','documents'} or value['schema_version']!='round8-stronger-cap-probe.inputs.v1' or not isinstance(value['documents'],list) or not len(value['documents'])==1:raise Stop('strict source manifest shape/one-document cap')
    rows=[];seen=set();pages=0
    for unit in value['documents']:
        if not isinstance(unit,dict) or set(unit)!=required or not isinstance(unit['document_id'],str) or not re.fullmatch(r'doc-[a-f0-9]{12}',unit['document_id']) or unit['document_id'] in seen:raise Stop('source identity/shape violation')
        seen.add(unit['document_id'])
        source_pin=j.loads((ROOT/'source-pin.json').read_bytes())
        if unit['document_id']!=source_pin['document_id'] or unit['text_sha256']!=source_pin['source_text_sha256'] or unit['pdf_sha256']!=source_pin['pdf_sha256'] or unit['pdf_pages']!=2:raise Stop('probe source differs from exact frozen WI')
        if unit['channel']!='native' or unit['scope'] not in ('full_notice','slice','unknown') or type(unit['native_page_map_known']) is not bool or type(unit['pdf_pages']) is not int or unit['pdf_pages']<1:raise Stop('source field types/scope violation')
        paths={}
        for kind,cap in [('pdf',25000000),('text',2000000)]:
            rel=unit[kind+'_path']
            if not isinstance(rel,str) or Path(rel).is_absolute():raise Stop('source relative path required')
            path=(manifest.parent/rel).resolve()
            expected_path=(ROUND.parent/'round8/sources/documents/doc-92211b8c7ba0'/('input.pdf' if kind=='pdf' else 'native.txt')).resolve()
            if path!=expected_path or not path.is_file() or path.stat().st_size>cap:raise Stop('source path/byte cap violation')
            want=unit[kind+'_sha256']
            if not isinstance(want,str) or not re.fullmatch(r'[a-f0-9]{64}',want) or sha(path.read_bytes())!=want:raise Stop('source hash violation')
            paths[kind]=path
        actual=len(PdfReader(str(paths['pdf'])).pages)
        if actual!=unit['pdf_pages']:raise Stop('actual PDF page count differs')
        pages+=actual
        if pages>2:raise Stop('two actual PDF-page cap exceeded')
        text=paths['text'].read_bytes().decode('utf-8')
        source=dict(document_id=unit['document_id'],channel=unit['channel'],scope=unit['scope'],source_text=text,source_text_sha256=unit['text_sha256'],pdf_pages=actual,page_map_known=unit['native_page_map_known'])
        if sha(j.encode(source))!=source_pin['source_descriptor_sha256']:raise Stop('source descriptor differs from frozen R8')
        pin=j.loads((ROOT/'input-pin.json').read_bytes())
        if unit['retained_inputs']!=pin['files']:raise Stop('retained input manifest differs')
        retained={}
        for name,item in pin['files'].items():
            path=Path(item['path']).resolve();expected=(ROUND.parent/('round8-evidence-table' if name=='wire_stronger_request' else 'round8-contract-probe')/'execution/run/documents/doc-92211b8c7ba0').resolve()
            if not path.is_relative_to(expected) or sha(path.read_bytes())!=item['sha256']:raise Stop('retained original input bytes drift')
            retained[name]=j.loads(path.read_bytes())
        assembled=p.assemble(source,retained['assembled']['inventory']);common=p.verification_payload(source,assembled)
        if retained['source']!=source or assembled!=retained['assembled'] or common!=retained['common_payload'] or common['payload_sha256']!=pin['payload_sha256'] or assembled['inventory_sha256']!=pin['inventory_sha256'] or sha(j.encode(assembled['record']))!=pin['record_sha256']:raise Stop('original record/source/assembly/payload differs')
        plans,restoration,originals=requests(source,assembled)
        if originals!=retained['wire_stronger_request']:raise Stop('original wire request mechanics changed')
        rows.append(dict(unit=unit,source=source,assembled=assembled,common=common,plans=plans,restoration=restoration,source_errors=p.source_errors(source)))
    return rows

def uncalled(reason):return {arm:dict(status='not_started',called=False,payload_sha256=None,source_coverage_complete=False,reason=reason) for arm in ('jev','stronger')}
def initial(doc):return dict(document_id=doc['unit']['document_id'],runtime_gate='not_started',gate_reasons=['scheduled_not_dispatched'],inventory_sha256=None,record_sha256=None,payload_sha256=None,provider_service_error=False,failure=None,review_reasons=[],arms=uncalled('scheduled not dispatched'))

def validate_observation(value):
    module=load('stronger_only_observation',ROOT/'observation.py');module.validate_observed(value)

def ledger_raw_reported(folder):
    if not (folder/'response.body').exists():return 0
    try:
        value=j.loads((folder/'response.body').read_bytes()).get('usage',{}).get('cost')
        import math
        return value if type(value) in (int,float) and math.isfinite(value) and value>=0 else 0
    except (Stop,ValueError,TypeError,AttributeError):return 0

def audit_failure_receipts(observed,out):
    """Independently resolve observation evidence hashes to exact retained ledger facts, read-only."""
    out=Path(out).resolve();ledger_root=out/'operations'
    def require(ok,message):
        if not ok:raise Stop('failure receipt audit: '+message)
    operations={}
    for folder in ledger_root.iterdir():
        if (folder/'identity.json').exists():
            meta=j.loads((folder/'identity.json').read_bytes());require(meta['operation_id'] not in operations,'duplicate operation identity');operations[meta['operation_id']]=(folder,meta)
    for document in observed['documents']:
        failure=document['failure']
        if failure is None:continue
        directory=out/'documents'/document['document_id']
        matches=[path for path in directory.glob('*.json') if sha(path.read_bytes())==failure['evidence_sha256']]
        require(len(matches)==1,'evidence missing or ambiguous');receipt=j.loads(matches[0].read_bytes())
        require(all(receipt.get(k)==failure[k] for k in ('stage','kind','intent_recorded','operation_id','http_status')),'observation/receipt fields disagree')
        expected_id=document['document_id']+'-'+failure['stage']
        if not failure['intent_recorded']:
            require(failure['operation_id'] in (None,expected_id),'pause operation identity')
            pair=operations.get(expected_id);require(not pair or not (pair[0]/'intent.json').exists(),'no-intent pause has durable intent')
            require(failure['kind'] in ('budget_stop','operator_pause','local_error'),'no-intent failure kind')
            continue
        require(failure['operation_id']==expected_id and expected_id in operations,'failed/completed operation identity')
        folder,meta=operations[expected_id];require(receipt.get('ledger_folder')==str(folder.relative_to(out)),'receipt ledger folder differs')
        names=('intent.json','status.json','stop.json','result.json')
        actual={name:sha((folder/name).read_bytes()) for name in names if (folder/name).exists()}
        require(receipt.get('operation_artifact_hashes')==actual,'referenced artifact bytes differ')
        require((folder/'intent.json').exists() and (folder/'stop.json').exists(),'attempted failure/stop lacks durable intent/cause')
        intent=j.loads((folder/'intent.json').read_bytes());require(all(intent.get(k)==v for k,v in meta.items()) and intent.get('automatic_retry') is False,'intent differs from operation binding')
        require(meta['kind']==failure['stage'] and meta['identity']['document_id']==document['document_id'],'stage/document binding mismatch')
        require(meta['request_sha256']==sha((folder/'request.json').read_bytes()) and meta['pins_sha256']==sha((out/'pins.json').read_bytes()),'request/pins digest mismatch')
        stop=j.loads((folder/'stop.json').read_bytes())['state']
        status=j.loads((folder/'status.json').read_bytes()) if (folder/'status.json').exists() else None
        if status:require(status['response_sha256']==sha((folder/'response.body').read_bytes()),'response digest mismatch')
        if failure['kind']=='http_error':require(stop=='provider_HTTP_error' and status and status['http_status']==failure['http_status'] and status['http_status']!=200 and 'result.json' not in actual,'HTTP cause/status mismatch')
        elif failure['kind']=='transport_uncertain':require(stop=='uncertain_POST' and not (folder/'response.body').exists() and 'result.json' not in actual,'uncertain cause has completed response')
        elif failure['kind']=='invalid_response':require(stop in ('invalid_response_or_usage','oversize_or_invalid_response','credential_echo_response') and 'result.json' not in actual,'invalid response cause mismatch')
        elif failure['kind']=='budget_stop':
            require(stop=='observed_budget_exceeded' and status and status['http_status']==200 and 'result.json' in actual,'budget stop lost successful operation')
            raw=(folder/'response.body').read_bytes();parse=a.parse_or
            require(parse(raw)==j.loads((folder/'result.json').read_bytes()),'budget completed native result differs')
            charge=PRIOR_DEBIT+sum(max(j.loads((f/'intent.json').read_bytes())['reserved_nominal_usd'],j.loads((f/'result.json').read_bytes()).get('observed_cost_usd',0) if (f/'result.json').exists() else 0,ledger_raw_reported(f)) for f,_ in operations.values() if (f/'intent.json').exists())
            require(charge>2 and receipt.get('budget_charge_usd')==charge,'budget receipt differs from charged operations')
        else:require(failure['kind']=='local_error','unknown failure kind')
    return True

def observation_snapshot(out,documents,ledger):
    result=dict(schema_version='round8-stronger-cap-probe.observed.v1',documents=documents)
    validate_observation(result)
    audit_failure_receipts(result,out)
    raw=sanitize_input(result,ledger.keys.values());put(out/('observed-'+sha(raw)+'.json'),raw)
    return result

def run(manifest,source_root,freeze,out,*,live=False,authorization=None,source_labels_freeze_sha256=None,max_new=1,budget=2.0,keys=None,transport=None):
    if type(budget) not in (int,float) or budget!=2.0 or type(max_new) is not int or not 0<=max_new<=1:raise Stop('fixed runtime caps invalid')
    prior=verify_prior_debit();impl=verify_implementation(freeze);docs=load_sources(manifest,source_root)
    plan=dict(documents=len(docs),PDF_pages=sum(d['unit']['pdf_pages'] for d in docs),max_nominal_reserved_usd=MAX_RESERVATION,prior_budget_debit_usd=PRIOR_DEBIT,prior_cost_reporting=prior['reporting'],aggregate_nominal_max_usd=PRIOR_DEBIT+MAX_RESERVATION,live=live,production_eligible=False,action_ready=False)
    validate_observation(dict(schema_version='round8-stronger-cap-probe.observed.v1',documents=[initial(d) for d in docs]))
    if not live:return {**plan,'source_validation':[dict(document_id=d['unit']['document_id'],errors=d['source_errors']) for d in docs]}
    if not authorization or not isinstance(source_labels_freeze_sha256,str) or not re.fullmatch(r'[a-f0-9]{64}',source_labels_freeze_sha256):raise Stop('live requires new authorization and source-label freeze binding')
    expected=dict(schema_version='round8-stronger-cap-probe.live-authorization.v1',implementation_sha256=sha(Path(freeze).read_bytes()),manifest_sha256=sha(Path(manifest).read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256=source_labels_freeze_sha256,nominal_budget_usd=2.0,**auth_scope())
    if j.loads(Path(authorization).read_bytes())!=expected:raise Stop('authorization differs from code/source/label/budget pins')
    if transport is None:transport=load('round8_provider_transport',ROOT/'provider_transport.py').post_once
    pins=dict(implementation=impl,manifest_sha256=expected['manifest_sha256'],source_root=str(Path(source_root).resolve()),documents=[d['unit'] for d in docs],budget=budget,prior_budget_debit_usd=PRIOR_DEBIT,prior_debit_sha256=sha((ROOT/'prior-debit.json').read_bytes()),authorization_sha256=sha(Path(authorization).read_bytes()),source_labels_freeze_sha256=source_labels_freeze_sha256)
    out=Path(out);out.mkdir(parents=True,exist_ok=True);keys=keys or {};terminals=[initial(d) for d in docs]
    with (out/'runner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger=Ledger(out,pins,max_new=max_new,budget=budget,keys=keys,transport=transport)
        put(out/'plan.json',sanitize_input(plan,keys.values()))
        stopped=False;paused=False;budget_stopped=False;budget_receipt_hash=None
        for index,doc in enumerate(docs):
            terminal=terminals[index];ident=terminal['document_id'];folder=out/'documents'/ident;folder.mkdir(parents=True,exist_ok=True)
            # Rebuild completed terminals through retained provider parses; put enforces byte-identical resume.
            def budget_stop():
                nonlocal budget_stopped,budget_receipt_hash
                matches=[item for item in (out/'operations').iterdir() if (item/'identity.json').exists() and j.loads((item/'identity.json').read_bytes())['operation_id']==current_id]
                op=matches[0]
                receipt=dict(stage=current_stage,kind='budget_stop',intent_recorded=True,operation_id=current_id,http_status=None,completed_operation_id=current_id,ledger_folder=str(op.relative_to(out)),operation_artifact_hashes={name:sha((op/name).read_bytes()) for name in ('intent.json','status.json','stop.json','result.json')},budget_charge_usd=ledger.totals()['budget_charge_usd'])
                raw=sanitize_input(receipt,keys.values());put(folder/('budget-stop-'+sha(raw)+'.json'),raw);budget_receipt_hash=sha(raw);budget_stopped=True
                failure={k:receipt[k] for k in ('stage','kind','intent_recorded','operation_id','http_status')};failure['evidence_sha256']=sha(raw)
                terminal.update(runtime_gate='postresponse_budget_stop',gate_reasons=['reported_budget_overrun_after_completed_operation'],failure=failure)

            def retain():put(folder/'terminal.json',sanitize_input(terminal,keys.values()))
            current_stage='stronger';current_id=ident+'-stronger'
            try:
                source=doc['source'];assembled=doc['assembled'];common=doc['common'];plans=doc['plans'];restoration=doc['restoration']
                put(folder/'source.json',sanitize_input(source,keys.values()));put(folder/'assembled.json',sanitize_input(assembled,keys.values()));put(folder/'common-payload.json',sanitize_input(common,keys.values()));put(folder/'restoration.json',sanitize_input(restoration,keys.values()))
                terminal.update(inventory_sha256=assembled['inventory_sha256'],record_sha256=p.sha(p.canonical(assembled['record'])),payload_sha256=common['payload_sha256'],review_reasons=assembled['validation']['review_reasons'])
                for arm in ('stronger',):
                    put(folder/(arm+'-admission.json'),plans[arm]['admission']);put(folder/(arm+'-request.json'),sanitize_input(plans[arm]['body'],keys.values()))
                denied=[arm+': '+plans[arm]['admission']['reason'] for arm in ('stronger',) if not plans[arm]['admission']['admitted']]
                if denied:terminal.update(runtime_gate='request_size_review',gate_reasons=denied);retain();continue
                terminal.update(runtime_gate='stronger_verification_completed',gate_reasons=[])
                identity=dict(document_id=ident,payload_sha256=common['payload_sha256'],record_sha256=terminal['record_sha256'],wire_payload_sha256=restoration['wire_sha256'])
                for arm in ('stronger',):
                    current_stage=arm;current_id=ident+'-'+arm
                    parse=a.parse_or
                    response=ledger.operation(current_id,arm,plans[arm]['body'],parse,identity=identity,reserve=plans[arm]['admission']['reservation_usd'])
                    checked=p.validate_verdict(source,assembled,response['structured']);put(folder/'stronger-validation.json',checked);valid=checked['valid'];errors=checked['errors']
                    labels=normalized.stronger_labels(checked['normalized_verdict']) if valid else {k:'uncertain' for k in normalized.CRITERIA}
                    judgment=normalized.terminal_arm(arm,labels,assembled,valid=valid,errors=errors,explanations=arm=='stronger')
                    terminal['arms'][arm]=dict(status=judgment['status'],called=True,payload_sha256=common['payload_sha256'],source_coverage_complete=valid,reason='native provider judgment and deterministic guards',judgment=judgment)
                    put(folder/('progress-after-'+arm+'.json'),sanitize_input(terminal,keys.values()))
                    if ledger.totals()['budget_charge_usd']>2:
                        budget_stop();break
                retain()
                if budget_stopped:break
            except Pause as error:
                kind='budget_stop' if 'budget' in str(error) else 'operator_pause'
                receipt=dict(stage=current_stage,kind=kind,intent_recorded=False,operation_id=current_id,http_status=None,reason=str(error))
                evidence=sanitize_input(receipt,keys.values());put(folder/('pause-'+sha(evidence)+'.json'),evidence)
                failure={k:receipt[k] for k in ('stage','kind','intent_recorded','operation_id','http_status')};failure['evidence_sha256']=sha(evidence)
                terminal.update(runtime_gate='operation_pause',gate_reasons=['safe_operation_boundary_cap'],failure=failure);paused=True;break
            except (Stop,a.Stop):
                matches=[item for item in (out/'operations').iterdir() if (item/'identity.json').exists() and j.loads((item/'identity.json').read_bytes())['operation_id']==current_id]
                op=matches[0] if matches else None;called=bool(op and (op/'intent.json').exists())
                stop=j.loads((op/'stop.json').read_bytes()) if op and (op/'stop.json').exists() else {}
                status=j.loads((op/'status.json').read_bytes()) if op and (op/'status.json').exists() else {}
                state=stop.get('state');kind='http_error' if state=='provider_HTTP_error' else 'transport_uncertain' if state=='uncertain_POST' else 'invalid_response' if state in ('invalid_response_or_usage','oversize_or_invalid_response','credential_echo_response') else 'local_error'
                http=status.get('http_status') if kind=='http_error' else None
                receipt=dict(stage=current_stage,kind=kind,intent_recorded=called,operation_id=current_id if called else None,http_status=http,ledger_folder=str(op.relative_to(out)) if op else None,operation_artifact_hashes={name:sha((op/name).read_bytes()) for name in ('intent.json','status.json','stop.json') if op and (op/name).exists()})
                evidence=sanitize_input(receipt,keys.values());put(folder/('failure-'+sha(evidence)+'.json'),evidence)
                failure={k:receipt[k] for k in ('stage','kind','intent_recorded','operation_id','http_status')};failure['evidence_sha256']=sha(evidence)
                terminal.update(gate_reasons=['provider_operation_latched_stop' if called else 'local_operation_stop'],provider_service_error=kind=='http_error',failure=failure)
                if not called:terminal['runtime_gate']='operation_pause'
                elif current_stage=='inventory':terminal['runtime_gate']='inventory_failed'
                else:
                    terminal['runtime_gate']='verification_failed'
                    terminal['arms'][current_stage]=dict(status='failed',called=True,payload_sha256=terminal['payload_sha256'],source_coverage_complete=False,reason='provider operation latched stop; inspect durable operation metadata')
                if called:retain();stopped=True
                else:paused=True
                break

        observed=observation_snapshot(out,terminals,ledger)
        result={**plan,'state':'stopped_budget' if budget_stopped else 'stopped_provider_operation' if stopped else 'paused_at_operation_boundary' if paused else 'completed','totals':ledger.totals(),'observed_sha256':sha(j.encode(observed)),'budget_stop_evidence_sha256':budget_receipt_hash}
        put(out/('snapshot-'+sha(j.encode(result))+'.json'),result)
        if not stopped and not paused and not budget_stopped:put(out/'completed.json',dict(documents=terminals,totals=ledger.totals(),production_eligible=False,action_ready=False))
        return result

def main():
    cli=argparse.ArgumentParser();cli.add_argument('--prepare-implementation',type=Path)
    for name in ('manifest','source-root','freeze','output','authorization'):cli.add_argument('--'+name,type=Path)
    cli.add_argument('--source-labels-freeze-sha256');cli.add_argument('--live',action='store_true');cli.add_argument('--max-new',type=int,default=1)
    args=cli.parse_args()
    try:
        if args.prepare_implementation:put(args.prepare_implementation,code_pins());print('Stronger-cap implementation pins saved; prior evidence verified; no credentials/provider calls.');return
        if not all((args.manifest,args.source_root,args.freeze,args.output)):raise Stop('missing paths')
        keys={'openrouter':os.environ.get('OPENROUTER_API_KEY')} if args.live else {}
        result=run(args.manifest,args.source_root,args.freeze,args.output,live=args.live,authorization=args.authorization,source_labels_freeze_sha256=args.source_labels_freeze_sha256,max_new=args.max_new,keys=keys)
        print(j.encode(result).decode())
        if result.get('state') in ('stopped_provider_operation','stopped_budget'):raise Stop('provider operation stopped')
    except Exception:cli.exit(1,'Stronger-cap stopped; inspect durable nonsecret artifacts; no automatic retries.\n')
if __name__=='__main__':main()
