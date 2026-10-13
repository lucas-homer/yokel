#!/usr/bin/env python3
"""Native-first research proposer. No network, gold, PDF parsing or provider calls."""
import argparse
import calendar
import hashlib
import json
import re
from pathlib import Path

VERSION = 'round4-proposer-1.0.0'
MONTH = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?'
MONTHS = {m.lower(): i for i,m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i,m in enumerate(calendar.month_abbr) if m})
MONTHS['sept'] = 9
DATE = re.compile(r'\b(?:' + MONTH + r'\s+\d{1,5}(?:\s*[–—-]\s*\d{1,2})?(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))\b', re.I)
EMAIL = re.compile(r'(?<![\w.+-])[\w.!#$%&\'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+', re.I)
COMMENT = re.compile(r'\b(?:comments?|commenting)\b', re.I)
WRITTEN = re.compile(r'\b(?:written\s+comments?|comments?\s+in\s+writing|in\s+writing|deadline\s+for\s+comments?)\b', re.I)
CLOSE = re.compile(r'\b(?:deadline|by|until|through|no later than|close[sd]?|ends?|received)\b', re.I)
SUBMIT = re.compile(r'\b(?:submit\w*|send|received|email|e-mail|electronic\s+mail)\b', re.I)
COMPETING = re.compile(r'\b(?:hearing|effective|publication|filed|filing)\b', re.I)
QUALIFIER = re.compile(r'\b(?:if|unless|provided that|within|after|following|upon|prior|previous|original|extended|extension|withdrawn|superseded|reopened|reopening)\b', re.I)
CLOCK = re.compile(r'\b(?:\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?|noon|midnight)\b',re.I)
LIFECYCLE = re.compile(r'\b(?:withdrawn|withdrawal|superseded|reopened|reopening|extended|extension|correction)\b', re.I)
KEYS = {'document_id','channel','text_path','text_sha256','pdf_path','pdf_sha256','pdf_pages','scope','native_page_map_known'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def normalize_date(value):
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        y,m,d = map(int,value.split('-'))
    else:
        match = re.fullmatch(r'(' + MONTH + r')\s+(\d{1,5})(?:st|nd|rd|th)?\s*,?\s*(\d{4})',value,re.I)
        if not match:
            return None, 'date_year_order_or_range_unresolved'
        m,d,y = MONTHS[match[1].lower().rstrip('.')],int(match[2]),int(match[3])
    if not 1 <= y <= 9999 or not 1 <= m <= 12 or not 1 <= d <= calendar.monthrange(y,m)[1]:
        return None, 'invalid_calendar_date'
    return f'{y:04d}-{m:02d}-{d:02d}', None

def blocks(text):
    start = 0
    result = []
    for match in re.finditer(r'\f|\n[ \t]*\n',text):
        if match.start() > start:
            result.append((start,match.start()))
        start = match.end()
    if start < len(text):
        result.append((start,len(text)))
    return result

def span(text,start,end):
    return {'start':start,'end':end,'quote':text[start:end]}

def propose(text, document_id, *, scope='full_notice', pdf_pages=1, page_map_known=False, channel='native'):
    contexts = blocks(text)
    routes, blockers = [], []
    empty = not text.strip()
    if empty:
        routes.append('parser_fallback_empty_text')
        blockers.append('empty_text')
    if scope != 'full_notice':
        blockers.append('source_scope_incomplete_or_unknown')
        routes.append('parser_fallback_scope_incomplete_or_unknown')
    native_pages = text.count('\f') + (1 if text.rsplit('\f',1)[-1].strip() else 0)
    if page_map_known and not empty and native_pages != pdf_pages:
        blockers.append('page_count_mismatch')
        routes.append('parser_fallback_page_count_mismatch')
    if '\ufffd' in text:
        blockers.append('replacement_character')
        routes.append('parser_fallback_text_corruption_signal')
    if re.search(r'(?<!\S)\S*@\s*\n|\b(?:https?://)\S*\n\S+',text):
        routes.append('parser_fallback_wrapped_destination_signal')
    if len(text) > 30000:
        blockers.append('source_overlimit')
        routes.append('review_source_overlimit_no_truncation')
    # Multiple explicit notice headings or named rule/chapter identities do not
    # get silently merged into a document-wide participation window.
    headings = re.findall(r'(?im)^\s*(?:notice of (?:proposed|public)|rulemaking notice|proposed rulemaking)',text)
    identities = set(x.lower() for x in re.findall(r'\b(?:rule|chapter)\s+([A-Z]\d+[\w.-]*|\d+(?:[.-]\d+)*)\b',text,re.I))
    if len(headings) > 1 or len(identities) > 1:
        blockers.append('multiple_notice_or_rule_scopes')
        routes.append('review_multiple_notice_or_rule_scopes')
    if LIFECYCLE.search(text):
        blockers.append('lifecycle_scope_unresolved')
        routes.append('review_lifecycle_scope')
    items = []
    for kind, pattern in [('date',DATE),('email',EMAIL)]:
        for match in pattern.finditer(text):
            start,end = match.span()
            a,b = next((a,b) for a,b in contexts if a <= start < b)
            context = text[a:b]
            # Restrict date-binding cues to the segment since the previous date
            # in this paragraph. The full paragraph/notice still reaches Jev.
            prefix = text[a:start]
            previous = list(DATE.finditer(prefix))
            local_a = a + previous[-1].end() if previous else a
            local = text[max(local_a,start-350):end]
            is_date_role = bool(COMMENT.search(local) and CLOSE.search(local))
            if kind == 'date' and not is_date_role:
                continue
            literal = text[start:end]
            reasons = list(blockers)
            if kind == 'date':
                value,problem = normalize_date(literal)
                if problem:
                    reasons.append(problem)
                if not WRITTEN.search(local):
                    reasons.append('written_comment_role_unverified')
                if COMPETING.search(local):
                    reasons.append('competing_temporal_role_cues')
                field,role = 'comment_deadline','written_comment_close'
                claim = f'The written-comment close date in the supplied notice is {literal} (date precision only).'
            else:
                value = literal  # Exact local-part/domain, no repair or case folding.
                field,role = 'submission_email','written_comment_submission_email'
                claim = f'The email address for written-comment submission in the supplied notice is {literal}.'
                if not (COMMENT.search(context) and SUBMIT.search(context)):
                    reasons.append('submission_role_unverified')
                if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',literal):
                    reasons.append('email_syntax_outside_supported_subset')
            qualifier_blocks = [(x,y) for x,y in contexts if (QUALIFIER.search(text[x:y]) or CLOCK.search(text[x:y])) and (x == a or COMMENT.search(text[x:y]) or re.search(r'\b(?:hearing|deadline)\b',text[x:y],re.I))]
            conditions = [text[x:y] for x,y in qualifier_blocks]
            if conditions:
                claim += ' Qualifications retained verbatim: ' + '\n'.join(conditions)
                reasons.append('condition_scope_requires_semantic_verification')
            evidence_ranges = sorted(set([(start,end),(a,b)] + qualifier_blocks))
            evidence = [span(text,x,y) for x,y in evidence_ranges]
            case_id = 'case-' + sha(f'{document_id}:{channel}:{field}:{start}:{end}'.encode())[:16]
            case = {'case_id':case_id,'source_text':text,'candidate':{'field':field,'value':value,'claim':claim,'target':document_id,'role':role,'conditions':conditions},'evidence':evidence,'source_id':document_id,'source_locator':channel}
            if len(evidence) > 12 or len(conditions) > 12 or len(claim) > 3000 or any(len(c)>3000 for c in conditions) or any(len(e['quote'])>15000 for e in evidence) or len(json.dumps(case,ensure_ascii=False).encode()) > 50000:
                reasons.append('case_overlimit')
            item = {'case_id':case_id,'field':field,'raw_literal':literal,'normalized_value':value,'precision':'date' if kind == 'date' else 'literal_email','timezone':None,'value_span':span(text,start,end),'context_span':span(text,a,b),'condition_spans':[span(text,x,y) for x,y in qualifier_blocks],'pdf_page':text.count('\f',0,start)+1 if page_map_known else None,'issues':sorted(set(reasons)),'case':case,'emit_case':not ('source_overlimit' in reasons or 'case_overlimit' in reasons)}
            items.append(item)
    # Distinct proposed values for one document-level role require identity/scope
    # resolution, not arbitrary first/last selection.
    for field in ('comment_deadline','submission_email'):
        subset = [i for i in items if i['field'] == field]
        if not subset:
            routes.append('parser_fallback_missing_' + field + '_candidate')
        if len({i['normalized_value'] for i in subset if i['normalized_value'] is not None}) > 1:
            routes.append('review_multiple_' + field + '_values')
            for item in subset:
                item['issues'].append('multiple_same_role_values_scope_unresolved' if field == 'comment_deadline' else 'multiple_email_candidates_require_role_resolution')
        for item in subset:
            item['issues'] = sorted(set(item['issues']))
            soft = {'condition_scope_requires_semantic_verification','written_comment_role_unverified','competing_temporal_role_cues','submission_role_unverified','multiple_email_candidates_require_role_resolution'}
            item['soft_issues'] = [x for x in item['issues'] if x in soft]
            item['hard_issues'] = [x for x in item['issues'] if x not in soft]
            item['field_disposition'] = 'review' if item['issues'] else 'shadow_eligible_text_only'
            if item['issues']:
                routes.append('review_candidate_' + field)
    if COMMENT.search(text) and not any(i['field'] == 'comment_deadline' for i in items):
        routes.append('parser_fallback_unresolved_participation_date_evidence')
    return {'document_id':document_id,'channel':channel,'pipeline_version':VERSION,'text_sha256':sha(text.encode()),'source_scope':scope,'full_source_context_map':{'start':0,'end':len(text),'truncated':False},'native_page_count':native_pages,'routes':sorted(set(routes)),'candidates':items,'production_eligible':False,'source_fidelity':'not_established','document_completeness':'requires_source_audit'}

def validate_manifest(manifest):
    if set(manifest) != {'schema_version','documents'} or manifest['schema_version'] != 'round4.sources.v1' or not isinstance(manifest['documents'],list) or not manifest['documents']:
        raise ValueError('invalid source manifest')
    seen = set()
    for unit in manifest['documents']:
        if set(unit) != KEYS:
            raise ValueError('extra/missing source keys; evaluator data forbidden')
        if not re.fullmatch(r'doc-[a-f0-9]{12}',unit['document_id']) or (unit['document_id'],unit['channel']) in seen:
            raise ValueError('nonopaque/duplicate document channel')
        seen.add((unit['document_id'],unit['channel']))
        if unit['channel'] not in ('native','fallback') or unit['scope'] not in ('full_notice','slice','unknown'):
            raise ValueError('invalid channel/scope')
        if type(unit['pdf_pages']) is not int or unit['pdf_pages'] < 1 or type(unit['native_page_map_known']) is not bool:
            raise ValueError('invalid mechanical metadata')
        for key in ('pdf_sha256','text_sha256'):
            if not isinstance(unit[key],str) or not re.fullmatch(r'[a-f0-9]{64}',unit[key]):
                raise ValueError('invalid hash')
        for key in ('pdf_path','text_path'):
            if not isinstance(unit[key],str) or not unit[key] or Path(unit[key]).is_absolute():
                raise ValueError('paths must be nonempty and relative')

def contained_path(base,root,value):
    path = (base/value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('source path outside explicit root')
    return path

def run(manifest_path,root,output,channel='native'):
    manifest = json.loads(manifest_path.read_bytes())
    validate_manifest(manifest)
    records,cases = [],[]
    for unit in manifest['documents']:
        if unit['channel'] != channel:
            raise ValueError('separate invocation/manifest required for fallback channel')
        pdf = contained_path(manifest_path.parent,root,unit['pdf_path']).read_bytes()
        raw = contained_path(manifest_path.parent,root,unit['text_path']).read_bytes()
        if sha(pdf) != unit['pdf_sha256'] or sha(raw) != unit['text_sha256']:
            raise ValueError('source hash changed: '+unit['document_id'])
        record = propose(raw.decode('utf-8'),unit['document_id'],scope=unit['scope'],pdf_pages=unit['pdf_pages'],page_map_known=unit['native_page_map_known'],channel=channel)
        record['input'] = unit
        for item in record['candidates']:
            if item['emit_case']:
                cases.append(item['case'])
            del item['case']
        records.append(record)
    output.mkdir(parents=True,exist_ok=False)
    (output/'cases.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in cases))
    (output/'traces.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    summary = {'documents':len(records),'verifier_cases':len(cases),'candidates':sum(len(r['candidates']) for r in records),'shadow_eligible_fields':sum(i['field_disposition']=='shadow_eligible_text_only' for r in records for i in r['candidates']),'review_fields':sum(i['field_disposition']=='review' for r in records for i in r['candidates']),'route_counts':{k:sum(k in r['routes'] for r in records) for k in sorted({k for r in records for k in r['routes']})},'manifest_sha256':sha(manifest_path.read_bytes()),'pipeline_version':VERSION,'provider_calls':0,'production_eligible':False,'files_sha256':{p.name:sha(p.read_bytes()) for p in output.iterdir()}}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True,help='new output directory; never overwrite frozen run')
    p.add_argument('--channel',choices=['native','fallback'],default='native')
    args = p.parse_args()
    print(json.dumps(run(args.manifest.resolve(),args.source_root.resolve(),args.output.resolve(),args.channel),indent=2))
