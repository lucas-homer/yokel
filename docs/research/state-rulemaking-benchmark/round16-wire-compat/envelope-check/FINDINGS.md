# Source duplication in the r16.w1 request

Read-only offline investigation. No provider or network calls were made, and no credentials were read. The probe rebuilt requests using the current r16.w1 `wire.build`; its rows-only measurements delete `source_text` from a deep copy in memory and re-encode the request.

## 1. Request assembly and span table

**Verified facts.** r16.w1 `build` calls the frozen r15.1 `span_table(source)`, then creates the user envelope with `source_text`, its SHA-256, `span_table`, and the table digest (`protocol/wire.py:224-234`). It canonical-JSON-encodes that envelope and puts the resulting JSON text in the user message's `content`; `common.encode(body)` then encodes the outer request (`wire.py:233-239`). Thus the source string appears once as `source_text` and again in the row texts, with nested JSON string escaping.

`span_table` uses `source.splitlines(keepends=True)`. Each row is `[sN, start, start + len(part), part]`, and `start` advances by the part's Unicode codepoint length. The function requires final `start == len(source)` (`round15-condition-preservation/protocol-revised/compact.py:138-147`). `validate_table` compares against a freshly generated table; `reconstruct` joins row texts and explicitly compares UTF-8 bytes (`compact.py:150-158`). r16.w1 `schema`, called by `build`, validates the table (`round16-wire-compat/protocol/wire.py:126-129`). But `build` does not call `reconstruct`.

**Conclusion.** Exact concatenation is guaranteed by construction: `splitlines(keepends=True)` returns the source's line segments with their line endings retained, and the table checks that their accumulated character length covers the source. There is no normalization or inserted separator. The explicit UTF-8 reconstruction comparison exists as a separate verifier, not as a build-time check.

## 2. Reconstruction coverage

**Verified facts.** The offline probe compared UTF-8 bytes from the source with bytes from `''.join(row[3] ...)`, recorded the first differing byte offset on mismatch, checked contiguous codepoint offsets, and called `reconstruct`. Every case matched; no first differing offset exists:

| Source | UTF-8 bytes | Rows | Exact byte reconstruction | `reconstruct()` |
| --- | ---: | ---: | --- | --- |
| prior R14 parsed-body source | 7,208 | 108 | yes | passed |
| disjoint600-u24 | 14,423 | 24 | yes | passed |
| r15.1 `source.txt` | 1,234 | 9 | yes | passed |
| r15.1 `long_disjoint1-source.txt` | 714 | 1 | yes | passed |
| r15.1 `long_disjoint8-source.txt` | 5,719 | 8 | yes | passed |
| r15.1 `long_disjoint16-source.txt` | 11,446 | 16 | yes | passed |
| r15.1 `long_shared8-source.txt` | 714 | 1 | yes | passed |
| r15.1 `long_shared64-source.txt` | 714 | 1 | yes | passed |

The probe output has the SHA-256s, contiguous-coverage results, and each mismatch offset (all `null`) in `probe-output.json`. It searches every `*source.txt` under the r15.1 fixtures directory.

## 3. Dependencies on `source_text`

**Verified facts.** The r15.1 system prompt says to inventory the complete supplied source, says the complete source and span table are supplied, and describes row text, codepoint offsets, and exact anchors (`protocol-revised/stage-a.system.txt:1-2`). Its instruction to echo schema-bound source/table hashes is on line 1. The r16.w1 prompt edits change the envelope version, fragment shape, and deadline representation; none refers to `source_text` (`round16-wire-compat/protocol/wire.py:201-221`). The model is asked to emit span IDs and exact text anchors, not source-relative numeric offsets (`stage-a.system.txt:2,6`; `wire.py:151-152`).

The input `source_text_sha256` is distinct from the duplicate text field and is not removed by this proposed change (`wire.py:228-229`). Output `h` and `t` are constrained by the response schema to the source hash and table digest (`wire.py:165-167`); the prompt's hash-echo instruction remains meaningful because those values remain schema-bound. The hash is SHA-256 over UTF-8 (`compact.py:60-63`).

**Conclusion / inference.** With `span_table` and its text rows intact, removing only `source_text` changes no source content, line-ending or Unicode information, anchor/offset convention, or hash-echo meaning available to the model. The JSON envelope shape does change, so this is a wire-contract change even though no unique source information is lost. This finding covers the supplied r16.w1 builder and prompt; it does not assert compatibility with consumers that require the old four-key envelope.

## 4. Guarded-byte measurements

**Verified facts.** Each guarded size is outer `common.encode(body)` UTF-8 byte length plus the builder's 1,024-byte allowance (`wire.py:237-240`). In a deep-copied request, the probe removed just the inner `source_text` key and re-encoded the body:

| Profile | Full guarded bytes | Without `source_text` | Bytes saved | Under 40,000? |
| --- | ---: | ---: | ---: | --- |
| Prior R14 parsed-body | 31,374 | 23,931 | 7,443 | yes |
| disjoint600-u24 | 43,432 | 28,942 | 14,490 | yes |

The earlier draft design report lists 28,880 bytes for the 24-row rows-only variant (`round16-wire-compat/design/DESIGN.md:249,261-263`). The current `wire.build` measurement is 28,942 bytes. The r16.w1 builder appends an additional `y=[]` clarification to its system prompt (`protocol/wire.py:216`), while the draft sizing helper builds the prompt from the five prompt edits without that appended clarification (`design/probe.py:195-211`); that accounts for the 62-byte difference.

## Verdict

**Conditional yes:** removing the duplicate field is lossless for the source and instructions the model needs, provided the exact span rows and hashes remain present and the same source partition is used. The field removal still changes the serialized user-envelope contract and requires consumers to accept the rows-only shape.

## Artifacts written

- `envelope-check/FINDINGS.md` — this report.
- `envelope-check/probe.py` — isolated offline reconstruction and sizing probe.
- `envelope-check/probe-output.json` — observed results.

Probe invocation: `python3 -I -S -B docs/research/state-rulemaking-benchmark/round16-wire-compat/envelope-check/probe.py`.
