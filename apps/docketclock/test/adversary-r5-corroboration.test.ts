import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { Observation } from "@yokel/contracts";
import {
  resolveAmendedClose,
  type AmendmentEvidence,
} from "../src/reconcile/amendment.js";
import { reconcile } from "../src/reconcile/reconcile.js";
import {
  extractDatesSection,
  govinfoPlainText,
} from "../src/sources/govinfo.js";

// Real USDA published text, with an explicit still-operative electronic deadline.
// Present perfect "has been scheduled" does not say the schedule was superseded.
const published = extractDatesSection(
  govinfoPlainText(
    readFileSync(
      new URL(
        "./fixtures/fr-amendments/govinfo/2026-19710.htm",
        import.meta.url,
      ),
      "utf8",
    ),
  ),
)!;
const text =
  published +
  " The electronic comment period has been scheduled to close on October 13, 2026.";
const original = {
  fr_close: "2026-10-13",
  publication_date: "2026-09-11",
  fr_document_number: "2026-18531",
};
const e: AmendmentEvidence = {
  ocd_id: "ocd-participation-window/federal/2026-19710",
  fr_document_number: "2026-19710",
  fr_observation_id: "b",
  govinfo_observation_id: "g",
  publication_date: "2026-09-25",
  is_extension: true,
  is_correction: false,
  is_reopening: false,
  is_withdrawal: false,
  fr_comments_close_on: "2026-11-02",
  fr_dates_text: text,
  govinfo_text: text,
  basis: "citation",
};
const stored = JSON.parse(
  readFileSync(
    new URL(
      "./fixtures/fr-amendments/stored/observations.json",
      import.meta.url,
    ),
    "utf8",
  ),
) as Observation[];
const own = stored.filter(
  (o) => o.ocd_id === "ocd-participation-window/federal/2026-18531",
);
const now = new Date("2026-10-27T12:00:00Z");

test("R5: a currently scheduled electronic close remains a competing deadline", () => {
  assert.equal(resolveAmendedClose(original, [e]).kind, "ambiguous");
});

test("R5: FR metadata echo cannot rescue a multi-deadline parse", () => {
  const frOnly = own.filter((o) => o.source === "federal_register");
  const baseline = reconcile(frOnly, now).window;
  const actual = reconcile(frOnly, now, {
    amendmentInputs: { original, amendments: [e] },
  }).window;
  assert.deepEqual(actual, baseline);
});

test("R5: matching portal cannot erase a competing electronic deadline", () => {
  const baseline = reconcile(own, now).window;
  const actual = reconcile(own, now, {
    amendmentInputs: {
      original,
      amendments: [{ ...e, fr_comments_close_on: null }],
    },
  }).window;
  assert.deepEqual(actual, baseline);
});
