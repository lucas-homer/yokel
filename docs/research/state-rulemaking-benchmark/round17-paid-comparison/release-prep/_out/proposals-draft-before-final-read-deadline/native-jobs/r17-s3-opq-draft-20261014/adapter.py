"""Template copied as native-jobs/<job-id>/adapter.py. No environment lookup here."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys


class JobDeadline(BaseException):
    pass


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args != ['--live-initial'] or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        return 2
    # Total local deadline includes config, imports, recovery, transport and fsync.
    # Host nested transport deadlines preserve this earlier timer.
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        return 2
    def expired(signum, frame):
        os._exit(4)  # Leave pending ledger for separately authorized accounting recovery.
    expired.r17_deadline = True
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 1740)
    try:
        here = Path(__file__).resolve().parent
        config = json.loads((here / 'arguments.json').read_bytes())
        if set(config) != {'schema_version', 'host_sha256', 'args'} or config['schema_version'] != 'r17.native-args.v1':
            return 2
        host = here.parents[1] / 'adapter-r1-3/host_driver.py'
        raw = host.read_bytes()
        if hashlib.sha256(raw).hexdigest() != config['host_sha256']:
            return 2
        spec = importlib.util.spec_from_file_location('r17_native_host', host)
        module = importlib.util.module_from_spec(spec)
        exec(compile(raw, str(host), 'exec'), module.__dict__)
        return module.main(config['args'])
    except (Exception, JobDeadline):
        print('R17 native shim stopped; primary must inspect ledger before any new release.', file=sys.stderr)
        return 4
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


if __name__ == '__main__':
    sys.exit(main())
