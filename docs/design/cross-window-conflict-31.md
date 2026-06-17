# Cross-window (chain) conflict shape — design for #31

> Status: **RATIFIED** (2026-06-17). Option (a) approved; reopening flag DEFERRED (O4). Contract
> change applied to `packages/contracts/src/index.ts` @ **0.4.0**. Canonical spec:
> `docs/architecture/docketclock.md`.
>
> **CAVEAT — see "Back-compat verdict" below.** The change is back-compat at the WIRE/PARSE level
> (defaults), but NOT at the TypeScript-emit level: `apps/docketclock` does NOT type-check against
> 0.4.0 with the reconcile emit site unchanged (Zod `.default(...)` fields are required on the
> inferred OUTPUT type). The 0.4.0 contract PR (#32) therefore DOES include the 3-field, zero-behavior
> `reconcile.ts` emit-site edit (`conflict_scope: "cross_source"`, `ocd_id_b: null`, `govinfo_url_b:
> null`) to restore that typecheck — the existing per-`ocd_id` engine keeps emitting only cross_source
> conflicts, so runtime behavior is unchanged. What remains for the #31 BUILD is the NEW behavior: the
> cross_window EMISSION, pair-aware retirement (scope the per-`ocd_id` sweep to cross_source rows), the
> migration (carry `conflict_scope`/`ocd_id_b`/`govinfo_url_b` columns), and the `/conflicts`
> either-side filter (O1).

## Problem (confirmed against the code)

`ConflictRecord` (contracts/src/index.ts) is PER-OCD_ID and encodes a CROSS-SOURCE disagreement
inside ONE window: `observation_a_id`/`observation_b_id` are two observations on the SAME `ocd_id`,
and `source_a`/`source_b` are the two SOURCES (FR vs Regs) that disagree. The persist natural key is
`(ocd_id, observation_a_id, observation_b_id)`; the engine (reconcile.ts) only emits when `fr &&
regs` are both present on one ocd_id.

A #31 **chain conflict** breaks BOTH assumptions:

- It spans TWO windows / two ocd_ids. An amendment notice (extension/correction/reopening/
  withdrawal) is a SEPARATE FR document and `makeOcdId` mints its OWN ocd_id from its own frDocNum —
  so it is a standalone window. The conflict is between the amendment's window (B) and the
  original's window (A).
- It is cross-DOCUMENT and often SAME-SOURCE: both observations can be `source = federal_register`
  (the FR amendment doc vs the FR original doc). The FR-vs-Regs `source_a`/`source_b` framing no
  longer holds.

`conflict_flags` already has the vocabulary (`extension_chain_unresolved`, `correction_pending`,
`withdrawn_vs_open`, `multi_target_notice`) — NO new flag is required. This is a RECORD SHAPE
decision.

## Ratified: Option (a) — extend `ConflictRecord` with optional cross-window fields

Keep ONE published conflict shape and ONE proof feed. Make the two "sides" of a conflict
self-describing, with the existing per-ocd_id fields preserved as-is for back-compat.

Applied @ 0.4.0:

- `conflict_scope: z.enum(["cross_source","cross_window"]).default("cross_source")`
- `ocd_id_b: OcdId.nullable().default(null)`
- `govinfo_url_b: z.string().url().nullable().default(null)`
- `superRefine`: cross_window ⇒ `ocd_id_b` present AND distinct from `ocd_id`; cross_source ⇒
  `ocd_id_b` null.

## Open questions — resolved

- **O1 = feed matches EITHER side.** The `/conflicts` query must match a cross_window row when the
  caller filters by `ocd_id` on EITHER side (`ocd_id` OR `ocd_id_b`). This is a QUERY-LAYER change,
  NOT a contract change. **#31-build note — queries.ts only; the contract task did not touch the API.**
- **O2 = explicit `conflict_scope` discriminant.** Chosen (vs inferring scope from `ocd_id_b`
  non-null) — an explicit, defaulted enum is self-documenting and lets the superRefine pin both
  directions. Applied.
- **O3 = include `govinfo_url_b` now.** Chosen — each side of a cross_window conflict is a distinct
  legal document with its own govinfo anchor; carrying B's URL now keeps the proof feed honest
  without a later contract bump. Applied.
- **O4 = reopening ConflictFlag — DEFERRED.** No new `ConflictFlag` added. The existing vocabulary
  covers chain conflicts; a dedicated reopening flag waits for a concrete need.

## Versioning verdict

ADDITIVE / MINOR bump (0.3.0 → 0.4.0). No existing field changed type or nullability; all new fields
are optional/defaulted. Existing serialized per-ocd_id conflicts stay valid on PARSE.

## Back-compat verdict (measured 2026-06-17)

- **Contract typecheck: PASS** (`pnpm --filter @yokel/contracts typecheck`, exit 0).
- **Wire/parse back-compat: PASS** — a row omitting all three fields parses as
  `{ conflict_scope: "cross_source", ocd_id_b: null, govinfo_url_b: null }`.
- **`apps/docketclock` typecheck against 0.4.0: FAIL** (`pnpm --filter @yokel/docketclock exec tsc
--noEmit`, exit 1):

  ```
  src/reconcile/reconcile.ts(371,5): error TS2739: Type '{ ... }' is missing the following
  properties from type ConflictRecord: conflict_scope, ocd_id_b, govinfo_url_b
  ```

  **Why:** Zod `.default(...)` fields are REQUIRED in the INPUT type but PRESENT in the
  `z.infer`/OUTPUT type. `ConflictRecord` = `z.infer<typeof ConflictRecord>` (the output type), so
  all three new fields are required on the inferred type. reconcile.ts assigns an object literal to
  a variable typed `ConflictRecord | null` (reconcile.ts:181), and that literal now omits the three
  new fields → TS2739. This is a TYPE-level (not parse-level) incompatibility.

  **This is expected/acceptable and belongs to #31 BUILD, not this contract task** (which is
  forbidden from editing reconcile.ts). The fix is a 3-field, no-behavior-change addition at the
  emit site:

  ```ts
  conflict = {
    ocd_id: ocdId as OcdId,
    observation_a_id: fr.observation_id,
    observation_b_id: regs.observation_id,
    source_a: fr.source,
    source_b: regs.source,
    conflict_flags: conflictFlags,
    govinfo_url: govinfo,
    conflict_scope: "cross_source", // current engine only emits cross-source
    ocd_id_b: null,
    govinfo_url_b: null,
    detected_at: nowIso,
  };
  ```

  (Alternatively the build could keep emit sites field-free by exporting a separate INPUT type via
  `z.input<typeof ConflictRecord>` for constructors — but the explicit 3 fields above are clearest.)

## #31 BUILD notes (load-bearing — for the builder, NOT this contract task)

1. **Emit site must add the 3 fields** (see above) — required to restore `apps/docketclock`
   typecheck. For the new cross_window emitter, set `conflict_scope: "cross_window"`, `ocd_id_b` =
   the amendment/other window's ocd_id, `govinfo_url_b` = that window's govinfo URL.
2. **Retirement MUST become pair-aware.** The current per-`ocd_id` "retire all conflicts for this
   ocd_id" sweep would wrongly retire a LIVE cross_window conflict that merely SHARES the ocd_id on
   one side. **Scope the per-ocd_id retirement sweep to `conflict_scope = 'cross_source'` rows** so
   it can never retire a cross_window conflict. cross_window conflicts need their own pair-aware
   retirement keyed on the (ocd_id, ocd_id_b) pair (or both observation ids).
3. **O1 query change (queries.ts):** the `/conflicts` filter-by-ocd_id must match EITHER `ocd_id` OR
   `ocd_id_b`.
4. **Persist natural key** must extend to disambiguate cross_window rows (the existing
   `(ocd_id, observation_a_id, observation_b_id)` key is fine since observation ids are unique, but
   confirm the migration carries `conflict_scope`, `ocd_id_b`, `govinfo_url_b` columns with
   matching defaults: `'cross_source'`, NULL, NULL).
