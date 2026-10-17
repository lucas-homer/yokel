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


def build_strata(manifest, completion, level, minutes_native, minutes_scan):
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
    for eid, e in entries.items():
        rows = [logs[p, eid] for p in ('pass_A', 'pass_B')]
        disposition = ('inclusion' if any(r['candidate_count'] for r in rows) else
                       'exclusions_only' if any(r['rejected_count'] for r in rows) else
                       'no_candidates')
        high = (disposition != 'inclusion' or e['format'] == 'scan_pdf'
                or e['text_layer'] != 'native')
        # Separate text-layer/both-empty flags remain explicit in stable stratum IDs.
        key = (e['source_id'], e['agency_id'], e['process_id'], e['format'],
               e['publication_cycle'] if level == 0 else 'all_cycles',
               disposition, 'both_empty='+str(disposition == 'no_candidates').lower(),
               'text_layer='+e['text_layer'])
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


def plan(manifest, completion, level, minutes_native, minutes_scan, mandatory, budget):
    history = []
    reasons = {1: 'Whole-document anchors retained; merge publication cycles only.',
               2: 'Reduce ordinary inclusion floor to max(2, ceil(10% N)), bounded by N.',
               3: 'Reduce risk sample to min(N, 20, max(5, ceil(20% N))); weaker sensitivity.'}
    scenarios = []
    for step in range(level+1):
        strata = build_strata(manifest, completion, step, minutes_native, minutes_scan)
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


def sample_note(state, audit, manifest, frozen_at, scenarios):
    entries = {e['entry_id']: e for e in manifest}
    out = [f'# {state} frozen random audit', '', f'Frozen (UTC): {frozen_at}',
           f'Seed: `{audit["seed"]}`', f'Frame SHA-256: `{audit["frame_hash"]}`', '',
           'Canonical frame is represented by the ordered strata and unit_coverage in run.json;',
           'audit_freeze.frame reconstructs its exact compact, sorted-key UTF-8 bytes.', '',
           f'Budget {audit["review_budget_minutes"]:g}; mandatory {audit["mandatory_minutes_estimate"]:g}; '
           f'overlap 0; total estimate {audit["estimate_minutes"]:g} minutes. '
           'No reviews completed; actual minutes 0.', '',
           'Check **boundaries, accepted labels, exclusions and overlooked candidates in originals** '
           'for every selected unit. Read selected content in full. Selection is not a completeness verdict.', '',
           'Level | Strata | Sample | Audit minutes | Total minutes', '---|---:|---:|---:|---:']
    for row in scenarios:
        out.append(' | '.join(str(row[k]) for k in
                              ('level', 'strata', 'sample', 'audit_minutes', 'estimate_minutes')))
    out += ['', 'Strata below retain source/agency/process/format, union disposition, both-empty and '
            'text-layer flags; cycles are merged at level 1. Each unit covers exactly its own entry.', '']
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
        out.append('')
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
    parser.add_argument('--force', action='store_true', help='explicitly override existing seed (protocol exception)')
    args = parser.parse_args()
    directory = args.state_dir
    run_path = directory/'run.json'
    run = json.loads(run_path.read_text())
    if not args.dry_run and run['audit']['seed'] is not None and not args.force:
        parser.error('existing non-null seed; refusing a second draw (including zero placeholders)')
    budget = args.review_budget if args.review_budget is not None else run['audit'].get('review_budget_minutes', 240)
    if any(not math.isfinite(x) or x < 0 for x in
           (budget, args.minutes_native, args.minutes_scan, args.mandatory)):
        parser.error('minutes and budget must be finite and nonnegative')
    manifest = lines(directory/'manifest.jsonl')
    completion = lines(directory/'completion.jsonl')
    audit, scenarios = plan(manifest, completion, args.level, args.minutes_native,
                            args.minutes_scan, args.mandatory, budget)
    print(json.dumps(scenarios, indent=2))
    if args.dry_run:
        return
    frozen_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    if audit['coarsening_history']:
        audit['coarsening_history'][-1]['reason'] += f' Frame frozen at {frozen_at} before seed.'
    audit['frame_hash'] = digest(canonical(frame(audit)))
    audit['frozen_before_seed'] = True
    # Persist all frame inputs, costs and hash BEFORE invoking the entropy source.
    replace_audit(run_path, audit)
    audit['seed'] = secrets.token_hex(32)
    select(audit)
    replace_audit(run_path, audit)
    note = directory/'reconcile'/'AUDIT-SAMPLE.md'
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(sample_note(run['state'], audit, manifest, frozen_at, scenarios))
    print(json.dumps({'seed': audit['seed'], 'frame_hash': audit['frame_hash'],
                      'frozen_at': frozen_at, 'N': len(audit['unit_coverage'])}))


if __name__ == '__main__':
    main()
