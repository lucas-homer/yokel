/**
 * amendment-round1.test.ts — the six round-1 adversarial-review findings on the amended FR close
 * (ADR 0016 §2–§7), PURE (no DB). The reviewer's own failing cases live in
 * adversary-amendment-safety.test.ts; this file pins each fix from more angles, on real GovInfo pages
 * where they exist (test/fixtures/fr-amendments/govinfo).
 *
 *   #1 a linked amendment newer than A's verdict is new evidence for A (selectHonoredVerdict, §7)
 *   #2 hearing / meeting / request-to-speak dates are never comment closes; "on or by" is a deadline
 *   #3 a second comment date in a comment sentence — recognized phrase or not — makes it ambiguous
 *   #4 a correction binds only when ITS sentence places it in the DATES section
 *   #5 successive extensions chain against the close in force
 * (#6, the stalled-body timeout, is in govinfo.test.ts — it needs an HTTP server.)
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/amendment-round1.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import {
  amendmentChangedSince,
  amendmentsAsOf,
  commentDeadlines,
  resolveAmendedClose,
  type AmendmentEvidence,
  type AmendmentInputs,
} from "../src/reconcile/amendment.js";
import { reconcile, selectHonoredVerdict } from "../src/reconcile/reconcile.js";
import {
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

const FIX = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "fr-amendments",
);
const datesOf = (doc: string) =>
  extractDatesSection(
    govinfoPlainText(readFileSync(join(FIX, "govinfo", `${doc}.htm`), "utf8")),
  )!;

const ORIG = {
  fr_close: "2026-10-16",
  publication_date: "2026-09-01",
  fr_document_number: "2026-10000",
};
let seq = 0;
function ev(over: Partial<AmendmentEvidence> = {}): AmendmentEvidence {
  seq++;
  return {
    ocd_id: `ocd-participation-window/federal/2026-2${String(seq).padStart(4, "0")}`,
    fr_document_number: `2026-2${String(seq).padStart(4, "0")}`,
    fr_observation_id: `00000000-0000-4000-8000-0000000010${String(seq).padStart(2, "0")}`,
    govinfo_observation_id: `00000000-0000-4000-8000-0000000020${String(seq).padStart(2, "0")}`,
    publication_date: "2026-10-01",
    is_extension: true,
    is_correction: false,
    is_reopening: false,
    is_withdrawal: false,
    fr_comments_close_on: null,
    fr_dates_text: null,
    govinfo_text: "Comments must be received on or before November 2, 2026.",
    basis: "docket_rin",
    fr_fetched_at: "2026-10-01T08:00:00.000Z",
    govinfo_fetched_at: "2026-10-01T09:00:00.000Z",
    ...over,
  };
}
const date = (o: ReturnType<typeof resolveAmendedClose>) =>
  o.kind === "amended" ? o.date : o.kind;

// ── #2 — hearing / meeting dates are never comment closes ──────────────────────────────────────────
{
  const epa = datesOf("2026-20982");
  const r = commentDeadlines(epa);
  assert(
    "#2 real EPA 2026-20982: the 'on or by November 30' comment deadline is the ONLY candidate; the Oct 19 hearing-request cutoff and the Oct 14 effective date are not",
    JSON.stringify(r.candidates) === '["2026-11-30"]' && r.others.length === 0,
    JSON.stringify(r),
  );
  assert(
    "#2 hearing range: 'Public hearings will run November 18 through November 20' never supplies a close",
    date(
      resolveAmendedClose(ORIG, [
        ev({
          govinfo_text:
            "Comments must be received on or before November 2, 2026. Public hearings will run November 18 through November 20, 2026.",
        }),
      ]),
    ) === "2026-11-02",
  );
  assert(
    "#2 a comment + hearing clause pair in one sentence splits at ';'",
    date(
      resolveAmendedClose(ORIG, [
        ev({
          govinfo_text:
            "Comments must be received on or before November 2, 2026; a public hearing will be held November 18 through November 20, 2026.",
        }),
      ]),
    ) === "2026-11-02",
  );
  assert(
    "#2 an UNRESOLVED role (comments AND requests to speak, one clause) supplies no close (round 2 #4: a competing date without a candidate → ambiguous, never amended)",
    resolveAmendedClose(ORIG, [
      ev({
        govinfo_text:
          "Comments and requests to speak at the hearing must be received on or before November 2, 2026.",
      }),
    ]).kind === "ambiguous",
  );
  assert(
    "#2 a meeting-only DATES text supplies nothing → none",
    resolveAmendedClose(ORIG, [
      ev({
        govinfo_text:
          "The committee will meet on November 5, 2026, from 9 a.m. to 3 p.m. Registration closes on November 1, 2026.",
      }),
    ]).kind === "none",
  );
  assert(
    "#2 'on or by' is a deadline phrase",
    date(
      resolveAmendedClose(ORIG, [
        ev({
          govinfo_text:
            "Comments on this rule must be received on or by November 30, 2026.",
        }),
      ]),
    ) === "2026-11-30",
  );
}

// ── #3 — a second comment deadline can never vanish ────────────────────────────────────────────────
{
  const interior = datesOf("2026-14450");
  const r = commentDeadlines(interior);
  assert(
    "#3 real Interior 2026-14450: Aug 17 written comments is the candidate AND Sep 15 information-collection comments is caught by the guard",
    JSON.stringify(r.candidates) === '["2026-08-17"]' &&
      JSON.stringify(r.others) === '["2026-09-15"]',
    JSON.stringify(r),
  );
  assert(
    "#3 … so an extension reading that text is ambiguous, never Aug 17",
    resolveAmendedClose(
      { ...ORIG, fr_close: "2026-08-01", publication_date: "2026-06-01" },
      [ev({ publication_date: "2026-07-17", govinfo_text: interior })],
    ).kind === "ambiguous",
  );
  assert(
    "#3 restating the close being extended is not a second deadline",
    date(
      resolveAmendedClose(ORIG, [
        ev({
          govinfo_text:
            "The comment period, which was scheduled to close on October 16, 2026, is extended to November 2, 2026.",
        }),
      ]),
    ) === "2026-11-02",
  );
  assert(
    "#3 a citation of the published document is not a second deadline",
    date(
      resolveAmendedClose(ORIG, [
        ev({
          govinfo_text:
            "The comment period for the proposed rule published in the Federal Register on September 1, 2026, is extended. Comments must be received on or before November 2, 2026.",
        }),
      ]),
    ) === "2026-11-02",
  );
  assert(
    "#3 an unrecognized-phrase comment date after the candidate → ambiguous",
    resolveAmendedClose(ORIG, [
      ev({
        govinfo_text:
          "Comments must be received on or before November 2, 2026. Comments on the collection should reach OMB by December 7, 2026.",
      }),
    ]).kind === "ambiguous",
  );
}

// ── #4 — a correction binds only in the DATES section ──────────────────────────────────────────────
{
  const cor = (text: string) =>
    resolveAmendedClose(ORIG, [
      ev({ is_extension: false, is_correction: true, govinfo_text: text }),
    ]);
  assert(
    "#4 the reviewer's case: DATES mentioned in instruction 1, an effective date corrected in SUPPLEMENTARY INFORMATION → none",
    cor(
      'In document 2026-10000 beginning on page 10000: 1. In the DATES section, "contact" should read "comments". 2. In the SUPPLEMENTARY INFORMATION section, the effective date "October 16, 2026" should read "November 20, 2026".',
    ).kind === "none",
  );
  assert(
    "#4 an instruction naming DATES AND another section is not bound",
    cor(
      'In the DATES section and in the SUMMARY, "October 16, 2026" should read "October 26, 2026".',
    ).kind === "none",
  );
  assert(
    "#4 an effective-date correction placed in DATES is not a comment close",
    cor(
      'In the DATES section, the effective date "October 16, 2026" should read "October 26, 2026".',
    ).kind === "none",
  );
  assert(
    "#4 the real GPO shape still binds (C1-2026-18574)",
    date(
      cor(
        "In proposed rule document 2026-10000 beginning on page 57968 in the issue of Friday, September 11, 2026, make the following correction: On page 57968, in the first column, in the second line of the DATES section, ``October 16, 2026'' should read ``October 26, 2026''.",
      ),
    ) === "2026-10-26",
  );
}

// ── #5 — successive extensions chain against the close in force ────────────────────────────────────
{
  const first = ev({ publication_date: "2026-10-05" });
  const second = ev({
    publication_date: "2026-10-20",
    govinfo_text: "Comments must be received on or before November 20, 2026.",
  });
  const o = resolveAmendedClose(ORIG, [second, first]);
  assert(
    "#5 Oct 16 → Nov 2 (published Oct 5) → Nov 20 (published Oct 20, before Nov 2): Nov 20, both in provenance",
    o.kind === "amended" &&
      o.date === "2026-11-20" &&
      o.amendment.fr_document_number === second.fr_document_number &&
      o.observation_ids.includes(first.fr_observation_id) &&
      o.observation_ids.includes(second.fr_observation_id),
    JSON.stringify(o),
  );
  assert(
    "#5 a gap — the second published after the extended close — stays ambiguous",
    resolveAmendedClose(ORIG, [
      first,
      { ...second, publication_date: "2026-11-05" },
    ]).kind === "ambiguous",
  );
  assert(
    "#5 a contradiction — the second moves the close earlier — stays ambiguous",
    resolveAmendedClose(ORIG, [
      first,
      {
        ...second,
        govinfo_text:
          "Comments must be received on or before October 30, 2026.",
      },
    ]).kind === "ambiguous",
  );
  assert(
    "#5 a correction of the EXTENDED close chains too (X = the close in force)",
    date(
      resolveAmendedClose(ORIG, [
        first,
        ev({
          publication_date: "2026-10-10",
          is_extension: false,
          is_correction: true,
          govinfo_text:
            'In the DATES section, "November 2, 2026" should read "November 3, 2026".',
        }),
      ]),
    ) === "2026-11-03",
  );
}

// ── #1 — a linked amendment newer than A's verdict is new evidence for A ───────────────────────────
{
  const stored = JSON.parse(
    readFileSync(join(FIX, "stored", "observations.json"), "utf8"),
  ) as Observation[];
  const census = stored.filter(
    (o) => o.ocd_id === "ocd-participation-window/federal/2026-18481",
  );
  const fr = census.find((o) => o.source === "federal_register")!;
  const regsBefore = census.filter(
    (o) => o.source === "regulations_gov" && o.fetched_at < "2026-10-01",
  );
  const baseline = regsBefore.at(-1)!;
  const pinAt = (fetched_at: string): Observation => ({
    ...fr,
    observation_id: `ffffffff-0000-4000-8000-${fetched_at.replace(/\D/g, "").slice(0, 12)}`,
    source: "human_review",
    fetched_at,
    raw: {
      kind: "pin_close",
      pinned_close_date: "2026-10-13",
      note: "reviewed the original notice",
      operator: "test",
      reviewed_payload_hashes: [fr.payload_hash, baseline.payload_hash],
    },
  });
  const ORIGINAL = {
    fr_close: "2026-10-13",
    publication_date: "2026-09-10",
    fr_document_number: "2026-18481",
  };
  const ext = (over: Partial<AmendmentEvidence> = {}) =>
    ev({
      publication_date: "2026-10-05",
      fr_comments_close_on: "2026-11-02",
      fr_dates_text: "Submit comments on or before November 2, 2026.",
      govinfo_text: "Submit comments on or before November 2, 2026.",
      fr_fetched_at: "2026-10-03T07:48:00.000Z",
      govinfo_fetched_at: "2026-10-27T06:00:00.000Z",
      ...over,
    });
  const inputs = (a: AmendmentEvidence[]): AmendmentInputs => ({
    original: ORIGINAL,
    amendments: a,
  });
  const honoredWith = (pin: Observation, a: AmendmentEvidence[]) =>
    selectHonoredVerdict([fr, ...regsBefore, pin], {
      amendmentInputs: inputs(a),
    });

  const early = pinAt("2026-10-01T00:00:00.000Z");
  assert(
    "#1 a pin written BEFORE the extension was fetched is superseded by it",
    honoredWith(early, [ext()]) === null,
  );
  const derived = reconcile(
    [fr, ...regsBefore, early],
    new Date("2026-10-27T00:00:00Z"),
    {
      amendmentInputs: inputs([ext()]),
    },
  );
  assert(
    "#1 … the window returns to machine derivation with the amended close (no human_resolved)",
    !derived.window.conflict_flags.includes("human_resolved") &&
      derived.window.conflict_flags.includes("fr_close_amended"),
    JSON.stringify(derived.window.conflict_flags),
  );
  const late = pinAt("2026-10-04T00:00:00.000Z");
  assert(
    "#1 a pin written AFTER the extension's FR row stays honored when only its GovInfo copy is newer (same date)",
    honoredWith(late, [ext()]) !== null,
  );
  assert(
    "#1 … but if the FR row alone gave no date and the newer GovInfo text supplies one, that IS new evidence",
    honoredWith(late, [
      ext({
        fr_dates_text:
          "The comment period for the document originally published on September 10, 2026,",
        fr_comments_close_on: "2026-09-10",
      }),
    ]) === null,
  );
  assert(
    "#1 a reopening linked AFTER the pin un-amends the window → new evidence",
    honoredWith(late, [
      ext(),
      ev({
        publication_date: "2026-10-06",
        is_extension: false,
        is_reopening: true,
        fr_fetched_at: "2026-10-06T08:00:00.000Z",
      }),
    ]) === null,
  );
  assert(
    "#1 an amendment with an UNKNOWN fetch time counts as newer (conservative)",
    honoredWith(late, [ext({ fr_fetched_at: undefined })]) === null,
  );
  assert(
    "#1 no linked amendment → the v2.3/v2.4 rule decides alone (honored)",
    honoredWith(early, []) !== null,
  );
  const a0 = [ext()];
  assert(
    "#1 amendmentsAsOf drops rows fetched after the cutoff and govinfo text not yet fetched",
    amendmentsAsOf(a0, Date.parse("2026-10-02T00:00:00Z")).length === 0 &&
      amendmentsAsOf(a0, Date.parse("2026-10-04T00:00:00Z"))[0]!
        .govinfo_text === null,
  );
  assert(
    "#1 amendmentChangedSince without inputs: an amended outcome fetched after the cutoff is new",
    amendmentChangedSince(
      Date.parse("2026-10-01T00:00:00Z"),
      resolveAmendedClose(ORIGINAL, a0),
      undefined,
    ) &&
      !amendmentChangedSince(
        Date.parse("2026-10-28T00:00:00Z"),
        resolveAmendedClose(ORIGINAL, a0),
        undefined,
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
