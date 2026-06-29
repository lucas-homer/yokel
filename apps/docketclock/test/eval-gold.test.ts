/**
 * eval-gold.test.ts — PR-D1 (observability slice D): the gold-label corpus validator, proven with NO I/O
 * beyond a throwaway temp file. Pins what loadGold() must guarantee before D2's eval consumes it:
 *
 *   • A fully-labeled, well-formed file parses to typed entries.
 *   • A still-null / missing `gold` (i.e. an unlabeled template) is REJECTED — labeling is mandatory.
 *   • An `input` that violates the frozen contract is REJECTED.
 *   • Duplicate content_hashes are REJECTED (the hash is the corpus key / Langfuse item id).
 *   • Bad JSON and an empty array fail loudly.
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { writeFileSync, rmSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadGold } from "../src/adjudicator/eval-gold.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// Realistic 64-hex sha256 content_hashes (validated as PayloadHash) — match production corpus keys.
const HASH_A = "a".repeat(64);
const HASH_B = "b".repeat(64);

const dir = mkdtempSync(join(tmpdir(), "gold-"));
const path = join(dir, "g.json");
function write(value: unknown): void {
  writeFileSync(
    path,
    typeof value === "string" ? value : JSON.stringify(value),
  );
}
/** A valid chain entry; pass overrides to break a specific field. */
function entry(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    content_hash: HASH_A,
    gold: "reject",
    note: "different docket",
    model_verdict: { classification: "reject", rationale: "because" },
    input: {
      kind: "chain",
      rulebook_version: "rb",
      a_title: "Notice A",
      a_dates_text: null,
      a_publication_date: null,
      b_title: "Notice B",
      b_dates_text: null,
      b_publication_date: null,
      shared_docket: false,
      shared_rin: false,
      explicit_reference: false,
    },
    ...over,
  };
}

function rejects(name: string, value: unknown): void {
  write(value);
  let threw = false;
  try {
    loadGold(path);
  } catch {
    threw = true;
  }
  assert(name, threw);
}

try {
  // happy path
  write([entry(), entry({ content_hash: HASH_B, gold: "affirm" })]);
  const loaded = loadGold(path);
  assert(
    "valid fully-labeled file parses to typed entries",
    loaded.length === 2 && loaded[0]!.gold === "reject",
    `n=${loaded.length}`,
  );
  assert(
    "note defaults to empty string when omitted",
    (() => {
      write([entry({ note: undefined })]);
      return loadGold(path)[0]!.note === "";
    })(),
  );

  // rejections
  rejects("rejects null gold (unlabeled template)", [entry({ gold: null })]);
  rejects("rejects missing gold", [entry({ gold: undefined })]);
  rejects("rejects an out-of-enum gold value", [entry({ gold: "maybe" })]);
  rejects("rejects a non-64-hex content_hash (not a PayloadHash)", [
    entry({ content_hash: "abc123" }),
  ]);
  rejects("rejects an input that violates the contract", [
    entry({ input: { kind: "chain", rulebook_version: "rb" } }),
  ]);
  rejects("rejects duplicate content_hash", [entry(), entry()]);
  rejects("rejects an empty corpus", []);
  rejects("rejects non-array JSON", { not: "an array" });
  rejects("rejects malformed JSON", "{ not json");

  // file-not-found: loadGold throws its custom "could not read" message, never reaches parsing.
  {
    let threw = false;
    try {
      loadGold(join(dir, "does-not-exist.json"));
    } catch {
      threw = true;
    }
    assert("rejects a missing file with a clear read error", threw);
  }
} finally {
  rmSync(dir, { recursive: true, force: true });
}

console.log("\n=== eval-gold results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
