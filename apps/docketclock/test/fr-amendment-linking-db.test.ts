/** Independent DB acceptance replay. Intentionally runs on main: only pre-existing runtime APIs
 * are statically imported. Missing GovInfo on main is an explicit fallback, never a skipped replay.
 * Destructive reset is allowed ONLY against the exact throwaway URL below; run suites serially.
 * DATABASE_URL=postgres://… node --import tsx apps/docketclock/test/fr-amendment-linking-db.test.ts
 */
import { strict as a } from "node:assert";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { ingestObservation } from "../src/ingest/observe.js";
import {
  reconcileOcdId,
  chainReconcileOnce,
} from "../src/reconcile/persist.js";

type Candidate = Parameters<typeof ingestObservation>[1];
type Stored = Candidate & { observation_id: string };
type WindowRow = {
  resolved_close_utc: Date | string | null;
  confidence: string;
  conflict_flags: string[];
  status: string;
  raw_fr_close_date: string | null;
  raw_regs_close_datetime: string | null;
  current_observation_ids: string[];
  provenance: unknown;
};
const DATABASE_URL = process.env.DATABASE_URL;
const NOW = new Date("2026-10-20T12:00:00Z");
const ROOT = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures/fr-amendments",
);
const stored: Stored[] = JSON.parse(
  readFileSync(join(ROOT, "stored/observations.json"), "utf8"),
);
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;
const api = (doc: string) =>
  JSON.parse(readFileSync(join(ROOT, "fr-api", `${doc}.json`), "utf8"));
let failures = 0;
let checks = 0;
const out: string[] = [];
function test(name: string, fn: () => void) {
  checks++;
  try {
    fn();
    out.push(`  PASS  ${name}`);
  } catch (error) {
    failures++;
    out.push(
      `  FAIL  ${name} — ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}
function summary(w: WindowRow) {
  return {
    close: w.resolved_close_utc
      ? new Date(w.resolved_close_utc).toISOString()
      : null,
    confidence: w.confidence,
    flags: [...w.conflict_flags].sort(),
    status: w.status,
    raw_fr: w.raw_fr_close_date,
    raw_regs: w.raw_regs_close_datetime,
  };
}
// Concrete HEAD 0a36548 main replay results, NOT computed with the implementation under test.
const baseline = {
  "2026-08068": {
    close: "2026-11-21T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-06-23",
    raw_regs: "2026-11-21T04:59:59Z",
  },
  "2026-08077": {
    close: "2026-11-21T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-06-23",
    raw_regs: "2026-11-21T04:59:59Z",
  },
  "2026-10969": {
    close: "2026-11-21T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-08-03",
    raw_regs: "2026-11-21T04:59:59Z",
  },
  "2026-17216": {
    close: "2026-09-24T03:59:59.000Z",
    confidence: "medium",
    flags: ["tz_normalization_only"],
    status: "closed",
    raw_fr: "2026-09-23",
    raw_regs: "2026-09-24T03:59:59Z",
  },
  "2026-19895": {
    close: "2026-10-30T03:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-08-24",
    raw_regs: "2026-10-30T03:59:59Z",
  },
  "2026-20660": {
    close: "2026-11-10T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-12-07",
    raw_regs: "2026-11-10T04:59:59Z",
  },
  "2026-18134": {
    close: "2026-11-19T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-10-19",
    raw_regs: "2026-11-19T04:59:59Z",
  },
} as const;
const positive = [
  {
    aDoc: "2026-18481",
    bDoc: "2026-20328",
    close: "2026-11-03T04:59:59.000Z",
    raw: "2026-10-13",
  },
  {
    aDoc: "2026-18531",
    bDoc: "2026-19710",
    close: "2026-11-03T04:59:59.000Z",
    raw: "2026-10-13",
  },
  {
    aDoc: "2026-18574",
    bDoc: "C1-2026-18574",
    close: "2026-10-27T03:59:59.000Z",
    raw: "2026-10-16",
  },
];
const nullAdjudicator = {
  id: "null:abstain",
  async adjudicate() {
    return {
      classification: "uncertain" as const,
      rationale: "acceptance replay: no network",
    };
  },
};

// Same idiom as the other DB suites: skip without a DATABASE_URL (CI and local runs supply their own
// throwaway Postgres). This suite drops and recreates the public schema, so point it at a throwaway DB.
if (!DATABASE_URL) {
  console.log("SKIP fr-amendment-linking-db.test.ts — DATABASE_URL not set");
  process.exit(0);
}
const sql = createClient(DATABASE_URL);
const ids = new Map<string, string>();
async function window(doc: string): Promise<WindowRow> {
  const [w] = await sql<WindowRow[]>`
    select resolved_close_utc, confidence, conflict_flags, status,
      raw_fr_close_date, raw_regs_close_datetime, current_observation_ids, provenance
    from participation_windows where ocd_id = ${ocd(doc)}
  `;
  a.ok(w, `missing persisted window ${doc}`);
  return w;
}
try {
  const [server] = await sql<{ database: string; version: string }[]>`
    select current_database() as database, current_setting('server_version') as version
  `;
  a.match(server!.version, /^18\./, "requires throwaway Postgres 18");
  out.push(
    `  INFO  Connected to ${server!.database}, PostgreSQL ${server!.version}`,
  );
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // Preserve historical parser flags and fetched_at verbatim, including IRS's false fr-v2 correction.
  for (const { observation_id, ...candidate } of [...stored].sort(
    (x, y) =>
      x.fetched_at.localeCompare(y.fetched_at) ||
      x.observation_id.localeCompare(y.observation_id),
  )) {
    const result = await ingestObservation(sql, candidate);
    if (result.observationId) ids.set(observation_id, result.observationId);
  }
  test("replay uses all stored FR/Regs rows without replacing fetched_at or old parser flags", () => {
    a.equal(stored.length, 175);
    a.equal(ids.size, stored.length);
    a.equal(
      stored.find((o) => o.fr_document_number === "C1-2026-18574")!
        .is_correction,
      false,
    );
  });
  const [fetched] = await sql<{ fetched_at: Date; is_correction: boolean }[]>`
    select fetched_at, is_correction from observations
    where source = 'federal_register' and fr_document_number = 'C1-2026-18574'
  `;
  test("persisted IRS historical observation keeps its original timestamp and false correction flag", () => {
    a.equal(fetched!.fetched_at.toISOString(), "2026-09-26T05:13:33.695Z");
    a.equal(fetched!.is_correction, false);
  });

  // PHMSA's meeting wasn't in the production log. Replay its recorded API payload as an ordinary
  // notice, so the negative exercises an ingested meeting alongside all three real NPRMs.
  const meeting = api("2026-19351");
  await ingestObservation(sql, {
    ocd_id: ocd("2026-19351") as Candidate["ocd_id"],
    source: "federal_register",
    fr_document_number: "2026-19351",
    regs_document_id: meeting.regulations_dot_gov_info?.document_id ?? null,
    regs_object_id: null,
    payload_hash: createHash("sha256")
      .update(JSON.stringify(meeting))
      .digest("hex"),
    fetched_at: NOW.toISOString(),
    parser_version: "fr-v2",
    raw_dates_text: meeting.dates,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: meeting,
  });
  const docnums = [
    ...new Set([...stored.map((o) => o.fr_document_number!), "2026-19351"]),
  ];
  for (const doc of docnums) await reconcileOcdId(sql, ocd(doc), NOW);
  await chainReconcileOnce(sql, NOW, { adjudicator: nullAdjudicator });
  await reconcileOcdId(sql, ocd("2026-18531"), NOW);
  const noGovUsda = await window("2026-18531");
  test("USDA without GovInfo stays conflicting at its main derivation", () => {
    a.deepEqual(summary(noGovUsda), {
      close: "2026-11-03T04:59:59.000Z",
      confidence: "conflicting",
      flags: ["fr_regs_date_mismatch"],
      status: "open",
      raw_fr: "2026-10-13",
      raw_regs: "2026-11-03T04:59:59Z",
    });
  });
  const beforeNegatives = new Map<string, WindowRow>();
  for (const doc of Object.keys(baseline))
    beforeNegatives.set(doc, await window(doc));

  let gov: typeof import("../src/sources/govinfo.js") | undefined;
  try {
    gov = await import("../src/sources/govinfo.js");
  } catch (error) {
    // Missing adapter is expected on main; a broken adapter/dependency on the implementation is not.
    if (
      !(error instanceof Error) ||
      (error as NodeJS.ErrnoException).code !== "ERR_MODULE_NOT_FOUND" ||
      !error.message.includes("/sources/govinfo")
    )
      throw error;
    out.push(
      "  INFO  GovInfo adapter not available on main; continuing every DB assertion without it",
    );
  }
  const govIds = new Map<string, string>();
  if (gov) {
    for (const doc of [
      "2026-20328",
      "2026-19710",
      "C1-2026-18574",
      "2026-19895",
      "2026-19351",
    ]) {
      const raw = api(doc);
      const candidate = gov.parseGovinfoObservation({
        frDocNum: doc,
        publicationDate: raw.publication_date,
        url: `https://www.govinfo.gov/content/pkg/FR-${raw.publication_date}/html/${doc}.htm`,
        html: readFileSync(join(ROOT, "govinfo", `${doc}.htm`), "utf8"),
        isCorrection: doc === "C1-2026-18574",
      });
      // Keep the replay clock deterministic; no future parser wall-clock affects the result.
      const result = await ingestObservation(sql, {
        ...candidate,
        fetched_at: NOW.toISOString(),
      });
      a.ok(result.observationId, `GovInfo ${doc} must append through ingest`);
      govIds.set(doc, result.observationId);
    }
  }
  // The production order: derive every window, chain with the null adjudicator, then rederive side A.
  for (const doc of docnums) await reconcileOcdId(sql, ocd(doc), NOW);
  const chainResult = await chainReconcileOnce(sql, NOW, {
    adjudicator: nullAdjudicator,
  });
  out.push(`  INFO  chain replay: ${JSON.stringify(chainResult)}`);
  for (const doc of [
    ...positive.map((p) => p.aDoc),
    ...Object.keys(baseline),
  ]) {
    await reconcileOcdId(sql, ocd(doc), NOW);
  }
  for (const p of positive) {
    const w = await window(p.aDoc);
    test(`${p.aDoc} + ${p.bDoc}: persisted A becomes HIGH/open with amended close and exact flags`, () => {
      a.deepEqual(summary(w), {
        close: p.close,
        confidence: "high",
        flags: ["fr_close_amended", "tz_normalization_only"],
        status: "open",
        raw_fr: p.raw,
        raw_regs: p.close.replace(".000Z", "Z"),
      });
    });
    if (gov)
      test(`${p.aDoc}: persisted evidence includes B's FR and GovInfo observation IDs`, () => {
        const oldFr = stored.find(
          (o) =>
            o.fr_document_number === p.bDoc && o.source === "federal_register",
        )!;
        for (const id of [
          ids.get(oldFr.observation_id)!,
          govIds.get(p.bDoc)!,
        ]) {
          a.ok(w.current_observation_ids.includes(id));
          a.ok(JSON.stringify(w.provenance).includes(id));
        }
      });
  }
  for (const [doc, expected] of Object.entries(baseline)) {
    const w = await window(doc);
    test(`${doc}: negative replay exactly matches concrete main close/confidence/flags/status/raw values`, () => {
      a.deepEqual(summary(w), expected);
      a.deepEqual(
        w,
        beforeNegatives.get(doc),
        "entire selected persisted derivation remains unchanged",
      );
    });
  }

  // New Regs payload AFTER the amendment: take a real stored payload and change only its comment count.
  // This MUST append a new observation (new hash/time), not silently deduplicate the freshness test.
  for (const p of positive) {
    const latest = stored
      .filter((o) => o.ocd_id === ocd(p.aDoc) && o.source === "regulations_gov")
      .sort((x, y) => x.fetched_at.localeCompare(y.fetched_at))
      .at(-1)!;
    const raw = structuredClone(latest.raw) as any;
    raw.data.attributes.commentCount =
      (Number(raw.data.attributes.commentCount) || 0) + 1;
    const { observation_id: _oldId, ...candidate } = latest;
    const result = await ingestObservation(sql, {
      ...candidate,
      raw,
      payload_hash: createHash("sha256")
        .update(JSON.stringify(raw))
        .digest("hex"),
      fetched_at: "2026-10-28T12:00:00Z",
    });
    a.equal(result.inserted, true, "refresh must be a NEW Regs observation");
    await reconcileOcdId(sql, ocd(p.aDoc), NOW);
    const w = await window(p.aDoc);
    test(`${p.aDoc}: NEW Regs observation retains amendment on reconcileOcdId without another chain pass`, () => {
      a.deepEqual(summary(w), {
        close: p.close,
        confidence: "high",
        flags: ["fr_close_amended", "tz_normalization_only"],
        status: "open",
        raw_fr: p.raw,
        raw_regs: p.close.replace(".000Z", "Z"),
      });
      a.ok(w.current_observation_ids.includes(result.observationId!));
    });
  }
} catch (error) {
  test("DB replay completed without a setup/import/runtime error", () => {
    throw error;
  });
} finally {
  await sql.end();
}
console.log("\n=== fr-amendment-linking-db results ===");
console.log(out.join("\n"));
console.log(
  `\n${checks - failures}/${checks} passed; ${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exitCode = failures === 0 ? 0 : 1;
