import { isDeepStrictEqual } from "node:util";
import type { Observation } from "@yokel/contracts";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/** Ignore only known Regulations.gov metadata; unknown content remains evidence. */
function evidenceRaw(raw: unknown): unknown {
  if (!object(raw) || !object(raw.data) || !object(raw.data.attributes))
    return raw;
  const attributes = { ...raw.data.attributes };
  if (
    attributes.modifyDate == null ||
    typeof attributes.modifyDate === "string"
  ) {
    delete attributes.modifyDate;
  }
  const normalized: Record<string, unknown> = {
    ...raw,
    data: { ...raw.data, attributes },
  };
  if (object(raw.links)) {
    const links = { ...raw.links };
    if (links.self == null || typeof links.self === "string") delete links.self;
    if (Object.keys(links).length === 0) delete normalized.links;
    else normalized.links = links;
  }
  return normalized;
}

/**
 * Compare the whole observation envelope and raw payload, except ingestion identity/time/hash
 * and explicitly irrelevant metadata. Never change the immutable observation or its hash.
 * Only Regulations.gov gets this exception; newer FR/GovInfo evidence still invalidates review.
 */
export function sameReviewedRegsEvidence(
  a: Observation,
  b: Observation,
): boolean {
  if (a.source !== "regulations_gov" || b.source !== "regulations_gov")
    return false;
  const evidence = (o: Observation) => {
    const {
      observation_id: _id,
      fetched_at: _time,
      payload_hash: _hash,
      ...rest
    } = o;
    return { ...rest, raw: evidenceRaw(o.raw) };
  };
  return isDeepStrictEqual(evidence(a), evidence(b));
}
