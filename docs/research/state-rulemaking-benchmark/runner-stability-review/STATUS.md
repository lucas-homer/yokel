# Stable runner continuity verified

2026-10-11: owner completed the reviewed Apple CLI partition repair without error. Fresh metadata confirms the sole stable-v1 partition and all other recorded ACL fields unchanged; opaque fields were not compared. Native identity and both signed zero-provider smoke jobs passed using the unchanged runner. No desktop-auth fallback was used. Evidence: deployment/continuity-result.json and migration-diagnosis/post-repair-metadata.json. The already-authorized stronger probe has been launched once; its outcome is pending. This verifies the current logged-in Mac session, not reboot or locked login-Keychain behavior.

## Prior preparation and repair record

# Stable runner built; stale Keychain partition repair pending

The owner delegated release of reviewed DocketClock research jobs within authorized scope and budgets to the primary. The replacement is implemented, independently reviewed, built and installed side by side at `/Users/home/.local/libexec/yokel/research-credentials-stable-v1`.

Executor SHA-256: `821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e`.

The protected primary-controlled signing key was initialized outside the repository. Three immutable jobs are signed and passed native check-job: job-alpha, job-beta, and round8-stronger-cap-initial. No job has run and no claim has been consumed. Native self-test and the stronger adapter's credential-free check passed. The 1,391 prior experimental files and current A/S freezes remain unchanged.

The owner ran `authorize-existing` and reported its success message. Subsequent identity checks failed in both Codex and the owner's Terminal. Metadata-only inspection, independently reproduced, found that a decrypt ACL trusts stable-v1, but the separate partition restriction still contains only the old v6 cdhash. Historical decrypt entries also remain; the earlier migration did not establish its intended complete ACL postcondition. See migration-diagnosis/REPORT.md and review/EVIDENCE.md. No token data was requested by the diagnostic helpers. The failed identity checks do not prove successful token access.

Independent review rejected the custom prompt-only repair: partition changes require explicit database credentials. The installed Apple security CLI supports a local password prompt when -k is omitted and invokes the required credential-bearing API. Owner and reviewer metadata-only queries each found exactly one matching item in the explicit login Keychain. The reviewer approved this fixed owner-run command on 2026-10-11:

```sh
/usr/bin/security set-generic-password-partition-list \
  -a docketclock-research-mini \
  -s yokel.docketclock.research.op \
  -S cdhash:e51b17a7a822e62cc4a0ad89c9de7a2602975a6c \
  /Users/home/Library/Keychains/login.keychain-db
```

The owner enters the login Keychain password only at Apple's local prompt, never as an argument or in chat. Live repair has not been performed. Keep the installed runner bytes unchanged; do not repeat authorize-existing or broaden trust. After the owner command, inspect metadata before any credential check; command success alone does not establish the intended postcondition.

After a reviewed repair, verify fresh metadata and identity, then run the two zero-cost signed smoke jobs sequentially with unchanged executable bytes. Check their boolean-only receipts and record any OS interaction. Only after those pass run the already authorized stronger probe once, then freeze and independently audit its outputs. Do not run smoke adapters directly with credentials or retry a consumed native job ID. Signed proposals expire at Unix 1791845496; if expired, prepare a reviewed new release rather than overwriting registry files.

Evidence: review/READY.json and FINAL.md; deployment/primary-validation.json, release-receipt.json, and FREEZE.json. Actual Keychain continuity and the new experiment outcome remain unverified. Future ordinary jobs change signed manifests; executor/tool/public-key maintenance may still require authorization.
