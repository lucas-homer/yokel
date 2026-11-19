/**
 * chain-index-equivalence.test.ts — chainCore's CandidateIndex must not change a single output byte.
 *
 * chainCore used to visit every (amendment, candidate) pair: 1,609 x 8,415 in production on 2026-11-18,
 * 48 s of CPU per cycle. It now visits only the candidates that share a docket with B, that B's
 * correction_of names, or whose citation appears in B's text. This file keeps the old full scan as a
 * reference (built from the same exported rule functions) and checks that both produce identical
 * confident and ambiguous sets on randomized corpora designed to hit every basis: shared dockets,
 * correction_of, doc-number references, shared RINs, unique and duplicated citations, odd citation shapes
 * (regex fallback), titles that corroborate a citation, missing dates, and closed or stale originals.
 */
import {
  RECENCY_WINDOW_MS,
  buildChainConflict,
  buildCitationIndex,
  chainCore,
  classify,
  CitationMemo,
  isAmendment,
  isKeywordFalsePositive,
  linkBasis,
  pubMs,
  type AmbiguousPair,
  type ChainCandidate,
  type ChainConflict,
} from "../src/reconcile/chain.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

/** The pre-index chainCore loop, verbatim in its rules: every candidate is visited for every amendment. */
function referenceChainCore(
  candidates: ChainCandidate[],
  now: Date,
): { confident: ChainConflict[]; ambiguous: AmbiguousPair[] } {
  const shareDocket = (a: ChainCandidate, b: ChainCandidate) => {
    if (a.docket_ids.length === 0 || b.docket_ids.length === 0) return false;
    const set = new Set(a.docket_ids);
    return b.docket_ids.some((d) => set.has(d));
  };
  const amendments = candidates.filter(
    (c) => isAmendment(c) && !isKeywordFalsePositive(c),
  );
  const citationIndex = buildCitationIndex(candidates);
  const memo = new CitationMemo();
  const confident: ChainConflict[] = [];
  const ambiguous: AmbiguousPair[] = [];
  for (const b of amendments) {
    const bMs = pubMs(b.publication_date);
    if (bMs === null) continue;
    const targets: ChainCandidate[] = [];
    const ambiguousForB: ChainCandidate[] = [];
    for (const a of candidates) {
      if (a.ocd_id === b.ocd_id) continue;
      if (a.fr_observation_id === b.fr_observation_id) continue;
      const aMs = pubMs(a.publication_date);
      if (aMs === null || !(bMs > aMs)) continue;
      let relevant = a.status === "open";
      if (!relevant && a.resolved_close_utc) {
        const closeMs = new Date(a.resolved_close_utc).getTime();
        if (!Number.isNaN(closeMs) && closeMs >= bMs - RECENCY_WINDOW_MS)
          relevant = true;
      }
      if (!relevant) continue;
      const docket = shareDocket(a, b);
      if (linkBasis(a, b, citationIndex, memo) === null) {
        if (docket) ambiguousForB.push(a);
        continue;
      }
      targets.push(a);
    }
    const multiTarget = targets.length > 1;
    for (const a of targets)
      confident.push(buildChainConflict(a, b, classify(b, multiTarget), now));
    for (const a of ambiguousForB) ambiguous.push({ a, b });
  }
  // Same final ordering as chainCore. compareConflict is internal, so compare on a canonical sort here
  // and let the byte comparison below check chainCore's own ordering against it.
  const key = (c: ChainConflict) =>
    [c.ocd_id, c.ocd_id_b, c.observation_a_id, c.observation_b_id].join("|");
  confident.sort((x, y) => (key(x) < key(y) ? -1 : key(x) > key(y) ? 1 : 0));
  ambiguous.sort(
    (x, y) =>
      x.a.ocd_id.localeCompare(y.a.ocd_id) ||
      x.b.ocd_id.localeCompare(y.b.ocd_id) ||
      x.a.fr_observation_id.localeCompare(y.a.fr_observation_id) ||
      x.b.fr_observation_id.localeCompare(y.b.fr_observation_id),
  );
  return { confident, ambiguous };
}

let seed = 20261118;
const rnd = () =>
  (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const pick = <T>(xs: readonly T[]): T => xs[Math.floor(rnd() * xs.length)]!;
const some = <T>(xs: readonly T[], p: number): T[] =>
  xs.filter(() => rnd() < p);

function corpus(
  n: number,
  amendmentRate: number,
  sparse = false,
): ChainCandidate[] {
  const dockets = Array.from(
    { length: Math.max(3, n / 6) },
    (_, i) => `EPA-HQ-${i}`,
  );
  const rins = ["2060-AA01", "2060-AA02", "1018-BF33", ""];
  const docNum = (i: number) => `2026-${String(10000 + i)}`;
  // Citations: mostly plain shape, some duplicated (non-unique → basis off), some odd shapes (fallback).
  const citation = (i: number) => {
    const r = rnd();
    if (r < 0.1) return null;
    if (r < 0.2) return "91 FR 50000"; // shared by many → never unique
    if (r < 0.25 && !sparse) return `91 Fed. Reg. ${60000 + i}`; // odd shape → regex path (none in prod)
    if (r < 0.3) return `  91  FR  ${60000 + i} `; // plain shape with stray whitespace
    return `91 FR ${60000 + i}`;
  };
  const titles = [
    "Air Plan Approval",
    "Endangered Species Listing",
    "Public Land Order No. 7963; Withdrawal",
    "",
  ];
  const day = () =>
    pick([
      `2026-0${1 + Math.floor(rnd() * 9)}-1${Math.floor(rnd() * 9)}`,
      "2026-02-30", // rolled-over date → null
      null,
    ]);
  const cands: ChainCandidate[] = [];
  for (let i = 0; i < n; i++) {
    const amend = rnd() < amendmentRate;
    const cit = citation(i);
    const t = pick(titles);
    cands.push({
      ocd_id: `ocd-participation-window/federal/w${i % Math.max(1, n - 3)}`, // a few shared ocd_ids
      fr_observation_id: `obs-${i}`,
      fr_document_number: rnd() < 0.95 ? docNum(i) : null,
      // Dense: a few dockets shared by many candidates (stresses the docket bases). Sparse: production's
      // shape (2026-11-18: 8,415 candidates, the largest docket has 42 docs, ~1,100 amendment pairs share one).
      docket_ids: sparse
        ? rnd() < 0.8
          ? [`D-${Math.floor(rnd() * n)}`]
          : []
        : some(dockets.slice(0, 6), 0.15).concat(
            rnd() < 0.7 ? [pick(dockets)] : [],
          ),
      rin: null,
      rins: some(rins, 0.25),
      is_extension: amend && rnd() < 0.5,
      is_correction: amend && rnd() < 0.4,
      is_withdrawal: amend && rnd() < 0.2,
      is_reopening: amend && rnd() < 0.2,
      title: t || null,
      publication_date: day(),
      govinfo_url: rnd() < 0.5 ? `https://www.govinfo.gov/x/${i}` : null,
      dates_text: null,
      status: pick(["open", "open", "closed", "unknown"]),
      resolved_close_utc:
        rnd() < 0.7
          ? `2026-0${1 + Math.floor(rnd() * 9)}-15T04:59:59.000Z`
          : null,
      citation: cit,
      correction_of: null,
      corrections: [],
      govinfo_text: null,
    });
  }
  // Second pass: amendments reference earlier docs by every channel.
  for (const b of cands) {
    if (!isAmendment(b)) continue;
    const ref = () => pick(cands);
    if (rnd() < 0.3) b.correction_of = ref().fr_document_number;
    const bits: string[] = [];
    for (let k = 0; k < 3; k++) {
      const a = ref();
      const r = rnd();
      if (r < 0.3 && a.fr_document_number)
        bits.push(`see FR Doc. ${a.fr_document_number.replace("-", "- ")}`);
      else if (r < 0.7 && a.citation)
        bits.push(`published at\n${a.citation.trim()},`);
      else bits.push("no reference here");
    }
    if (rnd() < 0.5) b.govinfo_text = bits.join(" ");
    else b.dates_text = bits.join(" ");
    if (rnd() < 0.3) {
      const a = ref();
      b.title = `${a.title ?? ""} extension of comment period`;
    }
  }
  return cands;
}

const now = new Date("2026-11-18T23:00:00.000Z");
let totalConfident = 0;
let totalAmbiguous = 0;
let mismatched = 0;
const bad: string[] = [];
for (let round = 0; round < 60; round++) {
  const n = 20 + Math.floor(rnd() * 180);
  const cands = corpus(n, 0.15 + rnd() * 0.4);
  const want = referenceChainCore(cands, now);
  const got = chainCore(cands, now);
  totalConfident += want.confident.length;
  totalAmbiguous += want.ambiguous.length;
  // chainCore's sort is the source of truth for order; compare as canonical multisets of serialized rows.
  const ser = (xs: unknown[]) => xs.map((x) => JSON.stringify(x)).sort();
  const c1 = JSON.stringify(ser(want.confident));
  const c2 = JSON.stringify(ser(got.confident));
  const a1 = JSON.stringify(
    want.ambiguous.map((p) => [p.a.fr_observation_id, p.b.fr_observation_id]),
  );
  const a2 = JSON.stringify(
    got.ambiguous.map((p) => [p.a.fr_observation_id, p.b.fr_observation_id]),
  );
  if (c1 !== c2 || a1 !== a2) {
    mismatched++;
    if (bad.length < 3)
      bad.push(
        `round ${round} n=${n}: confident ${want.confident.length}/${got.confident.length}, ambiguous ${want.ambiguous.length}/${got.ambiguous.length}`,
      );
  }
}
assert(
  "indexed chainCore == full-scan reference on 60 randomized corpora",
  mismatched === 0,
  bad.join(" | "),
);
assert(
  "corpora are not vacuous (many confident links)",
  totalConfident > 200,
  String(totalConfident),
);
assert(
  "corpora are not vacuous (many ambiguous pairs)",
  totalAmbiguous > 200,
  String(totalAmbiguous),
);

{
  // Order: chainCore's own output order must be identical to the reference's (both sort the same keys).
  const cands = corpus(300, 0.3);
  const want = referenceChainCore(cands, now);
  const got = chainCore(cands, now);
  const ids = (xs: ChainConflict[]) =>
    xs.map(
      (c) =>
        `${c.ocd_id}|${c.ocd_id_b}|${c.observation_a_id}|${c.observation_b_id}`,
    );
  assert(
    "confident output order matches",
    JSON.stringify(ids(want.confident)) === JSON.stringify(ids(got.confident)),
  );
}

{
  // Scale: production shape (8,415 candidates, ~1,600 amendments, sparse dockets). The index must make
  // this fast; the full scan visits ~13M pairs.
  const cands = corpus(8415, 0.19, true);
  const t0 = performance.now();
  const got = chainCore(cands, now);
  const ms = performance.now() - t0;
  const t1 = performance.now();
  const want = referenceChainCore(cands, now);
  const refMs = performance.now() - t1;
  assert(
    "production-size corpus: same output",
    want.confident.length === got.confident.length &&
      want.ambiguous.length === got.ambiguous.length,
    `${want.confident.length}/${got.confident.length} confident, ${want.ambiguous.length}/${got.ambiguous.length} ambiguous`,
  );
  assert(
    `production-size corpus: indexed is at least 10x faster (indexed ${Math.round(ms)} ms, full scan ${Math.round(refMs)} ms)`,
    ms * 10 < refMs,
  );
}

console.log("chain-index-equivalence.test.ts");
console.log(out.join("\n"));
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
