# Round8 credential integration review

Reviewed 2026-10-09. Scope: inspection of service-account adapter, manifest
preparation, runbook, runtime import/dependency boundary, native runner/build source,
and installed v2 nonsecret policy/binary metadata, plus an isolated synthetic
in-memory pypdf import/write/read and static native library dependency inspection.
No source documents, reference
labels, model outputs, credentials, Keychain, op commands, builds, or provider calls.

The fixed native integration is suitable for final binding review after A/S/B
freezes. This is not a validation of a generated v3 policy or live availability:
those artifacts and checks remain primary-owned.

## Concrete dependency closure evidence

`prepare_manifest.py` enumerates existing stdlib/extensions, top-level bundled
dylibs, pypdf, cryptography, PIL (including its `.dylibs`), cffi, `_cffi_backend`,
and pypdf distribution metadata. Implementation code keys include lineage and
protocol reuse dependencies; frozen inputs and authorization are separately bound.
The resulting job also pins binding/dependencies themselves. These are substantial
file pins. A clean environment invocation of the fixed bundled Python with
`-I -S -B`, adding the same SITE root, imported pypdf, created one blank page in
memory with PdfWriter, and read it with PdfReader. Among 170 loaded file-backed
modules (78 in site-packages), **none was absent from the generator's stdlib/package
enumeration**. Loaded package extensions were PIL `_imaging`, `_cffi_backend`, and
cryptography `_rust.abi3.so`; all are covered. `_ssl` is built into this interpreter,
not a separate unpinned lib-dynload extension.

`otool -L`/`-D` inspection of those extensions, every PIL `.dylibs` library, bundled
top-level dylibs, and the Python executable covered 25 native files and 73 load
dependency edges after excluding install IDs. There were **no missing/unpinned
non-OS targets and no unresolved rpath loads**. PIL loader-relative dylibs are
within the recursively pinned PIL tree. Cffi and cryptography's remaining direct
dependencies are OS libraries, already documented outside the pin boundary.

No concrete transitive package/shared-library addition is indicated by this check.
It covers the synthetic pypdf path, not every later protocol/runtime branch. Primary
can add any actual missing file found in its final offline adapter/import verification
to generated dependencies/job/binding manifests before building, without changing
frozen executable code. No whole-site hashing or executable amendment is requested.

`adapter.py:runtime_module` prepends the entire `site-packages` directory to
`sys.path`. Neither adapter verification nor native file checks rejects additional
files in that directory. An added module can shadow an otherwise pinned stdlib
module; optional imports can also find unenumerated packages. For example, cffi
contains a lazy pycparser import, whose installed package is not enumerated, and
pypdf has an optional Crypto fallback. Static inspection does not demonstrate that
either path is executed by this Python 3.12 run; typing_extensions imports examined
are guarded for older Python versions. Do not characterize this as a proven current
missing import or as complete dependency closure.

This is the existing trusted shared-runtime limitation, **not an evidenced missing
dependency or a new build blocker**. Exact installed-file pins do not prohibit directory
additions or same-user filesystem races. Retain that qualification instead of claiming
a hostile-user closed import namespace. Final generated native-job pins must be
reviewed after freezes; this review did not run the generator or adapter and did not
modify frozen code. No missing package was inferred solely from the shared SITE path.

## Boundaries confirmed by source inspection

- Native argv is fixed to bundled Python, `-I -S -B`, this adapter and
  `--live-initial`; no shell/caller argument override. Isolation excludes site
  startup hooks and user Python configuration. The adapter checks those flags and
  the resolved executable.
- Native checks job and op pins before Keychain access and repeats job checks
  before exec. It validates service-account identity, passes only the reviewed
  provider keys to the job, and drops the service token. Output is suppressed;
  the approved job must enforce its own artifact secret boundary.
- Binding validates implementation, manifest, authorization and A/S/B freeze
  hashes. Freeze entries are hash-checked, not interpreted as reference truth.
  Live mode refuses an existing run or intent and writes intent before paid work.
  Failure does not automatically restart the initial-only job.
- The generator emits a fixed 1800-second job, matching v2's timeout. The native
  runner imposes process-group termination; an interrupted initial job still needs
  review of durable nonsecret operation receipts, not a blind retry.

## V2 evidence and exact potential v3 trust step

Read-only metadata checks matched prior recorded v2 hashes:

- Binary `/Users/home/.local/libexec/yokel/research-credentials-v2`:
  `749044650cfe1b63be7f7dcd32eda995de874a6f5e120df0db91396e981e5bf9`.
- Policy `/Users/home/.config/yokel/research-credentials/policy-v2.json`:
  `b44b338970e22150a55ea6b02010a7c179a60b4ec03714e9c50f163cc07cc864`.
- V2 enables only `round6-initial`, isolated Python, 2465 file pins, and the two
  existing research-vault reference variables. No new vault/account/key setup is
  necessary for this proposed job.

The new embedded policy changes the ad-hoc binary identity. Do not assume the v2
Keychain ACL trusts v3. After primary reviews and builds the new side-by-side binary,
the potential one-time human step is to run that exact reviewed v3 binary's
`rotate-local` in a real Mini terminal with the default Keychain unlocked, entering
the existing service token directly at its hidden prompt. If Keychain asks to permit
the old item lookup, authorize only that exact v3 binary (Allow Once is sufficient
for the lookup; the runner then replaces the ACL). Never authorize a generic reader
or all applications. No provider-key entry or remote token rotation is required.

`rotate-local` modifies item data and then calls `SecKeychainItemSetAccess` to trust
only the current binary; v2 trust should not be assumed to survive successful ACL
replacement. These operations are not atomic, so a failure must not be treated as
rollback. Primary should verify v3 identity and smoke with runtime interaction
disabled before starting `round8-initial`. The live v2 result does not establish
v3 access, current desktop-lock state, logout/reboot availability, or unattended
Keychain unlock. This review performed no enrollment or trust change.

Changed artifact: this report only. No frozen files were edited. Remaining decision:
primary must review final generated pins/bindings and validate the new binary's
access. The shared import-directory qualification remains the existing trust limit;
the concrete synthetic check found no required closure additions.
