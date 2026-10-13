# REJECTED / SUPERSEDED: custom partition repair candidate

**Do not build or run repair.m.** Independent backend review found that its prompt-only
SetAccess path cannot authorize a partition change. Pure fixture tests do not establish
database permission. REJECTED.md supersedes the candidate discussion below. Use the
separately reviewed CLI-RUNBOOK.md instead; no live command has been executed here.

The remainder is retained as historical design/test evidence, not an actionable runbook.

2026-10-11. **Prepared only; no live mutation or production helper build.** Primary
will obtain independent review before building/presenting a user command. Stable-v1
reader bytes and signing key/token custody remain unchanged.

## Fixed target and intended delta

- User UID/eUID501, explicit default Keychain path
  `/Users/home/Library/Keychains/login.keychain-db`, already observed by read-only
  default-reference/path metadata. No search-list or arbitrary-keychain selector.
- Generic-password service `yokel.docketclock.research.op`, account
  `docketclock-research-mini`; length/data pointers both NULL, itemRef only.
- Installed reader `/Users/home/.local/libexec/yokel/research-credentials-stable-v1`;
  SHA-256 `821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e`;
  validated signature/CDHash `e51b17a7a822e62cc4a0ad89c9de7a2602975a6c`.
- Change exactly the singleton stale partition
  `cdhash:691cd655aae540caf887bff777bd48c9ef192326`
  to singleton `cdhash:e51b17a7a822e62cc4a0ad89c9de7a2602975a6c`.

Helper refuses wrong reader path/hash/CDHash, wrong current default Keychain, locked
Keychain, wrong UID, absent matching decrypt trust, missing/duplicate/combined partition
ACL, malformed/unknown plist, additional partitions or broadened apple:/team: entries.
Already-correct singleton partition is an idempotent no-op. No argument overrides exist.

The existing access instance is copied. Only its partition ACL's description is edited;
original application list, null-list representation, authorization tags and prompt flags
are passed through unchanged. No new trusted application/access instance is created,
no old trusted application is pruned and no repair-helper decrypt permission is added.
Historical decrypt entries remain intentionally untouched under this narrow scope.
All other ACL descriptions/metadata are preserved; target partition retains original
XML/binary plist format. Snapshots check exact in-memory delta before commit and exact
metadata readback after commit, with installed-reader verification repeated.

No password buffer, Token(), data-modify/export API, op or signer-file access exists.
The only item write is `SecKeychainItemSetAccess(item, copiedAccess)` after changing
one existing ACL. [Apple's SecACL implementation](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/SecACL.cpp)
marks the edited object modified; [Access update implementation](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/Access.cpp)
skips unchanged entries when update is true, as used by
[SecKeychainItemSetAccess](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/SecKeychainItem.cpp).
This supports the targeted copied-object approach, unlike fresh SecAccessCreate that
added a new decrypt entry without changing the old partition.

## Explicit user invocation and remaining uncertainty

Primary builds only after independent review with installed Apple clang/Foundation/
Security and a new helper output path. It **must not replace or re-sign stable-v1**.
The helper is a separate, one-time metadata repair tool, not another credential reader.
After source/binary digest verification and user approval, primary presents:

```sh
/ABSOLUTE/REVIEWED/repair-helper --repair-known-partition
```

The single mode requires stdin/stdout and `/dev/tty` to be real terminals. No automatic
invocation, hidden fallback, password argument or stdin password reader exists. The
helper performs preflight with Keychain interaction disabled; it enables interaction
only around the explicit ACL commit and always restores the previous process setting.
macOS may request authorization/Keychain password through its own UI. The owner should
authorize only the specific reviewed metadata operation, never allow all apps or broad
Apple/team partitions. No service token needs to be retrieved/pasted.

Apple's [NULL-password lookup contract](https://developer.apple.com/documentation/security/seckeychainfindgenericpassword(_:_:_:_:_:_:_:_:))
supports requesting the item object without password bytes.
[SetAccess documentation](https://developer.apple.com/documentation/security/seckeychainitemsetaccess(_:_:))
supports ACL attachment; Apple's source uses prompt credentials rather than requiring
password-in-argv. Actual permissions/prompts and successful persistence are **untested**.
If macOS cannot complete this targeted mutation, stop; do not broaden access or read
the token as a workaround.

Validation of existing trusted refs reuses diagnostic-only optional functions checked
at runtime, with signatures verified in [Apple's trusted-application source](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/SecTrustedApplication.cpp).
These SPI declarations are absent from the installed public SDK headers. The helper
refuses if unavailable; reviewer must explicitly assess this one-time compatibility
dependency. No opaque trusted-app bytes are logged (only metadata snapshots in memory).

OSStatus failure during commit can leave a partial change. `commit completed=no` means
the API did not return success, **not a guarantee that nothing changed**. Readback mismatch
after success is also a stop requiring fresh metadata inspection. There is no automatic
rollback/retry, deletion, recreation or old-reader trust change. A security daemon may
maintain ancillary integrity metadata; if readback differs, the helper reports failure
rather than claiming other ACLs were preserved. Synthetic fixtures do not establish
actual Keychain transactional/GUI behavior or hostile same-user race resistance.

After user-run success, primary independently verifies the exact partition via the
read-only diagnostic, then stable-v1 identity/smoke and the two zero-cost signed jobs.
The repair itself does not run identity or any job. Successful actual checks can prove
continuity without changing the trusted reader's identity.

## Synthetic evidence

test.py compiled/executed **only SYNTHETIC_FIXTURES**: live Keychain code is excluded.
19 native checks passed: exact sole description delta, unrelated ACLs/apps/flags/tags,
already-correct no-op, malformed hex, broad/extra/unknown partitions, missing/duplicate/
combined partition authorization, wrong target path/hash/CDHash, detecting an unrelated
app change and binary plist preservation. Synthetic binary rejects the live mode.
Production branch passed clang `-fsyntax-only`; no production executable was emitted.
Installed stable-v1 hash still matches. TEST-RESULT.json records source and evidence.

Source SHA-256: `7b504cfaa75f54b10f1703cc47b35cdd9002bbe91a35229f0a20bdd5475a01a2`.
Changed only new files here. No installed reader/source/key/trust changes or provider
calls. An earlier default-path probe was rejected by automatic review for an unrestored
interaction setter; the corrected probe used only read-only default/path APIs and
succeeded without changing interaction state. No action remains blocked from that probe.
