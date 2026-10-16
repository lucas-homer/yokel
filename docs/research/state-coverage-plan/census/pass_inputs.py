#!/usr/bin/env python3
"""Build the sanitized blind-pass input for one census state (PROTOCOL step 4).

The pass input is a projection of the frozen manifest plus hard links to the originals. It keeps
what a pass needs to find and open each original and drops every field that records acquisition
findings: expected bases and evidence refs, cross-checks, terminal evidence, completeness and review
refs, operator agency/process classification, retrieval reasons and, for MS, the publication cycle
(derived from operator-read FILED stamps). A leak scan then rejects any kept string that still
mentions stamps, OCR, cross-checks or review refs (URLs are exempt).
Text-failure locators are kept as bare page/image references so both passes know which pages need
rendered viewing (PROTOCOL step 3).

    python3 census/pass_inputs.py <census-state-dir> <out-dir>

Writes <out-dir>/manifest.pass.jsonl, <out-dir>/originals/<sha256> and <out-dir>/INPUTS.json
(projection version, source-manifest hash, projection hash, counts). Originals are hard-linked
from the content store and verified by hash; nothing is downloaded. <out-dir> must not exist.
"""
import hashlib, json, os, pathlib, re, sys

PROJECTION_VERSION = 'pass-input-2'
LEAK = re.compile(r'stamp|ocr|cross.?check|adjudicat|signoff|owner-|review|operator|human', re.I)
DROP_CYCLE = {'MS'}  # MS cycles are keyed to operator-read FILED stamps


def text_failure_locators(entry):
    """Pages/regions known to lack a text layer (PROTOCOL step 3), reduced to bare locators.

    Only page numbers and image references for this entry are kept; any commentary attached to the
    original ref (what a region contains, whether it was already inspected) is dropped.
    """
    me, out = entry['entry_id'], []
    for ref in entry['expected']['evidence_refs']:
        m = re.match(r'(?:text-extract-fail:|FAILED REGION \(no text layer\): )([\w.-]+)#page=(\d+)', ref)
        if m and m.group(1) == me:
            out.append(f'page {m.group(2)}: embedded image without text layer')
            continue
        m = re.match(r'text-extract-fail:([\w.-]+)#(img\[\d+\])', ref)
        if m and m.group(1) == me:
            out.append(f'{m.group(2)}: embedded image without text layer')
            continue
        m = re.match(r'FAILED REGION \(no text; external image not retained\): (?:[\w.-]+ img src=)?(\S+)', ref)
        if m:
            out.append(f'external image not retained: {m.group(1)}')
            continue
        m = re.match(r'text-layer-fail: page (\d+)', ref)
        if m:
            out.append(f'page {m.group(1)}: native text below threshold')
            continue
        m = re.search(r'text-layer-test: .*pages? (\d+(?:-\d+)?) need rendered-image inspection', ref)
        if m:
            out.append(f'pages {m.group(1)}: no native text')
            continue
        m = re.match(r'(zero-text|short-text) pages[^:]*: (.+)', ref)
        if m:
            kind = 'no native text' if m.group(1) == 'zero-text' else 'native text below 200 chars'
            out += [f'page {n}: {kind}' for n in re.findall(r'p(\d+)', m.group(2))]
    return sorted(set(out), key=lambda x: (len(x), x))


def project(entry, state):
    r = entry['retrieval']
    out = {
        'entry_id': entry['entry_id'],
        'state': entry['state'],
        'universe_version': entry['universe_version'],
        'source_id': entry['source_id'],
        'lineage_id': entry['lineage_id'],
        'parent_entry_id': entry['parent_entry_id'],
        'child_entry_ids': entry['accounting']['child_entry_ids'],
        'kind': entry['kind'],
        'format': entry['format'],
        'text_layer': entry['text_layer'],
        'selector': entry['expected']['selector'],
        'page_range': page_range(entry['accounting']['pagination_or_page_range']),
        'text_failure_locators': text_failure_locators(entry),
        'retrieval': {k: r[k] for k in ('result', 'requested_url', 'final_url', 'http_status',
                                        'content_type', 'attempted_at', 'sha256', 'byte_length')},
        'original_path': f"originals/{r['sha256']}" if r['result'] == 'retrieved' else None,
    }
    if state not in DROP_CYCLE:
        out['publication_cycle'] = entry['publication_cycle']
    return out


def page_range(value):
    # 'single page; no result rows' style suffixes describe content, not structure
    return value.split(';')[0] if value.startswith('single') else value


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def main(src, out):
    src, out = pathlib.Path(src), pathlib.Path(out)
    raw = (src / 'manifest.jsonl').read_bytes()
    entries = [json.loads(line) for line in raw.decode().splitlines()]
    state = entries[0]['state']
    rows = [project(e, state) for e in entries]
    leaks = [(row['entry_id'], s) for row in rows for s in strings(row)
             if not s.startswith(('http://', 'https://')) and LEAK.search(s)]
    if leaks:
        sys.exit('leak scan failed:\n' + '\n'.join(f'  {i}: {s[:160]}' for i, s in leaks[:20]))
    (out / 'originals').mkdir(parents=True)
    for e, row in zip(entries, rows):
        if row['original_path'] is None:
            continue
        stored = pathlib.Path(os.path.expanduser(e['retrieval']['storage_path']))
        target = out / row['original_path']
        if not target.exists():
            os.link(stored, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != row['retrieval']['sha256']:
            sys.exit(f"hash mismatch: {row['entry_id']}")
    body = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n' for row in rows)
    (out / 'manifest.pass.jsonl').write_text(body)
    info = {
        'projection_version': PROJECTION_VERSION,
        'state': state,
        'source_manifest_sha256': hashlib.sha256(raw).hexdigest(),
        'pass_manifest_sha256': hashlib.sha256(body.encode()).hexdigest(),
        'entries': len(rows),
        'retrieved': sum(r['original_path'] is not None for r in rows),
        'distinct_originals': len({r['original_path'] for r in rows if r['original_path']}),
    }
    (out / 'INPUTS.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
