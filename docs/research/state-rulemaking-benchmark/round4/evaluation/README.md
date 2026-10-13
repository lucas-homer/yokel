# Terminal source evaluation infrastructure

Ready evaluator skeleton; no source labeling or fresh-data evaluation was performed. The proposer/runtime remain unchanged. Read `LABEL-API.md` for the labeler integration boundary; concrete JSON schemas are `source-labels.schema.json` and `acceptance-audits.schema.json`. `label-schema.json` is a compact field inventory matching the protocol source-label contract plus typed normalization extensions.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s docs/research/state-rulemaking-benchmark/round4/evaluation -v
python3 docs/research/state-rulemaking-benchmark/round4/evaluation/evaluate.py \
  --manifest FROZEN_SOURCE_MANIFEST.json \
  --labels INDEPENDENT_SOURCE_LABELS.json \
  --audits TERMINAL_SOURCE_ACCEPTANCE_AUDITS.json \
  --run RETAINED_RUNTIME_DIRECTORY \
  --output NEW_EVALUATION_REPORT.json
```

Python standard library only. The evaluator neither imports nor executes the runtime. CLI scoring reads final per-document `shadow-observations.json`, mechanical stage-file existence and fallback-decision status, never provisional model acceptance files, parser text, PDFs, provider responses or source reference snippets. Terminal runs must bind to the scheduled manifest through `pins.json`; output reports cannot overwrite an existing file.

Every scheduled document appears as terminal, partial or not_started. The manifest's actual count controls notice denominators, including quota shortfalls and zero schedules. Labels omitted or not source-complete keep field coverage provisional; known positive counts and missing labels remain visible. Stops and missing candidates cannot shrink eligible source denominators or earn recovery/abstention credit.

Correct field recovery requires a source-eligible group, exact normalized value, and independent terminal acceptance audit confirming role, conditions, scope and precision. DATE is explicit valid YYYY-MM-DD/date-only; EMAIL must match the original source literal exactly, including case/local part. Model support labels never substitute for that audit. Wrong value/role/conditions/precision/scope count as source-incorrect acceptance. Source-conflicted/uncertain roles accepted as settled count as unresolved unsafe acceptance. Missing or unknown audits remain unauditable unsafe acceptance.

Independent `claim_group` IDs deduplicate semantically identical audited native/fallback claims. The field source `distinct_value_group` deduplicates repeated source mentions, while different values/conditions remain distinct required instances. Unsafe duplicates remain visible and prevent notice completeness. Unaudited claims lack sufficient evidence to merge and are conservatively counted separately; raw accepted row counts are also reported.

The report includes DATE, EMAIL and pooled correct field coverage; terminal unsafe acceptance; source-incorrect/unresolved/conflict/unauditable counts; source-audited notice completeness and its resolvable subset; false runtime readiness; OCR requests; unsupported abstention; and scheduled stage accounting. Notice completeness is an evaluator finding, never a retroactive runtime promotion. Unresolved notices do not earn complete-notice credit even when their unsupported-abstention behavior is correct; those outcomes are reported separately. Runtime whole-notice readiness must not be inferred from a supported field or empty candidate list.

Original-source candidate recall, recall conditional on faithful parse, all-proposal normalization accuracy, parser-text judgment accuracy and costs are explicitly unmeasured by this terminal-only adapter. They require separate stage/source audits or billed-cost evidence. This skeleton makes no twelve-notice success claim, national accuracy claim or production readiness claim.

Validation: 23 synthetic tests passed, including terminal-vs-provisional state, three-document and empty scheduled manifests, partial/not_started accounting, separate field denominators, exact email case, date precision, wrong role/conditions, source conflicts/uncertainty, missing audits/labels, duplicate mentions, material source grouping, unsupported abstention, unsafe extras, completeness/readiness, retained-PDF identity, and end-to-end CLI manifest pins. No provider calls, no fresh source reads, no reference-answer reads, and no labels assigned. `validation.json` retains this evidence; `inventory.json` pins the handoff files.

Labeler handoff: map independent source facts to the concrete source schema without changing runtime inputs. After terminal output, supply separate acceptance audits with source field IDs and semantically justified claim groups. Do not amend source truth to match model claims; any source-label correction must remain a versioned independent amendment under the protocol.

Focused reviewer findings E01–E03 were reproduced with four failing synthetic regressions, then fixed independently. Gold absence no longer certifies runtime readiness; an accepted supported fact no longer suppresses abstention on a distinct unsupported fact; claim groups reject different values/source conditions. All 23 tests pass, including valid cross-channel deduplication and unsafe-group tainting. `review-resolution.json` binds the reviewer findings and revised code hash. READY here means ready for independent recheck; Freeze E remains the primary/reviewer decision.
