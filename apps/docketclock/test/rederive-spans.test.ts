/**
 * rederive-spans.test.ts — the status refresh and amended-originals passes as Effect programs, and one
 * window's derivation as an Effect with a span per step (ADR 0018 slice 5b). The SEMANTICS are pinned by
 * status-refresh / amendment-persist / reconcile tests through the unchanged Promise exports; this file
 * pins only what the Effect versions add:
 *   - statusRefresh: SELECT stale open windows, then one reconcile.window per stale window;
 *   - reconcile.window: SELECT observations → reconcile.amendment_inputs → reconcile.core →
 *     TRANSACTION reconciliation, with the loader's own queries nested under amendment_inputs;
 *   - a window with no observations is a WindowFailure naming its step, isolated per row, and the
 *     Promise reconcileOcdId still rejects with the same Error message as before;
 *   - amendedOriginals: SELECT chain originals, a typed SqlError when that read fails.
 *
 * Needs a THROWAWAY Postgres (the schema is dropped and re-migrated):
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Effect, Tracer } from "effect";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import {
  reconcileWindow,
  WindowFailure,
} from "../src/reconcile/reconcile-window.js";
import {
  amendedOriginals,
  rederiveWindows,
} from "../src/reconcile/rederive.js";
import { statusRefresh } from "../src/reconcile/status-refresh.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const spans: Tracer.NativeSpan[] = [];
const tracer = Tracer.make({
  span(options) {
    const span = new Tracer.NativeSpan(options);
    spans.push(span);
    return span;
  },
});
const parentOf = (s: Tracer.NativeSpan) =>
  s.parent._tag === "Some" && "name" in s.parent.value
    ? (s.parent.value as Tracer.NativeSpan)
    : undefined;
const childrenOf = (p: Tracer.NativeSpan) =>
  spans.filter((s) => parentOf(s) === p).map((s) => s.name);
const traced = <A, E>(name: string, effect: Effect.Effect<A, E>) =>
  effect.pipe(
    Effect.withSpan(name),
    Effect.provideService(Tracer.Tracer, tracer),
  );

const HERE = dirname(fileURLToPath(import.meta.url));
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;
const T0 = new Date("2026-06-01T00:00:00Z");
const T1 = new Date("2026-09-01T00:00:00Z");
const OCD_A = "ocd-participation-window/federal/2025-02910";
const MISSING = "ocd-participation-window/federal/2099-00000";

const sql = createClient();
try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  await ingestObservation(
    sql,
    parseFrObservation({
      ...frFixture,
      publication_date: "2026-05-01",
      comments_close_on: "2026-06-16",
    }),
  );
  await reconcileOcdId(sql, OCD_A, T0); // open at T0; stale-open by T1

  // ── statusRefresh: the scan, then one reconcile.window per stale window ─────────────────────────
  {
    spans.length = 0;
    const summary = await Effect.runPromise(
      traced("poll.pass.status_refresh", statusRefresh(sql, T1)),
    );
    assert(
      "status refresh flips the stale window closed",
      summary.scanned === 1 && summary.closed === 1 && summary.failed === 0,
      JSON.stringify(summary),
    );
    const passSpan = spans.find((s) => s.name === "poll.pass.status_refresh")!;
    assert(
      "pass children: the scan, then one window",
      childrenOf(passSpan).join(" → ") ===
        "SELECT stale open windows → reconcile.window",
      childrenOf(passSpan).join(" → "),
    );
    const scan = spans.find((s) => s.name === "SELECT stale open windows")!;
    assert(
      "the scan is a postgres client span with its row count",
      scan.kind === "client" &&
        scan.attributes.get("db.system.name") === "postgresql" &&
        scan.attributes.get("db.response.returned_rows") === 1,
    );
    const win = spans.find((s) => s.name === "reconcile.window")!;
    assert(
      "the window span carries its ocd_id",
      win.attributes.get("docketclock.ocd_id") === OCD_A,
    );
    assert(
      "window steps, in order",
      childrenOf(win).join(" → ") ===
        "SELECT observations → reconcile.amendment_inputs → reconcile.core → TRANSACTION reconciliation",
      childrenOf(win).join(" → "),
    );
    const inputs = spans.find((s) => s.name === "reconcile.amendment_inputs")!;
    const loaderQueries = childrenOf(inputs);
    assert(
      "the amendment loader's own queries nest under reconcile.amendment_inputs",
      loaderQueries[0] === "SELECT latest FR observation" &&
        loaderQueries.includes("SELECT amendment corpus stamp"),
      loaderQueries.join(", "),
    );
    const core = spans.find((s) => s.name === "reconcile.core")!;
    assert(
      "reconcile.core carries the derived status",
      core.attributes.get("docketclock.window.status") === "closed",
      String(core.attributes.get("docketclock.window.status")),
    );
    const tx = spans.find((s) => s.name === "TRANSACTION reconciliation")!;
    assert(
      "the persist transaction records whether the close moved",
      tx.attributes.get("docketclock.window.version_bumped") === false,
    );
  }

  // ── a window with no observations: a typed failure, isolated per row ─────────────────────────────
  {
    spans.length = 0;
    const r = await Effect.runPromise(
      Effect.result(traced("t", reconcileWindow(sql, MISSING, T1))),
    );
    assert(
      "no observations → WindowFailure naming the step",
      r._tag === "Failure" &&
        r.failure instanceof WindowFailure &&
        r.failure.step === "SELECT observations",
    );
    const win = spans.find((s) => s.name === "reconcile.window")!;
    assert(
      "the failed window's span names the failed step",
      win.attributes.get("docketclock.failed_step") === "SELECT observations",
    );

    const rows = await Effect.runPromise(
      rederiveWindows(sql, [MISSING, OCD_A], T1),
    );
    assert(
      "rederiveWindows isolates the failure and continues",
      rows.length === 2 &&
        rows[0]!.error ===
          `reconcileOcdId: no observations for ocd_id "${MISSING}"` &&
        rows[1]!.error === null,
      JSON.stringify(rows),
    );

    let thrown: unknown;
    try {
      await reconcileOcdId(sql, MISSING, T1);
    } catch (err) {
      thrown = err;
    }
    assert(
      "the Promise form rejects with the same plain Error as before",
      thrown instanceof Error &&
        !(thrown instanceof WindowFailure) &&
        thrown.message ===
          `reconcileOcdId: no observations for ocd_id "${MISSING}"`,
      String(thrown),
    );
  }

  // ── amendedOriginals: the originals read, then the windows (none here) ───────────────────────────
  {
    spans.length = 0;
    const r = await Effect.runPromise(
      traced("poll.pass.amended_originals", amendedOriginals(sql, T1)),
    );
    assert(
      "no live links → nothing to re-derive",
      r.scanned === 0 && r.versionBumped === 0 && r.failed === 0,
      JSON.stringify(r),
    );
    const passSpan = spans.find(
      (s) => s.name === "poll.pass.amended_originals",
    )!;
    assert(
      "pass children: the originals read",
      childrenOf(passSpan).join(" → ") === "SELECT chain originals",
      childrenOf(passSpan).join(" → "),
    );

    await sql`alter table conflict_records rename to conflict_records_gone`;
    const failed = await Effect.runPromise(
      Effect.result(amendedOriginals(sql, T1)),
    );
    await sql`alter table conflict_records_gone rename to conflict_records`;
    assert(
      "a failed originals read is a typed SqlError",
      failed._tag === "Failure" &&
        failed.failure._tag === "SqlError" &&
        failed.failure.query === "SELECT chain originals",
    );
  }
} finally {
  await sql.end();
}

console.log("rederive-spans.test.ts");
console.log(out.join("\n"));
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
