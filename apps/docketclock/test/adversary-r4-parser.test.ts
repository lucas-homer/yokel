import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  extractCorrectionBody,
  extractDatesSection,
  govinfoPlainText,
} from "../src/sources/govinfo.js";
import {
  resolveAmendedClose,
  type AmendmentEvidence,
} from "../src/reconcile/amendment.js";

const original = {
  fr_close: "2026-10-16",
  publication_date: "2026-09-01",
  fr_document_number: "2026-10000",
};
function evidence(text: string, correction = false): AmendmentEvidence {
  return {
    ocd_id: "B",
    fr_document_number: "2026-20000",
    fr_observation_id: "b",
    govinfo_observation_id: "g",
    publication_date: "2026-10-01",
    is_extension: !correction,
    is_correction: correction,
    is_reopening: false,
    is_withdrawal: false,
    fr_comments_close_on: null,
    fr_dates_text: null,
    govinfo_text: text,
    basis: "docket_rin",
  };
}
for (const [name, competing] of [
  [
    "future passive closed",
    "The electronic comment docket will be closed on October 16, 2026.",
  ],
  [
    "originally modifies submissions",
    "Previously submitted comments must be resubmitted by October 16, 2026.",
  ],
  [
    "originally modifies announcement",
    "As originally announced, electronic comments remain due October 16, 2026.",
  ],
  ["live parenthetical", "Electronic comments remain due (October 16, 2026)."],
  [
    "dated governs submission requirement",
    "Electronic comments must be dated October 16, 2026.",
  ],
] as const)
  test(`R4 competing deadline: ${name}`, () => {
    const got = resolveAmendedClose(original, [
      evidence(
        `Comments submitted by mail are extended to November 2, 2026. ${competing}`,
      ),
    ]);
    assert.equal(got.kind, "ambiguous", JSON.stringify(got));
  });
for (const role of [
  "public hearing",
  '"public hearing"',
  "PM2.5",
  "PM2-5",
  "Form-1",
  "[[Page 64409]] public hearing",
])
  test(`R4 correction qualifier: ${role}`, () => {
    const got = resolveAmendedClose(original, [
      evidence(
        `In the DATES section, the date for ${role}, "October 16, 2026" should read "October 26, 2026".`,
        true,
      ),
    ]);
    assert.notEqual(got.kind, "amended", JSON.stringify(got));
  });

const page = (doc: string) =>
  govinfoPlainText(
    readFileSync(
      new URL(`./fixtures/fr-amendments/govinfo/${doc}.htm`, import.meta.url),
      "utf8",
    ),
  );
for (const doc of ["2026-19710", "2026-20328"]) {
  test(`R4 real ${doc} unchanged positive`, () => {
    const got = resolveAmendedClose(original, [
      evidence(extractDatesSection(page(doc))!),
    ]);
    assert.equal(got.kind === "amended" && got.date, "2026-11-02");
  });
  test(`R4 real ${doc} plus live future-passive deadline`, () => {
    const text =
      extractDatesSection(page(doc))! +
      " The electronic comment docket will be closed on October 16, 2026.";
    const got = resolveAmendedClose(original, [evidence(text)]);
    assert.equal(got.kind, "ambiguous", JSON.stringify(got));
  });
}
test("R4 real IRS correction unchanged positive", () => {
  const got = resolveAmendedClose(original, [
    evidence(extractCorrectionBody(page("C1-2026-18574"))!, true),
  ]);
  assert.equal(got.kind === "amended" && got.date, "2026-10-26");
});
test("R4 real IRS correction with quoted role cannot bind", () => {
  const text = extractCorrectionBody(page("C1-2026-18574"))!.replace(
    "DATES section,",
    'DATES section, for the "public hearing",',
  );
  const got = resolveAmendedClose(original, [evidence(text, true)]);
  assert.notEqual(got.kind, "amended", JSON.stringify(got));
});
