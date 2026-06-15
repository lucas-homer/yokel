/**
 * Ingestion — write an Observation candidate THROUGH the append-only log, with payload-hash dedupe.
 *
 * The log is the spine (docs/architecture/docketclock.md): every distinct raw payload appends exactly
 * one immutable row. Re-fetching the SAME payload must NOT append a duplicate — we skip the insert if
 * the candidate's payload_hash equals the LATEST row for that (source, document_id), using the
 * (fr_document_number, source, fetched_at desc) index. The insert and its observation_targets fan-out
 * (M:N: one notice -> many windows) happen in ONE transaction.
 */
import type { Sql } from "../db/client.js";
import type { ObservationCandidate } from "../sources/federal-register.js";

export interface IngestResult {
  inserted: boolean;
  observationId: string | null;
  ocdId: string;
}

/**
 * Insert the candidate as a new Observation row (+ primary observation_target), unless its payload_hash
 * matches the latest stored row for the same source document — in which case skip (idempotent re-fetch).
 *
 * document_id is fr_document_number for FR. The dedupe lookup keys on (source, fr_document_number)
 * ordered by fetched_at desc, exactly the shape the observations_fr_doc_idx index serves.
 */
export async function ingestObservation(
  sql: Sql,
  candidate: ObservationCandidate,
): Promise<IngestResult> {
  const ocdId = candidate.ocd_id;

  // Dedupe: compare against the LATEST payload for this (source, document_id). FR keys on
  // fr_document_number; if absent there is nothing to dedupe against (insert unconditionally).
  if (candidate.fr_document_number) {
    const [latest] = await sql<{ payload_hash: string }[]>`
      select payload_hash
      from observations
      where source = ${candidate.source}
        and fr_document_number = ${candidate.fr_document_number}
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
