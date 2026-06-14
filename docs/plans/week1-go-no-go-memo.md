# Week-1 Validation — Go / No-Go Memo

**Date:** 2026-06-14 · **Status:** code spikes complete (D1–D3, W1–W3); non-code tasks (D4/D5, W4–W6) pending.
**Method:** all numbers are measured against live APIs on 2026-06-14. See `spikes/` for runnable harness and
`spikes/out/*.md` for per-spike artifacts. A measured "no" this week is a success.

---

```
WEEK-1 VALIDATION RESULTS — 2026-06-14

TRACK D — DocketClock
 D1 frDocNum hit-rate ......... 78.7%  → GO frDocNum-primary
 D2 Eastern-date conflict rate. 1.29%  → story = reliable-alerts (conflicts secondary)
    tz false-positives seen? ... YES (920)  → CONFIRMS Eastern rule is load-bearing
 D3 extension movers/day ...... ≤3.3 (proj.)  precision = PENDING (label the 50-row sheet)
                                → review console = 20-min chore (not staffed)
 D4 differential polling fits budget? LIKELY (open set ~1.2k docs ≪ 1,000/hr)  GSA ticket: NOT FILED  ETA: —
 D5 buyer interviews: 0/5 (not run)              SLA expectation: —
 ──> SUBSTRATE DECISION: BUILD

TRACK W — Watershed Watch  (run? yes — code gates only)
 W1 POST /comments open to non-gov? NO  → action loop = draft+copy-paste
 W2 EPA EIS machine-readable? scraper (HTML/JSF)  fragility: HIGH (mitigated by keyless FR EIS spine)
 W3 novel in-basin windows/qtr: ~4  (EIS ~1.25 / Regs ~2.75) → GO (provisional — upper bound, label to confirm)
 W4 geo-recall on 50: — (not run)  partner labels committed? — (needs partner)
 W5 §404 pattern: — (not run)  → —
 W6 partner: Tier-1 alone worth a paid seat? — (not run)
 ──> WEDGE DECISION: DEFER the commit — no red light from code; gated on W3 labeling + partner (W4/W6)
```

---

## Track D — DocketClock (substrate)

### D1 — frDocNum join hit-rate ⟵ MASTER GATE → **GO**
- **78.7%** of open-comment Regs.gov docs (932 / 1,184) join to a Federal Register document on
  `frDocNum = document_number`. Among the docs that actually carry a `frDocNum`, the rate is **94.4%**.
- Misses are mostly stale, perpetually-open dockets with **no `frDocNum` at all** (197 of 252) — not a
  key-quality problem. A docket-array fallback against the *full* FR corpus (not just the open window)
  would recover more; measured combined floor here is 78.8%.
- **Decision:** ≥60% → **GO with `frDocNum` as the primary reconciliation key.** No pivot needed.
- Artifact: `spikes/out/D1_join_rate.md`.

### D2 — Eastern-date conflict rate → **reliable-alerts story; Eastern rule CONFIRMED**
- A **naive UTC** comparison flags **100%** (932/932) of joined pairs as conflicts — because Regs.gov
  stores comment-close as end-of-day Eastern expressed in UTC (`…T03:59:59Z`), one calendar day ahead.
- After America/New_York normalization, only **1.29%** (12) are real conflicts; **920** were pure
  timezone noise the rule suppresses (one example even crosses a year boundary).
- **tz false-positives = 920 > 0 → the Eastern-normalization rule is load-bearing**, exactly as the
  architecture foundry flagged. Without it the product would cry wolf on every record.
- **Positioning:** 1.29% is in the borderline 1–3% band → **lead with reliable alerts + audit log;**
  keep `/conflicts` as a real but secondary feature, not the marquee. The 12 true conflicts await a
  human eyeball (mostly weeks-apart ITC review deadlines — genuine, not parse bugs).
- Artifact: `spikes/out/D2_conflict_rate.md`.

### D3 — extension/correction volume & deny-list precision → **20-min chore**
- 90-day Federal Register window: 6,666 docs → **427 keyword candidates (4.7/day)** on the plan's
  `(extension|reopen|correction|withdraw)` title detector.
- Heuristics flag ~209 as likely false positives — **PRA/info-collection extensions (96)**, **editorial
  corrections (63)**, and the named **BLM land-withdrawal trap (3)**, isolated as predicted.
- **Volume verdict:** even at 0.7 precision the projection is **3.3 genuine movers/day** (2.4 at 0.5,
  1.4 at 0.3) — far under the ~15/day staffed-line threshold. **The review console is a 20-min/day
  chore, not a staffing line**, regardless of precision.
- **Open item:** *precision itself* (deny-list-is-enough vs LLM-classifier-load-bearing) needs the
  50-row sample hand-labeled. The heavy PRA/correction noise foreshadows precision **below 0.7**, which
  would make the LLM chain-classifier load-bearing from day 1 — but the daily volume is low either way.
- Artifact: `spikes/out/D3_extension_volume.md` (+ 50-row sheet to label).

### D4 / D5 — not run (action + interviews)
- **D4** (GSA rate-increase request) is an *action*, not a measurement — **not yet filed.** On paper,
  differential polling fits the 1,000/hr budget at MVP volume (open set ≈ 1,184 docs). File the request
  for scale/backfill insurance and record the ticket + ETA.
- **D5** (3–5 buyer interviews) — **not run.** Demand signal still unconfirmed.

### → SUBSTRATE DECISION: **BUILD**
The three gates that govern the substrate build are green: the join holds (D1), the Eastern rule is
validated (D2), and the human-review burden is light (D3). D4 is insurance, D5 is demand validation —
neither blocks starting substrate work, but D5 should land before heavy investment.

---

## Track W — Watershed Watch (vertical)

### W1 — POST /comments availability ⟵ KILL-SHOT → **gov-only; draft + copy-paste**
- Non-destructive probes with a standard (non-gov) key: `POST /submission-keys` → **201**,
  `GET /comments` → **200**, but `POST /comments` → **403 `API_KEY_UNAUTHORIZED`**.
- Read works and a submission key mints, but **posting a comment is denied at the service level** — a
  tier gate, not a bad key. Confirms the post-2025 closure of automated submission to non-gov keys.
- **Decision:** the "Act" step is **guided draft + copy-paste + link-out**, with an honest "filed by
  member (self-reported)" receipt — *not* one-click filing. Build the composer either way; a future
  GSA-authorized/gov tier could flip this to first-class.
- Artifact: `spikes/out/W1_comment_post.md`.

### W2 — EPA EIS machine-readability → **scraper-only; ship behind an interface**
- EPA's EIS search app (cdxapps) returns **HTML** (a JSF web app); guessed REST/JSON backends 404;
  Envirofacts has no EIS table. **EPA's own EIS database is scraper-only.**
- The **Federal Register EIS-notice stream is the keyless machine-readable spine** (51 notices in the
  last month — title/link/date direct; comment-close, state, and draft/final stage partial via title
  parsing).
- **Decision:** **GO with guardrails** — implement an `EisSource` interface so the EPA scraper and the
  FR spine are swappable and cross-checked; budget scraper maintenance; treat EPA DOM changes as
  expected breakage with FR as the always-on fallback.
- Artifact: `spikes/out/W2_eis_source.md`.

### W3 — in-basin value density ⟵ BUSINESS KILL-SHOT → **GO (provisional)**
- Choptank HUC-8 `02060005` (DE/MD), last 4 quarters: **~16 candidate in-basin Tier-1 windows
  (~4/quarter)**, **31% EIS share** (5 EIS / 11 Regs.gov rulemaking).
- These are **upper-bound candidates** from FR full-text basin search — the sheet already shows the
  expected false positives (national rules that merely name "Chesapeake Bay"). The plan's number is
  *novel* in-basin windows, which requires the candidate sheet to be hand-labeled.
- **Decision:** above the ~2–3/quarter death line **with a real EIS share → provisional GO**, pending
  manual labeling to convert candidates to confirmed-novel windows.
- Artifact: `spikes/out/W3_value_density.md` (+ candidate sheet to label).

### W4 / W5 / W6 — not run (partner-dependent)
- **W4** (geo-recall on a 50-row labeled set), **W5** (USACE §404 ingestion pattern), and **W6** (partner
  confirms Tier-1-alone is worth a paid seat) all require the Chesapeake design partner and were not run.

### → WEDGE DECISION: **DEFER the commit — no red light, gated on labeling + partner**
None of the code gates read red: the action loop has a viable fallback (W1), the EIS source is
ingestible with guardrails (W2), and in-basin signal is provisionally sufficient (W3). But the
*business* go/no-go can't be finalized until **W3 is hand-labeled** and the **partner gates (W4/W6)**
are answered. Recommend: finish W3 labeling, then run the partner conversations before committing to a
pilot.

---

## The single most important line
**D1 (does the join hold?) → green. W3 (is there enough in-basin signal?) → provisional green.**
Neither master gate reads red. Substrate: **BUILD now.** Wedge: **proceed to partner validation** with
the two known forks baked in (draft+copy-paste filing; scraper-behind-interface EIS).

## Still open before a full go/no-go
1. **D3** — label the 50-row sample → precision → deny-list vs LLM-classifier call.
2. **W3** — label the candidate sheet → confirmed novel windows (vs upper-bound candidates).
3. **D4** — file the GSA rate-increase request; record ticket + ETA.
4. **D5** — 3–5 buyer interviews (demand signal).
5. **W4 / W5 / W6** — partner-dependent: geo-recall labels, §404 pattern, Tier-1 paid-seat confirmation.
