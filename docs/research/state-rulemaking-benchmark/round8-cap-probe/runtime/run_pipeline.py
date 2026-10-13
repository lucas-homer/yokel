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
    if set(lineage)!={'schema_version','files'} or lineage['schema_version']!='round8-cap-probe.frozen_lineage.v1':raise Stop('R7 lineage shape/version')
    expected=ROUND.parent/'round7'
    for name,want in lineage['files'].items():
        path=Path(name)
        if not any(path.resolve().is_relative_to((ROUND.parent/name).resolve()) for name in ('round6','round7','round8')) or sha(path.read_bytes())!=want:raise Stop('frozen R7 dependency drift')
    return load('round8_frozen_r7_helpers',expected/'runtime/run_pipeline.py')
normalized=verified_r7();p=normalized.p;a=normalized.a

PRIOR_DEBIT=.100166
LIMITS={**a.LIMITS,'documents':1,'PDF_pages':2,'inventory_calls':1,'Jev_calls':1,'stronger_calls':1,'inventory_completion':12288}
MAX_RESERVATION=2*35000*a.PRICES['prompt']+12288*a.PRICES['completion']+4096*a.PRICES['completion']+64000*a.PRICES['jev']
assert abs(MAX_RESERVATION-.306528)<1e-12 and PRIOR_DEBIT+MAX_RESERVATION<2

def verify_prior_debit():
    debit=j.loads((ROOT/'prior-debit.json').read_bytes());freeze=Path(debit['freeze_E_path'])
    if debit['prior_budget_debit_usd']!=PRIOR_DEBIT or debit['freeze_E_sha256']!='ef9891fca1a9aa6e0eeeafcdfee22d46b7d6dab8c79ff39099c3e00ef4f2c996' or sha(freeze.read_bytes())!=debit['freeze_E_sha256']:raise Stop('prior budget debit/freeze differs')
    frozen=j.loads(freeze.read_bytes())['files'];old=ROUND.parent/'round8'
    for row in frozen:
        path=(old/row['path']).resolve()
        if not path.is_relative_to(old.resolve()) or sha(path.read_bytes())!=row['sha256'] or path.stat().st_size!=row['bytes']:raise Stop('R8 freeze E bytes drift')
    intent=Path(debit['prior_intent_path'])
    if sha(intent.read_bytes())!=debit['prior_intent_sha256']:raise Stop('prior paid intent drift')
    value=j.loads(intent.read_bytes())
    if value['operation_id']!=debit['prior_operation_id'] or value['reserved_nominal_usd']!=PRIOR_DEBIT:raise Stop('prior debit does not match durable intent')
    if any((old/'execution/run/operations').glob('*/result.json')):raise Stop('prior parsed results changed')
    return debit

def requests(source,assembled=None):
    plans=normalized.requests(source,assembled)
    for stage,item in plans.items():
        body=item['body']
        if stage=='inventory':
            body['max_tokens']=12288
            estimate=a.estimate_input(body);allowed=estimate<=LIMITS['OR_input_estimate']
            item['admission']={**item['admission'],'body_sha256':sha(j.encode(body)),'body_utf8_bytes':len(j.encode(body)),'estimate':estimate,'admitted':allowed,'reason':None if allowed else 'OpenRouter input overlimit; no clipping','reservation_usd':estimate*a.PRICES['prompt']+12288*a.PRICES['completion'] if allowed else None}
    return plans

def code_pins():
    import importlib.metadata
    paths=[ROOT/x for x in ('run_pipeline.py','operations.py','provider_transport.py','offline_checks.py','verify_offline.py','INTERFACE.md','README.md','lineage.json','source-pin.json','prior-debit.json')]
    paths.extend(ROUND/'execution/service-account'/x for x in ('adapter.py','prepare_manifest.py','test_adapter.py','README.md'))
    lineage=j.loads((ROOT/'lineage.json').read_bytes());files={str(path.resolve()):sha(path.read_bytes()) for path in paths}
    files.update(lineage['files'])
    prior=verify_prior_debit()
    return dict(schema_version='round8-cap-probe.implementation.v1',code=files,limits=LIMITS,models={'inventory':a.MODEL,'stronger':a.MODEL,'jev':a.j.JEV_MODEL},OR_canonical_slug=a.CANONICAL_MODEL,prices=a.PRICES,nominal_max_reservation_usd=MAX_RESERVATION,aggregate_nominal_with_prior_usd=PRIOR_DEBIT+MAX_RESERVATION,prior_debit_sha256=sha((ROOT/'prior-debit.json').read_bytes()),python_version=platform.python_version(),pypdf_version=importlib.metadata.version('pypdf'),R7_lineage_sha256=sha((ROOT/'lineage.json').read_bytes()),production_eligible=False,action_ready=False)

def verify_implementation(path):
    verified_r7();value=j.loads(Path(path).read_bytes())
    if value!=code_pins():raise Stop('implementation/code/model/schema pins changed')
    return value

def load_sources(manifest,root):
    from pypdf import PdfReader
    root=Path(root).resolve();manifest=Path(manifest).resolve()
    if not manifest.is_relative_to(root) or manifest.stat().st_size>100000:raise Stop('manifest path/size violation')
    value=j.loads(manifest.read_bytes());required={'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}
    if set(value)!={'schema_version','documents'} or value['schema_version']!='round8-cap-probe.sources.v1' or not isinstance(value['documents'],list) or not len(value['documents'])==1:raise Stop('strict source manifest shape/one-document cap')
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
        rows.append(dict(unit=unit,source=source,source_errors=p.source_errors(source)))
    return rows

def uncalled(reason):return {arm:dict(status='not_started',called=False,payload_sha256=None,source_coverage_complete=False,reason=reason) for arm in ('jev','stronger')}
def initial(doc):return dict(document_id=doc['unit']['document_id'],runtime_gate='not_started',gate_reasons=['scheduled_not_dispatched'],inventory_sha256=None,record_sha256=None,payload_sha256=None,provider_service_error=False,failure=None,review_reasons=[],arms=uncalled('scheduled not dispatched'))

def validate_observation(value):
    # R8 protocol owns real-provider failure and safe pause/unstarted extensions to R7 semantics.
    path=ROUND.parent/'round8/protocol/evaluate.py'
    if not path.exists():raise Stop('R8 observed contract not released')
    module=load('round8_observed_contract',path)
    module.validate_observed(value)


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
            raw=(folder/'response.body').read_bytes();parse=(lambda raw:a.parse_jev(raw,normalized.question_plan())) if failure['stage']=='jev' else a.parse_or
            require(parse(raw)==j.loads((folder/'result.json').read_bytes()),'budget completed native result differs')
            charge=PRIOR_DEBIT+sum(max(j.loads((f/'intent.json').read_bytes())['reserved_nominal_usd'],j.loads((f/'result.json').read_bytes()).get('observed_cost_usd',0) if (f/'result.json').exists() else 0) for f,_ in operations.values() if (f/'intent.json').exists())
            require(charge>2 and receipt.get('budget_charge_usd')==charge,'budget receipt differs from charged operations')
        else:require(failure['kind']=='local_error','unknown failure kind')
    return True

def observation_snapshot(out,documents,ledger):
    result=dict(schema_version='round8.observed.v1',documents=documents)
    validate_observation(result)
    audit_failure_receipts(result,out)
    raw=sanitize_input(result,ledger.keys.values());put(out/('observed-'+sha(raw)+'.json'),raw)
    return result

def run(manifest,source_root,freeze,out,*,live=False,authorization=None,source_labels_freeze_sha256=None,max_new=3,budget=2.0,keys=None,transport=None):
    if type(budget) not in (int,float) or budget!=2.0 or type(max_new) is not int or not 0<=max_new<=3:raise Stop('fixed runtime caps invalid')
    prior=verify_prior_debit();impl=verify_implementation(freeze);docs=load_sources(manifest,source_root)
    plan=dict(documents=len(docs),PDF_pages=sum(d['unit']['pdf_pages'] for d in docs),max_nominal_reserved_usd=MAX_RESERVATION,prior_budget_debit_usd=PRIOR_DEBIT,aggregate_nominal_max_usd=PRIOR_DEBIT+MAX_RESERVATION,live=live,production_eligible=False,action_ready=False)
    validate_observation(dict(schema_version='round8.observed.v1',documents=[initial(d) for d in docs]))
    if not live:return {**plan,'source_validation':[dict(document_id=d['unit']['document_id'],errors=d['source_errors']) for d in docs]}
    if not authorization or not isinstance(source_labels_freeze_sha256,str) or not re.fullmatch(r'[a-f0-9]{64}',source_labels_freeze_sha256):raise Stop('live requires new authorization and source-label freeze binding')
    expected=dict(schema_version='round8-cap-probe.live-authorization.v1',implementation_sha256=sha(Path(freeze).read_bytes()),manifest_sha256=sha(Path(manifest).read_bytes()),source_labels_frozen_before_outputs=True,source_labels_freeze_sha256=source_labels_freeze_sha256,nominal_budget_usd=2.0,prior_budget_debit_usd=PRIOR_DEBIT,prior_debit_sha256=sha((ROOT/'prior-debit.json').read_bytes()),max_new_operations=3,calls_per_stage=1,inventory_completion=12288)
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
            current_stage='inventory';current_id=ident+'-inventory'
            try:
                if doc['source_errors']:
                    terminal.update(runtime_gate='source_review',gate_reasons=doc['source_errors']);retain();continue
                source=doc['source'];put(folder/'source.json',sanitize_input(source,keys.values()))
                plans=requests(source);inv_req=plans['inventory'];put(folder/'inventory-admission.json',inv_req['admission']);put(folder/'inventory-plan.json',sanitize_input(p.inventory_request(source),keys.values()))
                if not inv_req['admission']['admitted']:
                    terminal.update(runtime_gate='request_size_review',gate_reasons=['inventory: '+inv_req['admission']['reason']]);retain();continue
                inventory=ledger.operation(current_id,current_stage,inv_req['body'],a.parse_or,identity=dict(document_id=ident,source_text_sha256=source['source_text_sha256'],stage='source_first'),reserve=inv_req['admission']['reservation_usd'])
                assembled=p.assemble(source,inventory['structured']);put(folder/'assembled.json',sanitize_input(assembled,keys.values()));terminal['inventory_sha256']=assembled['inventory_sha256']
                if not assembled['validation']['valid']:
                    terminal.update(runtime_gate='assembly_review',gate_reasons=assembled['validation']['errors'])
                    if ledger.totals()['budget_charge_usd']>2:budget_stop();retain();break
                    retain();continue
                common=p.verification_payload(source,assembled);put(folder/'common-payload.json',sanitize_input(common,keys.values()))
                terminal.update(record_sha256=p.sha(p.canonical(assembled['record'])),payload_sha256=common['payload_sha256'],review_reasons=assembled['validation']['review_reasons'])
                if ledger.totals()['budget_charge_usd']>2:budget_stop();retain();break
                plans=requests(source,assembled)
                for arm in ('jev','stronger'):
                    put(folder/(arm+'-admission.json'),plans[arm]['admission']);put(folder/(arm+'-request.json'),sanitize_input(plans[arm]['body'],keys.values()))
                denied=[arm+': '+plans[arm]['admission']['reason'] for arm in ('jev','stronger') if not plans[arm]['admission']['admitted']]
                if denied:terminal.update(runtime_gate='request_size_review',gate_reasons=denied);retain();continue
                terminal.update(runtime_gate='paired_verification_completed',gate_reasons=[])
                identity=dict(document_id=ident,payload_sha256=common['payload_sha256'],record_sha256=terminal['record_sha256'])
                for arm in ('jev','stronger'):
                    current_stage=arm;current_id=ident+'-'+arm
                    parse=(lambda raw:a.parse_jev(raw,normalized.question_plan())) if arm=='jev' else a.parse_or
                    response=ledger.operation(current_id,arm,plans[arm]['body'],parse,identity=identity,reserve=plans[arm]['admission']['reservation_usd'])
                    if arm=='jev':
                        labels={k:v['label'] if v['label'] is not None else 'uncertain' for k,v in response['answers'].items()};valid=True;errors=[]
                    else:
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
    cli.add_argument('--source-labels-freeze-sha256');cli.add_argument('--live',action='store_true');cli.add_argument('--max-new',type=int,default=3)
    args=cli.parse_args()
    try:
        if args.prepare_implementation:put(args.prepare_implementation,code_pins());print('Cap-probe code-only pins saved; no sources or credentials read.');return
        if not all((args.manifest,args.source_root,args.freeze,args.output)):raise Stop('missing paths')
        keys={'openrouter':os.environ.get('OPENROUTER_API_KEY'),'jev':os.environ.get('TYPESAFE_API_KEY')} if args.live else {}
        result=run(args.manifest,args.source_root,args.freeze,args.output,live=args.live,authorization=args.authorization,source_labels_freeze_sha256=args.source_labels_freeze_sha256,max_new=args.max_new,keys=keys)
        print(j.encode(result).decode())
        if result.get('state') in ('stopped_provider_operation','stopped_budget'):raise Stop('provider operation stopped')
    except Exception:cli.exit(1,'Cap-probe stopped; inspect durable nonsecret artifacts; no automatic retries.\n')
if __name__=='__main__':main()
