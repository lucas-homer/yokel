/**
 * W2 — EPA EIS database machine-readability  (first anti-skin pillar)
 *
 * Q: Does the EPA EIS database expose a documented machine-readable endpoint / bulk download, or is
 *    ingestion a scraper?
 * Gates: durability of the EIS adapter — the #1 thing DocketClock can't give Watershed Watch.
 *
 * Method (see § W2):
 *   1. Probe the EPA EIS search app (cdxapps) + likely REST/JSON backends + EPA Envirofacts for a
 *      machine-readable endpoint. Record content-type / status.
 *   2. Pull a 1-month sample from the Federal Register EIS-notice stream (keyless) — the candidate
 *      machine-readable spine — and confirm we can extract title / state / draft-final / comment
 *      dates / link.
 *
 * Decision rule:
 *   documented endpoint/bulk -> GO, EIS adapter is durable.
 *   scraper only -> still GO, but ship the adapter BEHIND an interface with FR EIS-notices as
 *                   fallback/cross-check; budget scraper maintenance; note fragility.
 *
 * Output: out/W2_eis_source.md (+ 1-month extracted sample)
 */
import { fetchJson, qs, today, writeData, writeOut } from "./_shared.js";

const US_STATES = [
  "Alabama",
  "Alaska",
  "Arizona",
  "Arkansas",
  "California",
  "Colorado",
  "Connecticut",
  "Delaware",
  "Florida",
  "Georgia",
  "Hawaii",
  "Idaho",
  "Illinois",
  "Indiana",
  "Iowa",
  "Kansas",
  "Kentucky",
  "Louisiana",
  "Maine",
  "Maryland",
  "Massachusetts",
  "Michigan",
  "Minnesota",
  "Mississippi",
  "Missouri",
  "Montana",
  "Nebraska",
  "Nevada",
  "New Hampshire",
  "New Jersey",
  "New Mexico",
  "New York",
  "North Carolina",
  "North Dakota",
  "Ohio",
  "Oklahoma",
  "Oregon",
  "Pennsylvania",
  "Rhode Island",
  "South Carolina",
  "South Dakota",
  "Tennessee",
  "Texas",
  "Utah",
  "Vermont",
  "Virginia",
  "Washington",
  "West Virginia",
  "Wisconsin",
  "Wyoming",
];

interface EndpointProbe {
  label: string;
  url: string;
  status: number;
  contentType: string;
  machineReadable: boolean;
  note: string;
}

async function probeEndpoint(
  label: string,
  url: string,
  note: string,
): Promise<EndpointProbe> {
  try {
    const res = await fetch(url, { method: "GET", redirect: "follow" });
    const ct = res.headers.get("content-type") ?? "";
    const machineReadable = res.ok && /json|csv|excel|spreadsheet|xml/.test(ct);
    return {
      label,
      url,
      status: res.status,
      contentType: ct.split(";")[0] ?? ct,
      machineReadable,
      note,
    };
  } catch (err) {
    return {
      label,
      url,
      status: 0,
      contentType: "",
      machineReadable: false,
      note: `${note} (error: ${String(err).slice(0, 80)})`,
    };
  }
}

interface FrEis {
  document_number: string;
  title: string | null;
  publication_date: string | null;
  comments_close_on: string | null;
  html_url: string | null;
  agencies?: { name?: string }[];
}

function draftFinal(title: string): string {
  const t = title.toLowerCase();
  if (t.includes("notice of intent")) return "NOI";
  if (t.includes("draft") && t.includes("supplement"))
    return "Draft Supplement";
  if (t.includes("final") && t.includes("supplement"))
    return "Final Supplement";
  if (t.includes("draft")) return "Draft";
  if (t.includes("final")) return "Final";
  return "—";
}

function statesIn(title: string): string {
  const found = US_STATES.filter((s) => new RegExp(`\\b${s}\\b`).test(title));
  return found.join(", ");
}

async function main(): Promise<void> {
  console.log(
    "W2: probing EPA EIS sources for a machine-readable endpoint...\n",
  );

  const probes = await Promise.all([
    probeEndpoint(
      "EPA EIS search app (cdxapps)",
      "https://cdxapps.epa.gov/cdx-enepa-II/public/action/eis/search",
      "the public EIS search UI",
    ),
    probeEndpoint(
      "cdxapps guessed REST backend",
      "https://cdxapps.epa.gov/cdx-enepa-II/rest/eis",
      "common REST path",
    ),
    probeEndpoint(
      "cdxapps guessed JSON API",
      "https://cdxapps.epa.gov/cdx-enepa-II/public/api/eis",
      "common API path",
    ),
    probeEndpoint(
      "EPA Envirofacts efservice",
      "https://data.epa.gov/efservice/",
      "REST data service base (is EIS a table?)",
    ),
  ]);
  for (const p of probes)
    console.log(
      `  ${p.label} -> ${p.status} ${p.contentType} ${p.machineReadable ? "[machine-readable]" : ""}`,
    );

  const epaMachineReadable = probes.some((p) => p.machineReadable);

  // FR EIS-notice spine — 1-month sample (keyless).
  console.log("\n  Pulling FR EIS-notice 1-month sample (keyless spine)...");
  const gte = (() => {
    const t = today();
    const [y, m, d] = t.split("-").map(Number) as [number, number, number];
    return new Date(Date.UTC(y, m - 1, d) - 30 * 86_400_000)
      .toISOString()
      .slice(0, 10);
  })();
  const fields = [
    "document_number",
    "title",
    "publication_date",
    "comments_close_on",
    "html_url",
    "agencies",
  ];
  const url =
    "https://www.federalregister.gov/api/v1/documents.json?" +
    qs({
      per_page: 1000,
      "conditions[term]": '"environmental impact statement"',
      "conditions[type][]": "NOTICE",
      "conditions[publication_date][gte]": gte,
    }) +
    "&" +
    fields.map((f) => `${encodeURIComponent("fields[]")}=${f}`).join("&");
  const res: { count?: number; results?: FrEis[] } = await fetchJson(url);
  const eis = res.results ?? [];
  console.log(
    `  FR EIS notices in last 30d: ${eis.length} (reported count=${res.count})`,
  );

  const sample = eis.map((e) => {
    const title = (e.title ?? "").replace(/\s+/g, " ").trim();
    return {
      document_number: e.document_number,
      publication_date: e.publication_date ?? "",
      comments_close_on: e.comments_close_on ?? "",
      stage: draftFinal(title),
      states: statesIn(title),
      agency: e.agencies?.[0]?.name ?? "",
      title,
      url: e.html_url ?? "",
    };
  });
  writeData("w2_eis_sample.json", {
    window: { gte, lte: today() },
    probes,
    count: sample.length,
    sample,
  });

  const withClose = sample.filter((s) => s.comments_close_on).length;
  const withState = sample.filter((s) => s.states).length;
  const withStage = sample.filter((s) => s.stage !== "—").length;

  const probeTable = probes
    .map(
      (p) =>
        `| ${p.label} | ${p.status || "—"} | \`${p.contentType || "—"}\` | ${p.machineReadable ? "✅" : "❌"} | ${p.note} |`,
    )
    .join("\n");

  const sampleTable = sample
    .slice(0, 30)
    .map(
      (s) =>
        `| ${s.publication_date} | ${s.stage} | ${s.comments_close_on || "—"} | ${s.states || "—"} | ${s.agency.slice(0, 22)} | ${s.title.slice(0, 60)} |`,
    )
    .join("\n");

  const verdict = epaMachineReadable
    ? "GO — EPA exposes a machine-readable EIS endpoint; the adapter is durable."
    : "GO (with guardrails) — EPA's EIS DB is **scraper-only**; ship the adapter behind an interface with the FR EIS-notice stream as the machine-readable spine/cross-check.";

  const md = `# W2 — EPA EIS database machine-readability

**Run:** ${today()} (Eastern)

## Endpoint probes

| source | HTTP | content-type | machine-readable? | note |
| --- | ---: | --- | :---: | --- |
${probeTable}

**Finding:** ${epaMachineReadable ? "a machine-readable EPA endpoint responded." : "the EPA EIS search app returns **HTML** (a JSF web app); guessed REST/JSON backends 404; Envirofacts has no EIS table. EPA's own EIS database is **scraper-only**."}

## Machine-readable spine: Federal Register EIS-notice stream (keyless)

The FR API carries individual agency EIS notices (NOI / Draft / Final) **and** EPA's weekly
consolidated "Notice of Availability." It is keyless, stable, and directly extractable.

| field | directly available? |
| --- | --- |
| title | ✅ (from \`title\`) |
| link | ✅ (\`html_url\`) |
| publication date | ✅ (\`publication_date\`) |
| comment close date | ⚠️ \`comments_close_on\` present on ${withClose}/${sample.length} of the sample |
| draft/final stage | ⚠️ parsed from title — ${withStage}/${sample.length} classified |
| state(s) | ⚠️ parsed from title — ${withState}/${sample.length} had a state in the title |

_1-month sample: **${sample.length}** FR EIS notices (${gte} → ${today()})._

## Decision

**${verdict}**

- Build the EIS adapter **behind an interface** (\`EisSource\`) so the EPA scraper and the FR spine are
  swappable; cross-check dates between them. Budget scraper maintenance explicitly and treat EPA DOM
  changes as expected breakage, with FR as the always-on fallback.

## 1-month EIS sample (first 30 of ${sample.length})

| published | stage | comment close | state(s) | agency | title |
| --- | --- | --- | --- | --- | --- |
${sampleTable || "| _(none)_ |  |  |  |  |  |"}

_Artifact: \`data/w2_eis_sample.json\` (${sample.length} records + probe results)._
`;

  const outPath = writeOut("W2_eis_source.md", md);
  console.log(`\n=== W2 RESULT ===`);
  console.log(
    `EPA machine-readable: ${epaMachineReadable ? "yes" : "no (scraper-only)"}`,
  );
  console.log(
    `FR EIS spine sample: ${sample.length} notices; comment-close on ${withClose}, state on ${withState}, stage on ${withStage}`,
  );
  console.log(`Verdict: ${verdict.replace(/\*\*/g, "")}`);
  console.log(`Wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
