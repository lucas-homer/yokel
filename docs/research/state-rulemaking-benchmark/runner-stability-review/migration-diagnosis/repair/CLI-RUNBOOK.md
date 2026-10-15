# Exact partition repair using installed security CLI

2026-10-11. Exact user-only repair **approved by primary and independent reviewer**.
No mutation command has been executed here. REJECTED.md supersedes the ineffective
custom repair.m; do not build/run it. Existing stable-v1 bytes stay unchanged.

## Verified preflight

Installed `/usr/bin/security help set-generic-password-partition-list` explicitly says
to omit `-k` for a password prompt and warns that supplying it is insecure. The exact
selectors below were independently checked with fixed native reference-only metadata:
generic-password class, service/account, explicit login-Keychain search list,
matchLimitAll, returnRef true and **returnData false**. Query/statuses were0 and
**exactly one match**; UI was disabled and the prior interaction setting restored.
CLI-PREFLIGHT.json captures the nonsecret result; count-only.m is the auditable probe.

Diagnosis shows the reader's decrypt ACL matches installed stable-v1, while the sole
partition remains old v6. Stable-v1 SHA-256:
`821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e`;
CDHash `e51b17a7a822e62cc4a0ad89c9de7a2602975a6c`.

Primary and independent reviewer report review of Apple's keychain_find.c implementation: local prompted
Keychain password when omitted, explicit matching/search list, copied existing access,
partition-only edit and SetAccessWithPassword. Independent reviewer also verified
one match and unchanged reader hash before approving. [Apple SecurityTool source](https://github.com/apple-oss-distributions/Security/blob/main/SecurityTool/macOS/keychain_find.c)
is the implementation basis; installed help is direct evidence of this host's prompt
option. The current fetched public main source did not expose the function through
web text search, so this task does not claim to have independently verified that
specific source slice. Primary/reviewer confirmation has now satisfied that gate.

## Exact reviewed command for the user

Before presenting it, primary rechecks unchanged installed reader hash/CDHash, the
one-match preflight if state/time has changed, and the intended old partition metadata.
Do not act on count0, count>1, unknown selector state or changed executable identity.
Then the user runs in their normal Mini Terminal:

```sh
/usr/bin/security set-generic-password-partition-list \
  -a docketclock-research-mini \
  -s yokel.docketclock.research.op \
  -S 'cdhash:e51b17a7a822e62cc4a0ad89c9de7a2602975a6c' \
  /Users/home/Library/Keychains/login.keychain-db
```

There is **no `-k`**, password/token argument, environment assignment or secret file.
The owner enters the **login Keychain password** only at the command's local prompt,
not the 1Password service token/account password and not in chat or a shell variable.
This command is a specific metadata mutation, not a generic password-read command.
Do not add `-w`, `-g`, broad apple:/apple-tool:/team: partitions, all-app trust, a missing
keychain argument or omit service/account selectors. Do not run under automation,
transcript capture or a wrapper that records prompt input. It grants only the exact
existing stable reader's cdhash; it does not admit the security tool as a decrypt reader.

The CLI can update all matches; the current one-match preflight makes this selector
bounded to the intended item. A new duplicate/race between check and mutation is not
prevented by a transactional guard. Existing user/session controls and unchanged item
metadata matter; do not claim hostile-user race resistance.

## Required post-checks

Primary first reads back exact-item metadata with password pointers NULL/UI disabled:
partition is only stable-v1 cdhash, current decrypt app still validates, and unrelated
ACL/trusted-app metadata is preserved. No pruning of historical apps is part of this
targeted repair. If command status or readback differs, stop and inspect metadata;
do not assume rollback, retry automatically, recreate the token item or widen trust.

Only then primary runs unchanged stable-v1 identity/smoke and the two approved zero-cost
signed credential jobs. No paid research run is implied by this repair. Actual success
can establish cross-manifest continuity; preflight/count/source review does not.

No custom live helper/private signing key/service token was read or created. Only new
diagnosis documentation and the read-only count probe were written/built. The earlier
unrestored-interaction path probe was rejected by automatic approval review; a pure
read-only default/path alternative succeeded. No approval blockage remains from it.
