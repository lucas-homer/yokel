/**
 * review-log.test.ts — the review core's PR-A3 surface against a throwaway Postgres: the verdict
 * ledger (`review log`) and the shadow-gate corpus (`review corpus`).
 *
 *   • LOG: newest first; filters are applied in SQL (reviewer — with the contract's `human` default
 *     applied to legacy rows that carry no key —, operator, kind, since, limit); every entry's
 *     STANDING is the engine's honoring rule over the full chain: honored / parked / superseded
 *     (a later verdict exists) / invalidated (latest verdict, but newer evidence) — the last is the
 *     signal the weekly audit reads for agent verdicts.
 *   • CORPUS: every window whose latest verdict is honored NOW, grouped by what a blind proposal must
 *     reproduce; an invalidated verdict is listed as not gated; a window with no verdict is absent.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { createHash } from "node:crypto";
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
  resolveWindow,
  reviewCorpus,
  reviewLog,
  reviewShow,
} from "../src/review/core.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
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

const OCD = (n: string) => `ocd-participation-window/federal/${n}`;
const OCD_A = OCD("2025-02910"); // legacy human pin, then an agent pin (superseded → honored)
const OCD_B = OCD("2025-55555"); // clean, never reviewed — must appear nowhere
const OCD_C = OCD("2025-77777"); // escalated by a human — parked
const OCD_D = OCD("2025-88888"); // human pin, then a newer FR observation — invalidated

const T0 = new Date("2026-09-02T00:00:00Z");
const T1 = new Date("2026-09-03T00:00:00Z"); // legacy pin on A
const T2 = new Date("2026-09-05T00:00:00Z"); // agent pin on A
const T3 = new Date("2026-09-06T00:00:00Z"); // escalate on C
const T3b = new Date("2026-09-06T01:00:00Z"); // pin on D
const T4 = new Date("2026-09-07T00:00:00Z"); // newer FR on D

/** Seed one window: FR says `frClose`, Regs says `regsEnd` (UTC instant). */
async function seed(docNum: string, frClose: string, regsEnd: string) {
  await ingestObservation(sql, {
    ...parseFrObservation({
      ...frFixture,
      document_number: docNum,
      comments_close_on: frClose,
    }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  const regsRaw = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
  Object.assign(regsRaw.data.attributes, {
    frDocNum: docNum,
    commentEndDate: regsEnd,
    withdrawn: false,
    openForComment: true,
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRaw),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  await reconcileOcdId(sql, OCD(docNum), T0);
}
async function latestHashes(ocdId: string): Promise<string[]> {
  return (await reviewShow(sql, ocdId)).sources.map((s) => s.payload_hash);
}

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  await seed("2025-02910", "2026-09-15", "2026-09-21T03:59:59Z"); // conflicting
  await seed("2025-55555", "2026-10-01", "2026-10-02T03:59:59Z"); // agrees → HIGH
  await seed("2025-77777", "2026-09-10", "2026-09-13T03:59:59Z"); // conflicting
  await seed("2025-88888", "2026-09-10", "2026-09-13T03:59:59Z"); // conflicting

  // A legacy-shaped verdict (pre-0.11.0: no `reviewer` key) written straight through ingest, the way
  // the 2026-09 Codex pins exist in the real log. The contract default makes it `human`.
  {
    const raw = {
      kind: "pin_close",
      pinned_close_date: "2026-09-20",
      note: "legacy codex pin (person authorized)",
      operator: "codex",
      reviewed_payload_hashes: await latestHashes(OCD_A),
    };
    await ingestObservation(sql, {
      ocd_id: OCD_A,
      source: "human_review",
      fr_document_number: null,
      regs_document_id: null,
      regs_object_id: null,
      payload_hash: createHash("sha256")
        .update(JSON.stringify(raw))
        .digest("hex"),
      fetched_at: T1.toISOString(),
      parser_version: "human-review-v1",
      raw_dates_text: null,
      is_extension: false,
      is_correction: false,
      is_withdrawal: false,
      is_reopening: false,
      raw,
    });
    await reconcileOcdId(sql, OCD_A, T1);
  }
  // An agent pin on the same window supersedes the legacy one (latest wins).
  const agentPin = await resolveWindow(
    sql,
    {
      ocdId: OCD_A,
      kind: "pin_close",
      close: "2026-09-20",
      note: "autopilot: FR DATES text states September 20; Regs carries the docket-level date",
      operator: "autopilot",
      reviewer: "agent",
      expect: await latestHashes(OCD_A),
    },
    T2,
  );
  assert("setup: agent pin honored", agentPin.honored);
  // A human escalate parks C.
  const esc = await resolveWindow(
    sql,
    {
      ocdId: OCD_C,
      kind: "escalate",
      note: "searched FR, GovInfo, Regs document + docket, extension search: no document explains the gap",
      operator: "lucas",
      expect: await latestHashes(OCD_C),
    },
    T3,
  );
  assert("setup: escalate parked", esc.honored);
  // A human pin on D, then a newer FR observation with a different date invalidates it (ADR 0010).
  const pinD = await resolveWindow(
    sql,
    {
      ocdId: OCD_D,
      kind: "pin_close",
      close: "2026-09-12",
      note: "pin that later evidence will invalidate",
      operator: "lucas",
      expect: await latestHashes(OCD_D),
    },
    T3b,
  );
  assert("setup: pin on D honored at write", pinD.honored);
  await ingestObservation(sql, {
    ...parseFrObservation({
      ...frFixture,
      document_number: "2025-88888",
      comments_close_on: "2026-09-11",
    }),
    fetched_at: T4.toISOString(),
  });
  await reconcileOcdId(sql, OCD_D, T4);

  // ── LOG: everything, newest first, with standing ──────────────────────────────────────────────────
  const all = await reviewLog(sql);
  assert(
    "LOG: four verdicts, newest first",
    all.entries.length === 4 &&
      all.entries.map((e) => e.ocd_id).join(",") ===
        [OCD_D, OCD_C, OCD_A, OCD_A].join(","),
    all.entries.map((e) => `${e.ocd_id}@${e.fetched_at}`).join(" "),
  );
  const standing = (ocdId: string, operator: string) =>
    all.entries.find(
      (e) =>
        e.ocd_id === ocdId &&
        !("unparseable" in e.verdict) &&
        e.verdict.operator === operator,
    )?.standing;
  assert(
    "LOG: agent pin on A is HONORED",
    standing(OCD_A, "autopilot") === "honored",
    String(standing(OCD_A, "autopilot")),
  );
  assert(
    "LOG: legacy pin on A is SUPERSEDED (a later verdict exists)",
    standing(OCD_A, "codex") === "superseded",
    String(standing(OCD_A, "codex")),
  );
  assert(
    "LOG: escalate on C is PARKED",
    standing(OCD_C, "lucas") === "parked",
    String(standing(OCD_C, "lucas")),
  );
  assert(
    "LOG: pin on D is INVALIDATED (latest verdict, newer evidence)",
    standing(OCD_D, "lucas") === "invalidated",
    String(standing(OCD_D, "lucas")),
  );
  assert(
    "LOG: legacy row reads as reviewer=human (contract default)",
    all.entries.some(
      (e) =>
        !("unparseable" in e.verdict) &&
        e.verdict.operator === "codex" &&
        e.verdict.reviewer === "human",
    ),
  );
  assert(
    "LOG: counts by kind and standing cover the returned entries",
    all.byKind["pin_close"] === 3 &&
      all.byKind["escalate"] === 1 &&
      all.byStanding.honored === 1 &&
      all.byStanding.superseded === 1 &&
      all.byStanding.parked === 1 &&
      all.byStanding.invalidated === 1 &&
      all.byStanding.unparseable === 0,
    JSON.stringify({ k: all.byKind, s: all.byStanding }),
  );

  // ── LOG: filters (applied in SQL — the limit means "the newest N matching") ───────────────────────
  const agent = await reviewLog(sql, { reviewer: "agent" });
  assert(
    "LOG --reviewer agent: exactly the agent pin",
    agent.entries.length === 1 &&
      agent.entries[0]!.ocd_id === OCD_A &&
      agent.entries[0]!.standing === "honored",
    JSON.stringify(agent.entries.map((e) => e.ocd_id)),
  );
  const human = await reviewLog(sql, { reviewer: "human" });
  assert(
    "LOG --reviewer human: the three human verdicts, INCLUDING the legacy row without a reviewer key",
    human.entries.length === 3 &&
      human.entries.some(
        (e) => !("unparseable" in e.verdict) && e.verdict.operator === "codex",
      ),
    JSON.stringify(human.entries.map((e) => e.ocd_id)),
  );
  const codex = await reviewLog(sql, { operator: "codex" });
  assert(
    "LOG --operator codex: the legacy pin only",
    codex.entries.length === 1 && codex.entries[0]!.standing === "superseded",
  );
  const escalates = await reviewLog(sql, { kind: "escalate" });
  assert(
    "LOG --kind escalate: the parked one only",
    escalates.entries.length === 1 && escalates.entries[0]!.ocd_id === OCD_C,
  );
  const since = await reviewLog(sql, { since: T2 });
  assert(
    "LOG --since T2: excludes the T1 legacy pin, keeps the rest (inclusive at T2)",
    since.entries.length === 3 &&
      !since.entries.some(
        (e) => !("unparseable" in e.verdict) && e.verdict.operator === "codex",
      ),
    JSON.stringify(since.entries.map((e) => e.fetched_at)),
  );
  const one = await reviewLog(sql, { limit: 1 });
  assert(
    "LOG --limit 1: the single newest verdict (the pin on D)",
    one.entries.length === 1 && one.entries[0]!.ocd_id === OCD_D,
  );
  const combo = await reviewLog(sql, {
    reviewer: "human",
    since: T2,
    limit: 1,
  });
  assert(
    "LOG combined filters: newest human verdict since T2 is the pin on D",
    combo.entries.length === 1 &&
      combo.entries[0]!.ocd_id === OCD_D &&
      combo.byStanding.invalidated === 1,
  );

  // ── CORPUS: honored verdicts grouped by what a blind proposal must reproduce ──────────────────────
  const corpus = await reviewCorpus(sql, T4);
  assert(
    "CORPUS: part 1 pins = the honored agent pin on A with the pinned date as expectation",
    corpus.pins.length === 1 &&
      corpus.pins[0]!.ocd_id === OCD_A &&
      corpus.pins[0]!.expected_close === "2026-09-20" &&
      corpus.pins[0]!.reviewer === "agent" &&
      corpus.pins[0]!.operator === "autopilot",
    JSON.stringify(corpus.pins),
  );
  assert(
    "CORPUS: part 3 escalations = the parked C; no withdrawals; nothing else honored",
    corpus.escalations.length === 1 &&
      corpus.escalations[0]!.ocd_id === OCD_C &&
      corpus.escalations[0]!.expected_close === null &&
      corpus.withdrawals.length === 0 &&
      corpus.other.length === 0,
    JSON.stringify({ e: corpus.escalations, w: corpus.withdrawals }),
  );
  assert(
    "CORPUS: the invalidated pin on D is listed as NOT gated, with its standing",
    corpus.not_honored.length === 1 &&
      corpus.not_honored[0]!.ocd_id === OCD_D &&
      corpus.not_honored[0]!.standing === "invalidated" &&
      corpus.not_honored[0]!.kind === "pin_close",
    JSON.stringify(corpus.not_honored),
  );
  const everywhere = [
    ...corpus.pins,
    ...corpus.escalations,
    ...corpus.withdrawals,
    ...corpus.other,
    ...corpus.not_honored,
  ].map((i) => i.ocd_id);
  assert(
    "CORPUS: a never-reviewed window appears nowhere; each reviewed window appears exactly once",
    !everywhere.includes(OCD_B) &&
      everywhere.length === 3 &&
      new Set(everywhere).size === 3,
    JSON.stringify(everywhere),
  );
  assert(
    "CORPUS: generated_at is the supplied clock",
    corpus.generated_at === T4.toISOString(),
  );
} finally {
  await sql.end();
}

console.log(`review-log.test.ts\n${out.join("\n")}`);
if (failures > 0) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log("\nall passed");
