/**
 * adjudicator.test.ts — Slice 2 of the RuleBox/classifier feature: the provider-agnostic
 * adjudication subsystem (LLM ambiguous-tail escalation machinery), built + proven in ISOLATION.
 * NO real LLM provider here (that's Slice 3/Gemini); the NullAdjudicator + a SPY double stand in.
 *
 * This subsystem is BEHAVIOR-PRESERVING for the live pipeline — nothing in the parse/reconcile hot
 * paths calls it. These tests pin the seam:
 *
 *   • CONTENT HASH determinism — same logical input (keys in different insertion order) hashes
 *     identically; changing ANY field (incl. rulebook_version) changes the hash; the hash is 64-hex
 *     and passes PayloadHash.parse; adjudicator_id is NOT an input field so it cannot affect the hash.
 *   • CACHE MISS → call + persist — a SPY adapter is called once; the row persists with the right
 *     content_hash and `spy:...@<rulebook_version>` provenance.
 *   • CACHE HIT → NO re-call (replay determinism, PER ADJUDICATOR) — a second consult with the SAME
 *     adjudicator returns the STORED verdict and the spy call count stays at 1.
 *   • CACHE KEY = (content_hash, adjudicator_id) (migration 0009) — a DIFFERENT adjudicator on the SAME
 *     input is a cache MISS and is consulted; both rows coexist; neither shadows the other.
 *   • uncertain IS cached & replayed per-adjudicator — an abstaining real adjudicator's `uncertain` is
 *     cached under its id and replayed on the 2nd consult (no re-call), exactly one row.
 *   • REGRESSION (the live bug) — a pre-seeded `null:abstain@<rb>` uncertain row does NOT shadow a real
 *     adjudicator: consult with a real spy on that same input CALLS it and returns its verdict.
 *   • NullAdjudicator — returns `uncertain` for BOTH a notice- and a chain-kind input; id="null:abstain".
 *   • WRITE-ONCE PER (content_hash, adjudicator_id) — a direct second INSERT of the same key with a
 *     different verdict does NOT change the stored row (ON CONFLICT DO NOTHING); consult still returns first.
 *   • peek keys by adjudicator — peek(A) returns A's verdict; peek(B) for the same input (no B row) is null.
 *   • BOTH KINDS — a notice input and a chain input both hash, persist, and round-trip AdjudicationRecord.parse.
 *
 * The pure-hashing assertions run WITHOUT postgres; the cache assertions need the throwaway container.
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import {
  AdjudicationRecord,
  PayloadHash,
  type AdjudicationInput,
  type AdjudicationVerdict,
} from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { adjudicationContentHash } from "../src/adjudicator/content-hash.js";
import {
  NullAdjudicator,
  NULL_ADJUDICATOR_ID,
} from "../src/adjudicator/null-adjudicator.js";
import {
  consultAdjudicator,
  peekAdjudication,
} from "../src/adjudicator/consult.js";
import type { Adjudicator } from "../src/adjudicator/port.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const RULEBOOK = "rulebox-2026-06-18";

const noticeInput: AdjudicationInput = {
  kind: "notice",
  rulebook_version: RULEBOOK,
  flag_key: "withdrawal",
  text: "Withdrawal of Land from Mineral Entry; Notice of Realty Action",
};

const chainInput: AdjudicationInput = {
  kind: "chain",
  rulebook_version: RULEBOOK,
  a_title: "Original Rule on Widget Safety",
  a_dates_text: "Comments due by 2025-03-01",
  a_publication_date: "2025-01-15",
  b_title: "Extension of Comment Period for Widget Safety",
  b_dates_text: "Comments now due 2025-04-01",
  b_publication_date: "2025-02-20",
  shared_docket: true,
  shared_rin: true,
  explicit_reference: false,
};

// A SPY adapter: counts adjudicate() calls and returns a FIXED verdict. id is provenance-significant.
function spyAdjudicator(
  id: string,
  verdict: AdjudicationVerdict,
): Adjudicator & { calls: number } {
  const spy = {
    id,
    calls: 0,
    async adjudicate(_input: AdjudicationInput): Promise<AdjudicationVerdict> {
      spy.calls++;
      return verdict;
    },
  };
  return spy;
}

// ── PURE HASHING (no DB) ─────────────────────────────────────────────────────────────────────────
{
  // same logical input, keys inserted in a DIFFERENT order — must hash identically (canonical/sorted).
  const reordered: AdjudicationInput = {
    text: "Withdrawal of Land from Mineral Entry; Notice of Realty Action",
    flag_key: "withdrawal",
    rulebook_version: RULEBOOK,
    kind: "notice",
  } as AdjudicationInput;
  const h1 = adjudicationContentHash(noticeInput);
  const h2 = adjudicationContentHash(reordered);
  assert(
    "content hash is stable across key insertion order",
    h1 === h2,
    `${h1.slice(0, 12)} vs ${h2.slice(0, 12)}`,
  );

  assert(
    "content hash is 64-hex and passes PayloadHash.parse",
    /^[a-f0-9]{64}$/.test(h1) && PayloadHash.parse(h1) === h1,
    h1,
  );

  // changing rulebook_version re-keys (the rulebook is part of cache identity).
  const bumped = { ...noticeInput, rulebook_version: "rulebox-2099-01-01" };
  assert(
    "changing rulebook_version changes the hash (re-adjudicate on rulebook change)",
    adjudicationContentHash(bumped) !== h1,
  );

  // changing any other field re-keys.
  const otherText = { ...noticeInput, text: "Something else entirely" };
  assert(
    "changing the text field changes the hash",
    adjudicationContentHash(otherText) !== h1,
  );

  // a chain input hashes too and differs from the notice hash.
  const ch = adjudicationContentHash(chainInput);
  assert(
    "chain input hashes to a distinct 64-hex digest",
    /^[a-f0-9]{64}$/.test(ch) && ch !== h1,
    ch,
  );
}

// ── NullAdjudicator (no DB) ──────────────────────────────────────────────────────────────────────
{
  const nul = new NullAdjudicator();
  assert("NullAdjudicator id is 'null:abstain'", nul.id === "null:abstain");
  const vN = await nul.adjudicate(noticeInput);
  assert(
    "NullAdjudicator abstains (uncertain) on a notice input",
    vN.classification === "uncertain" && vN.rationale.length > 0,
    vN.rationale,
  );
  const vC = await nul.adjudicate(chainInput);
  assert(
    "NullAdjudicator abstains (uncertain) on a chain input",
    vC.classification === "uncertain",
  );
}

// ── DB-backed cache tests ────────────────────────────────────────────────────────────────────────
if (!process.env.DATABASE_URL) {
  out.push("  SKIP  DB-backed cache tests (DATABASE_URL not set)");
} else {
  const sql = createClient();
  try {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    const applied = await runMigrations(sql);
    assert(
      "migration 0008 applies (adjudications cache table)",
      applied.includes("0008_adjudications_cache.sql"),
      applied.join(", "),
    );
    assert(
      "migration 0009 applies (per-adjudicator composite PK)",
      applied.includes("0009_adjudications_per_adjudicator_key.sql"),
      applied.join(", "),
    );

    // CACHE MISS → call + persist.
    const affirm: AdjudicationVerdict = {
      classification: "affirm",
      rationale: "spy says yes",
    };
    const spy = spyAdjudicator("spy:v1", affirm);
    const r1 = await consultAdjudicator(sql, spy, noticeInput);
    assert(
      "first consult is a cache MISS (cached:false)",
      r1.cached === false,
      String(r1.cached),
    );
    assert(
      "cache miss CALLS the adjudicator exactly once",
      spy.calls === 1,
      String(spy.calls),
    );
    assert(
      "cache miss returns the adapter verdict (affirm)",
      r1.verdict.classification === "affirm",
    );

    const expectHash = adjudicationContentHash(noticeInput);
    const stored = await sql<
      {
        content_hash: string;
        adjudicator_id: string;
        verdict: AdjudicationVerdict;
      }[]
    >`select content_hash, adjudicator_id, verdict from adjudications where content_hash = ${expectHash}`;
    assert(
      "row persisted under the canonical content_hash",
      stored.length === 1 && stored[0]!.content_hash === expectHash,
      stored[0]?.content_hash,
    );
    assert(
      "row carries provenance adjudicator_id 'spy:v1@<rulebook_version>'",
      stored[0]!.adjudicator_id === `spy:v1@${RULEBOOK}`,
      stored[0]?.adjudicator_id,
    );

    // CACHE HIT → NO re-call (replay determinism), same spy.
    const r2 = await consultAdjudicator(sql, spy, noticeInput);
    assert(
      "second consult is a cache HIT (cached:true)",
      r2.cached === true,
      String(r2.cached),
    );
    assert(
      "cache hit does NOT re-call the adjudicator (calls stays at 1)",
      spy.calls === 1,
      String(spy.calls),
    );
    assert(
      "cache hit returns the STORED verdict",
      r2.verdict.classification === "affirm",
    );

    // DIFFERENT ADJUDICATOR, SAME content_hash — the cache key is (content_hash, adjudicator_id), so a
    // distinct adjudicator is a cache MISS and is consulted; its verdict coexists under its own key and
    // does NOT replay spy1's. (This is the core fix: spy1's verdict can never shadow spy2's.)
    const reject: AdjudicationVerdict = {
      classification: "reject",
      rationale: "spy2 says no",
    };
    const spy2 = spyAdjudicator("spy:v2", reject);
    const r3 = await consultAdjudicator(sql, spy2, noticeInput);
    assert(
      "a DIFFERENT adjudicator on the same content_hash is a cache MISS (consulted, not shadowed)",
      r3.cached === false && r3.verdict.classification === "reject",
      `cached=${r3.cached} ${r3.verdict.classification}`,
    );
    assert(
      "the second adjudicator IS called (its verdict is not shadowed by spy:v1's affirm)",
      spy2.calls === 1,
      String(spy2.calls),
    );
    // Both rows coexist for the SAME content_hash, keyed by distinct adjudicator_id.
    const bothRows = await sql<{ adjudicator_id: string }[]>`
      select adjudicator_id from adjudications where content_hash = ${expectHash} order by adjudicator_id`;
    assert(
      "both adjudicators' rows coexist under the same content_hash (distinct adjudicator_id)",
      bothRows.length === 2 &&
        bothRows[0]!.adjudicator_id === `spy:v1@${RULEBOOK}` &&
        bothRows[1]!.adjudicator_id === `spy:v2@${RULEBOOK}`,
      bothRows.map((r) => r.adjudicator_id).join(", "),
    );
    // peek keys by adjudicator: peek(spy1) → affirm, peek(spy2) → reject; neither shadows the other.
    const peek1 = await peekAdjudication(sql, spy, noticeInput);
    const peek2 = await peekAdjudication(sql, spy2, noticeInput);
    assert(
      "peek(spy:v1) returns affirm; peek(spy:v2) returns reject (peek keys by adjudicator)",
      peek1?.classification === "affirm" && peek2?.classification === "reject",
      `peek1=${peek1?.classification} peek2=${peek2?.classification}`,
    );

    // WRITE-ONCE PER (content_hash, adjudicator_id) — a direct second INSERT of the SAME key (spy:v1) with a
    // different verdict is ignored (ON CONFLICT (content_hash, adjudicator_id) DO NOTHING).
    await sql`
      insert into adjudications (content_hash, input, verdict, adjudicator_id)
      values (${expectHash}, ${sql.json(noticeInput as never)}::jsonb,
              ${sql.json(reject as never)}::jsonb, ${"spy:v1@" + RULEBOOK})
      on conflict (content_hash, adjudicator_id) do nothing
    `;
    const afterWriteOnce = await sql<
      { verdict: AdjudicationVerdict }[]
    >`select verdict from adjudications where content_hash = ${expectHash} and adjudicator_id = ${"spy:v1@" + RULEBOOK}`;
    assert(
      "write-once: direct re-INSERT of the same (hash, adjudicator_id) with a different verdict does NOT change the row",
      afterWriteOnce[0]!.verdict.classification === "affirm",
      afterWriteOnce[0]?.verdict.classification,
    );
    const r4 = await consultAdjudicator(sql, spy, noticeInput);
    assert(
      "consult with spy:v1 still returns its FIRST verdict (affirm) after a write-once collision",
      r4.cached === true && r4.verdict.classification === "affirm",
    );

    // BOTH KINDS — a chain input also hashes, persists, and round-trips AdjudicationRecord.parse.
    const chainVerdict: AdjudicationVerdict = {
      classification: "reject",
      rationale: "B does not amend A",
    };
    const chainSpy = spyAdjudicator("spy:chain", chainVerdict);
    const rc = await consultAdjudicator(sql, chainSpy, chainInput);
    assert(
      "chain input: cache miss, adapter called, reject verdict returned",
      rc.cached === false &&
        chainSpy.calls === 1 &&
        rc.verdict.classification === "reject",
    );
    const chainRow = await sql<
      Record<string, unknown>[]
    >`select content_hash, input, verdict, adjudicator_id, created_at from adjudications where content_hash = ${adjudicationContentHash(chainInput)}`;
    const parsed = AdjudicationRecord.safeParse({
      ...chainRow[0],
      created_at: (chainRow[0]!.created_at as Date).toISOString(),
    });
    assert(
      "chain row round-trips AdjudicationRecord.parse",
      parsed.success,
      parsed.success ? "" : JSON.stringify(parsed.error.issues),
    );
    assert(
      "round-tripped chain record preserves kind='chain'",
      parsed.success && parsed.data.input.kind === "chain",
    );

    // notice row also round-trips (BOTH KINDS). Scope to spy:v1's row (two adjudicators share this hash now).
    const noticeRow = await sql<
      Record<string, unknown>[]
    >`select content_hash, input, verdict, adjudicator_id, created_at from adjudications where content_hash = ${expectHash} and adjudicator_id = ${"spy:v1@" + RULEBOOK}`;
    const parsedNotice = AdjudicationRecord.safeParse({
      ...noticeRow[0],
      created_at: (noticeRow[0]!.created_at as Date).toISOString(),
    });
    assert(
      "notice row round-trips AdjudicationRecord.parse",
      parsedNotice.success,
      parsedNotice.success ? "" : JSON.stringify(parsedNotice.error.issues),
    );

    // ── uncertain IS cached & replayed PER ADJUDICATOR (no special-casing, no eviction). A real adjudicator
    // that abstains has its `uncertain` cached under ITS id; the 2nd consult is a HIT (adjudicator not
    // re-called) and exactly one row exists. This is what makes an uncertain pair a free peek-hit (not a
    // re-consult) on later cycles.
    {
      const uncInput: AdjudicationInput = {
        kind: "notice",
        rulebook_version: RULEBOOK,
        flag_key: "withdrawal",
        text: "an input a real adjudicator abstains on",
      };
      const uncSpy = spyAdjudicator("spy:uncertain", {
        classification: "uncertain",
        rationale: "real adjudicator could not decide",
      });
      const u1 = await consultAdjudicator(sql, uncSpy, uncInput);
      assert(
        "uncertain: first consult is a MISS that persists the uncertain verdict",
        u1.cached === false &&
          u1.verdict.classification === "uncertain" &&
          uncSpy.calls === 1,
        `${JSON.stringify(u1)} calls=${uncSpy.calls}`,
      );
      const u2 = await consultAdjudicator(sql, uncSpy, uncInput);
      assert(
        "uncertain IS cached & replayed: 2nd consult is a HIT, adjudicator NOT re-called (calls stays 1)",
        u2.cached === true &&
          u2.verdict.classification === "uncertain" &&
          uncSpy.calls === 1,
        `${JSON.stringify(u2)} calls=${uncSpy.calls}`,
      );
      const uncRows = await sql<{ count: string }[]>`
        select count(*)::text as count from adjudications
        where content_hash = ${adjudicationContentHash(uncInput)}`;
      assert(
        "uncertain: exactly ONE row persisted for (input, adjudicator)",
        uncRows[0]!.count === "1",
        uncRows[0]!.count,
      );
    }

    // ── DIFFERENT ADJUDICATORS COEXIST for the SAME content_hash (the core fix). Adjudicator A (id "a:x",
    // affirm) and B (id "b:y", reject) on the SAME input → BOTH rows persist; peek(A)=affirm, peek(B)=reject;
    // neither shadows the other; peek(some-third-adjudicator) with no row is null.
    {
      const sharedInput: AdjudicationInput = {
        kind: "notice",
        rulebook_version: RULEBOOK,
        flag_key: "extension",
        text: "same input judged by two adjudicators",
      };
      const adjA = spyAdjudicator("a:x", {
        classification: "affirm",
        rationale: "A affirms",
      });
      const adjB = spyAdjudicator("b:y", {
        classification: "reject",
        rationale: "B rejects",
      });
      const ra = await consultAdjudicator(sql, adjA, sharedInput);
      const rb = await consultAdjudicator(sql, adjB, sharedInput);
      assert(
        "coexist: A consulted → affirm (miss); B consulted → reject (miss); both fresh, neither shadowed",
        ra.cached === false &&
          ra.verdict.classification === "affirm" &&
          rb.cached === false &&
          rb.verdict.classification === "reject" &&
          adjA.calls === 1 &&
          adjB.calls === 1,
        `${JSON.stringify({ ra, rb })} a=${adjA.calls} b=${adjB.calls}`,
      );
      const sharedHash = adjudicationContentHash(sharedInput);
      const coRows = await sql<{ count: string }[]>`
        select count(*)::text as count from adjudications where content_hash = ${sharedHash}`;
      assert(
        "coexist: BOTH rows persist under the one content_hash (two distinct adjudicator_ids)",
        coRows[0]!.count === "2",
        coRows[0]!.count,
      );
      const pA = await peekAdjudication(sql, adjA, sharedInput);
      const pB = await peekAdjudication(sql, adjB, sharedInput);
      const adjC = spyAdjudicator("c:z", {
        classification: "affirm",
        rationale: "C never consulted",
      });
      const pC = await peekAdjudication(sql, adjC, sharedInput);
      assert(
        "coexist: peek(A)=affirm, peek(B)=reject (each adjudicator sees its OWN verdict)",
        pA?.classification === "affirm" && pB?.classification === "reject",
        `pA=${pA?.classification} pB=${pB?.classification}`,
      );
      assert(
        "peek keys by adjudicator: peek(C) for the same input (no C row) is null",
        pC === null,
        String(pC),
      );
    }

    // ── REGRESSION (mirrors the live bug). Directly INSERT an `uncertain` row keyed by the NULL adapter's
    // provenance ("null:abstain@<rulebook_version>") for a chain input. Then consult a REAL adjudicator
    // (id "gemini:test", affirm) on that SAME input. Under the OLD content_hash-only key the stale abstention
    // would replay and the real adjudicator would never be called (the silent-suppression bug). With the
    // composite key it is a MISS for "gemini:test" → the adjudicator IS called and returns affirm; the
    // null:abstain row still peeks as uncertain under its own id, isolated.
    {
      const regInput: AdjudicationInput = {
        kind: "chain",
        rulebook_version: RULEBOOK,
        a_title: "Original Rule; Request for Comments",
        a_dates_text: "Comments due 2026-08-01",
        a_publication_date: "2026-05-01",
        b_title: "Extension of Comment Period",
        b_dates_text: "Comments now due 2026-09-15",
        b_publication_date: "2026-05-20",
        shared_docket: true,
        shared_rin: false,
        explicit_reference: false,
      };
      const regHash = adjudicationContentHash(regInput);
      const nullAdjudicatorId = `${NULL_ADJUDICATOR_ID}@${RULEBOOK}`;
      // Pre-seed the stale null:abstain uncertain row (the exact prod shape that had to be hand-deleted).
      await sql`
        insert into adjudications (content_hash, input, verdict, adjudicator_id)
        values (${regHash}, ${sql.json(regInput as never)}::jsonb,
                ${sql.json({ classification: "uncertain", rationale: "null adapter abstain" } as never)}::jsonb,
                ${nullAdjudicatorId})
        on conflict (content_hash, adjudicator_id) do nothing
      `;
      const realAdjudicator = spyAdjudicator("gemini:test", {
        classification: "affirm",
        rationale: "the extension genuinely amends the original",
      });
      const reg = await consultAdjudicator(sql, realAdjudicator, regInput);
      assert(
        "REGRESSION: a pre-seeded null:abstain uncertain does NOT shadow the real adjudicator — it IS called",
        realAdjudicator.calls === 1,
        String(realAdjudicator.calls),
      );
      assert(
        "REGRESSION: consult returns the REAL adjudicator's affirm (cache MISS, not the stale uncertain)",
        reg.cached === false && reg.verdict.classification === "affirm",
        `${JSON.stringify(reg)}`,
      );
      // Build a stand-in for the null adjudicator to peek under its id (uses NULL_ADJUDICATOR_ID).
      const nullStand: Adjudicator = {
        id: NULL_ADJUDICATOR_ID,
        async adjudicate() {
          return { classification: "uncertain", rationale: "unused" };
        },
      };
      const peekReal = await peekAdjudication(sql, realAdjudicator, regInput);
      const peekNull = await peekAdjudication(sql, nullStand, regInput);
      assert(
        "REGRESSION: peek(realAdjudicator)=affirm AND peek(nullAdjudicator)=uncertain (both isolated under their ids)",
        peekReal?.classification === "affirm" &&
          peekNull?.classification === "uncertain",
        `real=${peekReal?.classification} null=${peekNull?.classification}`,
      );
    }
  } finally {
    await sql.end();
  }
}

console.log("\n=== adjudicator results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
