"""Freeze source-only artifacts after independent review, before vendor calls.

Usage: python freeze_corpus.py ROOT
The resulting manifest is write-once. Paths under files are relative to ROOT so
the retained evidence can later be moved without changing the frozen manifest.
"""
import collections
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
HERE = Path(__file__).resolve().parent
IDS = [f"{lane}{i:02}" for lane in "AB" for i in range(1, 11)]
BUCKETS = {
    "clean standalone PDFs": "clean_standalone_pdf",
    "scanned/filled forms": "scanned_filled_form",
    "dense register layouts": "dense_register_layout",
    "lifecycle changes": "lifecycle_change",
}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain(path):
    key = str(path.relative_to(ROOT))
    return key, {"sha256": digest(path), "bytes": path.stat().st_size}


check = read(ROOT / "corpus-check.json")
audit = read(ROOT / "review/source-annotation-audit.json")
assert check["passed"] and audit["freeze_ready"]
assert audit["reviewed_units"] == 20 and not audit["new_vendor_outputs_inspected"]
assert not (ROOT / "corpus-freeze.json").exists(), "A frozen corpus must never be overwritten"
assert not list((ROOT / "llama/runs").glob("*/*/capture.json"))
assert not list((ROOT / "firecrawl/runs").glob("*/capture.json"))
assert digest(HERE / "PROTOCOL.md") == audit["protocol_sha256"]
assert digest(ROOT / "review/scoring-contract.json") == audit["scoring_contract_sha256"]

files = dict(retain(ROOT / name) for name in [
    "corpus-check.json", "review/source-annotation-audit.json",
    "review/scoring-contract.json", "review/adjudications.json",
    "review/corpus-audit.json", "review/independent-source-notes.json",
    "primary-source-checks.json",
])
units = []
checks = {f["fixture_id"]: f for f in check["fixtures"]}
audits = {u["fixture_id"]: u for u in audit["units"]}
for fid in IDS:
    lane = "source-a" if fid.startswith("A") else "source-b"
    folder = ROOT / lane / fid
    source = read(folder / "fixture.json")
    ref_path = ROOT / "review/adjudicated" / f"{fid}.json"
    ref = read(ref_path)
    row = checks[fid]
    reviewed = audits[fid]
    assert reviewed["all_relevant_rendered_pages_viewed"]
    assert digest(ref_path) == reviewed["adjudicated_annotation_hash"]
    assert digest(folder / "fixture.json") == reviewed["collector_annotation_hash"]
    assert digest(folder / "fixture.json") == row["fixture_metadata_sha256"]
    for filename, key in [("original.pdf", "original_sha256"), ("input.pdf", "input_sha256"), ("native.txt", "native_sha256")]:
        assert digest(folder / filename) == row[key], (fid, filename)
    images = sorted(folder.glob("page-*.png"))
    assert len(images) == row["input_page_count"]
    for page in reviewed["reviewed_page_records"]:
        assert page["complete_page_viewed"]
        assert digest(Path(page["rendered_image_path"])) == page["rendered_image_sha256"]
    for path in [folder / "original.pdf", folder / "input.pdf", folder / "native.txt", folder / "fixture.json", ref_path, *images]:
        k, v = retain(path)
        files[k] = v
    critical = [f for f in ref["reference_fields"] if f["critical"]]
    units.append({
        "fixture_id": fid, "directory": str(folder.relative_to(ROOT)),
        "input_path": str(folder / "input.pdf"),
        "input_sha256": row["input_sha256"], "input_bytes": row["input_bytes"],
        "input_page_count": row["input_page_count"],
        "original_sha256": row["original_sha256"],
        "original_page_count": row["original_page_count"],
        "original_physical_pages": row["original_physical_pages"],
        "state": "US-" + source["state"].removeprefix("US-"),
        "primary_bucket": BUCKETS[source["bucket"]],
        "layout_features": source["layout_features"], "event_type": source["event_type"],
        "source_url": source["source_url"], "source_title": source["source_title"],
        "template_family": source.get("template_family") or source.get("template_group"),
        "shared_original_group": source.get("shared_original_group"),
        "reference_path": str(ref_path.relative_to(ROOT)),
        "reference_sha256": digest(ref_path),
        "reference_fields": len(ref["reference_fields"]),
        "critical_fields": len(critical),
        "critical_determinate_groups": ref["critical_determinate_groups"],
        "reference_gate_eligible": ref["reference_gate_eligible"],
        "uncertain_critical_fields": [f["field_id"] for f in critical if f["answerability"] == "uncertain"],
    })

assert len({u["input_sha256"] for u in units}) == 20
assert max(collections.Counter(u["original_sha256"] for u in units).values()) <= 2
assert set(collections.Counter(u["primary_bucket"] for u in units).values()) == {5}
freeze = {
    "version": 1, "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "source and reference freeze before new vendor parsing",
    "artifact_root_at_run": str(ROOT),
    "path_policy": "files and directories are relative to artifact root; input_path is acquisition-time provenance",
    "protocol_sha256": digest(HERE / "PROTOCOL.md"),
    "scoring_contract_sha256": digest(ROOT / "review/scoring-contract.json"),
    "arm_settings": {
        "native": {"method": "retained embedded text extraction; no OCR"},
        "firecrawl_local_parse": {"formats": ["markdown"], "parsers": ["pdf"], "onlyMainContent": False, "pdfOptions": {"maxPages": "each input_page_count"}},
        "llama_agentic": {"tier": "agentic", "markdown": True, "version": "latest", "pages": "omitted; full bounded input"},
        "llama_agentic_plus": {"tier": "agentic_plus", "markdown": True, "version": "latest", "pages": "omitted; full bounded input"},
    },
    "ordered_fixture_ids": IDS, "units": units, "files": files,
    "counts": {
        "units": len(units), "input_page_instances": sum(u["input_page_count"] for u in units),
        "states": dict(collections.Counter(u["state"] for u in units)),
        "primary_buckets": dict(collections.Counter(u["primary_bucket"] for u in units)),
        "distinct_original_pdfs": len({u["original_sha256"] for u in units}),
        "reference_fields": sum(u["reference_fields"] for u in units),
        "critical_fields": sum(u["critical_fields"] for u in units),
        "reference_eligible_units": sum(u["reference_gate_eligible"] for u in units),
    },
}
with (ROOT / "corpus-freeze.json").open("x") as out:
    json.dump(freeze, out, indent=2)
    out.write("\n")
with (ROOT / "parser-inputs.json").open("x") as out:
    json.dump({"units": [{k: u[k] for k in ("fixture_id", "input_path", "input_sha256", "input_bytes", "input_page_count")} for u in units]}, out, indent=2)
    out.write("\n")
print(json.dumps({"manifest_sha256": digest(ROOT / "corpus-freeze.json"), "counts": freeze["counts"]}, indent=2))
