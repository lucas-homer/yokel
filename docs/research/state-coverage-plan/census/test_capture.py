"""Offline capture tests; no test opens a socket or uses the real hash store."""
import hashlib
import importlib.util
import io
import json
import multiprocessing
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from urllib.error import URLError
from urllib.request import Request
from unittest.mock import patch

HOME = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('census_capture', HOME / 'capture.py')
capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture
SPEC.loader.exec_module(capture)


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeTransport:
    def __init__(self, clock, responses=(), robots=None):
        self.clock = clock
        self.responses = list(responses)
        self.calls = []
        self.robots = robots

    def __call__(self, request):
        self.calls.append((request, self.clock()))
        if request.full_url.endswith('/robots.txt'):
            return self.robots or capture.Response(request.full_url, 200, {}, b'User-agent: *\nAllow: /\n')
        if not self.responses:
            raise AssertionError('unexpected transport call: ' + request.full_url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def originals(self):
        return [(r, at) for r, at in self.calls if not r.full_url.endswith('/robots.txt')]


def lock_worker(store, ready, release):
    with capture.RateLimiter(store).hold('example.test', 5):
        ready.set()
        release.wait(10)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Path(self.temporary.name) / 'store'
        self.clock = Clock()
        self.surface = {
            'surface_id': 'test', 'version': 'v1', 'url_pattern': r'https://example\.test/allowed/.*',
            'collection_rule': 'allowed', 'retention': 'internal_originals',
            'rate': {'min_interval_seconds': 5},
        }
        self.request = {'manifest_entry_id': 'entry-1', 'surface_id': 'test',
                        'url': 'https://example.test/allowed/one', 'method': 'GET'}

    def response(self, status=200, body=b'notice\x00\xff\n', headers=None, url=None):
        return capture.Response(url or self.request['url'], status,
                                headers or {'Content-Type': 'application/pdf'}, body)

    def runner(self, responses=(), *, robots=None, surfaces=None, **kwargs):
        fake = FakeTransport(self.clock, responses, robots)
        runner = capture.Capture(self.store, surfaces=surfaces or [self.surface],
                                 transport=fake, clock=self.clock, sleep=self.clock.sleep, **kwargs)
        return runner, fake

    def assert_schema(self, value, name):
        try:
            from jsonschema import Draft202012Validator, FormatChecker
        except ImportError:
            return  # Only the optional assertion is skipped; behavioral checks run.
        schema = json.loads((HOME / f'{name}.schema.json').read_text())
        if name == 'manifest':
            schema = schema['properties']['retrieval']
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)

    def assert_no_original(self, result):
        ret = result['retrieval']
        for name in ('sha256', 'storage_path', 'sidecar_path'):
            self.assertIsNone(ret[name])
        self.assertFalse(list(self.store.glob('[0-9a-f][0-9a-f]/*')))
        self.assert_schema(ret, 'manifest')

    def test_allowed_bytes_sidecar_retrieval_and_identifying_agent(self):
        body = b'%PDF-1.7\nexact bytes\x00\xff'
        runner, fake = self.runner([self.response(body=body)])
        self.request['headers'] = {'USER-AGENT': 'spoof', 'Host': 'other.test'}
        result = runner.capture(self.request)
        ret = result['retrieval']
        sha = hashlib.sha256(body).hexdigest()
        self.assertEqual(ret['result'], 'retrieved')
        self.assertEqual(ret['sha256'], sha)
        self.assertEqual(ret['byte_length'], len(body))
        self.assertEqual(result['surface_id'], 'test')
        self.assertEqual(result['rights_version'], 'v1')
        self.assertEqual(ret['storage_path'], f'{capture.STORE}/{sha[:2]}/{sha}')
        self.assertTrue(ret['attempted_at'].endswith('Z'))
        original = self.store / sha[:2] / sha
        self.assertEqual(original.read_bytes(), body)
        metadata = json.loads(original.with_name(sha + '.metadata.json').read_text())
        self.assertEqual(metadata['captures'][0]['manifest_entry_id'], 'entry-1')
        self.assertEqual(metadata['captures'][0]['captured_at'], ret['attempted_at'])
        self.assertEqual(metadata['captures'][0]['rights_version'], 'v1')
        self.assertEqual(metadata['captures'][0]['capture_method'], 'GET')
        self.assert_schema(ret, 'manifest')
        self.assert_schema(metadata, 'sidecar')
        for request, _ in fake.calls:
            self.assertEqual(request.get_header('User-agent'), capture.USER_AGENT)
            self.assertIsNone(request.get_header('Host'))
        self.assertEqual(fake.calls[1][1] - fake.calls[0][1], 5)

    def test_on_hold_blocked_and_retention_refused_without_transport(self):
        for rule, retention in [('on_hold', 'internal_originals'), ('blocked', 'internal_originals'),
                                ('allowed', 'not_authorized')]:
            with self.subTest(rule=rule, retention=retention):
                self.surface.update(collection_rule=rule, retention=retention)
                runner, fake = self.runner()
                result = runner.capture(self.request)
                self.assertEqual(result['retrieval']['result'], 'not_attempted')
                self.assertIsNone(result['retrieval']['attempted_at'])
                self.assertEqual(fake.calls, [])
                self.assert_no_original(result)

    def test_watched_only_requires_attended(self):
        self.surface['collection_rule'] = 'allowed_watched_only'
        runner, fake = self.runner()
        self.assertIn('--attended', runner.capture(self.request)['retrieval']['reason'])
        self.assertEqual(fake.calls, [])
        runner, _ = self.runner([self.response()], attended=True)
        result = runner.capture(self.request)
        self.assertEqual(result['retrieval']['result'], 'retrieved')
        self.assertTrue(result['attended'])

    def test_unknown_surface_and_full_url_match_required(self):
        runner, fake = self.runner()
        for request in [dict(self.request, surface_id='unknown'),
                        dict(self.request, url='https://example.test/disallowed/one'),
                        dict(self.request, url=self.request['url'] + '\nevil'),
                        dict(self.request, method='DELETE'),
                        dict(self.request, headers={'Good': 'bad\r\nheader: x'}),
                        dict(self.request, surface_id=[]), []]:
            with self.subTest(request=request):
                self.assertEqual(runner.capture(request)['retrieval']['result'], 'not_attempted')
        self.assertEqual(fake.calls, [])

    def test_off_pattern_redirect_not_followed(self):
        runner, fake = self.runner([self.response(302, headers={'Location': 'https://evil.test/one'})])
        result = runner.capture(self.request)
        self.assertEqual(result['retrieval']['result'], 'invalid_response')
        self.assertIn('redirect outside', result['retrieval']['reason'])
        self.assertEqual(len(fake.originals()), 1)
        self.assert_no_original(result)
        self.assertEqual(runner.capture(self.request)['retrieval']['result'], 'not_attempted')
        self.assertEqual(len(fake.originals()), 1)

    def test_defensive_final_url_check(self):
        runner, fake = self.runner([self.response(url='https://evil.test/one')])
        result = runner.capture(self.request)
        self.assertIn('off-pattern final URL', result['retrieval']['reason'])
        self.assert_no_original(result)

    def test_allowed_redirect_is_rate_limited_and_robots_cached(self):
        final = 'https://example.test/allowed/two'
        runner, fake = self.runner([self.response(302, headers={'Location': '/allowed/two'}),
                                    self.response(url=final)])
        result = runner.capture(self.request)
        self.assertEqual(result['retrieval']['final_url'], final)
        self.assertEqual(result['retrieval']['result'], 'retrieved')
        self.assertEqual([at for _, at in fake.calls], [self.clock.now - 10, self.clock.now - 5, self.clock.now])
        self.assertEqual(len(fake.calls), 3)

    def test_403_and_429_stop_whole_host_across_surfaces(self):
        for status in (403, 429):
            with self.subTest(status=status):
                other = dict(self.surface, surface_id='other')
                runner, fake = self.runner([self.response(status)], surfaces=[self.surface, other])
                result = runner.capture(self.request)
                self.assertEqual(result['retrieval']['http_status'], status)
                self.assertEqual(result['retrieval']['result'], 'inaccessible')
                self.assert_no_original(result)
                later = runner.capture(dict(self.request, surface_id='other', manifest_entry_id='entry-2'))
                self.assertEqual(later['retrieval']['result'], 'not_attempted')
                self.assertIn('host stopped', later['retrieval']['reason'])
                self.assertEqual(len(fake.originals()), 1)

    def test_cloudflare_challenges_stop_even_with_200(self):
        responses = [self.response(headers={'CF-Mitigated': 'challenge'}),
                     self.response(body=b'<html><title>Just a moment...</title></html>'),
                     self.response(503, body=b'<script src="/cdn-cgi/challenge-platform/a"></script>',
                                   headers={'Server': 'cloudflare'})]
        for response in responses:
            with self.subTest(response=response):
                runner, fake = self.runner([response])
                result = runner.capture(self.request)
                self.assertIn('bot challenge', result['retrieval']['reason'])
                self.assert_no_original(result)
                runner.capture(self.request)
                self.assertEqual(len(fake.originals()), 1)

    def test_connection_error_retried_once_after_interval(self):
        runner, fake = self.runner([URLError(socket.gaierror('DNS failed')), self.response()])
        self.assertEqual(runner.capture(self.request)['retrieval']['result'], 'retrieved')
        self.assertEqual(len(fake.originals()), 2)
        self.assertEqual(fake.originals()[1][1] - fake.originals()[0][1], 5)
        runner, fake = self.runner([TimeoutError('timeout'), ConnectionResetError('reset'), self.response()])
        result = runner.capture(self.request)
        self.assertEqual(result['retrieval']['result'], 'inaccessible')
        self.assertEqual(len(fake.originals()), 2)
        self.assert_no_original_failure_refs(result)

    def assert_no_original_failure_refs(self, result):
        for name in ('sha256', 'storage_path', 'sidecar_path'):
            self.assertIsNone(result['retrieval'][name])

    def test_http_500_not_retried_and_host_can_continue(self):
        runner, fake = self.runner([self.response(500), self.response()])
        first = runner.capture(self.request)
        self.assertEqual(first['retrieval']['http_status'], 500)
        self.assertEqual(len(fake.originals()), 1)
        self.assertEqual(first['retrieval']['result'], 'inaccessible')
        self.assert_no_original(first)
        self.assertEqual(runner.capture(self.request)['retrieval']['result'], 'retrieved')

    def test_rate_limiter_spacing_survives_new_instances_and_stricter_rate(self):
        first = capture.RateLimiter(self.store, self.clock, self.clock.sleep)
        second = capture.RateLimiter(self.store, self.clock, self.clock.sleep)
        with first.hold('example.test', 7):
            start = self.clock()
            self.clock.now += 3  # Lock spans the full request, not only its start.
        with second.hold('example.test', 5):
            self.assertEqual(self.clock() - start, 10)
        self.assertEqual(self.clock.sleeps, [7])
        with second.hold('other.test', 5):
            self.assertEqual(self.clock() - start, 10)

    def test_rate_lock_is_held_across_processes(self):
        ctx = multiprocessing.get_context('fork')
        ready, release = ctx.Event(), ctx.Event()
        worker = ctx.Process(target=lock_worker, args=(str(self.store), ready, release))
        worker.start()
        try:
            self.assertTrue(ready.wait(5))
            with (self.store / '.ratelimit/example.test').open('a+') as lock:
                with self.assertRaises(BlockingIOError):
                    capture.fcntl.flock(lock, capture.fcntl.LOCK_EX | capture.fcntl.LOCK_NB)
        finally:
            release.set()
            worker.join(5)
            if worker.is_alive():
                worker.terminate()
                worker.join()
        self.assertEqual(worker.exitcode, 0)

    def test_identical_bytes_append_provenance_without_rewriting_bytes(self):
        runner, fake = self.runner([self.response(), self.response()])
        first = runner.capture(self.request)
        sha = first['retrieval']['sha256']
        path = self.store / sha[:2] / sha
        before = path.stat().st_mtime_ns
        second = runner.capture(dict(self.request, manifest_entry_id='entry-2'))
        self.assertEqual(second['retrieval']['sha256'], sha)
        self.assertEqual(path.stat().st_mtime_ns, before)
        metadata = json.loads(path.with_name(sha + '.metadata.json').read_text())
        self.assertEqual([c['manifest_entry_id'] for c in metadata['captures']], ['entry-1', 'entry-2'])
        self.assert_schema(metadata, 'sidecar')
        self.assertEqual(len(fake.calls), 3)  # One robots check for the whole run.

    def test_invalid_bodies_not_accepted(self):
        for body, headers, reason in [
                (b'{"truncated":', {'Content-Type': 'application/json'}, 'truncated JSON'),
                (b'[1,', {'Content-Type': 'application/problem+json'}, 'truncated JSON'),
                (b'  ', {'Content-Type': 'text/plain'}, 'empty body'),
                (b'<html><title>404 Not Found</title></html>', {'Content-Type': 'text/html'}, 'HTML error page'),
                (b'short', {'Content-Length': '90'}, 'truncation')]:
            with self.subTest(reason=reason):
                runner, _ = self.runner([self.response(body=body, headers=headers)])
                result = runner.capture(self.request)
                self.assertEqual(result['retrieval']['result'], 'invalid_response')
                self.assertIn(reason, result['retrieval']['reason'])
                self.assert_no_original(result)

    def test_robots_disallow_not_fetched_and_cached(self):
        robots = capture.Response('https://example.test/robots.txt', 200, {},
                                  b'User-agent: *\nDisallow: /allowed/\n')
        runner, fake = self.runner(robots=robots)
        for _ in range(2):
            result = runner.capture(self.request)
            self.assertEqual(result['retrieval']['result'], 'not_attempted')
            self.assertIn('robots.txt disallows', result['retrieval']['reason'])
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.originals(), [])

    def test_unknown_robots_stops_host_including_challenges_and_redirects(self):
        for status, headers, body in [(403, {}, b''), (429, {}, b''), (500, {}, b''),
                                       (200, {}, b'<html>error</html>'),
                                       (302, {'Location': '/policy'}, b''),
                                       (200, {'CF-Mitigated': 'challenge'}, b'')]:
            with self.subTest(status=status, headers=headers):
                robots = capture.Response('https://example.test/robots.txt', status, headers, body)
                runner, fake = self.runner(robots=robots)
                result = runner.capture(self.request)
                self.assertEqual(result['retrieval']['result'], 'not_attempted')
                self.assertIn('host stopped', result['retrieval']['reason'])
                runner.capture(self.request)
                self.assertEqual(len(fake.calls), 1)
                self.assert_no_original(result)

    def test_robots_wildcard_rules_must_never_be_ignored(self):
        robots = capture.Response('https://example.test/robots.txt', 200, {},
                                  b'User-agent: *\nDisallow: /allowed/*\n')
        runner, fake = self.runner(robots=robots)
        result = runner.capture(self.request)
        self.assertEqual(result['retrieval']['result'], 'not_attempted')
        self.assertEqual(fake.originals(), [])

    def test_robots_specific_groups_longest_rules_anchors_and_escaped_paths(self):
        policy = capture.Robots([
            'User-agent: *', 'Disallow: /',
            'User-agent: DocketClock-research', 'Disallow: /allowed/*',
            'Allow: /allowed/public/', 'Crawl-delay: 7.5',
            'User-agent: DocketClock-research', 'Disallow: /download?secret=*',
            'Disallow: /ending$', 'Disallow: /%70rivate/', 'Request-rate: 1/9',
        ], 5)
        self.assertTrue(policy.can_fetch('https://example.test/other'))
        self.assertFalse(policy.can_fetch('https://example.test/allowed/private'))
        self.assertTrue(policy.can_fetch('https://example.test/allowed/public/notice'))
        self.assertFalse(policy.can_fetch('https://example.test/download?secret=1'))
        self.assertFalse(policy.can_fetch('https://example.test/ending'))
        self.assertTrue(policy.can_fetch('https://example.test/ending/extra'))
        self.assertFalse(policy.can_fetch('https://example.test/private/one'))
        self.assertEqual(policy.interval, 9)
        tie = capture.Robots(['User-agent: *', 'Disallow: /same', 'Allow: /same'], 5)
        self.assertTrue(tie.can_fetch('https://example.test/same'))

    def test_redirect_target_must_also_pass_robots(self):
        robots = capture.Response('https://example.test/robots.txt', 200, {},
                                  b'User-agent: *\nDisallow: /allowed/private\n')
        runner, fake = self.runner([self.response(302, headers={'Location': '/allowed/private'})], robots=robots)
        result = runner.capture(self.request)
        self.assertIn('robots.txt disallows', result['retrieval']['reason'])
        self.assertEqual(len(fake.originals()), 1)
        self.assert_no_original(result)

    def test_robots_404_and_stricter_crawl_delay(self):
        for status, body, delay in [(404, b'', 5), (200, b'User-agent: *\nCrawl-delay: 12\n', 12)]:
            with self.subTest(status=status):
                robots = capture.Response('https://example.test/robots.txt', status, {}, body)
                runner, fake = self.runner([self.response()], robots=robots)
                self.assertEqual(runner.capture(self.request)['retrieval']['result'], 'retrieved')
                self.assertGreaterEqual(fake.calls[1][1] - fake.calls[0][1], delay)

    def test_post_body_content_type_and_method_provenance(self):
        self.request.update(method='POST', body='{"key":"value"}', content_type='application/json')
        runner, fake = self.runner([self.response()])
        result = runner.capture(self.request)
        request = fake.originals()[0][0]
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.data, b'{"key":"value"}')
        self.assertEqual(request.get_header('Content-type'), 'application/json')
        sha = result['retrieval']['sha256']
        metadata = json.loads((self.store / sha[:2] / (sha + '.metadata.json')).read_text())
        self.assertEqual(metadata['captures'][0]['capture_method'], 'POST')

    def test_cross_host_redirect_checks_new_robots_and_drops_credentials(self):
        self.surface['url_pattern'] = r'https://(example|second)\.test/allowed/.*'
        final = 'https://second.test/allowed/two'
        self.request.update(method='POST', body='payload', headers={'Authorization': 'secret', 'Cookie': 'session'})
        runner, fake = self.runner([self.response(303, headers={'Location': final}), self.response(url=final)])
        result = runner.capture(self.request)
        self.assertEqual(result['retrieval']['result'], 'retrieved')
        self.assertEqual(len(fake.calls), 4)  # Each host gets its own robots check.
        last = fake.originals()[-1][0]
        self.assertEqual(last.get_method(), 'GET')
        self.assertIsNone(last.data)
        self.assertIsNone(last.get_header('Authorization'))
        self.assertIsNone(last.get_header('Cookie'))

    def test_dry_run_no_network_or_store(self):
        runner, fake = self.runner(dry_run=True)
        result = runner.capture(self.request)
        self.assertIn('dry-run:', result['retrieval']['reason'])
        self.assertEqual(result['retrieval']['result'], 'not_attempted')
        self.assertIsNone(result['retrieval']['attempted_at'])
        self.assertEqual(fake.calls, [])
        self.assertFalse(self.store.exists())

    def test_default_transport_disables_proxy_redirects_and_http_error_retries(self):
        transport = capture.Transport()
        self.assertTrue(any(isinstance(h, capture.NoRedirect) for h in transport.opener.handlers))
        self.assertFalse(any(isinstance(h, capture.ProxyHandler) and h.proxies for h in transport.opener.handlers))
        error = capture.HTTPError(self.request['url'], 500, 'error', {}, io.BytesIO(b'error body'))
        with patch.object(transport.opener, 'open', side_effect=error) as opener:
            response = transport(Request(self.request['url']))
        self.assertEqual(response.status, 500)
        self.assertEqual(response.body, b'error body')
        self.assertEqual(opener.call_count, 1)

    def test_http_error_body_timeout_preserves_status_and_cannot_trigger_retry(self):
        transport = capture.Transport()
        class TimedOutBody(io.BytesIO):
            def read(self, *args):
                raise TimeoutError('body stalled')
        for status in (403, 429, 500):
            with self.subTest(status=status):
                error = capture.HTTPError(self.request['url'], status, 'error', {}, TimedOutBody())
                with patch.object(transport.opener, 'open', side_effect=error) as opener:
                    response = transport(Request(self.request['url']))
                self.assertEqual(response.status, status)
                self.assertIn('body stalled', response.read_error)
                self.assertEqual(opener.call_count, 1)
                runner, fake = self.runner([response])
                self.assertEqual(runner.capture(self.request)['retrieval']['http_status'], status)
                self.assertEqual(len(fake.originals()), 1)

    def test_cli_real_registry_dry_run_and_no_overwrite(self):
        root = Path(self.temporary.name)
        source, output = root / 'requests.jsonl', root / 'results.jsonl'
        source.write_text('\n'.join(json.dumps(r) for r in [
            {'manifest_entry_id': 'allowed', 'surface_id': 'wa-register', 'method': 'GET',
             'url': 'https://lawfilesext.leg.wa.gov/law/wsr/2026/20/26-20.pdf'},
            {'manifest_entry_id': 'held', 'surface_id': 'va-townhall-listings', 'method': 'GET',
             'url': 'https://townhall.virginia.gov/L/meetings.cfm'},
            {'manifest_entry_id': 'blocked', 'surface_id': 'ct-law-journal', 'method': 'GET',
             'url': 'https://www.jud.ct.gov/lawjournal/'}]) + '\n')
        with patch.object(capture.Transport, '__call__', side_effect=AssertionError('network forbidden')):
            with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                status = capture.main(['--requests', str(source), '--out', str(output),
                                       '--store', str(self.store), '--dry-run'])
        self.assertEqual(status, 1)  # Refusals remain gaps, including in a dry run.
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertIn('dry-run:', rows[0]['retrieval']['reason'])
        self.assertEqual(rows[1]['retrieval']['reason'], 'collection_rule=on_hold')
        self.assertEqual(rows[2]['retrieval']['reason'], 'collection_rule=blocked')
        self.assertEqual(len(stdout.getvalue().splitlines()), 3)
        self.assertEqual(json.loads(stderr.getvalue())['failures'], 2)
        self.assertFalse(self.store.exists())
        old_output = output.read_bytes()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(capture.main(['--requests', str(source), '--out', str(output), '--dry-run']), 2)
        self.assertEqual(output.read_bytes(), old_output)

    def test_cli_host_stop_exits_nonzero_and_reports_each_request(self):
        root = Path(self.temporary.name)
        source, output = root / 'requests.jsonl', root / 'results.jsonl'
        source.write_text((json.dumps(self.request) + '\n') * 2)
        runner, fake = self.runner([self.response(429)])
        with patch.object(capture, 'Capture', return_value=runner):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr:
                status = capture.main(['--requests', str(source), '--out', str(output)])
        self.assertEqual(status, 1)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual([r['retrieval']['result'] for r in rows], ['inaccessible', 'not_attempted'])
        self.assertEqual(len(fake.originals()), 1)
        self.assertIn('example.test', json.loads(stderr.getvalue())['stopped_hosts'])


if __name__ == '__main__':
    unittest.main()


class FailedResultShapeTest(unittest.TestCase):
    def test_http_404_has_null_byte_length(self):
        # Regression: a 404 kept the error page length, which the manifest schema rejects.
        import capture as cap
        orig = cap.Capture._capture
        def fake(self, request):
            return {'attempts': [{'url': 'u', 'http_status': 404}],
                    'retrieval': {'result': 'missing', 'byte_length': 209, 'http_status': 404}}
        cap.Capture._capture = fake
        try:
            obj = cap.Capture.__new__(cap.Capture)
            result = cap.Capture.capture(obj, {})
        finally:
            cap.Capture._capture = orig
        self.assertIsNone(result['retrieval']['byte_length'])
        self.assertEqual(result['attempts'][-1]['byte_length'], 209)

