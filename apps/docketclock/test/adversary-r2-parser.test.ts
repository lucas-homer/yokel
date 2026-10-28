import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  resolveAmendedClose,
  type AmendmentEvidence,
} from "../src/reconcile/amendment.js";
import {
  extractDatesSection,
  govinfoPlainText,
} from "../src/sources/govinfo.js";
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
test("R2 restatement must not bypass conflicting FR metadata", () => {
  const first = ev("Comments must be received on or before November 2, 2026.");
  const second = ev(first.govinfo_text!, {
    ocd_id: "C",
    fr_observation_id: "c",
    govinfo_observation_id: "gc",
    fr_document_number: "2026-20001",
    publication_date: "2026-10-20",
    fr_comments_close_on: "2026-11-20",
  });
  const got = resolveAmendedClose(original, [first, second]);
  assert.equal(got.kind, "ambiguous", JSON.stringify(got));
});
test("R2 real Interior text with anaphoric second sentence keeps both deadlines", () => {
  const raw = readFileSync(
    new URL("./fixtures/fr-amendments/govinfo/2026-14450.htm", import.meta.url),
    "utf8",
  );
  const text = extractDatesSection(govinfoPlainText(raw))!.replace(
    "Therefore, comments should be submitted",
    "Therefore, they should be submitted",
  );
  const got = resolveAmendedClose(
    { ...original, fr_close: "2026-08-01", publication_date: "2026-06-01" },
    [ev(text, { publication_date: "2026-07-17" })],
  );
  assert.equal(got.kind, "ambiguous", JSON.stringify(got));
});
test("R2 DATES correction of hearing date is not a comment correction", () => {
  const got = resolveAmendedClose(original, [
    ev(
      'In the DATES section, the public hearing date "October 16, 2026" should read "October 26, 2026".',
      { is_extension: false, is_correction: true },
    ),
  ]);
  assert.notEqual(got.kind, "amended", JSON.stringify(got));
});
test("R2 later unparsed comment deadline must not silently preserve earlier amendment", () => {
  const first = ev("Comments must be received on or before November 2, 2026.");
  const second = ev("Comments should reach the agency by November 20, 2026.", {
    publication_date: "2026-10-20",
    ocd_id: "C",
    fr_observation_id: "c",
    govinfo_observation_id: "gc",
    fr_document_number: "2026-20001",
  });
  const got = resolveAmendedClose(original, [first, second]);
  assert.notEqual(got.kind, "amended", JSON.stringify(got));
});
