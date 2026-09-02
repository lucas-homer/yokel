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
 *   • INERT UNTIL reconcile-v2 — reconciling the window with a human_review row in its chain still
 *     derives from source observations only (v1.1 has no honor-the-verdict rule; the row is
 *     harmless, auditable data — the documented PR-R2 rollback stance holds in reverse).
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
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
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

  // ── INERT UNTIL reconcile-v2: v1.1 derivation ignores the verdict entirely ──────────────────────────
  const r = await reconcileOcdId(sql, OCD, new Date("2026-06-03T00:00:00Z"));
  assert(
    "INERT: reconcile-v1.1 still derives the FR-only close (verdict not honored yet)",
    r.window.resolved_close_display ===
      "closes 2026-09-10 at 11:59 p.m. ET (inferred from FR date-only value)" &&
      !r.window.conflict_flags.includes("human_resolved"),
    `${r.window.resolved_close_display} [${r.window.conflict_flags.join(",")}]`,
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
