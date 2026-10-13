#!/usr/bin/env python3
"""Native-first research proposer. No network, gold, PDF parsing or provider calls."""
import argparse
import calendar
import hashlib
import json
import re
from pathlib import Path

VERSION = 'round5-native-proposer-1.0.0'
MONTH = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?'
MONTHS = {m.lower(): i for i,m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i,m in enumerate(calendar.month_abbr) if m})
MONTHS['sept'] = 9
DATE = re.compile(r'\b(?:' + MONTH + r'\s+\d{1,5}(?:\s*[–—-]\s*\d{1,2})?(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))\b', re.I)
EMAIL = re.compile(r'(?<![\w.+-])[\w.!#$%&\'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+', re.I)
COMMENT = re.compile(r'\b(?:comments?|commenting)\b', re.I)
WRITTEN = re.compile(r'\b(?:written\s+comments?|comments?\s+in\s+writing|in\s+writing|deadline\s+for\s+comments?)\b', re.I)
CLOSE = re.compile(r'\b(?:deadline|by|until|through|no later than|on or before|before|close[sd]?|ends?|received)\b', re.I)
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

SOFT_ISSUES = {'condition_scope_requires_semantic_verification','competing_temporal_role_cues','submission_role_unverified','written_comment_role_unverified','multiple_email_candidates_require_role_resolution','multiple_date_candidates_require_role_resolution'}
HARD_ISSUES = {'empty_text','source_scope_incomplete_or_unknown','page_count_mismatch','replacement_character','source_overlimit','case_overlimit','multiple_notice_scopes','participation_lifecycle_unresolved','relative_participation_window_unresolved','conditional_deadline_unresolved','date_year_order_or_range_unresolved','invalid_calendar_date','email_syntax_outside_supported_subset','multiple_same_role_values_scope_unresolved','value_crosses_context_boundary'}
PART = re.compile(r'\b(?:comments?|commenting|testimony|protests?|hearing|deadline|participation|materials in writing)\b', re.I)
FORM = re.compile(r'\b(?:deadline|last date)\b[\s\S]{0,300}\b(?:materials|comments?|submissions?)\b[\s\S]{0,150}\b(?:writing|written)\b',re.I)
DURATION = re.compile(r'\b(?:\d+|[a-z]+(?:-[a-z]+)?)\s*(?:\(\d+\)\s*)?(?:(?:calendar|working|business)\s+)?(?:days?|hours?)\b',re.I)
IF = re.compile(r'\b(?:if|unless|provided that)\b',re.I)
DEMONSTRATIVE = re.compile(r'\bfollowing\s+(?:(?:email|e-mail|mailing|postal|web|proposed)\s+)?(?:address(?:es)?|rules?|chapters?|sections?|documents?|URL)\b',re.I)


def clauses(text):
    """Whole sentences/semicolons, never fixed-length truncation or page crossing."""
    out=[]
    for a,b in blocks(text):
        left=a
        for m in re.finditer(r'[.;!?](?=\s+[A-Z])',text[a:b]):
            end=a+m.end()
            prefix=text[left:end]
            if re.search(r'\b(?:[ap]\.m|Mr|Ms|Dr|Dept)\.$',prefix,re.I):continue
            out.append((left,end));left=end
            while left<b and text[left].isspace():left+=1
        if left<b:out.append((left,b))
    return out


def qualifier_cues(text,a,b):
    piece=text[a:b];ignored=[m.span() for m in DEMONSTRATIVE.finditer(piece)]
    cues=[]
    for pattern,name in ((QUALIFIER,'qualification'),(CLOCK,'clock'),(DURATION,'duration')):
        for m in pattern.finditer(piece):
            if name=='qualification' and any(x<=m.start()<y for x,y in ignored):continue
            cues.append({'kind':name,'span':span(text,a+m.start(),a+m.end())})
    return cues


def propose(text,document_id,*,scope='full_notice',pdf_pages=1,page_map_known=False,channel='native'):
    if channel!='native':raise ValueError('round5 is native-only; no fallback channel')
    contexts=blocks(text);segments=clauses(text);routes=[];blockers=[]
    if not text.strip():blockers.append('empty_text');routes.append('source_review_empty_text')
    if scope!='full_notice':blockers.append('source_scope_incomplete_or_unknown');routes.append('source_review_incomplete_scope')
    pages=text.count('\f')+(1 if text.rsplit('\f',1)[-1].strip() else 0)
    if page_map_known and text.strip() and pages!=pdf_pages:blockers.append('page_count_mismatch');routes.append('source_review_page_mismatch')
    if '\ufffd' in text:blockers.append('replacement_character');routes.append('source_review_corruption')
    if len(text)>30000:blockers.append('source_overlimit');routes.append('review_source_overlimit_no_truncation')
    # Authority/rule references alone do not prove separate windows. Explicit
    # distinct notice headings and distinct close-date proposals still block.
    headings=list(re.finditer(r'(?im)^\s*(?:notice of (?:proposed|public)|rulemaking notice|proposed rulemaking)',text))
    if len(headings)>1:blockers.append('multiple_notice_scopes');routes.append('review_multiple_notice_scopes')
    qualifications=[];lifecycle=[]
    for a,b in segments:
        piece=text[a:b];cues=qualifier_cues(text,a,b)
        participation=bool(PART.search(piece))
        if cues and participation:qualifications.append((a,b,cues))
        for m in LIFECYCLE.finditer(piece):
            applies=bool(participation or re.search(r'\b(?:notice|rulemaking)\b',piece,re.I) or re.search(r'\bproposed rule\s+(?:is|was|has been)\s+(?:withdrawn|superseded|reopened|extended)\b',piece,re.I))
            lifecycle.append({'span':span(text,a+m.start(),a+m.end()),'context_span':span(text,a,b),'association':'participation_or_notice' if applies else 'subject_or_unbound'})
            if applies and not re.search(r'\b(?:may|might|could)\b',piece,re.I):blockers.append('participation_lifecycle_unresolved')
        if participation:
            anchor=any(c['kind']=='qualification' and re.fullmatch(r'(?:within|after|following|upon|prior)',c['span']['quote'],re.I) for c in cues)
            if DURATION.search(piece) and anchor:blockers.append('relative_participation_window_unresolved')
            # A hearing-only contingency is preserved for semantic association,
            # not automatically assigned to a distinct written close date.
            if IF.search(piece) and COMMENT.search(piece) and DATE.search(piece) and CLOSE.search(piece):
                blockers.append('conditional_deadline_unresolved')
    if re.search(r'(?im)^\s*(?:WITHDRAWAL|REOPENING|CORRECTION)\s*(?:NOTICE|$)',text):blockers.append('participation_lifecycle_unresolved')
    blockers=sorted(set(blockers));items=[]
    for kind,pattern in [('date',DATE),('email',EMAIL)]:
        for m in pattern.finditer(text):
            start,end=m.span();a,b=next((a,b) for a,b in segments if a<=start<b)
            parent_a,parent_b=next((x,y) for x,y in contexts if x<=start<y)
            context=text[a:b];prefix=text[a:start]
            previous=list(DATE.finditer(prefix));local_a=a+previous[-1].end() if previous else a
            local=text[local_a:end];form=False;binding_a=a
            if kind=='date':
                is_role=bool(COMMENT.search(text[a:end]) and CLOSE.search(local))
                if not is_role:
                    # Adjacent form header only; never bridge a form-feed/page or
                    # another date-bearing paragraph, nor import its year.
                    prior=[(x,y) for x,y in contexts if y<=parent_a]
                    if prior:
                        x,y=prior[-1];gap=text[y:parent_a]
                        if '\f' not in gap and parent_a-y<20 and FORM.search(text[x:y]) and not DATE.search(text[x:y]):
                            is_role=True;form=True;binding_a=x
                if not is_role:continue
            if kind=='email' and not COMMENT.search(context):
                # A selected form option can follow its separate date value.
                # Carry the nearby label as uncertain association, without
                # borrowing a year/value or crossing page/event boundaries.
                prior=[(x,y) for x,y in contexts if y<=parent_a]
                for x,y in reversed(prior[-2:]):
                    between=text[y:parent_a]
                    if FORM.search(text[x:y]) and not DATE.search(text[x:y]) and '\f' not in between and parent_a-y<600 and not COMPETING.search(between):
                        binding_a=x;form=True;break
            reasons=[x for x in blockers if kind=='date' or x not in ('relative_participation_window_unresolved','conditional_deadline_unresolved')];literal=text[start:end]
            if end>b:reasons.append('value_crosses_context_boundary')
            condition_ranges={(x,y) for x,y,cues in qualifications if parent_a<=x and y<=parent_b}
            # Keep local qualification even without an explicit comment noun:
            # form modes, clocks, and submit-destination contingencies matter.
            if qualifier_cues(text,a,b):condition_ranges.add((a,b))
            if form and qualifier_cues(text,binding_a,parent_a):condition_ranges.add((binding_a,parent_a))
            condition_ranges=sorted(condition_ranges);conditions=[text[x:y] for x,y in condition_ranges]
            if kind=='date':
                value,problem=normalize_date(literal)
                if problem:reasons.append(problem)
                field,role='comment_deadline','written_comment_close'
                claim=f'The actual unconditional absolute written-comment close date in the supplied notice is {literal} (date precision only).'
                if form:reasons.append('written_comment_role_unverified')
                elif not WRITTEN.search(text[a:end]):reasons.append('written_comment_role_unverified')
                if COMPETING.search(text[a:end]) or re.search(r'\b(?:prior|previous|original|historical)\b',text[a:end],re.I):reasons.append('competing_temporal_role_cues')
            else:
                value=literal;field,role='submission_email','written_comment_submission_email'
                claim=f'The literal email address for written-comment/testimony submission in the supplied notice is {literal}.'
                if not (COMMENT.search(context) and SUBMIT.search(context)):reasons.append('submission_role_unverified')
                if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',literal):reasons.append('email_syntax_outside_supported_subset')
            if conditions:claim+=' Qualifications retained verbatim: '+'\n'.join(conditions);reasons.append('condition_scope_requires_semantic_verification')
            ctx=(binding_a,b);evidence_ranges=sorted(set([(start,end),ctx]+condition_ranges))
            case_id='case-'+sha(f'{VERSION}:{document_id}:{field}:{start}:{end}'.encode())[:16]
            case={'case_id':case_id,'source_text':text,'candidate':{'field':field,'value':value,'claim':claim,'target':document_id,'role':role,'conditions':conditions},'evidence':[span(text,x,y) for x,y in evidence_ranges],'source_id':document_id,'source_locator':'native'}
            if len(case['evidence'])>12 or len(conditions)>12 or len(claim)>3000 or any(len(c)>3000 for c in conditions) or any(len(e['quote'])>15000 for e in case['evidence']) or len(json.dumps(case,ensure_ascii=False).encode())>50000:reasons.append('case_overlimit')
            items.append({'case_id':case_id,'field':field,'raw_literal':literal,'normalized_value':value,'precision':'date' if kind=='date' else 'literal_email','timezone':None,'value_span':span(text,start,end),'context_span':span(text,*ctx),'condition_spans':[span(text,x,y) for x,y in condition_ranges],'pdf_page':text.count('\f',0,start)+1 if page_map_known else None,'form_association':form,'binding_strength':'explicit_close' if kind=='date' and not form and 'competing_temporal_role_cues' not in reasons else 'requires_role_verification','issues':reasons,'case':case,'emit_case':not any(x in reasons for x in ('source_overlimit','case_overlimit','value_crosses_context_boundary'))})
    for field in ('comment_deadline','submission_email'):
        subset=[i for i in items if i['field']==field]
        if not subset:routes.append('source_review_missing_'+field+'_candidate')
        if len({i['normalized_value'] for i in subset if i['normalized_value'] is not None})>1:
            for item in subset:item['issues'].append(('multiple_same_role_values_scope_unresolved' if all(i['binding_strength']=='explicit_close' for i in subset) else 'multiple_date_candidates_require_role_resolution') if field=='comment_deadline' else 'multiple_email_candidates_require_role_resolution')
            routes.append('review_multiple_'+field+'_values')
    for item in items:
        item['issues']=sorted(set(item['issues']));item['soft_issues']=[x for x in item['issues'] if x in SOFT_ISSUES];item['hard_issues']=[x for x in item['issues'] if x not in SOFT_ISSUES]
        item['verifier_eligible']=bool(item['emit_case'] and not item['hard_issues']);item['field_disposition']='requires_semantic_verification' if item['verifier_eligible'] else 'review'
    for issue in blockers:routes.append('review_'+issue)
    return {'document_id':document_id,'channel':'native','pipeline_version':VERSION,'text_sha256':sha(text.encode()),'source_scope':scope,'full_source_context_map':{'start':0,'end':len(text),'truncated':False},'native_page_count':pages,'routes':sorted(set(routes)),'candidates':items,'lifecycle_cues':lifecycle,'qualification_cues':[{'context_span':span(text,a,b),'cues':cues} for a,b,cues in qualifications],'production_eligible':False,'source_fidelity':'not_established','document_completeness':'requires_source_audit'}

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
        if unit['channel'] != 'native' or unit['scope'] not in ('full_notice','slice','unknown'):
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
    summary = {'documents':len(records),'verifier_cases':len(cases),'candidates':sum(len(r['candidates']) for r in records),'verifier_eligible_candidates':sum(i['verifier_eligible'] for r in records for i in r['candidates']),'review_fields':sum(i['field_disposition']=='review' for r in records for i in r['candidates']),'route_counts':{k:sum(k in r['routes'] for r in records) for k in sorted({k for r in records for k in r['routes']})},'manifest_sha256':sha(manifest_path.read_bytes()),'pipeline_version':VERSION,'provider_calls':0,'production_eligible':False,'files_sha256':{p.name:sha(p.read_bytes()) for p in output.iterdir()}}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True,help='new output directory; never overwrite frozen run')
    p.add_argument('--channel',choices=['native'],default='native')
    args = p.parse_args()
    print(json.dumps(run(args.manifest.resolve(),args.source_root.resolve(),args.output.resolve(),args.channel),indent=2))
