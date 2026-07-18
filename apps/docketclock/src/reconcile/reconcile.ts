/**
 * The reconciliation engine — the PURE, deterministic confidence rulebook (no DB, no hidden clock).
 *
 * Reads the Observation chain for a SINGLE ocd_id and derives a contract-valid ParticipationWindow plus
 * an optional ConflictRecord. Confidence is NEVER ML/LLM-scored (docs/architecture/docketclock.md
 * "Confidence model") — this is a fixed rulebook. The marquee rule: compare FR comments_close_on and
 * Regs.gov commentEndDate by normalizing BOTH to America/New_York calendar date. Same Eastern date =>
 * agree => HIGH (with an INFORMATIONAL tz_normalization_only marker when they differ only in their UTC
 * calendar day — the FR-2018-27875 artifact); a real Eastern-day difference OR cross-source
 * withdrawn-vs-open => CONFLICTING.
 *
 * Determinism: `now` is injectable so tests pin every timestamp; it is used only for the engine's own
 * stamps (detected_at / change-tracking), never read off a wall clock implicitly.
 *
 * The result is validated against the frozen contract (ParticipationWindow.parse / ConflictRecord.parse)
 * before returning, so this engine can NEVER emit an illegal window — e.g. tz_normalization_only paired
 * with conflicting, or a null close with HIGH (both forbidden by the contract superRefine).
 */
import {
  ConflictRecord,
  ParticipationWindow,
  type ConflictFlag,
  type Confidence,
  type Observation,
  type OcdId,
  type WindowStatus,
} from "@yokel/contracts";
import { extractFr, extractRegs } from "./extract.js";
import {
  easternCalendarDate,
  frCloseDateToUtcInstant,
  utcCalendarDate,
} from "./eastern-date.js";

/** Pins the rulebook version — bump on any rule change (mirrors PARSER_VERSION in the adapters). */
export const RECONCILER_VERSION = "reconcile-v1.1";

export interface ReconcileResult {
  window: ParticipationWindow;
  conflict: ConflictRecord | null;
}

/** Latest observation of a given source, compared by PARSED epoch-ms (not lexicographic string). */
function latestBySource(
  observations: Observation[],
  source: Observation["source"],
): Observation | null {
  // The Observation contract pins fetched_at to z.string().datetime() (UTC "…Z"), so lexicographic and
  // epoch ordering agree today — but epoch compare stays correct if that ever loosens to allow offsets.
  let latest: Observation | null = null;
  for (const o of observations) {
    if (o.source !== source) continue;
    if (
      !latest ||
      new Date(o.fetched_at).getTime() > new Date(latest.fetched_at).getTime()
    )
      latest = o;
  }
  return latest;
}

/** Build the govinfo legal-reliance URL only when BOTH FR publication date + doc number are present. */
function govinfoUrl(
  publicationDate: string | null,
  documentNumber: string | null,
): string | null {
  // Pattern source: docs/architecture/docketclock.md ("Data sources" — the legal-reliance backstop):
  //   https://www.govinfo.gov/content/pkg/FR-{YYYY-MM-DD}/html/{frDocNum}.htm
  if (!publicationDate || !documentNumber) return null;
  return `https://www.govinfo.gov/content/pkg/FR-${publicationDate}/html/${documentNumber}.htm`;
}

/**
 * ISO+offset (or "…Z") Regs commentEndDate -> a canonical UTC "…Z" instant. null on a bad date.
 *
 * Symmetric with the FR path's asCalendarDate (extract.ts): besides rejecting NaN, we require the parsed
 * instant to round-trip to the date portion of the input string. `new Date("2026-02-30…")` silently rolls
 * over to Mar 2 — that fabricated instant must NEVER become an operative close, so a rolled-over
 * commentEndDate is treated as ABSENT (null) and the rulebook degrades to UNKNOWN rather than surfacing a
 * date the source never asserted.
 *
 * The round-trip is offset-AWARE: we compare the input's leading YYYY-MM-DD against the parsed instant's
 * calendar components IN THE INPUT'S OWN timezone (UTC for a "…Z" or +00:00 input; the stated offset
 * otherwise). Regs.gov v4 returns UTC ("…Z") per docketclock.md ("responses UTC"), but parsing the offset
 * keeps a legitimate offset-bearing value (where the local date legitimately differs from its UTC date)
 * from being falsely rejected.
 */
function regsCloseToUtc(commentEndDate: string | null): string | null {
  if (!commentEndDate) return null;
  const d = new Date(commentEndDate);
  if (Number.isNaN(d.getTime())) return null;
  // Round-trip guard against silent rollover (e.g. 2026-02-30 -> Mar 2).
  const m =
    /^(\d{4})-(\d{2})-(\d{2})(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$/.exec(
      commentEndDate,
    );
  if (m) {
    const [, y, mo, dd, tz] = m;
    // Shift the instant into the input's own offset frame, then read its UTC components there.
    let offsetMinutes = 0; // default / "Z" / "+00:00" => UTC
    if (tz && tz !== "Z") {
      const om = /^([+-])(\d{2}):?(\d{2})$/.exec(tz);
      if (om) {
        const sign = om[1] === "-" ? -1 : 1;
        offsetMinutes = sign * (Number(om[2]) * 60 + Number(om[3]));
      }
    }
    const local = new Date(d.getTime() + offsetMinutes * 60_000);
    if (
      local.getUTCFullYear() !== Number(y) ||
      local.getUTCMonth() !== Number(mo) - 1 ||
      local.getUTCDate() !== Number(dd)
    )
      return null;
  }
  return d.toISOString();
}

export function reconcile(
  observations: Observation[],
  now: Date = new Date(),
): ReconcileResult {
  if (observations.length === 0)
    throw new Error("reconcile: no observations supplied");

  // All observations MUST share one ocd_id — a mixed array is a caller bug (reconcileOcdId queries by id).
  const ocdId = observations[0]!.ocd_id;
  for (const o of observations) {
    if (o.ocd_id !== ocdId)
      throw new Error(
        `reconcile: observations span multiple ocd_ids ("${ocdId}" vs "${o.ocd_id}")`,
      );
  }

  const fr = latestBySource(observations, "federal_register");
  const regs = latestBySource(observations, "regulations_gov");

  const frFields = fr ? extractFr(fr.raw) : null;
  const regsFields = regs ? extractRegs(regs.raw) : null;

  // ── normalize both sources' close to comparable forms ──────────────────────────────────────────
  const frEastern = frFields?.commentsCloseOn ?? null; // already an Eastern date-only string
  const regsCloseUtcInstant = regsCloseToUtc(
    regsFields?.commentEndDate ?? null,
  );
  const regsEastern = regsCloseUtcInstant
    ? easternCalendarDate(new Date(regsCloseUtcInstant))
    : null;
  const regsUtc = regsCloseUtcInstant
    ? utcCalendarDate(new Date(regsCloseUtcInstant))
    : null;

  const nowIso = now.toISOString();

  // identifiers / linkage carried on every window
  const frDocNum = fr?.fr_document_number ?? regs?.fr_document_number ?? null;
  const regsDocumentId = regs?.regs_document_id ?? fr?.regs_document_id ?? null;
  const regsObjectId = regs?.regs_object_id ?? fr?.regs_object_id ?? null;
  const docketId = Array.from(
    new Set([
      ...(frFields?.docketIds ?? []),
      ...(regsFields?.docketId ? [regsFields.docketId] : []),
    ]),
  );
  const rin = frFields?.rin ?? null;
  const govinfo = govinfoUrl(
    frFields?.publicationDate ?? null,
    frFields?.documentNumber ?? frDocNum,
  );
  const submissionUrl = frFields?.commentUrl ?? null;
  const currentObservationIds = [
    fr?.observation_id,
    regs?.observation_id,
  ].filter((x): x is string => typeof x === "string");

  // ── the rulebook — produce confidence, flags, resolved close, status ─────────────────────────────
  let confidence: Confidence;
  let conflictFlags: ConflictFlag[] = [];
  let resolvedCloseUtc: string | null = null;
  let resolvedCloseDisplay: string | null = null;
  let conflict: ConflictRecord | null = null;

  const frHasDate = frEastern !== null;
  const regsHasDate = regsEastern !== null;
  const regsWithdrawn = regsFields?.withdrawn === true;
  // CROSS-SOURCE "reads open": the OTHER source (FR) is present AND reads open (a valid close date).
  // Strictly cross-source — Regs's OWN openForComment is NOT counted, so withdrawn_vs_open only fires
  // when BOTH observations exist, which guarantees a ConflictRecord can always be emitted for it
  // (suppression is never silence). A Regs-only / internally-contradictory withdrawal is handled below.
  const frReadsOpen = fr !== null && frHasDate;

  // The FR date-only close, resolved to its 11:59:59 p.m. ET operative instant (the convention).
  const frResolvedUtc = frEastern ? frCloseDateToUtcInstant(frEastern) : null;
  // Like regsDisplay, the display MUST carry the calendar date — this string is the human-readable
  // close, and a reader gets no second field to consult (v1 omitted the date; every FR-only row
  // rendered as a time with no day. reconcile-v1.1).
  const frDisplay = (d: string) =>
    `closes ${d} at 11:59 p.m. ET (inferred from FR date-only value)`;
  const regsDisplay = (d: string) => `closes ${d} (per Regulations.gov)`;

  if (regsWithdrawn && frReadsOpen) {
    // ── CONFLICTING — withdrawn_vs_open (strictly CROSS-SOURCE) ──────────────────────────────────────
    // Regs marks the notice withdrawn while the OTHER source (FR) reads open. A real cross-source
    // disagreement, not a tz artifact. Because BOTH observations exist (fr && regs), a ConflictRecord is
    // ALWAYS emitted below — never a silent CONFLICTING. We surface the disputed close rather than null
    // (the contract permits a non-null close on CONFLICTING).
    //
    // NOTE(issue #18): This flag is wired and fully tested, but PRODUCTION will not surface it until
    // issue #18 (poll-loop withdrawal re-poll) lands — the differential poll's withinCommentPeriod=true
    // filter drops a notice the moment it's withdrawn, so no withdrawn:true observation reaches the log
    // yet. The reconcile rule is correct today; the OBSERVATION that triggers it can't yet arrive.
    confidence = "conflicting";
    conflictFlags = ["withdrawn_vs_open"];
    resolvedCloseUtc = regsCloseUtcInstant ?? frResolvedUtc;
    resolvedCloseDisplay = regsCloseUtcInstant
      ? regsDisplay(regsEastern!)
      : frHasDate
        ? frDisplay(frEastern!)
        : null;
  } else if (regsWithdrawn) {
    // ── WITHDRAWN — Regs-only / internally-contradictory withdrawal (NOT a cross-source conflict) ────
    // Regs says withdrawn but the OTHER source does not read open (no FR open signal) — including the
    // Regs-alone `withdrawn===true && openForComment===true` self-contradiction. This is NOT a
    // cross-source conflict (no FR observation to disagree with), so it must NOT be CONFLICTING.
    // status=withdrawn and confidence dropped OUT of the push-eligible tiers: a withdrawn notice is
    // never push-eligible. LOW when a close date exists (resolved via the usual rules so the contract's
    // non-null-close requirement holds), else UNKNOWN (null close) when no date exists anywhere.
    const withdrawnClose = regsCloseUtcInstant ?? frResolvedUtc;
    if (withdrawnClose) {
      confidence = "low";
      resolvedCloseUtc = withdrawnClose;
      resolvedCloseDisplay = regsCloseUtcInstant
        ? regsDisplay(regsEastern!)
        : frDisplay(frEastern!);
    } else {
      confidence = "unknown";
      resolvedCloseUtc = null;
      resolvedCloseDisplay = null;
    }
  } else if (frHasDate && regsHasDate && frEastern !== regsEastern) {
    // ── CONFLICTING — fr_regs_date_mismatch ─────────────────────────────────────────────────────────
    // Both present and the Eastern calendar dates differ by >=1 day. A TRUE conflict (extension/
    // correction moved the date). Never also flag tz_normalization_only (contract forbids it with
    // conflicting). We carry the Regs close as the (disputed) operative value.
    confidence = "conflicting";
    conflictFlags = ["fr_regs_date_mismatch"];
    resolvedCloseUtc = regsCloseUtcInstant;
    resolvedCloseDisplay = regsDisplay(regsEastern!);
  } else if (frHasDate && regsHasDate && frEastern === regsEastern) {
    // ── HIGH — both sources agree on the SAME America/New_York calendar date ─────────────────────────
    // Eastern-date agreement = HIGH (product-ratified). When the close ALSO differs in its UTC calendar
    // day (frEastern !== regsUtc — the normal 11:59 p.m. ET close stored as the NEXT UTC day, the
    // FR-2018-27875 artifact), we ATTACH `tz_normalization_only` as an INFORMATIONAL marker. The
    // contract's superRefine permits tz_normalization_only with HIGH (it only forbids it with
    // CONFLICTING), so the window still passes ParticipationWindow.parse.
    const tzArtifact = frEastern !== regsUtc;
    if (regsFields?.openForComment === false) {
      // Eastern dates agree but Regs says NOT open for comment — degrade to MEDIUM (the contradiction-
      // free agreement is gone), keep the agreed close. Attach tz_normalization_only here too if the
      // UTC day differs.
      confidence = "medium";
      conflictFlags = tzArtifact ? ["tz_normalization_only"] : [];
      resolvedCloseUtc = regsCloseUtcInstant;
      resolvedCloseDisplay = regsDisplay(regsEastern!);
    } else {
      confidence = "high";
      conflictFlags = tzArtifact ? ["tz_normalization_only"] : [];
      resolvedCloseUtc = regsCloseUtcInstant;
      resolvedCloseDisplay = regsDisplay(regsEastern!);
    }
  } else if (regsHasDate && !frHasDate) {
    // ── MEDIUM — single source (Regs only) ──────────────────────────────────────────────────────────
    // One source with a usable close, no contradiction. allowLateComments=true creates a formal-close-
    // vs-practical-close ambiguity (docketclock.md MEDIUM row) -> surface late_comment_ambiguous.
    confidence = "medium";
    if (regsFields?.allowLateComments === true)
      conflictFlags = ["late_comment_ambiguous"];
    resolvedCloseUtc = regsCloseUtcInstant;
    resolvedCloseDisplay = regsDisplay(regsEastern!);
  } else if (
    regsFields?.commentEndDate == null &&
    regsFields?.openForComment === true
  ) {
    // ── LOW — null_end_date_open_status ─────────────────────────────────────────────────────────────
    // Regs commentEndDate null but openForComment=true (the FR 2025-03547 pattern). LOW REQUIRES a
    // non-null close (contract), so this is only LOW when FR supplies a fallback date (resolved via the
    // 11:59pm ET convention). With genuinely NO date anywhere it degrades to UNKNOWN (which forces a
    // null close). This is checked BEFORE the generic FR-only branch so the open-status flag wins over a
    // plain single-source verdict.
    if (frResolvedUtc) {
      confidence = "low";
      conflictFlags = ["null_end_date_open_status"];
      resolvedCloseUtc = frResolvedUtc;
      resolvedCloseDisplay = frDisplay(frEastern!);
    } else {
      confidence = "unknown";
      conflictFlags = ["null_end_date_open_status"];
      resolvedCloseUtc = null;
    }
  } else if (frHasDate && !regsHasDate) {
    // ── single source (FR only) ─────────────────────────────────────────────────────────────────────
    // If there is a Regs observation but it lacks a date (and did NOT hit the open-status branch above),
    // that is "one source, no contradiction" => MEDIUM. If there is NO Regs observation at all, this is
    // an FR-only date-only value with no cross-source / timezone resolution from the authority source
    // => LOW (docketclock.md LOW row).
    resolvedCloseUtc = frResolvedUtc;
    resolvedCloseDisplay = frDisplay(frEastern!);
    if (regs !== null) {
      confidence = "medium";
      if (regsFields?.allowLateComments === true)
        conflictFlags = ["late_comment_ambiguous"];
    } else {
      confidence = "low";
    }
  } else {
    // ── UNKNOWN — both structured deadline fields missing ───────────────────────────────────────────
    // Contract FORCES resolved_close_utc === null here (never coerce a guess).
    confidence = "unknown";
    resolvedCloseUtc = null;
    resolvedCloseDisplay = null;
  }

  // ── status (WindowStatus) — kept simple + documented ─────────────────────────────────────────────
  // withdrawn if Regs says so; else open if Regs openForComment OR a future close; else closed if the
  // close is in the past; else unknown.
  let status: WindowStatus;
  if (regsWithdrawn) {
    status = "withdrawn";
  } else if (
    regsFields?.openForComment === true ||
    (resolvedCloseUtc !== null && new Date(resolvedCloseUtc) > now)
  ) {
    status = "open";
  } else if (resolvedCloseUtc !== null && new Date(resolvedCloseUtc) <= now) {
    status = "closed";
  } else {
    status = "unknown";
  }

  // ── provenance — agreeing when corroborating, conflicting in the CONFLICTING cases ───────────────
  const isConflicting = confidence === "conflicting";
  const provenance = {
    agreeing_observation_ids: isConflicting ? [] : currentObservationIds,
    conflicting_observation_ids: isConflicting ? currentObservationIds : [],
  };

  const window: ParticipationWindow = {
    ocd_id: ocdId as OcdId,
    fr_document_number: frDocNum,
    regs_document_id: regsDocumentId,
    regs_object_id: regsObjectId,
    docket_id: docketId,
    rin,
    window_type: "comment",
    resolved_close_utc: resolvedCloseUtc,
    resolved_close_display: resolvedCloseDisplay,
    raw_fr_close_date: frEastern,
    raw_regs_close_datetime: regsFields?.commentEndDate ?? null,
    confidence,
    conflict_flags: conflictFlags,
    status,
    submission_url: submissionUrl,
    govinfo_url: govinfo,
    tags: [],
    version: 0,
    current_observation_ids: currentObservationIds,
    provenance,
    change_history: [],
  };

  // ── emit a ConflictRecord for the CONFLICTING cases (proof feed) ─────────────────────────────────
  // Every CONFLICTING verdict is now strictly cross-source (both observations present), so this guard
  // ALWAYS fires when isConflicting — suppression is never silence.
  if (isConflicting && fr && regs) {
    conflict = {
      ocd_id: ocdId as OcdId,
      observation_a_id: fr.observation_id,
      observation_b_id: regs.observation_id,
      source_a: fr.source,
      source_b: regs.source,
      // This per-ocd_id engine only ever emits CROSS-SOURCE (FR↔Regs, intra-window) conflicts: both
      // observations share `ocd_id`, so the 0.4.0 cross-window fields take their cross_source defaults
      // (ocd_id_b/govinfo_url_b null). The cross-window (chain) emission lives in the #31 chain pass.
      conflict_scope: "cross_source",
      ocd_id_b: null,
      govinfo_url_b: null,
      conflict_flags: conflictFlags,
      govinfo_url: govinfo,
      detected_at: nowIso,
    };
  }

  // INVARIANT: a CONFLICTING window MUST always carry a ConflictRecord (the proof feed can never be
  // silent on a conflict). This holds because withdrawn_vs_open and fr_regs_date_mismatch are the only
  // CONFLICTING branches and both require fr && regs present.
  if (isConflicting && !conflict)
    throw new Error(
      "reconcile: invariant violated — a CONFLICTING window produced no ConflictRecord (suppression must never be silence)",
    );

  // ── VALIDATE against the frozen contract — never emit an illegal window/conflict ─────────────────
  const wParsed = ParticipationWindow.safeParse(window);
  if (!wParsed.success)
    throw new Error(
      `reconcile: derived window failed the ParticipationWindow contract: ${JSON.stringify(wParsed.error.issues)}`,
    );
  if (conflict) {
    const cParsed = ConflictRecord.safeParse(conflict);
    if (!cParsed.success)
      throw new Error(
        `reconcile: derived conflict failed the ConflictRecord contract: ${JSON.stringify(cParsed.error.issues)}`,
      );
  }

  return { window: wParsed.data, conflict };
}
