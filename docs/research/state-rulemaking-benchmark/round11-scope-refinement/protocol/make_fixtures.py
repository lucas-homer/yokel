"""Reproduce private synthetic annotations; never a semantic classifier."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
policy = {
 'version': 'round11.offline.scope-role.v2',
 'unit_keys': ['id','kind','value','modality','condition','qualifications','dependencies','evidence','uncertainty'],
 'facet_keys': ['kind','value','modality','condition','qualifications'],
 'kinds': ['identity','rule_transition','phase','timing','endpoint','endpoint_role','instruction','relationship','background'],
 'modalities': ['descriptive','mandatory','advisory','optional','prohibited','unknown'],
 'purposes': ['submit_written','testify_orally','attend_hearing','questions','accommodations','view_material','ancillary_contact'],
 'relationship_semantics': ['substitution','independent_permissions','joint_requirement','sequence','applies_to'],
 'scope_categories': ['required_participation','identifying_context','retained_background','unresolved_scope'],
 'scope_bases': ['participation_function','identifies_proceeding','substantive_background_only','uncertain_source_function'],
 'mapping_statuses': ['matched','missing','mismatched','unknown'],
 'allowed_scope_by_kind': {},
 'audit_keys': ['status','source_sha256','operative_sha256','reviewed_refs','unsupported_refs','unknown_refs'],
 'scope_basis_by_category': {'required_participation': 'participation_function', 'identifying_context': 'identifies_proceeding', 'retained_background': 'substantive_background_only', 'unresolved_scope': 'uncertain_source_function'},
 'source_only_classification': True,
 'inventory_mutation_allowed': False,
 'record_presence_scope_basis_allowed': False,
 'semantic_equivalence_requires_independent_review': True,
 'unresolved_scope_blocks_completeness': True,
 'unsupported_record_additions_separate_audit': True,
 'model_evaluation_claims': False,
 'live_compatibility': 'unverified',
 'production_ready': False
}
for kind in policy['kinds']:
 policy['allowed_scope_by_kind'][kind] = (
  ['identifying_context','unresolved_scope'] if kind in ['identity','rule_transition'] else
  ['required_participation','retained_background','unresolved_scope'] if kind in ['endpoint','background'] else
  ['required_participation','unresolved_scope'])
(ROOT/'policy.json').write_text(json.dumps(policy,indent=2)+'\n')
from validator import digest, facet

def unit(uid,kind,value,quote,modality='descriptive',condition='unconditional',deps=None,qual=None,uncertainty='none'):
 return dict(id=uid,kind=kind,value=value,modality=modality,condition=condition,qualifications=qual or [],dependencies=deps or [],evidence=[dict(quote=quote,occurrence=1)],uncertainty=uncertainty)

def case(source,units):
 scopes={}
 for u in units:
  cat='identifying_context' if u['kind'] in ['identity','rule_transition'] else 'retained_background' if u['kind']=='background' else 'required_participation'
  basis={'identifying_context':'identifies_proceeding','retained_background':'substantive_background_only','required_participation':'participation_function'}[cat]
  scopes[u['id']]=dict(category=cat,basis=basis,reason='Synthetic source-only adjudication of '+u['kind'],evidence=copy.deepcopy(u['evidence']))
 c=dict(source=source,inventory=units,classified_inventory=copy.deepcopy(units),scopes=scopes,
        operative={u['id']:facet(u) for u in units},mappings={u['id']:dict(status='matched',refs=[u['id']],reason='Synthetic exact operative recovery') for u in units},
        source_review={},record_audit=dict(status='not_run',source_sha256='',operative_sha256='',reviewed_refs=[],unsupported_refs=[],unknown_refs=[]))
 freeze(c)
 return c

def freeze(c):
 c['source_review']=dict(status='source_only_frozen',source_sha256=hashlib.sha256(c['source'].encode('utf-8')).hexdigest(),inventory_sha256=digest(c['inventory']),scopes_sha256=digest(c['scopes']))

def sync(c):
 c['classified_inventory']=copy.deepcopy(c['inventory']);freeze(c)

fixtures=[]
def add(name,c,expected):
 fixtures.append(dict(id=name,case=c,expected=expected,interpretation='Private synthetic annotation contract; no observed model behavior'))

s='The rule protects wetlands. Written comments are due May 3. For questions only call 555-0100. For accommodation requests email access@example.test.'
us=[unit('b','background','The rule protects wetlands.','The rule protects wetlands.'),unit('d','timing','May 3','Written comments are due May 3.'),unit('p','endpoint','555-0100','555-0100'),unit('q','endpoint_role',dict(endpoint='p',purpose='questions'),'For questions only call 555-0100.',deps=['p'],qual=['questions only']),unit('a','endpoint','access@example.test','access@example.test'),unit('ar','endpoint_role',dict(endpoint='a',purpose='accommodations'),'For accommodation requests email access@example.test.',deps=['a'])]
base=case(s,us)
add('complete_positive',copy.deepcopy(base),dict(valid=True,required_scope_status='all_required_inventoried_units_matched',record_fidelity='unverified'))
c=copy.deepcopy(base);c['mappings']['b']=dict(status='missing',refs=[],reason='Background omitted');del c['operative']['b'];add('background_missing_not_participation_defect',c,dict(valid=True,required_scope_status='all_required_inventoried_units_matched',background_diagnostics={'b':'missing'}))
c=copy.deepcopy(base);c['scopes']['d'].update(category='retained_background',basis='substantive_background_only');freeze(c);add('exclusion_hides_deadline',c,dict(valid=False,error='required_kind_excluded'))
c=copy.deepcopy(base);c['classified_inventory']=[u for u in c['classified_inventory'] if u['id']!='d'];add('classifier_deletes_inventory',c,dict(valid=False,error='inventory_changed'))
c=copy.deepcopy(base);c['scopes']['d']['basis']='record_has_no_deadline';freeze(c);add('record_absence_cannot_exclude',c,dict(valid=False,error='scope enum'))
c=copy.deepcopy(base);c['inventory'][0]['kind']='mixed';sync(c);add('mixed_background_instruction_requires_split',c,dict(valid=False,error='atomize mixed or unsupported kind'))
c=copy.deepcopy(base);c['mappings']['d']=dict(status='missing',refs=[],reason='Deadline missing');del c['operative']['d'];add('split_mixed_paragraph_deadline_missing',c,dict(valid=True,required_scope_status='not_complete',required_defects=['d']))
c=copy.deepcopy(base);c['operative']['q']['value']['purpose']='submit_written';add('phone_questions_only_not_submission',c,dict(valid=False,error='facet_mismatch'))
c=copy.deepcopy(base);c['operative']['ar']['value']['purpose']='questions';add('accommodations_not_questions',c,dict(valid=False,error='facet_mismatch'))
# Multiple roles share one endpoint, but cannot be bundled into one role assertion.
s='Send written comments or questions to office@example.test.'
m=case(s,[unit('e','endpoint','office@example.test','office@example.test'),unit('wr','endpoint_role',dict(endpoint='e',purpose='submit_written'),s,deps=['e']),unit('qr','endpoint_role',dict(endpoint='e',purpose='questions'),s,deps=['e'])])
add('same_endpoint_two_atomic_purposes',copy.deepcopy(m),dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
c=copy.deepcopy(m);c['inventory'][1]['value']['purpose']=['submit_written','questions'];sync(c);add('bundled_purposes_rejected',c,dict(valid=False,error='invalid role purpose'))
# Shared contact block ambiguity remains unresolved; not telephone submission or query-only truth.
s='Written comments and questions should be submitted to: office, phone 555-0110, mail@example.test.'
a=case(s,[unit('p','endpoint','555-0110','555-0110'),unit('r','endpoint_role',dict(endpoint='p',purpose='questions'),s,modality='unknown',deps=['p'],uncertainty='Shared contact block does not establish phone function')])
a['scopes']['r'].update(category='unresolved_scope',basis='uncertain_source_function',reason='Ambiguous shared contact role');a['mappings']['r']=dict(status='unknown',refs=['r'],reason='Function unresolved');freeze(a)
add('shared_contact_ambiguous_scope',a,dict(valid=True,required_scope_status='unverified',unresolved_scope=['r']))
c=copy.deepcopy(base);c['scopes']['b'].update(category='unresolved_scope',basis='uncertain_source_function',reason='Function ambiguous');freeze(c);add('uncertain_scope_blocks_complete_even_when_matched',c,dict(valid=True,required_scope_status='unverified',unresolved_scope=['b']))
# Conditional advisory force is independent of deadline and endpoint recovery.
s='If you plan to speak, preregistration is strongly encouraged.'
a=case(s,[unit('i','instruction','preregister',s,modality='advisory',condition='if you plan to speak')]);add('conditional_advisory_positive',copy.deepcopy(a),dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
c=copy.deepcopy(a);c['operative']['i']['modality']='mandatory';add('advisory_not_mandatory',c,dict(valid=False,error='facet_mismatch'))
c=copy.deepcopy(a);c['operative']['i']['condition']='unconditional';add('condition_loss',c,dict(valid=False,error='facet_mismatch'))
# Rule transitions identify the proceeding rather than expanding to all substantive rationale.
s='Repeal NR 107. Repeal NR 109. Recreate NR 107.'
a=case(s,[unit('t1','rule_transition','repeal NR 107','Repeal NR 107.'),unit('t2','rule_transition','repeal NR 109','Repeal NR 109.'),unit('t3','rule_transition','recreate NR 107','Recreate NR 107.')]);c=copy.deepcopy(a);c['operative']['t2']['value']='NR 109';add('rule_identifier_without_transition',c,dict(valid=False,error='facet_mismatch'));add('atomic_rule_transitions_positive',a,dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
# Actual substitution must preserve members, purpose, evidence and qualifications.
s='Attend via Zoom Z or phone P or phone Q; each permits hearing attendance. Zoom requires registration.'
us=[]
for i,v in enumerate(['Z','P','Q']):
 uid='e'+str(i);rid='r'+str(i);q=['Zoom requires registration'] if i==0 else []
 us.extend([unit(uid,'endpoint',v,v),unit(rid,'endpoint_role',dict(endpoint=uid,purpose='attend_hearing'),s,deps=[uid],qual=q)])
rel=dict(members=['r0','r1','r2'],purpose='attend_hearing',semantics='substitution',equivalence_evidence=[dict(quote='each permits hearing attendance',occurrence=1)])
us.append(unit('g','relationship',rel,s,deps=rel['members'],qual=['Zoom requires registration']))
a=case(s,us);add('substitution_with_qualifications_positive',copy.deepcopy(a),dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
c=copy.deepcopy(a);c['operative']['g']['value']['members']=['r1','r2'];add('relationship_subset_not_full',c,dict(valid=False,error='facet_mismatch'))
c=copy.deepcopy(a);c['operative']['g']['qualifications']=[];add('alternative_qualification_loss',c,dict(valid=False,error='facet_mismatch'))
c=copy.deepcopy(a);c['inventory'][-1]['value']['equivalence_evidence']=[];sync(c);add('unsupported_equivalence_no_evidence',c,dict(valid=False,error='evidence required'))
# Two independently retained viewing permissions do not imply substitution.
s='The rule may be viewed at site A. The rule may also be viewed at office B.'
us=[]
for i,v in enumerate(['site A','office B']):
 us.extend([unit('e'+str(i),'endpoint',v,v),unit('r'+str(i),'endpoint_role',dict(endpoint='e'+str(i),purpose='view_material'),s,modality='optional',deps=['e'+str(i)])])
a=case(s,us);add('independent_view_permissions_no_group_required',copy.deepcopy(a),dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
rel=dict(members=['r0','r1'],purpose='view_material',semantics='independent_permissions',equivalence_evidence=[])
a=case(s,us+[unit('g','relationship',rel,s,deps=['r0','r1'])]);add('explicit_independent_permissions_positive',copy.deepcopy(a),dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
c=copy.deepcopy(a);c['operative']['g']['value']['semantics']='substitution';add('permissions_not_actual_substitution',c,dict(valid=False,error='facet_mismatch'))
# References/glyphs keep closure unknown despite locally retained literals.
s='Join at https://example.test/Il. Use the form linked above.'
a=case(s,[unit('e','endpoint','https://example.test/Il','https://example.test/Il',uncertainty='Image I/l ambiguous; native text does not settle reference'),unit('r','endpoint_role',dict(endpoint='e',purpose='attend_hearing'),'Join at https://example.test/Il.',deps=['e']),unit('f','instruction','use referenced form','Use the form linked above.',deps=['r'],uncertainty='Referenced form target unavailable')])
for uid in ['e','r','f']:a['mappings'][uid]=dict(status='unknown',refs=[uid],reason='Reference closure unresolved')
add('glyph_and_reference_closure_unknown',copy.deepcopy(a),dict(valid=True,required_scope_status='unverified',required_unknown=['e','r','f']))
c=copy.deepcopy(a);c['mappings']['e']['status']='matched';add('native_literal_does_not_clear_glyph',c,dict(valid=False,error='uncertain_matched'))
# An ancillary coordinator remains participation contact even under a background heading.
s='Regulatory analysis. Small-business coordinator: coordinator@example.test for assistance.'
a=case(s,[unit('e','endpoint','coordinator@example.test','coordinator@example.test'),unit('r','endpoint_role',dict(endpoint='e',purpose='ancillary_contact'),s,deps=['e'])]);add('coordinator_heading_does_not_demote',copy.deepcopy(a),dict(valid=True,required_scope_status='all_required_inventoried_units_matched'))
c=copy.deepcopy(a);c['scopes']['r'].update(category='retained_background',basis='substantive_background_only');freeze(c);add('coordinator_background_exclusion_rejected',c,dict(valid=False,error='required_kind_excluded'))
c=copy.deepcopy(base);c['operative']['invented']={'kind':'timing','value':'June 1','modality':'mandatory','condition':'unconditional','qualifications':[]};add('unsupported_addition_separate_unrun_audit',copy.deepcopy(c),dict(valid=True,required_scope_status='all_required_inventoried_units_matched',record_fidelity='unverified'))
c['record_audit']=dict(status='reviewed',source_sha256=hashlib.sha256(c['source'].encode()).hexdigest(),operative_sha256=digest(c['operative']),reviewed_refs=list(c['operative']),unsupported_refs=['invented'],unknown_refs=[]);add('unsupported_addition_separate_reviewed_audit',c,dict(valid=True,required_scope_status='all_required_inventoried_units_matched',record_fidelity='not_faithful',unsupported_record_refs=['invented']))
c=copy.deepcopy(base);c['source_review']=dict(status='unverified',source_sha256='',inventory_sha256='',scopes_sha256='');add('all_matches_without_source_review_unverified',c,dict(valid=True,required_scope_status='unverified'))
# Source-only additions and candidate-only changes have distinct frozen universes.
c=copy.deepcopy(base);c['source'] += ' If you speak, registration closes May 2.'
u=unit('new','instruction','registration closes May 2','If you speak, registration closes May 2.',modality='mandatory',condition='if you speak')
c['inventory'].append(u);c['scopes']['new']=dict(category='required_participation',basis='participation_function',reason='New source-only instruction',evidence=copy.deepcopy(u['evidence']))
c['mappings']['new']=dict(status='missing',refs=[],reason='Unchanged candidate lacks new source instruction');sync(c)
add('source_only_new_obligation_unchanged_candidate',c,dict(valid=True,required_scope_status='not_complete',required_defects=['new']))
s='Wetland permit holders must register before speaking. Other wetland policy protects habitat.'
c=case(s,[unit('i','instruction','register before speaking','Wetland permit holders must register before speaking.',modality='mandatory',condition='wetland permit holders who speak'),unit('b','background','Other wetland policy protects habitat.','Other wetland policy protects habitat.')]);c['operative']['i']['condition']='all speakers';add('background_supplied_condition_not_discarded',c,dict(valid=False,error='facet_mismatch'))
c=copy.deepcopy(base);c['source_review']['source_sha256']='0'*64;add('wrong_source_binding',c,dict(valid=False,error='source_review_hash'))
(ROOT/'fixtures.json').write_text(json.dumps(fixtures,ensure_ascii=False,indent=2)+'\n')
print('Wrote',len(fixtures),'synthetic fixtures')
