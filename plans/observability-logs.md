# Observability Slice A — Logs (Grafana + Loki + structured app logs)

> Status: **Shipped** — PR-A1 (#49) and PR-A2 (#50) merged, plus the #52 follow-up (Grafana
> OutOfSync fix + platform-app globbing).
> Target: local k3d only (no cloud cluster yet; see memory `deploy-target-k3d-first`).
> Constraint: colima 12 GiB, ~5–6 GiB safe headroom — every component pinned lean.

## Decisions locked

- **Start with logs** (not metrics) — Grafana is the base layer everything else (metrics, Langfuse
  later) plugs into; logs are the highest-value first cut of "I can see the cluster."
- **LLM-obs tool (later slice): Langfuse v2** (Postgres-only) — out of scope for Slice A.
- **Log shipper: Grafana Alloy** (not Promtail). Promtail is in LTS/EOL; Alloy is the supported
  agent and the prod-parity choice. Slightly more config, worth it for longevity.
- **Structured JSON logs** from the app (pino) — JSON lines are what Alloy→Loki parse natively;
  k8s stdout is non-TTY so JSON is the natural format (no pretty-printing in-cluster).

## PR-A1 — Structured application logging (app code, no infra)

Independently mergeable; gives structured logs even before Loki exists (visible in `tilt`/`kubectl logs`).

1. **`src/log.ts`** — one configured pino root logger. `level` from `LOG_LEVEL` env (default `info`).
   JSON to stdout. Export a `child(component)` helper so each subsystem tags `component=poller|api|
reconcile|adjudicator`.
2. **API** — pass the instance to Fastify (v5 `loggerInstance`), drop the `logger: false` default.
   Request logs become structured; keep `/healthz` quiet (it's noisy) via a serializer/route opt.
3. **Poller hot paths** — replace `console.*` in `poll/poll.ts`, `poll/fr-poll.ts`, `poll/run.ts`,
   `reconcile/chain-adjudicate.ts` with structured logger calls. **The `[chain-adjudicate]` line
   becomes a structured event** — `log.info({ surfaced, cacheHits, llmCalls, deferred, llmLinked,
cap }, "chain adjudicate cycle")` — so Grafana can graph cacheHits vs llmCalls over time later.
4. **Leave** smoke tests + `db/migrate.ts` + backfill scripts on `console.*` (one-shot CLI tools).
5. **Verify:** `pnpm -r typecheck && pnpm -r test && pnpm lint` green; `kubectl logs` shows JSON lines
   with `component` + `level`; the adjudicate cycle line carries its fields.

Workflow: builder (against this spec) → adversary → PR → pr-feedback → merge (Tilt redeploys).

## PR-A2 — Loki + Alloy + Grafana (platform Argo apps)

Three `infra/argocd/apps/platform-*.yaml` Applications, sync-wave `"0"` (platform tier), `selfHeal`+
`prune`, `CreateNamespace=true`, `ServerSideApply=true` — matching the ESO/CNPG pattern. Argo syncs
from `main`, so these land via merge (same GitOps flow as the vault hardening #47).

1. **`platform-loki.yaml`** — `grafana/loki` chart, **SingleBinary mode**, filesystem storage,
   retention ~72h, 1 replica, tight resource requests. Namespace `observability`.
2. **`platform-alloy.yaml`** — `grafana/alloy` chart, DaemonSet, config tails `/var/log/pods` →
   Loki push API. Drops/relabels by namespace so we keep app + platform logs, not Alloy's own noise.
3. **`platform-grafana.yaml`** — `grafana/grafana` chart, Loki pre-provisioned as a datasource,
   admin password from a Vault→ESO secret (not inline). Exposed via Tilt port-forward initially
   (e.g. `localhost:3000`); a Traefik ingress can come later.
4. **Taskfile/README** — add a `grafana` port-forward convenience + a Troubleshooting note.
5. **Verify:** all three Argo apps `Synced/Healthy`; Grafana → Explore → Loki shows live pod logs;
   query `{namespace="docketclock"} |= "chain adjudicate cycle"` returns the structured cycle events;
   colima RAM still has headroom (`kubectl top nodes`).

## Out of scope (later slices)

- **Slice B — Metrics:** trimmed Prometheus + kube-state + node-exporter + app `/metrics` route.
- **Slice C — LLM-obs:** Langfuse v2, adjudicator instrumentation, seed eval dataset from the
  `adjudications` table.
- **Slice D — Evals:** dataset + scoring (Langfuse) and/or promptfoo CI regression gate.

## Rollback

- PR-A1: revert the merge; logging returns to `console.*`.
- PR-A2: delete the three Argo apps (or revert) → `observability` namespace prunes; app unaffected
  (logs still go to stdout, just uncollected).
