"""Primary-owned offline staging. Imports do not copy or open benchmark bodies.

The fixed STAGE-MANIFEST.json is built from authorized metadata, never from body
reads in this task. Running this later intentionally copies/rehashes the freeze.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent.parent
CORE = BENCH / 'runner-stability-review/deployment/core.json'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or str(p) != name:
        raise ValueError('invalid relative path')
    return p


def no_symlinks(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('symlink refused')
    return path


def directory_fd(path, *, create=False):
    """Walk every ancestor with openat + O_NOFOLLOW, including under races."""
    path = Path(os.path.abspath(path))
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:]:
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def file_fd(path, flags, mode=0o600, *, create_parents=False):
    path = no_symlinks(path)
    parent = directory_fd(path.parent, create=create_parents)
    try:
        return os.open(path.name, flags | os.O_NOFOLLOW, mode, dir_fd=parent)
    finally:
        os.close(parent)


def read_regular(path):
    fd = file_fd(path, os.O_RDONLY)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('regular file required')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            return f.read()
    finally:
        os.close(fd)


def inside(path, roots):
    return any(path != Path(r) and path.is_relative_to(Path(r)) for r in roots)


def load_manifest(path=HERE / 'STAGE-MANIFEST.json'):
    m = json.loads(read_regular(path))
    if set(m) != {'schema_version', 'files'} or m['schema_version'] != 'r17.stage.v1' or not m['files']:
        raise ValueError('stage manifest schema')
    for name, h in m['files'].items():
        relative(name)
        if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid hash')
    return m


def content_id(manifest):
    return digest(canonical(manifest))


def stage(source, parent, manifest, *, allowed_roots):
    source, parent = no_symlinks(source), no_symlinks(parent)
    if not inside(parent, allowed_roots):
        raise ValueError('target outside adapter roots')
    # No recursive tree copy: only reviewed manifest members; O_EXCL for every file.
    target = parent / content_id(manifest)
    if os.path.lexists(target):
        raise FileExistsError('stage target exists; never reuse it')
    parent_fd = directory_fd(parent, create=True)
    try:
        os.mkdir(target.name, mode=0o700, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)
    for name, expected in sorted(manifest['files'].items()):
        relative(name)
        raw = read_regular(source / name)
        if digest(raw) != expected:
            raise ValueError('source hash mismatch: ' + name)
        dest = target / name
        fd = file_fd(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, create_parents=True)
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        if digest(read_regular(dest)) != expected:
            raise ValueError('copied hash mismatch: ' + name)
    receipt = canonical(manifest)
    with os.fdopen(file_fd(target / 'STAGE-MANIFEST.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL), 'wb') as f:
        f.write(receipt)
        f.flush()
        os.fsync(f.fileno())
    verify_stage(target, manifest)
    return target


def verify_stage(target, manifest):
    target = no_symlinks(target)
    for name, expected in manifest['files'].items():
        if digest(read_regular(target / relative(name))) != expected:
            raise ValueError('stage pin mismatch: ' + name)
    if json.loads(read_regular(target / 'STAGE-MANIFEST.json')) != manifest:
        raise ValueError('stage receipt mismatch')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent', type=Path, default=Path.home() / 'dev/yokel/.r18-stage')
    args = p.parse_args()
    core = json.loads(read_regular(CORE))
    print(stage(BENCH, args.parent, load_manifest(), allowed_roots=core['adapter_roots']))


if __name__ == '__main__':
    main()
