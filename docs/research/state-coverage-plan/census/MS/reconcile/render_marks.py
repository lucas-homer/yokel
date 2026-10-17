#!/usr/bin/env python3
"""Render each visual_mark item's decisive regions to .census-passes/MS/review-renders/<item_id>.png.

Renders are derivatives, written outside git. Original bytes are hash-checked
first. Crops are fractions of the form page (oral-proceeding box, action
columns, filing-stamp row); FULL_PAGE lists variant layouts rendered whole.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
STATE = OUT.parent
ROOT = OUT.parents[5]
INPUTS = ROOT / '.census-passes/MS/inputs'
RENDERS = ROOT / '.census-passes/MS/review-renders'
WORK = RENDERS / '.work'

ORAL, ACTIONS, STAMPS = [0.0, 0.29, 1.0, 0.47], [0.0, 0.50, 1.0, 0.685], [0.0, 0.70, 1.0, 0.955]
CROPS = {'filed_stamp': [ACTIONS, STAMPS], 'oral_box': [ORAL], 'handwritten_id': [STAMPS],
         'handwritten_id_disagreement': [STAMPS], 'filed_stamp_index_quoted': [STAMPS],
         'stamp_index_scope_change': [ORAL, STAMPS], 'pass_a_dropped_note': [ORAL, ACTIONS, STAMPS],
         'pass_flagged_mark': [ORAL, ACTIONS], 'oral_box_disagreement': [ORAL], 'filed_stamp_disagreement': [STAMPS]}
# Forms whose layout differs from SOS APA Form 001 (checked by viewing).
FULL_PAGE = {}


def read(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def stamp_page(passes, form):
    for r in passes:
        for e in r['evidence']:
            if e['manifest_entry_id'] == 'ms-form-' + form and 'STAMP' in e['locator'].upper():
                m = re.search(r'\bp(?:age)?\s*(\d+)', e['locator'], re.I)
                if m:
                    return int(m[1])
    return 1


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    binary = WORK / 'render-marks'
    subprocess.run(['swiftc', '-O', '-module-cache-path', str(WORK / 'cache'), str(OUT / 'render-marks.swift'), '-o', str(binary)], check=True)
    manifest = {m['entry_id']: m for m in read(INPUTS / 'manifest.pass.jsonl')}
    pass_a = read(STATE / 'pass-A.jsonl')
    index = {}
    for item in read(OUT / 'review-queue.jsonl'):
        if item['trigger'] != 'visual_mark' or item['item_kind'] != 'case':
            continue
        crops = {}
        for x in item['sub_issues']:
            form = x['detail']['form']
            crops.setdefault(form, [])
            for c in CROPS[x['class']]:
                if c not in crops[form]:
                    crops[form].append(c)
        parts = []
        for form in sorted(crops):
            m = manifest['ms-form-' + form]
            blob = INPUTS / m['original_path']
            assert hashlib.sha256(blob.read_bytes()).hexdigest() == m['retrieval']['sha256'], form
            page = stamp_page(pass_a, form)
            boxes = [[0, 0, 1, 1]] if form in FULL_PAGE else sorted(crops[form], key=lambda c: c[1])
            parts.append({'label': f'ms-form-{form}  p{page}  sha256 {m["retrieval"]["sha256"][:12]}  ({item["owner_ref"]})',
                          'pdf': str(blob), 'page': page, 'crops': boxes})
        spec = {'out': str(RENDERS / f'{item["item_id"]}.png'), 'scale': 1.8, 'parts': parts}
        path = WORK / f'{item["item_id"]}.json'
        path.write_text(json.dumps(spec))
        subprocess.run([str(binary), str(path)], check=True)
        index[item['item_id']] = {'owner_ref': item['owner_ref'], 'forms': sorted(crops),
                                  'sha256': hashlib.sha256(Path(spec['out']).read_bytes()).hexdigest()}
    (RENDERS / 'INDEX.json').write_text(json.dumps(index, indent=1, sort_keys=True) + '\n')
    print(len(index), 'renders')


if __name__ == '__main__':
    main()
