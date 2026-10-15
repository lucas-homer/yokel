# R17 protocol review, round 4 — focused r3.1 diff check

**Verdict: freeze.** No new BLOCKER or SHOULD-FIX attributable to this diff was reproduced. This is protocol-freeze approval, not paid-release approval. RELEASE_POLICY remains the user's decision.

## Per-item disposition

| Round-3 item | Status | Reproduced evidence |
|---|---|---|
| R3-B1 — hidden confident AND→OR duplicate | **FIXED** | Original attack now yields a critical compound swap and **O1**, including after frozen r16.w2.1 wire validation of all six outputs. |
| R3-B2 — opposite + regardless | **FIXED** | Reversed target yields inversion; the six-cell record is rejected for FULL without an OPQ pass, including after wire validation. Stopping after OPQ1 yields **O3**. |
| R3-S1 — UNSET admission | **FIXED** | UNSET, missing/null and unknown policy refuse admission. Both allowed values with matching BIND_RELEASE admit; L22 checks disagreement. Policy-evidence acceptance remains the separate P7 human/release-gate requirement. |
| R3-S2 — freshness and frozen OPQ binding | **PARTIAL overall; freshness FIXED** | Reused sessions and listed reference sessions are rejected; A16–A18 also cover cross-role reuse. OPQ adjudication hash enforcement remains explicitly deferred to the adapter/run record in §14. Safe to defer implementation until that release prerequisite is satisfied; it is not implemented by today's `decide`. |
| R3-S3 — regression between polling reads | **FIXED** | $0.15 → $0.14 → $0.16 now HALTs on regression; the monotone control passes. |

Round-3 NOTES: adoption-scope language is present; opposite plus uncertain `qual` now yields contradiction; post-halt release is rejected (final and interim fixtures); partition/source-only review remains unchanged.

## Focused regression checks

- **Faithful duplicates:** two correct typed copies remain correct with no invented operators, in either link order. Duplicating every fully faithful FULL gold case tested **12 cases**, including nested structures, without typed harm or invented operators.
- **Hedged alternatives:** correct-first plus a link-hedged OR, node-hedged OR, or ALT remains correct with no invented operators. Reversing the order exposes an existing best-witness limitation: hedged OR first scores swap, ALT first scores hedged. I reproduced the same results against frozen r3. Thus this is **not introduced by this diff**, and is not a new finding in this focused round. Do not infer order-independent hedge handling from F15i.
- **Form-aware regardless:** direct forms with zero through three NOT wrappers remain relation-correct; inverse/opposite forms yield inversion at all four depths. Unsupported NOT can still be inventoried as invented, as in F19e; that behavior is unchanged. No new direct-form misfire was reproduced.

## NOTE — deferred OPQ binding must remain a release prerequisite

The hashes cannot exist before OPQ adjudication, so they should not be inserted into the already-bound pre-OPQ C6 release record. §6 C1, §10 and §14 together require freezing them before FULL and retaining the binding in the run record. That is sufficient for **design freeze**, with implementation still outstanding.

**Suggested implementation edit:** use a separate immutable OPQ-freeze record containing all six OPQ adjudication-file hashes and the OPQ decision, bound to the static release/manifest. Check it before every FULL dispatch and against the files used by final decision assembly. Add changed-file and missing-freeze rejection tests before P3/P7 sign-off. Merely recording fresh hashes after FULL would not satisfy the existing pre-FULL freeze requirement. This note tracks the acknowledged R3-S2 remainder; it is not a new blocker.

## Verification and boundaries

- Read the complete `diff -ru design-r3 design-r3-1`, excluding READY files. Local diff snapshot: `diff.txt`.
- `probe.py` is the round-3 probe with **only** its DESIGN import/data path changed to r3.1. Running it stops at its old assertion that the hidden duplicate scores correct; that expected failure confirms the behavior changed. Log: `original-probe.log`.
- `focused.py` loads the original attack-construction functions from that copy and observes repaired behavior independently. It adds the required v2 `excluded_sessions` envelope field outside the copy and matching policy fields for admission controls. It does not weaken the attacks. All focused and six-output wire assertions pass; log: `focused.log`.
- Re-ran `design-r3-1/fixtures/check.py`: **0 failures**, 71 scorer cases / 70 gold, 25 ledger checks, 23 assembly runs, 15 decision checks, 9 invalid references, 9 reference examples, 10 gate self-tests. Actual adjudicator gate remains unrun (P5).
- All Python ran as `python3 -I -S -B`. No network/provider calls, credentials, source bodies, installs or commits. Only this review directory was written.
