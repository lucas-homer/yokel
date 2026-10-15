# Final v6 evidence-table credential build review

2026-10-11. **PASS for primary's side-by-side v6 build with this exact policy.
No material credential-integration blocker.** This does not establish v6 Keychain
access or substitute for primary runtime/protocol release and live validation.

| Artifact under execution/service-account | Verified SHA-256 |
| --- | --- |
| `policy-v6.json` | `bdc7f69e660c2192ee8efd5a34fd4dac91903df3be1217566f4f58ec9a7ad7e2` |
| `binding.json` | `e6db7c8ec1ce52068a0cd29bd2d56571a31d3d4f32f5be2125db013c0d6f9d13` |
| `dependencies.json` | `2edb559c83023e129129ce879f05330617939a2303859863e22fa3f2acfe0932` |
| `native-job.json` | `019b83531df5f288ec829a7ff3ef98fee5e9bb67516cd618ee3627d84ef8d299` |

## Concrete review passed

- All **1745 native pins** are canonical absolute existing paths with matching
  SHA-256. The map exactly equals 1743 dependencies plus binding/dependencies JSON.
  All 1599 enumerated interpreter/package files, 42 implementation code entries
  and 25 lineage entries are included and hash matched. No concrete missing package
  or unrecognized external root was found. Two round5 metadata files
  (`runtime/API-CONTRACT-CHECK.json`, `runtime/INTEGRATION.md`) are explicitly in
  implementation/lineage and allowed by runtime lineage validation, with exact pins;
  other external roots are the reviewed prior rounds and bundled Python runtime.
- Prior v5 policy matches its reviewed hash
  `288d377cf10c12b52372009a3bc7b5434fd314cc5b801b780ca664a259794aac`.
  V6 schema and every non-job field match exactly: service-account identity, vault,
  op path/digest and credential reference map. Only `round8-evidence-table-initial`
  is enabled, exactly equal to the generated job. No extraction/old/generic job exists.
- Exact argv is bundled `python3.12 -I -S -B`, canonical evidence-table adapter,
  `--live-initial`; timeout is 1800 seconds. No caller overrides, alternate mode,
  broader credential scope or automatic retry is introduced.
- Binding matches implementation
  `bdd134986131062751b6e62dea176cb18e89b9c9bfc5344005e3997ce0c2f9a4`,
  manifest `635bfe33577746d8452e1365bf92fca20e2d79e26467e5f4aa1ded530c7db4b8`,
  authorization `6144c250e63490cb41f74e6a9e8c7516d54e1b6e951fb7f45e431c08537af1bf`,
  dependencies and every bound A/S/B freeze hash. A/S/B have 35/4/9 entries.
- Every local A/S and original B entry passes confinement, duplicate-path, size/hash
  and native-pin coverage checks. All three old E freezes and targets are included:
  original R8 20 entries, cap-probe 20, contract-probe 25. Entries remain confined
  to their respective immutable roots. Old results and labels were hashed as opaque
  bytes only, not interpreted here as provider responses or reference truth.
- All three prior-debit records' file references are canonical, confined to exact
  prior roots and native hash matched. Metadata retains each max(reservation,
  reported cost) and sums to $0.428936; debit JSON is bound in authorization/code.
  Runtime reviewer owns response-level debit recomputation; no reset/refund is implied.
- All **five retained inputs** resolve under the original contract-probe WI document
  directory, match input-pin hashes and native dependencies. Manifest retained_inputs
  exactly equal input-pin files. Original text/PDF resolve to original R8 WI
  `native.txt`/`input.pdf`, with matching native/manifest hashes. The single source
  identity is `doc-92211b8c7ba0`, two pages.
- Authorization exactly fixes two new operations, **zero inventory**, one Jev and
  one stronger call, shared $2 budget and $0.428936 prior debit, original B, explicit
  wire version, input/debit/instruction hashes and original payload/record identity.
  Guards remain stronger 40000/output4096, Jev total64000/state-plus-longest32000.
  Codec, decoding instructions and input-pin are explicitly hash matched in native
  pins. No run or live intent existed at review.
- Native runner source remains byte-identical to the earlier reviewed boundary:
  `b40d294dd46b44a3ced0313d60425863aa3e9fef7c49922869c5d85232e6bcce`.

Primary separately reported adapter check passing and independent runtime approval
with 31 checks. This reviewer did not rerun those checks or decode retained inputs.
Earlier concrete synthetic dependency evidence remains applicable; shared SITE
directory additions, same-user races, OS/network trust and logged-in/unlocked-Keychain
availability remain the documented limitations.

New embedded policy creates a new ad-hoc identity; v5 ACL trust is not assumed for v6.
After the reviewed build, validate identity/smoke with runtime interaction disabled.
If a user trust step is needed, run only that exact v6 binary's `rotate-local` in a
real Mini terminal with the existing token at its hidden prompt, authorizing only
that binary. Local data/ACL replacement is nonatomic and older trust may be replaced.
No new vault/account/provider-key setup or remote rotation is implied. Failed or
uncertain operations must not be automatically restarted.

Validation was read-only schemas/maps/nonsecret metadata, path/size/SHA-256 checks
and native-source comparison. Changed only this new report. No frozen/runtime/config
edits, builds, keys, Keychain/op/network/provider calls or source/truth/result decoding.
