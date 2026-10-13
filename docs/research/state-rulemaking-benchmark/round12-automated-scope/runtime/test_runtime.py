"""Supplied synthetic outputs test guards and durability, never semantic discovery."""
import ast,copy,importlib.util,json,socket,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import adapter as a
c=a.c;k=a.k
SECRET='synthetic-runtime-key'
RELEASE_SHA='ca845ca805dbbb5fd428a06d63c735b4a326aa09100dcaeb0e913859069032a2'
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.text,cls.record,cls.plans,cls.prior=a.preflight()
    def inventory(self,text=None,n=1,heavy=False):
        text=self.text if text is None else text
        return {'schema_version':'round12.source-inventory.v1','source_text_sha256':k.source_hash(text),'units':[{'id':f'u{i+1:03}','kind':'instruction','assertion':'x'*(360 if heavy else 20),'modality':'informational','applicability':'unconditional','uncertainty':'none','uncertainty_reason':'','required_unit_ids':[],'evidence':[{'quote':text[:80],'occurrence':1}]} for i in range(n)]}
    def scope(self,inv=None,category='required_participation',heavy=False,text=None):
        inv=self.inventory() if inv is None else inv;text=self.text if text is None else text;policy=c.read(c.PROTO/'policy.json')
        return {'schema_version':'round12.source-scope.v1','source_text_sha256':k.source_hash(text),'inventory_sha256':c.digest(inv),'scopes':{u['id']:{'category':category,'basis':policy['scope_basis_by_category'][category],'reason':'r'*(360 if heavy else 24),'evidence':copy.deepcopy(u['evidence'])} for u in inv['units']}}
    def mapping(self,inv=None,scope=None,record=None):
        inv=self.inventory() if inv is None else inv;scope=self.scope(inv) if scope is None else scope;record=self.record if record is None else record;p=next(p for p,v in k.fields(record).items() if v not in (None,'',[],{}))
        return {'schema_version':'round12.source-mapping.v1','source_text_sha256':inv['source_text_sha256'],'record_sha256':c.digest(record),'operative_record_sha256':c.digest(k.operative(record)[0]),'inventory_sha256':c.digest(inv),'scope_sha256':c.digest(scope),'mappings':{u['id']:{'disposition':'matched','operative_pointers':[p],'reason':'Supplied synthetic annotation, not semantic discovery.'} for u in inv['units']}}
    def direct(self,inv=None,scope=None,mapping=None):
        inv=self.inventory() if inv is None else inv;scope=self.scope(inv) if scope is None else scope;mapping=self.mapping(inv,scope) if mapping is None else mapping
        return {'schema_version':'round12.direct-verification.v1','source_text_sha256':k.source_hash(self.text),'record_sha256':c.digest(self.record),'operative_record_sha256':c.digest(k.operative(self.record)[0]),'units':[{'source_unit':copy.deepcopy(u),'scope':copy.deepcopy(scope['scopes'][u['id']]),'mapping':copy.deepcopy(mapping['mappings'][u['id']])} for u in inv['units']]}
    def native(self,v):return {'model':'openai/gpt-6.1-sol','provider':'OpenAI','choices':[{'finish_reason':'stop','message':{'content':c.encode(v).decode()}}],'usage':{'prompt_tokens':100,'completion_tokens':100,'cost':.0012}}
    def run_case(self,inv=None,scope=None,modify=None,transport=None,real_integrity=False):
        inv=self.inventory() if inv is None else inv;scope=self.scope(inv) if scope is None else scope;tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);run=Path(tmp.name)/'run';calls=[]
        def fake(body,key):
            name={'direct_verification':'D','source_inventory':'A','source_scope':'C','source_mapping':'B'}[body['response_format']['json_schema']['name']];calls.append((name,body));obj=self.native({'D':self.direct(),'A':inv,'C':scope,'B':self.mapping(inv,scope)}[name]);status=200
            if modify:status,obj=modify(name,obj,run)
            return status,obj if isinstance(obj,bytes) else c.encode(obj)
        try:result=a.execute_once(run,self.text,self.record,self.plans,SECRET,transport or fake,integrity_check=a.integrity if real_integrity else lambda *_:None)
        except c.Denied:result=None
        return run,calls,result
    def denied(self,fn,*args):
        with self.assertRaises((c.Denied,ValueError,KeyError,TypeError)):fn(*args)
    def test_01_preflight_isolated_and_witnesses(self):
        class Forbidden(dict):
            def get(self,*args):raise AssertionError('credential')
        with patch.object(a.os,'environ',Forbidden()),patch.object(socket.socket,'connect',side_effect=AssertionError('network')):text,record,plans,prior=a.preflight()
        self.assertEqual(prior['baseline_files'],6829);self.assertEqual(prior['prior_nanousd'],1182150718);self.assertEqual(plans['D']['guarded_bytes'],28441);self.assertEqual(plans['A']['guarded_bytes'],10205)
        self.assertEqual(len(k.fields(record)),276);self.assertEqual(len(k.identities(record)),58);self.assertEqual(a.PRIOR+4*a.RESERVE,1829830718)
        for p,v in k.fields(record).items():self.assertEqual(v,k.resolve(k.operative(record)[0],p))
    def test_02_four_stages_full_freezes_no_resume(self):
        run,calls,result=self.run_case(real_integrity=True);self.assertIsNotNone(result);self.assertEqual([n for n,_ in calls],list(a.ORDER));self.assertEqual(result['validation']['mapping_status'],'all_required_inventoried_units_matched')
        ledger=c.read(run/'ledger.json');self.assertEqual(ledger['cumulative_budget_charge_nanousd'],1829830718);self.assertEqual(len(ledger['planned_outcomes']),4)
        for n in a.ORDER:self.assertTrue((run/f'stage-{n.lower()}-freeze.json').exists())
        with self.assertRaises(FileExistsError):a.execute_once(run,self.text,self.record,self.plans,SECRET,lambda *_:self.fail('resume'))
    def test_03_field_set_and_arm_isolation(self):
        inv=self.inventory();scope=self.scope(inv);plans={'D':k.build_d(self.text,self.record),'A':k.build_a(self.text),'C':k.build_c(self.text,inv),'B':k.build_b(self.text,self.record,inv,scope)};boundary=c.read(c.PROTO/'boundaries.json')
        for name,p in plans.items():
            user=c.strict(p['body']['messages'][1]['content']);self.assertEqual(set(user),set(boundary['exact_user_fields'][name]));self.assertEqual(user['source_text'],self.text)
            self.assertEqual(p['guarded_bytes'],len(c.encode(p['body']))+1024)
        marked=copy.deepcopy(self.record);marked['record_notes'].append('candidate-only-marker')
        self.assertEqual(k.build_a(self.text),plans['A']);self.assertEqual(k.build_c(self.text,inv),plans['C']);self.assertNotEqual(k.build_d(self.text,marked)['request_sha256'],plans['D']['request_sha256'])
        self.assertNotEqual(k.build_a(self.text+' source-only-marker')['request_sha256'],plans['A']['request_sha256'])
        self.assertEqual(c.strict(plans['B']['body']['messages'][1]['content'])['inventory_wire'],c.strict(plans['C']['body']['messages'][1]['content'])['inventory_wire'])
    def test_04_all_native_failures_at_every_stage(self):
        kinds=('http','length','refusal','tools','provider','model','usage','cost','invalid','duplicate','nonfinite')
        for name in a.ORDER:
            for kind in kinds:
                def modify(n,obj,run):
                    if n!=name:return 200,obj
                    if kind=='http':return 429,obj
                    if kind=='length':obj['choices'][0]['finish_reason']='length'
                    elif kind=='refusal':obj['choices'][0]['message']['refusal']='yes'
                    elif kind=='tools':obj['choices'][0]['message']['tool_calls']=[{}]
                    elif kind=='provider':obj['provider']='other'
                    elif kind=='model':obj['model']='other'
                    elif kind=='usage':obj['usage']['prompt_tokens']=True
                    elif kind=='cost':del obj['usage']['cost']
                    else:obj['choices'][0]['message']['content']={'invalid':'{}','duplicate':'{"x":1,"x":2}','nonfinite':'{"x":1e999}'}[kind]
                    return 200,obj
                with self.subTest(stage=name,kind=kind):
                    run,calls,result=self.run_case(modify=modify);names=[n for n,_ in calls];self.assertEqual(names,{'D':['D','A','C','B'],'A':['D','A'],'C':['D','A','C'],'B':['D','A','C','B']}[name]);self.assertEqual(result is not None,name=='D');self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],len(calls)*a.RESERVE);self.assertTrue((run/f'stage-{name.lower()}/response.body').exists())
    def test_05_uncertain_D_continues_and_no_retry(self):
        calls=[]
        def fake(body,key):
            name=body['response_format']['json_schema']['name'];calls.append(name)
            if name=='direct_verification':raise RuntimeError(SECRET)
            value={'source_inventory':self.inventory(),'source_scope':self.scope(),'source_mapping':self.mapping()}[name];return 200,c.encode(self.native(value))
        run,_,result=self.run_case(transport=fake);self.assertIsNotNone(result);self.assertEqual(len(calls),4);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],4*a.RESERVE)
        for p in run.rglob('*'):
            if p.is_file():self.assertNotIn(SECRET.encode(),p.read_bytes())
    def test_06_uncertain_A_stops_dependents(self):
        def modify(n,obj,run):
            if n=='A':raise RuntimeError(SECRET)
            return 200,obj
        run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual([n for n,_ in calls],['D','A']);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],2*a.RESERVE)
    def test_07_actual_B_overflow_retains_partial_arm(self):
        inv=self.inventory(n=48,heavy=True);scope=self.scope(inv,heavy=True);plan=k.build_b(self.text,self.record,inv,scope);self.assertFalse(plan['fits'])
        run,calls,result=self.run_case(inv,scope);self.assertIsNone(result);self.assertEqual([n for n,_ in calls],['D','A','C']);self.assertFalse((run/'stage-b').exists());self.assertEqual(c.read(run/'stage-b-preflight.json')['guarded_bytes'],plan['guarded_bytes']);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],3*a.RESERVE)
    def test_08_actual_C_overflow_stops_C_B(self):
        inv=self.inventory(n=64,heavy=True)
        for u in inv['units']:u['applicability']='a'*240;u['evidence']*=3
        self.assertFalse(k.build_c(self.text,inv)['fits']);run,calls,result=self.run_case(inv);self.assertIsNone(result);self.assertEqual([n for n,_ in calls],['D','A']);self.assertFalse((run/'stage-c').exists())
    def test_09_fixed_D_overflow_allows_A(self):
        original=k.build_d
        def overflow(*args):v=original(*args);v.update(fits=False,guarded_bytes=40001);return v
        with patch.object(k,'build_d',side_effect=overflow):
            plans=copy.deepcopy(self.plans);plans['D']=overflow(self.text,self.record)
            with patch.object(self,'plans',plans):run,calls,result=self.run_case()
        self.assertIsNotNone(result);self.assertEqual([n for n,_ in calls],['A','C','B']);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],3*a.RESERVE)
    def test_10_fixed_A_overflow_stops_C_B(self):
        original=k.build_a
        def overflow(*args):v=original(*args);v.update(fits=False,guarded_bytes=40001);return v
        with patch.object(k,'build_a',side_effect=overflow):
            plans=copy.deepcopy(self.plans);plans['A']=overflow(self.text)
            with patch.object(self,'plans',plans):run,calls,result=self.run_case()
        self.assertIsNone(result);self.assertEqual([n for n,_ in calls],['D']);self.assertFalse((run/'stage-a').exists())
    def test_11_all_stage_budget_admission(self):
        for n in range(4):
            with self.subTest(admitted=n),patch.object(a,'CEILING',a.PRIOR+n*a.RESERVE):
                run,calls,result=self.run_case();self.assertIsNone(result);self.assertEqual(len(calls),n);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],n*a.RESERVE)
    def test_12_higher_reported_and_rate_costs_stop(self):
        for name in a.ORDER:
            for method in ('cost','usage'):
                def modify(n,obj,run):
                    if n==name:
                        if method=='cost':obj['usage']['cost']=2.0000000001
                        else:obj['usage']['completion_tokens']=300000
                    return 200,obj
                with self.subTest(stage=name,method=method):
                    run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual(len(calls),list(a.ORDER).index(name)+1);debit=c.read(run/'ledger.json');self.assertGreater(debit['cumulative_budget_charge_nanousd'],a.CEILING);self.assertTrue((run/f'stage-{name.lower()}/result.json').exists())
        self.assertEqual(a.cost_nano(.0000000001),1);self.assertEqual(a.recoverable(c.encode({'usage':{'cost':.2,'prompt_tokens':200000,'completion_tokens':0}})),400000000)
    def test_13_unsafe_secret_and_oversize_stop_without_raw(self):
        for raw in [c.encode(self.native({'secret':SECRET})),b'x'*2000001]:
            run,calls,result=self.run_case(transport=lambda *_:(200,raw));self.assertIsNone(result);self.assertFalse((run/'stage-d/response.body').exists());self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],a.RESERVE)
    def test_14_partial_intent_and_write_failures_latched(self):
        real=a.put
        for suffix in ('stage-a/request.json','stage-a/intent.json','stage-a/response.body','stage-a/status.json','stage-a/content.body','stage-a/result.json','stage-a/completed.json','stage-a-freeze.json'):
            def fail(p,*args,**kw):
                if str(p).endswith(suffix):raise OSError(SECRET)
                return real(p,*args,**kw)
            with self.subTest(receipt=suffix),patch.object(a,'put',side_effect=fail):run,calls,result=self.run_case()
            self.assertIsNone(result);self.assertEqual(c.read(run/'ledger.json')['new_budget_charge_nanousd'],2*a.RESERVE);self.assertFalse((run/'stage-c').exists())
            with self.assertRaises(FileExistsError):a.execute_once(run,self.text,self.record,self.plans,SECRET,lambda *_:self.fail('retry'))
    def test_15_freeze_A_tamper_during_C_stops_B(self):
        def modify(n,obj,run):
            if n=='C':(run/'stage-a/content.body').write_bytes(b'{}')
            return 200,obj
        run,calls,result=self.run_case(modify=modify);self.assertIsNone(result);self.assertEqual([n for n,_ in calls],['D','A','C']);self.assertFalse((run/'stage-b').exists())
    def test_16_C_frozen_receipt_tamper_stops_B(self):
        real=a.freeze_write
        def tamper(run,n,*args):
            real(run,n,*args)
            if n=='C':(run/'stage-c/validated.json').write_bytes(b'{}')
        with patch.object(a,'freeze_write',side_effect=tamper):run,calls,result=self.run_case()
        self.assertIsNone(result);self.assertEqual([n for n,_ in calls],['D','A','C']);self.assertFalse((run/'stage-b').exists())
    def test_17_strict_JSON(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":{"a":1,"a":2}}',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e999}',b'{} trailing'):
            self.denied(c.strict,raw)
    def test_18_closed_refs_and_unused_defs(self):
        s=k.schema('d',self.text,self.record)
        for ref in ('https://x','#/$defs/absent'):
            bad=copy.deepcopy(s);bad['$defs']['u']['properties']['id']={'$ref':ref};self.denied(c.expand,bad,bad['$defs'])
        for change in ('keyword','sibling','cycle','extra_def'):
            bad=copy.deepcopy(s)
            if change=='keyword':bad['$defs']['s']['pattern']='x'
            elif change=='sibling':bad['$defs']['s']={'$ref':'#/$defs/e','type':'object'}
            elif change=='cycle':bad['$defs']['s']={'$ref':'#/$defs/s'}
            else:bad['$defs']['unused']={'type':'object'}
            self.denied(c.expand,bad,bad['$defs'])
    def test_19_inventory_schedules_quotes_and_graphs(self):
        for change in ('id','duplicate','missing_dep','cycle','quote','occurrence_bool','uncertainty','blank','extra'):
            inv=self.inventory(n=2);u=inv['units'][0]
            if change=='id':u['id']='u065'
            elif change=='duplicate':inv['units'][1]['id']=u['id']
            elif change=='missing_dep':u['required_unit_ids']=['u003']
            elif change=='cycle':u['required_unit_ids']=['u002'];inv['units'][1]['required_unit_ids']=['u001']
            elif change=='quote':u['evidence'][0]['quote']='never in source'
            elif change=='occurrence_bool':u['evidence'][0]['occurrence']=True
            elif change=='uncertainty':u['uncertainty']='source_ambiguous'
            elif change=='blank':u['applicability']=' '
            else:u['new']='x'
            self.denied(k.validate_a,self.text,inv)
    def test_20_inventory_unicode_overlapping_roundtrip(self):
        text='😀aaaa é e\u0301';inv=self.inventory(text);inv['units'][0]['evidence']=[{'quote':'aa','occurrence':3},{'quote':'é','occurrence':1}];wire=k.wire_encode(text,inv);self.assertEqual(wire['units'][0][8][0],[3,5,3]);self.assertEqual(k.wire_decode(text,wire,inv),inv)
        for part in ('bool','width','occurrence','order','column'):
            bad=copy.deepcopy(wire)
            if part=='bool':bad['units'][0][8][0][0]=True
            elif part=='width':bad['units'][0].append('extra')
            elif part=='occurrence':bad['units'][0][8][0][2]=1
            elif part=='order':bad['units'][0][8].reverse()
            else:bad['columns'].reverse()
            self.denied(k.wire_decode,text,bad,inv)
    def test_21_scope_totality_basis_and_exact_evidence(self):
        inv=self.inventory(n=2);scope=self.scope(inv)
        for change in ('delete','extra','contradict','evidence','blank','inventoryhash','sourcehash'):
            bad=copy.deepcopy(scope)
            if change=='delete':del bad['scopes']['u001']
            elif change=='extra':bad['scopes']['u003']=bad['scopes']['u001']
            elif change=='contradict':bad['scopes']['u001']['basis']='substantive_background_only'
            elif change=='evidence':bad['scopes']['u001']['evidence'][0]['quote']='never in source'
            elif change=='blank':bad['scopes']['u001']['reason']=' '
            elif change=='inventoryhash':bad['inventory_sha256']='0'*64
            else:bad['source_text_sha256']='0'*64
            self.denied(k.validate_scope,self.text,inv,bad)
    def test_22_all_kinds_allow_background_no_classifier(self):
        for kind in c.read(c.PROTO/'policy.json')['allowed_scope_by_kind']:
            inv=self.inventory();inv['units'][0]['kind']=kind
            for category in c.read(c.PROTO/'policy.json')['scope_categories']:self.assertTrue(k.validate_scope(self.text,inv,self.scope(inv,category))['structural_valid'])
    def test_23_scope_codec_categories_independent_and_tampering(self):
        text='😀aaaa é';inv=self.inventory(text,n=4);cats=k.sc.CATEGORIES;scope=self.scope(inv,text=text)
        for u,category in zip(inv['units'],cats):
            u['evidence']=[{'quote':'aa','occurrence':3}]
            x=scope['scopes'][u['id']];x.update(category=category,basis=k.sc.BASES[cats.index(category)],evidence=[{'quote':'aa','occurrence':3}])
        scope['inventory_sha256']=c.digest(inv);wire=k.scope_wire(text,inv,scope);ids=[u['id'] for u in inv['units']];self.assertEqual(k.sc.decode(wire,text,c.digest(inv),ids,scope),scope)
        for change in ('bool','fraction','basis','reason','evidence','order','duplicate','width','hash','columns'):
            bad=copy.deepcopy(wire)
            if change=='bool':bad['scopes'][0][1]=True
            elif change=='fraction':bad['scopes'][0][2]=.5
            elif change=='basis':bad['scopes'][0][2]=2
            elif change=='reason':bad['scopes'][0][3]+='x'
            elif change=='evidence':bad['scopes'][0][4][0][2]=1
            elif change=='order':bad['scopes'].reverse()
            elif change=='duplicate':bad['scopes'][1][0]=bad['scopes'][0][0]
            elif change=='width':bad['scopes'][0].append('x')
            elif change=='hash':bad['inventory_sha256']='0'*64
            else:bad['columns'].reverse()
            self.denied(k.sc.decode,bad,text,c.digest(inv),ids,scope)
    def test_24_mapping_pointers_hashes_and_totality(self):
        inv=self.inventory();scope=self.scope(inv);value=self.mapping(inv,scope)
        for change in ('missing_schedule','extra','id_pointer','nested_pointer','evidence_pointer','sourcehash','recordhash','inventoryhash','scopehash','operativehash','mismatch_no_refs','missing_with_refs','duplicate_refs'):
            bad=copy.deepcopy(value);m=bad['mappings']['u001']
            if change=='missing_schedule':del bad['mappings']['u001']
            elif change=='extra':bad['mappings']['u002']=copy.deepcopy(m)
            elif change=='id_pointer':m['operative_pointers']=['/events/0/id']
            elif change=='nested_pointer':m['operative_pointers']=['/events/0/timing/0/anchor_event_ids/0']
            elif change=='evidence_pointer':m['operative_pointers']=['/evidence/0']
            elif change.endswith('hash'):bad[{'sourcehash':'source_text_sha256','recordhash':'record_sha256','inventoryhash':'inventory_sha256','scopehash':'scope_sha256','operativehash':'operative_record_sha256'}[change]]='0'*64
            elif change=='mismatch_no_refs':m.update(disposition='mismatched',operative_pointers=[])
            elif change=='missing_with_refs':m['disposition']='missing'
            else:m['operative_pointers']*=2
            self.denied(k.validate_b,self.text,self.record,inv,scope,bad)
    def test_25_known_required_loss_survives_unknown_dependency(self):
        inv=self.inventory(n=2);inv['units'][0].update(uncertainty='source_ambiguous',uncertainty_reason='Shared function unresolved.');inv['units'][1]['required_unit_ids']=['u001'];scope=self.scope(inv);value=self.mapping(inv,scope)
        value['mappings']['u001'].update(disposition='unknown',operative_pointers=[]);value['mappings']['u002']['disposition']='mismatched';result=k.validate_b(self.text,self.record,inv,scope,value)
        self.assertEqual(result['mapping_status'],'unverified');self.assertEqual(result['effective_dispositions']['u002'],'unknown');self.assertIn('u002',result['known_required_defects']);self.assertIn('u002',result['required_defects'])
    def test_26_background_visible_unresolved_blocks(self):
        inv=self.inventory();scope=self.scope(inv,'retained_background');value=self.mapping(inv,scope);value['mappings']['u001'].update(disposition='missing',operative_pointers=[]);result=k.validate_b(self.text,self.record,inv,scope,value)
        self.assertEqual(result['mapping_status'],'all_required_inventoried_units_matched');self.assertIn('u001',result['background_diagnostics']);self.assertIn('u001',result['known_defects']);self.assertEqual(result['whole_record_fidelity'],'unverified')
        scope=self.scope(inv,'unresolved_scope');value=self.mapping(inv,scope);self.assertEqual(k.validate_b(self.text,self.record,inv,scope,value)['mapping_status'],'unverified')
    def test_27_direct_discovery_independent_schedule(self):
        inv=self.inventory();inv['units'][0]['id']='u064';scope=self.scope(inv);value=self.direct(inv,scope,self.mapping(inv,scope));result=k.validate_d(self.text,self.record,value);self.assertTrue(result['structural_valid']);self.assertEqual(set(result['effective_dispositions']),{'u064'})
        value['units'][0]['source_unit']['id']='candidate-id';self.denied(k.validate_d,self.text,self.record,value)
    def test_28_conditional_force_roles_and_relations_are_not_inferred(self):
        inv=self.inventory(n=4);kinds=['endpoint','endpoint_role','instruction','relationship'];mods=['informational','optional','advisory','mandatory']
        for u,kind,mod in zip(inv['units'],kinds,mods):u.update(kind=kind,modality=mod,applicability='if intended speaker; qualifications retained')
        inv['units'][1]['required_unit_ids']=['u001'];inv['units'][3]['required_unit_ids']=['u002','u003'];scope=self.scope(inv);value=self.mapping(inv,scope)
        self.assertEqual(k.validate_b(self.text,self.record,inv,scope,value)['mapping_status'],'all_required_inventoried_units_matched')
        value['mappings']['u002'].update(disposition='missing',operative_pointers=[]);self.denied(k.validate_b,self.text,self.record,inv,scope,value)
        value['mappings']['u004']['disposition']='mismatched';result=k.validate_b(self.text,self.record,inv,scope,value);self.assertEqual(result['mapping_status'],'not_complete');self.assertIn('u004',result['known_required_defects'])
    def test_29_projection_preserves_all_operative_values_ids_and_notes(self):
        projected,values=k.operative(self.record);self.assertEqual(k.identities(projected),k.identities(self.record));self.assertEqual(values,k.fields(projected));self.assertEqual(projected['record_notes'],self.record['record_notes'])
        modified=copy.deepcopy(self.record);modified['requirements'][0]['description']='candidate-only-unsupported-addition';self.assertNotEqual(k.build_d(self.text,modified)['request_sha256'],self.plans['D']['request_sha256']);self.assertEqual(k.validate_b(self.text,modified,self.inventory(),self.scope(),self.mapping(record=modified))['whole_record_fidelity'],'unverified')
    def test_30_live_binding_requires_reviewed_full_closure(self):
        with self.assertRaises((c.Denied,FileNotFoundError)):a.verify_live_bindings()
        fields=a.authorization_fields();self.assertEqual(fields['max_new_operations'],4);self.assertEqual(fields['reservation_nanousd'],647680000);self.assertFalse(fields['reference_input']);self.assertFalse(fields['production_eligible'])
    def test_31_current_imported_files_are_exactly_pinned(self):
        pins=c.read(HERE/'dependency-pins.json')['files']|c.read(HERE/'code-pins.json')['files'];root=a.PYTHON.parent.parent
        for module in list(sys.modules.values()):
            path=getattr(module,'__file__',None)
            if path:
                p=Path(path).resolve()
                if p.is_relative_to(root) or p.is_relative_to(HERE):self.assertIn(str(p),pins);self.assertEqual(c.file_hash(p),pins[str(p)])
        self.assertLess(len(pins)+50,10000)
    def test_32_input_integrity_denies_modified_source_candidate_and_code(self):
        original=c.file_hash
        for target in (c.ROUND/'source/26-19-016.txt',c.ROUND/'candidate/candidate.json',HERE/'adapter.py'):
            def drift(p):return '0'*64 if Path(p)==target else original(p)
            with self.subTest(path=target.name),patch.object(c,'file_hash',side_effect=drift):self.denied(a.integrity,self.text,self.record)
    def test_33_synthetic_proposal_unchanged_release_validator(self):
        # Execute only unchanged pure validation functions; no signer module import,
        # signing key lookup, publication, executor or production configuration edit.
        release=HERE.parents[4]/'tools/research-credentials-stable/release.py'
        self.assertEqual(c.file_hash(release),RELEASE_SHA)
        tree=ast.parse(release.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','encode','digest','in_roots','validate'}]
        self.assertEqual(len(nodes),5);namespace={'Path':Path,'json':json,'hashlib':c.hashlib,'time':time};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(release),'exec'),namespace)
        spec=importlib.util.spec_from_file_location('r12_prep',HERE/'prepare_bindings.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
        core=c.read(c.BENCH/'runner-stability-review/deployment/core.json');self.assertEqual(core['python_path'],str(a.PYTHON));captured={};real=prep.digest
        def capture(path,value):captured[str(path)]=copy.deepcopy(value)
        def digest(path):
            if str(path) in captured:return c.digest(captured[str(path)])
            if Path(path)==c.ROUND/'live-authorization.json':return c.digest(a.authorization_fields())
            return real(path)
        with patch.object(prep,'put',side_effect=capture),patch.object(prep,'digest',side_effect=digest),patch.dict(namespace,{'digest':digest}):
            result=prep.prepare('synthetic-offline-scope',int(time.time())+3600,HERE/'test_runtime.py');proposal=captured[str(HERE/'UNSIGNED-JOB-PROPOSAL.json')];namespace['validate'](core,proposal)
        self.assertEqual(proposal['job_id'],'round12-automated-scope-initial');self.assertEqual(proposal['budget'],{'prior_nanousd':1182150718,'reservation_nanousd':647680000,'ceiling_nanousd':2000000000});self.assertEqual(proposal['provider_variables'],['OPENROUTER_API_KEY']);self.assertFalse(result['signed_job_created']);self.assertLess(result['dependency_files'],10000)
if __name__=='__main__':unittest.main(verbosity=2)
