/**
 * Ingestion — write an Observation candidate THROUGH the append-only log, with payload-hash dedupe.
 *
 * The log is the spine (docs/architecture/docketclock.md): every distinct raw payload appends exactly
 * one immutable row. Re-fetching the SAME payload must NOT append a duplicate — we skip the insert if
 * the candidate's payload_hash equals the LATEST row for that (source, document_id). The document key is
 * source-specific: FR keys on fr_document_number (observations_fr_doc_idx), Regs.gov on regs_document_id
 * (observations_regs_doc_idx). The insert and its observation_targets fan-out (M:N: one notice -> many
 * windows) happen in ONE transaction.
 */
import type { Sql } from "../db/client.js";
import type { ObservationCandidate } from "../sources/observation-candidate.js";

export interface IngestResult {
  inserted: boolean;
  observationId: string | null;
  ocdId: string;
}

/**
 * Insert the candidate as a new Observation row (+ primary observation_target), unless its payload_hash
 * matches the latest stored row for the same source document — in which case skip (idempotent re-fetch).
 *
 * The dedupe lookup keys on (source, <document-key>) ordered by fetched_at desc, exactly the shape the
 * per-source latest-first index serves (observations_fr_doc_idx / observations_regs_doc_idx).
 */
export async function ingestObservation(
  sql: Sql,
  candidate: ObservationCandidate,
): Promise<IngestResult> {
  const ocdId = candidate.ocd_id;

  // Dedupe: compare against the LATEST payload for this source's document key (FR -> fr_document_number,
  // Regs.gov -> regs_document_id). If the key is absent there is nothing to dedupe against (insert
  // unconditionally).
  //
  // CONCURRENCY(single-writer): this read-then-insert assumes ONE ingest writer (the differential
  // polling loop), so the latest-hash check can't race. Deliberately NOT a UNIQUE(payload_hash)
  // constraint — the log is an append-only time series and the same hash legitimately RE-appears
  // when a payload changes and later reverts; we only skip an *immediate* re-fetch of the latest.
  // When multi-writer ingest arrives, harden with an advisory lock / serializable txn (or tolerate
  // the rare benign duplicate, since replay is idempotent) — not a hash uniqueness constraint.
  const dedupeColumn =
    candidate.source === "regulations_gov"
      ? "regs_document_id"
      : "fr_document_number";
  const dedupeValue =
    candidate.source === "regulations_gov"
      ? candidate.regs_document_id
      : candidate.fr_document_number;
  if (dedupeValue) {
    const [latest] = await sql<{ payload_hash: string }[]>`
      select payload_hash
      from observations
      where source = ${candidate.source}
        and ${sql(dedupeColumn)} = ${dedupeValue}
      order by fetched_at desc
      limit 1
    `;
    if (latest && latest.payload_hash === candidate.payload_hash) {
      return { inserted: false, observationId: null, ocdId };
    }
  }

  // Insert the row and its primary target atomically — a row without its target would be a
  // half-written observation the M:N fan-out can't see.
  const observationId = await sql.begin(async (tx) => {
    const [row] = await tx<{ observation_id: string }[]>`
      insert into observations
        (ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
         payload_hash, fetched_at, parser_version, raw_dates_text,
         is_extension, is_correction, is_withdrawal, raw)
      values
        (${candidate.ocd_id}, ${candidate.source}, ${candidate.fr_document_number},
         ${candidate.regs_document_id}, ${candidate.regs_object_id},
         ${candidate.payload_hash}, ${candidate.fetched_at}, ${candidate.parser_version},
         ${candidate.raw_dates_text}, ${candidate.is_extension}, ${candidate.is_correction},
         ${candidate.is_withdrawal}, ${tx.json(candidate.raw as never)})
      returning observation_id
    `;
    const id = row!.observation_id;

    // Primary target: the derived window this observation feeds. (Multi-target fan-out for an
    // extension that touches N dockets — EPA 2025-02910 — is the reconciler's job to add later.)
    await tx`
      insert into observation_targets (observation_id, ocd_id)
      values (${id}, ${candidate.ocd_id})
      on conflict do nothing
    `;
    return id;
  });

  return { inserted: true, observationId, ocdId };
}
