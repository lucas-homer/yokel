/**
 * status-refresh.test.ts — the per-cycle status refresh pass (#107, src/reconcile/status-refresh.ts).
 *
 * Proves the load-bearing properties:
 *   • FLIP — an open window whose close passed since its last derivation is re-derived to `closed`
 *     within one pass, without any new observation arriving.
 *   • THE RULEBOOK DECIDES — a window the engine deliberately keeps open past its close (Regs
 *     openForComment=true, the late-comment semantic) matches the scan predicate but re-derives right
 *     back to `open` (counted stillOpen). The pass never forks the open/closed rule.
 *   • SELECTIVE — an open window with a FUTURE close is not scanned (derived_at untouched).
 *   • NO CLOSE MOVEMENT — a pure status flip never bumps `version` or touches change_history
 *     (versionBumped stays 0, the #106 audit posture).
 *   • STEADY-STATE — a second pass re-scans ONLY the deliberate Regs-open churn (the flipped window no
 *     longer matches the predicate) and changes nothing.
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
import { refreshStaleOpenWindows } from "../src/reconcile/status-refresh.js";

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

// Derive everything at T0 (all closes still in the future), then refresh at T1 (close A has passed).
const T0 = new Date("2026-06-01T00:00:00Z");
const T1 = new Date("2026-09-01T00:00:00Z");

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // ── window A: FR-only, closes 2026-06-16 — open at T0, stale-open by T1 ─────────────────────────────
  const OCD_A = "ocd-participation-window/federal/2025-02910";
  await ingestObservation(
    sql,
    parseFrObservation({ ...frFixture, comments_close_on: "2026-06-16" }),
  );
  const a0 = await reconcileOcdId(sql, OCD_A, T0);
  assert(
    "setup: window A derives OPEN at T0 (close still future)",
    a0.window.status === "open",
    a0.window.status,
  );

  // ── window B: FR close 2026-06-16 + Regs openForComment=true (null end date) — the deliberate class ─
  const OCD_B = "ocd-participation-window/federal/2025-88888";
  await ingestObservation(
    sql,
    parseFrObservation({
      ...frFixture,
      document_number: "2025-88888",
      comments_close_on: "2026-06-16",
    }),
  );
  const regsRawB = JSON.parse(
    JSON.stringify(regsFixture),
  ) as typeof regsFixture;
  Object.assign(regsRawB.data.attributes, {
    frDocNum: "2025-88888",
    commentEndDate: null,
    openForComment: true,
    withdrawn: false,
  });
  await ingestObservation(sql, parseRegsObservation(regsRawB));
  const b0 = await reconcileOcdId(sql, OCD_B, T0);
  assert(
    "setup: window B derives OPEN with null_end_date_open_status",
    b0.window.status === "open" &&
      b0.window.conflict_flags.includes("null_end_date_open_status"),
    `${b0.window.status} [${b0.window.conflict_flags.join(",")}]`,
  );

  // ── window C: FR-only, closes 2026-12-31 — open with a FUTURE close, must not be scanned ────────────
  const OCD_C = "ocd-participation-window/federal/2025-77777";
  await ingestObservation(
    sql,
    parseFrObservation({
      ...frFixture,
      document_number: "2025-77777",
      comments_close_on: "2026-12-31",
    }),
  );
  await reconcileOcdId(sql, OCD_C, T0);
  const [cBefore] = await sql<{ derived_at: Date }[]>`
    select derived_at from participation_windows where ocd_id = ${OCD_C}
  `;

  // ── pass #1 at T1: A flips closed, B re-derives back to open, C untouched ───────────────────────────
  const res1 = await refreshStaleOpenWindows(sql, T1);
  assert(
    "PASS 1: scans exactly the two past-close windows",
    res1.scanned === 2,
    JSON.stringify(res1),
  );
  assert(
    "FLIP: one window flipped open → closed",
    res1.closed === 1,
    JSON.stringify(res1),
  );
  assert(
    "RULEBOOK DECIDES: the Regs-open window re-derives back to open (stillOpen)",
    res1.stillOpen === 1,
    JSON.stringify(res1),
  );
  assert(
    "NO CLOSE MOVEMENT: versionBumped 0, failed 0",
    res1.versionBumped === 0 && res1.failed === 0,
    JSON.stringify(res1),
  );

  const [a1] = await sql<
    { status: string; version: number; change_history: unknown[] }[]
  >`
    select status, version, change_history from participation_windows where ocd_id = ${OCD_A}
  `;
  assert("FLIP: window A now persisted closed", a1!.status === "closed");
  assert(
    "NO CLOSE MOVEMENT: A's version 0 + empty change_history after the flip",
    a1!.version === 0 && a1!.change_history.length === 0,
    `version=${a1!.version} history=${a1!.change_history.length}`,
  );

  const [b1] = await sql<{ status: string }[]>`
    select status from participation_windows where ocd_id = ${OCD_B}
  `;
  assert(
    "RULEBOOK DECIDES: window B still persisted open",
    b1!.status === "open",
    b1!.status,
  );

  const [cAfter] = await sql<{ derived_at: Date }[]>`
    select derived_at from participation_windows where ocd_id = ${OCD_C}
  `;
  assert(
    "SELECTIVE: future-close window C untouched (derived_at unchanged)",
    cAfter!.derived_at.getTime() === cBefore!.derived_at.getTime(),
  );

  // ── pass #2 at T1: only the deliberate Regs-open churn remains ──────────────────────────────────────
  const res2 = await refreshStaleOpenWindows(sql, T1);
  assert(
    "STEADY-STATE: second pass re-scans only the Regs-open window, flips nothing",
    res2.scanned === 1 &&
      res2.closed === 0 &&
      res2.stillOpen === 1 &&
      res2.failed === 0,
    JSON.stringify(res2),
  );
} finally {
  await sql.end();
}

console.log("\n=== status-refresh results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
