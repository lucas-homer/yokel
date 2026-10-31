/**
 * review-fingerprint.test.ts — the decision fingerprint and the shadow-ledger skip rule
 * (src/review/fingerprint.ts). Pure: no database.
 *
 *   • STABLE when only volatile fields change: Regs modifyDate (the field that drifts daily) and the
 *     envelope's links.self.
 *   • CHANGES when any date or time of day, withdrawal, open/closed flag, identity, title, abstract,
 *     attachment or unknown field changes; and for FR / govinfo / linked-amendment rows whenever the
 *     payload hash changes (no normalization there).
 *   • VERSION BOUNDARY: a ledger line without fingerprints matches by payload hash only; fingerprints
 *     of different versions never match; a hash is never compared with a fingerprint.
 */
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseRegsObservation } from "../src/sources/regulations-gov.js";
import { parseFrObservation } from "../src/sources/federal-register.js";
import {
  decisionFingerprint,
  FINGERPRINT_VERSION,
  fingerprintVersion,
  ledgerSkip,
  sameFingerprintSet,
  type LedgerLine,
} from "../src/review/fingerprint.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const HERE = dirname(fileURLToPath(import.meta.url));
const regsFixture = JSON.parse(
  await readFile(
    join(HERE, "fixtures", "regs-FAA-2025-5396-0001.json"),
    "utf8",
  ),
) as {
  data: { id: string; attributes: Record<string, unknown> };
  links?: Record<string, unknown>;
};
const frFixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "fr-2025-02910.json"), "utf8"),
) as Record<string, unknown>;

type Regs = typeof regsFixture;
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
function regs(mut: (r: Regs) => void = () => {}): Regs {
  const r = clone(regsFixture);
  Object.assign(r.data.attributes, {
    frDocNum: "2025-02910",
    commentStartDate: "2026-08-01T04:00:00Z",
    commentEndDate: "2026-09-21T03:59:59Z",
    postedDate: "2026-08-01T04:00:00Z",
    withdrawn: false,
    openForComment: true,
    withinCommentPeriod: true,
    modifyDate: "2026-09-14T09:00:14Z",
    docketId: "FAA-2025-5396",
  });
  mut(r);
  return r;
}
/** Fingerprint exactly as `review show` computes it: from the parsed observation (envelope + raw). */
const fpRegs = (raw: Regs) => decisionFingerprint(parseRegsObservation(raw));
const hashRegs = (raw: Regs) => parseRegsObservation(raw).payload_hash;

const base = regs();
const fp0 = fpRegs(base);

// ── format ───────────────────────────────────────────────────────────────────────────────────────────
assert(
  "FORMAT: fp1:<64 hex>",
  /^fp1:[0-9a-f]{64}$/.test(fp0) &&
    fingerprintVersion(fp0) === FINGERPRINT_VERSION,
  fp0,
);
assert(
  "FORMAT: a fingerprint is not the payload hash",
  fp0.slice(4) !== hashRegs(base),
);

// ── stable under volatile drift ─────────────────────────────────────────────────────────────────────
const drifted = regs(
  (r) => (r.data.attributes.modifyDate = "2026-09-15T09:00:36Z"),
);
assert(
  "STABLE: modifyDate drift changes the payload hash",
  hashRegs(drifted) !== hashRegs(base),
);
assert(
  "STABLE: modifyDate drift keeps the fingerprint",
  fpRegs(drifted) === fp0,
);
const linked = regs(
  (r) =>
    (r.links = { self: "https://regulations.gov/v4/documents/" + r.data.id }),
);
assert(
  "STABLE: an added envelope links.self keeps the fingerprint",
  fpRegs(linked) === fp0,
);
const both = regs((r) => {
  r.data.attributes.modifyDate = "2026-10-31T09:00:00Z";
  r.links = { self: "https://regulations.gov/v4/documents/x" };
});
assert(
  "STABLE: modifyDate + links.self together keep the fingerprint",
  fpRegs(both) === fp0,
);
const keyOrder = regs();
keyOrder.data.attributes = Object.fromEntries(
  Object.entries(keyOrder.data.attributes).reverse(),
);
assert("STABLE: key order does not matter", fpRegs(keyOrder) === fp0);

// ── sensitive to every decision-relevant change ─────────────────────────────────────────────────────
const changes: [string, (r: Regs) => void][] = [
  [
    "commentEndDate date",
    (r) => (r.data.attributes.commentEndDate = "2026-09-22T03:59:59Z"),
  ],
  [
    "commentEndDate time of day only",
    (r) => (r.data.attributes.commentEndDate = "2026-09-20T21:00:00Z"),
  ],
  ["commentEndDate to null", (r) => (r.data.attributes.commentEndDate = null)],
  [
    "commentStartDate",
    (r) => (r.data.attributes.commentStartDate = "2026-08-02T04:00:00Z"),
  ],
  [
    "commentStartDate time of day only",
    (r) => (r.data.attributes.commentStartDate = "2026-08-01T05:00:00Z"),
  ],
  [
    "postedDate",
    (r) => (r.data.attributes.postedDate = "2026-08-03T04:00:00Z"),
  ],
  ["withdrawn", (r) => (r.data.attributes.withdrawn = true)],
  ["openForComment", (r) => (r.data.attributes.openForComment = false)],
  [
    "withinCommentPeriod",
    (r) => (r.data.attributes.withinCommentPeriod = false),
  ],
  [
    "allowLateComments",
    (r) =>
      (r.data.attributes.allowLateComments =
        !r.data.attributes.allowLateComments),
  ],
  ["frDocNum (identity)", (r) => (r.data.attributes.frDocNum = "2025-02911")],
  [
    "docketId (identity)",
    (r) => (r.data.attributes.docketId = "FAA-2025-5397"),
  ],
  ["document id (identity)", (r) => (r.data.id = "FAA-2025-5396-0002")],
  [
    "objectId (identity)",
    (r) => (r.data.attributes.objectId = "0900006400000000"),
  ],
  [
    "title",
    (r) =>
      (r.data.attributes.title =
        String(r.data.attributes.title) + " ; Extension of Comment Period"),
  ],
  ["documentType", (r) => (r.data.attributes.documentType = "Rule")],
  [
    "docAbstract",
    (r) =>
      (r.data.attributes.docAbstract =
        "Comment period extended to October 21, 2026."),
  ],
  ["frVolNum (citation)", (r) => (r.data.attributes.frVolNum = "91 FR 12345")],
  [
    "fileFormats (posted content)",
    (r) =>
      (r.data.attributes.fileFormats = [
        {
          fileUrl: "https://downloads.regulations.gov/x/content.pdf",
          format: "pdf",
          size: 1,
        },
      ]),
  ],
  [
    "an unknown new attribute",
    (r) => (r.data.attributes.someFutureField = "x"),
  ],
  [
    "data.links.self (not exempt)",
    (r) =>
      ((r.data as Record<string, unknown>).links = {
        self: "https://api.regulations.gov/v4/documents/other",
      }),
  ],
];
for (const [name, mut] of changes)
  assert(`CHANGES: ${name}`, fpRegs(regs(mut)) !== fp0);
const driftAndDate = regs((r) => {
  r.data.attributes.modifyDate = "2026-10-01T00:00:00Z";
  r.data.attributes.commentEndDate = "2026-10-22T03:59:59Z";
});
assert(
  "CHANGES: a real date change still shows when modifyDate drifts with it",
  fpRegs(driftAndDate) !== fp0,
);

// Normalization boundaries (review round 1): evidenceRaw drops ONLY a string/null modifyDate and a
// string/null top-level links.self; anything else stays evidence.
const fpRaw = (raw: unknown) =>
  decisionFingerprint({
    source: "regulations_gov",
    payload_hash: "0".repeat(64),
    raw,
  });
const withAttr = (k: string, v: unknown) =>
  regs((r) => (r.data.attributes[k] = v));
assert(
  "BOUNDARY: a non-string modifyDate is kept (changes are seen)",
  fpRaw(withAttr("modifyDate", 1)) !== fpRaw(withAttr("modifyDate", 2)),
);
assert(
  "BOUNDARY: a non-string top-level links.self is kept",
  fpRaw({ ...base, links: { self: { href: "a" } } }) !==
    fpRaw({ ...base, links: { self: { href: "b" } } }),
);
assert(
  "BOUNDARY: other top-level links keys are kept",
  fpRaw({ ...base, links: { self: "x", related: "a" } }) !==
    fpRaw({ ...base, links: { self: "x", related: "b" } }),
);
assert(
  "BOUNDARY: non-object raw is fingerprinted whole",
  fpRaw("a") !== fpRaw("b") && fpRaw(null) !== fpRaw([]),
);
assert(
  "BOUNDARY: raw without data.attributes is fingerprinted whole",
  fpRaw({ data: { id: "x" }, m: 1 }) !== fpRaw({ data: { id: "x" }, m: 2 }),
);
assert(
  "BOUNDARY: non-object data.attributes is fingerprinted whole",
  fpRaw({ data: { attributes: "a" } }) !== fpRaw({ data: { attributes: "b" } }),
);
assert(
  "BOUNDARY: modifyDate outside data.attributes is NOT exempt",
  fpRaw({ ...base, modifyDate: "1" }) !== fpRaw({ ...base, modifyDate: "2" }),
);

// Envelope fields the parser derives: a parser that reads the same raw differently is a change too.
const obs = parseRegsObservation(base);
assert(
  "CHANGES: parser_version",
  decisionFingerprint({ ...obs, parser_version: "zz-9" }) !== fp0,
);
assert(
  "CHANGES: is_extension flag",
  decisionFingerprint({ ...obs, is_extension: !obs.is_extension }) !== fp0,
);
assert(
  "CHANGES: is_withdrawal flag",
  decisionFingerprint({ ...obs, is_withdrawal: !obs.is_withdrawal }) !== fp0,
);
assert(
  "CHANGES: ocd_id",
  decisionFingerprint({
    ...obs,
    ocd_id: "ocd-participation-window/federal/2025-99999",
  }) !== fp0,
);
assert(
  "CHANGES: source",
  decisionFingerprint({ ...obs, source: "federal_register" }) !== fp0,
);
assert(
  "CONSERVATIVE: a Regs row without its raw falls back to the payload hash",
  decisionFingerprint({
    source: "regulations_gov",
    payload_hash: obs.payload_hash,
  }) !==
    decisionFingerprint({
      source: "regulations_gov",
      payload_hash: hashRegs(drifted),
    }),
);

// ── FR / govinfo / linked amendments: no normalization ──────────────────────────────────────────────
const fr = parseFrObservation({
  ...frFixture,
  comments_close_on: "2026-09-15",
});
const frViews = parseFrObservation({
  ...frFixture,
  comments_close_on: "2026-09-15",
  page_views: { count: 99999, last_updated: "2026-10-31T00:00:00Z" },
});
assert(
  "FR: fingerprint moves with the payload hash (even page_views — the engine treats new FR as new evidence)",
  decisionFingerprint(fr) !== decisionFingerprint(frViews),
);
assert(
  "FR: same payload, same fingerprint",
  decisionFingerprint(fr) ===
    decisionFingerprint(
      parseFrObservation({ ...frFixture, comments_close_on: "2026-09-15" }),
    ),
);
const frMut: [string, Record<string, unknown>][] = [
  ["comments_close_on", { comments_close_on: "2026-09-16" }],
  [
    "dates text",
    { dates: "Comments must be received on or before September 30, 2026." },
  ],
  ["document_number (identity)", { document_number: "2025-02911" }],
  ["citation", { citation: "91 FR 99999" }],
  ["publication_date", { publication_date: "2025-02-11" }],
  ["docket_ids", { docket_ids: ["FAA-2025-9999"] }],
  ["title (withdrawal wording)", { title: "Withdrawal of proposed rule" }],
  ["action", { action: "Proposed rule; withdrawal." }],
];
for (const [name, m] of frMut)
  assert(
    `FR: CHANGES on ${name}`,
    decisionFingerprint(
      parseFrObservation({
        ...frFixture,
        comments_close_on: "2026-09-15",
        ...m,
      }),
    ) !== decisionFingerprint(fr),
  );
const am = (h: string, w = "ocd-participation-window/federal/2026-00001") =>
  decisionFingerprint({
    source: "govinfo",
    payload_hash: h,
    amendment_window: w,
  });
assert(
  "AMENDMENT: fingerprint moves with its payload hash",
  am("a".repeat(64)) !== am("b".repeat(64)),
);
assert(
  "AMENDMENT: and with the amendment window",
  am("a".repeat(64)) !==
    am("a".repeat(64), "ocd-participation-window/federal/2026-00002"),
);

// ── fingerprint set comparison ──────────────────────────────────────────────────────────────────────
const fA = fp0,
  fB = decisionFingerprint(fr);
assert("SET: order-insensitive", sameFingerprintSet([fA, fB], [fB, fA]));
assert(
  "SET: different size never matches",
  !sameFingerprintSet([fA, fB], [fA]),
);
assert("SET: empty never matches", !sameFingerprintSet([], []));
const fp2 = "fp2:" + fA.slice(4);
assert(
  "SET: a different version never matches, even with the same digest",
  !sameFingerprintSet([fA], [fp2]),
);
assert(
  "SET: mixed versions never match",
  !sameFingerprintSet([fA, fp2], [fA, fp2]),
);
assert(
  "SET: a bare payload hash is not a fingerprint",
  !sameFingerprintSet([fA.slice(4)], [fA.slice(4)]),
);

// ── ledger skip across the version boundary ─────────────────────────────────────────────────────────
const OCD = "ocd-participation-window/federal/2025-02910";
const POL = "v1.2@2026-10-28";
const h0 = [fr.payload_hash, hashRegs(base)];
const h1 = [fr.payload_hash, hashRegs(drifted)]; // next day: Regs modifyDate drifted
const fps0 = [decisionFingerprint(fr), fp0];
const fps1 = [decisionFingerprint(fr), fpRegs(drifted)];
const line = (o: Partial<LedgerLine>): LedgerLine => ({
  run: "2026-10-30T07:00:10-07:00",
  policy: POL,
  harness: null,
  ocd_id: OCD,
  hashes: h0,
  fingerprints: fps0,
  proposal: { kind: "pin_close" },
  ...o,
});
const now = new Date("2026-10-31T14:00:00Z");
const cur = { ocd_id: OCD, policy: POL, hashes: h1, fingerprints: fps1, now };

const d1 = ledgerSkip([line({})], cur);
assert(
  "SKIP: a pin line with fingerprints skips next day's modifyDate-only drift",
  d1.skip && d1.matchedBy === "fingerprints",
  JSON.stringify(d1),
);
const d2 = ledgerSkip([line({ fingerprints: undefined })], cur);
assert(
  "BOUNDARY: an old line without fingerprints does NOT skip on drift (re-checked once)",
  !d2.skip,
  JSON.stringify(d2),
);
const d3 = ledgerSkip([line({ fingerprints: undefined })], {
  ...cur,
  hashes: h0,
  fingerprints: fps0,
});
assert(
  "BOUNDARY: an old line still skips by identical payload hashes",
  d3.skip && d3.matchedBy === "hashes",
  JSON.stringify(d3),
);
const d4 = ledgerSkip(
  [line({ fingerprints: fps0.map((f) => "fp2:" + f.slice(4)) })],
  cur,
);
assert(
  "BOUNDARY: a line with another fingerprint version does not skip",
  !d4.skip,
  JSON.stringify(d4),
);
const d5 = ledgerSkip([line({ fingerprints: [h0[0]!, h0[1]!] })], cur);
assert(
  "BOUNDARY: payload hashes stored as fingerprints never match a fingerprint",
  !d5.skip,
  JSON.stringify(d5),
);
const d5b = ledgerSkip(
  [line({ hashes: fps1.map((f) => f.slice(4)), fingerprints: undefined })],
  cur,
);
assert(
  "BOUNDARY: fingerprint digests stored as hashes never match payload hashes",
  !d5b.skip,
  JSON.stringify(d5b),
);
const changedFps = [
  decisionFingerprint(fr),
  fpRegs(
    regs((r) => (r.data.attributes.commentEndDate = "2026-10-22T03:59:59Z")),
  ),
];
const d6 = ledgerSkip([line({})], { ...cur, fingerprints: changedFps });
assert(
  "SENSITIVE: a real date change never skips",
  !d6.skip,
  JSON.stringify(d6),
);
const d7 = ledgerSkip([line({ policy: "v1.1@2026-10-20" })], cur);
assert("POLICY: another policy version never skips", !d7.skip);
const d8 = ledgerSkip([line({ harness: "h-1" })], cur);
assert("HARNESS: harness lines never skip a scheduled run", !d8.skip);
const d9 = ledgerSkip([line({ proposal: { kind: "escalate" } })], cur);
assert("ESCALATE: skips within 7 days", d9.skip);
const d10 = ledgerSkip([line({ proposal: { kind: "escalate" } })], {
  ...cur,
  now: new Date("2026-11-07T14:00:01Z"),
});
assert("ESCALATE: re-inspected after 7 days", !d10.skip);
const d11 = ledgerSkip([line({ proposal: { kind: "skip" } })], cur);
assert("SKIP-KIND: a skip line never skips", !d11.skip);
const d12 = ledgerSkip(
  [line({ proposal: { kind: "confirm_withdrawn" } })],
  cur,
);
assert("WITHDRAWN: skips indefinitely", d12.skip);
const d13 = ledgerSkip(
  [
    line({ run: "2026-10-20T07:00:00-07:00", proposal: { kind: "escalate" } }),
    line({ run: "2026-10-30T07:00:00-07:00", proposal: { kind: "skip" } }),
  ],
  { ...cur, now: new Date("2026-10-31T14:00:00Z") },
);
assert(
  "ORDER: an old escalate past 7 days is not revived by a later skip line",
  !d13.skip,
  JSON.stringify(d13),
);

const d14 = ledgerSkip(
  [
    line({ run: "2026-10-20T07:00:00-07:00", proposal: { kind: "pin_close" } }),
    line({ run: "2026-10-20T07:00:00-07:00", proposal: { kind: "escalate" } }),
  ],
  { ...cur, now: new Date("2026-10-31T14:00:00Z") },
);
assert(
  "ORDER: equal run stamps — the later ledger line (escalate, 7+ days old) decides, not the earlier pin",
  !d14.skip,
  JSON.stringify(d14),
);
const d15 = ledgerSkip(
  [
    line({ run: "2026-10-30T07:00:00-07:00", proposal: { kind: "escalate" } }),
    line({ run: "2026-10-30T07:00:00-07:00", proposal: { kind: "pin_close" } }),
  ],
  { ...cur, now: new Date("2026-11-20T14:00:00Z") },
);
assert(
  "ORDER: equal run stamps — a later pin decides over an earlier escalate",
  d15.skip && d15.line.proposal.kind === "pin_close",
  JSON.stringify(d15),
);

console.log("review-fingerprint.test.ts");
console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} failure(s)`);
  process.exit(1);
}
console.log(`\nall ${out.length} passed`);
