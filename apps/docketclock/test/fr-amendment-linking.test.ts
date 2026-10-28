/** Independent, fixture-driven acceptance tests for docs/plans/fr-amendment-linking.md.
 * Pure: no database, network, parser reimplementation, or generated expected outcomes.
 * Run: node --import tsx apps/docketclock/test/fr-amendment-linking.test.ts
 */
import { strict as a } from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Observation } from "@yokel/contracts";
import type {
  AmendmentEvidence,
  AmendmentOutcome,
} from "../src/reconcile/amendment.js";
import type { ChainCandidate, LinkBasis } from "../src/reconcile/chain.js";
import * as chain from "../src/reconcile/chain.js";
import {
  frNoticeFlags,
  parseFrObservation,
  payloadHash,
  PARSER_VERSION,
} from "../src/sources/federal-register.js";
import { reconcile, RECONCILER_VERSION } from "../src/reconcile/reconcile.js";

let failures = 0;
let checks = 0;
const out: string[] = [];
function test(name: string, fn: () => void) {
  checks++;
  try {
    fn();
    out.push(`  PASS  ${name}`);
  } catch (error) {
    failures++;
    out.push(
      `  FAIL  ${name} — ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}
const ROOT = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures/fr-amendments",
);
const NOW = new Date("2026-10-20T12:00:00Z");
const stored: Observation[] = JSON.parse(
  readFileSync(join(ROOT, "stored/observations.json"), "utf8"),
);
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;
const observations = (doc: string) =>
  stored.filter((o) => o.ocd_id === ocd(doc));
const api = (doc: string) =>
  JSON.parse(readFileSync(join(ROOT, "fr-api", `${doc}.json`), "utf8"));
const html = (doc: string) =>
  readFileSync(join(ROOT, "govinfo", `${doc}.htm`), "utf8");
const frRow = (doc: string): Observation => {
  const row = observations(doc)
    .filter((o) => o.source === "federal_register")
    .sort(
      (x, y) =>
        x.fetched_at.localeCompare(y.fetched_at) ||
        x.observation_id.localeCompare(y.observation_id),
    )
    .at(-1);
  a.ok(row, `missing stored FR observation for ${doc}`);
  return row;
};
const rawFr = (doc: string): any => frRow(doc).raw;
function summary(w: ReturnType<typeof reconcile>["window"]) {
  return {
    close: w.resolved_close_utc,
    confidence: w.confidence,
    flags: [...w.conflict_flags].sort(),
    status: w.status,
    raw_fr: w.raw_fr_close_date,
    raw_regs: w.raw_regs_close_datetime,
  };
}
// Recorded by replaying HEAD 0a36548 through the actual main engine, with the pinned clock above.
const baseline = {
  "2026-08068": {
    close: "2026-11-21T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-06-23",
    raw_regs: "2026-11-21T04:59:59Z",
  },
  "2026-08077": {
    close: "2026-11-21T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-06-23",
    raw_regs: "2026-11-21T04:59:59Z",
  },
  "2026-10969": {
    close: "2026-11-21T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-08-03",
    raw_regs: "2026-11-21T04:59:59Z",
  },
  "2026-17216": {
    close: "2026-09-24T03:59:59.000Z",
    confidence: "medium",
    flags: ["tz_normalization_only"],
    status: "closed",
    raw_fr: "2026-09-23",
    raw_regs: "2026-09-24T03:59:59Z",
  },
  "2026-19895": {
    close: "2026-10-30T03:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-08-24",
    raw_regs: "2026-10-30T03:59:59Z",
  },
  "2026-20660": {
    close: "2026-11-10T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-12-07",
    raw_regs: "2026-11-10T04:59:59Z",
  },
  "2026-18134": {
    close: "2026-11-19T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-10-19",
    raw_regs: "2026-11-19T04:59:59Z",
  },
  "2026-18531": {
    close: "2026-11-03T04:59:59.000Z",
    confidence: "conflicting",
    flags: ["fr_regs_date_mismatch"],
    status: "open",
    raw_fr: "2026-10-13",
    raw_regs: "2026-11-03T04:59:59Z",
  },
} as const;

for (const [doc, expected] of Object.entries(baseline)) {
  test(`${doc}: no-amendment derivation matches concrete main baseline`, () => {
    a.deepEqual(summary(reconcile(observations(doc), NOW).window), expected);
  });
}
test("FR parser is version fr-v3", () => a.equal(PARSER_VERSION, "fr-v3"));
test("reconciler is version reconcile-v2.4", () =>
  a.equal(RECONCILER_VERSION, "reconcile-v2.4"));
test("IRS C1 fixture: correction_of sets correction flag and survives parseFrObservation", () => {
  a.equal(
    frRow("C1-2026-18574").is_correction,
    false,
    "fixture must exercise old fr-v2 row",
  );
  a.equal(frNoticeFlags(api("C1-2026-18574")).is_correction, true);
  a.equal(parseFrObservation(api("C1-2026-18574")).is_correction, true);
});
test("blank correction_of is not a correction", () => {
  for (const correction_of of [null, "", "   "]) {
    a.equal(
      frNoticeFlags({ title: "An ordinary notice", correction_of })
        .is_correction,
      false,
    );
  }
});

// Guard imports to report every missing pinned module/export clearly on unmodified main.
let gov: typeof import("../src/sources/govinfo.js") | undefined;
let amendment: typeof import("../src/reconcile/amendment.js") | undefined;
try {
  gov = await import("../src/sources/govinfo.js");
} catch (error) {
  test("pinned interface src/sources/govinfo.ts is available", () => {
    throw error;
  });
}
try {
  amendment = await import("../src/reconcile/amendment.js");
} catch (error) {
  test("pinned interface src/reconcile/amendment.ts is available", () => {
    throw error;
  });
}
for (const name of [
  "govinfoPlainText",
  "extractDatesSection",
  "extractCorrectionBody",
  "parseGovinfoObservation",
] as const) {
  test(`pinned export govinfo.${name}`, () =>
    a.equal(typeof gov?.[name], "function"));
}
test("pinned export amendment.resolveAmendedClose", () =>
  a.equal(typeof amendment?.resolveAmendedClose, "function"));
test("pinned export chain.linkBasis", () =>
  a.equal(typeof chain.linkBasis, "function"));

try {
  if (
    gov &&
    amendment &&
    typeof chain.linkBasis === "function" &&
    [
      gov.govinfoPlainText,
      gov.extractDatesSection,
      gov.extractCorrectionBody,
      gov.parseGovinfoObservation,
      amendment.resolveAmendedClose,
    ].every((fn) => typeof fn === "function")
  ) {
    const {
      govinfoPlainText,
      extractDatesSection,
      extractCorrectionBody,
      parseGovinfoObservation,
    } = gov;
    const { resolveAmendedClose } = amendment;
    const { linkBasis, chainReconcile, chainAmbiguousPairs } = chain;
    const govObservation = (doc: string) => {
      const raw = api(doc);
      return parseGovinfoObservation({
        frDocNum: doc,
        publicationDate: raw.publication_date,
        url: `https://www.govinfo.gov/content/pkg/FR-${raw.publication_date}/html/${doc}.htm`,
        html: html(doc),
        isCorrection: frNoticeFlags(raw).is_correction,
      });
    };
    const urlDoc = (url: string) => url.split("/").at(-1)!;
    function candidate(doc: string, withGov = false): ChainCandidate {
      const row = stored.find(
        (o) => o.ocd_id === ocd(doc) && o.source === "federal_register",
      );
      const raw = (row?.raw as any) ?? api(doc);
      const w = row ? reconcile(observations(doc), NOW).window : null;
      return {
        ocd_id: ocd(doc),
        fr_observation_id:
          row?.observation_id ?? "00000000-0000-4000-8000-000000000193",
        fr_document_number: doc,
        docket_ids: raw.docket_ids ?? [],
        rin: raw.regulation_id_numbers?.[0] ?? null,
        rins: raw.regulation_id_numbers ?? [],
        ...frNoticeFlags(raw),
        title: raw.title ?? null,
        publication_date: raw.publication_date,
        dates_text: row?.raw_dates_text ?? raw.dates ?? null,
        status: w?.status ?? "unknown",
        resolved_close_utc: w?.resolved_close_utc ?? null,
        govinfo_url: w?.govinfo_url ?? null,
        citation: raw.citation ?? null,
        correction_of: raw.correction_of ? urlDoc(raw.correction_of) : null,
        corrections: (raw.corrections ?? []).map(urlDoc),
        govinfo_text: withGov ? govObservation(doc).raw_dates_text : null,
      };
    }
    function index(candidates: ChainCandidate[]): Map<string, number> {
      const docs = new Map<string, Set<string>>();
      for (const c of candidates)
        if (c.citation && c.fr_document_number) {
          if (!docs.has(c.citation)) docs.set(c.citation, new Set());
          docs.get(c.citation)!.add(c.fr_document_number);
        }
      return new Map(
        [...docs].map(([citation, docnums]) => [citation, docnums.size]),
      );
    }
    function evidence(b: ChainCandidate, basis: LinkBasis): AmendmentEvidence {
      const raw = stored.some((o) => o.ocd_id === b.ocd_id)
        ? rawFr(b.fr_document_number!)
        : api(b.fr_document_number!);
      return {
        ocd_id: b.ocd_id,
        fr_document_number: b.fr_document_number!,
        fr_observation_id: b.fr_observation_id,
        govinfo_observation_id: b.govinfo_text
          ? "00000000-0000-4000-8000-000000000099"
          : null,
        publication_date: b.publication_date!,
        is_extension: b.is_extension,
        is_correction: b.is_correction,
        is_reopening: b.is_reopening,
        is_withdrawal: b.is_withdrawal,
        fr_comments_close_on: raw.comments_close_on ?? null,
        fr_dates_text: b.dates_text,
        govinfo_text: b.govinfo_text,
        basis,
      };
    }
    const original = (doc: string) => ({
      fr_close: rawFr(doc).comments_close_on ?? null,
      publication_date: rawFr(doc).publication_date,
      fr_document_number: doc,
    });
    function outcomeFor(aDoc: string, bs: ChainCandidate[]): AmendmentOutcome {
      const ca = candidate(aDoc);
      const all = [ca, ...bs];
      const links = chainReconcile(all, NOW);
      const ev = bs.flatMap((b) => {
        const basis = linkBasis(ca, b, index(all));
        return basis &&
          links.some((l) => l.ocd_id === ca.ocd_id && l.ocd_id_b === b.ocd_id)
          ? [evidence(b, basis)]
          : [];
      });
      return resolveAmendedClose(original(aDoc), ev);
    }
    function unchanged(doc: keyof typeof baseline, outcome: AmendmentOutcome) {
      a.notEqual(outcome.kind, "amended");
      const before = reconcile(observations(doc), NOW);
      const after = reconcile(observations(doc), NOW, { amendment: outcome });
      a.deepEqual(
        after,
        before,
        "none/ambiguous must preserve the entire result, including conflict and provenance",
      );
      a.deepEqual(summary(after.window), baseline[doc]);
    }

    test("GovInfo plain text strips markup, decodes named/decimal/hex entities and normalizes CRLF", () => {
      a.equal(
        govinfoPlainText(
          "<pre>A &amp; &lt;B&gt; &quot;Q&quot; &#39;x&#39; &#65; &#x42;\r\nnext</pre>",
        ),
        "A & <B> \"Q\" 'x' A B\nnext",
      );
    });
    test("DATES section collapses whitespace and stops at every supported header or EOF", () => {
      for (const header of [
        "ADDRESSES:",
        "FOR FURTHER INFORMATION CONTACT:",
        "SUPPLEMENTARY INFORMATION:",
      ]) {
        const text = `SUMMARY: ignore\nDATES: Comments must be received\n  by November 2, 2026.\n${header} December 7, 2026.`;
        const section = extractDatesSection(text) ?? "";
        a.ok(
          section?.includes("Comments must be received by November 2, 2026."),
        );
        a.ok(!section.includes("December"));
        a.ok(!/\s{2,}/.test(section));
      }
      a.ok(
        extractDatesSection(
          "DATES: Comments close on November 2, 2026.",
        )?.includes("November 2, 2026."),
      );
      a.equal(extractDatesSection("SUMMARY: No date section."), null);
    });
    test("correction body recognizes document introductions, collapses whitespace, and excludes FR Doc footer", () => {
      for (const qualifier of [
        "proposed rule ",
        "rule ",
        "notice ",
        "presidential ",
        "",
      ]) {
        const body =
          extractCorrectionBody(
            `HEADER\n  In ${qualifier}document 2026-18574 beginning on page 57968\n in the DATES section, text changes.\n[FR Doc. C1-2026-18574 Filed]`,
          ) ?? "";
        a.ok(body?.startsWith(`In ${qualifier}document`));
        a.ok(!body.includes("HEADER") && !body.includes("[FR Doc."));
        a.ok(!/\s{2,}/.test(body));
      }
      a.equal(
        extractCorrectionBody("An unrelated paragraph mentioning a document."),
        null,
      );
    });
    test("GovInfo observations preserve real upstream raw/html/hash, own identity and false flags", () => {
      for (const doc of ["2026-20328", "2026-19710", "C1-2026-18574"]) {
        const obs = govObservation(doc);
        const raw = api(doc);
        const expectedRaw = {
          document_number: doc,
          publication_date: raw.publication_date,
          url: `https://www.govinfo.gov/content/pkg/FR-${raw.publication_date}/html/${doc}.htm`,
          html: html(doc),
        };
        a.equal(obs.source, "govinfo");
        a.equal(obs.ocd_id, ocd(doc));
        a.equal(obs.fr_document_number, doc);
        a.equal(obs.parser_version, "govinfo-v1");
        a.deepEqual(obs.raw, expectedRaw);
        a.equal(obs.payload_hash, payloadHash(expectedRaw));
        for (const flag of [
          "is_extension",
          "is_correction",
          "is_reopening",
          "is_withdrawal",
        ] as const)
          a.equal(obs[flag], false);
        const text = govinfoPlainText(html(doc));
        a.equal(
          obs.raw_dates_text,
          doc.startsWith("C1-")
            ? extractCorrectionBody(text)
            : extractDatesSection(text),
        );
      }
      a.ok(
        govObservation("2026-19710").raw_dates_text?.includes("(91 FR 57828)"),
      );
      a.ok(
        govObservation("C1-2026-18574").raw_dates_text?.includes("should read"),
      );
    });

    for (const [doc, bDoc, basis, date, close, change] of [
      [
        "2026-18481",
        "2026-20328",
        "docket_rin",
        "2026-11-02",
        "2026-11-03T04:59:59.000Z",
        "extension",
      ],
      [
        "2026-18531",
        "2026-19710",
        "citation",
        "2026-11-02",
        "2026-11-03T04:59:59.000Z",
        "extension",
      ],
      [
        "2026-18574",
        "C1-2026-18574",
        "correction_of",
        "2026-10-26",
        "2026-10-27T03:59:59.000Z",
        "correction",
      ],
    ] as const) {
      test(`${doc} + ${bDoc}: real stored observations → ${basis} → ${date} → HIGH/open amended window`, () => {
        const ca = candidate(doc);
        const cb = candidate(bDoc, true);
        a.equal(linkBasis(ca, cb, index([ca, cb])), basis);
        a.ok(
          chainReconcile([ca, cb], NOW).some(
            (l) => l.ocd_id === ca.ocd_id && l.ocd_id_b === cb.ocd_id,
          ),
        );
        a.equal(chainAmbiguousPairs([ca, cb], NOW).length, 0);
        const ev = evidence(cb, basis);
        const result = outcomeFor(doc, [cb]);
        a.equal(result.kind, "amended");
        if (result.kind !== "amended") return;
        a.equal(result.date, date);
        a.equal(result.change, change);
        a.deepEqual(result.amendment, ev);
        a.deepEqual(
          [...result.observation_ids].sort(),
          [ev.fr_observation_id, ev.govinfo_observation_id!].sort(),
        );
        const derived = reconcile(observations(doc), NOW, {
          amendment: result,
        });
        a.deepEqual(summary(derived.window), {
          close,
          confidence: "high",
          flags: ["fr_close_amended", "tz_normalization_only"],
          status: "open",
          raw_fr: rawFr(doc).comments_close_on,
          raw_regs: close.replace(".000Z", "Z"),
        });
        a.equal(derived.conflict, null);
        for (const id of result.observation_ids)
          a.ok(derived.window.current_observation_ids.includes(id));
        for (const id of result.observation_ids)
          a.ok(
            JSON.stringify(derived.window.provenance).includes(id),
            "provenance must include amendment evidence",
          );
      });
    }
    test("USDA: no GovInfo means no citation basis and truncated FR text yields none, unchanged", () => {
      const ca = candidate("2026-18531");
      const cb = candidate("2026-19710");
      a.equal(linkBasis(ca, cb, index([ca, cb])), null);
      a.equal(chainAmbiguousPairs([ca, cb], NOW).length, 1);
      a.deepEqual(
        resolveAmendedClose(original("2026-18531"), [evidence(cb, "citation")]),
        { kind: "none" },
      );
      const actual = outcomeFor("2026-18531", [cb]);
      a.deepEqual(actual, { kind: "none" });
      unchanged("2026-18531", actual);
    });
    test("USDA: bad own close is publication date and cannot override verified November 2", () => {
      const ev = evidence(candidate("2026-19710", true), "citation");
      a.equal(ev.fr_comments_close_on, "2026-09-11");
      const result = resolveAmendedClose(original("2026-18531"), [ev]);
      a.equal(result.kind, "amended");
      if (result.kind === "amended") a.equal(result.date, "2026-11-02");
    });
    test("IRS correction that changes non-date text yields none and never changes the window", () => {
      const ev = {
        ...evidence(candidate("C1-2026-18574", true), "correction_of"),
        govinfo_text:
          'In proposed rule document 2026-18574 beginning on page 57968, in the ADDRESSES section, "Room 100" should read "Room 200".',
      };
      const result = resolveAmendedClose(original("2026-18574"), [ev]);
      a.deepEqual(result, { kind: "none" });
      a.deepEqual(
        reconcile(observations("2026-18574"), NOW, { amendment: result }),
        reconcile(observations("2026-18574"), NOW),
      );
    });
    for (const doc of ["2026-08068", "2026-08077", "2026-10969"] as const) {
      test(`PHMSA meeting 2026-19351 never moves ${doc}`, () => {
        const cb = candidate("2026-19351", true);
        a.equal(
          cb.is_extension ||
            cb.is_reopening ||
            cb.is_correction ||
            cb.is_withdrawal,
          false,
        );
        a.deepEqual(outcomeFor(doc, [cb]), { kind: "none" });
        unchanged(doc, outcomeFor(doc, [cb]));
      });
      for (const flag of ["is_extension", "is_reopening"] as const) {
        test(`PHMSA synthetic ${flag} citing ${doc} stays unchanged (post-lapse/reopening)`, () => {
          const ca = candidate(doc);
          const cb = {
            ...candidate("2026-19351", true),
            [flag]: true,
            title: `${ca.title}; comment period`,
            govinfo_text: `(${ca.citation}) Comments must be received no later than November 20, 2026.`,
          };
          a.equal(linkBasis(ca, cb, index([ca, cb])), "citation");
          const actual = resolveAmendedClose(original(doc), [
            evidence(cb, "citation"),
          ]);
          a.equal(actual.kind, "ambiguous");
          unchanged(doc, actual);
        });
      }
    }
    test("USCG reopening 2026-19895 leaves original 2026-17216 and its own window unchanged", () => {
      const result = outcomeFor("2026-17216", [candidate("2026-19895", true)]);
      a.equal(result.kind, "ambiguous");
      unchanged("2026-17216", result);
      unchanged(
        "2026-19895",
        outcomeFor("2026-19895", [candidate("2026-17216")]),
      );
    });
    test("ICE stored December 7 metadata remains unchanged without an FR amendment", () => {
      a.equal(rawFr("2026-20660").comments_close_on, "2026-12-07");
      a.equal(
        api("2026-20660").comments_close_on,
        "2026-11-09",
        "live fixture is deliberately different",
      );
      unchanged("2026-20660", outcomeFor("2026-20660", []));
    });
    test("ICE synthetic extension carrying rule + PRA deadlines is ambiguous, unchanged", () => {
      const ev = {
        ...evidence(candidate("2026-20328"), "doc_number"),
        fr_comments_close_on: "2026-11-09",
        fr_dates_text: api("2026-20660").dates,
        govinfo_text: null,
      };
      const result = resolveAmendedClose(original("2026-20660"), [ev]);
      a.equal(result.kind, "ambiguous");
      unchanged("2026-20660", result);
    });
    test("EPA portal-only extension leaves October 19 FR vs November 18 ET portal conflict unchanged", () => {
      unchanged("2026-18134", outcomeFor("2026-18134", []));
    });

    const ca = candidate("2026-18531");
    const cb = candidate("2026-19710", true);
    test("RIN alone under different dockets gives no basis or confident/ambiguous chain", () => {
      const x = {
        ...ca,
        rins: ["1234-AA00"],
        rin: "1234-AA00",
        citation: null,
      };
      const y = {
        ...cb,
        docket_ids: ["OTHER"],
        rins: x.rins,
        rin: x.rin,
        govinfo_text: null,
        dates_text: "No reference.",
      };
      a.equal(linkBasis(x, y, index([x, y])), null);
      a.equal(chainReconcile([x, y], NOW).length, 0);
      a.equal(chainAmbiguousPairs([x, y], NOW).length, 0);
    });
    test("citation carried by two DISTINCT documents blocks citation linkage across the full candidate set", () => {
      const duplicate = {
        ...ca,
        ocd_id: ocd("2026-99999"),
        fr_document_number: "2026-99999",
        fr_observation_id: "00000000-0000-4000-8000-000000009999",
        docket_ids: ["UNRELATED"],
      };
      a.equal(linkBasis(ca, cb, index([ca, cb, duplicate])), null);
      a.equal(chainReconcile([ca, cb, duplicate], NOW).length, 0);
      a.equal(
        index([ca, ca, cb]).get(ca.citation!),
        1,
        "duplicate observations are not duplicate documents",
      );
      a.equal(linkBasis(ca, cb, index([ca, ca, cb])), "citation");
    });
    test("pin-cite/longer page tokens do not match; parenthesized whole citation does", () => {
      for (const text of [
        "91 FR 57820, 57828",
        "91 FR 578280",
        "191 FR 57828",
      ]) {
        a.equal(
          linkBasis(
            ca,
            { ...cb, govinfo_text: text, dates_text: null },
            index([ca, cb]),
          ),
          null,
          text,
        );
      }
      a.equal(
        linkBasis(
          ca,
          { ...cb, govinfo_text: "(91 FR 57828)", dates_text: null },
          index([ca, cb]),
        ),
        "citation",
      );
      a.equal(
        linkBasis(
          ca,
          { ...cb, govinfo_text: null, dates_text: "(91 FR 57828)" },
          index([ca, cb]),
        ),
        "citation",
      );
    });
    test("different-docket citation + normalized full-title prefix links, with no RIN", () => {
      const y = {
        ...cb,
        docket_ids: ["DIFFERENT"],
        title: `  ${ca.title!.toUpperCase().replaceAll(" ", "  ")} ; Extension`,
      };
      a.equal(linkBasis(ca, y, index([ca, y])), "citation");
      a.equal(chainReconcile([ca, y], NOW).length, 1);
      a.equal(chainAmbiguousPairs([ca, y], NOW).length, 0);
      a.equal(
        linkBasis(ca, { ...y, title: "Unrelated title" }, index([ca, y])),
        null,
        "citation needs corroboration",
      );
      a.equal(
        linkBasis(
          ca,
          { ...y, title: "Unrelated", rins: ["1234-AA00"] },
          index([ca, y]),
        ),
        null,
      );
      a.equal(
        linkBasis(
          { ...ca, rins: ["1234-AA00"] },
          { ...y, title: "Unrelated", rins: ["1234-AA00"] },
          index([ca, y]),
        ),
        "citation",
      );
    });
    test("doc number basis requires shared docket, accepts FR whitespace and GovInfo, rejects substrings", () => {
      for (const field of ["dates_text", "govinfo_text"] as const) {
        const y = {
          ...cb,
          dates_text: null,
          govinfo_text: null,
          [field]: "FR Doc. 2026- 18531",
        };
        a.equal(linkBasis(ca, y, index([ca, y])), "doc_number");
        a.equal(
          linkBasis(ca, { ...y, docket_ids: ["OTHER"] }, index([ca, y])),
          null,
        );
        a.equal(
          linkBasis(ca, { ...y, [field]: "2026-185310" }, index([ca, y])),
          null,
        );
      }
    });
    test("structured correction_of takes precedence over other deterministic bases without docket", () => {
      const originalIrs = candidate("2026-18574");
      const correctionIrs = {
        ...candidate("C1-2026-18574", true),
        docket_ids: [],
      };
      // The stored 18574 row was fetched before C1 existed, so ITS corrections[] is empty; the live FR
      // record (fr-api fixture) lists C1. correction_of on B alone must carry the link either way.
      a.equal(originalIrs.corrections.length, 0);
      a.ok(
        (api("2026-18574").corrections as string[]).some(
          (u) => urlDoc(u) === "C1-2026-18574",
        ),
      );
      a.equal(
        linkBasis(
          originalIrs,
          correctionIrs,
          index([originalIrs, correctionIrs]),
        ),
        "correction_of",
      );
      a.equal(chainReconcile([originalIrs, correctionIrs], NOW).length, 1);
    });
    test("LLM-only ambiguous pair has no deterministic basis and therefore never supplies evidence", () => {
      const y = {
        ...cb,
        govinfo_text: "Comments must be received by November 2, 2026.",
        dates_text: null,
      };
      a.equal(linkBasis(ca, y, index([ca, y])), null);
      a.equal(chainReconcile([ca, y], NOW).length, 0);
      a.equal(chainAmbiguousPairs([ca, y], NOW).length, 1);
      const actual = outcomeFor("2026-18531", [y]);
      a.deepEqual(actual, { kind: "none" });
      unchanged("2026-18531", actual);
    });
    test("citation links still obey ordering, recency, and keyword deny-list", () => {
      for (const publication_date of [
        ca.publication_date,
        "2026-09-01",
        "2026-02-30",
        null,
      ]) {
        a.equal(
          chainReconcile([ca, { ...cb, publication_date }], NOW).length,
          0,
        );
      }
      a.equal(
        chainReconcile(
          [
            {
              ...ca,
              status: "closed",
              resolved_close_utc: "2026-01-01T00:00:00Z",
            },
            cb,
          ],
          NOW,
        ).length,
        0,
      );
      a.equal(
        chainReconcile(
          [
            ca,
            { ...cb, title: "Public Land Order No. 7963", is_withdrawal: true },
          ],
          NOW,
        ).length,
        0,
      );
    });

    const base = evidence(cb, "citation");
    const orig = original("2026-18531");
    const resolve = (
      patch: Partial<AmendmentEvidence> = {},
      originalPatch = {},
    ) =>
      resolveAmendedClose({ ...orig, ...originalPatch }, [
        { ...base, ...patch },
      ]);
    test("resolver with no evidence is none", () =>
      a.deepEqual(resolveAmendedClose(orig, []), { kind: "none" }));
    test("any reopening/withdrawal is ambiguous even alongside a valid extension", () => {
      for (const flag of ["is_reopening", "is_withdrawal"] as const) {
        const result = resolveAmendedClose(orig, [
          base,
          { ...base, [flag]: true },
        ]);
        a.equal(result.kind, "ambiguous");
        if (result.kind === "ambiguous") a.ok(result.reasons.length);
      }
    });
    test("extension deadline phrase vocabulary yields exactly one distinct date", () => {
      for (const phrase of [
        "on or before",
        "no later than",
        "extended to",
        "extended until",
        "extended through",
        "to",
        "until",
        "through",
        "must be received by",
        "must be submitted on or before",
        "must be postmarked no later than",
        "closes on",
        "ends on",
      ]) {
        const result = resolve({
          govinfo_text: `Comments ${phrase} November 2, 2026.`,
        });
        a.equal(result.kind, "amended", phrase);
        if (result.kind === "amended") a.equal(result.date, "2026-11-02");
      }
    });
    test("publication/dated references and duplicate mentions do not become competing deadlines", () => {
      const result = resolve({
        govinfo_text:
          "Originally published on September 11, 2026, dated September 10, 2026. Comments on or before November 2, 2026; closes on November 2, 2026.",
      });
      a.equal(result.kind, "amended");
      if (result.kind === "amended") a.equal(result.date, "2026-11-02");
      a.deepEqual(
        resolve({
          govinfo_text:
            "Published on September 11, 2026; dated September 10, 2026.",
        }),
        { kind: "none" },
      );
    });
    test("GovInfo is authoritative; FR fallback needs matching text and valid metadata", () => {
      a.equal(
        resolve({
          govinfo_text: null,
          fr_dates_text: "Comments close on November 2, 2026.",
          fr_comments_close_on: "2026-11-02",
        }).kind,
        "amended",
      );
      for (const fr_comments_close_on of [null, "2026-02-30"]) {
        a.deepEqual(
          resolve({
            govinfo_text: null,
            fr_dates_text: "Comments close on November 2, 2026.",
            fr_comments_close_on,
          }),
          { kind: "none" },
        );
      }
      a.deepEqual(
        resolve({
          govinfo_text: "No deadline in the published DATES.",
          fr_dates_text: "Comments close on November 2, 2026.",
          fr_comments_close_on: "2026-11-02",
        }),
        { kind: "none" },
      );
    });
    test("extension cross-check rejects a conflicting future FR metadata close", () => {
      a.equal(
        resolve({ fr_comments_close_on: "2026-11-03" }).kind,
        "ambiguous",
      );
    });
    test("post-lapse publication is ambiguous; publication on original close remains eligible", () => {
      a.equal(resolve({ publication_date: "2026-10-14" }).kind, "ambiguous");
      a.equal(resolve({ publication_date: "2026-10-13" }).kind, "amended");
    });
    test("extensions cannot move earlier/equal; invalid calendar text cannot invent a close", () => {
      for (const date of ["October 13, 2026", "October 12, 2026"])
        a.equal(
          resolve({ govinfo_text: `Comments close on ${date}.` }).kind,
          "ambiguous",
        );
      a.deepEqual(
        resolve({ govinfo_text: "Comments close on February 30, 2027." }),
        { kind: "none" },
      );
    });
    test("correction supports GPO/straight/curly quotes only in DATES and only when old date matches", () => {
      const corr = evidence(candidate("C1-2026-18574", true), "correction_of");
      const old = original("2026-18574");
      for (const [left, right] of [
        ["``", "''"],
        ['"', '"'],
        ["“", "”"],
      ]) {
        const result = resolveAmendedClose(old, [
          {
            ...corr,
            govinfo_text: `In the DATES section, ${left}October 16, 2026${right} should read ${left}October 26, 2026${right}.`,
          },
        ]);
        a.equal(result.kind, "amended");
        if (result.kind === "amended") a.equal(result.date, "2026-10-26");
      }
      for (const govinfo_text of [
        null,
        'In DATES, "October 15, 2026" should read "October 26, 2026".',
        'In ADDRESSES, "October 16, 2026" should read "October 26, 2026".',
      ]) {
        a.deepEqual(
          resolveAmendedClose(old, [
            {
              ...corr,
              govinfo_text,
              fr_dates_text:
                'In DATES, "October 16, 2026" should read "October 26, 2026".',
            },
          ]),
          { kind: "none" },
        );
      }
    });
    test("two correction pairs producing different dates are ambiguous", () => {
      const corr = evidence(candidate("C1-2026-18574", true), "correction_of");
      const result = resolveAmendedClose(original("2026-18574"), [
        {
          ...corr,
          govinfo_text:
            'In DATES, "October 16, 2026" should read "October 26, 2026"; "October 16, 2026" should read "October 27, 2026".',
        },
      ]);
      a.equal(result.kind, "ambiguous");
    });
    test("correction may move earlier; repeated identical correction pairs are not ambiguous", () => {
      const corr = evidence(candidate("C1-2026-18574", true), "correction_of");
      const pair =
        'In DATES, "October 16, 2026" should read "October 12, 2026".';
      const result = resolveAmendedClose(original("2026-18574"), [
        { ...corr, govinfo_text: `${pair} ${pair}` },
      ]);
      a.equal(result.kind, "amended");
      if (result.kind === "amended") a.equal(result.date, "2026-10-12");
    });
    test("latest date-bearing amendment wins independent of input order; same-day disagreement poisons all", () => {
      const later = {
        ...base,
        publication_date: "2026-10-01",
        fr_observation_id: "00000000-0000-4000-8000-000000000100",
        govinfo_text: "Comments close on November 9, 2026.",
      };
      for (const list of [
        [base, later],
        [later, base],
      ]) {
        const result = resolveAmendedClose(orig, list);
        a.equal(result.kind, "amended");
        if (result.kind === "amended") {
          a.equal(result.date, "2026-11-09");
          a.deepEqual(result.amendment, later);
        }
      }
      a.equal(
        resolveAmendedClose(orig, [
          base,
          { ...later, publication_date: base.publication_date },
        ]).kind,
        "ambiguous",
      );
      a.equal(
        resolveAmendedClose(orig, [
          later,
          { ...base, fr_comments_close_on: "2026-12-01" },
        ]).kind,
        "ambiguous",
      );
      const result = resolveAmendedClose(orig, [
        base,
        { ...later, govinfo_text: "No deadline." },
      ]);
      a.equal(result.kind, "amended");
      if (result.kind === "amended") a.equal(result.date, "2026-11-02");
    });
    test("FR fallback provenance contains only FR id; FR-only display explains amendment and keeps original raw", () => {
      const ev = {
        ...base,
        govinfo_text: null,
        govinfo_observation_id: null,
        fr_dates_text: "Comments close on November 2, 2026.",
        fr_comments_close_on: "2026-11-02",
      };
      const result = resolveAmendedClose(orig, [ev]);
      a.equal(result.kind, "amended");
      if (result.kind !== "amended") return;
      a.deepEqual(result.observation_ids, [ev.fr_observation_id]);
      const frOnly = observations("2026-18531").filter(
        (o) => o.source === "federal_register",
      );
      const w = reconcile(frOnly, NOW, { amendment: result }).window;
      a.equal(w.resolved_close_utc, "2026-11-03T04:59:59.000Z");
      a.equal(w.confidence, "low");
      a.equal(w.raw_fr_close_date, "2026-10-13");
      a.equal(
        w.resolved_close_display,
        "closes 2026-11-02 at 11:59 p.m. ET (per FR extension 2026-19710; inferred from FR date-only value)",
      );
    });
    test("amended date that disagrees with portal remains CONFLICTING with both exact flags", () => {
      // ADR 0016 §8: the amended date must be independently corroborated (here by B's own plausible FR
      // comments_close_on) before it may contradict the portal; the uncorroborated case is below.
      const result = resolve({
        govinfo_text: "Comments close on November 9, 2026.",
        fr_comments_close_on: "2026-11-09",
      });
      a.equal(result.kind, "amended");
      const derived = reconcile(observations("2026-18531"), NOW, {
        amendment: result,
      });
      a.equal(derived.window.confidence, "conflicting");
      a.deepEqual([...derived.window.conflict_flags].sort(), [
        "fr_close_amended",
        "fr_regs_date_mismatch",
      ]);
      a.equal(derived.window.resolved_close_utc, "2026-11-03T04:59:59.000Z");
      a.ok(derived.conflict);
    });
    test("uncorroborated text-only amended date leaves the window byte-identical (ADR 0016 §8)", () => {
      const result = resolve({
        govinfo_text: "Comments close on November 9, 2026.",
      });
      const obs = observations("2026-18531");
      a.deepEqual(
        reconcile(obs, NOW, { amendment: result }).window,
        reconcile(obs, NOW).window,
      );
    });
  }
} catch (error) {
  test("fixture-driven acceptance setup completes", () => {
    throw error;
  });
}

console.log("\n=== fr-amendment-linking results ===");
console.log(out.join("\n"));
console.log(
  `\n${checks - failures}/${checks} passed; ${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exitCode = failures === 0 ? 0 : 1;
