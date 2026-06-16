/**
 * pollRegsOnce — the testable CORE of the Regs.gov differential poll loop (issue #18). One invocation
 * runs one full poll cycle against the spine; the thin scheduler (run.ts) just calls it on an interval.
 *
 * Two passes, both reconciled:
 *
 *   1. DIFFERENTIAL PASS — discover+ingest CHANGED open-comment documents.
 *      `since` = the persisted cursor (max lastModifiedDate consumed). Before the first run the cursor is
 *      NULL; we seed `since = now - initialLookbackMs` (default 48h) so the first poll picks up a recent
 *      window of changes rather than backfilling all history (that backfill is a separate seed job). The
 *      6h Eastern/UTC overlap is applied INSIDE listPage (regsListUrl/easternCursorLowerBound) — we pass
 *      the bare cursor and do NOT double-apply it.
 *      We PAGE TO COMPLETION: sort=lastModifiedDate is ASCENDING (issue #18 "Related"), so the NEWEST
 *      changes are on the LAST page. We loop pageNumber from 1, accumulating, until a page returns fewer
 *      than pageSize rows (the last page) or maxPages (the v4 20-page hard cap) is hit. Hitting maxPages
 *      with a still-full page means coverage was TRUNCATED — we surface it (summary.truncated + a console
 *      note), never silently cap. Accumulated items are deduped by documentId (the 6h overlap re-fetches
 *      the boundary), sorted ASCENDING by lastModifiedDate, then each is fetched-in-detail → parsed →
 *      ingested → reconciled.
 *      RECONCILE-ALWAYS (adversary fix #7): reconcile runs after EVERY successful fetch+ingest, regardless
 *      of whether ingest appended a new row — reconcile is an idempotent re-derive from the append-only
 *      log, so re-running it is cheap and SELF-HEALING (a crash that appended an observation but never
 *      reconciled is repaired on the next cycle even though the re-fetch dedupe-skips). `ingested`/
 *      `transitions` still count ONLY the new-row (inserted=true) cases.
 *      Every successfully fetched document is STAMPED in regs_poll_watch (last_checked_at = now) — the
 *      per-document re-poll throttle (fixes #5 + #2), decoupled from the dedupe-skipping observation log.
 *      CONTIGUOUS-SUCCESS CURSOR (adversary fix #1): the deduped list is processed ASCENDING and the cursor
 *      advances ONLY to the highest lastModifiedDate of the CONTIGUOUS PREFIX OF SUCCESSES — it STOPS at
 *      the first document that fails its fetch/parse/ingest (a NULL lastModifiedDate is treated
 *      conservatively as non-advancing). Documents after the first failure are still processed
 *      (idempotent), but the cursor does NOT pass the first failure, so that document is re-listed (within
 *      the 6h overlap and beyond) and retried next cycle — it can NEVER be silently skipped. The cursor is
 *      derived from the LIST item, NEVER a detail payload (the NOTE(cursor-slice) trap: detail carries
 *      `modifyDate`, not `lastModifiedDate`).
 *      TRADE-OFF: a PERSISTENTLY-failing document holds cursor progress (the contiguous successes BEFORE it
 *      re-process idempotently every cycle, and it logs loudly every cycle) — DELIBERATELY chosen over the
 *      old behavior of SILENTLY losing every change beyond it, which is unacceptable for a withdrawal-
 *      detection system. A bounded-retry / dead-letter cap is a noted follow-up, not this slice.
 *
 *   2. RE-POLL PASS — the heart of #18. The withinCommentPeriod=true list filter DROPS a notice the
 *      moment it is withdrawn, so the differential pass alone never re-fetches it and the withdrawn:true
 *      transition is never observed. So we separately re-poll, BY documentId (which bypasses the filter),
 *      the windows we have seen OPEN that did NOT appear in this cycle's differential list and whose
 *      per-document regs_poll_watch.last_checked_at is stale (older than repollStaleAfterMs) — INCLUDING
 *      FR-discovered windows that have a regs_document_id but NO regulations_gov observation yet (a NULL
 *      stamp coalesces to 'epoch' → maximally stale → eligible; fix #2). A detail fetch by documentId
 *      finally lands the withdrawn:true observation in the log; reconciliation then flips the window
 *      (→ status withdrawn, or CONFLICTING withdrawn_vs_open if an FR counterpart still reads open).
 *      As in the differential pass, every successful re-poll fetch STAMPS regs_poll_watch and reconciles
 *      ALWAYS (self-heal), counting a transition only when a NEW observation was actually appended.
 *      The staleness throttle keeps us inside budget: at ~1,000 windows and 1,000 req/hr we re-poll only
 *      windows untouched for repollStaleAfterMs (default 6h); the stamp advances even on a dedupe-skip, so
 *      a freshly re-checked-but-unchanged window is NOT re-polled again until it goes stale (fix #5).
 *
 * DEFENSIVE: a single document's fetch/parse/ingest failure must NEVER abort the cycle — it is caught
 * per-document, logged, and the loop continues (the failed doc HOLDS the cursor at the contiguous-prefix
 * boundary; the rest are still processed idempotently). One bad payload can't wedge the poller, and no
 * change beyond a failure is ever silently lost.
 *
 * DETERMINISTIC: the network and the clock are INJECTED (PollDeps), exactly like the reconcile engine
 * takes `now`. Tests drive fake deps; live network lives only in run.ts / poll.smoke.ts.
 */
import type { Sql } from "../db/client.js";
import {
  listChangedDocuments,
  fetchRegsDocument,
  parseRegsObservation,
  type RegsListItem,
} from "../sources/regulations-gov.js";
import { ingestObservation } from "../ingest/observe.js";
import { reconcileOcdId } from "../reconcile/persist.js";
import {
  readCursor,
  writeCursor,
  touchPolledAt,
  stampChecked,
} from "./cursor.js";

const SOURCE = "regulations_gov";

export interface PollDeps {
  /** Fetch ONE list page of changed open-comment docs. Defaults to listChangedDocuments. */
  listPage(opts: {
    sinceUtcIso?: string;
    pageSize: number;
    pageNumber: number;
  }): Promise<RegsListItem[]>;
  /** Fetch one document detail by documentId. Defaults to fetchRegsDocument. */
  fetchDetail(documentId: string): Promise<unknown>;
  /** The clock. Defaults to () => new Date(). */
  now(): Date;
}

export interface PollSummary {
  // differential pass
  listed: number; // distinct changed docs the list returned (after cross-page dedupe)
  ingested: number; // differential docs that appended a NEW observation
  deduped: number; // differential docs whose payload matched the latest (idempotent skip)
  // #18 re-poll pass
  repolled: number; // seen-open windows re-polled by documentId this cycle
  transitions: number; // re-polls that produced a NEW observation (e.g. the withdrawal)
  // cursor + coverage
  cursorAdvancedTo: string | null; // the UTC-ISO max LIST lastModifiedDate written, or null if unchanged
  pagesFetched: number;
  truncated: boolean; // true if we stopped at maxPages with a still-full page (coverage incomplete)
}

export interface PollOptions {
  pageSize?: number;
  maxPages?: number;
  repollStaleAfterMs?: number;
  initialLookbackMs?: number;
}

const DEFAULTS = {
  pageSize: 250, // v4 max page size
  maxPages: 20, // v4 hard cap (20 pages × 250 = 5,000 per query)
  repollStaleAfterMs: 6 * 3_600_000, // 6h — throttle the re-poll sweep to stay in budget
  initialLookbackMs: 48 * 3_600_000, // 48h — first run picks up recent changes, not all history
};

function resolveDeps(deps?: Partial<PollDeps>): PollDeps {
  return {
    listPage: deps?.listPage ?? ((o) => listChangedDocuments(o)),
    fetchDetail: deps?.fetchDetail ?? ((id) => fetchRegsDocument(id)),
    now: deps?.now ?? (() => new Date()),
  };
}

/** A window we've seen OPEN whose Regs detail is stale enough to re-poll for a withdrawal transition. */
interface StaleOpenWindow {
  ocd_id: string;
  regs_document_id: string;
}

export async function pollRegsOnce(
  sql: Sql,
  deps?: Partial<PollDeps>,
  opts?: PollOptions,
): Promise<PollSummary> {
  const d = resolveDeps(deps);
  const o = { ...DEFAULTS, ...opts };
  const now = d.now();

  const summary: PollSummary = {
    listed: 0,
    ingested: 0,
    deduped: 0,
    repolled: 0,
    transitions: 0,
    cursorAdvancedTo: null,
    pagesFetched: 0,
    truncated: false,
  };

  // ── 1. DIFFERENTIAL PASS — page the changed-document list to completion ───────────────────────────
  const storedCursor = await readCursor(sql, SOURCE);
  const since =
    storedCursor ?? new Date(now.getTime() - o.initialLookbackMs).toISOString();

  const accumulated: RegsListItem[] = [];
  let pageNumber = 1;
  for (; pageNumber <= o.maxPages; pageNumber++) {
    const page = await d.listPage({
      sinceUtcIso: since,
      pageSize: o.pageSize,
      pageNumber,
    });
    summary.pagesFetched++;
    accumulated.push(...page);
    if (page.length < o.pageSize) break; // a short page is the last page (ascending sort → newest last)
    if (pageNumber === o.maxPages && page.length === o.pageSize) {
      // Stopped at the hard cap with a still-full page: coverage is INCOMPLETE — surface, don't swallow.
      summary.truncated = true;
      console.warn(
        `pollRegsOnce: hit maxPages=${o.maxPages} with a full last page — coverage TRUNCATED ` +
          `(newest changes may be unconsumed; cursor will NOT cover them). Narrow the cursor or raise budget.`,
      );
    }
  }

  // Dedupe across pages by documentId (the 6h overlap deliberately re-fetches the boundary window),
  // then sort ASCENDING by lastModifiedDate so the cursor can advance through the CONTIGUOUS-SUCCESS
  // prefix and STOP at the first failure (fix #1). A NULL lastModifiedDate sorts FIRST (treated as the
  // oldest / most-conservative) so it can never let the cursor leap past a real instant.
  const changed = dedupeByDocumentId(accumulated).sort((a, b) =>
    (a.lastModifiedDate ?? "").localeCompare(b.lastModifiedDate ?? ""),
  );
  summary.listed = changed.length;

  // The set observed THIS cycle — used to exclude these from the re-poll sweep (they're already fresh).
  const observedDocIds = new Set<string>();
  // CONTIGUOUS-SUCCESS CURSOR (fix #1): advance only to the highest LIST lastModifiedDate of the
  // unbroken prefix of SUCCESSES. Once a document fails (or carries a NULL lastModifiedDate), the cursor
  // freezes at the last clean instant before it, so that document is re-listed and retried next cycle.
  let cursorPrefix: string | null = null;
  let prefixBroken = false;

  for (const item of changed) {
    observedDocIds.add(item.documentId);
    let success = false;
    try {
      const detail = await d.fetchDetail(item.documentId);
      // The fetch landed — stamp the per-document throttle (fix #5/#2) before ingest, so even a
      // dedupe-skip or a downstream parse hiccup still records "we checked this document's detail".
      await stampChecked(sql, item.documentId, now);
      const candidate = parseRegsObservation(detail);
      const { inserted, ocdId } = await ingestObservation(sql, candidate);
      if (inserted) {
        summary.ingested++;
      } else {
        summary.deduped++;
      }
      // RECONCILE-ALWAYS (fix #7): re-derive from the log regardless of inserted — idempotent + self-heal.
      await reconcileOcdId(sql, ocdId, now);
      success = true;
    } catch (err) {
      // Per-document isolation: one bad payload must not wedge the cycle. Log + continue. But this doc
      // FAILED, so it breaks the contiguous-success prefix — the cursor must not advance past it (fix #1).
      console.error(
        `pollRegsOnce: differential doc ${item.documentId} failed — skipping (HOLDS cursor):`,
        err instanceof Error ? err.message : err,
      );
    }
    // Cursor bookkeeping: extend the prefix ONLY while it is still unbroken AND this doc both succeeded
    // and carries a real lastModifiedDate. The FIRST gap (failure or NULL date) freezes the prefix; later
    // docs are still processed above but can no longer move the cursor.
    if (!prefixBroken && success && item.lastModifiedDate) {
      if (cursorPrefix === null || item.lastModifiedDate > cursorPrefix) {
        cursorPrefix = item.lastModifiedDate;
      }
    } else {
      prefixBroken = true;
    }
  }

  // Advance the cursor to the contiguous-success prefix's MAX LIST lastModifiedDate (monotonic). No
  // advanceable prefix → leave it unchanged (still stamp last_polled_at so "we ran" stays current).
  if (cursorPrefix) {
    // cursorPrefix is a v4 "…Z" instant; normalize through Date so the stored cursor is canonical ISO.
    const cursorIso = new Date(cursorPrefix).toISOString();
    await writeCursor(sql, SOURCE, cursorIso, now);
    summary.cursorAdvancedTo = (await readCursor(sql, SOURCE)) ?? null;
  } else {
    // No advanceable contiguous-success prefix (empty poll, or the very first doc failed/was NULL-dated):
    // do NOT move the cursor; just stamp "we ran". cursorAdvancedTo stays null (its default) — "unchanged".
    await touchPolledAt(sql, SOURCE, now);
  }

  // ── 2. RE-POLL PASS (#18) — re-fetch seen-open windows that dropped out of the list and are stale ──
  const stale = await selectStaleOpenWindows(
    sql,
    observedDocIds,
    new Date(now.getTime() - o.repollStaleAfterMs),
  );
  for (const win of stale) {
    summary.repolled++;
    try {
      const detail = await d.fetchDetail(win.regs_document_id);
      // Stamp the per-document throttle on a successful detail fetch (fix #5/#2) — this advances the
      // re-poll throttle even when the payload is unchanged (dedupe-skips), so a re-checked-but-unchanged
      // window stops being re-polled until it goes stale again.
      await stampChecked(sql, win.regs_document_id, now);
      const candidate = parseRegsObservation(detail);
      const { inserted, ocdId } = await ingestObservation(sql, candidate);
      if (inserted) {
        // A NEW payload for a window we'd seen open — the transition (e.g. withdrawn:true) finally lands.
        summary.transitions++;
      }
      // RECONCILE-ALWAYS (fix #7): re-derive from the log regardless of inserted. This SELF-HEALS the
      // crash window — an observation appended on a prior cycle but never reconciled is repaired here even
      // though THIS re-fetch dedupe-skips (inserted=false), flipping a still-open-but-withdrawn window.
      await reconcileOcdId(sql, ocdId, now);
    } catch (err) {
      console.error(
        `pollRegsOnce: re-poll of ${win.regs_document_id} failed — skipping:`,
        err instanceof Error ? err.message : err,
      );
    }
  }

  return summary;
}

/**
 * The seen-OPEN windows to re-poll: status='open', a non-null regs_document_id, NOT observed in this
 * cycle's differential list, AND whose per-document re-poll throttle (regs_poll_watch.last_checked_at) is
 * older than `staleBefore`.
 *
 * THROTTLE SOURCE (adversary fixes #5 + #2): staleness is read from the MUTABLE regs_poll_watch stamp, NOT
 * from max(observations.fetched_at). The observation log dedupe-skips an unchanged re-poll, so its
 * fetched_at never advanced and the old subquery re-polled an unchanged window EVERY cycle (#5); and an
 * FR-discovered window with a regs_document_id but ZERO regulations_gov observations had a NULL subquery,
 * and `NULL < x` is falsy, so it was NEVER eligible (#2). regs_poll_watch is stamped on every successful
 * detail fetch (advancing the throttle even on a dedupe-skip), and coalesce(last_checked_at, 'epoch')
 * makes a never-checked document (including an FR-only window) maximally stale → selected.
 *
 * NOT-observed is a caller-side filter (the observed set can be large; we filter in JS rather than build a
 * huge IN-list) — a document already fetched in THIS cycle's differential pass was just stamped fresh, so
 * the SQL throttle would exclude it anyway; the JS filter is a cheap belt-and-suspenders.
 */
async function selectStaleOpenWindows(
  sql: Sql,
  observedDocIds: Set<string>,
  staleBefore: Date,
): Promise<StaleOpenWindow[]> {
  const rows = await sql<StaleOpenWindow[]>`
    select w.ocd_id, w.regs_document_id
    from participation_windows w
    where w.status = 'open'
      and w.regs_document_id is not null
      and coalesce(
        (
          select pw.last_checked_at
          from regs_poll_watch pw
          where pw.regs_document_id = w.regs_document_id
        ),
        'epoch'
      ) < ${staleBefore.toISOString()}
  `;
  return rows.filter((r) => !observedDocIds.has(r.regs_document_id));
}

/**
 * Local copy of the documentId dedupe (keep the latest lastModifiedDate), used to collapse the
 * cross-page accumulation. The source adapter dedupes WITHIN a page; this dedupes ACROSS pages (and
 * across the 6h overlap re-fetch). String compare is chronological for v4's fixed UTC "…Z" format.
 */
function dedupeByDocumentId(items: RegsListItem[]): RegsListItem[] {
  const latest = new Map<string, RegsListItem>();
  for (const item of items) {
    if (!item.documentId) continue;
    const prev = latest.get(item.documentId);
    if (
      !prev ||
      (item.lastModifiedDate ?? "") > (prev.lastModifiedDate ?? "")
    ) {
      latest.set(item.documentId, item);
    }
  }
  return [...latest.values()];
}
