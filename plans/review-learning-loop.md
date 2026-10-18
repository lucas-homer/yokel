# Review learning loop — turning closed queue items into durable knowledge, and where a cheap typed-judgment model fits

> Status: **PROPOSED** (2026-10-16). Companion to `plans/review-autopilot.md`; everything here is
> additive to that plan's PR-A1 to PR-A4. Produced by a 20-agent design workflow (4 readers over the
> live TypeSafe docs, the 51-verdict corpus, the repo's eval seams and the contract invariants; 3
> independent design angles; 2 judges; 1 synthesis; 10 adversarial refutations) and then corrected by
> hand where the refuters found the synthesis overreaching. Corrections are marked **[corrected]**.
> Numbers are measurements from a live read of the k3d cluster on 2026-10-16, not estimates.

## The two questions, answered

**Can the system learn from closed review items and get smarter over time?** Yes, with a precise
meaning of "learn": every closed verdict becomes a committed, replayable fixture; recurring fixture
classes are distilled by the agent into _versioned rules-as-data_ that a human ratifies by merging;
ratified rules move whole classes out of the queue permanently, so future arrivals of the same
shape never need review. The ratification step is the learning signal, and the rule is the learned
artifact. Under that meaning, 26 of the 51 historical verdicts belong to classes decidable from
stored fields alone (FDA patent-review dual deadline 8, CMS OMB desk-officer 5, publication or
effective date mis-selected 7, PRA/OMB dual date 3, event date mis-selected 1, Regs sentinel 2).
What the system cannot do is _statistical_ learning that improves without ratification: the corpus
is 51 verdicts over 10 days by one operator, selected in template batches because they were easy,
with zero negative decisions in the database, and the contract forbids any learned score from
touching a close or a confidence.

**Can a model like TypeSafe Jev apply those learnings with evaluations or reinforcement learning,
on cheaper and faster calls?** It can _apply_ learnings that we encode; it cannot _acquire_ them.
Per the live docs, Jev is not fine-tuned or LoRA-adapted on customer data, the same weights serve
every account, and it is not trained on customer requests, so "reinforcement learning from our
verdicts" is not a product capability (https://docs.typesafe.ai/models.md#customizing-jev). The
documented levers are the request itself: state content, instructions, and criteria with examples.
There is no hosted eval product; evals are our own harness over our own labels. Every Jev answer
carries probabilities, which the DocketClock contract forbids storing, thresholding into
confidence, or attaching to a verdict. Jev also reads dates as text and is documented as unreliable
at comparing or subtracting them (https://docs.typesafe.ai/model-jaggedness/jev-1.13.md), while
the load-bearing checks here are date equality, delta sign, and a networked primary-source read.
So the cheap call does not replace the expensive steps. Its lawful residual role is a host-side,
categorical, veto-or-ordering assist whose probabilities are discarded at the boundary, off by
default, adopted only after the billing question below is answered, and tried first on the
already-keyed Gemini categorical seam because that needs no new vendor and yields no number to
discard. Price and speed, for the record: $0.042 per million input tokens, output free, "about
100 ms" claimed and unqualified (https://docs.typesafe.ai/models.md#current-models).

## What the corpus actually says

Measured on the 51 verdicts plus the 42 live queue items. **[corrected]** The 600-character cap on
`fr_dates` in the mined corpus was introduced by this analysis's export query, not by ingestion;
the observation log stores the full DATES text. Any "truncation" caveat in the workflow output is
void and the full text is available to rules.

| class                                                                                           | verdicts                      | decidable from stored fields                                             | live queue items                           |
| ----------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------ | ------------------------------------------ |
| extension or reopening published as a _separate_ FR document; Regs already carries the new date | 22–23                         | no, one external read each (FR search by doc number, docket, RIN, title) | 16–18, including the 10-item PHMSA cluster |
| FDA patent-review notice: FR metadata took the petition date, Regs the comment date             | 8                             | yes                                                                      | 3                                          |
| DATES text names a publication, effective or program date that FR metadata mis-selected         | 7                             | yes                                                                      | 1                                          |
| CMS 30-day OMB desk-officer notice: portal is a courtesy posting                                | 5                             | yes                                                                      | 0                                          |
| DATES text names a PRA/OMB information-collection date FR metadata mis-selected                 | 3                             | yes                                                                      | 1                                          |
| event or meeting date mis-selected                                                              | 1                             | yes                                                                      | 1                                          |
| amendment window whose Regs date is a sentinel or the old period                                | 2                             | yes                                                                      | 0                                          |
| withdrawal hidden by the #112 identity split                                                    | 2                             | partly (a DB join on the Regs document id)                               | 0                                          |
| echo of an honored pin after the portal closed (PR-A1 in the autopilot plan)                    | 7                             | yes                                                                      | 7                                          |
| unexplained portal offset, no document explains it (#127)                                       | 0 pins, 3 documented non-pins | detection yes, disposition needs a negative search                       | 6–8                                        |
| multi-stage comment periods (FCC, PRC, ITC): Regs carries the reply or adequacy deadline        | 0                             | yes, but the correct close is a _policy_ decision                        | 5                                          |

Two facts the refuters surfaced that change the emphasis:

- **The "Regs date wins" shortcut reproduces 40 of 49 pins and 20 of the 22 extension-elsewhere
  pins without any external read.** That is an artifact of selection (the human only approved
  those pins after the extension notice was found), not a licence: pinning on Regs agreement alone
  would publish HIGH on exactly the #127 class. But it tells us what the largest class really needs:
  not a review rule, but proof that _a later primary document exists for this notice_. That is a
  chain-linkage problem the system already has machinery for (the cross-window chain pass and its
  adjudicator), and it is where the biggest deterministic win sits (lever 2 below).
- **What the human meant by "low-hanging fruit"** is recoverable from the notes: items where one
  primary document states the operative deadline verbatim _and_ explains the competing value, so
  no judgment about what "comment close" means was required. Three shapes: templated agency notices
  whose own DATES text resolves the conflict; "Regs later than FR" windows where a one-hop FR search
  finds the extension; and withdrawals provable from a live Regs read. Every note converges on the
  same evidence card (notice URL, verbatim DATES text, the competing value explained).

## Where knowledge can live today, and the gap

The repo already has four tiers for knowledge, all deterministic and all gated: the contract, the
reconciler (`RECONCILER_VERSION` plus an ADR plus a projection sweep), the RuleBox rulebook
(`RULEBOOK_VERSION`, title-regex classify and deny rules only), and committed gold fixtures with
Zod loaders and replay tests (`eval/chain-gold.json`, `eval/accuracy-misses/`). What it lacks is
the tier this question is about: a versioned, testable, data-shaped layer between "a free-text
note on one verdict" and "a full ADR plus engine change", where "this notice template carries a
petition date" or "this agency's courtesy posting is not the channel" can be recorded, replayed,
and gated. The 51 verdicts exist only as rows in the Mini's Postgres; the steering that produced
them lives in skill prose with no version, schema, or test; and the repo's own history says
hand-labelled markdown stalls (`spikes/out/XCHECK_diff.md`).

## Decisions proposed

- **Learning tiers, from cheapest to most consequential.** (1) A _fixture_ for every verdict, no
  behaviour change. (2) A _route rule_: deterministic classification of a queue item into a
  playbook (`extension_search`, `escalate_only`, `policy_multi_stage`, `not_a_comment_window`);
  derives nothing, changes only what the agent does first. (3) A _resolve rule_ in the rulebook
  that can do exactly two things: convert a cross-source conflict into a two-source agreement by
  re-parsing the FR close from the stored DATES text (HIGH only when the re-parsed FR date equals
  the Regs Eastern date), or mark a source value non-evidentiary (the window then derives from the
  remaining source at MEDIUM). A resolve rule can never introduce a date absent from a primary
  source and never mints HIGH from one source. (4) A _reconciler rule_ via ADR, for structural
  classes (the PR-A1 echo, ADR 0010 metadata churn, lever 2 below). Every tier is replay-gated
  against the fixtures it came from and against every fixture of every other class (zero
  cross-class firing).
- **The agent proposes, the human ratifies by merge.** Each week the autopilot exports new
  fixtures, groups uncovered ones by agency, masked title template, date-gap sign and whether the
  note's deciding source was external, and opens one PR per candidate class with at least three
  precedents, the rule literal, the fixtures' expected rule id, adversary fixtures, and a
  rulebook-diff over every live window and the 586 retired conflicts. Merging is the authority.
  ADR 0016 records the two permitted effects of a resolve rule and that ratification is the merge.
- **Lever 2: chain-linked amendments should supersede the original's FR date deterministically.**
  The Roadless case is the specimen: extension `2026-18648` (RIN 0596-AD66) was ingested as its
  own window at HIGH while original `2026-16965` stayed CONFLICTING until a human pinned it. If a
  corroborated cross-window link (shared RIN or explicit reference, or an adjudicator `affirm`)
  does not already feed the original's derivation, adding that rule removes most of the largest
  class without any review at all; if it does, the gap is chain _discovery_ (searching FR by RIN
  and docket for later documents) rather than reconciliation. **Verify which before building
  anything in this lever**; it belongs to the reconciler tier (ADR), not the rulebook.
- **Negative knowledge is first-class.** The three #127 non-pins become hand-written fixtures with
  expected disposition `escalate_only`, every future `escalate` verdict exports automatically, and
  the hard gate for any rule change is FALSE-PIN-ROUTE = 0: no fixture whose expected disposition
  is escalate, policy, or not-a-comment-window may fire a reparse or non-evidentiary rule.
- **A cheap typed-judgment model, if any, is veto-or-ordering only.** Monotone safety: a non-human
  categorical judgment may move a decision toward `escalate` or shorten investigation, never toward
  `pin_close`. Permitted judgments: class triage for work ordering; recall-biased filtering of
  extension-search hits; evidence-card entailment ("does this quoted passage state the deadline
  for this document number") used to veto; competing-value-explained check used to veto; note
  completeness lint. Forbidden: generating or comparing dates, paraphrasing the verbatim quote,
  being the verifier, emitting any stored number, touching the engine. Ordering of adoption: Gemini
  categorical (already keyed, categorical by contract) first; Jev only if that proves unmeasurable
  and the operator approves a second API-billed vendor on the autopilot path.

## What the verification pass changed **[corrected]**

Ten refutations ran against the synthesis's key claims, two lenses each (live TypeSafe docs; the
codebase and corpus). Outcomes folded in above and here:

- The synthesis stated "an unpaired `RULEBOOK_VERSION` bump changes nothing for settled windows and
  a paired bump costs at most 25 Gemini calls per cycle". Inverted on the first half: the chain pass
  runs every poll cycle and re-peeks every ambiguous pair under a rulebook-keyed cache
  (`adjudicator/consult.ts`, `content-hash.ts`), so _any_ rulebook bump re-keys the adjudication
  cache and drains fresh calls at up to 25 per cycle until the backlog is re-decided; and the
  rederive sweep keys only on `RECONCILER_VERSION` (`db/rederive-stale-windows.ts`), so a
  rulebook-only bump does _not_ re-derive settled windows. PR-L1 therefore must either split the
  version string (classify/deny version feeds the adjudication hash; resolve version does not) or
  document the bounded cost, and must pair every resolve-rule change with a reconciler version bump
  or teach the sweep the rulebook version.
- "23 of 23 extension-elsewhere verdicts needed an external read" is 22 by the refuter's count, and
  the stored-field shortcut reproduces 20 of those 22 dates (see above). The conclusion stands for
  the _justification_; the emphasis moved to lever 2.
- "Jev cannot carry the learning" overstated the docs. Accurate statement: Jev cannot _acquire_
  learning (no fine-tuning, no per-account weights, not trained on customer traffic); it can
  _apply_ learning we encode in criteria and examples, and the docs warn that examples raise
  confidence, not correctness (https://docs.typesafe.ai/primitives/score.md).
- The synthesis's quantitative predictions (at least 25 verdicts reproduced by rules; queue 42 to
  about 30 after PR-A1 plus the first rules) are untested forecasts, not findings. They are kept
  below as acceptance targets to be measured, not as claims.

## First slice

Prerequisites: PR-A1 (echo rule) and PR-A2 (`escalate` kind, `reviewer`, `--expect`) from the
autopilot plan.

### PR-L0 — the review-gold corpus (no rules, no model, no key)

`scripts/export-review-gold.ts` (cloned from `export-accuracy-miss.ts`: read-only, versioned
filename, refuse overwrite) writes one fixture per `human_review` observation to
`apps/docketclock/eval/review-gold/`: verbatim note and operator; an `input` built by a pure
code-side state assembler (`src/review/triage-state.ts`: FR fields with full DATES text, Regs
fields, notice flags, prior verdicts, `candidate_dates[]` found by regex in the DATES text with
code-computed `equals_fr_close`, `equals_regs_close_eastern`, `is_before_publication`,
`delta_days_regs_minus_fr`, `regs_date_before_posted`, `regs_sentinel_year`); an `expected` block
(kind, pinned date, class from the taxonomy above, rule id or none, route); `traps[]`, `outcome`
(monitoring state, contradicting observation ids, superseded_by), `status: active|retired|
superseded` with a reason, and `held_out: true` on the 10 shadow-gate items. The three #127
non-pins are hand-written negatives. A Zod loader (`src/review/eval-review-gold.ts`) fails loudly
on a null expected, a duplicate id, or an active fixture without a class. `show --json` on the CLI.

**Verify:** 54 fixtures load; every fixture expects rule id none; assembler flags hand-checked on
one fixture per class; `pnpm -r test && pnpm -r typecheck` green; no secret or non-public payload
in the files.

### PR-L1 — resolve rules: contract 0.12.0 (or app-side fallback), evaluator, reconciler v2.3, ADR 0016, three rules

Contract-keeper: a third `Rule` kind `resolve` with `when` (title or type regex, DATES regex with a
named `comment_close` group, `regs: equals_comment_close | sentinel | equals_posted_date`),
`effect: reparse_fr_close | regs_non_evidentiary | route`, `precedents` (min 1), `ratified
{by, on}`, and the refinement that `reparse_fr_close` requires both the named group and
`regs: equals_comment_close`. `ConflictFlag += rule_resolved` (the `human_resolved` provenance
pattern). If the keeper declines a third kind, an app-side `reconcile/review-rules.ts` with the
same data shape and gates. Evaluator `applyResolveRules` in `rulebox/index.ts`, pure, first match
wins, English-month date parser in code. Wiring in the `fr_regs_date_mismatch` branch of
`reconcile.ts` before the Eastern comparison. First rules: `regs-sentinel` (2 precedents),
`fda-patent-review-dual-deadline` (8), `cms-omb-desk-officer` (5; derives MEDIUM, a product
decision recorded in the ADR). Version split or documented adjudication re-key cost; sweep pairing
as an acceptance criterion. `scripts/rulebook-diff.ts` over `export:windows` plus the retired
conflicts.

**Verify:** 15 fixtures fire with the expected dates, the other 39 do not; adversary fixtures per
rule (date moved, Regs changed, title drifted, deciding sentence removed) do not fire;
FALSE-PIN-ROUTE 0; an honored pin on the same window stays `human_resolved` HIGH; rulebook-diff
lists only the intended windows; after deploy and sweep `2026-20766` leaves the queue with
`rule_resolved`; the fresh Gemini call count after the bump is observed and recorded.

### PR-L2 — DATES-text rules, route rules, queue annotation, verdict stamp

Rules `dates-text-pra-omb-selected` (3 precedents; covers `2026-20660`),
`dates-text-publication-effective-selected` (7; covers `2026-19895`; relative phrasing must not
match); route rules `extension-search-shape`, `escalate-only-unexplained-offset`,
`policy-multi-stage`, `not-a-comment-window`; route printed on queue rows at read time; the
autopilot stamps `[rulebook=<ver> route=<route> class=<class>]` as the note's first line until
contract 0.11.0 offers a field; the PHMSA per-docket identity requirement written into the
`extension_search` playbook.

**Verify:** 11 more fixtures fire reparse rules; the extension-elsewhere fixtures fire only the
route rule; the #127 fixtures fire `escalate_only`; the queue shows a route for all items; the
held-out set contains no rule-resolved item.

### PR-L3 — the loop

`scripts/rule-coverage.ts` (groups uncovered fixtures and reports candidate classes with at least
three precedents in the Monday run); `export:review-gold --since`; a "Rule proposal" section in
`docs/runbooks/review-queue.md`; the eval CI path filter extended to `eval/review-gold/**`; PR-A4's
rollup gains a `rule_resolved` split and per-rule contradiction counts so a later extension on a
rule-resolved window convicts the rule and retires its fixtures (never deletes them); the shadow
gate runs with and without route annotation and gains a `route_misuse` disagreement category.

**Verify:** the coverage report reproduces the corpus counts; a seeded rule-resolved window
followed by a seeded extension observation appears under that rule id; CI re-runs on a
fixture-only change; both shadow runs report zero `route_misuse`.

### PR-L4 — lever 2 investigation, then the rule

A read-only check of whether a corroborated cross-window link already changes the original's
derived close. If not: ADR plus `reconcile-v2.4` rule "a corroborated later amendment supersedes
the original's FR close", with the Roadless pair and the PHMSA cluster as fixtures (the cluster
must _not_ link without a per-docket key). If it does: a chain-discovery slice (FR search by RIN
and docket for later documents) instead.

### PR-L5 (optional, off by default) — categorical assist

A `Judge` interface with a null default; Gemini categorical implementation first through the
existing adjudicator pattern (the Jev fallback, pinned `jev-1.13.0`, was dropped on 2026-10-17: no
second API-billed vendor; the Gemini categorical assist is the only option), probabilities discarded
in one threshold file, nothing written to observations, notes, cards or fixtures, and a tooling
failure keeps every item's deterministic route. Gated on the billing question and on a
contract-keeper ruling about any host-side probability cache.

## Open questions for the operator

1. **Billing route for any cheap typed-judgment model.** The house rules forbid API-billed Claude
   routes and the autopilot plan rejects an in-cluster API-billed agent. Gemini Flash is already
   keyed for the in-engine adjudicator. Is a second API-billed vendor (TypeSafe) acceptable on the
   autopilot path at all, and under what call budget?
   **Resolved 2026-10-17:** closed. Jev dropped; no second vendor.
2. **CMS OMB desk-officer windows** were pinned HIGH by humans; a non-evidentiary rule derives
   MEDIUM. Which is right is a product decision for ADR 0016.
   **Resolved 2026-10-17:** MEDIUM for rule-resolved windows; HIGH reserved for a read of the notice.
3. **Multi-stage comment periods** (FCC, PRC, ITC): initial deadline or reply deadline as the
   operative close? The corpus has no precedent and the choice is policy, not evidence.
   **Resolved 2026-10-17:** the initial deadline is the close for v1, reply deadline kept visible;
   revisit if the class grows. To be recorded in ADR 0016.

## Risks

- A wrong ratified rule is a class-wide error whose first contradicting observation may be weeks
  away on closed windows. Controls: three-precedent bar, rulebook-diff paste, adversary fixtures,
  per-rule contradiction split, rollback by version revert plus sweep.
- The rule tier may be smaller than the corpus suggests (selection bias); wording drift makes a rule
  go silent, which is safe but decays the benefit.
- Label debt: the design keeps hand labelling to one `class` enum per fixture, with a loud CI
  failure on an unlabelled active fixture and the exporter doing the mechanical work.
- Post-close monitoring cannot grade an honored pin (autopilot plan, Finding 3); automatic
  retirement of fixtures depends on PR-A4 attribution plus the weekly audit.
