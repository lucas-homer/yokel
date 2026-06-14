# 0001. Record architecture decisions

- Status: Accepted
- Date: 2026-06-14

## Context

Yokel's direction was shaped by a lot of reasoning (prior-art research, a multi-agent idea foundry,
an architecture foundry). The "why" behind big calls is easy to lose, especially as the project
opens to contributors and moves between machines.

## Decision

Use lightweight ADRs (this format: Status, Date, Context, Decision, Consequences), one file per
decision, numbered sequentially in `docs/decisions/`. ADRs are the **committed** memory; the
machine-local Claude memory (`~/.claude/...`) is just a pointer to them. Add an ADR for any
consequential, hard-to-reverse, or surprising decision.

## Consequences

- Contributors (and future-us on another machine) can reconstruct intent without re-deriving it.
- Superseded decisions are marked, not deleted, so the history stays legible.
