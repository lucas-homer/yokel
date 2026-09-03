/**
 * reconcile-human-review-adversary.test.ts — ADVERSARIAL probes against the reconcile-v2
 * honor-the-verdict overlay (Slice R, PR-R2; plans/review-resolve.md "Decisions locked").
 *
 * Goal: MAKE CONFIDENCE LIE — find a chain+verdict combination where the engine publishes fake
 * certainty, throws instead of returning (a production brick: that window can never re-derive), or
 * silences the dual-fire. Sections:
 *   S1 — freshness-gate ordering: multiple verdicts vs the newest source; malformed-latest masking
 *        a valid older verdict.
 *   S2 — govinfo observations count as sources for the gate even though they play no part in
 *        derivation.
 *   S3 — contract-illegality hunting: every kind honored over every degenerate machine branch
 *        (UNKNOWN + pin, withdrawn + reopen, null_end_date_open_status + withdraw, tz artifact
 *        carried into the overlay, withdrawn_vs_open + pin past/future, human-only chain). A THROW
 *        anywhere here is a brick.
 *   S4 — dual-fire silence: no honored path may leave confidence=conflicting; no ConflictRecord may
 *        co-exist with a human_resolved flag; illegal verdicts (smuggled date, blank note, zero
 *        hashes) must NOT silence a live alarm; the temporal-only gate honors a verdict whose
 *        reviewed_payload_hashes match nothing in the chain (documented behavior, probed).
 *   S6 — spicy-regs history replay: FR-2018-27875 tz artifact + verdicts layered on; rolled-over
 *        2026-02-30 dates (source-side AND pin-side); EPA 2025-02910 multi-docket linkage.
 *   S7 — determinism under array order: equal-fetched_at verdict pairs (and same-source machine
 *        pairs) shuffled — the plan's "same chain in, same window out".
 *
 * Pure engine, no DB. Harness style: assert/out/failures, process.exit.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ParticipationWindow, type Observation } from "@yokel/contracts";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { reconcile, type ReconcileResult } from "../src/reconcile/reconcile.js";
import { frCloseDateToUtcInstant } from "../src/reconcile/eastern-date.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
function parses(name: string, w: unknown): void {
  const r = ParticipationWindow.safeParse(w);
  assert(
    `${name} — window passes ParticipationWindow.parse`,
    r.success,
    r.success ? "" : JSON.stringify(r.error.issues),
  );
}
/** A THROW from the engine = a window that can never re-derive = a production brick. */
function runs(name: string, fn: () => ReconcileResult): ReconcileResult | null {
  try {
    const r = fn();
    assert(`${name} — engine RETURNED (no throw)`, true);
    return r;
  } catch (e) {
    assert(
      `${name} — engine RETURNED (no throw)`,
      false,
      `THREW: ${(e as Error).message}`,
    );
    return null;
  }
}
/** Every produced result feeds the global dual-fire invariants at the bottom. */
const produced: { label: string; r: ReconcileResult }[] = [];
function track(
  label: string,
  r: ReconcileResult | null,
): ReconcileResult | null {
  if (r) produced.push({ label, r });
  return r;
}

const HERE = dirname(fileURLToPath(import.meta.url));
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;
const regsFixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as { data: { id: string; attributes: Record<string, unknown> } };

const NOW = new Date("2026-06-01T00:00:00Z");
const OCD = "ocd-participation-window/federal/2025-02910";
let idSeq = 0;

function frObs(
  rawOverrides: Record<string, unknown>,
  fetchedAt = "2026-05-01T00:00:00Z",
): Observation {
  const raw = { ...frFixture, ...rawOverrides };
  const cand = parseFrObservation(raw);
  return {
    observation_id: `fr-${idSeq++}`,
    ...cand,
    ocd_id: OCD,
    raw,
    fetched_at: fetchedAt,
  } as Observation;
}
function regsObs(
  attrOverrides: Record<string, unknown>,
  fetchedAt = "2026-05-01T00:00:00Z",
): Observation {
  const raw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  Object.assign(raw.data.attributes, attrOverrides);
  const cand = parseRegsObservation(raw);
  return {
    observation_id: `regs-${idSeq++}`,
    ...cand,
    ocd_id: OCD,
    raw,
    fetched_at: fetchedAt,
  } as Observation;
}
/** A human_review Observation per the PR-R1 row conventions. */
function hrObs(
  raw: Record<string, unknown>,
  fetchedAt: string,
  note = "adversary probe",
): Observation {
  return {
    observation_id: `hr-${idSeq++}`,
    ocd_id: OCD,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: "c".repeat(64),
    fetched_at: fetchedAt,
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: {
      operator: "adversary",
      note,
      reviewed_payload_hashes: ["a".repeat(64)],
      ...raw,
    },
  } as Observation;
}
/** A govinfo Observation — a SOURCE for the freshness gate, invisible to derivation. */
function govObs(fetchedAt: string): Observation {
  return {
    observation_id: `gov-${idSeq++}`,
    ocd_id: OCD,
    source: "govinfo",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: "d".repeat(64),
    fetched_at: fetchedAt,
    parser_version: "govinfo-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: { pkg: "FR-2026-05-01" },
  } as Observation;
}

// Machine-CONFLICTING chain: FR says July 15, Regs says July 20 Eastern — fr_regs_date_mismatch.
const conflictChain = () => [
  frObs({ comments_close_on: "2026-07-15" }, "2026-05-01T00:00:00Z"),
  regsObs(
    {
      commentEndDate: "2026-07-21T03:59:59Z",
      withdrawn: false,
      openForComment: true,
    },
    "2026-05-02T00:00:00Z",
  ),
];
// FR-2018-27875 artifact chain: SAME Eastern date (07-20), DIFFERENT UTC day (07-21) — HIGH + tz flag.
const tzChain = () => [
  frObs({ comments_close_on: "2026-07-20" }, "2026-05-01T00:00:00Z"),
  regsObs(
    {
      commentEndDate: "2026-07-21T03:59:59Z",
      withdrawn: false,
      openForComment: true,
    },
    "2026-05-02T00:00:00Z",
  ),
];
// withdrawn_vs_open chain: Regs withdrawn=true while FR reads open — machine CONFLICTING + withdrawn.
const withdrawnVsOpenChain = () => [
  frObs({ comments_close_on: "2026-07-15" }, "2026-05-01T00:00:00Z"),
  regsObs(
    {
      commentEndDate: "2026-07-21T03:59:59Z",
      withdrawn: true,
      openForComment: false,
    },
    "2026-05-02T00:00:00Z",
  ),
];

// ═══ S1 — FRESHNESS-GATE ORDERING ════════════════════════════════════════════════════════════════════

// S1a: an OLDER verdict individually FAILS the gate (source newer than it), the LATEST passes — the
// latest is honored with ITS pin, never the older one. (The inverse — older passes, latest fails — is
// mathematically unrepresentable: latest = max(fetched_at), so older ≥ all sources ⇒ latest ≥ all
// sources. The gate semantic "the latest human_review observation" is therefore coherent; see report.)
{
  const v1 = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-16" },
    "2026-05-01T12:00:00Z", // older than the regs obs @05-02 — fails the gate alone
  );
  const v2 = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-22" },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S1a",
    runs("S1a gate: latest-of-two honored", () =>
      reconcile([...conflictChain(), v1, v2], NOW),
    ),
  );
  if (r) {
    assert(
      "S1a: LATEST verdict honored with ITS pin (older verdict never consulted)",
      r.window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-22") &&
        r.window.conflict_flags.includes("human_resolved"),
      String(r.window.resolved_close_utc),
    );
    parses("S1a", r.window);
  }
}

// S1b: when the LATEST verdict fails the gate, the overlay is skipped entirely — machine CONFLICTING
// stands and the record fires (no honoring of any verdict).
{
  const v1 = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-16" },
    "2026-05-01T06:00:00Z",
  );
  const v2 = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-22" },
    "2026-05-01T12:00:00Z", // still older than the regs obs @05-02
  );
  const r = track(
    "S1b",
    runs("S1b gate: both verdicts stale", () =>
      reconcile([...conflictChain(), v1, v2], NOW),
    ),
  );
  if (r) {
    assert(
      "S1b: no honoring — CONFLICTING stands, record emitted, no human_resolved",
      r.window.confidence === "conflicting" &&
        !r.window.conflict_flags.includes("human_resolved") &&
        r.conflict !== null,
      `${r.window.confidence} [${r.window.conflict_flags.join(",")}]`,
    );
    parses("S1b", r.window);
  }
}

// S1c: MALFORMED LATEST masks a VALID OLDER verdict that individually passes the gate. Current
// semantic: degrade to PURE derivation (no fallback to the older verdict). Conservative direction —
// less honoring, never more — judged acceptable; probed so a regression TOWARD honoring is caught.
{
  const valid = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z", // ≥ all sources — would pass the gate alone
  );
  const malformed = hrObs({ kind: "pin_close" }, "2026-05-04T00:00:00Z"); // pin w/o date — fails schema
  const r = track(
    "S1c",
    runs("S1c gate: malformed latest masks valid older", () =>
      reconcile([...conflictChain(), valid, malformed], NOW),
    ),
  );
  if (r) {
    assert(
      "S1c: pure derivation resumes (no fallback to the older valid verdict) — CONFLICTING + record",
      r.window.confidence === "conflicting" &&
        !r.window.conflict_flags.includes("human_resolved") &&
        r.conflict !== null,
      `${r.window.confidence} [${r.window.conflict_flags.join(",")}]`,
    );
    parses("S1c", r.window);
  }
}

// ═══ S2 — GOVINFO OBSERVATIONS GATE THE VERDICT (though they play no part in derivation) ═════════════

// S2a: a govinfo observation is the NEWEST thing in the chain — the verdict MUST be un-honored and the
// machine conflict must resurface with its ConflictRecord.
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  const gov = govObs("2026-05-04T00:00:00Z"); // newest of all
  const r = track(
    "S2a",
    runs("S2a govinfo newest", () =>
      reconcile([...conflictChain(), pin, gov], NOW),
    ),
  );
  if (r) {
    assert(
      "S2a: govinfo (non-derivation source) UN-honors the verdict — CONFLICTING resurfaces",
      r.window.confidence === "conflicting" &&
        !r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence} [${r.window.conflict_flags.join(",")}]`,
    );
    assert(
      "S2a: ConflictRecord emitted (dual-fire preserved past a govinfo-staled verdict)",
      r.conflict !== null &&
        !((r.conflict?.conflict_flags ?? []) as string[]).includes(
          "human_resolved",
        ),
      r.conflict === null ? "null" : r.conflict.conflict_flags.join(","),
    );
    parses("S2a", r.window);
  }
}

// S2b: govinfo OLDER than the verdict — verdict stays honored.
{
  const gov = govObs("2026-05-02T12:00:00Z");
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S2b",
    runs("S2b govinfo older", () =>
      reconcile([...conflictChain(), gov, pin], NOW),
    ),
  );
  if (r) {
    assert(
      "S2b: older govinfo does not un-honor — pin honored at HIGH, no record",
      r.window.confidence === "high" &&
        r.window.conflict_flags.includes("human_resolved") &&
        r.conflict === null,
      `${r.window.confidence}`,
    );
    parses("S2b", r.window);
  }
}

// ═══ S3 — CONTRACT-ILLEGALITY HUNTING (a throw = a bricked window) ═══════════════════════════════════

// S3a: machine UNKNOWN (regs present, no dates anywhere, not open) + pin_close → HIGH pinned.
{
  const chain = [
    regsObs(
      { commentEndDate: null, withdrawn: false, openForComment: false },
      "2026-05-01T00:00:00Z",
    ),
    hrObs(
      { kind: "pin_close", pinned_close_date: "2026-07-22" },
      "2026-05-02T00:00:00Z",
    ),
  ];
  const r = track(
    "S3a",
    runs("S3a UNKNOWN + pin_close", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3a: UNKNOWN machine + honored pin → HIGH with the pinned close, status open",
      r.window.confidence === "high" &&
        r.window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-22") &&
        r.window.status === "open",
      `${r.window.confidence} ${r.window.status} ${r.window.resolved_close_utc}`,
    );
    parses("S3a", r.window);
  }
}

// S3b: null_end_date_open_status UNKNOWN variant (no FR fallback) + confirm_withdrawn.
// Contract landmine probed: UNKNOWN forces null close; withdrawn status must coexist.
{
  const chain = [
    regsObs(
      { commentEndDate: null, withdrawn: false, openForComment: true },
      "2026-05-01T00:00:00Z",
    ),
    hrObs({ kind: "confirm_withdrawn" }, "2026-05-02T00:00:00Z"),
  ];
  const r = track(
    "S3b",
    runs("S3b null_end UNKNOWN + confirm_withdrawn", () =>
      reconcile(chain, NOW),
    ),
  );
  if (r) {
    assert(
      "S3b: UNKNOWN (null close) + withdrawn status + carried null_end flag + human_resolved",
      r.window.confidence === "unknown" &&
        r.window.resolved_close_utc === null &&
        r.window.status === "withdrawn" &&
        r.window.conflict_flags.includes("null_end_date_open_status") &&
        r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence} ${r.window.status} [${r.window.conflict_flags.join(",")}]`,
    );
    parses("S3b", r.window);
  }
}

// S3c: null_end_date_open_status LOW variant (FR fallback date) + confirm_withdrawn.
{
  const chain = [
    frObs({ comments_close_on: "2026-07-15" }, "2026-05-01T00:00:00Z"),
    regsObs(
      { commentEndDate: null, withdrawn: false, openForComment: true },
      "2026-05-01T00:00:00Z",
    ),
    hrObs({ kind: "confirm_withdrawn" }, "2026-05-02T00:00:00Z"),
  ];
  const r = track(
    "S3c",
    runs("S3c null_end LOW + confirm_withdrawn", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3c: LOW keeps the historical FR close, status withdrawn (contract: LOW ⇒ non-null close)",
      r.window.confidence === "low" &&
        r.window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-15") &&
        r.window.status === "withdrawn",
      `${r.window.confidence} ${r.window.resolved_close_utc}`,
    );
    parses("S3c", r.window);
  }
}

// S3d: machine WITHDRAWN/UNKNOWN (regs withdrawn=true, no dates) + confirm_reopened →
// status OPEN over a live withdrawn=true signal, confidence UNKNOWN, null close.
{
  const chain = [
    regsObs(
      { commentEndDate: null, withdrawn: true, openForComment: false },
      "2026-05-01T00:00:00Z",
    ),
    hrObs({ kind: "confirm_reopened" }, "2026-05-02T00:00:00Z"),
  ];
  const r = track(
    "S3d",
    runs("S3d withdrawn/UNKNOWN + confirm_reopened", () =>
      reconcile(chain, NOW),
    ),
  );
  if (r) {
    assert(
      "S3d: open + UNKNOWN + null close (never a coerced date to justify the reopening)",
      r.window.status === "open" &&
        r.window.confidence === "unknown" &&
        r.window.resolved_close_utc === null,
      `${r.window.status} ${r.window.confidence} ${r.window.resolved_close_utc}`,
    );
    parses("S3d", r.window);
  }
}

// S3e: machine WITHDRAWN/LOW (regs withdrawn with a date) + confirm_reopened → open + LOW + close.
{
  const chain = [
    regsObs(
      {
        commentEndDate: "2026-07-21T03:59:59Z",
        withdrawn: true,
        openForComment: false,
      },
      "2026-05-01T00:00:00Z",
    ),
    hrObs({ kind: "confirm_reopened" }, "2026-05-02T00:00:00Z"),
  ];
  const r = track(
    "S3e",
    runs("S3e withdrawn/LOW + confirm_reopened", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3e: open + LOW with the machine close carried",
      r.window.status === "open" &&
        r.window.confidence === "low" &&
        r.window.resolved_close_utc !== null,
      `${r.window.status} ${r.window.confidence}`,
    );
    parses("S3e", r.window);
  }
}

// S3f: withdrawn_vs_open CONFLICTING + honored FUTURE pin → HIGH + status OPEN while Regs still says
// withdrawn=true. Contract-legal (probed); the pin outranks while honored — see report for semantics.
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-22" },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S3f",
    runs("S3f withdrawn_vs_open + future pin", () =>
      reconcile([...withdrawnVsOpenChain(), pin], NOW),
    ),
  );
  if (r) {
    assert(
      "S3f: HIGH + open from the pin; withdrawn_vs_open carried + human_resolved; NO record",
      r.window.confidence === "high" &&
        r.window.status === "open" &&
        r.window.conflict_flags.includes("withdrawn_vs_open") &&
        r.window.conflict_flags.includes("human_resolved") &&
        r.conflict === null,
      `${r.window.confidence} ${r.window.status} [${r.window.conflict_flags.join(",")}]`,
    );
    parses("S3f", r.window);
  }
}

// S3g: withdrawn_vs_open + honored PAST pin → status closed.
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-05-20" },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S3g",
    runs("S3g withdrawn_vs_open + past pin", () =>
      reconcile([...withdrawnVsOpenChain(), pin], NOW),
    ),
  );
  if (r) {
    assert(
      "S3g: past pin → closed at HIGH (status derives from the pinned close alone)",
      r.window.confidence === "high" && r.window.status === "closed",
      `${r.window.confidence} ${r.window.status}`,
    );
    parses("S3g", r.window);
  }
}

// S3h: null_end UNKNOWN chain + pin — the carried null_end_date_open_status flag rides with HIGH.
{
  const chain = [
    regsObs(
      { commentEndDate: null, withdrawn: false, openForComment: true },
      "2026-05-01T00:00:00Z",
    ),
    hrObs(
      { kind: "pin_close", pinned_close_date: "2026-07-22" },
      "2026-05-02T00:00:00Z",
    ),
  ];
  const r = track(
    "S3h",
    runs("S3h null_end UNKNOWN + pin_close", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3h: HIGH + [null_end_date_open_status, human_resolved] is contract-legal and returned",
      r.window.confidence === "high" &&
        r.window.conflict_flags.includes("null_end_date_open_status") &&
        r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence} [${r.window.conflict_flags.join(",")}]`,
    );
    parses("S3h", r.window);
  }
}

// S3i: tz-artifact HIGH chain + confirm_withdrawn → LOW carrying tz_normalization_only.
// The contract forbids tz only with CONFLICTING — LOW must pass. A throw here = brick.
{
  const chain = [
    ...tzChain(),
    hrObs({ kind: "confirm_withdrawn" }, "2026-05-03T00:00:00Z"),
  ];
  const r = track(
    "S3i",
    runs("S3i tz HIGH + confirm_withdrawn", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3i: LOW + withdrawn + carried close, tz_normalization_only rides along legally",
      r.window.confidence === "low" &&
        r.window.status === "withdrawn" &&
        r.window.resolved_close_utc !== null &&
        r.window.conflict_flags.includes("tz_normalization_only") &&
        r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence} [${r.window.conflict_flags.join(",")}]`,
    );
    parses("S3i", r.window);
  }
}

// S3j: HUMAN-ONLY chain (zero source observations) + pin → honored (gate is vacuously true) at HIGH.
// Contract-legal; flagged in the report — HIGH with no source evidence in the chain at all.
{
  const chain = [
    hrObs(
      { kind: "pin_close", pinned_close_date: "2026-07-22" },
      "2026-05-01T00:00:00Z",
    ),
  ];
  const r = track(
    "S3j",
    runs("S3j human-only chain + pin", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3j: honored on a source-free chain — HIGH, open, pinned close (see report)",
      r.window.confidence === "high" &&
        r.window.status === "open" &&
        r.window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-22"),
      `${r.window.confidence} ${r.window.status}`,
    );
    parses("S3j", r.window);
  }
}

// S3k: machine UNKNOWN + dismiss_conflict → UNKNOWN stands (null close) + human_resolved.
{
  const chain = [
    regsObs(
      { commentEndDate: null, withdrawn: false, openForComment: false },
      "2026-05-01T00:00:00Z",
    ),
    hrObs({ kind: "dismiss_conflict" }, "2026-05-02T00:00:00Z"),
  ];
  const r = track(
    "S3k",
    runs("S3k UNKNOWN + dismiss_conflict", () => reconcile(chain, NOW)),
  );
  if (r) {
    assert(
      "S3k: UNKNOWN + null close survives an honored dismiss (no fabricated certainty)",
      r.window.confidence === "unknown" &&
        r.window.resolved_close_utc === null &&
        r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence} ${r.window.resolved_close_utc}`,
    );
    parses("S3k", r.window);
  }
}

// ═══ S4 — DUAL-FIRE SILENCE + ILLEGAL-VERDICT ALARM PROBES ═══════════════════════════════════════════

// S4a: every kind honored over the CONFLICTING chain — none may leave confidence=conflicting, none may
// emit a record while honored.
for (const kind of [
  "pin_close",
  "confirm_withdrawn",
  "confirm_reopened",
  "dismiss_conflict",
] as const) {
  const raw =
    kind === "pin_close" ? { kind, pinned_close_date: "2026-07-20" } : { kind };
  const r = track(
    `S4a:${kind}`,
    runs(`S4a ${kind} honored over CONFLICTING`, () =>
      reconcile([...conflictChain(), hrObs(raw, "2026-05-03T00:00:00Z")], NOW),
    ),
  );
  if (r) {
    assert(
      `S4a ${kind}: honored ⇒ never conflicting, never a live record, flags carry the dispute + human_resolved`,
      r.window.confidence !== "conflicting" &&
        r.conflict === null &&
        r.window.conflict_flags.includes("fr_regs_date_mismatch") &&
        r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence} conflict=${r.conflict === null ? "null" : "LIVE"}`,
    );
    parses(`S4a ${kind}`, r.window);
  }
}

// S4b/c/d: ILLEGAL verdicts must never silence a live alarm — smuggled date on dismiss, blank note,
// zero reviewed hashes. All must be ignored: CONFLICTING + record stands.
{
  const illegal: [string, Record<string, unknown>][] = [
    [
      "S4b smuggled date on dismiss_conflict",
      { kind: "dismiss_conflict", pinned_close_date: "2026-07-20" },
    ],
    ["S4c whitespace-only note", { kind: "dismiss_conflict", note: "   " }],
    [
      "S4d zero reviewed_payload_hashes",
      { kind: "dismiss_conflict", reviewed_payload_hashes: [] },
    ],
  ];
  for (const [label, raw] of illegal) {
    const r = track(
      label,
      runs(label, () =>
        reconcile(
          [...conflictChain(), hrObs(raw, "2026-05-03T00:00:00Z")],
          NOW,
        ),
      ),
    );
    if (r) {
      assert(
        `${label}: rejected verdict never silences — CONFLICTING + record stand`,
        r.window.confidence === "conflicting" &&
          !r.window.conflict_flags.includes("human_resolved") &&
          r.conflict !== null,
        `${r.window.confidence}`,
      );
    }
  }
}

// S4e: the gate is TEMPORAL-ONLY — a verdict whose reviewed_payload_hashes match NOTHING in the chain
// is still honored (per the locked plan; probed + reported as a design note, not asserted wrong).
{
  const pin = hrObs(
    {
      kind: "pin_close",
      pinned_close_date: "2026-07-20",
      reviewed_payload_hashes: ["b".repeat(64)], // matches no observation in this chain
    },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S4e",
    runs("S4e unmatched reviewed hashes", () =>
      reconcile([...conflictChain(), pin], NOW),
    ),
  );
  if (r) {
    assert(
      "S4e: temporal gate only — verdict honored despite unmatched reviewed hashes (documented)",
      r.window.confidence === "high" &&
        r.window.conflict_flags.includes("human_resolved"),
      `${r.window.confidence}`,
    );
  }
}

// ═══ S6 — SPICY-REGS HISTORY REPLAY ══════════════════════════════════════════════════════════════════

// S6a: FR-2018-27875 replay — the tz artifact must stay NON-conflicting under the machine, and an
// honored pin keeps the informational marker riding with HIGH.
{
  const base = track(
    "S6a-base",
    runs("S6a tz baseline", () => reconcile(tzChain(), NOW)),
  );
  if (base) {
    assert(
      "S6a baseline: same-Eastern-day 1-UTC-day gap is HIGH + tz_normalization_only, NEVER conflicting",
      base.window.confidence === "high" &&
        base.window.conflict_flags.includes("tz_normalization_only") &&
        base.conflict === null,
      `${base.window.confidence} [${base.window.conflict_flags.join(",")}]`,
    );
  }
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S6a-pin",
    runs("S6a tz + pin", () => reconcile([...tzChain(), pin], NOW)),
  );
  if (r) {
    assert(
      "S6a pin: tz marker + human_resolved ride with HIGH, window parses",
      r.window.confidence === "high" &&
        r.window.conflict_flags.includes("tz_normalization_only") &&
        r.window.conflict_flags.includes("human_resolved"),
      `[${r.window.conflict_flags.join(",")}]`,
    );
    parses("S6a pin", r.window);
  }
  // dismiss over the (non-conflicting) tz artifact: confidence stands at HIGH — nothing to degrade.
  const dis = hrObs({ kind: "dismiss_conflict" }, "2026-05-03T00:00:00Z");
  const r2 = track(
    "S6a-dismiss",
    runs("S6a tz + dismiss", () => reconcile([...tzChain(), dis], NOW)),
  );
  if (r2) {
    assert(
      "S6a dismiss over non-conflicting: machine HIGH stands + human_resolved (no degrade path)",
      r2.window.confidence === "high" &&
        r2.window.conflict_flags.includes("human_resolved"),
      `${r2.window.confidence}`,
    );
    parses("S6a dismiss", r2.window);
  }
}

// S6b: rolled-over source date (2026-02-30) degrades to UNKNOWN; a VALID pin fixes it at HIGH; a
// ROLLED pin (2026-02-30) must be REJECTED by the verdict schema — never a fabricated Mar-2 close.
{
  const rolledChain = () => [
    regsObs(
      {
        commentEndDate: "2026-02-30T04:59:59Z", // rolls to Mar 2 if parsed naively
        withdrawn: false,
        openForComment: true,
      },
      "2026-05-01T00:00:00Z",
    ),
  ];
  const base = track(
    "S6b-base",
    runs("S6b rolled source baseline", () => reconcile(rolledChain(), NOW)),
  );
  if (base) {
    assert(
      "S6b baseline: rolled-over commentEndDate treated ABSENT — UNKNOWN + null close (no Mar-2 fabrication)",
      base.window.confidence === "unknown" &&
        base.window.resolved_close_utc === null,
      `${base.window.confidence} ${base.window.resolved_close_utc}`,
    );
  }
  const goodPin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-03-02" },
    "2026-05-02T00:00:00Z",
  );
  const r = track(
    "S6b-goodpin",
    runs("S6b valid pin over rolled chain", () =>
      reconcile([...rolledChain(), goodPin], NOW),
    ),
  );
  if (r) {
    assert(
      "S6b valid pin: honored at HIGH with the ET-convention instant; past close ⇒ status closed",
      r.window.confidence === "high" &&
        r.window.resolved_close_utc === frCloseDateToUtcInstant("2026-03-02") &&
        r.window.status === "closed",
      `${r.window.confidence} ${r.window.resolved_close_utc} ${r.window.status}`,
    );
    parses("S6b valid pin", r.window);
  }
  const rolledPin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-02-30" },
    "2026-05-02T00:00:00Z",
  );
  const r2 = track(
    "S6b-rolledpin",
    runs("S6b ROLLED pin 2026-02-30", () =>
      reconcile([...rolledChain(), rolledPin], NOW),
    ),
  );
  if (r2) {
    assert(
      "S6b ROLLED pin: schema-rejected ⇒ ignored — UNKNOWN + null close, NEVER a rolled Mar-2 close at HIGH",
      r2.window.confidence === "unknown" &&
        r2.window.resolved_close_utc === null &&
        !r2.window.conflict_flags.includes("human_resolved"),
      `${r2.window.confidence} ${r2.window.resolved_close_utc}`,
    );
    parses("S6b ROLLED pin", r2.window);
  }
}

// S6c: EPA 2025-02910 (the multi-docket extension fixture) — an honored verdict must not drop the
// docket linkage the M:N join depends on.
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  const r = track(
    "S6c",
    runs("S6c EPA multi-docket + pin", () =>
      reconcile([...conflictChain(), pin], NOW),
    ),
  );
  if (r) {
    assert(
      "S6c: docket_id union preserved under an honored verdict (EPA-HQ-OW-2024-0454 present)",
      r.window.docket_id.includes("EPA-HQ-OW-2024-0454"),
      r.window.docket_id.join(","),
    );
  }
}

// ═══ S7 — DETERMINISM UNDER ARRAY ORDER (the plan's "same chain in, same window out") ════════════════

// S7a: TWO human verdicts with EQUAL fetched_at, different pins. The chain is the same SET either way;
// reconcileOcdId's `order by fetched_at asc` has NO tiebreak, so both array orders are reachable from
// the SAME DB state. latestBySource strict-`>` keeps the FIRST-encountered on a tie ⇒ order decides
// which verdict is honored.
{
  const T = "2026-05-03T00:00:00Z";
  const a = hrObs({ kind: "pin_close", pinned_close_date: "2026-07-20" }, T);
  const b = hrObs({ kind: "pin_close", pinned_close_date: "2026-07-22" }, T);
  const r1 = reconcile([...conflictChain(), a, b], NOW);
  const r2 = reconcile([...conflictChain(), b, a], NOW);
  assert(
    "S7a DETERMINISM: equal-fetched_at verdict pair — window identical under array-order shuffle",
    r1.window.resolved_close_utc === r2.window.resolved_close_utc &&
      JSON.stringify(r1.window.conflict_flags) ===
        JSON.stringify(r2.window.conflict_flags) &&
      r1.window.confidence === r2.window.confidence,
    `order[a,b] close=${r1.window.resolved_close_utc} vs order[b,a] close=${r2.window.resolved_close_utc}`,
  );
}

// S7b: the SAME class on a machine source (pre-existing in v1, sharpened by v2): two regs observations
// with equal fetched_at, one agreeing (Eastern 07-15) and one conflicting (Eastern 07-20) — array order
// flips the window between HIGH and CONFLICTING from the same DB state.
{
  const T = "2026-05-02T00:00:00Z";
  const fr = () =>
    frObs({ comments_close_on: "2026-07-15" }, "2026-05-01T00:00:00Z");
  const agree = regsObs(
    {
      commentEndDate: "2026-07-16T03:59:59Z", // Eastern 2026-07-15 — agrees with FR
      withdrawn: false,
      openForComment: true,
    },
    T,
  );
  const clash = regsObs(
    {
      commentEndDate: "2026-07-21T03:59:59Z", // Eastern 2026-07-20 — conflicts
      withdrawn: false,
      openForComment: true,
    },
    T,
  );
  const r1 = reconcile([fr(), agree, clash], NOW);
  const r2 = reconcile([fr(), clash, agree], NOW);
  assert(
    "S7b DETERMINISM (pre-existing class): equal-fetched_at regs pair — confidence identical under shuffle",
    r1.window.confidence === r2.window.confidence,
    `order[agree,clash]=${r1.window.confidence} vs order[clash,agree]=${r2.window.confidence}`,
  );
}

// ═══ GLOBAL DUAL-FIRE INVARIANTS over every window produced above ════════════════════════════════════
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
      r.window.confidence === "conflicting" &&
      r.window.conflict_flags.includes("tz_normalization_only")
    )
      assert(
        `GLOBAL: ${label} — tz_normalization_only paired with CONFLICTING (the FR-2018-27875 regression)`,
        false,
      );
  }
  assert(
    `GLOBAL: dual-fire invariants held across all ${produced.length} produced results`,
    true,
  );
}

console.log("\n=== reconcile-human-review-ADVERSARY results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL PROBES HELD" : `${failures} PROBE(S) BROKE THROUGH`}`,
);
process.exit(failures === 0 ? 0 : 1);
