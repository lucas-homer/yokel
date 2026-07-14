/**
 * xcheck.ts — the OFFLINE cross-check: does an independent bulk dataset agree with our live windows?
 * (Slice V, PR-V2 — plans/verification-accuracy.md.)
 *
 * Joins the spicy-regs Parquet mirror of Regulations.gov (civictechdc/spicy-regs, published to a
 * public R2 bucket — the `SPICY_REGS_PARQUET` hook `README.md` documented since week 1) against a
 * read-only JSONL export of the live `participation_windows` projection, and diffs:
 *   • the CLOSE, compared as America/New_York calendar dates (the same Eastern-date normalization
 *     the reconcile engine uses — a 1-UTC-day gap on the same Eastern date is NOT a disagreement),
 *   • the STATUS, on the one signal the mirror carries: `withdrawn`.
 *
 * Architecture rule (docs/architecture/docketclock.md): Mirrulations/spicy-regs is an OFFLINE
 * eval/seed asset only, never a live freshness source — so this is a batch differential run by hand
 * on a cadence, not a third adapter. The mirror can lag live Regulations.gov, which is exactly why
 * every disagreement gets a hand-filled `triage` value instead of an automated verdict:
 *   our_bug      — the live projection is wrong. A find: export it with export-accuracy-miss and
 *                  commit the replay fixture (the miss-to-regression-test loop).
 *   bulk_stale   — the mirror lags the live source (compare `parquet_modified` vs `derived_at`).
 *   source_drift — the sources themselves changed/disagree (e.g. Regs.gov edited a row in place).
 *
 * The diff file is CHECKED IN (`spikes/out/XCHECK_diff.md` is un-gitignored): an unfilled triage
 * column in the committed file IS the reminder that a pass is not done. Re-runs carry forward the
 * hand-filled triage of any disagreement that persists — keyed by (ocd_id, category), so a finding
 * that CHANGES category is treated as new, never silently inheriting a stale triage — and a
 * monthly re-run never clobbers finished triage work. When hand-editing notes, spell a literal
 * pipe as `\|` (markdown-standard): a raw `|` breaks the table AND shifts this parser's cells on
 * the next run (self-heals after — the writer re-escapes — but that one row's triage is lost).
 *
 * Pure logic (classification, triage parsing, Eastern dates) lives in xcheck-lib.ts and is
 * unit-tested in CI via xcheck.test.ts; this file is the side-effectful pass.
 *
 * Run:  pnpm --filter @yokel/docketclock export:windows   # → data/windows.jsonl (live export)
 *       pnpm --filter @yokel/spikes xcheck                # → out/XCHECK_diff.md
 * Env:  SPICY_REGS_PARQUET — parquet URL/glob for the documents table
 *                            (default https://r2.spicy-regs.dev/documents.parquet)
 *       WINDOWS_JSONL      — the live export (default data/windows.jsonl)
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { DATA_DIR, OUT_DIR, withDuckDB, rows, writeOut } from "./_shared.js";
import {
  type Category,
  type Finding,
  type JoinedRow,
  classify,
  easternDate,
  parseTriage,
  sqlLit,
  triageKey,
} from "./xcheck-lib.js";

const PARQUET =
  process.env.SPICY_REGS_PARQUET ??
  "https://r2.spicy-regs.dev/documents.parquet";
const WINDOWS_JSONL =
  process.env.WINDOWS_JSONL ?? resolve(DATA_DIR, "windows.jsonl");
const OUT_NAME = "XCHECK_diff.md";

async function main(): Promise<void> {
  if (!existsSync(WINDOWS_JSONL))
    throw new Error(
      `${WINDOWS_JSONL} not found — run \`pnpm --filter @yokel/docketclock export:windows\` first`,
    );
  console.log(`windows: ${WINDOWS_JSONL}`);
  console.log(`parquet: ${PARQUET}`);

  const { joined, totals } = await withDuckDB(async (conn) => {
    await conn.run("INSTALL httpfs; LOAD httpfs;");
    // Explicit columns= — auto-detect would infer the ISO-UTC strings as NAIVE TIMESTAMPs and
    // re-serialize them without the Z, which JS Date then parses as LOCAL time: every close would
    // drift one calendar day and the whole diff would be false mismatches.
    await conn.run(`
      create view win as select * from read_json('${sqlLit(WINDOWS_JSONL)}',
        format='newline_delimited', records=true,
        columns={ocd_id:'VARCHAR', fr_document_number:'VARCHAR', regs_document_id:'VARCHAR',
                 docket_id:'JSON', window_type:'VARCHAR',
                 resolved_close_utc:'VARCHAR', resolved_close_display:'VARCHAR',
                 raw_fr_close_date:'VARCHAR', raw_regs_close_datetime:'VARCHAR',
                 confidence:'VARCHAR', status:'VARCHAR', version:'INTEGER', derived_at:'VARCHAR'});
    `);
    // Column-pruned remote scan: only the join/compare columns' chunks are fetched (text_content,
    // the heavy column, never leaves the bucket).
    await conn.run(`
      create view docs as select document_id, fr_doc_num, comment_end_date, withdrawn, modify_date
      from read_parquet('${sqlLit(PARQUET)}');
    `);
    // Join preference: exact Regs document id first; fr_doc_num as the FALLBACK — both for
    // FR-only windows (no regs id at all) and for windows whose regs id is simply ABSENT from the
    // mirror (adversary #5: without the second case a real disagreement on such a window would
    // hide in the non-triage `unmatched` bucket). One output row per WINDOW — parquet matches are
    // aggregated so the multi-docket case (one FR doc num fanned out across dockets) compares
    // against ALL of them.
    const joined = await rows<JoinedRow>(
      conn,
      `
      with regs_matched as (
        select w.ocd_id, 'regs_id' as join_via, d.document_id as parquet_doc_id,
               d.comment_end_date as parquet_end, d.withdrawn as parquet_withdrawn,
               d.modify_date as parquet_modified
        from win w
        join docs d on d.document_id = w.regs_document_id
      ),
      fr_matched as (
        select w.ocd_id, 'fr_doc_num' as join_via, d.document_id as parquet_doc_id,
               d.comment_end_date as parquet_end, d.withdrawn as parquet_withdrawn,
               d.modify_date as parquet_modified
        from win w
        join docs d on d.fr_doc_num = w.fr_document_number
        where not exists (select 1 from regs_matched rm where rm.ocd_id = w.ocd_id)
      ),
      matched as (
        select * from regs_matched union all select * from fr_matched
      )
      select w.ocd_id, w.fr_document_number, w.regs_document_id,
             w.resolved_close_utc, w.confidence, w.status, w.derived_at,
             max(m.join_via) as join_via,
             string_agg(m.parquet_doc_id, ', ' order by m.parquet_doc_id) as parquet_doc_ids,
             string_agg(distinct m.parquet_end, '||') as parquet_end_dates,
             coalesce(bool_or(m.parquet_withdrawn = 'true'), false) as parquet_withdrawn_any,
             max(m.parquet_modified) as parquet_modified_max
      from win w
      left join matched m on m.ocd_id = w.ocd_id
      group by 1,2,3,4,5,6,7
      order by w.ocd_id
      `,
    );
    const totals = await rows<{ n: bigint; max_modify: string }>(
      conn,
      `select count(*) as n, max(modify_date) as max_modify from docs`,
    );
    return { joined, totals };
  });

  const findings = joined.map((r) =>
    r.parquet_doc_ids
      ? classify(r)
      : {
          category: "unmatched" as Category,
          row: r,
          oursEastern: r.resolved_close_utc
            ? easternDate(r.resolved_close_utc)
            : null,
          parquetEastern: [],
        },
  );

  const count = (c: Category) =>
    findings.filter((f) => f.category === c).length;
  const diffPath = resolve(OUT_DIR, OUT_NAME);
  const carried = existsSync(diffPath)
    ? parseTriage(readFileSync(diffPath, "utf8"))
    : new Map<string, { triage: string; note: string }>();
  const disagreements = findings.filter(
    (f) =>
      f.category === "date_mismatch" || f.category === "withdrawn_mismatch",
  );

  const detailRow = (f: Finding): string => {
    const r = f.row;
    const prev = carried.get(triageKey(r.ocd_id, f.category));
    // Escape any raw pipe an operator typed into a note — an unescaped `|` would both break the
    // markdown table and shift the parser's cells on the NEXT run (the RB-1 corruption).
    const note = (prev?.note ?? "").replace(/(?<!\\)\|/g, "\\|");
    return `| ${r.ocd_id} | ${f.category} | ${f.oursEastern ?? "—"} | ${
      f.parquetEastern.join(" / ") || "—"
    } | ${r.status}${f.category === "withdrawn_mismatch" ? " vs withdrawn" : ""} | ${
      r.confidence
    } | ${r.join_via} | ${r.parquet_doc_ids} | ${r.derived_at} | ${
      r.parquet_modified_max ?? "—"
    } | ${prev?.triage ?? ""} | ${note} |`;
  };

  const md = `# XCHECK — live windows vs spicy-regs Parquet (offline differential)

Generated: ${new Date().toISOString()}
Windows export: \`${WINDOWS_JSONL.replace(/^.*\/(spikes\/)/, "$1")}\` (${joined.length} windows)
Parquet: \`${PARQUET}\` (${totals[0]?.n ?? "?"} documents, freshest modify_date ${totals[0]?.max_modify ?? "?"})

A pass is NOT DONE until every disagreement below carries a \`triage\` value:
\`our_bug\` (live projection wrong — export a fixture with \`export:accuracy-miss\`),
\`bulk_stale\` (mirror lags live), \`source_drift\` (the sources themselves changed).
Re-runs carry forward filled triage for persisting disagreements (keyed by ocd_id + category —
a finding that changes category re-triages from scratch). In notes, spell a literal pipe \`\\|\`.

## Counts

| category | count | meaning |
| --- | ---: | --- |
| agree | ${count("agree")} | same Eastern close date (and no withdrawn signal against us) |
| **date_mismatch** | **${count("date_mismatch")}** | joined rows disagree on the Eastern close date — TRIAGE |
| **withdrawn_mismatch** | **${count("withdrawn_mismatch")}** | mirror says withdrawn, our status doesn't — TRIAGE |
| we_abstain | ${count("we_abstain")} | our close is null (honest abstention); mirror carries a date |
| parquet_no_close | ${count("parquet_no_close")} | joined, but no mirror row carries a comment_end_date |
| unmatched | ${count("unmatched")} | window not present in the mirror at all |

## Disagreements (${disagreements.length})

| ocd_id | category | ours (Eastern) | parquet (Eastern) | status | confidence | join | parquet docs | derived_at | parquet_modified | triage | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
${disagreements.map(detailRow).join("\n")}
${
  disagreements.length === 0
    ? "\n_No disagreements — every joined window agrees with the mirror on this snapshot._\n"
    : ""
}
## Abstentions with a mirror date (${count("we_abstain")}) — spot-check material, no triage required

| ocd_id | parquet (Eastern) | status | confidence | join | parquet docs |
| --- | --- | --- | --- | --- | --- |
${findings
  .filter((f) => f.category === "we_abstain")
  .slice(0, 50)
  .map(
    (f) =>
      `| ${f.row.ocd_id} | ${f.parquetEastern.join(" / ")} | ${f.row.status} | ${f.row.confidence} | ${f.row.join_via} | ${f.row.parquet_doc_ids} |`,
  )
  .join("\n")}
${count("we_abstain") > 50 ? `\n_…and ${count("we_abstain") - 50} more (first 50 shown)._\n` : ""}`;

  const path = writeOut(OUT_NAME, md);
  console.log(
    `agree=${count("agree")} date_mismatch=${count("date_mismatch")} withdrawn_mismatch=${count(
      "withdrawn_mismatch",
    )} we_abstain=${count("we_abstain")} parquet_no_close=${count("parquet_no_close")} unmatched=${count("unmatched")}`,
  );
  if (carried.size)
    console.log(
      `carried forward ${carried.size} triage value(s) from the previous diff`,
    );
  // A previously-triaged disagreement that is ABSENT this run is dropped from the rewritten file —
  // usually it genuinely resolved, but a one-run mirror flap would silently lose the triage
  // (adversary #6), so name the drops: recover them from `git diff` if the row comes back.
  const present = new Set(
    disagreements.map((f) => triageKey(f.row.ocd_id, f.category)),
  );
  const dropped = [...carried.keys()].filter((k) => !present.has(k));
  if (dropped.length)
    console.log(
      `NOTE ${dropped.length} previously-triaged disagreement(s) no longer present (resolved, flapped, or changed category) — triage dropped from the file, recoverable via git diff:\n  ${dropped.join("\n  ")}`,
    );
  console.log(`wrote ${path}`);
}

main().catch((err) => {
  console.error("xcheck failed:", err);
  process.exit(1);
});
