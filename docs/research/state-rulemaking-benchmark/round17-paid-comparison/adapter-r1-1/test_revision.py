"""Revision-specific adapter regressions; every source/packet/clock is synthetic."""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('revision_harness', HERE / 'test_adapter.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
a = t.a


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.revision-', dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.h = t.Harness(self.temp.name)

    def load_clean(self):
        ledger = a.Ledger(self.h.run, self.h.clock)
        with ledger.lock('inspect'):
            ledger.load()
        return ledger

    def test_s1_allowlist_receipts(self):
        h = self.h
        h.response['headers'] = {'Authorization': 'Bearer sk-or-synthetic',
            'set-cookie': 'secret-cookie', 'X-Unknown': 'secret-unknown', 'cookie': 'secret',
            'Content-Type': 'application/json', 'X-Request-ID': 'req', 'X-OpenRouter-Request-ID': 'or',
            'OpenAI-Request-ID': 'ai', 'X-RateLimit-Remaining': '3', 'date': 'synthetic',
            'x-openai-request-id': 'Bearer sk-or-synthetic', 'x-ratelimit-reset': 'x' * 1500}
        h.execute()
        headers = a.read(h.run / 'job1/status.json')['headers']
        self.assertEqual(set(headers), {'content-type', 'x-request-id', 'x-openrouter-request-id',
            'openai-request-id', 'x-ratelimit-remaining', 'date', 'x-ratelimit-reset'})
        self.assertEqual(len(headers['x-ratelimit-reset']), 1024)
        for p in (h.run / 'job1').iterdir():
            raw = p.read_bytes()
            for secret in (b'sk-or-synthetic', b'secret-cookie', b'secret-unknown', b'set-cookie'):
                self.assertNotIn(secret, raw)

    def test_s2_interleaving_exactly_one_post_clean_chain(self):
        h = self.h
        real_gate = a.staged_gate
        calls = 0
        def interleave(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                (h.run / 'ledger.lock').unlink()  # simulate the review's forbidden operator action
                a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
                h.queue = [t.packet(0), t.packet(10_000_000)]
                h.execute(job='second')
                (h.run / 'ledger.lock').write_bytes(b'{}')
            return real_gate(*args, **kwargs)
        with patch.object(a, 'staged_gate', interleave):
            with self.assertRaises(a.Refused):
                h.execute(job='first')
        self.assertEqual(len(h.posts), 1)
        self.load_clean()

    def test_s2_every_append_checks_size(self):
        h = self.h
        lg = a.Ledger(h.run, h.clock)
        with lg.lock('test'):
            lg.load()
            with lg.path.open('ab') as f:
                f.write(b' ')
            with self.assertRaisesRegex(a.Refused, 'ledger_tail_changed'):
                lg.append('HALT', reason='test')

    def test_s2_same_size_tail_mutation_detected(self):
        lg = a.Ledger(self.h.run, self.h.clock)
        with lg.lock('test'):
            lg.load()
            raw = lg.path.read_bytes().replace(b'BIND_RELEASE', b'BIND_RELEASX')
            lg.path.write_bytes(raw)
            with self.assertRaisesRegex(a.Refused, 'ledger_tail_changed'):
                lg.append('HALT', reason='test')

    def test_s3_changed_gate_resolves_zero_then_fresh_dispatch(self):
        h = self.h
        h.execute()
        gate = h.stage()
        def swap(stage, *_):
            if stage == 'before_mark':
                h.stage(state='unreachable')
        h.queue = [t.packet(10_000_000)]
        with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
            h.execute('S2-OPQ', 'second', staged_path=gate, hook=swap)
        self.assertEqual(len(h.posts), 1)
        self.assertFalse(any(e['type'] == 'SKIP' for e in h.entries()))
        self.assertFalse(h.entries()[-1]['dispatched'])
        reserve = next(e for e in h.entries() if e['type'] == 'RESERVE' and e['call'] == 'S2-OPQ')
        self.assertIsNotNone(reserve['staged_gate_sha256'])
        self.load_clean()
        self.assertEqual(a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock), [])
        gate = h.stage()
        h.queue = [t.packet(10_000_000), t.packet(20_000_000)]
        self.assertEqual(h.execute('S2-OPQ', 'third', staged_path=gate)['state'], 13)
        self.assertEqual(len(h.posts), 2)

    def test_s3_stopped_gate_cannot_append_skip_while_pending(self):
        h = self.h
        h.execute()
        gate = h.stage(state='unreachable')
        lg = a.Ledger(h.run, h.clock)
        with lg.lock('test'):
            lg.load()
            lg.append('RESERVE', call='S2-OPQ', job_id='second', attempt_dir='second', floor=a.recon.FLOOR)
            before = lg.path.read_bytes()
            with self.assertRaisesRegex(a.Refused, 'staged_gate_changed'):
                a.staged_gate(lg, 'S2-OPQ', a.sha(h.release_path.read_bytes()),
                              h.release['artifacts']['reference_ready']['sha256'], gate)
            self.assertEqual(before, lg.path.read_bytes())

    def crash_after_completion_gap(self):
        h = self.h
        real_put = a.put
        def crash(path, value):
            if Path(path).name == 'completed.json':
                raise t.Crash()
            return real_put(path, value)
        with patch.object(a, 'put', crash):
            with self.assertRaises(t.Crash):
                h.execute()
        (h.run / 'ledger.lock').unlink()  # synthetic crash, no live owner

    def test_n1_incomplete_receipt_blocks_next_then_terminal_recovery(self):
        self.crash_after_completion_gap()
        h = self.h
        with self.assertRaisesRegex(a.Refused, 'recovery_required'):
            h.execute('S2-OPQ', 'second', staged_path=h.stage())
        self.assertEqual(len(h.posts), 1)
        self.assertEqual(a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock), ['S1-OPQ'])
        self.assertEqual(h.entries()[-1]['type'], 'HALT')

    def test_n1_valid_json_incomplete_final_is_not_completion(self):
        self.h.execute()
        (self.h.run / 'job1/completed.json').write_bytes(b'{}')
        with self.assertRaisesRegex(a.Refused, 'recovery_required'):
            self.h.execute('S2-OPQ', 'second', staged_path=self.h.stage())
        self.assertEqual(len(self.h.posts), 1)

    def test_n2_mark_fsync_failure_recoverable_floor_no_post(self):
        h = self.h
        real = a.os.fsync
        fired = False
        def fail(fd):
            nonlocal fired
            if not fired and b'"type":"DISPATCH_MARK"' in (h.run / 'ledger.jsonl').read_bytes().splitlines()[-1]:
                fired = True
                raise OSError('synthetic durability failure')
            return real(fd)
        with patch.object(a.os, 'fsync', fail):
            with self.assertRaisesRegex(a.Refused, 'recovery_required'):
                h.execute()
        self.assertEqual(h.posts, [])
        self.load_clean()
        h.queue = [t.packet(0)]
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
        resolved = next(e for e in h.entries() if e['type'] == 'RESOLVE')
        self.assertTrue(resolved['dispatched'])
        self.assertGreaterEqual(resolved['debit'], a.recon.FLOOR)
        before = (h.run / 'ledger.jsonl').read_bytes()
        self.assertEqual(a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock), [])
        self.assertEqual(before, (h.run / 'ledger.jsonl').read_bytes())

    def test_n3_normally_halted_recovery_no_new_reads_or_halts(self):
        h = self.h
        h.queue = [t.packet(0)]
        h.execute()
        before, reads = (h.run / 'ledger.jsonl').read_bytes(), len(h.key_reads)
        for _ in range(2):
            self.assertEqual(a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock), [])
        self.assertEqual(before, (h.run / 'ledger.jsonl').read_bytes())
        self.assertEqual(reads, len(h.key_reads))
        self.assertFalse((h.run / 'job1/recovered.json').exists())

    def test_n4_torn_receipt_consumes_slot_preserves_bytes(self):
        h = self.h
        def crash(stage, *_):
            if stage == 'after_resolve':
                raise t.Crash()
        with self.assertRaises(t.Crash):
            h.execute(hook=crash)
        (h.run / 'ledger.lock').unlink()
        path = h.run / 'job1/recon-0.json'
        raw = path.read_bytes()[:20]
        path.write_bytes(raw)
        reads = len(h.key_reads)
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
        self.assertEqual(len(h.key_reads) - reads, 1)
        self.assertEqual(path.with_name(path.name + '.torn-' + a.sha(raw) + '.bin').read_bytes(), raw)
        self.assertTrue(a.read(path)['recovered_read_uncertain'])
        self.load_clean()

    def test_n4_torn_status_recovered(self):
        h = self.h
        def crash(stage, *_):
            if stage == 'after_resolve':
                raise t.Crash()
        with self.assertRaises(t.Crash):
            h.execute(hook=crash)
        (h.run / 'ledger.lock').unlink()
        (h.run / 'job1/status.json').write_bytes(b'{"resolved_at":')
        a.recover(run_root=h.run, key_info=h.key_info, clock=h.clock)
        self.assertTrue(list((h.run / 'job1').glob('status.json.torn-*.bin')))
        self.load_clean()

    def test_n5_no_negative_sleep(self):
        with patch.object(a.time, 'time', side_effect=[100, 160.5, 160.5]), patch.object(a.time, 'sleep') as sleep:
            a.Clock().wait_until(160)
        self.assertTrue(all(c.args[0] >= 0 for c in sleep.call_args_list))

    def test_n8_size_checked_before_parser(self):
        h = self.h
        h.response['raw'] = b' ' * (a.MAX_RAW + 1)
        real = a.strict
        def guarded(raw):
            self.assertLessEqual(len(raw), a.MAX_RAW)
            return real(raw)
        with patch.object(a, 'strict', guarded):
            result = h.execute()
        self.assertEqual(result['state'], 8)
        self.assertGreaterEqual(result['debit'], a.recon.FLOOR)

    def test_n9_utf16_body_row8_not_unexpected_failure(self):
        h = self.h
        h.response['raw'] = h.response['raw'].decode().encode('utf-16')
        result = h.execute()
        self.assertEqual(result['state'], 8)
        self.assertEqual(result['halt'], 'KEY_USAGE_UNRECONCILED')
        self.assertFalse((h.run / 'job1/unexpected-halt.json').exists())

    def test_malformed_transport_packets_row2(self):
        for packet in ({}, {'status': '200', 'raw': b'{}', 'headers': {}},
                       {'status': 200, 'raw': '{}', 'headers': {}},
                       {'status': 200, 'raw': b'{}', 'headers': []}, None):
            with self.subTest(packet=packet), tempfile.TemporaryDirectory(dir=HERE) as d:
                h = t.Harness(d)
                h.response = packet
                result = h.execute()
                self.assertEqual(result['state'], 2)
                self.assertEqual(len(h.posts), 1)


class MainTests(unittest.TestCase):
    setUp = RevisionTests.setUp
    def cli(self, recover_first=False, change_release=None, before=None, **overrides):
        h = self.h
        path = h.root / 'driver.py'
        path.write_bytes(b'def source(cell): return "synthetic"\n'
                         b'def post_once(url, body): return {}\n'
                         b'def key_info(url): return {}\n')
        pin = a.sha(path.read_bytes())
        h.release['driver_sha256'] = pin
        h.release['artifacts']['host_driver'] = dict(path='driver.py', sha256=pin)
        if change_release:
            change_release(h.release)
        h.save_release()
        entries = h.entries()
        entries[1]['release_sha256'] = a.sha(h.release_path.read_bytes())
        h.rewrite_ledger(entries)
        if before:
            before()
        driver = types.SimpleNamespace(source=lambda cell: t.SOURCE, post_once=h.post, key_info=h.key_info)
        driver.__dict__.update(overrides)
        args = ['--cell', 'S1-OPQ', '--release', str(h.release_path), '--run-root', str(h.run),
                '--attempt-dir', str(h.run / 'cli-job'), '--job-id', 'cli-job',
                '--driver', str(path), '--driver-sha256', pin]
        out, err = io.StringIO(), io.StringIO()
        real_execute = a.execute_once
        def execute(**kwargs):
            kwargs['artifact_root'] = h.root
            kwargs['clock'] = h.clock
            return real_execute(**kwargs)
        def load(name, path, expected):
            pinned_load(name, path, expected)  # exercise verified-byte compile on the synthetic driver
            return driver
        pinned_load = a.load_pinned
        with patch.object(a, 'BENCH', h.root), patch.object(a, 'load_pinned', load), \
             patch.object(a, 'execute_once', execute), patch.object(a, 'Clock', lambda: h.clock), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = a.main(args, recover_first=recover_first)
        return code, out.getvalue(), err.getvalue()

    def test_main_success_one_cell(self):
        code, out, err = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(a.strict(out)['state'], 13)
        self.assertEqual(err, '')
        self.assertEqual(len(self.h.posts), 1)

    def test_main_lock_vs_refusal(self):
        (self.h.run / 'ledger.lock').write_bytes(b'synthetic owner')
        code, out, err = self.cli()
        self.assertEqual(code, 3)
        self.assertIn('lock/claim exists', err)
        self.assertEqual(out, '')
        self.assertEqual((self.h.run / 'ledger.lock').read_bytes(), b'synthetic owner')
        (self.h.run / 'ledger.lock').unlink()
        with patch.object(a.sys, 'flags', types.SimpleNamespace(isolated=0, no_site=1)):
            code, _, err = self.cli()
        self.assertEqual(code, 2)
        self.assertIn('python_flags', err)

    def test_main_driver_exports_refused(self):
        code, _, err = self.cli(post_once=None)
        self.assertEqual(code, 2)
        self.assertIn('driver_exports', err)
        self.assertEqual(self.h.key_reads, [])

    def test_main_exception_text_not_printed(self):
        def source(_):
            raise RuntimeError('Bearer sk-or-SYNTHETIC-NEVER-PRINT')
        code, out, err = self.cli(source=source)
        self.assertEqual(code, 4)
        self.assertNotIn('sk-or-', out + err)

    def test_main_driver_release_pin_refused(self):
        code, _, err = self.cli(change_release=lambda r: r.update(driver_sha256='0' * 64))
        self.assertEqual(code, 2)
        self.assertIn('driver_release_pin', err)
        self.assertEqual(self.h.key_reads, [])

    def test_main_driver_signed_artifact_mismatch_refused(self):
        def change(r):
            r['artifacts']['host_driver']['sha256'] = '0' * 64
        code, _, err = self.cli(change_release=change)
        self.assertEqual(code, 2)
        self.assertEqual(self.h.key_reads, [])

    def test_main_unset_policy_refused_before_source_or_callbacks(self):
        code, _, err = self.cli(change_release=lambda r: r.update(release_policy='UNSET'),
                               source=lambda _: self.fail('source read before release'))
        self.assertEqual(code, 2)
        self.assertIn('release_policy_unset', err)
        self.assertEqual(self.h.key_reads, [])

    def pending(self, marked=False):
        def crash(stage, *_):
            if stage == ('after_resolve' if marked else 'after_reserve'):
                raise t.Crash()
        with self.assertRaises(t.Crash):
            self.h.execute(hook=crash)
        (self.h.run / 'ledger.lock').unlink()  # simulate recorded owner-death, never a live lock
        self.h.queue = [t.packet(0), t.packet(10_000_000)] if not marked else [t.packet(10_000_000)]

    def test_main_pending_refused_without_recover_first(self):
        code, _, err = self.cli(before=lambda: self.pending(),
                               source=lambda _: self.fail('source read before recovery'))
        self.assertEqual(code, 2)
        self.assertIn('recovery_required', err)
        self.assertEqual(self.h.posts, [])

    def test_main_unmarked_recovered_first_then_one_post(self):
        code, _, err = self.cli(before=lambda: self.pending(), recover_first=True)
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(len(self.h.posts), 1)
        resolves = [e for e in self.h.entries() if e['type'] == 'RESOLVE']
        self.assertEqual([e['dispatched'] for e in resolves], [False, True])

    def test_main_marked_recovered_first_then_refused_without_source_or_post(self):
        code, _, err = self.cli(before=lambda: self.pending(marked=True), recover_first=True,
                               source=lambda _: self.fail('source read after terminal recovery'))
        self.assertEqual(code, 2)
        self.assertEqual(len(self.h.posts), 1)
        self.assertEqual(self.h.entries()[-1]['type'], 'HALT')

if __name__ == '__main__':
    unittest.main(verbosity=2)
