/**
 * export-accuracy-miss.ts — snapshot ONE window's verification evidence into a committed replay
 * fixture (slice V, PR-V2: "every miss becomes a regression test").
 *
 * Given an ocd_id — from a V1 miss (`accuracy_records.was_correct = false`), a V2 `our_bug` triage
 * in `spikes/out/XCHECK_diff.md`, or any window worth pinning — this exports EXACTLY the inputs the
 * verifier's evaluateWatch assembles for computeVerdict (src/verify/run.ts):
 *   • the verification_watch at-close snapshot (the close CLAIM under judgment),
 *   • the projection's current close + status,
 *   • every observation fetched strictly post-close, via BOTH linkage paths (primary ocd_id +
 *     the observation_targets M:N fan-out — the EPA multi-docket lesson),
 *   • the regs_poll_watch confirmed-check stamp,
 * plus the live accuracy_record (reference, if one exists) and an `expected` verdict block.
 *
 * `expected` is the GOLD LABEL, same discipline as eval/chain-gold.json: it is INITIALIZED from
 * the live record's verdict (or computeVerdict at export time if no record exists yet) and then
 * HAND-CORRECTED to the true verdict when the fixture pins a bug. That's the loop: for an our_bug
 * find, the committed fixture's corrected `expected` makes test/accuracy-misses.test.ts FAIL until
 * the verdict/reconcile fix lands — and forever after guards the regression.
 *
 * SAFE: read-only on Postgres; writes only eval/accuracy-misses/<frDocNum>.v<version>.json
 * (committed). Never overwrites an existing fixture without --force; a window carrying multiple
 * watch versions requires an explicit --version choice.
 *
 * Run:  DATABASE_URL=… pnpm --filter @yokel/docketclock export:accuracy-miss -- <ocd_id> [--version N] [--force]
 *       (DATABASE_URL via the usual local port-forward of the docketclock Postgres)
 */
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createClient } from "../src/db/client.js";
import {
  classifyHorizon,
  DEFAULT_HORIZON_POLICY,
} from "../src/verify/select.js";
import {
  computeVerdict,
  type PostCloseObservation,
} from "../src/verify/verdict.js";

const envPath = fileURLToPath(new URL("../../../.env", import.meta.url));
if (existsSync(envPath)) process.loadEnvFile(envPath);

const FIXTURE_DIR = fileURLToPath(
  new URL("../eval/accuracy-misses/", import.meta.url),
);

const ocdId = process.argv
  .slice(2)
  .find((a) => a.startsWith("ocd-participation-window/"));
if (!ocdId) {
  console.error(
    "usage: pnpm --filter @yokel/docketclock export:accuracy-miss -- <ocd-participation-window/...> [--version N] [--force]",
  );
  process.exit(1);
}
// A reopened-and-reclosed window carries MULTIPLE watch versions, each a distinct claim
// (adversary RB-2): silently exporting the latest could snapshot a different claim than the miss
// the operator meant to pin — so when several exist the version must be chosen explicitly.
const versionFlag = process.argv.indexOf("--version");
let requestedVersion: number | null = null;
if (versionFlag !== -1) {
  const raw = process.argv[versionFlag + 1];
  // Strict integer check (Copilot #4): `--version --force` would otherwise coerce "--force" to
  // NaN and surface as a baffling "no verification_watch vNaN" error.
  if (raw === undefined || !/^\d+$/.test(raw)) {
    console.error(
      `--version requires a non-negative integer, got ${raw === undefined ? "nothing" : `"${raw}"`}`,
    );
    process.exit(1);
  }
  requestedVersion = Number(raw);
}
const FORCE = process.argv.includes("--force");

async function main(): Promise<void> {
  const sql = createClient();
  try {
    // The watch row IS the claim under judgment; without one the window never closed in the
    // verifier's eyes and there is nothing to replay.
    const watches = await sql<
      Array<{
        window_version: number;
        confidence_at_close: string;
        published_close_utc: Date;
        published_close_display: string | null;
        snapshotted_at: Date;
      }>
    >`
      select window_version, confidence_at_close, published_close_utc,
             published_close_display, snapshotted_at
      from verification_watch
      where ocd_id = ${ocdId}
      order by window_version desc
    `;
    if (watches.length === 0)
      throw new Error(
        `no verification_watch row for ${ocdId} — the window has no snapshotted close to judge`,
      );
    let watch = watches[0];
    if (requestedVersion !== null) {
      const found = watches.find((w) => w.window_version === requestedVersion);
      if (!found)
        throw new Error(
          `no verification_watch v${requestedVersion} for ${ocdId} — available: ${watches
            .map((w) => `v${w.window_version}`)
            .join(", ")}`,
        );
      watch = found;
    } else if (watches.length > 1) {
      throw new Error(
        `${ocdId} carries ${watches.length} watch versions (${watches
          .map((w) => `v${w.window_version}`)
          .join(
            ", ",
          )}) — each is a distinct claim; pass --version N to pick the one under judgment`,
      );
    }
    const publishedCloseIso = watch.published_close_utc.toISOString();

    const windows = await sql<
      Array<{
        fr_document_number: string | null;
        regs_document_id: string | null;
        resolved_close_utc: Date | null;
        status: string;
        last_checked_at: Date | null;
      }>
    >`
      select w.fr_document_number, w.regs_document_id,
             w.resolved_close_utc, w.status, pw.last_checked_at
      from participation_windows w
      left join regs_poll_watch pw on pw.regs_document_id = w.regs_document_id
      where w.ocd_id = ${ocdId}
    `;
    if (windows.length === 0) throw new Error(`no window row for ${ocdId}`);
    const win = windows[0];

    // Identical shape + linkage paths as evaluateWatch (src/verify/run.ts).
    const postClose = await sql<
      Array<{
        observation_id: string;
        fetched_at: Date;
        is_extension: boolean;
        is_correction: boolean;
        is_withdrawal: boolean;
        is_reopening: boolean;
      }>
    >`
      select distinct o.observation_id, o.fetched_at,
             o.is_extension, o.is_correction, o.is_withdrawal, o.is_reopening
      from observations o
      left join observation_targets t on t.observation_id = o.observation_id
      where (o.ocd_id = ${ocdId} or t.ocd_id = ${ocdId})
        and o.fetched_at > ${publishedCloseIso}
      order by o.fetched_at asc, o.observation_id asc
    `;

    const records = await sql<
      Array<{
        was_correct: boolean | null;
        basis: string;
        contradicting_observation_ids: string[];
        verified_at_utc: Date;
      }>
    >`
      select was_correct, basis, contradicting_observation_ids, verified_at_utc
      from accuracy_records
      where ocd_id = ${ocdId} and window_version = ${watch.window_version}
    `;
    const record = records[0] ?? null;

    const observationsSinceClose: PostCloseObservation[] = postClose.map(
      (o) => ({
        observation_id: o.observation_id,
        fetched_at: o.fetched_at.toISOString(),
        is_extension: o.is_extension,
        is_correction: o.is_correction,
        is_withdrawal: o.is_withdrawal,
        is_reopening: o.is_reopening,
      }),
    );

    // lapsed: from the live record when one exists (ground truth of what the verifier decided).
    // On the no-record path, mirror evaluateWatch EXACTLY (adversary RB-3): assemble the
    // confirmed-check instant from post-close observations + the regs_poll_watch stamp, apply the
    // snapshotBornLapsed guard, then classify. Feeding classifyHorizon a bare null check would
    // mark a checked-but-unjudged window lapsed=true — poisoning the REPLAY INPUT itself
    // (computeVerdict({lapsed:true}) abstains unconditionally, so no hand-corrected gold could
    // ever pass).
    let lapsed: boolean;
    let horizonStateAtExport: string;
    if (record) {
      lapsed = record.basis === "unverified_lapsed";
      horizonStateAtExport = "verdict_already_recorded";
    } else {
      const closeMs = watch.published_close_utc.getTime();
      let confirmedCheckAt: string | null = null;
      const candidates: Date[] = [
        ...postClose.map((o) => o.fetched_at),
        ...(win.last_checked_at ? [win.last_checked_at] : []),
      ];
      for (const c of candidates) {
        if (
          c.getTime() > closeMs &&
          (confirmedCheckAt === null ||
            c.getTime() > Date.parse(confirmedCheckAt))
        )
          confirmedCheckAt = c.toISOString();
      }
      const snapshotBornLapsed =
        watch.snapshotted_at.getTime() > closeMs + DEFAULT_HORIZON_POLICY.capMs;
      horizonStateAtExport = snapshotBornLapsed
        ? "due_lapsed"
        : classifyHorizon(
            { publishedCloseUtc: publishedCloseIso, confirmedCheckAt },
            new Date(),
            DEFAULT_HORIZON_POLICY,
          );
      lapsed = horizonStateAtExport === "due_lapsed";
      // A window that is NOT yet due a verdict can still be exported (pinning a live bug demo is a
      // legit workflow) — but the auto-initialized gold below comes from the SAME computeVerdict
      // call it asserts against, so it is trivially green while the claim is still provisional
      // (Claude review #1). Say so loudly, and stamp the state into the fixture.
      if (
        horizonStateAtExport !== "due_verdict" &&
        horizonStateAtExport !== "due_lapsed"
      )
        console.warn(
          `WARN ${ocdId} is "${horizonStateAtExport}" — the verifier would NOT write a verdict yet; the auto-initialized \`expected\` is provisional, not gold. Hand-review it before committing this fixture.`,
        );
    }

    const replayInput = {
      publishedCloseUtc: publishedCloseIso,
      currentCloseUtc: win.resolved_close_utc?.toISOString() ?? null,
      currentStatus: win.status,
      observationsSinceClose,
      lapsed,
    };

    const fixture = {
      // metadata (the replay test ignores everything in here)
      meta: {
        exported_at: new Date().toISOString(),
        ocd_id: ocdId,
        fr_document_number: win.fr_document_number,
        regs_document_id: win.regs_document_id,
        window_version: watch.window_version,
        confidence_at_close: watch.confidence_at_close,
        published_close_display: watch.published_close_display,
        snapshotted_at: watch.snapshotted_at.toISOString(),
        last_checked_at: win.last_checked_at?.toISOString() ?? null,
        // The horizon state the window was in when exported: "verdict_already_recorded", or the
        // classifyHorizon state on the no-record path. Anything other than due_verdict/due_lapsed
        // means the auto-initialized `expected` was provisional at export time.
        horizon_state_at_export: horizonStateAtExport,
        live_accuracy_record: record
          ? {
              was_correct: record.was_correct,
              basis: record.basis,
              contradicting_observation_ids:
                record.contradicting_observation_ids,
              verified_at_utc: record.verified_at_utc.toISOString(),
            }
          : null,
        note: "",
      },
      // computeVerdict input, verbatim (src/verify/verdict.ts VerdictInput)
      input: replayInput,
      // GOLD — hand-correct this block when the fixture pins a bug; the replay test asserts
      // computeVerdict(input) matches it on every Verdict field.
      expected: record
        ? {
            was_correct: record.was_correct,
            basis: record.basis,
            contradicting_observation_ids: record.contradicting_observation_ids,
          }
        : computeVerdict(replayInput),
    };

    // Filename: frDocNum when the window has one; otherwise the sanitized ocd tail (regs-only ids
    // carry a "regs:" prefix that would be hostile in a filename).
    const stem = (
      win.fr_document_number ??
      ocdId.split("/").pop() ??
      "unknown"
    ).replace(/[^A-Za-z0-9_-]/g, "-");
    mkdirSync(FIXTURE_DIR, { recursive: true });
    // The watch VERSION is part of the name (adversary RB-2): a re-closed window's second verdict
    // must never overwrite the committed regression fixture of the first miss.
    const path = resolve(FIXTURE_DIR, `${stem}.v${watch.window_version}.json`);
    if (existsSync(path) && !FORCE)
      throw new Error(
        `${path} already exists — a committed fixture is a pinned regression; pass --force only to deliberately refresh it`,
      );
    writeFileSync(path, JSON.stringify(fixture, null, 2) + "\n");
    console.log(`wrote ${path}`);
    console.log(
      `expected (${record ? "from live accuracy_record" : "computed at export — no record yet"}):`,
      JSON.stringify(fixture.expected),
    );
    console.log(
      "if this fixture pins a bug, hand-correct `expected` to the TRUE verdict — the replay test then fails until the fix lands.",
    );
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((err) => {
  console.error("export failed:", err);
  process.exit(1);
});
