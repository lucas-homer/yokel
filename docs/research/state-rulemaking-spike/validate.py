#!/usr/bin/env python3
"""Offline research-envelope/evidence checks; not a legal-truth validator."""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
PREDICATES = {
    'agency', 'title', 'event_type', 'rule_action', 'rule_citations', 'filing_date',
    'publication_date', 'comment_open', 'comment_close', 'hearing_time',
    'hearing_status', 'effective_date', 'withdraws', 'comment_duration',
    'hearing_request_duration', 'operational_policy_date',
}
TEMPORAL = {
    'filing_date', 'publication_date', 'comment_open', 'comment_close',
    'hearing_time', 'effective_date', 'comment_duration',
    'hearing_request_duration', 'operational_policy_date',
}
METHODS = {'deterministic', 'model', 'manual_visual', 'manual_text'}
SUBJECTS = {'proceeding', 'notice', 'participation_window', 'hearing', 'instrument'}
REPRESENTATIONS = {'raw_json', 'html', 'markdown', 'native_text', 'pdf', 'image'}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def temporal_errors(value):
    errors = []
    if not isinstance(value, dict):
        return ['temporal value must be an object']
    kind = value.get('kind')
    required = {
        'date': {'date'},
        'instant': {'utc_instant'},
        'local_datetime': {'date', 'time', 'timezone_text', 'iana_zone', 'utc_instant'},
        'relative': {'duration', 'unit', 'anchor', 'day_basis', 'computed_close'},
    }
    if kind not in required:
        return ['unsupported temporal kind']
    missing = required[kind] - value.keys()
    if missing:
        errors.append('missing temporal fields: ' + ', '.join(sorted(missing)))
    if kind in {'date', 'local_datetime'}:
        date = value.get('date')
        try:
            if not isinstance(date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
                raise ValueError()
            dt.date.fromisoformat(date)
        except (ValueError, TypeError):
            errors.append('invalid calendar date')
    if kind == 'date' and any(value.get(k) is not None for k in ['time', 'utc_instant']):
        errors.append('date-only value must not fabricate a time/instant')
    if kind == 'local_datetime':
        if not isinstance(value.get('time'), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value['time']):
            errors.append('invalid local clock time')
        for key in ['timezone_text', 'iana_zone']:
            if value.get(key) is not None and not nonempty(value[key]):
                errors.append(key + ' must be nonempty text or null')
    instant = value.get('utc_instant')
    if kind == 'instant' or instant is not None:
        try:
            if not isinstance(instant, str) or not instant.endswith('Z'):
                raise ValueError()
            parsed = dt.datetime.fromisoformat(instant.replace('Z', '+00:00'))
            if parsed.utcoffset() != dt.timedelta(0):
                raise ValueError()
        except (ValueError, TypeError):
            errors.append('invalid UTC instant')
    if kind == 'relative':
        duration = value.get('duration')
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            errors.append('relative duration must be a positive number')
        if value.get('unit') != 'days':
            errors.append('relative unit must be days')
        for key in ['anchor', 'day_basis']:
            if value.get(key) is not None and not nonempty(value[key]):
                errors.append(key + ' must be nonempty text or null')
        if value.get('computed_close') is not None:
            errors.append('this spike has no approved relative-date calculation policy')
    return errors


def check_observation(o, artifacts, lane):
    errors = []
    required = {'schema_version', 'observation_id', 'jurisdiction', 'source_record_id',
                'subject', 'predicate', 'value', 'evidence', 'method', 'review_state', 'warnings'}
    if not isinstance(o, dict):
        return ['observation must be an object']
    missing = required - o.keys()
    if missing:
        errors.append('missing fields: ' + ', '.join(sorted(missing)))
    if o.get('schema_version') != 'state-spike-v1':
        errors.append('wrong schema version')
    if not nonempty(o.get('observation_id')):
        errors.append('missing observation id')
    if not isinstance(o.get('jurisdiction'), str) or not re.fullmatch(r'US-[A-Z]{2}', o['jurisdiction']):
        errors.append('invalid jurisdiction')
    if o.get('source_record_id') is not None and not nonempty(o['source_record_id']):
        errors.append('source_record_id must be nonempty or null')
    subject = o.get('subject')
    if not isinstance(subject, dict) or subject.get('kind') not in SUBJECTS or not nonempty(subject.get('id')):
        errors.append('invalid subject')
    method = o.get('method')
    if not isinstance(method, dict) or method.get('kind') not in METHODS or not nonempty(method.get('name')) or not nonempty(method.get('version')):
        errors.append('invalid method')
    if o.get('review_state') not in {'candidate', 'needs_review', 'reviewed_for_research'}:
        errors.append('invalid research review state')
    if not isinstance(o.get('warnings'), list) or any(not nonempty(s) for s in o.get('warnings', [])):
        errors.append('warnings must be an array of text')
    predicate, value = o.get('predicate'), o.get('value')
    if predicate not in PREDICATES:
        errors.append('unknown predicate')
    elif predicate in TEMPORAL:
        errors += temporal_errors(value)
        if predicate.endswith('_duration') and isinstance(value, dict) and value.get('kind') != 'relative':
            errors.append('duration predicates require relative values')
    elif predicate == 'rule_citations':
        if not isinstance(value, list) or not value or any(not nonempty(v) for v in value):
            errors.append('rule citations must be a nonempty text array')
    elif predicate == 'withdraws':
        if not isinstance(value, dict) or not nonempty(value.get('target_source_record_id')) or not nonempty(value.get('scope')):
            errors.append('withdrawal requires target and scope')
    elif not nonempty(value):
        errors.append('predicate requires nonempty text')
    vocabularies = {
        'event_type': {'proposal', 'withdrawal'},
        'rule_action': {'new', 'amendment', 'repeal', 'adoption_by_reference'},
        'hearing_status': {'scheduled', 'not_scheduled', 'canceled'},
    }
    if predicate in vocabularies and (not isinstance(value, str) or value not in vocabularies[predicate]):
        errors.append('value is outside the canonical research vocabulary')
    evidence = o.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        errors.append('missing evidence')
        evidence = []
    for ev in evidence:
        if not isinstance(ev, dict):
            errors.append('evidence must be an object')
            continue
        artifact = artifacts.get(ev.get('artifact_id'))
        if artifact is None:
            errors.append('unknown evidence artifact')
            continue
        if not nonempty(ev.get('locator')) or not nonempty(ev.get('quote')):
            errors.append('evidence requires locator and quote')
        if ev.get('support') == 'text_exact':
            try:
                body = safe_path(lane, artifact['path']).read_text(encoding='utf-8')
                if not isinstance(ev.get('quote'), str) or ev['quote'] not in body:
                    errors.append('evidence quote not found verbatim')
            except (UnicodeDecodeError, OSError, ValueError):
                errors.append('text evidence artifact unreadable or invalid')
        elif ev.get('support') == 'visual_review':
            if not isinstance(method, dict) or method.get('kind') != 'manual_visual':
                errors.append('visual review must be explicitly manual')
            if artifact.get('representation') not in {'pdf', 'image'}:
                errors.append('visual evidence must reference PDF or image')
        else:
            errors.append('unsupported evidence support mode')
    return errors


def safe_path(lane, relative):
    if not isinstance(relative, str) or pathlib.Path(relative).is_absolute():
        raise ValueError('artifact path must be relative')
    target = (lane / relative).resolve()
    if not target.is_relative_to(lane.resolve()):
        raise ValueError('artifact path escapes lane')
    return target


def validate_lane(lane):
    manifest = json.loads((lane / 'manifest.json').read_text())
    if not isinstance(manifest, list):
        raise ValueError('manifest must be an array')
    artifacts, failures = {}, []
    required = {'artifact_id', 'path', 'sha256', 'source_url', 'retrieved_at',
                'media_type', 'representation', 'source_lineage', 'collector', 'is_inherited'}
    for a in manifest:
        aid = a.get('artifact_id')
        problems = []
        if required - a.keys():
            problems.append('missing manifest fields: ' + ', '.join(sorted(required-a.keys())))
        if not nonempty(aid) or aid in artifacts:
            problems.append('missing/duplicate artifact id')
        if a.get('representation') not in REPRESENTATIONS:
            problems.append('unknown artifact representation')
        if not isinstance(a.get('is_inherited'), bool):
            problems.append('is_inherited must be boolean')
        if not nonempty(a.get('source_lineage')):
            problems.append('source lineage required')
        try:
            p = safe_path(lane, a.get('path'))
            if hashlib.sha256(p.read_bytes()).hexdigest() != a.get('sha256'):
                problems.append('artifact hash mismatch')
        except (ValueError, OSError):
            problems.append('artifact path invalid/missing')
        if problems:
            failures.append({'artifact_id': aid, 'errors': problems})
        artifacts[aid] = a
    observations = json.loads((lane / 'observations.json').read_text())
    if not isinstance(observations, list):
        raise ValueError('observations must be an array')
    ids = set()
    for o in observations:
        problems = check_observation(o, artifacts, lane)
        oid = o.get('observation_id')
        if oid in ids:
            problems.append('duplicate observation id')
        ids.add(oid)
        if problems:
            failures.append({'observation_id': oid, 'errors': problems})
    return {
        'lane': lane.name, 'artifact_count': len(manifest), 'observation_count': len(observations),
        'method_counts': {m: sum(o.get('method', {}).get('kind') == m for o in observations) for m in sorted(METHODS)},
        'exact_quote_count': sum(ev.get('support') == 'text_exact' for o in observations for ev in o.get('evidence', [])),
        'visual_evidence_count': sum(ev.get('support') == 'visual_review' for o in observations for ev in o.get('evidence', [])),
        'failures': failures, 'passed': not failures,
        'semantic_entailment': 'requires separate source review',
        'production_readiness': 'not established',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('lanes', nargs='*', type=pathlib.Path)
    ap.add_argument('--output', type=pathlib.Path)
    args = ap.parse_args()
    lanes = args.lanes or [ROOT / name for name in ['ct', 'wa', 'pdf']]
    results = [validate_lane(lane) for lane in lanes]
    report = {'schema_version': 1, 'purpose': 'offline structural and evidence-integrity checks',
              'passed': all(r['passed'] for r in results), 'lanes': results}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
