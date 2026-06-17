/**
 * api.test.ts — proves the Delivery API read surface (buildServer) end to end, DB-backed, via app.inject
 * (NO real port/network). Matches the repo test style (regs/reconcile/poll): hand-rolled assert, out[]
 * accumulator, failures counter, process.exit; a throwaway Postgres seeded by running the REAL
 * ingest+reconcile path so the read model is exactly what production would have written.
 *
 * Seed plan (one fresh schema):
 *   • W-HIGH   2025-02910 — FR+Regs tz-agreement → HIGH window, close ~2026-06 (also carries docket_id
 *                EPA-HQ-OW-2024-0454 from the FR fixture → the docket_id filter target).
 *   • W-LOW    2025-55501 — FR-only date-only → LOW window, later close (closes_* boundary target).
 *   • W-CONF   2025-77777 — FR+Regs withdrawn-vs-open → CONFLICTING window + a LIVE conflict_records row.
 *   • W-RESOLVED 2025-33333 — mismatch then agreement → conflict RETIRED (resolved_at set) → must be
 *                ABSENT from the live /v1/conflicts feed (the resolved-exclusion proof).
 *
 * Coverage: auth (fail-closed: no key / wrong key → 401, good key → 200; /healthz + /openapi.json public),
 * the envelope trio + x-request-id header + per-request uniqueness, /v1/windows list + every real filter +
 * pagination + limit clamp + contract parse, /v1/windows/* (slashed ocd_id) detail + observations + 404 +
 * 400, /v1/conflicts live-only + no resolved_at leak + contract parse, and /openapi.json being a real
 * OpenAPI 3.1 doc generated from the Zod schemas (paths present).
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  apiItemEnvelope,
  apiListEnvelope,
  API_VERSION,
  ConflictRecord,
  DISCLAIMER,
  Observation,
  ParticipationWindow,
} from "@yokel/contracts";
import { z } from "zod";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { ingestObservation } from "../src/ingest/observe.js";
import { reconcileOcdId } from "../src/reconcile/persist.js";
import { buildServer } from "../src/api/server.js";

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
const ocd = (n: string) => `ocd-participation-window/federal/${n}`;

/** Body type for an item-envelope detail: ParticipationWindow + observations + EnvelopeMeta. */
const WindowDetailResponse = apiItemEnvelope(
  (ParticipationWindow as unknown as z.ZodEffects<z.ZodObject<z.ZodRawShape>>)
    .innerType()
    .extend({ observations: z.array(Observation) }),
);
const WindowListResponse = apiListEnvelope(ParticipationWindow);
const ConflictListResponse = apiListEnvelope(ConflictRecord);

const sql = createClient();
const app = buildServer(sql, { apiKeys: ["test-key"] });
await app.ready();

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);

  // ── SEED: W-HIGH (FR+Regs tz-agreement → HIGH, carries docket_id EPA-HQ-OW-2024-0454) ───────────────
  const HIGH = "2025-02910";
  {
    const frRaw = { ...frFixture, comments_close_on: "2026-06-16" };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    const regsRaw = JSON.parse(
      JSON.stringify(regsFixture),
    ) as typeof regsFixture;
    regsRaw.data.attributes.frDocNum = HIGH;
    regsRaw.data.attributes.commentEndDate = "2026-06-17T03:59:59Z";
    regsRaw.data.attributes.withdrawn = false;
    regsRaw.data.attributes.openForComment = true;
    await ingestObservation(sql, {
      ...parseRegsObservation(regsRaw),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    await reconcileOcdId(sql, ocd(HIGH), NOW);
  }

  // ── SEED: W-LOW (FR-only date-only → LOW, later close) ──────────────────────────────────────────────
  const LOW = "2025-55501";
  {
    const frRaw = {
      ...frFixture,
      document_number: LOW,
      docket_ids: ["DOI-LOW-0001"],
      comments_close_on: "2026-09-10",
    };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    await reconcileOcdId(sql, ocd(LOW), NOW);
  }

  // ── SEED: W-CONF (withdrawn-vs-open → CONFLICTING + a LIVE conflict_records row) ────────────────────
  const CONF = "2025-77777";
  {
    const frRaw = {
      ...frFixture,
      document_number: CONF,
      docket_ids: ["EPA-CONF-0001"],
      comments_close_on: "2026-07-15",
    };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    const regsC = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
    regsC.data.attributes.frDocNum = CONF;
    regsC.data.attributes.commentEndDate = "2026-07-15T12:00:00Z";
    regsC.data.attributes.withdrawn = true;
    regsC.data.attributes.openForComment = true;
    await ingestObservation(sql, {
      ...parseRegsObservation(regsC),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    const rc = await reconcileOcdId(sql, ocd(CONF), NOW);
    assert(
      "SEED: W-CONF reconciles to CONFLICTING with a live conflict",
      rc.window.confidence === "conflicting" && rc.conflict !== null,
      rc.window.confidence,
    );
  }

  // ── SEED: W-RESOLVED (mismatch → then agreement → conflict RETIRED; must be ABSENT from /conflicts) ──
  const RESOLVED = "2025-33333";
  {
    const frRaw = {
      ...frFixture,
      document_number: RESOLVED,
      docket_ids: ["EPA-RES-0001"],
      comments_close_on: "2026-07-01",
    };
    await ingestObservation(sql, {
      ...parseFrObservation(frRaw),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    const regsM = JSON.parse(JSON.stringify(regsFixture)) as typeof regsFixture;
    regsM.data.attributes.frDocNum = RESOLVED;
    regsM.data.attributes.commentEndDate = "2026-08-11T03:59:59Z"; // Eastern 08-10 → mismatch
    await ingestObservation(sql, {
      ...parseRegsObservation(regsM),
      fetched_at: "2026-05-20T00:00:00Z",
    });
    await reconcileOcdId(sql, ocd(RESOLVED), NOW);
    // A new Regs obs that now AGREES → window no longer conflicting → conflict retired.
    const regsA = JSON.parse(JSON.stringify(regsM)) as typeof regsM;
    regsA.data.attributes.commentEndDate = "2026-07-02T03:59:59Z"; // Eastern 07-01, agrees with FR
    await ingestObservation(sql, {
      ...parseRegsObservation(regsA),
      fetched_at: "2026-05-21T00:00:00Z",
    });
    await reconcileOcdId(sql, ocd(RESOLVED), new Date("2026-06-02T00:00:00Z"));
    const [open] = await sql<{ count: string }[]>`
      select count(*)::text as count from conflict_records
      where ocd_id = ${ocd(RESOLVED)} and resolved_at is null
    `;
    assert(
      "SEED: W-RESOLVED conflict was retired (0 live rows)",
      open!.count === "0",
      open!.count,
    );
    const [retired] = await sql<{ count: string }[]>`
      select count(*)::text as count from conflict_records
      where ocd_id = ${ocd(RESOLVED)} and resolved_at is not null
    `;
    assert(
      "SEED: W-RESOLVED has a retired (resolved_at set) conflict row",
      retired!.count === "1",
      retired!.count,
    );
  }

  // ── AUTH (fail-closed) ──────────────────────────────────────────────────────────────────────────────
  {
    const noKey = await app.inject({ method: "GET", url: "/v1/windows" });
    assert(
      "AUTH: /v1/windows with NO x-api-key → 401",
      noKey.statusCode === 401,
      String(noKey.statusCode),
    );
    const noKeyBody = noKey.json();
    assert(
      "AUTH: 401 body is enveloped error { code:'unauthorized', api_version, request_id }",
      noKeyBody.error?.code === "unauthorized" &&
        noKeyBody.api_version === API_VERSION &&
        typeof noKeyBody.request_id === "string" &&
        noKeyBody.request_id.length > 0,
      JSON.stringify(noKeyBody),
    );
    // Fix #6: EVERY response carries the disclaimer — errors included.
    assert(
      "AUTH: 401 error body ALSO carries disclaimer === DISCLAIMER (Fix #6)",
      noKeyBody.disclaimer === DISCLAIMER,
      String(noKeyBody.disclaimer).slice(0, 30),
    );
    const wrongKey = await app.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "nope" },
    });
    assert(
      "AUTH: /v1/windows with WRONG x-api-key → 401",
      wrongKey.statusCode === 401,
      String(wrongKey.statusCode),
    );
    const goodKey = await app.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "AUTH: /v1/windows with the correct key → 200",
      goodKey.statusCode === 200,
      String(goodKey.statusCode),
    );
    const health = await app.inject({ method: "GET", url: "/healthz" });
    assert(
      "AUTH: /healthz is PUBLIC (200 with no key) and db ok",
      health.statusCode === 200 && health.json().db === "ok",
      `${health.statusCode} ${JSON.stringify(health.json())}`,
    );
    const spec = await app.inject({ method: "GET", url: "/openapi.json" });
    assert(
      "AUTH: /openapi.json is PUBLIC (200 with no key)",
      spec.statusCode === 200,
      String(spec.statusCode),
    );
  }

  // ── FAIL-CLOSED: a server with NO keys configured 401s every data request ──────────────────────────
  {
    const closedApp = buildServer(sql, { apiKeys: [] });
    await closedApp.ready();
    const r = await closedApp.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "anything" },
    });
    assert(
      "FAIL-CLOSED: no keys configured → 401 even with a key header",
      r.statusCode === 401,
      String(r.statusCode),
    );
    const h = await closedApp.inject({ method: "GET", url: "/healthz" });
    assert(
      "FAIL-CLOSED: /healthz still public when no keys configured",
      h.statusCode === 200,
      String(h.statusCode),
    );
    await closedApp.close();
  }

  // ── ENVELOPE: disclaimer + api_version + request_id + x-request-id header + uniqueness ──────────────
  {
    const r1 = await app.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "test-key" },
    });
    const b1 = r1.json();
    assert(
      "ENVELOPE: disclaimer === DISCLAIMER",
      b1.disclaimer === DISCLAIMER,
      String(b1.disclaimer).slice(0, 30),
    );
    assert(
      "ENVELOPE: api_version === API_VERSION",
      b1.api_version === API_VERSION,
      String(b1.api_version),
    );
    assert(
      "ENVELOPE: request_id is a non-empty string",
      typeof b1.request_id === "string" && b1.request_id.length > 0,
      String(b1.request_id),
    );
    assert(
      "ENVELOPE: x-request-id response header equals the body request_id",
      r1.headers["x-request-id"] === b1.request_id,
      `${r1.headers["x-request-id"]} vs ${b1.request_id}`,
    );
    const r2 = await app.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "ENVELOPE: two requests yield DIFFERENT request_ids",
      r1.json().request_id !== r2.json().request_id,
    );
  }

  // ── /v1/windows: list + pagination + contract parse ────────────────────────────────────────────────
  {
    const r = await app.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "test-key" },
    });
    const parsed = WindowListResponse.safeParse(r.json());
    assert(
      "WINDOWS: body parses against apiListEnvelope(ParticipationWindow)",
      parsed.success,
      parsed.success ? "" : JSON.stringify(parsed.error.issues.slice(0, 3)),
    );
    const body = r.json();
    assert(
      "WINDOWS: all four seeded windows returned",
      body.data.length === 4,
      String(body.data.length),
    );
    assert(
      "WINDOWS: pagination block present with total=4",
      body.pagination &&
        body.pagination.total === 4 &&
        typeof body.pagination.limit === "number" &&
        typeof body.pagination.offset === "number",
      JSON.stringify(body.pagination),
    );
    // Order: resolved_close_utc asc — the earliest-closing window first.
    assert(
      "WINDOWS: ordered by resolved_close_utc asc (W-CONF 07-15 not after W-LOW 09-10)",
      new Date(body.data[0].resolved_close_utc).getTime() <=
        new Date(body.data[body.data.length - 1].resolved_close_utc).getTime(),
      body.data.map((w: { ocd_id: string }) => w.ocd_id).join(","),
    );
  }

  // ── /v1/windows: filters ────────────────────────────────────────────────────────────────────────────
  {
    const byConf = await app.inject({
      method: "GET",
      url: "/v1/windows?confidence=conflicting",
      headers: { "x-api-key": "test-key" },
    });
    const cb = byConf.json();
    assert(
      "FILTER confidence=conflicting narrows to the one CONFLICTING window",
      cb.data.length === 1 &&
        cb.data[0].ocd_id === ocd(CONF) &&
        cb.pagination.total === 1,
      JSON.stringify(cb.data.map((w: { ocd_id: string }) => w.ocd_id)),
    );

    const byStatus = await app.inject({
      method: "GET",
      url: "/v1/windows?status=withdrawn",
      headers: { "x-api-key": "test-key" },
    });
    const sb = byStatus.json();
    assert(
      "FILTER status=withdrawn narrows to W-CONF",
      sb.data.length === 1 && sb.data[0].ocd_id === ocd(CONF),
      JSON.stringify(sb.data.map((w: { ocd_id: string }) => w.ocd_id)),
    );

    const byDocket = await app.inject({
      method: "GET",
      url: "/v1/windows?docket_id=EPA-HQ-OW-2024-0454",
      headers: { "x-api-key": "test-key" },
    });
    const db = byDocket.json();
    assert(
      "FILTER docket_id (jsonb contains) narrows to W-HIGH",
      db.data.length === 1 && db.data[0].ocd_id === ocd(HIGH),
      JSON.stringify(db.data.map((w: { ocd_id: string }) => w.ocd_id)),
    );

    // closes_before 2026-08-01 → excludes W-LOW (09-10); includes the three earlier-closing windows.
    const cb2 = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_before=2026-08-01T00:00:00.000Z",
      headers: { "x-api-key": "test-key" },
    });
    const cbb = cb2.json();
    assert(
      "FILTER closes_before excludes the later-closing W-LOW",
      cbb.data.every((w: { ocd_id: string }) => w.ocd_id !== ocd(LOW)) &&
        cbb.data.length === 3,
      JSON.stringify(cbb.data.map((w: { ocd_id: string }) => w.ocd_id)),
    );

    const ca = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_after=2026-08-01T00:00:00.000Z",
      headers: { "x-api-key": "test-key" },
    });
    const cab = ca.json();
    assert(
      "FILTER closes_after includes only the later-closing W-LOW",
      cab.data.length === 1 && cab.data[0].ocd_id === ocd(LOW),
      JSON.stringify(cab.data.map((w: { ocd_id: string }) => w.ocd_id)),
    );
  }

  // ── /v1/windows: limit/offset pagination + clamp ───────────────────────────────────────────────────
  {
    const p1 = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=2&offset=0",
      headers: { "x-api-key": "test-key" },
    });
    const b1 = p1.json();
    assert(
      "PAGINATE: limit=2 returns 2 rows but total reflects the full set (4)",
      b1.data.length === 2 &&
        b1.pagination.total === 4 &&
        b1.pagination.limit === 2 &&
        b1.pagination.offset === 0,
      JSON.stringify(b1.pagination),
    );
    const p2 = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=2&offset=2",
      headers: { "x-api-key": "test-key" },
    });
    const b2 = p2.json();
    assert(
      "PAGINATE: offset=2 returns the next page (disjoint ocd_ids)",
      b2.data.length === 2 &&
        b1.data[0].ocd_id !== b2.data[0].ocd_id &&
        b1.data[1].ocd_id !== b2.data[0].ocd_id,
      `${b1.data.map((w: { ocd_id: string }) => w.ocd_id)} | ${b2.data.map((w: { ocd_id: string }) => w.ocd_id)}`,
    );
    const clamp = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=9999",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "PAGINATE: limit clamps at 200 (no error; all rows returned)",
      clamp.statusCode === 200 && clamp.json().data.length === 4,
      String(clamp.statusCode),
    );
  }

  // ── Fix #1: pagination reports the EFFECTIVE (clamped) limit/offset, never the requested ones ───────
  {
    // limit=10000 → reports the clamped 200 (NOT 10000), and returns at most 200 rows. A client doing
    // ceil(total/limit) would otherwise underestimate the page count.
    const huge = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=10000",
      headers: { "x-api-key": "test-key" },
    });
    const hb = huge.json();
    assert(
      "FIX#1: ?limit=10000 reports pagination.limit === 200 (effective, not requested)",
      huge.statusCode === 200 && hb.pagination.limit === 200,
      JSON.stringify(hb.pagination),
    );
    assert(
      "FIX#1: ?limit=10000 returns at most 200 rows",
      hb.data.length <= 200,
      String(hb.data.length),
    );

    // No limit, fewer than 50 matching rows → reports the effective DEFAULT 50 (NOT rows.length=4).
    const noLimit = await app.inject({
      method: "GET",
      url: "/v1/windows",
      headers: { "x-api-key": "test-key" },
    });
    const nlb = noLimit.json();
    assert(
      "FIX#1: no-limit with <50 rows reports pagination.limit === 50 (default, not rows.length)",
      nlb.pagination.limit === 50,
      JSON.stringify(nlb.pagination),
    );

    // An explicit negative limit/offset is now a clean 400 at the boundary (was a 500 before the fix).
    const negLimit = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=-5",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#1: ?limit=-5 → 400 (NOT 500)",
      negLimit.statusCode === 400 &&
        negLimit.json().error?.code === "bad_request",
      `${negLimit.statusCode} ${JSON.stringify(negLimit.json().error)}`,
    );
    const negOffset = await app.inject({
      method: "GET",
      url: "/v1/windows?offset=-7",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#1: ?offset=-7 → 400 (NOT 500)",
      negOffset.statusCode === 400,
      String(negOffset.statusCode),
    );
    // ?limit=abc still 400 (coerce → NaN fails .int()).
    const badLimit = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=abc",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#1: ?limit=abc → 400 (NaN fails int, unchanged)",
      badLimit.statusCode === 400,
      String(badLimit.statusCode),
    );

    // A valid limit=2&offset=1 echoes {limit:2, offset:1, total:<full 4>} and returns the right slice.
    const slice = await app.inject({
      method: "GET",
      url: "/v1/windows?limit=2&offset=1",
      headers: { "x-api-key": "test-key" },
    });
    const slb = slice.json();
    assert(
      "FIX#1: ?limit=2&offset=1 echoes {limit:2, offset:1, total:4} and slices correctly",
      slb.pagination.limit === 2 &&
        slb.pagination.offset === 1 &&
        slb.pagination.total === 4 &&
        slb.data.length === 2,
      JSON.stringify(slb.pagination),
    );
  }

  // ── Fix #2: a malformed date filter is a 400, never a 500 ──────────────────────────────────────────
  {
    const banana = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_before=banana",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#2: ?closes_before=banana → 400 enveloped (no leak, not 500)",
      banana.statusCode === 400 &&
        banana.json().error?.code === "bad_request" &&
        banana.json().disclaimer === DISCLAIMER,
      `${banana.statusCode} ${JSON.stringify(banana.json().error)}`,
    );
    const badMonth = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_before=2026-13-99",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#2: ?closes_before=2026-13-99 → 400",
      badMonth.statusCode === 400,
      String(badMonth.statusCode),
    );
    const empty = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_before=",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#2: ?closes_before= (empty) → 400",
      empty.statusCode === 400,
      String(empty.statusCode),
    );
    // A valid date-only filter still 200s AND actually narrows the set (excludes the later W-LOW 09-10).
    const valid = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_before=2026-08-01",
      headers: { "x-api-key": "test-key" },
    });
    const vb = valid.json();
    assert(
      "FIX#2: ?closes_before=2026-08-01 (valid date-only) → 200 and narrows (excludes W-LOW)",
      valid.statusCode === 200 &&
        vb.data.length === 3 &&
        vb.data.every((w: { ocd_id: string }) => w.ocd_id !== ocd(LOW)),
      `${valid.statusCode} ${JSON.stringify(vb.data?.map((w: { ocd_id: string }) => w.ocd_id))}`,
    );
    // A full ISO instant still works too.
    const validIso = await app.inject({
      method: "GET",
      url: "/v1/windows?closes_before=2026-08-01T00:00:00Z",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "FIX#2: ?closes_before=<full ISO> → 200 and narrows the same way",
      validIso.statusCode === 200 && validIso.json().data.length === 3,
      `${validIso.statusCode} ${validIso.json().data?.length}`,
    );
  }

  // ── /v1/windows/* — slashed ocd_id detail + observations, 404, 400 ─────────────────────────────────
  {
    const detail = await app.inject({
      method: "GET",
      url: `/v1/windows/${ocd(HIGH)}`,
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "DETAIL: a slashed ocd_id resolves via the wildcard route → 200",
      detail.statusCode === 200,
      String(detail.statusCode),
    );
    const parsed = WindowDetailResponse.safeParse(detail.json());
    assert(
      "DETAIL: body parses against the item-envelope detail schema",
      parsed.success,
      parsed.success ? "" : JSON.stringify(parsed.error.issues.slice(0, 3)),
    );
    const dbody = detail.json();
    assert(
      "DETAIL: data.ocd_id matches the requested window",
      dbody.data.ocd_id === ocd(HIGH),
      dbody.data.ocd_id,
    );
    assert(
      "DETAIL: observations array is present and non-empty (FR + Regs)",
      Array.isArray(dbody.data.observations) &&
        dbody.data.observations.length === 2,
      String(dbody.data.observations?.length),
    );

    const missing = await app.inject({
      method: "GET",
      url: `/v1/windows/${ocd("2099-00000")}`,
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "DETAIL: an unknown (but well-formed) ocd_id → 404 enveloped",
      missing.statusCode === 404 &&
        missing.json().error?.code === "not_found" &&
        missing.json().api_version === API_VERSION,
      `${missing.statusCode} ${JSON.stringify(missing.json().error)}`,
    );

    // A malformed id (has an illegal extra slash segment) → 400.
    const malformed = await app.inject({
      method: "GET",
      url: "/v1/windows/ocd-participation-window/federal/has/extra/slashes",
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "DETAIL: a malformed ocd_id → 400 enveloped",
      malformed.statusCode === 400 &&
        malformed.json().error?.code === "bad_request",
      `${malformed.statusCode} ${JSON.stringify(malformed.json().error)}`,
    );
  }

  // ── /v1/conflicts — LIVE only, no resolved_at leak, contract parse ─────────────────────────────────
  {
    const r = await app.inject({
      method: "GET",
      url: "/v1/conflicts",
      headers: { "x-api-key": "test-key" },
    });
    const parsed = ConflictListResponse.safeParse(r.json());
    assert(
      "CONFLICTS: body parses against apiListEnvelope(ConflictRecord)",
      parsed.success,
      parsed.success ? "" : JSON.stringify(parsed.error.issues.slice(0, 3)),
    );
    const body = r.json();
    assert(
      "CONFLICTS: exactly the ONE live conflict (W-CONF) is published",
      body.data.length === 1 && body.data[0].ocd_id === ocd(CONF),
      JSON.stringify(body.data.map((c: { ocd_id: string }) => c.ocd_id)),
    );
    assert(
      "CONFLICTS: the RESOLVED conflict (W-RESOLVED) is ABSENT from the live feed",
      body.data.every((c: { ocd_id: string }) => c.ocd_id !== ocd(RESOLVED)),
    );
    assert(
      "CONFLICTS: resolved_at is NEVER present on a returned conflict",
      body.data.every((c: Record<string, unknown>) => !("resolved_at" in c)),
      JSON.stringify(Object.keys(body.data[0] ?? {})),
    );
    assert(
      "CONFLICTS: pagination.total counts only live conflicts (1)",
      body.pagination.total === 1,
      String(body.pagination.total),
    );
    // ocd_id filter narrows to a specific (live) conflict.
    const filtered = await app.inject({
      method: "GET",
      url: `/v1/conflicts?ocd_id=${ocd(CONF)}`,
      headers: { "x-api-key": "test-key" },
    });
    assert(
      "CONFLICTS: ocd_id filter returns the matching live conflict",
      filtered.json().data.length === 1 &&
        filtered.json().data[0].ocd_id === ocd(CONF),
    );
  }

  // ── /openapi.json — a real OpenAPI 3.1 doc generated from the Zod schemas ──────────────────────────
  {
    const r = await app.inject({ method: "GET", url: "/openapi.json" });
    const doc = r.json();
    assert(
      "OPENAPI: openapi version starts with 3.1",
      typeof doc.openapi === "string" && doc.openapi.startsWith("3.1"),
      String(doc.openapi),
    );
    assert(
      "OPENAPI: info.title + version reflect the API",
      doc.info?.title === "DocketClock API" &&
        doc.info?.version === API_VERSION,
      JSON.stringify(doc.info),
    );
    const paths = Object.keys(doc.paths ?? {});
    assert(
      "OPENAPI: has a path for /v1/windows",
      paths.includes("/v1/windows"),
      paths.join(","),
    );
    assert(
      "OPENAPI: has a path for the /v1/windows wildcard detail route",
      paths.some((p) => p.startsWith("/v1/windows/")),
      paths.join(","),
    );
    assert(
      "OPENAPI: has a path for /v1/conflicts",
      paths.includes("/v1/conflicts"),
      paths.join(","),
    );
    // Spec ⇄ response: the published /v1/windows 200 schema carries the envelope (disclaimer field).
    const winSchema =
      doc.paths?.["/v1/windows"]?.get?.responses?.["200"]?.content?.[
        "application/json"
      ]?.schema;
    assert(
      "OPENAPI: the /v1/windows 200 schema is the contract envelope (has disclaimer + data + pagination)",
      !!winSchema?.properties?.disclaimer &&
        !!winSchema?.properties?.data &&
        !!winSchema?.properties?.pagination,
      JSON.stringify(Object.keys(winSchema?.properties ?? {})),
    );
    // Fix #7: the spec must publish the 400 these routes actually return (bad filter / negative page).
    const winResponses = doc.paths?.["/v1/windows"]?.get?.responses ?? {};
    assert(
      "FIX#7: /v1/windows publishes a 400 response in the spec",
      "400" in winResponses,
      JSON.stringify(Object.keys(winResponses)),
    );
    const confResponses = doc.paths?.["/v1/conflicts"]?.get?.responses ?? {};
    assert(
      "FIX#7: /v1/conflicts publishes a 400 response in the spec",
      "400" in confResponses,
      JSON.stringify(Object.keys(confResponses)),
    );
  }
} finally {
  await app.close();
  await sql.end();
}

console.log("\n=== api results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
