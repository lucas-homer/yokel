/**
 * envelope.ts — the response-envelope stampers. The SHAPE of the envelope lives in the FROZEN contract
 * (apiItemEnvelope / apiListEnvelope / EnvelopeMeta / Pagination, @yokel/contracts 0.3.0); this module
 * only fills it in per request with the canonical DISCLAIMER + API_VERSION constants and the per-request
 * request_id, so the published OpenAPI (driven by the same contract schemas in server.ts) and the actual
 * response bodies derive from ONE definition and can never diverge.
 *
 * Why every response carries the trio (never suppressed): buyers carry deadline LIABILITY and the FR
 * payloads are "Unofficial XML — NOT legal notice" (docketclock.md). The disclaimer steers a reader back
 * to the official sources before acting; api_version self-identifies a cached/forwarded response's
 * contract generation; request_id is the support/tracing correlation id the client quotes in tickets.
 */
import { API_VERSION, DISCLAIMER, type Pagination } from "@yokel/contracts";

/** { data } + the EnvelopeMeta trio — matches apiItemEnvelope(dataSchema) from the contract. */
export function itemEnvelope<T>(data: T, requestId: string) {
  return {
    data,
    disclaimer: DISCLAIMER,
    api_version: API_VERSION,
    request_id: requestId,
  };
}

/** { data[], pagination } + the EnvelopeMeta trio — matches apiListEnvelope(itemSchema) from the contract. */
export function listEnvelope<T>(
  rows: T[],
  pagination: Pagination,
  requestId: string,
) {
  return {
    data: rows,
    pagination,
    disclaimer: DISCLAIMER,
    api_version: API_VERSION,
    request_id: requestId,
  };
}
