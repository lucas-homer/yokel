"""key_info decimal preservation and envelope unwrapping, end to end into r17recon.parse_usd.

Exit 0 = every expectation held.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, install_fake_env, install_fake_transport, FakeSocket, http_response, SYNTHETIC_KEY, banner

a, t, d = load()
install_fake_env()
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def key(raw):
    install_fake_transport([FakeSocket(http_response(200, raw))])
    return d.key_info(d.KEY_URL)


banner('1. numeric tokens survive verbatim and parse exactly')
cases = {
    b'0.1': 100_000_000, b'0.10': 100_000_000, b'1.7300000000000000001': 1_730_000_001,
    b'1e-9': 1, b'1E-10': 1, b'0': 0, b'-0': 0, b'1.730e0': 1_730_000_000, b'0.000000001': 1,
    b'1234567890123456789': 1234567890123456789 * 10**9,   # 28 significant digits after *1e9
    b'0.3': 300_000_000,  # a float round trip would give 0.299999999999999988897769753748
}
# Note (pinned recon, not the driver): parse_usd uses the default Decimal context (28 digits),
# so a token with MORE than 28 significant digits is rounded half-even before the ceiling.
over = '1.0000000000000000000000000000001'
print('     (note) parse_usd(%s) = %d (exact ceiling would be 1000000001; >28 sig. digits never occur for USD)'
      % (over, a.recon.parse_usd(over)))
for token, nano in cases.items():
    raw = b'{"data":{"usage":' + token + b',"limit":null,"limit_remaining":null,"limit_reset":null,"label":"x"}}'
    fields = key(raw)['fields']
    parsed = a.strict(fields)
    check(fields == b'{"usage":' + token + b',"limit":null,"limit_remaining":null,"limit_reset":null}',
          'token %r emitted verbatim' % token)
    check(isinstance(parsed['usage'], a.Number) or type(parsed['usage']) is int, 'adapter sees raw token')
    check(a.money(parsed['usage']) == nano, 'parse_usd(%r) == %d' % (token, nano))

banner('2. adapter key_read on driver packets')
raw = b'{"data":{"usage":0.0123456789,"limit":1.73,"limit_remaining":1.7176543211,"limit_reset":null}}'
install_fake_transport([FakeSocket(http_response(200, raw))])
parsed, meta = a.key_read(d.key_info)
check(parsed == dict(usage=12_345_679, limit=1_730_000_000, limit_reset=None), 'usage rounded UP to nanoUSD: %r' % parsed)
check(meta['response_sha256'] == a.sha(raw), 'response_sha256 over original bytes')

banner('3. envelope and shape refusals (no key echo, no chained context)')
bad = [b'{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":null}',       # no data envelope
       b'[]', b'{"data":[]}', b'{"data":null}', b'{"data":{"usage":0}}',
       b'{"data":{"usage":"0.1","limit":1,"limit_remaining":1,"limit_reset":null}}',  # quoted number
       b'{"data":{"usage":NaN,"limit":1,"limit_remaining":1,"limit_reset":null}}',
       b'{"data":{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":0}}',       # numeric reset
       b'{"data":{"usage":{"a":1},"limit":1,"limit_remaining":1,"limit_reset":null}}',
       b'{"data":{"usage":0,"usage":1,"limit":1,"limit_remaining":1,"limit_reset":null}}',
       b'\xef\xbb\xbf{"data":{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":null}}',
       b'{"data":{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":"' + b'r' * 101 + b'"}}',
       b'{"data":{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":"' + SYNTHETIC_KEY.encode() + b'"}}']
for raw in bad:
    try:
        key(raw)
        check(False, 'should refuse %r' % raw[:40])
    except d.DriverError as exc:
        check(exc.__context__ is None and SYNTHETIC_KEY not in str(exc), 'refused %r -> %s' % (raw[:40], exc))

banner('4. permitted shapes')
raw = b'{"data":{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":"monthly"}}'
check(key(raw)['fields'] == b'{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":"monthly"}', 'string reset forwarded')
raw = b'{"data":{"usage":0,"limit":null,"limit_remaining":null,"limit_reset":null}}'
check(key(raw)['fields'] == b'{"usage":0,"limit":null,"limit_remaining":null,"limit_reset":null}', 'null limit forwarded (adapter halts on it)')
for status in (201, 204, 301, 401, 429, 500):
    install_fake_transport([FakeSocket(http_response(status, b'{"data":{"usage":0,"limit":1,"limit_remaining":1,"limit_reset":null}}'))])
    try:
        d.key_info(d.KEY_URL)
        check(False, 'status %d should refuse' % status)
    except d.DriverError:
        check(True, 'non-200 key status %d refused' % status)

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
