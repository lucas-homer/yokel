"""Hand-authored old-source development controls; not model extraction outputs."""
import json
from pathlib import Path
import pipeline as p


def evidence(quote, occurrence=None, context=None):
    return [{'quote':quote,'occurrence':occurrence,'context':context}]


def empty_inventory(source):
    return dict(schema_version='round7.source_inventory.v1', document_id=source['document_id'],
                source_text_sha256=source['source_text_sha256'],
                coverage=dict(status='uncertain',rationale='Hand-authored development fixture; no live extraction or completeness claim.',evidence=evidence(source['source_text'][:100])),
                events=[],routes=[],requirements=[],identities=[],uncertainties=[],alternative_groups=[])


def event(id,phase,quote,timing=None):
    return dict(id=id,phase=phase,description=phase,timing=timing or [],evidence=evidence(quote))


def timing(id,raw,value,kind='absolute_date',role=None,relation='none',anchors=None,conditions=None):
    return dict(id=id,kind=kind,role=role or ('closes' if kind in ('absolute_date','conditional') else 'hearing_start' if kind=='clock' else 'other'),dependency_relation=relation,anchor_event_ids=anchors or [],condition_requirement_ids=conditions or [],raw=raw,value=value,evidence=evidence(raw))


def route(id,literal,quote,events,group=None,role='submission',channel='email'):
    return dict(id=id,channel=channel,role=role,components=[dict(id=id+'-component',kind='endpoint',literal=literal,evidence=evidence(quote))],description=None,event_ids=events,alternative_group_id=group,association='source_resolved',evidence=evidence(quote))


def requirement(id,kind,quote,events=None,routes=None):
    return dict(id=id,kind=kind,modality='informational' if kind=='publication' else 'conditional' if kind in ('extension','late_submission') else 'mandatory',semantic_class='disclosure' if kind=='publication' else 'instruction',text=quote,event_ids=events or [],route_ids=routes or [],association='source_resolved',evidence=evidence(quote))



def verdict(source, assembled):
    return dict(schema_version='round7.record_verdict.v1',document_id=source['document_id'],payload_sha256=p.verification_payload(source,assembled)['payload_sha256'],
        completeness=dict(label='complete',reason='Synthetic development control',evidence=evidence(source['source_text'])),
        source_identity=dict(label='resolved',reason='Synthetic development control',evidence=evidence(source['source_text'])),
        assessments=[dict(item_id=i['id'],support='supported',association='matched',requirements='preserved',reason='Synthetic development control',evidence=evidence(source['source_text'])) for _,i in p.all_items(assembled['record'])],missing_items=[],contradictions=[])
