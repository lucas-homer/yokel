# Round 6 source preparation — collection held

Only local preparation has run. No fresh search, source inspection, download, provider, runtime, OCR, or labels calls are authorized until the primary sends explicit code/protocol-freeze release. `preparation.READY.json` means preparation ready, not sources collected.

`selection-plan.json` fixes 24 literal query strings from 24 states, with a fixed 2026 search term and trailing `filetype:pdf`. Search year is not source eligibility. Six general queries precede six conditional queries, then six general and six negative queries. Actual source strata govern quota filling. Search ranking and native/individual-document coverage biases must be disclosed.

`collection-protocol.json` fixes eight complete notices, six general plus two natural conditional/relative/negative controls, at least six states, at most two per state and 40 pages. Native text cap stays 30,000 Unicode codepoints; original PDF cap 25,000,000 bytes. Primary may revise limits only before protocol freeze. Case serialization/context limits require the primary's runtime pin; the collector does not generate cases. Only mechanically defensible individual notices or integrated single regulation filings qualify. No invented scopes, clipping, OCR or substantive-field-presence selection beyond the two control strata.

`dedup-inventory.json` preserves earlier underlying-notice identities and conservatively blocks all available historical PDF hashes, including excluded candidate originals and development/copy bytes. No historical labels are inspected. Prior artifacts are untouched.

Before collection, create `freeze-release.json` only from actual primary authorization, with:

- `authorized_collection: true`
- `primary_release_message`: verbatim message or exact trusted locator
- `timestamp_utc`
- `preparation_ready_sha256`
- `implementation_and_policy_freezes`: nonempty list of `{path, sha256}` for actual pinned freeze files

All collector mutating/transport commands check this receipt and every static preparation hash first. The preparation manifest deliberately excludes `search-access-ledger.jsonl` from immutable hashes: that separate ledger starts empty and is append-only. Search records and acquired files are write-once.

Use pinned Python `/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3` with `-B` to avoid bytecode artifacts. Poppler paths/version are recorded in `native-toolchain.json`.

1. `collect-native.py query-request Q01` emits the exact literal query after release. Submit that value unchanged once to the search tool. Repeat queries and altered strings are prohibited.
2. Before examining candidates, preserve the full raw return in an input JSON with `submitted_query`, `executed_at_utc`, `raw_tool_result`, `returned_result_count`, and `results`. Every result must have its actual consecutive `display_order`, title, URL and reference metadata. Direct official PDF candidates additionally have `direct_pdf_candidate: true` and a `pdf_candidate_basis` (direct PDF extension or observed official document route). Numeric citation IDs never establish rank. Do not expand HTML links. `collect-native.py register-search Q01 record.json` saves the entire response and bounds the first three distinct official candidates.
3. Resolve candidates sequentially with `acquire Q01 1`; this is the sole retrieval mechanism and allows one ordinary retry. Do not web-open then silently add two more attempts. If another access attempt occurs, record it and its consumed retry budget explicitly, resolve/exclude without retry inflation. Acquisition validates all mechanical size/page/native limits before retention; it does not select a source.
4. Record source-only administrative notes matching `source-notes.template.json`, without expected answers or decisive spans. If completeness/identity/native fidelity cannot be established, `exclude Q01 1 "reason"` appends the evidence-based decision. For an eligible source, `retain Q01 1 note.json` rechecks caps and deterministic quotas before copying/rendering/retaining. Full control slots exclude further relative/conditional sources; relative dates are not generally ineligible.
5. Stop immediately when all success conditions hold. Otherwise resolve Q24's bounded candidates and stop with shortfall. Never rerun or substitute for a rejected source. Source errors discovered before freeze must append corrections and preserve all artifacts; do not overwrite historical verdicts or reprocess skipped candidates.
6. Only after the stop point, `freeze-source-bundle.py` verifies exact native replay, original/input equality, page counts and every 150 DPI image, then emits runtime, source audit/metadata, minimal blinded all-page image inventory and source READY. It does not call the parser, model, provider or labels. The blinded inventory has opaque document IDs, page count and only page/image-path/image-hash entries; titles, URLs, strata and selection evidence stay outside it.

Preparation verification uses pure mechanical self-tests, AST compilation without bytecode, hash checks and proof that release-gated commands fail before a receipt exists. No installs, builds or fresh acquisition are needed.
