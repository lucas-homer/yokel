/**
 * amendment-loader-equivalence.test.ts — the optimized loadAmendmentEvidence (amendment corpus memo +
 * 0013 indexes) returns EXACTLY the outcome of the original per-call query, which is kept here VERBATIM
 * as the test oracle (`oracleLoad`). THROWAWAY Postgres (drops + recreates the public schema).
 *
 * Over every window of:
 *   • the recorded production log (test/fixtures/fr-amendments/stored) + the five recorded GovInfo pages;
 *   • adversarial rows — an amendment whose LATEST FR row lost its flags (an older row still flagged);
 *     a doc-number reference that appears ONLY in the govinfo text; a different-docket amendment linked
 *     by A's unique citation + title prefix; a correction_of URL with a ".json" suffix; and then a
 *     DUPLICATE citation (a second document carrying USDA's 91 FR 57828), which must turn the citation
 *     link off in both loaders.
 * Plus the memo's freshness: a new FR row appended after the corpus is built is seen on the next call;
 * a transaction's uncommitted rows are seen inside it and never leak into the shared memo.
 *
 * Run: DATABASE_URL=postgres://… pnpm --filter @yokel/docketclock exec tsx test/amendment-loader-equivalence.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import { createClient, type SqlHandle } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { ingestObservation } from "../src/ingest/observe.js";
import {
  amendmentOutcomeFromRows,
  loadAmendmentEvidence,
  type FrAmendmentRow,
} from "../src/reconcile/persist.js";
import type { AmendmentOutcome } from "../src/reconcile/amendment.js";
import { extractFr } from "../src/reconcile/extract.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import { parseGovinfoObservation } from "../src/sources/govinfo.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

if (!process.env.DATABASE_URL) {
  console.log(
    "SKIP amendment-loader-equivalence.test.ts — DATABASE_URL not set",
  );
  process.exit(0);
}

const FIX = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "fr-amendments",
);
const stored = JSON.parse(
  readFileSync(join(FIX, "stored", "observations.json"), "utf8"),
) as Observation[];
const api = (doc: string) =>
  JSON.parse(
    readFileSync(join(FIX, "fr-api", `${doc}.json`), "utf8"),
  ) as Record<string, unknown>;
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;

/**
 * THE ORACLE — the original reconcile-v2.4 loader as first shipped (round 1 only widened its SELECT list
 * with the fetch-time / payload-hash columns the evidence now carries — candidate selection untouched): a per-call
 * latest-per-document CTE over every FR row published after A, a lateral govinfo lookup, the SQL text
 * prefilter, and the citation count. Do not "fix" it: it is the reference the optimization must equal.
 */
async function oracleLoad(
  sql: SqlHandle,
  ocdId: string,
): Promise<AmendmentOutcome> {
  const [aRow] = await sql<FrAmendmentRow[]>`
    select observation_id, ocd_id, fr_document_number,
           is_extension, is_correction, is_withdrawal, is_reopening, raw,
           null::uuid as govinfo_observation_id, null::text as govinfo_text
    from observations
    where ocd_id = ${ocdId} and source = 'federal_register'
    order by fetched_at desc, observation_id desc
    limit 1
  `;
  if (!aRow) return { kind: "none" };
  const fr = extractFr(aRow.raw);
  const aPub = fr.publicationDate;
  if (!aPub) return { kind: "none" };
  const aDocNum = fr.documentNumber ?? aRow.fr_document_number ?? "";
  const aCitation = (fr.citation ?? "").replace(/\s+/g, " ").trim();
  const docLike = aDocNum ? `%${aDocNum}%` : "";
  const docLikeLoose = aDocNum ? `%${aDocNum.replace("-", "- ")}%` : "";
  const citeLike = aCitation ? `%${aCitation}%` : "";
  const bRows = await sql<FrAmendmentRow[]>`
    with latest_fr as (
      select distinct on (ocd_id)
        observation_id, ocd_id, fr_document_number,
        is_extension, is_correction, is_withdrawal, is_reopening, raw, fetched_at, payload_hash
      from observations
      where source = 'federal_register'
        and ocd_id <> ${ocdId}
        and raw->>'publication_date' > ${aPub}
      order by ocd_id, fetched_at desc, observation_id desc
    )
    select l.observation_id, l.ocd_id, l.fr_document_number,
           l.is_extension, l.is_correction, l.is_withdrawal, l.is_reopening, l.raw,
           l.fetched_at, l.payload_hash,
           g.observation_id as govinfo_observation_id, g.raw_dates_text as govinfo_text,
           g.fetched_at as govinfo_fetched_at, g.payload_hash as govinfo_payload_hash
    from latest_fr l
    left join lateral (
      select observation_id, raw_dates_text, fetched_at, payload_hash
      from observations g
      where g.ocd_id = l.ocd_id and g.source = 'govinfo'
      order by g.fetched_at desc, g.observation_id desc
      limit 1
    ) g on true
    where (l.is_extension or l.is_correction or l.is_withdrawal or l.is_reopening
           or coalesce(l.raw->>'correction_of', '') <> '')
      and (
        exists (
          select 1 from jsonb_array_elements_text(
            case when jsonb_typeof(l.raw->'docket_ids') = 'array' then l.raw->'docket_ids' else '[]'::jsonb end
          ) d
          where d = any(${fr.docketIds}::text[])
        )
        or (${docLike} <> '' and coalesce(l.raw->>'correction_of', '') like ${docLike})
        or (${docLike} <> '' and regexp_replace(coalesce(l.raw->>'dates', '') || ' ' || coalesce(g.raw_dates_text, ''), '\\s+', ' ', 'g') like ${docLike})
        or (${docLikeLoose} <> '' and regexp_replace(coalesce(l.raw->>'dates', '') || ' ' || coalesce(g.raw_dates_text, ''), '\\s+', ' ', 'g') like ${docLikeLoose})
        or (${citeLike} <> '' and regexp_replace(coalesce(l.raw->>'dates', '') || ' ' || coalesce(g.raw_dates_text, ''), '\\s+', ' ', 'g') like ${citeLike})
      )
    order by l.ocd_id
  `;
  if (bRows.length === 0) return { kind: "none" };
  const citationIndex = new Map<string, number>();
  if (fr.citation) {
    const [row] = await sql<{ n: number }[]>`
      select count(distinct fr_document_number)::int as n
      from observations
      where source = 'federal_register'
        and regexp_replace(btrim(raw->>'citation'), '\\s+', ' ', 'g') = ${aCitation}
    `;
    citationIndex.set(fr.citation.trim(), row?.n ?? 0);
  }
  return amendmentOutcomeFromRows(aRow, bRows, citationIndex);
}

const sql = createClient();

/** Compare both loaders over EVERY ocd_id in the log; returns the outcome kinds for non-vacuity checks. */
async function compareAll(
  label: string,
): Promise<Map<string, AmendmentOutcome>> {
  const ids = (
    await sql<
      { ocd_id: string }[]
    >`select distinct ocd_id from observations order by ocd_id`
  ).map((r) => r.ocd_id);
  const diffs: string[] = [];
  const outcomes = new Map<string, AmendmentOutcome>();
  for (const id of ids) {
    const fast = await loadAmendmentEvidence(sql, id);
    const slow = await oracleLoad(sql, id);
    outcomes.set(id, fast);
    if (JSON.stringify(fast) !== JSON.stringify(slow)) diffs.push(id);
  }
  const kinds = [...outcomes.values()].reduce<Record<string, number>>(
    (acc, o) => ({ ...acc, [o.kind]: (acc[o.kind] ?? 0) + 1 }),
    {},
  );
  assert(
    `${label}: optimized === oracle for all ${ids.length} windows`,
    diffs.length === 0,
    diffs.length ? diffs.join(",") : JSON.stringify(kinds),
  );
  return outcomes;
}

/** A synthetic FR observation from overrides on a recorded FR API document. */
function frObs(base: string, over: Record<string, unknown>, fetchedAt: string) {
  return {
    ...parseFrObservation({ ...api(base), ...over }),
    fetched_at: fetchedAt,
  };
}

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  await runMigrations(sql);
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
  }
  for (const [doc, pub, cor] of [
    ["2026-19710", "2026-09-25", false],
    ["2026-19895", "2026-09-29", false],
    ["2026-20328", "2026-10-05", false],
    ["C1-2026-18574", "2026-09-28", true],
  ] as const) {
    await ingestObservation(sql, {
      ...parseGovinfoObservation({
        frDocNum: doc,
        publicationDate: pub,
        url: `https://www.govinfo.gov/content/pkg/FR-${pub}/html/${doc}.htm`,
        html: readFileSync(join(FIX, "govinfo", `${doc}.htm`), "utf8"),
        isCorrection: cor,
      }),
      fetched_at: "2026-10-27T06:00:00.000Z",
    });
  }

  const base = await compareAll("recorded log + govinfo");
  const kinds = [...base.values()].map((o) => o.kind);
  assert(
    "non-vacuous: the recorded log yields amended AND ambiguous outcomes",
    kinds.filter((k) => k === "amended").length === 3 &&
      kinds.includes("ambiguous"),
    kinds.join(","),
  );

  // ── adversarial rows ──────────────────────────────────────────────────────────────────────────────
  // (1) Lost flags: an extension on the Census docket whose LATEST FR row is an un-flagged re-fetch.
  await ingestObservation(
    sql,
    frObs(
      "2026-20328",
      {
        document_number: "2026-29001",
        publication_date: "2026-10-07",
        citation: "91 FR 69001",
        dates: "Submit comments on or before November 9, 2026.",
        comments_close_on: "2026-11-09",
      },
      "2026-10-07T08:00:00.000Z",
    ),
  );
  await ingestObservation(
    sql,
    frObs(
      "2026-20328",
      {
        document_number: "2026-29001",
        publication_date: "2026-10-07",
        citation: "91 FR 69001",
        title: "Decennial Census of the Population of Americans; Notice",
        action: "Notice.",
        dates: "Submit comments on or before November 9, 2026.",
        comments_close_on: "2026-11-09",
      },
      "2026-10-08T08:00:00.000Z",
    ),
  );
  // (2) A doc-number reference ONLY in govinfo text (ICE docket; FR dates carry no reference).
  await ingestObservation(
    sql,
    frObs(
      "2026-20660",
      {
        document_number: "2026-29002",
        publication_date: "2026-10-20",
        citation: "91 FR 69002",
        title: "Optional Practical Training Fees; Extension of Comment Period",
        action: "Proposed rule; extension of comment period.",
        dates: "Comments are due as stated below.",
        comments_close_on: null,
        regulation_id_numbers: [],
      },
      "2026-10-20T08:00:00.000Z",
    ),
  );
  await ingestObservation(sql, {
    ...parseGovinfoObservation({
      frDocNum: "2026-29002",
      publicationDate: "2026-10-20",
      url: "https://www.govinfo.gov/content/pkg/FR-2026-10-20/html/2026-29002.htm",
      html: "<pre>DATES: The comment period for proposed rule document 2026-\n20660 is extended. Comments must be received on or before December 21, 2026.\nADDRESSES: x</pre>",
      isCorrection: false,
    }),
    fetched_at: "2026-10-21T08:00:00.000Z",
  });
  // (3) Different docket, linked by A's unique citation (91 FR 57524) + A's title as B's title prefix.
  await ingestObservation(
    sql,
    frObs(
      "2026-20328",
      {
        document_number: "2026-29003",
        publication_date: "2026-10-06",
        citation: "91 FR 69003",
        docket_ids: ["Docket No. CENSUS-OTHER-1"],
        regulation_id_numbers: [],
        dates:
          "The comment period for the proposed rule published at 91 FR\n57524 is extended. Submit comments on or before November 2, 2026.",
        comments_close_on: "2026-11-02",
      },
      "2026-10-06T08:00:00.000Z",
    ),
  );
  // (4) A correction_of URL with a ".json" suffix and no docket in common.
  await ingestObservation(
    sql,
    frObs(
      "C1-2026-18574",
      {
        document_number: "C2-2026-18574",
        publication_date: "2026-09-30",
        citation: "91 FR 69004",
        docket_ids: [],
        correction_of:
          "https://www.federalregister.gov/api/v1/documents/2026-18574.json",
      },
      "2026-09-30T08:00:00.000Z",
    ),
  );
  const adv = await compareAll("+ adversarial rows");
  assert(
    "adversarial (1): the lost-flags document is not evidence for Census (still amended to Nov 2)",
    (() => {
      const o = adv.get(ocd("2026-18481"));
      return o?.kind === "amended" && o.date === "2026-11-02";
    })(),
    JSON.stringify(adv.get(ocd("2026-18481"))),
  );
  assert(
    "adversarial (2): the govinfo-only doc-number reference links ICE (doc_number basis, Dec 21 from the published DATES)",
    (() => {
      const o = adv.get(ocd("2026-20660"));
      return (
        o?.kind === "amended" &&
        o.amendment.basis === "doc_number" &&
        o.date === "2026-12-21"
      );
    })(),
    JSON.stringify(adv.get(ocd("2026-20660"))),
  );

  // (5) A DUPLICATE citation: a second document carrying USDA's 91 FR 57828 turns the citation link off.
  await ingestObservation(
    sql,
    frObs(
      "2026-18134",
      {
        document_number: "2026-29005",
        citation: "91 FR 57828",
        publication_date: "2026-09-11",
      },
      "2026-09-12T08:00:00.000Z",
    ),
  );
  const dup = await compareAll("+ duplicate citation");
  assert(
    "adversarial (5): with the citation duplicated, USDA is no longer amended in either loader",
    dup.get(ocd("2026-18531"))?.kind === "none" &&
      adv.get(ocd("2026-18531"))?.kind === "amended",
    `${JSON.stringify(adv.get(ocd("2026-18531")))} → ${JSON.stringify(dup.get(ocd("2026-18531")))}`,
  );

  // ── memo freshness ────────────────────────────────────────────────────────────────────────────────
  const before = await loadAmendmentEvidence(sql, ocd("2026-17216"));
  await ingestObservation(
    sql,
    frObs(
      "2026-19895",
      {
        document_number: "2026-29006",
        publication_date: "2026-09-30",
        citation: "91 FR 69006",
        title: "Guidance on the Streamlined Inspection Program; Withdrawal",
        action: "Notice; withdrawal.",
      },
      "2026-09-30T09:00:00.000Z",
    ),
  );
  const after = await loadAmendmentEvidence(sql, ocd("2026-17216"));
  assert(
    "memo: an FR row appended after the corpus was built is seen on the very next call",
    JSON.stringify(after) ===
      JSON.stringify(await oracleLoad(sql, ocd("2026-17216"))) &&
      after.kind === "ambiguous" &&
      JSON.stringify(after) !== JSON.stringify(before),
    `${JSON.stringify(before)} → ${JSON.stringify(after)}`,
  );
  // A transaction's uncommitted extension is visible inside it and never pollutes the shared memo.
  const IRS = ocd("2026-18574");
  const committed = await loadAmendmentEvidence(sql, IRS);
  let inside: AmendmentOutcome | null = null;
  try {
    await sql.begin(async (tx) => {
      await tx`
        insert into observations
          (ocd_id, source, fr_document_number, regs_document_id, regs_object_id, payload_hash,
           fetched_at, parser_version, raw_dates_text, is_extension, is_correction, is_withdrawal,
           is_reopening, raw)
        values
          (${ocd("2026-29007")}, 'federal_register', '2026-29007', null, null, ${"f".repeat(64)},
           '2026-10-01T00:00:00Z', 'fr-v3', null, false, false, true, false,
           ${tx.json({ ...api("C1-2026-18574"), document_number: "2026-29007", publication_date: "2026-10-01", citation: "91 FR 69007", correction_of: null } as never)})
      `;
      inside = await loadAmendmentEvidence(tx, IRS);
      throw new Error("rollback");
    });
  } catch {
    /* rolled back on purpose */
  }
  assert(
    "transaction: its uncommitted withdrawal (shared docket + RIN) is seen inside → ambiguous",
    (inside as AmendmentOutcome | null)?.kind === "ambiguous",
    JSON.stringify(inside),
  );
  const afterTx = await loadAmendmentEvidence(sql, IRS);
  assert(
    "transaction: after rollback the shared memo still answers from committed rows only",
    JSON.stringify(afterTx) === JSON.stringify(committed) &&
      JSON.stringify(afterTx) === JSON.stringify(await oracleLoad(sql, IRS)),
    JSON.stringify(afterTx),
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
