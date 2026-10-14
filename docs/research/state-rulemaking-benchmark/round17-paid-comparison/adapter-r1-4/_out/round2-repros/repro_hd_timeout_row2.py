"""A server that is silent for longer than TIMEOUT_S after the POST is written.

The driver's socket timeout is per-operation: with stream=false the provider sends
NOTHING until the whole completion is generated, so a long generation looks exactly
like a dead peer. Here the fake socket raises TimeoutError on the first response
read; the request bytes were fully sent. Shows the end-to-end consequence through the
adapter: row 2, debit FLOOR, terminal HALT, next cell refused. Exit 0 = reproduces
(a timeout after a fully-sent request is a terminal, floor-charged halt).
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, install_fake_env, install_fake_transport, FakeSocket, http_response, tempdir, banner

a, t, d = load()
install_fake_env()
banner('silent server beyond TIMEOUT_S = %s s' % d.TIMEOUT_S)
with tempdir() as tmp:
    h = t.Harness(tmp)
    key_raw = b'{"data":' + t.packet(0)['fields'] + b'}'
    sockets = [FakeSocket(http_response(200, key_raw)),                    # preflight GET
               FakeSocket(http_response(200, b'{}'), fail_read=TimeoutError('timed out'))]  # POST: no bytes back
    sockets += [FakeSocket(http_response(200, key_raw)) for _ in range(4)]  # four RECON reads
    tr = install_fake_transport(sockets)
    h.post, h.key_info = d.post_once, d.key_info
    result = h.execute()
    wire = tr.wire()
    posts = [w for w in wire if w.startswith(b'POST ')]
    print('POSTs on the wire:', len(posts), '| request fully written:',
          posts[0].endswith((h.run / 'job1/request.json').read_bytes()))
    print('result state:', result['state'], '| halt:', result['halt'], '| debit:', result['debit'],
          '(FLOOR=%d)' % a.recon.FLOOR)
    types = [e['type'] for e in h.entries()]
    print('ledger:', types)
    ok, reason = a.recon.admit(h.entries(), 'S2-OPQ', a.last_usage(h.entries()))
    print('next cell admission:', ok, reason)
    reproduced = (len(posts) == 1 and result['state'] == 2 and result['halt'] and
                  result['debit'] == a.recon.FLOOR and 'HALT' in types and not ok)
print()
print('R14 evidence: round14 adapter.py used urlopen(timeout=180) for max_tokens 8192 and the one live call '
      'finished at 7,231 completion tokens; R14 job proposals set timeout_seconds 1800. R17 doubles the output '
      'cap to 16,384 with a 60 s socket timeout.')
sys.exit(0 if reproduced else 1)
