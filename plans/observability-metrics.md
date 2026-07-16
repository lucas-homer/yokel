# Observability Slice B — Metrics (Prometheus + app instrumentation + Grafana dashboards/alerts)

> Status: **Shipped** — PR-B1 (#63), PR-B2 (#64), PR-B3 (#65) merged. Closed the observability
> epic: A (logs, #49–#50), C (LLM-obs, #56–#59), D (evals, #60–#62), B (metrics, #63–#65).
> Target: local k3d only (no cloud cluster yet; see memory `deploy-target-k3d-first`).
> Constraint: colima 12 GiB. Live headroom is healthy — both nodes ~18% mem (~2.1 GiB each of 12),
> so a lean Prometheus + kube-state-metrics + node-exporter fits; still pin every limit and disable
> bundled extras, same discipline as Loki/Alloy.
> Builds on: Slice A (`observability-logs.md`) — reuses the `observability` namespace, the
> inlined-Helm-from-ArgoCD-Application convention, and the already-deployed Grafana (a Prometheus
> datasource + dashboards just plug into its existing values). And Slice C — the `LlmTracer` seam
> that already carries token/latency is the hook for LLM metrics.

## Why this slice, why now

We can see the cluster's **logs** (Slice A) and the adjudicator's **traces** (Slice C), but we have no
**metrics** — no time-series for "is the poller actually cycling," "what's the adjudicator's p95 latency
and token spend," "what's the cache-hit ratio," "are requests erroring." Logs answer "what happened in this
one event"; metrics answer "what's the rate/trend/distribution over time" and are what alerts fire on. This
is the missing middle of the epic, and the seams are unusually clean: the poll/chain cycles already compute
exactly the summary counts we'd export, and Slice C's `LlmTracer` interface already receives token usage +
latency on every call — it just routes them only to Langfuse today (and silently to a no-op when
`LANGFUSE_*` is unset). A second tracer impl turns that existing signal into Prometheus series for free.

## What exists today (the seams this slice hooks into)

**Infra (Slice A patterns to mirror exactly):**

- **Deploy convention** — Grafana/Loki/Alloy are each an ArgoCD `Application` under
  `infra/argocd/apps/platform-*.yaml` with the **Helm chart referenced directly** and values **inlined**
  under `spec.source.helm.values` (no vendored chart, no values file). All: `destination.namespace:
observability`, `syncOptions: [CreateNamespace=true, ServerSideApply=true]`, automated prune+selfHeal,
  `sync-wave` annotation. A new `platform-prometheus.yaml` dropped into `infra/argocd/apps/` is
  **auto-registered** — `task platform` globs `argocd/apps/platform-*.yaml` and the root app-of-apps
  (`infra/bootstrap/root-app-local.yaml`) manages the dir recursively. No registration edit needed.
- **RAM discipline** — every workload pins `requests` + a **memory `limits`** (CPU left unlimited), and
  Loki carries a block of "footgun disablers" (`gateway/chunksCache/resultsCache/monitoring.* = false`) to
  protect the budget. Mirror this for Prometheus (trim alertmanager/pushgateway).
- **Grafana** (`platform-grafana.yaml`) — datasources provisioned via the chart's
  `datasources."datasources.yaml"` value (Loki wired there, `isDefault: true`). Dashboards are **not yet
  provisioned** (a comment notes "dashboards arrive via provisioning later") — `dashboardProviders` +
  `dashboards` chart values are the unused insertion point. Admin via ESO secret `grafana-admin`.
- **No Prometheus anywhere** — no operator, no kube-prometheus-stack, no ServiceMonitor/PodMonitor CRDs, no
  scrape annotations on any pod. Loki's chart explicitly **disables** its serviceMonitor/rules. ⇒ we use
  **annotation-based static scraping** (`prometheus.io/scrape`), not the operator (staying in-budget, in
  the spirit of how A avoided it). Flipping Loki's `monitoring.serviceMonitor`/`rules` back on to scrape
  Loki itself is a natural later follow-up.
- **Secrets** — ESO + `vault-backend` ClusterSecretStore (sync-wave "1"). Prometheus server needs no
  secret; Grafana already has its admin secret. (We deliberately avoid a standalone Alertmanager — see
  Decisions — so no new secret is required for alerting.)
- **docketclock deploy** — the app ships via the first-party Helm chart `charts/docketclock` (Tilt-managed
  locally; `app-docketclock.yaml` is the one Argo app excluded from the platform glob). Pod scrape
  annotations go in that chart's Deployment template.

**App (DocketClock instrumentation seams):**

- **No `prom-client`** / no metrics lib present. `fastify ^5` (so a hand-rolled `/metrics` route is the
  clean fit, mirroring how `/openapi.json` opts out of the response envelope). `pino` for logs, `langfuse`
  for traces.
- **Fastify server** — `src/api/server.ts` `buildServer()`; public probes `/healthz` (`:265`, `select 1`),
  `/readyz` (`:285`), `/openapi.json` (`:304`, `schema:{hide:true}`, envelope-bypassed — the template for
  `/metrics`). The auth-gated scope registers at `:310`; `/metrics` mounts PUBLIC **before** it. `onRequest`
  hook at `:200` (add a paired `onResponse` for HTTP histograms).
- **Poller** — `src/poll/run.ts` self-rescheduling `tick()` (`:93`); three try/caught passes each emitting
  `log.info({ summary }, "… cycle")` at `:105/:111/:121`. `FrPollSummary` (`fr-poll.ts:128`) and
  `PollSummary` (`poll.ts:114`) carry `listed/ingested/deduped/skipped/transitions/deadLettered/recovered/
truncated/pagesFetched/…` — observe the whole summary object once per pass right at those log sites.
  Heartbeat written each cycle (`writeHeartbeat`, `:73`) → liveness gauge.
- **Chain adjudicator** — `chainReconcileOnce` **returns** `{ surfaced, cacheHits, llmCalls, deferred,
llmLinked, cap, links }` (`chain-adjudicate.ts:264`), captured at `run.ts:118` — a cleaner seam than the
  log event. Per-pair consult failures `log.warn` at `:228` → `llm_errors_total`. Verdict at `:237`
  (only `affirm` links) → verdict-distribution counter.
- **LLM token/latency** — `gemini-adjudicator.ts` times latency (`:213/:221`) and parses `usageMetadata` →
  `LlmTokenUsage {input,output,total}` (`:142`), handing both to `this.tracer.recordGeneration({ model,
usage, latencyMs, verdict, … })` (`:252`). The `LlmTracer` interface (`src/adjudicator/tracer.ts`:
  `recordGeneration` / `recordCacheHit`) is injected once in `select.ts`; when `LANGFUSE_*` is unset it's a
  `NoopTracer` and the data is dropped. **This interface is the seam for LLM metrics** — independent of
  Langfuse.
- **DB** — `src/db/client.ts:17` `createClient()` is a postgres.js pool created bare (no `max`/timeout, no
  native pool gauges). `db_up` is cheaply derivable from the `select 1` already in `/healthz`/`/readyz`.
- **Test/style** — hand-rolled `assert` + `out[]` + `process.exit` runners wired into `pnpm test`;
  prettier `--check .` + `tsc` are the `check` gate.

## Decisions locked

- **Lean standalone Prometheus, NOT kube-prometheus-stack.** The full stack bundles its own Grafana +
  node-exporter + operator and would collide with our Grafana and blow the RAM budget. Use the
  `prometheus-community/prometheus` chart, inlined in `platform-prometheus.yaml`, server + **kube-state-
  metrics** (pod/deployment/restart metrics — "see the cluster") + **node-exporter** (node CPU/mem/disk),
  with **alertmanager + pushgateway disabled**. Pin memory limits on each.
- **Annotation-based scraping, no operator.** No prometheus-operator (no CRDs to install, no extra wave-0
  app/RAM). The chart's bundled `kubernetes-pods` scrape job honors `prometheus.io/{scrape,port,path}` pod
  annotations; docketclock's chart Deployment gets those annotations. Matches how A deliberately avoided
  the operator.
- **Alerting = Grafana unified alerting, NOT a standalone Alertmanager.** Grafana is already deployed;
  its built-in alert rules + contact points cover our need (poller stalled, LLM error spike, `/readyz`
  down) with **zero extra RAM and zero new secret**. A dedicated Alertmanager is a later option only if we
  outgrow Grafana-managed alerts. (Contact point starts as a no-op/log receiver locally; a real
  Slack/webhook receiver — and its ESO secret — is a deliberate later add.)
- **Hand-rolled `/metrics`, not a Fastify plugin.** A raw `prom-client` registry exposed on a PUBLIC,
  `logLevel:"silent"`, envelope-bypassed route (mirroring `/openapi.json`) — the Zod type-provider +
  envelope-on-every-response conventions make `fastify-metrics`' assumptions a poor fit. Metric names are
  prefixed `docketclock_`.
- **LLM metrics via a second `LlmTracer`, not new call-site code.** A `MetricsTracer` implementing
  `recordGeneration`/`recordCacheHit`, composed with the existing tracer (composite), so token/latency
  metrics are emitted **independent of Langfuse** — closing today's "dropped when `LANGFUSE_*` unset" gap.
  No change to the Gemini call site or the contract.
- **Metrics are pull, retention is local + small.** Prometheus scrapes `/metrics`; small local TSDB with a
  **5Gi PVC + ~7d retention** (cheap, survives a pod restart — Loki already persists 5Gi; Grafana is
  ephemeral). Enough for local trend/alerting, not long-term capacity planning.
- **The eval gate stays in CI, NOT a Prometheus metric.** The D3 gate is a CI artifact (the red job IS the
  alert); surfacing it in Grafana would require pushing CI results into a store — explicitly out of scope
  (see below) to avoid scope creep.
- **No contract change**, no new infra secret (Prometheus server is unauthenticated in-cluster; reached via
  `task prometheus` port-forward, never Ingress).

## PR-B1 — App metrics: `/metrics` endpoint + instrumentation (app code, no infra)

Independently mergeable and useful before Prometheus exists (metrics visible via `curl localhost:8080/
metrics` / `kubectl exec`), exactly as A1 shipped structured logging before Loki. **No infra in this PR.**

1. **`src/metrics.ts`** — one `prom-client` `Registry` (+ `collectDefaultMetrics()` for Node process/GC/
   heap). Declare the app metrics (names below) and export typed recorder helpers. **As shipped** the
   summary recorders are split per source (`recordFrPoll(FrPollSummary)`, `recordRegsPoll(PollSummary)`) so
   each maps its own fields onto `poll_items_total{source,outcome}`, plus `recordChainCycle(result)`,
   `recordPollPassFailure(pass)`, `observePollCycle(seconds)`, `observeHttp({method,route,status,seconds})`,
   `setHeartbeat(unixSeconds)`, `setDbUp(bool)`, and `recordLlmGeneration`/`recordLlmCacheHit` (fed by the
   MetricsTracer). Pure module, no I/O. Unit-tested (`test/metrics.test.ts`).
2. **`/metrics` route** — PUBLIC, mounted before the auth scope in `server.ts` (alongside `/openapi.json`):
   `schema:{hide:true}`, `logLevel:"silent"`, returns `registry.metrics()` with `registry.contentType`,
   NOT the contract envelope. Add an `onResponse` hook (paired with the existing `onRequest` at `:200`) to
   feed `docketclock_http_request_duration_seconds{route,method,status}` + `_http_requests_total`. Exclude
   the probe/metrics routes from the histogram (self-noise).
3. **Poll + chain instrumentation** — at each `log.info({summary})` site call `recordFrPoll(fr)` /
   `recordRegsPoll(regs)`; in each pass's catch call `recordPollPassFailure("fr"|"regs"|"chain")`; wrap
   `tick()` for `docketclock_poll_cycle_duration_seconds` (a duration histogram — no `_poll_cycles_total`
   counter shipped; per-pass failures carry the error signal); set
   `docketclock_poller_last_heartbeat_seconds` in `writeHeartbeat`. Call `recordChainCycle(chain)` off
   `chainReconcileOnce`'s return. **The poller runs no HTTP server**, so it also starts its own standalone
   `/metrics` listener (`src/metrics-server.ts`, `METRICS_PORT` default 9464), drained on shutdown.
4. **LLM `MetricsTracer`** — `src/adjudicator/metrics-tracer.ts` implementing `LlmTracer`:
   `recordGeneration` → `docketclock_llm_tokens_total{model,kind=input|output}`,
   `_llm_call_latency_seconds{model}`, `_llm_calls_total{model,verdict}`; `recordCacheHit` →
   `_llm_cache_hits_total{kind}` (ratio derivable vs calls). Compose it with the existing tracer in
   `select.ts` via a `composeTracers()` combinator so it runs **whether or not Langfuse is configured**.
   Unit-tested against the `LlmTracer` contract.
5. **DB up** — set `docketclock_db_up` from the `select 1` in `/healthz`/`/readyz`.
6. **Verify:** `pnpm test` green (incl. new tests); `pnpm typecheck`/`lint`/`build` green; run the app and
   `curl /metrics` shows `docketclock_*` series + default Node metrics in prom format; confirm `/metrics` is
   unauthenticated and silent in logs; confirm token/latency series populate with `LANGFUSE_*` UNSET.

### Metric inventory (B1)

| Metric                                                                                                                                                                 | Type      | Seam                              |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | --------------------------------- |
| `docketclock_http_requests_total{route,method,status}`                                                                                                                 | counter   | `onResponse` hook                 |
| `docketclock_http_request_duration_seconds{route,method,status}`                                                                                                       | histogram | `onResponse` hook                 |
| `docketclock_poll_cycle_duration_seconds`                                                                                                                              | histogram | wrap `tick()`                     |
| `docketclock_poll_pass_failures_total{pass}`                                                                                                                           | counter   | per-pass catch                    |
| `docketclock_poll_items_total{source,outcome}` (listed/fetched/ingested/deduped/skipped/repolled/transitions/recovered/dead_lettered)                                  | counter   | `recordFrPoll`/`recordRegsPoll`   |
| `docketclock_poll_pages_fetched_total{source}`                                                                                                                         | counter   | `recordFrPoll`/`recordRegsPoll`   |
| `docketclock_poll_truncated{source}`                                                                                                                                   | gauge     | `recordFrPoll`/`recordRegsPoll`   |
| `docketclock_poller_last_heartbeat_seconds`                                                                                                                            | gauge     | `writeHeartbeat`                  |
| `docketclock_chain_candidates` / `_amendments` / `_conflicts_live`                                                                                                     | gauge     | `recordChainCycle`                |
| `docketclock_chain_confident_links_total` / `_ambiguous_total` / `_cache_hits_total` / `_llm_calls_total` / `_llm_linked_total` / `_deferred_total` / `_retired_total` | counter   | `recordChainCycle`                |
| `docketclock_llm_tokens_total{model,kind}`                                                                                                                             | counter   | `MetricsTracer.recordGeneration`  |
| `docketclock_llm_call_latency_seconds{model}`                                                                                                                          | histogram | `MetricsTracer.recordGeneration`  |
| `docketclock_llm_calls_total{model,verdict}`                                                                                                                           | counter   | `MetricsTracer.recordGeneration`  |
| `docketclock_llm_cache_hits_total{kind}`                                                                                                                               | counter   | `MetricsTracer.recordCacheHit`    |
| `docketclock_db_up`                                                                                                                                                    | gauge     | `/healthz` + `/readyz` `select 1` |
| `process_*` / `nodejs_*` (default)                                                                                                                                     | —         | `collectDefaultMetrics()`         |

> LLM **error rate** is not a dedicated series: it's derivable as `chain_llm_calls_total`
> (attempts, incl. throws) − `llm_calls_total` (successful generations recorded by the tracer). A dedicated
> `llm_errors_total` at the consult-fail site can be added later if a direct series proves more convenient.

## PR-B2 — Prometheus deploy + scrape wiring (infra)

1. **`infra/argocd/apps/platform-prometheus.yaml`** — ArgoCD Application, `prometheus-community/prometheus`
   chart inlined: server (pinned mem limit, 5Gi PVC, `--storage.tsdb.retention.time=7d`) +
   `kube-state-metrics` (enabled) + `node-exporter` (enabled, small) + **alertmanager: false** +
   **pushgateway: false**. `destination.namespace: observability`, `sync-wave "1"`, `CreateNamespace=true`,
   `ServerSideApply=true`, automated prune+selfHeal. Verify the bundled `kubernetes-pods` scrape job honors
   `prometheus.io/{scrape,port,path}` (default in this chart) — keep it; trim other default jobs only if
   noisy.
2. **Scrape annotations on docketclock** — add `prometheus.io/scrape: "true"`, `prometheus.io/port: "8080"`,
   `prometheus.io/path: "/metrics"` to the Deployment pod template in `charts/docketclock` (Tilt re-applies
   locally).
3. **Grafana Prometheus datasource** — append a `type: prometheus` entry
   (`url: http://prometheus-server.observability.svc.cluster.local`) to `datasources."datasources.yaml"` in
   `platform-grafana.yaml`; make Prometheus the default datasource (Loki stays for logs).
4. **`task prometheus`** — a port-forward convenience in `infra/Taskfile.yml` (mirror `task grafana`/
   `task langfuse`), and a one-line mention in `infra/README.md`'s observability legend.
5. **Verify:** `task platform` (or push → Argo auto-sync) brings the app to Synced/Healthy; `kubectl top
nodes` before/after stays within budget; Prometheus **Targets** page shows the docketclock pod `UP` and
   kube-state-metrics/node-exporter scraping; a PromQL query in Grafana (`docketclock_poll_cycles_total`)
   returns data; ArgoCD shows no permanent OutOfSync (replicate any chart `ignoreDifferences` quirk if it
   appears).

## PR-B3 — Dashboards + alerts (Grafana provisioning)

1. **Dashboards** — provision via Grafana chart `dashboardProviders` + `dashboards` (the unused insertion
   point) in `platform-grafana.yaml`:
   - **DocketClock app** — poll cycle rate/duration + items by source/outcome, dead-letter rate, poller
     heartbeat freshness; adjudicator panel: LLM calls/min, p50/p95 latency, token spend rate,
     cache-hit ratio, verdict distribution (affirm/reject/uncertain), error rate; HTTP req rate + p95 +
     5xx ratio; `db_up`.
   - **Cluster** — node CPU/mem/disk (node-exporter) + pod restarts/mem by namespace (kube-state-metrics),
     so "see the cluster" is real. (A curated import of a known KSM/node dashboard is fine.)
2. **Alerts (Grafana unified alerting)** — a small rule set with a local log/no-op contact point:
   - **Poller stalled** — `time() - docketclock_poller_last_heartbeat_seconds > 3×interval`.
   - **LLM error spike** — `rate(docketclock_llm_errors_total[15m])` above a floor.
   - **Readiness down** — `docketclock_db_up == 0` for N minutes (or probe-based).
   - (Optional) **cache-hit collapse** — ratio drops below a floor (a prompt/dedup regression signal).
3. **(Optional follow-up)** flip Loki's `monitoring.serviceMonitor.enabled`/`rules.enabled` back on now that
   Prometheus exists, to scrape Loki itself.
4. **Verify:** dashboards load with live data; force each alert (e.g. stop the poller → "stalled" fires to
   the contact point); confirm alert state visible in Grafana; document how to wire a real Slack/webhook
   receiver (+ its ESO secret) when wanted.

## Out of scope (later)

- **Standalone Alertmanager + real receivers** — Grafana-managed alerting suffices locally; a dedicated
  Alertmanager (and Slack/PagerDuty ESO secret) is a later add if we outgrow it.
- **prometheus-operator / ServiceMonitors** — annotation scraping is enough at this size; revisit if the
  number of scrape targets grows.
- **Surfacing the D3 eval gate in Grafana** — it's a CI artifact; pushing CI results into a metrics store
  is a separate effort.
- **Tracing-to-metrics correlation / exemplars**, **long-term remote-write storage**, **per-query DB
  timing histograms** (postgres.js exposes no native pool gauges — would require wrapping `createClient`).
- **Cloud-cluster wiring** — same `deploy-target-k3d-first` posture as the rest of the epic.

## Rollback

- PR-B1: revert; `src/metrics.ts` + the `/metrics` route + `MetricsTracer` are additive and touch no
  verdict/pipeline logic (the composite tracer falls back to the existing single tracer).
- PR-B2: delete `platform-prometheus.yaml` (+ the datasource entry + the chart scrape annotations); nothing
  depends on it — Grafana keeps Loki.
- PR-B3: remove the dashboard/alert provisioning values; Prometheus + the datasource remain.
