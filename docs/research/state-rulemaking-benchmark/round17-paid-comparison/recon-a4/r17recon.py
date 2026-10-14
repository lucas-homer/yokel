#!/usr/bin/env python3
"""R17 design-r3.1 reference semantics for ledger admission and key-usage reconciliation
(BUDGET §4-§5). Pure functions over already-parsed values: no I/O, no network, no credentials.
The adapter (PROTOCOL P3) must implement exactly these rules; check.py pins them with fixtures.

All money is integer nanoUSD. Provider decimals are parsed exactly (Decimal from the raw JSON
token, never a binary float) by `parse_usd`.
"""
from decimal import Decimal, ROUND_CEILING

CAP = 2_000_000_000
OPERATING = 1_800_000_000
FLOOR = 270_000_000
KEY_MAX = 50_000_000_000
TOL_PER_CALL = 1_000                   # nanoUSD per possibly-dispatched attempt, cumulative
READ_SCHEDULE_S = (0, 60, 300, 900)    # elapsed seconds after the attempt resolved
RELEASE_POLICIES = ('P-HARD', 'P-ACCEPT')  # BUDGET §0; UNSET or anything else never admits


class LedgerError(ValueError):
    pass


def parse_usd(token):
    """Exact decimal string -> nanoUSD, rounded up. Rejects non-finite or negative values."""
    if not isinstance(token, str):
        raise LedgerError('money must arrive as the raw decimal token (a string)')
    d = Decimal(token)
    if not d.is_finite() or d < 0:
        raise LedgerError(f'bad money token {token!r}')
    return int((d * 1_000_000_000).to_integral_value(rounding=ROUND_CEILING))


def key_limit_ok(limit, required_calls):
    """INIT condition: the verified, non-resetting key limit funds every required call at FLOOR
    and is no higher than KEY_MAX."""
    return type(limit) is int and required_calls * FLOOR <= limit <= KEY_MAX


def _calls(entries, kind):
    return [e['call'] for e in entries if e['type'] == kind]


def pending(entries):
    """Calls with more RESERVE than RESOLVE entries (a re-admitted, never-dispatched call
    has one RESERVE/RESOLVE pair per attempt)."""
    open_ = {}
    for e in entries:
        if e['type'] in ('RESERVE', 'RESOLVE'):
            open_[e['call']] = open_.get(e['call'], 0) + (1 if e['type'] == 'RESERVE' else -1)
    return sorted(c for c, n in open_.items() if n > 0)


def aggregate(entries):
    """Σ RESOLVE.debit + Σ RECONCILE_UP.debit + FLOOR per pending RESERVE."""
    total = sum(e['debit'] for e in entries if e['type'] in ('RESOLVE', 'RECONCILE_UP'))
    return total + FLOOR * len(pending(entries))


def admit(entries, call, key_usage):
    """Admission for `call`, evaluated under the exclusive lock BEFORE its RESERVE is written.
    entries: ledger entries (dicts with 'type' and, where relevant, 'call', 'debit',
    'dispatched'; INIT and BIND_RELEASE carry 'release_policy'). key_usage: the last RECONCILED provider usage (nanoUSD).
    Returns (True, None) or (False, reason)."""
    types = [e['type'] for e in entries]
    if not types or types[0] != 'INIT':
        return False, 'no INIT'
    init = entries[0]
    if init.get('release_policy') not in RELEASE_POLICIES:
        return False, 'release policy unset or unrecognised'
    if 'HALT' in types:
        return False, 'halted'
    if 'BIND_RELEASE' not in types:
        return False, 'release record not bound'
    if any(e.get('release_policy') != init['release_policy'] for e in entries if e['type'] == 'BIND_RELEASE'):
        return False, 'release policy differs between INIT and BIND_RELEASE'
    if call not in init['required_calls']:
        return False, 'not a required call'
    if pending(entries):
        return False, 'an attempt is unresolved'
    marked, reconciled = _calls(entries, 'DISPATCH_MARK'), set(_calls(entries, 'RECONCILED'))
    if any(c not in reconciled for c in marked):
        return False, 'key usage not reconciled for a dispatched attempt'
    done = {e['call'] for e in entries if e['type'] == 'RESOLVE' and e['dispatched']} | set(_calls(entries, 'SKIP'))
    if call in done:
        return False, 'call already completed or skipped (no retry)'
    remaining = sum(1 for c in init['required_calls'] if c not in done)
    need = remaining * FLOOR
    if aggregate(entries) + need > OPERATING:
        return False, 'operating limit'
    if key_usage + need > init['key_limit']:
        return False, 'key capacity'
    return True, None


def debit(reported=None, prompt_tokens=None, completion_tokens=None, key_delta=None):
    """BUDGET §4 rule 4: max(FLOOR, reported, rate estimate, attributable key usage)."""
    terms = [FLOOR]
    if reported is not None:
        terms.append(reported)
    if prompt_tokens is not None and completion_tokens is not None:
        terms.append(prompt_tokens * 2_500 + completion_tokens * 10_000)
    if key_delta is not None:
        terms.append(key_delta)
    return max(terms)


def reconcile(i, cumulative_reported, prev_usage, pinned, reads):
    """BUDGET §5 RECON after possibly-dispatched attempt number i (1-based, cumulative).
    cumulative_reported: Σ ceil(reported cost) over attempts 1..i (None if any is missing).
    prev_usage: last reconciled usage (0 at INIT). pinned: {'limit', 'limit_reset'} from INIT.
    reads: [(elapsed_s, read)] in time order, read = None (read error) or a dict with
    'usage', 'limit', 'limit_reset'. Returns ('RECONCILED', usage) or ('HALT', reason)."""
    if len(reads) > len(READ_SCHEDULE_S):
        return 'HALT', 'too many reads'
    for (elapsed, _), due in zip(reads, READ_SCHEDULE_S):
        if elapsed < due:
            return 'HALT', 'read before its scheduled time'
    tol, floor = i * TOL_PER_CALL, prev_usage
    for _, read in reads:
        if read is None:
            continue
        if read['limit'] is None or read['limit'] != pinned['limit'] or read['limit_reset'] != pinned['limit_reset']:
            return 'HALT', 'limit changed, unlimited or resetting'
        u = read['usage']
        if type(u) is not int or u < floor:
            return 'HALT', 'usage regressed or invalid'
        floor = u    # R3-S3: below any earlier read of this sequence is a regression too
        if cumulative_reported is None:
            continue
        if u > cumulative_reported + tol:
            return 'HALT', 'usage exceeds reported cost'
        if abs(u - cumulative_reported) <= tol:
            return 'RECONCILED', u
    return 'HALT', 'KEY_USAGE_UNRECONCILED'


def close_debit(entries, highest_usage):
    """Run-close retention: max(Σ conservative debits, highest key usage since zero).
    Returns the upward RECONCILE_UP amount (0 if none is needed)."""
    total = sum(e['debit'] for e in entries if e['type'] in ('RESOLVE', 'RECONCILE_UP'))
    return max(0, highest_usage - total)
