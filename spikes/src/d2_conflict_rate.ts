/**
 * D2 — FR <-> Regs.gov Eastern-date conflict rate
 *
 * Q: How often do FR comments_close_on and Regs.gov commentEndDate disagree when BOTH normalized to
 *    America/New_York calendar date? And how many are tz-only false positives a naive UTC compare
 *    would have mis-flagged?
 * Gates: product positioning — "conflict intelligence" vs "reliable alerts". Validates the
 *    load-bearing Eastern-date rule.
 *
 * Method (see § D2): over the D1 join (data/fr_open.json + data/regs_open.json), in DuckDB:
 *   - fr_eastern_date   = CAST(comments_close_on AS DATE)                              (FR is date-only Eastern)
 *   - regs_eastern_date = CAST(timezone('America/New_York', commentEndDate::TIMESTAMPTZ) AS DATE)
 *   - regs_utc_date     = CAST(timezone('UTC',             commentEndDate::TIMESTAMPTZ) AS DATE)  (the naive read)
 *   - true_conflict     = fr_eastern_date <> regs_eastern_date
 *   - tz_false_positive = naive UTC compare differs but eastern dates AGREE (rule suppressed it)
 *   Hand-verify ~10 true_conflicts are real (extension/correction), not parse bugs.
 *
 * NOTE: Regs.gov stores comment close as end-of-day Eastern expressed in UTC (e.g. summer
 *   "...T03:59:59Z" = 23:59:59 EDT the *previous* calendar day). So the raw UTC date sits one day
 *   ahead of the true Eastern close date — that gap is the false-positive the rule must kill.
 *
 * Decision rule (no kill — positioning input):
 *   conflict_pct >~ 3-5%  -> lead with conflict intelligence; /conflicts is marquee.
 *   conflict_pct <~ 1%    -> lead with reliable alerts + audit log; conflicts is a quiet feature.
 *   tz_false_positives > 0 CONFIRMS the Eastern-normalization rule is necessary.
 *
 * Output: out/D2_conflict_rate.md
 */
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { DATA_DIR, rows, today, withDuckDB, writeOut } from "./_shared.js";

interface Agg {
  joined: bigint;
  true_conflicts: bigint;
  conflict_pct: number;
  naive_conflicts: bigint;
  naive_pct: number;
  tz_false_positives: bigint;
}

interface ExampleRow {
  frDocNum: string;
  fr_eastern: string;
  regs_eastern: string;
  regs_utc: string;
  regs_raw: string;
  regs_type: string;
  title: string;
}

async function main(): Promise<void> {
  const frPath = resolve(DATA_DIR, "fr_open.json");
  const regsPath = resolve(DATA_DIR, "regs_open.json");
  if (!existsSync(frPath) || !existsSync(regsPath)) {
    throw new Error(
      "Missing data/fr_open.json or data/regs_open.json. Run D1 first (`pnpm d1`) — D2 reuses its pull.",
    );
  }

  const result = await withDuckDB(async (conn) => {
    await conn.run("SET TimeZone='UTC';"); // deterministic; we use explicit timezone() everywhere anyway
    await conn.run(
      `CREATE TABLE fr_open AS SELECT * FROM read_json_auto('${frPath}');`,
    );
    await conn.run(
      `CREATE TABLE regs_open AS SELECT * FROM read_json_auto('${regsPath}');`,
    );

    // The join with both date interpretations materialized once.
    await conn.run(`
      CREATE TABLE j AS
      SELECT
        r.frDocNum,
        fr.comments_close_on                                                        AS fr_date,
        r.commentEndDate                                                            AS regs_raw,
        r.documentType                                                              AS regs_type,
        coalesce(fr.title, r.title)                                                 AS title,
        CAST(fr.comments_close_on AS DATE)                                          AS fr_eastern,
        CAST(timezone('America/New_York', r.commentEndDate::TIMESTAMPTZ) AS DATE)   AS regs_eastern,
        CAST(timezone('UTC',             r.commentEndDate::TIMESTAMPTZ) AS DATE)    AS regs_utc
      FROM regs_open r
      JOIN fr_open fr ON r.frDocNum = fr.document_number
      WHERE r.commentEndDate IS NOT NULL AND fr.comments_close_on IS NOT NULL;
    `);

    const [agg] = await rows<Agg>(
      conn,
      `SELECT
         count(*)                                                              AS joined,
         count(*) FILTER (WHERE fr_eastern <> regs_eastern)                    AS true_conflicts,
         round(100.0 * count(*) FILTER (WHERE fr_eastern <> regs_eastern) / count(*), 2) AS conflict_pct,
         count(*) FILTER (WHERE fr_eastern <> regs_utc)                        AS naive_conflicts,
         round(100.0 * count(*) FILTER (WHERE fr_eastern <> regs_utc) / count(*), 2)     AS naive_pct,
         count(*) FILTER (WHERE fr_eastern <> regs_utc AND fr_eastern = regs_eastern)    AS tz_false_positives
       FROM j;`,
    );

    const selectCols = `
      frDocNum,
      CAST(fr_eastern AS VARCHAR)   AS fr_eastern,
      CAST(regs_eastern AS VARCHAR) AS regs_eastern,
      CAST(regs_utc AS VARCHAR)     AS regs_utc,
      regs_raw,
      coalesce(regs_type, '')       AS regs_type,
      coalesce(title, '')           AS title`;

    const conflicts = await rows<ExampleRow>(
      conn,
      `SELECT ${selectCols} FROM j
       WHERE fr_eastern <> regs_eastern
       ORDER BY abs(date_diff('day', fr_eastern, regs_eastern)) DESC, frDocNum
       LIMIT 12;`,
    );

    const falsePositives = await rows<ExampleRow>(
      conn,
      `SELECT ${selectCols} FROM j
       WHERE fr_eastern <> regs_utc AND fr_eastern = regs_eastern
       ORDER BY frDocNum
       LIMIT 8;`,
    );

    return { agg: agg!, conflicts, falsePositives };
  });

  const { agg, conflicts, falsePositives } = result;
  const conflictPct = Number(agg.conflict_pct);
  const story =
    conflictPct >= 3
      ? "lead the product story with **conflict intelligence**; `/conflicts` is the marquee feature"
      : conflictPct < 1
        ? "lead with **reliable alerts + audit log**; conflicts is a quiet correctness feature"
        : "borderline (1–3%) — conflicts is a real but secondary feature; lean on alerts, keep `/conflicts`";

  const ruleConfirmed = Number(agg.tz_false_positives) > 0;

  const exampleTable = (rs: ExampleRow[]): string =>
    rs.length === 0
      ? "_(none in this sample)_"
      : [
          "| frDocNum | FR Eastern | Regs Eastern | Regs UTC (naive) | Regs raw | type | title |",
          "| --- | --- | --- | --- | --- | --- | --- |",
          ...rs.map(
            (r) =>
              `| ${r.frDocNum} | ${r.fr_eastern} | ${r.regs_eastern} | ${r.regs_utc} | ${r.regs_raw} | ${r.regs_type} | ${r.title.replace(/\s+/g, " ").slice(0, 70)} |`,
          ),
        ].join("\n");

  const md = `# D2 — FR ↔ Regs.gov Eastern-date conflict rate

**Run:** ${today()} (Eastern) · over the D1 join (\`data/fr_open.json\` ⋈ \`data/regs_open.json\`)

## Counts (both dates normalized to America/New_York)

| metric | value |
| --- | ---: |
| joined pairs with both dates present | ${agg.joined} |
| **true_conflicts** (Eastern dates disagree) | **${agg.true_conflicts}** |
| **conflict_pct** | **${agg.conflict_pct}%** |
| naive UTC conflicts (date-slice the \`Z\` timestamp) | ${agg.naive_conflicts} (${agg.naive_pct}%) |
| **tz_false_positives** suppressed by the Eastern rule | **${agg.tz_false_positives}** |

> The naive UTC compare would flag **${agg.naive_conflicts}** conflicts (${agg.naive_pct}%); after Eastern
> normalization only **${agg.true_conflicts}** (${agg.conflict_pct}%) are real. The difference —
> **${agg.tz_false_positives}** rows — is pure timezone noise the rule removes.

## Decision (positioning, no kill)

**conflict_pct = ${agg.conflict_pct}% → ${story}.**

- **Eastern-normalization rule: ${ruleConfirmed ? "✅ CONFIRMED NECESSARY" : "⚠️ no tz false-positives in this sample"}.**
  ${
    ruleConfirmed
      ? `${agg.tz_false_positives} pair(s) differ in UTC but agree in Eastern — a naive UTC threshold would have raised ${agg.tz_false_positives} false "conflict" alert(s).`
      : "Keep the rule regardless (the foundry's load-bearing fix); this snapshot just didn't contain a boundary case."
  }

## True conflicts — hand-verify these are real (extension/correction), not parse bugs

${exampleTable(conflicts)}

## Timezone false-positives — the rule working (naive UTC ≠, Eastern =)

${exampleTable(falsePositives)}

_Eyeball the true-conflict titles above: an extension/correction notice that genuinely moved the
deadline is a real conflict; a same-deadline row that only differs by a day at the UTC boundary is not._
`;

  const outPath = writeOut("D2_conflict_rate.md", md);
  console.log(`\n=== D2 RESULT ===`);
  console.log(
    `joined=${agg.joined}  true_conflicts=${agg.true_conflicts} (${agg.conflict_pct}%)  ` +
      `naive=${agg.naive_conflicts} (${agg.naive_pct}%)  tz_false_pos=${agg.tz_false_positives}`,
  );
  console.log(`Story: ${story.replace(/\*\*/g, "").replace(/`/g, "")}`);
  console.log(`Wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
