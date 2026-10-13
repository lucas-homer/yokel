"""Read-only owner-test rerun plus independent synthetic adapter controls."""
import copy,hashlib,importlib.util,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[5]
HERE=REPO/'docs/research/state-rulemaking-benchmark/round8-stronger-cap-probe/execution/service-account'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def guard(event,args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):raise RuntimeError('independent offline guard')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=str(args[0]).lower()
        if '/library/keychains/' in name or '/.aws/' in name or Path(name).name in ('credentials','credentials.json'):raise RuntimeError('credential paths forbidden')
sys.addaudithook(guard)
a=load('adapter_independent',HERE/'adapter.py')
def main():
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()}
    owner=load('adapter_owner_tests',HERE/'test_adapter.py');log=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromModule(owner);result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite);assert result.wasSuccessful(),log.getvalue()
    checks=[]
    def check(name,ok):checks.append({'name':name,'passed':bool(ok)});assert ok,name
    def denied(name,fn):
        try:fn()
        except a.Denied:check(name,True)
        else:check(name,False)
    with tempfile.TemporaryDirectory(prefix='yokel-adapter-review-') as temp:
        base=Path(temp).resolve();root=base/'round8-stronger-cap-probe';here=root/'execution/service-account';here.mkdir(parents=True);(root/'runtime').mkdir();(root/'sources').mkdir()
        old=base/'round8/execution';old.mkdir(parents=True);original=base/'round8-evidence-table/runtime/decoding-instructions.txt';original.parent.mkdir(parents=True);original.write_text('synthetic instruction')
        def put(path,value):path.write_text(json.dumps(value))
        for name in ('A','S'):put(root/'execution'/f'freeze-{name}.json',dict(created_utc='synthetic',description='fixture',files=[]))
        freeze_b=old/'freeze-B.json';put(freeze_b,dict(created_utc='synthetic',description='fixture',files=[]))
        implementation=root/'runtime/implementation.json';manifest=root/'sources/source-inputs.READY.json';auth=root/'execution/live-authorization.json'
        put(implementation,{});put(manifest,{});put(root/'runtime/prior-debit.json',{});put(root/'runtime/input-pin.json',dict(payload_sha256='a'*64,record_sha256='b'*64));(here/'adapter.py').write_text('synthetic only')
        python=Path(sys.executable).resolve();pins={str(p):a.digest(p) for p in (python,here/'adapter.py')}
        put(here/'dependencies.json',dict(schema_version='round8-stronger-cap-probe.service-dependencies.v1',files=pins,dependency_scope='synthetic'))
        binding=dict(schema_version='round8-stronger-cap-probe.service-binding.v1',implementation_sha256=a.digest(implementation),manifest_sha256=a.digest(manifest),dependencies_sha256=a.digest(here/'dependencies.json'),freeze_B_sha256=a.digest(freeze_b),**{'freeze_'+n+'_sha256':a.digest(root/'execution'/f'freeze-{n}.json') for n in ('A','S')})
        authorization=dict(schema_version='round8-stronger-cap-probe.live-authorization.v1',implementation_sha256=binding['implementation_sha256'],manifest_sha256=binding['manifest_sha256'],source_labels_frozen_before_outputs=True,source_labels_freeze_sha256=binding['freeze_B_sha256'],nominal_budget_usd=2.0,prior_budget_debit_usd=.542976718,prior_debit_sha256=a.digest(root/'runtime/prior-debit.json'),max_new_operations=1,inventory_calls=0,jev_calls=0,stronger_calls=1,stronger_completion=8192,stronger_input_guard=40000,jev_total_input_guard=64000,jev_state_longest_guard=32000,wire_version='round8-evidence-table.wire.v1',decoding_instructions_sha256=a.digest(original),input_pin_sha256=a.digest(root/'runtime/input-pin.json'),original_payload_sha256='a'*64,original_record_sha256='b'*64)
        def rebind(value):
            put(auth,value);binding['authorization_sha256']=a.digest(auth);put(here/'binding.json',binding)
        rebind(authorization)
        # Actual isolated interpreter flags are required by this harness invocation.
        with patch.multiple(a,ROOT=root,HERE=here,PYTHON=python,REFERENCE_FREEZE=freeze_b,MANIFEST=manifest,IMPLEMENTATION=implementation,AUTHORIZATION=auth,RUN=root/'execution/run'):
            verified=a.verify_inputs();check('complete-synthetic-binding-accepted',verified['prior_budget_debit_usd']==.542976718 and verified['max_new_operations']==1)
            for name,field,value in [('extra-operation','max_new_operations',2),('jev-enabled','jev_calls',1),('inventory-enabled','inventory_calls',1),('larger-budget','nominal_budget_usd',3),('prior-debit-reset','prior_budget_debit_usd',0),('output-cap-changed','stronger_completion',4096)]:
                changed=copy.deepcopy(authorization);changed[field]=value;rebind(changed);denied(name,lambda:a.verify_inputs())
            rebind(authorization)
            (here/'adapter.py').write_text('drift');denied('dependency-drift-rejected',lambda:a.verify_inputs());(here/'adapter.py').write_text('synthetic only')
            a.receipt('synthetic-receipt.json',{'state':'original'})
            try:a.receipt('synthetic-receipt.json',{'state':'overwritten'})
            except FileExistsError:check('receipt-exclusive-preserves-original',json.loads((here/'synthetic-receipt.json').read_bytes())=={'state':'original'})
            else:check('receipt-exclusive-preserves-original',False)
            class FailingRuntime:
                def run(self,*args,**kw):
                    if kw.get('live'):raise RuntimeError('synthetic-secret-must-not-leak')
                    return {}
            with patch.object(a,'verify_inputs',return_value=verified),patch.object(a,'runtime_module',return_value=FailingRuntime()),patch.dict(os.environ,{'OPENROUTER_API_KEY':'synthetic-only'},clear=True):denied('live-failure-stops',a.live_initial)
            check('failure-receipts-do-not-leak-errors',all(b'synthetic-secret-must-not-leak' not in p.read_bytes() for p in here.glob('live-*.json')))
            check('failure-does-not-authorize-retry',json.loads((here/'live-stop.json').read_bytes())['automatic_retry'] is False)
    check('owner-files-remained-unchanged',before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()})
    print(json.dumps({'status':'passed','owner_tests_rerun':result.testsRun,'independent_checks':len(checks),'checks':checks,'native_builds':0,'real_credentials_read':False,'provider_calls':0,'live_intent_in_real_scope':False,'source_hashes':{p.name:h for p,h in before.items()}},indent=2))
if __name__=='__main__':main()
