# Stable candidate interface — 2026-10-11

Production key creation, installation, enrollment and live execution remain primary-owned.
The user directly delegated: “Primary releases reviewed jobs within my authorized scope
and budgets.” Primary's OWNER-DELEGATION.md / ADR 0012 are authoritative and unchanged.

Public executor commands: `check-policy`, `check-job JOB_ID`, `identity`, `smoke`,
`run JOB_ID`, `enroll`, `rotate-local`, `authorize-existing`. Only run dispatches a signed fixed job.
Registry path is compiled into the core: JOB_ID.json and JOB_ID.sig, owner-only.
No manifest-path/argv/environment/public-key override. Internal stages bind the same
manifest SHA-256; they do not read Keychain. Synthetic builds prohibit all Keychain calls.

Unsigned job proposal JSON (release tool signs exact canonical bytes):

```json
{
  "schema_version": "yokel.research-job.v1",
  "job_id": "round8-stronger-cap-initial",
  "scope_id": "OWNER_AUTHORIZED_SCOPE_ID",
  "project": "yokel.docketclock.research",
  "expires_unix": 0,
  "provider_variables": ["OPENROUTER_API_KEY"],
  "job": {
    "argv": ["/EXACT/BUNDLED/python3.12", "-I", "-S", "-B", "/EXACT/REVIEWED/adapter.py", "--live-initial"],
    "files": {"/EVERY/CANONICAL/DEPENDENCY": "sha256"},
    "timeout_seconds": 1800
  },
  "budget": {
    "prior_nanousd": 542976718,
    "reservation_nanousd": 161920000,
    "ceiling_nanousd": 2000000000
  },
  "review": {"path": "/CANONICAL/FINAL/REVIEW.md", "sha256": "sha256"}
}
```

expires_unix must be a future bounded Unix-second integer at release/launch (0 is a
placeholder and rejected). All budget fields are exact integer nanodollars. Scope
ID and approval receipt bind provenance; signer is the delegated primary authority,
not an independent judge. Review path/hash must be among file pins. Each ID is unique
and consumed before authenticated dispatch; failed claims are not automatically retried.

Provider variables are a nonempty subset of the immutable existing OpenRouter/TypeSafe
reference envelope; a stronger-only job gets OpenRouter only. No per-job reference,
account, vault or op override. Fixed adapter argv grammar above; Python and adapter
must be pinned. All files must reside under primary-reviewed dependency roots.
Budget metadata and native arithmetic do not enforce billed spend/calls: the reviewed
adapter/ledger remains responsible. No native inventory/Jev/stronger transport is added.
The core has no fixed dollar ceiling: only safe integer arithmetic limits. Each signed
manifest's ceiling must match owner authorization; the current experiment stays at $2.
Future owner-authorized budgets can use new signed manifests without another reader build.
Zero reservation is permitted for reviewed no-provider-cost credential smoke jobs.
It is signed metadata, not network enforcement. The paid stronger job keeps its
161920000-nanodollar reservation and 2000000000-nanodollar ceiling unchanged.

authorize-existing is an explicit user-only real-TTY migration command. It obtains
only the fixed existing item's reference (NULL password length/data) and replaces
ACL trust with this exact executable. It requests no token bytes and changes no token
data. Runtime never invokes it automatically; synthetic builds reject before any
Keychain API. Actual OS behavior is untested and primary must present this command
to the user after review/install; manual rotate-local remains the fallback.

Core config/build and local protected-file release signing tool will be supplied here.
They require primary-finalized absolute registry/journal/custody paths outside the repo;
the candidate generates/accesses no production signing key. No remote infrastructure.
