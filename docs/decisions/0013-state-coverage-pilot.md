# 0013. Build a bounded state-coverage pilot ahead of a paying customer

- Status: Accepted
- Date: 2026-10-15 (proposed 2026-10-14)
- Amends: [0003](0003-docketclock-substrate-first.md), only its federal-only rule

## Context

ADR 0003 made federal-only a hard rule until a paying customer funds a jurisdiction tranche. The
reasoning was that the net-new federal value is reconciliation, not discovery, and that states
have no normalized rulemaking API.

Our product hypothesis is that this gap is the opportunity. We believe nobody reliably covers
state comment periods and hearings because every state publishes differently. Evidenced state
coverage would then be DocketClock's main differentiator, and waiting for a customer to fund it
gets the order backwards. We have not run a competitive audit.

Prior state research (`docs/research/state-coverage-plan/INVENTORY.md`) produced reusable parsing
candidates, fixtures and two guarded adapters. It did not validate discovery completeness, notice
volume, update detection, date-role extraction at scale, review load or cost per state.

## Decision

Make an exception to the federal-only rule for a **bounded pilot**, run under
`docs/plans/state-coverage.md`:

- **Research:** allowed on the five named candidates, WA, CT, VA, MA and TN.
- **Production eligibility:** at most **4** selected pilot states. A state that is stopped may be
  replaced once, and the replacement counts against the limit of 4. Anything beyond that needs a
  new decision.
- **Scope:** rulemaking participation opportunities. That means written-comment windows,
  hearings, hearing-request windows and their lifecycle events, with dates and evidence.
  Who-is-affected conditions are excluded. A state whose declared coverage is narrower than
  statewide is labelled as narrower.
- **Contract:** state support enters `packages/contracts` as versioned additions. Federal schemas,
  source meanings, IDs, UTC semantics and API defaults are unchanged.
- **Publication:** state data becomes public only after the state passes its Phase 3/4 acceptance
  gate **and** the Phase 5 release checklist. Until then, a release boundary that denies by
  default keeps it off every public surface.

All of ADR 0003's other rules stand unchanged:
- the append-only observation log;
- federal conflict comparison in **America/New_York**;
- alert suppression that always fires a notification.

State date comparison follows source- and process-specific temporal policies defined in the state
contract. It never assumes Eastern time.

## Consequences

- Engineering time goes to state coverage before revenue. The plan's gates and per-state budgets
  are the stopping mechanism.
- On acceptance, update `AGENTS.md` and the canonical architecture through its generator, or an
  explicit override note, so builders don't get contradictory federal-only instructions.
- Expanding beyond the pilot needs a new ADR, informed by the Phase 5 scale memo.
