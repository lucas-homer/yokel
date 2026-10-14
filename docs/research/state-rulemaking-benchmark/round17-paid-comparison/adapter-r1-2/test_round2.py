"""Targeted round-2 regressions: real http.client over fake sockets; synthetic keys only."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import ssl
import tempfile
import traceback
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OUT = HERE / '_out'
OUT.mkdir(exist_ok=True)

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

f = load('round2_fake', 'fake_http.py')
r = load('round2_revision', 'test_revision.py')
a, t = r.a, r.t
d = load('round2_driver', 'host_driver.py')
KEY = f.SYNTHETIC_KEY


class WireTests(unittest.TestCase):
    def setUp(self):
        self.env = f.FakeEnv()
        self.addCleanup(patch.stopall)
        patch.object(d.os, 'environ', self.env).start()

    def transport(self, sockets):
        tr = f.Transport(sockets)
        patch.object(d.http.client, 'HTTPSConnection', tr.cls).start()
        return tr

    def call(self, sock):
        tr = self.transport([sock])
        result = d.post_once(d.POST_URL, b'{ "exact" : 1.00 }')
        return tr, result

    def assert_clean(self, exc):
        self.assertNotIn(KEY, repr(exc.args))
        self.assertIsNone(exc.__context__)
        self.assertIsNone(exc.__cause__)
        tb = exc.__traceback__
        names = []
        while tb:
            if tb.tb_frame.f_globals.get('__file__') == d.__file__:
                names.append(tb.tb_frame.f_code.co_name)
                for name in ('key', 'headers', 'connection', 'response', 'raw', 'safe_headers'):
                    if name == 'raw' and tb.tb_frame.f_code.co_name != '_request':
                        continue
                    self.assertNotIn(name, tb.tb_frame.f_locals)
                self.assertNotIn(KEY, repr(tb.tb_frame.f_locals))
            tb = tb.tb_next
        self.assertIn('_request', names)

    def test_s4_900_second_silent_response_exact_single_post(self):
        # No wait: the fake peer models 300 seconds of silence at getresponse().
        sock = f.FakeSocket(f.http_response(preamble=b'HTTP/1.1 100 Continue\r\n\r\n'))
        tr = self.transport([sock])
        original = sock.makefile
        def delayed(*args, **kwargs):
            if tr.connections[0].timeout < 300:
                raise TimeoutError(KEY)
            return original(*args, **kwargs)
        sock.makefile = delayed
        body = b'{ "exact" : 1.00 }'
        result = d.post_once(d.POST_URL, body)
        self.assertEqual(tr.hosts, [('openrouter.ai', 443, 900)])
        head, wire_body = tr.wire()[0].split(b'\r\n\r\n', 1)
        self.assertEqual(wire_body, body)
        self.assertEqual(head.count(b'POST '), 1)
        self.assertEqual(head.lower().count(b'content-length:'), 1)
        self.assertEqual(head.lower().count(b'host:'), 1)
        self.assertNotIn(b'transfer-encoding:', head.lower())
        self.assertEqual(result['status'], 200)
        self.assertTrue(sock.closed)

    def test_s4_timeout_and_disconnect_never_resend_no_secret_frames(self):
        for phase in ('send', 'read', 'disconnect', 'tls'):
            with self.subTest(phase=phase):
                sock = f.FakeSocket(f.http_response(),
                    fail_send=TimeoutError(KEY) if phase == 'send' else None,
                    fail_read=TimeoutError(KEY) if phase == 'read' else None)
                if phase == 'disconnect':
                    sock.response = b''
                tr = self.transport([sock])
                cm = patch.object(d, '_tls_context', side_effect=RuntimeError(KEY)) if phase == 'tls' else contextlib.nullcontext()
                with cm:
                    try:
                        d.post_once(d.POST_URL, b'{}')
                    except d.DriverError as exc:
                        self.assert_clean(exc)
                    else:
                        self.fail('expected transport refusal')
                self.assertLessEqual(len(tr.connections), 1)
                self.assertLessEqual(sum(w.count(b'POST ') for w in tr.wire()), 1)
                if phase != 'tls':
                    self.assertTrue(sock.closed)

    def test_n16_interrupts_scrub_frames_and_keep_baseexception(self):
        for interrupt in (KeyboardInterrupt(KEY), SystemExit(KEY), BaseException(KEY)):
            with self.subTest(kind=type(interrupt).__name__):
                sock = f.FakeSocket(f.http_response(), fail_send=interrupt)
                tr = self.transport([sock])
                try:
                    d.post_once(d.POST_URL, b'{}')
                except BaseException as exc:
                    self.assertIs(type(exc), type(interrupt))
                    self.assert_clean(exc)
                    self.assertNotIn(KEY, ''.join(traceback.format_exception(exc)))
                else:
                    self.fail('expected interrupt')
                self.assertEqual(len(tr.connections), 1)
                self.assertTrue(sock.closed)

    def test_n16_key_get_failure_scrubs_callback_frame(self):
        self.transport([f.FakeSocket(b'', fail_send=RuntimeError(KEY))])
        try:
            d.key_info(d.KEY_URL)
        except d.DriverError as exc:
            self.assert_clean(exc)
        else:
            self.fail('expected refusal')

    def test_n20_whitespace_and_all_ascii_controls_refused_before_connect(self):
        tr = self.transport([])
        bad = [' ' + KEY, KEY + ' ', KEY + '\n', KEY + '\t', KEY[:4] + ' ' + KEY[4:]]
        bad += [KEY + chr(i) for i in (*range(32), 127)]
        for key in bad:
            with self.subTest(code=ord(key[-1])):
                self.env['OPENROUTER_API_KEY'] = key
                for callback, args in ((d.post_once, (d.POST_URL, b'{}')), (d.key_info, (d.KEY_URL,))):
                    try:
                        callback(*args)
                    except d.DriverError as exc:
                        self.assert_clean(exc)
                    else:
                        self.fail('invalid key accepted')
        self.assertEqual(tr.connections, [])

    def test_n14_explicit_cafile_verified_hash_and_env_ignored(self):
        self.env.update(SSL_CERT_FILE='/synthetic/untrusted.pem', SSL_CERT_DIR='/synthetic',
                        SSLKEYLOGFILE='/synthetic/log')
        with patch.object(d.ssl.SSLContext, 'load_default_certs', side_effect=AssertionError('default roots')):
            tr, packet = self.call(f.FakeSocket(f.http_response()))
        ctx = tr.contexts[0]
        self.assertGreater(ctx.cert_store_stats()['x509_ca'], 0)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertIsNone(ctx.keylog_filename)
        self.assertEqual(packet['tls_ca_sha256'], hashlib.sha256(d.CA_BUNDLE.read_bytes()).hexdigest())
        self.assertEqual(self.env.reads, ['OPENROUTER_API_KEY'])

    def test_n14_missing_bundle_and_zero_anchors_refuse_before_connection(self):
        tr = self.transport([])
        with patch.object(d, 'CA_BUNDLE', OUT / 'missing-bundle.pem'):
            with self.assertRaises(d.DriverError):
                d.post_once(d.POST_URL, b'{}')
        empty = types.SimpleNamespace(load_verify_locations=lambda **kw: None,
                                      cert_store_stats=lambda: {'x509_ca': 0})
        with patch.object(d.ssl, 'SSLContext', return_value=empty):
            with self.assertRaisesRegex(d.DriverError, 'tls_no_trust_anchors'):
                d._tls_context()
            with self.assertRaises(d.DriverError):
                d.post_once(d.POST_URL, b'{}')
        self.assertEqual(tr.connections, [])

    def test_n14_exact_explicit_cafile_argument(self):
        calls = []
        ctx = types.SimpleNamespace(load_verify_locations=lambda **kw: calls.append(kw),
            cert_store_stats=lambda: {'x509_ca': 1}, verify_mode=ssl.CERT_REQUIRED, check_hostname=True)
        tr = self.transport([f.FakeSocket(f.http_response())])
        with patch.object(d.ssl, 'SSLContext', return_value=ctx):
            d.post_once(d.POST_URL, b'{}')
        self.assertEqual(calls, [{'cafile': '/etc/ssl/cert.pem'}])
        self.assertIs(tr.contexts[0], ctx)

    def test_n21_redirects_and_bounded_chunked_close_delimited_bodies(self):
        for kwargs in ({'status': 307, 'headers': [('Location', 'https://synthetic.invalid')]},
                       {'chunked': True}, {'content_length': False}):
            with self.subTest(kwargs=kwargs):
                tr, packet = self.call(f.FakeSocket(f.http_response(body=b'{}', **kwargs)))
                self.assertEqual(packet['raw'], b'{}')
                self.assertNotIn('location', packet['headers'])
                self.assertEqual(len(tr.connections), 1)
        for kwargs in ({'chunked': True}, {'content_length': False}, {}):
            sock = f.FakeSocket(f.http_response(body=b'x' * (d.MAX_RAW + 1), **kwargs))
            tr = self.transport([sock])
            with self.assertRaises(d.DriverError):
                d.post_once(d.POST_URL, b'{}')
            self.assertEqual(len(tr.connections), 1)
            self.assertTrue(sock.closed)
            self.assertLessEqual(max(n for reader in sock.files for n in reader.read_calls), d.MAX_RAW + 1)

    def test_n14_bundle_hash_in_success_and_failure_receipts(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory(dir=OUT) as tmp:
                h = t.Harness(tmp)
                key0 = b'{"data":' + t.packet(0)['fields'] + b'}'
                key1 = b'{"data":' + t.packet(10_000_000)['fields'] + b'}'
                sockets = [f.FakeSocket(f.http_response(body=key0)),
                    f.FakeSocket(f.http_response(body=h.response['raw']),
                        fail_read=TimeoutError(KEY) if fail else None)]
                sockets += [f.FakeSocket(f.http_response(body=key0 if fail else key1)) for _ in range(4 if fail else 1)]
                tr = self.transport(sockets)
                h.post, h.key_info = d.post_once, d.key_info
                result = h.execute()
                self.assertEqual(result['state'], 2 if fail else 13)
                self.assertEqual(sum(w.count(b'POST ') for w in tr.wire()), 1)
                want = hashlib.sha256(d.CA_BUNDLE.read_bytes()).hexdigest()
                for file in ('key-preflight.json', 'status.json', 'recon-0.json'):
                    self.assertEqual(a.read(h.run / 'job1' / file)['tls_ca_sha256'], want)
                for path in h.run.rglob('*'):
                    if path.is_file():
                        self.assertNotIn(KEY.encode(), path.read_bytes())

    def test_n14_bundle_hash_retained_on_invalid_key_get_receipts(self):
        want = hashlib.sha256(d.CA_BUNDLE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            h = t.Harness(tmp)
            self.transport([f.FakeSocket(f.http_response(body=b'{}'))])
            h.post, h.key_info = d.post_once, d.key_info
            with self.assertRaisesRegex(a.Refused, 'pre_dispatch_pause'):
                h.execute()
            self.assertEqual(a.read(h.run / 'job1/result.json')['tls_ca_sha256'], want)
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            h = t.Harness(tmp)
            key0 = b'{"data":' + t.packet(0)['fields'] + b'}'
            self.transport([f.FakeSocket(f.http_response(body=key0)),
                f.FakeSocket(f.http_response(body=h.response['raw']))] +
                [f.FakeSocket(f.http_response(body=b'{}')) for _ in range(4)])
            h.post, h.key_info = d.post_once, d.key_info
            h.execute()
            for due in a.recon.READ_SCHEDULE_S:
                receipt = a.read(h.run / 'job1' / f'recon-{due}.json')
                self.assertTrue(receipt['read_failed'])
                self.assertEqual(receipt['tls_ca_sha256'], want)


class RecoveryTests(unittest.TestCase):
    setUp = r.RevisionTests.setUp
    cli = r.MainTests.cli

    def evidence(self, **changes):
        evidence = dict(owner_gone=True, pid=7654321, host=a.socket.gethostname(), lock_sha256='a' * 64)
        evidence.update(changes)
        path = self.h.root / 'LOCK-EVIDENCE.json'
        path.write_bytes(a.encode(evidence))
        return path

    def pending(self, marked=False):
        if marked:
            original = self.h.post
            def interrupted_post(url, body):
                original(url, body)
                raise t.Crash()
            self.h.post = interrupted_post
        def crash(stage, *_):
            if not marked and stage == 'after_reserve':
                raise t.Crash()
        with self.assertRaises(t.Crash):
            self.h.execute(hook=crash)
        lock = self.h.run / 'ledger.lock'
        digest = a.sha(lock.read_bytes())
        lock.unlink()  # simulated operator records and removes a proven-dead synthetic lock
        return self.evidence(lock_sha256=digest)

    def test_s5_unmarked_cli_recovery_returns_without_source_or_post(self):
        evidence = self.pending()
        with patch.object(a.os, 'kill', side_effect=ProcessLookupError) as kill:
            code, out, err = self.cli(extra_args=['--lock-evidence', str(evidence)],
                source=lambda _: self.fail('source called'), post_once=lambda *_: self.fail('POST called'))
        self.assertEqual((code, err), (0, ''))
        self.assertIn('no dispatch', out)
        kill.assert_called_once_with(7654321, 0)
        self.assertEqual([e['type'] for e in self.h.entries()][-2:], ['LOCK_RECOVERED', 'RESOLVE'])
        self.assertEqual(self.h.entries()[-2]['evidence_sha256'], a.sha(evidence.read_bytes()))
        self.assertEqual(self.h.posts, [])

    def test_s5_marked_cli_recovery_floor_halt_no_post(self):
        evidence = self.pending(marked=True)
        self.h.queue = [t.packet(0)] * 4
        with patch.object(a.os, 'kill', side_effect=ProcessLookupError):
            code, _, err = self.cli(extra_args=['--lock-evidence', str(evidence)],
                source=lambda _: self.fail('source called'), post_once=lambda *_: self.fail('POST called'))
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(len(self.h.posts), 1)
        entries = self.h.entries()
        self.assertEqual(entries[-1]['type'], 'HALT')
        resolve = next(e for e in entries if e['type'] == 'RESOLVE')
        self.assertTrue(resolve['dispatched'])
        self.assertGreaterEqual(resolve['debit'], a.recon.FLOOR)
        self.assertEqual(len(self.h.key_reads), 5)  # preflight plus four reconciliation GETs

    def test_s5_existing_lock_preserved(self):
        evidence = self.evidence()
        lock = self.h.run / 'ledger.lock'
        lock.write_bytes(b'synthetic owner')
        with patch.object(a.os, 'kill') as kill:
            code, _, _ = self.cli(extra_args=['--lock-evidence', str(evidence)])
        self.assertEqual(code, 2)
        self.assertEqual(lock.read_bytes(), b'synthetic owner')
        kill.assert_not_called()

    def test_s5_live_pid_permission_denied_and_unknown_error_refused(self):
        evidence = self.evidence()
        for error in (None, PermissionError(), OSError('synthetic')):
            with self.subTest(error=type(error).__name__), patch.object(a.os, 'kill', side_effect=error):
                before = self.h.entries()
                code, _, err = self.cli(extra_args=['--lock-evidence', str(evidence)])
                self.assertEqual(code, 2)
                self.assertIn('lock_recovery_owner_alive', err)
                self.assertEqual([e['type'] for e in self.h.entries()], [e['type'] for e in before])
                self.assertEqual(self.h.key_reads, [])

    def test_s5_invalid_or_foreign_evidence_refused_before_pid_check(self):
        for change in ({'owner_gone': False}, {'host': 'synthetic-foreign-host'}, {'pid': 0},
                       {'pid': True}, {'pid': '7654321'}, {'lock_sha256': 'bad'}, {'lock_sha256': None}):
            with self.subTest(change=change), patch.object(a.os, 'kill') as kill:
                evidence = self.evidence(**change)
                code, _, err = self.cli(extra_args=['--lock-evidence', str(evidence)])
                self.assertEqual(code, 2)
                self.assertIn('lock_recovery_evidence', err)
                kill.assert_not_called()

    def test_n18_safe_admission_reason_printed(self):
        with patch.object(a.recon, 'admit', return_value=(False, 'halted')):
            code, _, err = self.cli()
        self.assertEqual(code, 2)
        self.assertIn('admission:halted', err)
        with patch.object(a.recon, 'admit', return_value=(False, KEY)):
            code, _, err = self.cli()
        self.assertEqual(code, 2)
        self.assertNotIn(KEY, err)
        self.assertIn('gate_refused', err)


class CliTests(unittest.TestCase):
    def test_n15_renamed_driver_uses_actual_filename_and_pin(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            path = Path(tmp) / 'reviewed-host-driver.py'
            path.write_bytes((HERE / 'host_driver.py').read_bytes())
            spec = importlib.util.spec_from_file_location('renamed_host_round2', path)
            renamed = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renamed)
            recorded = []
            adapter = types.SimpleNamespace(main=lambda args, recover_first: recorded.append(args) or 0)
            with patch.object(renamed.importlib.util, 'module_from_spec', return_value=adapter), \
                 patch.object(renamed.importlib.util, 'spec_from_file_location', return_value=types.SimpleNamespace(
                     loader=types.SimpleNamespace(exec_module=lambda _: None))):
                self.assertEqual(renamed.main(['--lock-evidence', 'synthetic.json']), 0)
            self.assertEqual(recorded[0][-4:], ['--driver', str(path), '--driver-sha256', a.sha(path.read_bytes())])
            self.assertEqual(recorded[0][:2], ['--lock-evidence', 'synthetic.json'])

    def test_n15_import_failure_fixed_exit_without_raw_exception(self):
        with patch.object(d.importlib.util, 'spec_from_file_location', side_effect=RuntimeError(KEY)), \
             contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(d.main([]), 4)
        self.assertNotIn(KEY, err.getvalue())
        self.assertIn('host_driver_failure', err.getvalue())

    def test_s6_round2_repro_copies_change_only_import_path(self):
        original = HERE.parent / 'adapter-review-r2'
        copied = OUT / 'round2-repros'
        for path in original.rglob('*.py'):
            rel = path.relative_to(original)
            expected = path.read_bytes()
            if rel.as_posix() == '_load.py':
                expected = expected.replace(b"HERE.parent / 'adapter-r1-1'", b'HERE.parent.parent')
            if rel.as_posix() == 'orig-repros/_load.py':
                expected = expected.replace(b"HERE.parent.parent / 'adapter-r1-1'", b'HERE.parent.parent.parent')
            self.assertEqual((copied / rel).read_bytes(), expected, str(rel))


if __name__ == '__main__':
    unittest.main(verbosity=2)
