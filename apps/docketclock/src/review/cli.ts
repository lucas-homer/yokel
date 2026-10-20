/**
 * review/cli.ts — the operator review CLI (Slice R, PR-R3; review autopilot PR-A2): `queue` / `show`
 * / `resolve` over review/core.ts. CLI-first, operator-only by design (locked decision) — the delivery
 * API stays read-only; this is the ONLY write path for human_review observations until the D5
 * console, and that console's spec is this CLI.
 *
 * Run (host-side, DATABASE_URL via the usual port-forward):
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review queue
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review show <ocd-id> [--blind]
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review resolve <ocd-id> \
 *     --kind pin_close --close 2026-09-20 --note "why" [--operator name] \
 *     [--reviewer human|agent] [--expect <sha256> --expect <sha256> …]
 * or in-cluster (zero setup — the poller image ships src/ + env):
 *   kubectl -n docketclock exec deploy/docketclock-poller -- pnpm exec tsx src/review/cli.ts queue
 *
 * Verdict kinds (see docs/runbooks/review-queue.md for full semantics):
 *   pin_close        — assert the operative close (--close required); derives HIGH while honored.
 *   confirm_withdrawn / confirm_reopened — assert status the machine can't see.
 *   dismiss_conflict — "the disagreement is noise"; lands at LOW, never picks a winner.
 *   escalate         — "primary sources examined; cannot be resolved from documents; a human decision
 *                      or agency clarification is needed". Derives NOTHING (the window stays in the
 *                      queue, flagged [escalated]); parks the item until a human supersedes it or new
 *                      evidence un-parks it; pages via the review-queue-escalated alert. REFUSED when
 *                      the window would not be a queue member with it (an escalation nobody can see
 *                      is silence) — pin or confirm instead, or supersede the wrong earlier verdict.
 *
 * Provenance (ADR 0015): --operator is who EXECUTES the write; --reviewer is who DECIDED — "human"
 * (default: a person authorized this verdict, even if an agent typed it) or "agent" (an unsupervised
 * autopilot). The reconciler stamps human_resolved or agent_resolved accordingly.
 *
 * Evidence binding (ADR 0015): --expect lists the latest-per-source payload hashes (from `show`) the
 * investigation assessed; the write refuses, in one transaction, if the live set differs. Automation
 * always passes it; humans may omit it.
 *
 * --blind (the shadow-gate harness): hides prior verdicts and shows the machine's own derivation of
 * the sources, so an agent under measurement cannot read the answer off the projection.
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
  "escalate",
] as const;
type Kind = (typeof KINDS)[number];
const REVIEWERS = ["human", "agent"] as const;
type Reviewer = (typeof REVIEWERS)[number];
const SHA256 = /^[a-f0-9]{64}$/;

function usage(): never {
  console.error(
    [
      "usage: review <command>",
      "  review queue",
      "  review show <ocd-id> [--blind]",
      "  review resolve <ocd-id> --kind <kind> [--close YYYY-MM-DD] --note <why> [--operator <name>]",
      "                 [--reviewer human|agent] [--expect <sha256-hash> ...]",
      `  kinds: ${KINDS.join(" | ")}`,
      "  --reviewer  who decided: human (default) or agent (unsupervised autopilot)",
      "  --expect    repeatable; the latest-per-source payload hashes you assessed (from `show`) —",
      "              the write refuses if the live evidence differs",
      "  --blind     hide prior verdicts; show the machine's own derivation of the sources",
    ].join("\n"),
  );
  process.exit(2);
}

// Validate EVERYTHING argument-side before opening a DB connection (#117 Copilot): `review` alone,
// a bad command, or missing flags must print usage — never a DATABASE_URL / connection error.
const [command, ...rest] = process.argv.slice(2);
if (command !== "queue" && command !== "show" && command !== "resolve") usage();
let showArgs: { ocdId: string; blind: boolean } | null = null;
if (command === "show") {
  const ocdId = rest[0];
  if (!ocdId || ocdId.startsWith("--")) usage();
  const { values } = parseArgs({
    args: rest.slice(1),
    options: { blind: { type: "boolean" } },
  });
  showArgs = { ocdId, blind: values.blind === true };
}
let resolveArgs: {
  ocdId: string;
  kind: Kind;
  close?: string;
  note: string;
  operator: string;
  reviewer: Reviewer;
  expect?: string[];
} | null = null;
if (command === "resolve") {
  const ocdId = rest[0];
  if (!ocdId || ocdId.startsWith("--")) usage();
  const { values } = parseArgs({
    args: rest.slice(1),
    options: {
      kind: { type: "string" },
      close: { type: "string" },
      note: { type: "string" },
      operator: { type: "string" },
      reviewer: { type: "string" },
      expect: { type: "string", multiple: true },
    },
  });
  const kind = values.kind as Kind | undefined;
  if (!kind || !KINDS.includes(kind) || !values.note) usage();
  const reviewer = (values.reviewer ?? "human") as Reviewer;
  if (!REVIEWERS.includes(reviewer)) {
    console.error(
      `review resolve: --reviewer must be one of ${REVIEWERS.join(" | ")} (got "${String(values.reviewer)}")`,
    );
    process.exit(2);
  }
  const expect = values.expect;
  if (expect !== undefined) {
    const bad = expect.filter((h) => !SHA256.test(h));
    if (expect.length === 0 || bad.length > 0) {
      console.error(
        `review resolve: --expect takes sha256 hex payload hashes as printed by \`review show\` (bad: ${bad.join(", ") || "(none given)"})`,
      );
      process.exit(2);
    }
  }
  const operator =
    values.operator ?? process.env.REVIEW_OPERATOR ?? process.env.USER;
  if (!operator) {
    console.error(
      "review resolve: no operator (pass --operator or set REVIEW_OPERATOR)",
    );
    process.exit(1);
  }
  resolveArgs = {
    ocdId,
    kind,
    close: values.close,
    note: values.note,
    operator,
    reviewer,
    ...(expect !== undefined ? { expect } : {}),
  };
}

const sql = createClient();
process.exitCode = 0;
try {
  if (command === "queue") {
    const rows = await reviewQueue(sql);
    if (rows.length === 0) {
      console.log("review queue: empty — nothing demands a human right now.");
    } else {
      const parked = rows.filter((r) => r.escalated !== null).length;
      console.log(
        `review queue: ${rows.length} window(s), closing-soonest first` +
          (parked > 0
            ? ` (${parked} parked as escalated — a human decision is owed, not a re-review)`
            : "") +
          "\n",
      );
      for (const r of rows) {
        const mark = r.escalated
          ? `  [escalated by ${r.escalated.operator} (${r.escalated.reviewer}) ${r.escalated.fetched_at.slice(0, 10)}]`
          : "";
        console.log(
          `  ${r.ocd_id}${mark}\n    ${r.confidence} [${r.conflict_flags.join(",")}] status=${r.status}` +
            `\n    ${r.resolved_close_display ?? "(no resolved close)"} — last derived ${r.derived_at}`,
        );
      }
    }
  } else if (command === "show") {
    const { ocdId, blind } = showArgs!;
    const s = await reviewShow(sql, ocdId, { blind });
    if (!s.window) {
      console.error(`review show: no participation_window for "${ocdId}"`);
      process.exit(1);
    }
    const w = s.window;
    console.log(`${ocdId}`);
    if (s.blind)
      console.log(
        "  (blind: prior verdicts hidden; the window below is the machine's own derivation of the sources, not the stored projection)",
      );
    console.log(
      `  confidence=${String(w.confidence)} status=${String(w.status)} flags=${JSON.stringify(w.conflict_flags)}`,
    );
    console.log(
      `  close: ${String(w.resolved_close_display ?? "(none)")} (utc: ${String(w.resolved_close_utc ?? "null")})`,
    );
    console.log(
      `  conflicts: ${s.liveConflicts} live / ${s.retiredConflicts} retired; chain links: ${s.blind ? "(hidden in blind mode)" : String(s.chainLinks.length)}`,
    );
    if (!s.blind) {
      console.log(
        s.honored
          ? `  honored verdict: ${s.honored.kind} by ${s.honored.operator} (${s.honored.reviewer}) @ ${s.honored.fetched_at}` +
              (s.honored.parked
                ? " — PARKED: escalated; derives nothing until a human supersedes it or new evidence un-parks it"
                : "")
          : `  honored verdict: none${s.priorVerdicts.length > 0 ? " (latest verdict superseded by newer evidence)" : ""}`,
      );
    }
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
      console.log(`\n  prior verdicts (latest first):`);
      for (const v of s.priorVerdicts) {
        const body =
          "unparseable" in v.verdict
            ? "(unparseable raw)"
            : `${v.verdict.kind}${v.verdict.pinned_close_date ? ` → ${v.verdict.pinned_close_date}` : ""} by ${v.verdict.operator} (${v.verdict.reviewer}): ${v.verdict.note}`;
        console.log(`    ${v.fetched_at}  ${body}`);
      }
    }
  } else {
    const out = await resolveWindow(sql, resolveArgs!);
    const w = out.result.window;
    const bound = resolveArgs!.expect !== undefined;
    console.log(
      out.inserted
        ? `✅ ${resolveArgs!.kind} written by ${resolveArgs!.operator} as ${resolveArgs!.reviewer} (evidence: ${out.reviewedHashes.length} source hash(es)${bound ? ", bound by --expect" : ""})`
        : `↩︎ identical verdict already latest for this window — deduped, re-derived anyway`,
    );
    console.log(
      `re-derived: confidence=${w.confidence} status=${w.status} flags=[${w.conflict_flags.join(",")}]`,
    );
    console.log(
      `  close: ${w.resolved_close_display ?? "(none)"} (utc: ${w.resolved_close_utc ?? "null"})`,
    );
    if (resolveArgs!.kind === "escalate") {
      console.log(
        out.honored
          ? "⏸ escalation recorded and PARKED — by design the window still derives purely from sources (it stays in the queue, flagged [escalated]) until a human supersedes this verdict or new evidence un-parks it."
          : "⚠ escalation NOT honored (newer source evidence arrived, or raw failed to parse) — the item is not parked. `review show` to inspect.",
      );
    } else if (!out.honored) {
      console.log(
        "⚠ verdict NOT honored (new source evidence invalidated the review, or raw failed to parse) — the window derives purely from sources. `review show` to inspect.",
      );
    }
  }
} catch (err) {
  // Operator tool: expected refusals (unknown ocd-id, contract violations, --expect mismatch) print
  // their MESSAGE, not a stack trace (#117 Copilot). The message text is written to be self-explanatory.
  console.error(
    `review ${command}: ${err instanceof Error ? err.message : String(err)}`,
  );
  process.exitCode = 1;
} finally {
  await sql.end();
}
