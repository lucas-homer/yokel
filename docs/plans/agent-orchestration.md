# Agent Orchestration — building DocketClock with agent teams

> How we use agent teams to build DocketClock *efficiently and thoroughly*. The org chart deliberately
> mirrors the architecture's trust invariants — that is what makes it thorough, not just parallel.

## Governing principle

Two of DocketClock's structural rules become orchestration rules:

- **"The Observation log is primary; the window is a derived projection, never silently mutated"**
  → **builders never mutate the contract.** A schema change routes through the one contract-keeper as
  a request — exactly like deadline corrections routing as `human_review` observations instead of
  direct window edits.
- **"Don't publish fake certainty"** → **nothing merges until a standalone adversary has tried to
  break it.** Verification is structural, not a final polish step.

You parallelize *behind* the seam, never across it. The contract barrier and serial merges cost some
serialization, but they prevent the `frDocNum`-vs-`fr_doc_num` field-casing divergence that would
otherwise force a rework pass across every adapter. Efficiency comes from fan-out *within* a phase.

## The team (`.claude/agents/`)

| Role | Owns | Cannot do | Tools |
| --- | --- | --- | --- |
| **contract-keeper** | `packages/contracts` — Zod schemas, OCD-ID scheme, confidence/conflict enums; freezes + versions | — | Read-all, Write contracts |
| **builder** | one component, TDD-first, in its own worktree | edit the contract (files a change-request instead) | full, scoped |
| **adversary** | the spike-derived regression suite; tries to make `confidence` lie | write impl code (tests only) | Read, Bash, Write tests |
| **integrator** | the only agent touching live state — migrations, live APIs, Postgres, serial merges | reconcile schema (routes to keeper) | full + Bash |

The contract-keeper is the serialization point. The adversary is **standalone** because buyers carry
deadline liability — a dedicated default-to-reject role guarding the documented edge cases
(FR-2018-27875, BLM 2023-27468, EPA 2025-02910, FR 2025-03547) is the harness expressing the
product's own thesis. (Optional future role — **scribe**: keeps ADRs/AGENTS.md/this memo in sync.)

## Phase → orchestration shape

| Phase (build sequence) | Shape | Notes |
| --- | --- | --- |
| **0 Contract** | **Barrier** — one keeper + adversary review | nothing fans out until schemas are frozen |
| **1 Spine** (Wk 2-3) | **parallel worktree builders** (DB+trigger, FR adapter, Regs adapter w/ 6h cursor, ingestion, OCD-ID) → adversary verify → integrator merge | different files, true fan-out |
| **2 Reconciliation** (Wk 4-5) | **pipeline**: builder writes a rule → adversary breaks it vs spicy-regs, loop-until-dry on edge cases | crown jewel; reuses the `spikes/src` DuckDB harness as the regression backbone |
| **3 Public API** (Wk 6-7) | **parallel route builders** consuming frozen Zod→OpenAPI; webhook outbox a separate track | the contract *is* the spec |
| **4-6 Review/proof/convert** | mostly serial + "every `was_correct=false` becomes a test" | low fan-out |

**Workflow vs Agent:** a *phase* is one `Workflow` script (deterministic fan-out + verify + merge) —
the orchestrator stays in the loop between phases. A *single component* is a plain `Agent`. Worktree
isolation is only for the parallel builder phases (they mutate files concurrently).

## The gating governor

D5 (buyer demand) is still **0/5**, and the Week-1 memo says it gates *heavy* investment. So the
harness caps itself:

- **Phases 0–2 run now** — contract + spine + reconciliation are cheap, reversible, technical
  de-risking. The substrate BUILD decision (D1 green) already authorizes them.
- **Phase 3+ holds for D5** — we do not build the customer-facing sales surface (public API hardening,
  onboarding) before a confirmed buyer.
- **Side quests:** D3 precision labeling (agent-assisted, human adjudicates) and the D4 GSA
  rate-increase request are cheap and run alongside.

## Where it lives

- `.claude/agents/*.md` — the team.
- `.claude/workflows/*` — phase scripts, authored as each phase is reached.
- This doc — the durable design.
