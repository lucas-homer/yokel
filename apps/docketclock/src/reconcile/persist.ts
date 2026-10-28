/**
 * Persist a reconciliation result into the DERIVED projections (0003) — and the entry point that reads
 * the Observation chain, runs the pure engine, and writes the result.
 *
 * ATOMICITY: the read (SELECT) + version-bump decision + participation_windows upsert + conflict_records
 * upsert + retirement UPDATE all run inside a SINGLE `sql.begin` transaction, so the projection and the
 * proof feed move together. A crash mid-sequence rolls the whole unit back rather than leaving the window
 * updated while the conflict feed is inconsistent.
 *
 * participation_windows is a re-derivable projection, so persisting is an UPSERT on ocd_id (NOT an
 * append). The ONE value we refuse to mutate silently is resolved_close_utc: when a re-derivation moves
 * the operative close, we BUMP `version` and APPEND a ChangeHistoryEntry (the PRIOR close + the prior
 * current_observation_ids + changed_at) to change_history — superseded deadlines live forever, exactly
 * as the contract intends. An unchanged close is an idempotent no-op refresh.
 *
 * conflict_records is INSERT-on-detection, deduped on the natural key (ocd_id, observation_a_id,
 * observation_b_id) per 0003 — re-running reconcile on the same disagreeing pair is an idempotent no-op
 * (it does NOT duplicate the row and does NOT bump the original detected_at). Stale/resolved conflicts
 * are RETIRED via a nullable resolved_at: when a re-derivation is no longer CONFLICTING, all still-open
 * rows for the ocd_id are stamped resolved_at=now; when it IS conflicting, the current pair is upserted
 * live (resolved_at=NULL) and any OTHER still-open (superseded) pair for the ocd_id is retired. The
 * proof feed publishes only live conflicts (resolved_at IS NULL).
 */
import type { Sql, SqlHandle } from "../db/client.js";
import type {
  ChangeHistoryEntry,
  Observation,
  ObservationSource,
  ParticipationWindow,
} from "@yokel/contracts";
import type { ReconcileResult } from "./reconcile.js";
import {
  RECONCILER_VERSION,
  reconcile,
  type ReconcileOptions,
} from "./reconcile.js";
import {
  chainAmbiguousPairs,
  chainReconcile,
  isAmendment,
  isKeywordFalsePositive,
  linkBasis,
  type ChainCandidate,
  type ChainConflict,
} from "./chain.js";
import { derivedIsCorrection, extractFr } from "./extract.js";
import {
  resolveAmendedClose,
  type AmendmentEvidence,
  type AmendmentInputs,
  type AmendmentOutcome,
} from "./amendment.js";
import type { Adjudicator } from "../adjudicator/port.js";
import { selectAdjudicator } from "../adjudicator/select.js";
import {
  adjudicateAmbiguousPairs,
  chainMaxEscalations,
} from "./chain-adjudicate.js";

export interface PersistResult {
  inserted: boolean; // true if this was a first-time insert of the window
  versionBumped: boolean; // true if resolved_close_utc changed and version advanced
}

interface StoredWindowRow {
  resolved_close_utc: string | null;
  version: number;
  change_history: ChangeHistoryEntry[];
  current_observation_ids: string[];
}

/** Compare two nullable close instants for equality (normalize via Date so offset/Z forms match). */
function sameClose(a: string | null, b: string | null): boolean {
  if (a === null || b === null) return a === b;
  const da = new Date(a).getTime();
  const db = new Date(b).getTime();
  return da === db;
}

export async function persistReconciliation(
  sql: Sql,
  result: ReconcileResult,
  now: Date = new Date(),
): Promise<PersistResult> {
  const { window, conflict } = result;

  // ATOMIC: the read-decide-version-bump and ALL writes (window upsert + conflict upsert/retirement)
  // run inside ONE transaction so the projection and the proof feed move together. A crash mid-sequence
  // can no longer leave the window updated while the conflict feed is stale/inconsistent — postgres.js
  // rolls the whole `begin` block back on any throw. `tx` is the transaction-scoped sql; every statement
  // below uses it (not the outer `sql`).
  return sql.begin(async (tx) => {
    // Read the currently-stored projection (if any) to decide insert-vs-update + version bump.
    const [stored] = await tx<StoredWindowRow[]>`
      select resolved_close_utc, version, change_history, current_observation_ids
      from participation_windows
      where ocd_id = ${window.ocd_id}
    `;

    let version = window.version;
    let changeHistory = window.change_history;
    let versionBumped = false;
    const inserted = !stored;

    if (stored) {
      const storedClose = stored.resolved_close_utc
        ? new Date(stored.resolved_close_utc).toISOString()
        : null;
      if (!sameClose(storedClose, window.resolved_close_utc)) {
        // The operative close moved — bump version + append the PRIOR close to change_history.
        version = stored.version + 1;
        const priorEntry: ChangeHistoryEntry = {
          version: stored.version,
          resolved_close_utc: storedClose,
          observation_ids: stored.current_observation_ids ?? [],
          changed_at: now.toISOString(),
        };
        changeHistory = [...(stored.change_history ?? []), priorEntry];
        versionBumped = true;
      } else {
        // Unchanged close: keep the stored version + history (idempotent refresh of the projection).
        version = stored.version;
        changeHistory = stored.change_history ?? [];
      }
    }

    const toPersist: ParticipationWindow = {
      ...window,
      version,
      change_history: changeHistory,
    };

    await tx`
      insert into participation_windows (
        ocd_id, fr_document_number, regs_document_id, regs_object_id, docket_id, rin,
        window_type, resolved_close_utc, resolved_close_display,
        raw_fr_close_date, raw_regs_close_datetime,
        confidence, conflict_flags, status, submission_url, govinfo_url, tags,
        version, current_observation_ids, provenance, change_history,
        reconciler_version, derived_at
      ) values (
        ${toPersist.ocd_id}, ${toPersist.fr_document_number}, ${toPersist.regs_document_id},
        ${toPersist.regs_object_id}, ${tx.json(toPersist.docket_id)}, ${toPersist.rin},
        ${toPersist.window_type}, ${toPersist.resolved_close_utc}, ${toPersist.resolved_close_display},
        ${toPersist.raw_fr_close_date}, ${toPersist.raw_regs_close_datetime},
        ${toPersist.confidence}, ${tx.json(toPersist.conflict_flags)}, ${toPersist.status},
        ${toPersist.submission_url}, ${toPersist.govinfo_url}, ${tx.json(toPersist.tags)},
        ${toPersist.version}, ${tx.json(toPersist.current_observation_ids)},
        ${tx.json(toPersist.provenance)}, ${tx.json(toPersist.change_history)},
        ${RECONCILER_VERSION}, ${now.toISOString()}
      )
      on conflict (ocd_id) do update set
        fr_document_number = excluded.fr_document_number,
        regs_document_id   = excluded.regs_document_id,
        regs_object_id     = excluded.regs_object_id,
        docket_id          = excluded.docket_id,
        rin                = excluded.rin,
        window_type        = excluded.window_type,
        resolved_close_utc = excluded.resolved_close_utc,
        resolved_close_display = excluded.resolved_close_display,
        raw_fr_close_date  = excluded.raw_fr_close_date,
        raw_regs_close_datetime = excluded.raw_regs_close_datetime,
        confidence         = excluded.confidence,
        conflict_flags     = excluded.conflict_flags,
        status             = excluded.status,
        submission_url     = excluded.submission_url,
        govinfo_url        = excluded.govinfo_url,
        tags               = excluded.tags,
        version            = excluded.version,
        current_observation_ids = excluded.current_observation_ids,
        provenance         = excluded.provenance,
        change_history     = excluded.change_history,
        reconciler_version = excluded.reconciler_version,
        derived_at         = excluded.derived_at
    `;

    // conflict_records — insert-on-detection, deduped on the disagreeing-pair natural key, with stale/
    // resolved-conflict RETIREMENT so the GET /conflicts proof feed never publishes dead conflicts.
    if (conflict) {
      // Current window is CONFLICTING. Upsert the current pair as LIVE (resolved_at = NULL); re-detecting
      // the SAME pair must NOT duplicate it and must NOT bump its original detected_at (idempotent
      // refresh of the metadata only — detected_at is the FIRST-detection stamp).
      // NULL-vs-'' SEAM (see 0006 header): the contract carries ocd_id_b as nullable (null for a
      // cross_source conflict — there is no side-B window), but the DB column is NOT NULL DEFAULT '' so
      // the widened unique key dedups cross_source rows (all share ''). Map contract null → DB ''.
      // reconcile emits only cross_source today, so conflict_scope is 'cross_source', ocd_id_b is '',
      // govinfo_url_b is null — but we read the fields off the ConflictRecord (defaults) so the seam is
      // already correct the moment a later slice begins emitting cross_window.
      const ocdIdB = conflict.ocd_id_b ?? "";
      await tx`
        insert into conflict_records (
          ocd_id, observation_a_id, observation_b_id, source_a, source_b,
          conflict_flags, govinfo_url, detected_at, resolved_at,
          conflict_scope, ocd_id_b, govinfo_url_b
        ) values (
          ${conflict.ocd_id}, ${conflict.observation_a_id}, ${conflict.observation_b_id},
          ${conflict.source_a}, ${conflict.source_b}, ${tx.json(conflict.conflict_flags)},
          ${conflict.govinfo_url}, ${conflict.detected_at}, ${null},
          ${conflict.conflict_scope}, ${ocdIdB}, ${conflict.govinfo_url_b}
        )
        on conflict (ocd_id, observation_a_id, observation_b_id, ocd_id_b) do update set
          conflict_flags = excluded.conflict_flags,
          govinfo_url    = excluded.govinfo_url,
          govinfo_url_b  = excluded.govinfo_url_b,
          resolved_at    = null
      `;
      // Retire every OTHER still-open conflict row for this ocd_id — a superseded pair (a newer
      // conflicting pair replaced it) must not linger live in the proof feed.
      //
      // SCOPED TO cross_source (#31 seam): a single-window FR↔Regs reconcile must NEVER collaterally
      // retire a cross_window/chain row that merely happens to name this ocd_id as side A. Such a row is
      // owned by a different (cross-window) detection pass, not by this FR↔Regs reconcile. This predicate
      // is a no-op today (no cross_window rows are emitted yet) but is the correct seam for the next slice.
      await tx`
        update conflict_records
          set resolved_at = ${now.toISOString()}
        where ocd_id = ${conflict.ocd_id}
          and resolved_at is null
          and conflict_scope = 'cross_source'
          and not (
            observation_a_id = ${conflict.observation_a_id}
            and observation_b_id = ${conflict.observation_b_id}
          )
      `;
    } else {
      // Current window is NOT conflicting — the conflict (if any) is RESOLVED. Retire ALL still-open
      // cross_source conflict rows for this ocd_id so the proof feed stops publishing a dead conflict.
      // SCOPED TO cross_source for the same reason as the supersede sweep above: a not-conflicting FR↔Regs
      // re-derivation must not retire a future cross_window row that shares this ocd_id as side A.
      await tx`
        update conflict_records
          set resolved_at = ${now.toISOString()}
        where ocd_id = ${window.ocd_id}
          and resolved_at is null
          and conflict_scope = 'cross_source'
      `;
    }

    return { inserted, versionBumped };
  });
}

export interface ReconcileOcdIdResult extends ReconcileResult {
  persist: PersistResult;
}

/**
 * loadObservations — the FULL Observation chain for one ocd_id, in the engine's deterministic read
 * order (fetched_at asc, observation_id asc), shaped as the contract carries it (fetched_at ISO).
 * Shared by reconcileOcdId and the review CLI (honoring, the blind derivation, escalation marks —
 * PR-A2) so every caller asks the engine about the SAME chain the projection was derived from.
 * Returns [] for an unknown ocd_id; the caller decides whether that is an error. Takes any handle,
 * so a caller can read the chain inside its own transaction (the review write's escalate check).
 */
export async function loadObservations(
  sql: SqlHandle,
  ocdId: string,
): Promise<Observation[]> {
  const rows = await sql<
    {
      observation_id: string;
      ocd_id: string;
      // Derived from the contract union (the #115 review note): a hand-listed union went stale the
      // moment 0.10.0 added human_review — and reconcile-v2 READS those rows, so a silent drop here
      // would silently disable supersedence for a future 5th source too.
      source: ObservationSource;
      fr_document_number: string | null;
      regs_document_id: string | null;
      regs_object_id: string | null;
      payload_hash: string;
      fetched_at: Date;
      parser_version: string;
      raw_dates_text: string | null;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
      raw: unknown;
    }[]
  >`
    select observation_id, ocd_id, source, fr_document_number, regs_document_id, regs_object_id,
           payload_hash, fetched_at, parser_version, raw_dates_text,
           is_extension, is_correction, is_withdrawal, is_reopening, raw
    from observations
    where ocd_id = ${ocdId}
    order by fetched_at asc, observation_id asc
  `;

  return rows.map((r) => ({
    ...r,
    // postgres.js returns timestamptz as a Date; the contract carries an ISO string.
    fetched_at:
      r.fetched_at instanceof Date ? r.fetched_at.toISOString() : r.fetched_at,
  }));
}

/** A latest-FR-observation row (plus its latest govinfo text) as the amendment loader reads it. */
export interface FrAmendmentRow {
  observation_id: string;
  ocd_id: string;
  fr_document_number: string | null;
  is_extension: boolean;
  is_correction: boolean;
  is_withdrawal: boolean;
  is_reopening: boolean;
  raw: unknown;
  govinfo_observation_id: string | null;
  govinfo_text: string | null;
  /** When this FR row / its latest govinfo row were fetched, and their payload hashes (§7 freshness + the review write's evidence binding). */
  fetched_at?: Date | string | null;
  payload_hash?: string | null;
  govinfo_fetched_at?: Date | string | null;
  govinfo_payload_hash?: string | null;
}

const toIso = (v: Date | string | null | undefined): string | null =>
  v instanceof Date ? v.toISOString() : (v ?? null);

/** One linked amendment observation the window's derivation reads — part of a verdict's evidence set. */
export interface AmendmentEvidenceRow {
  source: "federal_register" | "govinfo";
  /** the AMENDMENT document's window (not the window being derived). */
  ocd_id: string;
  observation_id: string;
  payload_hash: string;
  fetched_at: string | null;
}

/** Everything the amendment loader resolved for one window. */
export interface LoadedAmendment {
  outcome: AmendmentOutcome;
  /** the resolver's inputs (null when the window has no FR row / publication date / linked amendment). */
  inputs: AmendmentInputs | null;
  /** the linked amendments' latest FR + govinfo observations — evidence about THIS window (ADR 0016 §7). */
  evidenceRows: AmendmentEvidenceRow[];
}

/** The ReconcileOptions a derivation of this window passes (same log in, same window out). */
export function reconcileOptionsOf(l: LoadedAmendment): ReconcileOptions {
  return {
    amendment: l.outcome,
    ...(l.inputs ? { amendmentInputs: l.inputs } : {}),
  };
}

/** A ChainCandidate built from an FR row for identity checks only (status/close are not read by linkBasis). */
function identityCandidate(r: FrAmendmentRow): ChainCandidate {
  const fr = extractFr(r.raw);
  return {
    ocd_id: r.ocd_id,
    fr_observation_id: r.observation_id,
    fr_document_number: fr.documentNumber ?? r.fr_document_number,
    docket_ids: fr.docketIds,
    rin: fr.rin,
    rins: fr.rins,
    is_extension: r.is_extension,
    is_correction: derivedIsCorrection(r),
    is_withdrawal: r.is_withdrawal,
    is_reopening: r.is_reopening,
    title: fr.title,
    publication_date: fr.publicationDate,
    govinfo_url: null,
    dates_text: fr.datesText,
    status: "unknown",
    resolved_close_utc: null,
    citation: fr.citation,
    correction_of: fr.correctionOf,
    corrections: fr.corrections,
    govinfo_text: r.govinfo_text,
  };
}

/**
 * The amendment CORPUS: every FR and govinfo row — the full HISTORY, not only the latest (round 2,
 * finding 1) — of every window whose FR rows EVER carried an amendment signal (the four flags, or a
 * non-empty correction_of — the fr-v3 rule read off raw, so fr-v2 rows count). Every candidate B of
 * every window A is drawn from it; it is a pure function of the FR + govinfo rows of the log,
 * independent of A. Whether B is an amendment, and linked to A, is decided per STATE (its latest rows
 * as of a time), so a document whose latest row lost its flags is not an amendment NOW but was one
 * before — exactly what the verdict-freshness timeline needs.
 *
 * FR `raw` is SLIMMED to the fields the identity / resolver path reads (extractFr, the deny-list, the
 * correction rule); govinfo rows carry only their extracted text, so the corpus stays a few MB.
 */
interface CorpusFrRow {
  row: FrAmendmentRow; // govinfo_* fields null — attached per state (docStateAt)
  at: number; // fetched_at, epoch ms
}
interface CorpusGovRow {
  observation_id: string;
  at: number;
  fetched_at: Date | string;
  raw_dates_text: string | null;
  payload_hash: string;
}
interface CorpusDoc {
  ocd_id: string;
  fr: CorpusFrRow[]; // ascending (fetched_at, observation_id)
  gov: CorpusGovRow[]; // ascending
  /** unions over ALL rows — the prefilter must admit B if ANY of its states could link. */
  publication_dates: string[];
  docket_ids: Set<string>;
  correction_ofs: Set<string>;
  /** every FR dates text and govinfo text, whitespace-collapsed (the citation necessary condition). */
  texts: string[];
}
interface AmendmentCorpus {
  stamp: string;
  docs: CorpusDoc[];
}

/** B's rows as they stood at `atMs`: its latest FR row and latest govinfo row at or before it. */
function docStateAt(doc: CorpusDoc, atMs: number): FrAmendmentRow | null {
  let fr: CorpusFrRow | null = null;
  for (const r of doc.fr) if (r.at <= atMs) fr = r;
  if (!fr) return null;
  let gov: CorpusGovRow | null = null;
  for (const g of doc.gov) if (g.at <= atMs) gov = g;
  return {
    ...fr.row,
    govinfo_observation_id: gov?.observation_id ?? null,
    govinfo_text: gov?.raw_dates_text ?? null,
    govinfo_fetched_at: gov?.fetched_at ?? null,
    govinfo_payload_hash: gov?.payload_hash ?? null,
  };
}

/** The raw keys every reader downstream of the corpus consults (extractFr, isDenied, derivedIsCorrection). */
const CORPUS_RAW_KEYS = [
  "document_number",
  "publication_date",
  "title",
  "dates",
  "comments_close_on",
  "comment_url",
  "docket_ids",
  "regulation_id_numbers",
  "citation",
  "correction_of",
  "corrections",
] as const;

function slimRaw(raw: unknown): Record<string, unknown> {
  const src =
    raw && typeof raw === "object" && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : {};
  const out: Record<string, unknown> = {};
  for (const k of CORPUS_RAW_KEYS) if (k in src) out[k] = src[k];
  return out;
}

const collapseWs = (s: string) => s.replace(/\s+/g, " ");

/**
 * The freshness stamp of the corpus: the observations table's OID (a schema reset is a new table) plus
 * the row count and max fetched_at over exactly the FR + govinfo rows. The log is APPEND-ONLY (0001
 * rejects UPDATE / DELETE / TRUNCATE by trigger), so any change to what the corpus reads is an insert,
 * and every insert bumps the count. (The dev-only #O4 backfill, which disables that trigger to re-stamp
 * flags, is the one exception: restart any long-lived process after running it.) Index-only on 0013.
 */
async function corpusStamp(sql: SqlHandle): Promise<string> {
  const [r] = await sql<{ stamp: string }[]>`
    select 'observations'::regclass::oid::text || ':' || count(*)::text || ':' ||
           coalesce(max(fetched_at)::text, '') as stamp
    from observations
    where source in ('federal_register', 'govinfo')
  `;
  return r!.stamp;
}

async function buildAmendmentCorpus(
  sql: SqlHandle,
  stamp: string,
): Promise<AmendmentCorpus> {
  // Windows that EVER carried a signal (partial index 0013/3), then ALL their FR and govinfo rows in
  // time order (0013/1). govinfo `raw` (the whole page) is never read here — only its extracted text.
  const rows = await sql<
    {
      observation_id: string;
      ocd_id: string;
      source: "federal_register" | "govinfo";
      fr_document_number: string | null;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
      raw: unknown;
      raw_dates_text: string | null;
      fetched_at: Date;
      payload_hash: string;
    }[]
  >`
    with amend as (
      select distinct ocd_id from observations
      where source = 'federal_register'
        and (is_extension or is_correction or is_withdrawal or is_reopening
             or coalesce(raw->>'correction_of', '') <> '')
    )
    select o.observation_id, o.ocd_id, o.source, o.fr_document_number,
           o.is_extension, o.is_correction, o.is_withdrawal, o.is_reopening,
           case when o.source = 'federal_register' then o.raw end as raw,
           o.raw_dates_text, o.fetched_at, o.payload_hash
    from amend a
    join observations o
      on o.ocd_id = a.ocd_id and o.source in ('federal_register', 'govinfo')
    order by o.ocd_id, o.fetched_at, o.observation_id
  `;
  const byDoc = new Map<string, CorpusDoc>();
  for (const r of rows) {
    let doc = byDoc.get(r.ocd_id);
    if (!doc) {
      doc = {
        ocd_id: r.ocd_id,
        fr: [],
        gov: [],
        publication_dates: [],
        docket_ids: new Set(),
        correction_ofs: new Set(),
        texts: [],
      };
      byDoc.set(r.ocd_id, doc);
    }
    const at = r.fetched_at.getTime();
    if (r.source === "govinfo") {
      doc.gov.push({
        observation_id: r.observation_id,
        at,
        fetched_at: r.fetched_at,
        raw_dates_text: r.raw_dates_text,
        payload_hash: r.payload_hash,
      });
      if (r.raw_dates_text) doc.texts.push(collapseWs(r.raw_dates_text));
      continue;
    }
    const row: FrAmendmentRow = {
      observation_id: r.observation_id,
      ocd_id: r.ocd_id,
      fr_document_number: r.fr_document_number,
      is_extension: r.is_extension,
      is_correction: r.is_correction,
      is_withdrawal: r.is_withdrawal,
      is_reopening: r.is_reopening,
      raw: slimRaw(r.raw),
      govinfo_observation_id: null,
      govinfo_text: null,
      fetched_at: r.fetched_at,
      payload_hash: r.payload_hash,
    };
    doc.fr.push({ row, at });
    const fr = extractFr(row.raw);
    if (fr.publicationDate) doc.publication_dates.push(fr.publicationDate);
    for (const d of fr.docketIds) doc.docket_ids.add(d);
    if (fr.correctionOf) doc.correction_ofs.add(fr.correctionOf);
    if (fr.datesText) doc.texts.push(collapseWs(fr.datesText));
  }
  return { stamp, docs: [...byDoc.values()].filter((d) => d.fr.length > 0) };
}

/**
 * Per-client corpus memo. Keyed by the POOL client: a transaction handle (it has `savepoint`) may see
 * its own uncommitted inserts, so it always builds a private corpus and never stores one — no other
 * caller can ever observe a corpus built from uncommitted rows. The stamp is read BEFORE the corpus,
 * so a row committed between the two reads can only make the memo NEWER than its stamp, which forces a
 * rebuild on the next call, never a stale hit.
 */
const corpusMemo = new WeakMap<object, AmendmentCorpus>();

async function amendmentCorpus(sql: SqlHandle): Promise<AmendmentCorpus> {
  const stamp = await corpusStamp(sql);
  if ("savepoint" in sql) return buildAmendmentCorpus(sql, stamp);
  const hit = corpusMemo.get(sql);
  if (hit && hit.stamp === stamp) return hit;
  const built = await buildAmendmentCorpus(sql, stamp);
  corpusMemo.set(sql, built);
  return built;
}

/**
 * loadAmendmentEvidence — the AMENDED-CLOSE outcome for one window (reconcile-v2.4, ADR 0016): read the
 * window's own latest FR observation (A), find the FR amendment documents DETERMINISTICALLY linked to it
 * (B) with each B's latest govinfo text, and hand them to the pure resolver (amendment.ts).
 *
 * Candidate Bs come from the amendment CORPUS (every window whose latest FR row carries an amendment
 * signal, with its latest govinfo text — memoized per pool client behind an append-only freshness stamp,
 * so a whole poll pass or rederive sweep reads it once). A cheap NECESSARY condition for a non-null
 * linkBasis narrows it (shared docket, B's correction_of naming A, or A's citation in B's collapsed
 * FR-dates / govinfo text — the doc_number and docket_rin bases both need the shared docket); the
 * survivors go to amendmentOutcomeFromRows, where linkBasis (correction_of | doc_number | docket_rin |
 * citation, the citation basis gated by A's citation being carried by exactly ONE FR document across the
 * log), the deny-list and the after-A ordering decide exactly as before. An LLM-affirmed link is NOT read
 * here — llm_corroborated pairs never move a date.
 *
 * Reads ONLY the observation log — never participation_windows / conflict_records — so it carries no
 * verdict-derived state: the review CLI's blind derivation can call it without leaking a verdict, and
 * every derivation path gets the same answer for the same log. Takes any handle (the review write
 * derives inside its own transaction). Returns `none` when A has no FR observation / publication date.
 *
 * Cost (0013 indexes): two index lookups + the stamp per call; the corpus rebuild runs only when an FR
 * or govinfo row was appended since the last call on this client.
 */
export async function loadAmendmentEvidence(
  sql: SqlHandle,
  ocdId: string,
): Promise<AmendmentOutcome> {
  return (await loadAmendmentInputs(sql, ocdId)).outcome;
}

/**
 * loadAmendmentInputs — loadAmendmentEvidence's full result: the outcome, the resolver INPUTS (with each
 * linked amendment's fetch times, which the honor-the-verdict rule needs — ADR 0016 §7) and the linked
 * amendment observations as evidence rows (the review write binds a verdict to them). Every derivation
 * path calls this (reconcileOcdId, the review core), so they all see the same evidence.
 */
export async function loadAmendmentInputs(
  sql: SqlHandle,
  ocdId: string,
): Promise<LoadedAmendment> {
  const NONE: LoadedAmendment = {
    outcome: { kind: "none" },
    inputs: null,
    evidenceRows: [],
  };
  const [aRow] = await sql<FrAmendmentRow[]>`
    select observation_id, ocd_id, fr_document_number,
           is_extension, is_correction, is_withdrawal, is_reopening, raw,
           null::uuid as govinfo_observation_id, null::text as govinfo_text
    from observations
    where ocd_id = ${ocdId} and source = 'federal_register'
    order by fetched_at desc, observation_id desc
    limit 1
  `;
  if (!aRow) return NONE;
  const a = identityCandidate(aRow);
  if (!a.publication_date) return NONE;

  const aNum = a.fr_document_number;
  const aDockets = a.docket_ids;
  const aCitation = (a.citation ?? "").replace(/\s+/g, " ").trim();
  const corpus = await amendmentCorpus(sql);
  // Candidates: documents that could be linked to A in ANY of their states (unions over all rows) — a
  // necessary condition for a non-null linkBasis: a shared docket, B's correction_of naming A, or A's
  // citation in B's text (doc_number and docket_rin both need the shared docket).
  let citationSeen = false;
  const candidates: CorpusDoc[] = [];
  for (const d of corpus.docs) {
    if (d.ocd_id === ocdId) continue;
    if (!d.publication_dates.some((p) => p > a.publication_date!)) continue;
    const cites =
      aCitation.length > 0 && d.texts.some((t) => t.includes(aCitation));
    if (
      cites ||
      (aNum !== null && d.correction_ofs.has(aNum)) ||
      aDockets.some((k) => d.docket_ids.has(k))
    ) {
      candidates.push(d);
      if (cites) citationSeen = true;
    }
  }
  if (candidates.length === 0) return NONE;

  // The citation uniqueness index linkBasis needs — only A's citation is ever looked up, and only when
  // some candidate's text carries it (otherwise the citation basis cannot fire and the count is moot).
  // Counted over EVERY FR document carrying it, PER STATE (round 3, finding 1): a document counts from
  // its FIRST FR fetch on, and each such arrival is a timeline boundary. Today's count applied to every
  // state would let an unrelated document sharing A's citation, arriving later, erase an extension from
  // the past — and revive a verdict that extension had superseded. Expression index 0013/4.
  const citationArrivals: number[] = [];
  if (a.citation && citationSeen) {
    const rows = await sql<{ first_at: Date }[]>`
      select min(fetched_at) as first_at
      from observations
      where source = 'federal_register'
        and regexp_replace(btrim(raw->>'citation'), '\\s+', ' ', 'g') = ${aCitation}
      group by fr_document_number
    `;
    for (const r of rows) citationArrivals.push(r.first_at.getTime());
  }
  const citationKey = a.citation?.trim() ?? "";
  const indexAt = (atMs: number): Map<string, number> =>
    citationKey && citationArrivals.length > 0
      ? new Map([
          [citationKey, citationArrivals.filter((t) => t <= atMs).length],
        ])
      : new Map();

  // Per-(FR row, govinfo row, citation count) evidence, memoized: a state is just the set of rows
  // current at a time, read with that time's citation count.
  const memo = new Map<string, AmendmentEvidence | null>();
  const evidenceOf = (
    r: FrAmendmentRow,
    index: Map<string, number>,
  ): AmendmentEvidence | null => {
    const key = `${r.observation_id}|${r.govinfo_observation_id ?? ""}|${index.get(citationKey) ?? ""}`;
    if (!memo.has(key))
      memo.set(
        key,
        amendmentInputsFromRows(aRow, [r], index)?.inputs.amendments[0] ?? null,
      );
    return memo.get(key)!;
  };
  const stateAt = (atMs: number) =>
    candidates
      .map((d) => docStateAt(d, atMs))
      .filter((r): r is FrAmendmentRow => r !== null);
  // The timeline (ADR 0016 §7): the linked evidence set after each fetch time of any candidate's FR or
  // govinfo row AND each arrival of a document carrying A's citation (round 3). The last state is NOW.
  const times = [
    ...new Set([
      ...candidates.flatMap((d) => [
        ...d.fr.map((r) => r.at),
        ...d.gov.map((g) => g.at),
      ]),
      ...citationArrivals,
    ]),
  ].sort((x, y) => x - y);
  const timeline = times.map((t) => {
    const index = indexAt(t);
    return {
      at: new Date(t).toISOString(),
      amendments: stateAt(t)
        .map((r) => evidenceOf(r, index))
        .filter((e): e is AmendmentEvidence => e !== null),
    };
  });

  const built = amendmentInputsFromRows(
    aRow,
    stateAt(Number.POSITIVE_INFINITY),
    indexAt(Number.POSITIVE_INFINITY),
  );
  if (!built) return NONE;
  built.inputs.timeline = timeline;
  const evidenceRows: AmendmentEvidenceRow[] = [];
  for (const r of built.rows) {
    if (r.payload_hash)
      evidenceRows.push({
        source: "federal_register",
        ocd_id: r.ocd_id,
        observation_id: r.observation_id,
        payload_hash: r.payload_hash,
        fetched_at: toIso(r.fetched_at),
      });
    if (r.govinfo_observation_id && r.govinfo_payload_hash)
      evidenceRows.push({
        source: "govinfo",
        ocd_id: r.ocd_id,
        observation_id: r.govinfo_observation_id,
        payload_hash: r.govinfo_payload_hash,
        fetched_at: toIso(r.govinfo_fetched_at),
      });
  }
  return {
    outcome: resolveAmendedClose(
      built.inputs.original,
      built.inputs.amendments,
    ),
    inputs: built.inputs,
    evidenceRows,
  };
}

/**
 * amendmentOutcomeFromRows — the PURE half of loadAmendmentEvidence: given A's latest FR row, the
 * prefiltered candidate B rows (each with its latest govinfo text) and the citation uniqueness index,
 * keep the Bs that are amendments (derived flags), not keyword false-positives, published after A, with
 * a non-null linkBasis — and resolve. Exported so the recorded production rows can be driven through
 * the exact selection logic without a database.
 */
export function amendmentOutcomeFromRows(
  aRow: FrAmendmentRow,
  bRows: readonly FrAmendmentRow[],
  citationIndex: Map<string, number>,
): AmendmentOutcome {
  const built = amendmentInputsFromRows(aRow, bRows, citationIndex);
  return built
    ? resolveAmendedClose(built.inputs.original, built.inputs.amendments)
    : { kind: "none" };
}

/**
 * The selection half of amendmentOutcomeFromRows: the resolver inputs (original + the linked amendment
 * evidence, with fetch times) and the B rows they came from. null when A has no publication date.
 */
export function amendmentInputsFromRows(
  aRow: FrAmendmentRow,
  bRows: readonly FrAmendmentRow[],
  citationIndex: Map<string, number>,
): { inputs: AmendmentInputs; rows: FrAmendmentRow[] } | null {
  const a = identityCandidate(aRow);
  const aFr = extractFr(aRow.raw);
  if (!a.publication_date) return null;
  const evidence: AmendmentEvidence[] = [];
  const rows: FrAmendmentRow[] = [];
  for (const r of bRows) {
    const b = identityCandidate(r);
    if (!isAmendment(b) || isKeywordFalsePositive(b)) continue;
    if (
      r.ocd_id === aRow.ocd_id ||
      !b.publication_date ||
      !(b.publication_date > a.publication_date)
    )
      continue;
    const basis = linkBasis(a, b, citationIndex);
    if (basis === null) continue;
    const bFr = extractFr(r.raw);
    evidence.push({
      ocd_id: r.ocd_id,
      fr_document_number: b.fr_document_number ?? "",
      fr_observation_id: r.observation_id,
      govinfo_observation_id: r.govinfo_observation_id,
      publication_date: b.publication_date,
      is_extension: b.is_extension,
      is_correction: b.is_correction,
      is_reopening: b.is_reopening,
      is_withdrawal: b.is_withdrawal,
      fr_comments_close_on: bFr.commentsCloseOn,
      fr_dates_text: bFr.datesText,
      govinfo_text: r.govinfo_text,
      basis,
      fr_fetched_at: toIso(r.fetched_at),
      govinfo_fetched_at: r.govinfo_observation_id
        ? toIso(r.govinfo_fetched_at)
        : null,
    });
    rows.push(r);
  }
  return {
    inputs: {
      original: {
        fr_close: aFr.commentsCloseOn,
        publication_date: a.publication_date,
        fr_document_number: a.fr_document_number,
      },
      amendments: evidence,
    },
    rows,
  };
}

/**
 * Read every Observation for an ocd_id from the log, resolve its linked FR amendments
 * (loadAmendmentEvidence, reconcile-v2.4), run the pure engine, persist the projection. The single
 * DB-aware orchestration point; the rulebook itself stays pure + deterministic. Every write path that
 * derives a window — FR/Regs ingest, the rederive sweep, the status refresh, the review write — comes
 * through here, so they all pass the SAME amendment outcome.
 */
export async function reconcileOcdId(
  sql: Sql,
  ocdId: string,
  now: Date = new Date(),
): Promise<ReconcileOcdIdResult> {
  const observations = await loadObservations(sql, ocdId);
  if (observations.length === 0)
    throw new Error(`reconcileOcdId: no observations for ocd_id "${ocdId}"`);

  const amendment = await loadAmendmentInputs(sql, ocdId);
  const result = reconcile(observations, now, reconcileOptionsOf(amendment));
  const persist = await persistReconciliation(sql, result, now);
  return { ...result, persist };
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────
// CROSS-WINDOW (chain) pass — #31 Slice 3. The DB-aware sibling of persistReconciliation/reconcileOcdId,
// but for the cross_window engine (chain.ts). Unlike the per-ocd_id cross_source reconcile, the chain
// pass is a FULL SWEEP: it reads ALL windows-joined-to-their-FR-observation, computes the complete live
// cross_window set in one pure call, then UPSERTs the live set and retires every stale cross_window row.
// ─────────────────────────────────────────────────────────────────────────────────────────────────

export interface ChainPersistResult {
  /** cross_window rows live after this sweep (upserted with resolved_at = null). */
  conflictsLive: number;
  /** still-open cross_window rows retired (resolved_at stamped) because they left the live set. */
  retired: number;
}

/**
 * Stable composite key over a cross_window pair (used by the not-in-live-set retirement sweep). The SQL
 * retirement query rebuilds this SAME key by string concatenation, so the two must agree exactly.
 *
 * SEPARATOR INVARIANT: `|` is a safe delimiter because NEITHER component can contain it — an OcdId is
 * pinned by the contract regex (no `|`; verified by the adversary) and observation ids are UUIDs. If a
 * future id format ever admitted `|`, two distinct tuples could collapse to one key and a stale row could
 * silently fail to retire; at that point switch to a composite-column compare
 * (`(ocd_id, ocd_id_b, observation_a_id, observation_b_id) = ANY(VALUES …)`) which needs no delimiter.
 */
function pairKey(c: {
  ocd_id: string;
  ocd_id_b: string;
  observation_a_id: string;
  observation_b_id: string;
}): string {
  return `${c.ocd_id}|${c.ocd_id_b}|${c.observation_a_id}|${c.observation_b_id}`;
}

/**
 * persistChainConflicts — UPSERT the freshly-computed live cross_window set, then RETIRE every still-open
 * cross_window row whose pair is NOT in that live set. ATOMIC: the whole sweep runs in ONE transaction so
 * the upsert and retirement move together (a crash mid-sweep rolls back rather than leaving the feed in a
 * half-retired state). Mirrors persistReconciliation's atomicity discipline.
 *
 * SCOPE ISOLATION (the load-bearing #31 invariant): every statement is scoped to
 * `conflict_scope = 'cross_window'`. This pass NEVER touches a cross_source row — symmetric to Slice 1
 * scoping the per-ocd_id sweeps to cross_source. So a chain sweep can never collaterally retire a live
 * FR↔Regs conflict that merely shares an ocd_id on one side, and the cross_source reconcile can never
 * retire a chain conflict.
 *
 * RETIREMENT (the part Slice 1 did NOT do): because the chain pass is a full sweep each cycle, a global
 * retire of stale cross_window rows is correct. If the live set is empty, retire ALL open cross_window
 * rows; else retire open cross_window rows whose composite pair key is not among the live tuples. PG18
 * array binding uses `any(${arr}::text[])` (bare array + cast) — never sql.array().
 */
export async function persistChainConflicts(
  sql: Sql,
  conflicts: ChainConflict[],
  now: Date = new Date(),
): Promise<ChainPersistResult> {
  const nowIso = now.toISOString();
  return sql.begin(async (tx) => {
    // UPSERT each live cross_window conflict. detected_at is PRESERVED on re-detection (absent from the DO
    // UPDATE SET); resolved_at is reset to null so a previously-retired-then-relinked pair revives.
    //
    // ARBITER SAFETY: the `on conflict` key omits conflict_scope yet can never overwrite a cross_source row.
    // A cross_window row always carries a non-empty ocd_id_b (B's distinct window), while a cross_source row
    // carries the '' sentinel — and the contract superRefine FORBIDS a cross_source ConflictRecord from
    // having a non-empty ocd_id_b (it would fail .parse before reaching persist). So the 4-tuple keys of the
    // two scopes are structurally disjoint on ocd_id_b; this insert can only ever match another cross_window
    // row. (If the cross_source path ever emitted a non-empty ocd_id_b the index would need conflict_scope.)
    for (const c of conflicts) {
      await tx`
        insert into conflict_records (
          ocd_id, observation_a_id, observation_b_id, source_a, source_b,
          conflict_flags, govinfo_url, detected_at, resolved_at,
          conflict_scope, ocd_id_b, govinfo_url_b
        ) values (
          ${c.ocd_id}, ${c.observation_a_id}, ${c.observation_b_id},
          ${c.source_a}, ${c.source_b}, ${tx.json(c.conflict_flags)},
          ${c.govinfo_url}, ${c.detected_at}, ${null},
          ${c.conflict_scope}, ${c.ocd_id_b}, ${c.govinfo_url_b}
        )
        on conflict (ocd_id, observation_a_id, observation_b_id, ocd_id_b) do update set
          conflict_flags = excluded.conflict_flags,
          govinfo_url    = excluded.govinfo_url,
          govinfo_url_b  = excluded.govinfo_url_b,
          resolved_at    = null
      `;
    }

    // RETIRE stale cross_window rows — strictly scoped to conflict_scope='cross_window'.
    let retired = 0;
    if (conflicts.length === 0) {
      // Empty live set ⇒ every open cross_window row is stale.
      const rows = await tx`
        update conflict_records
          set resolved_at = ${nowIso}
        where conflict_scope = 'cross_window'
          and resolved_at is null
        returning conflict_id
      `;
      retired = rows.length;
    } else {
      // Retire open cross_window rows whose composite pair key is NOT among the live tuples. The composite
      // key (ocd_id|ocd_id_b|observation_a_id|observation_b_id) is rebuilt in SQL and compared against the
      // live keys via NOT (key = any(${arr}::text[])) — PG18-safe bare-array binding + cast.
      const liveKeys = conflicts.map(pairKey);
      const rows = await tx`
        update conflict_records
          set resolved_at = ${nowIso}
        where conflict_scope = 'cross_window'
          and resolved_at is null
          and not (
            ocd_id || '|' || ocd_id_b || '|' || observation_a_id || '|' || observation_b_id
            = any(${liveKeys}::text[])
          )
        returning conflict_id
      `;
      retired = rows.length;
    }

    return { conflictsLive: conflicts.length, retired };
  });
}

export interface ChainReconcileOnceResult extends ChainPersistResult {
  /** total windows-with-an-FR-observation read as candidates. */
  candidates: number;
  /** how many candidates carry an amendment signal (extension/correction/withdrawal). */
  amendments: number;
  /** CONFIDENT (A,B) links the deterministic engine emitted (rules 1–5). */
  linked: number;
  /** ambiguous pairs surfaced (structural rules pass, rule-2 corroboration fails) — the escalation set. */
  ambiguous: number;
  /** ambiguous pairs whose verdict was applied from the cache this cycle (free replays — no LLM call). */
  cacheHits: number;
  /** FRESH LLM calls made this cycle (cache misses that had budget). ≤ cap. A throw still counts. */
  llmCalls: number;
  /** affirmed pairs promoted to a cross_window link (each carries `llm_corroborated`). */
  llmLinked: number;
  /** uncached pairs DEFERRED this cycle because the per-cycle fresh-call budget was exhausted. */
  deferred: number;
}

/** Optional knobs for chainReconcileOnce — both default to the prod-safe path (null adapter, env cap). */
export interface ChainReconcileOnceOptions {
  /**
   * The adjudicator to escalate ambiguous pairs to. DEFAULTS to selectAdjudicator() — which is
   * NullAdjudicator (abstain) until the integrator provisions a key (Slice 3c), so prod is a NO-OP and
   * the persisted set is byte-identical to the confident-only set. Tests inject a spy / NullAdjudicator.
   */
  adjudicator?: Adjudicator;
  /** Per-cycle escalation cap. Defaults to chainMaxEscalations() (env CHAIN_MAX_ESCALATIONS_PER_CYCLE / 25). */
  cap?: number;
}

/**
 * chainReconcileOnce — read the candidate set (every participation_window joined to its LATEST
 * federal_register observation, so the amendment flags + DATES text reflect the current FR doc), build
 * ChainCandidate[], run the pure chain engine, and persist. The single DB-aware orchestration point; the
 * rulebook (chain.ts) stays pure + deterministic.
 *
 * Candidate join: a window contributes a candidate only when it HAS a federal_register observation (the
 * chain conflict is FR-doc ↔ FR-doc). We pick the LATEST FR observation per ocd_id by fetched_at. is_*
 * flags + raw come straight off that observation row; publication_date / docket_ids / rin / dates_text are
 * extracted from the FR raw payload (extractFr) — the same projection reconcile.ts uses, so the chain pass
 * sees identical structured fields.
 */
export async function chainReconcileOnce(
  sql: Sql,
  now: Date = new Date(),
  options: ChainReconcileOnceOptions = {},
): Promise<ChainReconcileOnceResult> {
  const adjudicator = options.adjudicator ?? selectAdjudicator();
  const cap = options.cap ?? chainMaxEscalations();
  // LATEST federal_register observation per window, joined to the window's status + resolved close +
  // govinfo anchor. distinct on (w.ocd_id) ordered by fetched_at desc gives the freshest FR doc.
  // INVARIANT (N1): this read THROWS on any DB failure (postgres.js rejects), so it can NEVER silently
  // return [] and trip the retire-all-cross_window path below. The empty live set only retires-all on a
  // GENUINELY empty candidate set (no FR-backed windows), never on a transient DB error.
  const rows = await sql<
    {
      ocd_id: string;
      fr_observation_id: string;
      is_extension: boolean;
      is_correction: boolean;
      is_withdrawal: boolean;
      is_reopening: boolean;
      raw: unknown;
      status: string;
      resolved_close_utc: Date | string | null;
      govinfo_url: string | null;
      govinfo_text: string | null;
    }[]
  >`
    select distinct on (w.ocd_id)
      w.ocd_id,
      o.observation_id as fr_observation_id,
      o.is_extension, o.is_correction, o.is_withdrawal, o.is_reopening, o.raw,
      w.status, w.resolved_close_utc, w.govinfo_url,
      (select g.raw_dates_text from observations g
        where g.ocd_id = w.ocd_id and g.source = 'govinfo'
        order by g.fetched_at desc, g.observation_id desc
        limit 1) as govinfo_text
    from participation_windows w
    join observations o
      on o.ocd_id = w.ocd_id and o.source = 'federal_register'
    order by w.ocd_id, o.fetched_at desc, o.observation_id desc
  `;

  const candidates: ChainCandidate[] = rows.map((r) => {
    const fr = extractFr(r.raw);
    return {
      ocd_id: r.ocd_id,
      fr_observation_id: r.fr_observation_id,
      fr_document_number: fr.documentNumber,
      docket_ids: fr.docketIds,
      rin: fr.rin,
      rins: fr.rins,
      is_extension: r.is_extension,
      // fr-v3 rule read off raw, so an fr-v2 correction row (correction_of, no keyword) is a correction.
      is_correction: derivedIsCorrection(r),
      is_withdrawal: r.is_withdrawal,
      is_reopening: r.is_reopening,
      title: fr.title,
      publication_date: fr.publicationDate,
      govinfo_url: r.govinfo_url,
      dates_text: fr.datesText,
      status: r.status,
      resolved_close_utc:
        r.resolved_close_utc instanceof Date
          ? r.resolved_close_utc.toISOString()
          : r.resolved_close_utc,
      citation: fr.citation,
      correction_of: fr.correctionOf,
      corrections: fr.corrections,
      govinfo_text: r.govinfo_text,
    };
  });

  // Count amendments by the SAME predicate the engine links on (single source of truth — see chain.ts).
  const amendments = candidates.filter(isAmendment).length;

  // CONFIDENT links — the deterministic engine (rules 1–5). Byte-identical to today's output. Under the
  // null adapter the merged set below equals exactly this (Invariant 1).
  const confident = chainReconcile(candidates, now);

  // AMBIGUOUS tail — pairs the confident path UNDER-LINKS (structural rules pass, rule-2 corroboration
  // fails). Escalate them to the adjudicator; only an `affirm` promotes a pair to a cross_window link
  // (carrying `llm_corroborated`). A null adapter / outage / reject / uncertain → no promotion (worst case
  // is today's confident-only output). Errors are isolated per-pair inside adjudicateAmbiguousPairs.
  const ambiguousPairs = chainAmbiguousPairs(candidates, now);
  const adjudicated = await adjudicateAmbiguousPairs(
    sql,
    adjudicator,
    ambiguousPairs,
    now,
    cap,
  );

  // MERGE confident + LLM-affirmed, then RE-SORT with the SAME total order the engine uses so the persisted
  // set is stable regardless of which links were LLM-promoted. (A confident and a promoted pair can never
  // collide on the 4-tuple key: an ambiguous pair fails rule 2, so it is never also a confident link.)
  const merged = [...confident, ...adjudicated.links].sort(
    (x, y) =>
      x.ocd_id.localeCompare(y.ocd_id) ||
      x.ocd_id_b.localeCompare(y.ocd_id_b) ||
      x.observation_a_id.localeCompare(y.observation_a_id) ||
      x.observation_b_id.localeCompare(y.observation_b_id),
  );

  const persisted = await persistChainConflicts(sql, merged, now);

  return {
    candidates: candidates.length,
    amendments,
    linked: confident.length,
    ambiguous: adjudicated.ambiguous,
    cacheHits: adjudicated.cacheHits,
    llmCalls: adjudicated.llmCalls,
    llmLinked: adjudicated.llmLinked,
    deferred: adjudicated.deferred,
    ...persisted,
  };
}

export interface ChainOriginalsRederiveResult {
  /** side-A windows of the live CONFIDENT cross_window set, re-derived this pass. */
  scanned: number;
  /** re-derivations that moved the operative close (an amendment taking effect — expected, audited). */
  versionBumped: number;
  /** re-derivations that threw (isolated per window; retried next cycle). */
  failed: number;
}

/**
 * rederiveChainOriginals — the reconcile-v2.4 trigger (ADR 0016): re-derive every side-A window of the
 * live CONFIDENT cross_window set, so an amendment that arrived (or whose GovInfo text arrived) this
 * cycle moves its original in the SAME cycle instead of waiting for the original's next Regs poll. Runs
 * after chainReconcileOnce. LLM-affirmed links (llm_corroborated) are skipped — they never move a date,
 * so re-deriving their originals would be pure churn. Idempotent: an unchanged derivation is a no-op
 * refresh (persistReconciliation's own version discipline). Per-window failures are isolated.
 */
export async function rederiveChainOriginals(
  sql: Sql,
  now: Date = new Date(),
): Promise<ChainOriginalsRederiveResult> {
  const rows = await sql<{ ocd_id: string }[]>`
    select distinct ocd_id from conflict_records
    where conflict_scope = 'cross_window'
      and resolved_at is null
      and not (conflict_flags @> '["llm_corroborated"]'::jsonb)
    order by ocd_id
  `;
  const result: ChainOriginalsRederiveResult = {
    scanned: rows.length,
    versionBumped: 0,
    failed: 0,
  };
  for (const { ocd_id } of rows) {
    try {
      const r = await reconcileOcdId(sql, ocd_id, now);
      if (r.persist.versionBumped) result.versionBumped++;
    } catch {
      result.failed++;
    }
  }
  return result;
}
