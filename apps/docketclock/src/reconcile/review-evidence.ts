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

/** The two Regulations.gov status flags the portal flips when its own announced close passes. */
const ECHO_FLAGS = ["openForComment", "withinCommentPeriod"] as const;
type EchoFlag = (typeof ECHO_FLAGS)[number];

/** data.attributes of a Regs raw payload, or null when the payload is not shaped that way. */
function attributesOf(o: Observation): Record<string, unknown> | null {
  const raw = o.raw;
  if (!object(raw) || !object(raw.data) || !object(raw.data.attributes))
    return null;
  return raw.data.attributes;
}

/**
 * Classify ONE newer observation against the reviewed baseline under clause 3 (below).
 * Returns the set of flags it shows flipped (true->false), or null when it differs from the baseline
 * in any way other than an allowed flip (so the caller must invalidate).
 *
 * Mechanism: for each echo flag, require identical presence on both sides and either a deep-equal
 * value or exactly `true -> false`; then overwrite the flipped keys with the BASELINE's values on a
 * COPY of the newer payload and hand the pair to the v2.1 comparison. Everything else — every other
 * attribute, unknown keys, top-level/data-level keys, non-self links, the whole envelope, a non-Regs
 * source — is therefore judged by exactly the same rule as before (ADR 0010); v2.2 adds nothing but
 * the two tolerated transitions. The caller's observation is never mutated.
 */
function allowedEchoFlips(
  baseline: Observation,
  newer: Observation,
): Set<EchoFlag> | null {
  if (newer.source !== "regulations_gov") return null;
  const baseAttrs = attributesOf(baseline);
  const newAttrs = attributesOf(newer);
  const flipped = new Set<EchoFlag>();
  if (baseAttrs === null || newAttrs === null) {
    // No attributes object to tolerate a flip in — only a byte-for-byte v2.1 match can pass.
    return sameReviewedRegsEvidence(baseline, newer) ? flipped : null;
  }
  const restored: Record<string, unknown> = { ...newAttrs };
  for (const key of ECHO_FLAGS) {
    const inBase = Object.prototype.hasOwnProperty.call(baseAttrs, key);
    const inNew = Object.prototype.hasOwnProperty.call(newAttrs, key);
    if (inBase !== inNew) return null; // absent <-> present is a change
    if (!inBase) continue; // absent on both sides — nothing to tolerate
    const before = baseAttrs[key];
    const after = newAttrs[key];
    if (isDeepStrictEqual(before, after)) continue; // unchanged (true->true, false->false, null->null)
    if (before === true && after === false) {
      // The ONE tolerated transition. Restore the baseline value on the copy so the v2.1 comparison
      // below sees the rest of the payload exactly as it was reviewed.
      restored[key] = before;
      flipped.add(key);
      continue;
    }
    return null; // false->true, true->null, "false" (string), 0, or any other value change
  }
  const raw = newer.raw as Record<string, unknown>;
  const data = raw.data as Record<string, unknown>;
  const comparable: Observation = {
    ...newer,
    raw: { ...raw, data: { ...data, attributes: restored } },
  };
  return sameReviewedRegsEvidence(baseline, comparable) ? flipped : null;
}

/**
 * reconcile-v2.2 (ADR 0014): "the portal recording its own announced close is not new evidence".
 *
 * Decides whether a post-verdict Regulations.gov chain that merely records the close the operator
 * already pinned still counts as the REVIEWED evidence, so an honored pin_close is not dropped (and
 * the window not bounced back into the review queue as a CLOSED conflicting item) the morning after
 * its own deadline. The rule has five clauses; ALL must hold:
 *
 *   1. The latest verdict is kind `pin_close` and is otherwise eligible exactly as in v2.1: a
 *      baseline exists (latest Regs observation at/before the verdict, same tiebreak) and its
 *      payload_hash is in reviewed_payload_hashes. Non-pin kinds get NO exception.
 *      -> Checked by the CALLER (reconcile.ts), which owns verdict parsing and the baseline search.
 *   2. The baseline's commentEndDate has an America/New_York calendar date strictly equal to
 *      pinned_close_date. The transition is predicted by the portal's own date; fetch timing proves
 *      nothing else.
 *      -> Checked by the CALLER (reconcile.ts owns regsCloseToUtc / the Eastern normalization);
 *         it passes the resulting pinned close INSTANT in as `pinnedCloseUtc`.
 *   3. Beyond the ADR 0010 metadata fields (modifyDate, links.self), the ONLY differences between the
 *      baseline and any post-verdict observation are data.attributes.openForComment and/or
 *      data.attributes.withinCommentPeriod, and each of those is either deep-equal to the baseline or
 *      boolean false where the baseline is boolean true. Anything else invalidates: absent<->present,
 *      non-boolean values (the string "false"), true->null, false->true, any other attribute, any
 *      top-level / data-level / envelope change, a non-Regs newer observation (FR/GovInfo still
 *      invalidate). Either flag alone may flip.
 *   4. Every post-verdict observation showing a flipped value has fetched_at STRICTLY after
 *      `pinnedCloseUtc` (11:59:59 p.m. ET of the pinned date, DST-correct). Equality fails.
 *      Observations identical to the baseline may of course occur before it.
 *   5. Monotonic over the WHOLE post-verdict history in deterministic order (fetched_at epoch asc,
 *      then observation_id asc): once a flag has been observed false, every later observation must
 *      show it false — a flip-then-revert invalidates, so a reopened portal can never stay pinned
 *      closed (an honored pin overrides the status rule). Two post-verdict observations sharing a
 *      fetched_at epoch but disagreeing in flag state invalidate (ambiguous order fails closed).
 *
 * Pure and side-effect-free: the caller's array is copied before sorting; no observation, payload or
 * hash is ever mutated. `newer` is every non-human observation strictly after the verdict (the v2
 * tie policy stands: fetched_at == reviewedAt is NOT newer). An empty `newer` returns true (nothing
 * to object to — the caller's v2.1 path already covers it).
 */
export function portalCloseEchoPreservesPin(
  baseline: Observation,
  newer: readonly Observation[],
  pinnedCloseUtc: string,
): boolean {
  if (baseline.source !== "regulations_gov") return false;
  const pinnedEpoch = new Date(pinnedCloseUtc).getTime();
  if (Number.isNaN(pinnedEpoch)) return false;

  // Deterministic order (clause 5) — the same (fetched_at, observation_id) order reconcileOcdId
  // reads in, applied to a COPY so caller arrays (and the DB read order) are never disturbed.
  const chain = [...newer].sort((a, b) => {
    const d =
      new Date(a.fetched_at).getTime() - new Date(b.fetched_at).getTime();
    if (d !== 0) return d;
    return a.observation_id < b.observation_id
      ? -1
      : a.observation_id > b.observation_id
        ? 1
        : 0;
  });

  const seenFalse = new Set<EchoFlag>();
  let prevEpoch: number | null = null;
  let prevState = "";
  for (const o of chain) {
    // Clause 3 — the only tolerated difference is a true->false flip of one or both flags.
    const flipped = allowedEchoFlips(baseline, o);
    if (flipped === null) return false;
    const epoch = new Date(o.fetched_at).getTime();
    if (Number.isNaN(epoch)) return false;
    // Clause 4 — a flipped value seen at or before the pinned instant is NOT the predicted echo.
    if (flipped.size > 0 && !(epoch > pinnedEpoch)) return false;
    // Clause 5 — monotonic: a flag already seen false must stay false; equal-epoch disagreement fails.
    const state = ECHO_FLAGS.map((k) => (flipped.has(k) ? "f" : "-")).join("");
    if (prevEpoch === epoch && state !== prevState) return false;
    for (const k of ECHO_FLAGS) {
      if (flipped.has(k)) seenFalse.add(k);
      else if (seenFalse.has(k)) return false; // flip-then-revert
    }
    prevEpoch = epoch;
    prevState = state;
  }
  return true;
}
