#!/usr/bin/env python3
"""Mississippi sealed comparison. Deterministic, stdlib only; never adjudicates.

Run from any directory. Reads only MS inputs plus the frozen pass inputs under
.census-passes/MS/inputs (bulletin slices for index dates). VA revision
materiality is retained: temporal entries match by role, then local_value; only
decisive fields queue; wording stays reference-only in pairs.wording_diffs.
MS additions: FILED-stamp/oral-box/handwritten-ID visual items (owner decision
14), stamp/index mismatches (sign-off 2c) and relative-close carry-in accounting.
"""
import collections
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
STATE = OUT.parent
ROOT = OUT.parents[5]
INPUTS = ROOT / '.census-passes/MS/inputs'
TYPES = ('notice', 'opportunity', 'proceeding', 'update', 'rejected_candidate')
TRIGGERS = ('disagreement', 'lifecycle_ambiguity', 'date_ambiguity', 'visual_mark', 'missing_source', 'identity', 'scope')
FIELDS = {'notice': ('proceeding_ids', 'cohorts'),
          'opportunity': ('opportunity_type', 'hearing_status', 'proceeding_id', 'cohorts'),
          'update': ('event_type', 'target_opportunity_ids', 'cohorts'),
          'proceeding': (), 'rejected_candidate': ()}
DECISIVE_TEMP = ('local_value', 'precision', 'status', 'iana_zone', 'cutoff', 'receipt_or_postmark')
ROLES = {'open', 'close', 'hearing_start', 'hearing_end'}
START, END = date(2026, 5, 18), date(2026, 8, 17)
CARRY_START = date(2026, 4, 13)
MONTHS = {m: i for i, m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split(), 1)}
STAMP = re.compile(r"FILED(?: stamp reading)?\s*'?\s*([A-Z]{3})\s*(\d{1,2})[^\d]{0,3}(\d{4}|20\[\d\d\])?")
HAND = re.compile(r"handwritten(?: accession)?(?: below stamp)?(?: reads)?\s*'?\s*(\d{4,6})")


def canonical(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def norm(v):
    if isinstance(v, str):
        return ' '.join(v.split()).casefold()
    if isinstance(v, list):
        return sorted({canonical(norm(x)): norm(x) for x in v}.values(), key=canonical)
    if isinstance(v, dict):
        return {k: norm(x) for k, x in sorted(v.items())}
    return v


def read(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def write(name, rows):
    with (OUT / name).open('w') as f:
        for row in rows:
            f.write(canonical(short_quotes(row)) + '\n')


def short_quotes(value):
    """Compare full sealed values, but expose at most 200 quoted characters."""
    if isinstance(value, list):
        return [short_quotes(x) for x in value]
    if not isinstance(value, dict):
        return value
    result, truncated = {}, {}
    for key, item in value.items():
        if key in ('quote', 'quote_or_mark_description', 'literal') and isinstance(item, str) and len(item) > 200:
            result[key] = item[:200]
            truncated[key] = {'full_length': len(item), 'full_utf8_sha256': hashlib.sha256(item.encode()).hexdigest(),
                              'reference': 'Complete wording remains in the sealed input record.'}
        else:
            result[key] = short_quotes(item)
    if truncated:
        result['reference_only_truncation'] = truncated
    return result


def evidence(r):
    p = r['payload']
    return r['evidence'] + p.get('before_evidence', []) + p.get('after_evidence', []) + [
        e for t in p.get('temporal', []) for e in t.get('evidence', [])]


def pointers(records):
    result = {}
    for r in records:
        for e in evidence(r):
            p = {k: e[k] for k in ('manifest_entry_id', 'locator')}
            p['quote'] = e.get('quote_or_mark_description', '')[:200]
            result[canonical(p)] = p
    return [result[k] for k in sorted(result)]


def distinct(values):
    return sorted({canonical(norm(x)): x for x in values}.values(), key=canonical)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def temporal_scalar(value, field='local_value'):
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    if field == 'local_value' and isinstance(value, str) and re.fullmatch(r'\d{4}-\d\d-\d\d[Tt]\d\d:\d\d(?::\d\d(?:\.\d+)?)?', value):
        # Serialize an already stated naive civil value; never supply a zone.
        value = datetime.fromisoformat(value.upper()).isoformat()
    return norm(value)


def temporal_compare(a, b):
    """Role -> local_value alignment (VA rule); wording is reference-only."""
    diffs, wording, slots = [], [], []
    def diff(field, av, bv):
        tail = field.rsplit('.', 1)[-1]
        def comparable(v):
            return norm([temporal_scalar(x, tail) for x in v]) if isinstance(v, list) else temporal_scalar(v, tail)
        equal = comparable(av) == comparable(bv)
        slots.append(equal)
        if not equal:
            diffs.append({'field': field, 'A': av, 'B': bv})
    def groups(entries):
        result = collections.defaultdict(list)
        for t in entries:
            result[t['role']].append(t)
        return result
    aa, bb = groups(a), groups(b)
    for role in sorted(set(aa) | set(bb)):
        ax, bx = aa[role], bb[role]
        wa = [{k: v for k, v in t.items() if k not in DECISIVE_TEMP and k != 'role'} for t in ax]
        wb = [{k: v for k, v in t.items() if k not in DECISIVE_TEMP and k != 'role'} for t in bx]
        if norm(wa) != norm(wb):
            wording.append({'field': f'temporal.{role}.wording', 'A': wa, 'B': wb})
        if role not in ROLES:
            if norm(ax) != norm(bx):
                wording.append({'field': f'temporal.{role}.nonparticipation', 'A': ax, 'B': bx})
            continue
        diff(f'temporal.{role}.present', bool(ax), bool(bx))
        if not ax or not bx:
            continue
        ag, bg = collections.defaultdict(list), collections.defaultdict(list)
        for t in ax:
            ag[canonical(temporal_scalar(t.get('local_value')))].append(t)
        for t in bx:
            bg[canonical(temporal_scalar(t.get('local_value')))].append(t)
        for key in sorted(set(ag) & set(bg)):
            for field in DECISIVE_TEMP:
                diff(f'temporal.{role}[local_value={key}].{field}',
                     distinct(t.get(field) for t in ag[key]), distinct(t.get(field) for t in bg[key]))
        ak, bk = set(ag) - set(bg), set(bg) - set(ag)
        if ak and bk:
            ar = [t for k in sorted(ak) for t in ag[k]]
            br = [t for k in sorted(bk) for t in bg[k]]
            for field in DECISIVE_TEMP:
                diff(f'temporal.{role}[changed_values].{field}',
                     distinct(t.get(field) for t in ar), distinct(t.get(field) for t in br))
        elif ak or bk:
            wording.append({'field': f'temporal.{role}.unmatched_extra_entries',
                            'A': [t for k in sorted(ak) for t in ag[k]],
                            'B': [t for k in sorted(bk) for t in bg[k]],
                            'note': 'Role exists on both sides; unmatched entries alone are not material.'})
    return diffs, wording, slots


def latest(rows):
    """Follow append-only supersession chains; never silently choose a branch."""
    by_record = {r['record_id']: r for r in rows}
    assert len(by_record) == len(rows), 'Duplicate immutable record_id'
    superseded = set()
    for r in rows:
        prior = r.get('supersedes_record_id')
        if prior:
            assert prior in by_record, ('Missing predecessor', prior)
            old = by_record[prior]
            assert (r['entity_id'], r['record_type']) == (old['entity_id'], old['record_type'])
            assert r['label_version'] > old['label_version']
            superseded.add(prior)
    groups = collections.defaultdict(list)
    for r in rows:
        if r['record_id'] not in superseded:
            groups[(r['record_type'], r['entity_id'])].append(r)
    result = []
    for key, chain in sorted(groups.items()):
        assert len(chain) == 1, ('Unlinked corrections or branched label chain', key)
        result.extend(chain)
    return result


# --- MS native identity helpers -------------------------------------------

def forms(r):
    """SOS system numbers of every notice-form view cited by the record."""
    return sorted({e['manifest_entry_id'][len('ms-form-'):] for e in evidence(r)
                   if e['manifest_entry_id'].startswith('ms-form-')})


def own_forms(r):
    return sorted({e['manifest_entry_id'][len('ms-form-'):] for e in r['evidence']
                   if e['manifest_entry_id'].startswith('ms-form-')})


def native_key(entity_id, byid):
    """Native system number from the sealed record's own form evidence, else alias."""
    r = byid.get(entity_id)
    if not r:
        return None
    own = own_forms(r)
    if r['record_type'] == 'proceeding':
        # A proceeding root is the system number whose hash preimage minted it.
        for n in own + [a['native_id'] for a in r['aliases']]:
            if entity_id.rsplit('/', 1)[1] == digest_compact(['ms-sos-bulletin-service', 'proceeding', n.strip().lower()]):
                return n
    return own[0] if own else (r['aliases'][0]['native_id'] if r['aliases'] else None)


def digest_compact(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def stamp_dates(r):
    """Visually read FILED stamp dates quoted in the record, by form."""
    result = collections.defaultdict(set)
    for e in evidence(r):
        if not e['manifest_entry_id'].startswith('ms-form-'):
            continue
        for m in STAMP.finditer(e.get('quote_or_mark_description', '')):
            year = m[3] if m[3] and m[3].isdigit() else None
            result[e['manifest_entry_id'][8:]].add((date(int(year), MONTHS[m[1]], int(m[2])).isoformat()
                                                    if year else f'{m[1]} {int(m[2])} (year not read)'))
    return result


def hand_readings(r):
    result = collections.defaultdict(set)
    for e in evidence(r):
        if e['manifest_entry_id'].startswith('ms-form-'):
            for m in HAND.finditer(e.get('quote_or_mark_description', '')):
                result[e['manifest_entry_id'][8:]].add(m[1])
    return result


def bulletin_index():
    """System number -> bulletin index rows (navigation only, never filing evidence)."""
    rows = collections.defaultdict(list)
    for m in read(INPUTS / 'manifest.pass.jsonl'):
        if m['kind'] != 'portal_slice' or m['retrieval']['result'] != 'retrieved':
            continue
        blob = INPUTS / m['original_path']
        assert hashlib.sha256(blob.read_bytes()).hexdigest() == m['retrieval']['sha256']
        body = json.loads(blob.read_text())['d'].rsplit('|', 2)[0]
        for n, row in enumerate(body.split('^'), 1):
            f = row.split('~')
            if len(f) > 8:
                rows[f[8].strip()].append({'slice': m['entry_id'], 'row': n, 'agency': f[0], 'proposed': f[2], 'final': f[3],
                                           'effective': f[4], 'withdrawn': f[5], 'rule': ' '.join(f[6].split())[:120]})
    return rows


def mdy(s):
    if not s:
        return None
    m, d, y = s.split('/')
    return date(int(y), int(m), int(d))


def band(d):
    if d is None:
        return None
    if d >= END:
        return 'after_interval'
    if d >= START:
        return 'interval'
    if d >= CARRY_START:
        return 'carry_in_band'
    if d >= date(2026, 2, 16):
        return 'hearing_band'
    return 'before_bands'


# --- Identity and comparison -----------------------------------------------

def identities(passes):
    """Native IDs are deterministic; only roots differing by native key need review.

    A one-to-one pair of unmatched same-type entities whose records hold the
    same notice set is proposed as a comparison crosswalk (review required).
    """
    byid = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    candidates, mapping = [], {}
    for typ in ('proceeding', 'notice', 'opportunity', 'update'):
        aa = [r for r in passes['A'] if r['record_type'] == typ and r['entity_id'] not in byid['B']]
        bb = [r for r in passes['B'] if r['record_type'] == typ and r['entity_id'] not in byid['A']]
        proposed = []
        for a in aa:
            for b in bb:
                links = 'notice_ids' if typ in ('proceeding', 'opportunity', 'update') else 'proceeding_ids'
                shared_links = sorted(set(a['payload'].get(links, [])) & set(b['payload'].get(links, [])))
                if typ == 'proceeding' and not shared_links:
                    # Roots are named by their dependants: the same notice/update
                    # entity points at A's root in A and at B's root in B.
                    links = 'dependant_proceeding_ids'
                    deps = {s: {x['entity_id'] for x in passes[s] if r['entity_id'] in x['payload'].get('proceeding_ids', [])}
                            for s, r in (('A', a), ('B', b))}
                    shared_links = sorted(deps['A'] & deps['B'])
                shared_forms = sorted(set(own_forms(a)) & set(own_forms(b)))
                if not shared_links:
                    continue
                proposed.append({'candidate_id': 'ms-identity-' + digest([typ, a['entity_id'], b['entity_id']]),
                                 'record_type': typ, 'A_entity_id': a['entity_id'], 'B_entity_id': b['entity_id'],
                                 'A_record_ids': [a['record_id']], 'B_record_ids': [b['record_id']],
                                 'A_native_root': native_key(a['entity_id'], byid['A']),
                                 'B_native_root': native_key(b['entity_id'], byid['B']),
                                 'confidence': 'low', 'mechanical_issue_normalization': False,
                                 'match_basis': [{'kind': 'same_linked_' + links, 'shared': shared_links,
                                                  'shared_form_views': shared_forms,
                                                  'note': 'Same role in both passes, different native root keys; the crosswalk only aligns comparison.'}]})
        degrees = collections.Counter((s, c[f'{s}_entity_id']) for c in proposed for s in 'AB')
        for c in proposed:
            c['comparison_mapping_applied'] = all(degrees[(s, c[f'{s}_entity_id'])] == 1 for s in 'AB')
            c['review_required'] = True
            if c['comparison_mapping_applied']:
                mapping[c['B_entity_id']] = c['A_entity_id']
        candidates.extend(proposed)
    return sorted(candidates, key=canonical), mapping


def compare(passes, mapping, candidates):
    index = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    reverse = {a: b for b, a in mapping.items()}
    candidate_ids = {c['A_entity_id']: c['candidate_id'] for c in candidates if c['comparison_mapping_applied']}
    def mapped(v):
        return [mapped(x) for x in v] if isinstance(v, list) else mapping.get(v, v) if isinstance(v, str) else v
    pairs = []
    for eid in sorted(set(index['A']) | {mapping.get(x, x) for x in index['B']}):
        a, b = index['A'].get(eid), index['B'].get(reverse.get(eid, eid))
        typ = (a or b)['record_type']
        assert not a or not b or a['record_type'] == b['record_type']
        diffs, wording, derived, slots = [], [], [], []
        if typ != 'rejected_candidate':
            slots.append(bool(a) == bool(b))
            if bool(a) != bool(b):
                diffs.append({'field': 'present', 'A': bool(a), 'B': bool(b)})
            if a and b:
                for field in FIELDS[typ]:
                    av = a['cohorts'] if field == 'cohorts' else a['payload'].get(field)
                    bv = b['cohorts'] if field == 'cohorts' else b['payload'].get(field)
                    mv = mapped(bv) if field in ('proceeding_ids', 'proceeding_id', 'target_opportunity_ids') else bv
                    equal = norm(av) == norm(mv)
                    slots.append(equal)
                    if not equal:
                        diffs.append({'field': field, 'A': av, 'B': bv, 'B_after_identity_mapping': mv})
                td, tw, ts = temporal_compare(a['payload'].get('temporal', []), b['payload'].get('temporal', [])) if typ in ('opportunity', 'update') else ([], [], [])
                diffs.extend(td); wording.extend(tw); slots.extend(ts)
                if typ == 'proceeding':
                    an, bn = set(a['payload']['notice_ids']), set(mapped(b['payload']['notice_ids']))
                    unexplained = []
                    for nid in sorted(an ^ bn):
                        ar = index['A'].get(nid)
                        br = index['B'].get(reverse.get(nid, nid))
                        agreed = (not ar or not br or norm(ar['payload']['proceeding_ids']) == norm(mapped(br['payload']['proceeding_ids'])))
                        if not agreed:
                            unexplained.append(nid)
                    if an != bn:
                        d = {'field': 'notice_ids', 'A': sorted(an), 'B': b['payload']['notice_ids'],
                             'B_after_identity_mapping': sorted(bn)}
                        if unexplained:
                            diffs.append(d); slots.append(False)
                        else:
                            derived.append({**d, 'reason': 'Notice forward ownership agrees, or notice absence has its own pair.'})
                    else:
                        slots.append(True)
                for field in sorted(set(a['payload']) | set(b['payload'])):
                    if field not in FIELDS[typ] and field != 'temporal':
                        av, bv = a['payload'].get(field), b['payload'].get(field)
                        if norm(av) != norm(bv):
                            wording.append({'field': field, 'A': av, 'B': bv})
                for field in ('evidence', 'unresolved', 'aliases'):
                    if norm(a[field]) != norm(b[field]):
                        wording.append({'field': field, 'A': a[field], 'B': b[field]})
        pairs.append({'pair_id': 'ms-pair-' + digest([typ, eid]), 'entity_id': eid, 'record_type': typ,
                      'in_A': bool(a), 'in_B': bool(b), 'exact_id_match': bool(a and b and a['entity_id'] == b['entity_id']),
                      'A_entity_id': a['entity_id'] if a else None, 'B_entity_id': b['entity_id'] if b else None,
                      'A_record_ids': [a['record_id']] if a else [], 'B_record_ids': [b['record_id']] if b else [],
                      'identity_candidate_id': candidate_ids.get(eid), 'field_diffs': diffs, 'wording_diffs': wording,
                      'derivable_membership_diffs': derived, 'decisive_slots_equal': sum(slots), 'decisive_slots_total': len(slots)})
    return pairs


# --- Review queue -----------------------------------------------------------

POLICIES = {
    'relative-close-status': ('date_ambiguity', 'Status of a 25-day comment close whose anchor the form leaves unstated?',
        'status unknown, precision relative, local_value null; keep the FILED stamp as the signed accounting proxy in relative_anchor/ambiguity '
        'and stamp + 25 days only as a non-asserted annotation (signed MS Q2). Same uncomputed-close principle as CT C11 (pending owner signature).',
        'The form states the length (“twenty-five (25) day public comment period”) but no anchor; “supported” would assert a close the source does not fix. '
        'A says unknown, B says supported; both leave local_value null. The request close, whose anchor is stated, is supported in both passes.'),
    'explicit-opening': ('date_ambiguity', 'Keep an explicit opening for the hearing-request window?',
        'Keep the explicit open role. The request wording states its anchor (“within twenty (20) days after the filing of this notice”), so record '
        'relative/supported with null local_value and the FILED stamp as proxy; comment-window openings stay unknown/null. Same as CT C15 (pending owner signature).',
        'A records relative/supported, B unknown/unknown, for every request window. Both passes already keep comment-window openings unknown; no opening instant is computed.'),
    'opening-cutoff': ('date_ambiguity', 'What cutoff for openings?',
        'not_applicable. Same as CT C14 (pending owner signature).',
        'Opening roles carry no submission cutoff. A uses not_applicable, B unknown; dates and status are settled separately.'),
    'carry-in-relative': ('scope', 'Which relative-close carry-in windows were active at 2026-05-18?',
        'Account by the signed FILED-stamp proxy: a comment/request window is carry_in when stamp + N days (filing day excluded) falls on or after 2026-05-18; '
        'otherwise reject it as outside_interval and keep it as historical-support evidence. The date stays a non-asserted annotation, never local_value. '
        'Scheduled hearings use their literal dates. Pre-start closures (28578) are cases.',
        'UNIVERSE carry-in rule plus signed MS Q2; the brief keeps relative boundaries as review cases, so both passes left all of them provisional. '
        'Each stamp is verified in its own visual item; boundary offsets are listed so the owner can see what a different counting rule would flip.'),
    'stamp-index-mismatch': ('date_ambiguity', 'Does the visually read FILED stamp govern where the bulletin index date differs?',
        'Yes. The stamp governs interval and cohort accounting (signed MS Q14; brief); keep the index date as conflicting navigation evidence. '
        'Each stamp is still checked in its visual item; mismatches that change scope or cohort remain cases.',
        'Both passes flag the same 76 forms (sign-off decision 2c sends every mismatch to step 5). Most are 1–4 days, stamp later, with no band change.'),
    'completion-attribution': ('disagreement', 'Reconcile completion counts with final source-view attribution?',
        'Final source-view attribution, corrected append-only; same as CT C16 (pending owner signature). Never sum overlapping views or treat a zero '
        'slice count as an uninspected source.',
        'Both passes logged the bulletin slices at 0 before body inspection (both self-report it); a few form/cross-check rows differ from direct evidence links. '
        'Counts are a diagnostic; the brief permits overlapping source-view attribution.'),
}

CLASS_ORDER = ('relative-close-status', 'explicit-opening', 'opening-cutoff', 'carry-in-relative',
               'stamp-index-mismatch', 'completion-attribution')

# Primary routing of pass notes that ask a concrete question with scored effect.
SCOPE_NOTE = re.compile(r'(?=.*(?:State Plan|waiver|local[- ]?gov|District|jurisdiction))(?=.*(?:scope review|requires humanreview))', re.I)
LIFECYCLE_NOTE = re.compile(r'withdrawing and replacing|Whole-chapter replacement', re.I)
REPROPOSAL_NOTE = re.compile(r'(?<![a-z-])re-proposal|Separate new-system-number round|withdrawn\d{5}/\d{5}|potentialoverlap|Potential re-proposal', re.I)
MARK_NOTE = re.compile(r'temporary-rules column|FILEDstamp placedfinalcolumn|strike|unboxed|printed ?statement|Variant lacks not-scheduled|'
                       r'Variant expresses|neither/both/unclear|No decisive oral mark|Neither oral', re.I)


def dropped_notes(att):
    """Pass A's review notes omitted from its labels (attestation anomaly)."""
    text = next(x for x in att['anomalies'] if x.startswith('Append-only defect'))
    body = text.split('Dropped notes:', 1)[1]
    return [(m[1], m[2].strip()) for m in re.finditer(r'ms-form-(\d{5}): (.*?)(?=\s*\|\||$)', body)]


# A dropped note with possible scored effect gets a case in its own bundle;
# the rest are reference-only (outside interval or classification unaffected).
DROPPED_SCORED = {'28568', '28569', '28905'}


def review_queue(passes, pairs, candidates, mapping, att, index_rows):
    byrecord = {r['record_id']: (s, r) for s, rows in passes.items() for r in rows}
    byid = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    pair_for = {rid: p for p in pairs for s in 'AB' for rid in p[s + '_record_ids']}
    accepted = {s: [r for r in rows if r['record_type'] != 'rejected_candidate'] for s, rows in passes.items()}
    issues = {}

    # Bundle by SOS filing/system-number chain: proceeding roots, their notices,
    # explicit withdrawal targets and re-proposal links noted by either pass.
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def join(xs):
        xs = sorted(set(xs))
        for x in xs[1:]:
            ra, rb = find(xs[0]), find(x)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    for s, rows in accepted.items():
        for r in rows:
            nums = set(own_forms(r)) | {native_key(x, byid[s]) for x in r['payload'].get('proceeding_ids', []) + [r['payload'].get('proceeding_id')] if x}
            if r['record_type'] == 'proceeding':
                nums |= {native_key(r['entity_id'], byid[s])}
            if r['record_type'] == 'update':
                nums |= set(forms(r))
            for x in r['unresolved']:
                if REPROPOSAL_NOTE.search(x):
                    nums |= set(re.findall(r'(?<!\d)(2\d{4})(?!\d)', x))
            join([n for n in nums if n])
    def chain(nums):
        roots = {find(n) for n in nums}
        members = sorted({n for n in parent if find(n) in roots} | set(nums))
        return 'MS ' + '+'.join(members) if members else 'MS-unbundled'

    def records_for(r):
        p = pair_for[r['record_id']]
        return [(s, byrecord[rid][1]) for s in 'AB' for rid in p[s + '_record_ids']]
    def add(trigger, rr, kind, detail, policy=None, evidence_extra=None, group=None, nums=None):
        rr = sorted({(s, r['record_id']): (s, r) for s, r in rr}.values(), key=lambda x: (x[0], x[1]['record_id']))
        nums = set(nums or []) | {n for s, r in rr for n in own_forms(r)}
        key = digest([trigger, kind, [(s, r['record_id']) for s, r in rr], detail.get('field'), detail.get('role'),
                      detail.get('manifest_entry_id'), detail.get('form'), policy])
        if key in issues:
            reports = issues[key].setdefault('additional_reports', [])
            if detail != issues[key]['detail'] and detail not in reports:
                reports.append(detail)
            return
        issues[key] = {'sub_issue_id': key, 'trigger': trigger, 'class': kind, 'detail': detail,
                       'policy_key': policy, 'proceeding': group or chain(nums), 'system_numbers': sorted(nums),
                       'entity_ids': sorted({r['entity_id'] for s, r in rr}),
                       'record_ids': {s: sorted(r['record_id'] for side, r in rr if side == s) for s in 'AB'},
                       'evidence': pointers([r for s, r in rr]) + (evidence_extra or [])}

    # 1. Decisive field differences.
    for p in pairs:
        if p['record_type'] == 'rejected_candidate':
            continue
        rr = [(s, byrecord[rid][1]) for s in 'AB' for rid in p[s + '_record_ids']]
        typ = p['record_type']
        for d in p['field_diffs']:
            f = d['field']
            policy = None
            if f.startswith('temporal.close[') and f.endswith('.status'):
                policy = 'relative-close-status'
            elif f.startswith('temporal.open[') and (f.endswith('.status') or f.endswith('.precision')):
                policy = 'explicit-opening'
            elif f.startswith('temporal.open[') and f.endswith('.cutoff'):
                policy = 'opening-cutoff'
            if f == 'hearing_status':
                add('visual_mark', rr, 'oral_box_disagreement', {**d, 'form': own_forms(rr[0][1])[0]})
            elif f.startswith('temporal.'):
                add('date_ambiguity', rr, 'decisive_temporal', d, policy)
            else:
                add('disagreement', rr, typ + '.' + f, d)
    # 2. Comparison crosswalks for differing native roots.
    for c in candidates:
        rr = [('A', byid['A'][c['A_entity_id']]), ('B', byid['B'][c['B_entity_id']])]
        dependents = [(s, r) for s in 'AB' for r in accepted[s] if c[s + '_entity_id'] in r['payload'].get('proceeding_ids', [])]
        add('identity', rr + dependents, 'native_root_crosswalk',
            {k: c[k] for k in ('candidate_id', 'record_type', 'A_native_root', 'B_native_root', 'match_basis')})
    # 3. Accept-vs-reject conflicts on the same form evidence only.
    for side, other in (('A', 'B'), ('B', 'A')):
        acc_forms = collections.defaultdict(list)
        for r in accepted[side]:
            for n in own_forms(r):
                acc_forms[n].append(r)
        other_acc = {n for r in accepted[other] for n in own_forms(r)}
        for rej in passes[other]:
            if rej['record_type'] != 'rejected_candidate':
                continue
            for n in own_forms(rej):
                if n in acc_forms and n not in other_acc:
                    acc = acc_forms[n]
                    add('disagreement', [(side, r) for r in acc] + [(other, rej)], 'accepted_rejected',
                        {'form': n, 'accepted_pass': side, 'accepted_types': sorted({r['record_type'] for r in acc}),
                         'reason_code': rej['payload']['reason_code'], 'rationale': rej['payload']['rationale']})

    # 4. Decisive visual marks (owner decision 14): every included form's FILED
    # stamp, oral-proceeding box and handwritten system number, plus any form
    # where the passes read a mark differently.
    stamps = {s: collections.defaultdict(set) for s in 'AB'}
    hands = {s: collections.defaultdict(set) for s in 'AB'}
    for s, rows in passes.items():
        for r in rows:
            for n, v in stamp_dates(r).items():
                stamps[s][n] |= v
            for n, v in hand_readings(r).items():
                hands[s][n] |= v
    notice_forms = collections.defaultdict(lambda: {'A': [], 'B': []})
    for s in 'AB':
        for r in accepted[s]:
            if r['record_type'] in ('notice', 'opportunity', 'update'):
                for n in own_forms(r):
                    notice_forms[n][s].append(r)
    def index_dates(n):
        rows = index_rows.get(n, [])
        return sorted({(k, x[k]) for x in rows for k in ('proposed', 'final', 'withdrawn') if x[k]})
    def opp_summary(rows):
        return sorted({(r['payload']['opportunity_type'], r['payload']['hearing_status']) for r in rows if r['record_type'] == 'opportunity'})
    for n in sorted(notice_forms):
        rr = [(s, r) for s in 'AB' for r in notice_forms[n][s]]
        st = {s: sorted(stamps[s][n]) for s in 'AB'}
        detail = {'form': n, 'mark': 'filed_stamp', 'A': st['A'], 'B': st['B'], 'index_dates': index_dates(n),
                  'band_by_stamp': sorted({band(date.fromisoformat(x)) for s in 'AB' for x in st[s] if x[:1].isdigit()}),
                  'decides': 'notice/opportunity/update cohort and interval accounting'}
        add('visual_mark', rr, 'filed_stamp', detail)
        if any(r['record_type'] == 'opportunity' for s, r in rr):
            add('visual_mark', rr, 'oral_box',
                {'form': n, 'mark': 'oral_proceeding_box', 'A': opp_summary(notice_forms[n]['A']), 'B': opp_summary(notice_forms[n]['B']),
                 'decides': 'hearing vs hearing_request opportunity and hearing_status'})
        add('visual_mark', rr, 'handwritten_id',
            {'form': n, 'mark': 'handwritten_system_number', 'A': sorted(hands['A'][n]), 'B': sorted(hands['B'][n]),
             'decides': 'second identity alias for the notice key'})
        flagged = sorted({x for s, r in rr for x in r['unresolved'] if MARK_NOTE.search(x)})
        if flagged:
            add('visual_mark', rr, 'pass_flagged_mark', {'form': n, 'mark': 'pass_flagged', 'notes': flagged})
    all_forms = sorted(set(stamps['A']) | set(stamps['B']) | set(hands['A']) | set(hands['B']))
    for n in all_forms:
        if n in notice_forms:
            continue
        rr = [(s, r) for s in 'AB' for r in passes[s] if n in own_forms(r)]
        if stamps['A'][n] != stamps['B'][n]:
            add('visual_mark', rr, 'filed_stamp_disagreement', {'form': n, 'mark': 'filed_stamp', 'A': sorted(stamps['A'][n]), 'B': sorted(stamps['B'][n])})
        if hands['A'][n] != hands['B'][n]:
            add('visual_mark', rr, 'handwritten_id_disagreement',
                {'form': n, 'mark': 'handwritten_system_number', 'A': sorted(hands['A'][n]), 'B': sorted(hands['B'][n]),
                 'note': 'A parse of each pass quote; an empty side means that pass quoted no numeric reading.'})

    # 5. Stamp/index mismatches (sign-off 2c): class membership plus scope cases.
    flagged = collections.defaultdict(lambda: {'A': [], 'B': []})
    for s, rows in passes.items():
        for r in rows:
            if any(re.search(r'stamp/index mismatch', x, re.I) for x in r['unresolved']):
                for n in own_forms(r):
                    flagged[n][s].append(r)
    for n in sorted(flagged):
        rr = [(s, r) for s in 'AB' for r in flagged[n][s]]
        stamp = sorted({x for s in 'AB' for x in stamps[s][n] if x[:1].isdigit()})
        idx = index_dates(n)
        sb = sorted({band(date.fromisoformat(x)) for x in stamp})
        ib = sorted({band(mdy(v)) for k, v in idx})
        near = min((mdy(v) for k, v in idx), key=lambda d: abs((d - date.fromisoformat(stamp[0])).days)) if stamp and idx else None
        detail = {'form': n, 'stamp': stamp, 'index_dates': idx, 'stamp_minus_nearest_index_days': (date.fromisoformat(stamp[0]) - near).days if near else None,
                  'band_by_stamp': sb, 'band_by_nearest_index': band(near), 'flagged_by': [s for s in 'AB' if flagged[n][s]]}
        add('date_ambiguity', rr, 'stamp_index_mismatch', detail, 'stamp-index-mismatch')
        accepted_here = any(r['record_type'] != 'rejected_candidate' for s, r in rr)
        if band(near) != (sb[0] if sb else None) and (band(near) in ('interval', 'carry_in_band') or accepted_here):
            add('visual_mark', rr, 'stamp_index_scope_change',
                {**detail, 'question': 'The index date would change interval or cohort accounting; confirm the stamp reading and the resulting disposition.'})

    # 6. Relative-close carry-in accounting (class) and pre-start closures (cases).
    finals = collections.defaultdict(list)
    for n, rows in index_rows.items():
        for x in rows:
            if x['final'] and x['proposed'] and n not in notice_forms:
                finals[(x['agency'], x['proposed'])].append((n, x))
    for p in pairs:
        if p['record_type'] != 'opportunity':
            continue
        rr = [(s, byrecord[rid][1]) for s in 'AB' for rid in p[s + '_record_ids']]
        if not any('carry_in' in r['cohorts'] for s, r in rr):
            continue
        r0 = rr[0][1]
        n = own_forms(r0)[0] if own_forms(r0) else None
        stamp = sorted({x for s in 'AB' for x in stamps[s].get(n, ()) if x[:1].isdigit()})
        typ = r0['payload']['opportunity_type']
        if typ == 'hearing':
            continue
        days = 25 if typ == 'written_comment' else 20
        s0 = date.fromisoformat(stamp[0]) if stamp else None
        annotation = (s0 + timedelta(days)).isoformat() if s0 else None
        offset = ((s0 + timedelta(days)) - START).days if s0 else None
        add('scope', rr, 'carry_in_relative',
            {'form': n, 'opportunity_type': typ, 'stamp': stamp, 'days': days, 'non_asserted_stamp_plus_n': annotation,
             'offset_from_start_days': offset, 'proposed_outcome': 'carry_in' if offset is not None and offset >= 0 else 'outside_interval (historical support)'},
            'carry-in-relative')
    for s, rows in passes.items():
        for r in rows:
            if r['record_type'] != 'rejected_candidate':
                continue
            n = (own_forms(r) or [None])[0]
            if not n:
                continue
            for x in index_rows.get(n, []):
                p_date, f_date = mdy(x['proposed']), mdy(x['final'])
                if not (p_date and f_date and CARRY_START <= p_date < START and f_date < START and f_date > p_date):
                    continue
                for m, rows_m in notice_forms.items():
                    mx = index_rows.get(m, [])
                    if any(y['agency'] == x['agency'] and y['proposed'] == x['proposed'] and not y['final'] and
                           norm(y['rule']) == norm(x['rule']) for y in mx):
                        rr = [(t, q) for t in 'AB' for q in rows_m[t]] + [(s, r)]
                        add('lifecycle_ambiguity', rr, 'pre_start_closure',
                            {'form': m, 'closing_final': n, 'final_index_date': x['final'], 'final_stamp': sorted(stamps[s][n]),
                             'match': 'same index agency, proposed date and rule name',
                             'question': 'A final adoption stamped before 2026-05-18 closes this carry-in candidate; reject its windows as carry-ins?'},
                            group=chain([m]), nums=[m, n])

    # 7. Lifecycle: every update's target scope; pass notes on lifecycle/scope/re-proposals.
    for s, rows in accepted.items():
        for r in rows:
            rr, p = records_for(r), r['payload']
            if r['record_type'] == 'update':
                add('lifecycle_ambiguity', rr, 'target_scope',
                    {'event_type': p['event_type'], 'targets_A_B': sorted({canonical(q['payload']['target_opportunity_ids']) for t, q in rr}),
                     'question': 'Confirm the exact withdrawal target, before-evidence and cohort; no invented prior opportunity.'})
                if not p['target_opportunity_ids']:
                    add('lifecycle_ambiguity', rr, 'empty_target', {'reason': p.get('target_unresolved_reason')})
            for x in r['unresolved']:
                if LIFECYCLE_NOTE.search(x):
                    add('lifecycle_ambiguity', rr, 'replacement_wording', {'reported_by': s, 'note': x[:300]})
                if SCOPE_NOTE.search(x) and r['record_type'] in ('notice', 'proceeding'):
                    add('scope', rr, 'inclusion_scope', {'reported_by': s, 'note': x[:300]})
                if REPROPOSAL_NOTE.search(x) and r['record_type'] in ('notice', 'proceeding'):
                    add('identity', rr, 'reproposal_link', {'reported_by': s, 'note': x[:300]})
                if re.search(r'linkage: agency notice|append-only anomaly|Agency source supplies', x):
                    add('identity', rr, 'agency_notice_link', {'reported_by': s, 'note': x[:300]})

    # 8. Pass A's dropped notes (attestation): scored ones become cases.
    for n, note in dropped_notes(att['A']):
        rr = [(s, r) for s in 'AB' for r in passes[s] if n in own_forms(r)]
        if n in DROPPED_SCORED:
            # Each turns on a mark read from the scan (stamp or typed hearing date).
            add('visual_mark', rr, 'pass_a_dropped_note', {'form': n, 'note': note[:300]})
        else:
            add('scope', rr, 'pass_a_dropped_note_reference', {'form': n, 'note': note[:300]}, group='MS-pass-A-dropped-notes')
    illegible = next(x for x in att['A']['anomalies'] if x.startswith('ms-form-28933'))
    rr = [(s, r) for s in 'AB' for r in passes[s] if '28933' in own_forms(r)]
    add('visual_mark', rr, 'filed_stamp_index_quoted', {'form': '28933', 'mark': 'filed_stamp', 'A': sorted(stamps['A']['28933']),
        'B': sorted(stamps['B']['28933']), 'A_attestation': illegible[:300]})

    # 9. Source gaps and completion attribution.
    for m in read(STATE / 'manifest.jsonl'):
        if m['retrieval']['result'] != 'retrieved':
            add('missing_source', [], 'source_gap', {'manifest_entry_id': m['entry_id'], 'result': m['retrieval']['result'],
                'signed': 'owner-signoff/ms-acq-2026-10-15/id-gap-28935'},
                evidence_extra=[{'manifest_entry_id': m['entry_id'], 'locator': 'manifest gap; no original', 'quote': ''}], group='MS-source-gaps')
    listed = {}
    for m in read(INPUTS / 'manifest.pass.jsonl'):
        if m['kind'] == 'portal_slice':
            listed[m['entry_id']] = {n for n, rows in index_rows.items() if any(x['slice'] == m['entry_id'] for x in rows)}
    for row in read(STATE / 'completion.jsonl'):
        side = row['pass'][-1]
        mid = row['manifest_entry_id']
        direct = [r for r in accepted[side] if mid in {e['manifest_entry_id'] for e in r['evidence']}]
        listing = [r for r in accepted[side] if mid in listed and set(own_forms(r)) & listed[mid]]
        if row['candidate_count'] != len(direct) or (mid in listed and row['candidate_count'] < len(listing)):
            add('disagreement', [(side, r) for r in direct], 'completion_attribution',
                {'manifest_entry_id': mid, 'pass': row['pass'], 'completion_candidate_count': row['candidate_count'],
                 'final_direct_evidence_count': len(direct), 'listed_accepted_records': len(listing) if mid in listed else None,
                 'note': 'Attribution diagnostic, not an assertion that only direct evidence counts.'},
                'completion-attribution', evidence_extra=[{'manifest_entry_id': mid, 'locator': 'completion row versus final evidence/listing attribution', 'quote': ''}],
                group='MS-source-accounting')

    # Collapse >=10 unique instances per policy into one class item.
    groups_by_policy = collections.defaultdict(list)
    for issue in issues.values():
        if issue['policy_key']:
            groups_by_policy[issue['policy_key']].append(issue)
    def instance(x):
        if x['detail'].get('manifest_entry_id'):
            return ('source', x['detail']['manifest_entry_id'])
        if x['policy_key'] == 'stamp-index-mismatch':
            return ('form', x['detail']['form'])
        return tuple(x['entity_ids'])
    classes = {key for key, xx in groups_by_policy.items() if len({instance(x) for x in xx}) >= 10}
    bundled = collections.defaultdict(list)
    for issue in issues.values():
        key = ('class', issue['policy_key']) if issue['policy_key'] in classes else ('case', issue['proceeding'], issue['trigger'])
        bundled[key].append(issue)
    items = []
    for key, xx in sorted(bundled.items()):
        xx.sort(key=canonical)
        policy = key[1] if key[0] == 'class' else None
        trigger = POLICIES[policy][0] if policy else key[2]
        records = {s: sorted({rid for x in xx for rid in x['record_ids'][s]}) for s in 'AB'}
        ev = sorted({canonical(e): e for x in xx for e in x['evidence']}.values(), key=canonical)
        item = {'item_id': 'ms-' + ('policy-' if policy else 'review-') + digest(key), 'item_kind': key[0],
                'trigger': trigger, 'policy_key': policy, 'proceeding': 'MS-policy' if policy else key[1],
                'system_numbers': sorted({n for x in xx for n in x['system_numbers']}), 'record_ids': records,
                'entity_ids': sorted({e for x in xx for e in x['entity_ids']}), 'sub_issues': xx,
                'affected_instance_count': len({instance(x) for x in xx}), 'evidence': ev}
        if policy:
            _, item['question'], item['proposed_answer'], item['rationale'] = POLICIES[policy]
            reps, seen = [], set()
            for x in sorted(xx, key=lambda x: (x['proceeding'], x['sub_issue_id'])):
                group = x['detail'].get('manifest_entry_id') or x['proceeding']
                if group in seen:
                    continue
                rep_evidence = x['evidence']
                if x['detail'].get('manifest_entry_id'):
                    rep_evidence = [e for e in rep_evidence if e['manifest_entry_id'] == x['detail']['manifest_entry_id']]
                reps.append({'proceeding': x['proceeding'], 'record_ids': x['record_ids'], 'detail': x['detail'],
                             'sub_issue_id': x['sub_issue_id'], 'evidence': rep_evidence[:3]})
                seen.add(group)
                if len(reps) == 3:
                    break
            item['representative_instances'] = reps
        else:
            item['question'] = f'Resolve {trigger.replace("_", " ")} for {item["proceeding"]}; retain unsupported facts as unknown/conflicting.'
            if trigger == 'visual_mark':
                item['render'] = f'.census-passes/MS/review-renders/{item["item_id"]}.png'
        items.append(item)
    items.sort(key=lambda i: (i['item_kind'] != 'class', CLASS_ORDER.index(i['policy_key']) if i['policy_key'] else 99,
                              i['proceeding'], TRIGGERS.index(i['trigger'])))
    for kind, prefix, width in [('class', 'C', 2), ('case', 'K', 3)]:
        for n, item in enumerate([i for i in items if i['item_kind'] == kind], 1):
            item['owner_ref'] = f'{prefix}{n:0{width}d}'
    return items


def queue_markdown(items, summary):
    classes = [i for i in items if i['item_kind'] == 'class']
    cases = [i for i in items if i['item_kind'] == 'case']
    md = ['# MS human review — proposed class and case decisions', '',
          f'{len(classes)} class items; {len(cases)} case items. All are unsigned proposals. No sealed pass or adjudication was changed.', '',
          'Class decisions settle only the named policy facet; concrete stamps, boxes, targets and scope calls remain cases. '
          'Every decisive visual mark on an included filing is its own visual_mark case (owner decision 14), bundled by SOS system-number chain, '
          'with a region render outside git at `.census-passes/MS/review-renders/<item_id>.png`. '
          'Latest append-only label-chain heads are compared once. Reference wording is retained in pairs.wording_diffs.', '',
          '## Counts by trigger', '', '| Trigger | Class | Case |', '|---|---:|---:|']
    for t in TRIGGERS:
        md.append(f'| {t} | {sum(i["item_kind"] == "class" and i["trigger"] == t for i in items)} | '
                  f'{sum(i["item_kind"] == "case" and i["trigger"] == t for i in items)} |')
    md += ['', '## Class questions', '']
    for i in classes:
        md += [f'### {i["owner_ref"]}. {i["question"]}', '', f'`{i["item_id"]}`; {i["affected_instance_count"]} instances; '
               f'{sum(map(len, i["record_ids"].values()))} label versions.', '',
               '**Proposed:** ' + i['proposed_answer'], '', i['rationale'], '',
               'Owner may accept, reject or specify exceptions by immutable record ID; nothing is applied.', '']
        for rep in i['representative_instances']:
            md.append(f'- **{rep["proceeding"]}**; sub-issue `{rep["sub_issue_id"]}`: {canonical(rep["detail"])[:400]}')
            for ev in rep['evidence']:
                md.append(f'  - `{ev["manifest_entry_id"]}`, {ev["locator"]}: “{" ".join(ev["quote"].split())[:200]}”')
        md.append('')
    md += ['## Cases bundled by SOS system-number chain', '']
    for i in cases:
        md += [f'### {i["owner_ref"]}. {i["proceeding"]} — {i["trigger"]}', '', f'`{i["item_id"]}`', '', i['question'], '']
        if i.get('render'):
            md += [f'Render (outside git): `{i["render"]}`', '']
        for x in i['sub_issues']:
            md.append(f'- `{x["sub_issue_id"]}` **{x["class"]}**: {canonical(x["detail"])[:1000]}')
        md.append('')
        for ev in i['evidence'][:6]:
            md.append(f'- `{ev["manifest_entry_id"]}`, {ev["locator"][:120]}: “{" ".join(ev["quote"].split())[:200]}”')
        md.append('')
    md += ['## Agreement statistics', '', '| Record type | A | B | Exact both | Mapped both | A only | B only | Paired decisive agreement |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for typ, st in summary['record_statistics'].items():
        md.append('| ' + typ + ' | ' + ' | '.join(str(st[k]) for k in ('A', 'B', 'exact_ID_both', 'comparison_both', 'A_only', 'B_only', 'both_decisive_agree')) + ' |')
    md += ['', f'Decisive slots equal: {summary["decisive_slots_equal"]}/{summary["decisive_slots_total"]}. '
           'Rejection exact-ID intersections are not agreement statistics; rejected candidates are compared by evidence only. '
           'No rejected-vs-absent or rejection-vs-rejection item is queued. All identity comparisons remain proposed crosswalks.', '',
           '## Appendix — complete class membership', '']
    for i in classes:
        md += [f'### {i["owner_ref"]} — `{i["item_id"]}`', '']
        for s in 'AB':
            md += [f'Pass {s}: {len(i["record_ids"][s])}', '']
            md += [f'- `{rid}`' for rid in i['record_ids'][s]]
            md.append('')
    (OUT / 'REVIEW-QUEUE.md').write_text('\n'.join(md) + '\n')


def main():
    passes, seals, att = {}, {}, {}
    for side in 'AB':
        path = STATE / f'pass-{side}.jsonl'
        att[side] = json.loads((STATE / 'attestations' / f'pass-{side}.json').read_text())
        seals[side] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert seals[side] == att[side]['output_sha256'], f'Pass {side} differs from sealed hash'
        passes[side] = latest(read(path))
    index_rows = bulletin_index()
    candidates, mapping = identities(passes)
    pairs = compare(passes, mapping, candidates)
    write('identity-candidates.jsonl', candidates)
    stats = {}
    for typ in TYPES:
        pp = [p for p in pairs if p['record_type'] == typ]
        stats[typ] = {'A': sum(p['in_A'] for p in pp), 'B': sum(p['in_B'] for p in pp),
                      'exact_ID_both': sum(p['exact_id_match'] for p in pp),
                      'comparison_both': sum(p['in_A'] and p['in_B'] for p in pp),
                      'A_only': sum(p['in_A'] and not p['in_B'] for p in pp),
                      'B_only': sum(p['in_B'] and not p['in_A'] for p in pp),
                      'both_decisive_agree': sum(p['in_A'] and p['in_B'] and not p['field_diffs'] for p in pp)}
    summary = {'sealed_sha256': seals, 'record_statistics': stats,
               'identity_candidates': len(candidates), 'identity_mappings': len(mapping),
               'decisive_slots_equal': sum(p['decisive_slots_equal'] for p in pairs),
               'decisive_slots_total': sum(p['decisive_slots_total'] for p in pairs),
               'union_opportunities': stats['opportunity']['A'] + stats['opportunity']['B'] - stats['opportunity']['comparison_both']}
    items = review_queue(passes, pairs, candidates, mapping, att, index_rows)
    write('review-queue.jsonl', items)
    summary['queue'] = {kind: {t: sum(i['item_kind'] == kind and i['trigger'] == t for i in items) for t in TRIGGERS}
                        for kind in ('class', 'case')}
    refs = collections.defaultdict(list)
    for item in items:
        for s in 'AB':
            for rid in item['record_ids'][s]:
                refs[rid].append(item['item_id'])
    for pair in pairs:
        pair['review_refs'] = sorted({ref for s in 'AB' for rid in pair[s + '_record_ids'] for ref in refs[rid]})
    write('pairs.jsonl', pairs)
    queue_markdown(items, summary)
    (OUT / 'comparison-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
