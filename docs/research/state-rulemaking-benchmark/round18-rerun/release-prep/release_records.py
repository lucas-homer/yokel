"""Future primary-owned exclusive INIT/RELEASE/BIND; no transport or source reads."""
import argparse
import importlib.util
from pathlib import Path


def adapter(stage):
    path = stage / 'round18-rerun/adapter/r17_adapter.py'
    spec = importlib.util.spec_from_file_location('primary_records_adapter', path)
    a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a)
    return a


def init_record(a, budget, key_initial_usage):
    a.require(type(key_initial_usage) is int and key_initial_usage >= 0, "key_initial_usage")
    return dict(type='INIT', namespace=a.NAMESPACE, CAP=2000000000,
        OPERATING=1800000000, FLOOR=270000000, KEY_MAX=50000000000,
        key_label='DocketClock', key_limit=50000000000, key_limit_reset=None,
        key_initial_usage=key_initial_usage, release_policy='P-ACCEPT', required_calls=a.CALLS[:3],
        budget_sha256=a.sha(budget), recon_sha256=a.RECON_SHA)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path, required=True)
    sub = p.add_subparsers(dest='step', required=True)
    init = sub.add_parser('init')
    init.add_argument('--budget', type=Path, required=True)
    init.add_argument('--key-initial-usage', type=int, required=True, help='machine-checked U0 in integer nanoUSD')
    release = sub.add_parser('release')
    release.add_argument('--input', type=Path, required=True)
    sub.add_parser('bind')
    args = p.parse_args()
    stage = args.stage.resolve()
    a = adapter(stage)
    run = stage / 'round18-rerun/run'
    if args.step == 'init':
        assert args.budget.resolve().is_relative_to(stage)
        raw = a.encode(init_record(a, args.budget.read_bytes(), args.key_initial_usage)) + b'\n'
        with (run/'ledger.jsonl').open('xb') as f:
            f.write(raw)
            f.flush()
            a.os.fsync(f.fileno())
        a.fsync_dir(run)
    elif args.step == 'release':
        ledger = a.Ledger(run)
        with ledger.lock('primary-release'):
            ledger.load()
            assert len(ledger.entries) == 1
            value = a.strict(args.input.read_bytes())
            assert value['schema_version'] == 'r17.release.v1'
            assert value['release_policy'] == 'P-ACCEPT'
            assert value['required_calls'] == a.CALLS[:3] and value['typed_testable'] is False
            assert a.REQUIRED_ARTIFACTS | {'host_driver'} <= value['artifacts'].keys()
            value['init_sha256'] = a.sha(a.encode(ledger.entries[0]))
            for name in value['artifacts']:
                a.artifact(stage, value, name)
            a.put(run/'RELEASE.json', value)
    else:
        ledger = a.Ledger(run)
        with ledger.lock('primary-bind'):
            ledger.load()
            assert len(ledger.entries) == 1
            ledger.append('BIND_RELEASE', release_policy='P-ACCEPT',
                release_sha256=a.sha((run/'RELEASE.json').read_bytes()))
    print('primary record step complete: ' + args.step)


if __name__ == '__main__':
    main()
