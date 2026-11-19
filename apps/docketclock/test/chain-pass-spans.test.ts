/**
 * chain-pass-spans.test.ts — the chain pass as an Effect program (src/reconcile/chain-pass.ts, ADR 0018
 * slice 5). The chain SEMANTICS are pinned by chain*.test.ts through the unchanged Promise export; this
 * file pins only what the Effect version adds:
 *   - each step is a child span of the caller's span, in order: SELECT chain candidates → chain.core →
 *     chain.adjudicate → TRANSACTION chain conflicts, with their count attributes;
 *   - a database failure is a typed SqlError in the Effect form, and the Promise form rejects with the
 *     driver's own error (not the wrapper), as before.
 *
 * Needs a THROWAWAY Postgres (the schema is dropped and re-migrated):
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { Effect, Tracer } from "effect";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { NullAdjudicator } from "../src/adjudicator/null-adjudicator.js";
import {
  chainReconcile,
  chainReconcileOnce,
} from "../src/reconcile/chain-pass.js";

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
const parentName = (s: Tracer.NativeSpan) =>
  s.parent._tag === "Some" && "name" in s.parent.value
    ? (s.parent.value as Tracer.NativeSpan).name
    : undefined;

const sql = createClient();

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // ── the step spans, on an empty candidate set ────────────────────────────────────────────────────
  {
    const result = await Effect.runPromise(
      chainReconcile(sql, new Date("2026-11-18T23:00:00Z"), {
        adjudicator: new NullAdjudicator(),
      }).pipe(
        Effect.withSpan("poll.pass.chain"),
        Effect.provideService(Tracer.Tracer, tracer),
      ),
    );
    assert(
      "empty candidate set → empty result",
      result.candidates === 0 &&
        result.linked === 0 &&
        result.conflictsLive === 0,
      JSON.stringify(result),
    );
    const steps = spans
      .filter((s) => parentName(s) === "poll.pass.chain")
      .map((s) => s.name);
    assert(
      "steps are child spans, in order",
      steps.join(" → ") ===
        "SELECT chain candidates → chain.core → chain.adjudicate → TRANSACTION chain conflicts",
      steps.join(" → "),
    );
    const select = spans.find((s) => s.name === "SELECT chain candidates");
    assert(
      "the candidate read is a postgres client span with its row count",
      select?.kind === "client" &&
        select.attributes.get("db.system.name") === "postgresql" &&
        select.attributes.get("db.operation.name") === "SELECT" &&
        select.attributes.get("db.response.returned_rows") === 0,
    );
    const core = spans.find((s) => s.name === "chain.core");
    assert(
      "chain.core carries the engine counts",
      core?.attributes.get("docketclock.chain.candidates") === 0 &&
        core.attributes.get("docketclock.chain.ambiguous") === 0,
    );
    const persist = spans.find((s) => s.name === "TRANSACTION chain conflicts");
    assert(
      "the persist transaction carries live/retired counts",
      persist?.attributes.get("docketclock.chain.live") === 0 &&
        persist.attributes.get("docketclock.chain.retired") === 0,
    );
    assert(
      "every span ended",
      spans.every((s) => s.status._tag === "Ended"),
    );
  }

  // ── a database failure ───────────────────────────────────────────────────────────────────────────
  {
    const dead = createClient();
    await dead.end({ timeout: 1 });
    const exit = await Effect.runPromiseExit(
      chainReconcile(dead, new Date(), { adjudicator: new NullAdjudicator() }),
    );
    const failure =
      exit._tag === "Failure"
        ? (exit.cause.reasons.find((r) => r._tag === "Fail") as
            | { error: { _tag: string; query: string } }
            | undefined)
        : undefined;
    assert(
      "Effect form fails with a typed SqlError naming the query",
      failure?.error._tag === "SqlError" &&
        failure.error.query === "SELECT chain candidates",
      exit._tag,
    );
    let thrown: unknown;
    try {
      await chainReconcileOnce(dead, new Date(), {
        adjudicator: new NullAdjudicator(),
      });
    } catch (err) {
      thrown = err;
    }
    assert(
      "Promise form rejects with the driver's error, not the wrapper",
      thrown instanceof Error &&
        (thrown as { _tag?: string })._tag === undefined,
      String(thrown),
    );
  }
} catch (err) {
  failures++;
  out.push(`  FAIL  unexpected error — ${String(err)}`);
} finally {
  await sql.end({ timeout: 5 });
}

console.log(`chain-pass-spans.test.ts\n${out.join("\n")}`);
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
