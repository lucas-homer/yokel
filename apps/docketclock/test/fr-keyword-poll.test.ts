/**
 * fr-keyword-poll.test.ts — proves Slice 2 (#26): FR KEYWORD discovery for amendment notices
 * (extension / correction / reopening / WITHDRAWAL) that carry NO open comment_date and so are invisible
 * to the open-comment discovery query. These notices must still be ingested through the existing
 * append-only path so the #31 chain-reconcile pass (Slice 3) has them in the observation log.
 *
 * Same harness as fr-poll.test.ts: hand-rolled assert, out[] accumulator, failures counter, process.exit;
 * the DB section is guarded by a THROWAWAY Postgres:
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 *
 * The network + clock are INJECTED (FrPollDeps fakes) — nothing hits the wire. The list fakes are
 * SERVER-HONORING: `listPage` returns the open-comment set; `listKeywordPage` returns docs whose backing
 * metadata matches the requested amendment `term` AND whose publicationDate >= the lookback bound,
 * paginated by perPage/page, newest-first. Detail payloads are built from the captured FR fixture.
 *
 * Coverage:
 *   - UNIT: frKeywordListUrl emits conditions[term], the publication_date][gte] lookback bound,
 *     order=newest, the two fields[]; easternDateDaysAgo offsets in Eastern;
 *   - UNION + DEDUPE: open=[A,B], keyword=[B,C] → A,B,C fetched exactly once each (B not double-fetched);
 *   - AMENDMENT-ONLY INGEST: a withdrawal that appears ONLY in the keyword set is fetched + ingested
 *     (is_withdrawal=true) + reconciled — the load-bearing Slice-3 prerequisite;
 *   - DIFFERENTIAL-BY-LOG: a keyword doc already in the log is skipped (no re-fetch);
 *   - DEAD-LETTER: a permanently-failing keyword-discovered doc dead-letters after maxFailAttempts;
 *   - PAGING: a full keyword page triggers a next-page fetch; a short page stops.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  frKeywordListUrl,
  easternDateDaysAgo,
} from "../src/sources/federal-register.js";
import { pollFrOnce, type FrPollDeps } from "../src/poll/fr-poll.js";

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

const SOURCE = "federal_register";

function frDetail(
  documentNumber: string,
  overrides: Record<string, unknown> = {},
): unknown {
  const raw = JSON.parse(JSON.stringify(frFixture)) as Record<string, unknown>;
  raw.document_number = documentNumber;
  Object.assign(raw, overrides);
  return raw;
}

/** One doc in the backing corpus: which discovery set(s) surface it, plus the detail it would return. */
interface FakeDoc {
  documentNumber: string;
  publicationDate: string;
  /** comment cutoff; absent/empty => never in the open-comment set (the amendment-notice shape). */
  commentsCloseOn?: string;
  /** amendment terms this doc matches in the keyword full-text search (its appearance in the keyword set). */
  terms?: string[];
  /** override the detail title so noticeFlags() lights the right flag (e.g. a withdrawal title). */
  title?: string;
  regsDocumentId?: string | null;
}

/**
 * A server-honoring FrPollDeps fake spanning BOTH discovery queries.
 *  - listPage: the open-comment set (commentsCloseOn >= commentOpenOnOrAfter), paginated, newest-first.
 *  - listKeywordPage: docs whose `terms` include the requested term AND publicationDate >= the lookback
 *    bound, paginated, newest-first. Throws like FR's HTTP 400 if page*perPage > 10,000.
 *  - fetchDetail: counts calls per doc (to prove single-fetch + skip), failOn throws for chosen docs.
 */
function serverFake(opts: {
  now: Date;
  set: FakeDoc[];
  failOn?: Set<string>;
  fetchCalls?: Map<string, number>;
  keywordReqs?: Array<{
    term: string;
    publicationDateOnOrAfter: string;
    page: number;
  }>;
}): Partial<FrPollDeps> {
  return {
    now: () => opts.now,
    sleep: async () => {},
    listPage: async (req) => {
      const { commentOpenOnOrAfter, perPage, page } = req;
      if (page * perPage > 10_000)
        throw new Error(`FR 400: page*per_page (${page * perPage}) > 10,000`);
      const open = opts.set
        .filter(
          (d) =>
            !!d.commentsCloseOn && d.commentsCloseOn >= commentOpenOnOrAfter,
        )
        .sort((a, b) => b.publicationDate.localeCompare(a.publicationDate));
      const start = (page - 1) * perPage;
      return open.slice(start, start + perPage).map((d) => ({
        documentNumber: d.documentNumber,
        publicationDate: d.publicationDate,
      }));
    },
    listKeywordPage: async (req) => {
      const { term, publicationDateOnOrAfter, perPage, page } = req;
      if (page * perPage > 10_000)
        throw new Error(`FR 400: page*per_page (${page * perPage}) > 10,000`);
      if (opts.keywordReqs)
        opts.keywordReqs.push({ term, publicationDateOnOrAfter, page });
      const matched = opts.set
        .filter((d) => (d.terms ?? []).includes(term))
        .filter((d) => d.publicationDate >= publicationDateOnOrAfter)
        .sort((a, b) => b.publicationDate.localeCompare(a.publicationDate));
      const start = (page - 1) * perPage;
      return matched.slice(start, start + perPage).map((d) => ({
        documentNumber: d.documentNumber,
        publicationDate: d.publicationDate,
      }));
    },
    fetchDetail: async (documentNumber: string) => {
      if (opts.fetchCalls)
        opts.fetchCalls.set(
          documentNumber,
          (opts.fetchCalls.get(documentNumber) ?? 0) + 1,
        );
      if (opts.failOn?.has(documentNumber))
        throw new Error(`synthetic fetch failure for ${documentNumber}`);
      const doc = opts.set.find((x) => x.documentNumber === documentNumber);
      if (!doc) throw new Error(`serverFake: no detail for ${documentNumber}`);
      const overrides: Record<string, unknown> = {};
      if (doc.commentsCloseOn)
        overrides.comments_close_on = doc.commentsCloseOn;
      if (doc.title !== undefined) overrides.title = doc.title;
      if (doc.regsDocumentId !== undefined) {
        overrides.regulations_dot_gov_info =
          doc.regsDocumentId === null
            ? null
            : { document_id: doc.regsDocumentId };
      }
      return frDetail(documentNumber, overrides);
    },
  };
}

const NOW = new Date("2026-06-01T12:00:00Z"); // Eastern: 2026-06-01

// ── UNIT: frKeywordListUrl + easternDateDaysAgo ──────────────────────────────────────────────────────
{
  const base = "https://fr.example/api/v1";
  const u = new URL(
    frKeywordListUrl({
      term: "withdrawal",
      publicationDateOnOrAfter: "2026-02-01",
      base,
    }),
  );
  assert(
    "frKeywordListUrl: sets conditions[term] to the amendment keyword",
    u.searchParams.get("conditions[term]") === "withdrawal",
    u.searchParams.get("conditions[term]") ?? "missing",
  );
  assert(
    "frKeywordListUrl: sets conditions[publication_date][gte] to the lookback bound (BOUNDED — unlike the open set)",
    u.searchParams.get("conditions[publication_date][gte]") === "2026-02-01",
    u.searchParams.get("conditions[publication_date][gte]") ?? "missing",
  );
  assert(
    "frKeywordListUrl: order=newest (keep newest amendments IF ever truncated)",
    u.searchParams.get("order") === "newest",
    u.searchParams.get("order") ?? "missing",
  );
  assert(
    "frKeywordListUrl: per_page defaults to 1000 (FR max)",
    u.searchParams.get("per_page") === "1000",
    u.searchParams.get("per_page") ?? "missing",
  );
  assert(
    "frKeywordListUrl: fields[] includes document_number and publication_date (same as the open-set query)",
    u.searchParams.getAll("fields[]").includes("document_number") &&
      u.searchParams.getAll("fields[]").includes("publication_date"),
    u.searchParams.getAll("fields[]").join(","),
  );
  // EXACT query string (param order-independent assertion): every required key present, no comment_date.
  assert(
    "frKeywordListUrl: does NOT set conditions[comment_date][gte] (that is the OPEN-set query, not keyword)",
    u.searchParams.get("conditions[comment_date][gte]") === null,
  );

  assert(
    "easternDateDaysAgo: 120 days before 2026-06-01 Eastern is 2026-02-01",
    easternDateDaysAgo(120, NOW) === "2026-02-01",
    easternDateDaysAgo(120, NOW),
  );
}

const sql = createClient();
try {
  // ── UNION + DEDUPE: open=[A,B], keyword=[B,C] → A,B,C fetched once each (B not double-fetched) ────────
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const fetchCalls = new Map<string, number>();
    const set: FakeDoc[] = [
      // A: open only
      {
        documentNumber: "2026-A0001",
        publicationDate: "2026-05-20",
        commentsCloseOn: "2026-08-01",
        regsDocumentId: null,
      },
      // B: in BOTH sets (open AND keyword 'extension') — the overlap that must dedupe to one fetch
      {
        documentNumber: "2026-B0002",
        publicationDate: "2026-05-21",
        commentsCloseOn: "2026-08-02",
        terms: ["extension"],
        title: "Notice; extension of comment period",
        regsDocumentId: null,
      },
      // C: keyword only (correction notice, no open comment_date)
      {
        documentNumber: "2026-C0003",
        publicationDate: "2026-05-22",
        terms: ["correction"],
        title: "Correction to a prior notice",
        regsDocumentId: null,
      },
    ];
    const s = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }),
      {},
    );
    assert(
      "UNION: listed reflects the deduped union size (A,B,C = 3)",
      s.listed === 3,
      String(s.listed),
    );
    assert(
      "UNION: keywordListed counts the keyword-set contribution (B,C = 2)",
      s.keywordListed === 2,
      String(s.keywordListed),
    );
    assert(
      "UNION: all three fetched + ingested exactly once",
      s.fetched === 3 &&
        s.ingested === 3 &&
        (fetchCalls.get("2026-A0001") ?? 0) === 1 &&
        (fetchCalls.get("2026-B0002") ?? 0) === 1 &&
        (fetchCalls.get("2026-C0003") ?? 0) === 1,
      `fetched=${s.fetched} ingested=${s.ingested} B=${fetchCalls.get("2026-B0002")}`,
    );
    assert(
      "UNION: the overlap doc B was fetched ONCE, not double-fetched across the two sets",
      (fetchCalls.get("2026-B0002") ?? 0) === 1,
      String(fetchCalls.get("2026-B0002")),
    );
  }

  // ── AMENDMENT-ONLY INGEST: a withdrawal present ONLY in the keyword set is fetched + ingested + reconciled
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const docWithdrawal = "2026-WD001";
    const set: FakeDoc[] = [
      {
        documentNumber: docWithdrawal,
        publicationDate: "2026-05-25",
        // NO commentsCloseOn → never in the open set; ONLY discoverable via the keyword path
        terms: ["withdrawal"],
        title: "Withdrawal of proposed rule and comment period",
        regsDocumentId: null,
      },
    ];
    const s = await pollFrOnce(sql, serverFake({ now: NOW, set }), {});
    assert(
      "AMENDMENT-ONLY: a withdrawal with NO open comment_date is discovered via keyword (listed=1, fetched=1, ingested=1)",
      s.listed === 1 && s.fetched === 1 && s.ingested === 1,
      `listed=${s.listed} fetched=${s.fetched} ingested=${s.ingested}`,
    );
    const [obs] = await sql<
      { fr_document_number: string; is_withdrawal: boolean }[]
    >`
      select fr_document_number, is_withdrawal from observations
      where source = ${SOURCE} and fr_document_number = ${docWithdrawal}
    `;
    assert(
      "AMENDMENT-ONLY: the withdrawal landed an observation in the append-only log (Slice-3 prerequisite)",
      !!obs && obs.fr_document_number === docWithdrawal,
      String(obs?.fr_document_number),
    );
    assert(
      "AMENDMENT-ONLY: the observation carries is_withdrawal=true (noticeFlags lit it from the title)",
      obs?.is_withdrawal === true,
      String(obs?.is_withdrawal),
    );
    const [win] = await sql<{ ocd_id: string }[]>`
      select ocd_id from participation_windows
      where ocd_id = ${`ocd-participation-window/federal/${docWithdrawal}`}
    `;
    assert(
      "AMENDMENT-ONLY: reconcile ran — a window exists for the keyword-discovered doc",
      !!win,
      String(win?.ocd_id),
    );
  }

  // ── DIFFERENTIAL-BY-LOG: a keyword doc already in the log is SKIPPED (no re-fetch) ───────────────────
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const docKw = "2026-KW777";
    const set: FakeDoc[] = [
      {
        documentNumber: docKw,
        publicationDate: "2026-05-26",
        terms: ["reopening"],
        title: "Reopening of the comment period",
        regsDocumentId: null,
      },
    ];
    const fetchCalls = new Map<string, number>();
    const s1 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }),
      {},
    );
    assert(
      "DIFFERENTIAL(kw): first cycle fetches + ingests the keyword doc",
      s1.fetched === 1 && s1.ingested === 1,
      `fetched=${s1.fetched} ingested=${s1.ingested}`,
    );
    const fetchesAfter1 = fetchCalls.get(docKw) ?? 0;
    const s2 = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, fetchCalls }),
      {},
    );
    assert(
      "DIFFERENTIAL(kw): second cycle SKIPS the already-in-log keyword doc (fetched=0, skipped=1)",
      s2.fetched === 0 &&
        s2.ingested === 0 &&
        s2.skipped === 1 &&
        s2.listed === 1,
      `fetched=${s2.fetched} skipped=${s2.skipped} listed=${s2.listed}`,
    );
    assert(
      "DIFFERENTIAL(kw): fetchDetail was NOT called again for the seen keyword doc",
      (fetchCalls.get(docKw) ?? 0) === fetchesAfter1,
      `${fetchCalls.get(docKw)} vs ${fetchesAfter1}`,
    );
  }

  // ── DEAD-LETTER: a permanently-failing keyword-discovered doc dead-letters after maxFailAttempts ─────
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const docFail = "2026-KWDL01";
    const maxFailAttempts = 3;
    const set: FakeDoc[] = [
      {
        documentNumber: docFail,
        publicationDate: "2026-05-27",
        terms: ["withdrawal"],
        title: "Withdrawal notice",
        regsDocumentId: null,
      },
    ];
    const fetchCalls = new Map<string, number>();
    let dl;
    for (let cycle = 1; cycle <= maxFailAttempts; cycle++) {
      dl = await pollFrOnce(
        sql,
        serverFake({ now: NOW, set, failOn: new Set([docFail]), fetchCalls }),
        { maxFailAttempts },
      );
    }
    assert(
      "DEAD-LETTER(kw): a keyword-discovered doc dead-letters on the Nth consecutive failure",
      dl!.deadLettered === 1,
      String(dl!.deadLettered),
    );
    assert(
      "DEAD-LETTER(kw): fetch-attempted exactly N times across the N failing cycles",
      (fetchCalls.get(docFail) ?? 0) === maxFailAttempts,
      String(fetchCalls.get(docFail)),
    );
    const [row] = await sql<
      { attempts: number; dead_lettered_at: Date | null }[]
    >`
      select attempts, dead_lettered_at from poll_dead_letter
      where source = ${SOURCE} and document_key = ${docFail}
    `;
    assert(
      "DEAD-LETTER(kw): a ledger row exists with dead_lettered_at set and attempts >= N",
      !!row && row.dead_lettered_at !== null && row.attempts >= maxFailAttempts,
      `attempts=${row?.attempts} dl=${row?.dead_lettered_at}`,
    );
    // A subsequent cycle (no failOn) within the slow-retry window SKIPS it from the hot path (no re-fetch).
    const fetchesAtDL = fetchCalls.get(docFail) ?? 0;
    const soon = new Date(NOW.getTime() + 60 * 60 * 1000);
    const sSoon = await pollFrOnce(
      sql,
      serverFake({ now: soon, set, fetchCalls }),
      { maxFailAttempts },
    );
    assert(
      "DEAD-LETTER(kw): a dead-lettered keyword doc is SKIPPED on the hot path (no re-fetch)",
      sSoon.fetched === 0 &&
        sSoon.skipped === 1 &&
        (fetchCalls.get(docFail) ?? 0) === fetchesAtDL,
      `fetched=${sSoon.fetched} skipped=${sSoon.skipped} calls=${fetchCalls.get(docFail)}`,
    );
  }

  // ── PAGING: a full keyword page triggers a next-page fetch; a short page stops ──────────────────────
  {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    const perPage = 2;
    // 3 'extension' docs at perPage=2 → page1 returns 2 (full) → page2 returns 1 (short, stop).
    const set: FakeDoc[] = [];
    for (let i = 1; i <= 3; i++) {
      set.push({
        documentNumber: `2026-PG00${i}`,
        publicationDate: `2026-05-1${i}`,
        terms: ["extension"],
        title: "Extension of the comment period",
        regsDocumentId: null,
      });
    }
    const keywordReqs: Array<{
      term: string;
      publicationDateOnOrAfter: string;
      page: number;
    }> = [];
    const s = await pollFrOnce(
      sql,
      serverFake({ now: NOW, set, keywordReqs }),
      { perPage, maxPages: 10 },
    );
    const extReqs = keywordReqs.filter((r) => r.term === "extension");
    assert(
      "PAGING(kw): the full first 'extension' page triggered a second-page fetch (pages 1 and 2 requested)",
      extReqs.some((r) => r.page === 1) && extReqs.some((r) => r.page === 2),
      extReqs.map((r) => r.page).join(","),
    );
    assert(
      "PAGING(kw): the short second page STOPPED paging — no page 3 for 'extension'",
      !extReqs.some((r) => r.page === 3),
      extReqs.map((r) => r.page).join(","),
    );
    assert(
      "PAGING(kw): all 3 keyword docs discovered + ingested across the two pages",
      s.keywordListed === 3 && s.ingested === 3,
      `keywordListed=${s.keywordListed} ingested=${s.ingested}`,
    );
    assert(
      "PAGING(kw): every keyword request carried the lookback publication_date bound (120d before NOW)",
      extReqs.every(
        (r) => r.publicationDateOnOrAfter === easternDateDaysAgo(120, NOW),
      ),
      extReqs.map((r) => r.publicationDateOnOrAfter).join(","),
    );
  }
} finally {
  await sql.end();
}

console.log("\n=== fr-keyword-poll results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
