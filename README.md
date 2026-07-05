# Yokel

> Civic-tech monorepo. Helping busy non-experts **monitor** public-comment periods, rules, and
> hearings — and take **meaningful action** with honest receipts.
>
> `yokel` is a working **codename** (a local yokel trying to give back). The public umbrella brand
> is deliberately undecided — see [ADR 0006](docs/decisions/0006-umbrella-brand-deferred.md).

## What's here

The "house" architecture: a shared **substrate** (DocketClock) with **vertical wedges** renting it
through a shared contract (`packages/contracts`). The
[Week-1 validation spikes](docs/plans/week1-validation-spikes.md) are done — see the
[go/no-go memo](docs/plans/week1-go-no-go-memo.md): the D1 join-rate master gate **passed**
(DocketClock: **BUILD**), and the W3 value-density gate returned a **STOP** (Watershed Watch:
shelved, its stub kept as the reference wedge shape).

**DocketClock is built and running** on a local k3d cluster. It ingests federal comment-deadline
notices from the Federal Register and Regulations.gov APIs, reconciles them into confidence-scored
`ParticipationWindow`s over an append-only observation log — including cross-window chain links
(extensions, corrections, reopenings, withdrawals) classified by a deterministic RuleBox with
optional LLM adjudication for borderline cases — and serves them through an authenticated Fastify
REST API. The stack deploys via GitOps (ADRs [0008](docs/decisions/0008-kubernetes-self-host-postgres-cloudnativepg.md),
[0009](docs/decisions/0009-gitops-iac-toolchain.md)) and ships with structured logs, metrics,
dashboards, alerts, LLM tracing, and a gold-corpus eval suite gated in CI.

```
yokel/
├─ apps/
│  ├─ docketclock/       ← the substrate: FR + Regs.gov ingest → observation log → reconcile
│  │                        (RuleBox + optional Gemini adjudicator) → delivery API. BUILT.
│  └─ watershed-watch/   ← first vertical wedge. Stub (shelved at the W3 spike gate).
├─ packages/
│  └─ contracts/         ← THE SEAM: shared Zod schemas (ParticipationWindow, OCD-IDs,
│                           confidence/conflict enums, REST envelope). Currently 0.8.0.
├─ charts/docketclock/   ← first-party Helm chart (API + poller + CNPG Postgres)
├─ infra/                ← GitOps platform: Argo CD app-of-apps, CNPG, ESO + self-hosted Vault
│                           (transit auto-unseal), Prometheus/Grafana/Loki/Alloy/Langfuse,
│                           go-task entrypoints, Terraform structure (provider deferred)
├─ docs/
│  ├─ architecture/      ← canonical, agent-readable designs (hosting section superseded by ADR 0008)
│  ├─ decisions/         ← ADRs: the durable "why" behind every big call
│  ├─ design/            ← ratified feature designs (e.g. cross-window conflicts)
│  ├─ plans/             ← week1 spikes + go/no-go memo, agent orchestration
│  └─ research/          ← heavy reference (HTML reports, foundry JSON). NOT loaded routinely.
├─ plans/                ← phase plans (observability slices A–D, rename)
├─ spikes/               ← Week-1 validation harness (done; results in the go/no-go memo)
└─ tools/                ← doc generators
```

## Status

- ✅ Week-1 spikes: D1 join rate 78.7% → DocketClock **BUILD**; W3 value density 0 confirmed →
  Watershed Watch shelved (revival paths recorded in the memo)
- ✅ Platform: k3d + Argo CD GitOps, CNPG Postgres 18, ESO + Vault, GitHub Actions CI
  (typecheck / lint / build / DB-backed tests / infra-config guard)
- ✅ DocketClock spine: FR + Regs.gov adapters, append-only observation log, reconciliation +
  live `/v1/conflicts` proof feed, differential poller with dead-lettering, delivery API,
  cross-window chain conflicts
- ✅ LLM adjudication: deterministic RuleBox (rules-as-data) + provider-agnostic adjudicator port
  with a Gemini adapter, content-hash verdict cache, call budgets
- ✅ Observability (slices A–D): pino → Loki/Alloy logs, Prometheus metrics + Grafana
  dashboards/alerts, Langfuse LLM tracing, gold-corpus adjudicator evals with a CI regression gate
- ⏭️ **Next:** deeper verification (post-close accuracy tracking) and hardening; the
  customer-facing "Phase 3+" surface (webhooks, onboarding) is held on D5 buyer discovery,
  and cloud cutover is deferred until the stack is validated locally (provider undecided)

## Getting up and running locally

Everything runs **in-cluster on k3d**, backed by a colima VM (6 CPU / 12 GiB). Postgres is managed
by CloudNativePG — no local `createdb`.

### Prereqs

```bash
brew install git gh node@24 duckdb
brew install colima k3d kubectl helm go-task terraform tilt
corepack enable && corepack prepare pnpm@10.23.0 --activate
```

### Clone → cluster → app

```bash
git clone https://github.com/lucas-homer/yokel.git && cd yokel
pnpm install

cd infra
task dev-up      # colima → k3d → Argo CD → platform (CNPG/ESO/Vault) → vault-seed → docketclock
task status      # Argo applications + key pods
```

### Secrets

`task dev-up` seeds Vault with placeholders. Patch in real values (they flow Vault → ESO →
Kubernetes Secret):

```bash
REGS_API_KEY=xxx bash infra/scripts/seed-docketclock-secrets.sh
```

- `REGS_API_KEY` — Regulations.gov v4 key ([api.data.gov/signup](https://api.data.gov/signup/));
  the Federal Register API needs no key
- `GEMINI_API_KEY` (with `ADJUDICATOR=gemini`) — optional LLM adjudication of borderline chain links
- `DOCKETCLOCK_API_KEYS` — keys for the delivery API's `x-api-key` auth (fails closed)

For host-side scripts and smokes, copy `.env.example` → `.env`.

### Inner loop

```bash
tilt up          # from repo root: builds the image, deploys the chart, hot-reloads
                 # src via tsx watch; API lands on http://localhost:8088
```

### Service UIs

| UI         | Command (from `infra/`) | URL                    |
| ---------- | ----------------------- | ---------------------- |
| Argo CD    | `task argocd-ui`        | https://localhost:8081 |
| Grafana    | `task grafana`          | http://localhost:3000  |
| Prometheus | `task prometheus`       | http://localhost:9090  |
| Langfuse   | `task langfuse`         | http://localhost:3001  |

Tear down with `task dev-down` (deletes the cluster; colima keeps running).

### Tests & evals

```bash
pnpm test                                      # workspace-wide
pnpm --filter @yokel/docketclock test          # docketclock suite (incl. adversarial variants)
pnpm --filter @yokel/docketclock eval:chain    # adjudicator gold-corpus eval
```

## Working setup

Authoring/organizing happens on the **MacBook Air**; **local builds, installs, and the dev
environment live on the Mac Mini.** GitHub is the bridge. Full walkthrough: **[SETUP.md](SETUP.md)**.
Conventions for agents and contributors: **[AGENTS.md](AGENTS.md)**.

## License

TBD — see [ADR 0007](docs/decisions/0007-license-deferred.md) (MIT vs AGPL tension for civic tech).
Until a license is chosen, this is **all rights reserved**; do not assume open-source terms yet.
