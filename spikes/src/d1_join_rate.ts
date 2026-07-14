/**
 * D1 — frDocNum join hit-rate  (MASTER GATE)
 *
 * Q: On the live corpus, what fraction of comment-open documents join FR <-> Regulations.gov on
 *    frDocNum / document_number?
 * Gates: the entire reconciliation join strategy.
 *
 * Method (see docs/plans/week1-validation-spikes.md § D1):
 *   1. FR open set (keyless): GET federalregister.gov/api/v1/documents.json
 *      ?conditions[comment_date][gte]=<today> with fields document_number, comments_close_on,
 *      docket_ids, regulations_dot_gov_info, type, action, title  -> data/fr_open.json
 *   2. Regs.gov open set (REGS_API_KEY, paged, <=1000/hr): GET api.regulations.gov/v4/documents
 *      filter[commentEndDate][ge]=today (VERIFIED against live OpenAPI: [ge], not [gte]) -> data/regs_open.json
 *   3. DuckDB LEFT JOIN regs_open.frDocNum = fr_open.document_number; compute hit_pct.
 *   4. For misses, measure fallback join on docket_id-array overlap.
 *
 * Decision rule:
 *   hit_pct >= 60%  -> GO with frDocNum primary key.
 *   hit_pct <  60%  -> PIVOT to Regs.gov-primary + docket_id/RIN fallback; FR-only records get
 *                      confidence=medium, conflict_reason="no_cross_source_join".
 *
 * Output: out/D1_join_rate.md  (regs_open / joined / hit_pct + fallback rate)
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  DATA_DIR,
  RateLimiter,
  fetchJson,
  qs,
  rows,
  today,
  withDuckDB,
  writeData,
  writeOut,
} from "./_shared.js";

const REGS_API_KEY = process.env.REGS_API_KEY || "DEMO_KEY";
const FROM = today(); // Eastern calendar date; open = comment window not yet closed

// ---- FR open-comment set (keyless) ---------------------------------------

interface FrDoc {
  document_number: string;
  comments_close_on: string | null;
  docket_ids: string[] | null;
  type: string | null;
  action: string | null;
  title: string | null;
}

async function pullFr(): Promise<FrDoc[]> {
  const fields = [
    "document_number",
    "comments_close_on",
    "docket_ids",
    "regulations_dot_gov_info",
    "type",
    "action",
    "title",
  ];
  const base = "https://www.federalregister.gov/api/v1/documents.json";
  const first =
    `${base}?` +
    qs({ per_page: 1000, "conditions[comment_date][gte]": FROM }) +
    "&" +
    fields.map((f) => `${encodeURIComponent("fields[]")}=${f}`).join("&");

  const out: FrDoc[] = [];
  let url: string | null = first;
  let page = 0;
  const MAX_PAGES = 60;
  while (url && page < MAX_PAGES) {
    const res: {
      count: number;
      results?: FrDoc[];
      next_page_url?: string | null;
    } = await fetchJson(url);
    if (page === 0) console.log(`  FR reports count=${res.count}`);
    for (const r of res.results ?? []) out.push(r);
    url = res.next_page_url ?? null;
    page++;
    console.log(
      `  FR page ${page}: +${res.results?.length ?? 0} (total ${out.length})`,
    );
  }
  return out;
}

// ---- Regs.gov open-comment set (REGS_API_KEY, lastModifiedDate cursor) -------

interface RegsDocRaw {
  id: string;
  attributes: {
    frDocNum: string | null;
    docketId: string | null;
    commentEndDate: string | null;
    documentType: string | null;
    title: string | null;
    lastModifiedDate: string | null;
  };
}
interface RegsDoc {
  id: string;
  frDocNum: string | null;
  docketId: string | null;
  commentEndDate: string | null;
  documentType: string | null;
  title: string | null;
}

async function pullRegs(): Promise<RegsDoc[]> {
  const limiter = RateLimiter.perHour(900); // stay safely under the 1,000/hr ceiling
  const base = "https://api.regulations.gov/v4/documents";
  const PAGE_SIZE = 250;
  const seen = new Map<string, RegsDoc>();
  // Regs.gov caps page[number] at 20 (5,000 records). Beyond that, advance a
  // lastModifiedDate cursor and restart paging, deduping by id.
  let cursor: string | null = null; // filter[lastModifiedDate][ge]
  for (let round = 0; round < 50; round++) {
    let pageAdded = 0;
    let lastSeenLmd: string | null = null;
    for (let pageNum = 1; pageNum <= 20; pageNum++) {
      const params: Record<string, string | number> = {
        "filter[commentEndDate][ge]": FROM,
        "page[size]": PAGE_SIZE,
        "page[number]": pageNum,
        sort: "lastModifiedDate",
      };
      if (cursor) params["filter[lastModifiedDate][ge]"] = cursor;
      const url = `${base}?${qs(params)}`;
      const res = await fetchJson<{
        data?: RegsDocRaw[];
        meta?: { totalElements?: number };
      }>(url, { headers: { "X-Api-Key": REGS_API_KEY }, limiter });
      const data = res.data ?? [];
      if (round === 0 && pageNum === 1) {
        console.log(
          `  Regs reports totalElements=${res.meta?.totalElements ?? "?"}`,
        );
      }
      for (const d of data) {
        const doc: RegsDoc = {
          id: d.id,
          frDocNum: d.attributes.frDocNum,
          docketId: d.attributes.docketId,
          commentEndDate: d.attributes.commentEndDate,
          documentType: d.attributes.documentType,
          title: d.attributes.title,
        };
        if (!seen.has(doc.id)) {
          seen.set(doc.id, doc);
          pageAdded++;
        }
        lastSeenLmd = d.attributes.lastModifiedDate ?? lastSeenLmd;
      }
      console.log(
        `  Regs round ${round} page ${pageNum}: +${data.length} (total ${seen.size})`,
      );
      if (data.length < PAGE_SIZE) {
        // exhausted this cursor window
        return [...seen.values()];
      }
    }
    // Hit the 20-page wall. Advance the cursor and keep going.
    if (!lastSeenLmd || pageAdded === 0) break;
    cursor = lastSeenLmd.slice(0, 19).replace("T", " "); // 'YYYY-MM-DD HH:mm:ss'
  }
  return [...seen.values()];
}

// ---- Join + report --------------------------------------------------------

async function main(): Promise<void> {
  if ((process.env.REGS_API_KEY ?? "") === "") {
    console.warn(
      "WARNING: REGS_API_KEY not set; using DEMO_KEY (heavily rate-limited — pagination will likely stall).\n" +
        "         Get a free key at https://api.data.gov/signup/ and put it in the repo-root .env",
    );
  }
  console.log(`D1: open-comment cutoff = ${FROM} (Eastern)\n`);

  // D1_USE_CACHE=1 re-runs the join/report over the last pull in data/ without hitting the APIs
  // (handy for iterating on the analysis or when the Regs.gov hourly budget is spent).
  const useCache = process.env.D1_USE_CACHE === "1";
  let fr: FrDoc[];
  let regs: RegsDoc[];
  if (
    useCache &&
    existsSync(resolve(DATA_DIR, "fr_open.json")) &&
    existsSync(resolve(DATA_DIR, "regs_open.json"))
  ) {
    console.log(
      "D1_USE_CACHE=1 — loading data/fr_open.json + data/regs_open.json (no API calls)\n",
    );
    fr = JSON.parse(readFileSync(resolve(DATA_DIR, "fr_open.json"), "utf8"));
    regs = JSON.parse(
      readFileSync(resolve(DATA_DIR, "regs_open.json"), "utf8"),
    );
  } else {
    console.log("Pulling FR open set (keyless)...");
    fr = await pullFr();
    writeData("fr_open.json", fr);
    console.log(`  -> ${fr.length} FR docs saved to data/fr_open.json\n`);

    console.log("Pulling Regs.gov open set...");
    regs = await pullRegs();
    writeData("regs_open.json", regs);
    console.log(`  -> ${regs.length} Regs docs saved to data/regs_open.json\n`);
  }

  if (regs.length === 0) {
    throw new Error(
      "Regs.gov returned 0 docs — almost certainly a missing/invalid REGS_API_KEY or rate-limit. " +
        "Set a real key in the repo-root .env and re-run.",
    );
  }

  console.log("Computing join rate in DuckDB...");
  const stats = await withDuckDB(async (conn) => {
    await conn.run(
      `CREATE TABLE fr_open AS SELECT * FROM read_json_auto('${DATA_DIR}/fr_open.json');`,
    );
    await conn.run(
      `CREATE TABLE regs_open AS SELECT * FROM read_json_auto('${DATA_DIR}/regs_open.json');`,
    );

    const [primary] = await rows<{
      regs_open: bigint;
      has_frdocnum: bigint;
      joined: bigint;
      hit_pct: number;
      hit_pct_of_frdocnum: number | null;
    }>(
      conn,
      `SELECT
         count(*)                                                            AS regs_open,
         count(*) FILTER (WHERE r.frDocNum IS NOT NULL)                      AS has_frdocnum,
         count(*) FILTER (WHERE fr.document_number IS NOT NULL)              AS joined,
         round(100.0 * count(*) FILTER (WHERE fr.document_number IS NOT NULL) / count(*), 1) AS hit_pct,
         round(100.0 * count(*) FILTER (WHERE fr.document_number IS NOT NULL)
               / nullif(count(*) FILTER (WHERE r.frDocNum IS NOT NULL), 0), 1)               AS hit_pct_of_frdocnum
       FROM regs_open r
       LEFT JOIN fr_open fr ON r.frDocNum = fr.document_number;`,
    );

    // Fallback: of the frDocNum misses, how many recover via docketId ∈ fr.docket_ids?
    const [fallback] = await rows<{
      misses: bigint;
      miss_null_frdoc: bigint;
      recovered_by_docket: bigint;
      combined_pct: number;
    }>(
      conn,
      `WITH miss AS (
         SELECT r.* FROM regs_open r
         LEFT JOIN fr_open fr ON r.frDocNum = fr.document_number
         WHERE fr.document_number IS NULL
       ),
       recovered AS (
         SELECT DISTINCT m.id
         FROM miss m
         JOIN fr_open fr ON m.docketId IS NOT NULL
           AND fr.docket_ids IS NOT NULL
           AND list_contains(fr.docket_ids, m.docketId)
       )
       SELECT
         (SELECT count(*) FROM miss)                                         AS misses,
         (SELECT count(*) FROM miss WHERE frDocNum IS NULL)                  AS miss_null_frdoc,
         (SELECT count(*) FROM recovered)                                    AS recovered_by_docket,
         round(100.0 * (
           (SELECT count(*) FROM regs_open r JOIN fr_open fr ON r.frDocNum = fr.document_number)
           + (SELECT count(*) FROM recovered)
         ) / (SELECT count(*) FROM regs_open), 1)                            AS combined_pct;`,
    );

    return { primary, fallback };
  });

  const p = stats.primary!;
  const f = stats.fallback!;
  const hitPct = Number(p.hit_pct);
  const verdict =
    hitPct >= 60
      ? "GO — frDocNum as primary reconciliation key"
      : "PIVOT — Regs.gov-primary + docket_id/RIN fallback";

  const md = `# D1 — frDocNum join hit-rate

**Run:** ${today()} (Eastern) · open-comment cutoff \`commentEndDate / comment_date >= ${FROM}\`
**Regs key:** ${process.env.REGS_API_KEY ? "real REGS_API_KEY" : "DEMO_KEY (smoke test only)"}

## Primary join (regs.frDocNum = fr.document_number)

| metric | value |
| --- | ---: |
| Regs.gov open docs | ${p.regs_open} |
| …with a non-null frDocNum | ${p.has_frdocnum} |
| joined to an FR document | ${p.joined} |
| **hit_pct** (joined / all open) | **${p.hit_pct}%** |
| hit_pct among docs that *have* a frDocNum | ${p.hit_pct_of_frdocnum ?? "n/a"}% |

## Fallback (docket_id array overlap, for the misses)

| metric | value |
| --- | ---: |
| frDocNum misses | ${f.misses} |
| …of which carry **no frDocNum at all** | ${f.miss_null_frdoc} |
| recovered via docketId ∈ fr.docket_ids | ${f.recovered_by_docket} |
| **combined coverage** (frDocNum + docket) | **${f.combined_pct}%** |

> **Interpretation:** the docket fallback is measured against the *open* FR set only, so it recovers
> little — ${f.miss_null_frdoc}/${f.misses} misses have a null frDocNum and are mostly stale,
> perpetually-open Regs dockets (e.g. \`*-2007-*\` with far-future commentEndDate) whose FR notice is
> years old and not in today's open pull. A production fallback would join against the *full* FR
> corpus, not just the open window. Treat \`combined coverage\` here as a conservative floor.
>
> RIN fallback not computed: Regs.gov exposes RIN at the *docket* level, not on the document record,
> so a document-level RIN join needs a second \`/v4/dockets\` pull. docketId overlap is the cheap proxy.

## Decision

**hit_pct = ${p.hit_pct}% → ${verdict}**

- Rule: \`hit_pct ≥ 60%\` → GO frDocNum-primary; \`< 60%\` → PIVOT to Regs.gov-primary with
  docket_id-array-overlap + RIN; FR-only records carry \`confidence=medium,
  conflict_reason="no_cross_source_join"\`.
${hitPct < 60 ? `- Note: combined frDocNum+docket coverage is ${f.combined_pct}%, which is the realistic ceiling for the pivoted join.` : `- Note: a meaningful share of open Regs docs carry no frDocNum at all (${p.regs_open} open, ${p.has_frdocnum} with frDocNum); the docket fallback still matters for those even under GO.`}

_Artifacts: \`data/fr_open.json\` (${fr.length} rows), \`data/regs_open.json\` (${regs.length} rows)._
`;

  const outPath = writeOut("D1_join_rate.md", md);
  console.log(`\n=== D1 RESULT ===`);
  console.log(
    `regs_open=${p.regs_open}  joined=${p.joined}  hit_pct=${p.hit_pct}%  combined=${f.combined_pct}%`,
  );
  console.log(`Verdict: ${verdict}`);
  console.log(`Wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
