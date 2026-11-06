/** Disposable DB integration suite. NEVER falls back to DATABASE_URL.
 * Provision a dedicated docketclock_mcp_test[_suffix] database, then run on the Mini:
 * MCP_TEST_DATABASE_URL=postgres://.../docketclock_mcp_test pnpm exec tsx test/mcp-queries.test.ts
 * This suite deliberately destroys public in that dedicated database.
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { Observation, ParticipationWindow } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  McpReadError,
  withMcpRead,
  resolveWindow,
  getWindowMetadata,
  listMcpWindows,
  listMcpConflicts,
  getEvidencePage,
  readEvidenceByIds,
  getEngineObservations,
  getProjectionStamp,
} from "../src/api/mcp-queries.js";

// Guard before client creation, and again against the actual server before ANY destructive SQL.
const databaseUrl = process.env.MCP_TEST_DATABASE_URL;
if (!databaseUrl)
  throw new Error(
    "MCP_TEST_DATABASE_URL is required; DATABASE_URL is never used.",
  );
const parsedUrl = new URL(databaseUrl);
const expectedDatabase = decodeURIComponent(parsedUrl.pathname.slice(1));
const testDatabase = /^docketclock_mcp_test(?:_[a-z0-9_]+)?$/;
if (
  !["postgres:", "postgresql:"].includes(parsedUrl.protocol) ||
  !testDatabase.test(expectedDatabase)
)
  throw new Error(
    "Refusing destructive setup: database must be named docketclock_mcp_test[_suffix].",
  );
// Avoid connection-string overrides obscuring the destination checked above.
if (
  [...parsedUrl.searchParams.keys()].some((key) =>
    ["database", "dbname", "host", "service", "options"].includes(key),
  )
)
  throw new Error("Refusing test URL with connection-routing overrides.");
const sql = createClient(databaseUrl);
const ocd = (n: string) => `ocd-participation-window/federal/${n}`;
const STATE = "ocd-participation-window/state/ca/2026-001";
const A = ocd("2026-10001"),
  B = ocd("2026-10002"),
  C = ocd("2026-10003");
const D = ocd("2026-10004"),
  REGS = ocd("regs:ABC123"),
  BAD = ocd("2026-10006");
const T = "2026-10-01T12:00:00.000Z",
  CLOSE = "2026-11-01T03:59:59.000Z";
let checks = 0;
async function check(name: string, run: () => Promise<void>) {
  await run();
  checks++;
  console.log(`PASS ${name}`);
}
async function seedWindow(
  id: string,
  changes: Partial<ParticipationWindow> = {},
) {
  const window = ParticipationWindow.parse({
    ocd_id: id,
    fr_document_number: id.includes("regs:") ? null : id.split("/").at(-1),
    regs_document_id: null,
    regs_object_id: null,
    docket_id: ["EPA-DOCKET-1"],
    rin: "2000-AA01",
    window_type: "comment",
    resolved_close_utc: CLOSE,
    resolved_close_display: "11:59 p.m. ET / 7:59 p.m. AK",
    raw_fr_close_date: "2026-10-31",
    raw_regs_close_datetime: null,
    confidence: "high",
    conflict_flags: ["tz_normalization_only"],
    status: "open",
    submission_url: null,
    govinfo_url:
      "https://www.govinfo.gov/content/pkg/FR-2026-10-01/pdf/2026-10001.pdf",
    tags: [],
    version: 3,
    current_observation_ids: [],
    provenance: {
      agreeing_observation_ids: [],
      conflicting_observation_ids: [],
    },
    change_history: [],
    ...changes,
  });
  await sql`insert into participation_windows (
    ocd_id, fr_document_number, regs_document_id, regs_object_id, docket_id, rin, window_type,
    resolved_close_utc, resolved_close_display, raw_fr_close_date, raw_regs_close_datetime, confidence,
    conflict_flags, status, submission_url, govinfo_url, tags, version, current_observation_ids, provenance, change_history,
    derived_at, reconciler_version
  ) values (
    ${window.ocd_id}, ${window.fr_document_number}, ${window.regs_document_id}, ${window.regs_object_id},
    ${sql.json(window.docket_id)}, ${window.rin}, ${window.window_type}, ${window.resolved_close_utc},
    ${window.resolved_close_display}, ${window.raw_fr_close_date}, ${window.raw_regs_close_datetime},
    ${window.confidence}, ${sql.json(window.conflict_flags)}, ${window.status}, ${window.submission_url},
    ${window.govinfo_url}, ${sql.json(window.tags)}, ${window.version}, ${sql.json(window.current_observation_ids)},
    ${sql.json(window.provenance)}, ${sql.json(window.change_history)}, ${T}, 'test-rulebook'
  )`;
  return window;
}
async function seedObservation(
  id: string,
  owner: string,
  raw: unknown = {},
  changes: Partial<Observation> = {},
) {
  const row = {
    observation_id: id,
    ocd_id: owner,
    source: "federal_register" as const,
    fr_document_number: owner.split("/").at(-1)!,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: createHash("sha256").update(id).digest("hex"),
    fetched_at: T,
    parser_version: "test-parser",
    raw_dates_text: "Original legal DATES wording",
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
    ...changes,
  };
  // State fixtures intentionally bypass today's federal-only contract to simulate future additions.
  if (owner !== STATE) Observation.parse(row);
  await sql`insert into observations (observation_id, ocd_id, source, fr_document_number, regs_document_id,
    regs_object_id, payload_hash, fetched_at, parser_version, raw_dates_text,
    is_extension, is_correction, is_withdrawal, is_reopening, raw)
    values (${row.observation_id}, ${row.ocd_id}, ${row.source}, ${row.fr_document_number},
      ${row.regs_document_id}, ${row.regs_object_id}, ${row.payload_hash}, ${row.fetched_at}, ${row.parser_version},
      ${row.raw_dates_text}, ${row.is_extension}, ${row.is_correction}, ${row.is_withdrawal}, ${row.is_reopening}, ${sql.json(row.raw as never)})`;
}
async function seedConflict(
  owner: string,
  other: string,
  a: string,
  b: string,
  retired = false,
) {
  await sql`insert into conflict_records (ocd_id, ocd_id_b, observation_a_id, observation_b_id,
    source_a, source_b, conflict_flags, detected_at, conflict_scope, resolved_at)
    values (${owner}, ${other}, ${a}, ${b}, 'federal_register', 'federal_register',
      '["fr_regs_date_mismatch"]'::jsonb, ${T}, ${other ? "cross_window" : "cross_source"}, ${retired ? T : null})`;
}
const read = <TResult>(
  fn: (tx: import("../src/api/mcp-queries.js").McpReadTx) => Promise<TResult>,
) => withMcpRead(sql, fn);
const isCode = (code: string) => (error: unknown) =>
  error instanceof McpReadError && error.code === code;

try {
  const [identity] = await sql`select current_database() as name`;
  assert.equal(
    identity!.name,
    expectedDatabase,
    "Actual database must match the guarded URL",
  );
  assert.match(
    identity!.name,
    testDatabase,
    "Actual database must be explicitly disposable",
  );
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  const canonical = await seedWindow(A, {
    current_observation_ids: ["a-latest", "state-secret"],
    provenance: {
      agreeing_observation_ids: ["a-latest", "ref-agree"],
      conflicting_observation_ids: ["ref-conflict"],
    },
    change_history: [
      {
        version: 2,
        resolved_close_utc: "2026-10-30T03:59:59.000Z",
        observation_ids: ["ref-history"],
        changed_at: T,
      },
    ],
  });
  await seedWindow(B, {
    confidence: "unknown",
    resolved_close_utc: null,
    conflict_flags: [],
  });
  await seedWindow(C, {
    confidence: "conflicting",
    conflict_flags: ["fr_regs_date_mismatch"],
  });
  await seedWindow(D, {
    confidence: "conflicting",
    resolved_close_utc: null,
    conflict_flags: ["fr_regs_date_mismatch"],
  });
  await seedWindow(REGS, { docket_id: ["REGS-ONLY"], rin: null });
  await seedWindow(BAD, { docket_id: ["BAD-META"], rin: null });
  // Copy a projection at SQL level so future state contracts cannot silently widen MCP reads.
  await sql`insert into participation_windows (ocd_id, window_type, confidence, status, resolved_close_utc)
    values (${STATE}, 'comment', 'unknown', 'open', null)`;
  const meta = {
    title: "Water Quality 100%_Literal",
    agencies: [{ slug: "environmental-protection-agency" }, { slug: 42 }, null],
  };
  await seedObservation(
    "a-old",
    A,
    { title: "Outdated title", agencies: [{ slug: "obsolete" }] },
    { fetched_at: "2026-09-01T00:00:00.000Z" },
  );
  await seedObservation("a-latest", A, meta);
  await seedObservation("b-latest", B, meta);
  await seedObservation("c-latest", C, meta);
  await seedObservation("d-latest", D, meta);
  await seedObservation(
    "regs-only",
    REGS,
    { data: { attributes: { agencyId: "EPA", title: "Portal title" } } },
    { source: "regulations_gov" },
  );
  await seedObservation("bad-old", BAD, meta, {
    fetched_at: "2026-09-01T00:00:00.000Z",
  });
  await seedObservation("bad-a-tied", BAD, meta);
  await seedObservation("bad-new", BAD, [meta]);

  await check(
    "read transaction has repeatable-read isolation, read-only mode, and local 2s timeout",
    async () => {
      await read(async (tx) => {
        const [isolation] = await tx`show transaction_isolation`;
        const [readonly] = await tx`show transaction_read_only`;
        const [timeout] = await tx`show statement_timeout`;
        assert.equal(isolation!.transaction_isolation, "repeatable read");
        assert.equal(readonly!.transaction_read_only, "on");
        assert.equal(timeout!.statement_timeout, "2s");
      });
      await assert.rejects(
        read(async (tx) => {
          await tx`delete from participation_windows`;
        }),
        (e: unknown) =>
          typeof e === "object" &&
          e !== null &&
          "code" in e &&
          e.code === "25006",
      );
    },
  );
  await check(
    "multi-query answers retain one snapshot across a concurrent projection update",
    async () => {
      await read(async (tx) => {
        const before = await resolveWindow(tx, A);
        await sql`update participation_windows set version = version + 1 where ocd_id = ${A}`;
        assert.equal((await resolveWindow(tx, A))!.version, before!.version);
      });
      await sql`update participation_windows set version = version - 1 where ocd_id = ${A}`;
    },
  );
  await check(
    "canonical trust, wording, provenance, history and null submission survive mapping",
    async () => {
      assert.deepEqual(await read((tx) => resolveWindow(tx, A)), canonical);
      assert.equal(
        await read((tx) => resolveWindow(tx, "2026-NOTFOUND")),
        null,
      );
      assert.deepEqual(await read((tx) => getProjectionStamp(tx, A)), {
        derivedAt: T,
        reconcilerVersion: "test-rulebook",
      });
      assert.deepEqual(
        await read((tx) => getProjectionStamp(tx, "2026-NOTFOUND")),
        { derivedAt: null, reconcilerVersion: null },
      );
    },
  );
  await check(
    "latest primary FR metadata only; malformed latest and Regs agency never fall back",
    async () => {
      assert.deepEqual(await read((tx) => getWindowMetadata(tx, A)), {
        title: meta.title,
        agencySlugs: ["environmental-protection-agency"],
        observationIds: ["a-latest"],
      });
      assert.deepEqual(await read((tx) => getWindowMetadata(tx, BAD)), {
        title: null,
        agencySlugs: [],
        observationIds: ["bad-new"],
      });
      assert.deepEqual(await read((tx) => getWindowMetadata(tx, REGS)), {
        title: null,
        agencySlugs: [],
        observationIds: [],
      });
    },
  );
  await check(
    "conjunctive docket, agency, RIN, literal keyword; date uncertainty counts remain visible",
    async () => {
      const filters = {
        agency: "environmental-protection-agency",
        docket_id: "EPA-DOCKET-1",
        rin: "2000-AA01",
        closes_after: "2026-10-31T00:00:00Z",
        closes_before: "2026-11-02T00:00:00Z",
        close_mode: "known" as const,
      };
      const result = await read((tx) => listMcpWindows(tx, filters));
      assert.deepEqual(
        result.rows.map((w) => w.ocd_id),
        [A, C],
      );
      assert.equal(result.total, 2);
      assert.equal(result.unknownCloseCount, 2);
      assert.equal(result.disputedCloseCount, 1);
      const unknown = await read((tx) =>
        listMcpWindows(tx, { agency: filters.agency, close_mode: "unknown" }),
      );
      assert.deepEqual(
        unknown.rows.map((w) => w.ocd_id),
        [B, D],
      );
      assert.equal(
        (await read((tx) => listMcpWindows(tx, { agency: "obsolete" }))).total,
        0,
      );
      assert.equal(
        (await read((tx) => listMcpWindows(tx, { keyword: "%_Literal" })))
          .total,
        4,
      );
      assert.equal(
        (await read((tx) => listMcpWindows(tx, { keyword: "%not-a-wildcard" })))
          .total,
        0,
      );
      assert.equal(
        (await read((tx) => listMcpWindows(tx, { keyword: "regs:abc123" })))
          .total,
        1,
      );
      assert.equal(
        (await read((tx) => listMcpWindows(tx, { keyword: "2000-aa01" })))
          .total,
        4,
      );
      assert.equal(
        (await read((tx) => listMcpWindows(tx, { docket_id: "REGS-ONLY" })))
          .total,
        1,
      );
    },
  );
  await check(
    "missing metadata counts broader pre-agency/keyword population; paging never changes counts",
    async () => {
      const result = await read((tx) =>
        listMcpWindows(tx, {
          agency: "no-match",
          keyword: "no-match",
          limit: 1,
          offset: 1000,
        }),
      );
      assert.equal(result.total, 0);
      assert.equal(result.metadataMissingCount, 2);
      const paged = await read((tx) =>
        listMcpWindows(tx, { limit: 1, offset: 1 }),
      );
      assert.equal(paged.total, 6);
      assert.equal(paged.rows[0]!.ocd_id, C);
      assert.equal(paged.unknownCloseCount, 2);
      const date = await read((tx) =>
        listMcpWindows(tx, { closes_before: CLOSE }),
      );
      assert.equal(date.total, 0);
      assert.equal(date.unknownCloseCount, 2);
      assert.equal(date.disputedCloseCount, 0);
    },
  );

  for (const [id, confidence, flags] of [
    ["2026-MED", "medium", ["llm_corroborated"]],
    ["2026-LOW", "low", ["human_resolved"]],
    ["2026-STALE", "stale", ["agent_resolved"]],
  ] as const) {
    const seeded = await seedWindow(ocd(id), {
      confidence,
      conflict_flags: [...flags],
    });
    await check(
      `preserves ${confidence} confidence and authority flags`,
      async () => {
        assert.deepEqual(
          await read((tx) => resolveWindow(tx, ocd(id))),
          seeded,
        );
      },
    );
  }
  await check(
    "FR shorthand preserves stored regs fallback; ambiguous IDs fail explicitly",
    async () => {
      const fallback = await seedWindow(ocd("regs:FALLBACK"), {
        fr_document_number: "2026-20001",
      });
      assert.deepEqual(
        await read((tx) => resolveWindow(tx, "2026-20001")),
        fallback,
      );
      await seedWindow(ocd("2026-20001"));
      await assert.rejects(
        read((tx) => resolveWindow(tx, "2026-20001")),
        (error: unknown) =>
          error instanceof McpReadError &&
          error.code === "ambiguous_identifier" &&
          error.candidateOcdIds.length === 2,
      );
      assert.equal(
        (await read((tx) => resolveWindow(tx, fallback.ocd_id)))!.ocd_id,
        fallback.ocd_id,
      );
    },
  );

  await seedObservation("target-only", C, {
    title: "Foreign target title",
    agencies: [{ slug: "foreign-agency" }],
  });
  await seedObservation("ref-agree", C, {}, { source: "govinfo" });
  await seedObservation("ref-conflict", C, {}, { source: "govinfo" });
  await seedObservation("ref-history", C, {}, { source: "govinfo" });
  await seedObservation("unrelated", C, {}, { source: "govinfo" });
  await seedObservation(
    "late",
    A,
    {},
    { source: "govinfo", fetched_at: "2026-10-02T00:00:00.000Z" },
  );
  await seedObservation("state-secret", STATE, { title: "SECRET STATE" });
  await sql`insert into observation_targets (observation_id, ocd_id) values
    ('target-only', ${A}), ('a-latest', ${A}), ('state-secret', ${A})`;
  await seedConflict(C, A, "c-latest", "a-latest");
  await seedConflict(C, A, "c-latest", "b-latest");
  await seedConflict(A, "", "a-latest", "b-latest");
  await seedConflict(A, "", "a-old", "b-latest", true);
  await seedConflict(A, STATE, "a-latest", "state-secret");
  await seedConflict(A, "", "state-secret", "a-latest");

  await check(
    "live conflicts use either side and deterministic observation-ID ties; no state side leaks",
    async () => {
      const first = await read((tx) =>
        listMcpConflicts(tx, { ocd_id: A, limit: 1 }),
      );
      const second = await read((tx) =>
        listMcpConflicts(tx, { ocd_id: A, limit: 1, offset: 1 }),
      );
      const third = await read((tx) =>
        listMcpConflicts(tx, { ocd_id: A, limit: 1, offset: 2 }),
      );
      assert.equal(first.total, 3);
      assert.equal(first.rows[0]!.ocd_id_b, null);
      assert.equal(second.rows[0]!.ocd_id_b, A);
      assert.equal(second.rows[0]!.observation_b_id, "a-latest");
      assert.equal(third.rows[0]!.observation_b_id, "b-latest");
      assert.ok(!("resolved_at" in first.rows[0]!));
      assert.equal((await read((tx) => listMcpConflicts(tx))).total, 3);
    },
  );
  await check(
    "evidence deduplicates primary/M:N/current/provenance/history/live conflict sides",
    async () => {
      assert.equal(
        (await read((tx) => getWindowMetadata(tx, A))).title,
        meta.title,
        "Target FR metadata must not override primary metadata",
      );
      const result = await read((tx) => getEvidencePage(tx, A));
      const byId = new Map(
        result.rows.map((r) => [r.observation.observation_id, r]),
      );
      assert.equal(result.total, byId.size);
      assert.equal(result.total, 9);
      assert.deepEqual(byId.get("a-latest")!.relationship, [
        "agreeing",
        "conflict_side",
        "current",
        "primary",
        "target",
      ]);
      assert.deepEqual(byId.get("target-only")!.relationship, ["target"]);
      assert.deepEqual(byId.get("ref-history")!.relationship, ["history"]);
      assert.deepEqual(byId.get("ref-conflict")!.relationship, ["conflicting"]);
      assert.ok(byId.has("c-latest"));
      assert.ok(byId.has("b-latest"));
      assert.ok(!byId.has("state-secret"));
      assert.ok(!byId.has("unrelated"));
      const frozen = await read((tx) =>
        getEvidencePage(tx, A, { evidenceAsOf: T }),
      );
      assert.equal(frozen.total, 8);
      assert.ok(frozen.rows.every((r) => r.observation.fetched_at <= T));
      const pages = await read(async (tx) => [
        await getEvidencePage(tx, A, { limit: 1 }),
        await getEvidencePage(tx, A, { limit: 1, offset: 1 }),
      ]);
      assert.equal(pages[0]!.rows[0]!.observation.observation_id, "late");
      assert.notEqual(
        pages[0]!.rows[0]!.observation.observation_id,
        pages[1]!.rows[0]!.observation.observation_id,
      );
    },
  );
  await check(
    "evidence ID reads are scoped; engine chain is complete PRIMARY only in ascending order",
    async () => {
      const scoped = await read((tx) =>
        readEvidenceByIds(tx, A, [
          "target-only",
          "unrelated",
          "state-secret",
          "target-only",
          "missing",
        ]),
      );
      assert.deepEqual(
        scoped.map((r) => r.observation_id),
        ["target-only"],
      );
      assert.deepEqual(
        (await read((tx) => getEngineObservations(tx, A))).map(
          (r) => r.observation_id,
        ),
        ["a-old", "a-latest", "late"],
      );
      assert.deepEqual(
        await read((tx) => getEvidencePage(tx, ocd("2026-ABSENT"))),
        { rows: [], total: 0, limit: 10, offset: 0 },
      );
    },
  );
  await check(
    "missing observation rows do not silently retire a live conflict",
    async () => {
      await seedConflict(A, "", "missing-a", "missing-b");
      const result = await read((tx) => listMcpConflicts(tx, { ocd_id: A }));
      assert.equal(result.total, 4);
      assert.ok(result.rows.some((r) => r.observation_a_id === "missing-a"));
      assert.deepEqual(
        await read((tx) =>
          readEvidenceByIds(tx, A, ["missing-a", "missing-b"]),
        ),
        [],
      );
    },
  );
  await check(
    "federal boundary applies to direct IDs, evidence, metadata, engine, stamps and counts",
    async () => {
      for (const query of [
        () => read((tx) => resolveWindow(tx, STATE)),
        () => read((tx) => getWindowMetadata(tx, STATE)),
        () => read((tx) => getEvidencePage(tx, STATE)),
        () => read((tx) => readEvidenceByIds(tx, STATE, ["state-secret"])),
        () => read((tx) => getEngineObservations(tx, STATE)),
        () => read((tx) => getProjectionStamp(tx, STATE)),
        () => read((tx) => listMcpConflicts(tx, { ocd_id: STATE })),
      ])
        await assert.rejects(query(), isCode("invalid_input"));
      assert.ok(
        (await read((tx) => listMcpWindows(tx))).rows.every(
          (r) => r.ocd_id !== STATE,
        ),
      );
      await assert.rejects(
        read((tx) =>
          listMcpWindows(tx, { close_mode: "unknown", closes_before: T }),
        ),
        isCode("invalid_input"),
      );
      await assert.rejects(
        read((tx) => listMcpWindows(tx, { limit: 21 })),
        isCode("invalid_input"),
      );
      await assert.rejects(
        read((tx) => resolveWindow(tx, "2026-X' OR true--")),
        isCode("invalid_input"),
      );
    },
  );
  await check(
    "contract-invalid projections fail loudly rather than filtering away uncertainty",
    async () => {
      const poison = ocd("2026-POISON");
      await sql`insert into participation_windows (ocd_id, window_type, confidence, status) values (${poison}, 'comment', 'high', 'open')`;
      await assert.rejects(read((tx) => resolveWindow(tx, poison)));
      await sql`delete from participation_windows where ocd_id = ${poison}`;
    },
  );
  await check(
    "engine chain cap fails explicitly rather than honoring from a truncated chain",
    async () => {
      await sql`insert into observations (observation_id, ocd_id, source, payload_hash, fetched_at, parser_version,
      is_extension, is_correction, is_withdrawal, is_reopening, raw)
      select 'bulk-' || n, ${A}, 'govinfo', repeat('a',64), ${T}::timestamptz, 'test-parser', false, false, false, false, '{}'::jsonb
      from generate_series(1, 997) n`;
      assert.equal(
        (await read((tx) => getEngineObservations(tx, A))).length,
        1000,
      );
      await seedObservation("overflow", A, {}, { source: "govinfo" });
      await assert.rejects(
        read((tx) => getEngineObservations(tx, A)),
        isCode("result_too_large"),
      );
    },
  );
  console.log(`${checks} MCP query integration checks passed.`);
} finally {
  await sql.end();
}
