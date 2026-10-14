"""host_driver._request through the REAL http.client with a fake socket (no network).

Checks: exact request bytes on the wire, exactly one request per call, no Expect /
100-continue negotiation, a server-side 100 Continue preamble is consumed without a
re-send, redirects not followed, a broken pipe during send makes one attempt and the
error carries no key, a chunked body over MAX_RAW is refused after one request, the
Connection header, Host header and Content-Length, and which environment names the
driver reads. Exit 0 = every expectation held (this script asserts GOOD behaviour).
"""
import traceback
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
from _load import (load, install_fake_env, install_fake_transport, FakeSocket, http_response,
                   SYNTHETIC_KEY, banner)

a, t, d = load()
env = install_fake_env(HTTPS_PROXY='https://proxy.invalid', ALL_PROXY='socks5://proxy.invalid',
                       SSLKEYLOGFILE='/tmp/should-never-be-used')
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


banner('1. exact bytes, one request, headers')
body = b'{"model":"openai/gpt-6.1-sol","max_tokens":16384,"messages":[{"role":"user","content":"\xce\xb1"}]}'
good = http_response(200, b'{"ok":true}', headers=[('Content-Type', 'application/json'),
                                                    ('Set-Cookie', 'secret=1'),
                                                    ('X-Request-Id', 'req-1'),
                                                    ('Authorization', 'Bearer ' + SYNTHETIC_KEY)])
tr = install_fake_transport([FakeSocket(good)])
packet = d.post_once(d.POST_URL, body)
wire = tr.wire()
check(len(wire) == 1, 'exactly one connection used')
head, _, sent_body = wire[0].partition(b'\r\n\r\n')
check(sent_body == body, 'body bytes on the wire identical to exact_bytes')
check(head.startswith(b'POST /api/v1/chat/completions HTTP/1.1\r\n'), 'request line')
hdrs = dict(l.split(b': ', 1) for l in head.split(b'\r\n')[1:])
check(hdrs.get(b'Host') == b'openrouter.ai', 'Host: openrouter.ai')
check(hdrs.get(b'Content-Length') == str(len(body)).encode(), 'Content-Length = len(exact_bytes)')
check(hdrs.get(b'Content-Type') == b'application/json', 'Content-Type json')
check(hdrs.get(b'Connection') == b'close', 'Connection: close')
check(b'Expect' not in hdrs, 'no Expect: 100-continue')
check(hdrs.get(b'Transfer-Encoding') is None, 'request not chunked')
check(hdrs.get(b'Accept-Encoding') == b'identity', 'Accept-Encoding identity (no compression)')
check(wire[0].count(b'POST ') == 1, 'one POST on the wire')
check(head.lower().count(b'content-length:') == 1 and head.lower().count(b'host:') == 1,
      'exactly one Content-Length and one Host header (http.client did not add duplicates)')
check(packet['status'] == 200 and packet['raw'] == b'{"ok":true}', 'packet status/raw')
check(packet['headers'] == {'content-type': 'application/json', 'x-request-id': 'req-1'},
      'headers reduced to allowlist: ' + repr(packet['headers']))
check(SYNTHETIC_KEY not in repr(packet), 'key absent from packet repr')
check(tr.hosts == [('openrouter.ai', 443, d.TIMEOUT_S)], 'host pinned, port 443, timeout=%s' % d.TIMEOUT_S)
check(tr.connections[0].fake.closed, 'connection closed after use')
check(env.reads == ['OPENROUTER_API_KEY'], 'env names read: ' + repr(env.reads))

banner('2. server 100 Continue preamble: consumed, no second send')
tr = install_fake_transport([FakeSocket(http_response(200, b'{"ok":1}', preamble=b'HTTP/1.1 100 Continue\r\n\r\n'))])
packet = d.post_once(d.POST_URL, body)
check(packet['status'] == 200, '100-continue preamble skipped, final status 200')
check(tr.wire()[0].count(b'POST ') == 1 and len(tr.connections) == 1, 'still exactly one POST')

banner('3. redirect returned, not followed')
tr = install_fake_transport([FakeSocket(http_response(307, b'', headers=[('Location', 'https://evil.invalid/x')]))])
packet = d.post_once(d.POST_URL, body)
check(packet['status'] == 307 and len(tr.connections) == 1, '307 returned as status; one connection')
check(packet['headers'] == {}, 'Location header not forwarded')

banner('4. broken pipe mid-send: one attempt, generic error, no key anywhere')
tr = install_fake_transport([FakeSocket(good, fail_send=BrokenPipeError(32, 'Broken pipe ' + SYNTHETIC_KEY)),
                             FakeSocket(good)])
try:
    d.post_once(d.POST_URL, body)
    check(False, 'should have raised')
except d.DriverError as exc:
    text = traceback.format_exc()
    check(str(exc) == 'transport_failed', 'DriverError transport_failed')
    check(exc.__context__ is None and exc.__cause__ is None, 'no chained exception')
    check(SYNTHETIC_KEY not in text and SYNTHETIC_KEY not in repr(exc), 'key absent from traceback text and repr')
    check(len(tr.connections) == 1 and len(tr.sockets) == 1, 'no second connection / re-send after broken pipe')
    locals_text = ''.join(traceback.TracebackException.from_exception(exc, capture_locals=True).format())
    print('     (note) frame locals of the raised DriverError contain the key: %s'
          % (SYNTHETIC_KEY in locals_text))

banner('5. remote disconnect before status line: one attempt')
tr = install_fake_transport([FakeSocket(b''), FakeSocket(good)])
try:
    d.post_once(d.POST_URL, body)
    check(False, 'should have raised')
except d.DriverError as exc:
    check(str(exc) == 'transport_failed' and len(tr.connections) == 1, 'RemoteDisconnected -> one attempt, no retry')

banner('6. bounded body: chunked and content-length framing over MAX_RAW')
for framing in ('chunked', 'content-length', 'close-delimited'):
    big = b'x' * (d.MAX_RAW + 7)
    resp = (http_response(200, big, chunked=True) if framing == 'chunked' else
            http_response(200, big) if framing == 'content-length' else
            http_response(200, big, content_length=False))
    tr = install_fake_transport([FakeSocket(resp)])
    try:
        d.post_once(d.POST_URL, body)
        check(False, framing + ': oversize should be refused')
    except d.DriverError as exc:
        check(str(exc) == 'transport_failed', framing + ': oversize refused with generic error')
    check(len(tr.connections) == 1 and tr.connections[0].fake.closed, framing + ': one request, socket closed')
    reads = tr.connections[0].fake.files[0].read_calls
    check(max(reads, default=0) <= d.MAX_RAW + 1 + 4, framing + ': largest single read request %s' % max(reads, default=0))
exact = b'y' * d.MAX_RAW
tr = install_fake_transport([FakeSocket(http_response(200, exact, chunked=True))])
check(len(d.post_once(d.POST_URL, body)['raw']) == d.MAX_RAW, 'exactly MAX_RAW chunked body accepted')

banner('7. key_info GET through real http.client')
key_raw = b'{"data":{"label":"drop","usage":0.000000001,"limit":1.73,"limit_remaining":1.729999999,"limit_reset":null,"is_free_tier":false}}'
tr = install_fake_transport([FakeSocket(http_response(200, key_raw))])
packet = d.key_info(d.KEY_URL)
head = tr.wire()[0]
check(head.startswith(b'GET /api/v1/key HTTP/1.1\r\n'), 'GET request line')
check(b'Content-Length' not in head and head.endswith(b'\r\n\r\n'), 'GET has no body / content-length')
check(packet['fields'] == b'{"usage":0.000000001,"limit":1.73,"limit_remaining":1.729999999,"limit_reset":null}', 'fields exact')
check('label' not in packet['fields'].decode(), 'label dropped')

banner('8. TLS context: verification on, hostname check, no keylog')
ctx = tr.contexts[0]
import ssl
check(ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname, 'CERT_REQUIRED + check_hostname')
check(ctx.keylog_filename is None, 'SSLKEYLOGFILE ignored (keylog_filename None)')
check(ctx.minimum_version >= ssl.TLSVersion.TLSv1_2, 'minimum TLS >= 1.2 (%s)' % ctx.minimum_version)
print('     trust anchors loaded on THIS host by load_default_certs(): x509=%d' % ctx.cert_store_stats()['x509'])
check(env.reads.count('OPENROUTER_API_KEY') == len(env.reads), 'only OPENROUTER_API_KEY ever read from env')

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
