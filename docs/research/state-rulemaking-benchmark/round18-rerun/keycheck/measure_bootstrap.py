"""Offline join of primary run boundaries and adapter timing. Never launches a job."""
import argparse
import decimal
import hashlib
import json
from pathlib import Path


def measure(timing, boundaries, receipt_bytes):
    start = boundaries['before_run_monotonic_ns']
    end = boundaries['after_run_monotonic_ns']
    entry = timing['adapter_entry_monotonic_ns']
    ready = timing['adapter_ready_monotonic_ns']
    if not all(type(v) is int for v in (start, end, entry, ready)) or not start <= entry <= ready <= end:
        raise ValueError('incompatible timing boundaries')
    # Same host/boot and monotonic clock are primary-attested, never inferred.
    if (boundaries.get('same_host_boot_and_monotonic_clock_confirmed_by_primary') is not True
            or type(boundaries.get('returncode')) is not int or boundaries['returncode'] != 0):
        raise ValueError('primary timing confirmation and successful run required')
    seconds = decimal.Decimal(ready - start) / decimal.Decimal(10**9)
    reserve = decimal.Decimal(60) - seconds
    result = dict(timing)
    result.update(bootstrap_seconds=str(seconds), native_reserve_seconds=str(reserve),
        numeric_encoding='exact decimal seconds as strings for joined measurements',
        measurement_kind='conservative_outer_run_to_adapter_ready_upper_bound',
        primary_run_boundaries=boundaries,
        native_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
        positive_native_reserve=reserve > 0, accepted_by_primary=False,
        measurement_gap='Native deadline start remains unexposed; outer start includes validation, initial pin hashing, claim, Keychain lookup, identity and supervisor launch before the native job deadline. This wider interval also includes op resolution, pre-exec pin hashing and adapter initialization.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('timing', 'boundaries', 'receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = measure(json.loads(args.timing.read_bytes()),
                     json.loads(args.boundaries.read_bytes()), args.receipt.read_bytes())
    result['adapter_timing_sha256'] = hashlib.sha256(args.timing.read_bytes()).hexdigest()
    result['run_boundaries_sha256'] = hashlib.sha256(args.boundaries.read_bytes()).hexdigest()
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print('Positive conservative reserve.' if result['positive_native_reserve'] else 'Reserve insufficient.')


if __name__ == '__main__':
    main()
