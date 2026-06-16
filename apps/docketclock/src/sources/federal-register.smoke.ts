/**
 * federal-register.smoke.ts — a one-shot LIVE proof of the FR seam (NOT a gated test; it hits the
 * network). Finds a currently-open comment document via the keyless FR list endpoint, fetches the full
 * document, runs it through parseFrObservation, and prints the resulting Observation candidate.
 *
 * Run:  pnpm --filter @yokel/docketclock smoke:fr
 */
import { fetchFrDocument, parseFrObservation } from "./federal-register.js";

function todayEastern(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

async function pickOpenDocumentNumber(): Promise<string> {
  const from = todayEastern();
  const url =
    "https://www.federalregister.gov/api/v1/documents.json?per_page=1" +
    `&conditions[comment_date][gte]=${from}` +
    "&fields[]=document_number&fields[]=title";
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok)
    throw new Error(`FR list query failed: ${res.status} ${res.statusText}`);
  const body = (await res.json()) as {
    count: number;
    results?: { document_number: string; title: string }[];
  };
  const first = body.results?.[0];
  if (!first)
    throw new Error(
      `No open-comment FR documents found for cutoff ${from} (count=${body.count}).`,
    );
  console.log(
    `FR reports ${body.count} open-comment docs (cutoff ${from}); using ${first.document_number}`,
  );
  console.log(`  title: ${first.title}`);
  return first.document_number;
}

async function main(): Promise<void> {
  const docNum = await pickOpenDocumentNumber();
  const raw = await fetchFrDocument(docNum);
  const candidate = parseFrObservation(raw);

  // Print everything except the (large) raw payload, plus a one-line raw-size note.
  const { raw: _raw, ...printable } = candidate;
  console.log("\n=== parsed Observation candidate ===");
  console.log(JSON.stringify(printable, null, 2));
  console.log(
    `\nraw payload: ${JSON.stringify(_raw).length} bytes (omitted above)`,
  );
}

main().catch((err) => {
  console.error("smoke:fr failed:", err);
  process.exit(1);
});
