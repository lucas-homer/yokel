/**
 * accuracy-misses-adversary.test.ts — adversarial integrity guard over the committed accuracy-miss
 * replay fixtures (slice V, PR-V2 adversary round).
 *
 * The official replay (test/accuracy-misses.test.ts) checks only a SHALLOW shape — `input` +
 * `expected` present, publishedCloseUtc a string, observationsSinceClose an array — before feeding
 * the fixture to computeVerdict. That leaves silent-degradation room this file closes:
 *
 *   • `input.lapsed` missing/undefined is treated as FALSE by computeVerdict (`if (input.lapsed)`),
 *     so a fixture that lost its `lapsed` key in a hand-edit replays a boolean verdict where the
 *     truth may have been an unverified_lapsed abstention — the exact fake-certainty direction the
 *     product exists to prevent. Here: `lapsed` MUST be a boolean.
 *   • An observation missing its is_* flags (undefined → falsy) silently WEAKENS convictions:
 *     a withdrawal observation whose `is_withdrawal` key was dropped stops contradicting the close.
 *     Here: all four flags MUST be present booleans on every observation.
 *   • The exporter's contract is that every observation was fetched STRICTLY after the published
 *     close (mirroring evaluateWatch's `o.fetched_at > publishedCloseUtc`). A fixture violating
 *     that replays a chain production could never assemble. Here: enforced per observation.
 *   • A miss's evidence must be REPLAYABLE: every id in expected.contradicting_observation_ids
 *     must exist in the fixture's own observation set, and be sorted (computeVerdict sorts, so an
 *     unsorted gold can never match — catch it as a fixture bug, not a mysterious replay diff).
 *   • zod's `.default([])` on contradicting_observation_ids means a TYPO'D key in a hand-edited
 *     gold block still safeParses. Here: `expected` must carry exactly the three verdict keys.
 *
 * Plus pure demonstrations pinning the degradation behaviors themselves, so if computeVerdict ever
 * starts throwing on malformed input instead (fine — better), this file says so explicitly.
 *
 * No fixtures committed is a PASS for the fixture section (same rule as the official replay); the
 * demonstration section always runs.
 */
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { computeVerdict, type VerdictInput } from "../src/verify/verdict.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const FIXTURE_DIR = fileURLToPath(
  new URL("../eval/accuracy-misses/", import.meta.url),
);

const files = existsSync(FIXTURE_DIR)
  ? readdirSync(FIXTURE_DIR)
      .filter((f) => f.endsWith(".json"))
      .sort()
  : [];

out.push(`fixture integrity (adversary): ${files.length} committed fixture(s)`);

const parseable = (s: unknown): boolean =>
  typeof s === "string" && Number.isFinite(Date.parse(s));

for (const file of files) {
  let fixture: {
    input: VerdictInput;
    expected: Record<string, unknown>;
  };
  try {
    fixture = JSON.parse(readFileSync(resolve(FIXTURE_DIR, file), "utf8"));
  } catch (err) {
    assert(`${file}: parses as JSON`, false, String(err));
    continue;
  }
  const inp = fixture.input;
  if (inp === undefined || fixture.expected === undefined) {
    // The official replay already fails this fixture; don't double-count here.
    out.push(
      `  SKIP  ${file}: missing input/expected (official replay owns this failure)`,
    );
    continue;
  }

  assert(
    `${file}: input.lapsed is a boolean (missing lapsed silently replays as false)`,
    typeof inp.lapsed === "boolean",
    `got ${typeof inp.lapsed}`,
  );
  assert(
    `${file}: publishedCloseUtc parses to a real instant`,
    parseable(inp.publishedCloseUtc),
  );
  assert(
    `${file}: currentCloseUtc is null or a parseable instant`,
    inp.currentCloseUtc === null || parseable(inp.currentCloseUtc),
  );
  assert(
    `${file}: currentStatus is a non-empty string`,
    typeof inp.currentStatus === "string" && inp.currentStatus.length > 0,
  );

  const obsOk = Array.isArray(inp.observationsSinceClose);
  assert(`${file}: observationsSinceClose is an array`, obsOk);
  if (obsOk) {
    const closeMs = Date.parse(inp.publishedCloseUtc);
    const ids = new Set<string>();
    let flagsOk = true;
    let strictlyAfter = true;
    let idsOk = true;
    for (const o of inp.observationsSinceClose) {
      if (
        typeof o.is_extension !== "boolean" ||
        typeof o.is_correction !== "boolean" ||
        typeof o.is_withdrawal !== "boolean" ||
        typeof o.is_reopening !== "boolean"
      )
        flagsOk = false;
      if (!parseable(o.fetched_at) || Date.parse(o.fetched_at) <= closeMs)
        strictlyAfter = false;
      if (typeof o.observation_id !== "string" || o.observation_id.length === 0)
        idsOk = false;
      ids.add(o.observation_id);
    }
    assert(
      `${file}: every observation carries all four is_* flags as booleans (a dropped flag silently un-convicts)`,
      flagsOk,
    );
    assert(
      `${file}: every observation fetched STRICTLY after the published close (the evaluateWatch contract)`,
      strictlyAfter,
    );
    assert(`${file}: observation ids are non-empty strings`, idsOk);
    assert(
      `${file}: observation ids are unique`,
      ids.size === inp.observationsSinceClose.length,
    );

    const contra = fixture.expected["contradicting_observation_ids"];
    const contraArr = Array.isArray(contra) ? (contra as string[]) : null;
    assert(
      `${file}: expected.contradicting_observation_ids is an array (zod default([]) must not paper over a typo'd key)`,
      contraArr !== null,
    );
    if (contraArr !== null) {
      assert(
        `${file}: every contradicting id cites an observation IN the fixture (replayable evidence)`,
        contraArr.every((id) => ids.has(id)),
      );
      assert(
        `${file}: contradicting ids are sorted (computeVerdict sorts; unsorted gold can never match)`,
        JSON.stringify(contraArr) === JSON.stringify([...contraArr].sort()),
      );
    }
  }

  assert(
    `${file}: expected carries exactly the three verdict keys`,
    JSON.stringify(Object.keys(fixture.expected).sort()) ===
      JSON.stringify(["basis", "contradicting_observation_ids", "was_correct"]),
    `got [${Object.keys(fixture.expected).sort().join(", ")}]`,
  );
}

// ── demonstrations: the degradation behaviors the guards above exist for ──────────────────────────
out.push("degradation demonstrations (why the guards above are load-bearing):");

const base: VerdictInput = {
  publishedCloseUtc: "2026-07-03T03:59:59.000Z",
  currentCloseUtc: "2026-07-03T03:59:59.000Z",
  currentStatus: "closed",
  observationsSinceClose: [
    {
      observation_id: "obs-w",
      fetched_at: "2026-07-04T00:00:00.000Z",
      is_extension: false,
      is_correction: false,
      is_withdrawal: true,
      is_reopening: false,
    },
  ],
  lapsed: true, // the truth for this hypothetical window: horizon lapsed, verdict must abstain
};

// 1. Deleting `lapsed` flips an abstention into a confident boolean verdict — silently.
const noLapsed = { ...base } as Record<string, unknown>;
delete noLapsed["lapsed"];
const degraded = computeVerdict(noLapsed as unknown as VerdictInput);
assert(
  "deleting input.lapsed silently converts an abstention into a boolean verdict (why lapsed must be type-checked)",
  degraded.basis !== "unverified_lapsed" && degraded.was_correct !== null,
  `got basis=${degraded.basis}`,
);

// 2. Dropping is_withdrawal un-convicts a revealed withdrawal — silently.
const noFlag = {
  ...base,
  lapsed: false,
  observationsSinceClose: [
    (() => {
      const o = {
        ...base.observationsSinceClose[0],
      } as Record<string, unknown>;
      delete o["is_withdrawal"];
      return o;
    })(),
  ],
} as unknown as VerdictInput;
const unconvicted = computeVerdict(noFlag);
assert(
  "dropping an observation's is_withdrawal flag silently un-convicts the miss (why flags must be present booleans)",
  unconvicted.was_correct === true,
  `got ${JSON.stringify(unconvicted)}`,
);
// …and the intact fixture convicts, proving the delta is the dropped key alone.
const intact = computeVerdict({ ...base, lapsed: false });
assert(
  "the intact withdrawal observation convicts (control for the demonstration above)",
  intact.was_correct === false &&
    intact.basis === "late_amendment" &&
    JSON.stringify(intact.contradicting_observation_ids) ===
      JSON.stringify(["obs-w"]),
  `got ${JSON.stringify(intact)}`,
);

console.log(out.join("\n"));
if (failures > 0) {
  console.error(`\n${failures} FAILURE(S)`);
  process.exit(1);
}
console.log("\nALL EXPECTATIONS MET");
