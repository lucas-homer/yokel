#!/usr/bin/env python3
"""Integrate two sealed blind passes into a census state directory (PROTOCOL step 4 exit).

    python3 census/integrate_passes.py <census-state-dir> <sealed-pass-A-dir> <sealed-pass-B-dir>

Copies pass-A.jsonl and pass-B.jsonl byte for byte, verifies each against its attestation's
output_sha256, writes the union completion.jsonl (pass A rows then pass B rows, bytes unchanged),
keeps each attestation under attestations/ and any listed supplements under supplements/<pass>/
(verbatim-row supplements as a hash only),
and fills run.json `passes` from the attestations (preserving run.json's indent). Refuses to run
unless both outputs are sealed and their hashes match.
"""
import hashlib, json, pathlib, shutil, sys

SUPPLEMENTS = ['completion-attribution-review.jsonl', 'source-view-attributions.jsonl', 'progress.jsonl']
# Verbatim copies of original rows stay in the sealed store (originals are internal only, rights
# decision 3); git keeps their hash.
HASH_ONLY = ['evidence-verbatim-supplement.jsonl']
FIELDS = ['pass', 'provider', 'model', 'task_id', 'brief_sha256', 'dispatched_at', 'sealed_at',
          'output_sha256', 'isolated']


def main(state_dir, a_dir, b_dir, overrides=None):
    state_dir = pathlib.Path(state_dir)
    entries, completion = [], b''
    for letter, src in (('A', pathlib.Path(a_dir)), ('B', pathlib.Path(b_dir))):
        att = json.loads((src / 'attestation.json').read_text())
        out = (src / f'pass-{letter}.jsonl').read_bytes()
        if hashlib.sha256(out).hexdigest() != att['output_sha256']:
            sys.exit(f'pass {letter}: output hash does not match attestation')
        (state_dir / f'pass-{letter}.jsonl').write_bytes(out)
        rows = (src / 'completion.jsonl').read_bytes()
        completion += rows if rows.endswith(b'\n') else rows + b'\n'
        (state_dir / 'attestations').mkdir(exist_ok=True)
        shutil.copyfile(src / 'attestation.json', state_dir / 'attestations' / f'pass-{letter}.json')
        for name in SUPPLEMENTS:
            if (src / name).is_file():
                dest = state_dir / 'supplements' / f'pass-{letter}'
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src / name, dest / name)
        for name in HASH_ONLY:
            if (src / name).is_file():
                dest = state_dir / 'supplements' / f'pass-{letter}'
                dest.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256((src / name).read_bytes()).hexdigest()
                (dest / f'{name}.sha256').write_text(f'{digest}  {name} (kept in the sealed pass store, not in git)\n')
        entry = {k: att[k] for k in FIELDS}
        entry.update((overrides or {}).get(letter, {}))
        entries.append(entry)
    (state_dir / 'completion.jsonl').write_bytes(completion)
    raw = (state_dir / 'run.json').read_text()
    second = raw.split('\n')[1]
    indent = len(second) - len(second.lstrip(' '))
    run = json.loads(raw)
    run['passes'] = entries
    (state_dir / 'run.json').write_text(json.dumps(run, indent=indent, ensure_ascii=False) + '\n')
    print(json.dumps(entries, indent=1))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:4], overrides=json.loads(sys.argv[4]) if len(sys.argv) == 5 else None)
