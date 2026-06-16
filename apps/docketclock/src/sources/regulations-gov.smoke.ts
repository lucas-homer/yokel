/**
 * regulations-gov.smoke.ts — a one-shot LIVE proof of the Regs.gov v4 seam (NOT a gated test; it hits
 * the network and needs a key). Lists currently-open comment documents (newest lastModifiedDate first),
 * picks one that carries an frDocNum (the FR<->Regs join), fetches its detail, runs it through
 * parseRegsObservation, and prints the resulting Observation candidate.
 *
 * Pass --capture to also write the raw detail JSON to test/fixtures/regs-<documentId>.json (used to seed
 * the deterministic test).
 *
 * Key: reads REGS_API_KEY from the repo-root .env (nothing auto-loads it). Run:
 *   pnpm --filter @yokel/docketclock smoke:regs            # print only
 *   pnpm --filter @yokel/docketclock smoke:regs -- --capture
 */
import { existsSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import {
  fetchRegsDocument,
  listChangedDocuments,
  parseRegsObservation,
} from "./regulations-gov.js";

// Load REGS_API_KEY (+ any REGS_API_BASE) from the repo-root .env if present.
const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

async function main(): Promise<void> {
  const capture = process.argv.includes("--capture");

  // Newest-changed open-comment documents (no cursor => the most recent page).
  const items = await listChangedDocuments({ pageSize: 50 });
  console.log(
    `Regs.gov returned ${items.length} open-comment documents (page 1).`,
  );
  if (items.length === 0) throw new Error("no open-comment documents returned");

  // Find one with an frDocNum so we exercise the FR<->Regs join path; fall back to the first.
  let chosen = "";
  for (const it of items) {
    const detail = (await fetchRegsDocument(it.documentId)) as {
      data?: { attributes?: { frDocNum?: string | null } | null } | null;
    };
    if (detail?.data?.attributes?.frDocNum) {
      chosen = it.documentId;
      await proveAndMaybeCapture(detail, capture);
      return;
    }
    chosen = it.documentId;
  }
  // None had an frDocNum — prove the fallback (regs:objectId) path on the last one fetched.
  const detail = await fetchRegsDocument(chosen);
  await proveAndMaybeCapture(detail, capture);
}

async function proveAndMaybeCapture(
  detail: unknown,
  capture: boolean,
): Promise<void> {
  const candidate = parseRegsObservation(detail);
  const { raw: _raw, ...printable } = candidate;
  console.log("\n=== parsed Observation candidate ===");
  console.log(JSON.stringify(printable, null, 2));
  console.log(
    `\nraw payload: ${JSON.stringify(_raw).length} bytes (omitted above)`,
  );

  if (capture) {
    const HERE = fileURLToPath(new URL(".", import.meta.url));
    const out = join(
      HERE,
      "..",
      "..",
      "test",
      "fixtures",
      `regs-${candidate.regs_document_id}.json`,
    );
    await writeFile(out, JSON.stringify(detail, null, 2) + "\n", "utf8");
    console.log(`\ncaptured fixture -> ${out}`);
  }
}

main().catch((err) => {
  console.error("smoke:regs failed:", err);
  process.exit(1);
});
