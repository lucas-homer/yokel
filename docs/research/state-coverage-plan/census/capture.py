#!/usr/bin/env python3
"""Rights-gated, sequential census capture (Python stdlib only).

Transport is a callable taking urllib.request.Request and returning Response. It MUST
perform a single HTTP exchange, without redirects or retries. The default disables
proxies and redirects; all redirect hops, robots checks and retries run through the
same rate limiter. Results are acquisition accounting, not a completeness verdict.
Custom --store locations contain the same relative hash layout; result paths remain
logical ~/yokel-captures/state-coverage paths required by the census validator.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

HOME = Path(__file__).resolve().parent
RIGHTS_FILE = HOME.parent / 'rights/surfaces.json'
STORE = '~/yokel-captures/state-coverage'
USER_AGENT = 'DocketClock-research/0.1 (+https://github.com/lucas-homer/yokel)'
REDIRECTS = {301, 302, 303, 307, 308}


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes
    read_error: str = None
    sha256: str = field(init=False)

    def __post_init__(self):
        # Hash every response before challenge detection or content decoding.
        self.sha256 = hashlib.sha256(self.body).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def tls_context():
    """Verified TLS context. Python.org macOS builds ship without CA certificates, so fall back to
    the system bundle; verification is never disabled."""
    import ssl

    context = ssl.create_default_context()
    if not context.get_ca_certs() and not os.environ.get("SSL_CERT_FILE"):
        for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
            if os.path.exists(cafile):
                context.load_verify_locations(cafile=cafile)
                break
    return context


class Transport:
    def __init__(self, timeout=60):
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=tls_context()))

    def __call__(self, request):
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except HTTPError as error:
            response = error  # Status errors are responses, never retry candidates.
        with response:
            read_error = None
            try:
                body = response.read()
            except http.client.IncompleteRead as error:
                body = error.partial
                read_error = 'incomplete response body'
            except (OSError, http.client.HTTPException) as error:
                body = b''
                read_error = f'response read failed: {error}'
            return Response(response.geturl(), response.code, dict(response.headers),
                            body, read_error)


def utc(clock):
    return datetime.fromtimestamp(clock(), timezone.utc).isoformat().replace('+00:00', 'Z')


class RateLimiter:
    """Hold the host's flock through the exchange; space from completion time.

    The timestamp is also persisted before sending, so a crashed worker still
    leaves a delay. Remember the strictest interval seen by any sharing process.
    Wall time (rather than process monotonic time) is shared across processes.
    """
    def __init__(self, store, clock=time.time, sleep=time.sleep):
        self.directory = Path(store) / '.ratelimit'
        self.clock, self.sleep = clock, sleep

    @contextmanager
    def hold(self, host, interval):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / host).open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            lock.seek(0)
            previous = lock.read()
            state = json.loads(previous) if previous else {}
            interval = max(5, interval, state.get('interval', 5))
            if 'timestamp' in state:
                while True:
                    remaining = state['timestamp'] + interval - self.clock()
                    if remaining <= 0:
                        break
                    self.sleep(remaining)

            def save():
                lock.seek(0)
                lock.truncate()
                json.dump({'timestamp': self.clock(), 'interval': interval}, lock)
                lock.flush()
                os.fsync(lock.fileno())

            save()
            try:
                yield
            finally:
                save()
                fcntl.flock(lock, fcntl.LOCK_UN)


def atomic_write(path, data):
    """Replace a complete file on the same filesystem; never expose partial bytes."""
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_capture(store, response, request, surface, timestamp):
    sha = response.sha256
    path = store / sha[:2] / sha
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = path.with_name(sha + '.metadata.json')
    # Serialize provenance updates even when different hosts produce the same hash.
    with path.with_name(sha + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() != response.body:
                raise ValueError('existing hash-store bytes do not match response')
        else:
            atomic_write(path, response.body)
        metadata = (json.loads(sidecar.read_text()) if sidecar.exists() else
                    {'schema_version': '1.0.0', 'sha256': sha,
                     'byte_length': len(response.body), 'captures': []})
        if (metadata['schema_version'] != '1.0.0' or metadata['sha256'] != sha or
                metadata['byte_length'] != len(response.body)):
            raise ValueError('existing sidecar identity mismatch')
        metadata['captures'].append({
            'manifest_entry_id': request['manifest_entry_id'],
            'requested_url': request['url'], 'final_url': response.url,
            'capture_method': request['method'], 'response_headers': response.headers,
            'captured_at': timestamp, 'rights_surface_id': surface['surface_id'],
            'rights_version': surface['version'],
        })
        atomic_write(sidecar, (json.dumps(metadata, indent=2, ensure_ascii=False) + '\n').encode())
    logical = f'{STORE}/{sha[:2]}/{sha}'
    return sha, logical, logical + '.metadata.json'


def safe_url(url):
    if not isinstance(url, str) or not url or re.search(r'[\s\x00-\x1f\x7f]', url):
        return False
    try:
        parts = urlsplit(url)
        return (parts.scheme in ('http', 'https') and bool(parts.hostname) and
                not parts.username and not parts.password and not parts.fragment and
                parts.port in (None, 80, 443) and
                re.fullmatch(r'[a-zA-Z0-9.-]+', parts.hostname) is not None)
    except ValueError:
        return False


def connection_error(error):
    if isinstance(error, URLError):
        error = error.reason
    return isinstance(error, (TimeoutError, ConnectionError, socket.gaierror))


def challenge(response):
    headers = {k.lower(): v.lower() for k, v in response.headers.items()}
    text = response.body[:262144].decode('utf-8', errors='replace').lower()
    return (headers.get('cf-mitigated') == 'challenge' or
            'challenge-platform' in text or 'cf-chl-' in text or
            bool(re.search(r'<title[^>]*>\s*just a moment', text)))


def content_checks(response):
    errors = []
    headers = {k.lower(): v for k, v in response.headers.items()}
    kind = headers.get('content-type', '').split(';')[0].lower().strip()
    if response.read_error:
        errors.append(response.read_error)
    if not response.body.strip():
        errors.append('empty body')
    if 'content-length' in headers:
        try:
            if int(headers['content-length']) != len(response.body):
                errors.append('content-length mismatch (possible truncation)')
        except ValueError:
            errors.append('invalid content-length')
    if kind == 'application/json' or kind.endswith('+json') or kind == 'text/json':
        try:
            json.loads(response.body)
        except (ValueError, UnicodeError):
            errors.append('invalid or truncated JSON')
    text = response.body[:262144].decode('utf-8', errors='replace').lower()
    if ('html' in kind or text.lstrip().startswith(('<!doctype html', '<html'))):
        if re.search(r'<(?:title|h1)\b[^>]*>\s*(?:error\b|[45]\d\d\b|'
                     r'access denied\b|forbidden\b|not found\b|page not found\b|'
                     r'service unavailable\b|internal server error\b)', text):
            errors.append('HTML error page')
    return errors


def robots_path(value):
    """Normalize URI octets without equating escaped reserved bytes with syntax."""
    value = quote(value, safe="/%?:@!$&'()+,;=-._~*")
    def escape(match):
        character = chr(int(match[1], 16))
        return character if character in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~' else match[0].upper()
    return re.sub(r'%([a-fA-F0-9]{2})', escape, value)


class Robots:
    """REP path rules, including wildcards/end anchors and merged agent groups.

    urllib.robotparser treats wildcard paths literally and uses first-match
    precedence. Here the most specific matching agent groups are merged, then
    the longest matching path wins (Allow wins equal-length ties).
    """
    def __init__(self, lines, minimum):
        groups = []
        agents, rules, delays, directives = [], [], [], False
        for line in list(lines) + ['User-agent: __end__']:
            name, separator, value = line.split('#', 1)[0].partition(':')
            if not separator:
                continue
            name, value = name.strip().lower(), value.strip()
            if name == 'user-agent':
                if directives:
                    groups.append((agents, rules, delays))
                    agents, rules, delays, directives = [], [], [], False
                agents.append(value.lower())
            elif agents:
                directives = True
                if name in ('allow', 'disallow') and value:
                    rules.append((name == 'allow', robots_path(value)))
                elif name == 'crawl-delay':
                    delay = float(value)
                    if not math.isfinite(delay) or delay < 0:
                        raise ValueError('invalid robots crawl-delay')
                    delays.append(delay)
                elif name == 'request-rate':
                    rate = re.fullmatch(r'(\d+)\s*/\s*(\d+)', value)
                    if not rate or int(rate[1]) == 0 or int(rate[2]) == 0:
                        raise ValueError('invalid robots request-rate')
                    delays.append(int(rate[2]) / int(rate[1]))
        product = USER_AGENT.split('/')[0].lower()
        selected, specificity = [], -1
        for agents, rules, delays in groups:
            score = max((0 if agent == '*' else len(agent)
                         for agent in agents if agent == '*' or (agent and agent in product)), default=-1)
            if score > specificity:
                selected, specificity = [], score
            if score == specificity and score >= 0:
                selected.append((rules, delays))
        self.rules = [rule for rules, _ in selected for rule in rules]
        self.interval = max([minimum] + [delay for _, delays in selected for delay in delays])

    def can_fetch(self, url):
        parts = urlsplit(url)
        target = robots_path((parts.path or '/') + ('?' + parts.query if parts.query else ''))
        matches = []
        for allow, rule in self.rules:
            anchor = rule.endswith('$')
            pattern = rule[:-1] if anchor else rule
            expression = '^' + '.*'.join(re.escape(piece) for piece in pattern.split('*'))
            if re.search(expression + ('$' if anchor else ''), target):
                length = len(re.sub(r'%[0-9A-F]{2}', 'x', pattern.replace('*', '')))
                matches.append((length, allow))
        return max(matches, default=(0, True))[1]


class Capture:
    def __init__(self, store=STORE, *, surfaces=None, attended=False, dry_run=False,
                 transport=None, clock=time.time, sleep=time.sleep):
        records = json.loads(RIGHTS_FILE.read_text()) if surfaces is None else surfaces
        self.surfaces = {}
        for surface in records:
            sid = surface['surface_id']
            if sid in self.surfaces:
                raise ValueError('duplicate surface_id: ' + sid)
            re.compile(surface['url_pattern'])
            rate = surface['rate']['min_interval_seconds']
            if not isinstance(rate, (float, int)) or not math.isfinite(rate) or rate < 5:
                raise ValueError('invalid surface rate: ' + sid)
            self.surfaces[sid] = surface
        self.store = Path(store).expanduser()
        self.attended, self.dry_run = attended, dry_run
        self.transport = transport if transport is not None else Transport()
        self.clock = clock
        self.limiter = RateLimiter(self.store, clock, sleep)
        self.robots = {}
        self.stopped = {}

    def gate(self, request):
        if not isinstance(request, dict):
            return None, 'request must be an object'
        sid = request.get('surface_id')
        surface = self.surfaces.get(sid) if isinstance(sid, str) else None
        for name in ('manifest_entry_id', 'surface_id', 'url'):
            if not isinstance(request.get(name), str) or not request[name]:
                return surface, 'missing or invalid ' + name
        if request.get('method') not in ('GET', 'POST'):
            return surface, 'method must be GET or POST'
        if not safe_url(request['url']):
            return surface, 'unsafe or invalid URL'
        headers = request.get('headers', {})
        if not isinstance(headers, dict) or any(
                not isinstance(k, str) or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", k) or
                not isinstance(v, str) or re.search(r'[\r\n\x00]', v)
                for k, v in headers.items()):
            return surface, 'invalid request headers'
        for name in ('body', 'content_type'):
            if name in request and not isinstance(request[name], str):
                return surface, 'invalid ' + name
        if re.search(r'[\r\n\x00]', request.get('content_type', '')):
            return surface, 'invalid content_type'
        if not surface:
            return None, 'unknown surface_id'
        if not re.fullmatch(surface['url_pattern'], request['url']):
            return surface, 'URL outside authorized surface pattern'
        rule = surface['collection_rule']
        if rule not in ('allowed', 'allowed_watched_only'):
            return surface, 'collection_rule=' + rule
        if rule == 'allowed_watched_only' and not self.attended:
            return surface, 'watched-only surface requires --attended'
        if surface['retention'] != 'internal_originals':
            return surface, 'original retention not authorized'
        return surface, None

    def fetch(self, url, method, headers, body, interval, attempts, budget):
        host = urlsplit(url).hostname.lower()
        while True:
            attempt = {'url': url, 'method': method, 'attempted_at': None,
                       'http_status': None, 'reason': None}
            attempts.append(attempt)
            try:
                with self.limiter.hold(host, interval):
                    attempt['attempted_at'] = utc(self.clock)
                    response = self.transport(Request(url, data=body, headers=headers, method=method))
                attempt['http_status'] = response.status
                if response.status in (403, 429) or challenge(response):
                    reason = ('bot challenge' if challenge(response) else
                              f'HTTP {response.status}')
                    self.stopped[host] = reason
                    attempt['reason'] = reason
                return response
            except Exception as error:
                attempt['reason'] = f'{type(error).__name__}: {error}'
                if connection_error(error) and budget[0]:
                    budget[0] -= 1
                    continue
                raise

    def robots_for(self, url, interval, attempts, budget):
        parts = urlsplit(url)
        host = parts.hostname.lower()
        if host in self.robots:
            return self.robots[host]
        robots_url = f'{parts.scheme}://{parts.netloc}/robots.txt'
        try:
            response = self.fetch(robots_url, 'GET', {'User-Agent': USER_AGENT},
                                  None, interval, attempts, budget)
            if host in self.stopped:
                return None
            if response.url != robots_url or response.status in REDIRECTS:
                raise ValueError('robots redirect: policy unknown (not followed)')
            if response.read_error:
                raise ValueError(response.read_error)
            if response.status in (404, 410):
                lines = []
            elif response.status == 200:
                kind = next((v for k, v in response.headers.items() if k.lower() == 'content-type'), '')
                if 'html' in kind.lower() or response.body.lstrip().lower().startswith((b'<html', b'<!doctype html')):
                    raise ValueError('robots returned HTML instead of a policy')
                lines = response.body.decode('utf-8-sig', errors='strict').splitlines()
            else:
                raise ValueError(f'robots HTTP {response.status}: policy unknown')
            policy = Robots(lines, interval)
            self.robots[host] = policy
            return policy
        except Exception as error:
            self.stopped[host] = f'robots unknown: {error}'
            return None

    def capture(self, request):
        surface, refusal = self.gate(request)
        request = request if isinstance(request, dict) else {}
        result = {
            'manifest_entry_id': request.get('manifest_entry_id'),
            'surface_id': request.get('surface_id'),
            'rights_version': surface['version'] if surface else None,
            'attended': self.attended, 'dry_run': self.dry_run,
            'content_checks': [], 'attempts': [],
            'retrieval': {
                'result': 'not_attempted', 'requested_url': request.get('url') or '(invalid request)',
                'final_url': None, 'attempted_at': None, 'http_status': None,
                'content_type': None, 'sha256': None, 'byte_length': None,
                'storage_path': None, 'sidecar_path': None, 'reason': refusal,
            },
        }
        ret = result['retrieval']
        if refusal:
            return result
        if self.dry_run:
            ret['reason'] = 'dry-run: rights and request validated; no network attempted'
            return result
        url = request['url']
        method = request['method']
        body = request.get('body')
        body = body.encode('utf-8') if body is not None else None
        # Neither caller nor environment may change identity or route through a proxy.
        headers = {k: v for k, v in request.get('headers', {}).items()
                   if k.lower() not in ('user-agent', 'host', 'proxy-authorization',
                                        'proxy-connection', 'accept-encoding', 'content-length')}
        headers['User-Agent'] = USER_AGENT
        headers['Accept-Encoding'] = 'identity'
        if 'content_type' in request:
            headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
            headers['Content-Type'] = request['content_type']
        budget = [1]  # At most one connection retry across robots and all redirect hops.
        interval = surface['rate']['min_interval_seconds']
        try:
            for hop in range(11):
                host = urlsplit(url).hostname.lower()
                if host in self.stopped:
                    ret['reason'] = 'host stopped: ' + self.stopped[host]
                    return result
                policy = self.robots_for(url, interval, result['attempts'], budget)
                if policy is None:
                    ret['reason'] = 'host stopped: ' + self.stopped[host]
                    return result
                if not policy.can_fetch(url):
                    ret['reason'] = 'robots.txt disallows URL'
                    return result
                ret['attempted_at'] = utc(self.clock)
                response = self.fetch(url, method, headers, body, max(interval, policy.interval),
                                      result['attempts'], budget)
                ret.update(final_url=response.url, http_status=response.status,
                           content_type=next((v for k, v in response.headers.items()
                                              if k.lower() == 'content-type'), None),
                           attempted_at=result['attempts'][-1]['attempted_at'],
                           byte_length=len(response.body))
                if host in self.stopped:
                    ret.update(result='inaccessible', reason=self.stopped[host])
                    return result
                if not safe_url(response.url) or not re.fullmatch(surface['url_pattern'], response.url):
                    self.stopped[host] = 'off-pattern final URL: ' + response.url
                    ret.update(result='invalid_response', reason=self.stopped[host])
                    return result
                if response.status in REDIRECTS:
                    location = next((v for k, v in response.headers.items() if k.lower() == 'location'), None)
                    destination = urljoin(url, location) if location else None
                    if not destination or not safe_url(destination) or not re.fullmatch(surface['url_pattern'], destination):
                        self.stopped[host] = 'redirect outside authorized surface: ' + str(destination)
                        ret.update(result='invalid_response', reason=self.stopped[host])
                        return result
                    if hop == 10:
                        ret.update(result='invalid_response', reason='redirect limit exceeded')
                        return result
                    if urlsplit(destination).netloc != urlsplit(url).netloc:
                        headers = {k: v for k, v in headers.items()
                                   if k.lower() not in ('authorization', 'cookie')}
                    if response.status == 303 or (response.status in (301, 302) and method == 'POST'):
                        method, body = 'GET', None
                        headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
                    url = destination
                    continue
                if not 200 <= response.status < 300:
                    ret.update(result='missing' if response.status in (404, 410) else 'inaccessible',
                               reason=f'HTTP {response.status}; no retry')
                    return result
                errors = content_checks(response)
                if surface['surface_id'] == 'ct-rendered' and 'json' in (ret['content_type'] or '').lower():
                    errors.append('CT rendered surface does not authorize JSON retention')
                result['content_checks'] = errors
                if errors:
                    ret.update(result='invalid_response', reason='; '.join(errors))
                    return result
                sha, storage, sidecar = save_capture(self.store, response, request, surface,
                                                    ret['attempted_at'])
                ret.update(result='retrieved', sha256=sha, storage_path=storage,
                           sidecar_path=sidecar, reason=None)
                return result
        except Exception as error:
            ret.update(result='inaccessible', reason=f'{type(error).__name__}: {error}')
            return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests', required=True, type=Path, help='UTF-8 request JSONL')
    parser.add_argument('--out', required=True, type=Path, help='result JSONL (created exclusively)')
    parser.add_argument('--attended', action='store_true', help='attest this is an attended run')
    parser.add_argument('--dry-run', action='store_true', help='validate requests and rights; no network or store writes')
    parser.add_argument('--store', default=STORE, help='external hash-store root (default: %(default)s)')
    args = parser.parse_args(argv)
    counts = Counter()
    failures = 0
    try:
        capture = Capture(args.store, attended=args.attended, dry_run=args.dry_run)
        with args.requests.open(encoding='utf-8') as source, args.out.open('x', encoding='utf-8') as output:
            for number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                try:
                    request = json.loads(line)
                    result = capture.capture(request)
                except (ValueError, TypeError) as error:
                    result = capture.capture({})
                    result['retrieval']['reason'] = f'invalid request line {number}: {error}'
                status = result['retrieval']['result']
                counts[status] += 1
                valid_dry_run = args.dry_run and result['retrieval']['reason'].startswith('dry-run:')
                failures += status != 'retrieved' and not valid_dry_run
                encoded = json.dumps(result, ensure_ascii=False)
                output.write(encoded + '\n')
                output.flush()
                print(encoded)
        print(json.dumps({'summary': dict(counts), 'failures': failures,
                          'stopped_hosts': capture.stopped}), file=sys.stderr)
        return 1 if failures else 0
    except (OSError, ValueError, KeyError) as error:
        print(f'capture: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
