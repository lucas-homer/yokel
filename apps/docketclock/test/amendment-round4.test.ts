/**
 * amendment-round4.test.ts — round-4 review (ADR 0016 §4, §8), PURE. The reviewer's own cases live in
 * adversary-r4-parser.test.ts; the DB proof of the backstop is amendment-backstop.test.ts.
 *
 *   #1 only explicit HISTORICAL grammar excludes a date; loose keywords nearby do not
 *   #2 only the should-read operands are removed before the allowlist; every other quoted text is read
 *   #3 a digit passes the allowlist only inside a strict structural form
 *   #4 the §8 backstop: an amended date moves the FR side only when the portal close or the final
 *      amendment's own plausible FR comments_close_on corroborates it — else ambiguous, window unchanged
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/amendment-round4.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import type { Observation } from "@yokel/contracts";
import {
  commentDeadlines,
  corroborateAmendedClose,
  correctionQualifiers,
  resolveAmendedClose,
  type AmendmentEvidence,
  type AmendmentOutcome,
} from "../src/reconcile/amendment.js";
import { reconcile } from "../src/reconcile/reconcile.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const ORIG = {
  fr_close: "2026-10-16",
  publication_date: "2026-09-01",
  fr_document_number: "2026-10000",
};
let seq = 0;
const ev = (over: Partial<AmendmentEvidence> = {}): AmendmentEvidence => {
  seq++;
  return {
    ocd_id: `ocd-participation-window/federal/2026-5${String(seq).padStart(4, "0")}`,
    fr_document_number: `2026-5${String(seq).padStart(4, "0")}`,
    fr_observation_id: `00000000-0000-4000-8000-0000000050${String(seq).padStart(2, "0")}`,
    govinfo_observation_id: null,
    publication_date: "2026-10-01",
    is_extension: true,
    is_correction: false,
    is_reopening: false,
    is_withdrawal: false,
    fr_comments_close_on: null,
    fr_dates_text: null,
    govinfo_text: "Comments must be received on or before November 2, 2026.",
    basis: "docket_rin",
    ...over,
  };
};
const reading = (t: string) => JSON.stringify(commentDeadlines(t));

// ── #1 — explicit historical grammar only ───────────────────────────────────────────────────────────
{
  const LIVE = "Comments submitted by mail are extended to November 2, 2026.";
  for (const live of [
    "The electronic comment docket will be closed on October 16, 2026.",
    "The electronic comment docket shall be closed on October 16, 2026.",
    "Previously submitted comments must be resubmitted by October 16, 2026.",
    "As originally announced, electronic comments remain due October 16, 2026.",
    "Electronic comments must be dated October 16, 2026.",
    "Electronic comments remain due (October 16, 2026).",
  ])
    assert(
      `#1 live: "${live.slice(0, 60)}…" counts → ambiguous`,
      resolveAmendedClose(ORIG, [ev({ govinfo_text: `${LIVE} ${live}` })])
        .kind === "ambiguous",
    );
  for (const past of [
    "The comment period originally scheduled to close on October 16, 2026, is extended.",
    "The comment period previously set to end October 16, 2026, is extended.",
    "The comment period, which was scheduled to close on October 16, 2026, is extended.",
    "The comment period, which would have closed on October 16, 2026, is extended.",
    "The original comment period closed on October 16, 2026.",
    "The comment period is extended from October 16, 2026.",
    "The notice published on September 1, 2026, dated August 30, 2026, is amended.",
    "Dated: September 30, 2026.",
  ])
    assert(
      `#1 historical: "${past.slice(0, 60)}…" is excluded`,
      reading(`${LIVE} ${past}`) ===
        JSON.stringify({ candidates: ["2026-11-02"], others: [] }),
      reading(`${LIVE} ${past}`),
    );
}

// ── #2 / #3 — the correction allowlist ──────────────────────────────────────────────────────────────
{
  const q = (s: string) =>
    correctionQualifiers(
      `In the DATES section, ${s} "October 16, 2026" should read "October 26, 2026".`,
    );
  assert(
    '#2 a quoted role ("public hearing") is read like any word',
    q('for the "public hearing",').includes("public"),
  );
  assert(
    "#2 the should-read operands themselves are removed (no qualifier from the dates)",
    q("").length === 0,
  );
  for (const tok of ["PM2.5", "PM2-5", "Form-1", "Item 7a", "the 2026 rule"])
    assert(
      `#3 a free digit token ("${tok}") is a qualifier`,
      q(`the date for ${tok},`).length > 0,
    );
  for (const loc of [
    "On page 57968, in the first column, in the second line of the",
    "On page 61466, in the fourth and fifth [[Page 64409]] line of the",
    "On pages 100 and 101, in the 24th line from the bottom, in paragraph (b) of the",
    "In column 2, line 7 of the",
  ])
    assert(
      `#3 structural numbers bind: "${loc.slice(0, 50)}…"`,
      correctionQualifiers(
        `${loc} DATES section, "October 16, 2026" should read "October 26, 2026".`,
      ).length === 0,
      JSON.stringify(
        correctionQualifiers(
          `${loc} DATES section, "October 16, 2026" should read "October 26, 2026".`,
        ),
      ),
    );
}

// ── #4 — the §8 backstop ────────────────────────────────────────────────────────────────────────────
{
  const amended = resolveAmendedClose(ORIG, [ev()]);
  assert("setup: the resolver reads Nov 2", amended.kind === "amended");
  assert(
    "§8 (a) the portal close corroborates → kept",
    corroborateAmendedClose(amended, "2026-11-02")?.kind === "amended",
  );
  assert(
    "§8 (b) the amendment's own plausible FR comments_close_on corroborates → kept",
    corroborateAmendedClose(
      resolveAmendedClose(ORIG, [ev({ fr_comments_close_on: "2026-11-02" })]),
      null,
    )?.kind === "amended",
  );
  const lone = corroborateAmendedClose(amended, "2026-10-17");
  assert(
    "§8 neither → ambiguous, the reason recorded",
    lone?.kind === "ambiguous" &&
      lone.reasons.some((r) => r.startsWith("uncorroborated: 2026-11-02")),
    JSON.stringify(lone),
  );
  assert(
    "§8 an IMPLAUSIBLE FR close (on/before publication, USDA's 09-11 pattern) never corroborates",
    corroborateAmendedClose(
      resolveAmendedClose(ORIG, [
        ev({
          fr_comments_close_on: "2026-09-11",
          govinfo_text:
            "Comments must be received on or before September 11, 2026.",
        }),
      ]),
      null,
    )?.kind !== "amended",
  );
  // Chain: an intermediate step needs no corroboration; the FINAL date does, and only from the amendment
  // that set it.
  const chain = resolveAmendedClose(ORIG, [
    ev({ publication_date: "2026-10-05" }),
    ev({
      publication_date: "2026-10-20",
      govinfo_text: "Comments must be received on or before November 20, 2026.",
      fr_comments_close_on: "2026-11-20",
    }),
  ]);
  assert(
    "§8 chain: the final Nov 20 is corroborated by the final amendment's FR close; the intermediate Nov 2 needed none",
    corroborateAmendedClose(chain, null)?.kind === "amended",
  );
  assert(
    "§8 chain: an earlier amendment's FR close does not corroborate the final date",
    corroborateAmendedClose(
      resolveAmendedClose(ORIG, [
        ev({
          publication_date: "2026-10-05",
          fr_comments_close_on: "2026-11-20",
        }),
        ev({
          publication_date: "2026-10-20",
          govinfo_text:
            "Comments must be received on or before November 20, 2026.",
        }),
      ]),
      null,
    )?.kind !== "amended",
  );
  assert(
    "§8 none / ambiguous pass through untouched",
    corroborateAmendedClose({ kind: "none" }, null)?.kind === "none",
  );

  // In the engine: a wrong-but-plausible parse with no corroboration leaves the window byte-identical.
  const FIX = join(
    dirname(fileURLToPath(import.meta.url)),
    "fixtures",
    "fr-amendments",
    "stored",
    "observations.json",
  );
  const census = (
    JSON.parse(readFileSync(FIX, "utf8")) as Observation[]
  ).filter((o) => o.ocd_id === "ocd-participation-window/federal/2026-18481");
  const NOW = new Date("2026-10-27T12:00:00Z");
  const wrongParse: AmendmentOutcome = resolveAmendedClose(
    {
      fr_close: "2026-10-13",
      publication_date: "2026-09-10",
      fr_document_number: "2026-18481",
    },
    [
      ev({
        publication_date: "2026-10-05",
        govinfo_text:
          "Comments must be received on or before November 9, 2026.",
        fr_comments_close_on: null, // text-only: no FR value to corroborate (portal says Nov 2)
      }),
    ],
  );
  assert(
    "§8 engine: the resolver reads the wrong Nov 9, yet the window is BYTE-IDENTICAL to no amendment",
    wrongParse.kind === "amended" &&
      isDeepStrictEqual(
        reconcile(census, NOW, { amendment: wrongParse }),
        reconcile(census, NOW),
      ),
  );
  const fronly = census.filter((o) => o.source === "federal_register");
  const epaLike = resolveAmendedClose(
    {
      fr_close: "2026-10-13",
      publication_date: "2026-09-10",
      fr_document_number: "2026-18481",
    },
    [
      ev({
        publication_date: "2026-10-05",
        fr_comments_close_on: "2026-11-02",
      }),
    ],
  );
  assert(
    "§8 engine, FR-only window (the EPA 2026-05167 shape): moves only when B's FR close corroborates",
    reconcile(fronly, NOW, { amendment: epaLike }).window.raw_fr_close_date ===
      "2026-10-13" &&
      reconcile(fronly, NOW, {
        amendment: epaLike,
      }).window.conflict_flags.includes("fr_close_amended") &&
      isDeepStrictEqual(
        reconcile(fronly, NOW, {
          amendment: resolveAmendedClose(
            {
              fr_close: "2026-10-13",
              publication_date: "2026-09-10",
              fr_document_number: "2026-18481",
            },
            [ev({ publication_date: "2026-10-05" })],
          ),
        }),
        reconcile(fronly, NOW),
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
