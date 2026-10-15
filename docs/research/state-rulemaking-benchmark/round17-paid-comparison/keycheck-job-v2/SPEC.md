# R17 metadata-only native signed job v2

This is an offline implementation candidate copied from frozen `keycheck-job/`,
excluding `proposals-*`, `evidence-*`, and `LIVE-VARS.txt`. V1 was not edited.
The reported 2026-10-14 run reached adapter initialization and then rejected
metadata; the exact live cause remains unknown. Masked `data.label` is a
hypothesis reproduced synthetically, not a verified provider response. This task
made no network calls and did not inspect credentials or invoke native tools.
The copied `primary-review/REVIEW.md` is historical v1 evidence, not v2 approval.

This candidate It does not establish the installed
credential's metadata, live timing, independent review acceptance or permission
to release the paid comparison. All implementation artifacts are confined here.

## Native compatibility and staging

Sources inspected: `tools/research-credentials-stable/{INTERFACE.md,README.md,
Manifest.h,runner.m,release.py}`, `runner-stability-review/deployment/core.json`,
the prior `live-smoke/job-alpha` proposal/adapter and R17
`adapter-r1-4/host_driver.py` / `release-prep-a4-r2/README.md`.

`Manifest.h` requires exactly six arguments, including an adapter path ending in
`/adapter.py`. Therefore stage **the exact keycheck.py bytes as adapter.py**;
there is no wrapper or additional imported local file. The job requests only
`OPENROUTER_API_KEY`; its fixed reference comes from the deployed core, never
from a caller. `~/.t3` is outside the deployed adapter roots. A fresh staging
directory under `/Users/home/dev/yokel` contains exactly `adapter.py` and a
primary-accepted independent `REVIEW.md`. Generated outputs live beside them.

`make_keycheck_proposal.py` requires the staged copy to exist, match the candidate,
and satisfy the configured canonical roots. It rejects using this SPEC as the
review. The primary remains responsible for review semantics. It produces a
fresh UUID-bearing native-compatible ID, an expiry in the next seven days,
30-second native timeout, exact supplied prior/ceiling nanodollars and zero
reservation. Native budget fields are signed metadata; the zero-cost property
comes from the adapter's sole fixed GET transport path.

The stage manifest lists exactly the two staged payload/review files. External
runtime pins follow the stable smoke precedent: interpreter, stdlib source,
cached bytecode, extensions and bundled top-level dylibs, excluding site-packages.
`-B` prevents new bytecode writes but does not prevent existing bytecode reads.
This is a conservative runtime closure, not a claim that every stdlib file is
imported. They are not copied into the stage. Native pin counts/body-size limits
are checked. System libraries and CA trust remain host prerequisites. The CA
cannot be a native file pin because `/etc/ssl/cert.pem` is outside dependency
roots; its SHA256 is recorded at runtime and its bytes are checked for change.
Outputs, tests, documentation and offline helpers are not job payload pins.

## Request and credential handling

Import is inert. Only the exact `--live-initial` invocation with the fixed bundled
interpreter and `-I -S -B` reaches transport. Successful preflight makes exactly
one HTTPS GET to `https://openrouter.ai/api/v1/key` with no body. Preflight/TLS
failures can make zero requests. There is no configurable method/host/path,
completion endpoint, model payload, subprocess, proxy, redirect or retry route.
Raw `http.client.HTTPSConnection` bypasses proxy environment variables.

TLS mirrors the hardened host driver: `SSLContext(PROTOCOL_TLS_CLIENT)`, hostname
checks and CERT_REQUIRED, explicit `load_verify_locations(cafile='/etc/ssl/cert.pem')`,
nonempty CA store, no default-context/keylog environment discovery. A 15-second
SIGALRM covers CA load, DNS, TLS, request, response and parsing; socket timeout is
also 15 seconds. Native timeout is 30 seconds. One bounded body read uses a
65,537-byte sentinel; bodies above 65,536 bytes fail. Only HTTP 200 proceeds.

The key is popped from `os.environ` inside the metadata call. It exists transiently
in the Authorization header and transport buffers, never in an output, key hash,
length, command argument or log. Local holders are deleted and the connection is
closed on all outcomes. Main also removes the environment variable on preflight
failure. Python cannot guarantee zeroization of immutable strings, inherited OS
environment storage, or copies in library memory. This is deletion of application
references, not a secure-memory claim. No Keychain, signing key, credential store
or provider reference resolver is implemented here.

Transport/parser/close errors, including interruptions, become a fresh fixed
exception outside the original handler. No original exception context is chained. Outward exception text is a fixed stage code.
The CLI emits a fixed status string. Plain credential echoes anywhere in the
response fail; escaped echoes in all decoded fields/names, including ignored fields and nested lists, also fail. No response
headers or raw body are written.

## FAILURE.json: fixed diagnostics, never raw data

All failures within `get_metadata_once()` become a fresh `Rejected(stage)` after
secret-bearing locals and original exceptions/tracebacks have been discarded.
`run()` publishes its sanitized `failure` record as `FAILURE.json` and re-raises;
the CLI returns 1 and prints only `Metadata check rejected.`. It writes no
KEY-MACHINE on a metadata failure. Every failure record contains only
`schema_version: "r17.keycheck-failure.v2"`, `stage`, and the extras below:

| Stage (fixed enum) | Meaning | Allowed extra fields |
| --- | --- | --- |
| `key_env_invalid` | Missing/empty/nonprintable/non-ASCII injected key or forbidden extra provider variable | none |
| `tls_context` | Explicit trust-file loading or TLS context validation | none |
| `connect` | DNS, TCP, TLS handshake, connection construction; close failure if there was no earlier failure | none |
| `request_send` | Sending the sole fixed GET | none |
| `response_status` | Getting HTTP status/headers or reading the bounded response; non-200 status | integer `status` if obtained; integer `error_code` from top-level JSON `error.code` if safely available |
| `body_too_large` | HTTP 200 body exceeds 65,536 bytes | none |
| `key_echo_in_body` | HTTP 200 body echoes key literally or in a decoded string/name anywhere | none |
| `json_parse` | Invalid UTF-8/JSON, duplicate names, nonfinite constant, parser failure | none |
| `missing_fields` | Required `data`, `label`, `limit`, `usage`, or uncomputable absent `limit_remaining` | sorted `missing_fields`, containing only missing expected names |
| `field_type` | Unexpected type or invalid numeric domain | `field` (allowlisted field name), `type` (Python type name only) |
| `label_shape` | Unsafe/oversized/empty name or unrecognized credential-shaped label; unsafe reset string | none |
| `deadline` | 15-second SIGALRM expiry, socket TimeoutError, or unavailable deadline setup | none |

`field_type` names are the fixed field names plus `root`, `data`,
`response_body`, `response_status` and `usage_*`. Supplemental usage names are
normalized to `usage_*` so arbitrary response-controlled names cannot leak.
Type names are restricted to Python JSON/buffer/number types (plus fixed `other`
for an unexpected Python class); names of custom classes are not copied.
Negative/nonfinite numeric fields are rejected with their type, never value.

No body, header, message, exception text, response-controlled extra name, key
fragment, key length, or key hash is included. A non-200 status takes precedence
over its error body's shape/size/echo and is retained even if body reading fails;
`error_code` is optional. Extraction uses the same bounded read and strict JSON
parser, rejects bool/float/string codes, and omits it for a malformed, duplicate,
oversized or key-echoing body. Timeout always becomes `deadline`. No secondary
request is made to diagnose a failure. If no status is obtained, it is omitted.

Output-path/preflight and filesystem-publication failures remain fixed CLI
rejections; they cannot promise a diagnostic receipt when the destination is
unusable. SIGKILL/native termination can also leave timing only. Existing or
partially written receipts are preserved, never repaired or overwritten.

## KEY-MACHINE.json v2 and labels

`schema_version` is `r17.key-machine.v2`. Strict parsing uses native Python `int`
for integer tokens and `Decimal` for fractional tokens. Numeric fields accept
both (explicitly excluding bool), normalize ints to exact Decimal, and retain
exact JSON numbers. Duplicate names and nonfinite constants fail. Top-level
`data` must be an object. Only these fields survive: `label` (plain names only),
optional `name`, `limit`, `limit_remaining`, `limit_reset`, `usage`, numeric/null
`usage_*` matching `usage_[a-z0-9_]+`, and optional boolean `is_free_tier`.
Unknown fields are discarded after the whole decoded tree is checked for echoes.

The masked-label regex is exactly
`sk-or-v1-[0-9a-f]{3,8}\.\.\.[0-9a-f]{3,8}` with `re.ASCII` and `fullmatch`:
ASCII lowercase hex, 3–8 characters on each side of exactly three literal dots,
no prefix/suffix whitespace or newline. This is equivalent to an anchored whole
string match. Other `sk-or-` shapes fail closed; no live shape is asserted.

- A masked label is **omitted entirely** from `fields`; record
  `label_kind="masked_key"` and `label_name_verifiable=false`.
- If `data.name` is present it must be a printable string of 1–100 characters
  without case-insensitive `sk-or-`, `bearer` followed by whitespace, or
  `authorization`. Record the safe name and compare it exactly to `DocketClock`.
  A safe mismatching name produces machine FAIL; an unsafe name is rejected.
  The masked label itself stays unverifiable even when the separate name matches.
- Without a name, record `checks.label="not_machine_verifiable"`,
  `label_check="not_machine_verifiable"`, `name_field_present=false`, and
  `user_attestation_required=true`. Machine PASS can establish the financial
  conditions, but **does not attest the DocketClock key name**. The primary must
  obtain the user's name attestation before accepting this path.
- A plain label follows v1: safe short string, recorded verbatim, exact
  `DocketClock` comparison. Record `label_kind="plain_name"`,
  `label_name_verifiable=true`. An optional separate name must also match.
  `label_check` is `match` or `mismatch` when machine verifiable.

`label`, `limit`, and `usage` are required. Missing `limit_reset` is normalized
to null with `limit_reset_present=false`; explicit null records true. Missing
`limit_remaining` is derived by exact Decimal subtraction `limit - usage` only
when both operands are numeric; record `limit_remaining_computed=true`.
Provided remaining values are checked independently and never silently replaced.
The subtraction bounds exponent span to 65,536 before allocating precision;
an uncomputable missing remaining rejects rather than fabricating a value.

Hard PASS conditions remain `usage == 0`, `limit == 50`, `limit_reset is null`,
and `limit_remaining == 50` (provided or computed). All four checks must be
literal true. The name/label check must be true or explicitly
`not_machine_verifiable`; false always fails. Well-formed mismatches write a
sanitized KEY-MACHINE with status FAIL and exit 1, rather than FAILURE.json.
Additional usage fields never override total usage. `accepted_by_primary=false`
and `units_and_field_documentation_confirmed_by_primary=false` remain mandatory.

Receipts retain the endpoint, raw-response SHA256 (never the raw response), CA
SHA256, USD currency and request/retrieval timestamps. No field-documentation
lookup occurred. USD 50.00 equals 50,000,000,000 nanoUSD.

All three receipt paths are preflighted with `lexists` before any transport.
Publication is exclusive `O_EXCL|O_NOFOLLOW`, owner-only mode0600, followed by
file fsync and parent-directory fsync. No previous output or symlink is replaced.
A partial attempt needs a fresh reviewed stage, proposal and job ID.

## BOOTSTRAP-TIMING.json and N29

`runner.m` builds a clean HOME/PATH/LANG environment, then copies only provider
variables into the payload. It emits no native start/deadline timestamp. The
claim journal stores only the signed manifest hash, not a timestamp. The native
job clock starts in `Subprocess` after task launch; op resolution and repeated
pre-exec pin hashing occur before adapter entry. Identity/initial validation
precede that job clock. No trusted job-start timestamp can be read by this adapter.

The adapter records wall/monotonic nanoseconds immediately after `import time`,
before other imports, and again after argument/output preflight before publishing
timing and issuing GET. It writes its measured initialization duration and honest
null bootstrap/reserve values before transport, so GET failure can still leave
timing evidence. Native start, interpreter startup/import time and pre-exec work
remain an explicit gap. The key GET/body parsing are outside bootstrap.

The primary's documented outer wrapper captures both clocks immediately before
and after the single native `run`, return code and native stdout/stderr receipt.
`measure_bootstrap.py` is an **offline** join, never a launcher. It requires
primary confirmation of same host/boot/monotonic clock, successful native return
and ordered boundaries. It computes:

```
bootstrap_seconds = (adapter_ready_monotonic_ns - before_run_monotonic_ns) / 1e9
native_reserve_seconds = 60 - bootstrap_seconds
```

This is explicitly a conservative **outer-run-to-adapter-ready upper bound**,
not the exact native deadline-to-exec interval. It includes validation, initial
pin hashing, claim, token/identity work and supervisor startup in addition to op
resolution, pre-exec hashing and adapter initialization. If the bound is under
60 seconds, the resulting positive reserve is conservative for N29. If it is
60 seconds or more, stop; that does not prove the narrower native bootstrap was
too slow. Native instrumentation would be a separately reviewed runner change.

Joined measurements use exact decimal strings and bind the original adapter
timing, primary boundary file and native receipt SHA256. The original partial
receipt is preserved; the joined file is written at a fresh evidence destination
as `BOOTSTRAP-TIMING-JOINED.json` (the raw `BOOTSTRAP-TIMING.json` is also copied). Primary acceptance remains false. This task has no
live measurement, fabricated margin, provider billing verification or signed job.

## Offline validation

Tests use synthetic keys and a fake socket installed at the real http.client
connection seam. Unexpected real socket construction raises immediately. No
runner, executor, release or check-job is invoked. Temporary files remain under
this directory and are deleted. Static AST checks and actual HTTP wire capture
assert a single fixed GET and the absence of paid-operation paths. Tests cover
required field mismatches, duplicate/nonfinite/type errors, decimal precision,
all 12 diagnostic stages, masked/name/attestation paths, absent optional fields, int/Decimal equivalence, seeded credential fuzz/exception context, redirects, oversize/non-JSON bodies,
exclusive/symlink outputs, CA arguments, deadlines, native proposal grammar,
scope/expiry/root/budget/drift checks and conservative timing arithmetic.
