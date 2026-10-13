"""Hand-authored old-source development controls; not model extraction outputs."""
import json
from pathlib import Path
import pipeline as p


def evidence(quote, occurrence=None, context=None):
    return [{'quote':quote,'occurrence':occurrence,'context':context}]


def empty_inventory(source):
    return dict(schema_version='round6.source_inventory.v1', document_id=source['document_id'],
                source_text_sha256=source['source_text_sha256'],
                coverage=dict(status='uncertain',rationale='Hand-authored development fixture; no live extraction or completeness claim.',evidence=evidence(source['source_text'][:100])),
                events=[],routes=[],requirements=[],identities=[],uncertainties=[])


def event(id,phase,quote,timing=None):
    return dict(id=id,phase=phase,description=phase,timing=timing or [],evidence=evidence(quote))


def timing(id,raw,value,kind='absolute_date',role=None,relation='none',anchors=None,conditions=None):
    return dict(id=id,kind=kind,role=role or ('closes' if kind in ('absolute_date','conditional') else 'hearing_start' if kind=='clock' else 'other'),dependency_relation=relation,anchor_event_ids=anchors or [],condition_requirement_ids=conditions or [],raw=raw,value=value,evidence=evidence(raw))


def route(id,literal,quote,events,group=None,role='submission',channel='email'):
    return dict(id=id,channel=channel,role=role,literal=literal,event_ids=events,alternative_group=group,association='source_resolved',evidence=evidence(quote))


def requirement(id,kind,quote,events=None,routes=None):
    return dict(id=id,kind=kind,modality='informational' if kind=='publication' else 'conditional' if kind in ('extension','late_submission') else 'mandatory',semantic_class='disclosure' if kind=='publication' else 'instruction',text=quote,event_ids=events or [],route_ids=routes or [],association='source_resolved',evidence=evidence(quote))


def source_from_round5(doc):
    path=Path(__file__).resolve().parents[2]/'round5/execution/run/documents'/doc/'native/pipeline-record.json'
    record=json.loads(path.read_text())
    source=p.make_source(record['candidates'][0]['case']['source_text'],doc,pdf_pages=record['native_page_count'],page_map_known=True)
    return source,empty_inventory(source)


def ky_fixture():
    source,inv=source_from_round5('doc-a97c415f9644')
    close='Written comments shall be accepted through March 31, 2025.'
    hearing='A public hearing on this\nadministrative regulation shall be held on Tuesday, March 25, 2025, at 11:00 Eastern Time\nat KDVA Headquarters Office, 1111 Louisville Rd., Suite B, Frankfort, Kentucky 40601.'
    relative='Individuals interested in being heard at this hearing shall notify this agency in writing by\nfive workdays prior to the hearing, of their intent to attend.'
    inv['events']=[event('written','written_comment',close,[timing('close','March 31, 2025','2025-03-31')]),
                   event('hearing','hearing',hearing,[timing('hearing-date','March 25, 2025','2025-03-25',role='hearing_start'),timing('hearing-clock','11:00 Eastern Time',None,'clock')]),
                   event('intent','hearing_intent',relative,[timing('intent-relative','five workdays prior to the hearing',None,'relative',role='hearing_intent_cutoff',relation='before',anchors=['hearing'])])]
    emails='Juan.Renaud@ky.gov or Mark.Bowman@ky.gov.'
    inv['routes']=[route('juan','Juan.Renaud@ky.gov',emails,['written','intent'],'email-alternatives'),
                   route('mark','Mark.Bowman@ky.gov',emails,['written','intent'],'email-alternatives'),
                   route('postal','1111 Louisville Rd., Suite B, Frankfort, Kentucky\n40601','1111 Louisville Rd., Suite B, Frankfort, Kentucky\n40601',['written','intent'],channel='postal')]
    inv['requirements']=[
        requirement('send-to-contact','hearing_procedure','Send written\nnotification of intent to be heard at the public hearing or written comments on the proposed\nadministrative regulation to the contact person.',['written','intent'],['juan','mark','postal']),
        requirement('notify-in-writing','format',relative,['intent']),
        requirement('hearing-cancellation','timing','If no notification of intent to\nattend the hearing is received by that date, the hearing may be cancelled.',['hearing','intent']),
        requirement('public-hearing','hearing_procedure','This hearing is\nopen to the public. Any person who wishes to be heard will be given an opportunity to\ncomment on the proposed administrative regulation.',['hearing']),
        requirement('transcript','hearing_procedure','A transcript of the public hearing will\nnot be made unless a written request for a transcript is made.',['hearing'])]
    inv['identities']=[dict(id='rule',kind='rule',literal='17 KAR 1:030',relation='canonical',event_ids=['written','hearing','intent'],evidence=evidence('17 KAR 1:030. Nurse Loan Repayment Program.'))]
    inv['requirements'][2]['modality']='conditional'
    return source,inv


def write_fixture(output):
    source,inv=ky_fixture();assembled=p.assemble(source,inv)
    if not assembled['validation']['valid']:raise ValueError(assembled['validation']['errors'])
    common=p.verification_payload(source,assembled)
    Path(output).write_text(json.dumps(dict(kind='hand_authored_round5_development_only',source=source,inventory=inv,assembled=assembled,paired=common),indent=2,ensure_ascii=False)+'\n')
    inventory_request=p.inventory_request(source);strong_request=p.verification_request(source,assembled)
    questions=p.jev_question_specs()
    return dict(source_codepoints=len(source['source_text']),source_pages=source['pdf_pages'],
                inventory_request_utf8_bytes=len(inventory_request['user'].encode()),
                inventory_system_and_user_utf8_bytes=len((inventory_request['system']+inventory_request['user']).encode()),
                common_payload_utf8_bytes=len(p.canonical(common['payload']).encode()),
                strong_verifier_user_utf8_bytes=len(strong_request['user'].encode()),
                strong_system_and_user_utf8_bytes=len((strong_request['system']+strong_request['user']).encode()),
                jev_longest_question_utf8_bytes=max(len(q['question'].encode()) for q in questions),
                jev_five_questions_utf8_bytes=sum(len(q['question'].encode()) for q in questions))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    print(json.dumps(write_fixture(args.output),indent=2))
