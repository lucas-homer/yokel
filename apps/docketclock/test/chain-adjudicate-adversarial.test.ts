/**
 * chain-adjudicate-adversarial.test.ts — the ADVERSARY's regression lock on #31 Slice 3b (the FIRST slice
 * where the LLM can change a classification). It hammers the six non-negotiable invariants from angles the
 * happy-path suite does not:
 *
 *   I2 PURITY        — classify / buildChainConflict / chainAmbiguousPairs are pure + deterministic; double
 *                      call + shuffled input ⇒ byte-identical. chain.ts imports no db/consult/adjudicator.
 *   I3 ENVELOPE      — adjudicateAmbiguousPairs: ONLY `affirm` links. reject / uncertain / THROW / cap=0 →
 *                      zero links; a throw is isolated and the function still resolves (never rejects). An
 *                      affirm in the SAME batch as a throw still links (one bad call ≠ batch abort).
 *   I4 HONESTY       — an affirmed link carries `llm_corroborated` ALONGSIDE its type flag(s); a
 *                      deterministic confident link NEVER carries `llm_corroborated`. Both directions.
 *   I5 BOUNDED       — chainMaxEscalations: NaN / negative / zero / float env → sane positive default (25),
 *                      never escalate-everything or crash. cap=0 / cap>surfaced honest counts.
 *   I6 CACHED        — two DIFFERENT ambiguous pairs get DIFFERENT content hashes (no replay cross-talk):
 *                      pair X's affirm must not be replayed for pair Y. (DB-backed.)
 *   LEAKS            — shared-RIN pair never leaks into the ambiguous set (would double-adjudicate); a
 *                      denied land-withdrawal pair never leaks into the ambiguous set (deny BEFORE escalate);
 *                      multi_target_notice is NEVER on an LLM-promoted link.
 *
 * Pure attacks run anywhere. The consult/cache attacks (I3 isolation, I6) need PG18 and are SKIPPED when
 * DATABASE_URL is unset. Repo test style: hand-rolled assert, out[] accumulator, failures counter, exit.
 */
import type { AdjudicationInput, AdjudicationVerdict } from "@yokel/contracts";
import {
  buildChainConflict,
  chainAmbiguousPairs,
  chainReconcile,
  classify,
  type ChainCandidate,
} from "../src/reconcile/chain.js";
import {
  adjudicateAmbiguousPairs,
  chainMaxEscalations,
} from "../src/reconcile/chain-adjudicate.js";
import type { Adjudicator } from "../src/adjudicator/port.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = ""): void {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const NOW = new Date("2026-06-01T00:00:00Z");

function original(over: Partial<ChainCandidate> = {}): ChainCandidate {
  return {
    ocd_id: "ocd-participation-window/federal/2025-00001",
    fr_observation_id: "obs-A",
    fr_document_number: "2025-00001",
    docket_ids: ["EPA-HQ-OW-2025-0001"],
    rin: "2040-AA01",
    rins: ["2040-AA01"],
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    title: "Notice of Proposed Rulemaking; Request for Comments",
    publication_date: "2025-01-01",
    govinfo_url:
      "https://www.govinfo.gov/content/pkg/FR-2025-01-01/html/2025-00001.htm",
    dates_text: "Comments must be received on or before February 1, 2025.",
    status: "open",
    resolved_close_utc: "2025-02-02T04:59:59Z",
    ...over,
  };
}

function amendment(over: Partial<ChainCandidate> = {}): ChainCandidate {
  return {
    ocd_id: "ocd-participation-window/federal/2025-00002",
    fr_observation_id: "obs-B",
    fr_document_number: "2025-00002",
    docket_ids: ["EPA-HQ-OW-2025-0001"],
    rin: "2040-AA01",
    rins: ["2040-AA01"],
    is_extension: true,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    title: "Extension of Comment Period",
    publication_date: "2025-02-01",
    govinfo_url:
      "https://www.govinfo.gov/content/pkg/FR-2025-02-01/html/2025-00002.htm",
    dates_text:
      "The comment period is extended. Comments now due March 1, 2025.",
    status: "open",
    resolved_close_utc: "2025-03-02T04:59:59Z",
    ...over,
  };
}

/** An ambiguous pair: disjoint RINs, no explicit reference, structural rules pass. */
function ambiguousPair(): { a: ChainCandidate; b: ChainCandidate } {
  const a = original({ rin: "2040-AA01", rins: ["2040-AA01"] });
  const b = amendment({ rin: "2040-ZZ99", rins: ["2040-ZZ99"] });
  return { a, b };
}

/** A spy returning a FIXED verdict, counting calls. */
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

// ───────────────────────────────────────────────────────────────────────────────────────────────────
// I2 — PURITY / DETERMINISM (no DB).
// ───────────────────────────────────────────────────────────────────────────────────────────────────

// classify is a pure function of (b, multiTarget): same input ⇒ byte-identical, never carries
// llm_corroborated, and multiTarget=false omits multi_target_notice.
{
  const b = amendment({ is_extension: true });
  const c1 = classify(b, false);
  const c2 = classify(b, false);
  assert(
    "I2 classify pure: same input ⇒ byte-identical output",
    JSON.stringify(c1) === JSON.stringify(c2),
    JSON.stringify(c1),
  );
  assert(
    "I4 classify NEVER injects llm_corroborated (provenance is appended OUTSIDE classify)",
    !c1.includes("llm_corroborated"),
    JSON.stringify(c1),
  );
  assert(
    "I2 classify(multiTarget=false) omits multi_target_notice",
    !classify(b, false).includes("multi_target_notice"),
    JSON.stringify(classify(b, false)),
  );
  assert(
    "I2 classify(multiTarget=true) adds multi_target_notice",
    classify(b, true).includes("multi_target_notice"),
    JSON.stringify(classify(b, true)),
  );
}

// chainAmbiguousPairs is pure: double call + shuffled input ⇒ byte-identical (stable sort).
{
  const a1 = original({
    ocd_id: "ocd-participation-window/federal/2024-30637",
    fr_observation_id: "obs-A1",
    fr_document_number: "2024-30637",
    docket_ids: ["D1"],
    rins: ["2040-RA01"],
    publication_date: "2024-12-26",
  });
  const a2 = original({
    ocd_id: "ocd-participation-window/federal/2025-00734",
    fr_observation_id: "obs-A2",
    fr_document_number: "2025-00734",
    docket_ids: ["D2"],
    rins: ["2040-RA02"],
    publication_date: "2025-01-15",
  });
  const b = amendment({
    docket_ids: ["D1", "D2"],
    rins: ["2040-ZZ99"],
    publication_date: "2025-02-20",
    dates_text: "The comment period is extended. Comments now due March 2025.",
  });
  const s1 = chainAmbiguousPairs([a1, a2, b], NOW);
  const s1again = chainAmbiguousPairs([a1, a2, b], NOW);
  const s2 = chainAmbiguousPairs([b, a2, a1], NOW);
  assert(
    "I2 chainAmbiguousPairs pure: same input twice ⇒ byte-identical",
    JSON.stringify(s1) === JSON.stringify(s1again),
    String(s1.length),
  );
  assert(
    "I2 chainAmbiguousPairs deterministic under shuffle ⇒ byte-identical",
    s1.length === 2 && JSON.stringify(s1) === JSON.stringify(s2),
    `${s1.length} vs ${s2.length}`,
  );
}

// buildChainConflict refuses A===B (would violate the contract superRefine) — a self-amendment can never
// become a published link even via the shared builder the LLM path uses.
{
  const a = original();
  let threw = false;
  try {
    buildChainConflict(a, a, classify(a, false), NOW);
  } catch {
    threw = true;
  }
  assert("I2 buildChainConflict(A,A) throws (no self-link can publish)", threw);
}

// ───────────────────────────────────────────────────────────────────────────────────────────────────
// LEAKS — the ambiguous set must be EXACTLY the under-linked tail. A confident (shared-RIN) pair or a
// denied land-withdrawal pair leaking in would be DOUBLE-ADJUDICATED / a known-FP escalated to the LLM.
// ───────────────────────────────────────────────────────────────────────────────────────────────────

// Shared-RIN pair: confident link, MUST NOT appear in the ambiguous set (mutual exclusivity).
{
  const a = original({ rins: ["2040-SHARED"] });
  const b = amendment({ rins: ["2040-SHARED"] });
  const conf = chainReconcile([a, b], NOW);
  const amb = chainAmbiguousPairs([a, b], NOW);
  assert(
    "LEAK shared-RIN: confident link AND empty ambiguous set (mutually exclusive, no double-adjudicate)",
    conf.length === 1 && amb.length === 0,
    `conf=${conf.length} amb=${amb.length}`,
  );
}

// Denied land-withdrawal (BLM 2023-27468 trap): disjoint RIN so it WOULD be ambiguous, but the deny-list
// must suppress it BEFORE escalation. Escalating a known false-positive to the LLM is a regression.
{
  const a = original({ rins: ["2040-AA01"] });
  const b = amendment({
    is_extension: false,
    is_withdrawal: true,
    rins: ["2040-ZZ99"], // disjoint → would be ambiguous if not denied
    title: "Public Land Order No. 7963; Withdrawal of Public Lands; Colorado",
    dates_text: null,
  });
  const conf = chainReconcile([a, b], NOW);
  const amb = chainAmbiguousPairs([a, b], NOW);
  assert(
    "LEAK deny-before-escalate: denied land-withdrawal pair NEVER surfaces as ambiguous (no LLM escalation of a known FP)",
    conf.length === 0 && amb.length === 0,
    `conf=${conf.length} amb=${amb.length}`,
  );
}

// ───────────────────────────────────────────────────────────────────────────────────────────────────
// I5 — BOUNDED env resolution (pure). NaN / negative / zero / float ⇒ the sane positive default (25),
// never escalate-everything and never crash.
// ───────────────────────────────────────────────────────────────────────────────────────────────────
{
  const D = 25;
  const cases: Array<[string | undefined, number]> = [
    [undefined, D],
    ["", D],
    ["not-a-number", D],
    ["NaN", D],
    ["0", D],
    ["-5", D],
    ["2.5", D], // non-integer floors to default, not 2
    ["  ", D],
    ["10", 10],
    ["1", 1],
  ];
  for (const [raw, want] of cases) {
    const env =
      raw === undefined ? {} : { CHAIN_MAX_ESCALATIONS_PER_CYCLE: raw };
    const got = chainMaxEscalations(env as NodeJS.ProcessEnv);
    assert(
      `I5 chainMaxEscalations(${JSON.stringify(raw)}) ⇒ ${want}`,
      got === want,
      String(got),
    );
  }
}

// ───────────────────────────────────────────────────────────────────────────────────────────────────
// I3 + I4 — CONSERVATIVE ENVELOPE + HONESTY via adjudicateAmbiguousPairs against a REAL throwaway PG18.
// (consultAdjudicator touches the DB cache; a high-fidelity envelope test goes through it.)
// I6 — content-hash distinguishes two different ambiguous pairs (no replay cross-talk).
// ───────────────────────────────────────────────────────────────────────────────────────────────────
if (!process.env.DATABASE_URL) {
  console.log(
    "\n=== chain-adjudicate-adversarial results ===\n" +
      out.join("\n") +
      "\n  (DB-backed envelope/cache attacks SKIPPED: DATABASE_URL unset)\n" +
      `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
  );
  process.exit(failures === 0 ? 0 : 1);
}

const { createClient } = await import("../src/db/client.js");
const { runMigrations } = await import("../src/db/migrate.js");
const sql = createClient();

async function reset(): Promise<void> {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
}

/** Build N ambiguous pairs over DISTINCT dockets / docs so each is a distinct content hash. */
function nDistinctAmbiguousPairs(
  n: number,
): { a: ChainCandidate; b: ChainCandidate }[] {
  const pairs: { a: ChainCandidate; b: ChainCandidate }[] = [];
  for (let i = 0; i < n; i++) {
    const a = original({
      ocd_id: `ocd-participation-window/federal/A-${i}`,
      fr_observation_id: `obs-A-${i}`,
      fr_document_number: `2025-A${i}`,
      docket_ids: [`DOCK-${i}`],
      rins: [`2040-A${i}`],
      title: `Original notice ${i}; request for comments`,
    });
    const b = amendment({
      ocd_id: `ocd-participation-window/federal/B-${i}`,
      fr_observation_id: `obs-B-${i}`,
      fr_document_number: `2025-B${i}`,
      docket_ids: [`DOCK-${i}`],
      rins: [`2040-Z${i}`], // disjoint with A-i
      title: `Extension of comment period ${i}`,
      dates_text: `Extension ${i}. Comments now due later.`,
    });
    pairs.push({ a, b });
  }
  return pairs;
}

try {
  // I3: reject / uncertain ⇒ ZERO links, spy IS consulted (escalated), nothing promoted.
  for (const cls of ["reject", "uncertain"] as const) {
    await reset();
    const spy = spyAdjudicator(`spy:${cls}`, {
      classification: cls,
      rationale: cls,
    });
    const res = await adjudicateAmbiguousPairs(
      sql,
      spy,
      [ambiguousPair()],
      NOW,
      25,
    );
    assert(
      `I3 envelope: ${cls} ⇒ llmCalls=1 but llmLinked=0 (no link)`,
      res.llmCalls === 1 && res.llmLinked === 0 && res.links.length === 0,
      JSON.stringify(res),
    );
  }

  // I3: affirm ⇒ exactly one link. I4: that link carries the type flag AND llm_corroborated, and NEVER
  // multi_target_notice (LLM-promoted links are built multiTarget=false).
  {
    await reset();
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "yes",
    });
    const res = await adjudicateAmbiguousPairs(
      sql,
      spy,
      [ambiguousPair()],
      NOW,
      25,
    );
    const link = res.links[0];
    assert(
      "I3 envelope: affirm ⇒ exactly one promoted link",
      res.llmLinked === 1 && res.links.length === 1,
      JSON.stringify(res),
    );
    assert(
      "I4 honesty: promoted link carries extension_chain_unresolved AND llm_corroborated",
      !!link &&
        link.conflict_flags.includes("extension_chain_unresolved") &&
        link.conflict_flags.includes("llm_corroborated"),
      link ? link.conflict_flags.join(",") : "no link",
    );
    assert(
      "I4 honesty: promoted link NEVER carries multi_target_notice (multiTarget=false by construction)",
      !!link && !link.conflict_flags.includes("multi_target_notice"),
      link ? link.conflict_flags.join(",") : "no link",
    );
  }

  // I4 (other direction): a DETERMINISTIC confident link NEVER carries llm_corroborated.
  {
    const a = original({ rins: ["2040-SHARED"] });
    const b = amendment({ rins: ["2040-SHARED"] });
    const conf = chainReconcile([a, b], NOW);
    assert(
      "I4 honesty: deterministic confident link NEVER carries llm_corroborated",
      conf.length === 1 &&
        !conf[0]!.conflict_flags.includes("llm_corroborated"),
      conf.length === 1 ? conf[0]!.conflict_flags.join(",") : "no link",
    );
  }

  // I3: a THROW is isolated — the function RESOLVES (never rejects), and an affirm pair in the SAME batch
  // (ordered AFTER the thrower) still links. One bad call must not abort the batch or drop the good link.
  {
    await reset();
    // Two distinct ambiguous pairs: pair0 will throw, pair1 will affirm. The adjudicator throws on its
    // FIRST call only, affirms after — so order-sensitivity of isolation is exercised.
    const pairs = nDistinctAmbiguousPairs(2);
    let n = 0;
    const flaky: Adjudicator & { calls: number } = {
      id: "spy:flaky",
      calls: 0,
      async adjudicate(_i: AdjudicationInput): Promise<AdjudicationVerdict> {
        flaky.calls++;
        n++;
        if (n === 1) throw new Error("first call down");
        return { classification: "affirm", rationale: "ok" };
      },
    };
    let rejected = false;
    let res: Awaited<ReturnType<typeof adjudicateAmbiguousPairs>> | undefined;
    try {
      res = await adjudicateAmbiguousPairs(sql, flaky, pairs, NOW, 25);
    } catch {
      rejected = true;
    }
    assert(
      "I3 isolation: a thrown consult does NOT reject the batch (function resolves)",
      !rejected && !!res,
    );
    assert(
      "I3 isolation: thrower drops its pair (no link) but the OTHER affirm still links (1 link, 2 fresh llmCalls — throw spent its budget unit)",
      !!res &&
        res.llmCalls === 2 &&
        res.llmLinked === 1 &&
        res.links.length === 1,
      JSON.stringify(res),
    );
    // The promoted link is the affirmed (second) pair, not the thrower.
    assert(
      "I3 isolation: the surviving link is the affirmed pair (B-1), never the thrown pair (B-0)",
      !!res &&
        res.links.length === 1 &&
        res.links[0]!.ocd_id_b === "ocd-participation-window/federal/B-1",
      res && res.links[0] ? res.links[0].ocd_id_b : "none",
    );
  }

  // I3: cap=0 ⇒ NOTHING consulted (spy never called), everything counted capped, no crash, no links.
  {
    await reset();
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "yes",
    });
    const pairs = nDistinctAmbiguousPairs(3);
    const res = await adjudicateAmbiguousPairs(sql, spy, pairs, NOW, 0);
    assert(
      "I3/I5 cap=0: no fresh calls, all 3 uncached pairs deferred, zero links, spy NEVER called",
      res.ambiguous === 3 &&
        res.llmCalls === 0 &&
        res.deferred === 3 &&
        res.cacheHits === 0 &&
        res.llmLinked === 0 &&
        spy.calls === 0,
      `${JSON.stringify(res)} calls=${spy.calls}`,
    );
  }

  // I3: a NEGATIVE cap passed DIRECTLY to the unit (bypassing chainMaxEscalations) must NOT escalate
  // everything — Math.max(0,cap) floors to 0. (Defense in depth: even if a caller botches the cap.)
  {
    await reset();
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "yes",
    });
    const pairs = nDistinctAmbiguousPairs(2);
    const res = await adjudicateAmbiguousPairs(sql, spy, pairs, NOW, -10);
    assert(
      "I3 negative cap floors to 0 (never escalates everything): llmCalls=0, links=0, spy uncalled",
      res.llmCalls === 0 && res.llmLinked === 0 && spy.calls === 0,
      `${JSON.stringify(res)} calls=${spy.calls}`,
    );
  }

  // I5: cap > surfaced ⇒ all escalated, none capped (no off-by-one inflation).
  {
    await reset();
    const spy = spyAdjudicator("spy:uncertain", {
      classification: "uncertain",
      rationale: "abstain",
    });
    const pairs = nDistinctAmbiguousPairs(2);
    const res = await adjudicateAmbiguousPairs(sql, spy, pairs, NOW, 100);
    assert(
      "I5 cap>surfaced: llmCalls=all, deferred=0 (counts honest)",
      res.ambiguous === 2 &&
        res.llmCalls === 2 &&
        res.deferred === 0 &&
        spy.calls === 2,
      `${JSON.stringify(res)} calls=${spy.calls}`,
    );
  }

  // I6: two DIFFERENT ambiguous pairs must NOT collide on the content hash. Affirm pair0, then in a SECOND
  // call adjudicate BOTH pairs with a spy that REJECTS: if pair1 wrongly replayed pair0's cached AFFIRM it
  // would link (BUG); with distinct hashes pair1 is a FRESH reject ⇒ NOT linked, pair0 replays its affirm.
  {
    await reset();
    const pairs = nDistinctAmbiguousPairs(2);
    // Round 1: only pair0, affirm and cache it.
    const spy1 = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "p0",
    });
    const r1 = await adjudicateAmbiguousPairs(sql, spy1, [pairs[0]!], NOW, 25);
    assert(
      "I6 setup: pair0 affirmed + cached",
      r1.llmLinked === 1 && spy1.calls === 1,
    );

    // Round 2: adjudicate BOTH. pair0 must REPLAY (no call); pair1 must be a FRESH call (distinct hash).
    const spy2 = spyAdjudicator("spy:reject", {
      classification: "reject",
      rationale: "p1-fresh-reject",
    });
    const r2 = await adjudicateAmbiguousPairs(sql, spy2, pairs, NOW, 25);
    assert(
      "I6 no hash collision: pair0 is a cache HIT replaying its affirm (no call), pair1 is a FRESH reject (1 call, NOT linked)",
      r2.cacheHits === 1 && // pair0 peek-hit (free, no budget)
        r2.llmCalls === 1 && // only pair1 was a fresh call
        r2.deferred === 0 &&
        r2.llmLinked === 1 && // only pair0 (cached affirm) links
        spy2.calls === 1 && // only pair1 reached the adjudicator (pair0 was a cache hit)
        r2.links.length === 1 &&
        r2.links[0]!.ocd_id_b === "ocd-participation-window/federal/B-0",
      JSON.stringify({
        cacheHits: r2.cacheHits,
        llmCalls: r2.llmCalls,
        llmLinked: r2.llmLinked,
        calls: spy2.calls,
      }),
    );
    // And the cache holds TWO distinct rows (two distinct content hashes) — pair0 affirm + pair1 reject.
    const rows = await sql<{ count: string }[]>`
      select count(*)::text as count from adjudications
    `;
    const count = rows[0]!.count;
    assert(
      "I6 two distinct content hashes persisted (no collision overwrote a row)",
      count === "2",
      count,
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== chain-adjudicate-adversarial results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
