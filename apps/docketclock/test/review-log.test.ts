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
 *     reproduce; an invalidated verdict is listed as not gated; an unparseable latest verdict is
 *     listed with NO invented kind or authority; a window with no verdict is absent.
 *   • BLIND IDS (review round 1, P1): the proposer's view is a flat sha256-ordered list of the gated
 *     ids — no grouping, no expectation, not-honored windows excluded.
 *   • TRUNCATION: `limit` smaller than the population sets `truncated` (a Monday sample must never be
 *     drawn from a truncated list); empty results are honest zeros.
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
  corpusBlindIds,
  parseSince,
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

const OCD = (n: string) => `ocd-participation-window/federal/${n}`;
const OCD_A = OCD("2025-02910"); // legacy human pin, then an agent pin (superseded → honored)
const OCD_B = OCD("2025-55555"); // clean, never reviewed — must appear nowhere
const OCD_C = OCD("2025-77777"); // escalated by a human — parked
const OCD_D = OCD("2025-88888"); // human pin, then a newer FR observation — invalidated
const OCD_E = OCD("2025-66666"); // confirmed withdrawn by a human — honored, LOW
const OCD_F = OCD("2025-44444"); // latest verdict row is an UNPARSEABLE raw (inserted below the typed gate)
const OCD_G = OCD("2025-33333"); // human dismiss_conflict — honored, the corpus's `other` group
const OCD_H = OCD("2025-22222"); // a human pin, then an unparseable AGENT-keyed row on top (superseded by garbage)

const T0 = new Date("2026-09-02T00:00:00Z");
const T1 = new Date("2026-09-03T00:00:00Z"); // legacy pin on A
const T2 = new Date("2026-09-05T00:00:00Z"); // agent pin on A
const T3 = new Date("2026-09-06T00:00:00Z"); // escalate on C
const T3b = new Date("2026-09-06T01:00:00Z"); // pin on D
const T4 = new Date("2026-09-07T00:00:00Z"); // newer FR on D
const T5 = new Date("2026-09-08T00:00:00Z"); // withdrawal on E
const T6 = new Date("2026-09-09T00:00:00Z"); // unparseable row on F
const T7 = new Date("2026-09-10T00:00:00Z"); // dismiss on G
const T8 = new Date("2026-09-11T00:00:00Z"); // pin on H, then its unparseable agent row at T8 + 1h

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
  await seed("2025-66666", "2026-09-10", "2026-09-13T03:59:59Z"); // conflicting, then withdrawn
  await seed("2025-44444", "2026-09-10", "2026-09-13T03:59:59Z"); // conflicting, then an unparseable row
  await seed("2025-33333", "2026-09-10", "2026-09-13T03:59:59Z"); // conflicting, then dismissed
  await seed("2025-22222", "2026-09-10", "2026-09-13T03:59:59Z"); // conflicting, pin, then garbage

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
  // A human withdrawal on E (honored, LOW) — the corpus's `withdrawals` group.
  const wd = await resolveWindow(
    sql,
    {
      ocdId: OCD_E,
      kind: "confirm_withdrawn",
      note: "live regs.gov shows this document withdrawn",
      operator: "lucas",
      expect: await latestHashes(OCD_E),
    },
    T5,
  );
  assert("setup: withdrawal honored", wd.honored);
  // An UNPARSEABLE latest verdict on F: the ingest gate refuses such a raw today, so it is inserted
  // directly — the shape a future contract change could leave behind. It must be listed, never
  // honored, and never dressed up with an invented kind or authority.
  await sql`
    insert into observations
      (ocd_id, source, fr_document_number, regs_document_id, regs_object_id, payload_hash,
       fetched_at, parser_version, raw_dates_text, is_extension, is_correction, is_withdrawal,
       is_reopening, raw)
    values
      (${OCD_F}, 'human_review', null, null, null,
       ${"f".repeat(64)}, ${T6.toISOString()}, 'human-review-v1', null, false, false, false, false,
       ${sql.json({ kind: "pin_close", note: "no date, no operator" })})
  `;
  await reconcileOcdId(sql, OCD_F, T6);
  // A human dismiss on G — honored, outside the v1 policy, the corpus's `other` group.
  const dis = await resolveWindow(
    sql,
    {
      ocdId: OCD_G,
      kind: "dismiss_conflict",
      note: "noise: the portal date is a known sentinel",
      operator: "lucas",
      expect: await latestHashes(OCD_G),
    },
    T7,
  );
  assert("setup: dismiss honored", dis.honored);
  // A human pin on H, then an unparseable row that CLAIMS reviewer=agent: the pin is superseded
  // (latest wins, whatever the latest one's standing) and the garbage belongs in the agent's log.
  const pinH = await resolveWindow(
    sql,
    {
      ocdId: OCD_H,
      kind: "pin_close",
      close: "2026-09-12",
      note: "pin that garbage will supersede",
      operator: "lucas",
      expect: await latestHashes(OCD_H),
    },
    T8,
  );
  assert("setup: pin on H honored at write", pinH.honored);
  const T8b = new Date(T8.getTime() + 3_600_000);
  await sql`
    insert into observations
      (ocd_id, source, fr_document_number, regs_document_id, regs_object_id, payload_hash,
       fetched_at, parser_version, raw_dates_text, is_extension, is_correction, is_withdrawal,
       is_reopening, raw)
    values
      (${OCD_H}, 'human_review', null, null, null,
       ${"e".repeat(64)}, ${T8b.toISOString()}, 'human-review-v1', null, false, false, false, false,
       ${sql.json({ kind: "pin_close", reviewer: "agent", operator: "autopilot", note: "no date" })})
  `;
  await reconcileOcdId(sql, OCD_H, T8b);

  // ── SHOW identity (smoke finding 8): what the evidence card needs, from source raw, blind-safe ────
  {
    // An enriched FR raw: citation, publication_date and RINs present (the fixture lacks them).
    const OCD_I = OCD("2025-11111");
    await ingestObservation(sql, {
      ...parseFrObservation({
        ...frFixture,
        document_number: "2025-11111",
        comments_close_on: "2026-09-15",
        citation: "91 FR 54096",
        publication_date: "2026-08-20",
        regulation_id_numbers: ["3245-AI67", " "],
      }),
      fetched_at: "2026-09-01T00:00:00.000Z",
    });
    await reconcileOcdId(sql, OCD_I, T0);
    const rich = await reviewShow(sql, OCD_I, { blind: true });
    assert(
      "SHOW identity: citation, publication date and RINs come through when present (blank RIN dropped); no Regs → nulls",
      rich.identity.citation === "91 FR 54096" &&
        rich.identity.publication_date === "2026-08-20" &&
        rich.identity.rins.join(",") === "3245-AI67" &&
        rich.identity.regs_document_id === null &&
        rich.identity.regs_title === null,
      JSON.stringify(rich.identity),
    );
    const plainA = await reviewShow(sql, OCD_A);
    assert(
      "SHOW identity: regs_title comes from the Regs attributes",
      (plainA.identity.regs_title ?? "").startsWith(
        "Intent to Designate as Abandoned",
      ),
      String(plainA.identity.regs_title),
    );
    const plain = await reviewShow(sql, OCD_A);
    const blind = await reviewShow(sql, OCD_A, { blind: true });
    const idOk = (i: typeof plain.identity) =>
      i.fr_document_number === "2025-02910" &&
      (i.title ?? "").startsWith(
        "Two Actions Published by the Environmental Protection Agency",
      ) &&
      i.docket_ids.join(",") === "EPA-HQ-OW-2024-0454" &&
      i.regs_document_id === "FAA-2025-5396-0001" &&
      i.regs_docket_id === "FAA-2025-5396" &&
      i.regs_fr_doc_num === "2025-02910" &&
      i.citation === null; // the fixture carries no citation: null, never invented
    assert(
      "SHOW identity: document number, title, dockets and the Regs document/docket/frDocNum from the raw",
      idOk(plain.identity),
      JSON.stringify(plain.identity),
    );
    assert(
      "SHOW --blind identity: identical (source raw only, nothing verdict-derived)",
      JSON.stringify(blind.identity) === JSON.stringify(plain.identity),
    );
  }

  // ── LOG: everything, newest first, with standing ──────────────────────────────────────────────────
  const all = await reviewLog(sql);
  assert(
    "LOG: nine verdicts, newest first, not truncated",
    all.entries.length === 9 &&
      !all.truncated &&
      all.entries.map((e) => e.ocd_id).join(",") ===
        [OCD_H, OCD_H, OCD_G, OCD_F, OCD_E, OCD_D, OCD_C, OCD_A, OCD_A].join(
          ",",
        ),
    all.entries.map((e) => `${e.ocd_id}@${e.fetched_at}`).join(" "),
  );
  assert(
    "LOG: an unparseable latest row is UNPARSEABLE with no verdict fields; the parseable pin under it is SUPERSEDED (latest wins, whatever its standing)",
    all.entries[0]!.standing === "unparseable" &&
      "unparseable" in all.entries[0]!.verdict &&
      all.entries[1]!.ocd_id === OCD_H &&
      all.entries[1]!.standing === "superseded",
    JSON.stringify(all.entries.slice(0, 2)),
  );
  assert(
    "LOG: the dismiss on G is HONORED; the withdrawal on E is HONORED",
    all.entries[2]!.standing === "honored" &&
      all.entries[4]!.ocd_id === OCD_E &&
      all.entries[4]!.standing === "honored",
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
    all.byKind["pin_close"] === 4 &&
      all.byKind["escalate"] === 1 &&
      all.byKind["confirm_withdrawn"] === 1 &&
      all.byKind["dismiss_conflict"] === 1 &&
      all.byKind["unparseable"] === 2 &&
      all.byStanding.honored === 3 &&
      all.byStanding.superseded === 2 &&
      all.byStanding.parked === 1 &&
      all.byStanding.invalidated === 1 &&
      all.byStanding.unparseable === 2,
    JSON.stringify({ k: all.byKind, s: all.byStanding }),
  );

  // ── LOG: filters (applied in SQL — the limit means "the newest N matching") ───────────────────────
  const agent = await reviewLog(sql, { reviewer: "agent" });
  assert(
    "LOG --reviewer agent: the agent pin AND the unparseable agent-keyed row (a malformed agent row is never hidden from the agent's log)",
    agent.entries.length === 2 &&
      agent.entries[0]!.ocd_id === OCD_H &&
      agent.entries[0]!.standing === "unparseable" &&
      agent.entries[1]!.ocd_id === OCD_A &&
      agent.entries[1]!.standing === "honored",
    JSON.stringify(agent.entries.map((e) => [e.ocd_id, e.standing])),
  );
  // Filters match the raw's fields AS STORED: the unparseable row on F has no reviewer key, so it
  // reads as `human` like any legacy row, and is listed with standing UNPARSEABLE — nothing hidden.
  const human = await reviewLog(sql, { reviewer: "human" });
  assert(
    "LOG --reviewer human: the six human verdicts PLUS the unparseable key-less row, INCLUDING the legacy row without a reviewer key",
    human.entries.length === 7 &&
      human.entries.some(
        (e) => e.ocd_id === OCD_F && e.standing === "unparseable",
      ) &&
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
    since.entries.length === 8 &&
      !since.entries.some(
        (e) => !("unparseable" in e.verdict) && e.verdict.operator === "codex",
      ),
    JSON.stringify(since.entries.map((e) => e.fetched_at)),
  );
  const one = await reviewLog(sql, { limit: 1 });
  assert(
    "LOG --limit 1: the single newest row (the garbage on H), flagged TRUNCATED",
    one.entries.length === 1 &&
      one.entries[0]!.ocd_id === OCD_H &&
      one.truncated,
  );
  const combo = await reviewLog(sql, {
    reviewer: "human",
    since: T2,
    limit: 1,
  });
  assert(
    "LOG combined filters: newest human-keyed row since T2 is the pin on H; truncated",
    combo.entries.length === 1 &&
      combo.entries[0]!.ocd_id === OCD_H &&
      combo.byStanding.superseded === 1 &&
      combo.truncated,
    JSON.stringify(combo.entries.map((e) => e.ocd_id)),
  );
  const exact = await reviewLog(sql, { reviewer: "human", limit: 7 });
  assert(
    "LOG limit equal to the matching population is NOT truncated",
    exact.entries.length === 7 && !exact.truncated,
  );
  await rejects(
    "LOG: a programmatic limit outside 1..10000 is refused by the core, not just the CLI",
    () => reviewLog(sql, { limit: 0 }),
    /limit must be an integer from 1 to 10000/,
  );
  await rejects(
    "LOG: an empty operator filter is refused (it could never match and would read as 'no filter')",
    () => reviewLog(sql, { operator: "  " }),
    /operator filter must not be empty/,
  );
  const NOW = new Date("2026-10-20T12:00:00Z");
  assert(
    "parseSince: 7d / 2w / 12h are relative to now; YYYY-MM-DD is UTC midnight; junk and rollovers are null",
    parseSince("7d", NOW)?.toISOString() === "2026-10-13T12:00:00.000Z" &&
      parseSince("2w", NOW)?.toISOString() === "2026-10-06T12:00:00.000Z" &&
      parseSince("12h", NOW)?.toISOString() === "2026-10-20T00:00:00.000Z" &&
      parseSince("2026-10-01", NOW)?.toISOString() ===
        "2026-10-01T00:00:00.000Z" &&
      parseSince("2026-02-30", NOW) === null &&
      parseSince("yesterday", NOW) === null &&
      parseSince("999999999999999999h", NOW) === null,
  );
  const none = await reviewLog(sql, { operator: "nobody" });
  assert(
    "LOG with no match: empty entries, zero counts, not truncated",
    none.entries.length === 0 &&
      Object.keys(none.byKind).length === 0 &&
      Object.values(none.byStanding).every((n) => n === 0) &&
      !none.truncated,
    JSON.stringify(none),
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
    "CORPUS: part 3 escalations = the parked C; withdrawals = the honored E; nothing else honored",
    corpus.escalations.length === 1 &&
      corpus.escalations[0]!.ocd_id === OCD_C &&
      corpus.escalations[0]!.expected_close === null &&
      corpus.withdrawals.length === 1 &&
      corpus.withdrawals[0]!.ocd_id === OCD_E &&
      corpus.withdrawals[0]!.kind === "confirm_withdrawn" &&
      corpus.other.length === 1 &&
      corpus.other[0]!.ocd_id === OCD_G &&
      corpus.other[0]!.kind === "dismiss_conflict",
    JSON.stringify({ e: corpus.escalations, w: corpus.withdrawals }),
  );
  const invalidated = corpus.not_honored.find((i) => i.ocd_id === OCD_D);
  const unparseable = corpus.not_honored.find((i) => i.ocd_id === OCD_F);
  assert(
    "CORPUS: the invalidated pin on D is listed as NOT gated, with its standing and verdict; H (garbage latest) is unparseable too",
    corpus.not_honored.length === 3 &&
      corpus.not_honored.find((i) => i.ocd_id === OCD_H)?.standing ===
        "unparseable" &&
      invalidated?.standing === "invalidated" &&
      invalidated.kind === "pin_close" &&
      invalidated.expected_close === "2026-09-12",
    JSON.stringify(corpus.not_honored),
  );
  assert(
    "CORPUS: the unparseable row on F is listed with NO kind, reviewer or operator",
    unparseable?.standing === "unparseable" &&
      !("kind" in unparseable) &&
      !("reviewer" in unparseable) &&
      !("operator" in unparseable),
    JSON.stringify(unparseable),
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
      everywhere.length === 7 &&
      new Set(everywhere).size === 7,
    JSON.stringify(everywhere),
  );

  // ── BLIND IDS: the proposer's view carries nothing but ids ───────────────────────────────────────
  const blind = corpusBlindIds(corpus);
  const sha = (id: string) => createHash("sha256").update(id).digest("hex");
  assert(
    "BLIND IDS: exactly the gated windows (A, C, E, and G from `other`) — not-honored D, F, H excluded, never-reviewed B absent",
    blind.length === 4 &&
      new Set(blind).size === 4 &&
      [OCD_A, OCD_C, OCD_E, OCD_G].every((id) => blind.includes(id)),
    JSON.stringify(blind),
  );
  assert(
    "BLIND IDS: ordered by sha256(id) — deterministic, and unrelated to the grouping",
    blind.join(",") ===
      [...blind].sort((a, b) => (sha(a) < sha(b) ? -1 : 1)).join(","),
    JSON.stringify(blind),
  );
  assert(
    "BLIND IDS: a second computation is identical",
    corpusBlindIds(corpus).join(",") === blind.join(","),
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
