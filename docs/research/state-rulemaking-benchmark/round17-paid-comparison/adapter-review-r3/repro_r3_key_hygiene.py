"""N16/N19/N20 against r1.2: does the key reach an exception, a traceback frame, a
receipt or stdout/stderr on ANY failure path the diff touched? Real http.client over
fake sockets; the synthetic key is the only credential. Frames of this script itself
are excluded from the locals scan (they hold the synthetic environment by design);
every other frame, including http.client's, must be key-free. Exit 0 = holds.
"""
import contextlib
import http.client
import io
import sys
import traceback
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from _load import (load, install_fake_env, install_fake_transport, FakeSocket, http_response,
                   SYNTHETIC_KEY, tempdir, banner)

a, t, d = load()
env = install_fake_env()
KEY = SYNTHETIC_KEY
ME = str(Path(__file__).resolve())
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def scan(exc):
    """All frames except this script's: formatted text with locals, plus exception metadata."""
    tbe = traceback.TracebackException.from_exception(exc, capture_locals=True)
    foreign = [f for f in tbe.stack if f.filename != ME]
    text = ''.join(traceback.format_exception(exc))
    locals_text = '\n'.join('%s:%s %s' % (f.filename, f.name, f.locals) for f in foreign)
    leaked = []
    if KEY in text:
        leaked.append('traceback text')
    if KEY in locals_text:
        leaked.append('frame locals: ' + ', '.join(f.name for f in foreign if KEY in str(f.locals)))
    if KEY in repr(exc.args) or KEY in repr(getattr(exc, '__dict__', {})):
        leaked.append('exception args/attrs')
    if exc.__context__ is not None or exc.__cause__ is not None:
        leaked.append('chained context/cause retained')
    if any('http/client.py' in f.filename for f in foreign):
        leaked.append('http.client frames retained')
    return leaked, [f.name for f in foreign]


class ClosingFails(FakeSocket):
    def close(self):
        super().close()
        raise RuntimeError(KEY)


class ClosingInterrupts(FakeSocket):
    def close(self):
        super().close()
        raise KeyboardInterrupt(KEY)


banner('1. driver failure phases: exception, traceback and frame locals are key-free')
NOPREFIX = 'SYNTHETIC-REVIEW-KEY-WITHOUT-THE-PROVIDER-PREFIX-0000'   # not caught by the (case-insensitive) sk-or- header filter
phases = {
    'tls context raises': dict(patch_tls=RuntimeError(KEY)),
    'send fails (OSError)': dict(sock=lambda: FakeSocket(b'', fail_send=OSError(KEY))),
    'read times out': dict(sock=lambda: FakeSocket(http_response(), fail_read=TimeoutError(KEY))),
    'peer closes before status line': dict(sock=lambda: FakeSocket(b'')),
    'key echoed in body': dict(sock=lambda: FakeSocket(http_response(200, b'{"echo":"' + KEY.encode() + b'"}'))),
    'sk-or- key echoed in permitted header': dict(sock=lambda: FakeSocket(http_response(200, b'{}', headers=[('Content-Type', 'application/json'), ('x-request-id', KEY)])), base=None),
    'prefixless key echoed in header': dict(sock=lambda: FakeSocket(http_response(200, b'{}', headers=[('Content-Type', 'application/json'), ('x-request-id', NOPREFIX)])), key=NOPREFIX),
    'prefixless key echoed in body': dict(sock=lambda: FakeSocket(http_response(200, b'{"echo":"' + NOPREFIX.encode() + b'"}')), key=NOPREFIX),
    'oversize body': dict(sock=lambda: FakeSocket(http_response(200, b'x' * (d.MAX_RAW + 1)))),
    'socket close raises': dict(sock=lambda: ClosingFails(http_response(200, b'{}'))),
    'KeyboardInterrupt on send': dict(sock=lambda: FakeSocket(b'', fail_send=KeyboardInterrupt(KEY)), base=KeyboardInterrupt),
    'SystemExit on send': dict(sock=lambda: FakeSocket(b'', fail_send=SystemExit(KEY)), base=SystemExit),
    'BaseException on send': dict(sock=lambda: FakeSocket(b'', fail_send=BaseException(KEY)), base=BaseException),
    'KeyboardInterrupt in close': dict(sock=lambda: ClosingInterrupts(http_response(200, b'{}')), base=KeyboardInterrupt),
}
for label, spec in phases.items():
    key = spec.get('key', KEY)
    env['OPENROUTER_API_KEY'] = key
    for callback, args in ((d.post_once, (d.POST_URL, b'{}')), (d.key_info, (d.KEY_URL,))):
        sock = spec['sock']() if 'sock' in spec else None
        tr = install_fake_transport([sock] if sock else [])
        cm = patch.object(d, '_tls_context', side_effect=spec['patch_tls']) if 'patch_tls' in spec else contextlib.nullcontext()
        err = io.StringIO()
        try:
            with cm, contextlib.redirect_stderr(err):
                packet = callback(*args)
            kind = None
            leaked = ['packet carries the key'] if key in repr(packet) else []
            if kind is None and spec.get('base', d.DriverError) is None:
                leaked += [] if 'x-request-id' not in packet.get('headers', {}) else ['echoing header kept']
        except BaseException as exc:
            leaked, names = scan(exc)
            if key != KEY and (key in ''.join(traceback.format_exception(exc)) or any(
                    key in str(f.locals) for f in traceback.TracebackException.from_exception(exc, capture_locals=True).stack if f.filename != ME)):
                leaked.append('prefixless key in traceback')
            kind = type(exc)
        want = spec.get('base', d.DriverError)
        if want is None:   # key_info parses the body, so the GET variant fails on JSON shape instead
            want = None if callback is d.post_once else d.DriverError
        check(kind is want and not leaked and err.getvalue() == '',
              '%-36s %-9s -> %s %s' % (label, callback.__name__, kind.__name__ if kind else 'no exception', leaked or 'clean'))
        if sock:
            check(len(tr.connections) <= 1 and sock.closed, '    one connection, closed')
        else:
            check(tr.connections == [], '    no connection')
env['OPENROUTER_API_KEY'] = KEY
print('     note: an sk-or- prefixed value in a permitted header is dropped by filter_headers before the echo check; a prefixless echo trips response_sensitive')

banner('2. key validation refuses before connecting; the error never carries the key')
tr = install_fake_transport([])
for bad in (None, '', b'sk', 'sk-or-v1-é', ' ' + KEY, KEY + '\n', KEY + '\x7f', KEY.replace('-', '\x00', 1), 12345):
    env['OPENROUTER_API_KEY'] = bad
    for callback, args in ((d.post_once, (d.POST_URL, b'{}')), (d.key_info, (d.KEY_URL,))):
        try:
            callback(*args)
            check(False, 'accepted %r' % (bad,))
        except d.DriverError as exc:
            leaked, _ = scan(exc)
            check(not leaked and str(exc) in ('transport_failed',) and (not isinstance(bad, str) or not bad or bad not in repr(exc.args)),
                  '%-9s refuses %r as %s' % (callback.__name__, (bad[:6] + '...') if isinstance(bad, str) and len(bad) > 8 else bad, exc))
check(tr.connections == [], 'no connection for any invalid key')
env['OPENROUTER_API_KEY'] = KEY

banner('3. end-to-end receipts after a key echo / early TLS failure / invalid key GET')
with tempdir() as tmp:
    for label, sockets, patch_tls in (
            ('key echoed in POST body', [FakeSocket(http_response(200, b'{"data":' + t.packet(0)['fields'] + b'}')),
                                         FakeSocket(http_response(200, b'{"choices":[],"echo":"' + KEY.encode() + b'"}'))]
                                        + [FakeSocket(http_response(200, b'{"data":' + t.packet(0)['fields'] + b'}')) for _ in range(4)], None),
            ('TLS context fails at the POST', [FakeSocket(http_response(200, b'{"data":' + t.packet(0)['fields'] + b'}'))]
                                              + [FakeSocket(http_response(200, b'{"data":' + t.packet(0)['fields'] + b'}')) for _ in range(4)], 'post')):
        root = Path(tmp) / label.replace(' ', '_')
        root.mkdir()
        h = t.Harness(root)
        tr = install_fake_transport(sockets)
        h.post, h.key_info = d.post_once, d.key_info
        if patch_tls:
            real_tls = d._tls_context
            n = {'c': 0}
            def tls_once(real_tls=real_tls, n=n):
                n['c'] += 1
                if n['c'] == 2:                        # preflight GET is call 1; the POST is call 2
                    raise RuntimeError(KEY)
                return real_tls()
            cm = patch.object(d, '_tls_context', side_effect=tls_once)
        else:
            cm = contextlib.nullcontext()
        out, err = io.StringIO(), io.StringIO()
        with cm, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = h.execute()
        status = a.read(h.run / 'job1/status.json')
        check(result['state'] == 2 and result['debit'] == a.recon.FLOOR and status['http_status'] is None,
              '%s: row 2, FLOOR, status None' % label)
        check((h.run / 'job1/response.body').read_bytes() == b'', '    response.body empty (echoing body never stored)')
        check(('tls_ca_sha256' in status) == (patch_tls is None), '    bundle hash %s in status.json' % ('present' if patch_tls is None else 'absent, context never built'))
        check(sum(w.count(b'POST ') for w in tr.wire()) == (0 if patch_tls else 1), '    POST count %d' % sum(w.count(b'POST ') for w in tr.wire()))
        hits = [p.name for p in h.run.rglob('*') if p.is_file() and KEY.encode() in p.read_bytes()]
        check(not hits and KEY not in out.getvalue() + err.getvalue(), '    key absent from every receipt and from stdout/stderr')
        extra = set(status) - {'http_status', 'response_sha256', 'headers', 'resolved_at', 'tls_ca_sha256'}
        check(not extra, '    status.json has no unexpected fields: %s' % sorted(status))

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
