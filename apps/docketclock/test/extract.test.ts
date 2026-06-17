/**
 * extract.test.ts — defensive structured-field extraction from an Observation's `raw` payload.
 *
 * Focused regression for the FR RIN field bug (#31 chain pass): FR returns the RIN in the PLURAL ARRAY
 * `regulation_id_numbers` (the singular `regulation_id_number` is `null` on every live document). The
 * extractor must read the plural array and expose BOTH the single `rin` (first element, for the
 * ParticipationWindow.rin contract column — lossy-by-design) AND the full `rins` array (for the chain
 * pass's RIN-intersection corroboration).
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { extractFr } from "../src/reconcile/extract.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// 1. The live FR shape: regulation_id_number=null (always), regulation_id_numbers=[..] (the real data).
{
  const fr = extractFr({
    document_number: "2025-00001",
    regulation_id_number: null,
    regulation_id_numbers: ["0412-AB19", "0414-AA00"],
  });
  assert(
    "1 plural array present: rin = first element",
    fr.rin === "0412-AB19",
    String(fr.rin),
  );
  assert(
    "1 plural array present: rins = full array",
    JSON.stringify(fr.rins) === JSON.stringify(["0412-AB19", "0414-AA00"]),
    JSON.stringify(fr.rins),
  );
}

// 2. Empty array (the typical Notice/amendment shape) → rin null, rins [].
{
  const fr = extractFr({
    document_number: "2025-00002",
    regulation_id_number: null,
    regulation_id_numbers: [],
  });
  assert("2 empty array: rin null", fr.rin === null, String(fr.rin));
  assert(
    "2 empty array: rins []",
    Array.isArray(fr.rins) && fr.rins.length === 0,
    JSON.stringify(fr.rins),
  );
}

// 3. Missing field entirely → rin null, rins [].
{
  const fr = extractFr({ document_number: "2025-00003" });
  assert("3 missing field: rin null", fr.rin === null, String(fr.rin));
  assert(
    "3 missing field: rins []",
    Array.isArray(fr.rins) && fr.rins.length === 0,
    JSON.stringify(fr.rins),
  );
}

// 4. Null raw (the defensive !doc branch) → rin null, rins [].
{
  const fr = extractFr(null);
  assert(
    "4 null raw: rin null, rins []",
    fr.rin === null && Array.isArray(fr.rins) && fr.rins.length === 0,
    `${fr.rin} / ${JSON.stringify(fr.rins)}`,
  );
}

// 5. Blank / whitespace entries (Copilot #35) → trimmed + dropped at the source: rins carries only real
// non-empty RINs and `rin` is a real RIN or null, NEVER "" — so no junk leaks into the contract column
// and shareRin can't corroborate on a whitespace value.
{
  const fr = extractFr({
    document_number: "2025-00005",
    regulation_id_numbers: ["", "  ", " 0412-AB19 ", "0414-AA00"],
  });
  assert(
    "5 blank entries dropped + trimmed: rins = real RINs only",
    JSON.stringify(fr.rins) === JSON.stringify(["0412-AB19", "0414-AA00"]),
    JSON.stringify(fr.rins),
  );
  assert(
    "5 leading blank does not make rin '': rin = first REAL rin",
    fr.rin === "0412-AB19",
    String(fr.rin),
  );
  // All-blank array → rin null (not "").
  const allBlank = extractFr({
    document_number: "2025-00006",
    regulation_id_numbers: ["", "   "],
  });
  assert(
    "5 all-blank array: rin null, rins []",
    allBlank.rin === null && allBlank.rins.length === 0,
    `${allBlank.rin} / ${JSON.stringify(allBlank.rins)}`,
  );
}

console.log("\n=== extract results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
