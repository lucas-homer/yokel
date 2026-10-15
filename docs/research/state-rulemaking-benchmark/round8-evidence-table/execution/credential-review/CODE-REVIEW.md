# Updated evidence-table service code review

2026-10-11. **Both draft findings are resolved; no current material service-boundary
code issue found.** Supersedes DRAFT-REVIEW.md's snapshot findings. Final v6 generated
artifact/build approval remains pending primary freeze/binding/policy preparation.

Reviewed current hashes:

- Adapter: `530686d7f2baa3ab7eca342809f1862131164af764a12e69fde639332043e71c`.
- Preparer: `ab01d5e8c7aebe9f2dfa2871c423133f57a3eb8d995b9d2b08479358c9ce1250`.

The adapter now matches runtime auth_scope and INTERFACE: $0.428936 prior debit;
two new operations; zero inventory, one Jev and one stronger; unchanged 40000/4096
stronger and 64000/32000 Jev guards; explicit wire version, decoding-instruction,
input-pin, original payload/record and prior-debit hashes. Every check/live call and
receipt now records two operations and the correct debit. Fixed isolated Python,
single initial mode, no existing run/intent, no service token in actual payload,
only approved provider keys, suppressed live output and no automatic retry remain.

Input-pin hash is `fcb29ae1f4cbd3ba37fed26b5fcf1d550070e96580846d2f98d79396ba2aa71f`;
instruction hash is `93f5c0f00bf794a61a6f224f17a95120f296c646c54a0cd4f2c0fbbb22b9b3df`.
Both match the new interface. Original B remains opaque under original R8; local
A/S remain separate. No independent labels are read as provider inputs by this
service boundary; runtime/request semantics remain the independent reviewer's scope.

The preparer now enumerates **all three prior E freezes** with confined path/hash/size
checks, plus every manifest retained_inputs target as an explicit native dependency.
Metadata comparisons confirm each of the three prior-debit records is covered by
its corresponding E closure, and all five retained input targets are covered by
original contract-probe E. It also includes exact external source text/PDF, final
implementation/lineage/code, codec/instructions/input-pin via the implementation
map, and the established interpreter/package closure. This verifies enumeration and
membership, not final generated file hashes; the latter remain a final review gate.

Native runner source remains byte-identical:
`b40d294dd46b44a3ced0313d60425863aa3e9fef7c49922869c5d85232e6bcce`.
Prior source/debit/retained artifacts were not decoded here; only reference metadata
and code were inspected. No new service import implies a missing package.

Final review must check all generated native hashes, exact dependencies-plus-binding
map, three E closures and five retained targets, original source paths, precise auth,
fixed argv/timeout, and unchanged v5 account/vault/op/reference metadata with only the
approved verifier-only initial job in v6. New ad-hoc identity still needs post-build
identity/smoke validation and, if necessary, the exact binary's user-controlled hidden
TTY trust step. No new credential/account setup is implied.

Validation: static source inspection, Python syntax parsing without module execution,
metadata closure comparisons and source hashes. Changed only this new report. No
runtime/old-round edits, keys, builds, Keychain/op/network/provider calls or truth/result
interpretation. Owner's offline runtime tests remain separately owned and unclaimed here.
