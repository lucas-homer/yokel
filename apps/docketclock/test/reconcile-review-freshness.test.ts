import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import type { Observation } from "@yokel/contracts";
import { reconcile } from "../src/reconcile/reconcile.js";

const OCD = "ocd-participation-window/federal/2026-16965";
const NOW = new Date("2026-09-23T00:00:00Z");
function source(
  source: Observation["source"],
  raw: unknown,
  fetched_at = "2026-09-18T00:00:00Z",
): Observation {
  return {
    observation_id: `${source}-${fetched_at}`,
    ocd_id: OCD,
    source,
    fr_document_number: "2026-16965",
    regs_document_id:
      source === "regulations_gov" ? "FS-2025-0001-223869" : null,
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
const fr = source("federal_register", {
  document_number: "2026-16965",
  comments_close_on: "2026-09-21",
  publication_date: "2026-08-20",
});
const regsRaw = {
  data: {
    id: "FS-2025-0001-223869",
    attributes: {
      commentEndDate: "2026-10-07T03:59:59Z",
      openForComment: true,
      withdrawn: false,
      modifyDate: "2026-09-18T00:00:00Z",
    },
  },
};
const regs = source("regulations_gov", regsRaw);
const human = source(
  "human_review",
  {
    kind: "pin_close",
    pinned_close_date: "2026-10-06",
    operator: "test",
    note: "Extension verified",
    reviewed_payload_hashes: [fr.payload_hash, regs.payload_hash],
  },
  "2026-09-19T00:00:00Z",
);

const refreshedRaw = structuredClone(regsRaw);
refreshedRaw.data.attributes.modifyDate = "2026-09-23T00:00:00Z";
const refreshed = source(
  "regulations_gov",
  refreshedRaw,
  "2026-09-23T00:00:00Z",
);
const result = reconcile([fr, regs, human, refreshed], NOW);
assert.equal(
  result.window.confidence,
  "high",
  "a metadata refresh preserves the reviewed deadline",
);
assert.ok(result.window.conflict_flags.includes("human_resolved"));
assert.equal(result.conflict, null);
assert.ok(
  result.window.current_observation_ids.includes(refreshed.observation_id),
);
console.log("review freshness: metadata refresh preserved");

const linked = source(
  "regulations_gov",
  {
    ...regsRaw,
    links: { self: "https://regulations.gov/v4/documents/FS-2025-0001-223869" },
  },
  "2026-09-23T01:00:00Z",
);
assert.ok(
  reconcile([fr, regs, human, linked], NOW).window.conflict_flags.includes(
    "human_resolved",
  ),
  "adding the API self link preserves the reviewed deadline",
);
console.log("review freshness: API self link preserved");

function staysUnreviewed(label: string, chain: Observation[]) {
  const r = reconcile(chain, NOW);
  assert.ok(!r.window.conflict_flags.includes("human_resolved"), label);
  assert.ok(
    !r.window.current_observation_ids.includes(human.observation_id),
    label,
  );
  if (r.window.confidence === "conflicting")
    assert.notEqual(r.conflict, null, label);
}
for (const [key, value] of Object.entries({
  commentEndDate: "2026-10-08T03:59:59Z",
  withdrawn: true,
  openForComment: false,
  allowLateComments: true,
  withinCommentPeriod: false,
  title: "Corrected notice",
  docketId: "different-docket",
  docAbstract: "The agency changed its instructions",
  unknownNewEvidence: "must not be silently excluded",
})) {
  const changed = structuredClone(regsRaw);
  Object.assign(changed.data.attributes, { [key]: value });
  staysUnreviewed(`changed ${key} reopens review`, [
    fr,
    regs,
    human,
    source("regulations_gov", changed, "2026-09-23T00:00:00Z"),
  ]);
}
for (const [key, value] of Object.entries({
  parser_version: "test-v2",
  is_extension: true,
  is_correction: true,
  is_withdrawal: true,
  is_reopening: true,
  raw_dates_text: "New deadline instructions",
  fr_document_number: "2026-99999",
  regs_document_id: "FS-2025-0001-999999",
  regs_object_id: "different-object",
})) {
  staysUnreviewed(`changed observation ${key} reopens review`, [
    fr,
    regs,
    human,
    { ...refreshed, [key]: value },
  ]);
}
staysUnreviewed("other links remain evidence", [
  fr,
  regs,
  human,
  source(
    "regulations_gov",
    { ...regsRaw, links: { next: "new evidence" } },
    "2026-09-23T00:00:00Z",
  ),
]);
staysUnreviewed("FR refresh retains conservative invalidation", [
  fr,
  regs,
  human,
  { ...fr, observation_id: "new-fr", fetched_at: "2026-09-23T00:00:00Z" },
]);
staysUnreviewed("new GovInfo source reopens review", [
  fr,
  regs,
  human,
  source("govinfo", { notice: "additional evidence" }, "2026-09-23T00:00:00Z"),
]);
const unknownHashes = {
  ...human,
  raw: { ...(human.raw as object), reviewed_payload_hashes: ["f".repeat(64)] },
};
staysUnreviewed("missing reviewed baseline fails closed", [
  fr,
  regs,
  unknownHashes,
  refreshed,
]);
staysUnreviewed("omitted history fails closed", [fr, human, refreshed]);
const revised = source(
  "regulations_gov",
  {
    ...regsRaw,
    data: {
      ...regsRaw.data,
      attributes: {
        ...regsRaw.data.attributes,
        commentEndDate: "2026-11-01T03:59:59Z",
      },
    },
  },
  "2026-09-20T00:00:00Z",
);
staysUnreviewed(
  "material change followed by reversion never revives old verdict",
  [fr, regs, human, revised, refreshed],
);
staysUnreviewed("latest pre-review baseline must be in reviewed hashes", [
  fr,
  regs,
  { ...revised, fetched_at: "2026-09-18T12:00:00Z" },
  human,
  { ...revised, fetched_at: "2026-09-23T00:00:00Z" },
]);

for (const kind of [
  "pin_close",
  "dismiss_conflict",
  "confirm_withdrawn",
  "confirm_reopened",
] as const) {
  const raw: Record<string, unknown> = {
    ...(human.raw as Record<string, unknown>),
    kind,
  };
  if (kind !== "pin_close") delete raw.pinned_close_date;
  const verdict = { ...human, raw };
  const before = reconcile([fr, regs, verdict], NOW);
  const after = reconcile([fr, regs, verdict, refreshed, linked], NOW);
  assert.equal(after.window.confidence, before.window.confidence, kind);
  assert.equal(after.window.status, before.window.status, kind);
  assert.equal(
    after.window.resolved_close_utc,
    before.window.resolved_close_utc,
    kind,
  );
  assert.ok(after.window.conflict_flags.includes("human_resolved"), kind);
  assert.equal(after.conflict, null, kind);
}
const chain = [fr, regs, human, refreshed, linked];
const frozenInput = JSON.stringify(chain);
assert.deepEqual(
  reconcile(chain, NOW),
  reconcile([...chain].reverse(), NOW),
  "input order cannot change the verdict",
);
assert.equal(
  JSON.stringify(chain),
  frozenInput,
  "raw observations and hashes remain untouched",
);
const repin = {
  ...human,
  observation_id: "repin",
  fetched_at: "2026-09-24T00:00:00Z",
};
assert.ok(
  reconcile(
    [fr, regs, human, revised, repin],
    NOW,
  ).window.conflict_flags.includes("human_resolved"),
  "a new human verdict can resolve genuinely changed evidence",
);
console.log(
  "review freshness: material changes, missing evidence, history, verdict kinds and determinism verified",
);
