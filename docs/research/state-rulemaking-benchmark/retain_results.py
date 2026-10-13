"""Copy completed research evidence, deduplicating identical PDF bytes.

Usage: python retain_results.py SOURCE_ROOT DESTINATION_ROOT
The destination must not exist. All source files are retained except bytecode
caches. PDF paths become relative symlinks to content-addressed PDF blobs.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


source, destination = [Path(p).resolve() for p in sys.argv[1:]]
assert source.is_dir() and not destination.exists()
destination.mkdir(parents=True)
blobs = destination / "pdf-blobs"
blobs.mkdir()
manifest = []
logical_pdf_bytes = 0
unique_pdf_bytes = 0
for old in sorted(source.rglob("*")):
    if not old.is_file() or "__pycache__" in old.parts:
        continue
    relative = old.relative_to(source)
    new = destination / relative
    new.parent.mkdir(parents=True, exist_ok=True)
    digest = sha(old)
    size = old.stat().st_size
    if old.suffix.lower() == ".pdf":
        logical_pdf_bytes += size
        blob = blobs / (digest + ".pdf")
        if not blob.exists():
            shutil.copyfile(old, blob)
            unique_pdf_bytes += size
        new.symlink_to(os.path.relpath(blob, new.parent))
    else:
        shutil.copyfile(old, new)
    assert sha(new) == digest
    manifest.append({"path": str(relative), "sha256": digest, "bytes": size, "relative_symlink": os.readlink(new) if new.is_symlink() else None})
frozen = json.loads((destination / "corpus-freeze.json").read_text())
for name, entry in frozen["files"].items():
    assert sha(destination / name) == entry["sha256"], name
record = {
    "source_root_at_run": str(source),
    "path_policy": "Original absolute paths in receipts are historical provenance. For replay, use this artifact root plus manifest-relative paths. PDF symlinks resolve entirely within this directory.",
    "file_count": len(manifest),
    "pdf_logical_bytes": logical_pdf_bytes,
    "pdf_unique_bytes": unique_pdf_bytes,
    "pdf_bytes_deduplicated": logical_pdf_bytes - unique_pdf_bytes,
    "frozen_files_verified": len(frozen["files"]),
    "files": manifest,
}
(destination / "retention-manifest.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: v for k, v in record.items() if k != "files"}, indent=2))
