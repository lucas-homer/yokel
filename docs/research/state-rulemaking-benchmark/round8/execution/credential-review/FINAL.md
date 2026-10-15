# Final generated Round8 credential integration review

Result: **PASS for primary's side-by-side v3 build of the reviewed policy**.
Reviewed 2026-10-09. No material integration issue was found in these generated
artifacts. This approves the concrete build input, not a claim of v3 Keychain access
or a substitute for the primary's live execution authorization and validation.

| Artifact | Verified SHA-256 |
| --- | --- |
| `service-account/policy-v3.json` | `1ace300890f8acacd80b78133f4e1bc8beaa616fdfbbff658f8ae61ddfe621bf` |
| `service-account/binding.json` | `187ca540cdb4979e7497333aa350073d5acde0cf253640efd62a7f3cbd12e859` |
| `service-account/dependencies.json` | `ed81829129d185e10ef2bae7df8d35f8e36d04df891ffd1842441e75f917397a` |
| `service-account/native-job.json` | `84a2ae221b9f7164549e3a7de85553aba7d9b013daf56f5a4e253fa32d0403d1` |
| `runtime/implementation.json` | `01a58ae40467c522ad335938531e5885e411377d2af572e59145a8fd8484fbda` |
| `sources/source-inputs.READY.json` | `f3f77a3a9bb42bbb854e5a4e4a1608cdafcc303e28d75d3b61c2953397cb6367` |
| `execution/live-authorization.json` | `41458d93a85435d543b7cfdef2c84d3ed74cd82843fad8c2631009fd080086be` |
| `execution/freeze-A.json` | `68ec942ed6be59a4a455fab4543bfb25609ea2969dfcedf90375ae11123956f7` |
| `execution/freeze-S.json` | `11714af529a247e31079f82cb30870d7f07c682ad9d4df906a7d030b8909d94f` |
| `execution/freeze-B.json` | `60b1e0f8c6321cee6407cfa04ad02af92a7546b059dd5235868746115cc5b792` |

All paths above are relative to round8, except `service-account`, which is under
`execution`. Every bound hash matched the current file. Freeze A/S/B contained
69/927/9 entries; every entry passed relative-path confinement, duplicate-path,
size and hash checks and was covered by the generated dependencies. Source and
label files were processed as opaque bytes for hashing only; truth was not decoded.

The dependencies map contains 2590 files. The native job map is exactly that map
plus the separately verified binding and dependencies JSON files: **2592 pins**.
All native pin paths are absolute, canonical existing files with matching SHA-256.
All 1599 currently enumerated interpreter/stdlib/package files from the generator's
declared closure were present. There are 924 source-tree pins, confined to the
canonical round8 source tree through freeze validation. Implementation and canonical
manifest were hash-checked without interpreting their contents.

The authorization object exactly binds this implementation, canonical manifest,
and B freeze, with labels frozen before outputs and a $2 nominal budget. The argv
is exactly the fixed bundled `python3.12 -I -S -B`, canonical round8 adapter,
`--live-initial`; timeout is 1800 seconds. No run or live intent existed at review.

The installed v2 policy hash matched its prior receipt. V3 has the same top-level
schema and identical service-account ID, vault ID, op path/digest and reference map.
Its only job is `round8-initial`, exactly equal to the generated native job; the old
round6 job is absent. No new vault/account/credential setup is needed.

Dependency scope is consistent with [the earlier review](REVIEW.md): the concrete
isolated in-memory pypdf check found no missing loaded package file, and native
library inspection found no missing bundled dependency. Shared SITE directory
additions, same-user races, OS libraries and network trust remain existing limits;
no executable amendment or additional closure pin is indicated by this review.
Primary separately reported adapter `--check` passing for 5 documents / 17 pages,
no source errors, and zero credential/provider accesses. This final review did not
rerun that adapter or inspect research input contents.

The changed embedded policy means a new ad-hoc code identity. V2 trust cannot be
assumed for v3. If required, the one-time user action remains the exact reviewed
v3 binary's `rotate-local` in a real Mini terminal, with the existing service token
entered at the hidden prompt and only that binary authorized. It replaces the item
ACL; identity and smoke must pass with runtime interaction disabled before the job.
No remote token/provider-key rotation is implied. Nonatomic local replacement,
logged-in/unlocked-Keychain availability and no automatic retries remain unchanged.

Validation: read-only JSON/schema/map comparisons and SHA-256 checks. Changed only
this new report. No frozen files, credentials, Keychain, op/provider calls, builds,
configuration writes, or reference/model-output inspection.
