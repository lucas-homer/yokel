/**
 * review/cli.ts — the operator review CLI (Slice R, PR-R3; review autopilot PR-A2/PR-A3): `queue` /
 * `show` / `resolve` / `log` / `corpus` over review/core.ts. CLI-first, operator-only by design
 * (locked decision) — the delivery API stays read-only; this is the ONLY write path for human_review
 * observations until the D5 console, and that console's spec is this CLI.
 *
 * Run (host-side, DATABASE_URL via the usual port-forward):
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review queue
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review show <ocd-id> [--blind]
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review resolve <ocd-id> \
 *     --kind pin_close --close 2026-09-20 --note "why" [--operator name] \
 *     [--reviewer human|agent] [--expect <sha256> --expect <sha256> …]
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review log [--reviewer agent] [--operator x] \
 *     [--kind k] [--since 7d|2026-10-01] [--limit 50] [--json]
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock review corpus [--json]
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
 *
 * log (PR-A3): the verdict ledger, newest first, each with its STANDING under the engine's honoring
 * rule (honored / parked / superseded / invalidated / unparseable). `--reviewer agent --since 7d` is
 * how an operator reads what the autopilot wrote this week without opening its thread.
 *
 * corpus (PR-A3): the shadow-gate corpus computed live — every window whose latest verdict is honored
 * now, grouped by what a blinded proposal must reproduce (pins → the date; escalations → `escalate`;
 * withdrawals → `confirm_withdrawn`). The harness feeds these ocd-ids to `show --blind`.
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

// Load the repo-root .env before env-reading imports (the poll/run.ts discipline).
const envPath = fileURLToPath(new URL("../../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const { createClient } = await import("../db/client.js");
const {
  reviewQueue,
  reviewShow,
  resolveWindow,
  reviewLog,
  reviewCorpus,
  corpusBlindIds,
  parseSince,
} = await import("./core.js");

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
      "  review log [--reviewer human|agent] [--operator <name>] [--kind <kind>]",
      "             [--since <N>h|<N>d|<N>w|YYYY-MM-DD] [--limit <n>] [--json]",
      "  review corpus [--blind] [--json]",
      `  kinds: ${KINDS.join(" | ")}`,
      "  --reviewer  who decided: human (default) or agent (unsupervised autopilot)",
      "  --expect    repeatable; the latest-per-source payload hashes you assessed (from `show`) —",
      "              the write refuses if the live evidence differs",
      "  --blind     hide prior verdicts; show the machine's own derivation of the sources",
      "  log         the verdict ledger, newest first, with each verdict's standing today",
      "  corpus      the shadow-gate corpus: honored verdicts grouped by what a blind proposal must reproduce;",
      "              --blind prints only the ids, flat and ungrouped (the proposer's view; the scorer reads the rest)",
    ].join("\n"),
  );
  process.exit(2);
}

// Validate EVERYTHING argument-side before opening a DB connection (#117 Copilot): `review` alone,
// a bad command, or missing flags must print usage — never a DATABASE_URL / connection error.
const [command, ...rest] = process.argv.slice(2);
if (
  command !== "queue" &&
  command !== "show" &&
  command !== "resolve" &&
  command !== "log" &&
  command !== "corpus"
)
  usage();
let showArgs: { ocdId: string; blind: boolean } | null = null;
let resolveArgs: {
  ocdId: string;
  kind: Kind;
  close?: string;
  note: string;
  operator: string;
  reviewer: Reviewer;
  expect?: string[];
} | null = null;
let logArgs: {
  reviewer?: Reviewer;
  operator?: string;
  kind?: Kind;
  since?: Date;
  limit?: number;
  json: boolean;
} | null = null;
let corpusArgs: { blind: boolean; json: boolean } | null = null;

function sinceOrExit(raw: string): Date {
  const d = parseSince(raw, new Date());
  if (d) return d;
  console.error(
    `review log: --since takes <N>h | <N>d | <N>w (N ≤ 100000) or a valid YYYY-MM-DD (got "${raw}")`,
  );
  process.exit(2);
}

try {
  if (command === "queue") {
    // No options yet: anything after `queue` is a typo, reported argument-side like every other.
    parseArgs({ args: rest, options: {} });
  }
  if (command === "show") {
    const ocdId = rest[0];
    if (!ocdId || ocdId.startsWith("--")) usage();
    const { values } = parseArgs({
      args: rest.slice(1),
      options: { blind: { type: "boolean" } },
    });
    showArgs = { ocdId, blind: values.blind === true };
  }
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
          `review resolve: --expect takes sha256 hex payload hashes as printed by \`review show\` (bad: ${bad.join(", ") || "(none given)"})` +
            (bad.some((h) => h.startsWith("fp"))
              ? " — a fingerprint= value is for the ledger skip only; pass the hash= values"
              : ""),
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

  if (command === "log") {
    const { values } = parseArgs({
      args: rest,
      options: {
        reviewer: { type: "string" },
        operator: { type: "string" },
        kind: { type: "string" },
        since: { type: "string" },
        limit: { type: "string" },
        json: { type: "boolean" },
      },
    });
    const reviewer = values.reviewer as Reviewer | undefined;
    if (reviewer !== undefined && !REVIEWERS.includes(reviewer)) {
      console.error(
        `review log: --reviewer must be one of ${REVIEWERS.join(" | ")} (got "${String(values.reviewer)}")`,
      );
      process.exit(2);
    }
    const kind = values.kind as Kind | undefined;
    if (kind !== undefined && !KINDS.includes(kind)) {
      console.error(
        `review log: --kind must be one of ${KINDS.join(" | ")} (got "${String(values.kind)}")`,
      );
      process.exit(2);
    }
    if (values.operator !== undefined && values.operator.trim().length === 0) {
      console.error("review log: --operator must not be empty");
      process.exit(2);
    }
    let limit: number | undefined;
    if (values.limit !== undefined) {
      limit = /^\d+$/.test(values.limit) ? Number(values.limit) : NaN;
      if (!Number.isSafeInteger(limit) || limit <= 0 || limit > 10_000) {
        console.error(
          `review log: --limit must be an integer from 1 to 10000 (got "${values.limit}")`,
        );
        process.exit(2);
      }
    }
    logArgs = {
      ...(reviewer !== undefined ? { reviewer } : {}),
      ...(values.operator !== undefined ? { operator: values.operator } : {}),
      ...(kind !== undefined ? { kind } : {}),
      ...(values.since !== undefined
        ? { since: sinceOrExit(values.since) }
        : {}),
      ...(limit !== undefined ? { limit } : {}),
      json: values.json === true,
    };
  }
  if (command === "corpus") {
    const { values } = parseArgs({
      args: rest,
      options: { blind: { type: "boolean" }, json: { type: "boolean" } },
    });
    corpusArgs = { blind: values.blind === true, json: values.json === true };
  }
} catch (err) {
  // parseArgs rejects unknown options and missing values with ERR_PARSE_ARGS_*: an operator typo,
  // reported as usage (still argument-side, still before any DB connection), not a stack trace.
  const code =
    err && typeof err === "object" && "code" in err ? String(err.code) : "";
  if (code.startsWith("ERR_PARSE_ARGS")) {
    console.error(
      `review ${command}: ${err instanceof Error ? err.message : String(err)}`,
    );
    usage();
  }
  throw err;
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
      `  conflicts: ${s.liveConflicts} live / ${s.blind ? "(retired: hidden in blind mode)" : `${s.retiredConflicts} retired`}; chain links: ${s.blind ? "(hidden in blind mode)" : String(s.chainLinks.length)}`,
    );
    const id = s.identity;
    console.log(
      `  identity: FR ${id.fr_document_number ?? "(none)"} — ${id.title ? JSON.stringify(id.title) : "(no title)"}` +
        ` — ${id.citation ?? "(no citation)"}${id.publication_date ? ` published ${id.publication_date}` : ""}` +
        ` — dockets [${id.docket_ids.join(", ")}] — RIN ${id.rins.length > 0 ? id.rins.join(", ") : "none"}` +
        `\n            Regs ${id.regs_document_id ?? "(none)"} — docket ${id.regs_docket_id ?? "(none)"} — frDocNum ${id.regs_fr_doc_num ?? "(none)"}` +
        (id.regs_title ? ` — ${JSON.stringify(id.regs_title)}` : ""),
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
      if (src.amendment_window) {
        // A linked amendment's observation (ADR 0016 §7): evidence about this window — pass it as --expect.
        console.log(
          `    linked amendment ${src.amendment_window.split("/").pop()} ${src.source} @ ${src.fetched_at}` +
            `\n      hash=${src.payload_hash}` +
            `\n      fingerprint=${src.fingerprint}`,
        );
        continue;
      }
      const closeField =
        src.source === "federal_register"
          ? "comments_close_on"
          : src.source === "regulations_gov"
            ? "commentEndDate"
            : "close";
      console.log(
        `    ${src.source} @ ${src.fetched_at}\n      ${closeField}=${src.close_value ?? "null"}` +
          ` withdrawn=${src.withdrawn ?? "n/a"} openForComment=${src.open_for_comment ?? "n/a"}` +
          ` flags[w/e/r]=${Number(src.is_withdrawal)}${Number(src.is_extension)}${Number(src.is_reopening)}` +
          `\n      hash=${src.payload_hash}` +
          // Ledger-skip comparison only (SKILL.md § Ledger) — never an --expect value.
          `\n      fingerprint=${src.fingerprint}`,
      );
    }
    if (s.context.length > 0) {
      // Not evidence about THIS window (ADR 0016): read it, but never pass it as --expect.
      console.log(
        `\n  context (not evidence for this window; not an --expect hash):`,
      );
      for (const c of s.context)
        console.log(
          `    ${c.source} @ ${c.fetched_at}\n      dates_text=${c.dates_text ?? "null"}`,
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
  } else if (command === "log") {
    const { json, ...filter } = logArgs!;
    const log = await reviewLog(sql, filter);
    if (json) {
      console.log(JSON.stringify(log, null, 2));
    } else {
      const applied = [
        filter.reviewer ? `reviewer=${filter.reviewer}` : null,
        filter.operator ? `operator=${filter.operator}` : null,
        filter.kind ? `kind=${filter.kind}` : null,
        filter.since ? `since=${filter.since.toISOString()}` : null,
        `limit=${filter.limit ?? 50}`,
      ]
        .filter((x) => x !== null)
        .join(" ");
      console.log(
        `review log: ${log.entries.length} verdict(s), newest first (${applied})` +
          (log.entries.length === 0 ? "" : "\n"),
      );
      for (const e of log.entries) {
        const body =
          "unparseable" in e.verdict
            ? "(unparseable raw)"
            : `${e.verdict.kind}${e.verdict.pinned_close_date ? ` → ${e.verdict.pinned_close_date}` : ""} by ${e.verdict.operator} (${e.verdict.reviewer})`;
        const note =
          "unparseable" in e.verdict
            ? ""
            : `\n    note: ${(e.verdict.note.length > 160 ? `${e.verdict.note.slice(0, 157)}…` : e.verdict.note).replace(/\r?\n/g, "\n          ")}`;
        console.log(
          `  ${e.fetched_at}  ${e.ocd_id}\n    ${body} — ${e.standing.toUpperCase()}${note}`,
        );
      }
      const fmt = (o: Record<string, number>) =>
        Object.entries(o)
          .filter(([, n]) => n > 0)
          .map(([k, n]) => `${k}=${n}`)
          .join(" ") || "(none)";
      console.log(
        `\nby kind: ${fmt(log.byKind)}\nby standing: ${fmt(log.byStanding)}` +
          (log.truncated
            ? `\n⚠ truncated at --limit ${filter.limit ?? 50}: more verdicts match — raise --limit before sampling or counting`
            : ""),
      );
    }
  } else if (command === "corpus") {
    const corpus = await reviewCorpus(sql);
    if (corpusArgs!.blind) {
      // The proposer's view: ids only, flat, ordered by sha256(id) — nothing about kind or expectation.
      const ids = corpusBlindIds(corpus);
      if (corpusArgs!.json) {
        console.log(
          JSON.stringify({ generated_at: corpus.generated_at, ids }, null, 2),
        );
      } else {
        console.log(
          `review corpus --blind: ${ids.length} id(s), order carries no information — propose on \`show <id> --blind\`; the scorer reads \`corpus --json\` afterwards`,
        );
        for (const id of ids) console.log(id);
      }
    } else if (corpusArgs!.json) {
      console.log(JSON.stringify(corpus, null, 2));
    } else {
      const line = (i: {
        ocd_id: string;
        expected_close: string | null;
        operator: string;
        reviewer: string;
        fetched_at: string;
      }) =>
        `    ${i.ocd_id}${i.expected_close ? `  expect ${i.expected_close}` : ""}  (${i.operator}, ${i.reviewer}, ${i.fetched_at.slice(0, 10)})`;
      console.log(
        `review corpus (shadow-gate harness, ADR 0015 §6) — generated ${corpus.generated_at}\n` +
          `  feed each ocd-id to \`review show <ocd-id> --blind\`; the expectation is what the blind proposal must reproduce.\n`,
      );
      console.log(
        `  part 1 — honored pins (${corpus.pins.length}): propose a date; expected = the pinned date`,
      );
      for (const i of corpus.pins) console.log(line(i));
      console.log(
        `\n  part 3 — escalation discipline: parked items (${corpus.escalations.length}) → expect \`escalate\`` +
          `; honored withdrawals (${corpus.withdrawals.length}) → expect \`confirm_withdrawn\``,
      );
      for (const i of corpus.escalations) console.log(line(i));
      for (const i of corpus.withdrawals) console.log(line(i));
      console.log(
        `\n  part 2 — the held-out set is the operator's sealed list of CURRENT queue items (runbook: Autopilot); not derivable from the DB.`,
      );
      console.log(
        `\n  not gated — other honored kinds (${corpus.other.length}); latest verdict not honored (${corpus.not_honored.length})`,
      );
      for (const i of corpus.other) console.log(`${line(i)}  ${i.kind}`);
      for (const i of corpus.not_honored)
        console.log(
          i.standing === "unparseable"
            ? `    ${i.ocd_id}  (latest verdict ${i.fetched_at.slice(0, 10)})  unparseable raw`
            : `    ${i.ocd_id}  ${i.kind}${i.expected_close ? ` ${i.expected_close}` : ""} by ${i.operator} (${i.reviewer}, ${i.fetched_at.slice(0, 10)})  ${i.standing} — nothing expected`,
        );
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
