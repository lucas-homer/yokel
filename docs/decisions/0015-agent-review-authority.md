# 0015. An agent may write review verdicts under a written policy, with its authority visible

- Status: Accepted
- Date: 2026-10-19
- Amends: [0010](0010-review-evidence-freshness.md) (freshness applies to a fifth verdict kind);
  builds on [0014](0014-portal-close-echo-preserves-pin.md). Contract 0.11.0; `reconcile-v2.3`.
- Plan: `plans/review-autopilot.md` (PR-A2 of four).

## Context

Until now the only path by which anything other than the deterministic rulebook sets a HIGH close
has been a `human_review` verdict a person authorized. The 49 `pin_close` verdicts written by Codex
in September 2026 were each individually authorized by the operator through the guided review skill;
the agent typed the command, the human decided. The review queue grows faster than a weekly human
sweep clears it, and the plan is a scheduled agent that works it unsupervised in **shadow mode**
first and, once it meets the gate, writes verdicts under a written policy.

Letting an agent choose a published close unsupervised expands that authority, whatever CLI it goes
through. It must be stated rather than smuggled in under "the LLM never touches deadline resolution".
Three further gaps were measured while planning (plan findings 1–3): the "truly needs a human" class
(issue #127: an explicit published date, an explicit different portal cutoff, and no document that
explains the difference — about 6% of reviewed items) has no parking state, so it keeps the rot
alert firing and is re-investigated from scratch by every sweep; a verdict is written against
"whatever is live now" rather than the evidence the investigation actually assessed; and the stored
projection shows an agent under measurement the answer it is supposed to find.

## Decision

1. **Scope of the authority.** An agent may write `pin_close` and `confirm_withdrawn` verdicts only
   under the written policy in `plans/review-autopilot.md` ("The write policy (v1)"): a primary
   document that explicitly states the operative deadline for this exact notice, an explanation of
   the competing value, an independent verifier that returns the same date from the evidence card,
   and escalation taking precedence over every other kind. `dismiss_conflict` and `confirm_reopened`
   are not permitted to an agent in v1. The in-engine invariants are unchanged: confidence is never
   LLM-scored, there are no numeric scores, and the adjudicator stays advisory-only. The agent is an
   operator with a phone-pageable owner, not an in-cluster component.

2. **Provenance is honest and visible.** `HumanReviewVerdict.reviewer` records the **decision
   authority** — `"human"` (a person authorized this verdict, even if an agent executed it) or
   `"agent"` (an autopilot chose it unsupervised) — while `operator` keeps naming the executor. The
   field defaults to `"human"`, so every pre-0.11.0 row, including the 49 Codex pins, parses to the
   meaning it always had. The reconciler stamps `agent_resolved` instead of `human_resolved` when
   the honored verdict's reviewer is `"agent"`; exactly one of the two rides on an honored
   non-escalate verdict, with the same composition and freshness rules as before.

3. **Escalation is an observation that asserts nothing.** New kind `escalate`: "primary sources
   examined (hashes recorded); the discrepancy cannot be resolved from documents; a human decision
   or agency clarification is needed." It carries a note saying what was searched, and the reviewed
   hashes, and it is forbidden a date like every non-pin kind. The reconciler derives **byte-for-
   byte** what it would without it: no provenance flag, no observation id in
   `current_observation_ids`, no change to close, confidence or status, and the live
   `ConflictRecord` stays live — suppression is never silence. It is honored for **freshness only**:
   while nothing newer than it changes the evidence (the ADR 0010 metadata exception applies, as for
   every kind), the item is **parked** — `review queue` marks it `[escalated by … ]`, `review show`
   reports it honored and parked, the autopilot skips it, and the `escalated` series of the
   queue-depth gauge counts it. Invalidating evidence un-parks it (the item is then an ordinary
   queue member again); a later verdict of any kind supersedes it. The ADR 0014 echo exception is
   **not** extended to `escalate` (its clause 1 is `pin_close`-only): the portal flipping to closed
   after its own announced date un-parks an open escalated item once. That is a deliberate
   re-inspection, not a defect; if shadow runs show it causing churn, extending the exception is a
   one-clause follow-up decision, recorded here rather than silently assumed.

4. **Writes are bound to assessed evidence.** `review resolve --expect <hash>…` names the
   latest-per-source payload hashes the investigation (and its verifier) assessed. The write runs in
   one transaction: read the live set, refuse if it differs from `--expect`, insert, re-read the live
   set, and refuse (rolling the insert back) if it moved. Automation never writes without
   `--expect`; a human may omit it and gets the pre-A2 behaviour. The refusal message lists which
   assessed hashes are no longer latest and which latest hashes were not assessed.

5. **The honoring decision is the engine's, shared.** `selectHonoredVerdict` is exported from the
   reconciler and used by `review show`, `review queue`, the queue statistics and the post-write
   check, so "honored" has one definition. The CLI's "verdict NOT honored" warning keys on that
   rule, not on the presence of a flag — an honored `escalate` leaves no flag.

6. **An agent under measurement cannot read the answer.** `review show --blind` hides every prior
   verdict and shows the machine's own in-memory derivation of the source chain (nothing persisted,
   no retirement history leaked). The shadow gate (plan, "Reliability") runs on it.

7. **Humans are paged through the existing alert path.** `docketclock_review_queue_depth{reason=
"escalated"}` is the parked subset of the queue; it overlaps `conflicting`/`stale` and is read
   per series, never summed across reasons. One provisioned Grafana rule, `review-queue-escalated`
   (`> 0`, `for: 1h`, `cadence=daily`, receiver ntfy) nags daily until every parked item is
   superseded. The rot alert is unchanged and keeps ageing parked items by design.

8. **Versioning.** Contract 0.11.0 is additive (no migration: raw is JSONB, the 0011 source CHECK is
   unaffected). The reconciler is stamped `reconcile-v2.3`: every existing row derives identically
   (no `escalate` or `reviewer=agent` rows exist yet), so the post-deploy sweep is expected to
   change nothing — the stamp records which code last derived each row, as 0014 did.

## Consequences

- No verdict is written by an agent until the shadow gate in the plan is met and the operator flips
  the autopilot prompt to write mode (PR-A3). This ADR grants the authority and makes it visible; the
  plan's gate and policy govern its use. The kill switch is pausing the scheduled task; a bad agent
  verdict is corrected by a superseding human verdict, never an edit.
- Consumers that key on `human_resolved` to mean "a person is in the loop" keep that meaning
  exactly; `agent_resolved` is a new, distinct signal.
- Rollout: deploy via git → Argo CD for the platform tier (the Grafana rule) and the app's usual
  path for the poller/API image, then run the `rederive-stale-windows.ts` sweep (expected: every
  window re-stamped, no derivation change). Then the live round-trip from the plan's verify list:
  one #127 item escalated through the CLI with `--expect`, visible in `queue`, counted by the gauge,
  and the alert fires and resolves through the drilled path.
- Rollback: order matters. Pause the autopilot **before** reverting the provenance-aware reconciler,
  because a pre-0.11.0 reconciler parses an agent pin (the unknown `reviewer` key is stripped) and
  stamps it `human_resolved`. If agent pins already exist, keep the provenance-aware reconciler or
  supersede those pins by hand rather than reverting. `escalate` rows become inert log data under an
  older reconciler (unknown kind → pure derivation).
- Verification (this PR): contract probes (escalate with a date fails; reviewer defaults to human on
  the legacy shape; a third reviewer value fails; `agent_resolved` parses with HIGH); engine tests
  (escalate preserves window and ConflictRecord byte-for-byte; parked through a metadata refresh;
  un-parked by newer FR, by a Regs date change and by the close flip, with the equal-date pin as the
  control; `agent_resolved` on an agent pin and an agent dismiss; legacy and explicit-human pins
  identical; supersedence in both directions; a malformed escalate is ignored); DB tests (`--expect`
  stale, subset and empty sets refuse and write nothing; the escalate round-trip through write →
  reconcile → queue mark → stats → show → blind → un-park; agent pin persisted with `agent_resolved`;
  a human pin supersedes it with `human_resolved`); the Argo manifest validator over the new rule.
