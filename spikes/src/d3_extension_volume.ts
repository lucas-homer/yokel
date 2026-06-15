/**
 * D3 — Extension/correction/reopening volume & deny-list false positives
 *
 * Q: How many genuine extension/correction/reopening/withdrawal notices per day, and how noisy is
 *    the keyword detector (the BLM "land-withdrawal extension" trap)?
 * Gates: whether the human-review console is a ~20-min/day chore or a part-time staffing line; and
 *    whether the LLM chain-classifier is load-bearing from day 1.
 *
 * Method (see § D3): the plan's detector is `lower(title) ~ '(extension|reopen|correction|withdraw)'`.
 *   These deadline-moving notices are published in the Federal Register (keyless, authoritative — and
 *   the BLM "land-withdrawal" trap is itself an FR *title* false-positive), so:
 *   1. Pull every NOTICE/PRORULE/RULE in a recent 90-day window (fields incl. title).
 *   2. Apply the title keyword detector client-side; count candidates total / per-keyword / per-day.
 *   3. Emit a 50-row sample (stride-sampled across the window) for hand-labeling: does each row
 *      actually MOVE a comment deadline? precision = movers / 50.
 *   4. Project daily genuine-mover volume = daily candidate volume × precision.
 *   (Set SPICY_REGS_PARQUET to also cross-check against the Mirrulations/spicy-regs Parquet — TODO hook.)
 *
 * Decision rule:
 *   precision >= ~0.7 -> deterministic deny-list + keywords enough for v1; LLM adjudicates the rest.
 *   precision <  ~0.5 -> LLM chain-classifier is load-bearing from day 1; tighten deny-list.
 *   genuine movers > ~15/day -> review console is a staffed line (flag it).
 *
 * Output: out/D3_extension_volume.md (+ the 50-row sheet to label).
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  DATA_DIR,
  fetchJson,
  qs,
  today,
  writeData,
  writeOut,
} from "./_shared.js";

const WINDOW_DAYS = 90;
const SAMPLE_SIZE = 50;

// Detector stems (mirror the plan's regex). Order = attribution priority.
const KEYWORDS = ["extension", "reopen", "correction", "withdraw"] as const;
type Keyword = (typeof KEYWORDS)[number];

interface FrDoc {
  document_number: string;
  title: string | null;
  type: string | null;
  action: string | null;
  publication_date: string | null;
  agencies?: { name?: string }[];
}

interface Candidate {
  document_number: string;
  publication_date: string;
  type: string;
  keyword: Keyword;
  all_keywords: string;
  agency: string;
  title: string;
  fp_hint: string;
}

/** YYYY-MM-DD that is `days` before `dateStr` (UTC date math — no tz drift for date-only). */
function daysBefore(dateStr: string, days: number): string {
  const [y, m, d] = dateStr.split("-").map(Number) as [number, number, number];
  const t = Date.UTC(y, m - 1, d) - days * 86_400_000;
  return new Date(t).toISOString().slice(0, 10);
}

async function pullWindow(gte: string, lte: string): Promise<FrDoc[]> {
  const fields = [
    "document_number",
    "title",
    "type",
    "action",
    "publication_date",
    "agencies",
  ];
  const fieldsQs = fields
    .map((f) => `${encodeURIComponent("fields[]")}=${f}`)
    .join("&");
  const types = ["NOTICE", "PRORULE", "RULE"];
  const typeQs = types
    .map((t) => `${encodeURIComponent("conditions[type][]")}=${t}`)
    .join("&");
  const first =
    `https://www.federalregister.gov/api/v1/documents.json?` +
    qs({
      per_page: 1000,
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
  while (url && page < 40) {
    const res: {
      count?: number;
      results?: FrDoc[];
      next_page_url?: string | null;
    } = await fetchJson(url);
    if (page === 0) console.log(`  FR reports count=${res.count}`);
    for (const r of res.results ?? []) out.push(r);
    url = res.next_page_url ?? null;
    page++;
    console.log(`  page ${page}: total ${out.length}`);
  }
  return out;
}

function matchedKeywords(title: string): Keyword[] {
  const t = title.toLowerCase();
  return KEYWORDS.filter((k) => t.includes(k));
}

/** Advisory hint for the labeler — NOT an authoritative label. Each points at a known FP class. */
function fpHint(title: string, kws: Keyword[]): string {
  const t = title.toLowerCase();
  const movesComment = /\b(comment|deadline|comment period|reopen)\b/.test(t);

  // PRA / OMB info-collection "extension" — a different kind of comment, not a docket deadline.
  if (
    kws.includes("extension") &&
    /\b(information collection|paperwork reduction|omb (review|control)|currently approved collection|collection of information)\b/.test(
      t,
    ) &&
    !movesComment
  ) {
    return "likely PRA/info-collection extension (not a docket comment deadline)";
  }
  // The named BLM trap: a public-land withdrawal, not a comment-period withdrawal.
  if (
    kws.includes("withdraw") &&
    /\b(public land|land order|\bacres?\b|mineral|national forest|reclamation|grazing|bureau of land management|\bblm\b)\b/.test(
      t,
    )
  ) {
    return "likely land-withdrawal FP (not a comment deadline)";
  }
  // Drug/SRO/application "withdrawal of approval" — a withdrawal, but not of a comment period.
  if (
    kws.includes("withdraw") &&
    /\bwithdrawal of (the )?(approval|application)|abbreviated new drug|self-regulatory|securities exchange\b/.test(
      t,
    )
  ) {
    return "likely approval/application withdrawal (not a comment deadline)";
  }
  if (kws.includes("withdraw") && !movesComment) {
    return "withdrawal — confirm it touches a comment period";
  }
  if (
    kws.includes("correction") &&
    !movesComment &&
    !/\b(extend|extension)\b/.test(t)
  ) {
    return "likely editorial/technical correction";
  }
  return "";
}

async function main(): Promise<void> {
  const runDate = today();
  const lte = runDate;
  const gte = daysBefore(runDate, WINDOW_DAYS);
  console.log(
    `D3: keyword detector over FR ${gte} → ${lte} (${WINDOW_DAYS} days)\n`,
  );

  // D3_USE_CACHE=1 re-applies the detector to the last pull in data/ without hitting FR.
  const cachePath = resolve(DATA_DIR, "fr_90day.json");
  let docs: FrDoc[];
  if (process.env.D3_USE_CACHE === "1" && existsSync(cachePath)) {
    console.log("D3_USE_CACHE=1 — loading data/fr_90day.json (no API calls)\n");
    docs = JSON.parse(readFileSync(cachePath, "utf8"));
  } else {
    docs = await pullWindow(gte, lte);
    writeData("fr_90day.json", docs);
    console.log(`  -> ${docs.length} docs saved to data/fr_90day.json\n`);
  }

  // Apply the title detector.
  const candidates: Candidate[] = [];
  for (const d of docs) {
    const title = (d.title ?? "").replace(/\s+/g, " ").trim();
    if (!title) continue;
    const kws = matchedKeywords(title);
    if (kws.length === 0) continue;
    candidates.push({
      document_number: d.document_number,
      publication_date: d.publication_date ?? "",
      type: d.type ?? "",
      keyword: kws[0]!,
      all_keywords: kws.join("+"),
      agency: d.agencies?.[0]?.name ?? "",
      title,
      fp_hint: fpHint(title, kws),
    });
  }
  candidates.sort(
    (a, b) =>
      a.publication_date.localeCompare(b.publication_date) ||
      a.document_number.localeCompare(b.document_number),
  );

  const perKeyword = KEYWORDS.map((k) => ({
    k,
    n: candidates.filter((c) => c.keyword === k).length,
  }));
  const hinted = candidates.filter((c) => c.fp_hint).length;
  const dailyCandidates = candidates.length / WINDOW_DAYS;

  // Stride-sample 50 evenly across the window (deterministic, representative).
  const stride = Math.max(1, Math.floor(candidates.length / SAMPLE_SIZE));
  const sample: Candidate[] = [];
  for (
    let i = 0;
    i < candidates.length && sample.length < SAMPLE_SIZE;
    i += stride
  ) {
    sample.push(candidates[i]!);
  }

  writeData("d3_candidates.json", {
    window: { gte, lte },
    total_docs: docs.length,
    candidates,
  });

  const perKwRow = perKeyword.map((x) => `${x.k} ${x.n}`).join(" · ");
  const sampleTable = sample
    .map(
      (c) =>
        `| ${c.publication_date} | ${c.type} | ${c.all_keywords} | ${c.agency.slice(0, 24)} | ${c.title.slice(0, 78)} | ${c.fp_hint} |   |`,
    )
    .join("\n");

  // Worked example of the decision arithmetic at the two precision thresholds.
  const projAt = (p: number): string => (dailyCandidates * p).toFixed(1);

  const md = `# D3 — Extension/correction/reopening volume & deny-list precision

**Run:** ${runDate} (Eastern) · detector \`lower(title) ~ '(extension|reopen|correction|withdraw)'\`
**Window:** ${gte} → ${lte} (${WINDOW_DAYS} days) · source: Federal Register NOTICE/PRORULE/RULE (keyless)

## Keyword-candidate volume (pre-labeling, upper bound)

| metric | value |
| --- | ---: |
| docs scanned in window | ${docs.length} |
| **keyword candidates** (title hit) | **${candidates.length}** |
| …per keyword | ${perKwRow} |
| flagged by FP heuristic (hint only) | ${hinted} |
| **candidate volume / day** | **${dailyCandidates.toFixed(1)}** |

> Per-keyword counts double-count titles that hit two stems (e.g. "extension" + "correction");
> the candidate total counts each document once. The "FP heuristic" column is an *advisory hint*
> for the labeler (e.g. the BLM land-withdrawal trap), not a label.

## Decision (finalize after labeling the 50-row sheet)

Compute **precision = genuine deadline-movers / 50**, then read off:

- \`precision ≥ 0.7\` → deterministic deny-list + keywords is enough for v1; the LLM adjudicates the rest.
- \`precision < 0.5\` → the LLM chain-classifier is **load-bearing from day 1**; tighten the deny-list with the labeled FPs.
- **Projected genuine movers/day = ${dailyCandidates.toFixed(1)} × precision.**
  Worked: at precision 0.7 → **${projAt(0.7)}/day**; at 0.5 → **${projAt(0.5)}/day**; at 0.3 → **${projAt(0.3)}/day**.
  If that projection exceeds **~15/day**, the review console is a *staffed line*, not a 20-min chore — flag it.

## 50-row sample — label each: does it MOVE a comment deadline?

\`mover?\` = does this notice actually extend/reopen/correct/withdraw a **comment-period deadline**
(vs. a land withdrawal, an editorial correction, an unrelated "extension of a program", etc.)?

| published | type | keyword | agency | title | FP hint | mover? (y/n) |
| --- | --- | --- | --- | --- | --- | --- |
${sampleTable || "| _(no candidates)_ |  |  |  |  |  |  |"}

_Sample is a stride of ${stride} across ${candidates.length} candidates (deterministic, representative
of the full window). After labeling, count the \`y\`s → that's the numerator over ${SAMPLE_SIZE}._

_Artifacts: \`data/fr_90day.json\` (${docs.length} docs), \`data/d3_candidates.json\` (${candidates.length} candidates)._
`;

  const outPath = writeOut("D3_extension_volume.md", md);
  console.log(`\n=== D3 RESULT ===`);
  console.log(
    `docs=${docs.length}  candidates=${candidates.length} (${dailyCandidates.toFixed(1)}/day)  ` +
      `[${perKwRow}]  fp_hinted=${hinted}`,
  );
  console.log(
    `Projected movers/day: 0.7→${projAt(0.7)}  0.5→${projAt(0.5)}  0.3→${projAt(0.3)}`,
  );
  console.log(`Sample of ${sample.length} written for hand-labeling.`);
  console.log(`Wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
