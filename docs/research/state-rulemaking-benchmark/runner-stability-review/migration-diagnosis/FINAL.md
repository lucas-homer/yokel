# Credential repair closed: current-session continuity verified

2026-10-11. **PASS in the current logged-in Mini session.** The owner completed the
independently reviewed, exact-item Apple CLI partition repair without reporting an
error. Primary then verified unchanged reader bytes, corrected partition metadata,
service-account identity and two different signed credential-smoke jobs. No further
credential/Keychain commands or source edits were performed by this closing update.

Evidence read:

- `post-repair-metadata.json`: fixed-item lookup/access/ACL statuses0, Keychain bits7,
  17 ACL entries. The partition entry now contains only
  `cdhash:e51b17a7a822e62cc4a0ad89c9de7a2602975a6c`; the matching reader decrypt entry
  still validates with status0. Metadata query requested no password data and made
  no item mutation. Primary compared recorded entries against baseline: unchanged
  except the intended partition. Full opaque ACL bytes were not compared.
- `../deployment/continuity-result.json`: state passed, identity
  `Service-account identity OK.`, reader SHA-256
  `821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e`.
  Both `job-alpha` and `job-beta` passed through this unchanged reader: OpenRouter
  present/nonempty, service-account token absent, TypeSafe key absent, network/provider
  calls false. No desktop-auth fallback. Receipts contain booleans, not key values.

This demonstrates actual native credential access and injection across **two signed
job definitions without rebuilding the trusted executor or another per-job trust step**
in this session. The earlier synthetic suite alone did not establish this; these live
bounded credential-smoke results do. They establish credential delivery, not provider
validity, research correctness or success of the separately running stronger experiment.

Limits remain: logged-in session and available unlocked login Keychain; screen lock,
logout/reboot and locked-Keychain behavior are not newly validated. No current desktop
lock state is inferred. Old decrypt entries were preserved under the narrowly reviewed
partition change; this repair is not a pruning of historical ACLs. Primary-delegated
signing authority, same-user signing-file/process exposure and reviewed-adapter budget
enforcement remain as documented. Core/software/op/Python/signing-key maintenance can
still require a reviewed trust migration; ordinary signed job releases preserve reader
identity. No arbitrary/future experiment or retry is authorized by this result.

The custom prompt-only native repair remains rejected and unbuilt. The successful
route was the reviewed built-in CLI with a local Keychain-password prompt, not token
reentry, token export, broad partition trust or installed-reader replacement.

Changed only this new diagnosis final report. Existing source, reader, signing files
and credentials were not accessed or changed by this closing step. The earlier
automatic-review rejection of an unrestored interaction setter was resolved using a
pure read-only path probe; no approval blockage remains.
