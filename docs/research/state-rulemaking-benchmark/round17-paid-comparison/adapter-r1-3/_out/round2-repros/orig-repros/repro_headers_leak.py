"""R-A (SHOULD-FIX): response headers are written verbatim to status.json.
The adapter does not allowlist or denylist header names. A host driver that mistakenly
returns the *request* headers, or a proxy that echoes Authorization, lands the bearer
token in a durable receipt. Fake transport only; the token below is synthetic."""
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('_load', Path(__file__).resolve().parent / '_load.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
a, t = L.load()

FAKE_TOKEN = 'Bearer sk-or-v1-SYNTHETIC-NOT-A-REAL-KEY-0000'
with L.tempdir() as d:
    h = t.Harness(d)
    real_post = h.post
    def echoing_post(url, raw):
        r = real_post(url, raw)
        # Simulate a buggy driver that merges request headers into the returned packet.
        r['headers'] = {'content-type': 'application/json', 'authorization': FAKE_TOKEN,
                        'set-cookie': 'session=synthetic'}
        return r
    h.post = echoing_post
    result = h.execute()
    status = (h.run / 'job1' / 'status.json').read_bytes()
    leaked = FAKE_TOKEN.encode() in status
    print('state', result['state'], 'halt', result['halt'])
    print('status.json contains the synthetic bearer token:', leaked)
    print('status.json contains set-cookie:', b'set-cookie' in status)
    sys.exit(0 if leaked else 1)
