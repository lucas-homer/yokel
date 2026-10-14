"""Shared loader for the round-2 review repros. Offline only.

Loads the r1.1 adapter, its test harness (fakes) and the host driver from
../adapter-r1-1 by absolute path, so every script runs under `python3 -I -S -B`.
Provides a fake *socket* so the REAL http.client request/response machinery is
exercised without any network: `install_fake_transport()` replaces
`http.client.HTTPSConnection` with a subclass whose `connect()` plugs in a
`FakeSocket`. Nothing here opens a real connection or reads a real credential:
`os.environ` is replaced by a synthetic mapping holding a synthetic key string.
"""
import http.client
import importlib.util
import io
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent / 'adapter-r1-1'
SYNTHETIC_KEY = 'sk-or-v1-SYNTHETIC-REVIEW-R2-NOT-A-REAL-KEY-0000000000000000'


def mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load():
    tests = mod('r17_tests_for_review_r2', ADAPTER / 'test_adapter.py')
    driver = mod('r17_host_driver_review_r2', ADAPTER / 'host_driver.py')
    return tests.a, tests, driver


def tempdir():
    return tempfile.TemporaryDirectory(prefix='.review-r2-', dir=HERE)


def banner(title):
    print('=' * 78)
    print(title)
    print('=' * 78)


class FakeEnv(dict):
    """Synthetic process environment. Records every name read."""

    def __init__(self, key=SYNTHETIC_KEY, **extra):
        super().__init__(OPENROUTER_API_KEY=key, **extra)
        self.reads = []

    def get(self, name, default=None):
        self.reads.append(name)
        return super().get(name, default)

    def __getitem__(self, name):
        self.reads.append(name)
        return super().__getitem__(name)


def http_response(status=200, body=b'{}', headers=None, chunked=False, content_length=True,
                  preamble=b''):
    """Serialize one HTTP/1.1 response the way a server would put it on the wire."""
    lines = [f'HTTP/1.1 {status} X'.encode()]
    for name, value in (headers or [('Content-Type', 'application/json')]):
        lines.append(f'{name}: {value}'.encode())
    if chunked:
        lines.append(b'Transfer-Encoding: chunked')
        wire_body = b''
        for start in range(0, len(body), 65536):
            chunk = body[start:start + 65536]
            wire_body += f'{len(chunk):x}'.encode() + b'\r\n' + chunk + b'\r\n'
        wire_body += b'0\r\n\r\n'
    else:
        if content_length:
            lines.append(f'Content-Length: {len(body)}'.encode())
        wire_body = body
    lines.append(b'Connection: close')
    return preamble + b'\r\n'.join(lines) + b'\r\n\r\n' + wire_body


class Reader(io.BytesIO):
    """The socket file object http.client reads the response from."""

    def __init__(self, data, fail_read=None):
        super().__init__(data)
        self.fail_read = fail_read
        self.read_calls = []

    def read(self, n=-1):
        self.read_calls.append(n)
        if self.fail_read:
            raise self.fail_read
        return super().read(n)

    def readline(self, n=-1):
        if self.fail_read and not self.getbuffer().nbytes:
            raise self.fail_read
        return super().readline(n)


class FakeSocket:
    def __init__(self, response, fail_send=None, fail_read=None):
        self.response = response
        self.fail_send = fail_send
        self.fail_read = fail_read
        self.sent = []
        self.closed = False
        self.files = []

    def sendall(self, data):
        self.sent.append(bytes(data))
        if self.fail_send:
            exc = self.fail_send
            self.fail_send = None
            raise exc

    def makefile(self, mode, *args, **kwargs):
        f = Reader(self.response if not self.fail_read else b'', fail_read=self.fail_read)
        self.files.append(f)
        return f

    def close(self):
        self.closed = True

    def setsockopt(self, *a):
        pass

    def settimeout(self, *a):
        pass


class Transport:
    """Factory installed as http.client.HTTPSConnection. Each call makes one connection
    object backed by the next scripted FakeSocket; the real http.client code runs."""

    def __init__(self, sockets):
        self.sockets = list(sockets)
        self.connections = []
        self.contexts = []
        self.hosts = []
        outer = self

        class Connection(http.client.HTTPConnection):
            # Same constructor contract as the real HTTPSConnection (3.13), without the
            # `super(HTTPSConnection, self)` global-name lookup that patching would break.
            default_port = 443

            def __init__(self, host, port=None, *, timeout, source_address=None, context=None,
                         blocksize=8192):
                super().__init__(host, port, timeout, source_address, blocksize=blocksize)
                self._context = context

            def connect(self):
                outer.hosts.append((self.host, self.port, self.timeout))
                outer.contexts.append(self._context)
                if not outer.sockets:
                    raise AssertionError('unscripted connection attempt')
                self.fake = self.sock = outer.sockets.pop(0)   # .fake survives close()
                outer.connections.append(self)
        self.cls = Connection

    def wire(self):
        return [b''.join(c.fake.sent) for c in self.connections]


def install_fake_transport(sockets):
    transport = Transport(sockets)
    http.client.HTTPSConnection = transport.cls
    return transport


def install_fake_env(**kw):
    env = FakeEnv(**kw)
    os.environ = env
    return env
