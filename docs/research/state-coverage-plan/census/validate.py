#!/usr/bin/env python3
"""Offline census consistency checks. Default fixtures are synthetic, not a census result."""
import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def load(path):
    return json.loads(path.read_text())

def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def validate(directory, verify_bytes=False, stage="final"):
    errors = []
    def check(ok, code, detail):
        if not ok:
            errors.append(f'{code}: {detail}')
    run = load(directory / 'run.json')
    manifest = lines(directory / 'manifest.jsonl')
    names = ['pass-A.jsonl', 'pass-B.jsonl', 'labels.jsonl', 'adjudications.jsonl']
    if stage == 'final':
        for name in names:
            check((directory/name).is_file(), 'C01', f'required final artifact missing: {name}')
    labels = sum((lines(directory / name) for name in names if (directory/name).is_file()), [])
    completion = lines(directory / 'completion.jsonl') if (directory/'completion.jsonl').is_file() else []
    rights = load(directory / run['rights_file'])
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        print('SKIP schema validation: jsonschema not importable; cross-record checks still run.')
    else:
        for schema_name, records in [('run', [run]), ('manifest', manifest), ('labels', labels),
                                     ('completion', completion), ('rights-surface', rights + load(HOME.parent / 'rights/surfaces.json'))]:
            schema = load(HOME / f'{schema_name}.schema.json')
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            for i, record in enumerate(records):
                for error in validator.iter_errors(record):
                    check(False, 'SCHEMA', f'{schema_name}[{i}] {list(error.path)}: {error.message}')
        print('Schema validation ran (Draft 2020-12).')
    def index(records, key, code):
        result = {r[key]: r for r in records}
        check(len(result) == len(records), code, f'duplicate {key}')
        return result
    entries = index(manifest, 'entry_id', 'C01')
    records = index(labels, 'record_id', 'C01')
    surfaces = {(r['surface_id'], r['version']): r for r in rights}
    for surface in rights + load(HOME.parent / 'rights/surfaces.json'):
        rate = surface['rate']
        check(rate['min_interval_seconds'] >= 5 and rate['concurrency'] == 1 and rate['stop_on_status'] == [403,429] and
              rate['identifying_user_agent'] and rate['no_bot_workaround'] and bool(surface['decision_version']) and bool(surface['decision_date']),
              'C02', f"{surface['surface_id']} rights rate/decision guard")
    check(len(surfaces) == len(rights), 'C02', 'duplicate rights surface/version')
    entities = {r['entity_id'] for r in labels if r['record_type'] != 'adjudication'}
    adjudications = {r['record_id']: r for r in labels if r['record_type'] == 'adjudication'}
    def human(ref):
        row = adjudications.get(ref, {})
        return row.get('author', {}).get('role') == 'human_reviewer' and bool(row.get('payload', {}).get('reviewer_id'))
    incomplete = not (run['scope_resolved'] and run['history_bounded'])
    proc_keys = {(p['agency_id'], p['process_id']) for p in run['processes']}
    check(len(proc_keys) == len(run['processes']), 'C03', 'duplicate process row')
    for entry in manifest:
        eid = entry['entry_id']; ret = entry['retrieval']; acc = entry['accounting']; r = entry['rights']
        check((entry['agency_id'], entry['process_id']) in proc_keys, 'C03', f'{eid} outside process universe')
        check(entry['schema_version'] == run['schema_version'] and entry['state'] == run['state'] and
              entry['universe_version'] == run['universe_version'], 'C01', f'{eid} namespace/version mismatch')
        for key in ['parent_entry_id', 'prior_capture_entry_id']:
            ref = entry[key]
            check(ref is None or ref in entries, 'C01', f'{eid} dangling {key}')
        child_ids = acc['child_entry_ids']
        check(len(set(child_ids)) == len(child_ids), 'C03', f'{eid} duplicate children')
        check(all(c in entries and entries[c]['parent_entry_id'] == eid for c in child_ids), 'C01', f'{eid} child linkage')
        actual_children = {e['entry_id'] for e in manifest if e['parent_entry_id'] == eid}
        check(set(child_ids) == actual_children, 'C03', f'{eid} child coverage')
        check(acc['observed_children'] == len(child_ids), 'C03', f'{eid} observed child count')
        if acc['expected_children'] is None or acc['expected_children'] != len(child_ids):
            incomplete = True
            check(entry['completeness'] != 'accounted', 'C03', f'{eid} unknown/missing children called accounted')
        if ret['result'] == 'retrieved' and entry['kind'] in ['index', 'portal_slice', 'history_slice']:
            check(bool(acc['terminal_evidence_refs']), 'C03', f'{eid} missing terminal proof')
        surface = surfaces.get((r['surface_id'], r['version']))
        check(surface is not None, 'C02', f'{eid} rights surface/version missing')
        check(Path(r['record_ref']).name == Path(run['rights_file']).name, 'C02', f'{eid} rights record path mismatch')
        if surface:
            mapping = {'allowed':'allowed', 'allowed_watched_only':'allowed', 'on_hold':'unresolved', 'blocked':'denied'}
            check(surface['state'] == entry['state'] and re.fullmatch(surface['url_pattern'], ret['requested_url']) is not None,
                  'C02', f'{eid} rights state/URL mismatch')
            check(r['collection_rule'] == mapping[surface['collection_rule']] and
                  r['retention_allowed'] == (surface['retention'] == 'internal_originals') and
                  r['third_party_processing'] == ('allowed' if surface['third_party_processing'] == 'public_notices_only' else 'denied') and
                  r['public_evidence_rule'] == surface['public_evidence_rule'], 'C02', f'{eid} rights decision mismatch')
            if surface['collection_rule'] == 'allowed_watched_only' and ret['result'] != 'not_attempted':
                check(run['attended'], 'C02', f'{eid} watched-only source without attended attestation')
        if r['surface_id'] == 'ct-rendered' and ret['result'] == 'retrieved':
            check('json' not in (ret['content_type'] or '').lower(), 'C02', f'{eid} CT rendered permission cannot authorize JSON')
        blocked = r['collection_rule'] != 'allowed' or not r['retention_allowed']
        if blocked:
            check(ret['result'] == 'not_attempted' and entry['completeness'] == 'gap', 'C02', f'{eid} blocked source must be not_attempted + gap')
        if ret['final_url'] and surface:
            check(re.fullmatch(surface['url_pattern'], ret['final_url']) is not None, 'C02', f'{eid} redirected outside authorized surface')
        if ret['result'] != 'retrieved':
            check(ret['sha256'] is None and ret['storage_path'] is None, 'C10', f'{eid} failed response has accepted bytes')
            incomplete = True
            check(entry['completeness'] == 'gap', 'C03', f'{eid} missing source without gap')
        else:
            check(not blocked, 'C02', f'{eid} unauthorized retrieval')
            sha = ret['sha256'] or ''
            expected = f'~/yokel-captures/state-coverage/{sha[:2]}/{sha}'
            check(re.fullmatch('[a-f0-9]{64}', sha) is not None and ret['storage_path'] == expected and
                  ret['sidecar_path'] == expected + '.metadata.json', 'C10', f'{eid} hash/path linkage')
            if verify_bytes:
                data = Path(ret['storage_path']).expanduser().read_bytes()
                sidecar = load(Path(ret['sidecar_path']).expanduser())
                check(digest(data) == sha and len(data) == ret['byte_length'] == sidecar['byte_length'] and
                      sidecar['sha256'] == sha, 'C10', f'{eid} saved-byte digest/length')
                try:
                    Draft202012Validator(load(HOME / 'sidecar.schema.json'), format_checker=FormatChecker()).validate(sidecar)
                except NameError:
                    pass
                check(any(c['manifest_entry_id'] == eid and c['requested_url'] == ret['requested_url'] and
                          c['final_url'] == ret['final_url'] and c['captured_at'] == ret['attempted_at'] and
                          c['rights_surface_id'] == r['surface_id'] and c['rights_version'] == r['version']
                          for c in sidecar['captures']), 'C10', f'{eid} sidecar capture linkage')
        if entry['completeness'] != 'accounted':
            incomplete = True
            check(human(entry['human_review_ref']), 'C03', f'{eid} gap/pending needs human review')
        for cross in acc['cross_checks']:
            target = entries.get(cross['against_entry_id'])
            check(target is not None and cross['lineage_id'] == target['lineage_id'], 'C03', f'{eid} cross-check target lineage')
            if cross['result'] != 'matches':
                incomplete = True
    for start in entries:
        for link in ['parent_entry_id', 'prior_capture_entry_id']:
            seen = set(); current = start
            while current in entries:
                check(current not in seen, 'C01', f'{start} cyclic {link}')
                if current in seen:
                    break
                seen.add(current); current = entries[current][link]
    for proc in run['processes']:
        units = [e for e in manifest if (e['agency_id'], e['process_id']) == (proc['agency_id'], proc['process_id'])]
        name = f"{proc['agency_id']}/{proc['process_id']}"
        check(bool(units), 'C03', f"{proc['process_id']} missing manifest units")
        coverage = proc.get('coverage')
        if coverage is None:
            # Legacy single-lineage rows remain explicit limitations. Never infer full
            # coverage from the mere existence of a different-lineage edge.
            check(proc['single_lineage'], 'C03', f'{name} independent claim requires explicit coverage (partial cross-check cannot establish whole process)')
            check(not proc['single_lineage'] or human(proc['human_review_ref']), 'C03',
                  f"{proc['process_id']} needs independent lineage or reviewed single_lineage")
            incomplete = True
            continue
        mode = coverage['mode']
        universe_rows = coverage['universe']
        universe = {r['unit_id'] for r in universe_rows}
        check(bool(universe) and len(universe) == len(universe_rows), 'C03', f'{name} coverage universe empty/duplicate')
        agencies = {r['unit_id']: r['agency_id'] for r in universe_rows}
        matched = set(); mismatched = set(); unresolved = set(); expected = set(); full = False
        for cross in coverage['checks']:
            left = entries.get(cross['entry_id']); right = entries.get(cross['against_entry_id'])
            valid = (left is not None and right is not None and
                     left['retrieval']['result'] == right['retrieval']['result'] == 'retrieved' and
                     left['lineage_id'] != right['lineage_id'] and
                     any((e['agency_id'], e['process_id']) == (proc['agency_id'], proc['process_id']) for e in [left, right]) and
                     any(c['against_entry_id'] == right['entry_id'] and c['lineage_id'] == right['lineage_id']
                         for c in left['accounting']['cross_checks']))
            check(valid, 'C03', f'{name} coverage check lacks retrieved different-lineage manifest edge')
            exp, mat, mis, unr = [set(cross[k]) for k in
                ['expected_unit_ids','matched_unit_ids','mismatched_unit_ids','unresolved_unit_ids']]
            check(all(len(cross[k]) == len(set(cross[k])) for k in
                      ['expected_unit_ids','matched_unit_ids','mismatched_unit_ids','unresolved_unit_ids']),
                  'C03', f'{name} duplicate coverage unit')
            partition = not (mat & mis or mat & unr or mis & unr) and mat | mis | unr == exp
            if valid and mat:
                matches = any(c['against_entry_id'] == right['entry_id'] and c['result'] == 'matches'
                              for c in left['accounting']['cross_checks'])
                check(matches, 'C03', f'{name} matched units require a resolved matching manifest edge')
                valid = valid and matches
            check(bool(exp) and exp <= universe and partition, 'C03', f'{name} coverage outcomes must partition expected subset of universe')
            check(cross['scope'] != 'full' or exp == universe, 'C03', f'{name} full source scope must cover whole universe')
            if valid and partition and exp <= universe:
                expected |= exp; matched |= mat; mismatched |= mis; unresolved |= unr
                full |= cross['scope'] == 'full' and exp == universe
        # Conflicting checks cannot cancel a discrepancy or an unresolved comparison.
        corroborated = matched - mismatched - unresolved
        uncovered = universe - expected
        print(f'C03 coverage {name}: {mode}; universe={len(universe)} expected={len(expected)} matched={len(matched)} mismatched={len(mismatched)} unresolved={len(unresolved)} uncovered={len(uncovered)}')
        check(proc['single_lineage'] == (mode == 'single_lineage'), 'C03', f'{name} single_lineage flag/coverage mode mismatch')
        check(mode != 'independent_full' or full, 'C03', f'{name} independent_full requires a whole-universe independent source; partial coverage is insufficient')
        check(mode != 'independent_partial' or bool(expected), 'C03', f'{name} independent_partial needs a covered subset')
        claim = set(coverage['claim_agency_ids'])
        eligible_agencies = {agencies[u] for u in corroborated}
        check(claim <= eligible_agencies, 'C03', f'{name} claim agencies exceed corroborated subset')
        fully_checked = mode == 'independent_full' and full and corroborated == universe
        check(coverage['completeness'] != 'established' or fully_checked, 'C03', f'{name} partial/uncovered or discrepant coverage requires completeness not_established')
        if not fully_checked or coverage['completeness'] != 'established':
            incomplete = True
        if mode == 'single_lineage':
            check(not coverage['checks'] and not claim and human(proc['human_review_ref']), 'C03', f'{name} single_lineage needs human review and no independent claim')
    if stage == 'manifest':
        return errors
    retrieved = {e['entry_id'] for e in manifest if e['retrieval']['result'] == 'retrieved'}
    logs = {}
    for phase in ['pass_A', 'pass_B']:
        rows = [r for r in completion if r['pass'] == phase]
        logs[phase] = index(rows, 'manifest_entry_id', 'C04')
        check(set(logs[phase]) == retrieved, 'C04', f'{phase} completion coverage != retrieved manifest')
        for row in rows:
            e = entries.get(row['manifest_entry_id'])
            if e and e['text_layer'] in ['none', 'partial']:
                check(row['inspection_mode'] in ['rendered_image', 'both'], 'C04', f"{phase} {e['entry_id']} requires image inspection")
            check(row['candidate_count'] != 0 or bool(row['zero_candidate_reason']), 'C04', f'{phase} zero count needs reason')
    passes = index(run['passes'], 'pass', 'C05')
    check(set(passes) == {'pass_A','pass_B'}, 'C05', 'two pass attestations required')
    check(len({p['provider'] for p in passes.values()}) == 2, 'C05', 'providers must differ')
    brief_ready = bool(run['brief_sha256'] and run['brief_frozen_at'])
    check(brief_ready, 'C05', 'brief hash/frozen time required at passes/final stage')
    check((directory / run['brief_file']).is_file() and digest((directory / run['brief_file']).read_bytes()) == run['brief_sha256'], 'C05', 'brief hash mismatch')
    for phase, p in passes.items():
        name = 'pass-A.jsonl' if phase == 'pass_A' else 'pass-B.jsonl'
        check(p['brief_sha256'] == run['brief_sha256'] and p['isolated'] and
              brief_ready and stamp(run['brief_frozen_at']) <= stamp(p['dispatched_at']) < stamp(p['sealed_at']), 'C05', f'{phase} brief/isolation/times')
        check(digest((directory / name).read_bytes()) == p['output_sha256'], 'C05', f'{phase} sealed output hash mismatch')
    if stage == 'passes':
        return errors
    pass_records = {r['record_id'] for r in labels if r['phase'] in passes}
    crosswalk = index(run['crosswalk'], 'record_id', 'C05')
    check(set(crosswalk) == pass_records, 'C05', 'crosswalk must cover every pass record')
    for c in crosswalk.values():
        check(c['canonical_entity_id'] in entities, 'C05', f"{c['record_id']} crosswalk target missing")
        if c['identity_action'] != 'same':
            check(human(c['adjudication_ref']) and adjudications[c['adjudication_ref']]['payload']['trigger'] == 'identity',
                  'C05', f"{c['record_id']} merge/split needs identity adjudication")
    final_entities = {r['entity_id'] for r in labels if r['phase'] == 'adjudicated' and r['record_type'] != 'adjudication'}
    check(all(c['canonical_entity_id'] in final_entities for c in crosswalk.values()), 'C05', 'crosswalk target missing from adjudicated snapshot')
    source_ids = {e['source_id'] for e in manifest}
    def evidence(ev, rid):
        entry = entries.get(ev['manifest_entry_id'])
        check(entry is not None and entry['retrieval']['result'] == 'retrieved' and
              entry['retrieval']['sha256'] == ev['sha256'] and bool(ev['locator']), 'C06', f'{rid} evidence hash/location')
    def walk(value):
        if isinstance(value, dict):
            yield value
            for v in value.values():
                yield from walk(v)
        elif isinstance(value, list):
            for v in value:
                yield from walk(v)
    for r in labels:
        rid = r['record_id']; payload = r['payload']; phase = r['phase']; typ = r['record_type']
        check(r['schema_version'] == run['schema_version'] and r['state'] == run['state'] and
              r['universe_version'] == run['universe_version'], 'C01', f'{rid} namespace/version')
        if typ != 'adjudication':
            check(bool(r['evidence']), 'C06', f'{rid} missing source evidence')
            check(f"/state-{run['state'].lower()}/" in r['entity_id'], 'C01', f'{rid} entity namespace')
        if phase in passes:
            p = passes[phase]
            check(r['author']['role'] == phase + '_child' and r['author']['provider'] == p['provider'] and
                  r['author']['task_id'] == p['task_id'], 'C06', f'{rid} phase author mismatch')
        else:
            check(r['author']['role'] in ['primary','human_reviewer'] and r['review_status'] != 'candidate', 'C06', f'{rid} adjudicated status/author')
        check(all(a['source_id'] in source_ids for a in r['aliases']), 'C01', f'{rid} alias source missing')
        if r['supersedes_record_id']:
            old = records.get(r['supersedes_record_id'])
            check(old is not None and old['entity_id'] == r['entity_id'] and old['label_version'] < r['label_version'], 'C01', f'{rid} nonmonotonic/dangling supersession')
        if typ in ['notice','opportunity','update']:
            check(bool(r['cohorts']), 'C06', f'{rid} empty cohorts')
        for node in walk(r):
            if 'manifest_entry_id' in node and 'sha256' in node:
                evidence(node, rid)
            if node.get('human_review_ref'):
                check(human(node['human_review_ref']), 'C06', f'{rid} human reference missing')
            if 'utc_value' in node and node['utc_value'] is not None:
                check(bool(node['policy_version']) and human(node['human_review_ref']) and node['precision'] == 'instant', 'C06', f'{rid} unsupported UTC')
        for key in ['proceeding_id','proceeding_ids','notice_ids','opportunity_ids','update_ids','target_opportunity_ids','duplicate_of']:
            refs = payload.get(key) or []
            if isinstance(refs, str):
                refs = [refs]
            check(all(ref in entities for ref in refs), 'C01', f'{rid} dangling {key}')
        if typ == 'opportunity':
            check(any(t['role'] in ['close','hearing_start'] for t in payload['temporal']), 'C06', f'{rid} missing close/hearing_start')
        if typ == 'rejected_candidate' and payload['reason_code'] == 'duplicate':
            check(bool(payload['duplicate_of']) and payload['duplicate_of'] in entities, 'C06', f'{rid} duplicate_of missing')
        for temporal in payload.get('temporal', []):
            if temporal['status'] != 'supported' or temporal['ambiguity']:
                check(any(rid in a['payload']['target_record_ids'] for a in adjudications.values()), 'C06', f'{rid} temporal ambiguity needs human review')
                if not any(t['record_id'] == rid for t in run['temporal_log']):
                    check(False, 'C06', f'{rid} ambiguity missing temporal log')
        if r['unresolved'] or r['review_status'] == 'needs_review':
            incomplete = True
        if typ == 'update':
            reviews = [a for a in adjudications.values() if rid in a['payload']['target_record_ids'] and human(a['record_id'])]
            if not payload['before_evidence']:
                check(bool(payload['before_missing_reason']) and bool(reviews), 'C07', f'{rid} missing-before requires human reason/review')
            if not payload['target_opportunity_ids']:
                check(bool(payload['target_unresolved_reason']) and bool(reviews), 'C07', f'{rid} unresolved update target needs human review')
                incomplete = True
            lo, hi = payload['first_seen_lower'], payload['first_seen_upper']
            check(bool(payload['posting_time']) or bool(lo), 'C07', f'{rid} no posting time or bounded first-seen')
            check(not lo or stamp(lo) <= stamp(hi), 'C07', f'{rid} reversed first-seen interval')
            check(not payload['posting_time'] or stamp(payload['posting_time']) <= stamp(hi), 'C07', f'{rid} posting after first seen')
            obs, vis, latency = payload['observed_at'], payload['visible_at'], payload['review_latency_minutes']
            check(not obs or stamp(hi) <= stamp(obs), 'C07', f'{rid} observed before first seen')
            if obs and vis:
                minutes = (stamp(vis)-stamp(obs)).total_seconds()/60
                check(minutes >= 0 and latency == minutes, 'C07', f'{rid} latency/order mismatch')
            else:
                check(latency is None, 'C07', f'{rid} unmeasured latency must be null')
        if typ == 'adjudication':
            check(human(rid), 'C09', f'{rid} adjudication is not human')
            check(all(t in records or t in entries or t == 'universe' for t in payload['target_record_ids']), 'C01', f'{rid} dangling review target')
            check(stamp(payload['ended_at']) >= stamp(payload['started_at']) and
                  payload['minutes'] <= (stamp(payload['ended_at'])-stamp(payload['started_at'])).total_seconds()/60,
                  'C09', f'{rid} review time invalid')
    # Human reviews must cover differences even when the two passes mint the same entity ID.
    by_entity = {}
    for c in crosswalk.values():
        by_entity.setdefault(c['canonical_entity_id'], {}).setdefault(records[c['record_id']]['phase'], []).append(records[c['record_id']])
    for entity, phases in by_entity.items():
        a = phases.get('pass_A', []); b = phases.get('pass_B', [])
        different = not a or not b or sorted(canonical(r['payload']) for r in a) != sorted(canonical(r['payload']) for r in b)
        if different:
            targets = {r['record_id'] for rows in phases.values() for r in rows}
            check(any(review['payload']['trigger'] in ['disagreement','identity'] and targets <= set(review['payload']['target_record_ids'])
                      for review in adjudications.values()), 'C09', f'{entity} unreviewed pass disagreement')
    final_opportunities = [r for r in labels if r['phase'] == 'adjudicated' and r['record_type'] == 'opportunity']
    if len(final_opportunities) <= 150:
        for opportunity in final_opportunities:
            check(any(opportunity['record_id'] in a['payload']['target_record_ids'] for a in adjudications.values()),
                  'C09', f"{opportunity['record_id']} small-census role/date review missing")
    for ref in run['mandatory_review_refs']:
        check(human(ref), 'C09', f'{ref} mandatory review missing')
    for t in run['temporal_log']:
        check(t['record_id'] in records and (t['human_review_ref'] is None or human(t['human_review_ref'])), 'C06', 'temporal log reference')
    audit = run['audit']; frame = []; covered = []
    check(bool(audit['seed'] and audit['frame_hash']) and audit['frozen_before_seed'],
          'C08', 'audit seed/frame hash/freeze required at final stage')
    coverage = audit['unit_coverage']
    flattened = [eid for members in coverage.values() for eid in members]
    check(set(flattened) == retrieved and len(flattened) == len(set(flattened)) and
          all(uid in entries and uid in members and members for uid, members in coverage.items()),
          'C08', 'audit unit coverage must partition retrieved entries with original anchors')
    check([r['level'] for r in audit['coarsening_history']] == list(range(1,audit['coarsening_level']+1)),
          'C08', 'coarsening steps/recalculations missing or out of order')
    estimate = audit['mandatory_minutes_estimate'] - audit['overlap_minutes']
    for stratum in audit['strata']:
        ids = stratum['unit_ids']; n = len(ids); covered += ids
        check(len(set(ids)) == n and set(ids) <= set(coverage), 'C08', 'audit unit reference/duplicate')
        disposition = []
        risk = []
        for uid in ids:
            members = coverage.get(uid, [])
            if not members or any(eid not in logs[p] for eid in members for p in passes):
                continue
            rows = [logs[p][eid] for eid in members for p in passes]
            d = 'inclusion' if any(r['candidate_count'] for r in rows) else ('exclusions_only' if any(r['rejected_count'] for r in rows) else 'no_candidates')
            disposition.append(d)
            risk.append(d != 'inclusion' or any(entries[eid]['format'] == 'scan_pdf' or entries[eid]['text_layer'] != 'native' for eid in members))
        check(all(d == stratum['disposition'] for d in disposition) and all(r == stratum['high_risk'] for r in risk), 'C08', 'union disposition/risk mismatch')
        unit_entries = [entries[eid] for eid in ids if eid in entries]
        for field in ['source_id','agency_id','process_id','format'] + ([] if audit['coarsening_level'] else ['publication_cycle']):
            check(len({e[field] for e in unit_entries}) <= 1, 'C08', f'{stratum["stratum_id"]} mixed {field} stratum')
        high = stratum['high_risk']; level = audit['coarsening_level']
        required = min(n, (min(20,max(5,math.ceil(.2*n))) if level == 3 else 20)) if high else min(n,max(2 if level >= 2 else 5, math.ceil((.1 if level >= 2 else .2)*n)))
        check(stratum['sample_size'] == required, 'C08', 'audit sample size/coarsening floor')
        sid = stratum['stratum_id']; ranked = sorted(ids, key=lambda uid:(digest(((audit['seed'] or '')+'\n'+sid+'\n'+uid).encode()), uid))
        check(stratum['selected_ids'] == ranked[:required], 'C08', f'{sid} seeded selection mismatch')
        check(set(stratum['selected_ids']) == set(stratum['completed_ids']), 'C08', f'{sid} drawn samples incomplete')
        estimate += required * stratum['minutes_per_unit']
        frame.append({'stratum_id':sid,'unit_ids':sorted(ids),'disposition':stratum['disposition'],'high_risk':high, 'unit_coverage':{uid:coverage[uid] for uid in sorted(ids)}})
    check(re.fullmatch('[a-f0-9]{64}', audit['seed'] or '') is not None and audit['frozen_before_seed'], 'C08', 'invalid seed or unfrozen audit plan')
    audited_targets = {t for a in adjudications.values() if a['payload']['trigger'] == 'random_audit' for t in a['payload']['target_record_ids']}
    check({eid for st in audit['strata'] for eid in st['completed_ids']} <= audited_targets, 'C08', 'completed samples lack human audit log')
    check(set(covered) == set(coverage) and len(covered) == len(set(covered)), 'C08', 'audit frame must cover every retrieved unit exactly once')
    check(digest(canonical(frame)) == audit['frame_hash'], 'C08', 'audit frame hash mismatch')
    actual = sum(a['payload']['minutes'] for a in adjudications.values())
    check(0 <= estimate <= audit.get('review_budget_minutes', 240) and abs(estimate-audit['estimate_minutes']) < .001 and
          actual == audit['actual_minutes'] and actual <= audit.get('review_budget_minutes', 240), 'C08', 'review estimate/actual budget mismatch or budget exceeded')
    verdict = adjudications.get(run['completeness_review_ref'])
    check(verdict is not None and human(run['completeness_review_ref']) and verdict['payload']['trigger'] == 'completeness_verdict', 'C09', 'human completeness verdict missing')
    if verdict:
        decision = verdict['payload']['decision']
        check(decision in ['established','not_established','narrowed'], 'C09', 'invalid completeness decision')
        check(not (incomplete and decision == 'established'), 'C09', 'established forbidden: rights/source/scope/lineage/review gap')
    envelopes = {'WA':2000,'CT':2000,'VA':2000,'TN':4000}
    ledger = index(run['credits'], 'state', 'C10')
    check(set(ledger) == set(envelopes), 'C10', 'shared credit/reviewer ledger requires all four states')
    reserve = 0; total = 0
    check(sum(r['reviewer_minutes'] for r in ledger.values()) <= 960 and
          ledger.get(run['state'], {}).get('reviewer_minutes') == actual and
          all(r['reviewer_minutes'] <= 240 for r in ledger.values()), 'C10', 'shared reviewer minutes mismatch or budget exceeded')
    for state, row in ledger.items():
        check(all(row[k] >= 0 for k in ['reserve_released','actual','outstanding','reviewer_minutes']), 'C10', f'{state} negative ledger amount')
        reserve += row['reserve_released']; total += row['actual'] + row['outstanding']
        check(row['actual'] + row['outstanding'] <= envelopes.get(state,0) + row['reserve_released'], 'C10', f'{state} credit envelope exceeded')
        check(not row['reserve_released'] or bool(row['primary_release_ref']), 'C10', f'{state} reserve lacks primary release')
    check(reserve <= 2000 and total <= 12000, 'C10', 'Phase 1 reserve/total credits exceeded')
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=HOME/'examples')
    parser.add_argument('--verify-bytes', action='store_true')
    parser.add_argument('--stage', choices=['manifest','passes','final'], default='final')
    args = parser.parse_args()
    try:
        errors = validate(args.directory.resolve(), args.verify_bytes, args.stage)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'FAIL input/structure: {exc}')
        return 1
    for error in errors:
        print('FAIL ' + error)
    if errors:
        print(f'{len(errors)} error(s).')
        return 1
    print('PASS cross-record checks ' + ('C01–C03/C10 storage' if args.stage == 'manifest' else 'C01–C05/C10 storage' if args.stage == 'passes' else 'C01–C10') + '; consistency only, not a completeness claim.')
    if not args.verify_bytes:
        print('Storage bytes not checked; real run gates require --verify-bytes.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
