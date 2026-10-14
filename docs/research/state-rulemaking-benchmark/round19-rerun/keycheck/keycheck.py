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
            'limit_remaining': None, 'limit_reset': None,
            'usage': None}
REQUIRED = ('label', 'limit', 'usage')
MASKED_LABEL_RE = re.compile(r'sk-or-v1-[0-9a-f]{3,8}\.\.\.[0-9a-f]{3,8}', re.ASCII)
FAILURE_STAGES = frozenset(('key_env_invalid', 'tls_context', 'connect',
    'request_send', 'response_status', 'body_too_large', 'key_echo_in_body',
    'json_parse', 'missing_fields', 'field_type', 'label_shape', 'deadline'))
DIAGNOSTIC_FIELDS = frozenset(EXPECTED) | {'name', 'is_free_tier', 'usage_*',
    'root', 'data', 'response_body', 'response_status'}
TYPE_NAMES = frozenset(('NoneType', 'bool', 'int', 'Decimal', 'str', 'list', 'dict',
    'float', 'bytes', 'other'))


class Rejected(RuntimeError):
    """Only fixed messages and allowlisted diagnostics cross the boundary."""
    def __init__(self, message='keycheck_rejected', failure=None):
        super().__init__(message)
        self.failure = failure


def failure_record(stage, *, status=None, error_code=None, missing=None,
                   field=None, type_name=None):
    require(stage in FAILURE_STAGES)
    record = {'schema_version': 'r18.keycheck-failure.v3', 'stage': stage}
    if stage == 'response_status':
        if type(status) is int:
            record['status'] = status
        if type(error_code) is int:
            record['error_code'] = error_code
    elif stage == 'missing_fields':
        require(type(missing) is list and all(n in EXPECTED or n == 'data' for n in missing))
        record['missing_fields'] = sorted(set(missing))
    elif stage == 'field_type':
        require(field in DIAGNOSTIC_FIELDS and type_name in TYPE_NAMES)
        record.update(field=field, type=type_name)
    return record


def reject(stage, **details):
    raise Rejected(stage, failure_record(stage, **details))


def typed(condition, field, item):
    if not condition:
        # Dynamic usage names and arbitrary Python class names are never copied.
        field = field if field in DIAGNOSTIC_FIELDS else 'usage_*'
        name = type(item).__name__
        reject('field_type', field=field, type_name=name if name in TYPE_NAMES else 'other')


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
        reject('deadline')
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


def decode_json(raw):
    def pairs(items):
        result = {}
        for name, value in items:
            if name in result:
                reject('json_parse')
            result[name] = value
        return result
    def constant(_value):
        reject('json_parse')
    return json.loads(raw.decode('utf-8'), parse_float=decimal.Decimal,
                      parse_int=int, parse_constant=constant, object_pairs_hook=pairs)


def contains_key(value, key):
    # Includes escaped strings in unknown fields, dictionary names and lists.
    if type(value) is str:
        return key in value
    if type(value) is dict:
        return any(contains_key(n, key) or contains_key(v, key) for n, v in value.items())
    if type(value) is list:
        return any(contains_key(v, key) for v in value)
    return False


def plain_name(value):
    return (0 < len(value) <= 100 and
            not re.search(r'sk-or-|bearer\s|authorization', value, re.I) and
            all(c.isprintable() for c in value))


def numeric(item):
    return item is None or (type(item) in (int, decimal.Decimal) and
        (type(item) is int or item.is_finite()) and item >= 0)


def parse_fields(raw, key):
    value = decode_json(raw)
    if contains_key(value, key):
        reject('key_echo_in_body')
    typed(type(value) is dict, 'root', value)
    if 'data' not in value:
        reject('missing_fields', missing=['data'])
    data = value['data']
    typed(type(data) is dict, 'data', data)
    missing = [name for name in REQUIRED if name not in data]
    if missing:
        reject('missing_fields', missing=missing)
    fields = {}
    masked = False
    for name, item in data.items():
        if name not in EXPECTED and name not in ('name', 'is_free_tier') and not re.fullmatch(r'usage_[a-z0-9_]+', name):
            continue
        if name in ('label', 'name'):
            typed(type(item) is str, name, item)
            if name == 'label' and MASKED_LABEL_RE.fullmatch(item):
                masked = True
                continue  # Never persist the masked credential fragment.
            if not plain_name(item):
                reject('label_shape')
        elif name == 'limit_reset':
            typed(item is None or type(item) is str, name, item)
            if item is not None and not plain_name(item):
                reject('label_shape')
        elif name == 'is_free_tier':
            typed(type(item) is bool, name, item)
        else:
            typed(numeric(item), name, item)
            if type(item) is int:
                item = decimal.Decimal(item)
        fields[name] = item
    reset_present = 'limit_reset' in fields
    fields.setdefault('limit_reset', None)
    remaining_computed = 'limit_remaining' not in fields
    if remaining_computed:
        limit, usage = fields['limit'], fields['usage']
        if limit is None or usage is None:
            reject('missing_fields', missing=['limit_remaining'])
        # Exact subtraction, including very small fractional usage. Bound the
        # exponent span before allocating precision for untrusted JSON numbers.
        span = max(limit.adjusted(), usage.adjusted(), 0) - min(
            limit.as_tuple().exponent, usage.as_tuple().exponent, 0) + 2
        typed(span <= MAX_RAW, 'limit_remaining', None)
        with decimal.localcontext() as ctx:
            ctx.prec = max(28, span)
            fields['limit_remaining'] = limit - usage
    label_check = (fields.get('name') == EXPECTED['label'] if masked and 'name' in fields
                   else 'not_machine_verifiable' if masked
                   else fields['label'] == EXPECTED['label'])
    if 'name' in fields and fields['name'] != EXPECTED['label']:
        label_check = False
    checks = {name: fields[name] == expected for name, expected in EXPECTED.items() if name != 'label'}
    checks['usage'] = fields['usage'] is not None and numeric(fields['usage'])
    if fields['limit'] is not None and fields['usage'] is not None:
        with decimal.localcontext() as ctx:
            span = max(fields['limit'].adjusted(), fields['usage'].adjusted(), 0) - min(
                fields['limit'].as_tuple().exponent, fields['usage'].as_tuple().exponent, 0) + 2
            typed(span <= MAX_RAW, 'limit_remaining', None)
            ctx.prec = max(28, span)
            checks['limit_remaining'] = fields['limit_remaining'] == fields['limit'] - fields['usage']
    else:
        checks['limit_remaining'] = False
    checks['label'] = label_check
    candidate = None
    if checks['usage']:
        with decimal.localcontext() as ctx:
            candidate_span = max(fields['usage'].adjusted(), 0) - min(fields['usage'].as_tuple().exponent, 0) + 12
            typed(candidate_span <= MAX_RAW, 'usage', None)
            ctx.prec = max(28, candidate_span)
            candidate = int((fields['usage'] * decimal.Decimal(10**9)).to_integral_value(rounding=decimal.ROUND_CEILING))
    metadata = {'key_initial_usage_candidate_usd': fields['usage'],
        'key_initial_usage_candidate_nanousd': candidate,
        'label_kind': 'masked_key' if masked else 'plain_name',
        'label_name_verifiable': not masked,
        'label_check': 'not_machine_verifiable' if label_check == 'not_machine_verifiable'
                       else 'match' if label_check is True else 'mismatch',
        'name_field_present': 'name' in fields,
        'user_attestation_required': masked and 'name' not in fields,
        'limit_reset_present': reset_present, 'limit_remaining_computed': remaining_computed}
    return fields, checks, metadata


def status_error_code(raw, key):
    # Best-effort integer extraction ONLY. Failure status wins over malformed,
    # oversized or credential-echoing error bodies; these bodies are discarded.
    code = None
    try:
        if type(raw) is bytes and len(raw) <= MAX_RAW and key.encode('ascii') not in raw:
            value = decode_json(raw)
            if not contains_key(value, key) and type(value) is dict:
                error = value.get('error')
                if type(error) is dict and type(error.get('code')) is int:
                    code = error['code']
    except Rejected as failure:
        if failure.failure and failure.failure['stage'] == 'deadline':
            raise
    except TimeoutError:
        raise
    except Exception:
        pass
    return code


def get_metadata_once():
    """One fixed authenticated HTTPS GET; failure exceptions contain no secrets."""
    connection = response = headers = raw = key = result = None
    failure = None
    stage = 'key_env_invalid'
    status = None
    try:
        key = os.environ.pop('OPENROUTER_API_KEY', None)
        require(isinstance(key, str) and bool(key) and key.isascii()
                and all(32 < ord(c) < 127 for c in key))
        require('OP_SERVICE_ACCOUNT_TOKEN' not in os.environ and 'TYPESAFE_API_KEY' not in os.environ)
        stage = 'deadline'
        with deadline():
            stage = 'tls_context'
            context, ca_sha256 = tls_context()
            stage = 'connect'
            connection = http.client.HTTPSConnection('openrouter.ai', timeout=TIMEOUT_SECONDS, context=context)
            connection.connect()  # Isolate DNS/TCP/TLS from sending the request.
            headers = {'Authorization': 'Bearer ' + key, 'Connection': 'close'}
            request_wall_ns = time.time_ns()
            stage = 'request_send'
            connection.request('GET', '/api/v1/key', body=None, headers=headers)
            stage = 'response_status'
            response = connection.getresponse()
            typed(type(response.status) is int, 'response_status', response.status)
            status = response.status
            raw = response.read(MAX_RAW + 1)
            if status != 200:
                reject('response_status', status=status, error_code=status_error_code(raw, key))
            typed(type(raw) is bytes, 'response_body', raw)
            if len(raw) > MAX_RAW:
                reject('body_too_large')
            if key.encode('ascii') in raw:
                reject('key_echo_in_body')
            retrieved_ns = time.time_ns()
            stage = 'json_parse'
            fields, checks, metadata = parse_fields(raw, key)
            passed = all(v is True for n, v in checks.items() if n != 'label') and (
                checks['label'] is True or checks['label'] == 'not_machine_verifiable')
            result = {'schema_version': 'r18.key-machine.v3', 'endpoint': ENDPOINT,
                'request_started_at': utc(request_wall_ns), 'retrieved_at': utc(retrieved_ns),
                'retrieved_wall_ns': retrieved_ns, 'response_sha256': hashlib.sha256(raw).hexdigest(),
                'tls_ca_sha256': ca_sha256, 'currency': 'USD', 'fields': fields,
                'checks': checks, **metadata, 'status': 'PASS' if passed else 'FAIL',
                'accepted_by_primary': False,
                'units_and_field_documentation_confirmed_by_primary': False}
    except Rejected as rejected:
        failure = rejected.failure or failure_record(stage, status=status)
    except TimeoutError:
        failure = failure_record('deadline')
    except BaseException:
        failure = failure_record(stage, status=status)
    finally:
        if connection is not None:
            try:
                connection.close()
            except BaseException:
                failure = failure or failure_record('connect')
        # Original exceptions/tracebacks are discarded. Clear secret holders
        # before constructing the outward exception outside the handler.
        del key, headers, connection, response, raw
    if failure is not None:
        raise Rejected(failure['stage'], failure)
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
    failure_path = output_dir / 'FAILURE.json'
    require(not any(os.path.lexists(p) for p in (key_path, timing_path, failure_path)))
    timing = bootstrap_timing()
    publish(timing_path, timing)  # Available even if the GET fails/is killed.
    try:
        record = get_metadata_once()
    except Rejected as rejected:
        if rejected.failure is not None:
            publish(failure_path, rejected.failure)
        raise
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
