/**
 * human-review-ingest.test.ts — PR-R1's DB seam (Slice R, plans/review-resolve.md): migration 0011
 * widens 0001's source CHECK in lockstep with contract 0.10.0, and a human_review observation rides
 * the EXISTING ingest machinery unchanged.
 *
 * Proves the load-bearing properties:
 *   • ROUND-TRIP — a human_review observation (HumanReviewVerdict raw, the plan's row conventions:
 *     flags false, document ids/dates_text null, parser_version human-review-v1) ingests through
 *     ingestObservation and the read-back row passes Observation.parse — the PR-R1 verify criterion.
 *   • CHECK STILL CLOSED — the widened constraint rejects an unknown source at the DB layer (the
 *     adversarial probe: widening is not opening).
 *   • APPEND-ONLY APPLIES UNCHANGED — a direct UPDATE on the ingested human_review row is rejected
 *     by 0001's trigger; corrections accrete, they never mutate.
 *   • IDEMPOTENT RETRY + TYPED-RAW GATE (the #115 review findings) — a verdict dedupes on its
 *     window (ocd_id, the natural key when document ids are null by convention) so a retried write
 *     never duplicates, a different verdict still accretes, and a freeform-raw candidate is
 *     schema-rejected at the ingest seam before it can touch the log.
 *   • THE FRESHNESS GATE, END-TO-END (reconcile-v2) — a verdict OLDER than the newest source
 *     observation is ignored through the real reconcileOcdId SQL read; a FRESH verdict is honored
 *     (HIGH, pinned close, human_resolved) and persisted; and on a CONFLICTING pair the honored
 *     verdict RETIRES the live conflict_records row (resolved_at stamped) while a newer
 *     still-disagreeing source observation RESURFACES a live conflict — the full supersedence
 *     lifecycle against real Postgres, not just the pure engine.
 *
 * Requires a throwaway Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  HumanReviewVerdict,
  Observation,
  type HumanReviewVerdict as HumanReviewVerdictT,
} from "@yokel/contracts";
import { RECONCILER_VERSION } from "../src/reconcile/reconcile.js";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";

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

const NOW = new Date("2026-06-01T00:00:00Z");
const OCD = "ocd-participation-window/federal/2025-02910";
const sha256 = (s: string) => createHash("sha256").update(s).digest("hex");

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0011 applies",
    applied.includes("0011_human_review_source.sql"),
    applied.join(", "),
  );

  // Seed a real FR-backed window so the human_review row targets an existing chain.
  const frCand = parseFrObservation({
    ...frFixture,
    comments_close_on: "2026-09-10",
  });
  await ingestObservation(sql, frCand);
  await reconcileOcdId(sql, OCD, NOW);

  // ── ROUND-TRIP: ingest a human_review observation through the normal path ───────────────────────────
  const verdict: HumanReviewVerdictT = HumanReviewVerdict.parse({
    kind: "pin_close",
    pinned_close_date: "2026-09-12",
    note: "Read both notices; FR DATES text controls — the close is Sep 12.",
    operator: "lucas",
    reviewed_payload_hashes: [frCand.payload_hash],
  });
  const raw = { ...verdict };
  const ingest = await ingestObservation(sql, {
    ocd_id: OCD,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: sha256(JSON.stringify(raw)),
    fetched_at: "2026-06-02T00:00:00.000Z",
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
  });
  assert("human_review candidate ingests (inserted)", ingest.inserted === true);

  const [row] = await sql<Record<string, unknown>[]>`
    select observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
           payload_hash, fetched_at, parser_version, raw_dates_text,
           is_extension, is_correction, is_withdrawal, is_reopening, raw
    from observations where source = 'human_review' and ocd_id = ${OCD}
  `;
  const parsed = Observation.safeParse({
    ...row,
    fetched_at:
      row!.fetched_at instanceof Date
        ? row!.fetched_at.toISOString()
        : row!.fetched_at,
  });
  assert(
    "ROUND-TRIP: read-back row passes Observation.parse",
    parsed.success,
    parsed.success ? "" : JSON.stringify(parsed.error.issues),
  );
  assert(
    "ROUND-TRIP: raw payload still parses as HumanReviewVerdict",
    HumanReviewVerdict.safeParse(row!.raw).success,
  );

  // ── IDEMPOTENT RETRY: a verdict's natural dedupe key is its WINDOW (ocd_id) ─────────────────────────
  // Document ids are null by convention, so without the ocd_id key every retried write would append a
  // duplicate row (the #115 Copilot finding). An identical re-ingest must dedupe; a DIFFERENT verdict
  // for the same window must still append (corrections accrete).
  const retry = await ingestObservation(sql, {
    ocd_id: OCD,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: sha256(JSON.stringify(raw)),
    fetched_at: "2026-06-02T00:05:00.000Z",
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
  });
  assert(
    "RETRY: identical verdict re-ingest dedupes (inserted=false)",
    retry.inserted === false,
  );
  const raw2 = {
    ...verdict,
    note: "Second look — still Sep 12, but the extension notice confirms it.",
  };
  const second = await ingestObservation(sql, {
    ocd_id: OCD,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: sha256(JSON.stringify(raw2)),
    fetched_at: "2026-06-02T01:00:00.000Z",
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: raw2,
  });
  assert(
    "ACCRETE: a different verdict for the same window still appends",
    second.inserted === true,
  );

  // ── TYPED-RAW GATE: a freeform-raw human_review candidate is rejected at the ingest seam ────────────
  let gateRejected = false;
  try {
    await ingestObservation(sql, {
      ocd_id: OCD,
      source: "human_review",
      fr_document_number: null,
      regs_document_id: null,
      regs_object_id: null,
      payload_hash: sha256("freeform"),
      fetched_at: "2026-06-02T02:00:00.000Z",
      parser_version: "human-review-v1",
      raw_dates_text: null,
      is_extension: false,
      is_correction: false,
      is_withdrawal: false,
      is_reopening: false,
      raw: { foo: "not a verdict" },
    });
  } catch {
    gateRejected = true;
  }
  assert(
    "TYPED-RAW GATE: freeform raw never reaches the log (ingest throws)",
    gateRejected,
  );
  const [hrRow] = await sql<{ count: string }[]>`
    select count(*) as count from observations where source = 'human_review'
  `;
  assert(
    "LOG STATE: exactly 2 human_review rows (verdict + accreted second; no dupe, no freeform)",
    hrRow!.count === "2",
    hrRow!.count,
  );

  // ── CHECK STILL CLOSED: an unknown source is rejected at the DB layer ───────────────────────────────
  let rejected = false;
  try {
    await sql`
      insert into observations (ocd_id, source, payload_hash, parser_version,
        is_extension, is_correction, is_withdrawal, is_reopening, raw)
      values (${OCD}, 'carrier_pigeon', ${sha256("x")}, 'v0', false, false, false, false, '{}'::jsonb)
    `;
  } catch (e) {
    rejected = /observations_source_check/.test(
      e instanceof Error ? e.message : String(e),
    );
  }
  assert(
    "CHECK CLOSED: unknown source rejected by observations_source_check",
    rejected,
  );

  // ── APPEND-ONLY: the human_review row is as immutable as any source row ─────────────────────────────
  let updateRejected = false;
  try {
    await sql`update observations set parser_version = 'tampered' where source = 'human_review'`;
  } catch {
    updateRejected = true;
  }
  assert(
    "APPEND-ONLY: direct UPDATE on the human_review row rejected",
    updateRejected,
  );

  // ── GATE (reconcile-v2): the STALE verdicts above are not honored ───────────────────────────────────
  // The FR observation's fetched_at is the ingest wall clock (today); both verdicts above are stamped
  // 2026-06-02 — older than it. The freshness gate ignores them: pure derivation, no human_resolved.
  const gated = await reconcileOcdId(
    sql,
    OCD,
    new Date("2026-06-03T00:00:00Z"),
  );
  assert(
    "GATE: verdict older than the newest source observation is ignored end-to-end",
    gated.window.resolved_close_display ===
      "closes 2026-09-10 at 11:59 p.m. ET (inferred from FR date-only value)" &&
      !gated.window.conflict_flags.includes("human_resolved"),
    `${gated.window.resolved_close_display} [${gated.window.conflict_flags.join(",")}]`,
  );

  // ── HONORED end-to-end: a FRESH verdict flows through the real SQL read + persist ───────────────────
  const rawFresh = {
    ...verdict,
    note: "Fresh verdict — newer than every source observation.",
  };
  await ingestObservation(sql, {
    ocd_id: OCD,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: sha256(JSON.stringify(rawFresh)),
    fetched_at: new Date().toISOString(), // strictly ≥ the FR ingest stamp; ties honor the human
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: rawFresh,
  });
  const honored = await reconcileOcdId(
    sql,
    OCD,
    new Date("2026-06-04T00:00:00Z"),
  );
  assert(
    "HONORED: fresh verdict honored through reconcileOcdId (HIGH, pinned close, human_resolved)",
    honored.window.confidence === "high" &&
      honored.window.resolved_close_display ===
        "closes 2026-09-12 at 11:59 p.m. ET (pinned by human review)" &&
      honored.window.conflict_flags.includes("human_resolved"),
    `${honored.window.confidence} ${honored.window.resolved_close_display}`,
  );
  const [persisted] = await sql<
    { confidence: string; reconciler_version: string }[]
  >`
    select confidence, reconciler_version from participation_windows where ocd_id = ${OCD}
  `;
  assert(
    "HONORED: projection row persisted at HIGH under the current reconciler version",
    persisted!.confidence === "high" &&
      persisted!.reconciler_version === RECONCILER_VERSION,
    `${persisted!.confidence} ${persisted!.reconciler_version}`,
  );

  // ── RETIRE + RESURFACE on a CONFLICTING pair (explicit fetched_at stamps — no wall-clock races) ─────
  const OCD_B = "ocd-participation-window/federal/2025-66666";
  const frB = {
    ...parseFrObservation({
      ...frFixture,
      document_number: "2025-66666",
      comments_close_on: "2026-09-15",
    }),
    fetched_at: "2026-09-01T00:00:00.000Z",
  };
  await ingestObservation(sql, frB);
  const regsRawB = JSON.parse(
    JSON.stringify(regsFixture),
  ) as typeof regsFixture;
  Object.assign(regsRawB.data.attributes, {
    frDocNum: "2025-66666",
    commentEndDate: "2026-09-21T03:59:59Z", // Eastern 2026-09-20 — a true date mismatch vs FR 09-15
    withdrawn: false,
    openForComment: true,
  });
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRawB),
    fetched_at: "2026-09-01T01:00:00.000Z",
  });
  const conflicted = await reconcileOcdId(
    sql,
    OCD_B,
    new Date("2026-09-02T00:00:00Z"),
  );
  const liveBefore = await sql<{ resolved_at: Date | null }[]>`
    select resolved_at from conflict_records where ocd_id = ${OCD_B}
  `;
  assert(
    "CONFLICT: machine mismatch emits a LIVE conflict_records row",
    conflicted.window.confidence === "conflicting" &&
      liveBefore.length === 1 &&
      liveBefore[0]!.resolved_at === null,
    `${conflicted.window.confidence} rows=${liveBefore.length}`,
  );

  const rawPinB = HumanReviewVerdict.parse({
    kind: "pin_close",
    pinned_close_date: "2026-09-20",
    note: "Regs is right; FR DATES text carries the superseded value.",
    operator: "lucas",
    reviewed_payload_hashes: [frB.payload_hash],
  });
  await ingestObservation(sql, {
    ocd_id: OCD_B,
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: sha256(JSON.stringify(rawPinB)),
    fetched_at: "2026-09-02T00:00:00.000Z",
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: rawPinB,
  });
  await reconcileOcdId(sql, OCD_B, new Date("2026-09-02T01:00:00Z"));
  const retired = await sql<{ resolved_at: Date | null }[]>`
    select resolved_at from conflict_records where ocd_id = ${OCD_B}
  `;
  assert(
    "RETIRE: honored verdict retires the live conflict (resolved_at stamped)",
    retired.length === 1 && retired[0]!.resolved_at !== null,
    `rows=${retired.length}`,
  );

  // A NEWER regs observation, STILL disagreeing (a third date) → verdict un-honored, conflict resurfaces.
  const regsRawB2 = JSON.parse(JSON.stringify(regsRawB)) as typeof regsRawB;
  regsRawB2.data.attributes.commentEndDate = "2026-09-26T03:59:59Z"; // Eastern 09-25
  await ingestObservation(sql, {
    ...parseRegsObservation(regsRawB2),
    fetched_at: "2026-09-03T00:00:00.000Z",
  });
  const resurfaced = await reconcileOcdId(
    sql,
    OCD_B,
    new Date("2026-09-03T01:00:00Z"),
  );
  const liveAfter = await sql<{ resolved_at: Date | null }[]>`
    select resolved_at from conflict_records where ocd_id = ${OCD_B} and resolved_at is null
  `;
  assert(
    "RESURFACE: newer disagreeing source un-honors the verdict — CONFLICTING again with a live record",
    resurfaced.window.confidence === "conflicting" &&
      !resurfaced.window.conflict_flags.includes("human_resolved") &&
      liveAfter.length === 1,
    `${resurfaced.window.confidence} live=${liveAfter.length}`,
  );
} finally {
  await sql.end();
}

console.log("\n=== human-review-ingest results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
