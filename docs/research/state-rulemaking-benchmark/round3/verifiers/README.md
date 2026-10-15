# Round 3 verifier adapters

`verifier.py` is a standard-library runner for pinned TypeSafe `jev-1.13.0` and OpenRouter `openai/gpt-4.1-nano`. It makes no credential calls during dry runs. The primary owns freeze, credential injection, paid execution and evaluation. This child made no paid calls.

## Runtime contract and judgments

`INPUT-CONTRACT.json` describes JSONL: one candidate field per case, the complete bounded parser source text, actual structured value, claim, target, semantic role, conditions and exact quote offsets. The challenge's 16-case runtime file conforms. Structured JSON values (ranges/relative clocks) remain structured. `source_text` means supplied parser evidence, not independently verified PDF fidelity. Gold/evaluation labels are separate and rejected as runtime keys. Case IDs do not enter model state. For this scoped challenge, the input construction supplies source_text as an excerpt of candidate.target; target discovery/segmentation is outside evaluation. Both arms receive that identical declared scope assumption and must still distinguish other events/targets explicitly mentioned.

Each adapter sees byte-identical serialized semantic state and the same explicit rubrics. Jev batches four independent Choice questions: support, role, condition and conflict. OpenRouter returns the same four categorical labels with a strict JSON schema. A Noul is unsuitable for the abstaining categorical contract here; no demo Noul threshold is imported. Neither adapter creates a normalized replacement value or a document trust score. The model judges the actual value AND claim, so a correct sentence cannot rescue a corrupted structured value.

Code checks exact Unicode code-point quote offsets without normalization. Missing/invalid evidence, null candidate values and recognizable value/claim disagreements abstain before any provider call. Compound value/prose consistency and semantic role/conditions remain model judgments; deterministic checks do not claim they establish truth. Over-limit context rejects rather than truncates. Known date normalization is limited to ISO and full English month/day/year; ambiguous or partial dates remain semantic/unknown, never guessed.

The primary selected this experimental categorical gate: no deterministic block; support `supported`; role `matched`; condition `preserved`; conflict `absent`. Only that conjunction yields `accept_shadow` and `requires_source_verification`. Every other combination yields review/not_ready. Raw Jev distributions and separately named confidence are retained; **confidence is concentration, not calibrated correctness**. No confidence cutoff is applied. Tied Choice distributions abstain. OpenRouter probabilities/confidence are not manufactured. This is a shadow experiment, not production action approval.

## Running offline and dry

Use the bundled runtime; the host Python had a certificate-store problem. Bundled Python 3 verified public-docs HTTPS successfully with OpenSSL 3.5.8. No dependencies need installing.

```sh
cd /Users/home/.codex/worktrees/e8f4/yokel
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round3/verifiers/offline_checks.py
/Users/home/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/research/state-rulemaking-benchmark/round3/verifiers/verifier.py --input docs/research/state-rulemaking-benchmark/round3/challenge/runtime.jsonl --provider openrouter --output docs/research/state-rulemaking-benchmark/round3/verifiers/execution/general-pilot
```

Change provider to `jev` and use a different output directory for its dry run. Dry-run does not create the output directory and does not read credential env vars. `dry-run-openrouter.json`, `dry-run-jev.json` and `validation.json` record tested engine/input hashes and conservative estimates.

## Paid pilot: primary only

After reviewing and freezing runtime, rubrics and engine, primary adds `--live` to the same command and injects only the applicable env var: `OPENROUTER_API_KEY` or `TYPESAFE_API_KEY`. Use the existing 1Password `op run` wrapper pattern; do not put a resolved key in command text, input files, logs or saved artifacts. This runner does not invoke 1Password. A missing key blocks execution.

Caps are at most 20 cases, at most 20,000 conservatively estimated input tokens per request, at most 1,024 output tokens for OpenRouter (default 512), and at most $0.25 estimated per arm. Jev has no undocumented output-token parameter; its four fixed Choice questions are bounded and output is free at the documented rate. Input estimation uses UTF-8 serialized request bytes plus 1,024 overhead, not a tokenizer; estimates are not invoices. OpenRouter additionally filters provider prices at $0.10/M input and $0.40/M output, requires parameter support, disables provider fallback, and omits model fallback lists. Actual returned model IDs must equal the requested IDs or the arm stops with raw response retained.

Before each POST, the runner fsyncs an immutable request/intent. It makes exactly one POST and never automatically retries, including 429/5xx/timeouts. An execution directory is single-use: restarting against it fails before another POST. Any transport uncertainty, HTTP error, malformed response, missing/invalid usage, refusal, truncation or model drift stops the batch before another case. The immutable intent records the planned POST; `status.json` and `result.json` show what was received. Remaining plan case IDs are unattempted. Do not retry an uncertain request in a new directory without primary reconciliation and explicit budget accounting.

Retained artifacts per case: immutable input/request, intent, exact `response.body` bytes and SHA-256, elapsed/status, categorical result, usage and provenance. Missing usage is never zero. OR's optional reported `usage.cost` stays null when absent. Unsafe responses echoing the supplied key or exceeding 2 MB are not retained; the stop marker explains this narrow exception to exact retention. No Authorization headers or exception messages are logged. TLS is verified and redirects are disabled.

## Protocol integration

These adapter records implement the primary-selected **four-axis categorical gate**. The earlier protocol's single four-way Choice/output schema needs reconciliation before execution: it currently asks for `supported/contradicted/conflicting/insufficient` with one distribution. This implementation deliberately retains four real per-axis distributions rather than inventing a four-way distribution by collapsing them. The primary should freeze the protocol's four-axis revision or request a single-Choice adapter variant before calls. Both model arms must keep the same finalized criteria; evaluating one arm with a different question would invalidate the comparison.

`build_request`, `deterministic`, `parse_response` and `run_cases` are reusable functions. Evaluation should read retained results and separate evaluator labels after execution. The runtime never opens evaluator files.

## Model selection and sources

The live catalog snapshot compares GPT-4.1 Nano, Gemma 3 27B, GPT-4o Mini and Gemini Flash Lite. Gemma previously worked and is slightly cheaper for input; Nano offers supported strict structured output at $0.10/M input and $0.40/M output, versus Gemma's $0.08/M and $0.45/M. Selection is an economical comparison choice, not a claim of superior verification accuracy. The experiment must measure that.

Documentation checked 2026-10-07 UTC: [TypeSafe index](https://docs.typesafe.ai/llms.txt), [HTTP API](https://docs.typesafe.ai/api.md), [models and pinned ID/pricing](https://docs.typesafe.ai/models.md), [Choice](https://docs.typesafe.ai/primitives/choice.md), [Noul](https://docs.typesafe.ai/primitives/noul.md), [state](https://docs.typesafe.ai/concepts/state.md), [confidence](https://docs.typesafe.ai/confidence.md), [citation checks](https://docs.typesafe.ai/cookbooks/citation_check.md), [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade.md), [OpenRouter catalog](https://openrouter.ai/api/v1/models), [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [API](https://openrouter.ai/docs/api/reference/overview), [provider selection/max-price units](https://openrouter.ai/docs/guides/routing/provider-selection). These sources establish API contracts; model quality remains unmeasured here.
