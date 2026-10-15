# Final v4 cap-probe credential build review

2026-10-09. **PASS: approved for primary's side-by-side v4 native build using
the exact reviewed policy below. No material credential-integration blocker.**
This supersedes the preparation snapshot findings. It does not establish new binary
Keychain trust or replace primary's runtime/protocol release and live validation.

| Artifact under execution/service-account | Verified SHA-256 |
| --- | --- |
| `policy-v4.json` | `4370219977baa4769c2d2ecc918e9cdf3cb1f2dcbbcb890f56a3e8fa258989b7` |
| `binding.json` | `449f411bd3f38f02c5bfc06e5f4d40fff7cbbf7267d3ff295800966f5d19e1bd` |
| `dependencies.json` | `60e59edaa18335d50809d21265176b1f4b4d0e06a859052a4f331180954c3540` |
| `native-job.json` | `e9903ba2509940e9bc742b01dfb02eb9a28c8a6eddc42522ee3fefc9096d7a58` |

All 1683 native file pins are canonical absolute existing paths with matching hashes.
The job map exactly equals the 1681 dependency pins plus binding/dependencies JSON.
All 1599 interpreter/stdlib/package files enumerated by the reviewed preparer are
included, as are all 29 implementation code entries. The earlier concrete synthetic
pypdf/import/native-library review remains applicable to this same dependency scope;
no new package requirement was found in the service update. OS/network trust, shared
SITE directory additions and same-user races remain documented limits.

V3 comparison used the hash-verified preceding policy
`1ace300890f8acacd80b78133f4e1bc8beaa616fdfbbff658f8ae61ddfe621bf` from
original R8 service-account artifacts; no installed `policy-v3.json` was present
at the previously used config path. Every non-job field and the top-level schema
matches exactly: service account, vault, op path/digest and two credential references.
V4 enables **only `round8-cap-probe-initial`**, exactly equal to native-job JSON.
Its fixed argv is bundled `python3.12 -I -S -B`, the canonical cap-probe adapter,
`--live-initial`; timeout is 1800 seconds. No generic/previous job or override exists.

Binding verification matched:

- Implementation: `396ce57d4912820d63ef55979c5484025972b0825a029ebbd452ee914a336da0`.
- Manifest: `73c2162a8a4e514f47dc0286f1345358c48a6211954d4476b29c450dbe3bebdd`.
- Authorization: `b1d6c7b3f58d0cd5caf5fc5dcf94c5561fa8a52e58645b098a51bf38a03440b9`.
- New A: `bf6d518c65a34258ab6a9e4eddbe5830369198a6d2bb5cd1934930f2b7dce7e4`, 29 entries.
- New S: `b226b5427d84c94be4abf351b2f7cfab0d8e72cf5354d10d5d01c94b4d9b7b7d`, 4 entries.
- Original B: `60b1e0f8c6321cee6407cfa04ad02af92a7546b059dd5235868746115cc5b792`, 9 entries.

Original E has 20 entries and is linked by the immutable prior-debit metadata.
Every A/S/B/E entry passed confinement, duplicate-path, size/hash and native-pin
coverage checks; original B/E entries remain under original R8. Those file bytes
were hashed only, never decoded as label truth or provider results.

The manifest admits one `doc-92211b8c7ba0`, two-page unit. Its two external targets
resolve exactly to original R8's `input.pdf` and `native.txt`, both matching manifest
hashes and native dependency pins. Authorization exactly binds this implementation,
manifest, original B, prior-debit file/hash and $0.100166 debit, shared $2 budget,
three operations, one call per stage and inventory completion allowance 12288.
No probe run or live intent existed at this review. Primary separately reported
adapter check passing; this reviewer did not rerun the adapter or paid runtime.

Native source is unchanged. New embedded policy creates a new ad-hoc identity, so
v3 Keychain trust must not be assumed. After build, primary verifies v4 identity and
smoke with runtime interaction disabled. If the user trust step is necessary, use
only the exact reviewed v4 binary's `rotate-local` in a real Mini terminal with the
existing token at its hidden prompt. Local replacement is not atomic and may replace
older-binary trust. No account/vault recreation or remote/provider-key rotation is
implied. Failed/uncertain probe operations must not be automatically rerun.

Validation was read-only metadata/schema comparisons and SHA-256/size/path checks.
Changed only this new credential-review report; no frozen paths, runtime/configuration
edits, credentials, Keychain/op/provider calls, builds or truth/output interpretation.
