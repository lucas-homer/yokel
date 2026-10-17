#!/usr/bin/env python3
"""Freeze a census audit plan before drawing its single random seed (stdlib only)."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import fcntl

from container_audit import build_frames, nested_selections


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def required(n, high, level):
    # Keep exactly in step with validate.py C08, including the level-3 cap.
    return (min(n, min(20, max(5, math.ceil(.2*n))) if level == 3 else 20)
            if high else min(n, max(2 if level >= 2 else 5,
                                   math.ceil((.1 if level >= 2 else .2)*n))))


def fixed_allocation(strata, sample_total=30):
    """A1 bounded Hamilton allocation; no randomness or mutable input order."""
    if type(sample_total) is not int or sample_total != 30:
        raise ValueError('fixed_sample_v1 requires sample_total 30')
    sizes = {s['stratum_id']: len(s['unit_ids']) for s in strata}
    if len(sizes) != len(strata):
        raise ValueError('duplicate stratum ID')
    result = dict.fromkeys(sizes, 0)
    k = min(sample_total, sum(sizes.values()))
    high = {s['stratum_id']: sizes[s['stratum_id']] for s in strata if s['high_risk']}
    ordinary = {sid: n for sid, n in sizes.items() if sid not in high}
    # Exactly the risk reserve, unless ordinary capacity forces a larger share.
    h = max(min(sum(high.values()), (2*k+4)//5), k-sum(ordinary.values()))
    for group, seats in ((high, h), (ordinary, k-h)):
        active = {sid: n for sid, n in group.items() if n}
        lower = seats >= len(active)
        # Fix only lower-bound violations, then recompute proportional quotas.
        while active and lower:
            population = sum(active.values())
            small = [sid for sid, n in active.items() if seats*n < population]
            if not small:
                break
            for sid in small:
                result[sid] = 1
                seats -= 1
                del active[sid]
        if not active:
            continue
        population = sum(active.values())
        for sid, n in active.items():
            result[sid] = seats*n//population
        remaining = seats-sum(result[sid] for sid in active)
        order = sorted(active, key=lambda sid: (-(seats*active[sid] % population), sid))
        for sid in order[:remaining]:
            result[sid] += 1
    return result


def paired_coverage(manifest, level):
    """Pair linked issue PDF/TOC views, retaining their original anchor IDs."""
    entries = {e['entry_id']: e for e in manifest if e['retrieval']['result'] == 'retrieved'}
    coverage = {eid: [eid] for eid in entries}
    if not level:
        return coverage
    for eid, entry in sorted(entries.items()):
        if entry['kind'] != 'issue' or entry['format'] not in ('text_pdf', 'scan_pdf'):
            continue
        matches = [tid for tid, toc in entries.items() if toc['kind'] in ('toc', 'index')
                   and (toc.get('parent_entry_id') == eid or tid in entry['accounting']['child_entry_ids'])
                   and all(toc[f] == entry[f] for f in
                           ('source_id', 'agency_id', 'process_id'))]
        # VA's frozen manifest links TOC and PDF as sibling views by native key.
        sibling = eid[:-3]+'toc' if eid.endswith('-pdf') else None
        if sibling in entries:
            toc = entries[sibling]
            if toc['kind'] in ('toc', 'index') and all(toc[f] == entry[f] for f in
                    ('source_id', 'agency_id', 'process_id')):
                matches.append(sibling)
        for tid in sorted(set(matches)):
            if tid in coverage:
                coverage[eid] += coverage.pop(tid)
        coverage[eid].sort()
    return coverage

def frame(audit):
    coverage = audit['unit_coverage']
    return [{'stratum_id': s['stratum_id'], 'unit_ids': sorted(s['unit_ids']),
             'disposition': s['disposition'], 'high_risk': s['high_risk'],
             'unit_coverage': {uid: coverage[uid] for uid in sorted(s['unit_ids'])}}
            for s in audit['strata']]


def select(audit):
    for s in audit['strata']:
        ranked = sorted(s['unit_ids'], key=lambda uid: (
            digest((audit['seed']+'\n'+s['stratum_id']+'\n'+uid).encode()), uid))
        s['selected_ids'] = ranked[:s['sample_size']]


def build_strata(manifest, completion, level, minutes_native, minutes_scan, coverage=None):
    entries = {e['entry_id']: e for e in manifest if e['retrieval']['result'] == 'retrieved'}
    if len({e['entry_id'] for e in manifest}) != len(manifest):
        raise ValueError('duplicate manifest entry ID')
    logs = {}
    for row in completion:
        key = row['pass'], row['manifest_entry_id']
        if key in logs:
            raise ValueError(f'duplicate completion: {key}')
        logs[key] = row
    if set(logs) != {(p, eid) for p in ('pass_A', 'pass_B') for eid in entries}:
        raise ValueError('completion must cover each retrieved entry once in each pass')
    groups = defaultdict(list)
    coverage = coverage if coverage is not None else {eid: [eid] for eid in entries}
    for eid, members in coverage.items():
        e = entries[eid]
        rows = [logs[p, member] for member in members for p in ('pass_A', 'pass_B')]
        disposition = ('inclusion' if any(r['candidate_count'] for r in rows) else
                       'exclusions_only' if any(r['rejected_count'] for r in rows) else
                       'no_candidates')
        high = (disposition != 'inclusion' or e['format'] == 'scan_pdf'
                or any(entries[mid]['format'] == 'scan_pdf' or entries[mid]['text_layer'] != 'native' for mid in members))
        # Separate text-layer/both-empty flags remain explicit in stable stratum IDs.
        text_layer = next((entries[mid]['text_layer'] for mid in members if entries[mid]['text_layer'] != 'native'), 'native')
        key = (e['source_id'], e['agency_id'], e['process_id'], e['format'],
               e['publication_cycle'] if level == 0 else 'all_cycles',
               disposition, 'both_empty='+str(disposition == 'no_candidates').lower(),
               'text_layer='+text_layer)
        groups[key, high].append(eid)
    strata = []
    for (key, high), ids in sorted(groups.items()):
        scan = key[3] == 'scan_pdf' or key[-1] != 'text_layer=native'
        strata.append({'stratum_id': json.dumps(key, ensure_ascii=False, separators=(',', ':')),
                       'unit_ids': sorted(ids), 'disposition': key[5], 'high_risk': high,
                       'minutes_per_unit': minutes_scan if scan else minutes_native,
                       'sample_size': required(len(ids), high, level),
                       'selected_ids': [], 'completed_ids': []})
    return strata


def plan(manifest, completion, level, minutes_native, minutes_scan, mandatory, budget,
         method="stratified_floor", sample_total=30, unit_minutes=None):
    history = []
    reasons = {1: 'Whole-document anchors retained; merge publication cycles only.',
               2: 'Reduce ordinary inclusion floor to max(2, ceil(10% N)), bounded by N.',
               3: 'Reduce risk sample to min(N, 20, max(5, ceil(20% N))); weaker sensitivity.'}
    if method == 'fixed_sample_v1':
        reasons = {1: 'Pair overlapping PDF/TOC views and merge cycles; A1 fixed allocation.',
                   2: 'Retain A1 fixed allocation; stratified ordinary floor reduction does not apply.',
                   3: 'Retain A1 fixed allocation; stratified risk floor reduction does not apply.'}
    scenarios = []
    for step in range(level+1):
        coverage = paired_coverage(manifest, step) if method == 'fixed_sample_v1' else None
        strata = build_strata(manifest, completion, step, minutes_native, minutes_scan, coverage)
        if method == 'fixed_sample_v1':
            allocation = fixed_allocation(strata, sample_total)
            for s in strata:
                s['sample_size'] = allocation[s['stratum_id']]
        if unit_minutes is not None:
            for s in strata:
                values = [unit_minutes[uid] for uid in s['unit_ids']]
                if any(not math.isfinite(v) or v < 0 for v in values):
                    raise ValueError('unit cost must be finite and nonnegative')
                s['minutes_per_unit'] = math.ceil(sum(values)/len(values))
        cost = sum(s['sample_size']*s['minutes_per_unit'] for s in strata)
        estimate = mandatory + cost
        scenarios.append({'level': step, 'strata': len(strata),
                          'sample': sum(s['sample_size'] for s in strata),
                          'audit_minutes': cost, 'estimate_minutes': estimate})
        if step:
            history.append({'level': step, 'estimate_minutes': estimate, 'reason': reasons[step]})
    if estimate > budget:
        raise ValueError(f'level {level} estimate {estimate:g} exceeds budget {budget:g}; stop/narrow')
    audit = {'seed': None, 'frame_hash': None, 'coarsening_level': level,
             'frozen_before_seed': False, 'review_budget_minutes': budget,
             'mandatory_minutes_estimate': mandatory, 'overlap_minutes': 0,
             'estimate_minutes': estimate, 'actual_minutes': 0, 'strata': strata,
             'unit_coverage': {eid: [eid] for s in strata for eid in s['unit_ids']},
             'coarsening_history': history}
    if method == 'fixed_sample_v1':
        audit.update(method=method, sample_total=sample_total, unit_coverage=coverage)
    return audit, scenarios


def replace_audit(path, audit):
    """Replace only the top-level audit value; preserve all other bytes and indentation."""
    source = path.read_text()
    match = re.search(r'(?m)^([ \t]*)"audit"[ \t]*:[ \t]*', source)
    if not match:
        raise ValueError('cannot locate top-level audit')
    start = match.end()
    _, length = json.JSONDecoder().raw_decode(source[start:])
    indent = match.group(1)
    # Detect the existing run.json indentation unit from its first property.
    unit = re.search(r'(?m)^([ \t]+)"', source).group(1)
    rendered = json.dumps(audit, ensure_ascii=False, indent=unit)
    rendered = rendered.replace('\n', '\n'+indent)
    path.write_text(source[:start]+rendered+source[start+length:])


def sample_note(state, audit, manifest, frozen_at, scenarios, container_frames=None):
    entries = {e['entry_id']: e for e in manifest}
    fixed = audit.get('method', 'stratified_floor') == 'fixed_sample_v1'
    instructions = ('A1: every unaccounted container row plus min(5, accounted) seeded verifications; '
                    'one seeded complete item participation read and remaining-body searches in context. '
                    'Read non-container units in full. Never skip drawn units.' if fixed else
                    'Read selected content in full.')
    out = [f'# {state} frozen random audit', '', f'Frozen (UTC): {frozen_at}',
           f'Seed: `{audit["seed"]}`', f'Frame SHA-256: `{audit["frame_hash"]}`', '',
           'Canonical frame is represented by the ordered strata and unit_coverage in run.json;',
           'audit_freeze.frame reconstructs its exact compact, sorted-key UTF-8 bytes.', '',
           f'Budget {audit["review_budget_minutes"]:g}; mandatory {audit["mandatory_minutes_estimate"]:g}; '
           f'overlap 0; total estimate {audit["estimate_minutes"]:g} minutes. '
           'No reviews completed; actual minutes 0.', '',
           'Check **boundaries, accepted labels, exclusions and overlooked candidates in originals** '
           f'for every selected unit. {instructions} Selection is not a completeness verdict.', '',
           'Level | Strata | Sample | Audit minutes | Total minutes', '---|---:|---:|---:|---:']
    if fixed:
        out[6:6] = [f'Container-frame SHA-256: `{audit["container_frame_hash"]}`',
                     'Frames: `reconcile/container-frames.json` (canonical JSON hash); frozen before the state seed.',
                     'Signed A1: rights/DECISIONS.md item 20; VA budget: item 21.', '']
    for row in scenarios:
        out.append(' | '.join(str(row[k]) for k in
                              ('level', 'strata', 'sample', 'audit_minutes', 'estimate_minutes')))
    out += ['', 'Strata below retain source/agency/process/format, union disposition, both-empty and '
            'text-layer flags; cycles are merged at level 1. See unit_coverage for every original entry covered.', '']
    for s in audit['strata']:
        out += [f'## `{s["stratum_id"]}`', '',
                f'N={len(s["unit_ids"])}; sample={s["sample_size"]}; '
                f'{s["minutes_per_unit"]:g} min/unit; '
                f'{s["minutes_per_unit"]*s["sample_size"]:g} minutes.', '']
        for uid in s['selected_ids']:
            e = entries[uid]
            locator = e['accounting']['pagination_or_page_range'] or e['expected']['selector']
            original = f'.census-passes/{state}/inputs/originals/{e["retrieval"]["sha256"]}'
            out.append(f'- [ ] `{uid}` — {locator}; `{original}`.')
            for member in audit['unit_coverage'][uid]:
                if member != uid:
                    out.append(f'Covered view `{member}`: `.census-passes/{state}/inputs/originals/{entries[member]["retrieval"]["sha256"]}`.')
            if fixed and uid in audit['container_selections']:
                chosen = audit['container_selections'][uid]
                container = container_frames['containers'][uid]
                by_id = {row['row_id']: row for row in container['rows']}
                out += ['', f'Container: {len(container["rows"])} rows; '
                        f'{len(chosen["unaccounted_row_ids"])} unaccounted (review ALL); '
                        f'{len(chosen["accounted_row_ids"])} seeded accounted verifications.']
                for kind, ids in [('Unaccounted', chosen['unaccounted_row_ids']),
                                  ('Seeded accounted', chosen['accounted_row_ids']),
                                  ('Seeded participation item (b)', [chosen['item_id']])]:
                    if not ids and kind == 'Unaccounted':
                        out.append('Unaccounted: none in this container.')
                    for rid in ids:
                        row = by_id[rid]
                        source = row['source_entry_id']
                        path = f'.census-passes/{state}/inputs/originals/{row["source_sha256"]}'
                        docs = ', '.join(row['doc_numbers']) or 'unnumbered; use ordinal/fingerprint'
                        pointer = row['union_record_id'] or 'unaccounted'
                        out += ['', f'- [ ] **{kind}** `{rid}` — {row["item_kind"]}; {docs}.',
                                f'  Source `{source}`: `{path}`; {row["source_locator"]}.',
                                f'  Union pointer: `{pointer}`. Native-text fingerprint: `{row["native_text_fingerprint"]}`.']
                        if kind == 'Seeded participation item (b)':
                            out.append('  Read heading, preamble/summary and EVERY public comment, hearing, hearing-request, '
                                       'objection and petition section in full. Search the remaining body for dates and '
                                       'comment/hearing/objection terms; read every hit in context. Use complete source '
                                       'boundaries, including all boundary-page context; no truncation to an extracted snippet.')
                        else:
                            out.append('  Check the original row, identity/boundaries, accepted/rejected union pointer, '
                                       'exclusions and overlooked participation candidates. Unaccounted is unresolved mapping, '
                                       'not a pre-decided omission verdict.')
            elif fixed:
                out.append('Read this non-container source IN FULL; check boundaries, labels, exclusions, '
                           'all dates/roles and overlooked participation candidates.')
        out.append('')
    if fixed:
        total = sum(len(v['unaccounted_row_ids']) for v in audit['container_selections'].values())
        out += ['', f'**Total unaccounted rows to review: {total}.**',
                'Log reviewer identity, start/end UTC, active minutes, target/trigger, evidence, input/output versions, finding, rationale and unresolved questions.',
                'An omission expands review to the whole affected template/process/cycle and requires a new label version. Never skip a drawn sample. Stop final claims if expansion exceeds budget.',
                'A1 has weaker sensitivity than stratified floors, no per-stratum inspection claim and no confidence claim. No human reviews or verdicts are recorded by this checklist.']
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state_dir', type=Path)
    parser.add_argument('--level', type=int, choices=range(4), required=True)
    parser.add_argument('--minutes-native', type=float, required=True)
    parser.add_argument('--minutes-scan', type=float, required=True)
    parser.add_argument('--mandatory', type=float, required=True)
    parser.add_argument('--review-budget', type=float)
    parser.add_argument('--dry-run', action='store_true', help='calculate only; never generate a seed')
    parser.add_argument('--method', choices=('stratified_floor', 'fixed_sample_v1'), default='stratified_floor',
                        help='A1 fixed_sample_v1 signed by the owner 2026-10-17 (rights/DECISIONS.md item 20)')
    parser.add_argument('--sample-total', type=int, default=30)
    parser.add_argument('--high-risk-share', type=float, default=.4)
    parser.add_argument('--costing-file', type=Path, help='Frozen local audit-estimate.json per-unit cost allowances')
    args = parser.parse_args()
    directory = args.state_dir
    run_path = directory/'run.json'
    with run_path.open() as guard:
        if not args.dry_run:
            fcntl.flock(guard.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        run = json.loads(run_path.read_text())
        if not args.dry_run and (run['audit']['seed'] is not None or run['audit'].get('frozen_before_seed') or
                                 any(s['selected_ids'] for s in run['audit'].get('strata', []))):
            parser.error('existing seed, frozen frame or drawn selection; refusing to replace/redraw')
        if args.method == 'fixed_sample_v1':
            if run['state'] not in ('VA', 'WA', 'MS'):
                parser.error('A1 scope is VA, WA and MS; CT retains stratified_floor')
            if args.sample_total != 30 or args.high_risk_share != .4:
                parser.error('fixed_sample_v1 requires --sample-total 30 --high-risk-share 0.4')
        budget = args.review_budget if args.review_budget is not None else run['audit'].get('review_budget_minutes', 240)
        if any(not math.isfinite(x) or x < 0 for x in
               (budget, args.minutes_native, args.minutes_scan, args.mandatory)):
            parser.error('minutes and budget must be finite and nonnegative')
        manifest = lines(directory/'manifest.jsonl')
        completion = lines(directory/'completion.jsonl')
        unit_minutes = None
        if args.costing_file:
            costing = json.loads(args.costing_file.read_text())
            source = costing['costings']['scripted_accounting_sampled_verification']
            unit_minutes = {u['unit_id']: u['minutes'] for u in source['initial_units']}
            if args.method != 'fixed_sample_v1':
                parser.error('--costing-file currently supports fixed_sample_v1 only')
        audit, scenarios = plan(manifest, completion, args.level, args.minutes_native,
                                args.minutes_scan, args.mandatory, budget, args.method, args.sample_total, unit_minutes)
        container_frames = None
        crosswalk_rows = None
        if args.method == 'fixed_sample_v1':
            crosswalk_path = directory/'reconcile/container-crosswalk.jsonl'
            crosswalk_rows = lines(crosswalk_path) if crosswalk_path.exists() else []
            needed = {e['entry_id'] for e in manifest if e['retrieval']['result'] == 'retrieved'
                      and e['kind'] in ('issue', 'index', 'portal_slice', 'history_slice')}
            legacy = crosswalk_rows and all('item_frame_status' not in row for row in crosswalk_rows)
            if legacy or needed - {row['container_id'] for row in crosswalk_rows}:
                from container_crosswalk import build_rows
                crosswalk_rows = build_rows(directory)
            container_frames = build_frames(crosswalk_rows, manifest)
            audit['container_frame_hash'] = digest(canonical(container_frames))
            audit['container_selections'] = {}
            if args.costing_file:
                audit['costing_file'] = str(args.costing_file.resolve().relative_to(directory.resolve()))
                audit['costing_sha256'] = digest(args.costing_file.read_bytes())
        print(json.dumps(scenarios, indent=2))
        if args.dry_run:
            return
        frozen_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        if container_frames is not None:
            audit['frozen_at'] = frozen_at
            target = directory/'reconcile/container-frames.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            (directory/'reconcile/container-crosswalk.jsonl').write_text(''.join(
                json.dumps(row, sort_keys=True, separators=(',', ':'))+'\n' for row in crosswalk_rows))
            target.write_text(json.dumps(container_frames, sort_keys=True, indent=2, ensure_ascii=False)+'\n')
        if audit['coarsening_history']:
            audit['coarsening_history'][-1]['reason'] += f' Frame frozen at {frozen_at} before seed.'
        audit['frame_hash'] = digest(canonical(frame(audit)))
        audit['frozen_before_seed'] = True
        # Persist all frame inputs, costs and hash BEFORE invoking the entropy source.
        replace_audit(run_path, audit)
        audit['seed'] = secrets.token_hex(32)
        select(audit)
        if container_frames is not None:
            audit['container_selections'] = nested_selections(audit, container_frames)
        replace_audit(run_path, audit)
        note = directory/'reconcile'/'AUDIT-SAMPLE.md'
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(sample_note(run['state'], audit, manifest, frozen_at, scenarios, container_frames))
        print(json.dumps({'seed': audit['seed'], 'frame_hash': audit['frame_hash'],
                          'container_frame_hash': audit.get('container_frame_hash'),
                          'frozen_at': frozen_at, 'N': len(audit['unit_coverage'])}))


if __name__ == '__main__':
    main()
