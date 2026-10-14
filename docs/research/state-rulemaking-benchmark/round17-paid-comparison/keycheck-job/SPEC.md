# R17 metadata-only native signed job

This is an offline implementation candidate. It does not establish the installed
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
exception outside the original handler. No original exception context is chained.
The CLI emits a fixed status string. Plain credential echoes anywhere in the
response fail; escaped echoes in allowed fields/names also fail. No response
headers or raw body are written.

## KEY-MACHINE.json

JSON parsing uses Decimal for both integer and fractional tokens and rejects
duplicate names/nonfinite constants. The top-level object must contain object
`data`. Only these response fields appear under `fields`: `label`, `limit`,
`limit_remaining`, `limit_reset`, `usage`, numeric/null `usage_*` names matching
`usage_[a-z0-9_]+`, and boolean `is_free_tier` when present. Unknown response
fields are dropped. Numeric values remain exact JSON numbers, never floats;
booleans/strings cannot masquerade as money. Nested usage values fail closed.

`checks` compares the five required fields to label DocketClock, limit USD 50.00,
remaining USD 50.00, reset null and usage 0. Well-formed mismatches write a
sanitized FAIL receipt and exit nonzero. Malformed/transport responses write no
KEY-MACHINE receipt. Additional usage fields are recorded, not used to override
the required total-usage test. The record includes endpoint, raw-response SHA256,
request/retrieval UTC and wall timestamps, CA SHA256, currency and
`accepted_by_primary=false`. Field/unit documentation confirmation is explicitly
false until the primary verifies it. Money 50.00 USD equals 50,000,000,000 nanoUSD;
no live field-documentation lookup occurred in this task.

Receipts are created exclusively mode0600 with O_NOFOLLOW and fsynced along with
the parent directory. Existing files or symlinks stop before transport. A partial
attempt is evidence, never authorization to overwrite or rerun the same job ID.

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
as `BOOTSTRAP-TIMING.json`. Primary acceptance remains false. This task has no
live measurement, fabricated margin, provider billing verification or signed job.

## Offline validation

Tests use synthetic keys and a fake socket installed at the real http.client
connection seam. Unexpected real socket construction raises immediately. No
runner, executor, release or check-job is invoked. Temporary files remain under
this directory and are deleted. Static AST checks and actual HTTP wire capture
assert a single fixed GET and the absence of paid-operation paths. Tests cover
required field mismatches, duplicate/nonfinite/type errors, decimal precision,
credential echoes/exception context, redirects, oversize/non-JSON bodies,
exclusive/symlink outputs, CA arguments, deadlines, native proposal grammar,
scope/expiry/root/budget/drift checks and conservative timing arithmetic.
