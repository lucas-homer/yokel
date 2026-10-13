#!/usr/bin/env python3
"""Offline R7 development replay. Prior observed inputs are immutable, never fresh accuracy data."""
import copy,hashlib,importlib.util,io,json,socket,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT.parent
PYTHON='/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def prior_hashes():return {str(f.relative_to(BENCH)):digest(f) for d in BENCH.glob('round[1-6]') for f in d.rglob('*') if f.is_file() and '__pycache__' not in str(f)}
def main():
    before=prior_hashes()
    def audit_guard(event,args):
        if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):
            raise RuntimeError('network/process disabled in offline replay')
        if event=='open' and isinstance(args[0],(str,bytes)):
            name=str(args[0]).lower()
            if any(part in name for part in ('/.env','/library/keychains/','/.aws/')) or Path(name).name in ('credentials','credentials.json'):
                raise RuntimeError('credential path disabled in offline replay')
    sys.addaudithook(audit_guard)
    socket.socket=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('network disabled in offline replay'))
    runtime=load('r7_runtime_replay',ROOT/'runtime/run_pipeline.py');p=runtime.p
    baseline=load('r6_pipeline_historical',BENCH/'round6/pipeline/pipeline.py')
    controls=[];log=io.StringIO()
    for folder,pattern in [('pipeline','test_pipeline.py'),('runtime','offline_checks.py'),('protocol','test_evaluate.py')]:
        oldpath=sys.path[:];sys.path.insert(0,str(ROOT/folder))
        # Pipeline fixtures depend on their local module; explicitly bind R7 for the test scope.
        previous=sys.modules.get('pipeline');sys.modules['pipeline']=p
        try:
            suite=unittest.defaultTestLoader.discover(str(ROOT/folder),pattern=pattern)
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
            controls.append(dict(name=folder+'_public_interface_controls',tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)))
        finally:
            sys.path[:]=oldpath
            if previous is None:sys.modules.pop('pipeline',None)
            else:sys.modules['pipeline']=previous
    origin=BENCH/'round6/execution/run/documents'
    authored=[];historical=[];inputs={str(f.relative_to(BENCH)):digest(f) for f in (BENCH/'round6/pipeline/pipeline.py',BENCH/'round6/runtime/provider_adapters.py',BENCH/'round6/runtime/run_pipeline.py',BENCH/'round6/protocol/evaluate.py')};admissions={}
    manual={
      'doc-de09ce82c4c7':{'route_header_address':['30 West Spring Street, L3','Columbus, Ohio 43215-2256']},
      'doc-7be63f24299e':{'r1':['William H. Green Building','Level 2, Room 2','30 W. Spring Street','Columbus, OH 43215'],'r2':['orally']},
      'doc-03d522cbc19e':{'r2':['Microsoft Teams','263 051 550 032 470','Ss9xo3gS'],'r3':['+1 603-931-4944,,468731372#','468 731 372#'],'r8':['Aron Johnson','Legal Coordinator','29 Hazen Drive','PO Box 95','Concord, NH 03302']}}
    for ident,components in manual.items():
        source_path=origin/ident/'source.json';assembled_path=origin/ident/'assembled.json'
        source=json.loads(source_path.read_text());retained=json.loads(assembled_path.read_text());raw=retained['inventory']
        inputs[str(source_path.relative_to(BENCH))]=digest(source_path);inputs[str(assembled_path.relative_to(BENCH))]=digest(assembled_path)
        old=baseline.assemble(source,raw);expected=retained['validation']['errors']
        historical.append(dict(document_id=ident,errors=old['validation']['errors'],same_errors=old['validation']['errors']==expected,record_null=old['record'] is None,raw_inventory_sha256=baseline.sha(baseline.canonical(raw))))
        migrated=copy.deepcopy(raw);migrated['schema_version']='round7.source_inventory.v1';migrated['alternative_groups']=[]
        changes=[];groups={}
        for route in migrated['routes']:
            literal=route.pop('literal');group=route.pop('alternative_group');route['alternative_group_id']=group;route['description']=None
            literals=components.get(route['id'],[literal])
            route['components']=[dict(id=route['id']+'-component-'+str(i),kind='activity' if value=='orally' else 'endpoint',literal=value,evidence=copy.deepcopy(route['evidence'])) for i,value in enumerate(literals)]
            if route['id'] in components:changes.append(dict(route=route['id'],original_literal=literal,authored_components=literals))
            if ident=='doc-7be63f24299e' and group=='hearing_modes':
                route['alternative_group_id']=None
                if route['id']=='r1':route['role']='other'
                else:route['description']=literal
                changes.append(dict(route=route['id'],change='Authored mixed-level hearing relation removed from alternatives; explicitly uncertain below.'))
            elif group:groups.setdefault(group,[]).append(route)
        purpose={'hearing_access':'hearing_access','hearing_help':'hearing_help','copies_questions_accessibility':'copies_questions_accessibility'}
        for gid,members in groups.items():
            shared=members[0]['event_ids'];evidence=[]
            for member in members:
                for ev in member['evidence']:
                    if ev not in evidence:evidence.append(ev)
            # Only help phone-or-email and explicit OH presentation/postal-email context are source-resolved authored controls.
            association='uncertain' if gid in ('hearing_access','copies_questions_accessibility','written_materials') else 'source_resolved'
            migrated['alternative_groups'].append(dict(id=gid,purpose=purpose.get(gid,'submission'),route_ids=[r['id'] for r in members],event_ids=shared,requirement_ids=[],association=association,evidence=evidence))
            changes.append(dict(group=gid,association=association,change='Authored role-purpose group; semantic interchangeability not inferred from exact endpoint quotes.'))
        if ident=='doc-7be63f24299e':
            migrated['uncertainties'].append(dict(id='dev-hearing-modes',kind='association',description='Development fixture keeps mixed venue/presentation relation unresolved; original group not certified.',event_ids=['e1'],route_ids=['r1','r2'],requirement_ids=[],identity_ids=[],evidence=copy.deepcopy(migrated['routes'][1]['evidence'])))
        fixture=dict(kind='authored_R6_migration_development_only',document_id=ident,source=source,inventory=migrated,origin_hashes={str(source_path.relative_to(BENCH)):digest(source_path),str(assembled_path.relative_to(BENCH)):digest(assembled_path)},authored_changes=changes,accuracy_claim=False)
        out=p.assemble(source,migrated);fixture['assembled']=out
        put(ROOT/'development/fixtures'/('authored-'+ident+'.json'),fixture)
        authored.append(dict(document_id=ident,valid=out['validation']['valid'],errors=out['validation']['errors'],review_reasons=out['validation']['review_reasons'],facts=sum(1 for _ in p.all_items(migrated)),fixture_sha256=digest(ROOT/'development/fixtures'/('authored-'+ident+'.json'))))
        if out['validation']['valid']:admissions[ident]={stage:item['admission'] for stage,item in runtime.requests(source,out).items()}
    ky=origin/'doc-9998d72f5aba/source.json';source=json.loads(ky.read_text());inputs[str(ky.relative_to(BENCH))]=digest(ky)
    ky_result=runtime.simulate(source,None,lambda *args:(_ for _ in ()).throw(AssertionError('KY must not dispatch')))
    admissions['doc-9998d72f5aba']=ky_result['admission']
    # Feed actual adapter outputs directly through evaluator, without rewriting arm statuses.
    evaluator=load('r7_evaluator_replay',ROOT/'protocol/evaluate.py')
    gate_runs=[ky_result]
    for h in historical:
        s=json.loads((origin/h['document_id']/'source.json').read_text());inv=json.loads((origin/h['document_id']/'assembled.json').read_text())['inventory']
        # R6 raw version is rejected by R7, preserving an honest assembly gate.
        gate_runs.append(runtime.simulate(s,inv,lambda stage,body:inv))
    observed=dict(schema_version='round7.observed.v1',documents=[x['observed'] for x in gate_runs],costs={})
    evaluator.validate_observed(observed)
    schedule=dict(schema_version='round7.schedule.v1',documents=[dict(document_id=d['document_id'],pdf_sha256=hashlib.sha256(d['document_id'].encode()).hexdigest(),pdf_pages=1,state='development',stratum='general') for d in observed['documents']])
    # Empty authored universe is solely a gate-schema/denominator control, never the real notice truth.
    truth=dict(schema_version='round7.truth.v1',documents=[dict(document_id=d['document_id'],pdf_sha256=d['pdf_sha256'],scope_status='complete',all_pages_viewed=True,universe_complete=True,reviewer='authored_empty_gate_universe_development_only',exclusions=['All semantic notice scoring excluded from this schema-only control'],domains={k:'absent' for k in evaluator.CATEGORIES},units=[],acceptance_blockers=[]) for d in schedule['documents']])
    audit=dict(schema_version='round7.matching-audit.v1',reviewer='authored_schema_only_development_control',documents=[])
    gate_report=evaluator.evaluate(schedule,truth,audit,observed)
    put(ROOT/'development/fixtures/gate-integration.json',dict(kind='schema_only_development_not_source_truth',observed=observed,schedule=schedule,truth=truth,audit=audit,evaluation=gate_report))
    after=prior_hashes();unchanged=before==after
    control_ok=all(x['passed'] for x in controls) and all(x['same_errors'] and x['record_null'] for x in historical) and sum(len(x['errors']) for x in historical)==18 and all(x['valid'] for x in authored) and ky_result['observed']['runtime_gate']=='request_size_review' and not ky_result['synthetic_dispatches'] and unchanged
    report=dict(schema_version='round7.offline_development_report.v1',passed=control_ok,scope='offline development only; no improved model extraction or accuracy claim',public_interface_controls=controls,historical_R6_replay=historical,authored_migrations=authored,admission=admissions,gate_integration=dict(runtime_gates=gate_report['runtime_gates'],arms=gate_report['arms'],scheduled_notices=gate_report['scheduled_notices']),network_disabled=True,credential_access=False,network_process_credential_guard='Python audit hook plus blocked socket construction' ,provider_calls=0,production_eligible=False,action_ready=False,prior_round_hashes_unchanged_during_replay=unchanged,prior_files_hashed=len(before),input_hashes=inputs,command='PYTHONDONTWRITEBYTECODE=1 '+PYTHON+' '+str(Path(__file__).resolve()))
    (ROOT/'development/test-output.txt').write_text(log.getvalue())
    put(ROOT/'development/results.json',report)
    artifacts={str(f.relative_to(ROOT)):digest(f) for folder in ('pipeline','runtime','protocol','development') for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in str(f) and f.name not in ('manifest.json','results.json','test-output.txt')}
    put(ROOT/'development/manifest.json',dict(schema_version='round7.development_manifest.v1',development_only=True,spec_sha256=digest(ROOT/'SPEC.md'),artifact_hashes=artifacts,input_hashes=inputs,prior_round_tree_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),results_sha256=digest(ROOT/'development/results.json'),test_output_sha256=digest(ROOT/'development/test-output.txt')))
    print(json.dumps(dict(passed=control_ok,tests=sum(x['tests'] for x in controls),historical_errors=sum(len(x['errors']) for x in historical),authored_assembly=[x['valid'] for x in authored],KY_gate=ky_result['observed']['runtime_gate'],prior_files_unchanged=len(before)),indent=2))
    if not control_ok:raise SystemExit(1)
if __name__=='__main__':main()
