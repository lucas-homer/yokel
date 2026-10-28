/** Usage: tsx scripts/replay-diff.ts BEFORE.json AFTER.json [--out FILE]
 * Defaults to /tmp/amend-replay/out/diff.md. No DB access or network.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { parseArgs } from "node:util";
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    out: { type: "string", default: "/tmp/amend-replay/out/diff.md" },
  },
});
if (positionals.length !== 2)
  throw new Error("Usage: replay-diff.ts BEFORE.json AFTER.json [--out FILE]");
type Row = Record<string, unknown> & { ocd_id: string };
type Snapshot = {
  counts: unknown;
  windows: Row[];
  conflicts: Row[];
  review_queue: string[];
};
const [before, after] = await Promise.all(
  positionals.map(
    async (path) => JSON.parse(await readFile(path, "utf8")) as Snapshot,
  ),
);
const fields = [
  "status",
  "confidence",
  "resolved_close_utc",
  "resolved_close_display",
  "raw_fr_close_date",
  "raw_regs_close_datetime",
  "conflict_flags",
  "current_observation_ids",
];
// Flags and evidence IDs are sets; avoid treating array reorderings as semantic changes.
const canonical = (value: unknown) =>
  JSON.stringify(Array.isArray(value) ? [...value].sort() : value);
const pretty = (value: unknown) =>
  JSON.stringify(value ?? null)
    .replaceAll("|", "\\|")
    .replaceAll("\n", " ");
const index = (rows: Row[]) => new Map(rows.map((row) => [row.ocd_id, row]));
const bi = index(before!.windows),
  ai = index(after!.windows);
const changed = [...new Set([...bi.keys(), ...ai.keys()])]
  .sort()
  .flatMap((id) => {
    const b = bi.get(id),
      a = ai.get(id);
    const changes = fields.filter(
      (field) => canonical(b?.[field]) !== canonical(a?.[field]),
    );
    return changes.length || !a || !b ? [{ id, b, a, changes }] : [];
  });
const lines = [
  "# Amendment replay diff",
  "",
  `Before: ${positionals[0]}`,
  `After: ${positionals[1]}`,
  "",
  "## Counts",
  "",
  "| Snapshot | Counts |",
  "|---|---|",
  `| Before | ${pretty(before!.counts)} |`,
  `| After | ${pretty(after!.counts)} |`,
  "",
  `## Changed windows (${changed.length})`,
  "",
];
for (const { id, b, a, changes } of changed) {
  lines.push(`### ${id}`, "", "| Field | Before | After |", "|---|---|---|");
  if (!a || !b)
    lines.push(
      `| membership | ${b ? "present" : "absent"} | ${a ? "present" : "absent"} |`,
    );
  for (const field of changes)
    lines.push(`| ${field} | ${pretty(b?.[field])} | ${pretty(a?.[field])} |`);
  lines.push("");
}
const bq = new Set(before!.review_queue),
  aq = new Set(after!.review_queue);
const entries = [...aq].filter((id) => !bq.has(id)).sort(),
  exits = [...bq].filter((id) => !aq.has(id)).sort();
lines.push(
  `## Review queue (${entries.length} entries, ${exits.length} exits)`,
  "",
  "| Change | Window |",
  "|---|---|",
);
for (const id of entries) lines.push(`| Entered | ${id} |`);
for (const id of exits) lines.push(`| Exited | ${id} |`);
const cross = (snapshot: Snapshot) => {
  const grouped = new Map<string, unknown[]>();
  for (const row of snapshot.conflicts.filter(
    (row) => row.conflict_scope === "cross_window",
  )) {
    const key = `${row.ocd_id} → ${row.ocd_id_b}`;
    grouped.set(key, [
      ...(grouped.get(key) ?? []),
      JSON.parse(canonical(row.conflict_flags)),
    ]);
  }
  // Preserve multiplicity when several live records share the same pair.
  return new Map(
    [...grouped].map(([key, flags]) => [
      key,
      flags.sort((a, b) => canonical(a).localeCompare(canonical(b))),
    ]),
  );
};
const bc = cross(before!),
  ac = cross(after!);
lines.push(
  "",
  "## Cross-window changes",
  "",
  "| Pair | Change | Before flags | After flags |",
  "|---|---|---|---|",
);
let crossChanges = 0;
for (const pair of [...new Set([...bc.keys(), ...ac.keys()])].sort()) {
  if (canonical(bc.get(pair)) === canonical(ac.get(pair))) continue;
  crossChanges++;
  lines.push(
    `| ${pair} | ${!bc.has(pair) ? "added" : !ac.has(pair) ? "removed" : "flags/multiplicity changed"} | ${pretty(bc.get(pair))} | ${pretty(ac.get(pair))} |`,
  );
}
const focus = [
  "2026-18574",
  "C1-2026-18574",
  "2026-18481",
  "2026-20328",
  "2026-18531",
  "2026-19710",
  "2026-08068",
  "2026-08077",
  "2026-10969",
  "2026-19895",
  "2026-17216",
  "2026-20660",
  "2026-18134",
];
lines.push(
  "",
  "## Focused windows",
  "",
  "| Document | Confidence (before → after) | Status (before → after) | Close UTC (before → after) | Flags (before → after) | Changed fields |",
  "|---|---|---|---|---|---|",
);
for (const doc of focus) {
  const id = `ocd-participation-window/federal/${doc}`,
    b = bi.get(id),
    a = ai.get(id);
  const transition = (field: string) =>
    `${pretty(b?.[field])} → ${pretty(a?.[field])}`;
  lines.push(
    `| ${doc} | ${transition("confidence")} | ${transition("status")} | ${transition("resolved_close_utc")} | ${transition("conflict_flags")} | ${!a || !b ? "missing window" : changed.find((c) => c.id === id)?.changes.join(", ") || "unchanged"} |`,
  );
}
await mkdir(dirname(values.out!), { recursive: true });
await writeFile(values.out!, lines.join("\n") + "\n");
console.log(
  JSON.stringify(
    {
      report: values.out,
      changed_windows: changed.length,
      changed_ids: changed.map((c) => c.id),
      queue_entries: entries,
      queue_exits: exits,
      cross_window_changes: crossChanges,
    },
    null,
    2,
  ),
);
