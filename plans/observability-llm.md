# Observability Slice C — LLM-obs (Langfuse v2 + adjudicator tracing + eval-dataset seed)

> Status: **Shipped** — PR-C1 (#56), PR-C2 (#57), PR-C3 (#59, eval-dataset seed) merged. Langfuse v2
> is deployed/healthy on k3d and verified end-to-end (live trace + 50-item seeded dataset).
> Target: local k3d only (no cloud cluster yet; see memory `deploy-target-k3d-first`).
> Constraint: colima 12 GiB, ~5–6 GiB safe headroom — Slice A (Loki/Alloy/Grafana) already
> spends some of that, so Langfuse + its Postgres must be pinned lean and RAM checked
> (`kubectl top nodes`) before and after.
> Builds on: Slice A logs (`observability-logs.md`, shipped) and the platform-tier
> `vault-backend` ClusterSecretStore hoist (#51) — Langfuse reuses both (ESO secret pattern + the
> git-sourced raw-manifest convention under `infra/argocd/manifests/`).

## Why this slice, why now

Our highest-value signal is **LLM adjudication quality**, not cluster metrics. The chain-seam
adjudicator (`apps/docketclock/src/adjudicator/`) decides whether one Federal Register notice genuinely
amends another — a real LLM call (Gemini), cached write-once in the `adjudications` table. Today we can
see _that_ it ran (the structured `chain adjudicate cycle` log event: `surfaced / cacheHits / llmCalls /
deferred / llmLinked / cap`), but not _what went in or came out_ of any single call, its latency, or its
token cost. Langfuse gives us per-call traces (input → output, model, latency, tokens) and — critically —
turns the `adjudications` table into the seed for an **eval dataset** (Slice D). C unblocks D.

## What exists today (the seams this slice hooks into)

- **`Adjudicator` port** — `src/adjudicator/port.ts`: `{ readonly id: string; adjudicate(input):
Promise<AdjudicationVerdict> }`. `id` is provenance `"provider:model"` (e.g. `gemini:gemini-2.5-flash`,
  `null:abstain`). Verdict is exactly `{ classification: affirm|reject|uncertain, rationale }`.
- **The one LLM call site** — `src/adjudicator/gemini-adjudicator.ts:157–211`: raw `fetch` POST to
  `…/v1beta/models/{GEMINI_MODEL}:generateContent`, `temperature: 0`, JSON `responseSchema`. The Gemini
  response carries `usageMetadata` (prompt/candidates/total token counts) that we **currently discard**.
- **Read-through cache + persist** — `src/adjudicator/consult.ts:109–157`: `consultAdjudicator()` peeks
  the cache (`SELECT … WHERE content_hash = $1 AND adjudicator_id = $2`), and on a miss calls
  `adjudicator.adjudicate()` then `INSERT … ON CONFLICT (content_hash, adjudicator_id) DO NOTHING`.
- **Orchestrator + existing log** — `src/reconcile/chain-adjudicate.ts:116` `adjudicateAmbiguousPairs()`;
  the `chain adjudicate cycle` event is logged at `:219`.
- **Selection/wiring** — `src/adjudicator/select.ts` `selectAdjudicator(env)`; instantiated at
  `src/reconcile/persist.ts:450` (`options.adjudicator ?? selectAdjudicator()`).
- **`adjudications` table** — `migrations/0008` + `0009`: PK `(content_hash, adjudicator_id)`, plus
  `input jsonb`, `verdict jsonb`, `created_at timestamptz`. The eval-seed source.
- **Env pattern** — entrypoints (`src/poll/run.ts:49`, `src/api/run.ts`) `process.loadEnvFile()` FIRST,
  then dynamic-import env-reading modules. Any `LANGFUSE_*` reads must sit behind that ordering.

## Decisions locked

- **Langfuse v2 (Postgres-only).** v3 adds ClickHouse + Redis + S3 — too heavy for the budget. v2 needs
  only a Postgres. Pin the **`langfuse/langfuse:2`** image; do **not** use the upstream Langfuse Helm
  chart (it assumes v3 infra). Deploy as raw manifests (Deployment + Service + ESO) under
  `infra/argocd/manifests/langfuse/`, fronted by one platform Argo app — exactly the git-sourced raw-
  manifest pattern we set up for the ClusterSecretStore (#51).
- **Dedicated Postgres via CNPG**, not the app DB. A 1-instance `Cluster` (`langfuse-db`) in a dedicated
  `langfuse` namespace, small PVC, default StorageClass. Isolation (Langfuse owns/migrates its own
  schema), prod-parity (same operator we already run), cheap. CNPG generates the credentials; ESO is not
  needed for the DB password (CNPG mints a `-app` secret), only for Langfuse's own app secrets.
- **App secrets via ESO from Vault**, mirroring `grafana-admin`: `NEXTAUTH_SECRET`, `SALT`, and the
  `ENCRYPTION_KEY` come from `secret/langfuse/*` through the `vault-backend` ClusterSecretStore; seeded by
  `infra/scripts/vault-seed.sh` (defaults for dev, override via env). The poller→Langfuse credentials
  (`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`, created in the Langfuse UI/bootstrap) flow back into the
  app via a `docketclock` ExternalSecret key — same all-or-nothing seeding rule.
- **Instrumentation seam: an injected tracer, not a port change.** The `Adjudicator` verdict contract
  stays frozen (no contract-keeper change). Tracing is a cross-cutting concern injected at construction:
  define a tiny `LlmTracer` interface (`src/adjudicator/tracer.ts`) with a single
  `record(generation)` method; `GeminiAdjudicator` calls it after each response, passing model / prompt /
  output / `usageMetadata` / latency. `selectAdjudicator()` injects a Langfuse-backed tracer when
  `LANGFUSE_*` env is present, else a **no-op** (so tests and local-without-Langfuse are untouched). This
  keeps `GeminiAdjudicator` ignorant of Langfuse specifically (depends only on `LlmTracer`).
- **Trace shape.** One Langfuse **trace per chain-adjudicate cycle**; each real LLM call is a
  **generation** (model, input, output, token usage, latency); cache hits are recorded as a cheap span
  tagged `cached=true` (no generation). Tag/metadata every generation with `content_hash`,
  `adjudicator_id`, `rulebook_version`, `input.kind` (notice|chain), and the pair's OCD-IDs so traces
  cross-reference the DB row and the logs.
- **Namespace: `langfuse`** (its own), keeping the CNPG cluster + app + secrets as one self-contained
  unit. (Grafana/Loki/Alloy stay in `observability`; cross-namespace is fine.)
- **No PII risk.** Adjudication inputs are public Federal Register notice text. The Gemini API key never
  enters a trace (it's an `x-goog-api-key` header, already kept out of logs).

## PR-C1 — Langfuse v2 platform deploy (infra, no app code)

Independently deployable; gives a running Langfuse UI before any app instrumentation exists.

1. **`infra/argocd/manifests/langfuse/`** — raw manifests: a CNPG `Cluster` (`langfuse-db`, 1 instance,
   ~256Mi, small PVC); a `Deployment` running `langfuse/langfuse:2` (env: `DATABASE_URL` from the CNPG
   `langfuse-db-app` secret; `NEXTAUTH_URL`, `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` from ESO;
   `TELEMETRY_ENABLED=false`); a `Service` (ClusterIP); the `langfuse-secrets` `ExternalSecret`
   (`vault-backend` → `secret/langfuse/*`). Pin resources (~512Mi limit for the Next.js server).
2. **`infra/argocd/apps/platform-langfuse.yaml`** — directory-type Argo app sourcing that dir from git
   (public repo, no creds), `CreateNamespace=true`, `ServerSideApply=true`, `selfHeal`+`prune`.
   Sync-waves: the CNPG `Cluster` depends on the CNPG operator (wave `"0"`) and the ESO secret depends on
   the `vault-backend` store (now wave `"1"`), so place this app at wave **`"2"`** (consumer tier, with
   grafana/docketclock). `task platform` already globs `platform-*.yaml`, so it auto-applies.
3. **`infra/scripts/vault-seed.sh`** — add a block seeding `secret/langfuse/*`
   (`nextauth_secret` / `salt` / `encryption_key`; dev defaults, override via `LANGFUSE_*` shell env),
   mirroring the existing `secret/observability/grafana` block.
4. **Taskfile / README** — a `task langfuse` port-forward (`svc/langfuse :3000 → localhost:3001`, to not
   collide with Grafana's 3000) + an Observability README subsection and a Troubleshooting note.
5. **Verify:** the Argo app + `langfuse-db` Cluster go `Synced/Healthy`; the Langfuse UI loads via
   port-forward; create the first project + API keys in the UI; `kubectl top nodes` still shows headroom.

## PR-C2 — Adjudicator instrumentation (app code)

1. **`src/adjudicator/tracer.ts`** — the `LlmTracer` interface + a `NoopTracer`. Shape (sketch):
   `record({ model, input, output, verdict, usage, latencyMs, contentHash, adjudicatorId, rulebookVersion,
kind, fromOcdId, toOcdId, cached }): void` and a `flush(): Promise<void>`.
2. **`src/adjudicator/langfuse-tracer.ts`** — a Langfuse-backed `LlmTracer` (the `langfuse` JS SDK),
   reading `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`. Creates a generation per real
   call; a `cached` span on hits. Exposes `flush()` (the poller is long-lived — flush per cycle and on
   shutdown; the SDK batches in the background otherwise).
3. **`gemini-adjudicator.ts`** — surface `usageMetadata` and per-call latency to an optional injected
   `LlmTracer` (default no-op). **The `adjudicate()` return type is unchanged** — the tracer is a side
   channel, so no contract change.
4. **`select.ts` / `consult.ts`** — `selectAdjudicator()` injects the Langfuse tracer when `LANGFUSE_*`
   is set, else `NoopTracer`. `consultAdjudicator()` records cache hits via the same tracer (so the trace
   shows hit-vs-call). Open a trace per cycle in `adjudicateAmbiguousPairs()` and `flush()` at cycle end,
   next to the existing `chain adjudicate cycle` log.
5. **`.env.example` + chart values** — document `LANGFUSE_HOST` (`http://langfuse.langfuse.svc:3000`),
   `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`; wire the two keys through the docketclock ExternalSecret.
6. **Verify:** `pnpm -r typecheck && pnpm -r test && pnpm lint` green **with no `LANGFUSE_*` set** (no-op
   path — existing tests unaffected); then with Langfuse running + `ADJUDICATOR=gemini`, a poll cycle
   produces traces in the UI with input/output/model/latency/tokens, tagged by `content_hash` +
   OCD-IDs, and cache hits show as cached spans.

   Workflow: builder (against this spec) → adversary (verify the no-op default truly inert; verify no key
   leaks into traces; verify flush-on-shutdown) → PR → pr-feedback → merge.

## PR-C3 — Eval-dataset seed from `adjudications` (script)

The `adjudications` table holds inputs + the model's _own_ past verdicts, but **no ground truth**. So
this PR seeds a Langfuse **dataset of representative inputs**, with the historical verdict attached as a
_provisional_ expected-output for a human to confirm/correct in Slice D — not as gold labels.

1. **`apps/docketclock/scripts/seed-langfuse-dataset.ts`** — read `adjudications`, dedupe by
   `content_hash`, **stratify** by `input.kind` (notice|chain) × `verdict.classification`
   (affirm|reject|uncertain) so the set isn't dominated by the common case; cap N per stratum. Push each
   as a Langfuse dataset item: `input` = the canonical `AdjudicationInput`, `expectedOutput` = the
   historical verdict (flagged `provisional`), `metadata` = `{ content_hash, adjudicator_id,
rulebook_version }`. Idempotent (keyed on `content_hash`).
2. **Verify:** the dataset appears in the Langfuse UI with the expected stratum counts; re-running is a
   no-op; a spot-check of items round-trips the input JSON.

## Out of scope (later slices)

- **Slice D — Evals:** human/gold labeling of the seeded dataset; a scoring run (Langfuse experiments
  and/or promptfoo) over the adjudicator; a CI regression gate on classification accuracy. D consumes
  C's dataset + traces.
- **Langfuse v3 upgrade** (ClickHouse/Redis/S3) — only if/when the cloud cluster lands and volume demands
  it; v2 is the deliberate lean choice for k3d.
- **Slice B — Metrics** (Prometheus/kube-state/node-exporter) — independent; heaviest on RAM; deferred.

## Rollback

- PR-C1: delete (or revert) `platform-langfuse.yaml` → the `langfuse` namespace prunes; nothing else
  depends on it. The `vault-seed` block and `secret/langfuse/*` are inert once unused.
- PR-C2: revert the merge → the injected tracer is gone; with no `LANGFUSE_*` env it was already a no-op,
  so the adjudicator path is byte-for-byte the prior behavior. Verdicts + the `adjudications` cache are
  unaffected (tracing never touched them).
- PR-C3: drop the Langfuse dataset in the UI; the script wrote nothing to our DB.
