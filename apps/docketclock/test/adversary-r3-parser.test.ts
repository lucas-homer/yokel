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
function ev(
  text: string,
  overrides: Partial<AmendmentEvidence> = {},
): AmendmentEvidence {
  return {
    ocd_id: "B",
    fr_document_number: "2026-20000",
    fr_observation_id: "b",
    govinfo_observation_id: "g",
    publication_date: "2026-10-01",
    is_extension: true,
    is_correction: false,
    is_reopening: false,
    is_withdrawal: false,
    fr_comments_close_on: null,
    fr_dates_text: null,
    govinfo_text: text,
    basis: "docket_rin",
    ...overrides,
  };
}
for (const [label, text] of [
  [
    "prior-close exclusion hides a still-live second deadline",
    "Comments submitted by mail are extended to November 2, 2026. Electronic submissions must still reach the agency by October 16, 2026.",
  ],
  [
    "publication exclusion hides a same-day deadline",
    "Comments submitted by mail are extended to November 2, 2026. Electronic submissions must still reach the agency by October 1, 2026.",
  ],
] as const)
  test(`R3 ${label}`, () => {
    const got = resolveAmendedClose(original, [ev(text)]);
    assert.equal(got.kind, "ambiguous", JSON.stringify(got));
  });
for (const role of [
  "public symposium",
  "oral presentations",
  "public inspection",
  "petitions for reconsideration",
])
  test(`R3 correction of ${role} does not move comment close`, () => {
    const got = resolveAmendedClose(original, [
      ev(
        `In the DATES section, the date for ${role}, "October 16, 2026" should read "October 26, 2026".`,
        { is_extension: false, is_correction: true },
      ),
    ]);
    assert.notEqual(got.kind, "amended", JSON.stringify(got));
  });
