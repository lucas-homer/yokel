# Step-5 owner review: where to start (2026-10-17)

All eight blind passes are sealed and integrated, and every state's audit is frozen. Each state
has two documents for you:

| State | Owner sheet (class questions + cases) | Audit checklist | Estimate / budget (min) |
|---|---|---|---|
| CT | [CT/reconcile/OWNER-SHEET.md](CT/reconcile/OWNER-SHEET.md): 16 class, 88 cases | [CT/reconcile/AUDIT-SAMPLE.md](CT/reconcile/AUDIT-SAMPLE.md): 83 units (stratified) | 543 / 600 |
| VA | [VA/reconcile/OWNER-SHEET.md](VA/reconcile/OWNER-SHEET.md): 7 class, 83 cases | [VA/reconcile/AUDIT-SAMPLE.md](VA/reconcile/AUDIT-SAMPLE.md): 30 units (A1) | 643 / 660 |
| MS | [MS/reconcile/OWNER-SHEET.md](MS/reconcile/OWNER-SHEET.md): 6 class, 179 cases (155 visual marks) | [MS/reconcile/AUDIT-SAMPLE.md](MS/reconcile/AUDIT-SAMPLE.md): 30 units (A1) | 371 / 400 |
| WA | [WA/reconcile/OWNER-SHEET.md](WA/reconcile/OWNER-SHEET.md): 9 class, 81 cases | [WA/reconcile/AUDIT-SAMPLE.md](WA/reconcile/AUDIT-SAMPLE.md): 30 units (A1) | 683 / 720 |

Budgets are decisions 19–22 in `../rights/DECISIONS.md`. The audit method is PROTOCOL §5, plus
Amendment A1 for VA, WA and MS.

**Suggested order.**
1. **CT class questions.** Several later states reuse them: CT C9/C11/C14/C15/C16 settle the
   deadline-wording cutoffs, openings and completion counts everywhere.
2. **The other states' class questions.** Most say "same as CT Cn".
3. **Cases, state by state.** Items marked LOOK need you to open the original. Rendered pages are
   in `.census-passes/<ST>/review-renders/`, outside git.
4. **The audit checklists.** Check boundaries, accepted labels, exclusions and anything both passes
   missed, in the originals under `.census-passes/<ST>/inputs/originals/`.

**How to answer.** In chat, for example "CT: accept all class proposals except C9; C9 → unknown" or
"VA K12 agree, K15 …". The primary turns your answers into signed adjudication records
(`<ST>/adjudications.jsonl`, author.role human_reviewer) and logs your active minutes against the
budget. Nothing is signed until you answer.

**Before the final stage, primary fixes still to make:** the validator's C10 shared ledger still
lists WA/CT/VA/TN with a 240-minute-per-state, 960-minute-total cap. It must follow the four pilot
states (WA, CT, VA, MS) and decisions 19–22.
