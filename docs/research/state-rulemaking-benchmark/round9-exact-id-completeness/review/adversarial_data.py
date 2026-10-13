"""Independent synthetic mutation corpus. No runtime import or live capabilities.

Rebound review objects exist only in memory to test invariants below hash binding.
They are not real endorsements and must never overwrite approved-development-audits.json.
"""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def hv(v):return hashlib.sha256(canon(v)).hexdigest()
def read(name):return json.loads((ROOT/name).read_bytes())
def context(audit_id='rule_assertion/semantic_positive'):
    family_id,variant_id=audit_id.split('/')
    family=next(f for f in read('protocol/development-fixtures.json')['fixtures'] if f['fixture_id']==family_id)
    variant=next(v for v in family['variants'] if v['id']==variant_id)
    audit=next(a for a in read('protocol/development-audit-inputs.json')['audits'] if a['audit_id']==audit_id)
    review=read('approved-development-audits.json')
    return dict(source=variant.get('source_text_override',family['source_text']),record=variant['record'],audit=audit,review=review)

def seal(c):
    """Make explicit TEST-ONLY envelope consistent, retaining mutated semantic contents."""
    a=c['audit'];a['record_sha256']=hv(c['record']);a['source_reference_sha256']=hv(a['source_reference'])
    entry=dict(audit_id=a['audit_id'],audit_sha256=hv(a),source_reference_sha256=a['source_reference_sha256'],record_sha256=a['record_sha256'],source_text_sha256=a['source_text_sha256'],decision='approved',primary_reviewer='adversarial-test-only-primary',independent_reviewer='adversarial-test-only-reviewer',review_note='ISOLATED TEST INPUT ONLY: synthetic presumed review permits testing validation below hash binding. Not a real adjudication, approval, or source-truth claim.')
    c['review']={'schema_version':'round9.offline-audit-review.v1','entries':[entry]}
    return c

def row(c,pointer):return next(x for x in c['audit']['candidate_claim_checks'] if x['record_pointer']==pointer)
def change(c,pointer,value):
    item=c['record'];parts=pointer.split('/')[1:]
    for key in parts[:-1]:item=item[int(key)] if isinstance(item,list) else item[key]
    item[parts[-1]]=value;row(c,pointer)['value_sha256']=hv(value)

def audit_cases():
    cases=[]
    def add(name,mutate,expected='unverified',reseal=True,base='rule_assertion/semantic_positive'):
        c=context(base);mutate(c)
        if reseal:seal(c)
        cases.append((name,c,expected))
    add('audit_missing',lambda c:c.update(audit=None),reseal=False)
    add('review_missing',lambda c:c.update(review=None),reseal=False)
    add('pending_original_review',lambda c:c.update(review=read('protocol/offline-audit-review.json')),reseal=False)
    add('stale_audit_digest',lambda c:c['audit']['provenance'].update(limitations='UNAPPROVED MUTATION'),reseal=False)
    add('source_unit_row_missing',lambda c:c['audit']['source_dispositions'].pop())
    add('source_unit_row_duplicate',lambda c:c['audit']['source_dispositions'].append(copy.deepcopy(c['audit']['source_dispositions'][0])))
    add('source_unit_id_duplicate',lambda c:c['audit']['source_reference']['units'].append(copy.deepcopy(c['audit']['source_reference']['units'][0])))
    add('source_scope_partial',lambda c:c['audit']['source_reference']['scope'].update(status='partial'))
    add('source_range_short',lambda c:c['audit']['source_reference']['scope'].update(reviewed_end=len(c['source'])-1))
    add('source_scope_unresolved',lambda c:c['audit']['source_reference']['scope']['unresolved_questions'].append('Unread source attachment'))
    add('source_scope_exclusion',lambda c:c['audit']['source_reference']['scope']['exclusions'].append('Unreviewed final sentence'))
    add('claim_row_missing',lambda c:c['audit']['candidate_claim_checks'].pop())
    add('claim_row_duplicate',lambda c:c['audit']['candidate_claim_checks'].append(copy.deepcopy(c['audit']['candidate_claim_checks'][0])))
    add('claim_pointer_alias',lambda c:c['audit']['candidate_claim_checks'][0].update(record_pointer='/events/00/phase'))
    add('claim_scope_incomplete',lambda c:c['audit']['claim_coverage'].update(status='partial'))
    add('claim_unreviewed_pointer',lambda c:c['audit']['claim_coverage']['unreviewed_pointers'].append('/events/0/description'))
    add('claim_value_hash_stale',lambda c:c['audit']['candidate_claim_checks'][0].update(value_sha256='0'*64))
    add('supported_claim_unbacked',lambda c:c['audit']['candidate_claim_checks'][0].update(source_unit_ids=[]))
    add('matched_source_no_pointers',lambda c:c['audit']['source_dispositions'][0].update(semantic_record_pointers=[],candidate_claim_ids=[]))
    add('source_evidence_wrong',lambda c:c['audit']['source_reference']['units'][0]['source_evidence'][0].update(quote='Not in the source'))
    add('source_evidence_boolean_offset',lambda c:c['audit']['source_reference']['units'][0]['source_evidence'][0].update(start=False))
    add('source_dependency_missing',lambda c:c['audit']['source_reference']['units'][0].update(required_source_unit_ids=['does-not-exist']))
    add('source_dependency_self',lambda c:c['audit']['source_reference']['units'][0].update(required_source_unit_ids=['src-agency']))
    def cycle(c):
        c['audit']['source_reference']['units'][0]['required_source_unit_ids']=['src-hearing'];c['audit']['source_reference']['units'][1]['required_source_unit_ids']=['src-agency']
    add('source_dependency_cycle',cycle)
    def no_backlink(c):row(c,'/identities/0/literal')['source_unit_ids']=['src-hearing']
    add('matched_mapping_no_backlink',no_backlink)
    def unsupported(c):
        change(c,'/events/0/description',c['record']['events'][0]['description']+' All submissions require a $500 fee.')
        row(c,'/events/0/description')['disposition']='unsupported'
        # Avoid an inconsistent matched row hiding the known unsupported claim.
        for r in c['audit']['source_dispositions']:
            if '/events/0/description' in r['semantic_record_pointers']:r['disposition']='mismatched'
    add('unsupported_compound_addition',unsupported,expected='not_complete')
    def unknown_over_defect(c):
        unsupported(c);row(c,'/identities/0/relation')['disposition']='unknown'
    add('unknown_precedes_known_defect',unknown_over_defect)
    add('unclear_modality_cannot_be_supported',lambda c:change(c,'/requirements/0/modality','unclear'),base='modality_preservation/optional_positive')
    add('unknown_channel_cannot_be_supported',lambda c:change(c,'/routes/0/channel','unknown'),base='full_alternatives/full_group_positive')
    add('uncertain_association_cannot_be_supported',lambda c:change(c,'/routes/0/association','uncertain'),base='full_alternatives/full_group_positive')
    add('unresolved_identity_cannot_be_supported',lambda c:change(c,'/identities/0/relation','unresolved'))
    add('unknown_event_phase_cannot_be_supported',lambda c:change(c,'/events/0/phase','unknown'))
    add('unknown_coverage_host_guard',lambda c:c['record']['coverage'].update(status='uncertain'))
    def null_support(c):
        r=next(x for x in c['audit']['source_dispositions'] if x['source_unit_id']=='src-email')
        r['semantic_record_pointers']=['/routes/0/alternative_group_id'];r['candidate_claim_ids']=[row(c,'/routes/0/alternative_group_id')['claim_id']]
        row(c,'/routes/0/alternative_group_id')['source_unit_ids']=['src-email']
    add('null_field_cannot_discharge_source_obligation',null_support,base='modality_preservation/optional_positive')
    # Intentionally bypass only binding integrity inside synthetic tests, not semantic checks.
    return cases
