"""Fully offline host tests: inject fake HTTPSConnection; never a real connection/key."""
import contextlib
import hashlib
import http.client
import importlib.util
import io
from pathlib import Path
import ssl
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OUT = HERE / '_out'
OUT.mkdir(exist_ok=True)


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('tested_host', 'host_driver.py')
t = load('host_adapter_harness', 'test_adapter.py')
a = t.a
SYNTHETIC = 'SYNTHETIC-ONLY-FAKE-KEY-17'
KEY_RAW = (b'{"data":{"usage":0.0000000001,"limit":1.7300000000000000001,'
           b'"limit_remaining":1.7299999999000000001,"limit_reset":null,'
           b'"label":"drop-label","is_free_tier":false,"rate_limit":{"x":1}}}')


class Env:
    def __init__(self, values=None):
        self.values = {'OPENROUTER_API_KEY': SYNTHETIC} if values is None else values
        self.reads = []

    def get(self, name, default=None):
        self.reads.append(name)
        if name != 'OPENROUTER_API_KEY':
            raise AssertionError('environment fallback/proxy read')
        return self.values.get(name, default)


class FakeResponse:
    def __init__(self, raw=b'{}', status=200, headers=None):
        self.raw = raw
        self.status = status
        self.headers = headers or [('Content-Type', 'application/json')]
        self.reads = []

    def read(self, amount):
        self.reads.append(amount)
        return self.raw[:amount]

    def getheaders(self):
        return self.headers


class Factory:
    def __init__(self, responses=None, fail=None):
        self.responses = responses or [FakeResponse()]
        self.fail = fail
        self.connections = []
        self.requests = []
        self.contexts = []
        self.on_request = None

    def __call__(self, host, *, timeout, context):
        if host != 'openrouter.ai':
            raise AssertionError('unexpected host')
        self.contexts.append(context)
        self.timeout = timeout
        outer = self
        response = self.responses.pop(0)
        class Connection:
            closed = False
            def request(self, method, path, *, body, headers):
                outer.requests.append((method, path, body, headers))
                if outer.on_request:
                    outer.on_request(method, path, body)
                if outer.fail == 'request':
                    raise TimeoutError(SYNTHETIC)
            def getresponse(self):
                if outer.fail == 'response':
                    raise TimeoutError(SYNTHETIC)
                return response
            def close(self):
                self.closed = True
        c = Connection()
        self.connections.append(c)
        return c


class HostTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.factory = Factory()
        self.addCleanup(patch.stopall)
        # Replace the mapping, never inspect/copy the real process environment.
        patch.object(d.os, 'environ', self.env).start()
        patch.object(d.http.client, 'HTTPSConnection', self.factory).start()

    def test_h1_exact_bytes_object_one_post_fixed_headers(self):
        raw = b'{ "untouched" : 1.0000 }\n'
        packet = d.post_once(d.POST_URL, raw)
        self.assertEqual(set(packet), {'status', 'raw', 'headers', 'tls_ca_sha256'})
        method, path, body, headers = self.factory.requests[0]
        self.assertEqual((method, path), ('POST', '/api/v1/chat/completions'))
        self.assertIs(body, raw)
        self.assertEqual(headers['Content-Length'], str(len(raw)))
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Connection'], 'close')
        self.assertEqual(len(self.factory.requests), 1)
        self.assertTrue(self.factory.connections[0].closed)

    def test_h1_redirect_returned_without_following(self):
        self.factory.responses = [FakeResponse(status=302, headers=[('Location', 'https://elsewhere.invalid')])]
        packet = d.post_once(d.POST_URL, b'{}')
        self.assertEqual(packet['status'], 302)
        self.assertEqual(packet['headers'], {})
        self.assertEqual(len(self.factory.requests), 1)

    def test_h1_fresh_connection_each_explicit_call(self):
        self.factory.responses = [FakeResponse(), FakeResponse()]
        d.post_once(d.POST_URL, b'{}')
        d.post_once(d.POST_URL, b'{}')
        self.assertEqual(len(self.factory.connections), 2)
        self.assertIsNot(self.factory.connections[0], self.factory.connections[1])
        self.assertTrue(all(c.closed for c in self.factory.connections))

    def test_h2_timeout_never_retry_exception_no_key_or_context(self):
        for phase in ('request', 'response'):
            with self.subTest(phase=phase):
                self.factory.responses = [FakeResponse()]
                self.factory.fail = phase
                before = len(self.factory.requests)
                with self.assertRaises(d.DriverError) as caught:
                    d.post_once(d.POST_URL, b'{}')
                self.assertEqual(len(self.factory.requests) - before, 1)
                self.assertNotIn(SYNTHETIC, str(caught.exception))
                self.assertIsNone(caught.exception.__context__)
                self.assertTrue(self.factory.connections[-1].closed)

    def test_h3_allowlist_matches_adapter_and_drops_sensitive_values(self):
        headers = {'authorization': 'Bearer ' + SYNTHETIC, 'cookie': 'cookie-secret',
                   'set-cookie': 'cookie-secret', 'X-Unknown': SYNTHETIC, 'Content-Type': 'application/json',
                   'Date': 'today', 'X-Request-ID': 'id', 'X-OpenRouter-Request-ID': 'or-id',
                   'X-OpenAI-Request-ID': 'ai-id', 'OpenAI-Request-ID': 'openai-id',
                   'X-RateLimit-Remaining': '42', 'X-RateLimit-Reset': 'x' * 1500,
                   'x-ratelimit-other': 'Bearer sk-or-synthetic', 'x-request-id': 'newline\r\n',
                   'content-length': '17'}
        self.assertEqual(d.filter_headers(headers), a.filter_headers(headers))
        self.factory.responses = [FakeResponse(headers=list(headers.items()))]
        packet = d.post_once(d.POST_URL, b'{}')
        self.assertNotIn(SYNTHETIC, repr(packet))
        self.assertNotIn('set-cookie', packet['headers'])
        self.assertEqual(len(packet['headers']['x-ratelimit-reset']), 1024)

    def test_h4_import_does_not_read_env_connect_or_read_source(self):
        env = Env()
        with patch.object(d.os, 'environ', env), patch.object(Path, 'read_bytes', side_effect=AssertionError('file read')):
            fresh = load('fresh_inert_host', 'host_driver.py')
        self.assertEqual(env.reads, [])
        self.assertEqual(self.factory.requests, [])
        self.assertTrue(callable(fresh.post_once))

    def test_h4_env_read_only_callbacks_one_name(self):
        self.assertEqual(self.env.reads, [])
        self.factory.responses = [FakeResponse(), FakeResponse(raw=KEY_RAW)]
        d.post_once(d.POST_URL, b'{}')
        self.assertEqual(self.env.reads, ['OPENROUTER_API_KEY'])
        d.key_info(d.KEY_URL)
        self.assertEqual(self.env.reads, ['OPENROUTER_API_KEY'] * 2)

    def test_h4_unset_key_no_fallback_or_request(self):
        self.env.values = {'OTHER_KEY': SYNTHETIC}
        for callback, args in ((d.post_once, (d.POST_URL, b'{}')), (d.key_info, (d.KEY_URL,))):
            with self.assertRaises(d.DriverError) as caught:
                callback(*args)
            self.assertNotIn(SYNTHETIC, str(caught.exception))
            self.assertIsNone(caught.exception.__context__)
        self.assertEqual(self.factory.requests, [])
        self.assertEqual(self.env.reads, ['OPENROUTER_API_KEY'] * 2)

    def test_h4_tls_verified_and_proxy_env_ignored(self):
        self.env.values.update({'HTTPS_PROXY': 'https://proxy.invalid', 'HTTP_PROXY': 'http://proxy.invalid',
                                'ALL_PROXY': 'http://proxy.invalid', 'NO_PROXY': '*'})
        d.post_once(d.POST_URL, b'{}')
        self.assertEqual(self.env.reads, ['OPENROUTER_API_KEY'])
        context = self.factory.contexts[0]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertIsNone(context.keylog_filename)
        self.assertEqual(self.factory.timeout, d.TIMEOUT_S)

    def test_h4_unverified_tls_refused(self):
        with patch.object(d, '_tls_context', return_value=types.SimpleNamespace(
            verify_mode=ssl.CERT_NONE, check_hostname=False)):
            with self.assertRaises(d.DriverError):
                d.post_once(d.POST_URL, b'{}')
        self.assertEqual(self.factory.requests, [])

    def test_h4_echoed_key_response_body_or_allowed_header_never_returned(self):
        for response in (FakeResponse(raw=SYNTHETIC.encode()),
                         FakeResponse(headers=[('x-request-id', SYNTHETIC)])):
            self.factory.responses = [response]
            with self.assertRaises(d.DriverError) as caught:
                d.post_once(d.POST_URL, b'{}')
            self.assertNotIn(SYNTHETIC, str(caught.exception))
            self.assertIsNone(caught.exception.__context__)

    def test_h5_cap_single_read_limit_plus_one(self):
        for size, okay in ((d.MAX_RAW, True), (d.MAX_RAW + 1, False), (d.MAX_RAW * 2, False)):
            with self.subTest(size=size):
                response = FakeResponse(raw=b'x' * size)
                self.factory.responses = [response]
                if okay:
                    self.assertEqual(len(d.post_once(d.POST_URL, b'{}')['raw']), d.MAX_RAW)
                else:
                    with self.assertRaises(d.DriverError):
                        d.post_once(d.POST_URL, b'{}')
                self.assertEqual(response.reads, [d.MAX_RAW + 1])
                self.assertTrue(self.factory.connections[-1].closed)

    def test_h6_get_exact_decimal_tokens_hash_original(self):
        self.factory.responses = [FakeResponse(raw=KEY_RAW)]
        packet = d.key_info(d.KEY_URL)
        self.assertEqual(set(packet), {'fields', 'response_sha256', 'tls_ca_sha256'})
        self.assertEqual(packet['response_sha256'], hashlib.sha256(KEY_RAW).hexdigest())
        self.assertEqual(packet['fields'], b'{"usage":0.0000000001,"limit":1.7300000000000000001,'
                         b'"limit_remaining":1.7299999999000000001,"limit_reset":null}')
        self.assertNotIn(b'drop-label', packet['fields'])
        method, path, body, _ = self.factory.requests[0]
        self.assertEqual((method, path, body), ('GET', '/api/v1/key', None))
        self.assertEqual(len(self.factory.requests), 1)

    def test_h6_integer_exponent_and_null_tokens_preserved(self):
        raw = b'{"data":{"usage":0,"limit":1.730e0,"limit_remaining":1.730e0,"limit_reset":null}}'
        self.factory.responses = [FakeResponse(raw=raw)]
        fields = d.key_info(d.KEY_URL)['fields']
        self.assertIn(b'"usage":0', fields)
        self.assertIn(b'1.730e0', fields)

    def test_h6_malformed_envelope_status_duplicates_types_refused(self):
        cases = [b'{}', b'not json', b'{"data":[]}',
                 b'{"data":{"usage":0,"usage":1}}',
                 b'{"data":{"usage":true,"limit":null,"limit_remaining":null,"limit_reset":null}}',
                 b'{"data":{"usage":"' + SYNTHETIC.encode() + b'"}}']
        for raw in cases:
            with self.subTest(raw=raw):
                self.factory.responses = [FakeResponse(raw=raw)]
                with self.assertRaises(d.DriverError) as caught:
                    d.key_info(d.KEY_URL)
                self.assertNotIn(SYNTHETIC, str(caught.exception))
                self.assertIsNone(caught.exception.__context__)
        self.factory.responses = [FakeResponse(raw=KEY_RAW, status=302)]
        with self.assertRaises(d.DriverError):
            d.key_info(d.KEY_URL)

    def test_h7_source_exact_utf8_synthetic_only(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            root = Path(tmp)
            ready_root = root / 'sources-r2'
            ready_root.mkdir()
            (ready_root / 'READY.json').write_bytes(b'{"selected":["a","b","c"]}')
            for name in ('a', 'b', 'c'):
                (ready_root / name).mkdir()
                (ready_root / name / 'parsed-body.txt').write_bytes('synthetic α\r\n'.encode())
            with patch.object(d, 'HERE', root / 'driver'):
                for cell in a.CALLS:
                    self.assertEqual(d.source(cell), 'synthetic α\r\n')
        self.assertEqual(self.env.reads, [])
        self.assertEqual(self.factory.requests, [])

    def test_h1_invalid_url_or_body_refused_before_env(self):
        for url, body in ((d.POST_URL + '?x=1', b'{}'), ('http://openrouter.ai', b'{}'),
                          (d.POST_URL, bytearray(b'{}')), (d.POST_URL, '{}')):
            with self.assertRaises(d.DriverError):
                d.post_once(url, body)
        with self.assertRaises(d.DriverError):
            d.key_info(d.KEY_URL + '/extra')
        self.assertEqual(self.env.reads, [])
        self.assertEqual(self.factory.requests, [])

    def test_h8_h9_cli_routes_one_cell_recover_first_and_self_pin(self):
        mock_adapter = types.SimpleNamespace(main=lambda argv, recover_first:
            self.record_cli(argv, recover_first))
        with patch.object(d.importlib.util, 'module_from_spec', return_value=mock_adapter), \
             patch.object(d.importlib.util, 'spec_from_file_location', return_value=types.SimpleNamespace(
                 loader=types.SimpleNamespace(exec_module=lambda module: None))):
            self.assertEqual(d.main(['--cell', 'S1-OPQ']), 17)
        self.assertTrue(self.cli_recover)
        self.assertEqual(self.cli_args[:2], ['--cell', 'S1-OPQ'])
        self.assertEqual(self.cli_args[-1], hashlib.sha256((HERE / 'host_driver.py').read_bytes()).hexdigest())
        self.assertEqual(self.env.reads, [])

    def test_h8_cli_cannot_override_driver(self):
        mock_adapter = types.SimpleNamespace(main=lambda *args, **kwargs: self.fail('CLI forwarded override'))
        with patch.object(d.importlib.util, 'module_from_spec', return_value=mock_adapter), \
             patch.object(d.importlib.util, 'spec_from_file_location', return_value=types.SimpleNamespace(
                 loader=types.SimpleNamespace(exec_module=lambda module: None))), \
             contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(d.main(['--driver=elsewhere.py']), 2)
        self.assertIn('driver_override', err.getvalue())
        self.assertEqual(self.env.reads, [])

    def test_h2_timeout_during_body_read_never_resends(self):
        response = FakeResponse()
        def fail_read(amount):
            response.reads.append(amount)
            raise TimeoutError(SYNTHETIC)
        response.read = fail_read
        self.factory.responses = [response]
        with self.assertRaises(d.DriverError) as caught:
            d.post_once(d.POST_URL, b'{}')
        self.assertEqual(len(self.factory.requests), 1)
        self.assertEqual(response.reads, [d.MAX_RAW + 1])
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn(SYNTHETIC, str(caught.exception))

    def test_h5_key_body_cap_and_no_followup_get(self):
        response = FakeResponse(raw=b' ' * (d.MAX_RAW + 1))
        self.factory.responses = [response]
        with self.assertRaises(d.DriverError):
            d.key_info(d.KEY_URL)
        self.assertEqual(response.reads, [d.MAX_RAW + 1])
        self.assertEqual(len(self.factory.requests), 1)

    def test_integration_success_three_requests_exact_post_no_key_receipt(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            h = t.Harness(tmp)
            self.factory.responses = [FakeResponse(raw=b'{"data":' + t.packet(0)['fields'] + b'}'),
                FakeResponse(raw=h.response['raw'], headers=[('authorization', SYNTHETIC),
                    ('set-cookie', 'synthetic-cookie'), ('content-type', 'application/json')]),
                FakeResponse(raw=b'{"data":' + t.packet(10_000_000)['fields'] + b'}')]
            def check(method, path, body):
                if method == 'POST':
                    self.assertEqual(h.entries()[-1]['type'], 'DISPATCH_MARK')
                    self.assertEqual((h.run / 'job1/request.json').read_bytes(), body)
            self.factory.on_request = check
            h.post, h.key_info = d.post_once, d.key_info
            self.assertEqual(h.execute()['state'], 13)
            self.assertEqual([req[0] for req in self.factory.requests], ['GET', 'POST', 'GET'])
            for file in h.run.rglob('*'):
                if file.is_file():
                    self.assertNotIn(SYNTHETIC.encode(), file.read_bytes())

    def record_cli(self, argv, recover_first):
        self.cli_args, self.cli_recover = argv, recover_first
        return 17

    def test_integration_key_never_in_any_adapter_receipt_timeout_row2(self):
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            h = t.Harness(tmp)
            keyraw = b'{"data":' + t.packet(0)['fields'] + b'}'
            self.factory.responses = [FakeResponse(raw=keyraw), FakeResponse()]
            def check(method, path, body):
                if method == 'POST':
                    self.assertEqual(h.entries()[-1]['type'], 'DISPATCH_MARK')
                    self.assertIsInstance(body, bytes)
                    raise TimeoutError(SYNTHETIC)
            self.factory.on_request = check
            # subsequent four GETs reconcile missing response cost conservatively
            self.factory.responses += [FakeResponse(raw=keyraw) for _ in range(4)]
            h.post, h.key_info = d.post_once, d.key_info
            result = h.execute()
            self.assertEqual(result['state'], 2)
            self.assertEqual(sum(req[0] == 'POST' for req in self.factory.requests), 1)
            for file in h.run.rglob('*'):
                if file.is_file():
                    self.assertNotIn(SYNTHETIC.encode(), file.read_bytes())

if __name__ == '__main__':
    unittest.main(verbosity=2)
