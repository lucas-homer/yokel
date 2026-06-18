/**
 * contract.adversary.ts — the standalone adversary's runnable attack on the FROZEN @0.2.1 contract.
 *
 * Goal: try to make `confidence` LIE at the SCHEMA level, and prove each documented edge case is
 * representable WITHOUT forcing fake certainty. Each block crafts a concrete payload, parses it
 * against the real schema (imported from ../src/index), and asserts the EXPECTED pass/fail.
 *
 * Run: pnpm --filter @yokel/contracts exec tsx test/contract.adversary.ts
 */
import {
  ParticipationWindow,
  ConflictRecord,
  Observation,
  ObservationTarget,
  makeOcdId,
  DISCLAIMER,
  API_VERSION,
  EnvelopeMeta,
  Pagination,
  apiListEnvelope,
} from "../src/index.js";

let failures = 0;
const log: string[] = [];

function assert(name: string, cond: boolean, detail = "") {
  if (cond) {
    log.push(`  PASS  ${name}${detail ? ` — ${detail}` : ""}`);
  } else {
    failures++;
    log.push(`  FAIL  ${name}${detail ? ` — ${detail}` : ""}`);
  }
}

/** A valid baseline window we can spread + mutate per attack. */
function baseWindow(over: Record<string, unknown> = {}) {
  return {
    ocd_id: makeOcdId({ frDocNum: "2018-27875" }),
    fr_document_number: "2018-27875",
    regs_document_id: null,
    regs_object_id: null,
    docket_id: [],
    rin: null,
    window_type: "comment",
    resolved_close_utc: "2018-12-21T05:00:00.000Z",
    resolved_close_display: "11:59 p.m. ET",
    raw_fr_close_date: "2018-12-20",
    raw_regs_close_datetime: "2018-12-21T04:59:00-05:00",
    confidence: "medium",
    conflict_flags: [],
    status: "open",
    submission_url: null,
    govinfo_url: null,
    tags: [],
    version: 1,
    current_observation_ids: [],
    provenance: {
      agreeing_observation_ids: [],
      conflicting_observation_ids: [],
    },
    change_history: [],
    ...over,
  };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 1 — FR-2018-27875: a 1-UTC-day gap that is the SAME Eastern calendar date.
// The load-bearing fix. Must be representable as MEDIUM + tz_normalization_only, and the schema
// must FORBID encoding it as 'conflicting' while carrying tz_normalization_only.
// ─────────────────────────────────────────────────────────────────────────────────────────────

// 1a — the HONEST representation: MEDIUM + tz_normalization_only. MUST PASS.
{
  const honest = baseWindow({
    confidence: "medium",
    conflict_flags: ["tz_normalization_only"],
  });
  const r = ParticipationWindow.safeParse(honest);
  assert(
    "FR-2018-27875 honest (MEDIUM + tz_normalization_only) parses",
    r.success,
    r.success ? "" : JSON.stringify(r.error.issues),
  );
}

// 1b — THE ATTACK: try to make the tz artifact LIE as a conflict. MUST FAIL.
{
  const lie = baseWindow({
    confidence: "conflicting",
    conflict_flags: ["tz_normalization_only"],
    resolved_close_utc: null, // conflicting is allowed null; rules out the other refinement masking this
  });
  const r = ParticipationWindow.safeParse(lie);
  assert(
    "FR-2018-27875 ATTACK: 'conflicting' + tz_normalization_only is REJECTED",
    !r.success,
    r.success
      ? "schema accepted the tz-as-conflict lie!"
      : "refinement #2 caught it",
  );
}

// 1c — attack variant: bury tz_normalization_only alongside OTHER flags while conflicting. MUST FAIL.
{
  const lie = baseWindow({
    confidence: "conflicting",
    conflict_flags: ["fr_regs_date_mismatch", "tz_normalization_only"],
    resolved_close_utc: null,
  });
  const r = ParticipationWindow.safeParse(lie);
  assert(
    "FR-2018-27875 ATTACK: tz_normalization_only mixed with other flags under 'conflicting' is REJECTED",
    !r.success,
    r.success
      ? "schema let tz flag ride along with a conflict verdict!"
      : "refinement #2 still catches it",
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 2 — EPA 2025-02910: ONE notice extending MULTIPLE dockets with different deadlines.
// The M:N observation_targets join must be expressible (not silently 1:1 / latest-wins).
// ─────────────────────────────────────────────────────────────────────────────────────────────
{
  const obs = {
    observation_id: "obs-epa-1",
    ocd_id: makeOcdId({ frDocNum: "2025-02910" }), // the notice's primary derived window
    source: "federal_register",
    fr_document_number: "2025-02910",
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: "a".repeat(64),
    fetched_at: "2025-02-10T12:00:00.000Z",
    parser_version: "p1",
    raw_dates_text: "Comments due ...",
    is_extension: true,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: {},
  };
  const rObs = Observation.safeParse(obs);
  assert("EPA 2025-02910 extension observation parses", rObs.success);

  // ONE observation -> TWO distinct windows with DIFFERENT deadlines, via the M:N join.
  const targetA = {
    observation_id: "obs-epa-1",
    ocd_id: makeOcdId({ frDocNum: "2025-02910" }),
  };
  const targetB = {
    observation_id: "obs-epa-1",
    ocd_id: makeOcdId({ regsObjectId: "0900006484abcd01" }),
  };
  const rA = ObservationTarget.safeParse(targetA);
  const rB = ObservationTarget.safeParse(targetB);
  assert(
    "EPA 2025-02910 M:N: one observation_id fans out to TWO distinct ocd_ids",
    rA.success && rB.success && targetA.ocd_id !== targetB.ocd_id,
    `${targetA.ocd_id} vs ${targetB.ocd_id}`,
  );

  // And the two target windows can carry DIFFERENT resolved_close_utc — not forced to agree.
  const winA = ParticipationWindow.safeParse(
    baseWindow({
      ocd_id: targetA.ocd_id,
      fr_document_number: "2025-02910",
      confidence: "high",
      resolved_close_utc: "2025-03-15T03:59:00.000Z",
      conflict_flags: ["multi_target_notice"],
    }),
  );
  const winB = ParticipationWindow.safeParse(
    baseWindow({
      ocd_id: targetB.ocd_id,
      fr_document_number: "2025-02910",
      confidence: "high",
      resolved_close_utc: "2025-04-01T03:59:00.000Z",
      conflict_flags: ["multi_target_notice"],
    }),
  );
  assert(
    "EPA 2025-02910: the two fanned-out windows hold DIFFERENT deadlines (no latest-wins collapse)",
    winA.success && winB.success,
    winA.success && winB.success
      ? "distinct close dates representable"
      : "schema rejected divergent deadlines",
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 3 — FR 2025-03547: an extension doc whose own commentEndDate is null / openForComment false.
// Must be representable WITHOUT inventing a bogus resolved_close_utc.
// ─────────────────────────────────────────────────────────────────────────────────────────────

// 3a — honest LOW with null end date + open status flag, resolved_close_utc present (the ORIGINAL's
// date is still operative; the extension doc itself carried no date). MUST PASS.
{
  const w = baseWindow({
    confidence: "low",
    conflict_flags: ["null_end_date_open_status"],
    resolved_close_utc: "2025-04-01T03:59:00.000Z",
  });
  const r = ParticipationWindow.safeParse(w);
  assert(
    "FR 2025-03547 LOW + null_end_date_open_status (original date retained) parses",
    r.success,
    r.success ? "" : JSON.stringify(r.error.issues),
  );
}

// 3b — the truly-unknown case: no structured deadline anywhere => UNKNOWN + null close. MUST PASS.
{
  const w = baseWindow({
    confidence: "unknown",
    conflict_flags: ["null_end_date_open_status"],
    resolved_close_utc: null,
    resolved_close_display: null,
    raw_fr_close_date: null,
    raw_regs_close_datetime: null,
  });
  const r = ParticipationWindow.safeParse(w);
  assert(
    "FR 2025-03547 UNKNOWN with null resolved_close_utc (no invented date) parses",
    r.success,
    r.success ? "" : JSON.stringify(r.error.issues),
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 4 — BLM 2023-27468: 'keyword_false_positive' must be expressible so a deny-list hit is flagged.
// ─────────────────────────────────────────────────────────────────────────────────────────────
{
  // On the window: a land-withdrawal "extension" that is NOT a comment-deadline extension.
  const w = baseWindow({
    ocd_id: makeOcdId({ frDocNum: "2023-27468" }),
    fr_document_number: "2023-27468",
    confidence: "low",
    conflict_flags: ["keyword_false_positive"],
    resolved_close_utc: "2024-01-15T05:00:00.000Z",
  });
  const r = ParticipationWindow.safeParse(w);
  assert(
    "BLM 2023-27468 keyword_false_positive flag is expressible on a window",
    r.success,
    r.success ? "" : JSON.stringify(r.error.issues),
  );

  // And on the published /conflicts feed (min(1) flag satisfied).
  const cr = ConflictRecord.safeParse({
    ocd_id: makeOcdId({ frDocNum: "2023-27468" }),
    observation_a_id: "o1",
    observation_b_id: "o2",
    source_a: "federal_register",
    source_b: "regulations_gov",
    conflict_flags: ["keyword_false_positive"],
    govinfo_url: null,
    detected_at: "2024-01-01T00:00:00.000Z",
  });
  assert(
    "BLM 2023-27468 keyword_false_positive expressible on a ConflictRecord",
    cr.success,
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 5 — Does the schema FORCE resolved_close_utc null discipline, or can a GUESS sneak through?
// ─────────────────────────────────────────────────────────────────────────────────────────────

// 5a — ATTACK: HIGH confidence but null close (a confident deadline with no date). MUST FAIL.
{
  const lie = baseWindow({ confidence: "high", resolved_close_utc: null });
  const r = ParticipationWindow.safeParse(lie);
  assert(
    "ATTACK: HIGH + null resolved_close_utc is REJECTED (no confident null)",
    !r.success,
    r.success
      ? "schema accepted a HIGH window with no deadline!"
      : "refinement #1 caught it",
  );
}

// 5b — ATTACK: STALE + null close. MUST FAIL (STALE still asserts a real, just-aging, deadline).
{
  const lie = baseWindow({ confidence: "stale", resolved_close_utc: null });
  const r = ParticipationWindow.safeParse(lie);
  assert(
    "ATTACK: STALE + null resolved_close_utc is REJECTED",
    !r.success,
    r.success
      ? "schema accepted a STALE window with no deadline!"
      : "refinement #1 caught it",
  );
}

// 5c — ATTACK: LOW + null close. MUST FAIL per refinement #1 (only conflicting/unknown may be null).
{
  const lie = baseWindow({ confidence: "low", resolved_close_utc: null });
  const r = ParticipationWindow.safeParse(lie);
  assert(
    "ATTACK: LOW + null resolved_close_utc is REJECTED",
    !r.success,
    r.success
      ? "schema accepted a LOW window with no deadline!"
      : "refinement #1 caught it",
  );
}

// 5d — THE OTHER DIRECTION (the more dangerous lie): can a GUESSED date sneak in under
// 'conflicting' / 'unknown'? UNKNOWN now force-nulls resolved_close_utc (refinement #1, reverse
// direction) per docketclock.md ("UNKNOWN => resolved_close_utc = NULL; never coerced to a guess").
// CONFLICTING is deliberately NOT force-nulled: the engine abstains there, but a reconciled-yet-
// disputed close may still be the operative legal value surfaced alongside the conflict.
{
  const guessConflicting = baseWindow({
    confidence: "conflicting",
    conflict_flags: ["fr_regs_date_mismatch"],
    resolved_close_utc: "2099-01-01T00:00:00.000Z", // a disputed-but-reconciled value, allowed
  });
  const rC = ParticipationWindow.safeParse(guessConflicting);

  const guessUnknown = baseWindow({
    confidence: "unknown",
    resolved_close_utc: "2099-01-01T00:00:00.000Z", // both fields "missing" semantically, yet a date present
    resolved_close_display: null,
    raw_fr_close_date: null,
    raw_regs_close_datetime: null,
  });
  const rU = ParticipationWindow.safeParse(guessUnknown);

  assert(
    "ALLOWED: 'conflicting' + a non-null reconciled close is accepted (engine may surface a disputed value)",
    rC.success,
    "conflicting is not force-nulled; the close rides alongside the conflict_flags / proof feed",
  );
  assert(
    "ATTACK: 'unknown' + a non-null close is REJECTED (spec: UNKNOWN => resolved_close_utc = NULL)",
    !rU.success,
    rU.success
      ? "schema accepted an UNKNOWN window carrying a fabricated deadline!"
      : "refinement #1 reverse-direction caught it",
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 6 — OcdId minting discipline (the cross-system seam must validate the federal scheme).
// ─────────────────────────────────────────────────────────────────────────────────────────────
{
  let threw = false;
  try {
    makeOcdId({}); // both ids optional at the type level; the runtime guard is what protects the seam
  } catch {
    threw = true;
  }
  assert(
    "makeOcdId throws when neither frDocNum nor regsObjectId is supplied",
    threw,
  );

  // An internal-UUID-shaped ocd_id must be rejected at the seam.
  const r = ParticipationWindow.safeParse(
    baseWindow({ ocd_id: "550e8400-e29b-41d4-a716-446655440000" }),
  );
  assert(
    "non-federal-scheme ocd_id (a UUID) is REJECTED at the window seam",
    !r.success,
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 7 — REST response envelope (@0.3.0). Every response carries disclaimer + api_version +
// request_id; list responses carry a non-negative limit/offset/total. The envelope never suppresses
// its own honesty signals, and the factories compose response shapes so spec == response.
// ─────────────────────────────────────────────────────────────────────────────────────────────
{
  // 7a — EnvelopeMeta accepts a well-formed envelope...
  const goodMeta = {
    disclaimer: DISCLAIMER,
    api_version: API_VERSION,
    request_id: "550e8400-e29b-41d4-a716-446655440000",
  };
  assert(
    "EnvelopeMeta accepts a good envelope",
    EnvelopeMeta.safeParse(goodMeta).success,
  );

  // 7b — ...and REJECTS a missing field (request_id dropped).
  const { request_id: _drop, ...missingReq } = goodMeta;
  assert(
    "EnvelopeMeta REJECTS an envelope missing request_id",
    !EnvelopeMeta.safeParse(missingReq).success,
  );

  // 7c — Pagination rejects negatives (offset < 0).
  assert(
    "Pagination REJECTS a negative offset",
    !Pagination.safeParse({ limit: 25, offset: -1, total: 100 }).success,
  );

  // 7d — apiListEnvelope(ParticipationWindow) accepts a well-formed paginated window response.
  const listResp = {
    data: [baseWindow()],
    pagination: { limit: 25, offset: 0, total: 1 },
    ...goodMeta,
  };
  assert(
    "apiListEnvelope(ParticipationWindow) accepts a well-formed paginated response",
    apiListEnvelope(ParticipationWindow).safeParse(listResp).success,
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
// EDGE 8 — ConflictRecord cross-window (chain) invariants (@0.4.0, #31). One published /conflicts
// shape carries TWO kinds of disagreement; the superRefine must make the illegal pairings of
// conflict_scope × ocd_id_b unrepresentable, while the legacy (defaulted) cross_source path stays
// back-compat. Side A and side B are DISTINCT valid federal OcdIds.
// ─────────────────────────────────────────────────────────────────────────────────────────────
{
  const ocdA = makeOcdId({ frDocNum: "2025-03547" }); // original window
  const ocdB = makeOcdId({ frDocNum: "2025-09999" }); // amendment's standalone window
  assert(
    "EDGE 8 setup: side A and side B are DISTINCT valid OcdIds",
    ocdA !== ocdB,
    `${ocdA} vs ${ocdB}`,
  );

  /** A valid cross_window ConflictRecord we can spread + mutate per attack. */
  const baseConflict = (over: Record<string, unknown> = {}) => ({
    ocd_id: ocdA,
    observation_a_id: "o-orig",
    observation_b_id: "o-amend",
    source_a: "federal_register",
    source_b: "federal_register", // chain conflicts are often SAME-SOURCE (FR amendment vs FR original)
    conflict_flags: ["extension_chain_unresolved"],
    govinfo_url: null,
    conflict_scope: "cross_window",
    ocd_id_b: ocdB,
    govinfo_url_b: null,
    detected_at: "2026-06-17T00:00:00.000Z",
    ...over,
  });

  // 8a — ATTACK: cross_window WITHOUT a side-B window. MUST FAIL (a chain conflict spans two windows).
  {
    const r = ConflictRecord.safeParse(baseConflict({ ocd_id_b: null }));
    assert(
      "EDGE 8 ATTACK: cross_window + ocd_id_b null is REJECTED (a chain conflict must name side B)",
      !r.success,
      r.success
        ? "schema accepted a cross_window conflict with no side-B window!"
        : "superRefine caught it",
    );
  }

  // 8b — ATTACK (the #31 builder footgun): cross_window with ocd_id_b === ocd_id (SAME window on both
  // sides). MUST FAIL — a chain conflict's two sides are DISTINCT windows; a same-window disagreement
  // is cross_source, not cross_window.
  {
    const r = ConflictRecord.safeParse(baseConflict({ ocd_id_b: ocdA }));
    assert(
      "EDGE 8 ATTACK (#31 footgun): cross_window + ocd_id_b === ocd_id (same window both sides) is REJECTED",
      !r.success,
      r.success
        ? "schema accepted a cross_window conflict pointing at itself on both sides!"
        : "superRefine caught the self-pair",
    );
  }

  // 8c — ATTACK: cross_source carrying a non-null ocd_id_b. MUST FAIL — cross_source is single-window
  // (FR↔Regs on ONE ocd_id); there is no side-B window.
  {
    const r = ConflictRecord.safeParse(
      baseConflict({ conflict_scope: "cross_source", ocd_id_b: ocdB }),
    );
    assert(
      "EDGE 8 ATTACK: cross_source + non-null ocd_id_b is REJECTED (single-window scope has no side B)",
      !r.success,
      r.success
        ? "schema accepted a cross_source conflict carrying a second window!"
        : "superRefine caught it",
    );
  }

  // 8d — a valid cross_window record (distinct side-B window, all required fields present). MUST PASS.
  {
    const r = ConflictRecord.safeParse(baseConflict());
    assert(
      "EDGE 8: a valid cross_window ConflictRecord (distinct ocd_id_b) parses",
      r.success,
      r.success ? "" : JSON.stringify(r.error.issues),
    );
  }

  // 8e — BACK-COMPAT: a record OMITTING conflict_scope/ocd_id_b/govinfo_url_b parses and defaults to
  // the legacy cross_source meaning (conflict_scope === "cross_source", ocd_id_b === null). This is
  // the wire/parse guarantee that lets every current reconcile emit site stay valid against 0.4.0.
  {
    const r = ConflictRecord.safeParse({
      ocd_id: ocdA,
      observation_a_id: "o1",
      observation_b_id: "o2",
      source_a: "federal_register",
      source_b: "regulations_gov",
      conflict_flags: ["fr_regs_date_mismatch"],
      govinfo_url: null,
      detected_at: "2026-06-17T00:00:00.000Z",
    });
    assert(
      "EDGE 8 BACK-COMPAT: a legacy record omitting the cross-window fields parses",
      r.success,
      r.success ? "" : JSON.stringify(r.error.issues),
    );
    assert(
      "EDGE 8 BACK-COMPAT: omitted conflict_scope defaults to 'cross_source' and ocd_id_b to null",
      r.success &&
        r.data.conflict_scope === "cross_source" &&
        r.data.ocd_id_b === null,
      r.success
        ? `conflict_scope=${r.data.conflict_scope} ocd_id_b=${String(r.data.ocd_id_b)}`
        : "record did not parse",
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────────────
console.log("\n=== contract.adversary results ===");
console.log(log.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
