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
 *   • CACHE HIT → NO re-call (replay determinism) — a second consult returns the STORED verdict and
 *     the spy call count stays at 1; swapping to a DIFFERENT spy still replays the ORIGINAL verdict
 *     and the new spy is NEVER called (provider swap does not re-adjudicate a cached input).
 *   • NullAdjudicator — returns `uncertain` for BOTH a notice- and a chain-kind input; id="null:abstain".
 *   • WRITE-ONCE — a direct second INSERT of the same content_hash with a different verdict does NOT
 *     change the stored row (ON CONFLICT DO NOTHING); consult still returns the first verdict.
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
import { NullAdjudicator } from "../src/adjudicator/null-adjudicator.js";
import { consultAdjudicator } from "../src/adjudicator/consult.js";
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

    // PROVIDER SWAP — a DIFFERENT spy (different id + verdict) must NOT re-adjudicate a cached input.
    const reject: AdjudicationVerdict = {
      classification: "reject",
      rationale: "spy2 says no",
    };
    const spy2 = spyAdjudicator("spy:v2", reject);
    const r3 = await consultAdjudicator(sql, spy2, noticeInput);
    assert(
      "provider swap on a cached input replays the ORIGINAL verdict (affirm, not reject)",
      r3.cached === true && r3.verdict.classification === "affirm",
      r3.verdict.classification,
    );
    assert(
      "the swapped-in spy is NEVER called for a cached input",
      spy2.calls === 0,
      String(spy2.calls),
    );

    // WRITE-ONCE — a direct second INSERT of the same content_hash with a different verdict is ignored.
    await sql`
      insert into adjudications (content_hash, input, verdict, adjudicator_id)
      values (${expectHash}, ${sql.json(noticeInput as never)}::jsonb,
              ${sql.json(reject as never)}::jsonb, ${"spy:v2@" + RULEBOOK})
      on conflict (content_hash) do nothing
    `;
    const afterWriteOnce = await sql<
      { verdict: AdjudicationVerdict }[]
    >`select verdict from adjudications where content_hash = ${expectHash}`;
    assert(
      "write-once: direct re-INSERT with a different verdict does NOT change the stored row",
      afterWriteOnce[0]!.verdict.classification === "affirm",
      afterWriteOnce[0]?.verdict.classification,
    );
    const r4 = await consultAdjudicator(sql, spy2, noticeInput);
    assert(
      "consult still returns the FIRST verdict after a write-once collision",
      r4.verdict.classification === "affirm",
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

    // notice row also round-trips (BOTH KINDS).
    const noticeRow = await sql<
      Record<string, unknown>[]
    >`select content_hash, input, verdict, adjudicator_id, created_at from adjudications where content_hash = ${expectHash}`;
    const parsedNotice = AdjudicationRecord.safeParse({
      ...noticeRow[0],
      created_at: (noticeRow[0]!.created_at as Date).toISOString(),
    });
    assert(
      "notice row round-trips AdjudicationRecord.parse",
      parsedNotice.success,
      parsedNotice.success ? "" : JSON.stringify(parsedNotice.error.issues),
    );
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
