import copy
import json
import pathlib
import tempfile
import unittest
import subprocess
import sys
import hashlib
from evaluate import evaluate,load_terminal

ID='doc-0123456789ab';HASH='a'*64

def field(typ='DATE',state='present_in_scope',value=None,group=None):
    value=value or ('2026-10-31' if typ=='DATE' else 'A+b@Example.gov')
    fid=typ.lower()
    return {'field_id':fid,'field_type':typ,'source_state':state,'raw_literal':value,'page_region':'page1 synthetic','exact_source_quote':value,'role':'written_comment_close' if typ=='DATE' else 'written_comment_submission_email','conditions':[],'supported_scope':state=='present_in_scope','distinct_value_group':group or fid,'uncertainty_reason_if_any':'synthetic unresolved' if state.startswith('unresolved') else None,'normalized_value':value if state not in ('not_stated','explicit_negative') else None,'source_precision':'date' if typ=='DATE' else 'literal_email'}

def setup(fields=None):
    fs=fields or [field(),field('EMAIL')]
    notice={'opaque_document_id':ID,'original_pdf_sha256':HASH,'retained_pdf_sha256':HASH,'official_url':'https://example.gov/synthetic.pdf','physical_page_mapping':[1],'all_source_pages_viewed':True,'complete_notice_scope':True,'source_states_for_both_fields':{t:sorted({f['source_state'] for f in fs if f['field_type']==t}) for t in ('DATE','EMAIL')},'required_field_values':[f['field_id'] for f in fs if f['source_state']=='present_in_scope'],'scan_degradation_basis':'synthetic','reviewer_identity':'synthetic reviewer','reviewed_at_utc':'2026-10-07T00:00:00Z','fields':fs}
    return {'schema_version':'round4.sources.v1','documents':[{'document_id':ID,'pdf_sha256':HASH}]},{'schema_version':'round4.evaluation.labels.v1','documents':[notice]}

def row(typ='DATE',value=None,case='c1',channel='native',status='text_supported'):
    value=value or ('2026-10-31' if typ=='DATE' else 'A+b@Example.gov')
    return {'case_id':case,'channel':channel,'field':'comment_deadline' if typ=='DATE' else 'submission_email','candidate_value':value,'raw_literal':value,'shadow_status':status,'disposition':'accept_shadow'}

def audit(typ='DATE',case='c1',channel='native',group=None):
    return {'document_id':ID,'case_id':case,'channel':channel,'claim_group':group or typ.lower(),'source_field_id':typ.lower(),'source_value':'correct','role':'matched','conditions':'preserved','precision':'date_only' if typ=='DATE' else 'exact_literal','scope':'matched','reviewer_identity':'synthetic reviewer','basis':'source image audit synthetic'}

def score(manifest,labels,rows=(),audits=(),stages=None,terminal=True,ready=False):
    final={ID:{'document_id':ID,'observations':list(rows),'action_ready':ready}} if terminal else {}
    return evaluate(manifest,labels,final,{'schema_version':'round4.evaluation.audits.v1','audits':list(audits)},stages)

class EvaluatorTests(unittest.TestCase):
    def test_correct_date_email_separate_and_complete(self):
        m,l=setup();r=score(m,l,[row(),row('EMAIL',case='c2')],[audit(),audit('EMAIL',case='c2')])
        for typ in ('DATE','EMAIL','pooled'):self.assertEqual(r['correct_shadow_acceptance_coverage'][typ]['value'],1)
        self.assertEqual(r['document_source_completeness']['numerator'],1)
        self.assertEqual(r['unsafe_acceptance_fraction']['value'],0)

    def test_terminal_review_ignores_provisional_accept_disposition(self):
        m,l=setup();r=score(m,l,[row(status='review')],[audit()])
        self.assertEqual(r['terminal_accepted_rows'],0)
        self.assertIsNone(r['unsafe_acceptance_fraction']['value'])
        self.assertEqual(r['correct_shadow_acceptance_coverage']['DATE']['numerator'],0)

    def test_dynamic_schedule_partial_not_started_are_unrecovered(self):
        m,l=setup()
        for suffix in ('c','d'):
            doc='doc-'+suffix*12;m['documents'].append({'document_id':doc,'pdf_sha256':HASH})
            n=copy.deepcopy(l['documents'][0]);n['opaque_document_id']=doc;l['documents'].append(n)
        r=score(m,l,[row()],[audit()],{m['documents'][1]['document_id']:{'started':True}})
        self.assertEqual(r['scheduled_documents'],3)
        self.assertEqual(r['partial_documents'],1)
        self.assertEqual(r['not_started_documents'],1)
        self.assertEqual(r['correct_shadow_acceptance_coverage']['DATE']['denominator'],3)
        self.assertEqual(r['correct_shadow_acceptance_coverage']['DATE']['numerator'],1)
        self.assertEqual(r['document_source_completeness']['denominator'],3)

    def test_wrong_email_case_is_source_incorrect(self):
        m,l=setup();a=audit('EMAIL');a['source_value']='incorrect'
        r=score(m,l,[row('EMAIL',value='a+b@example.gov')],[a])
        self.assertEqual(r['source_incorrect_accepted_claims'],1)
        self.assertEqual(r['correct_shadow_acceptance_coverage']['EMAIL']['numerator'],0)

    def test_correct_value_wrong_role_or_condition_or_precision_unsafe(self):
        m,l=setup()
        for key,value in [('role','mismatched'),('conditions','lost_or_changed'),('precision','mismatched'),('scope','out_of_scope')]:
            a=audit();a[key]=value;r=score(m,l,[row()],[a])
            self.assertEqual(r['unsafe_acceptance_fraction']['numerator'],1)
            self.assertEqual(r['source_incorrect_accepted_claims'],1)
            self.assertEqual(r['correct_shadow_acceptance_coverage']['DATE']['numerator'],0)

    def test_timestamp_not_date_precision(self):
        m,l=setup();r=score(m,l,[row(value='2026-10-31T00:00:00Z')],[audit()])
        self.assertEqual(r['source_incorrect_accepted_claims'],1)
        self.assertIn('invalid_or_non_date_precision',r['accepted_claim_audits'][0]['unsafe_reasons'])

    def test_missing_audit_unverifiable_and_unsafe(self):
        m,l=setup();r=score(m,l,[row()])
        self.assertEqual(r['unauditable_accepted_claims'],1)
        self.assertEqual(r['unsafe_acceptance_fraction']['value'],1)

    def test_source_conflict_or_uncertainty_not_settled(self):
        for state in ('unresolved_conflict','unresolved_uncertainty'):
            m,l=setup([field(state=state),field('EMAIL')]);r=score(m,l,[row()],[audit()])
            self.assertEqual(r['source_unresolved_accepted_claims'],1)
            self.assertEqual(r['accepted_source_conflicts'],int(state=='unresolved_conflict'))
            self.assertIsNone(r['correct_shadow_acceptance_coverage']['DATE']['value'])

    def test_missing_labels_never_shrink_schedule_or_certify_coverage(self):
        m,l=setup();l['documents']=[];r=score(m,l,[row()])
        self.assertEqual(r['scheduled_documents'],1)
        self.assertFalse(r['source_labels_complete'])
        self.assertIsNone(r['correct_shadow_acceptance_coverage']['pooled']['value'])
        self.assertEqual(r['document_source_completeness']['denominator'],1)

    def test_zero_eligible_type_null_not_vacuous_success(self):
        m,l=setup([field(),field('EMAIL',state='not_stated')]);r=score(m,l,[row()],[audit()])
        self.assertIsNone(r['correct_shadow_acceptance_coverage']['EMAIL']['value'])
        self.assertEqual(r['correct_shadow_acceptance_coverage']['EMAIL']['denominator'],0)

    def test_unsupported_abstention_requires_terminal_output(self):
        m,l=setup([field(state='present_out_of_scope'),field('EMAIL')])
        r=score(m,l,terminal=False,stages={ID:{'started':True}})
        self.assertEqual(r['unsupported_abstention']['numerator'],0)
        self.assertEqual(score(m,l)['unsupported_abstention']['numerator'],1)

    def test_audited_native_fallback_duplicates_count_once(self):
        m,l=setup();r=score(m,l,[row(),row(case='c2',channel='fallback')],[audit(),audit(case='c2',channel='fallback')])
        self.assertEqual(r['terminal_accepted_rows'],2)
        self.assertEqual(r['distinct_audited_or_unclassified_claims'],1)
        self.assertEqual(r['correct_shadow_acceptance_coverage']['DATE']['numerator'],1)

    def test_unsafe_duplicate_cannot_disappear(self):
        m,l=setup();a=audit(case='c2',channel='fallback');a['conditions']='lost_or_changed'
        r=score(m,l,[row(),row(case='c2',channel='fallback')],[audit(),a])
        self.assertEqual(r['unsafe_acceptance_fraction']['numerator'],1)
        self.assertEqual(r['document_source_completeness']['numerator'],0)

    def test_materially_different_source_groups_not_merged(self):
        m,l=setup();f=copy.deepcopy(l['documents'][0]['fields'][0]);f['field_id']='date2';f['normalized_value']='2026-11-01';l['documents'][0]['fields'].append(f);l['documents'][0]['required_field_values'].append('date2')
        with self.assertRaises(ValueError):score(m,l)
        f['distinct_value_group']='date2';r=score(m,l,[row()],[audit()])
        self.assertEqual(r['correct_shadow_acceptance_coverage']['DATE']['denominator'],2)

    def test_missing_field_and_unsafe_extra_prevent_notice_completeness(self):
        m,l=setup();r=score(m,l,[row()],[audit()],ready=True)
        self.assertEqual(r['document_source_completeness']['numerator'],0)
        self.assertEqual(r['runtime_false_readiness']['value'],1)

    def test_loader_reads_terminal_not_provisional_model_results(self):
        m,l=setup()
        with tempfile.TemporaryDirectory() as tmp:
            run=pathlib.Path(tmp);folder=run/'documents'/ID/'native';folder.mkdir(parents=True)
            (folder/'results.json').write_text(json.dumps([row()]))
            terminal,stages=load_terminal(run,m)
            r=evaluate(m,l,terminal,{'schema_version':'round4.evaluation.audits.v1','audits':[]},stages)
            self.assertEqual(r['partial_documents'],1)
            self.assertEqual(r['terminal_accepted_rows'],0)
            (folder.parent/'shadow-observations.json').write_text(json.dumps({'document_id':ID,'observations':[row()]}))
            terminal,stages=load_terminal(run,m)
            self.assertEqual(len(terminal),1)

    def test_zero_scheduled_quota_no_invented_denominator(self):
        r=evaluate({'schema_version':'round4.sources.v1','documents':[]},{'schema_version':'round4.evaluation.labels.v1','documents':[]},{},{'schema_version':'round4.evaluation.audits.v1','audits':[]})
        self.assertEqual(r['scheduled_documents'],0)
        self.assertIsNone(r['document_source_completeness']['value'])

    def test_gold_absence_cannot_certify_runtime_readiness_E01(self):
        m,l=setup([field(state='not_stated'),field('EMAIL',state='not_stated')])
        r=score(m,l,ready=True)
        self.assertEqual(r['document_source_completeness']['numerator'],1)
        self.assertEqual(r['runtime_false_readiness']['numerator'],1)
        self.assertEqual(r['runtime_false_readiness']['denominator'],1)
        self.assertIsNone(score(m,l,ready=False)['runtime_false_readiness']['value'])

    def test_supported_value_does_not_suppress_distinct_unsupported_abstention_E02(self):
        extra=field(state='present_out_of_scope',value='2026-11-01',group='unsupported-date')
        extra['field_id']='date-unsupported'
        m,l=setup([field(),extra,field('EMAIL')])
        r=score(m,l,[row()],[audit()])
        self.assertEqual(r['unsupported_abstention']['numerator'],1)
        self.assertEqual(r['unsupported_abstention']['denominator'],1)
        a=audit(case='c2',group='unsupported-date');a['source_field_id']='date-unsupported';a['scope']='out_of_scope'
        r=score(m,l,[row(value='2026-11-01',case='c2')],[a])
        self.assertEqual(r['unsupported_abstention']['numerator'],0)
        self.assertEqual(score(m,l,terminal=False)['unsupported_abstention']['numerator'],0)
        self.assertEqual(score(m,l,[row()])['unsupported_abstention']['numerator'],0)

    def test_claim_group_rejects_distinct_values_E03(self):
        extra=field(value='2026-11-01',group='different-date');extra['field_id']='date2'
        m,l=setup([field(),extra,field('EMAIL')])
        a=audit(case='c2');a['source_field_id']='date2'
        with self.assertRaisesRegex(ValueError,'materially inconsistent accepted claim_group'):
            score(m,l,[row(),row(value='2026-11-01',case='c2')],[audit(),a])

    def test_claim_group_rejects_same_value_distinct_source_conditions_E03(self):
        extra=field('EMAIL',group='different-email-scope');extra['field_id']='email2';extra['conditions']=['Only comments on Rule R2.']
        m,l=setup([field(),field('EMAIL'),extra])
        a=audit('EMAIL',case='c2');a['source_field_id']='email2'
        with self.assertRaisesRegex(ValueError,'materially inconsistent accepted claim_group'):
            score(m,l,[row('EMAIL'),row('EMAIL',case='c2')],[audit('EMAIL'),a])

    def test_cli_scores_synthetic_terminal_and_requires_manifest_pin(self):
        m,l=setup()
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);run=root/'run';folder=run/'documents'/ID;folder.mkdir(parents=True)
            paths={}
            for name,data in [('manifest',m),('labels',l),('audits',{'schema_version':'round4.evaluation.audits.v1','audits':[audit(),audit('EMAIL',case='c2')]})]:
                paths[name]=root/(name+'.json');paths[name].write_text(json.dumps(data))
            (run/'pins.json').write_text(json.dumps({'manifest_sha256':hashlib.sha256(paths['manifest'].read_bytes()).hexdigest()}))
            (folder/'shadow-observations.json').write_text(json.dumps({'document_id':ID,'observations':[row(),row('EMAIL',case='c2')]}))
            command=[sys.executable,str(pathlib.Path(__file__).with_name('evaluate.py'))]
            for key,path in paths.items():command += ['--'+key,str(path)]
            command += ['--run',str(run),'--output',str(root/'report.json')]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads((root/'report.json').read_bytes())
            self.assertEqual(report['correct_shadow_acceptance_coverage']['pooled']['numerator'],2)
            (run/'pins.json').unlink();command[-1]=str(root/'unbound.json')
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('terminal outputs lack runtime manifest pins',result.stderr)

    def test_unscheduled_terminal_and_source_identity_mismatch_rejected(self):
        m,l=setup();bad=copy.deepcopy(l);bad['documents'][0]['retained_pdf_sha256']='b'*64
        with self.assertRaises(ValueError):score(m,bad)
        with self.assertRaises(ValueError):evaluate(m,l,{'extra':{}},{'schema_version':'round4.evaluation.audits.v1','audits':[]})

if __name__=='__main__':unittest.main()
