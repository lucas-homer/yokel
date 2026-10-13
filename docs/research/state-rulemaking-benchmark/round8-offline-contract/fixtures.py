"""Authored structural/sizing controls, not extractions or semantic success claims."""
import copy,importlib.util,sys
import candidate as c
spec=importlib.util.spec_from_file_location('authored_r7',c.BASE/'round7/pipeline/development_fixtures.py');f=importlib.util.module_from_spec(spec)
prior=sys.modules.get('pipeline');sys.modules['pipeline']=c.p
try:spec.loader.exec_module(f)
finally:
    if prior is None:sys.modules.pop('pipeline',None)
    else:sys.modules['pipeline']=prior

def accessibility():
    s=c.p.make_source('Hearing July 13, 2026. With reasonable advance notice, aids include an interpreter and large-print documents. To request aids, contact help@example.org as soon as possible.','authored-accessibility')
    inv=f.empty_inventory(s);inv['events']=[f.event('hearing','hearing','Hearing July 13, 2026.',[f.timing('date','July 13, 2026','2026-07-13',role='hearing_start')]),f.event('access','other','To request aids, contact help@example.org as soon as possible.',[f.timing('advance','reasonable advance notice',None,kind='relative',role='other',relation='before',anchors=['hearing'],conditions=['aid']),f.timing('asap','as soon as possible',None,kind='relative',role='other',relation='other',conditions=['aid'])])]
    inv['routes']=[f.route('help','help@example.org','help@example.org',['access'],role='information_contact')]
    inv['requirements']=[f.requirement('aid','other','With reasonable advance notice, aids include an interpreter and large-print documents.',['access'],['help'])];inv['requirements'][0]['modality']='conditional'
    return s,inv

def represented_source_ambiguity(coverage):
    s=c.p.make_source('Hearing. For accessibility aids, contact the email address listed below. Contacts: a@example.org and b@example.org.','authored-source-ambiguity')
    inv=f.empty_inventory(s);inv['coverage'].update(status=coverage,rationale='Authored control: source ambiguity explicitly represented; coverage claim remains unverified.' if coverage=='claimed_complete' else 'Authored control: cannot establish full inventory coverage.',evidence=f.evidence(s['source_text']))
    inv['events']=[f.event('access','other','For accessibility aids, contact the email address listed below.')]
    inv['routes']=[f.route('a','a@example.org','a@example.org',[],role='information_contact'),f.route('b','b@example.org','b@example.org',[],role='information_contact')]
    for route in inv['routes']:route['association']='uncertain'
    inv['requirements']=[f.requirement('aid','other','For accessibility aids, contact the email address listed below.',['access'])];inv['requirements'][0].update(modality='conditional',association='uncertain')
    inv['uncertainties']=[dict(id='contact-ambiguity',kind='association',description='The single accessibility email reference does not resolve which of the two printed contacts it means.',event_ids=['access'],route_ids=['a','b'],requirement_ids=['aid'],identity_ids=[],evidence=f.evidence(s['source_text']))]
    return s,inv

def examples():
    rows=[]
    s=c.p.make_source('Comments close Monday, July 13, 2026.','authored-date');i=f.empty_inventory(s);i['events']=[f.event('comment','written_comment',s['source_text'],[f.timing('close','Monday, July 13, 2026','2026-07-13')])];rows.append(('weekday-date',s,i,'authored development'))
    s=c.p.make_source('Hearing at Office.\n10 Main St.\nCity. Present orally.','authored-venue');i=f.empty_inventory(s);i['events']=[f.event('hearing','hearing','Hearing at Office.')];i['routes']=[dict(id='venue',channel='in_person',role='other',components=[dict(id='office',kind='name',literal='Office',evidence=f.evidence('Office')),dict(id='street',kind='address_part',literal='10 Main St.',evidence=f.evidence('10 Main St.')),dict(id='city',kind='address_part',literal='City.',evidence=f.evidence('City.'))],description='Hearing venue',event_ids=['hearing'],alternative_group_id=None,association='source_resolved',evidence=f.evidence(s['source_text']))];rows.append(('multiline-venue',s,i,'authored development'))
    s=c.p.make_source('Hearing. For help call 555 or via email a@b.org. Dial-in is audio only.','authored-help');i=f.empty_inventory(s);i['events']=[f.event('hearing','hearing','Hearing.')];i['routes']=[f.route('phone','555','555',['hearing'],'help',role='information_contact',channel='telephone'),f.route('email','a@b.org','a@b.org',['hearing'],'help',role='information_contact')];i['requirements']=[f.requirement('scope','other','Dial-in is audio only.',['hearing'],['phone'])];i['alternative_groups']=[dict(id='help',purpose='hearing_help',route_ids=['phone','email'],event_ids=['hearing'],requirement_ids=['scope'],association='source_resolved',evidence=f.evidence('For help call 555 or via email a@b.org.'))];rows.append(('qualified-help-alternatives',s,i,'authored development'))
    s=c.p.make_source('Comments may be submitted. Written comments will be publicly posted except confidential material.','authored-disclosure');i=f.empty_inventory(s);i['events']=[f.event('comment','written_comment','Comments may be submitted.')];i['requirements']=[f.requirement('disclosure','publication','Written comments will be publicly posted except confidential material.',['comment'])];rows.append(('disclosure-exception',s,i,'authored development'))
    s,i=accessibility();rows.append(('accessibility-relative-and-asap',s,i,'authored development'))
    s=c.p.make_source('Notice. '+'x'*8000,'authored-size-stress');i=f.empty_inventory(s);i['events']=[f.event('event'+str(n),'other','Notice.') for n in range(8)]
    for event in i['events']:event['description']='x'*4000
    rows.append(('existing-authored-size-stress',s,i,'existing R7 authored sizing pattern; structural only, descriptions not semantically accepted'))
    for coverage in ('claimed_complete','uncertain'):
        s,i=represented_source_ambiguity(coverage);rows.append(('represented-source-ambiguity-'+coverage,s,i,'authored coverage/source-certainty distinction; no semantic acceptance'))
    s,paid=c.observed()
    for relation in ('other','uncertain'):
        i=copy.deepcopy(paid);next(t for e in i['events'] for t in e['timing'] if t['id']=='t-access-request')['dependency_relation']=relation
        rows.append(('paid-diagnostic-'+relation,s,i,'unobserved one-field development copy; semantic acceptance false'))
    return rows
