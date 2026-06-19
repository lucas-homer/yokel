/**
 * chain-adjudicate-starvation.test.ts — the ADVERSARY's deeper regression lock on the cap×cache
 * anti-starvation fix (#31 Slice 3b follow-up: the per-cycle cap budgets FRESH LLM CALLS, not
 * pairs-considered). It attacks the two headline risks the happy-path suite under-tests:
 *
 *   S1 SORT-JUMPING STARVATION — the OLD `slice(0, cap)` bug starved every pair beyond the first `cap`
 *      by sort order, FOREVER. The fix drains the backlog because a cached pair becomes a FREE peek-hit
 *      that no longer eats budget. The subtle attack the fixed-N drain test misses: a pair that DEFERS
 *      this cycle while NEW, LOWER-SORTING uncached pairs keep arriving. We prove the budget still
 *      ADVANCES past the freshly-cached front to the long-waiting tail — the last-sorting pair is NOT
 *      held hostage forever by a churn of pairs ahead of it (it drains the moment the ones ahead cache).
 *
 *   H1 PEEK/CONSULT HASH IDENTITY — peekAdjudication MUST compute the SAME content_hash as
 *      consultAdjudicator for the SAME logical input, or a peek-miss after a consult-write re-calls
 *      FOREVER (budget never drains) or reads the wrong row. We consult an input, then peek a logically
 *      identical input whose object keys are in a DIFFERENT order AND that carries an UNMODELED extra
 *      field — and assert the peek HITs and returns the consult's exact verdict. Both must wash out via
 *      AdjudicationInput.parse → canonicalize (sorted keys, stray fields stripped).
 *
 *   B1 THROW BUDGET BOUND — a throwing adjudicator must not be hammered across the WHOLE surfaced set in
 *      one cycle: with surfaced > cap and every call throwing, total call ATTEMPTS are bounded by `cap`
 *      (each throw spends a budget unit), and the overflow defers — no link, no batch abort.
 *
 * DB-backed; SKIPPED (with notice) when DATABASE_URL is unset. Repo test style: hand-rolled assert,
 * out[] accumulator, failures counter, process.exit.
 */
import type { AdjudicationInput, AdjudicationVerdict } from "@yokel/contracts";
import type { Adjudicator } from "../src/adjudicator/port.js";
import { RULEBOOK_VERSION } from "../src/rulebox/index.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = ""): void {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const NOW = new Date("2026-06-01T00:00:00Z");

function spyAdjudicator(
  id: string,
  verdict: AdjudicationVerdict,
): Adjudicator & { calls: number } {
  const spy = {
    id,
    calls: 0,
    async adjudicate(_i: AdjudicationInput): Promise<AdjudicationVerdict> {
      spy.calls++;
      return verdict;
    },
  };
  return spy;
}

function throwingAdjudicator(id: string): Adjudicator & { calls: number } {
  const spy = {
    id,
    calls: 0,
    async adjudicate(_i: AdjudicationInput): Promise<AdjudicationVerdict> {
      spy.calls++;
      throw new Error("simulated outage");
    },
  };
  return spy;
}

if (!process.env.DATABASE_URL) {
  console.log(
    "\n=== chain-adjudicate-starvation results ===\n  (skipped: DATABASE_URL unset — DB-integration only)\nALL EXPECTATIONS MET",
  );
  process.exit(0);
}

const { createClient } = await import("../src/db/client.js");
const { runMigrations } = await import("../src/db/migrate.js");
const { parseFrObservation } =
  await import("../src/sources/federal-register.js");
const { ingestObservation } = await import("../src/ingest/observe.js");
const { reconcileOcdId, chainReconcileOnce } =
  await import("../src/reconcile/persist.js");
const { consultAdjudicator, peekAdjudication } =
  await import("../src/adjudicator/consult.js");
const { adjudicateAmbiguousPairs } =
  await import("../src/reconcile/chain-adjudicate.js");
const { listConflicts } = await import("../src/api/queries.js");

const sql = createClient();

async function reset(): Promise<void> {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
}

async function seedWindow(opts: {
  docNum: string;
  docketIds: string[];
  rin: string | null;
  publicationDate: string;
  commentsCloseOn: string;
  action: string;
  dates: string;
}): Promise<string> {
  const raw: Record<string, unknown> = {
    document_number: opts.docNum,
    type: "Notice",
    action: opts.action,
    title: `Notice ${opts.docNum}`,
    dates: opts.dates,
    comments_close_on: opts.commentsCloseOn,
    publication_date: opts.publicationDate,
    docket_ids: opts.docketIds,
    regulation_id_number: null,
    regulation_id_numbers: opts.rin ? [opts.rin] : [],
  };
  const cand = parseFrObservation(raw);
  await ingestObservation(sql, cand);
  const ocdId = `ocd-participation-window/federal/${opts.docNum}`;
  await reconcileOcdId(sql, ocdId, NOW);
  return ocdId;
}

/** Seed one ambiguous A/B pair (shared docket, disjoint RIN, no explicit ref). Returns B's ocd_id. */
async function seedAmbiguousPair(
  docket: string,
  aDoc: string,
  bDoc: string,
): Promise<string> {
  await seedWindow({
    docNum: aDoc,
    docketIds: [docket],
    rin: "2040-AAA1",
    publicationDate: "2026-05-01",
    commentsCloseOn: "2026-08-01",
    action: "Notice of public comment period.",
    dates: "Comments must be received on or before August 1, 2026.",
  });
  await seedWindow({
    docNum: bDoc,
    docketIds: [docket],
    rin: "2040-ZZZ9",
    publicationDate: "2026-05-20",
    commentsCloseOn: "2026-09-15",
    action: "Notice; extension of comment period.",
    dates:
      "The comment period is extended. Comments now due September 15, 2026.",
  });
  return `ocd-participation-window/federal/${bDoc}`;
}

try {
  // ── S1: SORT-JUMPING STARVATION — the precise multi-cycle attack the fixed-N drain test misses.
  // cap=1. A hostage pair Z sorts LAST. We force Z to DEFER (a lower-sorting front pair eats the one unit
  // of budget), then inject lower-sorting churn for a BOUNDED number of cycles, THEN stop the churn. The
  // anti-starvation guarantee: once arrivals stop outpacing the cap, the budget ADVANCES past the freshly
  // cached front (cache hits are FREE peeks that never re-spend) and Z is adjudicated + linked. Under the
  // OLD slice(0,cap) bug the budget would re-pay the same front pair every cycle and Z would starve
  // FOREVER even after the churn stopped. (NOTE: sustained arrivals AT-OR-ABOVE the cap is an inherent
  // THROUGHPUT limit, not a regression — the backlog drains exactly when arrival-rate < cap, which is the
  // property under test here.)
  {
    await reset();
    const cap = 1;
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "drain",
    });

    // Front pair F0 (sorts before Z) + the hostage Z whose B doc sorts LAST ("2026-79999"). cap=1 → the
    // first cycle spends its unit on F0 (lower sort) and Z DEFERS.
    await seedAmbiguousPair("EPA-HQ-STARVE-F0", "2026-70000", "2026-70001");
    const zB = await seedAmbiguousPair(
      "EPA-HQ-STARVE-Z",
      "2026-70900",
      "2026-79999",
    );

    const CHURN_CYCLES = 3; // inject a new lower-sorting pair for the first 3 cycles, then STOP.
    let cycle = 0;
    let zLinkedAtCycle = -1;
    const callsPerCycle: number[] = [];
    while (cycle < 12 && zLinkedAtCycle === -1) {
      if (cycle >= 1 && cycle <= CHURN_CYCLES) {
        // churn pair Fk sorts before Z ("2026-701xx" < "2026-79999").
        const k = String(10 + cycle).padStart(3, "0");
        await seedAmbiguousPair(
          `EPA-HQ-STARVE-F${cycle}`,
          `2026-701${k}`,
          `2026-702${k}`,
        );
      }
      const before = spy.calls;
      await chainReconcileOnce(
        sql,
        new Date(`2026-06-${String(2 + cycle).padStart(2, "0")}T00:00:00Z`),
        { adjudicator: spy, cap },
      );
      callsPerCycle.push(spy.calls - before);
      const zLive = await listConflicts(sql, { ocdId: zB });
      if (zLive.total === 1) zLinkedAtCycle = cycle;
      cycle++;
    }

    assert(
      "S1 sort-jumping: the LAST-sorting hostage pair Z DRAINS once bounded churn stops (no permanent starvation — the old slice(0,cap) bug would never reach it)",
      zLinkedAtCycle >= 0,
      `zLinkedAtCycle=${zLinkedAtCycle} callsPerCycle=${JSON.stringify(callsPerCycle)}`,
    );
    assert(
      "S1 sort-jumping: budget honored every cycle (≤ cap=1 fresh call per cycle — cache hits never re-spend the budget)",
      callsPerCycle.every((c) => c <= cap),
      JSON.stringify(callsPerCycle),
    );
  }

  // ── H1: PEEK/CONSULT HASH IDENTITY under key-order shuffle + an UNMODELED extra field. A drift here
  // would re-call forever (peek-miss after a consult-write) or read the wrong row. We consult one input,
  // then peek a LOGICALLY IDENTICAL input with (a) keys in a different insertion order and (b) a stray
  // field the schema does not model. The peek MUST hit and return the consult's exact verdict.
  {
    await reset();
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "identity",
    });

    // Canonical chain input the loop would build (field order as in chain-adjudicate.ts).
    const consulted: AdjudicationInput = {
      kind: "chain",
      rulebook_version: RULEBOOK_VERSION,
      a_title: "Original Notice; Request for Comments",
      a_dates_text: "Comments due August 1, 2026.",
      a_publication_date: "2026-05-01",
      b_title: "Extension of Comment Period",
      b_dates_text: "Comments now due September 15, 2026.",
      b_publication_date: "2026-05-20",
      shared_docket: true,
      shared_rin: false,
      explicit_reference: false,
    };
    const { verdict: writeVerdict, cached: writeCached } =
      await consultAdjudicator(sql, spy, consulted);
    assert(
      "H1 setup: first consult is a cache MISS that writes the row",
      writeCached === false && writeVerdict.classification === "affirm",
      JSON.stringify({ writeCached, writeVerdict }),
    );
    assert("H1 setup: the spy was actually called once", spy.calls === 1);

    // SAME logical input, DIFFERENT key order + an UNMODELED extra field smuggled in.
    const peeked = {
      explicit_reference: false,
      b_publication_date: "2026-05-20",
      shared_rin: false,
      b_dates_text: "Comments now due September 15, 2026.",
      a_publication_date: "2026-05-01",
      shared_docket: true,
      b_title: "Extension of Comment Period",
      a_dates_text: "Comments due August 1, 2026.",
      rulebook_version: RULEBOOK_VERSION,
      a_title: "Original Notice; Request for Comments",
      kind: "chain" as const,
      // an unmodeled field the schema strips on parse — must NOT change the hash.
      smuggled_extra: "should be ignored by AdjudicationInput.parse",
    } as unknown as AdjudicationInput;

    const peekHit = await peekAdjudication(sql, peeked);
    assert(
      "H1 peek HITs the consult-written row despite shuffled key order + an unmodeled extra field (hash identity holds)",
      peekHit !== null && peekHit.classification === "affirm",
      JSON.stringify(peekHit),
    );
    // And a SECOND consult of the shuffled+smuggled input is a cache HIT — never re-calls the adjudicator.
    const { cached: secondCached } = await consultAdjudicator(sql, spy, peeked);
    assert(
      "H1 a re-consult of the shuffled/smuggled input is a cache HIT — adjudicator NOT re-called (no re-call-forever drift)",
      secondCached === true && spy.calls === 1,
      `secondCached=${secondCached} calls=${spy.calls}`,
    );
    // Exactly ONE row persisted (one content hash for all three logically-identical inputs).
    const countRows = await sql<{ count: string }[]>`
      select count(*)::text as count from adjudications`;
    const count = countRows[0]!.count;
    assert(
      "H1 exactly ONE adjudications row for all logically-identical inputs (no shadow row from a drifted hash)",
      count === "1",
      count,
    );
  }

  // ── B1: THROW BUDGET BOUND at the unit level. 5 uncached pairs, cap=2, every call throws → total call
  // ATTEMPTS bounded by cap (each throw spends a budget unit), the other 3 defer, zero links, no reject.
  {
    await reset();
    const N = 5;
    const cap = 2;
    // Build N distinct ambiguous pairs directly as AmbiguousPair[] for the unit entrypoint.
    const pairs = [];
    for (let i = 0; i < N; i++) {
      const a = {
        ocd_id: `ocd-participation-window/federal/TA-${i}`,
        fr_observation_id: `obs-A-${i}`,
        fr_document_number: `2025-TA${i}`,
        docket_ids: [`DK-${i}`],
        rin: `2040-A${i}`,
        rins: [`2040-A${i}`],
        is_extension: false,
        is_correction: false,
        is_withdrawal: false,
        is_reopening: false,
        title: `Original ${i}`,
        publication_date: "2025-01-01",
        govinfo_url: null,
        dates_text: "Comments due Feb 1, 2025.",
        status: "open",
        resolved_close_utc: "2025-02-02T04:59:59Z",
      };
      const b = {
        ...a,
        ocd_id: `ocd-participation-window/federal/TB-${i}`,
        fr_observation_id: `obs-B-${i}`,
        fr_document_number: `2025-TB${i}`,
        rin: `2040-Z${i}`,
        rins: [`2040-Z${i}`],
        is_extension: true,
        title: `Extension ${i}`,
        publication_date: "2025-02-01",
        dates_text: `Extension ${i}. Comments now due March 2025.`,
      };
      pairs.push({ a, b });
    }
    const flaky = throwingAdjudicator("spy:allthrow");
    let rejected = false;
    let res: Awaited<ReturnType<typeof adjudicateAmbiguousPairs>> | undefined;
    try {
      res = await adjudicateAmbiguousPairs(sql, flaky, pairs, NOW, cap);
    } catch {
      rejected = true;
    }
    assert(
      "B1 throw bound: the function RESOLVES even when every call throws (never rejects)",
      !rejected && !!res,
    );
    assert(
      "B1 throw bound: total call ATTEMPTS ≤ cap — a flapping provider is NOT hammered across the whole surfaced set (attempts=cap, overflow deferred)",
      flaky.calls === cap,
      `attempts=${flaky.calls} cap=${cap}`,
    );
    assert(
      "B1 throw bound: counts honest — llmCalls=cap (each throw spent its unit), deferred=N-cap, zero links",
      !!res &&
        res.ambiguous === N &&
        res.llmCalls === cap &&
        res.deferred === N - cap &&
        res.cacheHits === 0 &&
        res.llmLinked === 0 &&
        res.links.length === 0,
      JSON.stringify(res),
    );
    // Nothing was cached (every call threw → consult persisted nothing → clean retry next cycle).
    const countRows = await sql<{ count: string }[]>`
      select count(*)::text as count from adjudications`;
    const count = countRows[0]!.count;
    assert(
      "B1 throw bound: a thrown consult persists NOTHING — zero cache rows (clean retry next cycle)",
      count === "0",
      count,
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== chain-adjudicate-starvation results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
