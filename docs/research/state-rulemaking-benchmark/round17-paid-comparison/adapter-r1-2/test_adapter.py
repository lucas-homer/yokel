"""Offline synthetic P3 tests. Never imports a runner, reads R17 source text, or uses a socket.

Run: python3 -I -S -B test_adapter.py
Temporary files are created ONLY under adapter/ and removed after every test.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OUT = HERE / '_out'
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('r17_adapter_tested', HERE / 'r17_adapter.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
SOURCE = 'Operators must file notices.\n'


class FakeClock:
    def __init__(self):
        self.t = 1000
        self.waits = []

    def now(self):
        return self.t

    def wait_until(self, deadline):
        self.waits.append(deadline - 1000)
        self.t = max(self.t, deadline)


class Crash(BaseException):
    pass


def packet(usage, limit=1_730_000_000, reset=None):
    # Decimal JSON is authored as exact text, never via binary floating point.
    def decimal(n):
        return 'null' if n is None else f'{n // 10**9}.{n % 10**9:09d}'
    raw = ('{"usage":' + decimal(usage) + ',"limit":' + decimal(limit) +
           ',"limit_remaining":' + decimal(None if limit is None else limit - usage) +
           ',"limit_reset":' + json.dumps(reset) + '}').encode()
    return dict(fields=raw, response_sha256=a.sha(raw))


class Harness:
    def __init__(self, root):
        self.root = Path(root)
        self.run = self.root / 'run'
        self.run.mkdir()
        self.clock = FakeClock()
        self.posts = []
        self.key_reads = []
        self.queue = [packet(0), packet(10_000_000)]
        self.response = self.good_response()
        self.release_path = self.run / 'RELEASE.json'
        self.build_release()

    def good_response(self):
        plan = a.wire.build(SOURCE, 'opaque')
        value = dict(v=a.wire.VERSION, h=a.sha(SOURCE.encode()), t=a.sha(a.encode(plan['table'])),
                     u=[dict(i=1, k=0, s='Operators must file notices.', m=0, p=0, y=[],
                             d=[], b=[], e=[plan['table']['rows'][0][0]], q=0, r='')],
                     g=[], l=[], z='END')
        content = a.encode(value).decode()
        envelope = dict(model='openai/gpt-6.1-sol', provider='OpenAI',
                        choices=[dict(finish_reason='stop', native_finish_reason='stop',
                                      message=dict(content=content))],
                        usage=dict(prompt_tokens=1000, completion_tokens=1000, total_tokens=2000,
                                   completion_tokens_details=dict(reasoning_tokens=20),
                                   prompt_tokens_details=dict(cached_tokens=10, cache_write_tokens=20)))
        # Insert cost as a JSON numeric token, not a quoted string or float.
        raw = a.encode(envelope).replace(b'"usage":{', b'"usage":{"cost":0.010000000,')
        return dict(status=200, raw=raw, headers={'content-type': 'application/json'})

    def mutate_response(self, fn):
        value = json.loads(self.response['raw'])
        fn(value)
        self.response['raw'] = json.dumps(value, separators=(',', ':')).encode()

    def write(self, path, value):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = value if isinstance(value, bytes) else a.encode(value)
        path.write_bytes(raw)
        return dict(path=path.relative_to(self.root).as_posix(), sha256=a.sha(raw))

    def build_release(self):
        artifacts = {}
        mapping = dict(protocol='PROTOCOL.md', budget='BUDGET.md', reference_spec='REFERENCE-SPEC.md',
                       adjudication_spec='ADJUDICATION-SPEC.md', scorer='fixtures/r17score.py',
                       recon='fixtures/r17recon.py', cases='fixtures/cases.json',
                       cases_src='fixtures/cases.src.json', check='fixtures/check.py')
        design_pins = {}
        for name, filename in mapping.items():
            raw = (a.DESIGN / filename).read_bytes()
            if name == 'budget':
                raw = raw.replace(b'RELEASE_POLICY = UNSET', b'RELEASE_POLICY = P-HARD')
            artifacts[name] = self.write('design/' + filename, raw)
            design_pins[filename] = a.sha(raw)
        artifacts['design_primary'] = self.write('design/READY.primary.json', dict(
            release_policy='P-HARD', sha256=design_pins))
        artifacts['design_ready'] = self.write('design/READY.json', dict(release_policy='P-HARD'))
        for role in ('A1', 'A2'):
            artifacts[role + '_fixture_gate'] = self.write(role + '-gate.json', dict(
                role=role, failures=0, all_gold_packets=True, accepted_by_primary=True,
                cases_sha256=artifacts['cases']['sha256'], check_sha256=artifacts['check']['sha256']))
        src = a.sha(SOURCE.encode())
        source_ids = ['synthetic-001', 'synthetic-002', 'synthetic-003']
        artifacts['sources_ready'] = self.write('sources/READY.json', dict(files={
            s + '/parsed-body.txt': dict(sha256=src) for s in source_ids}))
        ref = self.write('reference/synthetic.json', dict(synthetic=True))
        artifacts['reference_ready'] = self.write('reference/READY.json', dict(
            accepted_by_primary=True, sha256={'synthetic.json': ref['sha256']}))
        manifest = dict(typed_testable=True, sources={f'S{i}': dict(
            source_id=s, source_sha256=src, relations={f'r{j}': False for j in range(4)},
            compounds={f'c{j}': False for j in range(2)}) for i, s in enumerate(source_ids, 1)})
        artifacts['scoring_manifest'] = self.write('manifest.json', manifest)
        document = self.write('run/enforcement-doc.txt', b'synthetic offline documentation')
        review = self.write('run/enforcement-review.txt', b'synthetic offline review')
        artifacts['policy_evidence'] = self.write('run/ENFORCEMENT-EVIDENCE.json', dict(
            accepted_by_primary=True, enforcement='E-1', cross_provider_review_accepted=True,
            documentation=[dict(**document, url='https://invalid.example/offline', retrieved_utc='synthetic')],
            review=review, review_sha256=review['sha256']))
        artifacts['key_attestation'] = self.write('run/KEY-ATTESTATION.json', dict(
            key_label=a.KEY_LABEL, limit=a.recon.KEY_MAX, limit_reset=None, creation_date='synthetic',
            used_only_for_R17=True, release_policy='P-HARD'))
        artifacts['machine_check'] = self.write('run/KEY-MACHINE.json', dict(
            endpoint=a.KEY_URL, documentation_confirmed=True, usage_units='USD', usage_field='usage',
            response_sha256=a.sha(b'synthetic key metadata'), accepted_by_primary=True, usage=0,
            limit=a.recon.KEY_MAX, limit_remaining=a.recon.KEY_MAX, limit_reset=None))
        artifacts['roles_auth'] = self.write('roles.json', dict(authMethod='claude.ai',
            anthropic_api_key_override=False, reference_reviewer='gpt-6-astra', reviewer_provider='codex',
            accepted_by_primary=True))
        artifacts['adapter'] = self.write('adapter/r17_adapter.py', (HERE / 'r17_adapter.py').read_bytes())
        artifacts['tests'] = self.write('adapter/test_adapter.py', Path(__file__).read_bytes())
        artifacts['adapter_ready'] = self.write('adapter/READY.json', dict(
            status='READY_OFFLINE_IMPLEMENTATION', sha256={
                'r17_adapter.py': artifacts['adapter']['sha256'], 'test_adapter.py': artifacts['tests']['sha256']}))
        self.init = dict(type='INIT', namespace=a.NAMESPACE, CAP=a.recon.CAP,
            OPERATING=a.recon.OPERATING, FLOOR=a.recon.FLOOR, KEY_MAX=a.recon.KEY_MAX,
            key_label=a.KEY_LABEL, key_limit=a.recon.KEY_MAX, key_limit_reset=None,
            key_initial_usage=0, release_policy='P-HARD', required_calls=a.CALLS,
            budget_sha256=artifacts['budget']['sha256'], recon_sha256=a.RECON_SHA)
        calls = {}
        for cell in a.CALLS:
            plan = a.wire.build(SOURCE, 'opaque' if cell.endswith('OPQ') else 'full')
            calls[cell] = dict(plan_request_sha256=plan['request_sha256'],
                               dispatched_body_sha256=a.sha(a.dispatched(plan)))
        self.release = dict(schema_version='r17.release.v1', release_policy='P-HARD',
            required_calls=a.CALLS, typed_testable=True, init_sha256=a.sha(a.encode(self.init)),
            model='openai/gpt-6.1-sol', provider='OpenAI', artifacts=artifacts, calls=calls,
            thresholds=dict(N=12, n_s=[4, 4, 4], N_c=6, D2=11, D3_correct=9, D3_acceptable=11,
                            D2_source=[3, 3, 3], T4=6, critical=0, critical_per_source=[0, 0, 0],
                            critical_compounds=0))
        self.save_release()
        self.rewrite_ledger([self.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                           release_sha256=a.sha(self.release_path.read_bytes()))])

    def save_release(self):
        self.release_path.write_bytes(a.encode(self.release))

    def rewrite_ledger(self, entries):
        output = []
        for entry in copy.deepcopy(entries):
            entry.pop('prev_sha256', None)
            if output:
                entry['prev_sha256'] = a.sha(a.encode(output[-1]))
            output.append(entry)
        (self.run / 'ledger.jsonl').write_bytes(b''.join(a.encode(e) + b'\n' for e in output))

    def entries(self):
        return [a.strict(line) for line in (self.run / 'ledger.jsonl').read_bytes().splitlines()]

    def post(self, url, raw):
        assert url == a.POST_URL
        assert self.entries()[-1]['type'] == 'DISPATCH_MARK'
        assert (self.run / 'ledger.lock').exists()
        last = self.entries()[-1]
        folder = self.run / last['attempt_dir']
        assert (folder / 'intent.json').exists()
        assert (folder / 'request.json').read_bytes() == raw
        self.posts.append((url, raw))
        return copy.deepcopy(self.response)

    def key_info(self, url):
        assert url == a.KEY_URL
        self.key_reads.append(self.clock.now())
        value = self.queue.pop(0) if len(self.queue) > 1 else self.queue[0]
        if isinstance(value, Exception):
            raise value
        return value

    def execute(self, cell='S1-OPQ', job='job1', **kwargs):
        return a.execute_once(cell=cell, source=SOURCE, release_path=self.release_path,
            run_root=self.run, attempt_dir=self.run / job, job_id=job, post=self.post,
            key_info=self.key_info, clock=self.clock, artifact_root=self.root, **kwargs)

    def stage(self, phase='opq', state='reachable'):
        entries = [e for e in self.entries() if e['type'] == 'RESOLVE' and e['dispatched']]
        files, calls = {}, {}
        for e in entries:
            cell = e['call']
            adj = {}
            for role in ('A1', 'A2'):
                name = cell + '-' + role + '.json'
                pin = self.write('run/' + name, dict(synthetic=True, cell=cell, role=role))
                files[name] = pin['sha256']
                adj[role + '_sha256'] = pin['sha256']
            calls[cell] = dict(result_sha256=a.sha((self.run / e['attempt_dir'] / 'result.json').read_bytes()), **adj)
        report = dict(outcome=None, state=dict(halted_phase=None, opq=dict(A1='pass', A2='pass')
            if phase == 'full' else dict(A1=state, A2=state), full=dict(A1=state, A2=state)))
        report_pin = self.write('run/scorer-report-' + str(len(entries)) + '.json', report)
        files[Path(report_pin['path']).name] = report_pin['sha256']
        gate = dict(accepted_by_primary=True, release_sha256=a.sha(self.release_path.read_bytes()),
            reference_ready_sha256=self.release['artifacts']['reference_ready']['sha256'],
            calls=calls, files=files, scorer_report_sha256=report_pin['sha256'])
        path = self.run / ('stage-' + str(len(entries)) + '.json')
        path.write_bytes(a.encode(gate))
        return path


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.offline-test-', dir=OUT)
        self.addCleanup(self.temp.cleanup)
        self.h = Harness(self.temp.name)

    def test_success_every_receipt_and_both_hashes(self):
        h = self.h
        with patch.object(a.wire, 'validate_response', wraps=a.wire.validate_response) as validator:
            result = h.execute()
        self.assertEqual(result['state'], 13)
        self.assertIsNone(result['halt'])
        self.assertEqual(result['debit'], a.recon.FLOOR)
        self.assertEqual(len(h.posts), 1)
        folder = h.run / 'job1'
        expected = {'key-preflight.json', 'plan.json', 'request.json', 'span-table.json', 'intent.json',
                    'response.body', 'status.json', 'usage.raw.json', 'content.body', 'expanded.json',
                    'post-checks.json', 'recon-0.intent.json', 'recon-0.json', 'reconciliation.json', 'ledger-snapshot.json',
                    'result.json', 'completed.json'}
        self.assertEqual({p.name for p in folder.iterdir()}, expected)
        plan, body = a.read(folder / 'plan.json'), a.read(folder / 'request.json')
        self.assertEqual(plan['body']['max_tokens'], 8192)
        expected_body = copy.deepcopy(plan['body'])
        expected_body['max_tokens'] = 16384
        self.assertEqual(body, expected_body)
        self.assertEqual(validator.call_args.kwargs['plan'], plan)
        intent = a.read(folder / 'intent.json')
        self.assertNotEqual(intent['plan_request_sha256'], intent['dispatched_body_sha256'])
        self.assertEqual(intent['dispatched_body_sha256'], a.sha(h.posts[0][1]))
        self.assertEqual(intent['guarded_bytes'], len(h.posts[0][1]) + 1024)
        self.assertIn(b'0.010000000', (folder / 'usage.raw.json').read_bytes())
        done = a.read(folder / 'completed.json')
        for filename, pin in done['files'].items():
            self.assertEqual(a.sha((folder / filename).read_bytes()), pin)
        self.assertEqual([e['type'] for e in h.entries()],
                         ['INIT', 'BIND_RELEASE', 'RESERVE', 'DISPATCH_MARK', 'RESOLVE', 'RECONCILED'])

    def test_unset_policy_refused(self):
        self.h.release['release_policy'] = 'UNSET'
        self.h.save_release()
        with self.assertRaisesRegex(a.Refused, 'release_policy_unset'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])

    def test_wrong_cell_order_refused(self):
        with self.assertRaisesRegex(a.Refused, 'wrong_cell_order'):
            self.h.execute('S2-OPQ')
        self.assertEqual(self.h.posts, [])

    def test_unfundable_remaining_calls_admission(self):
        h = self.h
        h.execute()
        entries = h.entries()
        next(e for e in entries if e['type'] == 'RESOLVE')['debit'] = 600_000_000
        h.rewrite_ledger(entries)
        stage = h.stage()
        with self.assertRaisesRegex(a.Refused, 'admission:operating limit'):
            h.execute('S2-OPQ', 'job2', staged_path=stage)
        self.assertEqual(len(h.posts), 1)

    def test_oversize_dispatched_body_zero_debit(self):
        h = self.h
        plan = a.wire.build(SOURCE, 'opaque')
        plan['body']['messages'][0]['content'] += 'x' * 40000
        plan['request_sha256'] = a.sha(a.encode(plan['body']))
        with patch.object(a.wire, 'build', return_value=plan):
            with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
                h.execute()
        self.assertEqual(h.posts, [])
        self.assertEqual(h.entries()[-1]['debit'], 0)
        self.assertFalse(h.entries()[-1]['dispatched'])

    def test_exact_boundary_guard_delta(self):
        body = dict(max_tokens=8192, synthetic='')
        overhead = len(a.encode(body)) + 1024
        body['synthetic'] = 'x' * (40000 - overhead)
        plan = dict(body=body, request_sha256=a.sha(a.encode(body)))
        self.assertEqual(len(a.encode(body)) + 1024, 40000)
        with self.assertRaisesRegex(a.Refused, 'dispatched_body_overflow'):
            a.dispatched(plan)

    def test_mutated_receipt_at_send_boundary(self):
        def tamper(stage, ledger, folder):
            if stage == 'before_mark':
                (folder / 'request.json').write_bytes(b'x' * 40001)
        with self.assertRaises(a.Refused):
            self.h.execute(hook=tamper)
        self.assertEqual(self.h.posts, [])
        self.assertEqual(self.h.entries()[-1]['debit'], 0)

    def test_lag_reconciles_at_60_seconds(self):
        h = self.h
        h.queue = [packet(0), packet(0), packet(10_000_000)]
        result = h.execute()
        self.assertIsNone(result['halt'])
        self.assertEqual(h.key_reads, [1000, 1000, 1060])
        self.assertEqual(h.clock.waits, [0, 60])

    def test_stale_zero_halts_at_900_seconds(self):
        h = self.h
        h.queue = [packet(0)]
        result = h.execute()
        self.assertEqual(result['halt'], 'KEY_USAGE_UNRECONCILED')
        self.assertEqual(h.key_reads, [1000, 1000, 1060, 1300, 1900])
        self.assertEqual(result['debit'], a.recon.FLOOR)
        self.assertEqual(h.entries()[-1]['type'], 'HALT')

    def test_falling_usage_halts_immediately(self):
        h = self.h
        h.queue = [packet(0), packet(9_000_000), packet(8_000_000), packet(10_000_000)]
        result = h.execute()
        self.assertEqual(result['halt'], 'usage regressed or invalid')
        self.assertEqual(h.key_reads, [1000, 1000, 1060])

    def test_limit_changed_halts_immediately(self):
        h = self.h
        h.queue = [packet(0), packet(10_000_000, limit=1_700_000_000)]
        result = h.execute()
        self.assertEqual(result['halt'], 'limit changed, unlimited or resetting')
        self.assertEqual(len(h.key_reads), 2)

    def test_reset_halts_immediately(self):
        h = self.h
        h.queue = [packet(0), packet(10_000_000, reset='daily')]
        self.assertEqual(h.execute()['halt'], 'limit changed, unlimited or resetting')
        self.assertEqual(len(h.key_reads), 2)

    def test_unlimited_halts_immediately(self):
        h = self.h
        h.queue = [packet(0), packet(10_000_000, limit=None)]
        self.assertEqual(h.execute()['halt'], 'limit changed, unlimited or resetting')
        self.assertEqual(len(h.key_reads), 2)

    def test_key_delta_above_floor(self):
        h = self.h
        h.queue = [packet(0), packet(280_000_000)]
        result = h.execute()
        self.assertEqual(result['debit'], 280_000_000)
        self.assertEqual(result['halt'], 'debit_exceeds_floor')

    def test_transport_error_never_retried(self):
        h = self.h
        calls = []
        def failed(url, raw):
            calls.append(url)
            raise OSError('synthetic timeout')
        h.post = failed
        h.queue = [packet(0)]
        result = h.execute()
        self.assertEqual(result['state'], 2)
        self.assertEqual(result['halt'], 'KEY_USAGE_UNRECONCILED')
        self.assertEqual(len(calls), 1)
        with self.assertRaises(a.Refused):
            h.execute(job='job2')
        self.assertEqual(len(calls), 1)

    def test_existing_run_directory_refused(self):
        (self.h.run / 'job1').mkdir()
        with self.assertRaisesRegex(a.Refused, 'existing_run_dir'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])

    def test_existing_stale_lock_is_never_broken(self):
        path = self.h.run / 'ledger.lock'
        path.write_bytes(a.encode(dict(pid=999999999, host='synthetic', started=0, run_id='old')))
        old = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.h.execute()
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(self.h.posts, [])

    def remove_lock_with_evidence(self):
        (self.h.run / 'ledger.lock').unlink()
        path = self.h.run / 'lock-evidence.json'
        path.write_bytes(a.encode(dict(owner_gone=True, evidence='synthetic process exit')))
        return path

    def test_crash_after_reserve_zero_recovery_then_fresh_claim(self):
        h = self.h
        def crash(stage, *_):
            if stage == 'after_reserve':
                raise Crash()
        with self.assertRaises(Crash):
            h.execute(hook=crash)
        self.assertEqual(h.posts, [])
        self.assertEqual(h.entries()[-1]['type'], 'RESERVE')
        evidence = self.remove_lock_with_evidence()
        recovered = a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
        self.assertEqual(recovered, ['S1-OPQ'])
        self.assertEqual(h.entries()[-2]['type'], 'LOCK_RECOVERED')
        self.assertEqual(h.entries()[-1]['debit'], 0)
        self.assertFalse(h.entries()[-1]['dispatched'])
        with self.assertRaisesRegex(a.Refused, 'existing_run_dir'):
            h.execute()
        h.queue = [packet(0), packet(10_000_000)]
        self.assertEqual(h.execute(job='fresh-job')['state'], 13)
        self.assertEqual(len(h.posts), 1)

    def test_crash_after_dispatch_mark_conservative_no_redispatch(self):
        h = self.h
        def crash(url, raw):
            h.posts.append((url, raw))
            raise Crash()
        h.post = crash
        with self.assertRaises(Crash):
            h.execute()
        evidence = self.remove_lock_with_evidence()
        h.queue = [packet(0)]
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
        self.assertEqual(len(h.posts), 1)
        self.assertEqual(h.entries()[-1]['type'], 'HALT')
        self.assertEqual(next(e for e in h.entries() if e['type'] == 'RESOLVE')['debit'], a.recon.FLOOR)
        with self.assertRaises(a.Refused):
            h.execute(job='new')
        self.assertEqual(len(h.posts), 1)

    def test_torn_tail_preserved_and_unresolved_reserve_assumed_dispatched(self):
        h = self.h
        def crash(stage, *_):
            if stage == 'after_reserve':
                raise Crash()
        with self.assertRaises(Crash):
            h.execute(hook=crash)
        (h.run / 'ledger.lock').unlink()
        torn = b'{"type":"DISPATCH_MARK"'
        with (h.run / 'ledger.jsonl').open('ab') as file:
            file.write(torn)
        h.queue = [packet(0)]
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
        self.assertEqual((h.run / ('ledger-torn-' + a.sha(torn) + '.bin')).read_bytes(), torn)
        self.assertIn('RECOVER', [e['type'] for e in h.entries()])
        self.assertEqual(h.entries()[-1]['type'], 'HALT')
        self.assertEqual(h.posts, [])

    def test_invalid_json_torn_tail_recovered(self):
        h = self.h
        with (h.run / 'ledger.jsonl').open('ab') as file:
            file.write(b'{broken}\n')
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
        self.assertEqual(h.entries()[-1]['type'], 'RECOVER')
        self.assertEqual(h.posts, [])

    def test_hash_chain_corruption_refused(self):
        path = self.h.run / 'ledger.jsonl'
        path.write_bytes(path.read_bytes().replace(b'"prev_sha256":"', b'"prev_sha256":"bad'))
        with self.assertRaisesRegex(a.Refused, 'ledger_chain'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])

    def test_directory_fsync_and_dispatch_mark_before_transport(self):
        h = self.h
        events = []
        real_sync, real_dir, real_post = a.os.fsync, a.fsync_dir, h.post
        def sync(fd):
            events.append('file_sync')
            return real_sync(fd)
        def directory(path):
            events.append(('dir_sync', Path(path)))
            return real_dir(path)
        def post(url, raw):
            self.assertEqual(events[-2:], [('dir_sync', h.run), 'file_sync'])
            events.append('POST')
            return real_post(url, raw)
        h.post = post
        with patch.object(a.os, 'fsync', side_effect=sync), patch.object(a, 'fsync_dir', side_effect=directory):
            result = h.execute()
        self.assertEqual(result['state'], 13)
        self.assertEqual(events.count('POST'), 1)
        self.assertGreater(sum(e == ('dir_sync', h.run / 'job1') for e in events), 10)

    def test_next_cell_requires_both_adjudicators(self):
        h = self.h
        h.execute()
        with self.assertRaisesRegex(a.Refused, 'adjudication_pause'):
            h.execute('S2-OPQ', 'job2')
        self.assertEqual(len(h.posts), 1)

    def test_semantic_unreachable_refuses_next_release(self):
        h = self.h
        h.execute()
        stage = h.stage(state='unreachable')
        with self.assertRaisesRegex(a.Refused, 'semantic_futility_stop'):
            h.execute('S2-OPQ', 'job2', staged_path=stage)
        self.assertEqual(len(h.posts), 1)
        self.assertEqual(sum(e['type'] == 'SKIP' for e in h.entries()), 5)

    def test_six_cell_order_requires_frozen_opq_pass(self):
        h = self.h
        for index, cell in enumerate(a.CALLS[:3]):
            stage = h.stage() if index else None
            h.queue = [packet(index * 10_000_000), packet((index + 1) * 10_000_000)]
            self.assertEqual(h.execute(cell, f'job{index + 1}', staged_path=stage)['state'], 13)
        stage = h.stage(phase='full')
        with self.assertRaisesRegex(a.Refused, 'FULL_requires_frozen_OPQ_pass'):
            h.execute('S1-FULL', 'job4', staged_path=stage)
        frozen = h.run / 'OPQ-FROZEN.json'
        frozen.write_bytes(a.encode(dict(accepted_by_primary=True,
            release_sha256=a.sha(h.release_path.read_bytes()), opq=a.read(stage)['calls'])))
        for index, cell in enumerate(a.CALLS[3:], 3):
            stage = h.stage(phase='full')
            h.queue = [packet(index * 10_000_000), packet((index + 1) * 10_000_000)]
            result = h.execute(cell, f'job{index + 1}', staged_path=stage, opq_freeze=frozen)
            self.assertEqual(result['state'], 13)
        self.assertEqual(len(h.posts), 6)
        self.assertEqual(result['aggregate'], 6 * a.recon.FLOOR)
        with self.assertRaises(a.Refused):
            h.execute('S1-OPQ', 'retry', staged_path=stage)
        self.assertEqual(len(h.posts), 6)

    def test_reported_cost_exact_decimal_ceiling(self):
        value = a.strict(b'{"usage":{"cost":0.0000000001,"prompt_tokens":1,"completion_tokens":0}}')
        self.assertEqual(a.recover_terms(value)['reported'], 1)
        self.assertEqual(a.recon.parse_usd('0.0100000000000000001'), 10_000_001)

    def test_cost_recovered_from_error_body(self):
        h = self.h
        h.response = dict(status=400, raw=b'{"error":{"usage":{"cost":0.28,"prompt_tokens":1,"completion_tokens":1}}}', headers={})
        h.queue = [packet(0), packet(280_000_000)]
        result = h.execute()
        self.assertEqual(result['state'], 7)
        self.assertEqual(result['debit'], 280_000_000)
        self.assertEqual(result['halt'], 'debit_exceeds_floor')

    def test_post_checks_use_expected_model_exactly(self):
        self.h.mutate_response(lambda v: v.update(model='openai/gpt-6.1-sol-20260929'))
        result = self.h.execute()
        self.assertEqual(result['state'], 9)
        self.assertIn('AD5', result['checks'])

    def test_release_policy_binding_mismatch(self):
        entries = self.h.entries()
        entries[1]['release_policy'] = 'P-ACCEPT'
        self.h.rewrite_ledger(entries)
        with self.assertRaisesRegex(a.Refused, 'BIND_RELEASE'):
            self.h.execute()

    def test_real_frozen_policy_is_unset(self):
        self.assertEqual(a.read(a.DESIGN / 'READY.primary.json')['release_policy'], 'UNSET')
        self.assertIn('RELEASE_POLICY = UNSET', (a.DESIGN / 'BUDGET.md').read_text())

    def test_fractional_clock_crash_after_resolve_reuses_reads(self):
        h = self.h
        h.clock.t = 1000.375
        def crash(stage, *_):
            if stage == 'after_resolve':
                raise Crash()
        with self.assertRaises(Crash):
            h.execute(hook=crash)
        evidence = self.remove_lock_with_evidence()
        old_reads = list(h.key_reads)
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
        self.assertEqual(h.key_reads, old_reads)
        self.assertEqual(sum(e['type'] == 'RESOLVE' for e in h.entries()), 1)
        self.assertEqual(h.entries()[-1]['type'], 'HALT')
        self.assertEqual(len(h.posts), 1)

    def test_crash_after_reconciled_before_completion_halts(self):
        h = self.h
        def crash(stage, *_):
            if stage == 'after_reconciled':
                raise Crash()
        with self.assertRaises(Crash):
            h.execute(hook=crash)
        evidence = self.remove_lock_with_evidence()
        old_reads = list(h.key_reads)
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
        self.assertEqual(h.key_reads, old_reads)
        self.assertEqual(sum(e['type'] == 'RECONCILED' for e in h.entries()), 1)
        self.assertEqual(h.entries()[-1]['type'], 'HALT')

    def test_crash_during_key_read_consumes_slot_without_retry(self):
        h = self.h
        original = h.key_info
        reads = []
        def key(url):
            reads.append(h.clock.now())
            if len(reads) == 2:
                raise Crash()
            return original(url)
        h.key_info = key
        with self.assertRaises(Crash):
            h.execute()
        evidence = self.remove_lock_with_evidence()
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
        self.assertEqual(reads, [1000, 1000, 1060])
        self.assertEqual(len(h.posts), 1)
        self.assertEqual(h.entries()[-1]['type'], 'HALT')

    def test_torn_tail_with_lock_evidence_records_lock_recovered_first(self):
        h = self.h
        def crash(stage, *_):
            if stage == 'after_reserve':
                raise Crash()
        with self.assertRaises(Crash):
            h.execute(hook=crash)
        evidence = self.remove_lock_with_evidence()
        with (h.run / 'ledger.jsonl').open('ab') as file:
            file.write(b'{broken')
        h.queue = [packet(0)]
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock, lock_evidence=evidence)
        kinds = [e['type'] for e in h.entries()]
        self.assertEqual(kinds[3:5], ['LOCK_RECOVERED', 'RECOVER'])
        self.assertEqual(kinds[-1], 'HALT')

    def test_missing_or_multiple_choices_row8(self):
        h = self.h
        h.mutate_response(lambda v: v.update(choices=[]))
        self.assertEqual(h.execute()['state'], 8)

    def test_unparseable_http200_row8(self):
        h = self.h
        h.response['raw'] = b'{broken'
        h.queue = [packet(0)]
        self.assertEqual(h.execute()['state'], 8)

    def test_nonfinite_cost_row8_and_floor(self):
        h = self.h
        h.response['raw'] = h.response['raw'].replace(b'0.010000000', b'NaN')
        h.queue = [packet(0)]
        result = h.execute()
        self.assertEqual(result['state'], 8)
        self.assertEqual(result['debit'], a.recon.FLOOR)

    def test_pretransport_key_endpoint_error_is_zero_pause(self):
        self.h.queue = [OSError('synthetic metadata failure')]
        with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
            self.h.execute()
        self.assertEqual(self.h.posts, [])
        self.assertEqual(a.read(self.h.run / 'job1/result.json')['debit'], 0)

    def test_key_read_failures_bounded_at_four(self):
        h = self.h
        h.queue = [packet(0), OSError('synthetic metadata failure')]
        result = h.execute()
        self.assertEqual(len(h.key_reads), 5)  # preflight plus four post-response reads
        self.assertEqual(result['halt'], 'KEY_USAGE_UNRECONCILED')

    def test_invalid_key_usage_halts_on_first_read(self):
        h = self.h
        bad = packet(10_000_000)
        bad['fields'] = bad['fields'].replace(b'0.010000000', b'-0.010000000')
        h.queue = [packet(0), bad]
        result = h.execute()
        self.assertEqual(result['halt'], 'usage regressed or invalid')
        self.assertEqual(len(h.key_reads), 2)

    def test_post_request_tampering_is_integrity_halt(self):
        h = self.h
        original = h.post
        def post(url, raw):
            response = original(url, raw)
            (h.run / 'job1/request.json').write_bytes(b'{"tampered":true}')
            return response
        h.post = post
        result = h.execute()
        self.assertEqual(result['state'], 9)
        self.assertIn('POST_INTEGRITY', result['checks'])
        self.assertIsNotNone(result['halt'])

    def test_headroom_mechanical_futility(self):
        h = self.h
        h.mutate_response(lambda v: v['usage'].update(completion_tokens=13927, total_tokens=14927))
        result = h.execute()
        self.assertEqual(result['state'], 13)
        self.assertIsNone(result['halt'])
        self.assertEqual(sum(e['type'] == 'SKIP' for e in h.entries()), 5)
        self.assertTrue(all(e['rule_id'] == 'D5' for e in h.entries() if e['type'] == 'SKIP'))

    def test_p_accept_requires_explicit_acceptance(self):
        h = self.h
        artifacts = h.release['artifacts']
        budget_path = h.root / artifacts['budget']['path']
        artifacts['budget'] = h.write(artifacts['budget']['path'], budget_path.read_bytes().replace(
            b'RELEASE_POLICY = P-HARD', b'RELEASE_POLICY = P-ACCEPT'))
        primary = a.read(h.root / artifacts['design_primary']['path'])
        primary['release_policy'] = 'P-ACCEPT'
        primary['sha256']['BUDGET.md'] = artifacts['budget']['sha256']
        artifacts['design_primary'] = h.write(artifacts['design_primary']['path'], primary)
        artifacts['design_ready'] = h.write(artifacts['design_ready']['path'], dict(release_policy='P-ACCEPT'))
        attestation = a.read(h.root / artifacts['key_attestation']['path'])
        attestation['release_policy'] = 'P-ACCEPT'
        artifacts['key_attestation'] = h.write(artifacts['key_attestation']['path'], attestation)
        artifacts['policy_evidence'] = h.write('run/CAP-ACCEPTANCE.json', dict(
            accepted_by_primary=True, date='synthetic', verbatim_acceptance='synthetic offline statement',
            residual_risk_accepted=True))
        h.init['release_policy'] = h.release['release_policy'] = 'P-ACCEPT'
        h.init['budget_sha256'] = artifacts['budget']['sha256']
        h.release['init_sha256'] = a.sha(a.encode(h.init))
        h.save_release()
        h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-ACCEPT',
                                     release_sha256=a.sha(h.release_path.read_bytes()))])
        self.assertEqual(h.execute()['state'], 13)

    def test_p9_omits_full_and_reserves_only_three_calls(self):
        h = self.h
        artifacts = h.release['artifacts']
        manifest = a.read(h.root / artifacts['scoring_manifest']['path'])
        manifest['typed_testable'] = False
        for source in manifest['sources'].values():
            source['compounds'] = {}
        artifacts['scoring_manifest'] = h.write(artifacts['scoring_manifest']['path'], manifest)
        h.release['typed_testable'] = False
        h.release['required_calls'] = h.init['required_calls'] = a.CALLS[:3]
        h.release['calls'] = {cell: h.release['calls'][cell] for cell in a.CALLS[:3]}
        h.release['thresholds'].update(N_c=0, T4=0)
        h.release['init_sha256'] = a.sha(a.encode(h.init))
        h.save_release()
        h.rewrite_ledger([h.init, dict(type='BIND_RELEASE', release_policy='P-HARD',
                                     release_sha256=a.sha(h.release_path.read_bytes()))])
        for index, cell in enumerate(a.CALLS[:3]):
            gate = h.stage() if index else None
            h.queue = [packet(index * 10_000_000), packet((index + 1) * 10_000_000)]
            result = h.execute(cell, f'p9-{index}', staged_path=gate)
        self.assertEqual(result['aggregate'], 3 * a.recon.FLOOR)
        with self.assertRaises(a.Refused):
            h.execute('S1-FULL', 'not-required')
        self.assertEqual(len(h.posts), 3)

    def test_full_t6_futility_skips_remaining_full_calls(self):
        h = self.h
        for index, cell in enumerate(a.CALLS[:3]):
            gate = h.stage() if index else None
            h.queue = [packet(index * 10_000_000), packet((index + 1) * 10_000_000)]
            h.execute(cell, f't6-{index}', staged_path=gate)
        gate = h.stage(phase='full')
        frozen = h.run / 'OPQ-FROZEN.json'
        frozen.write_bytes(a.encode(dict(accepted_by_primary=True,
            release_sha256=a.sha(h.release_path.read_bytes()), opq=a.read(gate)['calls'])))
        h.mutate_response(lambda v: v['usage'].update(completion_tokens=4501, total_tokens=5501))
        h.queue = [packet(30_000_000), packet(40_000_000)]
        result = h.execute('S1-FULL', 't6-full', staged_path=gate, opq_freeze=frozen)
        self.assertEqual(result['state'], 13)
        skips = [e for e in h.entries() if e['type'] == 'SKIP']
        self.assertEqual([e['call'] for e in skips], ['S2-FULL', 'S3-FULL'])
        self.assertTrue(all(e['rule_id'] == 'T6' for e in skips))

    def test_well_hashed_impossible_ledger_refused(self):
        h = self.h
        h.rewrite_ledger(h.entries() + [dict(type='RESOLVE', call='S1-OPQ', attempt_dir='forged',
                                           dispatched=False, debit=0)])
        with self.assertRaisesRegex(a.Refused, 'ledger_impossible_resolve'):
            h.execute()
        self.assertEqual(h.posts, [])

    def test_plain_text_schema_rejection_still_row6(self):
        h = self.h
        h.response = dict(status=400, raw=b'Unsupported response_format schema', headers={})
        h.queue = [packet(0)]
        result = h.execute()
        self.assertEqual(result['state'], 6)
        self.assertIsNotNone(result['halt'])
        self.assertEqual(len(h.posts), 1)


def response_test(status, expected, error=None):
    def test(self):
        h = self.h
        h.response['status'] = status
        if error:
            h.mutate_response(lambda v: v.update(error=dict(message=error)))
        result = h.execute()
        self.assertEqual(result['state'], expected)
        self.assertIsNotNone(result['halt'])
        self.assertEqual(len(h.posts), 1)
    return test


for status, state, text in [(401, 3, None), (403, 3, None), (402, 4, None), (429, 5, None),
                            (400, 6, 'unsupported response_format schema'), (422, 6, 'invalid parameter'),
                            (400, 7, 'other error'), (404, 7, None), (500, 7, None),
                            (200, 4, 'credit limit exceeded')]:
    setattr(AdapterTests, f'test_http_{status}_row_{state}', response_test(status, state, text))


def anomaly_test(mutation, code):
    def test(self):
        h = self.h
        h.mutate_response(mutation)
        result = h.execute()
        self.assertEqual(result['state'], 9)
        self.assertIn(code, result['checks'])
        self.assertIsNotNone(result['halt'])
        self.assertEqual(len(h.posts), 1)
    return test


for name, mutation, code in [
        ('wrong_model', lambda v: v.update(model='other'), 'AD5'),
        ('wrong_provider', lambda v: v.update(provider='other'), 'AD5'),
        ('missing_provider', lambda v: v.pop('provider'), 'AD5'),
        ('prompt_over_guard', lambda v: v['usage'].update(prompt_tokens=40001), 'AD1'),
        ('completion_over_cap', lambda v: v['usage'].update(completion_tokens=16385), 'AD2'),
        ('boolean_tokens', lambda v: v['usage'].update(prompt_tokens=True), 'AD1'),
        ('reasoning_over_completion', lambda v: v['usage']['completion_tokens_details'].update(reasoning_tokens=1001), 'AD3'),
        ('cache_over_prompt', lambda v: v['usage']['prompt_tokens_details'].update(cached_tokens=1000, cache_write_tokens=1), 'AD3'),
        ('total_mismatch', lambda v: v['usage'].update(total_tokens=1), 'AD3'),
        ('missing_usage', lambda v: v.pop('usage'), 'AD1'),
        ('missing_cost', lambda v: v['usage'].pop('cost'), 'AD4'),
        ('negative_cost', lambda v: v['usage'].update(cost=-1), 'AD4'),
        ('cost_exceeds_rate', lambda v: v['usage'].update(cost=0.02), 'AD4'),
        ('cost_exceeds_floor', lambda v: v['usage'].update(cost=0.28), 'AD4')]:
    setattr(AdapterTests, 'test_anomaly_' + name, anomaly_test(mutation, code))


def arm_failure_test(finish, expected, extra=None):
    def test(self):
        h = self.h
        def mutate(v):
            v['choices'][0]['finish_reason'] = finish
            if extra:
                v['choices'][0]['message'].update(extra)
        h.mutate_response(mutate)
        result = h.execute()
        self.assertEqual(result['state'], expected)
        self.assertIsNone(result['halt'])
        self.assertEqual(sum(e['type'] == 'SKIP' for e in h.entries()), 5)
        self.assertFalse(any(e['type'] == 'HALT' for e in h.entries()))
        with self.assertRaises(a.Refused):
            h.execute('S2-OPQ', 'new')
        self.assertEqual(len(h.posts), 1)
    return test


for name, finish, state, extra in [('non_stop', 'content_filter', 10, None),
    ('truncation', 'length', 11, None), ('refusal', 'stop', 10, dict(refusal='synthetic refusal')),
    ('tool_call', 'stop', 10, dict(tool_calls=[dict(synthetic=True)])),
    ('invalid_wire', 'stop', 12, dict(content='{}'))]:
    setattr(AdapterTests, 'test_arm_failure_' + name, arm_failure_test(finish, state, extra))


class ReferenceLedgerTests(unittest.TestCase):
    """L01–L25 through the adapter's exact imported engine, using pinned fixture expectations."""


primary = a.read(a.DESIGN / 'READY.primary.json')['sha256']
for filename in ('fixtures/check.py', 'fixtures/cases.json', 'fixtures/r17score.py'):
    assert a.sha((a.DESIGN / filename).read_bytes()) == primary[filename]
checker = a.load_pinned('r17_fixture_checker', a.DESIGN / 'fixtures/check.py', primary['fixtures/check.py'])
# Route its pure ledger harness through the adapter's module, not a separate reimplementation.
checker.L = a.recon
cases = json.loads((a.DESIGN / 'fixtures/cases.json').read_bytes())['ledger']['cases']
assert len(cases) == 25
for case in cases:
    def fixture(self, case=case):
        count, failures = checker.run_ledger(dict(ledger=dict(cases=[case])))
        self.assertEqual(count, 1)
        self.assertEqual(failures, [], case['id'])
    setattr(ReferenceLedgerTests, 'test_' + case['id'], fixture)


if __name__ == '__main__':
    unittest.main(verbosity=2)
