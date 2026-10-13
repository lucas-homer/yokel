# Final v5 contract-probe credential build review

2026-10-11. **PASS for primary's side-by-side v5 build using this exact reviewed
policy. No material credential-integration blocker.** New binary Keychain access
remains to be validated after build; this review does not replace the primary's
runtime/protocol release or authorize additional jobs.

| Artifact in execution/service-account | Verified SHA-256 |
| --- | --- |
| `policy-v5.json` | `288d377cf10c12b52372009a3bc7b5434fd314cc5b801b780ca664a259794aac` |
| `binding.json` | `ae5fa38982e374b8459b2a0d4be33c7e5a1e3708a9d27aa33fc20dda7e005675` |
| `dependencies.json` | `1fe83678b9c440cf1653f90602ca1de683fc6f51a5cbc0a25b3a4da8b6de5d8b` |
| `native-job.json` | `7a4a940ad32d5b164af5093afd2bbcd42534af91921b126d6f12ee34fbb29a94` |

## Concrete checks passed

- All **1706 native pins** are absolute canonical existing files with matching
  SHA-256. The job map exactly equals 1704 dependency pins plus binding/dependencies
  JSON. All 1599 enumerated interpreter/package files and 33 implementation code
  entries are included. No missing concrete dependency was found in this scope;
  earlier synthetic pypdf/native-library evidence remains applicable.
- V4 policy hash matched its reviewed receipt
  `4370219977baa4769c2d2ecc918e9cdf3cb1f2dcbbcb890f56a3e8fa258989b7`.
  All v5 non-job fields and top-level schema match exactly: service-account identity,
  vault, op path/digest and two credential references. The only job is
  `round8-contract-probe-initial`, exactly equal to generated native-job JSON.
- Exact argv is bundled `python3.12 -I -S -B`, the canonical contract-probe adapter,
  `--live-initial`; timeout is 1800 seconds. No caller override, generic/old job,
  retry/resume mode or broader credential scope exists in the policy.
- Binding hashes match implementation
  `2f40f7d167466e0aee8542e3cd3d7eb8280aa0e3e584a496641be670b16f2865`,
  manifest `a6833d2ca2ee499d4a1dd89043f0af4908ef964c023a321dfe357e8306dcf875`,
  authorization `1b650c00de32d1be4068a02ede7801003d29bba2837823b5133852f4b09867bb`,
  dependencies and all bound A/S/B freeze files. A/S/B have 28/3/9 entries.
- Every local A/S and original B entry passes path confinement, duplicate, size,
  hash and native dependency coverage checks. Both earlier E freezes have 20 entries;
  every entry and freeze file is confined to its respective old round, hash/size
  matched and included in native pins. Source/reference and old execution files
  were hashed as opaque bytes, not decoded as truth or provider outputs.
- Every reference in both immutable prior-debit records is canonical, confined to
  its exact old round and hash matched in native pins. Debit metadata retains
  max(reservation, reported cost) for each and sums to $0.261774; the prior-debit
  file is bound in authorization and implementation. No refund/reset is introduced.
  Runtime's independent reviewer owns recomputation from actual provider responses;
  this review did not interpret those responses.
- Authorization exactly fixes contract-probe schema, implementation/manifest/original
  B, shared $2 budget, prior debit/file hash, three operations/one per stage, output
  allowances 12288/4096, input guards 35000/40000/64000/32000, and prompt delta
  `90a6f51531f5e26c9e1530a9b7b6c9feebde3b0742e238303839b8c975bf70b6`.
  The prompt delta itself is hash matched and in native dependency pins.
- The manifest admits exactly `doc-92211b8c7ba0`, two pages, with canonical external
  text/PDF paths resolving to original R8's `native.txt` and `input.pdf`; their
  manifest hashes match native pins. No new run or live intent existed at review.
- Native runner source remains byte-identical to the initial code review:
  `b40d294dd46b44a3ced0313d60425863aa3e9fef7c49922869c5d85232e6bcce`.

Primary separately reported isolated adapter check passing and independent runtime
review passing 27 tests. This reviewer did not rerun either suite. Shared SITE
directory additions, same-user filesystem races, OS libraries/network trust and
logged-in/unlocked-Keychain availability remain the existing documented limitations.

New embedded policy produces a new ad-hoc binary identity. Do not assume v4 ACL trust
applies to v5. After the reviewed side-by-side build, validate identity and smoke with
runtime interaction disabled. If necessary, the user runs only that exact v5 binary's
`rotate-local` in a real Mini terminal with the existing token at its hidden prompt,
authorizing only that binary. Local data/ACL replacement is nonatomic and older-build
trust may be replaced. No new vault/account/provider-key setup or remote rotation is
implied. Failed/uncertain operations must not be automatically rerun.

Validation was read-only schema/map/metadata comparisons and SHA-256/path/size checks.
Changed only this new report. No frozen paths, runtime/configuration edits, credentials,
Keychain/op/provider/network calls, builds, source truth or output interpretation.
