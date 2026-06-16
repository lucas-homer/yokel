/**
 * Canonical payload hashing — the dedupe + tamper-evidence key on the observation log. Shared by every
 * source adapter so the canonicalization (stable key order) is identical across sources: the same raw
 * payload must hash the same regardless of source-specific key ordering.
 */
import { createHash } from "node:crypto";

/** Stable JSON serialization so the hash is canonical across key-ordering. */
function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(value as Record<string, unknown>).sort()) {
      out[k] = sortKeys((value as Record<string, unknown>)[k]);
    }
    return out;
  }
  return value;
}

export function canonicalize(value: unknown): string {
  return JSON.stringify(sortKeys(value));
}

/** sha256 hex of the canonical raw JSON — the dedupe + tamper-evidence key on the log. */
export function payloadHash(raw: unknown): string {
  return createHash("sha256").update(canonicalize(raw), "utf8").digest("hex");
}
