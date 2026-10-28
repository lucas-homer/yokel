/**
 * amendment-persist.test.ts — the amended FR close end-to-end against a THROWAWAY Postgres (ADR 0016;
 * docs/plans/fr-amendment-linking.md parts 1 + 5). The recorded production observation log
 * (test/fixtures/fr-amendments/stored) is loaded VERBATIM (same observation ids), then:
 *
 *   • loadAmendmentEvidence (the SQL prefilter + pure selection) resolves each window;
 *   • govinfoSweepOnce fetches GovInfo text for the amendment documents — candidates, newest first,
 *     per-cycle cap, 404 = retried next cycle, lookback + "published by Eastern today" bounds,
 *     append-only (a re-run finds nothing), each page on the amendment's own ocd_id;
 *   • chainReconcileOnce + rederiveChainOriginals (the v2.4 trigger) move USDA and IRS in the SAME
 *     cycle the text lands (version bump + change_history; their cross_source conflicts retire);
 *   • EVERY derivation path passes the same amendment outcome: a SUBSEQUENT Regs ingest on A (the
 *     poller's reconcileOcdId) keeps the amended derivation — it does not flip back — and so do the
 *     rederive sweep, the status refresh and the review CLI's blind derivation;
 *   • every other recorded window is exactly the pure v2.3 derivation.
 *
 * Run: DATABASE_URL=postgres://… pnpm --filter @yokel/docketclock exec tsx test/amendment-persist.test.ts
 * (drops + recreates the public schema — point it ONLY at a throwaway database).
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { NullAdjudicator } from "../src/adjudicator/null-adjudicator.js";
import {
  chainReconcileOnce,
  loadAmendmentEvidence,
  loadObservations,
  reconcileOcdId,
  rederiveChainOriginals,
} from "../src/reconcile/persist.js";
import { RECONCILER_VERSION, reconcile } from "../src/reconcile/reconcile.js";
import { rederiveStaleWindows } from "../src/db/rederive-stale-windows.js";
import { refreshStaleOpenWindows } from "../src/reconcile/status-refresh.js";
import { reviewShow } from "../src/review/core.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import {
  govinfoHtmlUrl,
  govinfoSweepOnce,
  parseGovinfoObservation,
  stripNul,
} from "../src/sources/govinfo.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { payloadHash } from "../src/sources/payload.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const FIX = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "fr-amendments",
);
const stored = JSON.parse(
  readFileSync(join(FIX, "stored", "observations.json"), "utf8"),
) as Observation[];
const govHtml = (doc: string) =>
  readFileSync(join(FIX, "govinfo", `${doc}.htm`), "utf8");
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;
const NOW = new Date("2026-10-27T12:00:00Z");

const CENSUS = ocd("2026-18481");
const USDA = ocd("2026-18531");
const IRS = ocd("2026-18574");
const AMENDED = [CENSUS, USDA, IRS];

interface WindowRow {
  ocd_id: string;
  confidence: string;
  conflict_flags: string[];
  resolved_close_utc: Date | null;
  raw_fr_close_date: string | null;
  version: number;
  change_history: unknown[];
  current_observation_ids: string[];
  reconciler_version: string;
}

if (!process.env.DATABASE_URL) {
  console.log("SKIP amendment-persist.test.ts — DATABASE_URL not set");
  process.exit(0);
}

const sql = createClient();
async function win(ocdId: string): Promise<WindowRow> {
  const [w] = await sql<WindowRow[]>`
    select ocd_id, confidence, conflict_flags, resolved_close_utc, raw_fr_close_date, version,
           change_history, current_observation_ids, reconciler_version
    from participation_windows where ocd_id = ${ocdId}
  `;
  return w!;
}
const iso = (d: Date | null) => (d ? d.toISOString() : null);

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // ── load the recorded log VERBATIM (same ids — this is the production state) ──────────────────────
  for (const o of stored) {
    await sql`
      insert into observations
        (observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
         payload_hash, fetched_at, parser_version, raw_dates_text,
         is_extension, is_correction, is_withdrawal, is_reopening, raw)
      values
        (${o.observation_id}, ${o.ocd_id}, ${o.source}, ${o.fr_document_number},
         ${o.regs_document_id}, ${o.regs_object_id}, ${o.payload_hash}, ${o.fetched_at},
         ${o.parser_version}, ${o.raw_dates_text}, ${o.is_extension}, ${o.is_correction},
         ${o.is_withdrawal}, ${o.is_reopening}, ${sql.json(o.raw as never)})
    `;
    await sql`
      insert into observation_targets (observation_id, ocd_id)
      values (${o.observation_id}, ${o.ocd_id}) on conflict do nothing
    `;
  }
  const ocdIds = [...new Set(stored.map((o) => o.ocd_id))].sort();
  for (const id of ocdIds) await reconcileOcdId(sql, id, NOW);

  // ── before any GovInfo text: only Census (its FR dates + close agree) is amended ──────────────────
  const census0 = await loadAmendmentEvidence(sql, CENSUS);
  assert(
    "loader: Census → amended 2026-11-02 via docket_rin",
    census0.kind === "amended" &&
      census0.date === "2026-11-02" &&
      census0.amendment.basis === "docket_rin",
    JSON.stringify(census0),
  );
  assert(
    "loader: USDA without GovInfo text → none",
    (await loadAmendmentEvidence(sql, USDA)).kind === "none",
  );
  assert(
    "loader: IRS without the published correction → none",
    (await loadAmendmentEvidence(sql, IRS)).kind === "none",
  );
  assert(
    "loader: USCG 17216 (reopening 19895 linked by citation) → ambiguous",
    (await loadAmendmentEvidence(sql, ocd("2026-17216"))).kind === "ambiguous",
  );
  for (const doc of ["2026-20660", "2026-18134", "2026-08068", "2026-10969"])
    assert(
      `loader: ${doc} → none`,
      (await loadAmendmentEvidence(sql, ocd(doc))).kind === "none",
    );
  const c0 = await win(CENSUS);
  assert(
    "Census window after first derivation: HIGH + fr_close_amended, v2.4",
    c0.confidence === "high" &&
      c0.conflict_flags.includes("fr_close_amended") &&
      c0.reconciler_version === RECONCILER_VERSION &&
      RECONCILER_VERSION === "reconcile-v2.4",
    JSON.stringify(c0.conflict_flags),
  );
  const usda0 = await win(USDA);
  const irs0 = await win(IRS);
  assert(
    "USDA and IRS still CONFLICTING before their text arrives",
    usda0.confidence === "conflicting" && irs0.confidence === "conflicting",
  );

  // ── the GovInfo sweep ─────────────────────────────────────────────────────────────────────────────
  const fetched: string[] = [];
  let missing = new Set(["2026-19895"]);
  const fetchHtml = async (pub: string, doc: string) => {
    fetched.push(`${pub}/${doc}`);
    if (missing.has(doc)) return null;
    return govHtml(doc);
  };
  const noSleep = async () => {};

  const bounded = await govinfoSweepOnce(sql, NOW, {
    cap: 0,
    lookbackDays: 25,
    fetchHtml,
    sleep: noSleep,
  });
  assert(
    "sweep: the lookback bounds candidates (25 days → only 20328, published 10-05)",
    bounded.candidates === 1 && bounded.fetched === 0 && fetched.length === 0,
    JSON.stringify(bounded),
  );
  const early = await govinfoSweepOnce(sql, new Date("2026-09-27T12:00:00Z"), {
    cap: 0,
    fetchHtml,
    sleep: noSleep,
  });
  assert(
    "sweep: nothing published after Eastern today is a candidate (C1 is dated 09-28; fetched 09-26)",
    early.candidates === 1,
    JSON.stringify(early),
  );

  const s1 = await govinfoSweepOnce(sql, NOW, {
    cap: 2,
    fetchHtml,
    sleep: noSleep,
  });
  assert(
    "sweep 1: 4 amendment candidates (incl. the fr-v2 C1 row via correction_of), newest first, capped at 2; a 404 28 days after publication is a recorded failure",
    s1.candidates === 4 &&
      s1.fetched === 2 &&
      s1.ingested === 1 &&
      s1.notPublished === 0 &&
      s1.failed === 1 &&
      fetched.join() === "2026-10-05/2026-20328,2026-09-29/2026-19895",
    `${JSON.stringify(s1)} ${fetched.join()}`,
  );
  missing = new Set();
  const s2 = await govinfoSweepOnce(sql, NOW, { fetchHtml, sleep: noSleep });
  assert(
    "sweep 2: the failed document is retried AFTER the never-failed ones; the backlog lands",
    s2.candidates === 3 &&
      s2.fetched === 3 &&
      s2.ingested === 3 &&
      fetched.slice(2).join() ===
        "2026-09-28/C1-2026-18574,2026-09-25/2026-19710,2026-09-29/2026-19895",
    `${JSON.stringify(s2)} ${fetched.slice(2).join()}`,
  );
  assert(
    "sweep 2: the recovered document's ledger row is cleared",
    (await sql`select 1 from poll_dead_letter where source = 'govinfo'`)
      .length === 0,
  );
  const s3 = await govinfoSweepOnce(sql, NOW, { fetchHtml, sleep: noSleep });
  assert(
    "sweep 3: append-only — nothing left to fetch",
    s3.candidates === 0 && s3.fetched === 0,
    JSON.stringify(s3),
  );
  const govRows = await sql<
    { ocd_id: string; parser_version: string; raw_dates_text: string | null }[]
  >`
    select ocd_id, parser_version, raw_dates_text from observations
    where source = 'govinfo' order by ocd_id
  `;
  assert(
    "sweep: one govinfo-v1 row per amendment, on the amendment's own ocd_id",
    govRows.length === 4 &&
      govRows.every((r) => r.parser_version === "govinfo-v1") &&
      govRows.map((r) => r.ocd_id).join() ===
        [
          ocd("2026-19710"),
          ocd("2026-19895"),
          ocd("2026-20328"),
          ocd("C1-2026-18574"),
        ].join(),
  );
  assert(
    "sweep: C1's row holds the correction instruction (isCorrection derived from correction_of)",
    govRows
      .find((r) => r.ocd_id === ocd("C1-2026-18574"))!
      .raw_dates_text?.includes("should read ``October 26, 2026''") === true,
  );
  assert(
    "sweep: the original windows are untouched until the chain trigger runs",
    (await win(USDA)).confidence === "conflicting" &&
      (await win(IRS)).confidence === "conflicting",
  );

  // ── chain pass + the v2.4 trigger ─────────────────────────────────────────────────────────────────
  const chain = await chainReconcileOnce(sql, NOW, {
    adjudicator: new NullAdjudicator(),
  });
  const links = await sql<{ ocd_id: string; ocd_id_b: string }[]>`
    select ocd_id, ocd_id_b from conflict_records
    where conflict_scope = 'cross_window' and resolved_at is null order by ocd_id
  `;
  const linkSet = links.map((l) => `${l.ocd_id}→${l.ocd_id_b}`);
  assert(
    "chain: Census, USDA (citation), IRS (correction_of) and USCG are confident cross_window links",
    chain.linked === 4 &&
      linkSet.includes(`${IRS}→${ocd("C1-2026-18574")}`) &&
      linkSet.includes(`${USDA}→${ocd("2026-19710")}`) &&
      linkSet.includes(`${CENSUS}→${ocd("2026-20328")}`),
    linkSet.join(" "),
  );
  const trig = await rederiveChainOriginals(sql, NOW);
  // The CONFLICTING window already carried the portal instant as its (disputed) close, so the amended
  // FR side changes the confidence, not resolved_close_utc — no version bump is the correct outcome.
  assert(
    "trigger: re-derives the 4 confident originals (no close moves: the portal instant was already carried)",
    trig.scanned === 4 && trig.versionBumped === 0 && trig.failed === 0,
    JSON.stringify(trig),
  );
  const trig2 = await rederiveChainOriginals(sql, NOW);
  assert(
    "trigger: idempotent — a second run is a no-op refresh",
    trig2.scanned === 4 && trig2.versionBumped === 0 && trig2.failed === 0,
  );

  const usdaGov = await sql<{ observation_id: string }[]>`
    select observation_id from observations where source = 'govinfo' and ocd_id = ${ocd("2026-19710")}
  `;
  for (const [id, close, raw] of [
    [CENSUS, "2026-11-03T04:59:59.000Z", "2026-10-13"],
    [USDA, "2026-11-03T04:59:59.000Z", "2026-10-13"],
    [IRS, "2026-10-27T03:59:59.000Z", "2026-10-16"],
  ] as const) {
    const w = await win(id);
    assert(
      `${id.slice(-10)}: HIGH + fr_close_amended, close ${close}, raw_fr_close_date ${raw}`,
      w.confidence === "high" &&
        w.conflict_flags.includes("fr_close_amended") &&
        iso(w.resolved_close_utc) === close &&
        w.raw_fr_close_date === raw,
      `${w.confidence} ${JSON.stringify(w.conflict_flags)} ${iso(w.resolved_close_utc)} ${w.raw_fr_close_date}`,
    );
    const live = await sql`
      select 1 from conflict_records
      where ocd_id = ${id} and conflict_scope = 'cross_source' and resolved_at is null
    `;
    assert(
      `${id.slice(-10)}: its cross_source conflict is retired`,
      live.length === 0,
    );
  }
  const usda1 = await win(USDA);
  const usdaFr = stored.find(
    (o) => o.ocd_id === ocd("2026-19710") && o.source === "federal_register",
  )!;
  assert(
    "USDA: same operative instant (version unchanged); provenance names the amendment's FR + govinfo ids",
    usda1.version === usda0.version &&
      usda1.current_observation_ids.includes(usdaFr.observation_id) &&
      usda1.current_observation_ids.includes(usdaGov[0]!.observation_id),
  );

  // Every other recorded window: exactly the pure v2.3 derivation.
  const drift: string[] = [];
  for (const id of ocdIds) {
    if (AMENDED.includes(id)) continue;
    const pure = reconcile(await loadObservations(sql, id), NOW).window;
    const w = await win(id);
    if (
      w.confidence !== pure.confidence ||
      JSON.stringify(w.conflict_flags) !==
        JSON.stringify(pure.conflict_flags) ||
      iso(w.resolved_close_utc) !== pure.resolved_close_utc
    )
      drift.push(id);
  }
  assert(
    "every other recorded window equals the un-amended derivation",
    drift.length === 0,
    drift.join(","),
  );

  // ── EVERY derivation path keeps the amended window ────────────────────────────────────────────────
  // (1) The next Regs poll on A: a fresh Regs payload (modifyDate moved) through ingest + reconcileOcdId,
  // exactly the poller's path. Before v2.4's wiring this flipped A straight back to CONFLICTING.
  for (const id of [IRS, USDA, CENSUS]) {
    const lastRegs = stored
      .filter((o) => o.ocd_id === id && o.source === "regulations_gov")
      .at(-1)!;
    const raw = JSON.parse(JSON.stringify(lastRegs.raw)) as {
      data: { attributes: Record<string, unknown> };
    };
    raw.data.attributes.modifyDate = "2026-10-27T11:00:00Z";
    const ing = await ingestObservation(sql, parseRegsObservation(raw));
    const r = await reconcileOcdId(sql, id, NOW);
    assert(
      `next Regs poll on ${id.slice(-10)}: still HIGH + fr_close_amended, close unmoved`,
      ing.inserted &&
        r.window.confidence === "high" &&
        r.window.conflict_flags.includes("fr_close_amended") &&
        !r.persist.versionBumped,
      `${r.window.confidence} ${JSON.stringify(r.window.conflict_flags)}`,
    );
  }
  // (2) The rederive sweep.
  await sql`update participation_windows set reconciler_version = 'reconcile-v2.3'`;
  const sweep = await rederiveStaleWindows(sql, NOW);
  assert(
    "rederive sweep: every window re-derived, no close moved, amended windows keep their flag",
    sweep.scanned === ocdIds.length &&
      sweep.versionBumped === 0 &&
      sweep.failed === 0 &&
      (await win(IRS)).conflict_flags.includes("fr_close_amended"),
    JSON.stringify(sweep),
  );
  // (3) The status refresh — IRS's amended close (Oct 26 ET) has passed; the portal still reads open.
  const refresh = await refreshStaleOpenWindows(sql, NOW);
  const irsAfter = await win(IRS);
  assert(
    "status refresh: re-derives IRS (close passed) and keeps the amended derivation",
    refresh.scanned >= 1 &&
      refresh.versionBumped === 0 &&
      irsAfter.confidence === "high" &&
      irsAfter.conflict_flags.includes("fr_close_amended"),
    JSON.stringify(refresh),
  );
  // (4) The review CLI's blind derivation asks the engine the same question.
  const blind = await reviewShow(sql, USDA, { blind: true, now: NOW });
  const bw = blind.window as { confidence?: string; conflict_flags?: string[] };
  assert(
    "review show --blind: derives the amended window (same log in, same window out)",
    bw?.confidence === "high" &&
      (bw.conflict_flags ?? []).includes("fr_close_amended"),
    JSON.stringify(bw?.conflict_flags),
  );

  // ══ NUL BYTES — real GPO pages carry U+0000 page-break artifacts (2026-10-27 replay: 49/717) ══════
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  /** A minimal FR amendment observation (the sweep's candidate source). */
  const frAmendment = (doc: string, pub: string, extra: object = {}) =>
    parseFrObservation({
      document_number: doc,
      publication_date: pub,
      type: "Notice",
      title: `Synthetic notice ${doc}; Extension of Comment Period`,
      action: "Notice; extension of comment period.",
      dates: null,
      docket_ids: [`DOCKET-${doc}`],
      regulation_id_numbers: [],
      citation: null,
      ...extra,
    });
  const nulPages: Record<string, string> = {
    "2026-14439": govHtml("2026-14439"),
    "2026-13404": govHtml("2026-13404"),
  };
  assert(
    "fixture: the real pages carry NULs (4 and 18)",
    (nulPages["2026-14439"]!.match(/\u0000/g) ?? []).length === 4 &&
      (nulPages["2026-13404"]!.match(/\u0000/g) ?? []).length === 18,
  );
  // The hazard itself: an unnormalized page cannot be stored at all.
  let pgError = "";
  try {
    await sql`select ${sql.json({ html: nulPages["2026-13404"] } as never)}::jsonb`;
  } catch (err) {
    pgError = err instanceof Error ? err.message : String(err);
  }
  assert(
    "hazard: Postgres rejects U+0000 in JSONB (why the page is normalized)",
    /unsupported Unicode escape sequence/i.test(pgError),
    pgError,
  );
  const NUL_NOW = new Date("2026-07-20T12:00:00Z");
  await ingestObservation(sql, frAmendment("2026-14439", "2026-07-17"));
  await ingestObservation(sql, frAmendment("2026-13404", "2026-07-02"));
  // A NUL-bearing CORRECTION page: the C1 correction with NULs where GPO puts them (line starts).
  const nulCorrection = govHtml("C1-2026-18574")
    .replace("\n    In proposed rule", "\n\u0000\u0000    In proposed rule")
    .replace("[FR Doc No:", "\u0000[FR Doc No:");
  await ingestObservation(
    sql,
    frAmendment("C9-2026-14439", "2026-07-18", {
      title: "Synthetic rule",
      action: null,
      correction_of:
        "https://www.federalregister.gov/api/v1/documents/2026-14439",
    }),
  );
  const nulFetch = async (_pub: string, doc: string) =>
    doc === "C9-2026-14439" ? nulCorrection : (nulPages[doc] ?? null);
  const nul = await govinfoSweepOnce(sql, NUL_NOW, {
    fetchHtml: nulFetch,
    sleep: noSleep,
  });
  assert(
    "NUL pages ingest (no 'unsupported Unicode escape sequence')",
    nul.candidates === 3 && nul.ingested === 3 && nul.failed === 0,
    JSON.stringify(nul),
  );
  const nulRows = await sql<
    {
      fr_document_number: string;
      raw: { html: string };
      payload_hash: string;
      raw_dates_text: string | null;
    }[]
  >`
    select fr_document_number, raw, payload_hash, raw_dates_text
    from observations where source = 'govinfo' order by fr_document_number
  `;
  const byDoc = new Map(nulRows.map((r) => [r.fr_document_number, r]));
  assert(
    "NUL pages: stored html is the page minus U+0000 (no other change)",
    byDoc.get("2026-13404")!.raw.html === stripNul(nulPages["2026-13404"]!) &&
      byDoc.get("2026-14439")!.raw.html === stripNul(nulPages["2026-14439"]!) &&
      !nulRows.some((r) => r.raw.html.includes("\u0000")),
  );
  const reparse = (html: string) =>
    parseGovinfoObservation({
      frDocNum: "2026-13404",
      publicationDate: "2026-07-02",
      url: govinfoHtmlUrl("2026-07-02", "2026-13404"),
      html,
      isCorrection: false,
    }).payload_hash;
  assert(
    "NUL pages: payload_hash is over the NORMALIZED raw (deterministic; equals a NUL-free fetch)",
    byDoc.get("2026-13404")!.payload_hash ===
      reparse(nulPages["2026-13404"]!) &&
      byDoc.get("2026-13404")!.payload_hash ===
        reparse(stripNul(nulPages["2026-13404"]!)) &&
      byDoc.get("2026-13404")!.payload_hash ===
        payloadHash(
          (
            await sql<{ raw: unknown }[]>`
              select raw from observations
              where source = 'govinfo' and fr_document_number = '2026-13404'
            `
          )[0]!.raw,
        ),
  );
  assert(
    "NUL page DATES extraction (2026-13404, NULs at line starts before DATES)",
    byDoc.get("2026-13404")!.raw_dates_text ===
      "Submit comments on or before August 31, 2026.",
    JSON.stringify(byDoc.get("2026-13404")!.raw_dates_text),
  );
  assert(
    "NUL page DATES extraction (2026-14439, 1.2 MB rule with running-head NULs)",
    byDoc
      .get("2026-14439")!
      .raw_dates_text?.startsWith(
        "This rule has been classified as a major rule",
      ) === true &&
      byDoc
        .get("2026-14439")!
        .raw_dates_text?.endsWith("terminate the rule.") === true,
    JSON.stringify(byDoc.get("2026-14439")!.raw_dates_text),
  );
  assert(
    "NUL correction page: the line-anchored correction body is still found",
    byDoc
      .get("C9-2026-14439")!
      .raw_dates_text?.startsWith("In proposed rule document 2026-18574") ===
      true &&
      byDoc
        .get("C9-2026-14439")!
        .raw_dates_text?.includes("should read ``October 26, 2026''") === true,
    JSON.stringify(byDoc.get("C9-2026-14439")!.raw_dates_text),
  );

  // ══ STARVATION — more than `cap` permanently failing candidates ahead of a good one ════════════
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
  const ST_NOW = new Date("2026-10-27T12:00:00Z");
  const CAP = 50;
  const BAD = 60; // > CAP, all NEWER than the good one, so newest-first alone would starve it forever
  const bad = Array.from(
    { length: BAD },
    (_, i) => `2026-9${String(i).padStart(4, "0")}`,
  );
  for (const [i, doc] of bad.entries())
    // Half answer 404 long after publication, half fail at ingest-like errors — both permanent.
    await ingestObservation(
      sql,
      frAmendment(doc, i % 2 === 0 ? "2026-10-20" : "2026-10-19"),
    );
  const GOOD = "2026-80000";
  const NEW_GOOD = "2026-80002"; // arrives after every bad doc is dead-lettered
  await ingestObservation(sql, frAmendment(GOOD, "2026-10-01"));
  const today = "2026-10-27";
  const FRESH_404 = "2026-80001"; // published today: a 404 is normal, never recorded
  await ingestObservation(sql, frAmendment(FRESH_404, today));
  const calls: string[][] = [];
  let cycle: string[] = [];
  const goodHtml = govHtml("2026-20328");
  const starveFetch = async (_pub: string, doc: string) => {
    cycle.push(doc);
    if (doc === GOOD || doc === NEW_GOOD) return goodHtml;
    if (doc === FRESH_404) return null;
    const i = bad.indexOf(doc);
    if (i % 2 === 0) return null; // permanent 404
    throw new Error(`synthetic permanent failure for ${doc}`);
  };
  const runCycle = async (at: Date) => {
    cycle = [];
    const r = await govinfoSweepOnce(sql, at, {
      cap: CAP,
      fetchHtml: starveFetch,
      sleep: noSleep,
    });
    calls.push(cycle);
    return r;
  };
  const c1 = await runCycle(ST_NOW);
  assert(
    "starvation c1: newest-first fills the cap with failing docs (the good one is older) — bounded so far",
    c1.fetched === CAP && !calls[0]!.includes(GOOD) && c1.failed === CAP - 1,
    JSON.stringify(c1),
  );
  assert(
    "starvation c1: the same-day 404 is 'not published yet' — no ledger row",
    c1.notPublished === 1 &&
      (
        await sql`select 1 from poll_dead_letter where document_key = ${FRESH_404}`
      ).length === 0,
  );
  const c2 = await runCycle(ST_NOW);
  assert(
    "starvation c2: never-failed candidates outrank failed ones → the good document IS fetched (≤ 2 cycles)",
    calls[1]!.includes(GOOD) && c2.ingested === 1,
    `${JSON.stringify(c2)} goodAt=${calls[1]!.indexOf(GOOD)}`,
  );
  // Keep cycling: every bad doc is dead-lettered after 3 consecutive failures and leaves the hot set.
  let deadLettered = c1.deadLettered + c2.deadLettered;
  for (let k = 0; k < 4; k++)
    deadLettered += (await runCycle(ST_NOW)).deadLettered;
  const [dlRow] = await sql<{ n: number }[]>`
    select count(*)::int as n from poll_dead_letter
    where source = 'govinfo' and dead_lettered_at is not null
  `;
  const dl = dlRow!.n;
  assert(
    "starvation: every permanently failing doc is dead-lettered (bounded cycles); the fresh 404 is not",
    dl === BAD && deadLettered === BAD,
    `dl=${dl} newly=${deadLettered}`,
  );
  const quiet = await runCycle(ST_NOW);
  assert(
    "dead-lettered docs leave the hot set: only the fresh same-day 404 is fetched",
    quiet.fetched === 1 &&
      quiet.deadLetterSkipped === BAD &&
      calls.at(-1)!.join() === FRESH_404,
    JSON.stringify(quiet),
  );
  await ingestObservation(sql, frAmendment(NEW_GOOD, "2026-10-25"));
  const next = await runCycle(ST_NOW);
  assert(
    "a newly arriving good candidate is fetched on its FIRST cycle",
    calls.at(-1)!.includes(NEW_GOOD) && next.ingested === 1,
    JSON.stringify(next),
  );
  const drain = await runCycle(new Date(ST_NOW.getTime() + 25 * 3_600_000));
  assert(
    "slow drain: 24h later the dead-letters are re-attempted once (capped), behind every fresh candidate",
    drain.deadLetterRetried === CAP - 1 &&
      calls.at(-1)![0] === FRESH_404 &&
      drain.deadLettered === 0,
    JSON.stringify(drain),
  );
  const [retriedRow] = await sql<{ n: number }[]>`
    select count(*)::int as n from poll_dead_letter
    where source = 'govinfo' and last_retry_at is not null
  `;
  const retried = retriedRow!.n;
  assert(
    "slow drain: a failed retry advances the throttle (last_retry_at), never re-counts deadLettered",
    retried === CAP - 1,
    String(retried),
  );
} finally {
  await sql.end();
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
