"""A1 container frames and nested draws. Pure stdlib; no entropy or file writes."""
from collections import defaultdict
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def build_frames(rows, manifest):
    manifest_ids = {e['entry_id'] for e in manifest}
    entries = {e['entry_id']: e for e in manifest if e['retrieval']['result'] == 'retrieved'}
    grouped = defaultdict(list)
    for row in rows:
        cid = row['container_id']
        if cid not in entries:
            raise ValueError(f'{cid}: container outside retrieved manifest')
        ordinal = row['item_ordinal']
        if type(ordinal) is not int or ordinal < 1:
            raise ValueError(f'{cid}: invalid row ordinal')
        if row.get('item_frame_status') != 'resolved' or type(row.get('complete_item')) is not bool:
            raise ValueError(f'{cid}:{ordinal}: unresolved item frame')
        if row.get('accounting_role') == 'pointer':
            # WA primary ruling: other-issue references are retained source-gap
            # signals, outside owner accounting and the complete-item read pool.
            issue = re.fullmatch(r'wa-(?:issue|idx|sec)-(\d\d-\d\d)(?:-[A-Za-z]+)?', cid)
            docs = row.get('doc_numbers', [])
            resolution = row.get('pointer_resolution') or {}
            targets = resolution.get('manifest_entry_ids', []) or resolution.get('union_record_ids', [])
            status = 'pointer' if targets else 'pointer_unresolved'
            if (not issue or len(docs) != 1 or docs[0][:5] == issue[1]
                    or row['accounting_status'] != status or row.get('pointer_status') != status
                    or row.get('owner_accounting_eligible') is not False or row['complete_item']):
                raise ValueError(f'{cid}:{ordinal}: invalid WA other-issue pointer')
            if any(mid not in manifest_ids for mid in resolution.get('manifest_entry_ids', [])):
                raise ValueError(f'{cid}:{ordinal}: pointer target outside manifest')
        else:
            if row['accounting_status'] not in ('accounted', 'unaccounted'):
                raise ValueError(f'{cid}:{ordinal}: invalid accounting status')
            if (row['accounting_status'] == 'accounted') != bool(row.get('union_record_id')):
                raise ValueError(f'{cid}:{ordinal}: accounting pointer/status mismatch')
        source = row.get('source_entry_id')
        if source not in entries or not row.get('source_locator') or not row.get('native_text_fingerprint'):
            raise ValueError(f'{cid}:{ordinal}: unresolved source locator/body')
        if row['item_kind'].startswith('guidance_catalogue_') and row['complete_item']:
            raise ValueError(f'{cid}:{ordinal}: catalogue pointer is not a complete item')
        grouped[cid].append({**row, 'row_id': f'{cid}:{ordinal}',
                             'source_sha256': entries[source]['retrieval']['sha256']})
    required = {eid for eid, e in entries.items()
                if e['kind'] in ('issue', 'index', 'portal_slice', 'history_slice')}
    if required - grouped.keys():
        raise ValueError('unresolved container frame: '+', '.join(sorted(required-grouped.keys())))
    containers = {}
    for cid, members in sorted(grouped.items()):
        members.sort(key=lambda row: row['item_ordinal'])
        if [r['item_ordinal'] for r in members] != list(range(1, len(members)+1)):
            raise ValueError(f'{cid}: duplicate or missing ordered row IDs')
        pool = [r['row_id'] for r in members if r['complete_item']]
        if not pool:
            raise ValueError(f'{cid}: empty complete-item read pool')
        containers[cid] = {'rows': members, 'complete_item_ids': pool}
    return {'version': 'fixed_sample_v1', 'crosswalk_hash': digest(canonical(rows)),
            'containers': containers}


def nested_selections(audit, frames):
    """Pure reproduction of the signed A1 hashes, including every unaccounted row."""
    selected = {uid for s in audit['strata'] for uid in s['selected_ids']}
    result = {}
    for cid, container in frames['containers'].items():
        if cid not in selected:
            continue
        def rank(ids, purpose):
            return sorted(ids, key=lambda rid: (
                digest((audit['seed']+'\n'+purpose+'\n'+cid+'\n'+rid).encode()), rid))
        accounted = [r['row_id'] for r in container['rows'] if r['accounting_status'] == 'accounted']
        result[cid] = {
            'unaccounted_row_ids': [r['row_id'] for r in container['rows'] if r['accounting_status'] == 'unaccounted'],
            'accounted_row_ids': rank(accounted, 'container-accounted')[:min(5, len(accounted))],
            'item_id': rank(container['complete_item_ids'], 'container-item')[0]}
    return result


def validate_containers(directory, audit, manifest):
    """Return C08 details; no review-completion waiver at any stage."""
    errors = []
    try:
        frames_path = directory/'reconcile/container-frames.json'
        frames = json.loads(frames_path.read_text())
        rows = [json.loads(line) for line in (directory/'reconcile/container-crosswalk.jsonl').read_text().splitlines() if line.strip()]
        rebuilt = build_frames(rows, manifest)
        if frames != rebuilt:
            errors.append('container frames do not reproduce from crosswalk/source frame')
        if digest(canonical(frames)) != audit.get('container_frame_hash'):
            errors.append('container frame hash mismatch')
        if not audit.get('frozen_at') or not audit.get('frozen_before_seed'):
            errors.append('container frame freeze time/order missing')
        if audit.get('container_selections') != nested_selections(audit, rebuilt):
            errors.append('container nested selections mismatch (unaccounted/accounted/item)')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append('invalid/missing container frame: '+str(exc))
    return errors
