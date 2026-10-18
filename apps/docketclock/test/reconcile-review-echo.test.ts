/**
 * reconcile-review-echo.test.ts — the reconcile-v2.2 "portal close echo" rule (ADR 0014; PR-A1).
 *
 * The measured class: an operator pins a close date that EQUALS the Eastern calendar date of the
 * reviewed Regulations.gov commentEndDate. Once that instant passes, the portal records its own
 * announced close by flipping openForComment / withinCommentPeriod true->false and nothing else.
 * Under v2.1 that flip counted as new evidence, the pin was dropped, and the window resurfaced in
 * the review queue as a CLOSED conflicting item (7 of 26 closed queue items at export time). v2.2
 * treats that chain as the reviewed evidence when all five clauses in
 * `portalCloseEchoPreservesPin` (src/reconcile/review-evidence.ts) hold.
 *
 * Proves, pure-engine (no DB):
 *   • POSITIVE CLAUSES — either flag alone, both in one observation, both in successive
 *     observations; DST edges (pinned 2026-11-01 / 2026-03-08: flip 1 s after the DST-correct
 *     instant is honored, 1 s before is not); an offset-form commentEndDate; a baseline already
 *     false with identical refreshes (the plain v2.1 path); a repin after an invalidating change.
 *   • LIVE REPLAY — all 7 full histories from test/fixtures/review-echo-histories.json at the export
 *     instant reconcile to HIGH / closed / no ConflictRecord / fr_regs_date_mismatch + human_resolved /
 *     resolved_close_utc == frCloseDateToUtcInstant(pinned) == the live v2.1 row's close (so the
 *     projection sweep retires the conflict without a version bump).
 *   • TRUNCATED REPLAYS — histories cut before the first flip and exactly at the first flip.
 *   • DETERMINISM — order reversal deep-equal, two runs deep-equal, inputs not mutated.
 *
 * Harness style: assert/out/failures tally, process.exit (as reconcile-human-review.test.ts).
 */
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { HumanReviewVerdict, type Observation } from "@yokel/contracts";
import { reconcile } from "../src/reconcile/reconcile.js";
import { frCloseDateToUtcInstant } from "../src/reconcile/eastern-date.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// ── synthetic chain builders (freshness-test conventions) ────────────────────────────────────────────
const OCD = "ocd-participation-window/federal/2026-08826";
const NOW = new Date("2026-10-18T06:13:26Z");
function source(
  src: Observation["source"],
  raw: unknown,
  fetched_at: string,
  id?: string,
): Observation {
  return {
    observation_id: id ?? `${src}-${fetched_at}`,
    ocd_id: OCD,
    source: src,
    fr_document_number: "2026-08826",
    regs_document_id: src === "regulations_gov" ? "FDA-2026-N-2886-0001" : null,
    regs_object_id: null,
    payload_hash: createHash("sha256")
      .update(JSON.stringify(raw))
      .digest("hex"),
    fetched_at,
    parser_version: "test-v1",
    raw_dates_text: null,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
  };
}
type RegsRaw = {
  data: { id: string; attributes: Record<string, unknown> };
  links?: Record<string, unknown>;
};
function regsRaw(attrs: Record<string, unknown>): RegsRaw {
  return {
    data: {
      id: "FDA-2026-N-2886-0001",
      attributes: {
        commentEndDate: "2026-10-03T03:59:59Z", // Eastern 2026-10-02
        openForComment: true,
        withinCommentPeriod: true,
        withdrawn: false,
        allowLateComments: false,
        title: "Modification of Certain Terminology in Title 21",
        docketId: "FDA-2026-N-2886",
        modifyDate: "2026-09-18T00:00:00Z",
        ...attrs,
      },
    },
  };
}
/** A later refresh of `base` whose only metadata change is modifyDate, plus the given attr overrides. */
function refresh(
  base: RegsRaw,
  fetched_at: string,
  attrs: Record<string, unknown> = {},
): Observation {
  const raw = structuredClone(base);
  raw.data.attributes.modifyDate = fetched_at;
  Object.assign(raw.data.attributes, attrs);
  return source("regulations_gov", raw, fetched_at);
}
function frAt(fetched_at: string): Observation {
  return source(
    "federal_register",
    {
      document_number: "2026-08826",
      comments_close_on: "2026-07-06", // the original close — a genuine FR/Regs Eastern-date mismatch
      publication_date: "2026-05-06",
    },
    fetched_at,
  );
}
const fr = frAt("2026-06-17T16:51:47Z");
function pin(
  pinned_close_date: string,
  baselines: Observation[],
  fetched_at = "2026-09-23T20:41:45Z",
  id = "human-pin",
): Observation {
  return source(
    "human_review",
    {
      kind: "pin_close",
      pinned_close_date,
      operator: "test",
      note: "Reopening notice verified",
      reviewed_payload_hashes: baselines.map((b) => b.payload_hash),
    },
    fetched_at,
    id,
  );
}
const PIN = "2026-10-02";
const PIN_INSTANT = frCloseDateToUtcInstant(PIN); // 2026-10-03T03:59:59.000Z (EDT)
const BASE = regsRaw({});
const baseline = source("regulations_gov", BASE, "2026-09-18T20:20:31Z");
const verdict = pin(PIN, [fr, baseline]);
const identical = refresh(BASE, "2026-10-01T05:27:19Z");
const FLIPPED = { openForComment: false, withinCommentPeriod: false };

function expectHonored(
  label: string,
  chain: Observation[],
  pinnedDate = PIN,
  human = verdict,
  now = NOW,
) {
  const r = reconcile(chain, now);
  const pinnedInstant = frCloseDateToUtcInstant(pinnedDate);
  assert(
    `${label} — confidence HIGH`,
    r.window.confidence === "high",
    r.window.confidence,
  );
  assert(
    `${label} — human_resolved carried`,
    r.window.conflict_flags.includes("human_resolved"),
    r.window.conflict_flags.join(","),
  );
  assert(`${label} — no live ConflictRecord`, r.conflict === null);
  assert(
    `${label} — resolved_close_utc is the pinned instant`,
    r.window.resolved_close_utc === pinnedInstant,
    `${r.window.resolved_close_utc} vs ${pinnedInstant}`,
  );
  assert(
    `${label} — verdict in current_observation_ids`,
    r.window.current_observation_ids.includes(human.observation_id),
  );
  assert(
    `${label} — status from the pinned instant`,
    r.window.status === (new Date(pinnedInstant) > now ? "open" : "closed"),
    r.window.status,
  );
  assert(
    `${label} — display string unchanged`,
    r.window.resolved_close_display ===
      `closes ${pinnedDate} at 11:59 p.m. ET (pinned by human review)`,
    r.window.resolved_close_display ?? "null",
  );
  return r;
}
function expectUnhonored(label: string, chain: Observation[], human = verdict) {
  const r = reconcile(chain, NOW);
  assert(
    `${label} — NOT honored (no human_resolved)`,
    !r.window.conflict_flags.includes("human_resolved"),
    r.window.conflict_flags.join(","),
  );
  assert(
    `${label} — verdict NOT in current_observation_ids`,
    !r.window.current_observation_ids.includes(human.observation_id),
  );
  if (r.window.confidence === "conflicting")
    assert(
      `${label} — CONFLICTING carries a ConflictRecord`,
      r.conflict !== null,
    );
  return r;
}

// ═══ POSITIVE CLAUSES ═══════════════════════════════════════════════════════════════════════════════
{
  const after = "2026-10-03T07:01:55Z"; // a few hours after PIN_INSTANT, as in the live class
  expectHonored("P1 openForComment alone flips after the pinned instant", [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, after, { openForComment: false }),
  ]);
  expectHonored("P2 withinCommentPeriod alone flips after the pinned instant", [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, after, { withinCommentPeriod: false }),
  ]);
  expectHonored("P3 both flags flip in the same observation", [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, after, FLIPPED),
  ]);
  expectHonored("P4 both flags flip in successive observations (open first)", [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, after, { openForComment: false }),
    refresh(BASE, "2026-10-04T07:01:55Z", FLIPPED),
  ]);
  expectHonored(
    "P5 both flags flip in successive observations (within first)",
    [
      fr,
      baseline,
      verdict,
      identical,
      refresh(BASE, after, { withinCommentPeriod: false }),
      refresh(BASE, "2026-10-04T07:01:55Z", FLIPPED),
    ],
  );
  expectHonored("P6 flipped state repeats across many later refreshes", [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, after, FLIPPED),
    refresh(BASE, "2026-10-05T07:01:55Z", FLIPPED),
    refresh(BASE, "2026-10-09T07:01:55Z", FLIPPED),
    refresh(BASE, "2026-10-17T07:01:55Z", FLIPPED),
  ]);
  expectHonored("P7 flip exactly 1 s after the pinned instant", [
    fr,
    baseline,
    verdict,
    refresh(BASE, "2026-10-03T04:00:00Z", FLIPPED),
  ]);
  expectHonored("P8 no flip yet, only identical refreshes (plain v2.1 path)", [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, "2026-10-02T05:26:26Z"),
  ]);
}

// ── DST edges — the pinned instant MUST be DST-correct ───────────────────────────────────────────────
{
  // 2026-11-01: DST ends at 02:00 ET that morning, so 23:59:59 ET is EST (UTC-5) -> 2026-11-02T04:59:59Z.
  const novPin = "2026-11-01";
  const novInstant = frCloseDateToUtcInstant(novPin);
  assert(
    "DST-N0 pinned 2026-11-01 resolves to 04:59:59Z (EST, not EDT)",
    novInstant === "2026-11-02T04:59:59.000Z",
    novInstant,
  );
  const novBase = regsRaw({ commentEndDate: "2026-11-02T04:59:59Z" });
  const novBaseline = source(
    "regulations_gov",
    novBase,
    "2026-10-20T00:00:00Z",
  );
  const novVerdict = pin(
    novPin,
    [fr, novBaseline],
    "2026-10-21T00:00:00Z",
    "human-nov",
  );
  const novNow = new Date("2026-11-10T00:00:00Z");
  expectHonored(
    "DST-N1 flip 1 s AFTER the EST pinned instant honored",
    [
      fr,
      novBaseline,
      novVerdict,
      refresh(novBase, "2026-11-02T05:00:00Z", FLIPPED),
    ],
    novPin,
    novVerdict,
    novNow,
  );
  {
    // 1 s BEFORE the instant: 04:59:58Z. (Under a naive -4 offset this would look "after".)
    const r = reconcile(
      [
        fr,
        novBaseline,
        novVerdict,
        refresh(novBase, "2026-11-02T04:59:58Z", FLIPPED),
      ],
      novNow,
    );
    assert(
      "DST-N2 flip 1 s BEFORE the EST pinned instant NOT honored",
      !r.window.conflict_flags.includes("human_resolved"),
      r.window.conflict_flags.join(","),
    );
    if (r.window.confidence === "conflicting")
      assert(
        "DST-N2 — CONFLICTING carries a ConflictRecord",
        r.conflict !== null,
      );
  }

  // 2026-03-08: DST starts at 02:00 ET that morning, so 23:59:59 ET is EDT (UTC-4) -> 2026-03-09T03:59:59Z.
  const marPin = "2026-03-08";
  const marInstant = frCloseDateToUtcInstant(marPin);
  assert(
    "DST-M0 pinned 2026-03-08 resolves to 03:59:59Z (EDT, not EST)",
    marInstant === "2026-03-09T03:59:59.000Z",
    marInstant,
  );
  const marBase = regsRaw({ commentEndDate: "2026-03-09T03:59:59Z" });
  const marFr = frAt("2026-01-10T00:00:00Z"); // FR must predate the verdict (else it is real newer evidence)
  const marBaseline = source(
    "regulations_gov",
    marBase,
    "2026-02-20T00:00:00Z",
  );
  const marVerdict = pin(
    marPin,
    [marFr, marBaseline],
    "2026-02-21T00:00:00Z",
    "human-mar",
  );
  const marNow = new Date("2026-03-20T00:00:00Z");
  expectHonored(
    "DST-M1 flip 1 s AFTER the EDT pinned instant honored",
    [
      marFr,
      marBaseline,
      marVerdict,
      refresh(marBase, "2026-03-09T04:00:00Z", FLIPPED),
    ],
    marPin,
    marVerdict,
    marNow,
  );
  {
    const r = reconcile(
      [
        marFr,
        marBaseline,
        marVerdict,
        refresh(marBase, "2026-03-09T03:59:58Z", FLIPPED),
      ],
      marNow,
    );
    assert(
      "DST-M2 flip 1 s BEFORE the EDT pinned instant NOT honored",
      !r.window.conflict_flags.includes("human_resolved"),
      r.window.conflict_flags.join(","),
    );
    if (r.window.confidence === "conflicting")
      assert(
        "DST-M2 — CONFLICTING carries a ConflictRecord",
        r.conflict !== null,
      );
  }
}

// ── offset-form commentEndDate ───────────────────────────────────────────────────────────────────────
{
  const offBase = regsRaw({ commentEndDate: "2026-10-02T23:59:59-04:00" });
  const offBaseline = source(
    "regulations_gov",
    offBase,
    "2026-09-18T20:20:31Z",
  );
  const offVerdict = pin(
    PIN,
    [fr, offBaseline],
    "2026-09-23T20:41:45Z",
    "human-off",
  );
  expectHonored(
    "P9 offset-form commentEndDate (2026-10-02T23:59:59-04:00) honored",
    [
      fr,
      offBaseline,
      offVerdict,
      refresh(offBase, "2026-10-03T07:01:55Z", FLIPPED),
    ],
    PIN,
    offVerdict,
  );
}

// ── baseline already false — identical refreshes ride the plain v2.1 path ───────────────────────────
{
  const closedBase = regsRaw(FLIPPED);
  const closedBaseline = source(
    "regulations_gov",
    closedBase,
    "2026-10-04T00:00:00Z",
  );
  const closedVerdict = pin(
    PIN,
    [fr, closedBaseline],
    "2026-10-05T00:00:00Z",
    "human-closed",
  );
  expectHonored(
    "P10 baseline already false + identical refreshes (v2.1 path)",
    [
      fr,
      closedBaseline,
      closedVerdict,
      refresh(closedBase, "2026-10-06T00:00:00Z"),
      refresh(closedBase, "2026-10-07T00:00:00Z"),
    ],
    PIN,
    closedVerdict,
  );
}

// ── repin after an invalidating change (existing v2 behavior) ────────────────────────────────────────
{
  const moved = refresh(BASE, "2026-09-25T00:00:00Z", {
    commentEndDate: "2026-10-10T03:59:59Z",
  });
  expectUnhonored("P11a a moved commentEndDate invalidates the first pin", [
    fr,
    baseline,
    verdict,
    moved,
  ]);
  const repin = pin(
    "2026-10-09",
    [fr, moved],
    "2026-09-26T00:00:00Z",
    "human-repin",
  );
  expectHonored(
    "P11b a repin over the changed evidence is honored, and its own echo too",
    [
      fr,
      baseline,
      verdict,
      moved,
      repin,
      refresh(moved.raw as RegsRaw, "2026-10-10T07:33:59Z", FLIPPED),
    ],
    "2026-10-09",
    repin,
  );
}

// ═══ LIVE REPLAY — the 7 exported histories ═════════════════════════════════════════════════════════
const HERE = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  await readFile(join(HERE, "fixtures", "review-echo-histories.json"), "utf8"),
) as {
  exported_at: string;
  observations: Observation[];
  windows: {
    ocd_id: string;
    confidence: string;
    status: string;
    conflict_flags: string[];
    resolved_close_utc: string | null;
    version: number;
    reconciler_version: string;
  }[];
};
const EXPORTED_AT = new Date(fixture.exported_at);
assert(
  "FIXTURE exported_at is the spec's NOW (2026-10-18T06:13:26Z)",
  fixture.exported_at.startsWith("2026-10-18T06:13:26"),
  fixture.exported_at,
);
assert(
  "FIXTURE has 210 observations / 7 windows",
  fixture.observations.length === 210 && fixture.windows.length === 7,
);
const historyByOcd = new Map<string, Observation[]>();
for (const o of fixture.observations) {
  const list = historyByOcd.get(o.ocd_id) ?? [];
  list.push(o);
  historyByOcd.set(o.ocd_id, list);
}
/** Deterministic order (fetched_at epoch asc, observation_id asc) — the DB read order. */
function ordered(obs: Observation[]): Observation[] {
  return [...obs].sort((a, b) => {
    const d =
      new Date(a.fetched_at).getTime() - new Date(b.fetched_at).getTime();
    return d !== 0
      ? d
      : a.observation_id < b.observation_id
        ? -1
        : a.observation_id > b.observation_id
          ? 1
          : 0;
  });
}
function isFlipped(o: Observation): boolean {
  const attrs = (o.raw as RegsRaw | null)?.data?.attributes;
  return (
    o.source === "regulations_gov" &&
    !!attrs &&
    (attrs.openForComment === false || attrs.withinCommentPeriod === false)
  );
}
const EXPECTED: Record<
  string,
  { pin: string; verdictAt: string; firstFlipAt: string; total: number }
> = {
  "2026-08826": {
    pin: "2026-10-02",
    verdictAt: "2026-09-23T20:41:45Z",
    firstFlipAt: "2026-10-03T07:01:55Z",
    total: 8,
  },
  "2026-13615": {
    pin: "2026-10-05",
    verdictAt: "2026-09-24T04:11:35Z",
    firstFlipAt: "2026-10-06T05:57:29Z",
    total: 75,
  },
  "2026-16246": {
    pin: "2026-10-09",
    verdictAt: "2026-09-20T15:48:39Z",
    firstFlipAt: "2026-10-10T07:33:59Z",
    total: 7,
  },
  "2026-16247": {
    pin: "2026-10-09",
    verdictAt: "2026-09-20T17:41:48Z",
    firstFlipAt: "2026-10-10T07:34:00Z",
    total: 8,
  },
  "2026-16664": {
    pin: "2026-10-01",
    verdictAt: "2026-09-20T15:18:03Z",
    firstFlipAt: "2026-10-02T05:57:28Z",
    total: 31,
  },
  "2026-16776": {
    pin: "2026-10-02",
    verdictAt: "2026-09-23T20:41:47Z",
    firstFlipAt: "2026-10-03T07:01:50Z",
    total: 27,
  },
  "2026-16965": {
    pin: "2026-10-06",
    verdictAt: "2026-09-19T21:20:26Z",
    firstFlipAt: "2026-10-07T07:47:19Z",
    total: 54,
  },
};
for (const liveRow of fixture.windows) {
  const doc = liveRow.ocd_id.split("/").pop()!;
  const exp = EXPECTED[doc]!;
  const history = ordered(historyByOcd.get(liveRow.ocd_id) ?? []);
  const human = history.find((o) => o.source === "human_review")!;
  const v = HumanReviewVerdict.parse(human.raw);
  assert(
    `LIVE ${doc} — history shape matches the spec (${exp.total} obs, pin ${exp.pin}, verdict ${exp.verdictAt})`,
    history.length === exp.total &&
      v.kind === "pin_close" &&
      v.pinned_close_date === exp.pin &&
      human.fetched_at.startsWith(exp.verdictAt.slice(0, 19)),
    `${history.length} obs, ${v.kind} ${v.pinned_close_date}, ${human.fetched_at}`,
  );
  const firstFlipIdx = history.findIndex(isFlipped);
  assert(
    `LIVE ${doc} — first flip observed at ${exp.firstFlipAt}`,
    firstFlipIdx >= 0 &&
      history[firstFlipIdx]!.fetched_at.startsWith(
        exp.firstFlipAt.slice(0, 19),
      ),
    history[firstFlipIdx]?.fetched_at ?? "no flip found",
  );
  assert(
    `LIVE ${doc} — the live v2.1 row is the echo symptom (conflicting/closed/fr_regs_date_mismatch)`,
    liveRow.confidence === "conflicting" &&
      liveRow.status === "closed" &&
      isDeepStrictEqual(liveRow.conflict_flags, ["fr_regs_date_mismatch"]) &&
      liveRow.reconciler_version === "reconcile-v2.1",
  );

  // Full history at the export instant.
  const r = expectHonored(
    `LIVE ${doc} full history`,
    history,
    exp.pin,
    human,
    EXPORTED_AT,
  );
  assert(
    `LIVE ${doc} — status closed`,
    r.window.status === "closed",
    r.window.status,
  );
  assert(
    `LIVE ${doc} — flags are exactly fr_regs_date_mismatch + human_resolved`,
    isDeepStrictEqual([...r.window.conflict_flags].sort(), [
      "fr_regs_date_mismatch",
      "human_resolved",
    ]),
    r.window.conflict_flags.join(","),
  );
  assert(
    `LIVE ${doc} — resolved_close_utc equals the live v2.1 row's close (sweep retires without a version bump)`,
    r.window.resolved_close_utc === liveRow.resolved_close_utc &&
      r.window.resolved_close_utc === frCloseDateToUtcInstant(exp.pin),
    `${r.window.resolved_close_utc} vs live ${liveRow.resolved_close_utc}`,
  );

  // Truncated: ending BEFORE the first flip — the plain v2.1 path (status may be open or closed
  // depending on the pinned instant vs the export instant; here every pin has passed).
  expectHonored(
    `LIVE ${doc} truncated before the first flip`,
    history.slice(0, firstFlipIdx),
    exp.pin,
    human,
    EXPORTED_AT,
  );
  // Truncated: ending EXACTLY at the first flipped observation.
  expectHonored(
    `LIVE ${doc} truncated at the first flipped observation`,
    history.slice(0, firstFlipIdx + 1),
    exp.pin,
    human,
    EXPORTED_AT,
  );

  // Determinism / order-independence / immutability over the live history.
  const frozen = JSON.stringify(history);
  const again = reconcile(history, EXPORTED_AT);
  const reversed = reconcile([...history].reverse(), EXPORTED_AT);
  assert(`LIVE ${doc} — two runs deep-equal`, isDeepStrictEqual(r, again));
  assert(
    `LIVE ${doc} — reversed input deep-equal`,
    isDeepStrictEqual(r, reversed),
  );
  assert(
    `LIVE ${doc} — inputs not mutated`,
    JSON.stringify(history) === frozen,
  );
}

// ═══ DETERMINISM over the synthetic chain ═══════════════════════════════════════════════════════════
{
  const chain = [
    fr,
    baseline,
    verdict,
    identical,
    refresh(BASE, "2026-10-03T07:01:55Z", { openForComment: false }),
    refresh(BASE, "2026-10-04T07:01:55Z", FLIPPED),
  ];
  const frozen = JSON.stringify(chain);
  const a = reconcile(chain, NOW);
  const b = reconcile(chain, NOW);
  const c = reconcile([...chain].reverse(), NOW);
  assert(
    "DETERMINISM synthetic — two runs deep-equal",
    isDeepStrictEqual(a, b),
  );
  assert(
    "DETERMINISM synthetic — reversed input deep-equal",
    isDeepStrictEqual(a, c),
  );
  assert(
    "DETERMINISM synthetic — inputs not mutated",
    JSON.stringify(chain) === frozen,
  );
  assert(
    "DETERMINISM synthetic — the chain was honored",
    a.window.conflict_flags.includes("human_resolved"),
  );
}

console.log("\n=== reconcile-review-echo results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
