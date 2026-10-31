/**
 * review/fingerprint.ts — the DECISION FINGERPRINT `review show` prints beside each `hash=`.
 *
 * Why it exists: a payload hash covers the whole raw source document, and Regulations.gov bumps
 * `data.attributes.modifyDate` on almost every daily fetch (8,618 of 8,795 consecutive Regs
 * observation pairs on 2026-10-31) without any other change. The review autopilot's shadow ledger
 * skips an item it has already decided only while the evidence is unchanged, so matching on payload
 * hashes made it re-verify the same pins every day.
 *
 * What it is: sha256 over the evidence the engine itself treats as evidence. For a Regulations.gov
 * observation that is the observation envelope plus `evidenceRaw(raw)` — the exact normalization the
 * honor-the-verdict rule uses (`sameReviewedRegsEvidence`, ADR 0010), which drops only `modifyDate`
 * and `links.self`. Every other field (dates and their time of day, withdrawn, open/closed flags,
 * document/docket/FR identity, title, abstract, attachments, unknown keys) stays in. For every other
 * source the engine applies no normalization, so the fingerprint is derived from the payload hash and
 * moves exactly when it does. A false skip is worse than a re-check: when in doubt, a field stays in.
 *
 * What it is NOT: an `--expect` hash. Writes stay bound to payload hashes (ADR 0015); the fingerprint
 * only decides whether the shadow ledger may skip re-investigating an item.
 *
 * Versioned (`fp1:`): a fingerprint is only ever compared with one of the same version; ledger lines
 * written before fingerprints existed match by payload hash only (`ledgerSkip`).
 */
import { createHash } from "node:crypto";
import { evidenceRaw } from "../reconcile/review-evidence.js";
import { canonicalize } from "../sources/payload.js";

export const FINGERPRINT_VERSION = "fp1";

/** The observation fields a fingerprint reads. Envelope fields are optional for linked-amendment rows. */
export interface FingerprintInput {
  source: string;
  payload_hash: string;
  /** Set for a linked amendment's row (ADR 0016 §7): the amendment document's own window. */
  amendment_window?: string;
  raw?: unknown;
  ocd_id?: string | null;
  fr_document_number?: string | null;
  regs_document_id?: string | null;
  regs_object_id?: string | null;
  parser_version?: string | null;
  raw_dates_text?: string | null;
  is_extension?: boolean | null;
  is_correction?: boolean | null;
  is_withdrawal?: boolean | null;
  is_reopening?: boolean | null;
}

export function decisionFingerprint(o: FingerprintInput): string {
  const normalizeRegs = o.source === "regulations_gov" && o.raw !== undefined;
  const material = {
    v: FINGERPRINT_VERSION,
    source: o.source,
    amendment_window: o.amendment_window ?? null,
    ocd_id: o.ocd_id ?? null,
    fr_document_number: o.fr_document_number ?? null,
    regs_document_id: o.regs_document_id ?? null,
    regs_object_id: o.regs_object_id ?? null,
    parser_version: o.parser_version ?? null,
    raw_dates_text: o.raw_dates_text ?? null,
    is_extension: o.is_extension ?? null,
    is_correction: o.is_correction ?? null,
    is_withdrawal: o.is_withdrawal ?? null,
    is_reopening: o.is_reopening ?? null,
    // Regs: the engine's evidence view of the raw payload. Anything else (or a Regs row without its
    // raw): the payload hash itself, so the fingerprint is exactly as sensitive as the hash.
    evidence: normalizeRegs
      ? evidenceRaw(o.raw)
      : { payload_hash: o.payload_hash },
  };
  return `${FINGERPRINT_VERSION}:${createHash("sha256").update(canonicalize(material), "utf8").digest("hex")}`;
}

export function fingerprintVersion(fp: string): string | null {
  const m = /^(fp\d+):[0-9a-f]{64}$/.exec(fp);
  return m ? m[1]! : null;
}

/** Order-insensitive equality of two string sets (no duplicates assumed; sizes must match). */
function sameSet(a: readonly string[], b: readonly string[]): boolean {
  if (a.length === 0 || a.length !== b.length) return false;
  const sb = new Set(b);
  return new Set(a).size === a.length && a.every((x) => sb.has(x));
}

/**
 * True iff two fingerprint sets are comparable (every entry well-formed and of ONE shared version)
 * and equal. Mixed or unknown versions never match — a re-check, never a silent skip.
 */
export function sameFingerprintSet(
  a: readonly string[],
  b: readonly string[],
): boolean {
  const versions = new Set([...a, ...b].map(fingerprintVersion));
  if (versions.size !== 1 || versions.has(null)) return false;
  return sameSet(a, b);
}

/** The ledger fields the skip rule reads (SKILL.md § Ledger). */
export interface LedgerLine {
  run: string;
  policy: string;
  harness: string | null;
  ocd_id: string;
  hashes: string[];
  /** Absent on lines written before fingerprints existed. */
  fingerprints?: string[];
  proposal: { kind: string };
}

export interface CurrentEvidence {
  ocd_id: string;
  policy: string;
  hashes: string[];
  fingerprints: string[];
  now: Date;
}

export type SkipDecision =
  | {
      skip: true;
      line: LedgerLine;
      matchedBy: "hashes" | "fingerprints";
      reason: string;
    }
  | { skip: false; reason: string };

const ESCALATE_SKIP_MS = 7 * 24 * 3600 * 1000;

/**
 * The shadow ledger skip rule (SKILL.md, Run procedure step 4), as a reference implementation.
 *
 * A previous scheduled line (harness null) for the same window and the same policy version, whose
 * evidence matches today's, skips the item: a pin_close / confirm_withdrawn proposal indefinitely, an
 * escalate for 7 days from its run; a skip never skips. The most recent matching decisive line
 * decides (`lines` in ledger order; equal run stamps resolve to the later line). Evidence matches
 * when the payload hash sets are equal, or when BOTH lines carry fingerprints of one version and
 * those sets are equal. A hash is
 * never compared with a fingerprint, so lines written before fingerprints existed match by hash only
 * (in practice: re-checked once, then fingerprinted).
 */
export function ledgerSkip(
  lines: readonly LedgerLine[],
  cur: CurrentEvidence,
): SkipDecision {
  // Most recent first. `run` is a per-run stamp shared by every line of that run, so ties fall back
  // to ledger (append) order: the later line wins.
  const candidates = lines
    .map((l, i) => ({ l, i }))
    .filter(
      ({ l }) =>
        l.harness === null &&
        l.ocd_id === cur.ocd_id &&
        l.policy === cur.policy,
    )
    .sort((a, b) => Date.parse(b.l.run) - Date.parse(a.l.run) || b.i - a.i)
    .map(({ l }) => l);
  for (const l of candidates) {
    const byHash = sameSet(l.hashes, cur.hashes);
    const byFp =
      !byHash &&
      Array.isArray(l.fingerprints) &&
      sameFingerprintSet(l.fingerprints, cur.fingerprints);
    if (!byHash && !byFp) continue;
    const matchedBy = byHash ? "hashes" : "fingerprints";
    const kind = l.proposal.kind;
    if (kind === "pin_close" || kind === "confirm_withdrawn")
      return {
        skip: true,
        line: l,
        matchedBy,
        reason: `${kind} proposed ${l.run.slice(0, 10)}, same ${matchedBy}`,
      };
    if (kind === "escalate") {
      if (cur.now.getTime() - Date.parse(l.run) < ESCALATE_SKIP_MS)
        return {
          skip: true,
          line: l,
          matchedBy,
          reason: `escalate proposed ${l.run.slice(0, 10)}, same ${matchedBy}`,
        };
      return {
        skip: false,
        reason: `escalate proposed ${l.run.slice(0, 10)} is 7+ days old: re-inspect`,
      };
    }
    // kind === "skip" (or anything unknown) never skips; an older decisive line may still apply.
  }
  return {
    skip: false,
    reason:
      candidates.length === 0
        ? "no previous line"
        : "evidence changed or no skipping line",
  };
}
