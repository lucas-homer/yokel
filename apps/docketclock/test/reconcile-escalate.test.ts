/**
 * reconcile-escalate.test.ts — reconcile-v2.3 (ADR 0015; review autopilot PR-A2): the `escalate`
 * verdict kind and reviewer-aware provenance, pure-engine (no DB).
 *
 * Proves the plan's verify list:
 *   • ESCALATE DERIVES NOTHING — window AND ConflictRecord are byte-for-byte what the machine derives
 *     without the verdict: no human_resolved / agent_resolved, the verdict never joins
 *     current_observation_ids, the conflict stays live (suppression is never silence).
 *   • PARKED = honored for freshness: selectHonoredVerdict returns the escalate while nothing newer
 *     than it changes the evidence; a metadata-only Regs refresh (ADR 0010) keeps it parked.
 *   • UN-PARKED by invalidating evidence: a newer FR observation, a substantive Regs change, and —
 *     deliberately, because the ADR 0014 echo exception is pin_close-only — the portal's own close
 *     flip after the deadline.
 *   • PROVENANCE follows `reviewer`: an agent pin stamps agent_resolved (never human_resolved); a
 *     legacy pin with no reviewer field and an explicit reviewer=human stamp human_resolved; the
 *     rule applies to every non-escalate kind (agent dismiss_conflict → LOW + agent_resolved).
 *   • SUPERSEDENCE is unchanged: a later escalate un-pins (conflict resurfaces); a later pin un-parks.
 *   • DETERMINISM + contract validity for every produced window.
 */
import { isDeepStrictEqual } from "node:util";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ParticipationWindow, type Observation } from "@yokel/contracts";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { reconcile, selectHonoredVerdict } from "../src/reconcile/reconcile.js";
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
  topLevel: Record<string, unknown> = {},
): Observation {
  const raw = {
    ...(JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture),
    ...topLevel,
  };
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
/** A human_review Observation per the PR-R1 row conventions, reviewing the given chain's hashes. */
function hrObs(
  raw: Record<string, unknown>,
  fetchedAt: string,
  reviewed: Observation[],
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
      operator: "autopilot",
      note: "FR notice, GovInfo edition, Regs document + docket list, extension/correction search by docket, RIN and title: no document explains the 5-day difference.",
      reviewed_payload_hashes: reviewed.map((o) => o.payload_hash),
      ...raw,
    },
  } as Observation;
}

// The recurring machine-CONFLICTING chain: FR says July 15, Regs says July 20 (Eastern).
const REGS_ATTRS = {
  commentEndDate: "2026-07-21T03:59:59Z",
  withdrawn: false,
  openForComment: true,
  withinCommentPeriod: true,
};
const conflictChain = () => [
  frObs({ comments_close_on: "2026-07-15" }, "2026-05-01T00:00:00Z"),
  regsObs(REGS_ATTRS, "2026-05-02T00:00:00Z"),
];

// ── ESCALATE DERIVES NOTHING (human and agent) ───────────────────────────────────────────────────────
for (const reviewer of ["human", "agent"] as const) {
  const chain = conflictChain();
  const esc = hrObs(
    { kind: "escalate", reviewer },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const base = reconcile(chain, NOW);
  const withEsc = reconcile([...chain, esc], NOW);
  assert(
    `ESCALATE (${reviewer}): window byte-for-byte equals the machine's own derivation`,
    isDeepStrictEqual(base.window, withEsc.window),
    JSON.stringify(withEsc.window.conflict_flags),
  );
  assert(
    `ESCALATE (${reviewer}): ConflictRecord still emitted and identical (the conflict stays live)`,
    withEsc.conflict !== null &&
      isDeepStrictEqual(base.conflict, withEsc.conflict),
  );
  assert(
    `ESCALATE (${reviewer}): confidence stays conflicting, NO provenance flag`,
    withEsc.window.confidence === "conflicting" &&
      !withEsc.window.conflict_flags.includes("human_resolved") &&
      !withEsc.window.conflict_flags.includes("agent_resolved"),
    `${withEsc.window.confidence} [${withEsc.window.conflict_flags.join(",")}]`,
  );
  assert(
    `ESCALATE (${reviewer}): the verdict never joins current_observation_ids`,
    !withEsc.window.current_observation_ids.includes(esc.observation_id),
  );
  const honored = selectHonoredVerdict([...chain, esc]);
  assert(
    `ESCALATE (${reviewer}): PARKED — selectHonoredVerdict returns the escalate`,
    honored !== null &&
      honored.verdict.kind === "escalate" &&
      honored.verdict.reviewer === reviewer &&
      honored.observation.observation_id === esc.observation_id,
    JSON.stringify(honored?.verdict),
  );
  parses(`ESCALATE (${reviewer})`, withEsc.window);
}

// ── STAYS PARKED through a metadata-only Regs refresh (ADR 0010) ─────────────────────────────────────
{
  const chain = conflictChain();
  const esc = hrObs({ kind: "escalate" }, "2026-05-03T00:00:00Z", chain);
  const refresh = regsObs(
    { ...REGS_ATTRS, modifyDate: "2026-05-04T00:00:00Z" },
    "2026-05-04T00:00:00Z",
    { links: { self: "https://api.regulations.gov/v4/documents/x" } },
  );
  const honored = selectHonoredVerdict([...chain, esc, refresh]);
  assert(
    "PARKED through metadata-only refresh: still honored (v2.1 exception applies to every kind)",
    honored !== null && honored.verdict.kind === "escalate",
  );
  const w = reconcile([...chain, esc, refresh], NOW).window;
  assert(
    "PARKED through refresh: derivation still the machine's (conflicting, no flag)",
    w.confidence === "conflicting" &&
      !w.conflict_flags.includes("human_resolved"),
  );
}

// ── UN-PARKED by invalidating evidence ───────────────────────────────────────────────────────────────
{
  const chain = conflictChain();
  const esc = hrObs({ kind: "escalate" }, "2026-05-03T00:00:00Z", chain);
  // (a) a newer FR observation — still disagreeing: the item is un-parked AND still conflicting.
  const newerFr = frObs(
    { comments_close_on: "2026-07-16" },
    "2026-05-05T00:00:00Z",
  );
  const a = selectHonoredVerdict([...chain, esc, newerFr]);
  assert("UN-PARK (newer FR): not honored", a === null);
  const wa = reconcile([...chain, esc, newerFr], NOW).window;
  assert(
    "UN-PARK (newer FR): machine derivation, conflicting, no flag",
    wa.confidence === "conflicting" &&
      !wa.conflict_flags.includes("human_resolved") &&
      !wa.conflict_flags.includes("agent_resolved"),
  );
  // (b) a substantive Regs change (the date moved).
  const movedRegs = regsObs(
    { ...REGS_ATTRS, commentEndDate: "2026-07-23T03:59:59Z" },
    "2026-05-05T00:00:00Z",
  );
  assert(
    "UN-PARK (Regs date moved): not honored",
    selectHonoredVerdict([...chain, esc, movedRegs]) === null,
  );
  // (c) DELIBERATE: the portal's own close flip after the deadline un-parks an escalate. ADR 0014's
  // echo exception is pin_close-only (clause 1) and ADR 0015 does not extend it; a closed, parked
  // item is re-inspected by the autopilot (and may be re-escalated), never silently kept parked.
  const flip = regsObs(
    { ...REGS_ATTRS, openForComment: false, withinCommentPeriod: false },
    "2026-07-22T12:00:00Z",
  );
  assert(
    "UN-PARK (portal close flip after the deadline): escalate gets NO v2.2 echo exception — not honored",
    selectHonoredVerdict([...chain, esc, flip]) === null,
  );
  // Control: the same flip on an equal-date PIN is the echo and keeps the pin (ADR 0014).
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const pinned = selectHonoredVerdict([...chain, pin, flip]);
  assert(
    "control: the same flip keeps an equal-date pin honored (v2.2 echo exception, pin_close only)",
    pinned !== null && pinned.verdict.kind === "pin_close",
  );
  assert(
    "control: flip instant is strictly after the pinned instant (the v2.2 clause 4 premise of this test)",
    new Date(flip.fetched_at).getTime() >
      new Date(frCloseDateToUtcInstant("2026-07-20")).getTime(),
  );
}

// ── PROVENANCE follows `reviewer` ────────────────────────────────────────────────────────────────────
{
  const chain = conflictChain();
  const agentPin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20", reviewer: "agent" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const w = reconcile([...chain, agentPin], NOW).window;
  assert(
    "AGENT PIN: HIGH, pinned close, agent_resolved — and NOT human_resolved",
    w.confidence === "high" &&
      w.resolved_close_utc === frCloseDateToUtcInstant("2026-07-20") &&
      w.conflict_flags.includes("agent_resolved") &&
      !w.conflict_flags.includes("human_resolved") &&
      w.conflict_flags.includes("fr_regs_date_mismatch"),
    `${w.confidence} [${w.conflict_flags.join(",")}]`,
  );
  assert(
    "AGENT PIN: verdict joins current_observation_ids, no ConflictRecord while honored",
    w.current_observation_ids.includes(agentPin.observation_id) &&
      reconcile([...chain, agentPin], NOW).conflict === null,
  );
  assert(
    "AGENT PIN: the consumer-facing display names the deciding authority (review finding: never 'human review' for an agent pin)",
    w.resolved_close_display ===
      "closes 2026-07-20 at 11:59 p.m. ET (pinned by agent review)",
    String(w.resolved_close_display),
  );
  parses("AGENT PIN", w);

  // Legacy row: NO reviewer field at all (every pre-0.11.0 verdict, incl. the 49 codex pins).
  const legacyPin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  delete (legacyPin.raw as Record<string, unknown>).reviewer;
  const wl = reconcile([...chain, legacyPin], NOW).window;
  assert(
    "LEGACY PIN (no reviewer field): human_resolved, never agent_resolved",
    wl.conflict_flags.includes("human_resolved") &&
      !wl.conflict_flags.includes("agent_resolved"),
    wl.conflict_flags.join(","),
  );
  assert(
    "LEGACY PIN: the display keeps its exact pre-0.11.0 wording",
    wl.resolved_close_display ===
      "closes 2026-07-20 at 11:59 p.m. ET (pinned by human review)",
    String(wl.resolved_close_display),
  );
  const explicitHuman = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20", reviewer: "human" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const wh = reconcile([...chain, explicitHuman], NOW).window;
  assert(
    "EXPLICIT reviewer=human: human_resolved",
    wh.conflict_flags.includes("human_resolved") &&
      !wh.conflict_flags.includes("agent_resolved"),
  );
  const sansIds = (w: ParticipationWindow) => ({
    ...w,
    current_observation_ids: [],
    provenance: {
      agreeing_observation_ids: [],
      conflicting_observation_ids: [],
    },
  });
  assert(
    "LEGACY vs EXPLICIT human: identical derivation (the default is the legacy meaning)",
    isDeepStrictEqual(sansIds(wl), sansIds(wh)),
  );

  // The rule applies to every non-escalate kind.
  const agentDismiss = hrObs(
    { kind: "dismiss_conflict", reviewer: "agent" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const wd = reconcile([...chain, agentDismiss], NOW).window;
  assert(
    "AGENT DISMISS: LOW with the carried close + agent_resolved (the overlay semantics are unchanged, only the flag follows reviewer)",
    wd.confidence === "low" &&
      wd.conflict_flags.includes("agent_resolved") &&
      !wd.conflict_flags.includes("human_resolved"),
    `${wd.confidence} [${wd.conflict_flags.join(",")}]`,
  );
  parses("AGENT DISMISS", wd);
}

// ── SUPERSEDENCE unchanged: latest verdict wins ───────────────────────────────────────────────────────
{
  const chain = conflictChain();
  const pin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const laterEsc = hrObs({ kind: "escalate" }, "2026-05-04T00:00:00Z", chain);
  const r1 = reconcile([...chain, pin, laterEsc], NOW);
  assert(
    "ESCALATE AFTER PIN: the pin is superseded — conflict resurfaces, window is the machine's",
    r1.window.confidence === "conflicting" &&
      r1.conflict !== null &&
      !r1.window.conflict_flags.includes("human_resolved"),
    `${r1.window.confidence}`,
  );
  const h1 = selectHonoredVerdict([...chain, pin, laterEsc]);
  assert(
    "ESCALATE AFTER PIN: honored verdict is the escalate (parked)",
    h1 !== null && h1.verdict.kind === "escalate",
  );

  const esc = hrObs({ kind: "escalate" }, "2026-05-03T00:00:00Z", chain);
  const laterPin = hrObs(
    { kind: "pin_close", pinned_close_date: "2026-07-20" },
    "2026-05-04T00:00:00Z",
    chain,
  );
  const r2 = reconcile([...chain, esc, laterPin], NOW);
  assert(
    "PIN AFTER ESCALATE: un-parked and pinned — HIGH + human_resolved",
    r2.window.confidence === "high" &&
      r2.window.conflict_flags.includes("human_resolved") &&
      r2.conflict === null,
    `${r2.window.confidence} [${r2.window.conflict_flags.join(",")}]`,
  );
}

// ── MALFORMED escalate (a date smuggled on) is ignored — pure derivation, no throw ────────────────────
{
  const chain = conflictChain();
  const bad = hrObs(
    { kind: "escalate", pinned_close_date: "2026-07-20" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  let threw = false;
  let w: ParticipationWindow | null = null;
  try {
    w = reconcile([...chain, bad], NOW).window;
  } catch {
    threw = true;
  }
  assert(
    "MALFORMED escalate (with a date): ignored, pure derivation, never throws",
    !threw &&
      w !== null &&
      w.confidence === "conflicting" &&
      selectHonoredVerdict([...chain, bad]) === null,
  );
}

// ── DETERMINISM ──────────────────────────────────────────────────────────────────────────────────────
{
  const chain = conflictChain();
  const esc = hrObs(
    { kind: "escalate", reviewer: "agent" },
    "2026-05-03T00:00:00Z",
    chain,
  );
  const a = reconcile([...chain, esc], NOW);
  const b = reconcile([esc, ...chain].reverse(), NOW);
  assert(
    "DETERMINISM: same chain in any order, same window + conflict out",
    isDeepStrictEqual(a.window, b.window) &&
      isDeepStrictEqual(a.conflict, b.conflict),
  );
}

console.log("\n=== reconcile-escalate results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
