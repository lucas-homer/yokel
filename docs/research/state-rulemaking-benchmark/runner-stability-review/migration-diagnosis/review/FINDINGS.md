# Partition repair review — release held

## P1 — ordinary SetAccess lacks the credentials needed to replace a protected partition entry

repair.m currently commits the copied partition through SecKeychainItemSetAccess after only enabling UI (around lines117–118). A pure in-memory Plan fixture cannot test whether securityd will accept that write.

Apple source chain:

1. SecKeychainItemSetAccess calls Access::setAccess with prompt credentials and update=true. https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/SecKeychainItem.cpp and https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/Access.cpp
2. SecurityServerAcl::changeAcl preserves CSSM_APPLE_ACL_TAG_PARTITION_ID unless db->checkCredentials(cred) succeeds. https://github.com/apple-oss-distributions/Security/blob/main/securityd/src/acls.cpp
3. KeychainDatabase::checkCredentials explicitly never prompts, ignores prompt samples, and accepts explicit validated database password/key credentials. https://github.com/apple-oss-distributions/Security/blob/main/securityd/src/kcdatabase.cpp
4. ObjectAcl::cssmChangeAcl rejects REPLACE when the existing entry has that preserved tag, even after owner validation. https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_cdsa_utilities/lib/objectacl.cpp

Therefore a successful owner authorization dialog alone does not establish that this helper can replace the partition. No live mutation was attempted to reproduce this; the blocker is established by the implementation path, subject to confirming the matching OS source behavior. Do not ask the user to run the current helper merely to discover another expected denial.

Bounded remedy: establish a supported authorization mechanism that supplies the required database credential while preserving the exact item, exact stable-v1 partition, existing metadata-only item lookup and unchanged reader bytes. Apple's adjacent SecKeychainItemSetAccessWithPassword implementation is evidence that explicit database credentials are a separate mechanism; using it would entail carefully scoped human Keychain-password handling, which this metadata-only candidate currently does not implement or authorize. Primary must resolve that design/authorization boundary before release. Do not work around it with broad partitions, generic credential extraction or changing the installed reader.

## Readback ordering/integrity question

The reviewed Apple path does not show an automatic integrity-ACL rewrite for this single partition update. ItemImpl's integrity digest is based on item attributes; SecKeychainItemSetAccess directly applies ACL updates, rather than modifying item attributes/data. ACL::setAccess modifies the existing handle; ObjectAcl replaces it while preserving the handle. These support retaining strict checks, although the source is not proof of this machine's exact post-write ordering. https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/Item.cpp and https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/ACL.cpp

A harmless order/serialization change could produce a conservative false failure. If observed, preserve every ACL's authorization tags, application identities, null-vs-empty list, prompt selector and description, including integrity metadata, while comparing the non-partition entries as a multiset. Do not simply ignore integrity or entire ACL classes. The helper already reports commit/readback failure and prohibits automatic retry/rollback; keep that distinction.

## Other reviewed boundaries

The current source fixes uid501, default Keychain path, service/account, reader path/SHA256/cdhash and expected old/new partition values. It checks the installed reader before planning, before commit and after readback, requires existing decrypt trust and rejects an all-app decrypt entry. Plan rejects missing/multiple partition entries, mixed authorization tags, unknown plist keys, malformed hex, broad/extra partition values, and supports an idempotent already-correct state. The copied partition's app list, prompt selector and unrelated ACL metadata are preserved. No helper identity is inserted by its plan; no token-data API is requested. Actual OS commit behavior remains untested.

SecKeychainFindGenericPassword returns the first matching item. The helper does not explicitly enumerate/reject duplicate matching item references. The observed item matches its exact partition/decrypt preconditions, but uniqueness is not independently established by this source. A bounded metadata-only enumeration that refuses more than one match would strengthen the exact-item precondition if duplicates are possible in the target legacy Keychain.
