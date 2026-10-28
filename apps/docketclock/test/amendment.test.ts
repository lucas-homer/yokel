/**
 * amendment.test.ts — the amended FR close (ADR 0016; docs/plans/fr-amendment-linking.md parts 4–5).
 * PURE (no DB): the recorded production observations (test/fixtures/fr-amendments/stored) and GovInfo
 * pages (…/govinfo, parsed by the real adapter) driven through the loader's pure half
 * (amendmentOutcomeFromRows — the exact selection logic loadAmendmentEvidence runs after its SQL
 * prefilter), resolveAmendedClose, and reconcile(…, { amendment }).
 *
 * The REQUIRED OUTCOMES (spec "Required outcomes"):
 *   • Census 18481 + 20328 → FR side 2026-11-02, HIGH + tz_normalization_only + fr_close_amended;
 *   • USDA 18531 + 19710 + govinfo → basis citation, 2026-11-02 from the published DATES, B's own
 *     2026-09-11 ignored, HIGH; WITHOUT the govinfo text → none, window unchanged;
 *   • IRS 18574 + C1 + govinfo → basis correction_of, Oct 16 → Oct 26, HIGH;
 *   • PHMSA (+ synthetic 19351 as extension / reopening), USCG 19895, ICE 20660 (+ synthetic rule+PRA
 *     extension → ambiguous), EPA 18134 → byte-identical windows;
 *   • every other recorded window: byte-identical to reconcile-v2.3's derivation.
 * Plus each resolver predicate on its own, and the engine integration details (raw_fr_close_date,
 * provenance ids, FR-driven display, CONFLICTING with the amended value, honored-verdict overlay).
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/amendment.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import type { Observation } from "@yokel/contracts";
import {
  deadlineDates,
  parseLongDate,
  resolveAmendedClose,
  shouldReadPairs,
  type AmendmentEvidence,
  type AmendmentOutcome,
} from "../src/reconcile/amendment.js";
import { buildCitationIndex } from "../src/reconcile/chain.js";
import { extractFr } from "../src/reconcile/extract.js";
import {
  amendmentOutcomeFromRows,
  type FrAmendmentRow,
} from "../src/reconcile/persist.js";
import {
  RECONCILER_VERSION,
  reconcile,
  selectHonoredVerdict,
} from "../src/reconcile/reconcile.js";
import {
  DERIVATION_SOURCES,
  isDerivationSource,
} from "../src/reconcile/review-evidence.js";
import { frNoticeFlags } from "../src/sources/federal-register.js";
import { parseGovinfoObservation } from "../src/sources/govinfo.js";

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
const stored = JSON.parse(
  readFileSync(join(FIX, "stored", "observations.json"), "utf8"),
) as Observation[];
const api = (doc: string) =>
  JSON.parse(
    readFileSync(join(FIX, "fr-api", `${doc}.json`), "utf8"),
  ) as Record<string, unknown>;
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;
const NOW = new Date("2026-10-27T12:00:00Z");

const observationsOf = (doc: string) =>
  stored.filter((o) => o.ocd_id === ocd(doc));

/** The latest FR observation of a document as a loader row (live FR JSON when never ingested). */
function frRow(doc: string, withGov = false): FrAmendmentRow {
  const frs = observationsOf(doc).filter(
    (o) => o.source === "federal_register",
  );
  const latest = frs.at(-1);
  const raw = latest?.raw ?? api(doc);
  const flags = latest ?? frNoticeFlags(raw);
  let govId: string | null = null;
  let govText: string | null = null;
  if (withGov) {
    const fr = extractFr(raw);
    const g = parseGovinfoObservation({
      frDocNum: doc,
      publicationDate: fr.publicationDate!,
      url: `https://www.govinfo.gov/content/pkg/FR-${fr.publicationDate}/html/${doc}.htm`,
      html: readFileSync(join(FIX, "govinfo", `${doc}.htm`), "utf8"),
      isCorrection:
        flags.is_correction ||
        !!(raw as { correction_of?: string }).correction_of,
    });
    govId = `00000000-0000-4000-8000-${doc.replace(/\D/g, "").padStart(12, "0").slice(-12)}`;
    govText = g.raw_dates_text;
  }
  return {
    observation_id: latest?.observation_id ?? `obs-${doc}`,
    ocd_id: ocd(doc),
    fr_document_number: doc,
    is_extension: flags.is_extension,
    is_correction: flags.is_correction,
    is_withdrawal: flags.is_withdrawal,
    is_reopening: flags.is_reopening,
    raw,
    govinfo_observation_id: govId,
    govinfo_text: govText,
    // Fetch times (ADR 0016 §7 freshness): the recorded FR fetch; the GovInfo sweep's first run.
    fetched_at: latest?.fetched_at ?? null,
    govinfo_fetched_at: withGov ? "2026-10-27T06:00:00.000Z" : null,
  };
}

const STORED_DOCS = [
  ...new Set(
    stored
      .filter((o) => o.source === "federal_register")
      .map((o) => o.fr_document_number!),
  ),
];
const GOV_DOCS = new Set([
  "2026-19351",
  "2026-19710",
  "2026-19895",
  "2026-20328",
  "C1-2026-18574",
]);

/** Every recorded document as a loader row, optionally with its GovInfo text attached. */
function corpus(opts: { gov?: boolean; extra?: FrAmendmentRow[] } = {}) {
  const docs = [...STORED_DOCS, "2026-19351"];
  return [
    ...docs.map((d) => frRow(d, opts.gov === true && GOV_DOCS.has(d))),
    ...(opts.extra ?? []),
  ];
}

function outcomeFor(
  doc: string,
  rows: FrAmendmentRow[] = corpus({ gov: true }),
): AmendmentOutcome {
  const a = rows.find((r) => r.ocd_id === ocd(doc)) ?? frRow(doc);
  const idx = buildCitationIndex(
    rows.map((r) => ({
      citation: extractFr(r.raw).citation,
      fr_document_number: r.fr_document_number,
    })),
  );
  return amendmentOutcomeFromRows(
    a,
    rows.filter((r) => r.ocd_id !== a.ocd_id),
    idx,
  );
}

const derive = (doc: string, amendment?: AmendmentOutcome) =>
  reconcile(observationsOf(doc), NOW, amendment ? { amendment } : {});
const unchanged = (doc: string, o: AmendmentOutcome) =>
  isDeepStrictEqual(derive(doc, o), derive(doc));

assert(
  "RECONCILER_VERSION is reconcile-v2.4",
  RECONCILER_VERSION === "reconcile-v2.4",
);

// ── REQUIRED: Census 2026-18481 + 2026-20328 ────────────────────────────────────────────────────────
{
  const before = derive("2026-18481");
  assert(
    "Census baseline (today): CONFLICTING fr_regs_date_mismatch",
    before.window.confidence === "conflicting",
  );
  const o = outcomeFor("2026-18481", corpus({ gov: false }));
  assert(
    "Census: amended 2026-11-02 by extension 2026-20328, basis docket_rin (no govinfo needed: FR dates + close agree)",
    o.kind === "amended" &&
      o.date === "2026-11-02" &&
      o.change === "extension" &&
      o.amendment.basis === "docket_rin" &&
      o.amendment.fr_document_number === "2026-20328",
    JSON.stringify(o),
  );
  const bFr = observationsOf("2026-20328").find(
    (x) => x.source === "federal_register",
  )!;
  assert(
    "Census: observation_ids = B's FR observation only (its FR text was read)",
    o.kind === "amended" &&
      o.observation_ids.length === 1 &&
      o.observation_ids[0] === bFr.observation_id,
  );
  const w = derive("2026-18481", o).window;
  assert(
    "Census window: HIGH + [tz_normalization_only, fr_close_amended], no conflict",
    w.confidence === "high" &&
      JSON.stringify(w.conflict_flags) ===
        '["tz_normalization_only","fr_close_amended"]' &&
      derive("2026-18481", o).conflict === null,
    JSON.stringify(w.conflict_flags),
  );
  assert(
    "Census window: the Regs instant (Nov 2 ET) is the close; raw_fr_close_date keeps the ORIGINAL FR value",
    w.resolved_close_utc === "2026-11-03T04:59:59.000Z" &&
      w.raw_fr_close_date === "2026-10-13",
    `${w.resolved_close_utc} ${w.raw_fr_close_date}`,
  );
  assert(
    "Census window: provenance names the amendment observation",
    w.current_observation_ids.includes(bFr.observation_id) &&
      w.provenance.agreeing_observation_ids.includes(bFr.observation_id),
  );
  const g = outcomeFor("2026-18481");
  assert(
    "Census with govinfo: the published DATES is read → its observation joins observation_ids",
    g.kind === "amended" &&
      g.date === "2026-11-02" &&
      g.observation_ids.length === 2,
  );
}

// ── REQUIRED: USDA 2026-18531 + 2026-19710 (+ govinfo) ──────────────────────────────────────────────
{
  const o = outcomeFor("2026-18531");
  assert(
    "USDA: amended 2026-11-02, basis citation, from the GovInfo DATES",
    o.kind === "amended" &&
      o.date === "2026-11-02" &&
      o.amendment.basis === "citation" &&
      o.amendment.govinfo_text?.includes("(91 FR 57828)") === true &&
      o.observation_ids.length === 2,
    JSON.stringify(o),
  );
  assert(
    "USDA: B's own comments_close_on 2026-09-11 is ignored as an FR extraction error (recorded in reasons)",
    o.kind === "amended" &&
      o.amendment.fr_comments_close_on === "2026-09-11" &&
      (o.reasons ?? []).some(
        (r) => r.includes("2026-09-11") && r.includes("ignored"),
      ),
    JSON.stringify(o.kind === "amended" ? o.reasons : o),
  );
  const r = derive("2026-18531", o);
  assert(
    "USDA window: HIGH with fr_close_amended (no longer CONFLICTING)",
    r.window.confidence === "high" &&
      r.window.conflict_flags.includes("fr_close_amended") &&
      r.conflict === null &&
      r.window.raw_fr_close_date === "2026-10-13",
    JSON.stringify(r.window.conflict_flags),
  );
  const none = outcomeFor("2026-18531", corpus({ gov: false }));
  assert(
    "USDA WITHOUT the govinfo observation: none (FR dates truncated) and the window is byte-identical",
    none.kind === "none" && unchanged("2026-18531", none),
    JSON.stringify(none),
  );
  assert(
    "USDA without govinfo: still CONFLICTING as today",
    derive("2026-18531", none).window.confidence === "conflicting",
  );
}

// ── REQUIRED: IRS 2026-18574 + C1-2026-18574 (+ govinfo) ────────────────────────────────────────────
{
  const o = outcomeFor("2026-18574");
  assert(
    "IRS: amended Oct 16 → 2026-10-26 by correction C1-2026-18574, basis correction_of",
    o.kind === "amended" &&
      o.date === "2026-10-26" &&
      o.change === "correction" &&
      o.amendment.basis === "correction_of" &&
      o.amendment.is_correction === true,
    JSON.stringify(o),
  );
  const r = derive("2026-18574", o);
  assert(
    "IRS window: HIGH + fr_close_amended; the portal's 2026-10-27T03:59:59Z (Oct 26 ET) is the close",
    r.window.confidence === "high" &&
      r.window.conflict_flags.includes("fr_close_amended") &&
      r.window.resolved_close_utc === "2026-10-27T03:59:59.000Z" &&
      r.window.raw_fr_close_date === "2026-10-16" &&
      r.conflict === null,
    `${r.window.confidence} ${JSON.stringify(r.window.conflict_flags)} ${r.window.resolved_close_utc}`,
  );
  const none = outcomeFor("2026-18574", corpus({ gov: false }));
  assert(
    "IRS WITHOUT the published correction: none — a correction's date is read only from its text",
    none.kind === "none" && unchanged("2026-18574", none),
  );
}

// ── REQUIRED negatives ──────────────────────────────────────────────────────────────────────────────
for (const doc of ["2026-08068", "2026-08077", "2026-10969"]) {
  const o = outcomeFor(doc);
  assert(
    `PHMSA ${doc} with meeting notice 2026-19351: never amended, unchanged`,
    o.kind === "none" && unchanged(doc, o),
    JSON.stringify(o),
  );
}
{
  // Synthetic 19351: flagged extension / reopening, citing the NPRM, on the NPRM's docket (so it LINKS by
  // citation) — the post-lapse guard / reopening rule must still keep the close.
  for (const [label, flags] of [
    ["extension", { is_extension: true, is_reopening: false }],
    ["reopening", { is_extension: false, is_reopening: true }],
  ] as const) {
    const base = frRow("2026-19351");
    const synthetic: FrAmendmentRow = {
      ...base,
      ...flags,
      raw: {
        ...(base.raw as Record<string, unknown>),
        docket_ids: ["Docket No. PHMSA-2026-1550"],
      },
      govinfo_text:
        "Written comments on the NPRM published at 91 FR 22115 must be received by November 20, 2026.",
    };
    const rows = corpus({ gov: true }).map((r) =>
      r.ocd_id === synthetic.ocd_id ? synthetic : r,
    );
    const o = outcomeFor("2026-08068", rows);
    assert(
      `PHMSA synthetic 19351 as ${label} citing the NPRM: ambiguous (${label === "extension" ? "post-lapse guard" : "reopening rule"}), unchanged`,
      o.kind === "ambiguous" && unchanged("2026-08068", o),
      JSON.stringify(o),
    );
  }
}
{
  const o = outcomeFor("2026-17216");
  assert(
    "USCG 2026-17216 with reopening 2026-19895: ambiguous (a reopening never moves a close), unchanged",
    o.kind === "ambiguous" && unchanged("2026-17216", o),
    JSON.stringify(o),
  );
  assert(
    "USCG 2026-19895 (the reopening's own window): unchanged",
    unchanged("2026-19895", outcomeFor("2026-19895")),
  );
}
{
  const o = outcomeFor("2026-20660");
  assert(
    "ICE 2026-20660 (stored 12-07 observation): none, unchanged",
    o.kind === "none" && unchanged("2026-20660", o),
  );
  const ext: FrAmendmentRow = {
    ...frRow("2026-20660"),
    observation_id: "obs-ice-ext",
    ocd_id: ocd("2026-29999"),
    fr_document_number: "2026-29999",
    is_extension: true,
    raw: {
      ...api("2026-20660"),
      document_number: "2026-29999",
      publication_date: "2026-10-20",
      title: "Optional Practical Training Fees; Extension of Comment Period",
      citation: "91 FR 69999",
      comments_close_on: "2026-11-23",
    },
    govinfo_observation_id: "00000000-0000-4000-8000-000000029999",
    govinfo_text: (api("2026-20660").dates as string).replace(
      "November 9",
      "November 23",
    ),
  };
  const amb = outcomeFor("2026-20660", corpus({ gov: true, extra: [ext] }));
  assert(
    "ICE synthetic extension whose DATES carries both the rule and PRA deadlines: ambiguous, unchanged",
    amb.kind === "ambiguous" && unchanged("2026-20660", amb),
    JSON.stringify(amb),
  );
}
{
  const o = outcomeFor("2026-18134");
  assert(
    "EPA 2026-18134 (Regs-only extension memo): none, unchanged",
    o.kind === "none" && unchanged("2026-18134", o),
  );
}
{
  // Every recorded window: only the three amended ones change; everything else is byte-identical.
  const moved: string[] = [];
  for (const doc of STORED_DOCS) {
    const o = outcomeFor(doc);
    if (!unchanged(doc, o)) moved.push(doc);
  }
  assert(
    "GLOBAL: only Census, USDA and IRS windows change; every other recorded window is byte-identical",
    JSON.stringify(moved.sort()) ===
      JSON.stringify(["2026-18481", "2026-18531", "2026-18574"]),
    moved.join(","),
  );
}

// ── the resolver predicates on their own ────────────────────────────────────────────────────────────
const ORIG = {
  fr_close: "2026-10-13",
  publication_date: "2026-09-10",
  fr_document_number: "2026-00001",
};
let n = 0;
function ev(over: Partial<AmendmentEvidence> = {}): AmendmentEvidence {
  n++;
  return {
    ocd_id: ocd(`2026-9000${n}`),
    fr_document_number: `2026-9000${n}`,
    fr_observation_id: `00000000-0000-4000-8000-00000000900${n}`,
    govinfo_observation_id: `00000000-0000-4000-8000-00000000800${n}`,
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
assert(
  "resolver: no evidence → none",
  resolveAmendedClose(ORIG, []).kind === "none",
);
{
  const o = resolveAmendedClose(ORIG, [
    ev({
      publication_date: "2026-10-05",
      govinfo_text: "Comments must be received on or before November 20, 2026.",
    }),
    ev({ publication_date: "2026-10-01" }),
  ]);
  assert(
    "rule 4: the latest publication date wins (regardless of input order)",
    o.kind === "amended" && o.date === "2026-11-20",
    JSON.stringify(o),
  );
}
assert(
  "rule 4: two amendments on the same publication date with different dates → ambiguous",
  resolveAmendedClose(ORIG, [
    ev(),
    ev({
      govinfo_text: "Comments must be received on or before November 9, 2026.",
    }),
  ]).kind === "ambiguous",
);
assert(
  "rule 4: any ambiguous amendment makes the whole outcome ambiguous",
  resolveAmendedClose(ORIG, [
    ev({ publication_date: "2026-10-05" }),
    ev({
      govinfo_text:
        "Comments must be received on or before November 9, 2026 and no later than December 7, 2026.",
    }),
  ]).kind === "ambiguous",
);
assert(
  "rule 1: a linked withdrawal → ambiguous even alongside a valid extension",
  resolveAmendedClose(ORIG, [
    ev(),
    ev({ is_extension: false, is_withdrawal: true }),
  ]).kind === "ambiguous",
);
assert(
  "rule 1: an 'Extension and Reopening' notice (both flags) → ambiguous",
  resolveAmendedClose(ORIG, [ev({ is_reopening: true })]).kind === "ambiguous",
);
assert(
  "rule 3: an extension to a date not after the original close → ambiguous",
  resolveAmendedClose(ORIG, [
    ev({
      govinfo_text: "Comments must be received on or before October 1, 2026.",
    }),
  ]).kind === "ambiguous",
);
assert(
  "rule 3: post-lapse — published after the original close → ambiguous",
  resolveAmendedClose(ORIG, [ev({ publication_date: "2026-10-20" })]).kind ===
    "ambiguous",
);
assert(
  "rule 3: no deadline phrase → none",
  resolveAmendedClose(ORIG, [
    ev({ govinfo_text: "The meeting is November 2, 2026." }),
  ]).kind === "none",
);
assert(
  "rule 3 cross-check: a plausible FR comments_close_on that disagrees with the text → ambiguous",
  resolveAmendedClose(ORIG, [ev({ fr_comments_close_on: "2026-11-05" })])
    .kind === "ambiguous",
);
{
  const o = resolveAmendedClose(ORIG, [
    ev({ fr_comments_close_on: "2026-11-02" }),
  ]);
  assert(
    "rule 3 cross-check: an agreeing FR comments_close_on → amended, nothing to note",
    o.kind === "amended" && o.date === "2026-11-02" && !("reasons" in o),
  );
}
{
  const frOnly = ev({
    govinfo_text: null,
    govinfo_observation_id: null,
    fr_dates_text: "Submit comments on or before November 2, 2026.",
    fr_comments_close_on: "2026-11-02",
  });
  const o = resolveAmendedClose(ORIG, [frOnly]);
  assert(
    "rule 3: FR dates text alone counts when it equals FR comments_close_on (two signals); ids = FR only",
    o.kind === "amended" &&
      o.date === "2026-11-02" &&
      JSON.stringify(o.observation_ids) ===
        JSON.stringify([frOnly.fr_observation_id]),
  );
  assert(
    "rule 3: FR dates text with NO FR close → none (one signal)",
    resolveAmendedClose(ORIG, [{ ...frOnly, fr_comments_close_on: null }])
      .kind === "none",
  );
  assert(
    "rule 3: FR dates text disagreeing with a plausible FR close → ambiguous",
    resolveAmendedClose(ORIG, [
      { ...frOnly, fr_comments_close_on: "2026-11-09" },
    ]).kind === "ambiguous",
  );
}
{
  const cor = (text: string, over: Partial<AmendmentEvidence> = {}) =>
    resolveAmendedClose(ORIG, [
      ev({
        is_extension: false,
        is_correction: true,
        govinfo_text: text,
        ...over,
      }),
    ]);
  const good =
    // The real GPO correction shape (C1-2026-18574's), with this test's dates.
    "In proposed rule document 2026-00001 beginning on page 57968 in the issue of Friday, September 11, 2026, make the following correction: On page 57968, in the first column, in the second line of the DATES section, ``October 13, 2026'' should read ``October 23, 2026''.";
  const o = cor(good);
  assert(
    "rule 2: a DATES correction of the original close → amended (correction), ids = FR + govinfo",
    o.kind === "amended" &&
      o.change === "correction" &&
      o.date === "2026-10-23" &&
      o.observation_ids.length === 2,
  );
  assert(
    "rule 2: straight and curly double quotes are accepted",
    (cor(good.replace(/``|''/g, '"')) as { date?: string }).date ===
      "2026-10-23" &&
      (
        cor(
          good
            .replace("``", "“")
            .replace("''", "”")
            .replace("``", "“")
            .replace("''", "”"),
        ) as {
          date?: string;
        }
      ).date === "2026-10-23",
  );
  assert(
    "rule 2: a correction touching other text → none (not ambiguous)",
    cor(
      "In rule document 2026-00001 … in the DATES section, ``Agency'' should read ``Bureau''.",
    ).kind === "none",
  );
  assert(
    "rule 2: a date correction whose X is not the original close → none",
    cor(good.replace("October 13", "November 5")).kind === "none",
  );
  assert(
    "rule 2: a correction body that never mentions DATES → none",
    cor(good.replace("DATES section", "SUMMARY")).kind === "none",
  );
  assert(
    "rule 2: two qualifying pairs (one DATES instruction) with different Ys → ambiguous",
    cor(
      good.replace(
        "''.",
        "''; ``October 13, 2026'' should read ``October 30, 2026''.",
      ),
    ).kind === "ambiguous",
  );
  assert(
    "rule 2 (round-1 #4): a pair in a SEPARATE sentence that does not place itself in DATES binds nothing",
    (() => {
      const o = cor(
        good + " Also ``October 13, 2026'' should read ``October 30, 2026''.",
      );
      return o.kind === "amended" && o.date === "2026-10-23";
    })(),
  );
  assert(
    "rule 2: a correction without published text → none",
    cor(null as unknown as string, { govinfo_text: null }).kind === "none",
  );
  assert(
    "rule 2 + post-lapse: a correction published after the original close → ambiguous",
    cor(good, { publication_date: "2026-10-20" }).kind === "ambiguous",
  );
}
assert(
  "deadlineDates: published-on dates and non-deadline dates are ignored; phrase vocabulary",
  JSON.stringify(
    deadlineDates(
      "The document originally published on September 11, 2026, is extended from October 13, 2026, to November 2, 2026. The meeting is November 5, 2026.",
    ),
  ) === '["2026-11-02"]',
);
assert(
  "deadlineDates: an abbreviated second date still counts (Dec. 7) → two dates",
  JSON.stringify(
    deadlineDates(
      "Comments must be received on or before November 9, 2026. PRA comments must be received by Dec. 7, 2026.",
    ),
  ) === '["2026-11-09","2026-12-07"]',
);
assert(
  "deadlineDates: closes on / ends on / through / until / no later than",
  JSON.stringify(
    deadlineDates(
      "closes on May 1, 2026; ends on May 2, 2026; through May 3, 2026; until May 4, 2026; no later than May 5, 2026",
    ),
  ) === '["2026-05-01","2026-05-02","2026-05-03","2026-05-04","2026-05-05"]',
);
assert(
  "parseLongDate: real dates only (no Feb 30 rollover)",
  parseLongDate("October 26, 2026") === "2026-10-26" &&
    parseLongDate("Sept. 3, 2026.") === "2026-09-03" &&
    parseLongDate("February 30, 2026") === null &&
    parseLongDate("Agency") === null,
);
assert(
  "shouldReadPairs: GPO doubled quotes",
  JSON.stringify(shouldReadPairs("``a'' should read ``b''")) ===
    '[{"from":"a","to":"b"}]',
);

// ── engine integration details ──────────────────────────────────────────────────────────────────────
{
  const frOnly = observationsOf("2026-18481").filter(
    (x) => x.source === "federal_register",
  );
  const o = outcomeFor("2026-18481");
  const r = reconcile(frOnly, NOW, { amendment: o });
  assert(
    "FR-only window: the FR-driven display names the amendment",
    r.window.resolved_close_display ===
      "closes 2026-11-02 at 11:59 p.m. ET (per FR extension 2026-20328; inferred from FR date-only value)" &&
      r.window.confidence === "low" &&
      JSON.stringify(r.window.conflict_flags) === '["fr_close_amended"]',
    r.window.resolved_close_display ?? "",
  );
  const regsOnly = observationsOf("2026-18481").filter(
    (x) => x.source === "regulations_gov",
  );
  assert(
    "a window with NO FR observation ignores an amended outcome (never invented)",
    isDeepStrictEqual(
      reconcile(regsOnly, NOW, { amendment: o }),
      reconcile(regsOnly, NOW),
    ),
  );
  const ambiguous: AmendmentOutcome = { kind: "ambiguous", reasons: ["x"] };
  assert(
    "ambiguous / none → byte-identical to no option at all",
    unchanged("2026-18481", ambiguous) &&
      unchanged("2026-18481", { kind: "none" }),
  );
}
{
  // §8 backstop: an amended date corroborated by NEITHER the portal (Nov 2) NOR the amendment's own FR
  // comments_close_on (20328 says Nov 2) changes nothing — the window is byte-identical.
  const o = outcomeFor("2026-18481");
  if (o.kind !== "amended") throw new Error("setup");
  const wrongUncorroborated: AmendmentOutcome = { ...o, date: "2026-11-09" };
  assert(
    "§8: an uncorroborated text date (Nov 9 vs portal Nov 2 vs FR Nov 2) leaves the window byte-identical",
    unchanged("2026-18481", wrongUncorroborated),
  );
  // Corroborated by the amendment's own plausible FR close but disagreeing with the portal: the amended
  // FR side stays CONFLICTING, carrying both flags.
  const wrong: AmendmentOutcome = {
    ...o,
    date: "2026-11-09",
    amendment: { ...o.amendment, fr_comments_close_on: "2026-11-09" },
  };
  const r = derive("2026-18481", wrong);
  assert(
    "FR-corroborated amended value disagreeing with Regs → CONFLICTING [fr_regs_date_mismatch, fr_close_amended] + ConflictRecord",
    r.window.confidence === "conflicting" &&
      JSON.stringify(r.window.conflict_flags) ===
        '["fr_regs_date_mismatch","fr_close_amended"]' &&
      r.conflict !== null &&
      r.conflict.conflict_flags.includes("fr_close_amended") &&
      r.window.provenance.conflicting_observation_ids.includes(
        o.observation_ids[0]!,
      ),
  );
}
{
  // An honored human pin still overlays AFTER the amended derivation, exactly as before.
  const obs = observationsOf("2026-18481");
  const regs = obs.filter((x) => x.source === "regulations_gov").at(-1)!;
  const pin: Observation = {
    observation_id: "ffffffff-0000-4000-8000-000000000001",
    ocd_id: ocd("2026-18481"),
    source: "human_review",
    fr_document_number: null,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: "a".repeat(64),
    fetched_at: "2026-10-27T10:00:00.000Z",
    parser_version: "human-review-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw: {
      kind: "pin_close",
      pinned_close_date: "2026-11-02",
      note: "per the Census extension",
      operator: "test",
      reviewed_payload_hashes: [regs.payload_hash],
    },
  };
  const r = reconcile([...obs, pin], NOW, {
    amendment: outcomeFor("2026-18481"),
  });
  assert(
    "honored pin overlays the amended derivation (flags carried + human_resolved)",
    r.window.confidence === "high" &&
      r.window.conflict_flags.includes("fr_close_amended") &&
      r.window.conflict_flags.includes("human_resolved") &&
      r.window.resolved_close_display?.includes("pinned by human review") ===
        true,
    JSON.stringify(r.window.conflict_flags),
  );
}

// ── v2.4 freshness rule: a govinfo row is not evidence about its own window (ADR 0016) ─────────────
// Real data: 2026-18297 (open, FDA; pin_close 2026-11-09 on 09-20, then a metadata-only Regs refresh)
// and 2026-15026 (closed, BOEM; pin_close 2026-08-22, portal shows a junk 1900-01-01 close). On the
// 2026-10-27 replay the GovInfo sweep appended a govinfo row to each chain AFTER the verdict, and the
// v2.3 rule ("every newer non-human observation is evidence") superseded both pins.
{
  const hr = JSON.parse(
    readFileSync(join(FIX, "stored", "human-resolved.json"), "utf8"),
  ) as Observation[];
  assert(
    "DERIVATION_SOURCES is exactly FR + Regs (named, not 'not human')",
    JSON.stringify(DERIVATION_SOURCES) ===
      '["federal_register","regulations_gov"]' &&
      !isDerivationSource("govinfo") &&
      !isDerivationSource("human_review"),
  );
  for (const doc of ["2026-18297", "2026-15026"]) {
    const chain = hr.filter((o) => o.ocd_id === ocd(doc));
    const withoutGov = chain.filter((o) => o.source !== "govinfo");
    const gov = chain.find((o) => o.source === "govinfo")!;
    const verdict = chain.filter((o) => o.source === "human_review").at(-1)!;
    assert(
      `${doc} fixture: the govinfo row is newer than the verdict (the replay's shape)`,
      gov.fetched_at > verdict.fetched_at,
    );
    const before = selectHonoredVerdict(withoutGov);
    const after = selectHonoredVerdict(chain);
    assert(
      `${doc}: the verdict is honored before AND after its own govinfo row lands`,
      before?.observation.observation_id === verdict.observation_id &&
        after?.observation.observation_id === verdict.observation_id,
    );
    const wBefore = reconcile(withoutGov, NOW);
    const wAfter = reconcile(chain, NOW);
    assert(
      `${doc}: the derivation is byte-identical with and without the govinfo row (HIGH, pinned, human_resolved)`,
      isDeepStrictEqual(wBefore, wAfter) &&
        wAfter.window.confidence === "high" &&
        wAfter.window.conflict_flags.includes("human_resolved") &&
        wAfter.window.resolved_close_display?.includes(
          "pinned by human review",
        ) === true &&
        wAfter.conflict === null,
      `${wAfter.window.confidence} ${JSON.stringify(wAfter.window.conflict_flags)} ${wAfter.window.resolved_close_utc}`,
    );
    // Real new evidence still invalidates: a newer FR payload (any change) supersedes the pin.
    const fr = chain.filter((o) => o.source === "federal_register").at(-1)!;
    const newerFr: Observation = {
      ...fr,
      observation_id: "eeeeeeee-0000-4000-8000-000000000001",
      fetched_at: "2026-10-28T00:00:00.000Z",
      payload_hash: "e".repeat(64),
      raw: {
        ...(fr.raw as Record<string, unknown>),
        comments_close_on: "2026-12-31",
      },
    };
    assert(
      `${doc}: a newer FEDERAL REGISTER observation still supersedes the verdict`,
      selectHonoredVerdict([...chain, newerFr]) === null,
    );
  }
  {
    // A newer Regs observation with a material change still supersedes (ADR 0010 unchanged).
    const chain = hr.filter((o) => o.ocd_id === ocd("2026-18297"));
    const regs = chain.filter((o) => o.source === "regulations_gov").at(-1)!;
    const raw = JSON.parse(JSON.stringify(regs.raw)) as {
      data: { attributes: Record<string, unknown> };
    };
    raw.data.attributes.commentEndDate = "2026-12-01T04:59:59Z";
    assert(
      "2026-18297: a materially changed newer Regs observation still supersedes the verdict",
      selectHonoredVerdict([
        ...chain,
        {
          ...regs,
          observation_id: "eeeeeeee-0000-4000-8000-000000000002",
          fetched_at: "2026-10-28T00:00:00.000Z",
          payload_hash: "d".repeat(64),
          raw,
        },
      ]) === null,
    );
  }
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
