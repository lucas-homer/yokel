"""Q5: stage.py behaviour against temporary trees only (never ~/dev/yokel), synthetic bytes only.

Also probes the stage.py CLI with a temporary --parent: it must refuse before copying anything,
because the parent is outside the deployed adapter roots.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _load as L
st = L.load('r4_stage', L.R17 / 'release-prep-a4/stage.py')
PY = sys.executable
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('ok   ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


def tree(root):
    src = root / 'source'
    m = {'schema_version': 'r17.stage.v1', 'files': {}}
    def put(name, raw):
        p = src / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        m['files'][name] = hashlib.sha256(raw).hexdigest()
    put('round17-paid-comparison/adapter-r1-4/host_driver.py', b'# synthetic host\n')
    put('round17-paid-comparison/adapter-r1-4/native_entry.py', b'# synthetic shim\n')
    put('round17-paid-comparison/sources-r2/x/parsed-body.txt', b'synthetic body\n')
    put('round17-paid-comparison/reference/E/ref.json', b'{"synthetic":1}')
    (src / 'round17-paid-comparison/adapter-r1-4/_out').mkdir()
    (src / 'round17-paid-comparison/adapter-r1-4/_out/log.txt').write_text('not pinned')
    (src / 'round17-paid-comparison/adapter-r1-4/stray.py').write_text('not pinned either')
    return src, m


with L.tempdir('stage') as tmp:
    root = Path(tmp)
    src, m = tree(root)
    parent = root / 'allowed/.r17-stage'
    allowed = [str(root / 'allowed')]
    target = st.stage(src, parent, m, allowed_roots=allowed)
    copied = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
    check('copies exactly the pinned members plus the receipt; unpinned stray/_out files are NOT copied',
          copied == set(m['files']) | {'STAGE-MANIFEST.json'}, str(sorted(copied)))
    check('target name is the manifest content id', target.name == st.content_id(m))
    check('every copied byte matches its pin', all(hashlib.sha256((target / n).read_bytes()).hexdigest() == h for n, h in m['files'].items()))
    check('receipt equals canonical manifest', (target / 'STAGE-MANIFEST.json').read_bytes() == st.canonical(m))
    check('staged files are owner-only (0600) and dirs 0700',
          all(oct((target / n).stat().st_mode)[-3:] == '600' for n in m['files']) and oct(target.stat().st_mode)[-3:] == '700')
    try:
        st.stage(src, parent, m, allowed_roots=allowed)
        check('existing target refused', False)
    except FileExistsError:
        check('existing target refused (FileExistsError), nothing overwritten', True)

    # source drift -> refused before any write of that file; partial stage is never reused
    src2, m2 = tree(root / 'b')
    (src2 / 'round17-paid-comparison/reference/E/ref.json').write_bytes(b'{"synthetic":2}')
    try:
        st.stage(src2, root / 'b-parent', m2, allowed_roots=[str(root)])
        check('source drift refused', False)
    except ValueError as exc:
        partial = root / 'b-parent' / st.content_id(m2)
        check('source hash drift refused (%s); partial stage left for inspection, not reused' % exc, 'source hash mismatch' in str(exc) and partial.is_dir())
    try:
        st.stage(src2, root / 'b-parent', m2, allowed_roots=[str(root)])
        check('partial stage reuse refused', False)
    except FileExistsError:
        check('partial stage reuse refused', True)

    # symlinks: file member, directory member inside the source, source ancestor, destination ancestor
    src3, m3 = tree(root / 'c')
    link = src3 / 'round17-paid-comparison/adapter-r1-4/host_driver.py'
    link.unlink()
    link.symlink_to(src3 / 'round17-paid-comparison/adapter-r1-4/native_entry.py')
    try:
        st.stage(src3, root / 'c-parent', m3, allowed_roots=[str(root)])
        check('file symlink member refused', False)
    except (ValueError, OSError) as exc:
        check('file symlink member refused (%s)' % type(exc).__name__, True)
    src4, m4 = tree(root / 'd')
    real = src4 / 'round17-paid-comparison/adapter-r1-4'
    moved = root / 'd-moved-adapter'
    real.rename(moved)
    real.symlink_to(moved, target_is_directory=True)
    try:
        st.stage(src4, root / 'd-parent', m4, allowed_roots=[str(root)])
        check('intermediate directory symlink inside the source refused', False)
    except (ValueError, OSError) as exc:
        check('intermediate directory symlink inside the source refused (%s)' % type(exc).__name__, True)
    src5, m5 = tree(root / 'e')
    (root / 'e-parent').mkdir()
    (root / 'e-parent/.r17-stage').symlink_to(root / 'e-elsewhere', target_is_directory=True)
    (root / 'e-elsewhere').mkdir()
    try:
        st.stage(src5, root / 'e-parent/.r17-stage', m5, allowed_roots=[str(root)])
        check('destination parent symlink refused', False)
    except (ValueError, OSError) as exc:
        check('destination parent symlink refused (%s)' % type(exc).__name__, True)
    # hardlinked member: a regular file, allowed (content-addressed, so harmless) -- NOTE only
    src6, m6 = tree(root / 'f')
    hl = src6 / 'round17-paid-comparison/adapter-r1-4/host_driver.py'
    os.link(hl, root / 'f-hardlink')
    t6 = st.stage(src6, root / 'f-parent', m6, allowed_roots=[str(root)])
    check('hardlinked source member is copied (regular file; hash-verified) - NOTE, not a defect', (t6 / 'round17-paid-comparison/adapter-r1-4/host_driver.py').is_file())

    # relative() rejects
    for bad in ('../x', '/abs', 'a/../b', 'a/./b', 'a//b', 'a/', '', 'round17-paid-comparison/adapter-r1-4/..'):
        try:
            st.relative(bad)
            check('relative(%r) accepted?!' % bad, False)
        except ValueError:
            check('relative(%r) refused' % bad, True)
    # outside roots and root itself
    for bad_parent in (root / 'outside', root / 'allowed'):
        try:
            st.stage(src, bad_parent, m, allowed_roots=allowed)
            check('parent %s accepted?!' % bad_parent, False)
        except ValueError as exc:
            check('parent %s refused (%s)' % (bad_parent.name, exc), 'outside' in str(exc))
    # manifest schema
    for bad_m in ({'schema_version': 'r17.stage.v2', 'files': m['files']}, {'schema_version': 'r17.stage.v1', 'files': {}},
                  {'schema_version': 'r17.stage.v1', 'files': {'x': 'ABC'}}, {'schema_version': 'r17.stage.v1', 'files': m['files'], 'extra': 1}):
        p = root / 'bad-manifest.json'
        p.write_bytes(json.dumps(bad_m).encode())
        try:
            st.load_manifest(p)
            check('bad manifest accepted?!', False)
        except ValueError:
            check('bad manifest refused', True)

    # the CLI against a temporary parent: refused as outside the deployed adapter roots, before copying
    r = subprocess.run([PY, '-I', '-S', '-B', str(L.R17 / 'release-prep-a4/stage.py'), '--parent', str(root / 'cli-parent')],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env={'HOME': tmp, 'PATH': '/usr/bin:/bin'})
    check('stage.py CLI with a temp --parent refuses (target outside adapter roots) and creates nothing',
          r.returncode != 0 and b'target outside adapter roots' in r.stdout and not (root / 'cli-parent').exists(), r.stdout.decode()[-200:])
    check('~/dev/yokel/.r17-stage untouched by this review', not Path('/Users/home/dev/yokel/.r17-stage').exists())

    # What the stage does NOT pin: nothing outside the manifest. The signed job pins the interpreter
    # binary only; the bundled stdlib under the python prefix is same-user writable and unpinned (NOTE).
    prefix = Path('/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python')
    stdlib = prefix / 'lib/python3.12/json/__init__.py'
    check('bundled stdlib exists, is user-owned and writable, and is not a signed file pin (NOTE: runner trust boundary)',
          stdlib.is_file() and stdlib.stat().st_uid == os.getuid() and os.access(stdlib, os.W_OK))

print('SUMMARY stage:', sum(results), 'of', len(results), 'checks held')
sys.exit(0 if all(results) else 1)
