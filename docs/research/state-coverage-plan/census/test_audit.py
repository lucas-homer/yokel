"""Offline audit-freeze regression tests; no real capture store or network access."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch

HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(HOME))


def module(name):
    spec = importlib.util.spec_from_file_location(name, HOME / (name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


freeze = module('audit_freeze')
validator = module('validate')


def fixture():
    manifest, completion = [], []
    for prefix, n, accepts in [('u', 20, True), ('r', 30, False)]:
        for i in range(n):
            uid = f'{prefix}{i:02}'
            manifest.append({'entry_id': uid, 'source_id': 'source', 'agency_id': 'agency',
                             'process_id': 'process', 'kind': 'page', 'format': 'text_pdf',
                             'text_layer': 'native', 'publication_cycle': f'cycle-{i%2}',
                             'retrieval': {'result': 'retrieved', 'sha256': 'a'*64},
                             'accounting': {'pagination_or_page_range': 'pages 1–2'},
                             'expected': {'selector': 'whole notice'}})
            completion.extend({'pass': p, 'manifest_entry_id': uid,
                               'candidate_count': int(accepts and p == 'pass_B'),
                               'rejected_count': int(not accepts)}
                              for p in ('pass_A', 'pass_B'))
    return manifest, completion


class AuditTests(unittest.TestCase):
    def test_freeze_before_entropy_reproduce_and_refuse_redraw(self):
        manifest, completion = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            run_path = directory/'run.json'
            original = '{\n    "state": "XX",\n    "audit": {"seed": null},\n    "untouched": [1,  2]\n}\n'
            run_path.write_text(original)
            for name, rows in [('manifest', manifest), ('completion', completion)]:
                (directory/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            argv = ['audit_freeze.py', str(directory), '--level', '3',
                    '--minutes-native', '2', '--minutes-scan', '3', '--mandatory', '10']

            def entropy(n):
                frozen = json.loads(run_path.read_text())['audit']
                self.assertEqual(n, 32)
                self.assertIsNone(frozen['seed'])
                self.assertTrue(frozen['frozen_before_seed'])
                self.assertEqual(frozen['frame_hash'], freeze.digest(freeze.canonical(freeze.frame(frozen))))
                self.assertTrue(all(not s['selected_ids'] for s in frozen['strata']))
                return 'b'*64

            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex', side_effect=entropy) as random:
                with contextlib.redirect_stdout(io.StringIO()):
                    freeze.main()
                random.assert_called_once()
            written = run_path.read_text()
            self.assertTrue(written.startswith('{\n    "state": "XX",\n    "audit": {\n        '))
            self.assertTrue(written.endswith(',\n    "untouched": [1,  2]\n}\n'))
            audit = json.loads(written)['audit']
            self.assertEqual(audit['actual_minutes'], 0)
            self.assertEqual(audit['estimate_minutes'], 26)
            self.assertEqual(len(audit['unit_coverage']), 50)
            for s in audit['strata']:
                sid = s['stratum_id']
                ranked = sorted(s['unit_ids'], key=lambda uid: (
                    hashlib.sha256(('b'*64+'\n'+sid+'\n'+uid).encode()).hexdigest(), uid))
                self.assertEqual(s['selected_ids'], ranked[:s['sample_size']])
                self.assertEqual(s['sample_size'], 2 if s['disposition'] == 'inclusion' else 6)
                self.assertEqual(s['completed_ids'], [])
            reproduced = copy.deepcopy(audit)
            for s in reproduced['strata']:
                s['selected_ids'] = []
            freeze.select(reproduced)
            self.assertEqual(reproduced, audit)
            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as random:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    freeze.main()
                random.assert_not_called()
            self.assertEqual(run_path.read_text(), written)

    def test_risk_and_coarsening_floors(self):
        self.assertEqual([freeze.required(100, True, n) for n in range(4)], [20]*4)
        self.assertEqual([freeze.required(30, True, n) for n in range(4)], [20, 20, 20, 6])
        self.assertEqual([freeze.required(30, False, n) for n in range(4)], [6, 6, 3, 3])
        self.assertEqual(freeze.required(2, True, 3), 2)
        manifest, completion = fixture()
        manifest[0]['text_layer'] = 'partial'
        strata = freeze.build_strata(manifest, completion, 3, 2, 3)
        scan = next(s for s in strata if 'u00' in s['unit_ids'])
        self.assertTrue(scan['high_risk'])
        self.assertEqual(scan['minutes_per_unit'], 3)
        self.assertEqual(scan['sample_size'], 1)

    def test_fixed_allocation_risk_reserve_lower_bounds_and_ties(self):
        def strata(spec):
            return [{'stratum_id': sid, 'unit_ids': [f'{sid}-{i}' for i in range(n)],
                     'high_risk': high} for sid, n, high in spec]
        rows = strata([('h-a', 90, True), ('h-b', 10, True),
                       ('o-a', 90, False), ('o-b', 9, False), ('o-c', 1, False)])
        expected = {'h-a': 11, 'h-b': 1, 'o-a': 15, 'o-b': 2, 'o-c': 1}
        self.assertEqual(freeze.fixed_allocation(rows), expected)
        self.assertEqual(freeze.fixed_allocation(list(reversed(rows))), expected)
        ties = strata([(f'h-{i:02}', 1, True) for i in range(20)] + [('ordinary', 100, False)])
        result = freeze.fixed_allocation(ties)
        self.assertEqual([result[f'h-{i:02}'] for i in range(20)], [1]*12+[0]*8)
        self.assertEqual(result['ordinary'], 18)
        for spec in ([('h', 2, True), ('o', 100, False)],
                     [('h', 100, True), ('o', 2, False)],
                     [('h', 2, True), ('o', 1, False)], [], [('only', 50, True)]):
            rows = strata(spec)
            result = freeze.fixed_allocation(rows)
            self.assertEqual(sum(result.values()), min(30, sum(n for _, n, _ in spec)))
            self.assertTrue(all(0 <= result[sid] <= n for sid, n, _ in spec))
        with self.assertRaises(ValueError):
            freeze.fixed_allocation(rows, 29)

    def test_fixed_plan_and_validator_reproduction_reject_bad_size_and_ranking(self):
        manifest, completion = fixture()
        audit, scenarios = freeze.plan(manifest, completion, 1, 2, 3, 10, 240,
                                       method='fixed_sample_v1')
        self.assertEqual(audit['method'], 'fixed_sample_v1')
        self.assertEqual(audit['sample_total'], 30)
        self.assertEqual(sum(s['sample_size'] for s in audit['strata']), 30)
        self.assertEqual({s['high_risk']: s['sample_size'] for s in audit['strata']},
                         {True: 12, False: 18})
        audit['seed'] = 'c'*64
        freeze.select(audit)
        for s in audit['strata']:
            ranked = sorted(s['unit_ids'], key=lambda uid: (
                hashlib.sha256(('c'*64+'\n'+s['stratum_id']+'\n'+uid).encode()).hexdigest(), uid))
            self.assertEqual(s['selected_ids'], ranked[:s['sample_size']])

        # Exercise C08 in a complete final fixture, not just the allocator helper.
        path = HOME/'examples/run.json'
        original_load = validator.load
        run = copy.deepcopy(original_load(path))
        run['audit'].update(method='fixed_sample_v1', sample_total=30, frozen_at='2026-10-17T00:00:00Z')
        with patch.object(validator, 'load', side_effect=lambda p: run if p == path else original_load(p)), \
             patch.object(validator, 'validate_containers', return_value=[]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validator.validate(HOME/'examples'), [])
            run['audit']['strata'][0]['sample_size'] = 0
            with contextlib.redirect_stdout(io.StringIO()):
                errors = validator.validate(HOME/'examples')
            self.assertTrue(any('C08: audit sample size' in e for e in errors), errors)
            run['audit']['strata'][0]['sample_size'] = 1
            run['audit']['strata'][0]['selected_ids'] = []
            with contextlib.redirect_stdout(io.StringIO()):
                errors = validator.validate(HOME/'examples')
            self.assertTrue(any('seeded selection mismatch' in e for e in errors), errors)

    def test_va_proposed_allocation_reproduces_in_c08_without_mutating_run(self):
        directory = HOME/'VA'
        path = directory/'run.json'
        before = path.read_bytes()
        run = json.loads(before)
        costing = json.loads((directory/'reconcile/audit-estimate.json').read_text())['costings']['fixed_sample_v1']
        manifest = freeze.lines(directory/'manifest.jsonl')
        coverage = freeze.paired_coverage(manifest, 1)
        strata = freeze.build_strata(manifest, freeze.lines(directory/'completion.jsonl'), 1, 1, 1, coverage)
        allocation = freeze.fixed_allocation(strata)
        self.assertEqual(allocation, {s['stratum_id']: s['sample_size'] for s in costing['strata']})
        self.assertEqual(coverage, costing['unit_coverage'])
        costs = {s['stratum_id']: s['minutes_per_unit'] for s in costing['strata']}
        for s in strata:
            s.update(sample_size=allocation[s['stratum_id']], minutes_per_unit=costs[s['stratum_id']])
        # Fixed literal is a synthetic test seed, never a real entropy draw or persisted plan.
        audit = run['audit']
        for key in ('costing_file', 'costing_sha256'):
            audit.pop(key, None)
        audit.update(method='fixed_sample_v1', sample_total=30, strata=strata, unit_coverage=coverage,
                     coarsening_level=1, coarsening_history=[{'level': 1, 'estimate_minutes': costing['total_minutes'],
                     'reason': 'Synthetic C08 regression only'}], seed='d'*64, frozen_before_seed=True,
                     frozen_at='2026-10-17T00:00:00Z', mandatory_minutes_estimate=costing['mandatory_minutes'],
                     estimate_minutes=costing['total_minutes'], review_budget_minutes=360)
        audit['frame_hash'] = freeze.digest(freeze.canonical(freeze.frame(audit)))
        freeze.select(audit)
        for s in strata:
            s['completed_ids'] = list(s['selected_ids'])
        original_load = validator.load
        with patch.object(validator, 'load', side_effect=lambda p: run if p == path else original_load(p)), \
             patch.object(validator, 'validate_containers', return_value=[]):
            with contextlib.redirect_stdout(io.StringIO()):
                errors = validator.validate(directory)
            c08 = [e for e in errors if e.startswith('C08:')]
            # Completion logs and budget remain required: A1 must not weaken either.
            self.assertEqual(set(c08), {
                'C08: completed samples lack human audit log',
                'C08: review estimate/actual budget mismatch or budget exceeded'})
            sampled = next(s for s in strata if s['sample_size'] > 1)
            sampled['sample_size'] -= 1
            with contextlib.redirect_stdout(io.StringIO()):
                errors = validator.validate(directory)
            self.assertTrue(any('C08: audit sample size' in e for e in errors), errors)
            sampled['sample_size'] += 1
            sampled['selected_ids'].reverse()
            with contextlib.redirect_stdout(io.StringIO()):
                errors = validator.validate(directory)
            self.assertTrue(any('seeded selection mismatch' in e for e in errors), errors)
        self.assertEqual(path.read_bytes(), before)

    def test_stratified_floor_default_and_ct_frozen_sample_unchanged(self):
        manifest, completion = fixture()
        default, _ = freeze.plan(manifest, completion, 3, 2, 3, 10, 240)
        explicit, _ = freeze.plan(manifest, completion, 3, 2, 3, 10, 240,
                                  method='stratified_floor')
        self.assertEqual(default, explicit)
        self.assertNotIn('method', default)
        schema = json.loads((HOME/'run.schema.json').read_text())['properties']['audit']
        self.assertEqual(schema['properties']['method']['default'], 'stratified_floor')
        self.assertFalse(schema['additionalProperties'])
        ct = HOME/'CT'
        before = (ct/'run.json').read_bytes()
        audit = json.loads(before)['audit']
        self.assertEqual(audit.get('method', 'stratified_floor'), 'stratified_floor')
        for s in audit['strata']:
            self.assertEqual(s['sample_size'], freeze.required(len(s['unit_ids']), s['high_risk'],
                                                               audit['coarsening_level']))
        reproduced = copy.deepcopy(audit)
        freeze.select(reproduced)
        self.assertEqual(reproduced, audit)
        self.assertEqual(freeze.digest(freeze.canonical(freeze.frame(audit))), audit['frame_hash'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validator.validate(ct, stage='passes', verify_bytes=True), [])
        self.assertEqual((ct/'run.json').read_bytes(), before)

    def test_fixed_cli_dry_run_never_uses_entropy_or_writes(self):
        manifest, completion = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'run.json').write_text(json.dumps({'state': 'VA', 'audit': {'seed': None}}))
            for name, rows in [('manifest', manifest), ('completion', completion)]:
                (directory/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            argv = ['audit_freeze.py', str(directory), '--level', '1', '--method', 'fixed_sample_v1',
                    '--sample-total', '30', '--high-risk-share', '0.4', '--minutes-native', '2',
                    '--minutes-scan', '3', '--mandatory', '10', '--dry-run']
            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as entropy:
                with contextlib.redirect_stdout(io.StringIO()):
                    freeze.main()
                entropy.assert_not_called()
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before)
            # Even a null-seed, already-frozen frame must not be replaced.
            (directory/'run.json').write_text(json.dumps({'state': 'VA', 'audit': {
                'seed': None, 'frozen_before_seed': True}}))
            with patch.object(sys, 'argv', argv[:-1]), patch.object(freeze.secrets, 'token_hex') as entropy:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    freeze.main()
                entropy.assert_not_called()

    def test_container_frames_freeze_before_entropy_nested_draws_and_c08_tampering(self):
        manifest, completion = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            reconcile = directory/'reconcile'
            reconcile.mkdir()
            run_path = directory/'run.json'
            run_path.write_text(json.dumps({'state': 'VA', 'audit': {'seed': None}}, indent=2))
            for name, rows in [('manifest', manifest), ('completion', completion)]:
                (directory/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            rows = []
            for entry in manifest:
                for n in range(1, 11):
                    rows.append({'container_id': entry['entry_id'], 'item_ordinal': n,
                                 'item_kind': 'guidance_catalogue_row' if n == 10 else 'notice',
                                 'accounting_status': 'accounted' if n <= 7 else 'unaccounted',
                                 'union_record_id': f'label-{n}' if n <= 7 else None,
                                 'item_frame_status': 'resolved', 'complete_item': n != 10,
                                 'source_entry_id': entry['entry_id'], 'source_locator': f'Full original item {n}',
                                 'native_text_fingerprint': 'e'*64, 'doc_numbers': []})
            crosswalk_path = reconcile/'container-crosswalk.jsonl'
            crosswalk_path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            argv = ['audit_freeze.py', str(directory), '--level', '1', '--method', 'fixed_sample_v1',
                    '--sample-total', '30', '--high-risk-share', '0.4', '--minutes-native', '2',
                    '--minutes-scan', '3', '--mandatory', '10']
            def entropy(n):
                frozen = json.loads(run_path.read_text())['audit']
                frames = json.loads((reconcile/'container-frames.json').read_text())
                self.assertIsNone(frozen['seed'])
                self.assertTrue(frozen['frozen_before_seed'])
                self.assertEqual(frozen['container_selections'], {})
                self.assertEqual(frozen['container_frame_hash'], freeze.digest(freeze.canonical(frames)))
                self.assertEqual(len(frames['containers']), 50)
                self.assertTrue(frozen['frozen_at'])
                return 'b'*64
            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex', side_effect=entropy) as random:
                with contextlib.redirect_stdout(io.StringIO()):
                    freeze.main()
                random.assert_called_once_with(32)
            run = json.loads(run_path.read_text())
            self.assertEqual(validator.validate_a1_plan(directory, run, manifest), [])
            selected = run['audit']['container_selections']
            self.assertEqual(len(selected), 30)
            for cid, choice in selected.items():
                self.assertEqual(choice['unaccounted_row_ids'], [f'{cid}:{i}' for i in (8, 9, 10)])
                expected = sorted([f'{cid}:{i}' for i in range(1, 8)], key=lambda rid: (
                    hashlib.sha256(('b'*64+'\ncontainer-accounted\n'+cid+'\n'+rid).encode()).hexdigest(), rid))[:5]
                self.assertEqual(choice['accounted_row_ids'], expected)
                expected_item = min([f'{cid}:{i}' for i in range(1, 10)], key=lambda rid: (
                    hashlib.sha256(('b'*64+'\ncontainer-item\n'+cid+'\n'+rid).encode()).hexdigest(), rid))
                self.assertEqual(choice['item_id'], expected_item)
            original = copy.deepcopy(run)
            cid = next(iter(selected))
            for field, value in [('unaccounted_row_ids', []), ('accounted_row_ids', []), ('item_id', f'{cid}:10')]:
                bad = copy.deepcopy(original)
                bad['audit']['container_selections'][cid][field] = value
                self.assertTrue(any('nested selections mismatch' in e for e in
                                    validator.validate_a1_plan(directory, bad, manifest)))
            artifact = reconcile/'container-frames.json'
            frames = json.loads(artifact.read_text())
            frames['containers'][cid]['rows'].reverse()
            artifact.write_text(json.dumps(frames))
            errors = validator.validate_a1_plan(directory, original, manifest)
            self.assertTrue(any('frame hash mismatch' in e for e in errors), errors)
            self.assertTrue(any('do not reproduce' in e for e in errors), errors)
            # A redraw remains impossible even with nested artifacts present.
            before = run_path.read_bytes()
            with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as random:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    freeze.main()
                random.assert_not_called()
            self.assertEqual(run_path.read_bytes(), before)
            note = (reconcile/'AUDIT-SAMPLE.md').read_text()
            self.assertIn('Total unaccounted rows to review: 90', note)
            self.assertIn('hearing-request', note)

    def test_c08_final_and_passes_validate_nested_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'state'
            shutil.copytree(HOME/'examples', directory)
            run = json.loads((directory/'run.json').read_text())
            manifest = freeze.lines(directory/'manifest.jsonl')
            rows = [{'container_id': e['entry_id'], 'item_ordinal': 1, 'item_kind': 'notice',
                     'accounting_status': 'unaccounted', 'union_record_id': None,
                     'item_frame_status': 'resolved', 'complete_item': True,
                     'source_entry_id': e['entry_id'], 'source_locator': 'complete original item',
                     'native_text_fingerprint': 'f'*64, 'doc_numbers': []}
                    for e in manifest if e['retrieval']['result'] == 'retrieved']
            frames = freeze.build_frames(rows, manifest)
            reconcile = directory/'reconcile'
            reconcile.mkdir(exist_ok=True)
            (reconcile/'container-crosswalk.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            (reconcile/'container-frames.json').write_text(json.dumps(frames))
            run['audit'].update(method='fixed_sample_v1', sample_total=30,
                frozen_at='2026-10-17T00:00:00Z', container_frame_hash=freeze.digest(freeze.canonical(frames)))
            run['audit']['container_selections'] = freeze.nested_selections(run['audit'], frames)
            (directory/'run.json').write_text(json.dumps(run))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validator.validate(directory), [])
                self.assertEqual(validator.validate(directory, stage='passes'), [])
            first = next(iter(run['audit']['container_selections'].values()))
            first['unaccounted_row_ids'] = []
            (directory/'run.json').write_text(json.dumps(run))
            for stage in ('passes', 'final'):
                with contextlib.redirect_stdout(io.StringIO()):
                    errors = validator.validate(directory, stage=stage)
                self.assertTrue(any(e.startswith('C08:') and 'nested selections' in e for e in errors), errors)

    def test_unresolved_duplicate_and_empty_container_frames_refuse_before_seed(self):
        manifest, completion = fixture()
        base = {'container_id': 'u00', 'item_ordinal': 1, 'item_kind': 'notice',
                'accounting_status': 'unaccounted', 'union_record_id': None,
                'item_frame_status': 'resolved', 'complete_item': True,
                'source_entry_id': 'u00', 'source_locator': 'complete original item',
                'native_text_fingerprint': 'f'*64, 'doc_numbers': []}
        for changes in ({'item_frame_status': 'unresolved'}, {'complete_item': False},
                        {'source_locator': None}, {'item_ordinal': 2}):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                (directory/'reconcile').mkdir()
                run_path = directory/'run.json'
                run_path.write_text(json.dumps({'state': 'VA', 'audit': {'seed': None}}))
                (directory/'manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in manifest))
                (directory/'completion.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in completion))
                (directory/'reconcile/container-crosswalk.jsonl').write_text(json.dumps({**base, **changes})+'\n')
                before = run_path.read_bytes()
                argv = ['audit_freeze.py', str(directory), '--level', '1', '--method', 'fixed_sample_v1',
                        '--minutes-native', '2', '--minutes-scan', '3', '--mandatory', '10']
                with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as random:
                    with self.assertRaises(ValueError):
                        freeze.main()
                    random.assert_not_called()
                self.assertEqual(run_path.read_bytes(), before)
                self.assertFalse((directory/'reconcile/container-frames.json').exists())

    def test_ms_bulletin_wire_format_and_fail_closed(self):
        crosswalk = module('container_crosswalk')
        row = 'Agency~False~1/1/2026~~~~Rule~Purpose~12345~00012345a.pdf~Not Found~00012345b.pdf'
        self.assertEqual(crosswalk.ms_bulletin_rows({'d': row+'|1|0'}), [('12345', row)])
        self.assertEqual(crosswalk.ms_bulletin_rows({'d': '|0|0'}), [])
        for payload in ({'rows': []}, {'d': []}, {'d': row+'|2|0'},
                        {'d': row+'|1|1'}, {'d': row+'^'+row+'|2|0'},
                        {'d': row.replace('~12345~', '~bad~')+'|1|0'},
                        {'d': row.replace('00012345a', '00054321a')+'|1|0'},
                        {'d': row.replace('~Purpose', '')+'|1|0'}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                crosswalk.ms_bulletin_rows(payload)

    def test_ms_crosswalk_union_identity_gaps_and_full_original_fallbacks(self):
        crosswalk = module('container_crosswalk')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            inputs = directory/'inputs'
            inputs.mkdir()
            manifest = {}
            def entry(uid, kind, fmt, data, **extra):
                (inputs/uid).write_bytes(data)
                manifest[uid] = {'entry_id': uid, 'kind': kind, 'format': fmt,
                    'original_path': uid, 'source_id': 'ms-sos-bulletin-service',
                    'retrieval': {'result': 'retrieved', 'sha256': hashlib.sha256(data).hexdigest()}, **extra}
            def wire(number):
                return f'Agency~False~1/1/2026~~~~Rule mentions 99999~Purpose~{number}~{int(number):08}a.pdf~Not Found~Not Found'
            entry('ms-slice-test', 'portal_slice', 'json',
                  json.dumps({'d': '^'.join(wire(n) for n in ('12345', '12346', '12347', '12348', '99999'))+'|5|0'}).encode())
            entry('ms-slice-empty', 'portal_slice', 'json', b'{"d":"|0|0"}')
            entry('ms-xchk-mdeq-regulations-page', 'index', 'html', b'<h2>Rules</h2><a>Two notices</a>')
            for number in ('12345', '12346', '12347'):
                entry('ms-form-'+number, 'attachment', 'scan_pdf', b'%PDF fixture')
            def label(rid, kind, number=None, evidence=None, source='ms-sos-acproposed'):
                return {'record_id': rid, 'entity_id': rid, 'record_type': kind, 'payload': {},
                    'aliases': [{'source_id': source, 'native_id': number}] if number else [],
                    'evidence': [{'manifest_entry_id': evidence}] if evidence else []}
            a = [label('accepted', 'notice', '99999', evidence='ms-form-12345'), label('rejected', 'rejected_candidate', '12346'),
                 label('wrong-source', 'notice', '12347', source='unrelated'),
                 label('whole-page', 'rejected_candidate', evidence='ms-xchk-mdeq-regulations-page')]
            b = [label('conflict', 'rejected_candidate', evidence='ms-form-12345'),
                 label('empty', 'rejected_candidate', evidence='ms-slice-empty')]
            for side, records in (('A', a), ('B', b)):
                (directory/f'pass-{side}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            rows = crosswalk.ms_rows(directory, inputs, manifest)
            listing = [r for r in rows if r['container_id'] == 'ms-slice-test']
            self.assertEqual([r['accounting_status'] for r in listing],
                             ['accounted', 'accounted', 'unaccounted', 'unaccounted', 'unaccounted'])
            self.assertTrue(listing[0]['accept_reject_conflict'])
            self.assertEqual(listing[0]['union_record_id'], 'accepted')
            self.assertEqual(listing[1]['union_label_matches'][0]['disposition'], 'rejected')
            self.assertEqual(listing[0]['source_entry_id'], 'ms-form-12345')
            self.assertTrue(listing[2]['complete_item'])
            self.assertFalse(listing[3]['complete_item'])
            agency = next(r for r in rows if r['container_id'] == 'ms-xchk-mdeq-regulations-page')
            self.assertEqual(agency['accounting_status'], 'unaccounted')
            self.assertTrue(agency['complete_item'])
            self.assertIn('full original', agency['source_locator'])
            empty = next(r for r in rows if r['container_id'] == 'ms-slice-empty')
            self.assertEqual(empty['item_kind'], 'empty_listing_verification')
            self.assertEqual(empty['union_record_id'], 'empty')
            self.assertTrue(empty['complete_item'])
            self.assertNotIn('Purpose', json.dumps(rows))
            frames = freeze.build_frames(rows, list(manifest.values()))
            self.assertEqual(len(frames['containers']), 3)
            (directory/'run.json').write_text(json.dumps({'state': 'MS'}))
            (directory/'manifest.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in manifest.values()))
            (inputs/'manifest.pass.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in manifest.values()))
            self.assertEqual(crosswalk.build_rows(directory, inputs), rows)
            entry('unknown', 'index', 'html', b'<p>Unknown format</p>')
            with self.assertRaisesRegex(ValueError, 'unsupported MS container'):
                crosswalk.ms_rows(directory, inputs, manifest)

    def test_ms_costed_dry_run_budget_stop_without_entropy_or_writes(self):
        directory = HOME/'MS'
        cost_path = directory/'reconcile/audit-estimate.json'
        cost = json.loads(cost_path.read_text())
        paths = [directory/'run.json', directory/'reconcile/container-crosswalk.jsonl', cost_path]
        before = {p: p.read_bytes() for p in paths}
        frozen_outputs = {p: p.exists() for p in (directory/'reconcile/container-frames.json',
                                                  directory/'reconcile/AUDIT-SAMPLE.md')}
        argv = ['audit_freeze.py', str(directory), '--level', '3', '--method', 'fixed_sample_v1',
                '--sample-total', '30', '--high-risk-share', '0.4', '--minutes-native', '2',
                '--minutes-scan', '3', '--mandatory', '270', '--costing-file', str(cost_path),
                '--review-budget', '10000', '--dry-run']
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as entropy:
            with contextlib.redirect_stdout(output):
                freeze.main()
            entropy.assert_not_called()
        scenarios = json.loads(output.getvalue())
        for actual, expected in zip(scenarios, cost['coarsening_history']):
            self.assertEqual(actual['audit_minutes'], expected['audit_minutes'])
            self.assertEqual(actual['estimate_minutes'], expected['total_minutes'])
            self.assertEqual(actual['sample'], 30)
        argv[argv.index('--review-budget')+1] = '360'
        with patch.object(sys, 'argv', argv), patch.object(freeze.secrets, 'token_hex') as entropy:
            with self.assertRaisesRegex(ValueError, 'exceeds budget 360; stop/narrow'):
                freeze.main()
            entropy.assert_not_called()
        self.assertEqual({p: p.read_bytes() for p in paths}, before)
        self.assertEqual({p: p.exists() for p in frozen_outputs}, frozen_outputs)
        # Diagnostic dry runs also remain read-only after the owner freezes MS.
        audit_before = json.loads(before[directory/'run.json'])['audit']
        audit_after = json.loads((directory/'run.json').read_text())['audit']
        self.assertEqual(audit_after['frozen_before_seed'], audit_before['frozen_before_seed'])
        self.assertEqual(audit_after['seed'], audit_before['seed'])

    def test_validator_default_budget_and_explicit_override(self):
        # Use only the synthetic example, with real C08 validation of estimate AND actual.
        original_load = validator.load
        run_path = HOME/'examples'/'run.json'
        original_run = original_load(run_path)
        for actual_overrun in (False, True):
            run = copy.deepcopy(original_run)
            if actual_overrun:
                run['audit']['actual_minutes'] = 241
            else:
                run['audit']['mandatory_minutes_estimate'] = 235
                run['audit']['estimate_minutes'] = 241

            def load(path):
                return run if path == run_path else original_load(path)

            original_lines = validator.lines

            def lines(path):
                rows = original_lines(path)
                if actual_overrun and path.name == 'adjudications.jsonl':
                    rows = copy.deepcopy(rows)
                    rows[0]['payload']['minutes'] += 211
                return rows

            with patch.object(validator, 'load', side_effect=load), patch.object(validator, 'lines', side_effect=lines):
                with contextlib.redirect_stdout(io.StringIO()):
                    errors = validator.validate(HOME/'examples')
                self.assertTrue(any(e.startswith('C08: review estimate/actual budget') for e in errors), errors)
                run['audit']['review_budget_minutes'] = 600
                with contextlib.redirect_stdout(io.StringIO()):
                    errors = validator.validate(HOME/'examples')
                self.assertFalse(any(e.startswith('C08:') for e in errors), errors)
                # C10's separate shared-ledger limit is intentionally outside this change.


if __name__ == '__main__':
    unittest.main()
