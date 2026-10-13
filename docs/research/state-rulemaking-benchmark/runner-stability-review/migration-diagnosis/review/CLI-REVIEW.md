# Built-in partition repair — approved for one owner Terminal invocation

2026-10-11. Supersedes the repair path, not the rejected helper verdict in FINDINGS.md.
Do not build/run repair.m. Its 19 owner fixtures cannot resolve the authorization blocker.

The reviewer independently ran installed help on macOS 15.7.4 (24G517): it explicitly
supports omitting -k for a password prompt. No mutation command was invoked.

Apple implementation review: the exact account/service form searches all matching generic
items in the supplied keychain, prompts when -k is absent, copies existing access, edits
partition descriptions while retaining application lists/prompt selectors, then calls
SecKeychainItemSetAccessWithPassword. It requests no token data through its item-printing
path. It adds no helper/CLI decrypt trust. It does not assert uniqueness, check the old
partition, check the installed reader, or verify readback; SecACLSetSimpleContents's
return is not checked. Password buffers are freed, not demonstrably zeroized. Hence no
zeroization or transactional-success claim is made.
[Apple keychain_find.c](https://github.com/apple-oss-distributions/Security/blob/main/SecurityTool/macOS/keychain_find.c)

The prompt uses getpass. Attribute printing passes NULL data output pointers with
show_data=false; the command prints item metadata, not the token value.
[Apple keychain_utilities.c](https://github.com/apple-oss-distributions/Security/blob/main/SecurityTool/macOS/keychain_utilities.c)
[Apple command help source](https://github.com/apple-oss-distributions/Security/blob/main/SecurityTool/macOS/security.c)

## Independent local preconditions

Reviewed count-only.m requests references only with exact class/account/service, explicit
login keychain, MatchLimitAll, ReturnData=false. It disables and restores interaction.
Independent invocation returned exact_match_count=1, all status fields zero, uid501,
interaction_restored=1, password_data_requested=false, mutation=false.

- count-only.m SHA256: ca8300ee8ff1a21ed626daeb6a846f4fe8b56d5b6764fca05863779bd81f16d1
- count-only binary SHA256: af1314818e95f0d0095a66595eb0e33eb47f8902c1c9b398741eff20d1a3acbf
- Installed stable-v1 SHA256 rechecked: 821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e
- Installed stable-v1 CDHash rechecked: e51b17a7a822e62cc4a0ad89c9de7a2602975a6c
- EVIDENCE.md and metadata-independent.json establish existing stable-v1 decrypt trust,
  sole old-v6 partition, and 17 ACL entries. This is a snapshot, not an atomic race guard.

## Approved exact command

Owner executes directly in their Terminal as home/uid501, with their Keychain password
entered only at the local prompt. No -k, sudo, password environment variable, pipe,
scripted input, token retrieval, or agent terminal interaction.

```sh
/usr/bin/security set-generic-password-partition-list \
  -a 'docketclock-research-mini' \
  -s 'yokel.docketclock.research.op' \
  -S 'cdhash:e51b17a7a822e62cc4a0ad89c9de7a2602975a6c' \
  '/Users/home/Library/Keychains/login.keychain-db'
```

Approval relies on the above current preconditions remaining true. If execution is
delayed or item/reader state changes, refresh metadata/reference count and reader pins.
This replaces the old partition with the sole stable-v1 CDHash; no apple:, apple-tool:,
teamid:, old-reader partition, or additional CDHash is authorized. Existing historical
decrypt ACLs remain; this is not a claim that sole-reader trust has been established.

## Required verification and limits

After the one invocation, inspect metadata even if the command returns an error.
Require exactly the stable-v1 partition, stable-v1 decrypt validation success, preserved
ACL count/tags/app requirements/null-list/prompt metadata, and unchanged reader digest.
On any unexpected delta or failure, stop and inspect; no automatic retry/rollback.
Only primary then runs already-authorized stable identity/smoke/jobs. This reviewer
performs no credential read, provider call, signing-key access, or live ACL mutation.

The existing diagnostic does not expose complete nonpartition descriptions/integrity
payloads or trusted-app path-data hashes. It can verify its recorded metadata fields,
not bit-for-bit preservation of every ACL field. Source inspection supports targeted
preservation; full preservation remains unproven until a complete metadata snapshot
comparison is available. Do not describe a zero exit code as verified repair success.

A custom hidden-password API helper is technically plausible from the reviewed Apple
call chain, but unnecessary while this installed built-in route is available. No custom
password handler was built, approved, or tested. Apple main source is not an assertion
that every implementation detail matches the installed OS binary.
