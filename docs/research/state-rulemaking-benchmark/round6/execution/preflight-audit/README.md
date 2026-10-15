# Mechanical preflight — PREPARED, awaiting source audit release

Owned writes are confined to this directory. Frozen runtime/pipeline/protocol/static selection artifacts remain read-only. No actual collected source audit has run. Five synthetic preparation tests pass; no credentials, network/provider calls, native extraction, proposed record generation or labels inspection.

The checker independently verifies Freeze A exact hashes and bytes, source READY and full file-inventory identity, strict native manifest and minimal collector image inventory, original/input PDF equality, native bytes hashes/caps/UTF-8/codepoint/formfeed page map, actual PDF page-tree counts, all image hashes/maps/dimensions at 150DPI, recorded official URL/redirect-domain provenance and local/recorded tool versions. It never imports the runtime or collector, calls extraction on a PDF, or prints native text, collector completeness assertions, titles, strata, decisive spans, selection notes or expected answers. Metadata metrics are mechanical only, not source fidelity or notice completeness. Exact native re-extraction is outside this task; the collector's prior replay is not reasserted as an independent audit result.

Upon primary's explicit source-READY notification, primary supplies a release JSON with exactly:

```
schema_version: round6.preflight-release.v1
authorized_mechanical_source_audit: true
primary_release_message: verbatim primary authorization
freeze_A_sha256: d2acd7aaed9d08298809aeda03f25ddecf5df28913b753512fdc7fe0edfabe9f
source_READY_sha256: exact SHA256 of sources/source-collection.READY.json
```

Then run bundled Python3.12 with `-B audit.py --primary-release <release JSON>`. No sources are inspected before that notification and binding. Audit outputs are write-once: checks.json, audit.json, labeler-inputs.json and audit.READY.json. The minimal provenance image inventory includes only opaque doc ID, physical page count, recorded official URL, original/input PDF paths/hashes, and physical page/image paths/hashes. It contains no native text, substantive collector assertion or strata. All paths are confined; image inventory uses absolute paths for the labeler.

FreezeA expected58files. Dynamic search/access ledger is outside Freeze A and will be verified only as part of final source READY. Preparation does not execute source checks while collection is underway. Source-shortfall cannot be converted into a successful target claim by this checker.
