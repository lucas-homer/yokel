/**
 * review/cli.ts — the operator review CLI (Slice R, PR-R3): `queue` / `show` / `resolve` over
 * review/core.ts. CLI-first, operator-only by design (locked decision) — the delivery API stays
 * read-only; this is the ONLY write path for human_review observations until the D5 console, and
 * that console's spec is this CLI.
 *
 * Run (host-side, DATABASE_URL via the usual port-forward):
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review queue
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review show <ocd-id>
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review resolve <ocd-id> \
 *     --kind pin_close --close 2026-09-20 --note "why" [--operator name]
 * or in-cluster (zero setup — the poller image ships src/ + env):
 *   kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts queue
 *
 * Verdict kinds (see docs/runbooks/review-queue.md for full semantics):
 *   pin_close        — assert the operative close (--close required); derives HIGH while honored.
 *   confirm_withdrawn / confirm_reopened — assert status the machine can't see.
 *   dismiss_conflict — "the disagreement is noise"; lands at LOW, never picks a winner.
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

// Load the repo-root .env before env-reading imports (the poll/run.ts discipline).
const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const { createClient } = await import("../db/client.js");
const { reviewQueue, reviewShow, resolveWindow } = await import("./core.js");

const KINDS = [
  "pin_close",
  "confirm_withdrawn",
  "confirm_reopened",
  "dismiss_conflict",
] as const;
type Kind = (typeof KINDS)[number];

function usage(): never {
  console.error(
    [
      "usage: review <command>",
      "  review queue",
      "  review show <ocd-id>",
      "  review resolve <ocd-id> --kind <kind> [--close YYYY-MM-DD] --note <why> [--operator <name>]",
      `  kinds: ${KINDS.join(" | ")}`,
    ].join("\n"),
  );
  process.exit(2);
}

const [command, ...rest] = process.argv.slice(2);
const sql = createClient();
try {
  if (command === "queue") {
    const rows = await reviewQueue(sql);
    if (rows.length === 0) {
      console.log("review queue: empty — nothing demands a human right now.");
    } else {
      console.log(
        `review queue: ${rows.length} window(s), closing-soonest first\n`,
      );
      for (const r of rows) {
        console.log(
          `  ${r.ocd_id}\n    ${r.confidence} [${r.conflict_flags.join(",")}] status=${r.status}` +
            `\n    ${r.resolved_close_display ?? "(no resolved close)"} — last derived ${r.derived_at}`,
        );
      }
    }
  } else if (command === "show") {
    const ocdId = rest[0];
    if (!ocdId) usage();
    const s = await reviewShow(sql, ocdId);
    if (!s.window) {
      console.error(`review show: no participation_window for "${ocdId}"`);
      process.exit(1);
    }
    const w = s.window;
    console.log(`${ocdId}`);
    console.log(
      `  confidence=${String(w.confidence)} status=${String(w.status)} flags=${JSON.stringify(w.conflict_flags)}`,
    );
    console.log(
      `  close: ${String(w.resolved_close_display ?? "(none)")} (utc: ${String(w.resolved_close_utc ?? "null")})`,
    );
    console.log(
      `  conflicts: ${s.liveConflicts} live / ${s.retiredConflicts} retired; chain links: ${s.chainLinks.length}`,
    );
    console.log(`\n  latest per source:`);
    for (const src of s.sources) {
      console.log(
        `    ${src.source} @ ${src.fetched_at}\n      close=${src.close_value ?? "null"}` +
          ` withdrawn=${src.withdrawn ?? "n/a"} openForComment=${src.open_for_comment ?? "n/a"}` +
          ` flags[w/e/r]=${Number(src.is_withdrawal)}${Number(src.is_extension)}${Number(src.is_reopening)}` +
          `\n      hash=${src.payload_hash}`,
      );
    }
    if (s.priorVerdicts.length > 0) {
      console.log(`\n  prior human verdicts (latest first):`);
      for (const v of s.priorVerdicts) {
        const body =
          "unparseable" in v.verdict
            ? "(unparseable raw)"
            : `${v.verdict.kind}${v.verdict.pinned_close_date ? ` → ${v.verdict.pinned_close_date}` : ""} by ${v.verdict.operator}: ${v.verdict.note}`;
        console.log(`    ${v.fetched_at}  ${body}`);
      }
    }
  } else if (command === "resolve") {
    const ocdId = rest[0];
    if (!ocdId || ocdId.startsWith("--")) usage();
    const { values } = parseArgs({
      args: rest.slice(1),
      options: {
        kind: { type: "string" },
        close: { type: "string" },
        note: { type: "string" },
        operator: { type: "string" },
      },
    });
    const kind = values.kind as Kind | undefined;
    if (!kind || !KINDS.includes(kind) || !values.note) usage();
    const operator =
      values.operator ?? process.env.REVIEW_OPERATOR ?? process.env.USER;
    if (!operator) {
      console.error(
        "review resolve: no operator (pass --operator or set REVIEW_OPERATOR)",
      );
      process.exit(1);
    }
    const out = await resolveWindow(sql, {
      ocdId,
      kind,
      close: values.close,
      note: values.note,
      operator,
    });
    const w = out.result.window;
    console.log(
      out.inserted
        ? `✅ verdict written (evidence: ${out.reviewedHashes.length} source hash(es))`
        : `↩︎ identical verdict already latest for this window — deduped, re-derived anyway`,
    );
    console.log(
      `re-derived: confidence=${w.confidence} status=${w.status} flags=[${w.conflict_flags.join(",")}]`,
    );
    console.log(
      `  close: ${w.resolved_close_display ?? "(none)"} (utc: ${w.resolved_close_utc ?? "null"})`,
    );
    if (!w.conflict_flags.includes("human_resolved")) {
      console.log(
        "⚠ verdict NOT honored (a source observation is newer, or raw failed to parse) — the window derives purely from sources. `review show` to inspect.",
      );
    }
  } else {
    usage();
  }
} finally {
  await sql.end();
}
