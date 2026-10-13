"""Independently verify the evidence ledger and recompute descriptive metrics.

Usage: python aggregate_results.py ARTIFACT_ROOT [--allow-partial]
       [--results-dir PATH] [--output-dir PATH]
No vendor calls. Final reporting requires all 80 document and 696 field rows.
This verifies bookkeeping and exact quotes, not the reviewer's semantic judgment.
"""
import argparse
import collections
import hashlib
import itertools
import json
import statistics
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counter(items):
    return dict(collections.Counter(items))


def load_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--results-dir", type=Path, help="Ledger directory (default: ROOT/review/results-v1)")
    parser.add_argument("--output-dir", type=Path, help="Metrics destination (default: ROOT)")
    args = parser.parse_args()
    root = args.root.resolve()
    results = args.results_dir.resolve() if args.results_dir else root / "review/results-v1"
    output = args.output_dir.resolve() if args.output_dir else root
    frozen = json.loads((root / "corpus-freeze.json").read_text())
    units = {u["fixture_id"]: u for u in frozen["units"]}
    contract = json.loads((root / "review/scoring-contract.json").read_text())
    arms = contract["arms"]
    fields = load_lines(results / "field-scores.jsonl")
    documents = load_lines(results / "document-scores.jsonl")
    operations = load_lines(results / "operation-records.jsonl")
    extra = load_lines(results / "extra-assertions.jsonl")
    references = {fid: {f["field_id"]: f for f in json.loads((root / u["reference_path"]).read_text())["reference_fields"]} for fid, u in units.items()}
    expected_docs = set(itertools.product(units, arms))
    expected_fields = {(fid, arm, field) for fid in units for arm in arms for field in references[fid]}
    assert len(documents) == len(operations) == 80
    assert len(fields) == len(expected_fields) == 696
    assert {(d["fixture_id"], d["arm"]) for d in documents} == expected_docs
    assert {(o["fixture_id"], o["arm"]) for o in operations} == expected_docs
    assert {(f["fixture_id"], f["arm"], f["field_id"]) for f in fields} == expected_fields
    for rel, record in frozen["files"].items():
        assert sha(root / rel) == record["sha256"], ("frozen artifact changed", rel)
    complete_docs = [d for d in documents if d["evaluation_status"] == "complete"]
    complete_fields = [f for f in fields if f["evaluation_status"] == "complete"]
    complete_ops = [o for o in operations if o["evaluation_status"] == "complete"]
    complete = len(complete_docs) == 80 and len(complete_fields) == 696 and len(complete_ops) == 80
    assert complete or args.allow_partial, "Evaluation incomplete; no final metrics"

    texts = {}
    quote_count = 0

    def check_output(row, quote_key=None):
        nonlocal quote_count
        rel = row.get("output_artifact")
        if rel:
            path = (root / rel).resolve()
            assert path.is_relative_to(root), rel
            if rel not in texts:
                texts[rel] = (path.read_text(), sha(path))
            text, digest = texts[rel]
            assert digest == row["output_artifact_hash"], rel
            quote = row.get(quote_key) if quote_key else None
            if quote:
                assert quote in text, (row.get("fixture_id"), row.get("field_id"), "quote not retained")
                quote_count += 1
                loc = row.get("output_locator")
                if isinstance(loc, dict):
                    for left, right in [("char_start", "char_end"), ("start_char", "end_char"), ("start", "end")]:
                        if left in loc and right in loc:
                            assert text[loc[left]:loc[right]] == quote, (rel, loc)
                            break
        elif quote_key:
            assert not row.get(quote_key), "Quote without output artifact"

    for row in complete_docs + complete_fields + complete_ops:
        unit = units[row["fixture_id"]]
        assert row["input_sha256"] == unit["input_sha256"]
        assert row["reference_version_hash"] == unit["reference_sha256"]
        assert row["operation_status"] in contract["operation_statuses"]
        check_output(row, "exact_output_quote" if "field_id" in row else None)
    field_index = collections.defaultdict(list)
    for row in complete_fields:
        fid, arm = row["fixture_id"], row["arm"]
        reference = references[fid][row["field_id"]]
        for key in ["critical", "answerability", "semantic_group_id"]:
            assert row[key] == reference[key], (fid, row["field_id"], key)
        assert row["outcome"] in contract["outcome_definitions"]
        gate = row["operation_status"] == "completed_nonempty" and row["outcome"] in contract["field_gate_rules"][row["answerability"]]
        if gate and row["answerability"] == "not_stated":
            gate = row["scope_coverage"] == "complete"
        if gate and row["answerability"] in ("present", "explicit_negative"):
            gate = row["decisive_relation_preserved"] is True
            assert row["exact_output_quote"], (fid, row["field_id"], "supported answer needs evidence")
        assert row["field_gate_pass"] == gate, (fid, arm, row["field_id"], "gate mismatch")
        field_index[fid, arm].append(row)
    extra_index = collections.defaultdict(list)
    assert len({e["assertion_id"] for e in extra}) == len(extra)
    for row in extra:
        assert (row["fixture_id"], row["arm"]) in expected_docs
        check_output(row, "assertion_text")
        if row["critical"]:
            extra_index[row["fixture_id"], row["arm"]].append(row["assertion_id"])
    operation_index = {(o["fixture_id"], o["arm"]): o for o in complete_ops}
    for doc in complete_docs:
        fid, arm = doc["fixture_id"], doc["arm"]
        rows = field_index[fid, arm]
        assert len(rows) == len(references[fid]), (fid, arm, "incomplete field evaluation")
        assert operation_index[fid, arm]["operation_status"] == doc["operation_status"]
        assert all(f["operation_status"] == doc["operation_status"] for f in rows)
        assert doc["reference_gate_eligible"] == units[fid]["reference_gate_eligible"]
        assert set(doc["critical_extra_assertion_ids"]) == set(extra_index[fid, arm])
        if not doc["reference_gate_eligible"]:
            gate = "insufficient_reference"
        elif doc["operation_status"] == "not_attempted_provider_stop":
            gate = "not_attempted_provider_stop"
        elif doc["operation_status"] != "completed_nonempty":
            gate = "operational_unusable"
        else:
            assert doc["extra_assertion_audit_complete"]
            gate = "pass" if all(f["field_gate_pass"] for f in rows if f["critical"]) and not extra_index[fid, arm] else "content_fail"
        assert doc["gate_outcome"] == gate, (fid, arm, "document gate mismatch", gate)

    def metrics(docs, rows):
        positive = [r for r in rows if r["critical"] and r["answerability"] in ("present", "explicit_negative")]
        usable_positive = [r for r in positive if r["operation_status"] == "completed_nonempty"]
        negative = [r for r in rows if r["critical"] and r["answerability"] == "not_stated"]
        usable_negative = [r for r in negative if r["operation_status"] == "completed_nonempty"]
        groups = collections.defaultdict(list)
        for r in rows:
            if r["critical"] and r["answerability"] != "uncertain":
                groups[r["fixture_id"], r["semantic_group_id"]].append(r)
        return {
            "documents": len(docs), "document_gates": counter(d["gate_outcome"] for d in docs),
            "operations": counter(d["operation_status"] for d in docs),
            "reference_eligible_documents": sum(d["reference_gate_eligible"] for d in docs),
            "critical_positive_evidence_yield": {"supported": sum(r["field_gate_pass"] for r in positive), "scheduled": len(positive), "outcomes": counter(r["outcome"] for r in positive)},
            "critical_positive_successful_output_content": {"supported": sum(r["field_gate_pass"] for r in usable_positive), "eligible": len(usable_positive)},
            "critical_not_stated_scope": {"safe_abstention": sum(r["field_gate_pass"] for r in usable_negative), "usable_output_eligible": len(usable_negative), "scheduled": len(negative)},
            "determinate_critical_groups": {"all_facets_pass": sum(all(r["field_gate_pass"] for r in rs) for rs in groups.values()), "scheduled": len(groups)},
            "critical_uncertain_fields": sum(r["critical"] and r["answerability"] == "uncertain" for r in rows),
            "critical_field_outcomes": counter(r["outcome"] for r in rows if r["critical"]),
            "documents_with_critical_incorrect_assertions": sum(bool(d["critical_extra_assertion_ids"]) for d in docs),
        }

    summary = {"complete": complete, "scope": "Agent-reviewed evidence preservation on this purposive corpus; not automated extractor precision or national accuracy.", "frozen_counts": frozen["counts"], "arms": {}, "paired_document_gates": {}, "paired_usable_positive_evidence": {}, "strata": {}}
    for arm in arms:
        docs = [d for d in complete_docs if d["arm"] == arm]
        rows = [r for r in complete_fields if r["arm"] == arm]
        summary["arms"][arm] = metrics(docs, rows)
        timing = [o["wrapper_wall_ms"] for o in complete_ops if o["arm"] == arm and o["operation_status"] == "completed_nonempty" and o.get("wrapper_wall_ms") is not None]
        summary["arms"][arm]["successful_wrapper_latency_ms"] = {"observations": len(timing), "median": statistics.median(timing) if timing else None, "min": min(timing) if timing else None, "max": max(timing) if timing else None}
    docs_by_key = {(d["fixture_id"], d["arm"]): d for d in complete_docs}
    for left, right in itertools.combinations(arms, 2):
        cells = collections.defaultdict(list)
        for fid in units:
            if (fid, left) not in docs_by_key or (fid, right) not in docs_by_key:
                continue
            a, b = docs_by_key[fid, left], docs_by_key[fid, right]
            if not a["reference_gate_eligible"]:
                category = "reference_insufficient"
            elif a["operation_status"] != "completed_nonempty" or b["operation_status"] != "completed_nonempty":
                category = "one_or_both_operationally_unusable"
            elif a["gate_outcome"] == b["gate_outcome"] == "pass":
                category = "both_pass"
            elif a["gate_outcome"] == "pass":
                category = "left_only_pass"
            elif b["gate_outcome"] == "pass":
                category = "right_only_pass"
            else:
                category = "both_content_fail"
            cells[category].append(fid)
        summary["paired_document_gates"][f"{left}__{right}"] = dict(cells)
        common = {fid for fid in units if (fid, left) in docs_by_key and (fid, right) in docs_by_key and docs_by_key[fid, left]["operation_status"] == docs_by_key[fid, right]["operation_status"] == "completed_nonempty"}
        pairs = []
        for fid in sorted(common):
            a_fields = {f["field_id"]: f for f in field_index[fid, left]}
            b_fields = {f["field_id"]: f for f in field_index[fid, right]}
            for field_id, a in a_fields.items():
                if a["critical"] and a["answerability"] in ("present", "explicit_negative"):
                    pairs.append((fid, field_id, a["field_gate_pass"], b_fields[field_id]["field_gate_pass"]))
        summary["paired_usable_positive_evidence"][f"{left}__{right}"] = {
            "common_nonempty_documents": len(common), "eligible_fields": len(pairs),
            "left_supported": sum(a for _, _, a, _ in pairs), "right_supported": sum(b for _, _, _, b in pairs),
            "left_only_supported": [{"fixture_id": fid, "field_id": f} for fid, f, a, b in pairs if a and not b],
            "right_only_supported": [{"fixture_id": fid, "field_id": f} for fid, f, a, b in pairs if b and not a],
        }
    for dimension in ["state", "primary_bucket", "layout_features", "event_type"]:
        groups = collections.defaultdict(set)
        for fid, unit in units.items():
            values = unit[dimension] if dimension == "layout_features" else [unit[dimension]]
            for value in values:
                groups[value].add(fid)
        summary["strata"][dimension] = {value: {arm: metrics([d for d in complete_docs if d["arm"] == arm and d["fixture_id"] in ids], [r for r in complete_fields if r["arm"] == arm and r["fixture_id"] in ids]) for arm in arms} for value, ids in groups.items()}
    validation = {"passed": True, "complete": complete, "frozen_files_verified": len(frozen["files"]), "completed_document_rows": len(complete_docs), "completed_field_rows": len(complete_fields), "exact_quotes_verified": quote_count, "output_artifacts_verified": len(texts), "recomputed_document_gates": len(complete_docs), "source_ledgers": {name: sha(results / name) for name in ["field-scores.jsonl", "document-scores.jsonl", "operation-records.jsonl", "extra-assertions.jsonl"]}, "limit": "Checks integrity, quote existence, frozen reference identity and deterministic aggregation; semantic judgments also need source/output review."}
    output.mkdir(parents=True, exist_ok=True)
    (output / "primary-metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output / "primary-verification.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps({"validation": validation, "arms": summary["arms"]}, indent=2))


if __name__ == "__main__":
    main()
