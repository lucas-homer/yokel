"""Read-only verification of the dashboard recovery supplement (Python stdlib)."""

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "artifacts"
RECOVERY = ROOT / "llama-recovery-2026-10-05"


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_quote(row):
    output = ROOT / row["output_artifact"]
    assert sha(output) == row["output_artifact_hash"]
    text = output.read_text()
    loc = row["output_locator"]
    assert text[loc["char_start"]:loc["char_end"]] == row["exact_output_quote"]


def main():
    retained = read_json(ROOT / "retention-manifest.json")
    for item in retained["files"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    freeze = read_json(ROOT / "corpus-freeze.json")
    for name, item in freeze["files"].items():
        assert sha(ROOT / name) == item["sha256"], name

    manifest = read_json(RECOVERY / "recovery-manifest.json")
    assert sha(ROOT / "corpus-freeze.json") == manifest["corpus_freeze_sha256"]
    assert sha(RECOVERY / "usage-export.json") == manifest["usage_export"]["sha256"]
    usage = read_json(RECOVERY / "usage-export.json")
    jobs = manifest["jobs"]
    assert len(jobs) == len({j["job_id"] for j in jobs}) == 4
    assert len({(j["fixture_id"], j["tier"]) for j in jobs}) == 4
    for job in jobs:
        capture_path = ROOT / job["original_capture"]
        assert sha(capture_path) == job["original_capture_sha256"]
        capture = read_json(capture_path)
        config = job["dashboard_configuration_observation"]
        assert config["file_id"] == capture["file_id"]
        assert config["file_size_bytes"] == capture["input_byte_length"]
        assert config["tier"] == capture["tier"] == job["tier"]
        assert job["input_sha256"] == capture["input_sha256"]
        assert capture["outcome"] == "timeout_backend_unknown"
        matches = [u for u in usage if u["event_aggregation_key"] == job["job_id"]]
        assert len(matches) == 1
        assert matches[0]["credits"] == job["reported_credits"]
        assert matches[0]["properties"]["tier"] == job["tier"]
        for output in job["outputs"]:
            path = RECOVERY / output["path"]
            assert sha(path) == output["sha256"]
            assert path.stat().st_size == output["byte_length"]
            if path.suffix == ".json":
                assert len(read_json(path)["pages"]) == job["dashboard_pages"]
    assert sum(j["reported_credits"] for j in jobs) == 110

    fields = read_jsonl(RECOVERY / "review/field-scores.jsonl")
    documents = read_jsonl(RECOVERY / "review/document-scores.jsonl")
    assert len(fields) == len({(r["fixture_id"], r["arm"], r["field_id"]) for r in fields}) == 40
    assert len(documents) == 4
    for field in fields:
        verify_quote(field)
        assert sha(ROOT / "review/adjudicated" / (field["fixture_id"] + ".json")) == field["reference_version_hash"]
        assert field["answerability"] in ("present", "explicit_negative")
        expected = field["outcome"] == "supported" and field["decisive_relation_preserved"]
        assert field["field_gate_pass"] == expected
    extras = read_jsonl(RECOVERY / "review/extra-assertions.jsonl")
    for document in documents:
        relevant = [f for f in fields if (f["fixture_id"], f["arm"]) == (document["fixture_id"], document["arm"]) and f["critical"]]
        critical_extras = [e for e in extras if (e["fixture_id"], e["arm"]) == (document["fixture_id"], document["arm"]) and e["critical"]]
        expected = "pass" if all(f["field_gate_pass"] for f in relevant) and not critical_extras else "content_fail"
        assert document["gate_outcome"] == expected
    diagnostics = read_jsonl(RECOVERY / "review/supplementary-diagnostics.jsonl")
    for row in diagnostics:
        verify_quote(row)
        assert sha(ROOT / row["source_artifact"]) == row["source_artifact_hash"]
    summary = {
        "passed": True,
        "original_retained_files_unchanged": len(retained["files"]),
        "frozen_files_unchanged": len(freeze["files"]),
        "recovered_jobs": len(jobs),
        "downloaded_outputs_verified": sum(len(j["outputs"]) for j in jobs),
        "matched_credits": sum(j["reported_credits"] for j in jobs),
        "field_quotes_verified": len(fields),
        "supplementary_quotes_verified": len(diagnostics),
        "document_gates_recomputed": len(documents),
        "positive_critical_supported": dict(Counter(f["arm"] for f in fields if f["critical"] and f["field_gate_pass"])),
        "strict_passes": dict(Counter(d["arm"] for d in documents if d["gate_outcome"] == "pass")),
        "limitations": "Verifies retained artifacts and ledger arithmetic; does not independently authenticate UI observations or prove all semantic judgments. Both source pages and material discrepancies were separately inspected by the primary."
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
