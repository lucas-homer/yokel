# R16 wire compatibility inventory

Access date for public documentation: **2026-10-13**.

## 1. R14 local checker: accepted syntax and instance behavior

`check_schema()` accepts only JSON-object schema nodes at depth 0–16 and only the following keyword names (R14 `runtime/common.py:49-53`). It rejects any other keyword, regardless of whether that keyword is meaningful to JSON Schema. Thus `$schema`, `prefixItems`, `anyOf`, and `pattern` are rejected as unsupported keys; `$defs` and `$ref` are also rejected. R15’s revised schema contains these keywords, and its spec explicitly says its positional `prefixItems`/`items:false` form is incompatible with the local runtime checker (`round15-condition-preservation/protocol-revised/schema.json`; `round15-condition-preservation/protocol-revised/SPEC.md:39`). `items:false` is rejected because the checker requires `items` to be a schema-object node (`common.py:51,53`).

| Keyword | Accepted schema form | Instance effect in `schema_errors()` |
|---|---|---|
| `type` | Any value is accepted syntactically; intended scalar string or list of strings | Enforces recognized declared type. Integer instances also satisfy `number`. An empty/falsy declaration and unrecognized declaration are not meaningfully checked. |
| `properties` | Any value syntactically; intended object mapping names to schema objects | Recursively validates values only for present keys named in the mapping. Unknown instance keys are handled only by `additionalProperties`. |
| `required` | Any value syntactically; intended list of property names | Reports each listed key absent from an object. No effect on non-object values. |
| `additionalProperties` | Any value syntactically | Only literal `false` rejects undeclared object keys. Missing/true/non-false values allow extras. A schema-valued form is not recursively checked and does not validate extras. |
| `enum` | Any value syntactically; intended array of values | Uses host-language membership/equality to require the instance equal a listed value. |
| `minimum`, `maximum` | Any value syntactically; intended numbers | Enforce inclusive bounds for integer/number instances. |
| `minLength`, `maxLength` | Any value syntactically; intended integers | Enforce Python string length for string instances. |
| `items` | Recursively checked schema object only when present | Each array element is recursively checked against this schema; when missing, the default empty schema allows every element. `false` fails the schema-node object check. |
| `minItems`, `maxItems` | Any value syntactically; intended integers | Enforce inclusive array length bounds. |

The static check is deliberately shallow: it verifies that nodes are dictionaries, depth is at most 16, and keys are in the allowlist; it does **not** validate keyword value types, required/property consistency, or full JSON Schema semantics (`common.py:49-53`). `properties` must function as a mapping whose values are schema nodes, and `items` must be a schema node, because the checker traverses those values. For most other allowed keywords it accepts malformed value forms at schema-check time; any subsequent behavior follows Python operations in `schema_errors()` and may reject or error rather than implementing JSON Schema. Instance validation enforces only the type, enum, required, closed-object, array size/items, string length, and numeric range behavior in the table (`common.py:25-40`). It does not enforce formats, patterns, tuple/prefix items, composition, references, or other constraints. Accepted but irrelevant constraints can therefore pass the schema checker without affecting instances (for example, `minimum` on a string).

**Request size:** canonical JSON bytes are produced with UTF-8 encoding, `ensure_ascii=False`, sorted keys, compact separators, and `allow_nan=False` (`common.py:12`). The body byte count is `len(c.encode(plan['body']))`; the guarded count is body bytes plus 1,024 bytes of allowance and must be at most 40,000 (`contract.py:16`). The runtime also repeats the `guarded_bytes <= 40000` check before dispatch (`adapter.py:129`). This is serialized request-body bytes, not source characters or token count. The frozen request was 28,307 bytes / 29,331 guarded bytes (`runtime/README.md:7`; `runtime/REPORT.json:6-8`).

## 2. Provider route and actual R14 call

**Verified from configuration and receipt:** the adapter POSTs to `https://openrouter.ai/api/v1/chat/completions` (`runtime/adapter.py:107-112`). The request settings select `openai/gpt-6.1-sol`, `stream:false`, `max_tokens:8192`, reasoning effort `low`, OpenAI only, no fallback, and `require_parameters:true` (`runtime/adapter.py:90-92`; `runtime/protocol-revised/request-settings.json:2-20`). Structured output is requested as Chat Completions `response_format: {type:"json_schema", json_schema:{name, strict:true, schema}}`; the actual serialized request includes `strict:true` (`runtime/source-request.json`, top-level `response_format`; adapter builds/post body at `adapter.py:107-110`).

The actual R14 execution receipt records one provider call and a `validated_frozen` result (`round14-semantic-contract/execution/READY.json:52-60`). Its response envelope and result report resolved model `openai/gpt-6.1-sol`, provider `OpenAI`, HTTP 200, and `finish_reason: stop` (`execution/run/result.json`, keys `model`, `provider`, `finish_reason`; `execution/run/status.json`, `http_status`). This is evidence that this exact R14 schema request was accepted and returned a complete response. The newer candidate runtime’s report says `provider_calls: 0` and `provider_compatibility: "unverified"` (`runtime/REPORT.json:55,72-75`); the R14 README also explains the later fresh-source attempt stopped before dispatch (`round14-semantic-contract/README.md:21-32`). So “R14 used” refers to the earlier frozen execution, not the current offline candidate runtime.

## 3. Provider documentation for schema compatibility

The OpenRouter documentation says support is endpoint-specific, instructs callers to set `require_parameters:true`, and says strict enforcement/features vary by provider ([OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs), accessed 2026-10-13). OpenAI’s official Structured Outputs guide documents the following subset and limits ([OpenAI Structured Outputs: supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat), accessed 2026-10-13). These are OpenAI API statements; OpenRouter itself does not publish per-keyword guarantees for this exact model endpoint. The actual R14 successful response is separate empirical evidence for the particular R14 schema.

| Feature | Official OpenAI documentation | Status for exact OpenRouter → OpenAI route |
|---|---|---|
| `anyOf` | Supported within the subset; nested schemas must themselves be valid. Root schema must remain an object (guide lines 16200–16215, 16359, 16561–62). | **Documented for OpenAI; empirical endpoint status UNKNOWN** for arbitrary `anyOf` schema through OpenRouter. |
| Nullable type arrays | Supported: an optional-like value can be a required field with union type including `null`, example `type:["string","null"]` (lines 16438–84). | **Documented for OpenAI; empirical endpoint status UNKNOWN** beyond the concrete schema actually run. |
| `pattern` | Supported for ordinary models; explicitly listed as unsupported additionally for fine-tuned models (lines 16216–23, 16554–60). | **Documented for OpenAI; empirical endpoint status UNKNOWN** for this endpoint’s general pattern subset. |
| `enum` limits | At most 1,000 enum values total. For a single string enum with more than 250 values, combined value length at most 15,000 characters (lines 16492–96). Total string size across property names, definition names, enum and const values is at most 120,000 characters (lines 16489–91). | **Documented for OpenAI; empirical endpoint status UNKNOWN** for the boundary limits. Actual R14 schema’s source-span enum of 108 values was accepted. |
| `prefixItems` | The guide does not mention it in the supported or unsupported keyword lists; no statement found. | **UNKNOWN.** |
| `items:false` | The guide shows schema-valued `items` examples, but does not state support or rejection for boolean `false`. | **UNKNOWN.** |
| `$defs` / `$ref` | Explicitly supported: definitions are referenced with `$ref` and declared in `$defs` (lines 16675–50). Recursive references also have a supported example (lines 16751 onward). | **Documented for OpenAI; empirical endpoint status UNKNOWN** for arbitrary refs through OpenRouter. |
| Nesting depth and property count | Up to 10 levels of nesting and 5,000 object properties total (lines 16485–87). | **Documented for OpenAI; empirical endpoint status UNKNOWN** for boundary acceptance through this endpoint. |
| `additionalProperties:false` | Required for every object schema (lines 16497–500). All fields must also be required; null unions can model nullable fields (line 16395, 16438–84). | **Documented for OpenAI; empirically present in accepted R14 schema.** |

OpenRouter says unsupported structured-output requests and invalid schemas fail, but does not enumerate the exact OpenAI schema dialect it forwards (`OpenRouter Structured Outputs`, “Error Handling”). Do not treat documentation silence as either support or rejection. Also, OpenAI says a strict request with an unsupported JSON Schema receives an error (OpenAI guide lines 16550–60).

## 4. Earlier provider evidence in BENCH

- **R14 actual acceptance:** `round14-semantic-contract/execution/READY.json:52-60` records one provider call with `structural_outcome:"validated_frozen"`; the corresponding request used strict JSON Schema and the response reported HTTP 200 / OpenAI / `openai/gpt-6.1-sol`. This proves acceptance of the exact submitted R14 schema, including its object, array/items, enum (including a 108-value enum), numeric/string bounds, required keys, and `additionalProperties:false`; it does not establish support for omitted keywords such as `anyOf`, `pattern`, `prefixItems`, or `$ref`.
- **R7 note is not counted as provider rejection:** `round7/SPEC.md:71` says “Raw R6 schema is rejected,” but this is a version/migration compatibility statement; the cited artifact does not document an actual provider rejection receipt. No other prior actual provider rejection for a specific schema keyword was found in this inventory.

