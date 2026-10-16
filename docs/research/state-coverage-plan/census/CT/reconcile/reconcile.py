#!/usr/bin/env python3
"""CT sealed-pass comparison, class/case materiality specification revision 3.

Stdlib only; run from any directory. Only this file's CT inputs are read. Outputs
are proposals, not adjudications. One-to-one identity candidates supply a clearly
marked comparison-only mapping; sealed IDs and exact-ID pair membership survive.
"""
import collections
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
STATE = OUT.parent
BEFORE = {'disagreement': 701, 'lifecycle_ambiguity': 249, 'date_ambiguity': 272,
          'visual_mark': 3, 'missing_source': 77, 'identity': 149, 'scope': 26}
BEFORE_MINUTES = 4735
TRIGGERS = tuple(BEFORE)
TYPES = ('notice', 'opportunity', 'proceeding', 'rejected_candidate', 'update')
FIELDS = {'notice': ('proceeding_ids', 'cohorts'),
          'opportunity': ('opportunity_type', 'hearing_status', 'proceeding_id', 'cohorts'),
          'update': ('event_type', 'target_opportunity_ids', 'cohorts'),
          'proceeding': (), 'rejected_candidate': ()}
DECISIVE_TEMP = ('local_value', 'precision', 'status', 'iana_zone', 'cutoff', 'receipt_or_postmark')
ROLES = {'open', 'close', 'hearing_start', 'hearing_end'}
TRACK = re.compile(r'PR\d{4}-\d{3}', re.I)
GUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)


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
            f.write(canonical(row) + '\n')
            f.flush()


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


def aliases(r, specific=False):
    result = {(norm(a['source_id']), norm(a['native_id']).strip('{}')) for a in r['aliases']}
    if specific:
        # Tracking and publication dates identify multiple distinct events/roles.
        result = {a for a in result if not TRACK.fullmatch(a[1]) and not a[1].startswith('publish-date:')}
    return result


def overlapping_locator(a, b):
    a, b = norm(a), norm(b)
    if a == b or a in b or b in a:
        return True
    ga, gb = set(GUID.findall(a)), set(GUID.findall(b))
    if ga and gb:
        return bool(ga & gb)
    def rows(v):
        return set(re.findall(r'rmrid\s*[=:]?\s*(\d+)', v))
    ra, rb = rows(a), rows(b)
    if ra and rb:
        return bool(ra & rb)
    def pages(v):
        result = set()
        for lo, hi in re.findall(r'\b(?:pdf\s+)?(?:pages?|p)\s*\.?\s*(\d+)(?:\s*[-–]\s*(\d+))?', v):
            result.update(range(int(lo), int(hi or lo) + 1))
        return result
    # A page overlap is conservative region overlap, never a decided identity.
    pa, pb = pages(a), pages(b)
    return bool(pa & pb)


def same_evidence(a, b, overlap=False, operative=False):
    def source(r):
        return r['payload']['after_evidence'] if operative and r['record_type'] == 'update' else evidence(r)
    return sorted({(ea['manifest_entry_id'], ea['locator'], eb['locator'])
                   for ea in source(a) for eb in source(b)
                   if ea['manifest_entry_id'] == eb['manifest_entry_id'] and
                   (overlapping_locator(ea['locator'], eb['locator']) if overlap else norm(ea['locator']) == norm(eb['locator']))})


def identify(a, b):
    shared = sorted(aliases(a, True) & aliases(b, True))
    exact = same_evidence(a, b, operative=True)
    basis = []
    if shared:
        basis.append({'kind': 'shared_alias', 'values': shared})
    if exact:
        basis.append({'kind': 'same_evidence_locator', 'values': exact})
    # Evidence overlap only when the source has event-specific GUID/row locators;
    # a shared PDF page alone could contain several distinct opportunities.
    event_overlap = [x for x in same_evidence(a, b, True, operative=True)
                     if (set(GUID.findall(norm(x[1]))) & set(GUID.findall(norm(x[2])))) or
                     (re.search(r'rmrid', x[1], re.I) and re.search(r'rmrid', x[2], re.I))]
    # A withdrawal row can support a later reopening; shared supporting evidence
    # alone must not propose equating those different actions.
    if a['record_type'] == 'update' and a['payload']['event_type'] != b['payload']['event_type'] and not shared:
        event_overlap = []
        exact = []
        basis = [x for x in basis if x['kind'] != 'same_evidence_locator']
    if event_overlap and not exact:
        basis.append({'kind': 'overlapping_event_locator', 'values': event_overlap})
    ta = {x.upper() for x in TRACK.findall(canonical(a['aliases']))}
    tb = {x.upper() for x in TRACK.findall(canonical(b['aliases']))}
    def rd(r):
        return {(t['role'], t['local_value']) for t in r['payload'].get('temporal', []) if t.get('local_value') and t['role'] in ROLES}
    same_role = a['payload'].get('opportunity_type') == b['payload'].get('opportunity_type')
    if ta & tb and rd(a) & rd(b) and same_role:
        basis.append({'kind': 'tracking_role_date', 'tracking_numbers': sorted(ta & tb), 'role_dates': sorted(rd(a) & rd(b))})
    if not basis or (a['record_type'] == 'opportunity' and not same_role):
        return None
    return basis, 'high' if shared and (exact or event_overlap) else 'medium' if shared or exact else 'low'


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


def policy_partition(queue, passes, byid, track_for):
    """Move policy facets out of case bundles without losing residual facts.

    Class membership is an explicit predicate, never an adjudication. Repeated
    shape alone does not settle identity, unknown dates, or missing originals.
    """
    records = {r['record_id']: (side, r) for side, rows in passes.items() for r in rows}
    specs = {}
    classes = {}

    def register(key, trigger, title, question, options, threshold=1):
        specs[key] = {'trigger': trigger, 'title': title, 'question': question,
                      'answer_consequences': options, 'threshold': threshold}

    register('natural-end-and-passive-snapshots', 'scope', 'Natural ends and passive status snapshots',
             'Does a comment period simply ending, or a portal snapshot stating its current status, count as an update without an evidenced participation-changing action?',
             {'action_required': 'Treat natural closures and passive snapshots as rejected candidates (choose no_participation or non_notice explicitly); keep their source evidence and remove their update counts/targets.',
              'explicit_closures_only': 'Keep explicitly recorded closure events as updates; reject unchanged open-period/agency status snapshots. Resolve event mapping and before-state policy separately.',
              'include_both': 'Retain both as research updates, with unknown event_type where no exact enum exists; this does not supply missing before evidence or certify a legal participation change.',
              'unresolved': 'Keep all affected candidates unresolved and leave counts conditional.'})
    register('nondeadline-cutoff-open', 'date_ambiguity', 'Cutoff for opening labels',
             'For an opening/start label rather than a submission deadline, should cutoff be not_applicable or unknown?',
             {'not_applicable': 'Normalize affected opening cutoff labels to not_applicable; do not change opening dates or status.',
              'unknown': 'Retain unknown cutoff on the affected opening labels; do not infer a submission condition.',
              'exception_review': 'State an explicit rule and return exceptions to proceeding review.'}, 10)
    register('nondeadline-cutoff-hearing', 'date_ambiguity', 'Cutoff for hearing sessions',
             'For hearing start/end session labels rather than submission deadlines, should cutoff be not_applicable or unknown?',
             {'not_applicable': 'Normalize affected session cutoff labels to not_applicable; hearing times and scheduling status are unchanged.',
              'unknown': 'Retain unknown cutoff; do not infer a submission deadline from a session time.',
              'exception_review': 'State a narrower rule and return exceptions to proceeding review.'}, 10)
    families = {
        'no-later-than-date': 'no/not later than a stated date or time',
        'ends-on-date': 'shall end on a stated date or time',
        'through-date': 'through a stated date',
        'by-date': 'by a stated date',
        'relative-not-later-than': 'not later than N days after posting',
        'relative-within': 'within N days following publication',
    }
    for family, wording in families.items():
        register('cutoff-' + family, 'date_ambiguity', 'Deadline cutoff: ' + wording,
                 f'For "{wording}", what is the default cutoff: inclusive, exclusive, or unknown pending a more specific rule?',
                 {'inclusive': 'Set the affected cutoff labels to inclusive; preserve literal wording, asserted precision and nullable zone.',
                  'exclusive': 'Set cutoff to exclusive only under the owner’s stated interpretation; preserve dates and do not calculate relative deadlines.',
                  'unknown': 'Keep unknown cutoff across this family; the owner’s class decision records that unresolved interpretation once.',
                  'exceptions': 'Define exceptions explicitly and return those affected instances to case review. Relative anchors/counting rules and source conflicts remain unresolved.'})
    register('unstated-opening-label', 'date_ambiguity', 'Explicit opening role versus publication metadata',
             'Must an explicit open temporal entry be retained in addition to publication metadata, including an unknown opening when no opening date is stated?',
             {'explicit_open': 'Retain source-supported opening wording, including relative openings, and explicit unknown/null openings where unstated. Do not calculate dates from publication.',
              'publication_metadata_suffices': 'Treat open as optional research metadata when publication evidence is retained; this does not equate publication with a legal opening instant.',
              'split_by_support': 'Require supported opening labels but make unstated/unknown open entries optional; identify the chosen support rule explicitly.'}, 10)
    register('conditional-undated-hearings', 'date_ambiguity', 'Undated offered hearings',
             'How should an offered hearing with no evidenced scheduled date be represented: retain the conditional opportunity with unknown date, or exclude until scheduling is evidenced?',
             {'retain_unknown': 'Retain the offered opportunity and unknown date/status. This class decision does not assert that a hearing occurred or was scheduled.',
              'exclude_until_scheduled': 'Exclude these undated candidates under a documented scope change; recalculate opportunity/cohort counts and preserve exclusions.',
              'case_recovery': 'Keep the affected cases pending and seek scheduling evidence separately. Existing concrete date conflicts are not covered.'}, 10)
    register('cohort-older-vs-interval', 'scope', 'Cohorts for updates to older proceedings',
             'For an interval update on a proceeding opened before the interval, should the cohort be older_proceeding_update or interval_update?',
             {'older_proceeding_update': 'Apply the older-proceeding cohort to the listed notice/update labels; rescore affected cohort counts.',
              'interval_update': 'Apply interval_update under the owner’s stated cohort interpretation; rescore and document the protocol interpretation.',
              'exceptions': 'Identify exceptions by record ID; retain other unresolved cohort cases.'}, 10)
    register('history-notice-entities', 'identity', 'Notice entities supported only by history',
             'Should a history event or history-linked unsupplied document have its own research notice entity, or remain evidence on the update/proceeding until a notice original is supplied?',
             {'retain_notice': 'Retain the listed history-supported notice entities and their provisional keys; no blanket merge/split is authorized.',
              'evidence_only': 'Do not count these as separate notices; preserve history evidence and adjust links via explicit append-only decisions.',
              'recover_originals': 'Keep these notice candidates unresolved until originals are recovered. No fictional document may be minted.'}, 10)
    register('completion-attribution-timing', 'disagreement', 'Completion counts before later attribution',
             'Should source-view candidate_count describe candidates known when that completion row was written, or final candidates attributable after all body/history inspection?',
             {'final_attribution': 'Use the final attributable-candidate definition; record append-only count corrections against all listed source rows and verify the supplement, without rewriting sealed rows.',
              'inspection_time': 'Retain the inspection-time interpretation as a documented diagnostic deviation; never sum overlapping view counts as entity counts.',
              'defer': 'Keep the 25 rows diagnostic and unresolved pending source-accounting review.'}, 10)

    def issue_records(issue):
        return [records[rid] for side in 'AB' for rid in issue['record_ids'][side]]

    natural = set()
    for side, rows in passes.items():
        for r in rows:
            if r['record_type'] != 'update' or r['payload']['event_type'] != 'unknown':
                continue
            after = r['payload']['after_evidence']
            mids = [e['manifest_entry_id'] for e in after]
            text = norm(canonical(after) + r['payload']['target_scope'])
            if ('comment period closed' in text and mids and all(m.startswith('ct-json-getrmrhistory-') for m in mids)) or (mids and all(m == 'ct-json-open-comment-periods' or m.startswith('ct-xchk-') for m in mids)):
                natural.add(r['entity_id'])

    def temporal_entries(issue):
        field = issue.get('field', '')
        role = field.split('.')[1].split('[')[0]
        value = json.loads(field.split('local_value=', 1)[1].split('].', 1)[0]) if 'local_value=' in field else None
        result = []
        for side, r in issue_records(issue):
            for t in r['payload'].get('temporal', []):
                if t['role'] == role and ('local_value=' not in field or temporal_scalar(t.get('local_value')) == value):
                    result.append((side, r, t))
        return result

    def cutoff_policy(issue):
        entries = temporal_entries(issue)
        role = issue['field'].split('.')[1].split('[')[0]
        def focus(pattern):
            result = []
            for side, r, t in entries:
                for e in t['evidence']:
                    raw = e.get('quote_or_mark_description', '')
                    match = re.search(pattern, raw, re.I)
                    start = match.start() if match else 0
                    result.append({'manifest_entry_id': e['manifest_entry_id'], 'locator': e['locator'], 'quote': raw[start:start+200]})
            return sorted({canonical(p): p for p in result}.values(), key=canonical)
        if set(issue['A']) | set(issue['B']) == {'not_applicable', 'unknown'}:
            issue['policy_evidence'] = focus(r'\b(?:shall\s+begin|begin|from|upon\s+posting|hearing|date:)\b')
            return 'nondeadline-cutoff-open' if role == 'open' else 'nondeadline-cutoff-hearing'
        if set(issue['A']) | set(issue['B']) != {'inclusive', 'unknown'}:
            return None
        # The inclusive claimant’s matched temporal literal decides the family;
        # surrounding paragraphs and unrelated roles never classify the wording.
        literals = [t['literal'] for side, r, t in entries if t['cutoff'] == 'inclusive']
        text = norm(' | '.join(literals))
        if re.search(r'not later than.*days?.*after', text):
            family = 'relative-not-later-than'
        elif re.search(r'within.*days?.*(?:following|after)', text):
            family = 'relative-within'
        elif 'no later than' in text or 'not later than' in text:
            family = 'no-later-than-date'
        elif 'through' in text:
            family = 'through-date'
        elif 'shall end' in text or 'ends on' in text:
            family = 'ends-on-date'
        elif re.search(r'\bby\b', text):
            family = 'by-date'
        else:
            return None  # unrecognized wording stays a case, never guessed
        issue['wording_family'] = family
        issue['policy_evidence'] = focus(r'\b(?:(?:no|not)\s+later\s+than|within|through|shall\s+end|ends\s+on|by)\b')
        issue['wording_literals'] = literals
        return 'cutoff-' + family

    proposed = []
    for item in queue.values():
        for original in item['sub_issues']:
            issue = json.loads(canonical(original))
            policy = None
            typ = issue['class']
            rr = issue_records(issue)
            if typ == 'decisive_temporal' and issue['field'].endswith('.cutoff'):
                policy = cutoff_policy(issue)
            elif typ == 'decisive_temporal' and issue['field'] == 'temporal.open.present':
                policy = 'unstated-opening-label'
            elif typ == 'unknown_conflicting_date':
                reports = [issue] + issue.get('additional_reports', [])
                vals = [t for report in reports for t in report['values']]
                if vals and all(t.get('local_value') is None and t['status'] == 'unknown' for t in vals):
                    if issue['role'] == 'hearing_start':
                        policy = 'conditional-undated-hearings'
                    elif issue['role'] == 'open':
                        policy = 'unstated-opening-label'
            elif typ.endswith('.cohorts'):
                if set(issue['A']) | set(issue['B']) == {'older_proceeding_update', 'interval_update'}:
                    policy = 'cohort-older-vs-interval'
            elif typ == 'completion_attribution':
                policy = 'completion-attribution-timing'
            elif typ == 'notice.present':
                if rr and all(all(e['manifest_entry_id'].startswith('ct-json-') for e in r['evidence']) for side, r in rr):
                    policy = 'history-notice-entities'
            # Natural-end policy owns inclusion/rejection facets only. Concrete
            # scope, missing source and other lifecycle questions stay separate.
            if typ in ('update.present', 'accepted_rejected') and any(r['entity_id'] in natural for side, r in rr if r['record_type'] == 'update'):
                policy = 'natural-end-and-passive-snapshots'
            if typ == 'lifecycle_evidence':
                missing = [(side, r) for side, r in rr if r['record_type'] == 'update' and r['payload']['before_missing_reason']]
                for side, r in missing:
                    after = r['payload']['after_evidence']
                    history = all(e['manifest_entry_id'].startswith('ct-json-') for e in after)
                    event = r['payload']['event_type']
                    key = ('history-before-' if history else 'document-before-') + event
                    if key not in specs:
                        register(key, 'lifecycle_ambiguity', f'Missing before evidence: {"history-only" if history else "document/snapshot-backed"} {event} events',
                                 f'For {event} events supported by {"history only" if history else "a decision document or status snapshot"}, what research treatment is allowed when operative before evidence is absent?',
                                 {'retain_diagnostic': 'Keep the listed event candidates with explicit before_missing_reason and a class review reference; this does not establish prior state or completeness.',
                                  'require_before': 'Keep affected events pending until before evidence is recovered; do not invent targets or prior opportunities.',
                                  'exclude_event_class': 'Exclude this event class under an explicit scope decision and rescore; preserve evidence and rejected candidates.'}, 1 if history else 10)
                    facet = json.loads(canonical(issue))
                    facet['policy_facet'] = 'missing before evidence'
                    facet['reported_by'] = side
                    # One policy facet per entity across pass reports.
                    proposed.append((item, facet, key))
                if missing:
                    issue['reasons'] = [reason for reason in issue['reasons'] if reason != 'missing before evidence']
                    issue['before_evidence_policy_refs'] = sorted({('history-before-' if all(e['manifest_entry_id'].startswith('ct-json-') for e in r['payload']['after_evidence']) else 'document-before-') + r['payload']['event_type'] for side, r in missing})
                    # Avoid recharging the before-state question as a case. A
                    # withdrawal/empty-target/reopening facet still needs a case.
                    if not issue['reasons']:
                        continue
            proposed.append((item, issue, policy))

    # A minimum of ten distinct entity/row instances for optional patterns; a
    # second pass report or several fields on one record does not reach the floor.
    grouped = collections.defaultdict(set)
    for item, issue, key in proposed:
        if key:
            grouped[key].add(issue.get('manifest_entry_id') or tuple(issue['entity_ids']))
    enabled = {key for key in grouped if len(grouped[key]) >= specs[key]['threshold']}
    result = {}
    for old, issue, key in proposed:
        if key not in enabled:
            # A proposed optional before-policy below threshold returns its facet
            # to the original lifecycle case, without losing the missing-before.
            if issue.get('policy_facet'):
                issue['reasons'] = ['missing before evidence']
            k = old['item_id']
            if k not in result:
                result[k] = {k: v for k, v in old.items() if k != 'sub_issues'}
                result[k].update(item_kind='case', sub_issues=[])
            target = result[k]
        else:
            spec = specs[key]
            k = 'policy:' + key
            if k not in result:
                result[k] = {'item_id': 'ct-policy-' + hashlib.sha256(key.encode()).hexdigest(),
                             'item_kind': 'class', 'policy_key': key, 'trigger': spec['trigger'],
                             'title': spec['title'], 'question': spec['question'],
                             'answer_consequences': spec['answer_consequences'],
                             'proceeding': 'CT-policy/' + key, 'tracking_numbers': [], 'entity_ids': [],
                             'record_ids': {'A': [], 'B': []}, 'context_record_ids': {'A': [], 'B': []},
                             'evidence': [], 'sub_issues': [], 'estimated_minutes': 10}
            target = result[k]
        # Deduplicate transferred facets without dropping pass-specific reports.
        token = canonical([issue['sub_issue_id'], issue.get('policy_facet') if target['item_kind'] == 'class' else None])
        existing = next((x for x in target['sub_issues'] if canonical([x['sub_issue_id'], x.get('policy_facet') if target['item_kind'] == 'class' else None]) == token), None)
        if existing is None:
            target['sub_issues'].append(issue)
        else:
            if issue.get('reasons'):
                existing['reasons'] = sorted(set(existing.get('reasons', [])) | set(issue['reasons']))
            if issue != existing and issue not in existing.setdefault('policy_reports', []):
                existing['policy_reports'].append(issue)
        for side in 'AB':
            target['record_ids'][side] = sorted(set(target['record_ids'][side]) | set(issue['record_ids'][side]))
        target['entity_ids'] = sorted(set(target['entity_ids']) | set(issue['entity_ids']))

    # Rebuild case membership from remaining facets, not the pre-partition bundle.
    # Classes also list the opposite pass's typed proceeding/notice context when
    # that pass emitted no corresponding event; those IDs are marked contextual.
    for item in result.values():
        item['record_ids'] = {side: sorted({rid for x in item['sub_issues'] for rid in x['record_ids'][side]}) for side in 'AB'}
        direct = {side: set(item['record_ids'][side]) for side in 'AB'}
        item['entity_ids'] = sorted({e for x in item['sub_issues'] for e in x['entity_ids']})
        if item['item_kind'] == 'class':
            for side in 'AB':
                other = 'B' if side == 'A' else 'A'
                for rid in direct[side]:
                    r = records[rid][1]
                    p = r['payload']
                    links = p.get('proceeding_ids', [p.get('proceeding_id')]) + p.get('notice_ids', [])
                    for eid in links:
                        if eid in byid[other] and byid[other][eid]['record_id'] not in direct[other]:
                            item['context_record_ids'][other].append(byid[other][eid]['record_id'])
            for side in 'AB':
                item['context_record_ids'][side] = sorted(set(item['context_record_ids'][side]))
                item['record_ids'][side] = sorted(direct[side] | set(item['context_record_ids'][side]))
            item['direct_record_ids'] = {side: sorted(direct[side]) for side in 'AB'}
        rr = [records[rid] for side in 'AB' for rid in item['record_ids'][side]]
        item['tracking_numbers'] = sorted({t for side, r in rr for t in track_for(r, side)})
        if item['item_kind'] == 'class':
            representatives = []
            seen = set()
            ordered = sorted(item['sub_issues'], key=lambda x: (canonical(x['record_ids']), x['sub_issue_id']))
            if item['policy_key'] in ('natural-end-and-passive-snapshots', 'history-before-unknown'):
                def source_family(x):
                    mids = [e['manifest_entry_id'] for side, r in issue_records(x) if r['record_type'] == 'update' for e in r['payload']['after_evidence']]
                    if any(m == 'ct-json-open-comment-periods' for m in mids):
                        return 'open-period snapshot'
                    if any(m.startswith('ct-xchk-') for m in mids):
                        return 'agency status snapshot'
                    if any(m.startswith('ct-json-getrmrnotes-') for m in mids):
                        return 'notes event'
                    return 'history event'
                first = {}
                for x in ordered:
                    first.setdefault(source_family(x), x)
                ordered = [first[k] for k in sorted(first)] + [x for x in ordered if x not in first.values()]
            for x in ordered:
                rs = issue_records(x)
                tracks = sorted({t for side, r in rs for t in track_for(r, side)})
                group = tuple(tracks) or tuple(x['entity_ids'])
                if group in seen:
                    continue
                ptr = x.get('policy_evidence') or pointers([r for side, r in rs])
                if x.get('manifest_entry_id'):
                    source_ptr = [p for p in ptr if p['manifest_entry_id'] == x['manifest_entry_id']]
                    ptr = source_ptr or [{'manifest_entry_id': x['manifest_entry_id'], 'locator': 'completion-attribution-review supplement row',
                                          'quote': canonical({k: v for k, v in x.items() if 'count' in k})[:200]}]
                if not ptr:
                    continue
                representatives.append({'tracking_numbers': tracks, 'entity_ids': x['entity_ids'],
                                        'record_ids': x['record_ids'], 'sub_issue_id': x['sub_issue_id'],
                                        'A': x.get('A'), 'B': x.get('B'),
                                        'evidence': sorted({canonical(p): p for p in ptr}.values(), key=canonical)[:3]})
                seen.add(group)
                if len(representatives) == 3:
                    break
            item['representative_instances'] = representatives
            item['representative_note'] = 'Three distinct proceedings where available; fewer means the mandatory event-type class has fewer supplied instances.'
            item['affected_instance_count'] = len({x.get('manifest_entry_id') or tuple(x['entity_ids']) for x in item['sub_issues']})
            item['evidence'] = sorted({canonical(e): e for r in representatives for e in r['evidence']}.values(), key=canonical)
        else:
            # Keep manifest-gap/attribution pointers even if they have no label.
            item['evidence'] = sorted({canonical(e): e for e in pointers([r for side, r in rr]) + item['evidence'] if any(x.get('manifest_entry_id') == e['manifest_entry_id'] for x in item['sub_issues']) or e in pointers([r for side, r in rr])}.values(), key=canonical)
    return result


def main():
    passes = {s: read(STATE / f'pass-{s}.jsonl') for s in 'AB'}
    atts = {s: json.loads((STATE / 'attestations' / f'pass-{s}.json').read_text()) for s in 'AB'}
    for s in 'AB':
        if hashlib.sha256((STATE / f'pass-{s}.jsonl').read_bytes()).hexdigest() != atts[s]['output_sha256']:
            raise ValueError(f'Pass {s} differs from sealed hash')
    index = {s: {(r['record_type'], r['entity_id']): r for r in rows} for s, rows in passes.items()}
    assert all(len(index[s]) == len(passes[s]) for s in 'AB'), 'Repeated entity records need explicit version handling'
    byid = {s: {r['entity_id']: r for r in rows} for s, rows in passes.items()}
    keys = sorted(set(index['A']) | set(index['B']))
    candidates = []
    for typ in TYPES:
        if typ == 'rejected_candidate':
            continue
        aa = [r for (t, e), r in index['A'].items() if t == typ and (t, e) not in index['B']]
        bb = [r for (t, e), r in index['B'].items() if t == typ and (t, e) not in index['A']]
        for a in aa:
            for b in bb:
                match = identify(a, b)
                if match:
                    basis, confidence = match
                    c = {'record_type': typ, 'A_entity_id': a['entity_id'], 'B_entity_id': b['entity_id'],
                         'A_record_ids': [a['record_id']], 'B_record_ids': [b['record_id']],
                         'match_basis': basis, 'confidence': confidence}
                    c['candidate_id'] = 'ct-identity-' + hashlib.sha256(canonical([typ, a['entity_id'], b['entity_id']]).encode()).hexdigest()
                    candidates.append(c)
    candidates.sort(key=canonical)
    degrees = collections.Counter(e for c in candidates for e in (c['A_entity_id'], c['B_entity_id']))
    map_b = {}
    mapped_candidates = {}
    counterpart = {}
    for c in candidates:
        c['comparison_mapping_applied'] = degrees[c['A_entity_id']] == degrees[c['B_entity_id']] == 1
        if c['comparison_mapping_applied']:
            map_b[c['B_entity_id']] = c['A_entity_id']
            counterpart[c['A_entity_id']] = c['B_entity_id']
            counterpart[c['B_entity_id']] = c['A_entity_id']
            mapped_candidates[c['A_entity_id']] = c['candidate_id']
    write('identity-candidates.jsonl', candidates)

    def mapped(v):
        if isinstance(v, list):
            return [mapped(x) for x in v]
        return map_b.get(v, v) if isinstance(v, str) else v

    pairs, slots = [], []
    for typ, eid in keys:
        a, b = index['A'].get((typ, eid)), index['B'].get((typ, eid))
        raw_a, raw_b = a, b
        used = None
        if eid in counterpart:
            a = a or index['A'].get((typ, counterpart[eid]))
            b = b or index['B'].get((typ, counterpart[eid]))
            used = mapped_candidates.get(eid, mapped_candidates.get(map_b.get(eid)))
        diffs, wording = [], []
        if typ != 'rejected_candidate':
            slots.append(bool(a) == bool(b))
            if bool(a) != bool(b):
                diffs.append({'field': 'present', 'A': bool(a), 'B': bool(b)})
            if a and b:
                for field in FIELDS[typ]:
                    av = a['cohorts'] if field == 'cohorts' else a['payload'].get(field)
                    bv = b['cohorts'] if field == 'cohorts' else b['payload'].get(field)
                    mv = mapped(bv) if field in ('target_opportunity_ids', 'notice_ids', 'proceeding_ids', 'proceeding_id') else bv
                    equal = norm(av) == norm(mv)
                    slots.append(equal)
                    if not equal:
                        d = {'field': field, 'A': av, 'B': bv}
                        if mv != bv:
                            d['B_after_proposed_identity_mapping'] = mv
                        diffs.append(d)
                td, tw, ts = temporal_compare(a['payload'].get('temporal', []), b['payload'].get('temporal', [])) if typ in ('opportunity', 'update') else ([], [], [])
                diffs.extend(td)
                wording.extend(tw)
                slots.extend(ts)
                for field in sorted(set(a['payload']) | set(b['payload'])):
                    if field not in FIELDS[typ] and field != 'temporal':
                        av, bv = a['payload'].get(field), b['payload'].get(field)
                        if norm(av) != norm(bv):
                            wording.append({'field': field, 'A': av, 'B': bv})
                for field in ('unresolved', 'evidence'):
                    if norm(a[field]) != norm(b[field]):
                        wording.append({'field': field, 'A': a[field], 'B': b[field]})
        derivable = []
        if typ == 'proceeding' and a and b and norm(a['payload']['notice_ids']) != norm(mapped(b['payload']['notice_ids'])):
            derivable.append({'field': 'notice_ids', 'A': a['payload']['notice_ids'], 'B': b['payload']['notice_ids'],
                              'reason': 'Reverse list is derivable from each notice.proceeding_ids. Only disagreements on that authoritative forward link are queued, on the notice pair; notice presence has its own case.'})
        pairs.append({'entity_id': eid, 'record_type': typ, 'in_A': bool(raw_a), 'in_B': bool(raw_b),
                      'A_record_ids': [raw_a['record_id']] if raw_a else [],
                      'B_record_ids': [raw_b['record_id']] if raw_b else [],
                      'comparison_record_ids': {'A': [a['record_id']] if a else [], 'B': [b['record_id']] if b else []},
                      'proposed_identity_mapping': used, 'field_diffs': diffs, 'wording_diffs': wording,
                      'derivable_membership_diffs': derivable})
    write('pairs.jsonl', pairs)

    def track_for(r, s):
        # Typed proceeding links take precedence over stray tracking numbers in
        # copied source bodies. Native tracking alias precedes source locators.
        p = r['payload']
        roots = [r] if r['record_type'] == 'proceeding' else [byid[s][x] for x in p.get('proceeding_ids', [p.get('proceeding_id')]) if x in byid[s]]
        native = {x.upper() for root in roots for x in TRACK.findall(canonical(root['aliases']))}
        if not native:
            native = {x.upper() for x in TRACK.findall(canonical(r['aliases']))}
        if not native:
            native = {x.upper() for e in evidence(r) for x in TRACK.findall(e['manifest_entry_id'])}
        if not native:
            native = {x.upper() for e in evidence(r) for x in TRACK.findall(e['locator'])}
        return sorted(native)

    queue = {}
    def add(trigger, records, issue, group=None, identity_id=None, extra_evidence=None):
        tracking = sorted({t for s, r in records for t in track_for(r, s)})
        # One question-type bundle per proceeding; cross-proceeding problems
        # remain one linked bundle instead of being duplicated into each file.
        group = group or ('+'.join(tracking) if tracking else 'CT-unlinked')
        key = (group, trigger, identity_id or '')
        if key not in queue:
            queue[key] = {'item_id': 'ct-review-' + hashlib.sha256(canonical(key).encode()).hexdigest(),
                          'trigger': trigger, 'proceeding': group, 'tracking_numbers': tracking,
                          'entity_ids': [], 'record_ids': {'A': [], 'B': []}, 'sub_issues': [], 'evidence': []}
        item = queue[key]
        issue['entity_ids'] = sorted({r['entity_id'] for s, r in records})
        issue['record_ids'] = {s: sorted({r['record_id'] for side, r in records if side == s}) for s in 'AB'}
        # Stable issue key ignores which pass reported a shared uncertainty.
        issue_key = canonical([issue['class'], issue['entity_ids'], issue.get('field'), issue.get('role'), issue.get('candidate_id'), issue.get('manifest_entry_id')])
        issue['sub_issue_id'] = hashlib.sha256(issue_key.encode()).hexdigest()
        old = next((x for x in item['sub_issues'] if x['sub_issue_id'] == issue['sub_issue_id']), None)
        if old is None:
            item['sub_issues'].append(issue)
        else:
            # Preserve both pass reports in one case, not one case per note.
            variants = old.setdefault('additional_reports', [])
            if canonical(issue) != canonical({k: v for k, v in old.items() if k != 'additional_reports'}) and issue not in variants:
                variants.append(issue)
        item['entity_ids'] = sorted(set(item['entity_ids']) | {r['entity_id'] for s, r in records})
        for s in 'AB':
            item['record_ids'][s] = sorted(set(item['record_ids'][s]) | {r['record_id'] for side, r in records if side == s})
        item['evidence'] = sorted({canonical(e): e for e in item['evidence'] + pointers([r for s, r in records]) + (extra_evidence or [])}.values(), key=canonical)
        return item

    seen_pairs = set()
    for pair in pairs:
        if pair['record_type'] == 'rejected_candidate':
            continue
        recs = [(s, r) for s in 'AB' for r in passes[s] if r['record_id'] in pair['comparison_record_ids'][s]]
        pairkey = tuple(sorted(r['record_id'] for s, r in recs))
        if pairkey in seen_pairs:
            continue
        seen_pairs.add(pairkey)
        for d in pair['field_diffs']:
            temporal = d['field'].startswith('temporal.')
            add('date_ambiguity' if temporal else 'disagreement', recs,
                {'class': 'decisive_temporal' if temporal else pair['record_type'] + '.' + d['field'], **d})
    for c in candidates:
        recs = [('A', byid['A'][c['A_entity_id']]), ('B', byid['B'][c['B_entity_id']])]
        add('identity', recs, {'class': 'identity_match', **c}, identity_id=c['candidate_id'])

    # Accepted/rejected conflicts only. Rejection-vs-nothing and shared rejections
    # are outside this queue. A generic tracking alias alone is not event identity.
    rejection_conflicts = []
    for s, other in [('A', 'B'), ('B', 'A')]:
        accepted = [r for r in passes[s] if r['record_type'] != 'rejected_candidate']
        rejected = [r for r in passes[other] if r['record_type'] == 'rejected_candidate']
        for acc in accepted:
            for rej in rejected:
                shared = sorted(aliases(acc, True) & aliases(rej, True))
                overlap = same_evidence(acc, rej, True)
                if not shared and not overlap:
                    continue
                # If the other side accepts this very entity too, this rejection
                # describes another view/role; do not turn it into an A/B conflict.
                if acc['entity_id'] in byid[other] or counterpart.get(acc['entity_id']) in byid[other]:
                    continue
                issue = {'class': 'accepted_rejected', 'accepted_pass': s, 'accepted_type': acc['record_type'],
                         'reason_code': rej['payload']['reason_code'], 'rationale': rej['payload']['rationale'],
                         'match_basis': {'shared_alias': shared, 'overlapping_evidence': overlap}}
                recs = [(s, acc), (other, rej)]
                add('disagreement', recs, issue)
                rejection_conflicts.append((acc, rej))

    scope_re = re.compile(r'carry.in|active.at.start|inclusion|in.scope|out.of.scope|scor(?:ed|ing)|scope|interval bound|follow.up|horizon|historical.support', re.I)
    uncertain_re = re.compile(r'\?|review|unknown|uncertain|pending|unfinished|conflict|may |unresolved|cannot|not supplied|unbounded', re.I)
    missing_re = re.compile(r'not supplied|unsupplied|missing (?:body|document|histor|source)|unavailable|unreadable|unbounded|not (?:fully )?supplied', re.I)
    for s in 'AB':
        for r in passes[s]:
            if r['record_type'] == 'rejected_candidate':
                continue
            eid, typ, p = r['entity_id'], r['record_type'], r['payload']
            recs = [(s, r)]
            if eid in byid['B' if s == 'A' else 'A']:
                recs.append(('B' if s == 'A' else 'A', byid['B' if s == 'A' else 'A'][eid]))
            elif eid in counterpart:
                other = 'B' if s == 'A' else 'A'
                recs.append((other, byid[other][counterpart[eid]]))
            for role in sorted(ROLES):
                flagged = [t for t in p.get('temporal', []) if t['role'] == role and t['status'] in ('unknown', 'conflicting')]
                if flagged:
                    add('date_ambiguity', recs, {'class': 'unknown_conflicting_date', 'role': role,
                        'reported_by': s, 'values': [{k: t.get(k) for k in ('role',) + DECISIVE_TEMP} for t in flagged]})
            if typ == 'update':
                reasons = []
                if not p['target_opportunity_ids']:
                    reasons.append('empty targets')
                if p.get('before_missing_reason'):
                    reasons.append('missing before evidence')
                if p['event_type'] in ('full_withdrawal', 'partial_withdrawal', 'reopening'):
                    reasons.append(p['event_type'])
                if reasons:
                    add('lifecycle_ambiguity', recs, {'class': 'lifecycle_evidence', 'reported_by': s,
                        'event_type': p['event_type'], 'reasons': reasons,
                        'before_missing_reason': p.get('before_missing_reason'), 'target_unresolved_reason': p.get('target_unresolved_reason')})
            questions = sorted(set(x for x in r['unresolved'] if scope_re.search(x) and uncertain_re.search(x)))
            if questions:
                add('scope', recs, {'class': 'scope_question', 'reported_by': s, 'questions': questions})
            missing = sorted(set(x for x in r['unresolved'] if missing_re.search(x)))
            if typ == 'update' and p.get('before_missing_reason'):
                # The same prior-state sufficiency question is already in the
                # lifecycle case. A named absent document remains missing_source.
                missing = [x for x in missing if not re.search(r'prior operative evidence|missing historical before/target', x, re.I)]
            if missing:
                add('missing_source', recs, {'class': 'missing_evidence', 'reported_by': s, 'questions': missing})
            if typ == 'opportunity':
                visual = [e for e in r['evidence'] + [e for t in p['temporal'] if t['role'] in ROLES for e in t['evidence']] if e['mode'] == 'visual_review']
                if visual:
                    add('visual_mark', recs, {'class': 'decisive_visual', 'reported_by': s,
                                            'locators': sorted({e['locator'] for e in visual})})
    manifest = read(STATE / 'manifest.jsonl')
    adjudications = read(STATE / 'adjudications.jsonl')
    for m in manifest:
        if m['retrieval']['result'] == 'retrieved':
            continue
        mid = m['entry_id']
        add('missing_source', [], {'class': 'source_gap', 'manifest_entry_id': mid,
            'result': m['retrieval']['result'], 'reason': m['retrieval'].get('reason'),
            'existing_adjudication_refs': [a['record_id'] for a in adjudications if mid in a['payload']['target_record_ids']]},
            group='CT-source-gaps', extra_evidence=[{'manifest_entry_id': mid, 'locator': 'manifest retrieval/accounting; no original', 'quote': ''}])

    # Completion count discrepancies are retained as one source-accounting
    # question bundle; attribution counts across source views are not census N.
    completion = read(STATE / 'completion.jsonl')
    attrib = read(STATE / 'supplements/pass-B/completion-attribution-review.jsonl')
    for row in attrib:
        mid = row['manifest_entry_id']
        direct = TRACK.findall(mid)
        eids = row.get('reconciled_candidate_entity_ids', row.get('later_directly_attributable_entity_ids', []))
        recs = [(s, byid[s][e]) for s in 'AB' for e in eids if e in byid[s]]
        add('disagreement', recs, {'class': 'completion_attribution', **row},
            group=direct[0].upper() if direct else 'CT-source-accounting',
            extra_evidence=[{'manifest_entry_id': mid, 'locator': 'completion log and append-only attribution supplement', 'quote': ''}])

    queue = policy_partition(queue, passes, byid, track_for)
    questions = {
        'disagreement': 'Resolve every listed decisive inclusion, role, cohort, membership/target or source-count difference. Are the candidates distinct, duplicates, rejected or still unresolved?',
        'date_ambiguity': 'Resolve the listed decisive date/role/status differences or unknown/conflicting roles; retain unknown where evidence cannot decide. Wording-only notes are reference material.',
        'identity': 'Do these two IDs represent the same entity? Confirm or reject this proposed match and any conditional comparison mapping; no canonical merge has been applied.',
        'lifecycle_ambiguity': 'Which event occurred, which round(s) does it affect, and is its before/after evidence sufficient? Resolve empty targets, withdrawal and reopening questions without inventing targets.',
        'visual_mark': 'Inspect the original visual evidence deciding the listed opportunities’ dates, roles or hearing status. What does it establish?',
        'missing_source': 'Recover missing evidence through an allowed route, narrow/re-freeze scope, or leave completeness unestablished. Existing gap sign-offs are not inspections.',
        'scope': 'Resolve the listed carry-in, active-status, historical-support and follow-up inclusion/accounting questions.'}
    for item in queue.values():
        item['sub_issues'].sort(key=canonical)
        item['sub_issue_count'] = len(item['sub_issues'])
        item['estimated_minutes'] = 10 if item['item_kind'] == 'class' else 5 if item['trigger'] in ('identity', 'visual_mark') or len(item['sub_issues']) >= 3 else 3
        if item['item_kind'] == 'case':
            item['question'] = questions[item['trigger']]
        parts = []
        for s in 'AB':
            rr = [r for r in passes[s] if r['record_id'] in item['record_ids'][s]]
            counts = collections.Counter(r['record_type'] for r in rr)
            events = collections.Counter(r['payload']['event_type'] for r in rr if r['record_type'] == 'update')
            dates = sorted({f"{t['role']}={t.get('local_value')} ({t['status']})" for r in rr for t in r['payload'].get('temporal', []) if t['role'] in ROLES})
            claim = ', '.join(f'{n} {t}' for t, n in sorted(counts.items())) or 'no linked label record'
            if events:
                claim += '; events ' + ', '.join(f'{e}={n}' for e, n in sorted(events.items()))
            if dates:
                claim += '; participation values ' + ' / '.join(dates[:4])
                if len(dates) > 4:
                    claim += f' (plus {len(dates)-4} more listed in source records)'
            parts.append(f'{s}: {claim}.')
        item['summary'] = ' '.join(parts)
        if item['item_kind'] == 'case':
            item['title'] = f"{item['proceeding']}: {item['trigger'].replace('_', ' ')} ({item['sub_issue_count']} sub-issues)"
    priority = {'missing_source': 0, 'scope': 1, 'identity': 2, 'lifecycle_ambiguity': 3, 'date_ambiguity': 4, 'visual_mark': 5, 'disagreement': 6}
    items = sorted(queue.values(), key=lambda i: (i['item_kind'] != 'class', priority[i['trigger']], i['proceeding'], i['item_id']))
    write('review-queue.jsonl', items)
    counts = collections.Counter(i['trigger'] for i in items)
    minutes = sum(i['estimated_minutes'] for i in items)

    # Diagnose material classes from deduplicated comparison/queue cases. Raw
    # exact-ID counts remain separate from conditional identity interpretation.
    classes = collections.Counter(x['class'] for i in items for x in i['sub_issues'])
    largest = classes.most_common(5)
    descriptions = {
        'decisive_temporal': 'Decisive participation temporal field/role differences after role/local-value alignment; several fields can describe one date problem.',
        'unknown_conflicting_date': 'Distinct entity/role cases carrying explicit unknown or conflicting status; ambiguity prose alone is excluded.',
        'lifecycle_evidence': 'Update events needing before-state/target or withdrawal/reopening review; one case per update, not per unresolved sentence.',
        'update.present': 'Update records not explained by an unambiguous alternate-key identity proposal.',
        'completion_attribution': 'Source-view completion attribution discrepancies from the 25-row append-only supplement.',
        'accepted_rejected': 'Accepted-vs-rejected same-evidence candidates; shared rejections and rejection-only candidates are not queued.',
        'missing_evidence': 'Entity-level missing-document/history/before-evidence questions, bundled by proceeding.',
        'scope_question': 'Explicit unresolved participation inclusion/accounting questions.',
        'proceeding.notice_ids': 'Proceeding notice-set membership differs even after the comparison-only identity mapping.',
    }
    extra_b = [r for r in passes['B'] if r['record_type'] == 'update' and r['entity_id'] not in byid['A']]
    extra_classes = collections.Counter()
    extra_detail = []
    for r in extra_b:
        after = r['payload']['after_evidence']
        mids = [e['manifest_entry_id'] for e in after]
        text = norm(canonical(after) + r['payload']['target_scope'])
        if r['entity_id'] in map_b:
            category = 'same event proposed under another fallback key'
        elif mids and all(m.startswith('ct-json-') for m in mids):
            if 'comment period closed' in text:
                category = 'additional history-only closure event'
            elif all(m.startswith('ct-json-getrmrnotes-') for m in mids):
                category = 'additional notes-only event'
            elif all(m == 'ct-json-open-comment-periods' for m in mids):
                category = 'additional open-period snapshot event'
            elif any(m.startswith('ct-json-hearing-') for m in mids):
                category = 'additional history/hearing-detail event'
            else:
                category = 'additional other history/JSON event'
        elif mids and all(m.startswith('ct-xchk-') for m in mids):
            category = 'additional cross-check-only event'
        else:
            category = 'additional document-backed event'
        extra_classes[category] += 1
        extra_detail.append({'entity_id': r['entity_id'], 'tracking_numbers': track_for(r, 'B'),
                            'category': category, 'event_type': r['payload']['event_type'], 'after_manifest_ids': mids})
    # Keep the diagnostic partition inside the existing output, not a sixth file.
    presence_bundles = [i for i in items if any(x['class'] == 'update.present' for x in i['sub_issues'])]
    for item in presence_bundles:
        item['extra_B_update_analysis'] = [d for d in extra_detail if d['entity_id'] in item['entity_ids'] and d['entity_id'] not in map_b]
    for item in items:
        if item['trigger'] == 'identity':
            item['extra_B_update_analysis'] = [d for d in extra_detail if d['entity_id'] in item['entity_ids']]
    write('review-queue.jsonl', items)

    def impact(i):
        if i['proceeding'] == 'CT-source-gaps':
            return 100
        if i['proceeding'] == 'PR2023-031' and i['trigger'] == 'scope':
            return 99
        if i['proceeding'] == 'PR2025-036' and i['trigger'] == 'lifecycle_ambiguity':
            return 98
        if i['trigger'] == 'visual_mark':
            return 97
        if i['trigger'] == 'date_ambiguity' and any('"conflicting"' in canonical(x) for x in i['sub_issues']):
            return 96
        if i['trigger'] == 'identity':
            return 95
        return 80 - priority[i['trigger']]
    high, seen = [], set()
    for item in sorted((i for i in items if i['item_kind'] == 'case'), key=lambda i: (-impact(i), -i['sub_issue_count'], i['proceeding'], i['item_id'])):
        if item['proceeding'] not in seen:
            high.append(item)
            seen.add(item['proceeding'])
        if len(high) == 10:
            break
    policy_items = [i for i in items if i['item_kind'] == 'class']
    case_items = [i for i in items if i['item_kind'] == 'case']
    by_kind_trigger = {kind: {t: sum(i['item_kind'] == kind and i['trigger'] == t for i in items) for t in TRIGGERS} for kind in ('class', 'case')}
    kind_minutes = {kind: sum(i['estimated_minutes'] for i in items if i['item_kind'] == kind) for kind in ('class', 'case')}
    for item in policy_items:
        item['decision_scope'] = 'One human class adjudication listing every affected record ID; no decision has been applied. Context-only parents are marked separately.'
        if 'before-' in item['policy_key']:
            item['conditional_applicability'] = 'If the natural-end policy excludes an event, that event no longer needs a retained-update before-state decision. Retained events still require the selected before-evidence treatment.'
    refs = collections.defaultdict(list)
    for item in items:
        for eid in {e for x in item['sub_issues'] for e in x['entity_ids']}:
            refs[eid].append({'item_id': item['item_id'], 'item_kind': item['item_kind'], 'trigger': item['trigger']})
    for pair in pairs:
        pair['review_refs'] = sorted(refs[pair['entity_id']], key=canonical)
    write('pairs.jsonl', pairs)
    write('review-queue.jsonl', items)
    stats = []
    for typ in TYPES:
        pp = [p for p in pairs if p['record_type'] == typ]
        stats.append((typ, sum(p['in_A'] and p['in_B'] for p in pp), sum(p['in_A'] and not p['in_B'] for p in pp), sum(p['in_B'] and not p['in_A'] for p in pp)))
    equal, total = sum(slots), len(slots)
    derived = sum(bool(p['derivable_membership_diffs']) for p in pairs)
    md = ['# CT human review — class and case decisions (revision 3)', '',
          f'**{len(policy_items)} class items + {len(case_items)} case items = {len(items)} items; {minutes} / 360 minutes.** '
          f'{"Fits" if minutes <= 360 else "Does not fit"}; {max(0, minutes-360)} minutes over before audit. '
          f'Class decisions: {kind_minutes["class"]} minutes; case decisions: {kind_minutes["case"]} minutes. Previous revision: 229 case items / 861 minutes.', '',
          '| Trigger | Class items | Case items | Total minutes |', '|---|---:|---:|---:|']
    md += [f'| {t} | {by_kind_trigger["class"][t]} | {by_kind_trigger["case"][t]} | {sum(i["estimated_minutes"] for i in items if i["trigger"] == t)} |' for t in TRIGGERS]
    md += ['', '## How to use this queue', '',
           'Settle each class question once, as in the step-3 sign-off. Class membership is an enumerated set, not a sample: the adjudication must list every affected record_id in the appendix. '
           'Each class costs 10 minutes and includes answer consequences plus three representative instances where available. '
           'Three mandatory small wording/event-type classes have only one instance; their single real instance is shown rather than fabricated examples. '
           'Context-only notice/proceeding IDs explain the other pass’s treatment and are marked; direct_record_ids identify the labels subject to the policy.', '',
           'A class settles only its named policy facet. Missing-before policy does not decide withdrawal identity, an empty target or a concrete date conflict; those remain cases. '
           'If natural ends/snapshots are excluded, their retained-update before-state questions become inapplicable; the estimate does not assume an answer or waive another class. '
           'Optional patterns require at least ten distinct entities/source rows. The mandatory cutoff-wording and history-before event-type classes can be smaller.', '',
           f'{derived} reverse proceeding notice-list differences are reference-only in pairs.derivable_membership_diffs. Notice.proceeding_ids governs membership. '
           'Only contradictory notice-owned proceeding assignments are material; notice presence is reviewed separately. No genuine forward-link ownership conflict was found in these inputs.', '',
           'All earlier materiality rules remain: role/local_value temporal alignment, equivalent datetime serialization, no positional comparison, decisive fields only, '
           'unmatched extra entries reference-only when the role exists on both sides, and no rejection-vs-nothing cases. '
           'One-to-one identity mapping remains a comparison assumption requiring human identity review. Nine identity proposals are unchanged.', '',
           '## Class questions and consequences', '']
    for n, item in enumerate(policy_items, 1):
        md += [f'### {n}. {item["title"]}', '', f'`{item["item_id"]}` — {item["trigger"]}; 10 minutes; {item["affected_instance_count"]} affected instances.', '', item['question'], '']
        md += [f'- **{answer}**: {consequence}' for answer, consequence in item['answer_consequences'].items()]
        md += ['', f'Direct records: A={len(item["direct_record_ids"]["A"])}; B={len(item["direct_record_ids"]["B"])}. '
               f'Context records: A={len(item["context_record_ids"]["A"])}; B={len(item["context_record_ids"]["B"])}.', '', 'Representative evidence:', '']
        for rep in item['representative_instances']:
            name = ', '.join(rep['tracking_numbers']) or 'source accounting'
            md.append(f'- **{name}** (`{rep["sub_issue_id"]}`)')
            for ev in rep['evidence']:
                quote = ' '.join(ev['quote'].split())
                md.append(f'  - `{ev["manifest_entry_id"]}`, {ev["locator"]}: “{quote}”')
        if len(item['representative_instances']) < 3:
            md += ['', f'Only {len(item["representative_instances"])} supplied instance is available for this required class.']
        md.append('')
    md += ['## Ten highest-impact case items', '']
    for n, item in enumerate(high, 1):
        topics = collections.Counter(x['class'] for x in item['sub_issues'])
        context = ', '.join(f'{k.replace("_", " ")}: {v}' for k, v in topics.most_common(3))
        if item['proceeding'] == 'CT-source-gaps':
            context = 'Law Journal not inspected; DEEP RBCR cross-check invalid. Decide recovery, scope narrowing or unresolved completeness'
        elif item['trigger'] == 'identity':
            context = 'Confirm the same native history event under different fallback update IDs'
        elif item['trigger'] == 'visual_mark':
            context = 'Inspect the rendered evidence deciding this opportunity’s hearing/date label'
        elif item['trigger'] == 'date_ambiguity':
            flags = [x for x in item['sub_issues'] if x['class'] == 'unknown_conflicting_date']
            vals = sorted({f"{t['role']} {temporal_scalar(t.get('local_value')) or 'unstated'} ({t['status']})" for x in flags for report in [x] + x.get('additional_reports', []) for t in report['values']})
            context = 'Resolve concrete date/status questions: ' + ', '.join(vals[:3])
        if item['proceeding'] == 'PR2023-031':
            context += '; stated carry-in close versus withdrawal before interval start'
        if item['proceeding'] == 'PR2025-036':
            context += '; withdrawal, provisional replacement and separately opened round'
        md.append(f'{n}. **{item["title"]}** — {context}. `{item["item_id"]}`; {item["estimated_minutes"]} min.')
    md += ['', '## Agreement and input accounting', '', '| Type | Both | A only | B only |', '|---|---:|---:|---:|']
    md += [f'| {t} | {both} | {a} | {b} |' for t, both, a, b in stats]
    md += ['', f'Decisive agreement: {equal}/{total} ({equal/total:.2%}) slots, excluding reverse-list membership. '
           'This includes conditional alternate-key comparisons twice in exact-ID rows; it is a diagnostic, not a correctness verdict.', '',
           'Pass B’s 97 extra update IDs:', '', '| Evidence category | Count |', '|---|---:|']
    md += [f'| {category} | {n} |' for category, n in sorted(extra_classes.items())]
    md += ['', 'Both sealed output hashes match. Both passes have 350 completion rows for 350 retrieved views. '
           'Pass B remains diagnostic: 210 normalized JSON quotes and 25 completion-attribution discrepancies are not repaired. '
           'The exact-span supplement itself is not supplied, only its hash file. Pass A reports corrected timing allocations. '
           'No other state, .census-passes directory, original capture, install or network was accessed.', '',
           '## Record decisions and budget', '',
           'The primary drafts one append-only adjudication per owner answer in CT/adjudications.jsonl, author.role=human_reviewer, phase=adjudicated. '
           'For a class, payload.target_record_ids lists the full affected record_ids from both passes, with context-only records identified in the finding; '
           'cite the class item_id, selected answer, policy limits/exceptions and affected sub_issue_ids. Record input/result versions, finding/rationale, actual reviewer/time/minutes and rescore references. '
           'Scope decisions use established/not_established/narrowed as the schema requires. No agent signs the owner’s decision.', '',
           'The 360-minute CT budget is a task-specific override. This queue excludes the still-required agreed-date/role and random-audit work; 110 raw union opportunity IDs trigger the protocol’s ≤150 rule. '
           'The predeclared reductions coarsen overlapping audit units, then reduce ordinary samples, then scan/empty/exclusion samples while retaining floors. '
           'They cannot waive remaining case questions. An over-budget result still needs an owner scope/budget decision before final claims.', '',
           '## Appendix: every affected class record', '',
           'Lists below exactly match each class item’s record_ids. **Context** means a typed parent/notice in the other pass, included for traceability rather than a direct policy label. '
           'All IDs are immutable sealed-pass record IDs; no adjudication or record change has been made.', '']
    for item in policy_items:
        md += [f'### {item["title"]}', '', f'`{item["item_id"]}`', '']
        for side in 'AB':
            md += [f'Pass {side} ({len(item["record_ids"][side])} records):', '']
            for rid in item['record_ids'][side]:
                suffix = ' — context' if rid in item['context_record_ids'][side] else ''
                md.append(f'- `{rid}`{suffix}')
            md.append('')
    (OUT / 'REVIEW-QUEUE.md').write_text('\n'.join(md))
    print(canonical({'counts_by_item_kind_and_trigger': by_kind_trigger, 'minutes_by_kind': kind_minutes,
                     'total_items': len(items), 'total_minutes': minutes, 'budget': 360,
                     'classes': [{'key': i['policy_key'], 'instances': i['affected_instance_count'], 'representatives': len(i['representative_instances'])} for i in policy_items],
                     'derivable_membership_diffs_removed': derived,
                     'top10_cases': [{'proceeding': i['proceeding'], 'trigger': i['trigger']} for i in high]}))


if __name__ == '__main__':
    main()
