/**
 * review-escalate.test.ts — the review core's PR-A2 surface (ADR 0015) against a throwaway Postgres:
 * evidence-bound writes (`expect`), the `escalate` kind end to end (parked, visible, counted,
 * un-parked), `show --blind`, and reviewer provenance through the real write → reconcile path.
 *
 *   • EXPECT: a stale set, a subset, and an empty set each REFUSE and write nothing; the exact live
 *     set writes.
 *   • ESCALATE (agent): the window derives exactly the machine's state (conflicting, machine flags
 *     only, live conflict stays), yet `queue` marks it, stats count it, `show` reports it honored +
 *     parked, and an identical retry dedupes while still reading as parked.
 *   • BLIND: no verdicts, no honored line, the machine's own derivation, retired count hidden.
 *   • UN-PARK: a newer, still-disagreeing FR observation drops the mark (still in the queue), the
 *     stats escalated count goes to 0, `show` reports the verdict superseded.
 *   • AGENT PIN with `expect`: HIGH + agent_resolved (never human_resolved), display attributed to
 *     agent review; the queue empties; a later human pin supersedes it with human_resolved.
 *   • REVIEW ROUND 1 FIXES: an escalate that would park nothing (a non-queue window) is REFUSED;
 *     superseding an honored agent pin with an escalate (the audit's disagreement) is accepted and
 *     parks; blind hides chain links; honoredIsThisWrite keys a deduped write on its payload hash.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import {
  honoredIsThisWrite,
  resolveWindow,
  reviewQueue,
  reviewQueueStats,
  reviewShow,
} from "../src/review/core.js";
import type { HonoredVerdict } from "../src/reconcile/reconcile.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}
async function rejects(name: string, op: () => unknown, re: RegExp) {
  try {
    await op();
    assert(name, false, "did not throw");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    assert(name, re.test(msg), msg);
  }
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

const OCD = "ocd-participation-window/federal/2025-02910";
const OCD_CLEAN = "ocd-participation-window/federal/2025-55555";
const T0 = new Date("2026-09-02T00:00:00Z");

// ── honoredIsThisWrite (pure) — the dedupe-path identity rule from review round 1 ───────────────────
{
  const h = (observation_id: string, payload_hash: string) =>
    ({ observation: { observation_id, payload_hash } }) as HonoredVerdict;
  assert(
    "honoredIsThisWrite: inserted write matches by observation id",
    honoredIsThisWrite(h("o1", "h1"), {
      observationId: "o1",
      payloadHash: "h1",
    }) &&
      !honoredIsThisWrite(h("o2", "h1"), {
        observationId: "o1",
        payloadHash: "h1",
      }),
  );
  assert(
    "honoredIsThisWrite: deduped write matches by payload hash only — a concurrent superseding verdict (different hash) is NOT this write",
    honoredIsThisWrite(h("o9", "h1"), {
      observationId: null,
      payloadHash: "h1",
    }) &&
      !honoredIsThisWrite(h("o9", "h2"), {
        observationId: null,
        payloadHash: "h1",
      }),
  );
  assert(
    "honoredIsThisWrite: nothing honored → false",
    !honoredIsThisWrite(null, { observationId: null, payloadHash: "h1" }),
  );
}

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // A CONFLICTING window: FR says 09-15, Regs says 09-20 Eastern.
  await ingestObservation(sql, {
    ...parseFrObservation({ ...frFixture, comments_close_on: "2026-09-15" }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  const regsRaw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  Object.assign(regsRaw.data.attributes, {
    frDocNum: "2025-02910",
    commentEndDate: "2026-09-21T03:59:59Z",
    withdrawn: false,
    openForComment: true,
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRaw),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD, T0);

  // A clean HIGH window (sources agree) — never a queue member.
  await ingestObservation(sql, {
    ...parseFrObservation({
      ...frFixture,
      document_number: "2025-55555",
      comments_close_on: "2026-10-01",
    }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  const regsRawClean = JSON.parse(
    JSON.stringify(regsFixture),
  ) as typeof regsFixture;
  Object.assign(regsRawClean.data.attributes, {
    frDocNum: "2025-55555",
    commentEndDate: "2026-10-02T03:59:59Z", // Eastern 2026-10-01 — agrees
    withdrawn: false,
    openForComment: true,
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRawClean),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD_CLEAN, T0);

  const machine = await reviewShow(sql, OCD);
  const liveHashes = machine.sources.map((s) => s.payload_hash);
  assert(
    "SETUP: conflicting window with two live source hashes",
    machine.window?.confidence === "conflicting" && liveHashes.length === 2,
  );

  const humanRows = async () =>
    Number(
      (
        await sql<{ n: string }[]>`
          select count(*) as n from observations where source = 'human_review'
        `
      )[0]!.n,
    );

  // ── EXPECT: refusals write nothing ─────────────────────────────────────────────────────────────────
  await rejects(
    "EXPECT: a stale/foreign hash set REFUSES with a diff",
    () =>
      resolveWindow(sql, {
        ocdId: OCD,
        kind: "escalate",
        note: "n",
        operator: "autopilot",
        reviewer: "agent",
        expect: ["d".repeat(64), liveHashes[0]!],
      }),
    /--expect mismatch.*assessed but no longer latest: \[dddddddddddd\].*latest but not assessed: \[(federal_register|regulations_gov):/s,
  );
  await rejects(
    "EXPECT: a SUBSET of the live set REFUSES (every latest-per-source hash must have been assessed)",
    () =>
      resolveWindow(sql, {
        ocdId: OCD,
        kind: "escalate",
        note: "n",
        operator: "autopilot",
        reviewer: "agent",
        expect: [liveHashes[0]!],
      }),
    /--expect mismatch/,
  );
  await rejects(
    "EXPECT: an EMPTY set REFUSES (binding to nothing is not binding)",
    () =>
      resolveWindow(sql, {
        ocdId: OCD,
        kind: "escalate",
        note: "n",
        operator: "autopilot",
        reviewer: "agent",
        expect: [],
      }),
    /--expect mismatch/,
  );
  assert(
    "EXPECT: zero human_review rows written by any refusal",
    (await humanRows()) === 0,
  );

  // ── ESCALATE on a NON-queue window is refused (review round 1, P3: an unseen parking is silence) ──
  await rejects(
    "ESCALATE on a clean HIGH window REFUSES — it would park nothing (unmarked, uncounted, unpaged)",
    () =>
      resolveWindow(sql, {
        ocdId: OCD_CLEAN,
        kind: "escalate",
        note: "n",
        operator: "autopilot",
        reviewer: "agent",
      }),
    /escalate parks nothing here — .*derives high/,
  );
  assert(
    "ESCALATE on a non-queue window: nothing written, window untouched",
    (await humanRows()) === 0 &&
      (await reviewShow(sql, OCD_CLEAN)).window?.confidence === "high",
  );

  // ── ESCALATE by the agent with the exact live set ───────────────────────────────────────────────────
  const T1 = new Date("2026-09-02T01:00:00Z");
  const esc = await resolveWindow(
    sql,
    {
      ocdId: OCD,
      kind: "escalate",
      note: "FR notice, GovInfo, Regs document + docket list, extension search: no document explains the difference.",
      operator: "autopilot",
      reviewer: "agent",
      expect: [...liveHashes].reverse(), // order-insensitive
    },
    T1,
  );
  assert(
    "ESCALATE: written, bound to the two live hashes, honored (parked)",
    esc.inserted &&
      esc.observationId !== null &&
      esc.reviewedHashes.length === 2 &&
      esc.honored,
    JSON.stringify({ inserted: esc.inserted, honored: esc.honored }),
  );
  const w1 = esc.result.window;
  assert(
    "ESCALATE: the window is exactly the machine's — conflicting, machine flags only, verdict absent from current ids",
    w1.confidence === "conflicting" &&
      w1.conflict_flags.join(",") === "fr_regs_date_mismatch" &&
      !w1.current_observation_ids.includes(esc.observationId!),
    `${w1.confidence} [${w1.conflict_flags.join(",")}]`,
  );
  const s1 = await reviewShow(sql, OCD);
  assert(
    "ESCALATE: show — honored + parked, reviewer agent, live conflict still 1, retired 0",
    s1.honored?.kind === "escalate" &&
      s1.honored.parked &&
      s1.honored.reviewer === "agent" &&
      s1.honored.observation_id === esc.observationId &&
      s1.liveConflicts === 1 &&
      s1.retiredConflicts === 0 &&
      s1.priorVerdicts.length === 1 &&
      !("unparseable" in s1.priorVerdicts[0]!.verdict) &&
      s1.priorVerdicts[0]!.verdict.reviewer === "agent",
    JSON.stringify({ honored: s1.honored, live: s1.liveConflicts }),
  );
  const q1 = await reviewQueue(sql);
  assert(
    "ESCALATE: queue still lists the window, MARKED escalated by autopilot (agent)",
    q1.length === 1 &&
      q1[0]!.ocd_id === OCD &&
      q1[0]!.escalated?.operator === "autopilot" &&
      q1[0]!.escalated.reviewer === "agent" &&
      q1[0]!.escalated.observation_id === esc.observationId,
    JSON.stringify(q1.map((r) => [r.ocd_id, r.escalated?.operator])),
  );
  const st1 = await reviewQueueStats(sql, new Date("2026-09-03T00:00:00Z"));
  assert(
    "ESCALATE: stats — conflicting 1, stale 0, escalated 1 (the parked subset), rot age still anchored on first detection",
    st1.byReason.conflicting === 1 &&
      st1.byReason.stale === 0 &&
      st1.byReason.escalated === 1 &&
      st1.oldestAgeSeconds !== null &&
      Math.abs(st1.oldestAgeSeconds - 86400) < 60,
    JSON.stringify(st1),
  );

  // Identical retry dedupes and still reads as parked.
  const again = await resolveWindow(
    sql,
    {
      ocdId: OCD,
      kind: "escalate",
      note: "FR notice, GovInfo, Regs document + docket list, extension search: no document explains the difference.",
      operator: "autopilot",
      reviewer: "agent",
      expect: liveHashes,
    },
    T1,
  );
  assert(
    "ESCALATE retry: deduped (not inserted), still honored, one human_review row",
    !again.inserted &&
      again.observationId === null &&
      again.honored &&
      (await humanRows()) === 1,
  );

  // ── BLIND ───────────────────────────────────────────────────────────────────────────────────────────
  const blind = await reviewShow(sql, OCD, { blind: true, now: T1 });
  assert(
    "BLIND: verdicts hidden, no honored line, machine derivation, retired + chain links hidden, sources intact",
    blind.blind &&
      blind.priorVerdicts.length === 0 &&
      blind.honored === null &&
      blind.window?.confidence === "conflicting" &&
      blind.liveConflicts === 1 &&
      blind.retiredConflicts === 0 &&
      blind.chainLinks.length === 0 &&
      blind.sources.length === 2,
    JSON.stringify({ conf: blind.window?.confidence, pv: blind.priorVerdicts }),
  );

  // ── UN-PARK: a newer, still-disagreeing FR observation ──────────────────────────────────────────────
  await ingestObservation(sql, {
    ...parseFrObservation({ ...frFixture, comments_close_on: "2026-09-16" }),
    fetched_at: "2026-09-03T00:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD, new Date("2026-09-03T01:00:00Z"));
  const q2 = await reviewQueue(sql);
  assert(
    "UN-PARK: still in the queue, mark gone",
    q2.length === 1 && q2[0]!.ocd_id === OCD && q2[0]!.escalated === null,
    JSON.stringify(q2.map((r) => [r.ocd_id, r.escalated])),
  );
  const st2 = await reviewQueueStats(sql, new Date("2026-09-03T02:00:00Z"));
  assert(
    "UN-PARK: stats escalated 0, conflicting still 1",
    st2.byReason.escalated === 0 && st2.byReason.conflicting === 1,
    JSON.stringify(st2.byReason),
  );
  const s2 = await reviewShow(sql, OCD);
  assert(
    "UN-PARK: show — verdict listed but NOT honored (superseded by evidence)",
    s2.honored === null && s2.priorVerdicts.length === 1,
  );

  // ── AGENT PIN bound to the NEW live set ─────────────────────────────────────────────────────────────
  const live2 = s2.sources.map((s) => s.payload_hash);
  await rejects(
    "AGENT PIN: the OLD evidence set now REFUSES (the FR hash moved)",
    () =>
      resolveWindow(sql, {
        ocdId: OCD,
        kind: "pin_close",
        close: "2026-09-20",
        note: "n",
        operator: "autopilot",
        reviewer: "agent",
        expect: liveHashes,
      }),
    /--expect mismatch.*latest but not assessed: \[federal_register:/s,
  );
  const T3 = new Date("2026-09-03T03:00:00Z");
  const pin = await resolveWindow(
    sql,
    {
      ocdId: OCD,
      kind: "pin_close",
      close: "2026-09-20",
      note: "Regs document text states the deadline; FR DATES carries a superseded date (extension notice cited).",
      operator: "autopilot",
      reviewer: "agent",
      expect: live2,
    },
    T3,
  );
  const w3 = pin.result.window;
  assert(
    "AGENT PIN: HIGH, pinned close, agent_resolved and NOT human_resolved, honored",
    pin.inserted &&
      pin.honored &&
      w3.confidence === "high" &&
      w3.resolved_close_display ===
        "closes 2026-09-20 at 11:59 p.m. ET (pinned by agent review)" &&
      w3.conflict_flags.includes("agent_resolved") &&
      !w3.conflict_flags.includes("human_resolved"),
    `${w3.confidence} [${w3.conflict_flags.join(",")}]`,
  );
  {
    const qa = await reviewQueue(sql);
    const sa = await reviewShow(sql, OCD);
    const sta = await reviewQueueStats(sql, new Date("2026-09-04T00:00:00Z"));
    // Two retired pairs: the original (FR 09-15 vs Regs) was superseded by the newer FR's pair (FR
    // 09-16 vs Regs) at un-park time, and the pin retired that one.
    assert(
      "AGENT PIN: queue empties, both conflict pairs retired, stats all zero with null rot age",
      qa.length === 0 &&
        sa.liveConflicts === 0 &&
        sa.retiredConflicts === 2 &&
        JSON.stringify(sta.byReason) ===
          JSON.stringify({ conflicting: 0, stale: 0, escalated: 0 }) &&
        sta.oldestAgeSeconds === null,
      JSON.stringify({
        q: qa.length,
        live: sa.liveConflicts,
        retired: sa.retiredConflicts,
        stats: sta,
      }),
    );
  }
  const [stored] = await sql<{ conflict_flags: string[] }[]>`
    select conflict_flags from participation_windows where ocd_id = ${OCD}
  `;
  assert(
    "AGENT PIN: the PERSISTED projection carries agent_resolved (JSONB round trip)",
    Array.isArray(stored?.conflict_flags) &&
      stored!.conflict_flags.includes("agent_resolved"),
    JSON.stringify(stored?.conflict_flags),
  );
  const blind2 = await reviewShow(sql, OCD, { blind: true, now: T3 });
  assert(
    "BLIND on a pinned window: the machine's view (conflicting), no verdicts, no chain links",
    blind2.window?.confidence === "conflicting" &&
      blind2.priorVerdicts.length === 0 &&
      blind2.honored === null &&
      blind2.chainLinks.length === 0,
  );

  // ── The audit's disagreement: a human escalate SUPERSEDING the honored agent pin is accepted ──────
  // Pre-write the window is HIGH (not a queue member); with the escalate as latest it returns to the
  // machine's conflicting derivation, so the escalate parks something and passes the refusal check.
  const audit = await resolveWindow(
    sql,
    {
      ocdId: OCD,
      kind: "escalate",
      note: "Weekly audit: re-read the live notice; the agent's cited extension names a different docket. Needs a human decision.",
      operator: "lucas",
      expect: live2,
    },
    new Date("2026-09-03T03:30:00Z"),
  );
  const wa = audit.result.window;
  assert(
    "AUDIT ESCALATE over an honored agent pin: accepted, parked, window back to the machine's conflicting derivation with NO provenance flag",
    audit.inserted &&
      audit.honored &&
      wa.confidence === "conflicting" &&
      !wa.conflict_flags.includes("agent_resolved") &&
      !wa.conflict_flags.includes("human_resolved"),
    `${wa.confidence} [${wa.conflict_flags.join(",")}]`,
  );
  assert(
    "AUDIT ESCALATE: queue marks it (reviewer human), stats escalated 1",
    (await reviewQueue(sql)).some(
      (r) => r.ocd_id === OCD && r.escalated?.reviewer === "human",
    ) &&
      (await reviewQueueStats(sql, new Date("2026-09-04T00:00:00Z"))).byReason
        .escalated === 1,
  );

  // ── A later HUMAN pin supersedes with human_resolved (no expect: the pre-A2 path still works) ──────
  const human = await resolveWindow(
    sql,
    {
      ocdId: OCD,
      kind: "pin_close",
      close: "2026-09-20",
      note: "Confirmed the agent's reading against the live notice.",
      operator: "lucas",
    },
    new Date("2026-09-03T04:00:00Z"),
  );
  const w4 = human.result.window;
  assert(
    "HUMAN PIN supersedes: human_resolved, NOT agent_resolved; reviewer defaulted to human",
    human.inserted &&
      human.honored &&
      w4.conflict_flags.includes("human_resolved") &&
      !w4.conflict_flags.includes("agent_resolved") &&
      (await reviewShow(sql, OCD)).honored?.reviewer === "human",
    `[${w4.conflict_flags.join(",")}]`,
  );
  assert(
    "HUMAN PIN: the written raw carries reviewer=human explicitly",
    (
      await sql<{ reviewer: string | null }[]>`
        select raw->>'reviewer' as reviewer from observations
        where ocd_id = ${OCD} and source = 'human_review'
        order by fetched_at desc limit 1
      `
    )[0]!.reviewer === "human",
  );
} finally {
  await sql.end();
}

console.log("\n=== review-escalate results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
