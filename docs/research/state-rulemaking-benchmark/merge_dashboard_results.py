"""Strictly overlay all 40 reviewed Llama document arms, preserving v1.

Usage: python merge_dashboard_results.py ARTIFACT_ROOT [--check-only]
Incomplete overlays fail without writing; --diagnostic reports readiness only.
Never run vendor jobs, synthesize scores, or keep an old Llama timeout as fallback.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ARMS = ("llama_agentic", "llama_agentic_plus")
TABLES = ("document-scores.jsonl", "field-scores.jsonl", "operation-records.jsonl", "extra-assertions.jsonl")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def key(row, table):
    return (row["fixture_id"], row["arm"], row["field_id"]) if table == "field-scores.jsonl" else (row["fixture_id"], row["arm"])


def read_table(path, snapshots):
    raw = path.read_bytes()
    snapshots[path] = digest(raw)
    return [(json.loads(line), line) for line in raw.splitlines(keepends=True) if line.strip()]


def index_rows(rows, table):
    result = {}
    for row, raw in rows:
        k = row["assertion_id"] if table == "extra-assertions.jsonl" else key(row, table)
        require(k not in result, f"Duplicate {table} key: {k}")
        result[k] = (row, raw)
    return result


def artifact(root, rel):
    path = (root / rel).resolve()
    require(path.is_relative_to(root), f"Artifact escapes root: {rel}")
    return path


def verify_provenance(root, row, unit):
    require(row.get("input_sha256") == unit["input_sha256"], f"Input hash mismatch: {row.get('fixture_id')}")
    require(row.get("reference_version_hash") == unit["reference_sha256"], f"Reference hash mismatch: {row.get('fixture_id')}")
    for path_key, hash_key in [("output_artifact", "output_artifact_hash"), ("capture_artifact", "capture_sha256"), ("supplemental_json_artifact", "supplemental_json_sha256"), ("source_input_artifact", "source_input_sha256")]:
        if row.get(path_key):
            require(digest(artifact(root, row[path_key]).read_bytes()) == row.get(hash_key), f"Artifact hash mismatch: {row[path_key]}")
    for image in row.get("source_image_artifacts", []):
        require(digest(artifact(root, image["path"]).read_bytes()) == image["sha256"], f"Source image changed: {image['path']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--original-dir", type=Path)
    parser.add_argument("--supplemental-dir", type=Path, action="append", help="Exactly three paths, in recovery-4, review-a, review-b order")
    parser.add_argument("--output-dir", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--diagnostic", action="store_true", help="Read-only readiness report; allow incomplete inputs, never write a merge")
    mode.add_argument("--check-only", action="store_true", help="Require complete overlays and validate in temporary storage without publishing")
    args = parser.parse_args()
    root = args.root.resolve()
    original = args.original_dir.resolve() if args.original_dir else root / "review/results-v1"
    destination = args.output_dir.resolve() if args.output_dir else root / "review/results-dashboard-v1"
    defaults = [root / "llama-recovery-2026-10-05/review", root / "execution-dashboard-1/review-a", root / "execution-dashboard-1/review-b"]
    supplements = [p.resolve() for p in args.supplemental_dir] if args.supplemental_dir else defaults
    require(len(supplements) == 3, "Exactly three supplemental ledgers are required")
    require(destination != original and destination not in supplements, "Destination must be a new directory")
    snapshots = {}
    freeze_path = root / "corpus-freeze.json"
    frozen_raw = freeze_path.read_bytes(); snapshots[freeze_path] = digest(frozen_raw)
    frozen = json.loads(frozen_raw)
    units = {u["fixture_id"]: u for u in frozen["units"]}
    require(set(units) == {f"{lane}{i:02}" for lane in "AB" for i in range(1, 11)}, "Expected frozen 20-unit corpus")
    for rel, record in frozen["files"].items():
        require(digest(artifact(root, rel).read_bytes()) == record["sha256"], f"Frozen artifact changed: {rel}")
    contract_path = root / "review/scoring-contract.json"
    contract = json.loads(contract_path.read_text())
    snapshots[contract_path] = digest(contract_path.read_bytes())
    references = {fid: {f["field_id"] for f in json.loads(artifact(root, u["reference_path"]).read_text())["reference_fields"]} for fid, u in units.items()}
    all_docs = {(fid, arm) for fid in units for arm in contract["arms"]}
    all_fields = {(fid, arm, field) for fid, arm in all_docs for field in references[fid]}
    base = {table: read_table(original / table, snapshots) for table in TABLES}
    base_indexes = {table: index_rows(rows, table) for table, rows in base.items()}
    require(len(all_docs) == 80 and len(all_fields) == 696, "Unexpected original corpus denominator")
    for table, expected in [("document-scores.jsonl", all_docs), ("operation-records.jsonl", all_docs), ("field-scores.jsonl", all_fields)]:
        require(set(base_indexes[table]) == expected, f"Original ledger incomplete: {table}")
    expected_groups = [{(f"A{i:02}", arm) for i in (1, 2) for arm in ARMS}, {(f"A{i:02}", arm) for i in range(3, 11) for arm in ARMS}, {(f"B{i:02}", arm) for i in range(1, 11) for arm in ARMS}]
    overlays = {table: {} for table in TABLES}; owners = {}; issues = []
    for source, expected_docs in zip(supplements, expected_groups):
        validation_path = source / "validation.json"
        if not validation_path.exists():
            issues.append(f"Missing supplemental validation: {validation_path}")
        else:
            validation_raw = validation_path.read_bytes(); snapshots[validation_path] = digest(validation_raw)
            if json.loads(validation_raw).get("passed") is not True:
                issues.append(f"Supplemental validation not passed: {validation_path}")
        local = {}
        for table in TABLES:
            path = source / table
            if not path.exists():
                issues.append(f"Missing supplemental ledger: {path}"); local[table] = {}; continue
            local[table] = index_rows(read_table(path, snapshots), table)
            expected = {(fid, arm, field) for fid, arm in expected_docs for field in references[fid]} if table == "field-scores.jsonl" else expected_docs
            if table != "extra-assertions.jsonl":
                require(not (set(local[table]) - expected), f"Unexpected supplemental keys: {path}")
                missing = expected - set(local[table])
                if missing:
                    issues.append(f"{path}: missing {len(missing)} required rows")
            for k, (row, raw) in local[table].items():
                doc_key = (row["fixture_id"], row["arm"])
                require(doc_key in expected_docs, f"Unexpected supplemental arm/fixture: {doc_key}")
                if table == "operation-records.jsonl":
                    doc_pair = local.get("document-scores.jsonl", {}).get(doc_key)
                    if not doc_pair:
                        issues.append(f"Operation without reviewed document: {doc_key}"); continue
                    doc = doc_pair[0]; row = dict(row)
                    # Required aggregator fields absent from supplemental ops are taken
                    # only from this new reviewed document, never an old timeout row.
                    for name in ("evaluation_status", "operation_status", "reference_version_hash"):
                        if name not in row:
                            row[name] = doc.get(name)
                        require(row[name] == doc.get(name), f"Supplemental operation/document mismatch: {doc_key}, {name}")
                    row.setdefault("wrapper_wall_ms", None)
                    raw = (json.dumps(row) + "\n").encode()
                if table != "extra-assertions.jsonl":
                    if row.get("evaluation_status") != "complete" or row.get("operation_status") != "completed_nonempty" or not row.get("output_artifact"):
                        issues.append(f"Supplemental output score incomplete: {table}, {k}")
                    elif table == "document-scores.jsonl" and not row.get("extra_assertion_audit_complete"):
                        issues.append(f"Supplemental extra-assertion audit incomplete: {k}")
                    else:
                        verify_provenance(root, row, units[row["fixture_id"]])
                require(k not in overlays[table], f"Conflicting overlays: {table}, {k}")
                overlays[table][k] = (row, raw)
                if table == "document-scores.jsonl":owners[k] = source
    readiness = {"ready": not issues, "required_llama_document_arms": 40, "required_llama_field_rows": 348, "observed_document_rows": len(overlays["document-scores.jsonl"]), "completed_document_rows": sum(row.get("evaluation_status") == "complete" for row, raw in overlays["document-scores.jsonl"].values()), "observed_field_rows": len(overlays["field-scores.jsonl"]), "completed_field_rows": sum(row.get("evaluation_status") == "complete" for row, raw in overlays["field-scores.jsonl"].values()), "issues": issues, "destination": str(destination)}
    if args.diagnostic:
        print(json.dumps(readiness, indent=2)); return
    require(not issues, "Incomplete overlay; no merged results written:\n" + "\n".join(issues))
    require(len(overlays["document-scores.jsonl"]) == 40 and len(overlays["field-scores.jsonl"]) == 348, "All 40 Llama document arms must be replaced")
    merged = {}
    for table in TABLES:
        retained = [(row, raw) for row, raw in base[table] if row["arm"] not in ARMS]
        if table == "extra-assertions.jsonl":
            merged[table] = retained + list(overlays[table].values())
        else:
            merged[table] = [overlays[table][key(row, table)] if row["arm"] in ARMS else (row, raw) for row, raw in base[table]]
        require([(row, raw) for row, raw in merged[table] if row["arm"] not in ARMS] == retained, f"Unchanged-arm bytes altered: {table}")
    history = []
    for k in sorted(owners):
        original_doc = base_indexes["document-scores.jsonl"][k][0]
        original_op = base_indexes["operation-records.jsonl"][k][0]
        history.append({"fixture_id": k[0], "arm": k[1], "original_operation_status": original_doc["operation_status"], "original_document_row": original_doc, "original_operation_row": original_op, "supplemental_directory": str(owners[k].relative_to(root)) if owners[k].is_relative_to(root) else str(owners[k]), "new_output_artifact": overlays["document-scores.jsonl"][k][0]["output_artifact"]})
    with tempfile.TemporaryDirectory(prefix="dashboard-merge-check-") as scratch:
        stage = Path(scratch)
        for table, rows in merged.items():
            # Raw native/Firecrawl line bytes are preserved, including whitespace.
            (stage / table).write_bytes(b"".join(raw for row, raw in rows))
        validator = Path(__file__).with_name("aggregate_results.py")
        checked = subprocess.run([sys.executable, str(validator), str(root), "--results-dir", str(stage), "--output-dir", str(stage)], text=True, capture_output=True)
        require(checked.returncode == 0, "Merged integrity/gate validation failed; no results published:\n" + checked.stderr)
        require(all(digest(path.read_bytes()) == hash_value for path, hash_value in snapshots.items()), "Input ledger changed during merge; rerun after reviewers finish")
        metadata = {"kind": "dashboard-overlay-v1", "original_ledgers_unchanged": True, "native_firecrawl_raw_rows_unchanged": True, "replaced_llama_document_arms": 40, "replaced_llama_field_rows": 348, "original_timeout_status_retained": True, "operational_capture_policy": "Captures remain at their original paths; overlay rows and original-operation-history.json retain provenance.", "source_snapshots": {str(p.relative_to(root)) if p.is_relative_to(root) else str(p): h for p, h in snapshots.items()}, "validation": json.loads((stage / "primary-verification.json").read_text())}
        (stage / "merge-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        (stage / "original-operation-history.json").write_text(json.dumps(history, indent=2) + "\n")
        if not args.check_only:
            require(not destination.exists(), f"Refusing existing destination: {destination}")
            require(destination.parent.is_dir(), f"Destination parent must exist: {destination.parent}")
            with tempfile.TemporaryDirectory(prefix=".dashboard-merge-", dir=destination.parent) as publish:
                candidate = Path(publish) / "results"
                shutil.copytree(stage, candidate)
                require(not destination.exists(), f"Refusing existing destination: {destination}")
                os.rename(candidate, destination)
    print(json.dumps({**readiness, "validated": True, "published": not args.check_only}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"Merge rejected: {error}", file=sys.stderr)
        sys.exit(1)
