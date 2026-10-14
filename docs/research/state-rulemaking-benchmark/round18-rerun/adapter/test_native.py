"""Offline R17 native integration and elapsed-time bounds; no provider calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r17_bound_driver', HERE / 'host_driver.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class NativeTests(unittest.TestCase):
    def test_timeout_arithmetic(self):
        # 900 is the last absolute scheduled offset, not 0+60+300+900.
        self.assertEqual(d.TIMEOUT_S, 600)
        self.assertEqual(d.KEY_TIMEOUT_S + d.POST_TOTAL_S + 900 + 4*d.KEY_TIMEOUT_S, 1590)
        self.assertEqual(900 + 4*d.KEY_TIMEOUT_S, 960)
        self.assertLess(1590, d.JOB_DEADLINE_S)
        self.assertLess(d.JOB_DEADLINE_S, 1800)

    def test_elapsed_deadline_stops_local_blocking_operation(self):
        before = signal.getsignal(signal.SIGALRM)
        with self.assertRaises(d.DriverError):
            with d.deadline(.02):
                time.sleep(.2)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0., 0.))
        self.assertEqual(signal.getsignal(signal.SIGALRM), before)

    def test_nested_deadline_restores_earlier_outer_deadline(self):
        with self.assertRaises(d.DriverError):
            with d.deadline(.04):
                with d.deadline(1):
                    time.sleep(.2)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0., 0.))

    def test_inner_cleanup_does_not_extend_outer_deadline(self):
        with d.deadline(2):
            before = signal.getitimer(signal.ITIMER_REAL)[0]
            with d.deadline(1):
                time.sleep(.01)
            after = signal.getitimer(signal.ITIMER_REAL)[0]
            self.assertLess(after, before)

    def test_unrelated_alarm_refuses(self):
        old = signal.signal(signal.SIGALRM, lambda *args: None)
        signal.setitimer(signal.ITIMER_REAL, 2)
        try:
            with self.assertRaises(d.DriverError):
                with d.deadline(1):
                    self.fail('entered conflicting deadline')
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)

    def test_get_uses_short_total_and_socket_timeout(self):
        with patch.object(d.os, 'environ', {'OPENROUTER_API_KEY': 'SYNTHETIC'}), \
             patch.object(d, '_request', return_value={}) as request:
            with self.assertRaises(KeyError):
                d.key_info(d.KEY_URL)
            self.assertEqual(request.call_args.args[:3], ('GET', '/api/v1/key', None))
        self.assertEqual(d.KEY_TIMEOUT_S, 15)

    def test_get_real_http_over_fake_socket_uses_15_seconds(self):
        spec = importlib.util.spec_from_file_location('r17_native_fake', HERE / 'fake_http.py')
        f = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(f)
        sock = f.FakeSocket(f.http_response(body=b'{"data":{"usage":0,"limit":50.00,"limit_remaining":50.00,"limit_reset":null}}'))
        tr = f.Transport([sock])
        with patch.object(d.os, 'environ', f.FakeEnv()), patch.object(d.http.client, 'HTTPSConnection', tr.cls), \
             patch.object(d, 'deadline', wraps=d.deadline) as alarms:
            packet = d.key_info(d.KEY_URL)
        self.assertEqual([call.args[0] for call in alarms.call_args_list], [15, 15, 15])
        self.assertEqual(tr.hosts, [('openrouter.ai', 443, 15)])
        self.assertTrue(sock.closed)
        self.assertIn(b'"usage":0', packet['fields'])

    def test_post_setup_total_and_response_alarm_budgets(self):
        spec = importlib.util.spec_from_file_location('r17_native_post_fake', HERE / 'fake_http.py')
        f = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(f)
        sock = f.FakeSocket(f.http_response())
        tr = f.Transport([sock])
        with patch.object(d.os, 'environ', f.FakeEnv()), patch.object(d.http.client, 'HTTPSConnection', tr.cls), \
             patch.object(d, 'deadline', wraps=d.deadline) as alarms:
            d.post_once(d.POST_URL, b'{}')
        self.assertEqual([call.args[0] for call in alarms.call_args_list], [615, 15, 600])
        self.assertEqual(len(tr.connections), 1)
        self.assertEqual(tr.wire()[0].count(b'POST '), 1)

    def test_shim_exact_args_and_verified_bytes_with_synthetic_host(self):
        spec = importlib.util.spec_from_file_location('r17_shim_unit', HERE / 'native_entry.py')
        shim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shim)
        with tempfile.TemporaryDirectory(dir=HERE / '_out') as tmp:
            root = Path(tmp)
            job = root / 'native-jobs/test-id'
            job.mkdir(parents=True)
            host = root / 'adapter/host_driver.py'
            host.parent.mkdir()
            raw = b"def main(args):\n    return 42 if args == ['SYNTHETIC'] else 1\n"
            host.write_bytes(raw)
            config = {'schema_version': 'r17.native-args.v1', 'host_sha256': hashlib.sha256(raw).hexdigest(), 'args': ['SYNTHETIC']}
            (job / 'arguments.json').write_text(json.dumps(config))
            with patch.object(shim, '__file__', str(job / 'adapter.py')):
                self.assertEqual(shim.main(['--live-initial']), 42)
                self.assertEqual(shim.main(['--cell', 'S1-OPQ']), 2)
                host.write_bytes(raw + b'# drift')
                self.assertEqual(shim.main(['--live-initial']), 2)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0., 0.))

    def test_ca_store_offline(self):
        self.assertGreater(d._tls_context().cert_store_stats()['x509_ca'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
