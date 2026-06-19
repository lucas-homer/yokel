/**
 * adjudicator/consult.ts — the READ-THROUGH cache in front of an Adjudicator. This is the only entry
 * point the (later-slice) poller/reconcile caller uses; it never touches the deterministic evaluator.
 *
 * Semantics:
 *   1. Compute content_hash = sha256(canonical(input)) — the cache key (includes rulebook_version).
 *   2. SELECT by content_hash. HIT → return the STORED verdict WITHOUT calling the adjudicator
 *      (cached:true). This is the replay-determinism guarantee: a cached input is NEVER re-adjudicated,
 *      even if the adjudicator changed (the FIRST verdict for a hash wins, forever).
 *   3. MISS → call adjudicator.adjudicate(input), build the AdjudicationRecord (adjudicator_id =
 *      `${adjudicator.id}@${input.rulebook_version}` provenance), INSERT ... ON CONFLICT (content_hash)
 *      DO NOTHING, then SELECT-BACK the row now present. The select-back handles a race where a concurrent
 *      miss inserted first — the first writer wins and BOTH readers get the same verdict. Return cached:false.
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

async function selectByHash(
  sql: Sql,
  contentHash: string,
): Promise<AdjudicationRecord | null> {
  const rows = await sql<Record<string, unknown>[]>`
    select content_hash, input, verdict, adjudicator_id, created_at
    from adjudications
    where content_hash = ${contentHash}
  `;
  return rows.length > 0 ? rowToRecord(rows[0]!) : null;
}

/**
 * peekAdjudication — a READ-ONLY cache probe. Computes the SAME content_hash consultAdjudicator uses
 * (reusing adjudicationContentHash, which parses the input canonically) and SELECTs by it, returning the
 * stored verdict or null WITHOUT ever calling the adjudicator. This is the cap×cache fix's free "is this
 * pair already decided?" check: a peek HIT applies a stored verdict for free (no LLM call, no budget
 * spent); a peek MISS means a real consult is needed (and will write the row this peek will hit next time).
 *
 * KEY IDENTITY (load-bearing): peek and consult MUST key identically — same canonicalInput → same hash —
 * so a peek-miss-then-consult writes exactly the row the next peek finds. Both go through
 * adjudicationContentHash(AdjudicationInput.parse(...)), so the hashes are byte-identical by construction.
 */
export async function peekAdjudication(
  sql: Sql,
  input: AdjudicationInput,
): Promise<AdjudicationVerdict | null> {
  const contentHash = adjudicationContentHash(AdjudicationInput.parse(input));
  const hit = await selectByHash(sql, contentHash);
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

  // 1. Cache lookup — a HIT replays the stored verdict and never calls the adjudicator.
  const hit = await selectByHash(sql, contentHash);
  if (hit) return { verdict: hit.verdict, cached: true };

  // 2. MISS — call the adjudicator on the CANONICAL input (may throw; we let it propagate, nothing is
  //    persisted on error). PARSE the verdict before it touches the immutable write-once row: an adapter
  //    that volunteers a stray field (e.g. a numeric `confidence`) must NOT have it baked into the audit
  //    log — confidence is NEVER LLM-scored, and this row is the source-of-truth for replay.
  const verdict = AdjudicationVerdict.parse(
    await adjudicator.adjudicate(canonicalInput),
  );
  const adjudicatorId = `${adjudicator.id}@${canonicalInput.rulebook_version}`;

  // 3. Write-once insert: the first writer for this content_hash wins; a concurrent insert is a no-op.
  await sql`
    insert into adjudications (content_hash, input, verdict, adjudicator_id)
    values (${contentHash}, ${sql.json(canonicalInput as never)}::jsonb,
            ${sql.json(verdict as never)}::jsonb, ${adjudicatorId})
    on conflict (content_hash) do nothing
  `;

  // 4. Select-back — returns OUR row, or the racing writer's row if it landed first. Either way the
  //    first verdict wins; both concurrent readers observe the same persisted verdict.
  const persisted = await selectByHash(sql, contentHash);
  if (!persisted) {
    // Should be unreachable: we just inserted-or-collided, so a row exists.
    throw new Error(
      `adjudications row vanished after insert for content_hash ${contentHash}`,
    );
  }
  return { verdict: persisted.verdict, cached: false };
}
