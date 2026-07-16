# Review/Resolve Slice R — the human review path (`human_review` observations)

> Status: **Ready to build** — decisions locked, awaiting go on PR-R1.
> Follows Slice V (`plans/verification-accuracy.md`), which named this exact slice in its
> out-of-scope list ("candidate for its own small slice right after V1"). Gap #3 of the
> 2026-07 progress review (per the PR #103 body; #1 = README drift, #4 = drill cadence).
> Target: local k3d; no new platform services, no new RAM (a CLI + one contract bump + a
> reconciler rule + one gauge).

## Why this slice, why now

The system now detects wrongness end-to-end — CONFLICTING/STALE windows, chain ambiguity, accuracy
misses, xcheck disagreements — but the operator has **no durable write path to resolve anything**.
Concretely, today:

- A `confidence: conflicting` window stays conflicting until the sources happen to converge. There
  is no way to record "a human read both notices; the close is X" — the architecture's
  human-review console concept (corrections flow as `human_review` observations, preserving the
  audit chain) has zero code behind it: `ObservationSource` is three live sources, the DB CHECK
  (migration 0001) matches, and `grep -ri review apps/docketclock/src/` comes back empty.
- xcheck triage (`spikes/out/XCHECK_diff.md`) writes `our_bug` / `bulk_stale` / `source_drift`
  verdicts into a **markdown table** — human judgment about live data, recorded outside the
  audit chain the product sells. Closed-window misses flow to regression fixtures (V2); open-window
  findings have nowhere to go.
- The D5 design-partner promise depends on this loop: partner corrections become support tickets
  become `human_review` observations. Building the write path now (operator-only) is the substrate
  for that, minus the console.

## What exists today (the seams this slice hooks into)

- **The append-only observation log** — DB-trigger-enforced; `ingestObservation`
  (`apps/docketclock/src/ingest/observe.ts`) is the single write path with payload-hash idempotency. A human
  resolution can ride this exact machinery.
- **The pure reconciler** (`apps/docketclock/src/reconcile/reconcile.ts`,
  `RECONCILER_VERSION = reconcile-v1`) —
  derives a window from the observation chain for one ocd_id via latest-per-source; validates
  output against the frozen contract. A supersedence rule slots in as one more deterministic rule.
- **Contracts @ 0.9.0** — `ObservationSource` (3 live sources), `ConflictFlag` already carries a
  provenance-marker precedent (`llm_corroborated` rides alongside type flags), and the version-log
  discipline makes an additive 0.10.0 routine for the contract-keeper.
- **Conflict-dual-fire semantics** — suppression never means silence. A human resolution must not
  become a new silence path (see the supersedence rule below).
- **The alert path (V3)** — ntfy + Grafana provisioned rules; queue-staleness alerting reuses it.
- **Migration 0001's CHECK** — `source in ('federal_register','regulations_gov','govinfo')` must
  be widened in lockstep with the contract bump.

## Decisions locked

- **Resolution is an OBSERVATION, never a mutation.** `human_review` becomes a fourth
  `ObservationSource`; the verdict is the observation's `raw` payload; the append-only trigger
  applies unchanged. There is no admin UPDATE path and never will be — corrections accrete,
  exactly like source data, so the audit chain stays complete.
- **A typed verdict payload, not freeform JSON.** Contract 0.10.0 adds `HumanReviewVerdict` (the
  `raw` shape for `source: human_review`): `kind` (`pin_close` | `confirm_withdrawn` |
  `confirm_reopened` | `dismiss_conflict`), an optional pinned close date (required by
  `pin_close`, forbidden otherwise — superRefine), a **required** free-text `note` (the "why" is
  the point), `operator`, and `reviewed_payload_hashes` — the source observations the human
  actually looked at (≥1, superRefine). Field conventions for the Observation row: notice flags
  all false, `raw_dates_text`/document ids null, `parser_version: human-review-v1`.
- **Supersedence — the load-bearing rule: a human verdict is authoritative only while it has
  seen everything the machine has.** The reconciler honors the latest `human_review` observation
  iff no source observation for that window has `fetched_at` newer than it. The moment a newer
  source observation lands, the window returns to pure derivation — and if derivation disagrees
  again, the conflict RESURFACES. An outdated human verdict is never silently trusted, and a
  resolution never suppresses the dual-fire behavior: it changes what we assert, not what we
  watch. (Mirrors the whole-chain re-evaluation stance: never blind latest-wins, never sticky
  human-wins.)
- **Confidence stays deterministic.** A honored verdict sets the derived fields per its `kind`
  (e.g. `pin_close` → that close, confidence `high`) and stamps a new `human_resolved`
  provenance `ConflictFlag` (riding alongside other flags, the `llm_corroborated` pattern), so
  every consumer can see a human is in the loop. The rulebook remains a fixed rulebook — the
  human is an _input_ to versioned rules (`reconcile-v2`), not an override around them.
- **CLI-first, operator-only; the API stays read-only.** The interface is a `review` CLI in the
  app workspace (`pnpm --filter @yokel/docketclock review …`), host-side against the CNPG DB
  like the existing scripts/smokes. No API write route: delivery API keys must never be able to
  write observations. The Retool/web console stays deferred to D5 — this slice is its substrate.
- **Queue v1 = what already demands a human**: windows with confidence `conflicting` or `stale`,
  ordered by closing-soonest. xcheck `our_bug` rows on OPEN windows get resolved through the CLI
  (entering the audit chain) instead of dying in the markdown table; closed-window misses keep
  flowing the V2 fixture path. Chain-ambiguous pairs and dead-letter triage are explicit
  follow-ups, not v1 queue members.
- **The queue is enforced like the drills**: a depth gauge and an oldest-item-age alert through
  the existing ntfy path — an unworked queue pages, it doesn't rot.
- **No manual AccuracyRecords in this slice.** `AccuracyBasis` already reserves `manual`, but the
  verifier stays the only accuracy writer until a real case demands a manual verdict — resolving
  live windows and re-grading the track record are different powers, kept separate deliberately.

## PR-R1 — Contract 0.10.0 + migration (the seam)

Contract-keeper work: `ObservationSource` += `human_review`; `HumanReviewVerdict` with the
superRefines above; `ConflictFlag` += `human_resolved`; version-log entry. Migration 0011 widens
the 0001 CHECK in lockstep. Adversarial probes: verdict payloads that lie (pin without a date,
empty note, zero reviewed hashes) must not parse; the widened CHECK still rejects unknown sources.

**Verify:** `pnpm -r typecheck && pnpm -r test` green; migration applies via the migrate Job;
a hand-inserted `human_review` observation row round-trips `Observation.parse`.

## PR-R2 — Reconciler supersedence (pure engine)

`reconcile-v2`: honor-the-verdict rule with the freshness gate, per-kind derivation,
`human_resolved` flag emission, conflict-resurfacing on newer contradicting source observations.
Pure + injectable-`now` like everything else in the engine; regression tests for: honored pin,
un-pinned by a newer source observation (agreeing AND disagreeing variants), dual-fire preserved,
a second human verdict superseding the first, determinism (same chain in, same window out).

**Verify:** engine suite green incl. the adversarial variants; `eval:chain` unaffected (chain
classification never reads human_review rows).

## PR-R3 — The `review` CLI + runbook

`review queue` (the v1 queue, closing-soonest first), `review show <ocd-id>` (side-by-side
latest-per-source dates, chain links, conflict flags, prior human verdicts — what a reviewer needs
in one screen), `review resolve <ocd-id> --kind … --close … --note …` (writes through
`ingestObservation`, prints the re-derived window as confirmation). Runbook
`docs/runbooks/review-queue.md`: the weekly sweep, verdict-kind semantics, and the xcheck
integration note (`our_bug` on an open window → `review resolve`, so the triage table stops being
the system of record for live-data judgments).

**Verify:** end-to-end on the live cluster — resolve a real CONFLICTING window, watch confidence
flip with `human_resolved` set, then simulate a newer contradicting source observation and watch
the conflict resurface.

## PR-R4 — Queue observability

`docketclock_review_queue_depth{reason}` gauge computed per poll cycle (rides the existing metrics
conventions), a Grafana queue panel, and one provisioned alert: oldest unresolved queue
item > 7d → ntfy. `validate-argocd-apps.py` stays green.

**Verify:** gauge visible in Prometheus; stage a stale queue item (or lower the threshold) →
alert fires and resolves through the drilled path.

## Out of scope (later)

- **Web/Retool console** — D5-gated; the CLI is its substrate and its spec.
- **Partner-facing corrections** (support ticket → human_review) — needs tenancy; the observation
  shape built here is deliberately already the one that flow will write.
- **Manual AccuracyRecords / re-grading verdicts** — see decision above.
- **Chain-ambiguous pair triage + dead-letter replay tooling** — same CLI home, own follow-up.

## Rollback

- PR-R1: revert; contract minor bumps are additive, migration 0011 only widens a CHECK (existing
  rows unaffected either way).
- PR-R2: revert to `reconcile-v1` — human_review rows become inert data in the log (harmless,
  still auditable).
- PR-R3/R4: revert; no state beyond ordinary observations already governed by the log's
  append-only discipline.
