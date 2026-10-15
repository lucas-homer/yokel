# Primary decision: remove per-experiment Keychain trust churn

2026-10-11. Current v6 is demonstrably cdhash-bound. Rebuilt-policy authorization
is a consequence of our ad-hoc reader design, not a fundamental requirement for
1Password service-account runs. No currently implemented safe new-job shortcut was
found. [Detailed spec and sources](RECOMMENDATION.md).

Recommend a stable native executor with externally signed, fixed, fully pinned job
manifests. Authorize the reader once at migration; keep reader/account/vault/reference
scope unchanged for subsequent reviewed jobs. Signing certificates with a stable
requirement are a shorter alternative if properly protected signing infrastructure
already exists, but its availability and actual custom-ACL continuity are unknown.

The security decision is **who may release credential-bearing jobs without another
human action**. Signed manifests do not solve interaction if every signature needs
a user touch. An unattended signer must have explicit bounded release delegation and
protected custody; an unrestricted signer available to the primary/runtime agent is
not independent approval. It transfers admission authority to that agent. No such
production signer or standing delegation has been established in this review.

Authorities differ:

- A stable code-signing private key can create replacement code satisfying the trusted
  reader identity, including a reader that exports the service token. Access to that
  key is effectively authority over the Keychain item and the entire service account.
- A manifest signer can authorize payload code to use/exfiltrate the allowed provider
  credentials and spend with them. It cannot expand the immutable native reference
  envelope or invoke a service-token export API in the proposed protocol. This narrower
  scope is useful, but the existing same-user/dependency/process-memory limitations
  remain; it must not be described as a hostile-user sandbox or proof of reviewed code.
- A protected, policy-constrained release signer can admit only jobs in an owner-approved
  scope, based on exact artifact/approval evidence. That independent signing service is
  additional infrastructure, not a capability already present today.

Primary can prepare a **nonsecret synthetic candidate** and tests before any production
trust migration. No current ACL/key/token must change for that work. Before production
deployment, make the exact executor, public-key fingerprint, signer custody/delegation,
hard scope and migration steps reviewable, then obtain explicit approval for the new
authority arrangement and one-time trust migration. Exploration of reduced prompts
does not authorize silently replacing exact-build trust with unrestricted signing.

For the immediate experiment, do not rebuild yet merely to force another token/trust
step if primary chooses to pursue this migration first. The pending research job remains
separate from runner changes; no old completed job or frozen pin can be repurposed.

Changed only these new design reports. No implementation, builds, security settings,
Keychain/key access or paid calls. Public-document browsing and read-only signature
metadata were the only network/signature activities.
