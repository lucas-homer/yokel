# Read-only migration diagnosis: partition mismatch

2026-10-11. **Concrete mismatch found:** the fixed token item's decrypt ACL trusts
installed stable-v1, but its partition-ID ACL still contains only the old v6 cdhash.
This supports a Keychain access gate as the cause; it does not rely on near-zero
tool timing or prove the precise failing Token() OSStatus from the generic error.

One bounded metadata inspection returned:

- Default Keychain/state/item-reference/access/ACL-copy statuses all **0**; state bits7.
- **17 ACL entries**. Entry13 includes decrypt authorization, one trusted app, requirement
  `cdhash H"e51b17a7a822e62cc4a0ad89c9de7a2602975a6c"`; validation against the actual
  installed stable-v1 path returns **0**.
- Entry15 has `ACLAuthorizationPartitionID` with only
  `cdhash:691cd655aae540caf887bff777bd48c9ef192326` — the old v6 identity, **not stable-v1**.
- Historical decrypt ACL entries remain; authorize-existing did not replace the entire
  effective list with a sole new-reader entry as the candidate's intent implied.
  Null application lists observed on encrypt/integrity/partition entries do not imply
  all-app decrypt permission; do not conflate operation types.

Installed binary SHA-256 is
`821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e`;
codesign reports ad-hoc/runtime/restrict/kill and cdhash `e51b17a7a822e62cc4a0ad89c9de7a2602975a6c`.
check-policy passes in this agent context, uid/euid501. Conditional synthetic-auth
marker is absent (supplementary evidence, not a substitute for the production build
receipt). Source hashes match stopped candidate. Primary separately verified op pin,
all deployment pins and unlocked state, and user confirmed exact authorize-existing
success text. Primary observed no op descendant during one bounded identity sample;
absence in a short sample is not proof. This diagnostic did not rerun identity.

## Method and boundaries

`acl-metadata.m` is a separate exact-item diagnostic compiled only in this diagnosis
directory, **not a rebuild of the installed reader**. It disables interaction and
queries only the default Keychain, fixed service/account, with **NULL password length
and data**. It copies item/access/ACL metadata, decodes only allowlisted partition-ID
strings, and prints operation tags, app counts, code requirements and validation statuses.
No token buffer, token prefix/length/value, raw trusted-app data, signer file or generic
secret reader is used. It invokes no setters, unlock command, enrollment, op or provider.

Public APIs perform the metadata lookup/access/ACL copies. Installed SDK lacks public
declarations for optional trusted-app validation/requirement-copy; the helper checks
runtime symbol availability and uses the signatures/behavior verified in
[Apple's Security source](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/SecTrustedApplication.cpp).
Those diagnostic-only optional symbols were available; requirement metadata was printed,
never opaque trusted-app bytes. They are not added to production source.
Apple documents the NULL-password item-reference lookup in
[SecKeychainFindGenericPassword](https://developer.apple.com/documentation/security/seckeychainfindgenericpassword(_:_:_:_:_:_:_:_:))
and operation-specific ACL metadata in
[Access Control Lists](https://developer.apple.com/documentation/security/access-control-lists).

## Recommended next decision, not an action taken

Preserve installed stable-v1's bytes/identity. Further reader rebuilds would create a
different cdhash and obscure this targeted mismatch. Do not broaden to apple:, apple-tool:,
team-wide or allow-all trust, and do not use generic token readers or repaste the token
as a diagnostic. Terminal identity comparison can still clarify context, but both
contexts must satisfy the same remaining partition gate.

Primary should independently review a **specific metadata-only repair** of this exact
item's partition restriction to the existing stable-v1 cdhash, with user-controlled
authorization and readback. Separately decide whether historical decrypt entries should
be removed to restore the intended sole-reader boundary; current SetAccess behavior
must not be assumed to prune them. A repair must preserve token data and avoid adding
the repair helper itself as a decrypt reader. Its precise API/mutation and prompt
behavior require review before any write; none was implemented or executed here.

After a reviewed repair, primary can rerun the exact reader's identity/smoke and the
two zero-cost signed jobs without rebuilding. Success then establishes actual continuity;
current signature/ACL metadata alone does not. If it still fails, capture only per-stage
status metadata under further authorization, rather than guessing token content or
weakening ACLs. Existing generic errors hide the exact failure stage.

Artifacts: RESULT.json contains compact nonsecret evidence; helper source is auditable.
Only new diagnosis artifacts were written. Installed binary, source candidate, Keychain
trust/data, signer files and credentials remain unchanged by this diagnostic.
