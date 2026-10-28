/**
 * reconcile-review-echo-adversary.test.ts — ADVERSARIAL probes against the reconcile-v2.2 portal
 * close echo exception (ADR 0014; PR-A1; portalCloseEchoPreservesPin in src/reconcile/review-evidence.ts).
 *
 * Goal: MAKE THE EXCEPTION OVER-REACH — find a chain where something OTHER than "the portal recording
 * the close the operator already pinned" keeps a stale pin alive (fake certainty at HIGH), or where
 * the engine throws (a production brick). Every probe below must stay UN-honored: no human_resolved,
 * verdict not in current_observation_ids, and a non-null ConflictRecord whenever confidence is
 * conflicting. Sections:
 *   C  — control: the base echo chain IS honored (so the negatives below are meaningful).
 *   A1 — timing: flip before the pinned instant; flip at EXACTLY the pinned instant.
 *   A2 — clause 2 (date equality): pin one day early / late; the UTC-day artifact (commentEndDate
 *        2026-10-07T03:59:59Z is Eastern 10-06, so a pin of 10-07 is NOT equal).
 *   A3 — flip plus any other change: commentEndDate, withdrawn, title, allowLateComments, docketId,
 *        an unknown attribute; envelope (parser_version, each is_* flag, regs_document_id,
 *        raw_dates_text); top-level / data-level / non-self links changes.
 *   A4 — kind: each non-pin kind with the identical flip gets NO exception.
 *   A5 — monotonic: flip-then-revert (both flags, each alone); a material change then a revert
 *        before the flip; same-fetched_at disagreement.
 *   A6 — other sources: a newer FR observation interleaved anywhere; a newer govinfo observation
 *        (synthetic AND spliced into every live history) — since reconcile-v2.4 (ADR 0016 §6) govinfo
 *        is NOT a derivation source, so it must leave the echo decision exactly as without it.
 *   A7 — flag shapes: false->true when the baseline was already false; absent->present(false);
 *        present(true)->absent; the string "false"; true->null; true->0.
 *   A8 — evidence: reviewed_payload_hashes lacks the baseline hash; omitted history.
 *   G  — global dual-fire invariants over every produced result.
 *
 * Pure engine, no DB. Harness style: assert/out/failures, process.exit.
 */
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import { reconcile, type ReconcileResult } from "../src/reconcile/reconcile.js";
import { frCloseDateToUtcInstant } from "../src/reconcile/eastern-date.js";
import { portalCloseEchoPreservesPin } from "../src/reconcile/review-evidence.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
/** Every produced result feeds the global dual-fire invariants at the bottom. */
const produced: { label: string; r: ReconcileResult }[] = [];

// ── synthetic chain builders (echo-test conventions) ─────────────────────────────────────────────────
const OCD = "ocd-participation-window/federal/2026-08826";
const NOW = new Date("2026-10-18T06:13:26Z");
let idSeq = 0;
function source(
  src: Observation["source"],
  raw: unknown,
  fetched_at: string,
  id?: string,
): Observation {
  return {
    observation_id: id ?? `${src}-${fetched_at}-${idSeq++}`,
    ocd_id: OCD,
    source: src,
    fr_document_number: "2026-08826",
    regs_document_id: src === "regulations_gov" ? "FDA-2026-N-2886-0001" : null,
    regs_object_id: null,
    payload_hash: createHash("sha256")
      .update(JSON.stringify(raw))
      .digest("hex"),
    fetched_at,
    parser_version: "test-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
  };
}
type RegsRaw = {
  data: { id: string; attributes: Record<string, unknown> };
  links?: Record<string, unknown>;
  [k: string]: unknown;
};
function regsRaw(attrs: Record<string, unknown>): RegsRaw {
  return {
    data: {
      id: "FDA-2026-N-2886-0001",
      attributes: {
        commentEndDate: "2026-10-03T03:59:59Z", // Eastern 2026-10-02
        openForComment: true,
        withinCommentPeriod: true,
        withdrawn: false,
        allowLateComments: false,
        title: "Modification of Certain Terminology in Title 21",
        docketId: "FDA-2026-N-2886",
        modifyDate: "2026-09-18T00:00:00Z",
        ...attrs,
      },
    },
  };
}
/** A later refresh of `base`: modifyDate moves, the given attrs are overridden (undefined = delete). */
function refresh(
  base: RegsRaw,
  fetched_at: string,
  attrs: Record<string, unknown> = {},
  envelope: Partial<Observation> = {},
): Observation {
  const raw = structuredClone(base);
  raw.data.attributes.modifyDate = fetched_at;
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined) delete raw.data.attributes[k];
    else raw.data.attributes[k] = v;
  }
  return { ...source("regulations_gov", raw, fetched_at), ...envelope };
}
function frAt(fetched_at: string): Observation {
  return source(
    "federal_register",
    {
      document_number: "2026-08826",
      comments_close_on: "2026-07-06", // genuine FR/Regs Eastern-date mismatch -> machine CONFLICTING
      publication_date: "2026-05-06",
    },
    fetched_at,
  );
}
const fr = frAt("2026-06-17T16:51:47Z");
function verdictObs(
  raw: Record<string, unknown>,
  fetched_at = "2026-09-23T20:41:45Z",
  id = "human-pin",
): Observation {
  return source("human_review", raw, fetched_at, id);
}
function pin(
  pinned_close_date: string,
  baselines: Observation[],
  id = "human-pin",
): Observation {
  return verdictObs(
    {
      kind: "pin_close",
      pinned_close_date,
      operator: "test",
      note: "Reopening notice verified",
      reviewed_payload_hashes: baselines.map((b) => b.payload_hash),
    },
    "2026-09-23T20:41:45Z",
    id,
  );
}
const PIN = "2026-10-02";
const PIN_INSTANT = frCloseDateToUtcInstant(PIN); // 2026-10-03T03:59:59.000Z
const BASE = regsRaw({});
const baseline = source(
  "regulations_gov",
  BASE,
  "2026-09-18T20:20:31Z",
  "regs-baseline",
);
const verdict = pin(PIN, [fr, baseline]);
const identical = refresh(BASE, "2026-10-01T05:27:19Z");
const FLIPPED = { openForComment: false, withinCommentPeriod: false };
const AFTER = "2026-10-03T07:01:55Z"; // a few hours after PIN_INSTANT
const LATER = "2026-10-04T07:01:55Z";

/** A THROW from the engine = a window that can never re-derive = a production brick. */
function unhonored(
  label: string,
  chain: Observation[],
  human = verdict,
): ReconcileResult | null {
  let r: ReconcileResult;
  try {
    r = reconcile(chain, NOW);
  } catch (e) {
    assert(
      `${label} — engine RETURNED (no throw)`,
      false,
      `THREW: ${(e as Error).message}`,
    );
    return null;
  }
  produced.push({ label, r });
  assert(
    `${label} — NOT honored (no human_resolved)`,
    !r.window.conflict_flags.includes("human_resolved"),
    `${r.window.confidence} ${r.window.conflict_flags.join(",")}`,
  );
  assert(
    `${label} — verdict NOT in current_observation_ids`,
    !r.window.current_observation_ids.includes(human.observation_id),
  );
  if (r.window.confidence === "conflicting")
    assert(
      `${label} — CONFLICTING carries a ConflictRecord`,
      r.conflict !== null,
    );
  return r;
}

// ═══ C — CONTROL: the base echo chain IS honored ════════════════════════════════════════════════════
{
  const r = reconcile(
    [fr, baseline, verdict, identical, refresh(BASE, AFTER, FLIPPED)],
    NOW,
  );
  produced.push({ label: "C control", r });
  assert(
    "C control: base echo chain honored (HIGH + human_resolved, no ConflictRecord)",
    r.window.confidence === "high" &&
      r.window.conflict_flags.includes("human_resolved") &&
      r.conflict === null &&
      r.window.resolved_close_utc === PIN_INSTANT,
    `${r.window.confidence} ${r.window.conflict_flags.join(",")}`,
  );
  assert(
    "C control: the pure function agrees on the same inputs",
    portalCloseEchoPreservesPin(
      baseline,
      [identical, refresh(BASE, AFTER, FLIPPED)],
      PIN_INSTANT,
    ),
  );
}

// ═══ A1 — TIMING ════════════════════════════════════════════════════════════════════════════════════
unhonored("A1a flip observed BEFORE the pinned instant", [
  fr,
  baseline,
  verdict,
  refresh(BASE, "2026-10-02T05:26:26Z", FLIPPED),
]);
unhonored("A1b flip observed BEFORE the pinned instant, then again after", [
  fr,
  baseline,
  verdict,
  refresh(BASE, "2026-10-02T05:26:26Z", FLIPPED),
  refresh(BASE, AFTER, FLIPPED),
]);
unhonored(
  "A1c flip observed at EXACTLY the pinned instant (fetched_at == pinned instant)",
  [fr, baseline, verdict, refresh(BASE, PIN_INSTANT, FLIPPED)],
);
unhonored("A1d openForComment alone flipped 1 s before the pinned instant", [
  fr,
  baseline,
  verdict,
  refresh(BASE, "2026-10-03T03:59:58Z", { openForComment: false }),
]);

// ═══ A2 — CLAUSE 2: the pin must equal the portal's own Eastern date ════════════════════════════════
{
  const early = pin("2026-10-01", [fr, baseline], "human-early");
  unhonored(
    "A2a pin one day EARLIER than the portal's Eastern date (10-01 vs 10-02)",
    [fr, baseline, early, refresh(BASE, AFTER, FLIPPED)],
    early,
  );
  const late = pin("2026-10-03", [fr, baseline], "human-late");
  unhonored(
    "A2b pin one day LATER than the portal's Eastern date (10-03 vs 10-02)",
    [fr, baseline, late, refresh(BASE, "2026-10-04T07:00:00Z", FLIPPED)],
    late,
  );
  // The UTC-day artifact: 2026-10-07T03:59:59Z is Eastern 10-06; a pin of 10-07 is the UTC day, NOT equal.
  const artifactBase = regsRaw({ commentEndDate: "2026-10-07T03:59:59Z" });
  const artifactBaseline = source(
    "regulations_gov",
    artifactBase,
    "2026-09-18T20:20:31Z",
  );
  const utcPin = pin("2026-10-07", [fr, artifactBaseline], "human-utcday");
  unhonored(
    "A2c UTC-day artifact: commentEndDate 2026-10-07T03:59:59Z (Eastern 10-06) with a pin of 10-07",
    [
      fr,
      artifactBaseline,
      utcPin,
      refresh(artifactBase, "2026-10-08T07:00:00Z", FLIPPED),
    ],
    utcPin,
  );
  // Null / rolled-over commentEndDate predicts nothing.
  const nullBase = regsRaw({ commentEndDate: null });
  const nullBaseline = source(
    "regulations_gov",
    nullBase,
    "2026-09-18T20:20:31Z",
  );
  const nullPin = pin(PIN, [fr, nullBaseline], "human-null");
  unhonored(
    "A2d baseline commentEndDate null -> no exception",
    [fr, nullBaseline, nullPin, refresh(nullBase, AFTER, FLIPPED)],
    nullPin,
  );
  const rolledBase = regsRaw({ commentEndDate: "2026-02-30T03:59:59Z" });
  const rolledBaseline = source(
    "regulations_gov",
    rolledBase,
    "2026-09-18T20:20:31Z",
  );
  const rolledPin = pin("2026-03-01", [fr, rolledBaseline], "human-rolled");
  unhonored(
    "A2e baseline commentEndDate rolled-over (2026-02-30) -> no exception",
    [fr, rolledBaseline, rolledPin, refresh(rolledBase, AFTER, FLIPPED)],
    rolledPin,
  );
}

// ═══ A3 — FLIP PLUS ANY OTHER CHANGE ════════════════════════════════════════════════════════════════
for (const [key, value] of Object.entries({
  commentEndDate: "2026-10-10T03:59:59Z",
  withdrawn: true,
  title: "Corrected notice",
  allowLateComments: true,
  docketId: "FDA-2026-N-9999",
  unknownNewEvidence: "must not be silently excluded",
  docAbstract: "The agency changed its instructions",
})) {
  unhonored(`A3 attr: flip + ${key} changed`, [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, AFTER, { ...FLIPPED, [key]: value }),
  ]);
}
for (const [key, value] of Object.entries({
  parser_version: "test-v2",
  is_extension: true,
  is_correction: true,
  is_withdrawal: true,
  is_reopening: true,
  regs_document_id: "FDA-2026-N-2886-9999",
  raw_dates_text: "New deadline instructions",
  fr_document_number: "2026-99999",
  regs_object_id: "different-object",
})) {
  unhonored(`A3 envelope: flip + ${key} changed`, [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, AFTER, FLIPPED, { [key]: value } as Partial<Observation>),
  ]);
}
{
  const flippedTop = refresh(BASE, AFTER, FLIPPED);
  unhonored("A3 top-level: flip + new top-level key", [
    fr,
    baseline,
    verdict,
    {
      ...flippedTop,
      raw: { ...(flippedTop.raw as RegsRaw), meta: { page: 1 } },
    },
  ]);
  unhonored("A3 top-level: flip + non-self link", [
    fr,
    baseline,
    verdict,
    {
      ...flippedTop,
      raw: { ...(flippedTop.raw as RegsRaw), links: { next: "new evidence" } },
    },
  ]);
  const r = flippedTop.raw as RegsRaw;
  unhonored("A3 data-level: flip + data.id changed", [
    fr,
    baseline,
    verdict,
    {
      ...flippedTop,
      raw: { ...r, data: { ...r.data, id: "FDA-2026-N-2886-0002" } },
    },
  ]);
  unhonored("A3 data-level: flip + new data-level key", [
    fr,
    baseline,
    verdict,
    { ...flippedTop, raw: { ...r, data: { ...r.data, relationships: {} } } },
  ]);
}

// ═══ A4 — NON-PIN KINDS GET NO EXCEPTION ════════════════════════════════════════════════════════════
for (const kind of [
  "confirm_withdrawn",
  "confirm_reopened",
  "dismiss_conflict",
] as const) {
  const v = verdictObs(
    {
      kind,
      operator: "test",
      note: "Probe",
      reviewed_payload_hashes: [fr.payload_hash, baseline.payload_hash],
    },
    "2026-09-23T20:41:45Z",
    `human-${kind}`,
  );
  unhonored(
    `A4 ${kind} with the identical flip`,
    [fr, baseline, v, identical, refresh(BASE, AFTER, FLIPPED)],
    v,
  );
}

// ═══ A5 — MONOTONIC ═════════════════════════════════════════════════════════════════════════════════
unhonored("A5a flip then revert (both flags)", [
  fr,
  baseline,
  verdict,
  refresh(BASE, AFTER, FLIPPED),
  refresh(BASE, LATER),
]);
unhonored(
  "A5b openForComment flips then reverts (withinCommentPeriod stays false)",
  [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, FLIPPED),
    refresh(BASE, LATER, { withinCommentPeriod: false }),
  ],
);
unhonored(
  "A5c withinCommentPeriod flips then reverts (openForComment stays false)",
  [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, FLIPPED),
    refresh(BASE, LATER, { openForComment: false }),
  ],
);
unhonored("A5d openForComment alone flips then reverts", [
  fr,
  baseline,
  verdict,
  refresh(BASE, AFTER, { openForComment: false }),
  refresh(BASE, LATER),
]);
unhonored("A5e withinCommentPeriod alone flips then reverts", [
  fr,
  baseline,
  verdict,
  refresh(BASE, AFTER, { withinCommentPeriod: false }),
  refresh(BASE, LATER),
]);
unhonored("A5f flip, revert, flip again", [
  fr,
  baseline,
  verdict,
  refresh(BASE, AFTER, FLIPPED),
  refresh(BASE, LATER),
  refresh(BASE, "2026-10-05T07:01:55Z", FLIPPED),
]);
unhonored("A5g a material change then a revert BEFORE the flip", [
  fr,
  baseline,
  verdict,
  refresh(BASE, "2026-09-25T00:00:00Z", {
    commentEndDate: "2026-11-01T03:59:59Z",
  }),
  identical,
  refresh(BASE, AFTER, FLIPPED),
]);
{
  const a = refresh(BASE, AFTER, FLIPPED);
  const b = refresh(BASE, AFTER); // same fetched_at, NOT flipped
  const tiedA = { ...a, observation_id: "tie-a" };
  const tiedB = { ...b, observation_id: "tie-b" };
  unhonored(
    "A5h two post-verdict observations with the SAME fetched_at that disagree (a,b)",
    [fr, baseline, verdict, tiedA, tiedB],
  );
  unhonored(
    "A5i two post-verdict observations with the SAME fetched_at that disagree (b,a)",
    [fr, baseline, verdict, tiedB, tiedA],
  );
  unhonored("A5j same-fetched_at disagreement in one flag only", [
    fr,
    baseline,
    verdict,
    { ...refresh(BASE, AFTER, FLIPPED), observation_id: "tie-c" },
    {
      ...refresh(BASE, AFTER, { openForComment: false }),
      observation_id: "tie-d",
    },
  ]);
  assert(
    "A5k pure function: same-epoch disagreement fails regardless of input order",
    !portalCloseEchoPreservesPin(baseline, [tiedA, tiedB], PIN_INSTANT) &&
      !portalCloseEchoPreservesPin(baseline, [tiedB, tiedA], PIN_INSTANT),
  );
  // tie-a (flipped) sorts before tie-b (unflipped), so plain monotonicity already rejects the pairs
  // above. Here the UNFLIPPED observation sorts FIRST: (open, then closed) is a legal monotone
  // sequence, so ONLY the equal-epoch disagreement guard can reject it (Codex review round 1,
  // finding 2).
  const openFirst = { ...b, observation_id: "tie-1-open" };
  const closedSecond = { ...a, observation_id: "tie-2-closed" };
  unhonored(
    "A5m same fetched_at, unflipped sorts BEFORE flipped — only the equal-epoch guard rejects",
    [fr, baseline, verdict, openFirst, closedSecond],
  );
  unhonored(
    "A5n same fetched_at, unflipped sorts BEFORE flipped — reversed input order",
    [fr, baseline, verdict, closedSecond, openFirst],
  );
  assert(
    "A5o pure function: equal-epoch guard rejects the (open, closed) tie in either input order",
    !portalCloseEchoPreservesPin(
      baseline,
      [openFirst, closedSecond],
      PIN_INSTANT,
    ) &&
      !portalCloseEchoPreservesPin(
        baseline,
        [closedSecond, openFirst],
        PIN_INSTANT,
      ),
  );
  const input = [tiedB, tiedA];
  const before = JSON.stringify(input);
  portalCloseEchoPreservesPin(baseline, input, PIN_INSTANT);
  assert(
    "A5l pure function: does not sort or mutate the caller's array",
    JSON.stringify(input) === before &&
      input[0] === tiedB &&
      input[1] === tiedA,
  );
}

// ═══ A6 — OTHER SOURCES ═════════════════════════════════════════════════════════════════════════════
unhonored("A6a newer FR observation BEFORE the flip", [
  fr,
  baseline,
  verdict,
  frAt("2026-09-25T00:00:00Z"),
  refresh(BASE, AFTER, FLIPPED),
]);
unhonored("A6b newer FR observation AFTER the flip", [
  fr,
  baseline,
  verdict,
  refresh(BASE, AFTER, FLIPPED),
  frAt("2026-10-05T00:00:00Z"),
]);
unhonored("A6c newer FR observation between identical refreshes", [
  fr,
  baseline,
  verdict,
  identical,
  frAt("2026-10-01T06:00:00Z"),
  refresh(BASE, "2026-10-02T05:26:26Z"),
  refresh(BASE, AFTER, FLIPPED),
]);
unhonored("A6d newer FR observation at the same fetched_at as the flip", [
  fr,
  baseline,
  verdict,
  refresh(BASE, AFTER, FLIPPED),
  frAt(AFTER),
]);
// A6e — reconcile-v2.4 (ADR 0016 §6): a newer govinfo row is not evidence about this window (only
// DERIVATION_SOURCES are), so the echo exception decides exactly as it would without it: honored.
{
  const flip = refresh(BASE, AFTER, FLIPPED); // ONE row shared by both chains (ids are minted per call)
  const withGov = reconcile(
    [
      fr,
      baseline,
      verdict,
      source("govinfo", { notice: "published text" }, "2026-10-05T00:00:00Z"),
      flip,
    ],
    NOW,
  );
  const without = reconcile([fr, baseline, verdict, flip], NOW);
  produced.push({ label: "A6e newer govinfo observation", r: withGov });
  assert(
    "A6e newer govinfo observation — the echo exception decides as without it (honored, same window)",
    withGov.window.conflict_flags.includes("human_resolved") &&
      JSON.stringify(withGov.window) === JSON.stringify(without.window),
    `${withGov.window.confidence} ${withGov.window.conflict_flags.join(",")}`,
  );
}

// ═══ A7 — FLAG SHAPES ═══════════════════════════════════════════════════════════════════════════════
{
  const closedBase = regsRaw(FLIPPED);
  const closedBaseline = source(
    "regulations_gov",
    closedBase,
    "2026-10-04T00:00:00Z",
  );
  // The verdict must come AFTER this baseline (pin() stamps 2026-09-23, before it) so the closed
  // payload is the REVIEWED baseline and the false->true refresh is rejected by clause 3 alone —
  // not by the absence of any eligible baseline (Codex review round 1, finding 1).
  const closedPin = verdictObs(
    {
      kind: "pin_close",
      pinned_close_date: PIN,
      operator: "test",
      note: "Reopening notice verified",
      reviewed_payload_hashes: [fr.payload_hash, closedBaseline.payload_hash],
    },
    "2026-10-05T00:00:00Z",
    "human-closed",
  );
  produced.push({
    label: "A7-control already-false baseline, identical refresh",
    r: reconcile(
      [
        fr,
        closedBaseline,
        closedPin,
        refresh(closedBase, "2026-10-06T00:00:00Z"),
      ],
      NOW,
    ),
  });
  assert(
    "A7-control already-false baseline with an identical refresh IS honored (plain v2.1 path)",
    produced[produced.length - 1]!.r.window.conflict_flags.includes(
      "human_resolved",
    ),
  );
  unhonored(
    "A7a false->true when the baseline was already false (both flags)",
    [
      fr,
      closedBaseline,
      closedPin,
      refresh(closedBase, "2026-10-06T00:00:00Z", {
        openForComment: true,
        withinCommentPeriod: true,
      }),
    ],
    closedPin,
  );
  unhonored(
    "A7b false->true when the baseline was already false (openForComment alone)",
    [
      fr,
      closedBaseline,
      closedPin,
      refresh(closedBase, "2026-10-06T00:00:00Z", { openForComment: true }),
    ],
    closedPin,
  );
  const noFlagBase = regsRaw({
    openForComment: undefined,
    withinCommentPeriod: undefined,
  });
  delete noFlagBase.data.attributes.openForComment;
  delete noFlagBase.data.attributes.withinCommentPeriod;
  const noFlagBaseline = source(
    "regulations_gov",
    noFlagBase,
    "2026-09-18T20:20:31Z",
  );
  const noFlagPin = pin(PIN, [fr, noFlagBaseline], "human-noflag");
  unhonored(
    "A7c flags ABSENT in baseline but present (false) later",
    [fr, noFlagBaseline, noFlagPin, refresh(noFlagBase, AFTER, FLIPPED)],
    noFlagPin,
  );
  unhonored(
    "A7d openForComment absent in baseline, present (false) later",
    [
      fr,
      noFlagBaseline,
      noFlagPin,
      refresh(noFlagBase, AFTER, { openForComment: false }),
    ],
    noFlagPin,
  );
  unhonored("A7e flag present (true) in baseline but ABSENT later (both)", [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, {
      openForComment: undefined,
      withinCommentPeriod: undefined,
    }),
  ]);
  unhonored("A7f openForComment present (true) in baseline, absent later", [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, { openForComment: undefined }),
  ]);
  unhonored('A7g the string "false" instead of boolean (both)', [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, {
      openForComment: "false",
      withinCommentPeriod: "false",
    }),
  ]);
  unhonored('A7h the string "false" on one flag, boolean on the other', [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, {
      openForComment: false,
      withinCommentPeriod: "false",
    }),
  ]);
  unhonored("A7i true->null", [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, { openForComment: null, withinCommentPeriod: null }),
  ]);
  unhonored("A7j true->0", [
    fr,
    baseline,
    verdict,
    refresh(BASE, AFTER, { openForComment: 0, withinCommentPeriod: 0 }),
  ]);
  const strBase = regsRaw({ openForComment: "true" });
  const strBaseline = source(
    "regulations_gov",
    strBase,
    "2026-09-18T20:20:31Z",
  );
  const strPin = pin(PIN, [fr, strBaseline], "human-str");
  unhonored(
    'A7k baseline string "true" -> boolean false is not a boolean true->false',
    [
      fr,
      strBaseline,
      strPin,
      refresh(strBase, AFTER, {
        openForComment: false,
        withinCommentPeriod: false,
      }),
    ],
    strPin,
  );
}

// ═══ A8 — EVIDENCE ══════════════════════════════════════════════════════════════════════════════════
{
  const noHash = verdictObs(
    {
      kind: "pin_close",
      pinned_close_date: PIN,
      operator: "test",
      note: "Probe",
      reviewed_payload_hashes: ["f".repeat(64)],
    },
    "2026-09-23T20:41:45Z",
    "human-nohash",
  );
  unhonored(
    "A8a reviewed_payload_hashes lacks the baseline hash",
    [fr, baseline, noHash, identical, refresh(BASE, AFTER, FLIPPED)],
    noHash,
  );
  const frOnlyHash = verdictObs(
    {
      kind: "pin_close",
      pinned_close_date: PIN,
      operator: "test",
      note: "Probe",
      reviewed_payload_hashes: [fr.payload_hash],
    },
    "2026-09-23T20:41:45Z",
    "human-fronly",
  );
  unhonored(
    "A8b reviewed_payload_hashes names only the FR observation",
    [fr, baseline, frOnlyHash, refresh(BASE, AFTER, FLIPPED)],
    frOnlyHash,
  );
  unhonored("A8c omitted history (no Regs baseline at/before the verdict)", [
    fr,
    verdict,
    refresh(BASE, AFTER, FLIPPED),
  ]);
  // The latest pre-verdict Regs observation is the baseline — a reviewed hash on an OLDER one does not count.
  const staleReviewed = pin(PIN, [fr, baseline], "human-stale");
  unhonored(
    "A8d latest pre-verdict Regs observation (unreviewed) is the baseline, not the older reviewed one",
    [
      fr,
      baseline,
      refresh(BASE, "2026-09-20T00:00:00Z", { title: "Renamed before review" }),
      staleReviewed,
      refresh(BASE, AFTER, FLIPPED),
    ],
    staleReviewed,
  );
}

// ═══ LIVE HISTORIES — splice adversarial evidence into each of the 7 exported chains ════════════════
const HERE = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "review-echo-histories.json"), "utf8"),
) as { exported_at: string; observations: Observation[] };
const EXPORTED_AT = new Date(fixture.exported_at);
const historyByOcd = new Map<string, Observation[]>();
for (const o of fixture.observations) {
  const list = historyByOcd.get(o.ocd_id) ?? [];
  list.push(o);
  historyByOcd.set(o.ocd_id, list);
}
function liveUnhonored(
  label: string,
  chain: Observation[],
  human: Observation,
) {
  let r: ReconcileResult;
  try {
    r = reconcile(chain, EXPORTED_AT);
  } catch (e) {
    assert(
      `${label} — engine RETURNED (no throw)`,
      false,
      `THREW: ${(e as Error).message}`,
    );
    return;
  }
  produced.push({ label, r });
  assert(
    `${label} — NOT honored`,
    !r.window.conflict_flags.includes("human_resolved") &&
      !r.window.current_observation_ids.includes(human.observation_id),
    `${r.window.confidence} ${r.window.conflict_flags.join(",")}`,
  );
  if (r.window.confidence === "conflicting")
    assert(
      `${label} — CONFLICTING carries a ConflictRecord`,
      r.conflict !== null,
    );
}
for (const [ocd, history] of historyByOcd) {
  const doc = ocd.split("/").pop()!;
  const human = history.find((o) => o.source === "human_review")!;
  const liveFr = history.find((o) => o.source === "federal_register")!;
  const flipped = history.filter(
    (o) =>
      o.source === "regulations_gov" &&
      (o.raw as RegsRaw).data.attributes.openForComment === false,
  );
  const firstFlip = [...flipped].sort((a, b) =>
    a.fetched_at.localeCompare(b.fetched_at),
  )[0]!;
  // Control: the untouched live history IS honored (the echo test proves this in detail).
  const control = reconcile(history, EXPORTED_AT);
  produced.push({ label: `LIVE ${doc} control`, r: control });
  assert(
    `LIVE ${doc} control: untouched history honored`,
    control.window.conflict_flags.includes("human_resolved"),
  );
  liveUnhonored(
    `LIVE ${doc} + newer FR observation (re-fetched after the verdict)`,
    [
      ...history,
      {
        ...liveFr,
        observation_id: "live-fr-refetch",
        fetched_at: "2026-10-01T00:00:00Z",
        ocd_id: ocd,
      },
    ],
    human,
  );
  {
    // v2.4 (ADR 0016 §6): a newer govinfo row leaves the live decision exactly as without it.
    const withGov = reconcile(
      [
        ...history,
        {
          ...source(
            "govinfo",
            { notice: "published text" },
            "2026-10-12T00:00:00Z",
          ),
          ocd_id: ocd,
        },
      ],
      EXPORTED_AT,
    );
    const without = reconcile(history, EXPORTED_AT);
    produced.push({
      label: `LIVE ${doc} + newer govinfo observation`,
      r: withGov,
    });
    assert(
      `LIVE ${doc} + newer govinfo observation — decided exactly as without it`,
      JSON.stringify(withGov.window) === JSON.stringify(without.window) &&
        withGov.window.current_observation_ids.includes(
          human.observation_id,
        ) ===
          without.window.current_observation_ids.includes(human.observation_id),
      `${withGov.window.confidence} ${withGov.window.conflict_flags.join(",")}`,
    );
  }
  liveUnhonored(
    `LIVE ${doc} + a revert to open after the flip`,
    [
      ...history,
      {
        ...firstFlip,
        observation_id: "live-revert",
        fetched_at: "2026-10-17T00:00:00Z",
        raw: {
          ...(firstFlip.raw as RegsRaw),
          data: {
            ...(firstFlip.raw as RegsRaw).data,
            attributes: {
              ...(firstFlip.raw as RegsRaw).data.attributes,
              openForComment: true,
              withinCommentPeriod: true,
            },
          },
        },
      },
    ],
    human,
  );
  liveUnhonored(
    `LIVE ${doc} with the first flip moved BEFORE the pinned instant`,
    history.map((o) =>
      o === firstFlip
        ? {
            ...o,
            fetched_at: new Date(
              new Date(human.fetched_at).getTime() + 60_000,
            ).toISOString(),
          }
        : o,
    ),
    human,
  );
}

// ═══ G — GLOBAL DUAL-FIRE INVARIANTS over every window produced above ═══════════════════════════════
{
  for (const { label, r } of produced) {
    if (r.window.confidence === "conflicting" && r.conflict === null)
      assert(
        `GLOBAL: ${label} — CONFLICTING window without a ConflictRecord (silent conflict)`,
        false,
      );
    if (
      r.conflict !== null &&
      r.window.conflict_flags.includes("human_resolved")
    )
      assert(
        `GLOBAL: ${label} — live ConflictRecord co-exists with human_resolved (inconsistent pair)`,
        false,
      );
    if (
      r.window.confidence === "high" &&
      !r.window.conflict_flags.includes("human_resolved")
    )
      assert(
        `GLOBAL: ${label} — HIGH without a human verdict over an FR/Regs mismatch (fake certainty)`,
        false,
      );
  }
  assert(
    `GLOBAL: dual-fire invariants held across all ${produced.length} produced results`,
    true,
  );
}

console.log("\n=== reconcile-review-echo-ADVERSARY results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL PROBES HELD" : `${failures} PROBE(S) BROKE THROUGH`}`,
);
process.exit(failures === 0 ? 0 : 1);
