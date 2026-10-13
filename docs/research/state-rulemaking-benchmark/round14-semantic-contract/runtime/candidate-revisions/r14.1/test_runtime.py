"""Offline supplied compact outputs; validates guards/durability, not discovery."""
import ast,copy,importlib.util,json,socket,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import adapter as a
c=a.c;k=a.k
SECRET='synthetic-r14-key'
RELEASE_SHA='ca845ca805dbbb5fd428a06d63c735b4a326aa09100dcaeb0e913859069032a2'
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source,cls.plan,cls.prior=a.prepare_offline()
    def value(self):
        # Synthetic structural output only; no claim these assertions describe the source.
        units=[]
        for i,kind in enumerate((4,5,0,7,3,6,8,8),1):
            units.append(dict(i=i,k=kind,s='Supplied synthetic assertion.',m=0,c='',d=[1] if kind==5 else [],b=[1,3] if kind==7 else [],e=['s1'],q=0,r=''))
        return {'v':'r14.1','h':k.protocol().source_hash(self.source),'t':c.digest(self.plan['table']),'z':'END','u':units}
    def native(self,value=None):return {'model':'openai/gpt-6.1-sol','provider':'OpenAI','choices':[{'finish_reason':'stop','message':{'content':c.encode(self.value() if value is None else value).decode()}}],'usage':{'prompt_tokens':100,'completion_tokens':100,'cost':.0012,'prompt_tokens_details':{'cache_write_tokens':90}}}
    def run_case(self,modify=None,transport=None,real_integrity=False):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);run=Path(tmp.name)/'run';calls=[]
        def fake(body,key):
            calls.append(body);obj=self.native();status=200
            if modify:status,obj=modify(obj,run)
            return status,obj if isinstance(obj,bytes) else c.encode(obj)
        try:result=a.execute_once(run,self.source,self.plan,SECRET,transport or fake,integrity_check=a.offline_integrity if real_integrity else lambda *_:None)
        except c.Denied:result=None
        return run,calls,result
    def denied(self,fn,*args):
        with self.assertRaises((ValueError,KeyError,TypeError)):fn(*args)
    def test_01_preflight_exact_source_guard_baseline_and_no_credentials(self):
        class Forbidden(dict):
            def get(self,*args):raise AssertionError('credential')
        with patch.object(a.os,'environ',Forbidden()),patch.object(socket.socket,'connect',side_effect=AssertionError('network')):source,plan,prior=a.prepare_offline()
        self.assertEqual(prior['prior_nanousd'],1705990718);self.assertEqual(prior['baseline_rows'],7063);self.assertEqual(plan['guarded_bytes'],c.read(HERE/'input-pins.json')['guarded_bytes']);self.assertEqual(len(plan['table']['rows']),len(c.read(HERE/'source-span-table.json')['rows']));self.assertEqual(a.PRIOR+a.RESERVE,1905990718)
        user=c.strict(plan['body']['messages'][1]['content']);self.assertEqual(set(user),{'source_text','source_text_sha256','span_table','span_table_sha256'});self.assertEqual(user['source_text'],source);self.assertEqual(k.protocol().reconstruct(source,plan['table']).encode(),source.encode())
    def test_02_success_charge_ledger_completion_concordance_and_no_resume(self):
        run,calls,result=self.run_case(real_integrity=True);self.assertEqual(len(calls),1);self.assertIsNotNone(result);self.assertEqual(result['unit_count'],8)
        ledger=c.read(run/'ledger.json');done=c.read(run/'completed.json');self.assertEqual(ledger['state'],'charge_recorded');self.assertEqual(done['state'],'validated_frozen');self.assertEqual(done['files']['ledger.json'],c.file_hash(run/'ledger.json'));self.assertEqual(ledger['budget_charge_nanousd'],result['budget_charge_nanousd']);self.assertEqual(ledger['cumulative_budget_charge_nanousd'],1905990718);self.assertFalse((run/'stop.json').exists())
        compact=c.read(run/'validated.json');expanded=c.read(run/'expanded.json');self.assertEqual(k.protocol().contract(expanded,self.source,self.plan['table']),compact);self.assertEqual((run/'content.body').read_bytes(),c.encode(compact));self.assertFalse(expanded['production_eligible']);self.assertEqual(expanded['source_inventory_completeness'],'unverified')
        for name,want in done['files'].items():self.assertEqual(c.file_hash(run/name),want)
        with self.assertRaises(FileExistsError):a.execute_once(run,self.source,self.plan,SECRET,lambda *_:self.fail('resume'))
    def test_03_native_and_structural_failures_keep_raw_usage_and_content(self):
        kinds=('http','length','refusal','tools','model','provider','usage','cost','invalid','duplicate','nonfinite','missing_terminal','wrong_source','capacity')
        for kind in kinds:
            def modify(obj,run):
                if kind=='http':return 429,obj
                if kind=='length':obj['choices'][0]['finish_reason']='length'
                elif kind=='refusal':obj['choices'][0]['message']['refusal']='yes'
                elif kind=='tools':obj['choices'][0]['message']['tool_calls']=[{}]
                elif kind=='model':obj['model']='other'
                elif kind=='provider':obj['provider']='other'
                elif kind=='usage':obj['usage']['prompt_tokens']=True
                elif kind=='cost':del obj['usage']['cost']
                elif kind in ('invalid','duplicate','nonfinite'):obj['choices'][0]['message']['content']={'invalid':'{}','duplicate':'{"v":1,"v":2}','nonfinite':'{"x":1e999}'}[kind]
                else:
                    v=self.value()
                    if kind=='missing_terminal':del v['z']
                    elif kind=='wrong_source':v['h']='0'*64
                    else:v['u']=[dict(i=i+1,k=8,s='Supplied synthetic assertion.',m=0,c='',d=[],b=[],e=['s1'],q=0,r='') for i in range(160)]
                    obj['choices'][0]['message']['content']=c.encode(v).decode()
                return 200,obj
            with self.subTest(kind=kind):
                run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertTrue((run/'response.body').exists());self.assertTrue((run/'content.body').exists());self.assertEqual(c.read(run/'ledger.json')['budget_charge_nanousd'],a.RESERVE);self.assertEqual(c.read(run/'stop.json')['state'],'failed_or_uncertain');self.assertFalse((run/'completed.json').exists())
    def test_04_transport_uncertainty_no_retry_secret_exception_not_logged(self):
        calls=[]
        def fail(*_):calls.append(1);raise RuntimeError(SECRET)
        run,_,result=self.run_case(transport=fail);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertEqual(c.read(run/'ledger.json')['budget_charge_nanousd'],200000000)
        for p in run.iterdir():
            if p.is_file():self.assertNotIn(SECRET.encode(),p.read_bytes())
        with self.assertRaises(FileExistsError):a.execute_once(run,self.source,self.plan,SECRET,fail)
    def test_05_budget_refusal_and_request_overflow_no_POST(self):
        with patch.object(a,'CEILING',a.PRIOR+a.RESERVE-1):run,calls,result=self.run_case()
        self.assertIsNone(result);self.assertEqual(calls,[]);self.assertFalse((run/'intent.json').exists())
        self.denied(k.build,'x'*40000)
        plan=copy.deepcopy(self.plan);plan['guarded_bytes']=40001
        with patch.object(self,'plan',plan):run,calls,result=self.run_case()
        self.assertIsNone(result);self.assertEqual(calls,[])
    def test_06_reported_and_rate_overruns_remain_charged(self):
        for method in ('reported','rate'):
            def modify(obj,run):
                if method=='reported':obj['usage']['cost']=.6000000001
                else:obj['usage']['completion_tokens']=60000
                return 200,obj
            with self.subTest(method=method):
                run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertGreater(c.read(run/'ledger.json')['cumulative_budget_charge_nanousd'],a.CEILING);self.assertTrue((run/'result.json').exists());self.assertFalse((run/'completed.json').exists())
        self.assertEqual(a.cost_nano(.0000000001),1);self.assertEqual(a.recoverable(c.encode({'usage':{'cost':.3,'prompt_tokens':200000,'completion_tokens':0}})),400000000);self.assertEqual(a.recoverable(b'bad'),200000000)
    def test_07_unsafe_or_oversize_raw_not_retained(self):
        for raw in (c.encode(self.native({'key':SECRET})),b'x'*2000001):
            run,_,result=self.run_case(transport=lambda *_:(200,raw));self.assertIsNone(result);self.assertFalse((run/'response.body').exists());self.assertEqual(c.read(run/'ledger.json')['budget_charge_nanousd'],a.RESERVE)
    def test_08_receipt_write_failures_latched_and_charge_ledger_never_claims_success(self):
        real=a.put
        for name in ('request.json','span-table.json','intent.json','response.body','status.json','content.body','validated.json','expanded.json','result.json','completed.json'):
            def fail(path,*args,**kwargs):
                if Path(path).name==name:raise OSError(SECRET)
                return real(path,*args,**kwargs)
            with self.subTest(receipt=name),patch.object(a,'put',side_effect=fail):run,calls,result=self.run_case()
            self.assertIsNone(result);self.assertFalse((run/'completed.json').exists());self.assertEqual(c.read(run/'stop.json')['state'],'failed_or_uncertain');self.assertEqual(c.read(run/'ledger.json')['state'],'charge_recorded');self.assertEqual(c.read(run/'ledger.json')['budget_charge_nanousd'],200000000);self.assertLessEqual(len(calls),1)
            with self.assertRaises(FileExistsError):a.execute_once(run,self.source,self.plan,SECRET,lambda *_:self.fail('resume'))
    def test_09_expanded_evidence_tampering_rejected(self):
        checked=k.validate_response(c.encode(self.value()).decode(),'stop',self.source,self.plan['table']);expanded=checked['expanded'];expanded['units'][0]['evidence'][0]['quote']+='x';self.denied(k.protocol().contract,expanded,self.source,self.plan['table'])
        real=a.put
        def tamper(path,data,*args):
            if Path(path).name=='expanded.json':data=c.encode(expanded)
            return real(path,data,*args)
        with patch.object(a,'put',side_effect=tamper):run,calls,result=self.run_case()
        self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertFalse((run/'completed.json').exists())
    def test_10_table_or_request_tamper_before_dispatch_rejected(self):
        real=a.put
        for name in ('request.json','span-table.json'):
            def tamper(path,data,*args):
                if Path(path).name==name:data=b'{}'
                return real(path,data,*args)
            with self.subTest(file=name),patch.object(a,'put',side_effect=tamper):run,calls,result=self.run_case()
            self.assertIsNone(result);self.assertEqual(calls,[])
    def test_11_compact_closed_codes_references_defaults_and_capacity(self):
        for change in ('missing_c','missing_m','boolean','unknown_span','bad_hash','dep_cycle','wrong_role','relationship_members','unknown_force','uncertainty_reason','extra','missing_terminal'):
            v=self.value();u=v['u'][0]
            if change=='missing_c':del u['c']
            elif change=='missing_m':del u['m']
            elif change=='boolean':u['i']=True
            elif change=='unknown_span':u['e']=['s999']
            elif change=='bad_hash':v['t']='0'*64
            elif change=='dep_cycle':u['d']=[1]
            elif change=='wrong_role':v['u'][1]['d']=[3]
            elif change=='relationship_members':v['u'][3]['b']=[2]
            elif change=='unknown_force':u['m']=5
            elif change=='uncertainty_reason':u['r']='unexpected'
            elif change=='extra':u['other']='x'
            else:v['z']=''
            self.denied(k.validate_response,c.encode(v).decode(),'stop',self.source,self.plan['table'])
        v=self.value();checked=k.validate_response(c.encode(v).decode(),'stop',self.source,self.plan['table']);self.assertEqual(checked['expanded']['units'][0]['applicability'],'');self.assertEqual(checked['expanded']['units'][0]['uncertainty_reason'],'');self.assertEqual(checked['expanded']['units'][0]['modality'],'informational')
    def test_12_unicode_line_table_and_original_empty_values_roundtrip(self):
        source='😀a\r\nrepeat\nrepeat\n\nlast e\u0301';table=k.protocol().span_table(source);v={'v':'r14.1','h':k.protocol().source_hash(source),'t':c.digest(table),'z':'END','u':[dict(i=160,k=8,s='Synthetic assertion.',m=5,c='',d=[],b=[],e=['s2','s3'],q=3,r='Function unresolved.')]} 
        result=k.validate_response(c.encode(v).decode(),'stop',source,table);self.assertEqual(k.protocol().contract(result['expanded'],source,table),v);self.assertEqual(k.protocol().reconstruct(source,table),source);self.assertEqual([e['occurrence'] for e in result['expanded']['units'][0]['evidence']],[1,2]);self.assertEqual(result['expanded']['units'][0]['id'],160)
        table['rows'][0][1]=True;self.denied(k.protocol().validate_table,source,table)
    def test_13_source_only_builder_no_annotations_or_kind_exclusions(self):
        user=c.strict(k.build(self.source)['body']['messages'][1]['content']);self.assertEqual(user['source_text'],self.source);self.assertEqual(set(user),{'source_text','source_text_sha256','span_table','span_table_sha256'});self.assertNotEqual(k.build(self.source+'\nsource-only-addition')['request_sha256'],self.plan['request_sha256'])
        for code in (0,1,2,3,4,6,8):
            v={'v':'r14.1','h':k.protocol().source_hash(self.source),'t':c.digest(self.plan['table']),'z':'END','u':[dict(i=1,k=code,s='Supplied atomic assertion.',m=0,c='',d=[],b=[],e=['s1'],q=0,r='')]};self.assertEqual(len(k.validate_response(c.encode(v).decode(),'stop',self.source,self.plan['table'])['expanded']['units']),1)
    def test_14_strict_JSON_and_closed_schema_keywords(self):
        for raw in ('{"x":1,"x":2}','{"x":{"a":1,"a":2}}','{"x":NaN}','{"x":1e999}','{} trailing'):self.denied(k.protocol().strict_load,raw)
        s=k.protocol().schema(self.source,self.plan['table']);s['properties']['u']['items']['pattern']='unknown';self.denied(c.check_schema,s)
    def test_15_missing_or_changed_approval_source_and_protocol_fail_closed(self):
        real=c.file_hash
        for target in (c.PROTO/'READY.json',c.PROTO/'compact.py',c.SOURCE_PATH):
            def drift(path):return '0'*64 if Path(path)==target else real(path)
            with self.subTest(path=target.name),patch.object(c,'file_hash',side_effect=drift):self.denied(a.offline_integrity,self.source)
        realread=c.read
        def absent(path):
            if Path(path)==c.ROUND/'implementation-release.json':raise FileNotFoundError()
            return realread(path)
        with patch.object(c,'read',side_effect=absent),self.assertRaises(FileNotFoundError):a.preflight()
    def test_16_observed_imports_and_historical_reservation_pins(self):
        pins=c.read(HERE/'dependency-pins.json')['files']|c.read(HERE/'code-pins.json')['files'];root=a.PYTHON.parent.parent
        modules=list(sys.modules.values())+[k.protocol()]
        for module in modules:
            path=getattr(module,'__file__',None)
            if path:
                p=Path(path).resolve()
                if p.is_relative_to(root) or p.is_relative_to(HERE) or p==c.PROTO/'compact.py':self.assertIn(str(p),pins);self.assertEqual(c.file_hash(p),pins[str(p)])
        self.assertLess(len(pins)+60,10000);self.assertEqual(a.HISTORICAL_RESERVE,161920000);self.assertEqual(a.RESERVE,200000000);self.assertEqual(a.recoverable(b'{}',a.HISTORICAL_RESERVE),161920000)
    def test_17_synthetic_unsigned_job_unchanged_pure_validator(self):
        release=HERE.parents[4]/'tools/research-credentials-stable/release.py';self.assertEqual(c.file_hash(release),RELEASE_SHA);tree=ast.parse(release.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','encode','digest','in_roots','validate'}];self.assertEqual(len(nodes),5);namespace={'Path':Path,'json':json,'hashlib':c.hashlib,'time':time};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(release),'exec'),namespace)
        spec=importlib.util.spec_from_file_location('r14_prep',HERE/'prepare_bindings.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep);core=c.read(c.BENCH/'runner-stability-review/deployment/core.json');self.assertEqual(core['python_path'],str(a.PYTHON));captured={};real=prep.digest
        def capture(path,value):captured[str(path)]=copy.deepcopy(value)
        def digest(path):
            if str(path) in captured:return c.digest(captured[str(path)])
            if Path(path)==c.ROUND/'live-authorization.json':return c.digest({'synthetic_authorization':True})
            return real(path)
        with patch.object(prep,'put',side_effect=capture),patch.object(prep,'digest',side_effect=digest),patch.dict(namespace,{'digest':digest}):
            summary=prep.prepare('synthetic-offline-scope',int(time.time())+3600,HERE/'test_runtime.py');proposal=captured[str(HERE/'UNSIGNED-JOB-PROPOSAL.json')];namespace['validate'](core,proposal)
        self.assertEqual(proposal['job_id'],'round14-semantic-contract-initial');self.assertEqual(proposal['budget'],{'prior_nanousd':1705990718,'reservation_nanousd':200000000,'ceiling_nanousd':2000000000});self.assertEqual(proposal['provider_variables'],['OPENROUTER_API_KEY']);self.assertFalse(summary['signed_job_created']);self.assertLess(summary['dependency_files'],10000)
    def test_18_live_entry_requires_missing_primary_late_bindings(self):
        with self.assertRaises((ValueError,FileNotFoundError)):a.verify_live_bindings()
        with patch.object(c,'file_hash',side_effect=lambda p:'0'*64):fields=a.authorization_fields()
        self.assertEqual(fields['max_new_operations'],1);self.assertEqual(fields['reservation_nanousd'],200000000);self.assertEqual(fields['scope_calls'],0);self.assertEqual(fields['mapping_calls'],0);self.assertFalse(fields['candidate_or_reference_input'])
    def test_19_r13_debit_and_receipt_binding_tamper_rejected(self):
        real=c.read;target=c.BENCH/'round13-compact-inventory/execution/run/ledger.json'
        def drift(path):
            value=real(path)
            if Path(path)==target:value['budget_charge_nanousd']-=1
            return value
        with patch.object(c,'read',side_effect=drift):self.denied(a.verify_baseline)
        self.assertEqual(self.prior['historical_rounds'][-1],{'round':'round13-compact-inventory','budget_charge_nanousd':200000000,'state':'validated_frozen'})
    def test_20_source_ready_and_full_source_provenance_tamper_rejected(self):
        real=c.file_hash;target=c.ROUND/'source/READY.json'
        with patch.object(c,'file_hash',side_effect=lambda p:'0'*64 if Path(p)==target else real(p)):self.denied(a.read_source)
        pins=c.read(HERE/'input-pins.json');self.assertEqual(pins['source_ready_sha256'],c.SOURCE_READY_SHA)
        self.assertEqual(self.source.encode(),c.SOURCE_PATH.read_bytes());self.assertEqual(self.plan['body'],c.read(HERE/'source-request.json'))
        self.assertNotEqual(self.plan['body'],c.read(c.PROTO/'offline-request.json'))
        self.assertEqual(self.plan['table'],c.read(HERE/'source-span-table.json'))
        self.assertFalse(c.read(HERE/'CAPACITY.json')['output_headroom_established'])
if __name__=='__main__':unittest.main(verbosity=2)
