"""Offline schema mapping of recorded authorization; never modifies run/ evidence."""
import argparse
import base64
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / 'run'
NAMES = ('KEY-ATTESTATION.json', 'CAP-ACCEPTANCE.json')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def normalize(raw, name):
    source = json.loads(raw)
    if 'source_bytes_base64' in source:
        original = base64.b64decode(source['source_bytes_base64'], validate=True)
        assert hashlib.sha256(original).hexdigest() == source['source_sha256']
        result = normalize(original, name)
        assert json.loads(result) == source, 'normalized evidence drift'
        return result
    value = copy.deepcopy(source)
    value['source_record'] = source
    value['source_sha256'] = hashlib.sha256(raw).hexdigest()
    # Exact original bytes, including JSON escaping, are recoverable as well.
    value['source_bytes_base64'] = base64.b64encode(raw).decode('ascii')
    value['normalization'] = 'Schema mapping of existing primary-recorded user authorization; not machine evidence.'
    if name == NAMES[0]:
        assert source['key_label'] == 'DocketClock'
        assert source['release_policy'] == 'P-ACCEPT'
        assert source['limit_reset'] == 'none'
        assert source['newly_created_no_prior_usage'] == 'yes'
        assert source['used_only_for_r17'].startswith('correct (user:')
        limit = Decimal(source['limit_usd']) * 10**9
        assert limit == 50_000_000_000 and limit == limit.to_integral_value()
        value.update(limit=int(limit), limit_reset=None, used_only_for_R17=True,
                     creation_date=source['date'])
        value['creation_date_basis'] = 'Recorded newly-created affirmation on source date; no independent creation timestamp.'
    elif name == NAMES[1]:
        assert source['status'] == 'ACCEPTED' and source['release_policy_selected'] == 'P-ACCEPT'
        assert source['residual_risk_affirmation_verbatim'] == 'accept re residual risk statement.'
        assert source['user_statement_verbatim'] == '$3 is fine'
        assert source['amendment_A4']['key_limit_usd'] == '50.00'
        value.update(accepted_by_primary=True, residual_risk_accepted=True,
                     verbatim_acceptance=source['residual_risk_affirmation_verbatim'])
        value['acceptance_basis'] = 'Existing primary-recorded ACCEPTED status, residual-risk affirmation and A4 amendment; historical statements remain verbatim.'
    else:
        raise ValueError('unknown evidence')
    return canonical(value)


def write(output=HERE / 'evidence', run=RUN):
    output.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        result = normalize((run / name).read_bytes(), name)
        path = output / name
        if path.exists() and path.read_bytes() != result:
            raise ValueError('refuse changed normalized evidence; inspect provenance')
        if not path.exists():
            with path.open('xb') as f:
                f.write(result)
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE / 'evidence')
    args = p.parse_args()
    # Keep outputs within this release-preparation tree.
    if not args.output.resolve().is_relative_to(HERE):
        p.error('output must be under release-prep-a4-r2')
    print(write(args.output))
