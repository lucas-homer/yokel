import { test } from "node:test";
import assert from "node:assert/strict";
import {
  resolveAmendedClose,
  type AmendmentEvidence,
} from "../src/reconcile/amendment.js";
const original = {
  fr_close: "2026-10-16",
  publication_date: "2026-09-01",
  fr_document_number: "2026-10000",
};
const evidence = (
  overrides: Partial<AmendmentEvidence> = {},
): AmendmentEvidence => ({
  ocd_id: "ocd-participation-window/federal/2026-20000",
  fr_document_number: "2026-20000",
  fr_observation_id: "00000000-0000-4000-8000-000000000001",
  govinfo_observation_id: "00000000-0000-4000-8000-000000000002",
  publication_date: "2026-10-01",
  is_extension: true,
  is_correction: false,
  is_reopening: false,
  is_withdrawal: false,
  fr_comments_close_on: null,
  fr_dates_text: null,
  govinfo_text: null,
  basis: "doc_number",
  ...overrides,
});
test("a hearing range is not a comment deadline", () => {
  const result = resolveAmendedClose(original, [
    evidence({
      govinfo_text:
        "Comments are due November 2, 2026. Public hearings will run November 18 through November 20, 2026.",
    }),
  ]);
  console.log("hearing range:", JSON.stringify(result));
  assert.notEqual(result.kind === "amended" && result.date, "2026-11-20");
});
test("unrecognized second comment deadline prevents confidence", () => {
  const result = resolveAmendedClose(original, [
    evidence({
      govinfo_text:
        "Comments on the proposed rule must be received on or before November 2, 2026. Comments on the information collection are due December 7, 2026.",
    }),
  ]);
  console.log("two deadlines:", JSON.stringify(result));
  assert.equal(result.kind, "ambiguous");
});
test("DATES mention cannot authorize correcting an unrelated effective date", () => {
  const result = resolveAmendedClose(original, [
    evidence({
      is_extension: false,
      is_correction: true,
      govinfo_text:
        'In document 2026-10000 beginning on page 10000: 1. In the DATES section, "contact" should read "comments". 2. In the SUPPLEMENTARY INFORMATION section, the effective date "October 16, 2026" should read "November 20, 2026".',
    }),
  ]);
  console.log("unrelated correction:", JSON.stringify(result));
  assert.notEqual(result.kind, "amended");
});
test("second extension before the extended close does not revert to original deadline", () => {
  const result = resolveAmendedClose(original, [
    evidence({ govinfo_text: "Comments are extended to November 2, 2026." }),
    evidence({
      fr_document_number: "2026-21000",
      publication_date: "2026-10-20",
      govinfo_text: "Comments are extended to November 20, 2026.",
    }),
  ]);
  console.log("successive extensions:", JSON.stringify(result));
  assert.equal(result.kind === "amended" && result.date, "2026-11-20");
});

import { fetchTextWithRetry } from "../src/sources/http.js";
test("GovInfo timeout also bounds reading a stalled response body", async () => {
  const saved = globalThis.fetch;
  let controller!: ReadableStreamDefaultController;
  globalThis.fetch = async (_input, init) =>
    new Response(
      new ReadableStream({
        start(c) {
          controller = c;
          c.enqueue(new TextEncoder().encode("<pre>"));
          init?.signal?.addEventListener("abort", () =>
            c.error(new Error("aborted")),
          );
        },
      }),
    );
  try {
    const request = fetchTextWithRetry("https://example.invalid", {
      timeoutMs: 5,
      retries: 0,
    }).then(
      () => "completed",
      () => "aborted",
    );
    const outcome = await Promise.race([
      request,
      new Promise((r) => setTimeout(() => r("still waiting"), 50)),
    ]);
    // Release a non-aborting implementation; a correct one already errored the stream on abort, and
    // closing an errored stream throws (ERR_INVALID_STATE). The assertion below carries the finding.
    try {
      controller.close();
    } catch {}
    await request;
    console.log("body timeout:", outcome);
    assert.equal(outcome, "aborted");
  } finally {
    globalThis.fetch = saved;
  }
});

import { readFileSync } from "node:fs";
import { reconcile } from "../src/reconcile/reconcile.js";
import type { Observation } from "@yokel/contracts";
test("a pin predating newly published amendment must be re-reviewed", () => {
  const stored: Observation[] = JSON.parse(
    readFileSync(
      new URL(
        "./fixtures/fr-amendments/stored/observations.json",
        import.meta.url,
      ),
      "utf8",
    ),
  );
  const fr = stored.find(
    (o) =>
      o.source === "federal_register" && o.fr_document_number === "2026-18481",
  )!;
  const pin: Observation = {
    ...fr,
    observation_id: "ffffffff-0000-4000-8000-000000000001",
    source: "human_review",
    fetched_at: "2026-10-01T00:00:00.000Z",
    raw: {
      kind: "pin_close",
      pinned_close_date: "2026-10-13",
      note: "Reviewed original notice before extension published",
      operator: "adversary",
      reviewed_payload_hashes: [fr.payload_hash],
    },
  };
  const a = resolveAmendedClose(
    {
      fr_close: "2026-10-13",
      publication_date: "2026-09-10",
      fr_document_number: "2026-18481",
    },
    [
      evidence({
        publication_date: "2026-10-05",
        govinfo_text: "Submit comments on or before November 2, 2026.",
      }),
    ],
  );
  const result = reconcile([fr, pin], new Date("2026-10-27T00:00:00Z"), {
    amendment: a,
  });
  console.log(
    "old pin with new amendment:",
    JSON.stringify({
      confidence: result.window.confidence,
      close: result.window.resolved_close_utc,
      flags: result.window.conflict_flags,
    }),
  );
  assert.equal(result.window.conflict_flags.includes("human_resolved"), false);
});
