"""Reproducible offline-only verifier; writes confined to this runtime, never protocol/review/prior files."""
import contextlib,hashlib,io,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('offline network/process forbidden')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=os.fsdecode(args[0]);lower=name.lower()
        if '/library/keychains/' in lower or '/.env' in lower or '/.aws/' in lower or Path(lower).name in ('credentials','credentials.json'):raise RuntimeError('credential path forbidden')
        if args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            if not Path(name).resolve().is_relative_to(ROOT):raise RuntimeError('write outside owned runtime forbidden')
sys.addaudithook(guard)
import common as c,request,response,semantic
stream=io.StringIO()
with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT),pattern='test_runtime.py'))
(ROOT/'test-output.txt').write_text(stream.getvalue())
if not result.wasSuccessful():print(stream.getvalue());raise SystemExit(1)
fixtures=c.read(c.PROTO/'development-fixtures.json')['fixtures'];endorsed=c.read(c.ROUND/'approved-development-audits.json');pending=c.read(c.PROTO/'offline-audit-review.json');outcomes=[]
for audit in c.read(c.PROTO/'development-audit-inputs.json')['audits']:
    family,variant_id=audit['audit_id'].split('/');f=next(x for x in fixtures if x['fixture_id']==family);v=next(x for x in f['variants'] if x['id']==variant_id);text=v.get('source_text_override',f['source_text']);checked=semantic.aggregate(text,v['record'],audit,endorsed)
    outcomes.append({'audit_id':audit['audit_id'],'source_sha256':c.file_hash_bytes(text.encode()),'record_sha256':c.digest(v['record']),'audit_sha256':c.digest(audit),'source_rows':len(audit['source_dispositions']),'semantic_field_rows':len(semantic.fields(v['record'])),'endorsed_result':checked,'pending_result':semantic.aggregate(text,v['record'],audit,pending)['semantic_status'],'manually_reviewed_development_input':True,'model_observation':False})
built=request.wi();raw_cases=c.read(c.PROTO/'response-fixtures.json')['cases'];checks=[{'case':row['id'],'expected':row['expected_structural_valid'],'actual':response.validate_response(row['raw_json'],request.ASSEMBLED['source'],request.ASSEMBLED)['structural_valid']} for row in raw_cases]
report={'schema_version':'round9.runtime.offline-report.v1','tests':result.testsRun,'passed':True,'protocol_READY_sha256':c.READY_SHA,'approved_audits_sha256':c.APPROVAL_SHA,'read_only_dependency_files_verified':c.verify_inputs(),'raw_response_cases':checks,'request':{'schema_bytes':built['schema_bytes'],'baseline_schema_bytes':len(c.encode(request.BASELINE['response_format']['json_schema']['schema'])),'schema_delta_bytes':built['schema_bytes']-len(c.encode(request.BASELINE['response_format']['json_schema']['schema'])),'baseline_body_bytes':len(c.encode(request.BASELINE)),'body_delta_bytes':built['body_bytes']-len(c.encode(request.BASELINE)),'neutral_instruction_bytes':len(('\n'+request.SIZES['added_neutral_instruction']).encode()),'body_bytes':built['body_bytes'],'estimate':built['estimate'],'guard':built['guard'],'headroom':built['guard']-built['estimate'],'body_sha256':c.digest(built['body']),'schema_sha256':c.digest(built['body']['response_format']['json_schema']['schema']),'expanded_schema_sha256':c.digest(response.expand(built['body']['response_format']['json_schema']['schema'])),'provider_compatibility':'unverified','user_source_record_evidence_unchanged':True},'semantic_results':outcomes,'provider_calls':0,'credentials_read':False,'approvals_created':False,'semantic_discovery_performed':False,'model_accuracy_measured':False,'production_eligible':False,'action_ready':False,'audit_mutation_note':'Mutated audits use existing unchanged external endorsements and fail closed; no mutation receives a newly synthesized approval.','log_sha256':c.file_hash(ROOT/'test-output.txt')}
(ROOT/'REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'tests':result.testsRun,'raw_cases':len(checks),'semantic_status_counts':{s:sum(x['endorsed_result']['semantic_status']==s for x in outcomes) for s in ('complete_supported','not_complete','unverified')},'request_estimate':built['estimate'],'provider_calls':0}))
