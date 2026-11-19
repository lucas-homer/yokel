/**
 * slim-raw.test.ts — slimFrRaw (SQL) must return exactly what slimRaw (TypeScript) returns, so the chain
 * candidate read and the amendment corpus can trim the FR payload in the database (Neon transfer quota,
 * 2026-11-19) without changing a single extracted field.
 *
 * Needs a THROWAWAY Postgres:  DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { createClient } from "../src/db/client.js";
import { slimFrRaw, slimRaw } from "../src/reconcile/persist.js";
import { extractFr } from "../src/reconcile/extract.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const cases: [string, unknown][] = [
  [
    "a full FR payload",
    {
      document_number: "2026-01234",
      publication_date: "2026-05-01",
      title: "Air Plan Approval; Extension of Comment Period",
      dates: "Comments must be received on or before June 16, 2026.",
      comments_close_on: "2026-06-16",
      comment_url: "https://www.regulations.gov/commenton/EPA-HQ-1",
      docket_ids: ["EPA-HQ-OAR-2026-0001"],
      regulation_id_numbers: ["2060-AA01"],
      citation: "91 FR 57828",
      correction_of: "https://www.federalregister.gov/d/2026-01000",
      corrections: [],
      abstract: "x".repeat(4000),
      full_text_xml_url: "https://example.test/full.xml",
      agencies: [{ name: "EPA", id: 145 }],
    },
  ],
  ["only unused keys", { abstract: "long", agencies: [] }],
  ["an empty object", {}],
  ["explicit nulls stay present", { citation: null, dates: null }],
  ["a JSON array", [1, 2, 3]],
  ["a JSON string", "not an object"],
  ["JSON null", null],
];

const sql = createClient();
try {
  for (const [name, raw] of cases) {
    const [row] = await sql<{ raw: unknown }[]>`
      select ${slimFrRaw(sql)} as raw
      from (select ${sql.json(raw as never)}::jsonb as raw) o
    `;
    const want = slimRaw(raw);
    assert(
      `${name}: SQL slim equals slimRaw`,
      JSON.stringify(row!.raw, Object.keys(row!.raw as object).sort()) ===
        JSON.stringify(want, Object.keys(want).sort()),
      `${JSON.stringify(row!.raw)} vs ${JSON.stringify(want)}`,
    );
    assert(
      `${name}: extractFr is unchanged`,
      JSON.stringify(extractFr(row!.raw)) === JSON.stringify(extractFr(raw)),
    );
  }
} finally {
  await sql.end();
}

console.log("slim-raw.test.ts");
console.log(out.join("\n"));
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
