"""Offline synthetic lifecycle, codec, schema/isolation and annotated fixture guard regressions."""
import copy, importlib.util, json, socket, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a
c=a.c; k=a.k
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.text,cls.record,cls.planned,cls.prior=a.preflight()
    def inventory(self,text=None,n=1,heavy=False):
        text=self.text if text is None else text
        return {'schema_version':'round10.source-inventory.v1','source_text_sha256':k.source_hash(text),'units':[{'id':f'u{i+1:03}','kind':'fact','assertion':'x'*(360 if heavy else 20),'modality':'informational','applicability':'unconditional','uncertainty':'none','uncertainty_reason':'','required_unit_ids':[],'evidence':[{'quote':text[:80],'occurrence':1}]} for i in range(n)]}
    def mapping(self,inventory=None,record=None):
        inv=self.inventory() if inventory is None else inventory; record=self.record if record is None else record
        p=next(p for p,v in k.fields(record).items() if v not in (None,'',[],{}))
        return {'schema_version':'round10.source-mapping.v1','source_text_sha256':inv['source_text_sha256'],'record_sha256':c.digest(record),'inventory_sha256':c.digest(inv),'mappings':{u['id']:{'disposition':'matched','operative_pointers':[p],'reason':'Synthetic supplied mapping; not semantic discovery.'} for u in inv['units']}}
    def native(self,value):return {'model':'openai/gpt-6.1-sol','provider':'OpenAI','choices':[{'finish_reason':'stop','message':{'content':c.encode(value).decode()}}],'usage':{'prompt_tokens':100,'completion_tokens':100,'cost':.0012}}
    def run_case(self,inv=None,modify=None,transport=None):
        inv=self.inventory() if inv is None else inv; tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);run=Path(tmp.name)/'run';calls=[]
        def fake(body,key):
            calls.append(body); stage=len(calls); obj=self.native(inv if stage==1 else self.mapping(inv)); status=200
            if modify:status,obj=modify(stage,obj)
            return status,c.encode(obj)
        try: result=a.execute_once(run,self.text,self.record,self.planned,'synthetic-secret-key',transport or fake)
        except c.Denied:result=None
        return run,calls,result
    def test_check_isolation_and_frozen_request(self):
        class Forbidden(dict):
            def get(self,*args):raise AssertionError('credential')
        with patch.object(a.os,'environ',Forbidden()),patch.object(socket.socket,'connect',side_effect=AssertionError('network')):text,record,planned,prior=a.preflight()
        self.assertEqual(prior['prior_nanousd'],858310718);self.assertEqual(planned['body_bytes'],7650);self.assertEqual(set(c.strict(planned['body']['messages'][1]['content'])),{'source_text','source_text_sha256'})
        self.assertEqual(planned['body'],c.read(c.PROTO/'stage-a.offline-request.json'))
        self.assertEqual(planned,k.build_a(text));self.assertEqual(a.PRIOR+2*a.RESERVE,1182150718)
    def test_positive_two_stages_and_no_resume(self):
        run,calls,result=self.run_case();self.assertEqual(len(calls),2);self.assertEqual(result['validation']['mapping_status'],'all_inventoried_units_matched');self.assertEqual(result['validation']['source_inventory_completeness'],'unverified')
        self.assertTrue((run/'stage-a-freeze.json').exists());self.assertEqual(c.read(run/'ledger.json')['cumulative_budget_charge_nanousd'],1182150718)
        with self.assertRaises(FileExistsError):a.execute_once(run,self.text,self.record,self.planned,'synthetic-secret-key',lambda *_:self.fail('retry'))
    def test_failed_a_suppresses_b(self):
        for kind in ('http','length','refusal','tools','provider','model','usage','cost','invalid','duplicate'):
            def modify(stage,obj):
                status=200
                if kind=='http':status=429
                elif kind=='length':obj['choices'][0]['finish_reason']='length'
                elif kind=='refusal':obj['choices'][0]['message']['refusal']='yes'
                elif kind=='tools':obj['choices'][0]['message']['tool_calls']=[{}]
                elif kind=='provider':obj['provider']='other'
                elif kind=='model':obj['model']='other'
                elif kind=='usage':obj['usage']['prompt_tokens']=True
                elif kind=='cost':del obj['usage']['cost']
                elif kind=='invalid':obj['choices'][0]['message']['content']='{}'
                else:obj['choices'][0]['message']['content']='{"x":1,"x":2}'
                return status,obj
            with self.subTest(kind=kind):
                run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertFalse((run/'stage-b').exists());self.assertTrue((run/'stage-a/response.body').exists());self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],a.RESERVE)
    def test_transport_uncertain_latched(self):
        calls=[]
        def fail(*_):calls.append(1);raise RuntimeError('synthetic-secret-key')
        run,_,result=self.run_case(transport=fail);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],a.RESERVE)
        for p in run.rglob('*'):
            if p.is_file():self.assertNotIn(b'synthetic-secret-key',p.read_bytes())
        with self.assertRaises(FileExistsError):a.execute_once(run,self.text,self.record,self.planned,'synthetic-secret-key',fail)
    def test_b_failure_retains_both_reservations(self):
        def modify(stage,obj):return (500 if stage==2 else 200),obj
        run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(len(calls),2);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],2*a.RESERVE);self.assertTrue((run/'stage-a-freeze.json').exists())
    def test_a_budget_prevents_b_and_b_overrun_preserved(self):
        for stage,cost in ((1,1.1),(1,1.5),(2,1.1)):
            def modify(n,obj):
                if n==stage:obj['usage']['cost']=cost
                return 200,obj
            run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(len(calls),stage)
            self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],int(cost*1e9)+(a.RESERVE if stage==2 else 0))
            self.assertTrue((run/f'stage-{chr(96+stage)}/result.json').exists())
    def test_usage_charge_dominates_missing_cost(self):
        def modify(stage,obj):obj['usage'].update(prompt_tokens=300000,completion_tokens=100);del obj['usage']['cost'];return 429,obj
        run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],601000000)
        self.assertEqual(a.cost_nano(.0000000001),1)
        for v in (-1,True,None,float('nan')):
            with self.assertRaises(c.Denied):a.cost_nano(v)
    def test_b_guard_stop_preserves_a(self):
        inv=self.inventory(n=64,heavy=True);self.assertFalse(k.build_b(self.text,self.record,inv)['fits'])
        run,calls,result=self.run_case(inv);self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertFalse((run/'stage-b').exists());self.assertTrue((run/'stage-a-freeze.json').exists());self.assertFalse(c.read(run/'stage-b-preflight.json')['fits'])
    def test_a_guard_no_call(self):
        text='x'*40000;planned=k.build_a(text);self.assertFalse(planned['fits']);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);record=copy.deepcopy(self.record);record['source_text_sha256']=k.source_hash(text)
        with self.assertRaises(c.Denied):a.execute_once(Path(tmp.name)/'run',text,record,planned,'synthetic-key',lambda *_:self.fail('POST'))
    def test_strict_json(self):
        for raw in ('{"a":1,"a":2}','{"a":{"b":0,"b":1}}','{"a":1e999}','{"a":NaN}','{"a":Infinity}','{} trailing'):
            with self.assertRaises((ValueError,c.Denied)):c.strict(raw)
    def test_bounded_ref_expansion(self):
        s=k.a_schema(self.text);expanded=c.expand(s,s['$defs']);self.assertNotIn('$ref',c.encode(expanded).decode())
        for bad in ('external','sibling','cycle','keyword','unused'):
            v=copy.deepcopy(s);defs=copy.deepcopy(s['$defs'])
            if bad=='external':v['properties']['units']['items']={'$ref':'https://x'}
            elif bad=='sibling':v['properties']['units']['items']['type']='object'
            elif bad=='cycle':defs['e']={'$ref':'#/$defs/u'};v['$defs']=defs
            elif bad=='keyword':v['allOf']=[]
            else:defs['e']['ignored']=True;v['$defs']=defs
            with self.subTest(kind=bad),self.assertRaises(c.Denied):c.expand(v,defs)
    def test_inventory_bounds_and_dependency_checks(self):
        base=self.inventory(n=2)
        for bad in ('zero','many','duplicate','id','absent','self','cycle','dupdep','assertion','applicability','reason','quote','occ','bool','extra','source'):
            inv=copy.deepcopy(base);u=inv['units'][0]
            if bad=='zero':inv['units']=[]
            elif bad=='many':inv=self.inventory(n=65)
            elif bad=='duplicate':inv['units'][1]['id']=u['id']
            elif bad=='id':u['id']='u065'
            elif bad=='absent':u['required_unit_ids']=['u003']
            elif bad=='self':u['required_unit_ids']=['u001']
            elif bad=='cycle':u['required_unit_ids']=['u002'];inv['units'][1]['required_unit_ids']=['u001']
            elif bad=='dupdep':u['required_unit_ids']=['u002','u002']
            elif bad=='assertion':u['assertion']='  '
            elif bad=='applicability':u['applicability']='  '
            elif bad=='reason':u['uncertainty_reason']='why'
            elif bad=='quote':u['evidence'][0]['quote']='absent quote private canary'
            elif bad=='occ':u['evidence'][0]['occurrence']=10000
            elif bad=='bool':u['evidence'][0]['occurrence']=True
            elif bad=='extra':inv['completeness']='complete'
            else:inv['source_text_sha256']='0'*64
            with self.subTest(kind=bad),self.assertRaises(c.Denied):k.validate_a(self.text,inv)
    def test_span_unicode_overlap_and_invalid(self):
        for text,quote,occ in (('aaaa','aa',3),('😀e\u0301😀e\u0301','e\u0301',2),('x\r\nx\r\n','x\r\n',2),('"\\"\\','"\\',2)):
            inv=self.inventory(text);inv['units'][0]['evidence']=[{'quote':quote,'occurrence':occ}];wire=k.wire_encode(text,inv);self.assertEqual(k.wire_decode(text,wire,inv),inv)
        inv=self.inventory('aaaa');inv['units'][0]['evidence']=[{'quote':'aa','occurrence':2}];wire=k.wire_encode('aaaa',inv)
        for bad in ([True,2,1],[0,False,1],[0,2,True],[-1,2,1],[2,1,1],[0,0,1],[0,5,1],[0,2,0],[0,2,2],[0,2,4],[0,2],[0,2,1,7],[0.,2,1]):
            v=copy.deepcopy(wire);v['units'][0][-1]=[bad]
            with self.subTest(span=bad),self.assertRaises(c.Denied):k.wire_decode('aaaa',v,inv)
    def test_wire_alterations_rejected(self):
        inv=self.inventory();wire=k.wire_encode(self.text,inv)
        for bad in ('columns','width','envelope','hash','assertion','units','type','version'):
            w=copy.deepcopy(wire)
            if bad=='columns':w['columns']=list(reversed(w['columns']))
            elif bad=='width':w['units'][0].pop()
            elif bad=='envelope':w['extra']=1
            elif bad=='hash':w['source_text_sha256']='0'*64
            elif bad=='assertion':w['units'][0][2]='changed'
            elif bad=='units':w['units']=[]
            elif bad=='type':w['units'][0][7]='wrong'
            else:w['schema_version']='wrong'
            with self.subTest(kind=bad),self.assertRaises(c.Denied):k.wire_decode(self.text,w,inv)
    def test_operative_projection_and_pointer_invalid(self):
        p,fields=k.operative(self.record);self.assertEqual(p,c.read(c.PROTO/'stage-b.operative-record.json'));self.assertEqual(len(fields),310);self.assertEqual(len(k.identities(p)),70)
        inv=self.inventory();value=self.mapping(inv)
        for pointer in ('/events','/events/0','/events/0/id','/events/0/evidence','/coverage/rationale','/source_text','/events/999/phase','/events/00/phase','/events/0/description/x','/events/0/~2bad'):
            v=copy.deepcopy(value);v['mappings']['u001']['operative_pointers']=[pointer]
            with self.subTest(pointer=pointer),self.assertRaises(c.Denied):k.validate_b(self.text,self.record,inv,v)
    def test_mapping_keys_and_bindings(self):
        inv=self.inventory();v=self.mapping(inv)
        for bad in ('missing','extra','hash','source','record','duplicate','reason','empty','missing_pointer'):
            value=copy.deepcopy(v);m=value['mappings']['u001']
            if bad=='missing':value['mappings']={}
            elif bad=='extra':value['mappings']['u002']=copy.deepcopy(m)
            elif bad=='hash':value['inventory_sha256']='0'*64
            elif bad=='source':value['source_text_sha256']='0'*64
            elif bad=='record':value['record_sha256']='0'*64
            elif bad=='duplicate':m['operative_pointers']*=2
            elif bad=='reason':m['reason']=' '
            elif bad=='empty':m['operative_pointers']=[]
            else:m['disposition']='missing'
            with self.subTest(kind=bad),self.assertRaises(c.Denied):k.validate_b(self.text,self.record,inv,value)
    def test_uncertainty_and_dependency_precedence(self):
        inv=self.inventory(n=3);inv['units'][2]['required_unit_ids']=['u001'];value=self.mapping(inv)
        value['mappings']['u001']['disposition']='unknown';value['mappings']['u002']['disposition']='mismatched';value['mappings']['u003']['disposition']='mismatched'
        checked=k.validate_b(self.text,self.record,inv,value);self.assertEqual(checked['mapping_status'],'unverified');self.assertEqual(checked['effective_dispositions']['u003'],'unknown');self.assertIn('u002',checked['known_defects'])
        value['mappings']['u003']['disposition']='matched'
        with self.assertRaises(c.Denied):k.validate_b(self.text,self.record,inv,value)
        for field,val in (('uncertainty','source_ambiguous'),('modality','unknown')):
            i=self.inventory();i['units'][0][field]=val
            if field=='uncertainty':i['units'][0]['uncertainty_reason']='Scoped ambiguity'
            with self.assertRaises(c.Denied):k.validate_b(self.text,self.record,i,self.mapping(i))
    def test_credential_echo_and_oversize_not_retained(self):
        for huge in (False,True):
            def fake(*_):return 200,b'x'*2000001 if huge else c.encode(self.native({'echo':'synthetic-secret-key'}))
            run,_,result=self.run_case(transport=fake);self.assertIsNone(result);self.assertFalse((run/'stage-a/response.body').exists());self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],a.RESERVE)
    def test_frozen_a_tamper_suppresses_b(self):
        original=k.build_b
        def tamper(text,record,inv):
            for root in active:
                (root/'stage-a/content.body').write_bytes(b'changed')
            return original(text,record,inv)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);run=Path(tmp.name)/'run';active=[run];calls=[]
        def fake(*_):calls.append(1);return 200,c.encode(self.native(self.inventory()))
        with patch.object(k,'build_b',tamper),self.assertRaises(c.Denied):a.execute_once(run,self.text,self.record,self.planned,'synthetic-key',fake)
        self.assertEqual(len(calls),1);self.assertFalse((run/'stage-b').exists())
    def test_durable_write_failures_latch(self):
        original=a.put
        for target in ('response.body','status.json','validated.json','completed.json'):
            def fail(path,*args):
                if Path(path).name==target:raise OSError('synthetic-secret-key')
                return original(path,*args)
            with patch.object(a,'put',fail):run,calls,result=self.run_case()
            self.assertIsNone(result);self.assertEqual(len(calls),1);self.assertTrue((run/'stage-a/intent.json').exists());self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],a.RESERVE)
    def test_partial_intent_reserves_and_blocks_dispatch(self):
        original=a.put;tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);run=Path(tmp.name)/'run';calls=[]
        def broken(path,*args):
            if Path(path).name=='intent.json':Path(path).write_bytes(b'{partial');raise OSError('synthetic-key')
            return original(path,*args)
        with patch.object(a,'put',broken),self.assertRaises(c.Denied):a.execute_once(run,self.text,self.record,self.planned,'synthetic-key',lambda *_:calls.append(1))
        self.assertEqual(calls,[]);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],a.RESERVE);self.assertFalse(c.read(run/'stage-a/stop.json')['provider_calls_may_have_occurred'])
        with self.assertRaises(FileExistsError):a.execute_once(run,self.text,self.record,self.planned,'synthetic-key',lambda *_:self.fail('retry'))
    def test_missing_live_binding_before_credentials(self):
        with patch.object(a.os,'environ',{}),patch.object(a,'post_once',side_effect=AssertionError('POST')):
            with self.assertRaises((FileNotFoundError,c.Denied)):a.live_initial()
    def test_ten_existing_annotated_regressions_and_isolation(self):
        fixtures=c.read(c.BENCH/'round9-exact-id-completeness/protocol/development-fixtures.json')['fixtures'];count=0
        for family in fixtures:
            for variant in family['variants']:
                text=variant.get('source_text_override',family['source_text']);record=variant['record'];self.assertEqual(k.source_hash(text),record['source_text_sha256']);units=family['source_units']+variant.get('additional_source_units',[]);ids={u['source_unit_id']:f'u{n+1:03}' for n,u in enumerate(units)};oracle={o['source_unit_id']:o for o in variant['oracle_mapping']}
                # Explicit private fixture annotations, never runtime discovery or paid payloads.
                inv={'schema_version':'round10.source-inventory.v1','source_text_sha256':k.source_hash(text),'units':[]}
                for u in units:
                    name=u['source_unit_id'];o=oracle[name];e=u['source_evidence'][0];quote=e['quote'];occ=k.starts(text,quote).index(e['start'])+1
                    inv['units'].append({'id':ids[name],'kind':u['category'] if u['category'] in ('fact','instruction','relationship','identity','policy') else 'fact','assertion':u['assertion'],'modality':'informational','applicability':'unconditional','uncertainty':'none','uncertainty_reason':'','required_unit_ids':[ids[d] for d in o['required_source_unit_ids']],'evidence':[{'quote':quote,'occurrence':occ}]})
                value=self.mapping(inv,record);value['mappings']={ids[n]:{'disposition':'missing' if o['expected_disposition']=='omitted' else o['expected_disposition'],'operative_pointers':o['semantic_record_pointers'],'reason':'Explicit supplied offline annotation, not model observation.'} for n,o in oracle.items()}
                checked=k.validate_b(text,record,inv,value);expected=variant['expected'];target=expected.get('target_unit')
                if target:self.assertEqual(value['mappings'][ids[target]]['disposition'],expected['target_disposition'])
                self.assertEqual(checked['source_inventory_completeness'],'unverified')
                if variant['id'] in ('semantic_positive','full_group_positive','optional_positive'):self.assertEqual(checked['mapping_status'],'all_inventoried_units_matched')
                elif variant['id'] in ('unknown_endpoint_blocks_group','unclear_negative'):self.assertEqual(checked['mapping_status'],'unverified')
                else:self.assertEqual(checked['mapping_status'],'not_complete')
                before=k.build_a(text);mutated=copy.deepcopy(variant);mutated.update(expected={'canary':'private-expected-canary'},record={'canary':'private-record-canary'},oracle_mapping=['private-oracle-canary']);self.assertEqual(before,k.build_a(text))
                raw=c.encode(before['body']);self.assertNotIn(b'private-',raw);user=c.strict(k.build_b(text,record,inv)['body']['messages'][1]['content']);self.assertEqual(user['source_text'],text);self.assertEqual(k.wire_decode(text,user['inventory_wire'],inv),inv);count+=1
                if variant['id']=='source_only_extra_negative':self.assertNotEqual(k.build_a(text),k.build_a(family['source_text']))
        self.assertEqual(count,10)
    def test_unsigned_proposal_core_validation(self):
        sys.path.insert(0,str(a.PYTHON.parent.parent/'lib/python3.12/site-packages'))
        def module(name,path):
            spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
        prep=module('r10_prep',HERE/'prepare_bindings.py');release=module('r10_release',HERE.parents[4]/'tools/research-credentials-stable/release.py');core=c.read(c.BENCH/'runner-stability-review/deployment/core.json');captured={};orig=prep.digest
        def capture(path,v):captured[str(path)]=c.encode(v)
        def digest(path):
            if str(path) in captured:return c.sha(captured[str(path)])
            if str(path)==str(c.ROUND/'live-authorization.json'):return c.digest(a.authorization_fields())
            return orig(path)
        with patch.object(prep,'put',capture),patch.object(prep,'digest',digest),patch.object(release,'digest',digest),patch.object(release,'read_key',side_effect=AssertionError('sign')),patch.object(release,'publish',side_effect=AssertionError('publish')):
            prep.prepare('synthetic-offline-scope',int(prep.time.time())+3600,HERE/'test_runtime.py');proposal=c.strict(captured[str(HERE/'UNSIGNED-JOB-PROPOSAL.json')]);release.validate(core,proposal)
        self.assertEqual(proposal['provider_variables'],['OPENROUTER_API_KEY']);self.assertEqual(proposal['budget']['reservation_nanousd'],323840000)
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')):unittest.main(verbosity=2)
