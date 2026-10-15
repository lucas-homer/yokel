# R7 independent specification review

**Disposition: approve for bounded offline implementation; no blocking specification changes.** Primary retains the implementation-start decision. This does not approve an implementation, live calls, collection or production use.

Reviewed 2026-10-09: `round7/SPEC.md`, SHA-256 `cfc6e8847637c3333fcd994649a6349471585d2fd5efb54952b6d75014324406`. Review used [CHECKLIST.md](CHECKLIST.md), the frozen R6 pipeline/runtime/evaluator and retained failure/independent-audit evidence. Line references below are to that exact spec version.

| Checklist | Sufficient contract in spec |
| --- | --- |
| B1 frozen lineage | Lines 13–15, 57, 70–71, 77: R7-only ownership and versions, explicit old-version rejection, authored migrations with provenance, historical replay and byte comparison. |
| B2 exact evidence | Lines 21, 25–27, 43, 63–65: exact literals/selectors/spans retained, no arbitrary display, whole-record failure and separate semantic association. Existing exact-evidence mechanics are inherited; no relaxation authorized. |
| B3 dates | Lines 21, 61–62: bounded weekday grammar, explicit Gregorian consistency rejection and no missing-year/timezone inference. |
| B4 components/display | Lines 25–27, 63–65: globally unique component IDs, component and route evidence, audited description, optional deterministic derived view and tamper rejection. Omission of a display feature is permitted and does not require a new rendering subsystem. |
| B5 alternatives | Lines 31–33, 66–67: explicit group/role-purpose contract, reciprocal references, scope and qualification preservation, uncertainty and semantic checks for unproven alternatives. |
| B6 disclosure/completeness | Lines 37–39, 68–69: preserve typing/modality and full ancillary universe; independent mapping must expose omissions/classification failures even if assembly succeeds. |
| B7 size routing | Lines 43–45, 72: unchanged caps/reservation, final request-body receipts, zero dispatch on admission failure, explicit permission for KY to remain rejected. No cap increase, clipping, chunking or new transport optimization required. |
| B8 compatibility | Lines 15, 25, 33, 45, 51, 73: new IDs covered by verifier assessment/aggregate accounting, five dimensions retained, canonical paired evidence and identity checks, adapter/evaluator integration. |
| B9 actual arm state | Lines 49–53, 74–75: explicit called/uncalled status, system gates distinct from arm judgments, preserved real hashes, missing rows and partial dispatch handled honestly. |
| B10 acceptance/reporting | Lines 39, 51–53, 65, 69, 73–75: structural/semantic/accepted-useful distinctions, unresolved-state veto, independent mapping, retained denominator and null zero-acceptance ratios. |
| B11 development only | Lines 3, 57, 70–71, 77, 81–83: offline synthetic controls and observed-source replays are development evidence only; future live evaluation needs a new freeze and unseen labeled cohort. |

## Nonblocking implementation review notes

- Test the inherited exact-selector controls as well as the new components, and ensure `all_items`/reference checks/stronger-verdict coverage include every component and group. The spec already requires this; it needs implementation evidence rather than another design layer.
- In the stated below/at/over-limit request matrix, exercise Jev's total-request and state-plus-longest-probe caps independently, plus inventory/stronger reservations. A retained rejection is a passing routing control when that is the expected outcome.
- Make the chosen cross-event equality/binding rule and gate/status consistency table explicit in the interface/tests. Concrete local validation rules suffice; no new research architecture is requested.

No implementation checks were run in this review. The reviewed spec hash matched the supplied hash. Only `round7/review/` was written; no provider/credential/production actions occurred. Implementation review should verify the matrix and prior-round integrity before declaring completion.
