/**
 * backfill-reopening-flag.ts — DEV-ONLY one-shot: re-derive every observation's notice-type flags from
 * its retained `raw`, so existing rows pick up the #O4 is_reopening split (and shed the stale
 * is_extension=true that a reopening used to carry). NOT a migration — it is never wired into the
 * production migrate Job, because it briefly disables the append-only guard.
 *
 * WHY A BACKFILL (not re-ingest). The observation log is append-only and content-deduped (payload_hash),
 * so bumping parser_version does NOT cause settled notices to be re-observed — their flags would stay at
 * the old v1 classification forever. Since `raw` is retained intact, we can RE-DERIVE the v2 flags from it
 * directly. This reconstructs exactly what parser v2 WOULD have written (frNoticeFlags / regsNoticeFlags —
 * the SAME functions the live adapters use, so there is no drift), so it is re-derivation, not fabrication.
 *
 * APPEND-ONLY SAFETY. `observations` carries a BEFORE UPDATE trigger (0001) that rejects row mutation. The
 * whole pass runs inside ONE transaction that disables `observations_append_only`, UPDATEs, then re-enables
 * it. DDL is transactional in Postgres, so if anything throws the transaction rolls back and the trigger is
 * restored automatically — the guard can never be left off. This is acceptable ONLY because it is a
 * controlled dev one-shot over disposable data; production never runs it.
 *
 * IDEMPOTENT: deterministic re-derivation, so re-running is a no-op (0 updated). Run AFTER migration 0007.
 *
 * Run: DATABASE_URL=... pnpm --filter @yokel/docketclock tsx src/db/backfill-reopening-flag.ts
 */
import { pathToFileURL } from "node:url";
import { createClient, type Sql } from "./client.js";
import {
  PARSER_VERSION as FR_PARSER_VERSION,
  frNoticeFlags,
} from "../sources/federal-register.js";
import {
  PARSER_VERSION as REGS_PARSER_VERSION,
  regsNoticeFlags,
} from "../sources/regulations-gov.js";

export interface BackfillResult {
  scanned: number; // observations examined
  updated: number; // observations whose flags or parser_version actually changed
  skipped: number; // rows of a source we don't re-derive (e.g. govinfo) — left untouched
}

/**
 * Re-derive notice flags + parser_version for every FR/Regs observation from its `raw`, updating only the
 * rows that actually change. Runs with the append-only trigger disabled inside a single transaction.
 */
export async function backfillReopeningFlag(sql: Sql): Promise<BackfillResult> {
  const rows = await sql<
    {
      observation_id: string;
      source: string;
      raw: unknown;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
      parser_version: string;
    }[]
  >`
    select observation_id, source, raw,
           is_extension, is_correction, is_withdrawal, is_reopening, parser_version
    from observations
  `;

  let updated = 0;
  let skipped = 0;

  await sql.begin(async (tx) => {
    // Disable the row-mutation guard for the duration of this transaction only. A rollback (on any throw
    // below) restores it automatically — DDL is transactional — so the guard is never left off.
    await tx`alter table observations disable trigger observations_append_only`;

    for (const r of rows) {
      let flags;
      let pv: string;
      if (r.source === "federal_register") {
        flags = frNoticeFlags(r.raw);
        pv = FR_PARSER_VERSION;
      } else if (r.source === "regulations_gov") {
        flags = regsNoticeFlags(r.raw);
        pv = REGS_PARSER_VERSION;
      } else {
        skipped++; // a source we don't classify (e.g. govinfo) — leave it exactly as it is
        continue;
      }

      const changed =
        flags.is_extension !== r.is_extension ||
        flags.is_correction !== r.is_correction ||
        flags.is_withdrawal !== r.is_withdrawal ||
        flags.is_reopening !== r.is_reopening ||
        pv !== r.parser_version;
      if (!changed) continue;

      await tx`
        update observations set
          is_extension   = ${flags.is_extension},
          is_correction  = ${flags.is_correction},
          is_withdrawal  = ${flags.is_withdrawal},
          is_reopening   = ${flags.is_reopening},
          parser_version = ${pv}
        where observation_id = ${r.observation_id}
      `;
      updated++;
    }

    await tx`alter table observations enable trigger observations_append_only`;
  });

  return { scanned: rows.length, updated, skipped };
}

// CLI entrypoint — only when run directly, not when imported by tests.
const invokedPath = process.argv[1];
if (invokedPath && import.meta.url === pathToFileURL(invokedPath).href) {
  const sql = createClient();
  try {
    const result = await backfillReopeningFlag(sql);
    console.log(
      `✅ reopening backfill: scanned ${result.scanned}, updated ${result.updated}, skipped ${result.skipped}`,
    );
  } finally {
    await sql.end();
  }
}
