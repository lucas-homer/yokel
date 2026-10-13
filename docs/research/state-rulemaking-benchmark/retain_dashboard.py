"""Retain completed dashboard downloads and their explicitly transcribed UI metadata."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent / "artifacts/execution-dashboard-1"
row = json.load(sys.stdin)
staging = json.loads((ROOT / "staging-manifest.json").read_text())
source = next(s for s in staging["inputs"] if s["fixture_id"] == row["fixture_id"])
assert row["status"] == "SUCCESS"
assert int(row["config"]["file_size_bytes"]) == source["input_bytes"]
assert row["config"]["file_name"] == source["filename"]
assert row["tier"] == row["config"]["tier"]
assert row["config"]["version"] == "latest"
assert row["config"]["parsing_instruction"] == '""'
ledger = ROOT / "dashboard-jobs.jsonl"
existing = [json.loads(s) for s in ledger.read_text().splitlines() if s.strip()]
assert not any((s["fixture_id"], s["tier"]) == (row["fixture_id"], row["tier"]) for s in existing)
assert not any(s["job_id"] == row["job_id"] for s in existing)
directory = ROOT / "runs" / row["fixture_id"] / row["tier"]
downloads = [Path("/Users/home/Downloads") / (row["download_stem"] + "." + ext) for ext in ("md", "json")]
assert all(s.exists() and s.stat().st_size for s in downloads)
assert len(json.loads(downloads[1].read_text())["pages"]) == source["input_page_count"]
directory.mkdir(parents=True, exist_ok=True)
row.update(input_sha256=source["input_sha256"], input_bytes=source["input_bytes"], pages=source["input_page_count"], file_id=row["config"]["file_id"])
row["outputs"] = []
for source_file in downloads:
    dest = directory / ("output" + source_file.suffix)
    assert not dest.exists()
    shutil.copy2(source_file, dest)
    row["outputs"].append({"path": str(dest.relative_to(ROOT)), "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "bytes": dest.stat().st_size, "download_path": str(source_file), "download_modified_at_utc": datetime.datetime.fromtimestamp(source_file.stat().st_mtime, datetime.timezone.utc).isoformat()})
row["provenance_note"] = "Metadata transcribed from visible dashboard diagnostics/configuration, not a raw API response. Downloaded output bytes are retained unchanged."
(directory / "capture.json").write_text(json.dumps(row, indent=2) + "\n")
with ledger.open("a") as handle:
    handle.write(json.dumps(row) + "\n")
print(json.dumps({"retained": row["fixture_id"], "tier": row["tier"], "job_id": row["job_id"], "pages": row["pages"], "outputs": row["outputs"]}, indent=2))
