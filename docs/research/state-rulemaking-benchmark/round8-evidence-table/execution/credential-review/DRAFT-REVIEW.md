# Evidence-table service boundary: draft review

2026-10-11. Owner is still testing; these are concrete pending draft corrections,
not a verdict on final implementation. **Final v6 build approval is pending.**
Scope: execution/SCOPE.md, current service adapter/preparer, runtime authorization
and retained-input interface, nonsecret lineage/input/debit metadata. No keys,
Keychain, builds, network/provider calls, retained-result contents or labels were
read. Changed only this new credential-review report.

## Current draft integration gaps

1. The adapter uses the new namespace but still expects the previous authorization
   fields: $0.261774 prior debit, three operations, inventory allowances and old
   prompt delta. Check/live invocations and receipts also retain three operations.
   The released scope and current runtime auth_scope instead fix $0.428936, two
   operations, zero inventory, one Jev and one stronger call. They bind explicit
   wire version, decoding-instruction hash, input-pin hash, original payload/record
   hashes and retained verifier guards. Adapter expected auth and all calls/receipts
   must match that exact scope before freeze/build.
2. The preparer explicitly includes original B and only original R8/cap-probe E.
   The third debit's contract-probe E and its four operation evidence files are
   absent from lineage, and the script does not otherwise add them. Pin the third
   E with confined hash/size-verified targets as well. It currently resolves only
   text/PDF manifest paths; retained_inputs references also need native pins.
   Including the whole third E should cover the frozen retained input files, but
   final review must confirm each input-pin `files[*].path/sha256` is actually in
   generated dependencies, rather than assuming transitive coverage from pin JSON.

Snapshot hashes after the current read:

- Adapter: `d6f335a04fc2e35e54daf0b783060080f85fcbaf26fcb5801eefb6453525a7ec`.
- Preparer: `681f66311d2d35d9f45a82f7f21ba26aaa796a639f13f392e5b0af18c0ae4797`.

## Boundaries already present

Fixed check/live-initial modes, exact isolated bundled Python `-I -S -B`, canonical
new-root paths, hash verification before environment key access, no existing run or
intent, absent service token in actual payload, only two injected provider keys,
suppressed live output, generic errors, exclusive durable receipts and no automatic
retry remain intact. Original B is hash-checked opaquely under its original root;
labels are not a provider request input in the reviewed interface. Native source
remains the existing reviewed credential architecture.

## Final concrete review gates

Review generated A/S/B and all three E hashes/entry confinement/size/native coverage;
every original source/retained source, assembled record, common payload and old
verifier request in input-pin; all implementation/lineage code, codec and instruction
files; original payload/record identity and exact narrow authorization. No extraction
job may be enabled. Runtime/semantic reviewer owns request transformation, restoration,
all-ID judgment/evidence interpretation and paired-dispatch semantics.

The native job must use only fixed bundled Python `-I -S -B`, this adapter and
`--live-initial`, reviewed timeout, with native pins exactly dependencies plus
binding/dependencies JSON. Revalidate the established interpreter/package closure;
no new service dependency is implied by the table codec. V6 must inherit unchanged
account/vault/op/reference metadata from the hash-verified v5 policy and replace
jobs with only the approved evidence-table initial job. Record current policy and
binding/job hashes before primary builds side by side.

V6 embedded policy creates a new ad-hoc identity. Prior v5 Keychain trust is not
assumed. Primary prepares the concrete reviewed binary before any necessary real-TTY
`rotate-local` using the existing token and permission only for that binary, then
validates identity/smoke with runtime interaction disabled. Local replacement remains
nonatomic; no account/vault/provider-key recreation or remote rotation is implied.
