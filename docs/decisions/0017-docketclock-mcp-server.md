# 0017. Expose reconciled federal deadlines through a read-only OAuth MCP surface

- Status: **Accepted** — approach approved 2026-10-20; implementation/release remain gated.
- Date: 2026-10-19
- Revised: 2026-10-20 after Claude Fable 5.1 cross-provider review.
- Plan: [DocketClock MCP specification and phased implementation](../../plans/docketclock-mcp-server.md)
- Builds on: ADRs 0008/0009 (platform), 0013 (public release boundary) and 0015 (review authority).
- Number 0016 remains reserved for the review-policy decision in `plans/review-learning-loop.md`.

## Context

The operator has committed to an AI-agent access pilot through Claude and Codex. This supplies
the named buyer/use case required before specifying the deferred MCP contract, without claiming
an external paying customer. Agents need reconciled closes, deterministic confidence, conflicts,
submission links and evidence; ordinary Federal Register discovery does not provide that seam.

The delivery API already reads contract-validated Postgres projections and observations with
disclaimer/version/request-ID envelopes. Agency/search metadata and bounded evidence queries
are still gaps. MCP must share those read models rather than create another deadline engine.
The operator review CLI remains the only operator verdict write path.

The only cluster is k3d/colima on the Mac Mini, behind NAT, with roughly 5–6 GiB available in
a 6-CPU/12-GiB VM. Cloud provider selection is deferred. OAuth and remote-client requirements
are moving: delegated research reports a newer 2026-07-28 MCP transport and CIMD registration
preference, but actual client/SDK compatibility has not been tested. The plan labels all
protocol/vendor facts requiring implementation-time verification.

## Decision

Adopt the following, conditional on the plan's measured gates:

1. **Read-only federal MCP.** Six tools: `list_windows`, `search`, `fetch`, `list_conflicts`,
   `explain_window`, `get_submission_info`. Search/fetch provide the research-client facade;
   the other tools expose precise structured filters/evidence. No writes, subscriptions,
   submission, arbitrary SQL/URLs, bulk export, source refresh or LLM calls.
2. **One trust model.** Copy confidence/flags and close/display semantics from the stored,
   validated projection, including non-null conflicting closes and visible agent/human
   authority. Unknown/conflicting/stale and missing submission information are first-class
   answers. Every data result carries the shared disclaimer, version and request ID; transport
   metadata retains its protocol-defined format. Bounded evidence never masquerades as an
   intact raw Observation or a causal trace that was not recorded.
3. **Shared reads, separate workload.** Reuse/extend delivery queries for REST and MCP.
   Deploy `docketclock-mcp` in the existing chart/image with a dedicated SELECT-only civic-data
   role, bounded pool and separate limits. Authentication/audit state has separate writable
   roles and no civic write grants. Deny state data across every result, count and evidence
   relationship; passing a future state's release gate does not automatically widen MCP v1.
4. **Contract-keeper owns additions.** Propose the next free additive minor, assigned by the
   keeper because review-learning-loop PR-L1 also proposes 0.12.0:
   MCP inputs, bounded output DTOs, error/abstention envelopes and probes. Existing contracts,
   IDs, enums and REST `API_VERSION` remain compatible. Phase 0 candidates are reviewed
   before the value gate and frozen afterward; no production schema fork or keeper bypass.
5. **Remote Streamable HTTP, OAuth resource server.** Pin the protocol/SDK only after current
   docs and real-client probes. Require authorization code with PKCE S256, discoverable
   resource/AS metadata, resource-bound audience validation, short-lived tokens, rotation/
   revocation and one `docketclock:read` scope. Support tested pre-registration/CIMD and a
   constrained DCR compatibility path where required; never advertise an unimplemented mode.
6. **Conditional lightweight AS preference.** Spike a maintained `oidc-provider`-based
   separate Node process with Postgres persistence and invited-user login/consent/recovery.
   Two implementation days and a complete auth-negative-test gate bound this investment.
   If it fails, price and test hosted Auth0 rather than invent OAuth or weaken authentication.
   No new general-purpose IdP, queue or search service without measured need.
7. **Stable local exposure, portable names.** Prefer a named Cloudflare Tunnel to owned
   HTTPS resource/issuer hostnames after testing discovery, callbacks and streaming. T3
   Connect remains unverified for arbitrary third-party MCP; accept only if it passes the
   same tests. Cloud migration preserves names and moves through Terraform/Argo/Helm with
   PG18/CNPG, Vault/ESO and a controlled auth/data cutover.
8. **Validate before exposing.** Phase 0 stdio in Claude Code/Codex CLI measures nine jobs,
   all confidence states and provenance cases. Remote OAuth starts with one claude.ai
   connector, then compatibility/abuse/observability hardening, then cloud only after a
   measured availability need. Every phase has a go/no-go and rollback in the plan.

## Alternatives considered

- **An `/mcp` route on the existing API:** fewer processes/pools, but public OAuth parsing and
  agent load share its credentials and failure domain. Separate deployment is preferred for
  testable isolation/rollback; revisit only if measured resource cost forces it.
- **A REST proxy holding an operator API key:** avoids sharing query code, but inherits
  unbounded detail payloads and obscures per-user/client authorization. Direct shared,
  bounded read functions are a better seam.
- **Hosted AS first:** reduces local RAM and identity security operations. It remains a valid
  fallback and may win if the local adapter/login slice exceeds its budget. Current cost,
  custom-domain, DCR/CIMD and resource-audience behavior must be demonstrated.
- **Full self-hosted IdP:** richer account administration than this invited-user pilot needs;
  extra operational/RAM budget is unjustified without multi-user evidence.
- **Stdio only:** the right value spike and fallback, but cannot serve cloud-hosted claude.ai.
- **Ephemeral tunnel names or unauthenticated public access:** inconsistent with stable OAuth
  discovery/audience/callbacks and per-client revocation; rejected.
- **LLM deadline resolution or MCP review writes:** expands authority beyond this access task
  and bypasses the CLI policy. Rejected; existing `agent_resolved` evidence is read honestly.

## Consequences

- Adds an agent surface without changing the source of truth or review authority. The
  operator must still verify primary notices; downstream agents cannot be forced to display
  warnings, so user-visible caveat preservation is a measured client release gate.
- Requires real delivery work: metadata search, bounded M:N/conflict evidence, snapshot-aware
  reads, public redaction and output-schema probes. Those gaps are not hidden behind an MCP
  wrapper or treated as already implemented REST endpoints.
- The local design budgets about 1.4 GiB incremental ceiling and under 800 MiB steady-state
  target; these are estimates pending measurement. Library maintenance and login security
  are explicit costs, not “free OAuth.” Hosted and tunnel prices remain unquoted.
- Logs use existing Pino/Alloy/Loki (72 hours); minimal operational audit metadata uses
  Postgres (proposed 30 days plus backup retention). No prompts/tokens/raw evidence are logged.
- Local availability depends on the Mini and tunnel. Stable domains ease cloud migration,
  but switching issuers or restoring auth state can require revocation and renewed consent.
- Disabling MCP/tunnel and revoking grants rolls back exposure without changing observations,
  window projections, REST delivery or the CLI. This ADR authorizes no deployment or git action.
