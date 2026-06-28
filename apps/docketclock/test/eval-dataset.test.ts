/**
 * eval-dataset.test.ts — PR-C3 (observability slice C): the PURE selection logic behind the Langfuse
 * eval-dataset seed, proven with NO Postgres and NO Langfuse. Pins the load-bearing invariants that the
 * Slice D labeling corpus depends on:
 *
 *   • Dedup by content_hash — one item per distinct input.
 *   • null-skip NEVER shadows a deciding verdict for the same hash (in either ordering).
 *   • Cap per (kind × classification) stratum is never exceeded.
 *   • Stability — appending NEWER rows at the tail can't change the selection once a stratum is full
 *     (this is what makes a re-run after cache growth a true no-op).
 *   • KINDS / CLASSES are DERIVED from @yokel/contracts, so the grid covers every kind/classification —
 *     no silent stratum drop.
 *   • Malformed rows are skipped+counted, never thrown.
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit. Needs no DB.
 */
import {
  selectDatasetItems,
  KINDS,
  CLASSES,
  type AdjudicationRow,
} from "../src/adjudicator/eval-dataset.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const RB = "rulebox-2026-06-18";
const GEMINI = `gemini:gemini-2.5-flash@${RB}`;
const NULLID = `null:abstain@${RB}`;

/** A valid chain row with the given hash / adjudicator / classification. */
function chainRow(
  hash: string,
  adjudicatorId: string,
  classification: string,
): AdjudicationRow {
  return {
    content_hash: hash,
    adjudicator_id: adjudicatorId,
    created_at: new Date(0),
    input: {
      kind: "chain",
      rulebook_version: RB,
      a_title: "Notice A",
      a_dates_text: null,
      a_publication_date: null,
      b_title: "Notice B",
      b_dates_text: null,
      b_publication_date: null,
      shared_docket: true,
      shared_rin: false,
      explicit_reference: false,
    },
    verdict: { classification, rationale: "because" },
  };
}

/** A valid notice row. */
function noticeRow(
  hash: string,
  adjudicatorId: string,
  classification: string,
): AdjudicationRow {
  return {
    content_hash: hash,
    adjudicator_id: adjudicatorId,
    created_at: new Date(0),
    input: {
      kind: "notice",
      rulebook_version: RB,
      flag_key: "withdrawal",
      text: "Withdrawal of Land from Mineral Entry; Notice of Realty Action",
    },
    verdict: { classification, rationale: "because" },
  };
}

const opts = { cap: 25, includeNull: false };

// 1. KINDS / CLASSES are derived from the contract (not hardcoded).
assert(
  "KINDS derived from contract = [notice, chain]",
  JSON.stringify([...KINDS].sort()) === JSON.stringify(["chain", "notice"]),
  JSON.stringify(KINDS),
);
assert(
  "CLASSES derived from contract = [affirm, reject, uncertain]",
  JSON.stringify([...CLASSES].sort()) ===
    JSON.stringify(["affirm", "reject", "uncertain"]),
  JSON.stringify(CLASSES),
);
assert(
  "grid covers every kind × classification cell",
  selectDatasetItems([], opts).grid.length === KINDS.length * CLASSES.length,
);

// 2. Dedup by content_hash — two rows, same hash → one item.
{
  const r = selectDatasetItems(
    [chainRow("h1", GEMINI, "affirm"), chainRow("h1", GEMINI, "affirm")],
    opts,
  );
  assert("dedup by content_hash keeps one", r.selected.length === 1);
}

// 3. null-skip never shadows a deciding verdict — BOTH orderings.
{
  // null appears AFTER the deciding verdict (null is "newer").
  const a = selectDatasetItems(
    [chainRow("h2", GEMINI, "affirm"), chainRow("h2", NULLID, "uncertain")],
    opts,
  );
  assert(
    "null after deciding: keeps the deciding verdict",
    a.selected.length === 1 && a.selected[0]!.classification === "affirm",
    a.selected[0]?.classification,
  );
  // null appears BEFORE the deciding verdict (null is "older").
  const b = selectDatasetItems(
    [chainRow("h3", NULLID, "uncertain"), chainRow("h3", GEMINI, "reject")],
    opts,
  );
  assert(
    "null before deciding: still keeps the deciding verdict (not the abstention)",
    b.selected.length === 1 && b.selected[0]!.classification === "reject",
    b.selected[0]?.classification,
  );
  assert(
    "null-only hash is dropped, counted as skippedNull",
    (() => {
      const c = selectDatasetItems([chainRow("h4", NULLID, "uncertain")], opts);
      return c.selected.length === 0 && c.skippedNull === 1;
    })(),
  );
}

// 4. Cap per stratum is never exceeded.
{
  const rows = Array.from({ length: 5 }, (_, i) =>
    chainRow(`cap${i}`, GEMINI, "affirm"),
  );
  const r = selectDatasetItems(rows, { cap: 2, includeNull: false });
  const affirmCell = r.grid.find(
    (g) => g.kind === "chain" && g.classification === "affirm",
  );
  assert(
    "stratum never exceeds cap",
    r.selected.length === 2 && affirmCell?.count === 2,
    `selected=${r.selected.length} cell=${affirmCell?.count}`,
  );
}

// 5. Stability — appending NEWER rows at the tail can't change a full stratum's selection.
{
  const base = [
    chainRow("s1", GEMINI, "affirm"),
    chainRow("s2", GEMINI, "affirm"),
  ];
  const grown = [
    ...base,
    chainRow("s3", GEMINI, "affirm"),
    chainRow("s4", GEMINI, "affirm"),
  ];
  const o = { cap: 2, includeNull: false };
  const before = selectDatasetItems(base, o)
    .selected.map((c) => c.contentHash)
    .sort();
  const after = selectDatasetItems(grown, o)
    .selected.map((c) => c.contentHash)
    .sort();
  assert(
    "selection is stable when newer rows are appended (re-run is a no-op)",
    JSON.stringify(before) === JSON.stringify(after),
    `${JSON.stringify(before)} vs ${JSON.stringify(after)}`,
  );
}

// 6. New strata (notice / uncertain) are NOT dropped — proves derived grid coverage end-to-end.
{
  const r = selectDatasetItems(
    [noticeRow("n1", GEMINI, "uncertain"), chainRow("c1", GEMINI, "reject")],
    opts,
  );
  const noticeUncertain = r.grid.find(
    (g) => g.kind === "notice" && g.classification === "uncertain",
  );
  assert(
    "notice/uncertain stratum is selected, not silently dropped",
    r.selected.length === 2 && noticeUncertain?.count === 1,
    `selected=${r.selected.length} cell=${noticeUncertain?.count}`,
  );
}

// 7. Malformed rows are skipped + counted, never thrown.
{
  let threw = false;
  let r;
  try {
    r = selectDatasetItems(
      [
        { ...chainRow("bad", GEMINI, "affirm"), input: { kind: "chain" } }, // missing required chain fields
        chainRow("good", GEMINI, "affirm"),
      ],
      opts,
    );
  } catch {
    threw = true;
  }
  assert(
    "malformed row skipped+counted, valid row still selected, no throw",
    !threw &&
      r !== undefined &&
      r.skippedInvalid === 1 &&
      r.selected.length === 1 &&
      r.selected[0]!.contentHash === "good",
  );
}

// 8. includeNull: true keeps abstentions.
{
  const r = selectDatasetItems([chainRow("k1", NULLID, "uncertain")], {
    cap: 25,
    includeNull: true,
  });
  assert(
    "includeNull keeps null:* abstentions",
    r.selected.length === 1 && r.skippedNull === 0,
  );
}

console.log("\n=== eval-dataset results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
