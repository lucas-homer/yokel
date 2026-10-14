# Amendment A1: P5 fixture gate in batched sessions

- **Status:** approved by the user ("Amend to batches. Each adjudicator answers the packets in about 7 fresh sessions of 10, so about 14 sessions total. Fable and Opus stay independent, and paid scoring keeps its one-fresh-session-per-output rule.")
- **Date:** 2026-10-13
- **Amends:** frozen protocol r3.1 (`../../design-r3-1/`, pinned by `READY.primary.json`). The frozen files are not edited. This amendment is read alongside PROTOCOL P5 and ADJUDICATION-SPEC C4.4.
- **Check:** `python3 -I -S -B gate_batched.py --adjudications DIR` replaces `check.py --adjudications DIR` for P5. The self-tests are in `test_gate_batched.py`.

## What changes

Only the P5 fixture-gate session rule (C4.4: "one fresh session per packet … a session id used nowhere else") changes.

**Batches.** The gold packet ids are sorted and split into consecutive batches of 10; the last batch may be smaller. Both roles use the same partition. With 70 gold packets, that gives **7 batches of 10**. `gate_batched.py` derives the partition from the frozen `cases.json` and writes it to `BATCHES.json`, which binds each packet file in `../../gate/packets/` by SHA-256. The primary dispatches from `BATCHES.json`.

**One session per (role, batch).** Each role answers each batch in **one** fresh session, so there are **14 sessions** in total (7 per role). The session receives that batch's 10 packets unchanged. Each packet still carries Part A and its own `part_a_sha256`, and the session writes one Part A4 answer object per packet to `<role>/<packet id>.json`. The dispatch prompt tells the adjudicator to apply Part A to each packet on its own. Part A's text is unchanged; its "you receive one packet" is read as "each packet is answered independently". All answers in a batch carry the same session id.

**Session constraints** (checked by `gate_batched.py`):

- A session id is used for exactly one (role, batch). It cannot be reused in another batch, in the other role, or by any reference author or reviewer session (`--excluded-sessions FILE`, a JSON list).
- A file whose session id differs from its batch's session fails. The batch's session is the one most of its files carry.
- Answering one packet per session, as the unamended rule required, is **not** accepted by this gate, because those files do not form batches. It still passes the frozen `check.py --adjudications`.
- Sessions stay blind exactly as Part A A1 requires: a fresh session with no other context, no other files, outputs, adjudicators' answers or scores. A batch session sees **only its own 10 packets**: not other batches, not the other role's answers and not `BATCHES.json` beyond its own entry.
- On a C4.5 rerun, both roles answer every batch again in 14 new sessions. Pass the previous round's gate sessions in `--excluded-sessions` so that reuse is caught.

## What does NOT change

- **Paid scoring.** `decide`, C1 (one fresh session per scored output per role, unique across all scored outputs and both roles, and not in `excluded_sessions`) and the C5 manifest are unchanged. Gate sessions are never reused for paid outputs, because C1 freshness already forbids it.
- **The gold comparison.** Every file must still carry the right role, the pinned model (A1 `claude-fable-5-1`, A2 `claude-opus-5-5`) and effort `high`, and must echo `call_id`/`source_id`/`output_sha256`/`reference_sha256`. Its mapping must equal gold exactly on **(target, unit, form)**; `basis` and notes are never compared. There must be exactly `DIR/A1` and `DIR/A2`, each with one file per gold packet. `gate_batched.py` runs the frozen `check.py` `adjudicator_gate` for all of this. It imports the file by path after verifying the SHA-256 pins, and changes only the session-uniqueness input.
- **All other P-steps**, the fixtures, the packets, Part A, the scorer and the C4.5 correction and escalation rule. The frozen scorer checks (`check.py` exit 0) still run, and `gate_batched.py` runs them too.

## Rationale

Per-packet sessions guard against **cross-packet contamination within one role**: an earlier packet's mapping could prime a later one. The packets are fictional fixtures that each carry their own source, reference and output, so this risk is minor. In particular, no answer can be copied across packets: every packet has its own targets and units, and the mapping is checked against that packet's gold.

What the gate actually tests is that **two independent adjudicators** can each reproduce gold from Part A alone. That independence is fully kept: A1 and A2 never share a session, a batch or each other's answers, and the gate rejects a session shared across roles.

**Cost.** Without the amendment, each role answers 70 packets in 70 sessions, which is 140 fresh sessions for a gate on a 6-call experiment. With it, there are 14 sessions, ten times fewer. The packet content read per role is the same (70 packets, about 454 KB). What is saved is 126 sets of per-session overhead: harness and system context, cold start, dispatch, and the primary collecting results. A batch session holds about 65 KB of packets plus 10 answers, well within one session's context.

## Residual risk

- **Within-batch carryover.** Earlier packets in a session can shape how later ones are mapped. That could make agreement with gold easier (a pattern learned on packet 1 reused correctly on packet 7) or harder (a misreading repeated through the batch). The gate cannot tell these apart from independent per-packet judgement. It is accepted because both directions are bounded by the exact per-packet gold comparison: carryover can only pass a packet whose answer is exactly gold.
- **All-or-nothing batches.** One broken session (a crash, truncation or wrong identity) puts all 10 of its packets in doubt. Under C4.5, any failure reruns the whole gate in new sessions anyway, so batching adds no new failure path. A single bad session simply costs more packets.
- **The order inside a batch is fixed** (sorted packet ids), so any position effect is the same for A1 and A2 and is not randomised.
