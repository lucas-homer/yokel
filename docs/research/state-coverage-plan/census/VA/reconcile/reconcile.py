#!/usr/bin/env python3
"""Virginia sealed comparison. Deterministic, stdlib only; never adjudicates.

Run from any directory. Reads only VA inputs plus the protocol/scope references.
CT revision-3 temporal materiality is retained. Issue spellings are canonicalized
only for comparison; no sealed label or canonical identity is changed.
"""
import collections
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
STATE = OUT.parent
INPUTS = OUT.parents[5] / '.census-passes/VA/inputs'
TYPES = ('notice', 'opportunity', 'proceeding', 'update', 'rejected_candidate')
TRIGGERS = ('disagreement', 'lifecycle_ambiguity', 'date_ambiguity', 'visual_mark', 'missing_source', 'identity', 'scope')
FIELDS = {'notice': ('proceeding_ids', 'cohorts'),
          'opportunity': ('opportunity_type', 'hearing_status', 'proceeding_id', 'cohorts'),
          'update': ('event_type', 'target_opportunity_ids', 'cohorts'),
          'proceeding': (), 'rejected_candidate': ()}
DECISIVE_TEMP = ('local_value', 'precision', 'status', 'iana_zone', 'cutoff', 'receipt_or_postmark')
ROLES = {'open', 'close', 'hearing_start', 'hearing_end'}
DOC = re.compile(r'(?<![a-z0-9])(?:PFR|R)\d{1,4}-\d+', re.I)
ISSUE = re.compile(r'^va-(\d+)-(\d+)-(?:pdf|s\d+|toc)$')

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
            f.flush()


def short_quotes(value):
    """Compare full sealed values, but expose at most 200 quoted characters.

    Hash/length metadata preserves an exact reference to long input literals;
    the immutable record IDs lead back to the complete sealed wording.
    """
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


def temporal_scalar(value, field='local_value'):
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    if field == 'local_value' and isinstance(value, str) and re.fullmatch(r'\d{4}-\d\d-\d\d[Tt]\d\d:\d\d(?::\d\d(?:\.\d+)?)?', value):
        # Serialize an already stated naive civil value; never compute a date,
        # supply a zone or turn date precision into midnight/end-of-day.
        value = datetime.fromisoformat(value.upper()).isoformat()
    return norm(value)


def temporal_compare(a, b):
    """Role -> local_value alignment, never entry position or literal wording.

    Compare all same-value groups. If both sides have residual values, compare
    residual sets. One-sided extra entries in a role present on both sides are
    reference-only, per the materiality spec; missing whole roles are decisive.
    None, [None], duplicate entries and array order cannot create artifacts.
    """
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
        # All non-decisive temporal material remains inspectable without queuing.
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
            # Same value, compare decisive attributes as sets, not duplicate count.
            for field in DECISIVE_TEMP:
                diff(f'temporal.{role}[local_value={key}].{field}',
                     distinct(t.get(field) for t in ag[key]), distinct(t.get(field) for t in bg[key]))
        ak, bk = set(ag) - set(bg), set(bg) - set(ag)
        if ak and bk:
            # These are changed asserted values, not missing extra sessions.
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


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


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


def doc_aliases(r):
    return sorted({m.upper() for a in r['aliases'] for m in DOC.findall(a['native_id'])})


def issue_keys(r):
    return sorted({f'{int(m[1])}:{int(m[2]):02d}' for e in evidence(r)
                   if (m := ISSUE.fullmatch(e['manifest_entry_id']))})


def pdf_pages(r, operative=False):
    ev = r['payload'].get('after_evidence', []) if operative else evidence(r)
    return {(e['manifest_entry_id'], int(p)) for e in ev if e['manifest_entry_id'].endswith('-pdf')
            for p in re.findall(r'\b(?:PDF\s+)?page\s*(\d+)', e['locator'], re.I)}


def role_values(r):
    return sorted({(t['role'], canonical(temporal_scalar(t.get('local_value'))))
                   for t in r['payload'].get('temporal', []) if t['role'] in ROLES and t.get('local_value')})


def chapters(r):
    # A chapter corroborates an original region; it is never sufficient alone.
    text = r['payload'].get('title', '') + ' ' + r['payload'].get('target_scope', '')
    if r['record_type'] == 'rejected_candidate':
        text += ' ' + r['payload'].get('rationale', '')
    text += ' ' + ' '.join(e.get('quote_or_mark_description', '') for e in evidence(r))
    return set(re.findall(r'\d+VAC\d+-\d+', text, re.I))


def native_notices(rows):
    """Recover specified hash preimages, testing both literal issue spellings.

    A verified preimage is stronger than a shared proceeding alias/page. No
    deadline, title, inferred publication instant or mutable text enters it.
    """
    result = {}
    for r in rows:
        if r['record_type'] != 'notice':
            continue
        for doc in doc_aliases(r):
            for issue in issue_keys(r):
                volume, number = issue.split(':')
                for spelling in sorted({issue, f'{volume}:{int(number)}'}):
                    for ordinal in range(1, 5):
                        key = canonical([doc.lower(), spelling, ordinal])
                        if r['entity_id'].rsplit('/', 1)[1] == digest(['va-register', 'notice', key]):
                            result[r['entity_id']] = {'doc': doc.lower(), 'issue': issue, 'ordinal': ordinal,
                                                      'raw_key': key, 'key': canonical([doc.lower(), issue, ordinal]),
                                                      'issue_spelling': spelling}
    return result


def identities(passes):
    byid = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    native = {s: native_notices(rows) for s, rows in passes.items()}
    def context_values(r, side):
        linked = r['payload'].get('opportunity_ids', [])
        if r['record_type'] == 'proceeding':
            linked = [x for n in r['payload']['notice_ids'] if n in byid[side]
                      for x in byid[side][n]['payload'].get('opportunity_ids', [])]
        return set(role_values(r)) | {v for eid in linked if eid in byid[side] for v in role_values(byid[side][eid])}
    # Match notices before dependent windows/actions, proceedings before forward links.
    candidates, mapping = [], {}
    for typ in ('proceeding', 'notice', 'opportunity', 'update'):
        aa = [r for r in passes['A'] if r['record_type'] == typ and r['entity_id'] not in byid['B']]
        bb = [r for r in passes['B'] if r['record_type'] == typ and r['entity_id'] not in byid['A']]
        proposed = []
        for a in aa:
            for b in bb:
                if typ == 'opportunity' and a['payload']['opportunity_type'] != b['payload']['opportunity_type']:
                    continue
                basis, confidence, mechanical = [], 'medium', False
                na, nb = native['A'].get(a['entity_id']), native['B'].get(b['entity_id'])
                if typ == 'notice' and na and nb and na['key'] == nb['key']:
                    basis = [{'kind': 'verified_notice_hash_preimages', 'A': na, 'B': nb}]
                    confidence, mechanical = 'high', True
                elif typ in ('opportunity', 'update'):
                    # Verify each dependent hash from the notice preimage as well.
                    for an in a['payload'].get('notice_ids', []):
                        for bn in b['payload'].get('notice_ids', []):
                            na, nb = native['A'].get(an), native['B'].get(bn)
                            if not na or not nb or na['key'] != nb['key']:
                                continue
                            for ordinal in range(1, 5):
                                def expected(r, n):
                                    if typ == 'update':
                                        return digest(['va-register', 'update', n['raw_key'], ordinal])
                                    roots = byid['A' if r is a else 'B'].get(r['payload']['proceeding_id'])
                                    for doc in doc_aliases(roots) if roots else []:
                                        h = digest(['va-register', 'participation-window', doc.lower(), n['raw_key'],
                                                    r['payload']['opportunity_type'], ordinal])
                                        if h == r['entity_id'].rsplit('/', 1)[1]:
                                            return h
                                    return None
                                if (expected(a, na) == a['entity_id'].rsplit('/', 1)[1] and
                                        expected(b, nb) == b['entity_id'].rsplit('/', 1)[1]):
                                    basis = [{'kind': 'verified_dependent_hash_preimages', 'A_notice': na, 'B_notice': nb,
                                              'ordinal': ordinal}]
                                    confidence, mechanical = 'high', True
                if not basis:
                    # Fallbacks/printed-vs-HTML aliases: require original region plus
                    # discriminating native aliases, date/role or mapped parent links.
                    shared = sorted(set(doc_aliases(a)) & set(doc_aliases(b)))
                    pages = sorted(pdf_pages(a, typ == 'update') & pdf_pages(b, typ == 'update'))
                    same_values = bool(context_values(a, 'A') & context_values(b, 'B'))
                    mapped_notices = {mapping.get(x, x) for x in b['payload'].get('notice_ids', [])}
                    same_parent = bool(set(a['payload'].get('notice_ids', [])) & mapped_notices)
                    exact_quotes = {norm(e.get('quote_or_mark_description', '')) for e in evidence(a)} & {
                        norm(e.get('quote_or_mark_description', '')) for e in evidence(b)}
                    meaningful_quotes = [q for q in exact_quotes if len(q) >= 20 and not q.startswith('volume ')]
                    compatible = (typ != 'opportunity' or a['payload']['opportunity_type'] == b['payload']['opportunity_type'])
                    same_chapters = bool(chapters(a) & chapters(b))
                    if pages and compatible and ((shared and (set(issue_keys(a)) & set(issue_keys(b)))) or
                                                 same_parent or (same_values and (meaningful_quotes or not chapters(a) and not chapters(b))) or same_chapters):
                        basis = [{'kind': 'same_original_region', 'pages': pages, 'shared_doc_aliases': shared,
                                  'same_role_value': same_values, 'mapped_notice_link': same_parent,
                                  'shared_quote': meaningful_quotes[:1], 'same_chapters': sorted(chapters(a)) if same_chapters else []}]
                        confidence = 'high' if same_parent and same_values else 'medium'
                if basis:
                    proposed.append({'candidate_id': 'va-identity-' + digest([typ, a['entity_id'], b['entity_id']]),
                                     'record_type': typ, 'A_entity_id': a['entity_id'], 'B_entity_id': b['entity_id'],
                                     'A_record_ids': [a['record_id']], 'B_record_ids': [b['record_id']],
                                     'confidence': confidence, 'mechanical_issue_normalization': mechanical,
                                     'match_basis': basis})
        # Prefer independently verified hash preimages over weaker page matches.
        strong_a = {c['A_entity_id'] for c in proposed if c['mechanical_issue_normalization']}
        strong_b = {c['B_entity_id'] for c in proposed if c['mechanical_issue_normalization']}
        proposed = [c for c in proposed if c['mechanical_issue_normalization'] or
                    (c['A_entity_id'] not in strong_a and c['B_entity_id'] not in strong_b)]
        def strength(c):
            if c['mechanical_issue_normalization']:
                return 100
            b = c['match_basis'][0]
            return (10 * bool(b.get('mapped_notice_link')) + 5 * bool(b.get('same_chapters')) +
                    3 * bool(b.get('shared_doc_aliases')) + bool(b.get('same_role_value')))
        maxima = {}
        for c in proposed:
            for s in 'AB':
                key = (s, c[f'{s}_entity_id'])
                maxima[key] = max(maxima.get(key, 0), strength(c))
        proposed = [c for c in proposed if all(strength(c) == maxima[(s, c[f'{s}_entity_id'])] for s in 'AB')]
        degrees = collections.Counter((side, c[f'{side}_entity_id']) for c in proposed for side in 'AB')
        for c in proposed:
            c['comparison_mapping_applied'] = all(degrees[(s, c[f'{s}_entity_id'])] == 1 for s in 'AB')
            c['review_required'] = not c['mechanical_issue_normalization']
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
                    # Suppress only when each changed notice's forward assignment
                    # agrees across passes, or its presence already has a case.
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
                for field in sorted(set(a['payload']) | set(b['payload'])):
                    if field not in FIELDS[typ] and field != 'temporal':
                        av, bv = a['payload'].get(field), b['payload'].get(field)
                        if norm(av) != norm(bv):
                            wording.append({'field': field, 'A': av, 'B': bv})
                for field in ('evidence', 'unresolved'):
                    if norm(a[field]) != norm(b[field]):
                        wording.append({'field': field, 'A': a[field], 'B': b[field]})
        pairs.append({'pair_id': 'va-pair-' + digest([typ, eid]), 'entity_id': eid, 'record_type': typ,
                      'in_A': bool(a), 'in_B': bool(b), 'exact_id_match': bool(a and b and a['entity_id'] == b['entity_id']),
                      'A_entity_id': a['entity_id'] if a else None, 'B_entity_id': b['entity_id'] if b else None,
                      'A_record_ids': [a['record_id']] if a else [], 'B_record_ids': [b['record_id']] if b else [],
                      'identity_candidate_id': candidate_ids.get(eid), 'field_diffs': diffs, 'wording_diffs': wording,
                      'derivable_membership_diffs': derived, 'decisive_slots_equal': sum(slots), 'decisive_slots_total': len(slots)})
    return pairs


POLICIES = {
    'explicit-opening': ('date_ambiguity', 'Keep an explicit unknown opening?',
        'Keep supported opening wording or an explicit unknown/null opening. Same as CT C15 (pending owner signature).',
        'The brief requires applicable open roles; publication metadata supplies no legal opening instant.'),
    'on-or-before-cutoff': ('date_ambiguity', 'Is “on or before” inclusive?',
        'Inclusive at the stated precision; same endpoint principle as CT C9 (pending owner signature).',
        'The literal includes the endpoint; do not add a time, zone or computed deadline.'),
    'fallback-key-crosswalk': ('identity', 'Confirm fallback identities supported by the same original region?',
        'One entity for each enumerated one-to-one original-region/chapter/role match; preserve both sealed IDs in a crosswalk.',
        'Fallback locators differ between passes. Region plus chapter or linked participation values supports identity; no match uses title alone.'),
    'petition-disposition-enum': ('lifecycle_ambiguity', 'How do petition decisions map to the update enum?',
        'Keep explicit agency dispositions diagnostically as unknown event_type; no adoption-as-withdrawal or invented new opportunity.',
        'The brief expressly includes petition closure updates and has no exact closure enum. Identity, missing before-state and targets remain cases.'),
    'issue-42-25-boundary': ('scope', 'Which issue date controls 42:25 interval accounting?',
        'Propose July 27, 2026 issue date; remove unrelated new notices from the scored interval and retain linked follow-up only within its horizon.',
        'Cover July 25 conflicts with body footers and other supplied official issue views. Boundary uncertainty cannot be resolved by agent agreement.'),
    'issue-42-19-date': ('scope', 'Resolve May 4 / May 6 publication wording in 42:19?',
        'Propose May 4, 2026 as the issue publication date; keep the erroneous May 6 footers as source-conflict evidence.',
        'Cover and HTML agree on May 4. The two-day discrepancy does not cross the interval boundary or change explicit participation deadlines.'),
    'stale-horizon-notes': ('scope', 'How should interim follow-up-pending notes be reconciled?',
        'Retain original notes; verify endpoints against supplied issue coverage and append a final horizon status. Never turn inspection coverage into a lifecycle verdict.',
        'Both attestations describe a later completed sweep while immutable labels retain interim pending prose. Unknown endpoints and concrete unfinished horizons remain cases.'),
    'publication-copy': ('disagreement', 'Repair Pass B’s known Issue 6/7 copy error?',
        'Propose append-only wording corrections to “November 17, 2025; Volume 42, Issue 7”; preserve identity, date and cohorts.',
        'The preseal supplement enumerates 15 notice copy errors. Publication wording is otherwise reference-only; this is one disclosed output-quality repair class.'),
    'completion-attribution': ('disagreement', 'Reconcile completion counts with final source-view attribution?',
        'Final source-view attribution, corrected append-only; same as CT C16 (pending owner signature). Verify the 18 B discrepancies, including two intentionally counted duplicate views; never sum views or equate absent evidence links with an uninspected source.',
        'Final historical labels can postdate completion rows. Direct-evidence counts are a diagnostic; the brief permits overlapping source-view attribution. A TOC counts also require source-attribution interpretation, not automatic zeroing.'),
}

CLASS_ORDER = ('explicit-opening', 'fallback-key-crosswalk', 'issue-42-19-date', 'issue-42-25-boundary',
               'on-or-before-cutoff', 'petition-disposition-enum', 'publication-copy', 'stale-horizon-notes',
               'completion-attribution')


def review_queue(passes, pairs, candidates, mapping):
    byrecord = {r['record_id']: (s, r) for s, rows in passes.items() for r in rows}
    byid = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    pair_for = {rid: p for p in pairs for s in 'AB' for rid in p[s + '_record_ids']}
    issues = {}
    def records_for(r):
        p = pair_for[r['record_id']]
        return [(s, byrecord[rid][1]) for s in 'AB' for rid in p[s + '_record_ids']]
    def groups(rr):
        roots = []
        for s, r in rr:
            ids = r['payload'].get('proceeding_ids', [r['payload'].get('proceeding_id')])
            roots += [(s, byid[s][x]) for x in ids if x in byid[s]]
        docs = sorted({x for s, r in roots or rr for x in doc_aliases(r)})
        if docs:
            return '+'.join(docs), docs
        # No native Doc. No.: use exact issue and chapters, with original page as
        # the stable fallback. Never invent a Doc. No. for the owner sheet.
        codes = sorted({x for s, r in rr for x in chapters(r)})
        pages = sorted({x for s, r in rr for x in pdf_pages(r) if x[1] != 1})
        return (' / '.join(codes[:4]) or 'no-Doc-No') + (' @ ' + canonical(pages[:1]) if pages else ''), []
    def add(trigger, rr, kind, detail, policy=None, evidence_extra=None, group=None):
        rr = sorted({(s, r['record_id']): (s, r) for s, r in rr}.values(), key=lambda x: (x[0], x[1]['record_id']))
        proceeding, docs = groups(rr)
        key = digest([trigger, kind, [(s, r['record_id']) for s, r in rr], detail.get('field'), detail.get('role'), detail.get('manifest_entry_id'), policy])
        if key in issues:
            # Preserve both pass reports without counting a shared ambiguity twice.
            reports = issues[key].setdefault('additional_reports', [])
            if detail != issues[key]['detail'] and detail not in reports:
                reports.append(detail)
            return
        issues[key] = {'sub_issue_id': key, 'trigger': trigger, 'class': kind, 'detail': detail,
                       'policy_key': policy, 'proceeding': group or proceeding, 'doc_numbers': docs,
                       'entity_ids': sorted({r['entity_id'] for s, r in rr}),
                       'record_ids': {s: sorted(r['record_id'] for side, r in rr if side == s) for s in 'AB'},
                       'evidence': pointers([r for s, r in rr]) + (evidence_extra or [])}
    for p in pairs:
        if p['record_type'] == 'rejected_candidate':
            continue
        rr = [(s, byrecord[rid][1]) for s in 'AB' for rid in p[s + '_record_ids']]
        for d in p['field_diffs']:
            temporal = d['field'].startswith('temporal.')
            policy = 'explicit-opening' if d['field'] == 'temporal.open.present' else None
            if temporal and '.cutoff' in d['field'] and '.close' in d['field']:
                literals = ' '.join(t['literal'] for s, r in rr for t in r['payload'].get('temporal', []) if t['role'] == 'close')
                if 'on or before' in literals.casefold():
                    policy = 'on-or-before-cutoff'
            add('date_ambiguity' if temporal else 'disagreement', rr,
                'decisive_temporal' if temporal else p['record_type'] + '.' + d['field'], d, policy)
    for c in candidates:
        if not c['review_required']:
            continue  # High-confidence padding normalization is not a disagreement.
        rr = [('A', byid['A'][c['A_entity_id']]), ('B', byid['B'][c['B_entity_id']])]
        add('identity', rr, 'fallback_identity', c, 'fallback-key-crosswalk')
    # Rejections are compared only to an unmatched acceptance on the same item,
    # not to other rejections or to absent records. Same PDF page alone is weak.
    for p in pairs:
        if p['record_type'] == 'rejected_candidate' or p['in_A'] == p['in_B']:
            continue
        side = 'A' if p['in_A'] else 'B'
        other = 'B' if side == 'A' else 'A'
        acc = byrecord[p[side + '_record_ids'][0]][1]
        for rej in passes[other]:
            if rej['record_type'] != 'rejected_candidate':
                continue
            shared = sorted(set(doc_aliases(acc)) & set(doc_aliases(rej)))
            region = sorted(pdf_pages(acc) & pdf_pages(rej))
            codes = sorted(chapters(acc) & chapters(rej))
            same_views = sorted({e['manifest_entry_id'] for e in evidence(acc)} & {e['manifest_entry_id'] for e in evidence(rej)})
            # This no-number notice has a distinctive subject on the same
            # original page, but the passes quote different paragraphs. Its
            # heading is in the acceptance title and rejection rationale.
            schedule_subject = (acc['record_type'] == 'notice' and
                                'schedule i' in norm(acc['payload'].get('title', '')) and
                                'schedule i' in norm(rej['payload'].get('rationale', '')) and
                                'pharmacy' in norm(canonical(evidence(acc))) and
                                'pharmacy' in norm(canonical(rej)))
            if not ((shared and region) or (region and codes) or (region and schedule_subject)):
                continue
            add('disagreement', [(side, acc), (other, rej)], 'accepted_rejected',
                {'accepted_pass': side, 'accepted_type': acc['record_type'],
                 'reason_code': rej['payload']['reason_code'], 'rationale': rej['payload']['rationale'],
                 'match_basis': {'doc_aliases': shared, 'original_pages': region, 'chapters': codes, 'views': same_views}})
    for side, rows in passes.items():
        for r in rows:
            if r['record_type'] == 'rejected_candidate':
                continue
            rr, p = records_for(r), r['payload']
            for t in p.get('temporal', []):
                if t['role'] in ROLES and t['status'] in ('unknown', 'conflicting'):
                    add('date_ambiguity', rr, 'unknown_conflicting_date',
                        {'role': t['role'], 'reported_by': side, 'value': {k: t.get(k) for k in ('role',) + DECISIVE_TEMP}},
                        'explicit-opening' if t['role'] == 'open' else None)
            if r['record_type'] == 'update':
                if p['event_type'] == 'correction' and not p.get('temporal'):
                    add('scope', rr, 'nonparticipation_correction',
                        {'question': 'Does this regulatory-text/contact erratum change participation, or only substantive/reference text?',
                         'target_scope': p['target_scope']})
                if p['event_type'] == 'unknown':
                    is_petition = any(x.startswith('PFR') for x in doc_aliases(r))
                    add('lifecycle_ambiguity', rr, 'event_enum', {'event_type': p['event_type']},
                        'petition-disposition-enum' if is_petition else None)
                if p.get('before_missing_reason'):
                    add('lifecycle_ambiguity', rr, 'missing_before', {'reason': p['before_missing_reason']})
                if not p['target_opportunity_ids']:
                    add('lifecycle_ambiguity', rr, 'empty_target', {'reason': p.get('target_unresolved_reason')})
                if p['event_type'] in ('full_withdrawal', 'partial_withdrawal', 'reopening'):
                    add('lifecycle_ambiguity', rr, 'target_scope', {'event_type': p['event_type'], 'target_scope': p['target_scope']})
            notes = ' '.join(r['unresolved'])
            flat = re.sub(r'\s+', '', notes).casefold()
            if 'july25' in flat or 'july 25' in notes.casefold():
                if any(e['manifest_entry_id'].startswith('va-42-25-') for e in evidence(r)):
                    add('scope', rr, 'issue_date_boundary', {'issue': '42:25', 'question': 'July 25 cover versus July 27 official issue views'}, 'issue-42-25-boundary')
            if ('follow' in flat or 'horizon' in flat) and any(x in flat for x in ('pending', 'notyet', 'unfinished')):
                add('scope', rr, 'interim_horizon', {'question': 'Interim pending note versus final attestation; verify supplied horizon'}, 'stale-horizon-notes')
            # Concrete source/identity/scope gaps are retained even when both passes agree.
            real_questions = []
            missing_questions = []
            for x in r['unresolved']:
                compressed = re.sub(r'\s+', '', x).casefold()
                if ('fallback' in compressed or 'groupingreview' in compressed or 'citationtypo' in compressed):
                    continue  # Existing fallback class; wording-only scope notes.
                if 'july25' in compressed and 'july27' in compressed:
                    continue  # Covered once, in the boundary class.
                if 'may4' in compressed and 'may6' in compressed:
                    continue  # Reference-only: neither date changes cohort or a participation value.
                if re.search(r'(?:not supplied|not among|missing).{0,40}(?:original|target|histor|notice)|'
                             r'(?:original|target|histor|notice).{0,40}(?:not supplied|missing)', x, re.I):
                    missing_questions.append(x)
                elif re.search(r'(?:scope|inclusion).{0,25}(?:review|uncertain)|(?:review|uncertain).{0,25}(?:scope|inclusion)|'
                               r'(?:identity|docno|doc\.?\s*no|alias).{0,60}(?:conflict|mismatch|crosswalk)|'
                               r'(?:conflict|mismatch).{0,40}(?:pdf|html)|'
                               r'(?:unbounded|unfinished horizon|unknown.{0,20}deadline)', x, re.I):
                    real_questions.append(x)
            if real_questions:
                add('scope', rr, 'concrete_source_scope', {'questions': real_questions})
            if missing_questions:
                add('missing_source', rr, 'missing_original', {'questions': missing_questions})
            # Visuals only when they determine identity, role, participation date or
            # status. Formula/figure images in regulatory text are reference-only.
            visuals = [e for e in evidence(r) if e['mode'] == 'visual_review' and re.search(
                r'closing.*Doc|Doc\.?No|hearing.*check|deadline|filing stamp|strike.{0,20}(?:date|hearing)',
                e['locator'] + ' ' + e.get('quote_or_mark_description', ''), re.I)]
            if visuals:
                add('visual_mark', rr, 'decisive_visual', {'locators': sorted({e['locator'] for e in visuals})})
    manifest = read(STATE / 'manifest.jsonl')
    for m in manifest:
        if m['retrieval']['result'] != 'retrieved':
            add('missing_source', [], 'source_gap', {'manifest_entry_id': m['entry_id'], 'result': m['retrieval']['result']},
                evidence_extra=[{'manifest_entry_id': m['entry_id'], 'locator': 'manifest gap; no original', 'quote': ''}], group='VA-source-gaps')
    # External HTML images are named missing sources, even where a PDF offers a
    # potentially equivalent figure. They are not silently treated as inspected.
    for m in read(INPUTS / 'manifest.pass.jsonl'):
        absent = [x for x in m.get('text_failure_locators', []) if x.startswith('external image not retained:')]
        if absent:
            add('missing_source', [], 'unretained_body_images',
                {'manifest_entry_id': m['entry_id'], 'missing_image_count': len(absent),
                 'question': 'Recover through an allowed route, establish equivalence transparently, narrow or keep the viewing gap.'},
                evidence_extra=[{'manifest_entry_id': m['entry_id'], 'locator': 'manifest text_failure_locators; external images not supplied', 'quote': ''}],
                group='VA-source-gaps')
    # The 18 sealed-B discrepancies reproduce its attestation from direct record
    # evidence. A's TOC attributions are not assumed to be evidence-list counts.
    for row in read(STATE / 'completion.jsonl'):
        if row['pass'] != 'pass_B':
            continue
        mid = row['manifest_entry_id']
        linked = [r for r in passes['B'] if r['record_type'] != 'rejected_candidate' and
                  mid in {e['manifest_entry_id'] for e in r['evidence']}]
        if row['candidate_count'] != len(linked):
            add('disagreement', [('B', r) for r in linked], 'completion_attribution',
                {'manifest_entry_id': mid, 'completion_candidate_count': row['candidate_count'],
                 'final_direct_evidence_count': len(linked), 'note': 'Attribution diagnostic, not an assertion that only direct evidence counts.'},
                'completion-attribution', evidence_extra=[{'manifest_entry_id': mid, 'locator': 'completion row versus final direct-evidence links', 'quote': ''}],
                group='VA-source-accounting')
    quality = json.loads((STATE / 'supplements/pass-B/preseal-output-quality.json').read_text())
    # The 15 known publication_wording copy errors remain in wording_diffs;
    # a disclosed copy error is not an exception to decisive-field materiality.
    for err in quality['schema_blockers']:
        r = byrecord[err['record_id']][1]
        add('date_ambiguity', records_for(r), 'cutoff_enum_blocker', err)
    # Collapse only >=10 unique entity-pairs/source instances. All smaller
    # policy questions stay as concrete cases; no mandatory small-class exception.
    groups_by_policy = collections.defaultdict(list)
    for issue in issues.values():
        if issue['policy_key']:
            groups_by_policy[issue['policy_key']].append(issue)
    def instance(x):
        return ('source', x['detail']['manifest_entry_id']) if x['detail'].get('manifest_entry_id') else tuple(x['entity_ids'])
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
        item = {'item_id': 'va-' + ('policy-' if policy else 'review-') + digest(key), 'item_kind': key[0],
                'trigger': trigger, 'policy_key': policy, 'proceeding': 'VA-policy' if policy else key[1],
                'doc_numbers': sorted({d for x in xx for d in x['doc_numbers']}), 'record_ids': records,
                'entity_ids': sorted({e for x in xx for e in x['entity_ids']}), 'sub_issues': xx,
                'affected_instance_count': len({instance(x) for x in xx}),
                'evidence': ev, 'estimated_minutes': 10 if policy else 5 if trigger in ('identity', 'visual_mark') or len(xx) >= 3 else 3}
        if policy:
            _, item['question'], item['proposed_answer'], item['rationale'] = POLICIES[policy]
            # Distinct proceedings for examples; retain all original references
            # and every affected record in sub_issues/appendix.
            reps, seen = [], set()
            for x in sorted(xx, key=lambda x: (x['proceeding'], x['sub_issue_id'])):
                representative_group = x['detail'].get('manifest_entry_id') or x['proceeding']
                if representative_group in seen:
                    continue
                rep_evidence = x['evidence']
                if x['detail'].get('manifest_entry_id'):
                    rep_evidence = [e for e in rep_evidence if e['manifest_entry_id'] == x['detail']['manifest_entry_id']]
                reps.append({'proceeding': x['proceeding'], 'record_ids': x['record_ids'], 'detail': x['detail'],
                             'sub_issue_id': x['sub_issue_id'], 'evidence': rep_evidence[:3]})
                seen.add(representative_group)
                if len(reps) == 3:
                    break
            item['representative_instances'] = reps
        else:
            item['question'] = f'Resolve {trigger.replace("_", " ")} for {item["proceeding"]}; retain unsupported facts as unknown/conflicting.'
        items.append(item)
    items.sort(key=lambda i: (i['item_kind'] != 'class', CLASS_ORDER.index(i['policy_key']) if i['policy_key'] else 99,
                              i['proceeding'], TRIGGERS.index(i['trigger'])))
    for kind, prefix in [('class', 'C'), ('case', 'K')]:
        for n, item in enumerate([i for i in items if i['item_kind'] == kind], 1):
            item['owner_ref'] = f'{prefix}{n:02d}'
    return items


def queue_markdown(items, summary):
    classes = [i for i in items if i['item_kind'] == 'class']
    cases = [i for i in items if i['item_kind'] == 'case']
    md = ['# VA human review — proposed class and case decisions', '',
          f'{len(classes)} class items; {len(cases)} case items. All are unsigned proposals. No sealed pass or adjudication was changed.', '',
          'Class decisions settle only the named policy facet; concrete targets, dates and missing evidence remain cases. '
          'Issue padding maps verified hash preimages and is an identity candidate, not a disagreement. '
          'Latest append-only label-chain heads are compared once. Reference wording is retained in pairs.wording_diffs.', '',
          '## Counts by trigger', '', '| Trigger | Class | Case | Minutes |', '|---|---:|---:|---:|']
    for t in TRIGGERS:
        md.append(f'| {t} | {sum(i["item_kind"] == "class" and i["trigger"] == t for i in items)} | '
                  f'{sum(i["item_kind"] == "case" and i["trigger"] == t for i in items)} | '
                  f'{sum(i["estimated_minutes"] for i in items if i["trigger"] == t)} |')
    md += ['', '## Class questions', '']
    for i in classes:
        md += [f'### {i["owner_ref"]}. {i["question"]}', '', f'`{i["item_id"]}`; {i["affected_instance_count"]} instances; '
               f'{sum(map(len, i["record_ids"].values()))} label versions; {i["estimated_minutes"]} min.', '',
               '**Proposed:** ' + i['proposed_answer'], '', i['rationale'], '',
               'Owner may accept, reject or specify exceptions by immutable record ID; nothing is applied.', '']
        for rep in i['representative_instances']:
            md.append(f'- **{rep["proceeding"]}**; sub-issue `{rep["sub_issue_id"]}`')
            if rep['detail'].get('manifest_entry_id'):
                md.append('  - Source attribution: ' + canonical(rep['detail']))
            for ev in rep['evidence']:
                md.append(f'  - `{ev["manifest_entry_id"]}`, {ev["locator"]}: “{" ".join(ev["quote"].split())[:200]}”')
        md.append('')
    md += ['## Cases bundled by Doc. No. (or precise no-number source)', '']
    for i in cases:
        md += [f'### {i["owner_ref"]}. {i["proceeding"]} — {i["trigger"]}', '', f'`{i["item_id"]}`; {i["estimated_minutes"]} min.', '', i['question'], '']
        for x in i['sub_issues']:
            detail = x['detail']
            md.append(f'- `{x["sub_issue_id"]}` **{x["class"]}**: {canonical(detail)[:1400]}')
        md.append('')
        for ev in i['evidence'][:8]:
            md.append(f'- `{ev["manifest_entry_id"]}`, {ev["locator"]}: “{" ".join(ev["quote"].split())[:200]}”')
        md.append('')
    md += ['## Agreement statistics', '', '| Record type | A | B | Exact both | Mapped both | A only | B only | Paired decisive agreement |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for typ, st in summary['record_statistics'].items():
        md.append('| ' + typ + ' | ' + ' | '.join(str(st[k]) for k in ('A', 'B', 'exact_ID_both', 'comparison_both', 'A_only', 'B_only', 'both_decisive_agree')) + ' |')
    md += ['', 'Rejection exact-ID intersections are not agreement statistics; rejected candidates are compared by evidence only. '
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
    passes, seals = {}, {}
    for side in 'AB':
        path = STATE / f'pass-{side}.jsonl'
        att = json.loads((STATE / 'attestations' / f'pass-{side}.json').read_text())
        seals[side] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert seals[side] == att['output_sha256'], f'Pass {side} differs from sealed hash'
        passes[side] = latest(read(path))
    candidates, mapping = identities(passes)
    pairs = compare(passes, mapping, candidates)
    write('identity-candidates.jsonl', candidates)
    write('pairs.jsonl', pairs)
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
               'mechanical_issue_mappings': sum(c['comparison_mapping_applied'] and c['mechanical_issue_normalization'] for c in candidates),
               'decisive_slots_equal': sum(p['decisive_slots_equal'] for p in pairs),
               'decisive_slots_total': sum(p['decisive_slots_total'] for p in pairs)}
    summary['reference_only_quality_notes'] = {'B_publication_wording_copy_errors': 15,
        'issue_42_19_cover_footer_date': 'May 4 / May 6 stays reference-only: no changed cohort or participation date.'}
    items = review_queue(passes, pairs, candidates, mapping)
    write('review-queue.jsonl', items)
    summary['queue'] = {kind: {t: sum(i['item_kind'] == kind and i['trigger'] == t for i in items) for t in TRIGGERS}
                        for kind in ('class', 'case')}
    summary['queue_minutes'] = sum(i['estimated_minutes'] for i in items)
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


