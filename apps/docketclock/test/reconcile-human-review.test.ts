/**
 * reconcile-human-review.test.ts — the reconcile-v2 honor-the-verdict rule (Slice R, PR-R2;
 * plans/review-resolve.md "Decisions locked" → supersedence).
 *
 * Proves the plan's regression matrix, pure-engine (no DB):
 *   • HONORED PIN — over a CONFLICTING date mismatch: pinned close via the 11:59pm ET convention,
 *     confidence HIGH, machine flags CARRIED + human_resolved, NO ConflictRecord (persist retires).
 *   • UN-PINNED BY A NEWER SOURCE OBSERVATION — agreeing AND disagreeing variants: the verdict is
 *     ignored the moment source data is strictly newer; the disagreeing variant RESURFACES the
 *     conflict (dual-fire preserved — a stale human verdict can never keep an alarm silent).
 *   • SECOND VERDICT SUPERSEDES THE FIRST — latest human_review wins.
 *   • PER-KIND — confirm_withdrawn (the #112 shape), confirm_reopened, dismiss_conflict (LOW, not
 *     a winner-picker), each contract-parsed.
 *   • TIE — a verdict with fetched_at EQUAL to the newest source observation is honored.
 *   • MALFORMED RAW IGNORED — defense-in-depth: garbage raw degrades to pure derivation, never throws.
 *   • DETERMINISM — same chain in, same window out (deep equality across runs).
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ParticipationWindow, type Observation } from "@yokel/contracts";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { reconcile } from "../src/reconcile/reconcile.js";
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
/** A human_review Observation per the PR-R1 row conventions (flags false, ids/dates_text null). */
function hrObs(
  raw: Record<string, unknown>,
  fetchedAt: string,
  note = "reviewed",
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
      operator: "lucas",
      note,
      reviewed_payload_hashes: ["a".repeat(64)],
      ...raw,
    },
  } as Observation;
}

// The recurring machine-CONFLICTING chain: FR says July 15, Regs says July 20 (Eastern) — a true
// fr_regs_date_mismatch.
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

// ── HONORED PIN over CONFLICTING ──────────────────────────────────────────────────────────────────────
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  const { window, conflict } = reconcile([...conflictChain(), pin], NOW);
  assert(
    "HONORED PIN: confidence high",
    window.confidence === "high",
    window.confidence,
  );
  assert(
    "HONORED PIN: pinned close via the 11:59pm ET convention",
    window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-20"),
    String(window.resolved_close_utc),
  );
  assert(
    "HONORED PIN: display carries the pinned date + provenance",
    window.resolved_close_display ===
      "closes 2026-07-20 at 11:59 p.m. ET (pinned by human review)",
    String(window.resolved_close_display),
  );
  assert(
    "HONORED PIN: machine flags carried + human_resolved appended",
    window.conflict_flags.includes("fr_regs_date_mismatch") &&
      window.conflict_flags.includes("human_resolved"),
    window.conflict_flags.join(","),
  );
  assert("HONORED PIN: NO ConflictRecord while honored", conflict === null);
  assert(
    "HONORED PIN: verdict observation joins current_observation_ids",
    window.current_observation_ids.includes(pin.observation_id),
    window.current_observation_ids.join(","),
  );
  assert(
    "HONORED PIN: status derives from the pinned close (future ⇒ open)",
    window.status === "open",
    window.status,
  );
  parses("HONORED PIN", window);
}

// ── UN-PINNED by a newer source observation — AGREEING variant ────────────────────────────────────────
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  // A NEWER FR correction agreeing with the pin (and with Regs): machine derivation is clean again.
  const newerFr = frObs(
    { comments_close_on: "2026-07-20" },
    "2026-05-04T00:00:00Z",
  );
  const { window, conflict } = reconcile(
    [...conflictChain(), pin, newerFr],
    NOW,
  );
  assert(
    "UN-PIN (agreeing): pure derivation resumes — HIGH from source agreement, not the pin",
    window.confidence === "high" &&
      !window.conflict_flags.includes("human_resolved"),
    `${window.confidence} [${window.conflict_flags.join(",")}]`,
  );
  assert(
    "UN-PIN (agreeing): display is the machine's, not the pin's",
    window.resolved_close_display === "closes 2026-07-20 (per Regulations.gov)",
    String(window.resolved_close_display),
  );
  assert("UN-PIN (agreeing): no conflict", conflict === null);
  parses("UN-PIN (agreeing)", window);
}

// ── UN-PINNED by a newer source observation — DISAGREEING variant: the conflict RESURFACES ────────────
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
  );
  // A NEWER Regs value moving the close again: the verdict is stale; machine disagreement is live.
  const newerRegs = regsObs(
    {
      commentEndDate: "2026-08-11T03:59:59Z",
      withdrawn: false,
      openForComment: true,
    },
    "2026-05-05T00:00:00Z",
  );
  const { window, conflict } = reconcile(
    [...conflictChain(), pin, newerRegs],
    NOW,
  );
  assert(
    "RESURFACE: stale verdict ignored — CONFLICTING again",
    window.confidence === "conflicting" &&
      !window.conflict_flags.includes("human_resolved"),
    `${window.confidence} [${window.conflict_flags.join(",")}]`,
  );
  assert(
    "RESURFACE: ConflictRecord emitted (dual-fire preserved — a stale human verdict never silences)",
    conflict !== null &&
      conflict.conflict_flags.includes("fr_regs_date_mismatch"),
    conflict === null ? "null" : conflict.conflict_flags.join(","),
  );
  parses("RESURFACE", window);
}

// ── SECOND VERDICT SUPERSEDES THE FIRST ───────────────────────────────────────────────────────────────
{
  const pin1 = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
    "first look",
  );
  const pin2 = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-22" },
    "2026-05-04T00:00:00Z",
    "second look — corrected",
  );
  const { window } = reconcile([...conflictChain(), pin1, pin2], NOW);
  assert(
    "SUPERSEDE: the later verdict's pin wins",
    window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-22"),
    String(window.resolved_close_utc),
  );
  assert(
    "SUPERSEDE: only the later verdict joins current_observation_ids",
    window.current_observation_ids.includes(pin2.observation_id) &&
      !window.current_observation_ids.includes(pin1.observation_id),
    window.current_observation_ids.join(","),
  );
  parses("SUPERSEDE", window);
}

// ── PER-KIND: confirm_withdrawn (the #112 shape — FR-only window, machine can't see the withdrawal) ──
{
  const fr = frObs({ comments_close_on: "2026-07-15" }, "2026-05-01T00:00:00Z");
  const verdict = hrObs(
    { kind: "confirm_withdrawn" },
    "2026-05-06T00:00:00Z",
    "regs.gov shows withdrawn=true; withdrawal observation landed on the shadow window (#112)",
  );
  const { window, conflict } = reconcile([fr, verdict], NOW);
  assert(
    "CONFIRM_WITHDRAWN: status withdrawn",
    window.status === "withdrawn",
    window.status,
  );
  assert(
    "CONFIRM_WITHDRAWN: LOW with the historical close kept (never push-eligible)",
    window.confidence === "low" &&
      window.resolved_close_utc === frCloseDateToUtcInstant("2026-07-15"),
    `${window.confidence} ${window.resolved_close_utc}`,
  );
  assert(
    "CONFIRM_WITHDRAWN: human_resolved present, no conflict",
    window.conflict_flags.includes("human_resolved") && conflict === null,
    window.conflict_flags.join(","),
  );
  parses("CONFIRM_WITHDRAWN", window);
}

// ── PER-KIND: confirm_reopened over a CONFLICTING chain ──────────────────────────────────────────────
{
  const verdict = hrObs(
    { kind: "confirm_reopened" },
    "2026-05-06T00:00:00Z",
    "agency reopened the docket; sources still disagree on the old close",
  );
  const { window, conflict } = reconcile([...conflictChain(), verdict], NOW);
  assert(
    "CONFIRM_REOPENED: status open",
    window.status === "open",
    window.status,
  );
  assert(
    "CONFIRM_REOPENED: conflicting degrades to LOW w/ carried close (never stays conflicting while honored)",
    window.confidence === "low" && window.resolved_close_utc !== null,
    `${window.confidence} ${window.resolved_close_utc}`,
  );
  assert("CONFIRM_REOPENED: no live ConflictRecord", conflict === null);
  parses("CONFIRM_REOPENED", window);
}

// ── PER-KIND: dismiss_conflict — removes the alarm, never picks a winner ──────────────────────────────
{
  const verdict = hrObs(
    { kind: "dismiss_conflict" },
    "2026-05-06T00:00:00Z",
    "known duplicate-docket artifact; not a real disagreement",
  );
  const { window, conflict } = reconcile([...conflictChain(), verdict], NOW);
  assert(
    "DISMISS: LOW with the machine's carried close (not medium/high — dismissal adds no corroboration)",
    window.confidence === "low" && window.resolved_close_utc !== null,
    `${window.confidence} ${window.resolved_close_utc}`,
  );
  assert(
    "DISMISS: machine flags carried + human_resolved; no live record",
    window.conflict_flags.includes("fr_regs_date_mismatch") &&
      window.conflict_flags.includes("human_resolved") &&
      conflict === null,
    window.conflict_flags.join(","),
  );
  parses("DISMISS", window);
}

// ── TIE: verdict fetched_at EQUAL to the newest source observation is honored ─────────────────────────
{
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-02T00:00:00Z", // exactly the regs observation's fetched_at
  );
  const { window } = reconcile([...conflictChain(), pin], NOW);
  assert(
    "TIE: equal fetched_at honors the human",
    window.conflict_flags.includes("human_resolved") &&
      window.confidence === "high",
    `${window.confidence} [${window.conflict_flags.join(",")}]`,
  );
  parses("TIE", window);
}

// ── MALFORMED RAW: ignored, pure derivation, never throws ─────────────────────────────────────────────
{
  const bad = hrObs({ kind: "pin_close" }, "2026-05-06T00:00:00Z"); // pin without a date — fails the schema
  const { window, conflict } = reconcile([...conflictChain(), bad], NOW);
  assert(
    "MALFORMED: unparseable verdict ignored — machine CONFLICTING stands, record emitted",
    window.confidence === "conflicting" &&
      !window.conflict_flags.includes("human_resolved") &&
      conflict !== null,
    `${window.confidence}`,
  );
  parses("MALFORMED", window);
}

// ── DETERMINISM: same chain in, same window out ───────────────────────────────────────────────────────
{
  const chain = [
    ...conflictChain(),
    hrObs(
      { kind: "pin_close", pinned_close_date: "2026-07-20" },
      "2026-05-03T00:00:00Z",
    ),
  ];
  const a = reconcile(chain, NOW);
  const b = reconcile(chain, NOW);
  assert(
    "DETERMINISM: two runs over the same chain are deep-equal",
    JSON.stringify(a.window) === JSON.stringify(b.window) &&
      JSON.stringify(a.conflict) === JSON.stringify(b.conflict),
  );
}

console.log("\n=== reconcile-human-review results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
