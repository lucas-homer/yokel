#!/usr/bin/env python3
"""Offline developmental evidence extraction. No references, providers or production writes."""
import argparse
import calendar
import hashlib
import json
import re
from pathlib import Path

VERSION = 'native-evidence-0.1.1'
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTH = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?'
MONTHS['sept'] = 9
PATTERNS = {
    'date': re.compile(r'\b(?:' + MONTH + r'\s+\d{1,5}(?:\s*[–—-]\s*\d{1,2})?(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:\d{4}|\d{2}))\b', re.I),
    'time': re.compile(r'\b(?:\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)|noon|midnight)(?:\s*(?:EST|EDT|CST|CDT|MST|MDT|PST|PDT|ET|CT|MT|PT))?(?!\w)', re.I),
    'duration': re.compile(r'\b(?:\d+|twenty|thirty|forty|sixty)\s*(?:[-–]\s*)?(?:(?:calendar|working|business)\s+)?days?\b', re.I),
    'email': re.compile(r'(?<![\w.+-])[\w.!#$%&\'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+', re.I),
    'url': re.compile(r'https?://[^\s<>"\[\]]+', re.I),
}
# These are lexical role cues, not assertions about legal effect or window identity.
CUES = {
    'comment': r'\b(?:comments?|commenting|submissions?)\b',
    'hearing': r'\b(?:hearings?|oral testimony)\b',
    'effective': r'\b(?:effective|take effect)\b',
    'filing': r'\b(?:filed|filing)\b',
    'publication': r'\b(?:published|publication)\b',
    'conditional': r'\b(?:if|unless|upon|following|after|within)\b',
    'proposed': r'\b(?:proposed|anticipated|tentative)\b',
    'historical': r'\b(?:previous|prior|previously|original|formerly)\b',
    'close': r'\b(?:deadline|until|through|by|close|closes|end|ends|ending|received|no later than)\b',
}
CUE_RE = {k: re.compile(v, re.I) for k, v in CUES.items()}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def span(text, start, end):
    """Offsets count Unicode code points in unchanged UTF-8 decoded native text."""
    return {'start': start, 'end': end, 'literal': text[start:end],
            'page': text.count('\f', 0, start) + 1,
            'line': text.count('\n', 0, start) + 1}

def normalize_date(literal):
    if '/' in literal:
        return None, ['numeric_date_order_or_century_unresolved']
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', literal):
        parts = [int(x) for x in literal.split('-')]
        values = [parts]
    else:
        m = re.fullmatch(r'(' + MONTH + r')\s+(\d{1,5})(?:\s*[–—-]\s*(\d{1,2}))?(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?', literal, re.I)
        if not m:
            return None, ['unparsed_date']
        if not m[4]:
            return None, ['year_missing']
        mon = MONTHS[m[1].lower().rstrip('.')]
        first, last, year = int(m[2]), int(m[3] or m[2]), int(m[4])
        if last < first:
            return None, ['invalid_date_range']
        values = [[year, mon, first], [year, mon, last]] if m[3] else [[year, mon, first]]
    for year, mon, day in values:
        if year < 1 or mon < 1 or mon > 12 or day < 1 or day > calendar.monthrange(year, mon)[1]:
            return None, ['invalid_calendar_date']
    dates = [f'{y:04}-{m:02}-{d:02}' for y, m, d in values]
    return {'calendar_dates': dates, 'kind': 'range' if len(dates) > 1 else 'date', 'timezone': None}, []

def role_evidence(text, start, end):
    # Bounded left context, including at most the current and previous line.
    # Never borrow cues across a page boundary. Distance is reported for audit.
    left = max(0, start - 180, text.rfind('\f', 0, start) + 1)
    lines = [m.end() for m in re.finditer('\n', text[left:start])]
    if len(lines) > 1:
        left += lines[-2]
    context = text[left:end]
    cues = []
    for role, pattern in CUE_RE.items():
        for m in pattern.finditer(context):
            cues.append({'cue': role, 'span': span(text, left + m.start(), left + m.end())})
    labels = {c['cue'] for c in cues}
    roles = []
    if 'comment' in labels:
        roles.append('comment_close_candidate' if 'close' in labels else 'comment_related_unresolved')
    for role in ('hearing', 'effective', 'filing', 'publication'):
        if role in labels:
            roles.append(role + '_candidate')
    # Conditions and historical qualifiers can follow the value. Inspect up to
    # 180 code points on this line, without borrowing role nouns from that tail.
    right = min(len(text), end + 180)
    for delimiter in ('\n', '\f'):
        boundary = text.find(delimiter, end, right)
        if boundary >= 0:
            right = min(right, boundary)
    for modifier in ('conditional', 'proposed', 'historical'):
        for m in CUE_RE[modifier].finditer(text[end:right]):
            cues.append({'cue': modifier, 'span': span(text, end + m.start(), end + m.end())})
            labels.add(modifier)
    modifiers = sorted(labels & {'conditional', 'proposed', 'historical'})
    return sorted(roles), modifiers, cues

def extract(text, fixture_id='synthetic'):
    candidates = []
    for kind, regex in PATTERNS.items():
        for match in regex.finditer(text):
            start, end = match.span()
            if kind == 'url':
                while end > start and text[end - 1] in '.,;:)':
                    end -= 1
            literal = text[start:end]
            roles, modifiers, cues = role_evidence(text, start, end) if kind in ('date', 'time', 'duration') else ([], [], [])
            normalized, issues = (None, [])
            if kind == 'date':
                normalized, issues = normalize_date(literal)
            if kind == 'duration':
                issues = ['anchor_and_counting_rule_unresolved']
            if kind == 'time':
                issues = ['date_binding_unresolved']
                if not re.search(r'\b(?:EST|EDT|CST|CDT|MST|MDT|PST|PDT|ET|CT|MT|PT)\b', literal):
                    issues.append('timezone_missing')
            if kind in ('date', 'time', 'duration') and len(roles) != 1:
                issues.append('role_missing' if not roles else 'multiple_role_cues')
            if kind in ('date', 'time', 'duration'):
                issues.append('notice_scope_and_role_binding_unverified')
            if modifiers:
                issues.append('temporal_modifier_requires_review')
            identity = f'{fixture_id}:{kind}:{start}:{end}:{literal}'.encode()
            candidates.append({'candidate_id': sha(identity)[:24], 'kind': kind,
                'span': span(text, start, end), 'normalization': normalized,
                'role_candidates': roles, 'modifiers': modifiers, 'cue_evidence': cues,
                'unresolved': sorted(set(issues)), 'status': 'research_candidate'})
    candidates.sort(key=lambda c: (c['span']['start'], c['kind']))
    routes = []
    if not text.strip():
        routes.append('parser_fallback_empty_native_text')
    else:
        temporal = [c for c in candidates if c['kind'] in ('date', 'time', 'duration')]
        if any(c['unresolved'] for c in temporal):
            routes.append('temporal_evidence_review')
        if not any('comment_close_candidate' in c['role_candidates'] for c in temporal):
            routes.append('missing_explicit_comment_close_evidence')
        closes = [c for c in temporal if 'comment_close_candidate' in c['role_candidates']]
        values = {json.dumps(c['normalization'], sort_keys=True) for c in closes if c['normalization']}
        if len(values) > 1:
            routes.append('multiple_comment_values_scope_unresolved')
        bases = {m.lower() for m in re.findall(r'\b(calendar|working|business)\s+days?\b', text, re.I)}
        if len(bases) > 1:
            routes.append('mixed_duration_bases_scope_unresolved')
        if re.search(r'\b(?:check one|check all|effective date|final adoption)\b', text, re.I):
            routes.append('visual_marks_or_lifecycle_require_source_review')
        if not candidates:
            routes.append('no_supported_candidates')
    return {'fixture_id': fixture_id, 'extractor_version': VERSION,
            'text_sha256': sha(text.encode()), 'offset_unit': 'unicode_code_point',
            'candidates': candidates, 'routes': sorted(set(routes)),
            'resolved_close_utc': None, 'decision': 'escalate' if routes else 'candidate_only',
            'source_fidelity': 'not_established_from_native_text',
            'production_eligible': False}

def run(manifest_path, output_path):
    manifest = json.loads(manifest_path.read_text())
    root = manifest_path.parents[2]  # benchmark root: round3/baseline/manifest.json
    records = []
    for unit in manifest['units']:
        pdf = (root / unit['pdf_path']).read_bytes()
        data = (root / unit['text_path']).read_bytes()
        if sha(pdf) != unit['pdf_sha256'] or sha(data) != unit['text_sha256']:
            raise ValueError('Frozen input changed: ' + unit['fixture_id'])
        record = extract(data.decode('utf-8'), unit['fixture_id'])
        record['input'] = unit
        records.append(record)
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n')
    summary = {'documents': len(records), 'candidate_count': sum(len(r['candidates']) for r in records),
               'decisions': {k: sum(r['decision'] == k for r in records) for k in ('escalate', 'candidate_only')},
               'routes': {k: sum(k in r['routes'] for r in records) for k in sorted({x for r in records for x in r['routes']})},
               'results_sha256': sha(output_path.read_bytes()), 'manifest_sha256': sha(manifest_path.read_bytes()),
               'developmental_only': True, 'accuracy_not_measured': True}
    output_path.with_name('summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('manifest.json'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('results.json'))
    args = parser.parse_args()
    run(args.manifest.resolve(), args.output.resolve())
