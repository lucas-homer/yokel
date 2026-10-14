"""Metadata-only signed adapter; import is inert. Staged basename must be adapter.py."""
import time

# Earliest Python-side boundary: time import/interpreter startup precede this.
ENTRY_MONOTONIC_NS = time.monotonic_ns()
ENTRY_WALL_NS = time.time_ns()

import contextlib
import datetime
import decimal
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import ssl
import sys
import threading

ENDPOINT = 'https://openrouter.ai/api/v1/key'
CA_BUNDLE = Path('/etc/ssl/cert.pem')
PYTHON = Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
MAX_RAW = 65536
TIMEOUT_SECONDS = 15
EXPECTED = {'label': 'DocketClock', 'limit': decimal.Decimal('50.00'),
            'limit_remaining': decimal.Decimal('50.00'), 'limit_reset': None,
            'usage': decimal.Decimal('0')}


class Rejected(RuntimeError):
    """Only fixed messages may cross the transport boundary."""


def require(condition):
    if not condition:
        raise Rejected('keycheck_rejected')


def utc(ns):
    return datetime.datetime.fromtimestamp(ns / 1_000_000_000,
        datetime.timezone.utc).isoformat(timespec='microseconds')


def encode(value):
    """Emit Decimal as JSON numbers, retaining exact decimal values (never float)."""
    if isinstance(value, decimal.Decimal):
        require(value.is_finite())
        return str(value)
    if isinstance(value, dict):
        return '{' + ','.join(encode(k) + ':' + encode(v)
                             for k, v in sorted(value.items())) + '}'
    if isinstance(value, list):
        return '[' + ','.join(encode(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def publish(path, value):
    """Exclusive, owner-only and durable; never overwrite a previous attempt."""
    raw = (encode(value) + '\n').encode('utf-8')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def deadline():
    # Includes CA loading, DNS, connection, headers and trickled body; no retries.
    require(threading.current_thread() is threading.main_thread())
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0))
    old = signal.getsignal(signal.SIGALRM)
    def expired(_signum, _frame):
        raise Rejected('metadata_deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, TIMEOUT_SECONDS)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def tls_context():
    # Explicit trust file; avoid SSLKEYLOGFILE and SSL_CERT_* default discovery.
    raw = CA_BUNDLE.read_bytes()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(CA_BUNDLE))
    require(context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname)
    require(context.cert_store_stats()['x509_ca'] > 0)
    require(CA_BUNDLE.read_bytes() == raw)
    return context, hashlib.sha256(raw).hexdigest()


def parse_fields(raw, key):
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result)
            result[name] = value
        return result
    def constant(_value):
        raise Rejected('invalid_metadata')
    value = json.loads(raw.decode('utf-8'), parse_float=decimal.Decimal,
                       parse_int=decimal.Decimal, parse_constant=constant,
                       object_pairs_hook=pairs)
    require(type(value) is dict and type(value.get('data')) is dict)
    data = value['data']
    require(set(EXPECTED) <= set(data))
    fields = {}
    for name, item in data.items():
        if name not in EXPECTED and name != 'is_free_tier' and not re.fullmatch(r'usage_[a-z0-9_]+', name):
            continue
        # No nested/free-form usage values; unknown top-level fields are discarded.
        require(key not in name)
        if name == 'label':
            require(type(item) is str and len(item) <= 100 and key not in item)
            require(not re.search(r'sk-or-|bearer\s|authorization', item, re.I))
        elif name == 'limit_reset':
            require(item is None or (type(item) is str and len(item) <= 100
                    and key not in item and not re.search(r'sk-or-|bearer\s|authorization', item, re.I)))
        elif name == 'is_free_tier':
            require(type(item) is bool)
        else:
            require(item is None or (isinstance(item, decimal.Decimal)
                    and item.is_finite() and item >= 0))
        fields[name] = item
    # Catch escaped credential echoes in otherwise allowed fields/names.
    require(key not in encode(fields))
    return fields


def get_metadata_once():
    """Only transport path: one fixed authenticated HTTPS GET, no redirect/retry."""
    connection = response = headers = raw = key = result = None
    failed = False
    try:
        # Consume the injected variable inside this call; it is absent thereafter.
        key = os.environ.pop('OPENROUTER_API_KEY', None)
        require(isinstance(key, str) and bool(key) and key.isascii()
                and all(32 < ord(c) < 127 for c in key))
        require('OP_SERVICE_ACCOUNT_TOKEN' not in os.environ and 'TYPESAFE_API_KEY' not in os.environ)
        with deadline():
            context, ca_sha256 = tls_context()
            connection = http.client.HTTPSConnection('openrouter.ai', timeout=TIMEOUT_SECONDS, context=context)
            headers = {'Authorization': 'Bearer ' + key, 'Connection': 'close'}
            request_wall_ns = time.time_ns()
            connection.request('GET', '/api/v1/key', body=None, headers=headers)
            response = connection.getresponse()
            require(type(response.status) is int and response.status == 200)
            raw = response.read(MAX_RAW + 1)
            require(type(raw) is bytes and len(raw) <= MAX_RAW and key.encode('ascii') not in raw)
            retrieved_ns = time.time_ns()
            fields = parse_fields(raw, key)
            checks = {name: fields[name] == expected for name, expected in EXPECTED.items()}
            result = {'schema_version': 'r17.key-machine.v1', 'endpoint': ENDPOINT,
                'request_started_at': utc(request_wall_ns), 'retrieved_at': utc(retrieved_ns),
                'retrieved_wall_ns': retrieved_ns, 'response_sha256': hashlib.sha256(raw).hexdigest(),
                'tls_ca_sha256': ca_sha256, 'currency': 'USD', 'fields': fields,
                'checks': checks, 'status': 'PASS' if all(checks.values()) else 'FAIL',
                'accepted_by_primary': False,
                'units_and_field_documentation_confirmed_by_primary': False}
    except BaseException:
        failed = True
    finally:
        if connection is not None:
            try:
                connection.close()
            except BaseException:
                failed = True
        # No original transport/parser exception or secret-bearing locals survive.
        del key, headers, connection, response, raw
    if failed:
        # Raised outside the handler: no credential-bearing exception context.
        raise Rejected('metadata_failed')
    return result


def bootstrap_timing():
    ready_monotonic_ns = time.monotonic_ns()
    ready_wall_ns = time.time_ns()
    return {'schema_version': 'r17.bootstrap-timing.v1',
        'adapter_entry_monotonic_ns': ENTRY_MONOTONIC_NS,
        'adapter_entry_wall_ns': ENTRY_WALL_NS, 'adapter_entry_at': utc(ENTRY_WALL_NS),
        'adapter_ready_monotonic_ns': ready_monotonic_ns,
        'adapter_ready_wall_ns': ready_wall_ns, 'adapter_ready_at': utc(ready_wall_ns),
        'adapter_initialization_seconds': decimal.Decimal(ready_monotonic_ns - ENTRY_MONOTONIC_NS) / decimal.Decimal(10**9),
        'runner_start_exposed': False, 'runner_start_monotonic_ns': None,
        'bootstrap_seconds': None, 'native_reserve_seconds': None,
        'accepted_by_primary': False,
        'boundaries': {'entry': 'After import time, before remaining adapter imports.',
            'ready': 'After argument/output preflight, immediately before timing publication and metadata GET.',
            'missing': 'Native launch/deadline, op resolution, pre-exec pin hashing, interpreter startup and import time are not exposed by the runner.'}}


def run(output_dir):
    output_dir = Path(output_dir)
    key_path = output_dir / 'KEY-MACHINE.json'
    timing_path = output_dir / 'BOOTSTRAP-TIMING.json'
    require(not os.path.lexists(key_path) and not os.path.lexists(timing_path))
    timing = bootstrap_timing()
    publish(timing_path, timing)  # Available even if the GET fails/is killed.
    record = get_metadata_once()
    publish(key_path, record)
    return 0 if record['status'] == 'PASS' else 1


def main():
    try:
        require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
        require(Path(sys.executable).resolve() == PYTHON.resolve())
        require(sys.argv[1:] == ['--live-initial'])
        result = run(Path(__file__).resolve().parent)
        print('Metadata check PASS.' if result == 0 else 'Metadata check FAIL.')
        return result
    except BaseException:
        print('Metadata check rejected.')
        return 1
    finally:
        # Delete on preflight failure without fetching a credential value here.
        try:
            del os.environ['OPENROUTER_API_KEY']
        except KeyError:
            pass


if __name__ == '__main__':
    sys.exit(main())
