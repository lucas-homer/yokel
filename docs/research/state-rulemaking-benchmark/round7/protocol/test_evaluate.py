import copy,unittest
import evaluate as e

def fixture(status='not_started',called=False,gate='assembly_review'):
    schedule=dict(schema_version='round7.schedule.v1',documents=[dict(document_id='doc',pdf_sha256='a'*64,pdf_pages=1,state='OH',stratum='general')])
    truth=dict(schema_version='round7.truth.v1',documents=[dict(document_id='doc',pdf_sha256='a'*64,scope_status='complete',all_pages_viewed=True,universe_complete=True,reviewer='authored development reference',exclusions=[],domains={k:'absent' for k in e.CATEGORIES},units=[],acceptance_blockers=[])])
    audit=dict(schema_version='round7.matching-audit.v1',reviewer='independent authored mapping',documents=[])
    doc=dict(document_id='doc',runtime_gate=gate,gate_reasons=['development control'],inventory_sha256='b'*64,record_sha256=None,payload_sha256=None,provider_service_error=False,review_reasons=[],arms={a:dict(status=status,called=called,payload_sha256=None,source_coverage_complete=False,reason='uncalled gate') for a in e.ARMS})
    if called and status in ('accepted_complete','review'):
        for arm in doc['arms'].values():arm['judgment']=dict(common_dimensions={k:'pass' if status=='accepted_complete' else 'fail' for k in ('support','association','requirements','source_identity','completeness')},complete_record_shadow_accepted=status=='accepted_complete',status=status,validation_errors=[],deterministic_review_reasons=[],action_ready=False,production_eligible=False)
    observed=dict(schema_version='round7.observed.v1',documents=[doc],costs={})
    return schedule,truth,audit,observed

class Controls(unittest.TestCase):
    def test_system_gate_preserved_and_forged_invocation_rejected(self):
        args=fixture();report=e.evaluate(*args)
        self.assertEqual(report['arms']['jev']['accepted_records'],0)
        self.assertIsNone(report['arms']['jev']['unsafe_acceptance_fraction']['value'])
        self.assertEqual(report['runtime_gates'],{'assembly_review':1})
        bad=copy.deepcopy(args);bad[3]['documents'][0]['arms']['jev']['called']=True
        with self.assertRaises(ValueError):e.evaluate(*bad)

    def test_independent_disclosure_and_ancillary_audit_vetoes_mock_acceptance(self):
        args=fixture(status='accepted_complete',called=True,gate='paired_verification_completed')
        schedule,truth,audit,observed=args;doc=observed['documents'][0]
        doc.update(record_sha256='c'*64,payload_sha256='d'*64,gate_reasons=[])
        for arm in doc['arms'].values():arm.update(payload_sha256='d'*64,source_coverage_complete=True)
        source=truth['documents'][0];source['domains']['disclosure']='present';source['domains']['ancillary']='present'
        source['units']=[dict(id=id,category=cat,subtype=id,description='Authored R6-derived development '+id,raw_value=None,modality='descriptive',targets=targets,evidence=[dict(page=1,region='development source',quote=id)]) for id,cat,targets in [('disclosure','disclosure',[]),('office','ancillary',[]),('helper','ancillary',[]),('phone','ancillary',['office'])]]
        claims=[dict(id=u['id'],categories=[u['category']],status='correct',evidence_status='matched',literal_kind='none',literal_status='not_applicable',basis='Independent authored development field mapping') for u in source['units']]
        matches=[dict(source_unit_id=u['id'],status='matched',claim_ids=[u['id']],basis='Independent authored mapping; content must be explicit') for u in source['units']]
        review=dict(sha256='c'*64,review_complete=True,claims=claims,source_matches=matches)
        review['claims'].append(dict(id='coverage',categories=['uncertainty'],status='correct',evidence_status='matched',literal_kind='none',literal_status='not_applicable',basis='Authored complete universe claim separately audited'))
        audit['documents']=[dict(document_id='doc',inventory=None,record=review)]
        self.assertEqual(e.evaluate(*args)['arms']['jev']['correct_complete_accepted'],1)
        for change in ('disclosure_class','office_omission','helper_omission','scope_exception','ownership','coverage_overclaim'):
            bad=copy.deepcopy(args);review=bad[2]['documents'][0]['record']
            if change in ('disclosure_class','scope_exception','ownership','coverage_overclaim'):
                target='coverage' if change=='coverage_overclaim' else 'disclosure' if change!='ownership' else 'phone'
                next(c for c in review['claims'] if c['id']==target)['status']='incorrect' if change!='ownership' else 'unknown'
                if change!='coverage_overclaim':next(m for m in review['source_matches'] if m['source_unit_id']==target)['status']='mismatched' if change!='ownership' else 'unknown'
            else:
                target='office' if change=='office_omission' else 'helper'
                review['claims']=[c for c in review['claims'] if c['id']!=target]
                next(m for m in review['source_matches'] if m['source_unit_id']==target).update(status='omitted',claim_ids=[])
                if target=='office':next(m for m in review['source_matches'] if m['source_unit_id']=='phone')['status']='unknown'
            report=e.evaluate(*bad)
            self.assertEqual(report['arms']['jev']['unsafe_accepted'],1,change)
            self.assertEqual(report['arms']['jev']['useful_coverage']['value'],0,change)

    def test_partial_dispatch_missing_rows_and_hash_mismatch(self):
        args=fixture(gate='verification_failed');doc=args[3]['documents'][0]
        doc.update(record_sha256='c'*64,payload_sha256='d'*64)
        doc['arms']['jev'].update(status='failed',called=True,payload_sha256='d'*64)
        report=e.evaluate(*args);self.assertEqual(report['arm_invocations']['jev']['called'],1);self.assertEqual(report['arm_invocations']['stronger']['called'],0)
        bad=copy.deepcopy(args);bad[3]['documents'][0]['arms']['jev']['payload_sha256']='e'*64
        with self.assertRaises(ValueError):e.evaluate(*bad)
        missing=copy.deepcopy(args);missing[3]['documents']=[];report=e.evaluate(*missing)
        self.assertEqual(report['missing_observations'],1);self.assertEqual(report['arms']['jev']['review_or_unserved_fraction']['value'],1)
        self.assertIn('1-notice observed cohort',report['limitations'][1])

    def test_reviewed_impossible_gate_and_judgment_states_reject(self):
        args=fixture(status='review',called=True,gate='paired_verification_completed');doc=args[3]['documents'][0]
        doc.update(record_sha256='c'*64,payload_sha256='d'*64,gate_reasons=[])
        for arm in doc['arms'].values():arm.update(payload_sha256='d'*64,source_coverage_complete=True,judgment=dict(common_dimensions={k:'fail' for k in ('support','association','requirements','source_identity','completeness')},complete_record_shadow_accepted=False,validation_errors=[],deterministic_review_reasons=[],status='review',action_ready=False,production_eligible=False))
        e.evaluate(*args)
        for change in ('completed_failed','after_failed','forged_accepted'):
            bad=copy.deepcopy(args);d=bad[3]['documents'][0]
            if change=='completed_failed':d['arms']['jev']['status']='failed'
            if change=='after_failed':d.update(runtime_gate='verification_failed',gate_reasons=['synthetic']);d['arms']['jev']['status']='failed'
            if change=='forged_accepted':d['arms']['jev']['status']='accepted_complete';d['arms']['jev']['judgment']['complete_record_shadow_accepted']=True
            with self.assertRaises(ValueError,msg=change):e.evaluate(*bad)
        zeros=fixture();zeros[3]['costs']={stage:{k:0 for k in ('usage_estimate_usd','conservative_charge_usd','provider_reported_usd')} for stage in ('extraction','jev','stronger')}
        self.assertEqual(e.evaluate(*zeros)['costs']['experiment_total']['provider_reported_usd'],0)
        for value in (1,1.5,None):
            costs=copy.deepcopy(zeros);costs[3]['costs']['extraction']['provider_reported_usd']=value;e.evaluate(*costs)
        costs=copy.deepcopy(zeros);costs[3]['costs']['extraction']['provider_reported_usd']=True
        with self.assertRaises(ValueError):e.evaluate(*costs)

if __name__=='__main__':unittest.main(verbosity=2)
