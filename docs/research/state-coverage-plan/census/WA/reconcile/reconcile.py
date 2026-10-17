#!/usr/bin/env python3
"""Washington sealed comparison. Deterministic, stdlib only; never adjudicates.

Run from any directory. Reads sealed WA inputs; never writes passes, run.json, or human verdicts.
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
INPUTS = OUT.parents[5] / '.census-passes/WA/inputs'
TYPES = ('notice', 'opportunity', 'proceeding', 'update', 'rejected_candidate')
TRIGGERS = ('disagreement', 'lifecycle_ambiguity', 'date_ambiguity', 'visual_mark', 'missing_source', 'identity', 'scope')
FIELDS = {'notice': ('proceeding_ids', 'cohorts'),
          'opportunity': ('opportunity_type', 'hearing_status', 'proceeding_id', 'cohorts'),
          'update': ('event_type', 'target_opportunity_ids', 'cohorts'),
          'proceeding': (), 'rejected_candidate': ()}
DECISIVE_TEMP = ('local_value', 'precision', 'status', 'iana_zone', 'cutoff', 'receipt_or_postmark')
ROLES = {'open', 'close', 'hearing_start', 'hearing_end'}
WSR = re.compile(r'(?<![0-9])\d{2}-\d{2}-\d{3}[a-z]?(?![0-9])', re.I)
ROOT = OUT.parents[5]

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
    """Rights-safe output: all long strings become short references plus hashes.

    Full strings exist only in memory and sealed inputs, never in reconcile/.
    Wording differences are fingerprinted separately below.
    """
    if isinstance(value, list):
        return [short_quotes(x) for x in value]
    if isinstance(value, str) and len(value) > 200:
        return {'excerpt': value[:180], 'characters': len(value), 'sha256': hashlib.sha256(value.encode()).hexdigest()}
    if isinstance(value, dict):
        return {k: short_quotes(v) for k, v in value.items()}
    return value


def fingerprint(value):
    return {'sha256': digest(value), 'reference_only': True}


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
        pairs.append({'pair_id': 'wa-pair-' + digest([typ, eid]), 'entity_id': eid, 'record_type': typ,
                      'in_A': bool(a), 'in_B': bool(b), 'exact_id_match': bool(a and b and a['entity_id'] == b['entity_id']),
                      'A_entity_id': a['entity_id'] if a else None, 'B_entity_id': b['entity_id'] if b else None,
                      'A_record_ids': [a['record_id']] if a else [], 'B_record_ids': [b['record_id']] if b else [],
                      'identity_candidate_id': candidate_ids.get(eid), 'field_diffs': diffs, 'wording_diffs': [{**{k:v for k,v in w.items() if k not in ('A','B')}, 'A': fingerprint(w.get('A')), 'B': fingerprint(w.get('B'))} for w in wording],
                      'derivable_membership_diffs': derived, 'decisive_slots_equal': sum(slots), 'decisive_slots_total': len(slots)})
    return pairs


# Native identity is reconstructed from the brief's immutable hash tuples.
def compact_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def numbers(r, operative=False):
    ev = r['payload'].get('after_evidence', []) if operative else r['evidence']
    found = {m[1].lower() for e in ev if (m := re.fullmatch(r'wa-f-(\d\d-\d\d-\d{3}[a-z]?)-(?:pdf|htm)', e['manifest_entry_id'], re.I))}
    return sorted(found)


def native_maps(passes):
    pool = set()
    for rows in passes.values():
        for r in rows:
            pool.update(WSR.findall(canonical(r)))
    roots = {compact_digest(['wa-register', 'proceeding', n.lower()]): n.lower() for n in pool}
    result = {}
    for rows in passes.values():
        for r in rows:
            if r['record_type'] == 'proceeding':
                result[r['entity_id']] = roots.get(r['entity_id'].rsplit('/', 1)[-1], 'unresolved-root')
    return result


def identities(passes):
    # WA native tuples agree for all shared entities. Only map different IDs
    # on a unique operative filing/type; never merge distinct update ordinals.
    candidates, mapping = [], {}
    by = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    for typ in ('notice', 'opportunity', 'update'):
        aa = [r for r in passes['A'] if r['record_type'] == typ and r['entity_id'] not in by['B']]
        bb = [r for r in passes['B'] if r['record_type'] == typ and r['entity_id'] not in by['A']]
        for a in aa:
            for b in bb:
                shared = sorted(set(numbers(a, typ == 'update')) & set(numbers(b, typ == 'update')))
                if not shared or (typ == 'opportunity' and a['payload']['opportunity_type'] != b['payload']['opportunity_type']):
                    continue
                candidates.append({'candidate_id': 'wa-identity-'+digest([a['entity_id'], b['entity_id']]),
                    'record_type': typ, 'A_entity_id': a['entity_id'], 'B_entity_id': b['entity_id'],
                    'A_record_ids': [a['record_id']], 'B_record_ids': [b['record_id']],
                    'match_basis': {'same_operative_filing': shared}, 'confidence': 'medium',
                    'comparison_mapping_applied': False, 'review_required': True,
                    'reason': 'Possible split/merge; immutable action ordinal and target scope require owner inspection.'})
    return candidates, mapping


POLICIES = {
 'opening-cutoff': ('date_ambiguity', 'What cutoff applies to openings?',
    'not_applicable; same as CT C14 (pending owner signature).',
    'An opening is not a submission cutoff. Preserve its stated precision; do not create an instant.'),
 'explicit-opening': ('date_ambiguity', 'Keep applicable opening roles, including unknown ones?',
    'Keep supported opening wording or unknown/null; same as CT C15 / VA C01 (pending owner signature).',
    'A published filing timestamp is not automatically a legal opening instant.'),
 'relative-opening': ('date_ambiguity', 'Resolve an opening stated only as filing or publication?',
    'Keep literal anchor and null unasserted local value; same relative-clock principle as CT C10–C11 (pending owner signature).',
    'Do not calculate an unstated date or copy the publication date into a participation role.'),
 'hearing-end': ('date_ambiguity', 'Keep explicit hearing end times in the same hearing opportunity?',
    'Retain every source-stated session start/end in ONE hearing opportunity per notice; cutoff not_applicable, same as CT C13 (pending owner signature).',
    'Signed WA Q6 fixes one opportunity, while all dated sessions and their explicitly stated ranges remain represented.'),
 'receipt-condition': ('date_ambiguity', 'Does bare “by” establish receipt rather than postmark?',
    'Preserve explicit received/postmarked conditions only; bare “by” stays literal with null receipt condition.',
    'A temporal endpoint alone does not select a delivery condition; every affected original remains enumerated.'),
 'prepublication-carry-in': ('disagreement', 'Can first interval publication also carry an already open window?',
    'Allow new_notice plus carry_in where the stated window opened before June 3 and remained active then. Preserve the printed opening and issue date.',
    'The common brief expressly permits overlapping cohorts. Filing/opening and authoritative publication are distinct.'),
 'provisional-root': ('identity', 'Use the current filing when no earlier root is explicitly cited?',
    'Keep current WSR key provisionally; do not merge by title. Same evidence-based identity principle as VA C02 (pending owner signature).',
    'The frozen WA tuple requires the earliest explicitly cited initiating chain root; historical amendatory citations are not initiating roots.'),
 'missing-before': ('lifecycle_ambiguity', 'May a document-backed action retain a missing before-state?',
    'Retain diagnostic explicit action with its specific missing-before reason; same as CT C4 / C5 (pending owner signature).',
    'No invented prior opportunity. Exact scope, supplied targets and source gaps still need concrete review.'),
 'undated-cr101-target': ('lifecycle_ambiguity', 'Does withdrawal of an undated CR-101 imply a participation target?',
    'Keep explicit withdrawal evidence with empty targets when no dated opportunity is evidenced; same diagnostic-action principle as CT C5 (pending owner signature).',
    'The signed WA CR-101 scope requires a dated deadline or meeting; the withdrawal cannot manufacture one.'),
 'completion-attribution': ('disagreement', 'Reconcile completion counts with final source-view attribution?',
    'Verify final source-view attribution and append corrections where needed; same as CT C16 (pending owner signature).',
    'Direct evidence counts are a diagnostic, not proof that a source was uninspected. Do not sum overlapping source views.'),
}


def review_queue(passes, pairs, candidates, mapping, att):
    byrecord = {r['record_id']: (s, r) for s, rows in passes.items() for r in rows}
    byid = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    rootmap = native_maps(passes)
    pairfor = {rid: p for p in pairs for s in 'AB' for rid in p[s+'_record_ids']}
    issues = {}
    def rr_for(r):
        p = pairfor[r['record_id']]
        return [byrecord[rid] for s in 'AB' for rid in p[s+'_record_ids']]
    def chain(rr):
        roots = set()
        for s, r in rr:
            p = r['payload']
            ids = [r['entity_id']] if r['record_type'] == 'proceeding' else p.get('proceeding_ids', []) + ([p['proceeding_id']] if p.get('proceeding_id') else [])
            roots.update(rootmap.get(eid, 'unresolved-root') for eid in ids)
        return ' / '.join(sorted(roots)) if roots else ((numbers(rr[0][1]) or ['WA-source-gaps'])[0] if rr else 'WA-source-gaps')
    def add(trigger, rr, kind, detail, policy=None, group=None, extra=None):
        # Instances are immutable entity pairs, not one copy per reporting pass.
        ids = {s: sorted({r['record_id'] for side, r in rr if side == s}) for s in 'AB'}
        key = [trigger, ids, kind, policy, group, detail]
        sid = 'wa-sub-'+digest(key)
        issues[sid] = {'sub_issue_id': sid, 'trigger': trigger, 'class': kind, 'policy_key': policy,
            'proceeding': group or chain(rr), 'record_ids': ids,
            'entity_ids': sorted({r['entity_id'] for s,r in rr}),
            'wsr_numbers': sorted({n for s,r in rr for n in numbers(r)}),
            'detail': detail, 'evidence': pointers([r for s,r in rr])+(extra or [])}
    for p in pairs:
        if p['record_type'] == 'rejected_candidate':
            continue
        rr = [byrecord[rid] for s in 'AB' for rid in p[s+'_record_ids']]
        for d in p['field_diffs']:
            field = d['field']; policy = None
            if re.match(r'temporal\.open.*\.cutoff$', field): policy = 'opening-cutoff'
            elif field == 'temporal.open.present': policy = 'explicit-opening'
            elif field == 'temporal.hearing_end.present': policy = 'hearing-end'
            elif field.endswith('.receipt_or_postmark') and any('by' in canonical(d.get(s)).lower() for s in 'AB'): policy = 'receipt-condition'
            elif field == 'cohorts' and {tuple(sorted(d['A'])),tuple(sorted(d['B']))} == {('new_notice',),('carry_in','new_notice')}: policy = 'prepublication-carry-in'
            add('date_ambiguity' if field.startswith('temporal.') else 'disagreement', rr,
                'decisive_temporal' if field.startswith('temporal.') else p['record_type']+'.'+field, d, policy)
        if p['in_A'] != p['in_B']:
            side = 'A' if p['in_A'] else 'B'; other = 'B' if side == 'A' else 'A'
            acc = rr[0][1]; own = set(numbers(acc))
            for rej in passes[other]:
                if rej['record_type'] == 'rejected_candidate' and own & set(numbers(rej)):
                    # Shared individual filing original, not an issue/page alone.
                    shared = sorted({e['sha256'] for e in acc['evidence']} & {e['sha256'] for e in rej['evidence']})
                    if shared:
                        add('disagreement', rr+[(other,rej)], 'accepted_rejected',
                            {'accepted_pass': side,'accepted_type': acc['record_type'], 'reason_code':rej['payload']['reason_code'],
                             'rejection_rationale': rej['payload']['rationale'], 'same_filing': sorted(own & set(numbers(rej))), 'shared_original_hashes':shared})
    for c in candidates:
        add('identity', [('A',byid['A'][c['A_entity_id']]),('B',byid['B'][c['B_entity_id']])], 'split_merge', c)
    seen = set()
    for s, rows in passes.items():
        for r in rows:
            if r['record_type'] == 'rejected_candidate': continue
            p = pairfor[r['record_id']]
            if p['pair_id'] in seen: continue
            seen.add(p['pair_id']); rr = rr_for(r)
            notes = [(side,x) for side,q in rr for x in q['unresolved']]
            for role in sorted(ROLES):
                entries = [t for side,q in rr for t in q['payload'].get('temporal',[]) if t['role']==role]
                unknown = [t for t in entries if t['status'] in ('unknown','conflicting')]
                if unknown:
                    policy = 'explicit-opening' if role=='open' and all(t['precision']=='unknown' for t in unknown) else 'relative-opening' if role=='open' and all(t['precision']=='relative' for t in unknown) else None
                    add('date_ambiguity',rr,'unknown_conflicting_date',{'role':role,'values':distinct({k:t.get(k) for k in ('role',)+DECISIVE_TEMP} for t in unknown)},policy)
            if r['record_type']=='proceeding' and any(re.search('provisional|no.{0,20}(?:earlier|initiating)|root.{0,20}(?:unresolved|not)',x,re.I) for side,x in notes):
                add('identity',rr,'provisional_root',{'question':'Confirm explicitly cited root or current-filing provisional root.'},'provisional-root')
            if r['record_type']=='update':
                pp=[q['payload'] for side,q in rr]
                add('lifecycle_ambiguity',rr,'target_scope',{'events':distinct(q['event_type'] for q in pp),
                    'targets_by_pass':{side:q['payload']['target_opportunity_ids'] for side,q in rr},
                    'scope_fingerprints':{side:fingerprint(q['payload']['target_scope']) for side,q in rr}})
                if any(q.get('before_missing_reason') for q in pp):
                    add('lifecycle_ambiguity',rr,'missing_before',{'reasons':distinct(q['before_missing_reason'] for q in pp if q.get('before_missing_reason'))},'missing-before')
                if any(not q['target_opportunity_ids'] for q in pp):
                    cr101=any(re.search(r'preproposal|(?:withdrawal of |of )CR.?101',q.get('target_scope',''),re.I) for q in pp)
                    add('lifecycle_ambiguity',rr,'empty_target',{'reasons':distinct(q.get('target_unresolved_reason') for q in pp)},'undated-cr101-target' if cr101 else None)
            # Source-specific facts remain cases; generic null-zone boilerplate,
            # historical support, immutable reverse indexes and future horizons do not.
            for side,x in notes:
                compressed=re.sub(r'\s+','',x).casefold()
                if any(t in compressed for t in ['pst[pdt]','weekday','tentative','active-at-2026-06-03','unboundedearly-stage','september22eleven','hearingjoininginformationconflicts','date-range','thursday,august17']):
                    add('date_ambiguity' if not ('active-at' in x or 'Unbounded' in x) else 'scope',rr,'concrete_source_question',{'reported_by':side,'note':x})
                elif 'source-labelledhearing' in compressed or 'mechanism/timeambiguity' in compressed:
                    add('scope',rr,'hearing_mechanism',{'reported_by':side,'note':x})
                elif re.search(r'partial vs full|partial.{0,30}withdrawal.{0,30}(?:scope|judgment)|root.{0,30}only indirectly|withdrawal.{0,40}conflict',x,re.I):
                    add('lifecycle_ambiguity',rr,'concrete_lifecycle_question',{'reported_by':side,'note':x})
    # The backlink anomaly is derivable, reference-only, not an additional
    # notice-membership disagreement; explicitly carry it into the deliverable.
    gaps=read(STATE/'manifest.jsonl')
    for m in gaps:
        if m['retrieval']['result']!='retrieved':
            future=m['entry_id'] in ('wa-issue-26-20','wa-issue-26-21')
            add('missing_source',[],'unpublished_follow_up' if future else 'source_gap',
                {'manifest_entry_id':m['entry_id'],'result':m['retrieval']['result'],'not_disagreement':future},
                group='WA-source-gaps',extra=[{'manifest_entry_id':m['entry_id'],'locator':'manifest gap; no original','quote':''}])
    # Full direct evidence counts are only attribution diagnostics. Include
    # notice/proceeding/update and temporal/before/after views consistently.
    linked={s:collections.Counter(eid for r in rows for eid in {e['manifest_entry_id'] for e in evidence(r)} if r['record_type']!='rejected_candidate') for s,rows in passes.items()}
    for row in read(STATE/'completion.jsonl'):
        s=row['pass'][-1];mid=row['manifest_entry_id'];count=linked[s][mid]
        if count!=row['candidate_count']:
            rr=[(s,r) for r in passes[s] if r['record_type']!='rejected_candidate' and mid in {e['manifest_entry_id'] for e in evidence(r)}]
            add('disagreement',rr,'completion_attribution',{'manifest_entry_id':mid,'pass':row['pass'],'completion_count':row['candidate_count'],'evidence_attribution_count':count},'completion-attribution',group='WA-source-accounting',extra=[{'manifest_entry_id':mid,'locator':'completion vs union evidence attribution','quote':''}])
    policies=collections.defaultdict(list)
    for x in issues.values():
        if x['policy_key']:policies[x['policy_key']].append(x)
    def instance(x):
        return ('source',x['detail']['manifest_entry_id']) if x['detail'].get('manifest_entry_id') else tuple(x['entity_ids'])
    classes={k for k,xx in policies.items() if len({instance(x) for x in xx})>=10}
    bundles=collections.defaultdict(list)
    for x in issues.values():
        key=('class',x['policy_key']) if x['policy_key'] in classes else ('case',x['proceeding'],x['trigger'])
        bundles[key].append(x)
    items=[]
    for key,xx in sorted(bundles.items()):
        xx.sort(key=canonical);policy=key[1] if key[0]=='class' else None;trigger=POLICIES[policy][0] if policy else key[2]
        i={'item_id':'wa-'+('policy-' if policy else 'review-')+digest(key),'item_kind':key[0],'trigger':trigger,'policy_key':policy,
           'proceeding':'WA-policy' if policy else key[1], 'record_ids':{s:sorted({rid for x in xx for rid in x['record_ids'][s]}) for s in 'AB'},
           'entity_ids':sorted({e for x in xx for e in x['entity_ids']}),'wsr_numbers':sorted({n for x in xx for n in x['wsr_numbers']}),
           'sub_issues':xx,'affected_instance_count':len({instance(x) for x in xx}),
           'evidence':sorted({canonical(e):e for x in xx for e in x['evidence']}.values(),key=canonical)}
        if policy:
            _,i['question'],i['proposed_answer'],i['rationale']=POLICIES[policy]
            reps=[];seen_groups=set()
            for x in sorted(xx,key=lambda x:(x['proceeding'],x['sub_issue_id'])):
                group=x['detail'].get('manifest_entry_id') or x['proceeding']
                if group in seen_groups:continue
                reps.append({k:x[k] for k in ('sub_issue_id','proceeding','record_ids','detail','evidence')});seen_groups.add(group)
                if len(reps)==3:break
            i['representative_instances']=reps
        else:i['question']=f'Resolve {trigger.replace("_"," ")} for WSR chain {i["proceeding"]}.'
        items.append(i)
    items.sort(key=lambda i:(i['item_kind']!='class',list(POLICIES).index(i['policy_key']) if i['policy_key'] else 99,i['proceeding'],TRIGGERS.index(i['trigger'])))
    for kind,prefix in [('class','C'),('case','K')]:
        for n,i in enumerate([x for x in items if x['item_kind']==kind],1):i['owner_ref']=f'{prefix}{n:02d}'
    return items


def main():
    passes={};seals={};att={}
    for s in 'AB':
        path=STATE/f'pass-{s}.jsonl';att[s]=json.loads((STATE/'attestations'/f'pass-{s}.json').read_text())
        seals[s]=hashlib.sha256(path.read_bytes()).hexdigest();assert seals[s]==att[s]['output_sha256']
        passes[s]=latest(read(path))
    candidates,mapping=identities(passes);pairs=compare(passes,mapping,candidates)
    items=review_queue(passes,pairs,candidates,mapping,att)
    refs=collections.defaultdict(list)
    for i in items:
        for s in 'AB':
            for rid in i['record_ids'][s]:refs[rid].append(i['item_id'])
    for p in pairs:p['review_refs']=sorted({ref for s in 'AB' for rid in p[s+'_record_ids'] for ref in refs[rid]})
    for name,rows in [('identity-candidates.jsonl',candidates),('pairs.jsonl',pairs),('review-queue.jsonl',items)]:write(name,rows)
    stats={}
    for typ in TYPES:
        pp=[p for p in pairs if p['record_type']==typ]
        stats[typ]={'A':sum(p['in_A'] for p in pp),'B':sum(p['in_B'] for p in pp),'exact_ID_both':sum(p['exact_id_match'] for p in pp),
            'comparison_both':sum(p['in_A'] and p['in_B'] for p in pp),'A_only':sum(p['in_A'] and not p['in_B'] for p in pp),
            'B_only':sum(p['in_B'] and not p['in_A'] for p in pp),'both_decisive_agree':sum(p['in_A'] and p['in_B'] and not p['field_diffs'] for p in pp)}
    summary={'sealed_sha256':seals,'record_statistics':stats,'identity_candidates':len(candidates),'identity_mappings':len(mapping),
        'decisive_slots_equal':sum(p['decisive_slots_equal'] for p in pairs),'decisive_slots_total':sum(p['decisive_slots_total'] for p in pairs),
        'union_opportunities':stats['opportunity']['A']+stats['opportunity']['B']-stats['opportunity']['comparison_both'],
        'queue':{kind:{t:sum(i['item_kind']==kind and i['trigger']==t for i in items) for t in TRIGGERS} for kind in ('class','case')},
        'reference_only_anomalies':['A 26-13-109 notice-to-workshop backlink is derivable from workshop notice_ids; preserve for append-only repair.',
          'B five approved v2 corrections selected at chain heads; 55 rejection tuple limitations do not create rejection-ID disagreements.',
          '27 unfinished B horizons and unpublished 26-20/21 remain unfinished, not disagreement.',
          'A three late-view image notes disclosed; regulatory reference figures are not decisive participation marks.']}
    (OUT/'comparison-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    md=['# WA review queue — proposed, unsigned','','Latest sealed chain heads only. Reference wording is fingerprinted in pairs.jsonl; full wording stays in sealed inputs.',
        'Class membership lists every affected record; three source-backed representative instances per class. Cases are bundled by WSR chain root and trigger. No adjudication.','',
        '## Counts by trigger','','| Trigger | Class | Case |','|---|---:|---:|']
    for t in TRIGGERS:md.append(f'| {t} | {summary["queue"]["class"][t]} | {summary["queue"]["case"][t]} |')
    for i in items:
        md += ['',f'## {i["owner_ref"]}. {i["question"]}','',f'`{i["item_id"]}`; {i["affected_instance_count"]} instances.', '']
        if i['item_kind']=='class':
            md += ['Proposed: '+i['proposed_answer'],'',i['rationale'],'']
            for rep in i['representative_instances']:
                md += [f'- WSR {rep["proceeding"]}; `{rep["sub_issue_id"]}`; detail fingerprint `{digest(rep["detail"])}`.']
                for ev in rep['evidence'][:2]:md += [f'  - `{ev["manifest_entry_id"]}`: {ev["locator"][:150]}; excerpt: '+ev['quote'][:180]]
            md += ['','Complete affected records:']
            for s in 'AB':md += [f'- {s}: `{rid}`' for rid in i['record_ids'][s]]
        else:
            for x in i['sub_issues']:md += [f'- `{x["sub_issue_id"]}`: {x["class"]}; '+canonical(short_quotes(x['detail']))]
            for e in i['evidence'][:4]:md += [f'- Original `{e["manifest_entry_id"]}`: {e["locator"][:140]}']
    (OUT/'REVIEW-QUEUE.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
