"""N14 against r1.2: can the TLS context still fall back to the default store or skip
verification? Real ssl module, no network. Needs the openssl CLI for the synthetic
CA / leaf certificates (skips those steps otherwise). Exit 0 = every check holds.
"""
import hashlib
import os
import shutil
import ssl
import stat
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from _load import load, install_fake_env, install_fake_transport, FakeSocket, http_response, tempdir, banner

a, t, d = load()
env = install_fake_env()
problems = []


def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond:
        problems.append(what)


def refuse(fn):
    try:
        fn()
    except d.DriverError as exc:
        return str(exc)
    except Exception as exc:
        return type(exc).__name__
    return None


bundle = d.CA_BUNDLE
banner('1. the driver context on this host')
st = os.stat(bundle)
print('     bundle:', bundle, '| symlink:', bundle.is_symlink(), '| uid:', st.st_uid, '| mode:', stat.filemode(st.st_mode), '| bytes:', st.st_size)
pem_blocks = bundle.read_bytes().count(b'-----BEGIN CERTIFICATE-----')
ctx = d._tls_context()
stats = ctx.cert_store_stats()
print('     PEM blocks in file:', pem_blocks, '| cert_store_stats:', stats)
check(stats['x509_ca'] > 0 and stats['x509_ca'] == pem_blocks, 'every PEM block loaded as a CA anchor (%d)' % stats['x509_ca'])
check(ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname, 'CERT_REQUIRED + check_hostname')
check(ctx.minimum_version >= ssl.TLSVersion.TLSv1_2, 'minimum TLS %s' % ctx.minimum_version.name)
check(ctx.keylog_filename is None, 'no keylog')
print('     verify_flags:', ctx.verify_flags, '| options:', ctx.options)
check(ctx.r17_ca_sha256 == hashlib.sha256(bundle.read_bytes()).hexdigest(), 'r17_ca_sha256 = sha256(bundle)')
bare = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
print('     for contrast, a bare PROTOCOL_TLS_CLIENT context has', bare.cert_store_stats()['x509_ca'], 'anchors (round-2 N14)')
print('     default verify paths:', ssl.get_default_verify_paths())

banner('2. default-store entry points are never called; SSL_CERT_FILE/SSL_CERT_DIR are ignored')
env.reads.clear()     # step 1's ssl.get_default_verify_paths() read the env vars itself
with patch.object(ssl.SSLContext, 'load_default_certs', side_effect=AssertionError('load_default_certs')), \
     patch.object(ssl.SSLContext, 'set_default_verify_paths', side_effect=AssertionError('set_default_verify_paths')), \
     patch.object(ssl, 'create_default_context', side_effect=AssertionError('create_default_context')), \
     patch.object(ssl, '_create_default_https_context', side_effect=AssertionError('_create_default_https_context'), create=True):
    ctx2 = d._tls_context()
    check(ctx2.cert_store_stats() == stats, 'context built without any default-store call; same anchors')
    tr = install_fake_transport([FakeSocket(http_response(200, b'{}'))])
    packet = d.post_once(d.POST_URL, b'{}')
    check(tr.contexts[0].cert_store_stats() == stats and tr.contexts[0].verify_mode == ssl.CERT_REQUIRED
          and tr.contexts[0].check_hostname, 'HTTPSConnection received that context (verified, same anchors)')
    check(packet['tls_ca_sha256'] == ctx.r17_ca_sha256, 'packet carries the bundle hash')
    check(env.reads == ['OPENROUTER_API_KEY'], 'only OPENROUTER_API_KEY read from the environment: %s' % env.reads)

have_openssl = bool(shutil.which('openssl'))
with tempdir() as tmp:
    tmp = Path(tmp)
    if have_openssl:
        ca, leaf = tmp / 'synthetic-ca.pem', tmp / 'synthetic-leaf.pem'
        for out, extra in ((ca, []), (leaf, ['-addext', 'basicConstraints=critical,CA:FALSE'])):
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(tmp / (out.stem + '.key')),
                            '-out', str(out), '-subj', '/CN=review-synthetic-' + out.stem, '-days', '1'] + extra,
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        env.update(SSL_CERT_FILE=str(ca), SSL_CERT_DIR=str(tmp))
        os.environ = env                        # the driver's os.environ is this mapping already
        import os as real_os
        saved = {k: real_os.getenv(k) for k in ('SSL_CERT_FILE', 'SSL_CERT_DIR')}
        real_os.putenv('SSL_CERT_FILE', str(ca)); real_os.putenv('SSL_CERT_DIR', str(tmp))   # process env for OpenSSL itself
        ctx3 = d._tls_context()
        subjects = [str(c.get('subject')) for c in ctx3.get_ca_certs()]
        check(ctx3.cert_store_stats() == stats and not any('review-synthetic' in s for s in subjects),
              'with SSL_CERT_FILE/SSL_CERT_DIR pointing at a synthetic CA: anchors unchanged, synthetic CA NOT trusted')
        for k, v in saved.items():
            real_os.unsetenv(k) if v is None else real_os.putenv(k, v)
        env.pop('SSL_CERT_FILE'); env.pop('SSL_CERT_DIR')

        banner('3. bundle content checks: a leaf-only bundle has zero CA anchors and is refused')
        with patch.object(d, 'CA_BUNDLE', leaf):
            code = refuse(d._tls_context)
            probe = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            probe.load_verify_locations(cafile=str(leaf))
            check(code == 'tls_no_trust_anchors', 'leaf-only bundle -> %s (store stats %s: a plain x509 count would have passed)' % (
                code, probe.cert_store_stats()))
            tr = install_fake_transport([])
            check(refuse(lambda: d.post_once(d.POST_URL, b'{}')) == 'transport_failed' and tr.connections == [],
                  'post_once refuses before any connection')
        with patch.object(d, 'CA_BUNDLE', ca):
            ctx4 = d._tls_context()
            check(ctx4.cert_store_stats()['x509_ca'] == 1 and ctx4.r17_ca_sha256 == hashlib.sha256(ca.read_bytes()).hexdigest(),
                  'a one-CA bundle loads (the check is a count, so a replaced file is only detectable through the receipt hash)')
    else:
        print('     openssl CLI not available; synthetic-certificate steps skipped')

    banner('4. missing / empty / mid-load-changed bundle: refused before any connection')
    tr = install_fake_transport([])
    with patch.object(d, 'CA_BUNDLE', tmp / 'missing.pem'):
        check(refuse(d._tls_context) == 'FileNotFoundError' and refuse(lambda: d.post_once(d.POST_URL, b'{}')) == 'transport_failed',
              'missing bundle: FileNotFoundError inside, transport_failed at the seam')
    empty = tmp / 'empty.pem'
    empty.write_bytes(b'')
    with patch.object(d, 'CA_BUNDLE', empty):
        code = refuse(d._tls_context)
        check(code in ('SSLError', 'tls_no_trust_anchors') and refuse(lambda: d.post_once(d.POST_URL, b'{}')) == 'transport_failed',
              'empty bundle: %s inside, transport_failed at the seam' % code)
    changing = tmp / 'changing.pem'
    changing.write_bytes(bundle.read_bytes())
    real_lvl = ssl.SSLContext.load_verify_locations
    def swap_during_load(self, cafile=None, capath=None, cadata=None):
        real_lvl(self, cafile=cafile, capath=capath, cadata=cadata)
        changing.write_bytes(bundle.read_bytes() + b'\n')
    with patch.object(d, 'CA_BUNDLE', changing), patch.object(ssl.SSLContext, 'load_verify_locations', swap_during_load):
        check(refuse(d._tls_context) == 'tls_bundle_changed', 'bundle bytes changing during load -> tls_bundle_changed')
    check(tr.connections == [], 'no connection was attempted in any refusal above')

banner('5. verification cannot be relaxed by the transport seam')
tr = install_fake_transport([FakeSocket(http_response(200, b'{}'))])
relaxed = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
relaxed.check_hostname = False
relaxed.verify_mode = ssl.CERT_NONE
with patch.object(d, '_tls_context', return_value=relaxed):
    check(refuse(lambda: d.post_once(d.POST_URL, b'{}')) == 'transport_failed' and tr.connections == [],
          'a CERT_NONE context is refused (tls_unverified) before connecting')

print()
print('problems:', problems)
sys.exit(0 if not problems else 1)
