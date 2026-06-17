/**
 * conflict-plumbing.test.ts — Slice 1 of issue #31 (cross-window / chain conflicts), DB-backed.
 *
 * This slice is BEHAVIOR-PRESERVING: it lays the DB + persist + query seam (migration 0006: the
 * conflict_scope / ocd_id_b / govinfo_url_b columns, the widened (ocd_id, observation_a_id,
 * observation_b_id, ocd_id_b) dedup key, the scope-scoped retirement sweeps, and the either-side ocd_id
 * filter) WITHOUT emitting any cross_window rows from the engine. Reconcile still writes only
 * cross_source. These tests pin the seam:
 *
 *   1. DEDUP under the widened key — re-running reconcile on the same cross_source pair still UPSERTs
 *      (no duplicate row, detected_at preserved). Proves the '' sentinel makes the 4-column key dedup.
 *   2. RETIREMENT carries the conflict_scope='cross_source' predicate — a synthetic cross_window row
 *      sharing the ocd_id as side A is NOT collaterally retired by a not-conflicting FR↔Regs re-derive.
 *   3. EITHER-SIDE filter — a cross_window row is found by listConflicts({ocdId: <side B id>}); a
 *      cross_source row (ocd_id_b='') is NOT matched by an unrelated id.
 *   4. READ MAPPING — a cross_source row round-trips ocd_id_b → null (superRefine passes); a cross_window
 *      row round-trips ocd_id_b present (superRefine passes).
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit; a throwaway
 * Postgres with a fresh schema. A fixed `now` keeps stamps reproducible.
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
import { listConflicts } from "../src/api/queries.js";

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

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0006 applies (cross-window conflict columns + widened key)",
    applied.includes("0006_cross_window_conflict.sql"),
    applied.join(", "),
  );

  // The widened unique constraint exists and includes ocd_id_b; the old 3-column key is gone.
  const cons = await sql<{ conname: string; def: string }[]>`
    select conname, pg_get_constraintdef(oid) as def
    from pg_constraint
    where conrelid = 'conflict_records'::regclass and contype = 'u'
  `;
  assert(
    "widened unique key is (ocd_id, observation_a_id, observation_b_id, ocd_id_b)",
    cons.length === 1 &&
      cons[0]!.def ===
        "UNIQUE (ocd_id, observation_a_id, observation_b_id, ocd_id_b)",
    cons.map((c) => `${c.conname}: ${c.def}`).join(" | "),
  );
  assert(
    "the original 3-column key was dropped",
    !cons.some(
      (c) =>
        c.conname ===
        "conflict_records_ocd_id_observation_a_id_observation_b_id_key",
    ),
  );

  // ── 1. DEDUP under the widened key ──────────────────────────────────────────────────────────────────
  // A withdrawn-vs-open pair → CONFLICTING + a cross_source conflict row. Re-running reconcile on the
  // SAME pair must UPSERT (no duplicate; detected_at preserved) — proves ocd_id_b='' collapses the key.
  const OCD_DEDUP = "ocd-participation-window/federal/2025-77701";
  {
    const frC = {
      ...frFixture,
      document_number: "2025-77701",
      comments_close_on: "2026-07-15",
    };
    await ingestObservation(sql, parseFrObservation(frC));
    const regsC = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
    regsC.data.attributes.frDocNum = "2025-77701";
    regsC.data.attributes.commentEndDate = "2026-07-15T12:00:00Z";
    regsC.data.attributes.withdrawn = true;
    regsC.data.attributes.openForComment = true;
    await ingestObservation(sql, parseRegsObservation(regsC));

    const r1 = await reconcileOcdId(sql, OCD_DEDUP, NOW);
    assert(
      "DEDUP: first derive is conflicting (cross_source)",
      r1.window.confidence === "conflicting" && r1.conflict !== null,
      r1.window.confidence,
    );
    const count = async () =>
      (
        await sql<{ count: string }[]>`
          select count(*)::text as count from conflict_records where ocd_id = ${OCD_DEDUP}
        `
      )[0]!.count;
    assert("DEDUP: one row after first detect", (await count()) === "1");

    const [before] = await sql<
      { detected_at: Date; conflict_scope: string; ocd_id_b: string }[]
    >`
      select detected_at, conflict_scope, ocd_id_b from conflict_records where ocd_id = ${OCD_DEDUP}
    `;
    assert(
      "DEDUP: persisted row is conflict_scope=cross_source with ocd_id_b=''",
      before!.conflict_scope === "cross_source" && before!.ocd_id_b === "",
      `${before!.conflict_scope} / "${before!.ocd_id_b}"`,
    );

    await reconcileOcdId(sql, OCD_DEDUP, new Date("2026-06-03T00:00:00Z"));
    assert(
      "DEDUP: re-running does NOT duplicate the row (widened key dedups via '')",
      (await count()) === "1",
      await count(),
    );
    const [after] = await sql<{ detected_at: Date }[]>`
      select detected_at from conflict_records where ocd_id = ${OCD_DEDUP}
    `;
    assert(
      "DEDUP: detected_at preserved across re-detection",
      after!.detected_at.getTime() === before!.detected_at.getTime(),
      `${before!.detected_at.toISOString()} -> ${after!.detected_at.toISOString()}`,
    );
  }

  // ── 2. RETIREMENT is scope-scoped — a cross_window row sharing the ocd_id (side A) survives ──────────
  // Seed a CONFLICTING cross_source on OCD_RET, then inject a synthetic OPEN cross_window row whose side A
  // is the SAME ocd_id. A not-conflicting re-derive of OCD_RET must retire the cross_source row but leave
  // the cross_window row LIVE (the supersede + resolve sweeps both carry conflict_scope='cross_source').
  const OCD_RET = "ocd-participation-window/federal/2025-33301";
  const OCD_RET_B = "ocd-participation-window/federal/2025-33302";
  {
    const frR = {
      ...frFixture,
      document_number: "2025-33301",
      comments_close_on: "2026-07-01",
    };
    await ingestObservation(sql, parseFrObservation(frR));
    const regsR = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
    regsR.data.attributes.frDocNum = "2025-33301";
    regsR.data.attributes.commentEndDate = "2026-08-11T03:59:59Z"; // Eastern 08-10 → mismatch
    await ingestObservation(sql, {
      ...parseRegsObservation(regsR),
      fetched_at: "2026-05-01T00:00:00Z",
    });
    await reconcileOcdId(sql, OCD_RET, NOW);

    const openCount = async (ocd: string) =>
      (
        await sql<{ count: string }[]>`
          select count(*)::text as count from conflict_records
          where ocd_id = ${ocd} and resolved_at is null
        `
      )[0]!.count;
    assert(
      "RETIRE-SCOPE: cross_source conflict open after mismatch",
      (await openCount(OCD_RET)) === "1",
      await openCount(OCD_RET),
    );

    // Inject a synthetic LIVE cross_window row whose side A is OCD_RET (the seam target a later slice
    // would write). This row must NOT be collaterally retired by an OCD_RET FR↔Regs re-derivation.
    await sql`
      insert into conflict_records (
        ocd_id, observation_a_id, observation_b_id, source_a, source_b,
        conflict_flags, govinfo_url, detected_at, resolved_at,
        conflict_scope, ocd_id_b, govinfo_url_b
      ) values (
        ${OCD_RET}, 'cw-a-1', 'cw-b-1', 'federal_register', 'federal_register',
        ${sql.json(["fr_regs_date_mismatch"])}, null, ${NOW.toISOString()}, null,
        'cross_window', ${OCD_RET_B}, 'https://www.govinfo.gov/content/pkg/FR-2026-01-01/html/2026-00001.htm'
      )
    `;

    // New Regs obs that now AGREES → window no longer conflicting → resolve sweep fires.
    const regsRb = JSON.parse(JSON.stringify(regsR)) as typeof regsR;
    regsRb.data.attributes.commentEndDate = "2026-07-02T03:59:59Z"; // Eastern 07-01 → agrees with FR
    await ingestObservation(sql, {
      ...parseRegsObservation(regsRb),
      fetched_at: "2026-05-02T00:00:00Z",
    });
    await reconcileOcdId(sql, OCD_RET, new Date("2026-06-04T00:00:00Z"));

    const crossSourceOpen = (
      await sql<{ count: string }[]>`
        select count(*)::text as count from conflict_records
        where ocd_id = ${OCD_RET} and resolved_at is null and conflict_scope = 'cross_source'
      `
    )[0]!.count;
    assert(
      "RETIRE-SCOPE: cross_source row was retired by the agreeing re-derive",
      crossSourceOpen === "0",
      crossSourceOpen,
    );
    const crossWindowOpen = (
      await sql<{ count: string }[]>`
        select count(*)::text as count from conflict_records
        where ocd_id = ${OCD_RET} and resolved_at is null and conflict_scope = 'cross_window'
      `
    )[0]!.count;
    assert(
      "RETIRE-SCOPE: the cross_window row (same ocd_id side A) is NOT collaterally retired",
      crossWindowOpen === "1",
      crossWindowOpen,
    );
  }

  // ── 3. EITHER-SIDE filter — a window finds a conflict where it is side B ─────────────────────────────
  // OCD_RET_B is side B of the synthetic cross_window row inserted above. listConflicts filtered by that
  // side-B id must return the row (proving the OR on ocd_id_b). An unrelated id must NOT match the
  // cross_source rows (ocd_id_b='' never equals a real OcdId).
  {
    const bySideB = await listConflicts(sql, { ocdId: OCD_RET_B });
    assert(
      "EITHER-SIDE: filtering by side-B ocd_id returns the cross_window row",
      bySideB.total === 1 &&
        bySideB.rows.length === 1 &&
        bySideB.rows[0]!.ocd_id_b === OCD_RET_B &&
        bySideB.rows[0]!.conflict_scope === "cross_window",
      `total=${bySideB.total} rows=${bySideB.rows.length}`,
    );
    assert(
      "EITHER-SIDE: the matched row names OCD_RET as side A and OCD_RET_B as side B",
      bySideB.rows[0]!.ocd_id === OCD_RET &&
        bySideB.rows[0]!.ocd_id_b === OCD_RET_B,
      `${bySideB.rows[0]?.ocd_id} / ${bySideB.rows[0]?.ocd_id_b}`,
    );

    // An unrelated id must not leak any cross_source row (those have ocd_id_b='').
    const unrelated = await listConflicts(sql, {
      ocdId: "ocd-participation-window/federal/2025-00000",
    });
    assert(
      "EITHER-SIDE: an unrelated id matches nothing (cross_source ocd_id_b='' never equals a real id)",
      unrelated.total === 0 && unrelated.rows.length === 0,
      `total=${unrelated.total}`,
    );

    // The LIVE cross_source dedup row (OCD_DEDUP) is found by its own ocd_id as side A, not as side B.
    const bySideA = await listConflicts(sql, { ocdId: OCD_DEDUP });
    assert(
      "EITHER-SIDE: a cross_source row is found by its own ocd_id (side A)",
      bySideA.total === 1 && bySideA.rows[0]!.ocd_id === OCD_DEDUP,
      `total=${bySideA.total}`,
    );

    // REGRESSION (#31 adversary B1): an EMPTY ocd_id filter must NOT leak the cross_source feed. Because
    // cross_source rows carry the ocd_id_b='' sentinel, a naive `ocd_id_b = $1` with $1='' would match
    // EVERY cross_source row — publishing a foreign, scoped-looking feed (the forbidden "fake certainty").
    // Pre-Slice-1 an empty filter matched nothing (total=0); that honest behavior must be preserved.
    const emptyFilter = await listConflicts(sql, { ocdId: "" });
    assert(
      "EITHER-SIDE: an empty ocd_id filter matches nothing (must NOT leak the '' sentinel rows)",
      emptyFilter.total === 0 && emptyFilter.rows.length === 0,
      `total=${emptyFilter.total} rows=${emptyFilter.rows.length}`,
    );
  }

  // ── 4. READ MAPPING — '' → null round-trip + superRefine passes for BOTH scopes ─────────────────────
  {
    // cross_source (OCD_DEDUP): ocd_id_b parses to null, conflict_scope cross_source — superRefine OK
    // (listConflicts already ConflictRecord.parse'd it, so reaching here means it passed).
    const cs = (await listConflicts(sql, { ocdId: OCD_DEDUP })).rows[0]!;
    assert(
      "READ-MAP: cross_source row maps ocd_id_b='' → null in the parsed ConflictRecord",
      cs.ocd_id_b === null && cs.conflict_scope === "cross_source",
      `ocd_id_b=${String(cs.ocd_id_b)} scope=${cs.conflict_scope}`,
    );
    assert(
      "READ-MAP: cross_source row carries no side-B anchor (govinfo_url_b null)",
      cs.govinfo_url_b === null,
      String(cs.govinfo_url_b),
    );

    // cross_window (OCD_RET_B side B): ocd_id_b present + distinct from ocd_id, govinfo_url_b present.
    const cw = (await listConflicts(sql, { ocdId: OCD_RET_B })).rows[0]!;
    assert(
      "READ-MAP: cross_window row keeps ocd_id_b present (distinct from ocd_id) — superRefine passes",
      cw.ocd_id_b === OCD_RET_B && cw.ocd_id_b !== cw.ocd_id,
      `${cw.ocd_id} / ${String(cw.ocd_id_b)}`,
    );
    assert(
      "READ-MAP: cross_window row carries side-B govinfo anchor",
      cw.govinfo_url_b ===
        "https://www.govinfo.gov/content/pkg/FR-2026-01-01/html/2026-00001.htm",
      String(cw.govinfo_url_b),
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== conflict-plumbing results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
