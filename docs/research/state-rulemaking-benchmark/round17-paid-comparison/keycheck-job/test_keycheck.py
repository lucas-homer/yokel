"""Synthetic socket-only tests. All temporary files stay in this directory."""
import ast
import contextlib
import decimal
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load('keycheck_candidate', 'keycheck.py')
proposal = load('keycheck_proposal', 'make_keycheck_proposal.py')
measurement = load('keycheck_measurement', 'measure_bootstrap.py')
KEY = 'synthetic-key-never-real-0123456789'
VALID = b'{"data":{"label":"DocketClock","limit":50.00,"limit_remaining":50.00,"limit_reset":null,"usage":0,"usage_daily":0.000000000000000001,"is_free_tier":false,"ignored":"discard"}}'


class FakeSocket:
    def __init__(self, raw, status=200, fail=None):
        self.writes = []
        self.closed = False
        self.fail = fail
        self.response = io.BytesIO(b'HTTP/1.1 ' + str(status).encode() + b' test\r\nContent-Length: '
            + str(len(raw)).encode() + b'\r\nLocation: https://example.invalid/\r\n\r\n' + raw)

    def sendall(self, data):
        self.writes.append(data)
        if self.fail:
            raise self.fail

    def makefile(self, *_args, **_kwargs):
        return self.response

    def close(self):
        self.closed = True


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE, prefix='synthetic-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Global guard: an unexpected real socket is an immediate test failure.
        self.guard = mock.patch.object(socket, 'socket', side_effect=AssertionError('network forbidden'))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    @contextlib.contextmanager
    def seam(self, raw=VALID, status=200, fail=None, key=KEY, extra=None):
        sock = FakeSocket(raw, status, fail)
        hosts = []
        def connect(connection):
            hosts.append((connection.host, connection.port, connection.timeout))
            connection.sock = sock
        environment = {'OPENROUTER_API_KEY': key}
        environment.update(extra or {})
        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch.object(adapter, 'tls_context', return_value=(object(), 'a' * 64)), \
             mock.patch.object(adapter.http.client.HTTPSConnection, 'connect', connect):
            yield sock, hosts

    def test_single_fixed_get_sanitized_exact_decimals_and_timing(self):
        with self.seam() as (sock, hosts):
            self.assertEqual(adapter.run(self.root), 0)
            self.assertNotIn('OPENROUTER_API_KEY', os.environ)
        self.assertEqual(hosts, [('openrouter.ai', 443, 15)])
        wire = b''.join(sock.writes)
        self.assertEqual(wire.count(b'GET /api/v1/key HTTP/1.1'), 1)
        self.assertNotIn(b'POST ', wire)
        self.assertNotIn(b'chat/completions', wire)
        self.assertTrue(sock.closed)
        raw = (self.root / 'KEY-MACHINE.json').read_bytes()
        self.assertNotIn(KEY.encode(), raw)
        record = json.loads(raw, parse_float=decimal.Decimal)
        self.assertEqual(record['response_sha256'], hashlib.sha256(VALID).hexdigest())
        self.assertEqual(record['fields']['usage_daily'], decimal.Decimal('0.000000000000000001'))
        self.assertEqual(set(record['fields']), set(adapter.EXPECTED) | {'usage_daily', 'is_free_tier'})
        self.assertFalse(record['accepted_by_primary'])
        self.assertEqual(record['status'], 'PASS')
        self.assertEqual((self.root / 'KEY-MACHINE.json').stat().st_mode & 0o777, 0o600)
        timing = json.loads((self.root / 'BOOTSTRAP-TIMING.json').read_bytes())
        self.assertIsNone(timing['bootstrap_seconds'])
        self.assertIsNone(timing['native_reserve_seconds'])
        self.assertFalse(timing['runner_start_exposed'])
        self.assertLessEqual(timing['adapter_entry_monotonic_ns'], timing['adapter_ready_monotonic_ns'])

    def test_required_mismatches_fail_with_sanitized_receipt(self):
        for field, value in [('label', 'Other'), ('usage', 1), ('limit_reset', 'monthly'),
                             ('limit', 49), ('limit_remaining', 49)]:
            with self.subTest(field=field):
                data = json.loads(VALID)
                data['data'][field] = value
                folder = self.root / field
                folder.mkdir()
                with self.seam(json.dumps(data).encode()):
                    self.assertEqual(adapter.run(folder), 1)
                record = json.loads((folder / 'KEY-MACHINE.json').read_bytes())
                self.assertFalse(record['checks'][field])
                self.assertEqual(record['status'], 'FAIL')

    def test_redirect_http_error_oversize_nonjson_fail_closed(self):
        for status, raw in [(301, VALID), (302, VALID), (307, VALID), (308, VALID),
                            (401, VALID), (500, VALID), (200, b'x' * (adapter.MAX_RAW + 1)),
                            (200, b'not JSON')]:
            with self.subTest(status=status, size=len(raw)), self.seam(raw, status) as (sock, hosts):
                with self.assertRaises(adapter.Rejected) as error:
                    adapter.get_metadata_once()
                self.assertIsNone(error.exception.__context__)
                self.assertNotIn(KEY, str(error.exception))
                self.assertEqual(len(hosts), 1)
                self.assertEqual(b''.join(sock.writes).count(b'GET /api/v1/key HTTP/1.1'), 1)
                self.assertTrue(sock.closed)

    def test_invalid_json_types_duplicates_and_constants_fail_closed(self):
        cases = [b'{}', b'{"data":[]}', VALID.replace(b'50.00', b'true'),
                 VALID.replace(b'50.00', b'"50.00"'), VALID.replace(b'50.00', b'NaN'),
                 VALID.replace(b'"usage":0,', b'"usage":0,"usage":0,'),
                 VALID.replace(b'"usage_daily":0.000000000000000001', b'"usage_daily":{"key":"bad"}')]
        for raw in cases:
            with self.subTest(raw=raw), self.seam(raw):
                with self.assertRaises(adapter.Rejected):
                    adapter.get_metadata_once()

    def test_secret_echo_plain_and_json_escaped_never_persist(self):
        escaped = ''.join('\\u%04x' % ord(c) for c in KEY).encode()
        for raw in [VALID.replace(b'DocketClock', KEY.encode()), VALID.replace(b'DocketClock', escaped),
                    VALID.replace(b'null', b'"' + escaped + b'"')]:
            with self.subTest(raw=raw), self.seam(raw):
                with self.assertRaises(adapter.Rejected) as error:
                    adapter.run(self.root)
                self.assertNotIn(KEY, str(error.exception))
                self.assertIsNone(error.exception.__context__)
                self.assertFalse((self.root / 'KEY-MACHINE.json').exists())
            (self.root / 'BOOTSTRAP-TIMING.json').unlink()

    def test_transport_exception_and_close_exception_are_sanitized(self):
        for failure in [RuntimeError('Authorization: Bearer ' + KEY), KeyboardInterrupt(KEY)]:
            with self.subTest(failure=type(failure)), self.seam(fail=failure) as (sock, _):
                with self.assertRaises(adapter.Rejected) as error:
                    adapter.get_metadata_once()
                self.assertIsNone(error.exception.__context__)
                self.assertNotIn(KEY, repr(error.exception))
                self.assertTrue(sock.closed)
                self.assertNotIn('OPENROUTER_API_KEY', os.environ)
        with self.seam() as (sock, _), mock.patch.object(sock, 'close', side_effect=RuntimeError(KEY)):
            with self.assertRaises(adapter.Rejected) as error:
                adapter.get_metadata_once()
            self.assertIsNone(error.exception.__context__)

    def test_invalid_missing_and_forbidden_credentials_no_connection(self):
        for key, extra in [(None, {}), ('', {}), ('invalid\nkey', {}), ('é', {}),
                           (KEY, {'OP_SERVICE_ACCOUNT_TOKEN': 'synthetic'}),
                           (KEY, {'TYPESAFE_API_KEY': 'synthetic'})]:
            with self.subTest(key=key, extra=extra):
                with self.seam(key=key or '', extra=extra) as (_sock, hosts):
                    with self.assertRaises(adapter.Rejected):
                        adapter.get_metadata_once()
                    self.assertEqual(hosts, [])

    def test_output_preflight_no_network_and_symlink_no_overwrite(self):
        target = self.root / 'target'
        target.write_text('preserve')
        (self.root / 'KEY-MACHINE.json').symlink_to(target)
        with self.seam() as (_sock, hosts):
            with self.assertRaises(adapter.Rejected):
                adapter.run(self.root)
            self.assertEqual(hosts, [])
        self.assertEqual(target.read_text(), 'preserve')
        (self.root / 'KEY-MACHINE.json').unlink()
        with self.seam() as (_sock, hosts):
            self.assertEqual(adapter.run(self.root), 0)
            with self.assertRaises(adapter.Rejected):
                adapter.run(self.root)
            self.assertEqual(len(hosts), 1)

    def test_main_fixed_messages_and_environment_cleanup(self):
        with self.seam(fail=RuntimeError(KEY)), mock.patch.object(adapter, 'run',
            side_effect=lambda _path: adapter.get_metadata_once()), \
            mock.patch.object(adapter.sys, 'argv', ['adapter.py', '--live-initial']):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                self.assertEqual(adapter.main(), 1)
            self.assertEqual(output.getvalue(), 'Metadata check rejected.\n')
            self.assertNotIn(KEY, output.getvalue())
            self.assertNotIn('OPENROUTER_API_KEY', os.environ)

    def test_static_only_get_no_completion_or_process_code(self):
        source = (HERE / 'keycheck.py').read_text()
        tree = ast.parse(source)
        requests = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == 'request']
        self.assertEqual(len(requests), 1)
        self.assertEqual([ast.literal_eval(n) for n in requests[0].args], ['GET', '/api/v1/key'])
        self.assertNotIn('POST', source)
        self.assertNotIn('chat/completions', source)
        self.assertNotIn('subprocess', source)
        self.assertNotIn('urllib', source)
        self.assertNotIn('requests', source)

    def test_explicit_ca_and_no_keylog_default_context(self):
        ca = self.root / 'synthetic-ca.pem'
        ca.write_bytes(b'synthetic public CA fixture')
        context = mock.Mock(verify_mode=ssl.CERT_REQUIRED, check_hostname=True)
        context.cert_store_stats.return_value = {'x509_ca': 1}
        with mock.patch.object(adapter, 'CA_BUNDLE', ca), \
             mock.patch.object(adapter.ssl, 'SSLContext', return_value=context) as factory:
            actual, sha = adapter.tls_context()
        factory.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations.assert_called_once_with(cafile=str(ca))
        self.assertIs(actual, context)
        self.assertEqual(sha, hashlib.sha256(ca.read_bytes()).hexdigest())

    def test_deadline_restoration_and_expiry(self):
        old = adapter.signal.getsignal(adapter.signal.SIGALRM)
        with self.assertRaises(adapter.Rejected), adapter.deadline():
            adapter.signal.getsignal(adapter.signal.SIGALRM)(0, None)
        self.assertEqual(adapter.signal.getsignal(adapter.signal.SIGALRM), old)
        self.assertEqual(adapter.signal.getitimer(adapter.signal.ITIMER_REAL), (0.0, 0.0))


class ProposalAndTimingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE, prefix='synthetic-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        (self.stage / 'adapter.py').write_bytes((HERE / 'keycheck.py').read_bytes())
        (self.stage / 'REVIEW.md').write_text('Synthetic review fixture; no live acceptance.')
        self.core = {'python_path': str(proposal.PYTHON), 'adapter_roots': [str(self.root)],
            'dependency_roots': [str(self.root), str(proposal.PYTHON.parent.parent)],
            'timeout_max_seconds': 1800, 'base_policy': {'references': {'OPENROUTER_API_KEY': 'synthetic-reference'}}}

    def prepare(self, **overrides):
        args = dict(core=self.core, stage=self.stage, scope_id='synthetic-scope',
            expires_unix=200, prior_nanousd=542976718, ceiling_nanousd=2000000000,
            now=100, dependencies=set())
        args.update(overrides)
        return proposal.prepare(**args)

    def test_exact_native_grammar_unique_id_zero_reserve_manifest(self):
        job, manifest = self.prepare()
        self.assertNotEqual(job['job_id'], self.prepare()[0]['job_id'])
        self.assertRegex(job['job_id'], r'^[a-z][a-z0-9-]{0,63}$')
        self.assertEqual(job['provider_variables'], ['OPENROUTER_API_KEY'])
        self.assertEqual(job['job']['argv'], [str(proposal.PYTHON), '-I', '-S', '-B',
            str(self.stage / 'adapter.py'), '--live-initial'])
        self.assertEqual(job['budget']['reservation_nanousd'], 0)
        self.assertEqual(job['budget']['prior_nanousd'], 542976718)
        self.assertEqual(job['job']['timeout_seconds'], 30)
        self.assertEqual(len(manifest['files']), 2)
        self.assertEqual(set(job['job']['files']), {str(proposal.PYTHON),
            str(self.stage / 'adapter.py'), str(self.stage / 'REVIEW.md')})
        self.assertEqual(job['review']['sha256'], job['job']['files'][job['review']['path']])

    def test_expiry_scope_budget_root_drift_and_extra_files_rejected(self):
        for changes in [{'expires_unix': 100}, {'expires_unix': 100 + 7 * 86400 + 1},
                        {'scope_id': 'invalid/scope'}, {'prior_nanousd': True},
                        {'prior_nanousd': 2000000001}, {'ceiling_nanousd': 0},
                        {'core': dict(self.core, adapter_roots=['/not-the-stage'])}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.prepare(**changes)
        (self.stage / 'extra').write_text('not needed')
        with self.assertRaises(ValueError):
            self.prepare()
        (self.stage / 'extra').unlink()
        (self.stage / 'adapter.py').write_text('drift')
        with self.assertRaises(ValueError):
            self.prepare()

    def test_offline_proposal_cli_full_runtime_pins_and_no_overwrite(self):
        core_path = self.root / 'synthetic-core.json'
        core_path.write_text(json.dumps(self.core))
        output = self.root / 'proposals'
        command = [str(proposal.PYTHON), '-I', '-S', '-B',
            str(HERE / 'make_keycheck_proposal.py'), '--core', str(core_path),
            '--stage', str(self.stage), '--output', str(output),
            '--scope-id', 'synthetic-scope', '--expires-unix', str(int(time.time()) + 3600),
            '--prior-nanousd', '542976718', '--ceiling-nanousd', '2000000000']
        # This subprocess is solely the offline generator, never a native tool.
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        job_path = output / 'UNSIGNED-ZERO-COST-PROPOSAL.json'
        job = json.loads(job_path.read_bytes())
        manifest = json.loads((output / 'STAGE-MANIFEST.json').read_bytes())
        self.assertEqual(result.stdout.strip(), job['job_id'])
        self.assertEqual(len(manifest['files']), 2)
        self.assertGreater(len(job['job']['files']), 100)
        self.assertEqual(job['job']['files'][str(proposal.PYTHON)], proposal.digest(proposal.PYTHON))
        self.assertTrue(all('site-packages' not in Path(p).parts for p in job['job']['files']))
        raw_before = job_path.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(job_path.read_bytes(), raw_before)

    def test_conservative_measurement_exact_reserve_receipt_binding(self):
        timing = {'adapter_entry_monotonic_ns': 2_000_000_000,
                  'adapter_ready_monotonic_ns': 3_123_456_789, 'bootstrap_seconds': None}
        boundaries = {'before_run_monotonic_ns': 1_000_000_000,
                      'after_run_monotonic_ns': 5_000_000_000, 'returncode': 0,
                      'same_host_boot_and_monotonic_clock_confirmed_by_primary': True}
        result = measurement.measure(timing, boundaries, b'synthetic native receipt')
        self.assertEqual(result['bootstrap_seconds'], '2.123456789')
        self.assertEqual(result['native_reserve_seconds'], '57.876543211')
        self.assertTrue(result['positive_native_reserve'])
        self.assertFalse(result['accepted_by_primary'])
        self.assertEqual(result['native_receipt_sha256'], hashlib.sha256(b'synthetic native receipt').hexdigest())
        boundaries['before_run_monotonic_ns'] = 4_000_000_000
        with self.assertRaises(ValueError):
            measurement.measure(timing, boundaries, b'')

    def test_measurement_refuses_unconfirmed_failed_and_nonpositive_reserve(self):
        timing = {'adapter_entry_monotonic_ns': 61_000_000_000, 'adapter_ready_monotonic_ns': 62_000_000_000}
        boundaries = {'before_run_monotonic_ns': 0, 'after_run_monotonic_ns': 63_000_000_000,
                      'returncode': 0, 'same_host_boot_and_monotonic_clock_confirmed_by_primary': True}
        self.assertFalse(measurement.measure(timing, boundaries, b'')['positive_native_reserve'])
        for changes in [{'returncode': 1}, {'same_host_boot_and_monotonic_clock_confirmed_by_primary': False},
                        {'before_run_monotonic_ns': True}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                measurement.measure(timing, dict(boundaries, **changes), b'')


if __name__ == '__main__':
    unittest.main(verbosity=2)
