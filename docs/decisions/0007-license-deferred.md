# 0007. License deferred (all rights reserved for now)

- Status: Proposed (decision pending)
- Date: 2026-06-14

## Context

This is intended to become an open civic-tech project that may take outside contributions. License
choice is consequential and has a real tension:

- **Permissive (MIT/Apache-2.0):** maximum contributor- and adoption-friendliness; allows proprietary
  reuse (e.g. an incumbent could fold the substrate into a closed product).
- **Copyleft (AGPL-3.0):** protects against proprietary forks of a network service — relevant given
  the competitive risk from govtech incumbents (Granicus/FiscalNote) noted in the research. Prior art
  in this space (Decidim, Consul) is AGPL. But AGPL deters some commercial contributors/users.

Note also a possible split: the `contracts`/substrate could be permissive (to encourage the OCD-ID
ecosystem and AI-agent builders) while a vertical app is copyleft.

## Decision

**Deferred.** Until a license is chosen, the repo is **all rights reserved** — contributors should
not assume open-source terms. Decide before any public release or first external contribution.

## Consequences

- No accidental open-source grant before the model is intentional.
- Revisit alongside [0006](0006-umbrella-brand-deferred.md) at go-public time. Likely default lean:
  Apache-2.0 for `contracts`, AGPL-3.0 for the apps — to be confirmed.
