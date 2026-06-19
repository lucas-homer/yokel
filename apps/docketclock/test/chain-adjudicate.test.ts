/**
 * chain-adjudicate.test.ts — #31 Slice 3b: wiring the LLM adjudicator into the CROSS-WINDOW (chain)
 * reconcile pass. This is the FIRST slice where the LLM can change a classification, so this file proves
 * the NON-NEGOTIABLE safety invariants end-to-end against a throwaway PG18.
 *
 *   • INVARIANT 1 (null adapter = today): chainReconcileOnce with NullAdjudicator over a fixture that
 *     CONTAINS an ambiguous pair persists EXACTLY the confident set — the ambiguous pair is NOT linked.
 *   • PROMOTION (spy affirm): an affirm spy → the ambiguous pair becomes a persisted cross_window conflict
 *     carrying B's type flag(s) + `llm_corroborated`; it shows in listConflicts; the adjudications cache
 *     row exists with the spy's provenance. Second run → consult is CACHED (spy not re-called), same link.
 *   • NO PROMOTION (spy reject / uncertain) → no link; llmLinked=0.
 *   • ERROR ISOLATION: a spy that THROWS → the cycle completes, that pair is not linked, no exception
 *     escapes, and the confident links persist normally alongside.
 *   • CAP: more ambiguous pairs than the cap → only cap-many consulted, the remainder counted as capped.
 *   • COUNTS: the summary reflects ambiguous/escalated/llmLinked/escalationsCapped honestly.
 *
 * The whole file needs the DB; it is SKIPPED (with a notice) when DATABASE_URL is unset. Repo test style:
 * hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import type { AdjudicationInput, AdjudicationVerdict } from "@yokel/contracts";
import { RULEBOOK_VERSION } from "../src/rulebox/index.js";
import type { Adjudicator } from "../src/adjudicator/port.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const NOW = new Date("2026-06-01T00:00:00Z");

/** A counting SPY: returns a FIXED verdict, tallies calls; id is provenance-significant. */
function spyAdjudicator(
  id: string,
  verdict: AdjudicationVerdict,
): Adjudicator & { calls: number } {
  const spy = {
    id,
    calls: 0,
    async adjudicate(_input: AdjudicationInput): Promise<AdjudicationVerdict> {
      spy.calls++;
      return verdict;
    },
  };
  return spy;
}

/** A SPY that THROWS on every call (gemini down / timeout / malformed). */
function throwingAdjudicator(id: string): Adjudicator & { calls: number } {
  const spy = {
    id,
    calls: 0,
    async adjudicate(_input: AdjudicationInput): Promise<AdjudicationVerdict> {
      spy.calls++;
      throw new Error("simulated adjudicator outage");
    },
  };
  return spy;
}

if (!process.env.DATABASE_URL) {
  console.log(
    "\n=== chain-adjudicate results ===\n  (skipped: DATABASE_URL unset — DB-integration only)\nALL EXPECTATIONS MET",
  );
  process.exit(0);
}

const { createClient } = await import("../src/db/client.js");
const { runMigrations } = await import("../src/db/migrate.js");
const { parseFrObservation } =
  await import("../src/sources/federal-register.js");
const { ingestObservation } = await import("../src/ingest/observe.js");
const { reconcileOcdId, chainReconcileOnce } =
  await import("../src/reconcile/persist.js");
const { NullAdjudicator } =
  await import("../src/adjudicator/null-adjudicator.js");
const { listConflicts } = await import("../src/api/queries.js");

const sql = createClient();

/** Ingest an FR doc + reconcile it into a materialized window. */
async function seedWindow(opts: {
  docNum: string;
  docketIds: string[];
  rin: string | null;
  publicationDate: string;
  commentsCloseOn: string;
  action: string;
  title?: string;
  dates: string;
}): Promise<string> {
  const raw: Record<string, unknown> = {
    document_number: opts.docNum,
    type: "Notice",
    action: opts.action,
    title: opts.title ?? `Notice ${opts.docNum}`,
    dates: opts.dates,
    comments_close_on: opts.commentsCloseOn,
    publication_date: opts.publicationDate,
    docket_ids: opts.docketIds,
    regulation_id_number: null,
    regulation_id_numbers: opts.rin ? [opts.rin] : [],
  };
  const cand = parseFrObservation(raw);
  await ingestObservation(sql, cand);
  const ocdId = `ocd-participation-window/federal/${opts.docNum}`;
  await reconcileOcdId(sql, ocdId, NOW);
  return ocdId;
}

/**
 * Reset to a clean schema between scenarios. The observation log is APPEND-ONLY (a DB trigger forbids
 * TRUNCATE/DELETE on observations), so we cannot wipe rows — instead we drop + recreate the schema and
 * re-run migrations, giving each scenario an isolated, empty substrate.
 */
async function reset(): Promise<void> {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
}

/**
 * Seed an AMBIGUOUS A/B pair: same docket, B is an extension published after A (open), but DISJOINT RINs
 * and NO explicit doc-number reference in B's DATES text. The confident path drops this (rule 2 fails); it
 * is surfaced as the single ambiguous pair. Returns [A, B] ocd_ids.
 */
async function seedAmbiguousPair(
  docket: string,
  aDoc: string,
  bDoc: string,
): Promise<[string, string]> {
  const A = await seedWindow({
    docNum: aDoc,
    docketIds: [docket],
    rin: "2040-AAA1", // A's rin
    publicationDate: "2026-05-01",
    commentsCloseOn: "2026-08-01",
    action: "Notice of public comment period.",
    dates: "Comments must be received on or before August 1, 2026.",
  });
  const B = await seedWindow({
    docNum: bDoc,
    docketIds: [docket],
    rin: "2040-ZZZ9", // DISJOINT rin → rule 2 RIN fails
    publicationDate: "2026-05-20",
    commentsCloseOn: "2026-09-15",
    action: "Notice; extension of comment period.",
    // NO doc-number reference to A → rule 2 reference fails too.
    dates:
      "The comment period is extended. Comments now due September 15, 2026.",
  });
  return [A, B];
}

try {
  // ── INVARIANT 1: NullAdjudicator over a fixture WITH an ambiguous pair persists ONLY the confident set.
  {
    await reset(); // also performs the initial schema setup + migrations
    const [, B] = await seedAmbiguousPair(
      "EPA-HQ-AMB-0001",
      "2026-30001",
      "2026-30002",
    );
    const run = await chainReconcileOnce(sql, NOW, {
      adjudicator: new NullAdjudicator(),
    });
    assert(
      "I1 null adapter: ambiguous pair surfaced (ambiguous=1) but NOT linked (linked=0, llmLinked=0, conflictsLive=0)",
      run.ambiguous === 1 &&
        run.linked === 0 &&
        run.llmLinked === 0 &&
        run.conflictsLive === 0,
      JSON.stringify(run),
    );
    const live = await listConflicts(sql, { ocdId: B });
    assert(
      "I1 null adapter: nothing persisted to the live feed (byte-identical to today)",
      live.total === 0,
      String(live.total),
    );
  }

  // ── PROMOTION: affirm spy → the ambiguous pair becomes a cross_window link carrying llm_corroborated.
  {
    await reset();
    const [A, B] = await seedAmbiguousPair(
      "EPA-HQ-AMB-0002",
      "2026-30003",
      "2026-30004",
    );
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "the extension genuinely amends the original",
    });
    const run = await chainReconcileOnce(sql, NOW, { adjudicator: spy });
    assert(
      "P1 affirm: counts honest (ambiguous=1, escalated=1, llmLinked=1, conflictsLive=1, linked=0)",
      run.ambiguous === 1 &&
        run.escalated === 1 &&
        run.llmLinked === 1 &&
        run.conflictsLive === 1 &&
        run.linked === 0,
      JSON.stringify(run),
    );
    assert(
      "P1 affirm: spy consulted exactly once",
      spy.calls === 1,
      String(spy.calls),
    );

    const live = await listConflicts(sql, { ocdId: B });
    assert(
      "P1 affirm: promoted cross_window link shows in listConflicts (A→B)",
      live.total === 1 &&
        live.rows[0]!.ocd_id === A &&
        live.rows[0]!.ocd_id_b === B &&
        live.rows[0]!.conflict_scope === "cross_window",
      `total=${live.total}`,
    );
    assert(
      "P1 affirm: link carries B's type flag (extension_chain_unresolved) AND llm_corroborated",
      live.total === 1 &&
        live.rows[0]!.conflict_flags.includes("extension_chain_unresolved") &&
        live.rows[0]!.conflict_flags.includes("llm_corroborated"),
      live.total === 1 ? live.rows[0]!.conflict_flags.join(",") : "none",
    );

    // The adjudications cache row exists with the spy's provenance (spy:affirm@<rulebook_version>).
    const [cacheRow] = await sql<
      { adjudicator_id: string; verdict: AdjudicationVerdict }[]
    >`
      select adjudicator_id, verdict from adjudications
    `;
    assert(
      "P1 affirm: adjudications cache row persisted with spy provenance + affirm verdict",
      !!cacheRow &&
        cacheRow.adjudicator_id === `spy:affirm@${RULEBOOK_VERSION}` &&
        cacheRow.verdict.classification === "affirm",
      cacheRow ? cacheRow.adjudicator_id : "no row",
    );

    // Second run → consult is CACHED: the spy is NOT re-called, the same link persists.
    const run2 = await chainReconcileOnce(
      sql,
      new Date("2026-06-02T00:00:00Z"),
      {
        adjudicator: spy,
      },
    );
    assert(
      "P1 affirm replay: second run does NOT re-call the spy (content-hash cache hit)",
      spy.calls === 1 && run2.llmLinked === 1 && run2.conflictsLive === 1,
      `calls=${spy.calls} ${JSON.stringify(run2)}`,
    );
    const live2 = await listConflicts(sql, { ocdId: B });
    assert(
      "P1 affirm replay: still exactly one live cross_window link (no duplicate)",
      live2.total === 1,
      String(live2.total),
    );
  }

  // ── NO PROMOTION: reject and uncertain spies → no link.
  for (const cls of ["reject", "uncertain"] as const) {
    await reset();
    const [, B] = await seedAmbiguousPair(
      `EPA-HQ-AMB-${cls}`,
      `2026-31${cls === "reject" ? "001" : "101"}`,
      `2026-31${cls === "reject" ? "002" : "102"}`,
    );
    const spy = spyAdjudicator(`spy:${cls}`, {
      classification: cls,
      rationale: `spy ${cls}`,
    });
    const run = await chainReconcileOnce(sql, NOW, { adjudicator: spy });
    assert(
      `N1 ${cls}: ambiguous=1, escalated=1, but NO link (llmLinked=0, conflictsLive=0)`,
      run.ambiguous === 1 &&
        run.escalated === 1 &&
        run.llmLinked === 0 &&
        run.conflictsLive === 0,
      JSON.stringify(run),
    );
    const live = await listConflicts(sql, { ocdId: B });
    assert(
      `N1 ${cls}: nothing in the live feed`,
      live.total === 0,
      String(live.total),
    );
  }

  // ── ERROR ISOLATION: a throwing spy → cycle completes, the ambiguous pair is not linked, and a SEPARATE
  // confident (fully-corroborated) chain in the SAME cycle still persists normally. No exception escapes.
  {
    await reset();
    // Confident pair (shared RIN) — MUST persist regardless of the adjudicator throwing.
    const Aok = await seedWindow({
      docNum: "2026-32001",
      docketIds: ["EPA-HQ-OK-0001"],
      rin: "2040-OKK1",
      publicationDate: "2026-05-01",
      commentsCloseOn: "2026-08-01",
      action: "Notice of public comment period.",
      dates: "Comments due August 1, 2026.",
    });
    const Bok = await seedWindow({
      docNum: "2026-32002",
      docketIds: ["EPA-HQ-OK-0001"],
      rin: "2040-OKK1", // SAME rin → confident link
      publicationDate: "2026-05-20",
      commentsCloseOn: "2026-09-15",
      action: "Notice; extension of comment period.",
      dates:
        "The comment period is extended. Comments now due September 15, 2026.",
    });
    // Ambiguous pair (disjoint rin) on a DIFFERENT docket — this is the one that escalates and THROWS.
    const [, Bamb] = await seedAmbiguousPair(
      "EPA-HQ-ERR-0001",
      "2026-32101",
      "2026-32102",
    );
    const spy = throwingAdjudicator("spy:throws");
    let threw = false;
    let run: Awaited<ReturnType<typeof chainReconcileOnce>> | undefined;
    try {
      run = await chainReconcileOnce(sql, NOW, { adjudicator: spy });
    } catch {
      threw = true;
    }
    assert(
      "E1 error isolation: chainReconcileOnce does NOT throw when the adjudicator throws",
      !threw && !!run,
    );
    assert(
      "E1 error isolation: confident link persisted; ambiguous (throwing) pair NOT linked",
      !!run &&
        run.linked === 1 &&
        run.ambiguous === 1 &&
        run.escalated === 1 &&
        run.llmLinked === 0 &&
        run.conflictsLive === 1,
      JSON.stringify(run),
    );
    assert(
      "E1 error isolation: the confident chain is live; the throwing pair is absent",
      (await listConflicts(sql, { ocdId: Bok })).total === 1 &&
        (await listConflicts(sql, { ocdId: Bamb })).total === 0,
    );
    assert(
      "E1 error isolation: the failed consult persisted NOTHING to the cache (clean retry)",
      (
        await sql<
          { count: string }[]
        >`select count(*)::text as count from adjudications`
      )[0]!.count === "0",
    );
  }

  // ── CAP: 3 ambiguous pairs, cap=2 → only 2 consulted, 1 counted capped, no crash. With an affirm spy
  // the 2 escalated pairs link; the capped one does not.
  {
    await reset();
    await seedAmbiguousPair("EPA-HQ-CAP-0001", "2026-33001", "2026-33002");
    await seedAmbiguousPair("EPA-HQ-CAP-0002", "2026-33003", "2026-33004");
    await seedAmbiguousPair("EPA-HQ-CAP-0003", "2026-33005", "2026-33006");
    const spy = spyAdjudicator("spy:affirm", {
      classification: "affirm",
      rationale: "affirm",
    });
    const run = await chainReconcileOnce(sql, NOW, {
      adjudicator: spy,
      cap: 2,
    });
    assert(
      "C1 cap=2 over 3 ambiguous: escalated=2, escalationsCapped=1, llmLinked=2 (only cap-many consulted)",
      run.ambiguous === 3 &&
        run.escalated === 2 &&
        run.escalationsCapped === 1 &&
        run.llmLinked === 2 &&
        spy.calls === 2,
      `${JSON.stringify(run)} calls=${spy.calls}`,
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== chain-adjudicate results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
