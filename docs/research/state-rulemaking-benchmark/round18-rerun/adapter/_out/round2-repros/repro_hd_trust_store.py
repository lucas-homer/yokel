"""TLS trust anchors of host_driver._tls_context() on this host, and whether the process
environment (SSL_CERT_FILE / SSL_CERT_DIR) can redirect them.

load_default_certs() -> OpenSSL set_default_verify_paths, which honours SSL_CERT_FILE and
SSL_CERT_DIR. The driver's `tls_unverified` check only looks at verify_mode/check_hostname,
so (a) an empty store passes the check and fails every handshake (fail closed, floor-free
at preflight), and (b) an env-supplied bundle silently becomes the only trust anchor.
No network. Needs the `openssl` CLI to mint a throwaway self-signed certificate.
Exit 0 = env redirection of trust anchors demonstrated.
"""
import os
import shutil
import ssl
import subprocess
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, tempdir, banner

a, t, d = load()
banner('1. trust anchors on this host with the driver context')
ctx = d._tls_context()
print('verify_mode CERT_REQUIRED:', ctx.verify_mode == ssl.CERT_REQUIRED, '| check_hostname:', ctx.check_hostname)
print('x509 trust anchors loaded:', ctx.cert_store_stats()['x509'])
print('default verify paths:', ssl.get_default_verify_paths())
print('driver tls_unverified check would pass with an EMPTY store:',
      ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname)

banner('2. SSL_CERT_FILE redirects the trust store')
if not shutil.which('openssl'):
    print('openssl CLI not available; cannot mint a synthetic CA. exit 2')
    sys.exit(2)
with tempdir() as tmp:
    cert = os.path.join(tmp, 'synthetic-ca.pem')
    key = os.path.join(tmp, 'synthetic-ca.key')
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', cert,
                    '-subj', '/CN=review-synthetic-ca', '-days', '1'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.environ['SSL_CERT_FILE'] = cert       # process env only; the shell env is untouched
    os.environ['SSL_CERT_DIR'] = tmp
    ctx2 = d._tls_context()
    count = ctx2.cert_store_stats()['x509']
    print('x509 trust anchors after SSL_CERT_FILE=<synthetic CA>:', count)
    subjects = [c.get('subject') for c in ctx2.get_ca_certs()]
    print('subjects:', subjects)
    redirected = count >= 1 and any('review-synthetic-ca' in str(s) for s in subjects)
    print('env-supplied CA is now trusted by the driver context:', redirected)
    del os.environ['SSL_CERT_FILE'], os.environ['SSL_CERT_DIR']
sys.exit(0 if redirected else 1)
