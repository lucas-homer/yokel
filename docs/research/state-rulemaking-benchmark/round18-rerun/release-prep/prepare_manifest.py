"""Offline R18 staging closure; reuse frozen R17 evidence, never paid outputs."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r18_manifest_stage', HERE / 'stage.py')
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
R17 = 'round17-paid-comparison'
R18 = 'round18-rerun'
DESIGN = R17 + '/design-r3-1-paccept'

def build(bench=st.BENCH, extras=None, require_installed=False):
    files = {}
    def metadata(name):
        raw = st.read_regular(bench / name)
        files[name] = st.digest(raw)
        return json.loads(raw)
    def table(prefix, pins):
        for name, item in pins.items():
            st.relative(name)
            files[prefix + '/' + name] = item['sha256'] if isinstance(item, dict) else item
    for folder in ('adapter', 'wire', 'recon'):
        r = metadata(R18 + '/' + folder + '/READY.json')
        table(R18 + '/' + folder, r['files'])
        for name, item in r['dependencies'].items():
            files[name] = item['sha256']
    for design in (DESIGN, R17 + '/design-r3-1'):
        for filename in ('READY.json', 'READY.primary.json'):
            d = metadata(design + '/' + filename)
            table(design, d['sha256'])
    src = metadata(R17 + '/sources-r2/READY.json')
    if len(src['selected']) != 3 or src['selected'] != sorted(set(src['selected'])):
        raise ValueError('source slots')
    for sid in src['selected']:
        name = sid + '/parsed-body.txt'
        files[R17 + '/sources-r2/' + name] = src['files'][name]['sha256']
    frozen = json.loads(st.read_regular(bench / R17 / 'release-prep/STAGE-MANIFEST.json'))
    files.update({n: h for n, h in frozen['files'].items() if n.startswith(R17 + '/reference/')})
    release = json.loads(st.read_regular(bench / R17 / 'run-live/stage-run/RELEASE.json'))
    for role in ('A1_fixture_gate', 'A2_fixture_gate', 'reference_ready', 'scoring_manifest', 'roles_auth'):
        item = release['artifacts'][role]
        st.relative(item['path'])
        files[item['path']] = item['sha256']
    for name in ('KEY-ATTESTATION.json', 'CAP-ACCEPTANCE.json'):
        normalized = R18 + '/release-prep/evidence/' + name
        raw = st.read_regular(bench / normalized)
        files[normalized] = st.digest(raw)
        files[R18 + '/run/' + name] = st.digest(raw)
        if require_installed and st.read_regular(bench / R18 / 'run' / name) != raw:
            raise ValueError('normalized evidence not installed: ' + name)
    for name in ('amendments/A5-A6.md', 'DESIGN-NOTE.md', 'release-prep/README.md',
                 'release-prep/SPEC.md', 'release-prep/prepare_manifest.py', 'release-prep/stage.py',
                 'release-prep/release_records.py', 'release-prep/make_proposals.py'):
        files[R18 + '/' + name] = st.digest(st.read_regular(bench / R18 / name))
    amendment = R17 + '/amendments/A4-key-limit-label/AMENDMENT.md'
    files[amendment] = st.digest(st.read_regular(bench / amendment))
    for name, h in (extras or {}).items():
        st.relative(name)
        if name in files and files[name] != h:
            raise ValueError('conflicting pin')
        files[name] = h
    return {'schema_version': 'r17.stage.v1', 'files': files}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE / 'STAGE-MANIFEST.json')
    p.add_argument('--evidence', action='append', default=[], help='BENCH-relative-path=sha256; nonsecret evidence only')
    p.add_argument('--require-installed', action='store_true')
    args = p.parse_args()
    m = build(extras=dict(item.split('=', 1) for item in args.evidence), require_installed=args.require_installed)
    args.output.write_bytes(st.canonical(m))
    st.load_manifest(args.output)
    print('stage content ID: ' + st.content_id(m))
    print('files: ' + str(len(m['files'])))

if __name__ == '__main__':
    main()
