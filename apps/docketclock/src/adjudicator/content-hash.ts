/**
 * adjudicator/content-hash.ts — the cache key for the adjudication subsystem: sha256 of a CANONICAL
 * (stable/sorted-key) serialization of the AdjudicationInput. The same logical input always hashes
 * identically, which is what makes the read-through cache correct and replay deterministic.
 *
 * We REUSE the ingest path's canonicalization (sources/payload.ts `canonicalize` — sorted keys, recursive)
 * so the substrate has ONE canonical-JSON definition, not two that can drift. The hash includes EVERY
 * field of the input — crucially `rulebook_version` (so a rulebook change re-keys and re-adjudicates) —
 * and excludes `adjudicator_id` BY CONSTRUCTION: adjudicator_id is not a field of AdjudicationInput, so it
 * cannot enter the hash. Two providers answering the "same" question collide on one key (first writer wins).
 *
 * Returns a 64-hex digest that satisfies the contract's PayloadHash shape.
 *
 * We hash the PARSED input (AdjudicationInput.parse), not the raw object, so the key is canonical: stray
 * extra fields are stripped and schema defaults applied before hashing. Two semantically-identical inputs
 * that differ only by an unmodeled field therefore share one cache key (no accidental re-adjudication), and
 * a caller cannot poison the cache by smuggling fields the schema doesn't recognize.
 */
import { createHash } from "node:crypto";
import { AdjudicationInput } from "@yokel/contracts";
import { canonicalize } from "../sources/payload.js";

export function adjudicationContentHash(input: AdjudicationInput): string {
  return createHash("sha256")
    .update(canonicalize(AdjudicationInput.parse(input)), "utf8")
    .digest("hex");
}
