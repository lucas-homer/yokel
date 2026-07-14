/**
 * export-windows.ts — read-only JSONL export of the live `participation_windows` projection for the
 * offline cross-check (slice V, PR-V2). `spikes/src/xcheck.ts` joins this file against the
 * Mirrulations/spicy-regs Parquet in DuckDB and diffs Eastern-date closes + status — the independent
 * "would an outside dataset agree with us?" differential the architecture reserves Mirrulations for
 * (offline eval only, never a live freshness source).
 *
 * SAFE: read-only on Postgres; writes ONE file, `spikes/data/windows.jsonl` by default (gitignored —
 * regenerable scratch, like every spikes data pull). One JSON object per line; xcheck reads it with
 * DuckDB's read_json.
 *
 * Exported per window: the join keys (fr_document_number, regs_document_id, docket_id), the claim
 * under comparison (resolved_close_utc/_display, confidence, status), the raw per-source values
 * (transparency for triage — they say WHICH source we believed), and version/derived_at (freshness,
 * so a disagreement can be triaged bulk_stale when the parquet snapshot simply lags the live row).
 *
 * Run:  DATABASE_URL=… pnpm --filter @yokel/docketclock export:windows
 *       …              export:windows -- --out /path/to/windows.jsonl
 *       (DATABASE_URL via the usual local port-forward of svc/docketclock-pg-rw)
 */
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";

const envPath = fileURLToPath(new URL("../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

// apps/docketclock/scripts/ → repo-root spikes/data/ (gitignored).
const DEFAULT_OUT = fileURLToPath(
  new URL("../../../spikes/data/windows.jsonl", import.meta.url),
);
const outFlag = process.argv.indexOf("--out");
const OUT_PATH =
  outFlag !== -1 && process.argv[outFlag + 1]
    ? process.argv[outFlag + 1]
    : DEFAULT_OUT;

interface WindowExportRow {
  ocd_id: string;
  fr_document_number: string | null;
  regs_document_id: string | null;
  docket_id: string[];
  window_type: string;
  resolved_close_utc: Date | null;
  resolved_close_display: string | null;
  raw_fr_close_date: string | null;
  raw_regs_close_datetime: string | null;
  confidence: string;
  status: string;
  version: number;
  derived_at: Date;
}

async function main(): Promise<void> {
  const sql = createClient();
  try {
    const rows = await sql<WindowExportRow[]>`
      select ocd_id, fr_document_number, regs_document_id, docket_id, window_type,
             resolved_close_utc, resolved_close_display,
             raw_fr_close_date, raw_regs_close_datetime,
             confidence, status, version, derived_at
      from participation_windows
      order by ocd_id
    `;
    console.log(`read ${rows.length} window(s)`);

    const lines = rows.map((r) =>
      JSON.stringify({
        ...r,
        resolved_close_utc: r.resolved_close_utc?.toISOString() ?? null,
        derived_at: r.derived_at.toISOString(),
      }),
    );
    mkdirSync(dirname(OUT_PATH), { recursive: true });
    writeFileSync(OUT_PATH, lines.join("\n") + (lines.length ? "\n" : ""));
    console.log(`wrote ${OUT_PATH}`);
    console.log("next: pnpm --filter @yokel/spikes xcheck");
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((err) => {
  console.error("export failed:", err);
  process.exit(1);
});
