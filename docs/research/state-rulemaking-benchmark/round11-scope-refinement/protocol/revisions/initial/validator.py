#!/usr/bin/env python3
"""Offline annotation contract checks; no language understanding or provider runtime."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY = json.loads((ROOT / 'policy.json').read_text(encoding='utf-8'))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_load(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite constant: ' + value)
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    canonical(value)  # also rejects overflow such as 1e999
    return value


def closed(obj, keys, label):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError(label + ': wrong keys')


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ': nonempty string required')


def unique_strings(values, label):
    if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values) or len(values) != len(set(values)):
        raise ValueError(label + ': unique string list required')


def evidence(items, source):
    if not isinstance(items, list) or not items:
        raise ValueError('evidence required')
    for item in items:
        closed(item, ['quote', 'occurrence'], 'evidence')
        nonempty(item['quote'], 'quote')
        occurrence = item['occurrence']
        if type(occurrence) is not int or occurrence < 1:
            raise ValueError('occurrence: positive integer required')
        quote = item['quote']
        starts = [i for i in range(len(source)) if source.startswith(quote, i)]
        if occurrence > len(starts):
            raise ValueError('evidence not exact in source')


def facet(unit):
    result = strict_load(canonical({k: unit[k] for k in POLICY['facet_keys']}).decode('utf-8'))
    if result['kind'] == 'relationship':
        result['value'].pop('equivalence_evidence', None)
    return result


def validate(case):
    """Raise ValueError on contract violation; report annotation-derived gates otherwise."""
    closed(case, ['source', 'inventory', 'classified_inventory', 'scopes', 'operative', 'mappings', 'source_review', 'record_audit'], 'case')
    source = case['source']
    nonempty(source, 'source')
    inventory = case['inventory']
    if not isinstance(inventory, list) or not inventory:
        raise ValueError('inventory required')
    # Classification is strictly an immutable-inventory annotation, not a filter.
    if canonical(inventory) != canonical(case['classified_inventory']):
        raise ValueError('inventory_changed')
    units = {}
    for unit in inventory:
        closed(unit, POLICY['unit_keys'], 'unit')
        nonempty(unit['id'], 'id')
        if unit['id'] in units:
            raise ValueError('duplicate unit')
        units[unit['id']] = unit
        if not isinstance(unit['kind'], str) or unit['kind'] not in POLICY['kinds']:
            raise ValueError('atomize mixed or unsupported kind')
        nonempty(unit['modality'], 'modality')
        if unit['modality'] not in POLICY['modalities']:
            raise ValueError('invalid modality')
        nonempty(unit['condition'], 'condition')
        unique_strings(unit['qualifications'], 'qualifications')
        unique_strings(unit['dependencies'], 'dependencies')
        nonempty(unit['uncertainty'], 'uncertainty')
        evidence(unit['evidence'], source)
        value = unit['value']
        if unit['kind'] == 'endpoint_role':
            closed(value, ['endpoint', 'purpose'], 'role')
            nonempty(value['endpoint'], 'endpoint')
            if not isinstance(value['purpose'], str) or value['purpose'] not in POLICY['purposes']:
                raise ValueError('invalid role purpose')
        elif unit['kind'] == 'relationship':
            closed(value, ['members', 'purpose', 'semantics', 'equivalence_evidence'], 'relationship')
            unique_strings(value['members'], 'members')
            if len(value['members']) < 2 or not isinstance(value['purpose'], str) or value['purpose'] not in POLICY['purposes']:
                raise ValueError('relationship members or purpose')
            if value['semantics'] not in POLICY['relationship_semantics']:
                raise ValueError('relationship semantics')
            if not isinstance(value['equivalence_evidence'], list):
                raise ValueError('equivalence evidence list required')
            if value['semantics'] == 'substitution':
                evidence(value['equivalence_evidence'], source)
            elif value['equivalence_evidence']:
                raise ValueError('equivalence evidence only for substitution')
        else:
            nonempty(value, 'atomic value')
    scopes = case['scopes']
    mappings = case['mappings']
    if not isinstance(scopes, dict) or set(scopes) != set(units):
        raise ValueError('scope_totality')
    if not isinstance(mappings, dict) or set(mappings) != set(units):
        raise ValueError('mapping_totality')
    visiting, done = set(), set()
    def visit(uid):
        if uid in visiting:
            raise ValueError('dependency cycle')
        if uid in done:
            return
        visiting.add(uid)
        for dep in units[uid]['dependencies']:
            if dep not in units:
                raise ValueError('unknown dependency')
            visit(dep)
        visiting.remove(uid)
        done.add(uid)
    for uid in units:
        visit(uid)
    operative = case['operative']
    if not isinstance(operative, dict):
        raise ValueError('operative object required')
    for ref, claim in operative.items():
        nonempty(ref, 'operative ref')
        closed(claim, POLICY['facet_keys'], 'operative facet')
    for uid, unit in units.items():
        scope = scopes[uid]
        closed(scope, ['category', 'basis', 'reason', 'evidence'], 'scope')
        if scope['category'] not in POLICY['scope_categories'] or scope['basis'] not in POLICY['scope_bases']:
            raise ValueError('scope enum')
        nonempty(scope['reason'], 'scope reason')
        evidence(scope['evidence'], source)
        allowed = POLICY['allowed_scope_by_kind'][unit['kind']]
        if scope['category'] not in allowed:
            raise ValueError('required_kind_excluded')
        if scope['category'] == 'unresolved_scope' and scope['basis'] != 'uncertain_source_function':
            raise ValueError('unresolved scope basis')
        if scope['category'] == 'retained_background' and scope['basis'] != 'substantive_background_only':
            raise ValueError('background basis')
        if unit['kind'] == 'endpoint_role':
            target = unit['value']['endpoint']
            if target not in units or units[target]['kind'] != 'endpoint' or target not in unit['dependencies']:
                raise ValueError('role endpoint dependency')
        if unit['kind'] == 'relationship':
            rel = unit['value']
            for member in rel['members']:
                if member not in units or units[member]['kind'] != 'endpoint_role' or member not in unit['dependencies']:
                    raise ValueError('relationship role dependency')
                if units[member]['value']['purpose'] != rel['purpose']:
                    raise ValueError('relationship purpose mismatch')
            if rel['semantics'] == 'independent_permissions' and rel['purpose'] != 'view_material':
                raise ValueError('independent view permissions purpose')
        mapping = mappings[uid]
        closed(mapping, ['status', 'refs', 'reason'], 'mapping')
        if mapping['status'] not in POLICY['mapping_statuses']:
            raise ValueError('mapping status')
        unique_strings(mapping['refs'], 'refs')
        nonempty(mapping['reason'], 'mapping reason')
        if any(ref not in operative for ref in mapping['refs']):
            raise ValueError('unknown operative ref')
        if mapping['status'] == 'missing' and mapping['refs']:
            raise ValueError('missing with refs')
        if mapping['status'] in ['matched', 'mismatched'] and not mapping['refs']:
            raise ValueError('recovery without operative refs')
        equal = any(operative[ref] == facet(unit) for ref in mapping['refs'])
        if mapping['status'] == 'matched':
            if not equal:
                raise ValueError('facet_mismatch')
            if unit['uncertainty'] != 'none' or unit['modality'] == 'unknown':
                raise ValueError('uncertain_matched')
            if any(mappings[d]['status'] != 'matched' for d in unit['dependencies']):
                raise ValueError('dependency_not_matched')
        if mapping['status'] == 'mismatched' and equal:
            raise ValueError('exact recovery labeled mismatch')
    effective = {}
    def effect(uid):
        if uid in effective:
            return effective[uid]
        unit = units[uid]
        deps = [effect(d) for d in unit['dependencies']]
        status = mappings[uid]['status']
        if unit['uncertainty'] != 'none' or unit['modality'] == 'unknown' or 'unknown' in deps:
            status = 'unknown'
        elif any(d in ['missing', 'mismatched'] for d in deps):
            status = 'mismatched' if status == 'matched' else status
        effective[uid] = status
        return status
    for uid in units:
        effect(uid)
    review = case['source_review']
    closed(review, ['status', 'source_sha256', 'inventory_sha256', 'scopes_sha256'], 'source review')
    if review['status'] not in ['unverified', 'source_only_frozen']:
        raise ValueError('source review status')
    if review['status'] == 'source_only_frozen':
        if review['source_sha256'] != hashlib.sha256(source.encode('utf-8')).hexdigest() or review['inventory_sha256'] != digest(inventory) or review['scopes_sha256'] != digest(scopes):
            raise ValueError('source_review_hash')
    elif review['source_sha256'] or review['inventory_sha256'] or review['scopes_sha256']:
        raise ValueError('unverified review cannot certify hashes')
    audit = case['record_audit']
    closed(audit, ['status', 'reviewed_refs', 'unsupported_refs', 'unknown_refs'], 'record audit')
    if audit['status'] not in ['not_run', 'reviewed']:
        raise ValueError('record audit status')
    for key in ['reviewed_refs', 'unsupported_refs', 'unknown_refs']:
        unique_strings(audit[key], key)
        if any(ref not in operative for ref in audit[key]):
            raise ValueError('audit unknown ref')
    if audit['status'] == 'not_run' and any(audit[k] for k in ['reviewed_refs', 'unsupported_refs', 'unknown_refs']):
        raise ValueError('not-run audit has results')
    if audit['status'] == 'reviewed' and set(audit['reviewed_refs']) != set(operative):
        raise ValueError('audit not exhaustive')
    if set(audit['unsupported_refs']) & set(audit['unknown_refs']):
        raise ValueError('audit incompatible labels')
    required = [u for u in units if scopes[u]['category'] in ['required_participation', 'identifying_context']]
    unresolved = [u for u in units if scopes[u]['category'] == 'unresolved_scope']
    unknown = [u for u in required if effective[u] == 'unknown']
    defects = [u for u in required if effective[u] in ['missing', 'mismatched']]
    gate = 'unverified' if unresolved or unknown or review['status'] != 'source_only_frozen' else ('not_complete' if defects else 'all_required_inventoried_units_matched')
    return {'required_scope_status': gate, 'unresolved_scope': unresolved, 'required_unknown': unknown,
            'required_defects': defects, 'effective_mappings': effective,
            'background_diagnostics': {u: effective[u] for u in units if scopes[u]['category'] == 'retained_background'},
            'source_completeness': 'reviewer_attestation_only' if review['status'] == 'source_only_frozen' else 'unverified',
            'record_fidelity': 'unverified' if audit['status'] == 'not_run' or audit['unknown_refs'] else ('not_faithful' if audit['unsupported_refs'] else 'reviewer_attestation_only'),
            'unsupported_record_refs': audit['unsupported_refs'], 'production_ready': False, 'live_compatibility': 'unverified'}


def run_fixtures():
    fixtures = strict_load((ROOT / 'fixtures.json').read_text(encoding='utf-8'))
    rows = []
    for fixture in fixtures:
        try:
            result = validate(fixture['case'])
            actual = {'valid': True, **{k: result[k] for k in fixture['expected'] if k != 'valid'}}
        except ValueError as exc:
            actual = {'valid': False, 'error': str(exc)}
        expected = fixture['expected']
        ok = all(actual.get(k) == v for k, v in expected.items())
        rows.append({'id': fixture['id'], 'pass': ok, 'actual': actual, 'expected': expected})
    return rows


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        print(json.dumps(validate(strict_load(Path(sys.argv[1]).read_text(encoding='utf-8'))), indent=2))
    elif len(sys.argv) == 1:
        rows = run_fixtures()
        print(json.dumps({'interpretation': 'synthetic contract checks only; no model evaluation', 'passed': sum(r['pass'] for r in rows), 'total': len(rows), 'results': rows}, indent=2))
        sys.exit(0 if all(r['pass'] for r in rows) else 1)
    else:
        sys.exit('usage: python3 validator.py [annotated-case.json]')
