/**
 * amendment-round2.test.ts — the five round-2 adversarial-review findings (ADR 0016 §4, §7), PURE.
 * The reviewer's own cases live in adversary-r2-parser.test.ts and adversary-r2-history.test.ts (DB);
 * this file pins each fix from more angles.
 *
 *   #1 the verdict's freshness is judged on the amendment HISTORY (inputs.timeline): the state at the
 *      verdict must hold through every later state — a reversion never revives, a same-effect
 *      re-fetch never invalidates, a document linked or unlinked later is a change
 *   #2 a correction whose own sentence names a non-comment role binds nothing
 *   #3 a date in a sentence with no established role still counts against the candidate
 *   #4 a later date-bearing extension with a competing date but no candidate poisons the chain
 *   #5 the FR cross-check runs before a restatement is accepted
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/amendment-round2.test.ts
 */
import {
  amendmentChangedSince,
  commentDeadlines,
  resolveAmendedClose,
  type AmendmentEvidence,
  type AmendmentInputs,
} from "../src/reconcile/amendment.js";

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
function ev(over: Partial<AmendmentEvidence> = {}): AmendmentEvidence {
  seq++;
  return {
    ocd_id: `ocd-participation-window/federal/2026-3${String(seq).padStart(4, "0")}`,
    fr_document_number: `2026-3${String(seq).padStart(4, "0")}`,
    fr_observation_id: `00000000-0000-4000-8000-0000000030${String(seq).padStart(2, "0")}`,
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
}
const kind = (o: ReturnType<typeof resolveAmendedClose>) =>
  o.kind === "amended" ? o.date : o.kind;

// ── #1 — the timeline rule ──────────────────────────────────────────────────────────────────────────
{
  const ext = ev();
  const sameAgain = { ...ext, fr_observation_id: "refetch-same" };
  const removed: AmendmentEvidence[] = []; // the re-fetched row no longer identifies an amendment
  const tl = (states: [string, AmendmentEvidence[]][]): AmendmentInputs => ({
    original: ORIG,
    amendments: states.at(-1)![1],
    timeline: states.map(([at, amendments]) => ({ at, amendments })),
  });
  const VERDICT = Date.parse("2026-10-10T00:00:00Z");
  assert(
    "#1 a same-effect re-fetch after the verdict never invalidates it",
    !amendmentChangedSince(
      VERDICT,
      undefined,
      tl([
        ["2026-10-03T00:00:00Z", [ext]],
        ["2026-10-20T00:00:00Z", [sameAgain]],
      ]),
    ),
  );
  assert(
    "#1 a later row that removes the amendment supersedes the verdict",
    amendmentChangedSince(
      VERDICT,
      undefined,
      tl([
        ["2026-10-03T00:00:00Z", [ext]],
        ["2026-10-20T00:00:00Z", removed],
      ]),
    ),
  );
  assert(
    "#1 a material change followed by a reversion never revives the verdict",
    amendmentChangedSince(
      VERDICT,
      undefined,
      tl([
        ["2026-10-03T00:00:00Z", [ext]],
        ["2026-10-20T00:00:00Z", removed],
        ["2026-10-25T00:00:00Z", [sameAgain]],
      ]),
    ),
  );
  assert(
    "#1 a document that becomes LINKED only after the verdict is a change",
    amendmentChangedSince(
      VERDICT,
      undefined,
      tl([
        ["2026-10-03T00:00:00Z", []],
        ["2026-10-20T00:00:00Z", [ext]],
      ]),
    ),
  );
  assert(
    "#1 changes that settled BEFORE the verdict are the verdict's own baseline (honored)",
    !amendmentChangedSince(
      VERDICT,
      undefined,
      tl([
        ["2026-10-01T00:00:00Z", []],
        ["2026-10-03T00:00:00Z", [ext]],
      ]),
    ),
  );
  assert(
    "#1 tie policy: a row fetched exactly AT the verdict is not newer",
    !amendmentChangedSince(
      VERDICT,
      undefined,
      tl([["2026-10-10T00:00:00Z", [ext]]]), // a state AT the verdict is its baseline
    ),
  );
  assert(
    "#1 a different amended date later is a change (extension superseded by a further one)",
    amendmentChangedSince(
      VERDICT,
      undefined,
      tl([
        ["2026-10-03T00:00:00Z", [ext]],
        [
          "2026-10-20T00:00:00Z",
          [
            ext,
            ev({
              publication_date: "2026-10-18",
              govinfo_text:
                "Comments must be received on or before November 20, 2026.",
            }),
          ],
        ],
      ]),
    ),
  );
}

// ── #2 — correction roles ───────────────────────────────────────────────────────────────────────────
{
  const cor = (sentence: string) =>
    resolveAmendedClose(ORIG, [
      ev({ is_extension: false, is_correction: true, govinfo_text: sentence }),
    ]).kind;
  for (const role of [
    "the public hearing date",
    "the meeting date",
    "the registration deadline",
    "the deadline for requests to speak",
    "the effective date",
    "the information collection comment date",
  ])
    assert(
      `#2 a DATES correction of ${role} never moves the comment close`,
      cor(
        `In the DATES section, ${role} "October 16, 2026" should read "October 26, 2026".`,
      ) !== "amended",
    );
  assert(
    "#2 a DATES correction with no other role still binds",
    cor(
      'In the DATES section, "October 16, 2026" should read "October 26, 2026".',
    ) === "amended",
  );
}

// ── #3 — a date with no established role counts ─────────────────────────────────────────────────────
{
  const r = commentDeadlines(
    "Comments must be received on or before November 2, 2026. Therefore, they should be submitted to the Service by December 7, 2026.",
  );
  assert(
    "#3 an anaphoric sentence's date is a competing comment date",
    JSON.stringify(r.candidates) === '["2026-11-02"]' &&
      JSON.stringify(r.others) === '["2026-12-07"]',
    JSON.stringify(r),
  );
  const ok = commentDeadlines(
    "This rule is effective on December 1, 2026. Comments must be received on or before November 2, 2026. A public hearing will be held on November 18, 2026.",
  );
  assert(
    "#3 explicitly effective-date / hearing sentences stay excluded",
    JSON.stringify(ok.candidates) === '["2026-11-02"]' &&
      ok.others.length === 0,
    JSON.stringify(ok),
  );
}

// ── #4 — a later unparsed extension poisons the chain ───────────────────────────────────────────────
{
  const first = ev();
  const later = ev({
    publication_date: "2026-10-20",
    govinfo_text: "Comments should reach the agency by November 20, 2026.",
  });
  assert(
    "#4 a later extension with a competing comment date but no candidate → ambiguous",
    kind(resolveAmendedClose(ORIG, [first, later])) === "ambiguous",
  );
  assert(
    "#4 a later linked amendment with NO date at all leaves the chain (none)",
    kind(
      resolveAmendedClose(ORIG, [
        first,
        ev({
          publication_date: "2026-10-20",
          govinfo_text: "The docket number is corrected.",
        }),
      ]),
    ) === "2026-11-02",
  );
}

// ── #5 — cross-check before a restatement ───────────────────────────────────────────────────────────
{
  const first = ev();
  const restate = ev({
    publication_date: "2026-10-20",
    fr_comments_close_on: "2026-11-20",
  });
  assert(
    "#5 a restatement contradicted by its own plausible FR close → ambiguous",
    kind(resolveAmendedClose(ORIG, [first, restate])) === "ambiguous",
  );
  assert(
    "#5 a restatement whose FR close agrees still confirms",
    kind(
      resolveAmendedClose(ORIG, [
        first,
        { ...restate, fr_comments_close_on: "2026-11-02" },
      ]),
    ) === "2026-11-02",
  );
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
