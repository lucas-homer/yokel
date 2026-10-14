"""Reviewed offline candidate. Import is inert; only explicit callbacks can use HTTPS.

Run one cell with python3 -I -S -B host_driver.py and the adapter CLI arguments,
except --driver and --driver-sha256 (derived from this file). No stale-lock removal.
"""
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import ssl
import sys

HERE = Path(__file__).resolve().parent
POST_URL = 'https://openrouter.ai/api/v1/chat/completions'
KEY_URL = 'https://openrouter.ai/api/v1/key'
MAX_RAW = 2_000_000
TIMEOUT_S = 60
HEADER_NAMES = {'content-type', 'date', 'x-request-id', 'x-openrouter-request-id',
                'x-openai-request-id', 'openai-request-id'}


class DriverError(RuntimeError):
    """Messages are fixed strings, with no retained transport exception context."""


def filter_headers(headers):
    result = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        name = name.lower()
        if name not in HEADER_NAMES and not re.fullmatch(r'x-ratelimit-[a-z0-9-]+', name):
            continue
        if re.search(r'sk-or-|bearer\s|authorization|set-cookie', value, re.I):
            continue
        if '\r' in value or '\n' in value:
            continue
        result[name] = value[:1024]
    return result


def _tls_context():
    # PROTOCOL_TLS_CLIENT enables CERT_REQUIRED + hostname checking. Avoid
    # create_default_context's SSLKEYLOGFILE lookup; this driver never enables logs.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    return context


def _request(method, path, body, key):
    """Raw http.client has no redirect/retry/proxy machinery. One fresh TLS session."""
    connection, packet, failed = None, None, False
    try:
        if not isinstance(key, str) or not key or not key.isascii() or any(c.isspace() for c in key):
            raise DriverError('credential_unavailable')
        context = _tls_context()
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise DriverError('tls_unverified')
        connection = http.client.HTTPSConnection('openrouter.ai', timeout=TIMEOUT_S, context=context)
        headers = {'Authorization': 'Bearer ' + key, 'Connection': 'close'}
        if method == 'POST':
            headers.update({'Content-Type': 'application/json', 'Content-Length': str(len(body))})
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        # The sentinel byte detects overflow without an unbounded read or second read.
        raw = response.read(MAX_RAW + 1)
        if not isinstance(raw, bytes) or len(raw) > MAX_RAW:
            raise DriverError('body_overflow')
        if type(response.status) is not int or not 100 <= response.status <= 599:
            raise DriverError('status_invalid')
        # A credential echoed in any permitted response field never crosses the seam.
        safe_headers = filter_headers(dict(response.getheaders()))
        if key.encode('ascii') in raw or any(key in v for v in safe_headers.values()):
            raise DriverError('response_sensitive')
        packet = dict(status=response.status, raw=raw, headers=safe_headers)
    except Exception:
        failed = True
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                failed = True
    # Raise outside the except block: __context__ cannot retain the original exception.
    if failed:
        raise DriverError('transport_failed')
    return packet


def post_once(url, exact_bytes):
    if url != POST_URL or type(exact_bytes) is not bytes:
        raise DriverError('request_refused')
    key = os.environ.get('OPENROUTER_API_KEY')
    return _request('POST', '/api/v1/chat/completions', exact_bytes, key)


class Token(str):
    """Raw numeric JSON token; never converted through float."""


def _key_fields(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise DriverError('key_response_invalid')
            result[k] = v
        return result
    def constant(_):
        raise DriverError('key_response_invalid')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_float=Token,
                       parse_int=Token, parse_constant=constant)
    data = value['data']
    if not isinstance(data, dict):
        raise DriverError('key_response_invalid')
    fields = []
    for name in ('usage', 'limit', 'limit_remaining', 'limit_reset'):
        v = data[name]
        if name == 'limit_reset':
            if v is not None and (type(v) is not str or len(v) > 100):
                raise DriverError('key_response_invalid')
            token = json.dumps(v, ensure_ascii=False, allow_nan=False)
        elif isinstance(v, Token):
            token = str(v)
        elif v is None:
            token = 'null'
        else:
            raise DriverError('key_response_invalid')
        fields.append(json.dumps(name) + ':' + token)
    return ('{' + ','.join(fields) + '}').encode('utf-8')


def key_info(url):
    if url != KEY_URL:
        raise DriverError('request_refused')
    key = os.environ.get('OPENROUTER_API_KEY')
    packet = _request('GET', '/api/v1/key', None, key)
    failed, fields = False, None
    try:
        if packet['status'] != 200:
            raise DriverError('key_http_status')
        fields = _key_fields(packet['raw'])
    except Exception:
        failed = True
    if failed:
        raise DriverError('key_response_invalid')
    return dict(fields=fields, response_sha256=hashlib.sha256(packet['raw']).hexdigest())


def source(cell):
    """Exact UTF-8 source, with no newline translation or alternate source fallback."""
    if cell not in [f'S{i}-{arm}' for arm in ('OPQ', 'FULL') for i in (1, 2, 3)]:
        raise DriverError('source_cell_invalid')
    root = HERE.parent / 'sources-r2'
    ready = json.loads((root / 'READY.json').read_bytes())
    selected = ready['selected']
    if (not isinstance(selected, list) or len(selected) != 3 or selected != sorted(selected)
            or len(set(selected)) != 3
            or not all(isinstance(s, str) and re.fullmatch(r'[A-Za-z0-9_-]+', s) for s in selected)):
        raise DriverError('source_metadata_invalid')
    raw = (root / selected[int(cell[1]) - 1] / 'parsed-body.txt').read_bytes()
    return raw.decode('utf-8')


def main(argv=None):
    # No imports of benchmark executables and no credential lookup at module import.
    path = HERE / 'r17_adapter.py'
    spec = importlib.util.spec_from_file_location('r17_host_adapter', path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    args = list(sys.argv[1:] if argv is None else argv)
    if any(v == '--driver' or v == '--driver-sha256' or v.startswith('--driver=')
           or v.startswith('--driver-sha256=') for v in args):
        print('R17 refusal: driver_override. No retry.', file=sys.stderr)
        return 2
    args += ['--driver', str(HERE / 'host_driver.py'), '--driver-sha256',
             hashlib.sha256((HERE / 'host_driver.py').read_bytes()).hexdigest()]
    return adapter.main(args, recover_first=True)


if __name__ == '__main__':
    sys.exit(main())
