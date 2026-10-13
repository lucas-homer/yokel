# Independent lossless size-diagnostic review

2026-10-11. **PASS for diagnostic data preservation and measured byte savings.
Recommend the quote-and-offset table as the next candidate for separate contract
review; no live/provider compatibility or semantic-success approval.**

Reviewed prototype SHA-256:
`73bc13bee5615c294bc5ecf21a86c4f730708c1e7b1cefd783391b46a6484104`.
Reviewed REPORT.json SHA-256:
`dd2f6c85f0e6a7efca8e24731a9070b66fb80166318763a82f5ac8903a27490e`.
Owner was finishing the prototype; this verdict applies to those exact snapshots.

## Independently verified

Extracted only codec, sizing and restoration functions/constants from the prototype
AST into a clean isolated Python process, without executing its artifact-writing
top-level program. Independently verified all 25 frozen E entries by confined paths,
size and SHA-256, then read the two frozen verifier requests. Their full payloads
match. Recomputed report baselines, every variant's full body measurements and net
savings including decoder instructions in all five Jev questions and the stronger
system message. Every value matched the report.

For each variant, canonical JSON bytes of decoded payload exactly equal the original,
and both fully restored request bodies exactly equal the original canonical bodies.
The source, entire record, IDs, associations, groups, uncertainties, evidence sequence,
duplicate evidence uses, and all remaining body settings survive restoration.
This is canonical JSON equality, not a claim that arbitrary original whitespace or
serialization formatting is preserved. Both arm wire payloads remain identical.

29 independent assertion groups passed, including repeated identical text at distinct
positions, astral Unicode plus combining characters, the same evidence repeated
within/across containing items, empty evidence lists, associated event/route/group
IDs, changed source, negative/out-of-range/boolean/string references or offsets, and
table quote corruption. Distinct spans with identical quote text remain separate
entries; exact quote-plus-span entries deduplicate without losing occurrences.
Evidence-reference bounds and codepoint spans reject malformed tested inputs.
The codec does not validate domain ID referential integrity or the entire extraction
schema: those associations are retained exactly and remain the original validator's
responsibility. Preservation is established for validated inputs, not arbitrary
malformed-record acceptance.

## Net full-request savings and recommendation

| Diagnostic variant | Jev bytes saved | Stronger bytes saved | Jev state+longest estimate | Stronger estimate |
| --- | ---: | ---: | ---: | ---: |
| Quote-and-offset table | 2817 | 4798 | 28708 / 32000 | 35755 / 40000 |
| Inline spans | 6874 | 8858 | 24703 / 32000 | 31695 / 40000 |
| Span table | 7538 | 9752 | 23963 / 32000 | 30801 / 40000 |

Baseline limiting estimates were 33149 / 32000 for Jev state+longest question and
40553 / 40000 for stronger. All three variants mechanically fit the unchanged
byte-based guards after accounting for instruction overhead; Jev total-body guard
also passes. These are the actual canonical UTF-8 body byte differences, not measured
provider token savings. The estimates remain bytes+1024, and no verifier was called.

Prefer the quote-and-offset table despite its smaller savings: every table object
contains the original exact quote, start and end. Models need only resolve integer
references and apply evidence to its containing item; they need not calculate Unicode
offset slices. The inline-span and span-table decoders are computationally lossless,
but their proposed model instructions require reconstructing quote text from codepoint
arithmetic over the full source. Their greater byte savings do not establish equally
reliable evidence retrieval. Table indirection also creates a model lookup burden;
its correctness still needs separate evidence, not inference from roundtrip tests.

The report correctly marks prototypes diagnostic-only, unobserved, provider-incompatible,
and model correctness unmeasured. The changed wire envelopes and added instructions
need a new reviewed contract and provider-shaped tests before any separately authorized
live experiment. This review approves no schema/guard/runtime change, new runner,
automatic retry, or expansion of experiment scope.

Changed only this new size-review report. No old/frozen writes, owner-program execution,
live/provider/network calls, credentials, reference-label interpretation or deployment.
