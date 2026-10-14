"""Pin exact staging closure from metadata; never open source/reference body files.

Primary regenerates after finalizing policy/design/acceptance evidence. Extra
nonsecret evidence is accepted as explicit relative-path=sha256 pins only.
"""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r17_manifest_stage', HERE / 'stage.py')
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
R17 = 'round17-paid-comparison'


def build(bench=st.BENCH, extras=None):
    files = {}
    def metadata(name):
        raw = st.read_regular(bench / name)
        files[name] = st.digest(raw)
        return json.loads(raw)
    def table(prefix, pins):
        for name, item in pins.items():
            st.relative(name)
            files[prefix + '/' + name] = item['sha256'] if isinstance(item, dict) else item
    a = metadata(R17 + '/adapter-r1-3/READY.json')
    table(R17 + '/adapter-r1-3', a['files'])
    # Minimal wire runtime closure, using recorded immutable pins.
    for name in ('round14-semantic-contract/runtime/common.py',
                 'round15-condition-preservation/protocol-revised/READY.json',
                 'round15-condition-preservation/protocol-revised/compact.py',
                 'round15-condition-preservation/protocol-revised/request-settings.json',
                 'round15-condition-preservation/protocol-revised/stage-a.system.txt',
                 'round16-wire-compat/protocol-w2-1/wire.py'):
        files[name] = a['dependencies'][name]['sha256']
    d = metadata(R17 + '/design-r3-1/READY.json')
    dp = metadata(R17 + '/design-r3-1/READY.primary.json')
    table(R17 + '/design-r3-1', d['sha256'])
    table(R17 + '/design-r3-1', dp['sha256'])
    src = metadata(R17 + '/sources-r2/READY.json')
    require_selected = src['selected']
    if len(require_selected) != 3 or require_selected != sorted(set(require_selected)):
        raise ValueError('source slots')
    for sid in require_selected:
        name = sid + '/parsed-body.txt'
        files[R17 + '/sources-r2/' + name] = src['files'][name]['sha256']
    ref = metadata(R17 + '/reference/READY.json')
    table(R17 + '/reference', ref.get('sha256', ref.get('files', {})))
    # E8 is used solely as frozen metadata bytes/hash, never as semantic input.
    e8 = st.read_regular(bench / R17 / 'reference/E8-SUFFICIENCY.json')
    if st.digest(e8) != files[R17 + '/reference/E8-SUFFICIENCY.json']:
        raise ValueError('E8 metadata hash drift')
    raw = st.read_regular(bench / R17 / 'run/CAP-ACCEPTANCE.json')
    files[R17 + '/run/CAP-ACCEPTANCE.json'] = st.digest(raw)
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
    args = p.parse_args()
    extras = dict(item.split('=', 1) for item in args.evidence)
    m = build(extras=extras)
    args.output.write_bytes(st.canonical(m))
    st.load_manifest(args.output)
    print('stage content ID: ' + st.content_id(m))
    print('files: ' + str(len(m['files'])))


if __name__ == '__main__':
    main()
