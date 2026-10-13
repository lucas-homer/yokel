"""Synthetic controls only. No fresh source/labels/provider calls."""
import copy,unittest
import evaluate as e

def arm(status='not_started'):
    called=status!='not_started';accepted=status=='accepted_complete'
    v=dict(status=status,called=called,payload_sha256='d'*64 if called else None,source_coverage_complete=status in ('review','accepted_complete'),reason='synthetic')
    if status in ('review','accepted_complete'):v['judgment']=dict(common_dimensions={k:'pass' if accepted else 'fail' for k in ('support','association','requirements','source_identity','completeness')},complete_record_shadow_accepted=accepted,status=status,validation_errors=[],deterministic_review_reasons=[],action_ready=False,production_eligible=False)
    return v

def failure(stage,kind,intent=True,status=None):return dict(stage=stage,kind=kind,intent_recorded=intent,operation_id=stage+'-synthetic' if intent else None,http_status=status,evidence_sha256='e'*64)
def fixture():
    schedule=dict(schema_version='round8.schedule.v1',documents=[dict(document_id='doc',pdf_sha256='a'*64,pdf_pages=1,state='OH',stratum='general')])
    truth=dict(schema_version='round8.truth.v1',documents=[dict(document_id='doc',pdf_sha256='a'*64,scope_status='complete',all_pages_viewed=True,universe_complete=True,reviewer='synthetic empty-universe control',exclusions=[],domains={k:'absent' for k in e.CATEGORIES},units=[],acceptance_blockers=[])])
    audit=dict(schema_version='round8.matching-audit.v1',reviewer='synthetic mapping',documents=[])
    doc=dict(document_id='doc',runtime_gate='not_started',gate_reasons=['earlier stop'],inventory_sha256=None,record_sha256=None,payload_sha256=None,provider_service_error=False,review_reasons=[],failure=None,arms={a:arm() for a in e.ARMS})
    return schedule,truth,audit,dict(schema_version='round8.observed.v1',documents=[doc],costs={})
def assembled(d):d.update(inventory_sha256='b'*64,record_sha256='c'*64,payload_sha256='d'*64)
class Controls(unittest.TestCase):
    def test_inventory_http_and_transport_distinct(self):
        for kind,status,service in [('http_error',503,True),('http_error',429,True),('transport_uncertain',None,False),('invalid_response',None,False)]:
            args=fixture();d=args[3]['documents'][0];d.update(runtime_gate='inventory_failed',failure=failure('inventory',kind,status=status),provider_service_error=service)
            original=copy.deepcopy(args);out=e.evaluate(*args)
            self.assertEqual(args,original);self.assertEqual(out['provider_service_errors'],int(service));self.assertEqual(out['operational_failures'][kind],1)
            self.assertEqual(out['arm_invocations']['jev'],{'called':0,'uncalled':1});self.assertIsNone(out['arms']['jev']['unsafe_acceptance_fraction']['value'])
    def test_partial_failure_preserves_prior_arm(self):
        for stage in ('jev','stronger'):
            args=fixture();d=args[3]['documents'][0];assembled(d);d.update(runtime_gate='verification_failed',failure=failure(stage,'http_error',status=500),provider_service_error=True)
            d['arms']['jev']=arm('failed' if stage=='jev' else 'accepted_complete');d['arms']['stronger']=arm() if stage=='jev' else arm('failed')
            out=e.evaluate(*args);self.assertEqual(out['arms']['jev']['accepted_records'],int(stage=='stronger'));self.assertEqual(out['arm_invocations']['stronger']['called'],int(stage=='stronger'))
    def test_safe_pause_before_each_stage(self):
        for stage in ('inventory','jev','stronger'):
            args=fixture();d=args[3]['documents'][0];d.update(runtime_gate='operation_pause',failure=failure(stage,'budget_stop',intent=False))
            if stage!='inventory':assembled(d)
            if stage=='stronger':d['arms']['jev']=arm('review')
            out=e.evaluate(*args);self.assertEqual(out['provider_service_errors'],0);self.assertEqual(out['arm_invocations']['jev']['called'],int(stage=='stronger'))
    def test_false_service_and_impossible_states_reject(self):
        for variant in ('local_service','uncertain_service','http_200','no_intent','later_called'):
            args=fixture();d=args[3]['documents'][0]
            if variant=='local_service':d['provider_service_error']=True
            else:
                assembled(d);d.update(runtime_gate='verification_failed',failure=failure('jev','http_error',status=503),provider_service_error=True);d['arms']['jev']=arm('failed')
                if variant=='uncertain_service':d['failure'].update(kind='transport_uncertain',http_status=None)
                if variant=='http_200':d['failure']['http_status']=200
                if variant=='no_intent':d['failure']['intent_recorded']=False
                if variant=='later_called':d['arms']['stronger']=arm('review')
            with self.assertRaises(ValueError,msg=variant):e.evaluate(*args)
    def test_retained_judgment_and_hash_consistency(self):
        args=fixture();d=args[3]['documents'][0];assembled(d);d.update(runtime_gate='paired_verification_completed',gate_reasons=[]);d['arms']={a:arm('review') for a in e.ARMS};e.evaluate(*args)
        for variant in ('promote','missing','hash','coverage'):
            bad=copy.deepcopy(args);a=bad[3]['documents'][0]['arms']['jev']
            if variant=='promote':a['status']='accepted_complete'
            if variant=='missing':a.pop('judgment')
            if variant=='hash':a['payload_sha256']='f'*64
            if variant=='coverage':a['source_coverage_complete']=False
            with self.assertRaises(ValueError,msg=variant):e.evaluate(*bad)
    def test_shortfall_missing_rows_costs_versions(self):
        args=fixture();args[3]['documents']=[];out=e.evaluate(*args)
        self.assertEqual(out['scheduled_notices'],1);self.assertFalse(out['cohort_adequacy']);self.assertEqual(out['missing_observations'],1);self.assertEqual(out['arm_invocations']['jev']['uncalled'],1)
        self.assertIsNone(out['costs']['experiment_total']['provider_reported_usd']);self.assertIn('original_canonical_sha256',out['version_adapter'])
        args[0]['schema_version']='round7.schedule.v1'
        with self.assertRaises(ValueError):e.evaluate(*args)
    def test_postresponse_budget_stop_preserves_completed_result(self):
        for stage in ('inventory','jev','stronger'):
            args=fixture();d=args[3]['documents'][0];d.update(runtime_gate='postresponse_budget_stop',failure=failure(stage,'budget_stop'),inventory_sha256='b'*64)
            if stage!='inventory':
                assembled(d);d['arms']['jev']=arm('accepted_complete')
            if stage=='stronger':d['arms']['stronger']=arm('review')
            out=e.evaluate(*args);self.assertEqual(out['provider_service_errors'],0);self.assertEqual(out['operational_failures']['budget_stop'],1)
            self.assertEqual(out['arm_invocations']['jev']['called'],int(stage!='inventory'))
            bad=copy.deepcopy(args);bad[3]['documents'][0]['failure']['intent_recorded']=False
            with self.assertRaises(ValueError):e.evaluate(*bad)
            if stage!='inventory':
                bad=copy.deepcopy(args);bad[3]['documents'][0]['arms'][stage]=arm('failed')
                with self.assertRaises(ValueError):e.evaluate(*bad)
    def test_numeric_unknown_costs(self):
        for value in (0,1,0.5,None):
            args=fixture();args[3]['costs']={'extraction':{'provider_reported_usd':value}};e.evaluate(*args)
        args=fixture();args[3]['costs']={'extraction':{'provider_reported_usd':True}}
        with self.assertRaises(ValueError):e.evaluate(*args)
if __name__=='__main__':unittest.main(verbosity=2)
