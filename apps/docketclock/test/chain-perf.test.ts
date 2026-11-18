/**
 * chain-perf.test.ts — the chainCore performance memo (CitationMemo) must answer EXACTLY what
 * textCitesCitation answers. chainCore used to call textCitesCitation for every (original, amendment) pair,
 * a fresh regex over the whole GovInfo text each time; on ~8k windows that was minutes of blocking CPU on
 * the poller (2026-11-18). The memo scans each text once. This pins equivalence on adversarial texts:
 * overlapping tokens, line wraps, pin-cite ranges, digits touching either end, odd citation shapes (which
 * must fall back to the regex path), and a randomized sweep.
 */
import { CitationMemo, textCitesCitation } from "../src/reconcile/chain.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const texts = [
  "see 91 FR 57828 for details",
  "at\n91 FR 54729, published",
  "91 FR 57820, 57828 (pin cite range)",
  "191 FR 57828 and 91 FR 578280",
  "1 FR 2 FR 3 overlapping",
  "91  FR\t\t57828 tabs",
  "91 fr 57828 lowercase",
  "x91 FR 57828y",
  "",
  "no citations here",
  "091 FR 057828 leading zeros",
  "91 FR 57828.",
];
const citations = [
  "91 FR 57828",
  "91 FR 54729",
  "91 FR 57820",
  "91 FR 578280",
  "191 FR 57828",
  "2 FR 3",
  "1 FR 2",
  "091 FR 057828",
  "  91 FR 57828  ",
  "91 FR. 57828", // odd shape → regex fallback
  "91 Fed. Reg. 57828", // odd shape → regex fallback
];

{
  const memo = new CitationMemo();
  let mismatches = 0;
  const bad: string[] = [];
  for (const t of texts)
    for (const c of citations) {
      const want = textCitesCitation(t, c);
      const got = memo.cites(t, c);
      if (want !== got) {
        mismatches++;
        bad.push(
          `${JSON.stringify(t)} / ${JSON.stringify(c)}: want ${want} got ${got}`,
        );
      }
    }
  assert(
    "hand-picked texts × citations agree",
    mismatches === 0,
    bad.slice(0, 3).join(" | "),
  );
  assert(
    "null text → false (both)",
    !memo.cites(null, "91 FR 1") && !textCitesCitation(null, "91 FR 1"),
  );
}

{
  // Randomized sweep: texts built from digit runs, "FR", whitespace and punctuation.
  let seed = 7;
  const rnd = () =>
    (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  const tok = () => {
    const r = rnd();
    if (r < 0.35) return String(Math.floor(rnd() * 4));
    if (r < 0.6) return "FR";
    if (r < 0.75) return [" ", "  ", "\n", "\t"][Math.floor(rnd() * 4)]!;
    return [",", ".", "x", "-", "fr"][Math.floor(rnd() * 5)]!;
  };
  const memo = new CitationMemo();
  let checked = 0;
  let mismatches = 0;
  let positives = 0;
  for (let i = 0; i < 400; i++) {
    let t = "";
    for (let j = 0; j < 40; j++) t += tok() + (rnd() < 0.5 ? " " : "");
    for (let k = 0; k < 15; k++) {
      const c = `${Math.floor(rnd() * 4)} FR ${Math.floor(rnd() * 4)}`;
      checked++;
      const want = textCitesCitation(t, c);
      if (want) positives++;
      if (want !== memo.cites(t, c)) mismatches++;
    }
  }
  assert(
    `randomized sweep agrees (${checked} checks)`,
    mismatches === 0,
    String(mismatches),
  );
  assert(
    "randomized sweep is not vacuous (many true matches)",
    positives > 100,
    String(positives),
  );
}

console.log("chain-perf.test.ts");
console.log(out.join("\n"));
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
