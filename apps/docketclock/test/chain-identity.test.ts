/**
 * chain-identity.test.ts — deterministic chain identity (ADR 0016; docs/plans/fr-amendment-linking.md
 * parts 2–3). PURE (no DB).
 *
 * Proves:
 *   • fr-v3: FR's structured `correction_of` makes is_correction true at parse time (frNoticeFlags) AND at
 *     read time for fr-v2 rows (derivedIsCorrection) — C1-2026-18574 as stored in production;
 *   • extractFr's new identity fields (citation, correctionOf, corrections) off the live FR JSON;
 *   • textCitesCitation is whole-token (no pin-cite range, no digit-adjacent match), wrap-tolerant;
 *   • buildCitationIndex counts DISTINCT document numbers;
 *   • linkBasis: each basis, its precedence, and the identity negatives (shared RIN alone; a citation
 *     carried by two candidates; a citation with no corroborator) plus the positive cross-docket case
 *     (a different docket whose text cites A's unique citation and whose title starts with A's title);
 *   • chainReconcile / chainAmbiguousPairs on the RECORDED rows: IRS (never chained before) links by
 *     correction_of; USDA (LLM-only before) becomes confident by citation and leaves the ambiguous tail;
 *     Census stays confident; ordering/recency/deny-list still apply to the new bases.
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/chain-identity.test.ts
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildCitationIndex,
  chainAmbiguousPairs,
  chainReconcile,
  linkBasis,
  textCitesCitation,
  type ChainCandidate,
} from "../src/reconcile/chain.js";
import {
  derivedIsCorrection,
  extractFr,
  frDocNumberFromUrl,
} from "../src/reconcile/extract.js";
import {
  frNoticeFlags,
  parseFrObservation,
  PARSER_VERSION,
} from "../src/sources/federal-register.js";
import {
  govinfoPlainText,
  extractCorrectionBody,
  extractDatesSection,
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
interface StoredRow {
  observation_id: string;
  ocd_id: string;
  source: string;
  fr_document_number: string | null;
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
  raw: Record<string, unknown>;
}
const stored = JSON.parse(
  readFileSync(join(FIX, "stored", "observations.json"), "utf8"),
) as StoredRow[];
const api = (doc: string) =>
  JSON.parse(
    readFileSync(join(FIX, "fr-api", `${doc}.json`), "utf8"),
  ) as Record<string, unknown>;
const govText = (doc: string, correction: boolean) => {
  const t = govinfoPlainText(
    readFileSync(join(FIX, "govinfo", `${doc}.htm`), "utf8"),
  );
  return correction ? extractCorrectionBody(t) : extractDatesSection(t);
};
const ocd = (doc: string) => `ocd-participation-window/federal/${doc}`;
const NOW = new Date("2026-10-27T12:00:00Z");

/** A candidate from the STORED latest FR row (falls back to the live FR JSON when never ingested). */
function cand(
  doc: string,
  over: Partial<ChainCandidate> = {},
  withGov = false,
): ChainCandidate {
  const rows = stored.filter(
    (r) => r.ocd_id === ocd(doc) && r.source === "federal_register",
  );
  const row = rows.at(-1);
  const raw = row?.raw ?? api(doc);
  const fr = extractFr(raw);
  const correction = row
    ? derivedIsCorrection(row)
    : frNoticeFlags(raw).is_correction;
  const flags = row ?? frNoticeFlags(raw);
  return {
    ocd_id: ocd(doc),
    fr_observation_id: row?.observation_id ?? `obs-${doc}`,
    fr_document_number: doc,
    docket_ids: fr.docketIds,
    rin: fr.rin,
    rins: fr.rins,
    is_extension: flags.is_extension,
    is_correction: correction,
    is_withdrawal: flags.is_withdrawal,
    is_reopening: flags.is_reopening,
    title: fr.title,
    publication_date: fr.publicationDate,
    govinfo_url: null,
    dates_text: fr.datesText,
    status: "open",
    resolved_close_utc: null,
    citation: fr.citation,
    correction_of: fr.correctionOf,
    corrections: fr.corrections,
    govinfo_text: withGov ? govText(doc, correction) : null,
    ...over,
  };
}

// ── fr-v3 correction rule ───────────────────────────────────────────────────────────────────────────
{
  const c1Stored = stored.find(
    (r) => r.ocd_id === ocd("C1-2026-18574") && r.source === "federal_register",
  )!;
  assert(
    "fixture: C1-2026-18574 was stored fr-v2 with is_correction=false",
    c1Stored.is_correction === false,
  );
  assert(
    "derivedIsCorrection: the stored fr-v2 C1 row derives is_correction=true (correction_of)",
    derivedIsCorrection(c1Stored),
  );
  assert(
    "derivedIsCorrection: an ordinary row stays false",
    !derivedIsCorrection(stored.find((r) => r.ocd_id === ocd("2026-18574"))!),
  );
  assert(
    "frNoticeFlags (fr-v3): C1 live JSON → is_correction=true",
    frNoticeFlags(api("C1-2026-18574")).is_correction === true,
  );
  assert(
    "frNoticeFlags: an empty correction_of is not a correction",
    frNoticeFlags({ ...api("2026-18481"), correction_of: "" }).is_correction ===
      false,
  );
  const parsed = parseFrObservation(api("C1-2026-18574"));
  assert(
    "parseFrObservation: fr-v3 stamp + is_correction",
    PARSER_VERSION === "fr-v3" &&
      parsed.parser_version === "fr-v3" &&
      parsed.is_correction === true,
  );
  assert(
    "frDocNumberFromUrl: URL → last segment; bare number kept; empty → null",
    frDocNumberFromUrl(
      "https://www.federalregister.gov/api/v1/documents/2026-18574",
    ) === "2026-18574" &&
      frDocNumberFromUrl("https://x/documents/2026-18574.json") ===
        "2026-18574" &&
      frDocNumberFromUrl("2026-18574") === "2026-18574" &&
      frDocNumberFromUrl("") === null &&
      frDocNumberFromUrl(null) === null,
  );
  const fr = extractFr(api("2026-18574"));
  assert(
    "extractFr: citation + corrections (live JSON) / correctionOf",
    fr.citation === "91 FR 57968" &&
      fr.corrections.join() === "C1-2026-18574" &&
      fr.correctionOf === null &&
      extractFr(api("C1-2026-18574")).correctionOf === "2026-18574",
  );
}

// ── textCitesCitation / buildCitationIndex ──────────────────────────────────────────────────────────
assert(
  "citation: whole token in published text",
  textCitesCitation("(91 FR 57828) is extended", "91 FR 57828"),
);
assert(
  "citation: a pin-cite range never matches its later page",
  !textCitesCitation("see 91 FR 57820, 57828", "91 FR 57828"),
);
assert(
  "citation: digit-adjacent never matches",
  !textCitesCitation("191 FR 57828", "91 FR 57828") &&
    !textCitesCitation("91 FR 578280", "91 FR 57828"),
);
assert(
  "citation: a GPO line wrap between the parts still matches",
  textCitesCitation("at\n91 FR\n54729,", "91 FR 54729"),
);
assert(
  "citation: null text / citation → false",
  !textCitesCitation(null, "91 FR 1") && !textCitesCitation("91 FR 1", null),
);
{
  const idx = buildCitationIndex([
    { citation: "91 FR 1", fr_document_number: "A" },
    { citation: "91 FR 1", fr_document_number: "A" },
    { citation: "91 FR 1", fr_document_number: "B" },
    { citation: "91 FR 2", fr_document_number: "C" },
    { citation: null, fr_document_number: "D" },
  ]);
  assert(
    "citation index: DISTINCT document numbers per citation",
    idx.get("91 FR 1") === 2 && idx.get("91 FR 2") === 1 && idx.size === 2,
  );
}

// ── linkBasis on the recorded documents ─────────────────────────────────────────────────────────────
const usdaA = cand("2026-18531");
const usdaB = cand("2026-19710", {}, true);
const censusA = cand("2026-18481");
const censusB = cand("2026-20328");
const irsA = cand("2026-18574");
const irsB = cand("C1-2026-18574", {}, true);
const all = [usdaA, usdaB, censusA, censusB, irsA, irsB];
const idx = buildCitationIndex(all);

assert(
  "linkBasis: Census 20328 → 18481 by docket_rin",
  linkBasis(censusA, censusB, idx) === "docket_rin",
);
assert(
  "linkBasis: USDA 19710 (+govinfo) → 18531 by citation (shared docket corroborates)",
  linkBasis(usdaA, usdaB, idx) === "citation",
);
assert(
  "linkBasis: USDA 19710 WITHOUT govinfo → null (FR dates truncated before the citation)",
  linkBasis(usdaA, { ...usdaB, govinfo_text: null }, idx) === null,
);
assert(
  "linkBasis: IRS C1 → 18574 by correction_of",
  linkBasis(irsA, irsB, idx) === "correction_of",
);
assert(
  "linkBasis: correction_of needs no docket and outranks every other basis",
  linkBasis(irsA, { ...irsB, docket_ids: [] }, idx) === "correction_of" &&
    linkBasis(
      irsA,
      { ...irsB, govinfo_text: "2026-18574 91 FR 57968" },
      idx,
    ) === "correction_of",
);
assert(
  "linkBasis: doc_number via published text (shared docket), outranks docket_rin",
  linkBasis(
    censusA,
    { ...censusB, govinfo_text: "extends document 2026-18481" },
    idx,
  ) === "doc_number",
);
assert(
  "linkBasis: doc_number tolerates the FR '2026- 18481' wrap",
  linkBasis(
    censusA,
    { ...censusB, rins: [], dates_text: "document 2026- 18481 is extended" },
    idx,
  ) === "doc_number",
);
assert(
  "linkBasis: unrelated pairs → null",
  linkBasis(censusA, usdaB, idx) === null &&
    linkBasis(usdaA, censusB, idx) === null &&
    linkBasis(irsA, censusB, idx) === null,
);
assert(
  "linkBasis: never a self-link",
  linkBasis(censusA, censusA, idx) === null,
);

// Identity negatives.
{
  const a = { ...usdaA, rins: ["1234-AA00"], rin: "1234-AA00" };
  const b = {
    ...usdaB,
    docket_ids: ["OTHER-DOCKET"],
    rins: ["1234-AA00"],
    rin: "1234-AA00",
    govinfo_text: "No reference.",
    dates_text: "No reference.",
  };
  assert(
    "NEGATIVE: a shared RIN alone (different dockets, no citation, no correction_of) → no link",
    linkBasis(a, b, buildCitationIndex([a, b])) === null &&
      chainReconcile([a, b], NOW).length === 0 &&
      chainAmbiguousPairs([a, b], NOW).length === 0,
  );
}
{
  const dup = {
    ...usdaA,
    ocd_id: ocd("2026-99999"),
    fr_document_number: "2026-99999",
    fr_observation_id: "obs-dup",
    docket_ids: ["UNRELATED"],
  };
  const set = [usdaA, usdaB, dup];
  assert(
    "NEGATIVE: a citation carried by two candidates → no citation link (and no confident chain)",
    linkBasis(usdaA, usdaB, buildCitationIndex(set)) === null &&
      chainReconcile(set, NOW).length === 0,
  );
  assert(
    "  …the pair falls back to the ambiguous (LLM) tail on its shared docket",
    chainAmbiguousPairs(set, NOW).some(
      (p) => p.a.ocd_id === usdaA.ocd_id && p.b.ocd_id === usdaB.ocd_id,
    ),
  );
}
{
  const b = {
    ...usdaB,
    govinfo_text: "The document published at 91 FR 57820, 57828 is extended.",
  };
  assert(
    "NEGATIVE: a pin-cite range is not a citation of 91 FR 57828",
    linkBasis(usdaA, b, buildCitationIndex([usdaA, b])) === null,
  );
}
{
  const b = {
    ...usdaB,
    docket_ids: ["OTHER-DOCKET"],
    title: "Something Else Entirely; Extension of Comment Period",
  };
  assert(
    "NEGATIVE: citation with NO corroborator (other docket, no RIN, unrelated title) → null",
    linkBasis(usdaA, b, buildCitationIndex([usdaA, b])) === null,
  );
}
{
  const b = {
    ...usdaB,
    docket_ids: ["Docket No: USDA-2026-9999"],
    title:
      "  MODERNIZATION of Regulations Under 9 CFR Parts 101-118 and   123-124; Extension of Comment Period",
  };
  const set = [usdaA, b];
  assert(
    "POSITIVE: a different docket whose text carries A's unique citation and whose title starts with A's title → citation",
    linkBasis(usdaA, b, buildCitationIndex(set)) === "citation",
  );
  const links = chainReconcile(set, NOW);
  assert(
    "  …and the chain engine links it confidently without a shared docket",
    links.length === 1 &&
      links[0]!.ocd_id === usdaA.ocd_id &&
      links[0]!.conflict_flags.includes("extension_chain_unresolved"),
    JSON.stringify(links.map((l) => l.conflict_flags)),
  );
}
{
  const b = { ...usdaB, docket_ids: ["OTHER"], rins: ["0607-AA75"] };
  const a = { ...usdaA, rins: ["0607-AA75"] };
  assert(
    "citation + shared RIN (no docket) → citation (RIN only ever corroborates)",
    linkBasis(a, b, buildCitationIndex([a, b])) === "citation",
  );
}

// ── the chain engine on the recorded set ────────────────────────────────────────────────────────────
{
  const confident = chainReconcile(all, NOW);
  const pairs = confident.map((c) => `${c.ocd_id}→${c.ocd_id_b}`);
  assert(
    "chain: IRS C1 → 18574 is now a confident link (never chained before: no keyword flag)",
    pairs.includes(`${irsA.ocd_id}→${irsB.ocd_id}`),
    pairs.join(" "),
  );
  assert(
    "  …flagged correction_pending",
    confident
      .find((c) => c.ocd_id_b === irsB.ocd_id)!
      .conflict_flags.includes("correction_pending"),
  );
  assert(
    "chain: USDA 19710 → 18531 is confident (was LLM-only) — no llm_corroborated",
    pairs.includes(`${usdaA.ocd_id}→${usdaB.ocd_id}`) &&
      !confident.some((c) => c.conflict_flags.includes("llm_corroborated")),
  );
  assert(
    "chain: Census 20328 → 18481 stays confident",
    pairs.includes(`${censusA.ocd_id}→${censusB.ocd_id}`),
  );
  assert(
    "chain: no spurious cross-agency links",
    confident.length === 3,
    pairs.join(" "),
  );
  assert(
    "chain: the ambiguous tail no longer holds the deterministically linked pairs",
    chainAmbiguousPairs(all, NOW).length === 0,
  );
  assert(
    "chain: WITHOUT govinfo, USDA is back in the ambiguous tail (LLM path unchanged)",
    chainAmbiguousPairs(
      all.map((c) => (c === usdaB ? { ...c, govinfo_text: null } : c)),
      NOW,
    ).some((p) => p.b.ocd_id === usdaB.ocd_id),
  );
}
{
  // Rules 3 / 4 / 5 still gate the new bases.
  const before = { ...irsB, publication_date: "2026-09-01" };
  assert(
    "rule 3: a correction_of link published BEFORE A never links",
    chainReconcile([irsA, before], NOW).length === 0,
  );
  const dead = {
    ...irsA,
    status: "closed",
    resolved_close_utc: "2026-06-01T03:59:59Z",
  };
  assert(
    "rule 4: an original closed long before the amendment never links",
    chainReconcile([dead, irsB], NOW).length === 0,
  );
  const denied = { ...usdaB, title: "Public Land Order No. 7963; Withdrawal" };
  assert(
    "rule 5: a keyword false-positive is denied even with a citation basis",
    chainReconcile([usdaA, denied], NOW).length === 0,
  );
}
{
  // USCG reopening 19895 → 17216: its FR dates cite 91 FR 54729 on the shared docket.
  const a = cand("2026-17216");
  const b = cand("2026-19895");
  const links = chainReconcile([a, b], NOW);
  assert(
    "chain: USCG reopening links deterministically by citation and carries `reopening`",
    linkBasis(a, b, buildCitationIndex([a, b])) === "citation" &&
      links.length === 1 &&
      links[0]!.conflict_flags.includes("reopening"),
    JSON.stringify(links.map((l) => l.conflict_flags)),
  );
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
