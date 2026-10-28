/**
 * amendment-round3.test.ts — the round-3 adversarial-review findings 2–3 (ADR 0016 §4), PURE, on real
 * GovInfo pages (test/fixtures/fr-amendments/govinfo). Finding 1 (per-state citation uniqueness) needs
 * the DB: adversary-r3-citation-history.test.ts and amendment-citation-history.test.ts.
 *
 *   #2 a date is excluded ONLY by textual context (citation / past / replaced) — never by its value;
 *      the real positives still read their close
 *   #3 a correction instruction binds only when every word of its sentence outside the quoted strings and
 *      the GPO header is on the closed-world allowlist (location / comment period / boilerplate)
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/amendment-round3.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  commentDeadlines,
  correctionQualifiers,
  resolveAmendedClose,
  type AmendmentEvidence,
} from "../src/reconcile/amendment.js";
import {
  extractCorrectionBody,
  extractDatesSection,
  govinfoPlainText,
} from "../src/sources/govinfo.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const GOV = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "fr-amendments",
  "govinfo",
);
const page = (doc: string) =>
  govinfoPlainText(readFileSync(join(GOV, `${doc}.htm`), "utf8"));
const ORIG = {
  fr_close: "2026-10-16",
  publication_date: "2026-09-01",
  fr_document_number: "2026-10000",
};
const ev = (over: Partial<AmendmentEvidence> = {}): AmendmentEvidence => ({
  ocd_id: "ocd-participation-window/federal/2026-40000",
  fr_document_number: "2026-40000",
  fr_observation_id: "00000000-0000-4000-8000-000000004000",
  govinfo_observation_id: null,
  publication_date: "2026-10-01",
  is_extension: true,
  is_correction: false,
  is_reopening: false,
  is_withdrawal: false,
  fr_comments_close_on: null,
  fr_dates_text: null,
  govinfo_text: null,
  basis: "docket_rin",
  ...over,
});
const read = (text: string) => JSON.stringify(commentDeadlines(text));

// ── #2 — context, never value ───────────────────────────────────────────────────────────────────────
{
  for (const [doc, close] of [
    ["2026-19710", "2026-11-02"], // USDA: "originally published on September 11, 2026, (91 FR 57828)"
    ["2026-20328", "2026-11-02"], // Census
    ["2026-15231", "2026-08-26"], // "the NPRM published at 91 FR 38593 on June 26, 2026, is extended to …"
    ["2026-17132", "2026-09-21"], // "The August 21, 2026, due date for comments … is extended."
  ] as const)
    assert(
      `#2 real ${doc}: the citation / replaced date is excluded BY CONTEXT; the close ${close} is the only reading`,
      read(extractDatesSection(page(doc))!) ===
        JSON.stringify({ candidates: [close], others: [] }),
      read(extractDatesSection(page(doc))!),
    );
  for (const [label, text] of [
    [
      "a second deadline EQUAL to the close being extended",
      "Comments submitted by mail are extended to November 2, 2026. Electronic submissions must still reach the agency by October 16, 2026.",
    ],
    [
      "a second deadline ON the publication date",
      "Comments submitted by mail are extended to November 2, 2026. Electronic submissions must still reach the agency by October 1, 2026.",
    ],
    [
      "a second deadline BEFORE the publication date, with no past context",
      "Comments are extended to November 2, 2026. Hand-delivered submissions must reach the agency by September 30, 2026.",
    ],
  ] as const)
    assert(
      `#2 ${label} counts → ambiguous`,
      resolveAmendedClose(ORIG, [ev({ govinfo_text: text })]).kind ===
        "ambiguous",
    );
  for (const [label, text] of [
    [
      "(was) scheduled to close on D",
      "The comment period, which was scheduled to close on October 16, 2026, is extended to November 2, 2026.",
    ],
    [
      "extended from D to D2",
      "The comment period is extended from October 16, 2026, to November 2, 2026.",
    ],
    [
      "previously … D",
      "The comment period, previously set to end October 16, 2026, is extended. Comments must be received on or before November 2, 2026.",
    ],
    [
      "originally scheduled to end D (the keyword directly governs the date)",
      "The comment period originally scheduled to end October 16, 2026, is extended. Comments must be received on or before November 2, 2026.",
    ],
    [
      "would have closed on D",
      "The comment period, which would have closed on October 16, 2026, is extended to November 2, 2026.",
    ],
    [
      "Dated: D (signature line)",
      "Comments must be received on or before November 2, 2026. Dated: September 30, 2026.",
    ],
  ] as const)
    assert(
      `#2 past / citation context excludes its date: ${label}`,
      (() => {
        const o = resolveAmendedClose(ORIG, [ev({ govinfo_text: text })]);
        return o.kind === "amended" && o.date === "2026-11-02";
      })(),
    );
  assert(
    "#2 'originally' never reaches across another date to swallow the live close",
    read(
      "The comment period for the document originally published on September 11, 2026, is extended from October 13, 2026, to November 2, 2026.",
    ) === JSON.stringify({ candidates: ["2026-11-02"], others: [] }),
  );
}

// ── #3 — the closed-world correction allowlist ──────────────────────────────────────────────────────
{
  const irs = extractCorrectionBody(page("C1-2026-18574"))!;
  const ofc = extractCorrectionBody(page("C1-2026-19812"))!;
  const two = extractCorrectionBody(page("C1-2026-16331"))!;
  assert(
    "#3 real IRS C1-2026-18574 sentence: no qualifiers → binds (Oct 16 → Oct 26)",
    (() => {
      const o = resolveAmendedClose(ORIG, [
        ev({
          is_extension: false,
          is_correction: true,
          govinfo_text: irs,
        }),
      ]);
      return o.kind === "amended" && o.date === "2026-10-26";
    })(),
  );
  assert(
    "#3 real C1-2026-19812 (DATES, 'fourth and fifth [[Page 64409]] line'): binds Dec 28 → Nov 30",
    (() => {
      const o = resolveAmendedClose({ ...ORIG, fr_close: "2026-12-28" }, [
        ev({ is_extension: false, is_correction: true, govinfo_text: ofc }),
      ]);
      return o.kind === "amended" && o.date === "2026-11-30";
    })(),
  );
  assert(
    "#3 real C1-2026-16331 (date pairs outside DATES): binds nothing",
    resolveAmendedClose({ ...ORIG, fr_close: "2026-08-18" }, [
      ev({ is_extension: false, is_correction: true, govinfo_text: two }),
    ]).kind === "none",
  );
  for (const q of [
    "the date for public symposium,",
    "the date for oral presentations,",
    "the date for public inspection,",
    "the deadline for petitions for reconsideration,",
    "the public hearing date",
    "the effective date",
    "the date for the webcast",
    "the date of the listening session",
  ])
    assert(
      `#3 a qualifier outside the allowlist ("${q}") means no binding`,
      correctionQualifiers(
        `In the DATES section, ${q} "October 16, 2026" should read "October 26, 2026".`,
      ).length > 0 &&
        resolveAmendedClose(ORIG, [
          ev({
            is_extension: false,
            is_correction: true,
            govinfo_text: `In the DATES section, ${q} "October 16, 2026" should read "October 26, 2026".`,
          }),
        ]).kind !== "amended",
    );
  for (const ok of [
    "In the DATES section, the comment deadline",
    "On page 1000, in the second column, in the third line of the DATES section, the date by which comments must be received,",
    "Under DATES, in the last line,",
  ])
    assert(
      `#3 explicit comment-period / location vocabulary binds: "${ok}"`,
      correctionQualifiers(
        `${ok} "October 16, 2026" should read "October 26, 2026".`,
      ).length === 0,
      JSON.stringify(
        correctionQualifiers(
          `${ok} "October 16, 2026" should read "October 26, 2026".`,
        ),
      ),
    );
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
