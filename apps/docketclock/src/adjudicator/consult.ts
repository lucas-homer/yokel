/**
 * adjudicator/consult.ts — the READ-THROUGH cache in front of an Adjudicator. This is the only entry
 * point the (later-slice) poller/reconcile caller uses; it never touches the deterministic evaluator.
 *
 * CACHE KEY = (content_hash, adjudicator_id) — see migration 0009. adjudicator_id is the SAME provenance
 * string written on the row: `${adjudicator.id}@${input.rulebook_version}`. This is deliberately NOT
 * content_hash alone (which is what 0008 keyed on): a content_hash-only key let a NON-DECIDING adapter
 * (the null adapter, "null:abstain@<rb>", which only ever abstains) persist an `uncertain` and then SHADOW
 * a real adjudicator's verdict for the SAME input — the real provider was never consulted and the link was
 * silently suppressed. Keying by (content_hash, adjudicator_id) isolates each adjudicator: a non-deciding
 * adapter's verdict lives under a DIFFERENT key than a real one's (different adjudicator_id ⇒ different
 * key), so it can never shadow it. A provider/model OR rulebook change ALSO re-adjudicates (new
 * adjudicator_id and/or new content_hash) — correct: a different engine/rulebook is a different question.
 *
 * Semantics:
 *   1. Compute content_hash = sha256(canonical(input)) (includes rulebook_version) and adjudicatorId =
 *      `${adjudicator.id}@${input.rulebook_version}`. Together they are the cache key.
 *   2. SELECT by (content_hash, adjudicator_id). HIT → return the STORED verdict WITHOUT calling the
 *      adjudicator (cached:true). This is per-adjudicator replay determinism: a given adjudicator's verdict
 *      for a given input is cached and replayed under ITS id — including `uncertain`, with NO special-casing
 *      and NO eviction (the FIRST verdict for THIS (hash, adjudicator_id) wins, forever). No re-bill, no
 *      starvation. A DIFFERENT adjudicator on the same content_hash is a MISS (different key) and consults.
 *   3. MISS → call adjudicator.adjudicate(input), build the AdjudicationRecord (adjudicator_id as above),
 *      INSERT ... ON CONFLICT (content_hash, adjudicator_id) DO NOTHING, then SELECT-BACK the row now
 *      present for THIS key. The select-back handles a race where a concurrent miss for the SAME
 *      (hash, adjudicator_id) inserted first — the first writer wins and BOTH readers get the same verdict.
 *      Return cached:false.
 *   4. Validate the round-tripped row with AdjudicationRecord.parse on the way out.
 *
 * FAIL/THROW BEHAVIOR (documented choice): if adjudicator.adjudicate throws or times out, this function
 * LETS IT THROW — it does NOT swallow the error into an `uncertain` verdict here. Rationale: the caller's
 * degrade-to-deterministic behavior is the safety net, and the real timeout/fail-safe wrapper is designed
 * in Slice 3; surfacing the raw failure keeps this cache layer honest and side-effect-free on error (a
 * thrown adjudicate means NOTHING is persisted, so the next consult retries cleanly rather than caching a
 * fabricated abstain). A nothing-was-written-on-error invariant is exactly the replay property we want.
 */
import {
  AdjudicationRecord,
  AdjudicationInput,
  AdjudicationVerdict,
} from "@yokel/contracts";
import type { Sql } from "../db/client.js";
import type { Adjudicator } from "./port.js";
import { adjudicationContentHash } from "./content-hash.js";

export interface ConsultResult {
  verdict: AdjudicationVerdict;
  cached: boolean;
}

/** Validate a DB row into an AdjudicationRecord (created_at comes back as a Date from postgres.js). */
function rowToRecord(row: Record<string, unknown>): AdjudicationRecord {
  const created = row.created_at;
  return AdjudicationRecord.parse({
    content_hash: row.content_hash,
    input: row.input,
    verdict: row.verdict,
    adjudicator_id: row.adjudicator_id,
    created_at:
      created instanceof Date ? created.toISOString() : String(created),
  });
}

/**
 * selectByHash — fetch the cache row for the FULL key (content_hash, adjudicator_id). The cache is keyed
 * by BOTH columns (migration 0009), so a lookup that omitted adjudicator_id could return a DIFFERENT
 * adjudicator's verdict for the same input — exactly the null:abstain-shadows-Gemini bug. Both peek and
 * consult go through here with the same (hash, adjudicatorId) so they key identically.
 */
async function selectByHash(
  sql: Sql,
  contentHash: string,
  adjudicatorId: string,
): Promise<AdjudicationRecord | null> {
  const rows = await sql<Record<string, unknown>[]>`
    select content_hash, input, verdict, adjudicator_id, created_at
    from adjudications
    where content_hash = ${contentHash} and adjudicator_id = ${adjudicatorId}
  `;
  return rows.length > 0 ? rowToRecord(rows[0]!) : null;
}

/**
 * peekAdjudication — a READ-ONLY cache probe. Computes the SAME (content_hash, adjudicator_id) cache key
 * consultAdjudicator uses and SELECTs by it, returning THIS adjudicator's stored verdict or null WITHOUT
 * ever calling the adjudicator. This is the cap×cache fix's free "has THIS adjudicator already decided this
 * pair?" check: a peek HIT applies a stored verdict for free (no LLM call, no budget spent); a peek MISS
 * means a real consult is needed (and will write the row this peek will hit next time).
 *
 * KEY IDENTITY (load-bearing): peek and consult MUST key identically — same canonicalInput → same hash AND
 * same adjudicator ⇒ same adjudicator_id — so a peek-miss-then-consult writes exactly the row the next peek
 * finds. The `adjudicator` param (added by 0009's re-key) is what lets peek compute the same adjudicator_id;
 * a peek for adjudicator B never sees adjudicator A's row (different key), so a non-deciding adapter's
 * verdict can never be peeked-and-applied in place of a real adjudicator's.
 */
export async function peekAdjudication(
  sql: Sql,
  adjudicator: Adjudicator,
  input: AdjudicationInput,
): Promise<AdjudicationVerdict | null> {
  // adjudicationContentHash already parses+canonicalizes the input (same path consultAdjudicator uses),
  // so we hash directly — no separate parse needed. The adjudicator_id mirrors consult's provenance string.
  const contentHash = adjudicationContentHash(input);
  const adjudicatorId = `${adjudicator.id}@${input.rulebook_version}`;
  const hit = await selectByHash(sql, contentHash, adjudicatorId);
  return hit ? hit.verdict : null;
}

export async function consultAdjudicator(
  sql: Sql,
  adjudicator: Adjudicator,
  input: AdjudicationInput,
): Promise<ConsultResult> {
  // PARSE the input ONCE, up front, and use the canonical form for EVERYTHING — hashing, the cache key,
  // the adjudicator call, provenance, and persistence. Feeding the adapter the SAME parsed value the cache
  // is keyed on closes a poisoning seam: a caller that smuggles unmodeled fields (e.g. via `any`) could
  // otherwise influence the adapter's verdict with fields the content_hash excludes, so that verdict would
  // later replay for the canonical input. Parsing once also removes a redundant double-parse.
  const canonicalInput = AdjudicationInput.parse(input);
  const contentHash = adjudicationContentHash(canonicalInput);
  // adjudicatorId is part of the cache key (with content_hash) — compute it up front so the lookup, the
  // insert, and the select-back all key IDENTICALLY. Same provenance string written on the row.
  const adjudicatorId = `${adjudicator.id}@${canonicalInput.rulebook_version}`;

  // 1. Cache lookup by (content_hash, adjudicator_id) — a HIT replays THIS adjudicator's stored verdict and
  //    never calls the adjudicator. A different adjudicator's row for the same content_hash is NOT a hit.
  const hit = await selectByHash(sql, contentHash, adjudicatorId);
  if (hit) return { verdict: hit.verdict, cached: true };

  // 2. MISS — call the adjudicator on the CANONICAL input (may throw; we let it propagate, nothing is
  //    persisted on error). PARSE the verdict before it touches the immutable write-once row: an adapter
  //    that volunteers a stray field (e.g. a numeric `confidence`) must NOT have it baked into the audit
  //    log — confidence is NEVER LLM-scored, and this row is the source-of-truth for replay.
  const verdict = AdjudicationVerdict.parse(
    await adjudicator.adjudicate(canonicalInput),
  );

  // 3. Write-once insert PER (content_hash, adjudicator_id): the first writer for THIS key wins; a
  //    concurrent insert for the same key is a no-op. A different adjudicator_id is a distinct row.
  await sql`
    insert into adjudications (content_hash, input, verdict, adjudicator_id)
    values (${contentHash}, ${sql.json(canonicalInput as never)}::jsonb,
            ${sql.json(verdict as never)}::jsonb, ${adjudicatorId})
    on conflict (content_hash, adjudicator_id) do nothing
  `;

  // 4. Select-back by (content_hash, adjudicator_id) — returns OUR row, or the racing writer's row if it
  //    landed first. Either way the first verdict for THIS key wins; both concurrent readers observe it.
  const persisted = await selectByHash(sql, contentHash, adjudicatorId);
  if (!persisted) {
    // Should be unreachable: we just inserted-or-collided, so a row exists.
    throw new Error(
      `adjudications row vanished after insert for content_hash ${contentHash} adjudicator_id ${adjudicatorId}`,
    );
  }
  return { verdict: persisted.verdict, cached: false };
}
