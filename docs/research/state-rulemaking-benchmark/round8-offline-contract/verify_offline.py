"""Guarded offline verification and reproducible complete-body sizing report."""
import contextlib,hashlib,io,json,os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
def guard(event,args):
    if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','subprocess.Popen','os.system'):raise RuntimeError('offline: network/process forbidden')
    if event=='open' and isinstance(args[0],(str,bytes)):
        flags=args[2]
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            path=Path(os.fsdecode(args[0])).resolve()
            if not path.is_relative_to(ROOT) or path.is_relative_to(ROOT/'review'):raise RuntimeError('offline: writes confined to owned new root')
sys.addaudithook(guard)
import candidate as c
import fixtures as f
stream=io.StringIO()
with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_candidate.py');result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
(ROOT/'test-output.txt').write_text(stream.getvalue())
if not result.wasSuccessful():
    print(stream.getvalue());raise SystemExit(1)
rows=[]
for name,source,inventory,label in f.examples():
    before=c.a.encode(inventory);assembled,bodies=c.paired_bodies(source,inventory);assert before==c.a.encode(inventory)
    comparisons={str(cap):c.paired_gate(bodies,cap) for cap in (35000,40000)}
    for report in comparisons.values():
        for stage,receipt in report['admission'].items():
            receipt['margin']=receipt['cap']-receipt['estimate']
            receipt['state_longest_margin']=receipt['state_longest_cap']-receipt['state_longest_estimate'] if stage=='jev' else None
            receipt['body_codepoints']=len(c.a.encode(bodies[stage]).decode())
    rows.append({'fixture':name,'provenance':label,'observed':False,'semantic_acceptance':False,'source_text_sha256':source['source_text_sha256'],'inventory_sha256':c.a.sha(before),'record_sha256':c.a.sha(c.a.encode(assembled['record'])),'payload_sha256':c.p.verification_payload(source,assembled)['payload_sha256'],'full_source_in_each_arm':True,'paired_evidence_equal':True,'guards_change_body_bytes':False,'comparison':comparisons})
source,_=c.observed();old=c.a.loads((c.BASE/'round8-cap-probe/execution/run/operations/inventory-8f69eccb0e19f2d6e43cc72d/request.json').read_bytes());new=c.inventory_body(source)
oldestimate=c.a.estimate_input(old);newestimate=c.a.estimate_input(new)
report={'schema_version':'round8-offline-contract.report.v1','tests':result.testsRun,'passed':True,'provider_calls':0,'credentials_read':False,'source_truth_decoded':False,'network_process_guard':True,'write_guard':'only owned new root; review excluded','immutable_input_files_verified':c.verify_inputs(),'prompt_delta_sha256':c.a.sha((ROOT/'prompt-delta.txt').read_bytes()),'inventory_request':{'old_body_sha256':c.a.sha(c.a.encode(old)),'candidate_body_sha256':c.a.sha(c.a.encode(new)),'changed_fields':['messages[0].content (append exact prompt-delta.txt)'],'old_estimate':oldestimate,'candidate_estimate':newestimate,'estimate_delta':newestimate-oldestimate,'old_reservation_usd':oldestimate*.000002+12288*.000010,'candidate_admission':c.admission(new,'inventory'),'reservation_delta_usd':(newestimate-oldestimate)*.000002,'schema_unchanged':True,'source_user_payload_unchanged':True,'model_provider_reasoning_output_cap_unchanged':True},'fixtures':rows,'candidate_budget_by_stronger_guard':{str(cap):c.budget(cap) for cap in (35000,40000)},'unmeasured':['candidate prompt model generation','generation consistency improvement','semantic correctness/completeness improvement','unseen-source generalization','actual provider token counts or context capacity for candidate bodies','new generated output size/cost'],'production_eligible':False,'action_ready':False,'log_sha256':c.a.sha((ROOT/'test-output.txt').read_bytes())}
(ROOT/'REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'passed':True,'tests':result.testsRun,'fixtures':len(rows),'provider_calls':0,'inputs':report['immutable_input_files_verified']}))
