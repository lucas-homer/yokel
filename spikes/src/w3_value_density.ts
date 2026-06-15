/**
 * W3 — In-basin value density  (BUSINESS KILL-SHOT)
 *
 * Q: For one real Chesapeake HUC-8 subbasin, how many NOVEL (previously-unknown-to-the-org) in-basin
 *    Tier-1 windows appear per quarter, split EIS vs Regs.gov?
 * Gates: if it's 2-3/quarter, the paid-seat thesis is dead regardless of architecture quality.
 *
 * Method (see § W3):
 *   1. Resolve a HUC-8 (default Choptank 02060005) to name + states via The National Map WBD
 *      ArcGIS REST (MapServer layer 4 = HUC8).
 *   2. Build a basin keyword set (basin name + named tributaries + counties + Chesapeake Bay).
 *   3. Over the last 4 quarters, count in-basin candidates from two keyless Federal Register streams,
 *      which mirror the two Tier-1 sources:
 *        - EIS    = FR NOTICEs matching "environmental impact statement", basin-keyword filtered.
 *        - Regs.gov rulemaking = FR PRORULE/RULE basin-keyword term search.
 *      (FR is the authoritative publisher of rules + EIS notices, keyless, and good enough for an
 *       ESTIMATE. The production estimate should additionally read spicy-regs/Mirrulations Parquet —
 *       set SPICY_REGS_PARQUET to a glob and it will be cross-checked via DuckDB httpfs.)
 *   4. Split EIS vs Regs.gov-rulemaking, per quarter. Write a candidate sheet for manual labeling
 *      (the "novel / previously-unknown-to-the-org" judgment is a human call — see note in output).
 *
 * Decision rule:
 *   >~ a handful of novel in-basin Tier-1 windows/quarter, EIS a meaningful share -> GO.
 *   ~2-3/quarter or EIS share ~0 -> STOP; reconsider basin, scope, or whether WW is a product.
 *
 * Output: out/W3_value_density.md
 */
import { fetchJson, qs, today, writeData, writeOut } from "./_shared.js";

const HUC8 = process.env.HUC8 || "02060005"; // Choptank

// Per-basin keyword seed. Extend via env W3_KEYWORDS="a,b,c" (added to term search + filter).
// Bare state abbreviations are intentionally NOT term-searched (too broad); kept only as context.
const BASIN_SEED: Record<string, string[]> = {
  "02060005": [
    "Choptank",
    "Tuckahoe",
    "Tred Avon",
    "Marshyhope",
    "Chesapeake Bay",
    "Caroline County",
    "Talbot County",
    "Dorchester County",
    "Queen Anne",
  ],
};

interface FrDoc {
  document_number: string;
  title: string | null;
  abstract: string | null;
  publication_date: string | null;
  type: string | null;
  agencies?: { name?: string }[];
}

interface Quarter {
  label: string; // e.g. 2026Q1
  start: string; // YYYY-MM-DD inclusive
  end: string; // YYYY-MM-DD inclusive
}

/** The 4 most recent calendar-quarter buckets ending at `todayStr`. */
function recentQuarters(todayStr: string, n = 4): Quarter[] {
  const [y, m] = todayStr.split("-").map(Number) as [number, number, number];
  let yr = y;
  let q = Math.floor((m - 1) / 3); // 0..3
  const out: Quarter[] = [];
  for (let i = 0; i < n; i++) {
    const qStartMonth = q * 3 + 1;
    const start = `${yr}-${String(qStartMonth).padStart(2, "0")}-01`;
    const endMonth = qStartMonth + 2;
    const lastDay = new Date(Date.UTC(yr, endMonth, 0)).getUTCDate();
    let end = `${yr}-${String(endMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
    if (end > todayStr) end = todayStr; // clamp the current (partial) quarter
    out.unshift({ label: `${yr}Q${q + 1}`, start, end });
    q -= 1;
    if (q < 0) {
      q = 3;
      yr -= 1;
    }
  }
  return out;
}

const FR = "https://www.federalregister.gov/api/v1/documents.json";
const FIELDS = [
  "document_number",
  "title",
  "abstract",
  "publication_date",
  "type",
  "agencies",
];
const fieldsQs = FIELDS.map(
  (f) => `${encodeURIComponent("fields[]")}=${f}`,
).join("&");
const RULE_TYPES = ["NOTICE", "PRORULE", "RULE"];

/**
 * FR full-text search for a single quoted phrase over the given doc types + date window.
 * (FR conditions[term] does NOT support `"a" OR "b"` boolean — one phrase per call.)
 * Full-text means body mentions count, not just title/abstract — that's the recall we need.
 */
async function frSearchPhrase(
  phrase: string,
  gte: string,
  lte: string,
): Promise<FrDoc[]> {
  const typeQs = RULE_TYPES.map(
    (t) => `${encodeURIComponent("conditions[type][]")}=${t}`,
  ).join("&");
  const first =
    `${FR}?` +
    qs({
      per_page: 1000,
      "conditions[term]": `"${phrase}"`,
      "conditions[publication_date][gte]": gte,
      "conditions[publication_date][lte]": lte,
    }) +
    "&" +
    typeQs +
    "&" +
    fieldsQs;
  const out: FrDoc[] = [];
  let url: string | null = first;
  let page = 0;
  while (url && page < 10) {
    const res: { results?: FrDoc[]; next_page_url?: string | null } =
      await fetchJson(url);
    for (const r of res.results ?? []) out.push(r);
    url = res.next_page_url ?? null;
    page++;
  }
  return out;
}

// NOTE: the FR API *returns* human-readable type values ("Notice", "Proposed Rule", "Rule"),
// even though the request *filter* uses abbreviations (NOTICE/PRORULE/RULE).
const isEis = (doc: FrDoc): boolean => {
  const hay = `${doc.title ?? ""} ${doc.abstract ?? ""}`.toLowerCase();
  return (
    doc.type === "Notice" &&
    (hay.includes("environmental impact statement") || /\beis\b/.test(hay))
  );
};

/** EIS notice | Regs.gov rulemaking (Proposed Rule/Rule) | null (other notice — out of Tier-1 scope here). */
const bucketOf = (doc: FrDoc): "EIS" | "Regs" | null => {
  if (isEis(doc)) return "EIS";
  if (doc.type === "Proposed Rule" || doc.type === "Rule") return "Regs";
  return null;
};

interface Candidate {
  quarter: string;
  bucket: "EIS" | "Regs";
  document_number: string;
  publication_date: string | null;
  type: string | null;
  matched: string;
  agency: string;
  title: string;
}

async function main(): Promise<void> {
  const runDate = today();
  const extra = (process.env.W3_KEYWORDS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const keywords = [...(BASIN_SEED[HUC8] ?? []), ...extra];
  if (keywords.length === 0) {
    throw new Error(
      `No keyword seed for HUC8 ${HUC8}. Add one to BASIN_SEED or pass W3_KEYWORDS="term1,term2,...".`,
    );
  }

  // 1. Resolve basin metadata.
  console.log(`W3: resolving HUC-8 ${HUC8} via The National Map WBD...`);
  const wbd = await fetchJson<{
    features?: {
      attributes: {
        huc8: string;
        name: string;
        states: string;
        areaacres: number;
      };
    }[];
  }>(
    "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query?" +
      qs({
        where: `huc8='${HUC8}'`,
        outFields: "huc8,name,states,areaacres",
        returnGeometry: "false",
        f: "json",
      }),
  );
  const basin = wbd.features?.[0]?.attributes;
  if (!basin) throw new Error(`HUC8 ${HUC8} not found in WBD layer 4.`);
  console.log(
    `  ${basin.name} (${basin.states}), ${Math.round(basin.areaacres).toLocaleString()} acres`,
  );

  const quarters = recentQuarters(runDate);
  console.log(`  Quarters: ${quarters.map((q) => q.label).join(", ")}`);
  console.log(`  Keywords: ${keywords.join(", ")}\n`);

  const candidates: Candidate[] = [];
  for (const q of quarters) {
    // One full-text search per basin phrase; classify each hit by type; dedup by FR doc #.
    const seen = new Set<string>();
    let eisN = 0;
    let regsN = 0;
    let hits = 0;
    for (const kw of keywords) {
      const docs = await frSearchPhrase(kw, q.start, q.end);
      hits += docs.length;
      for (const d of docs) {
        if (seen.has(d.document_number)) continue;
        const bucket = bucketOf(d);
        if (!bucket) continue;
        seen.add(d.document_number);
        if (bucket === "EIS") eisN++;
        else regsN++;
        candidates.push({
          quarter: q.label,
          bucket,
          document_number: d.document_number,
          publication_date: d.publication_date,
          type: d.type,
          matched: kw,
          agency: d.agencies?.[0]?.name ?? "",
          title: (d.title ?? "").replace(/\s+/g, " ").trim(),
        });
      }
    }
    console.log(
      `  ${q.label}: EIS=${eisN}  Regs=${regsN}  (from ${hits} full-text hits across ${keywords.length} phrases)`,
    );
  }

  writeData("w3_candidates.json", { basin, quarters, keywords, candidates });

  // 2. Aggregate per quarter.
  const perQuarter = quarters.map((q) => {
    const eis = candidates.filter(
      (c) => c.quarter === q.label && c.bucket === "EIS",
    ).length;
    const regs = candidates.filter(
      (c) => c.quarter === q.label && c.bucket === "Regs",
    ).length;
    return { q: q.label, eis, regs, total: eis + regs };
  });
  const totEis = perQuarter.reduce((s, r) => s + r.eis, 0);
  const totRegs = perQuarter.reduce((s, r) => s + r.regs, 0);
  const tot = totEis + totRegs;
  const avgPerQ = (tot / quarters.length).toFixed(1);
  const eisShare = tot > 0 ? Math.round((100 * totEis) / tot) : 0;

  const verdict =
    tot / quarters.length >= 4 && totEis > 0
      ? "GO (provisional) — a handful of in-basin candidates/quarter with a real EIS share"
      : "STOP (provisional) — too few in-basin windows or EIS share ~0; reconsider basin/scope";

  // 3. Markdown with per-quarter table + candidate sheet for manual labeling.
  const qHeader = `| metric | ${perQuarter.map((r) => r.q).join(" | ")} | total |`;
  const qSep = `| --- | ${perQuarter.map(() => "---:").join(" | ")} | ---: |`;
  const eisRow = `| EIS | ${perQuarter.map((r) => r.eis).join(" | ")} | ${totEis} |`;
  const regsRow = `| Regs.gov rulemaking | ${perQuarter.map((r) => r.regs).join(" | ")} | ${totRegs} |`;
  const totRow = `| **total** | ${perQuarter.map((r) => `**${r.total}**`).join(" | ")} | **${tot}** |`;

  const sheet = candidates
    .map(
      (c) =>
        `| ${c.quarter} | ${c.bucket} | ${c.document_number} | ${c.publication_date ?? ""} | ${c.matched} | ${c.agency} | ${c.title.slice(0, 90)} |   |`,
    )
    .join("\n");

  const md = `# W3 — In-basin value density

**Run:** ${runDate} (Eastern)
**Basin:** HUC-8 \`${HUC8}\` — **${basin.name}** (${basin.states}), ${Math.round(basin.areaacres).toLocaleString()} acres
**Window:** last ${quarters.length} quarters (${quarters[0]!.start} → ${quarters[quarters.length - 1]!.end})
**Keywords:** ${keywords.map((k) => `\`${k}\``).join(", ")}

## Candidate counts per quarter (estimate — keyword + manual, not the production classifier)

${qHeader}
${qSep}
${eisRow}
${regsRow}
${totRow}

- **Average in-basin candidates/quarter:** ${avgPerQ}
- **EIS share of candidates:** ${eisShare}% (${totEis} EIS / ${totRegs} Regs.gov rulemaking)

## Decision (provisional — finalize after manual labeling below)

**${verdict}**

- Rule: \`≳ a handful/quarter with EIS a meaningful share\` → GO; \`~2–3/quarter or EIS share ≈ 0\` → STOP.
- ⚠️ These are **candidate** counts (FR full-text search per basin phrase, body mentions included —
  recall-biased, so expect false positives like national rules that merely name a water body). The plan's number is
  *novel* in-basin Tier-1 windows — "novel" (previously-unknown-to-the-org) is a human judgment.
  Label the sheet below, drop false positives + already-known items, then recompute. Treat the
  counts above as an **upper bound**.
- Source caveat: EIS + rulemaking are drawn from the Federal Register (authoritative, keyless). For a
  fuller Regs.gov-rulemaking estimate, set \`SPICY_REGS_PARQUET\` and cross-check against the
  Mirrulations/spicy-regs Parquet via DuckDB httpfs (not yet wired into the count here).

## Candidate sheet — label each row

\`novel?\` = is this a window the org wouldn't already know about? \`in_basin?\` = does the text really
place it in ${basin.name}, not just mention a keyword?

| quarter | bucket | FR doc # | published | matched kw | agency | title | novel? in_basin? (y/n) |
| --- | --- | --- | --- | --- | --- | --- | --- |
${sheet || "| _(no candidates surfaced — widen keywords or window)_ |  |  |  |  |  |  |  |"}

_Artifact: \`data/w3_candidates.json\` (${candidates.length} candidates)._
`;

  const outPath = writeOut("W3_value_density.md", md);
  console.log(`\n=== W3 RESULT ===`);
  console.log(
    `basin=${basin.name}  candidates=${tot}  avg/qtr=${avgPerQ}  EIS share=${eisShare}%`,
  );
  console.log(`Verdict: ${verdict}`);
  console.log(`Wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
