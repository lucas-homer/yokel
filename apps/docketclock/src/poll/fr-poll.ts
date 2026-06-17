/**
 * pollFrOnce — the testable CORE of the Federal Register discovery poll. One invocation lists the
 * FULL set of currently-OPEN FR comment documents, ingests each NEW one into the append-only
 * observation log, and reconciles — so FR-anchored windows can reach HIGH (FR↔Regs agreement) or
 * CONFLICTING, instead of the MEDIUM ceiling we get when only Regs.gov is polled. The thin scheduler
 * (run.ts) calls this once per cycle, FIRST, before pollRegsOnce.
 *
 * FULL-OPEN-SET DISCOVERY EACH CYCLE (the B1 design). Every cycle re-lists the COMPLETE open set:
 * conditions[comment_date][gte]={Eastern-today}, paged to completion. There is NO publication_date
 * cursor. WHY: FR `publication_date` is IMMUTABLE (the print date, never edited) — it is NOT a change
 * cursor like Regs `lastModifiedDate`. Open comment periods routinely run for months, so open docs are
 * commonly published long before their deadline (live FR carries open docs published ~18 months ago).
 * A conditions[publication_date][gte]={cursor} discovery filter would therefore list only docs in the
 * cursor's narrow recent window and PERMANENTLY bury the older open back-catalog — the cursor never
 * reaches them again, because publication_date never moves. So discovery is the full open set; complete,
 * no back-catalog hole.
 *
 * DIFFERENTIAL-BY-THE-LOG (not by a date cursor). FR documents are IMMUTABLE: a notice's text never
 * changes, and a withdrawal/extension is published as a SEPARATE new FR document, not an edit of the
 * original. So a doc we have ALREADY ingested never needs re-fetching. After listing the open set we
 * query which of those document numbers already carry a `federal_register` observation, and SKIP them —
 * we only fetch detail + ingest + reconcile the docs NOT yet in the log. This replaces the old
 * contiguous-success date cursor: a doc whose fetch/parse/ingest FAILS simply stays absent from the log,
 * so it is naturally RE-LISTED (the full open set is re-listed every cycle) and RETRIED next cycle. Same
 * "never silently skip a failure" guarantee as the old cursor, but simpler and immune to the B1 hole.
 *
 * NO RE-POLL PASS (unlike pollRegsOnce). Because FR docs are immutable there is nothing to re-poll by
 * id. Discovering the WITHDRAWAL/extension/correction notices themselves is the keyword path — deferred
 * to issue #26 (see NOTE(fr-keyword-discovery, #26) in federal-register.ts). Meanwhile the Regs.gov
 * re-poll pass in poll.ts already lands the withdrawn:true operational signal and reconciles any
 * cross-source window.
 *
 * FR-FIRST HANDOFF: an FR document carries regulations_dot_gov_info.document_id → regs_document_id on
 * the derived window (see parseFrObservation). Discovering FR docs FIRST means the SAME cycle's later
 * pollRegsOnce re-poll pass picks up any FR-discovered window that has a regs_document_id but no
 * regulations_gov observation yet (a NULL watch stamp coalesces to 'epoch' → maximally stale →
 * eligible), fetching the Regs counterpart and lifting the pair toward HIGH/CONFLICTING.
 *
 * RECONCILE-ALWAYS for the docs we fetch: reconcile runs after every successful fetch+ingest of a NEW
 * doc — it is an idempotent re-derive from the append-only log. (We only fetch docs NOT yet in the log,
 * so in steady state this runs only for genuinely new docs.)
 *
 * SELF-HEAL NUANCE (accepted limitation, not fixed this slice): a process crash BETWEEN ingest and
 * reconcile of a BRAND-NEW FR-ONLY doc leaves it ingested-but-skipped-thereafter — the differential
 * filter sees it in the log and won't FR-reconcile it again. The append-only log is intact, and the
 * Regs pass reconciles any cross-source window, so this is a narrow, accepted limitation. Do not
 * over-engineer a fix here.
 *
 * PAGE TO COMPLETION + REAL CAP: loop page=1.. accumulating, until a page returns fewer than perPage
 * rows (the last page) or maxPages is hit. FR enforces page * per_page <= 10,000 (page 11 at
 * per_page=1000 is an HTTP 400), so the defaults perPage=1000 / maxPages=10 make the cap REAL and
 * exactly FR's hard ceiling. Hitting maxPages with a still-full page means coverage is TRUNCATED —
 * surfaced (summary.truncated + a console.warn), never silently capped. Beyond 10k open docs FR requires
 * its search_after_cursor (a scale follow-up; the ~1,000-window design has ~10x headroom today).
 *
 * DEFENSIVE: a single document's fetch/parse/ingest/reconcile failure must NEVER abort the cycle — it is
 * caught per-document, logged, and the loop continues (the failed doc stays unseen → re-listed + retried
 * next cycle).
 *
 * DETERMINISTIC: the network and the clock are INJECTED (FrPollDeps), exactly like pollRegsOnce. Tests
 * drive fakes; live network lives only in run.ts / the smoke.
 */
import type { Sql } from "../db/client.js";
import {
  listOpenCommentDocuments,
  fetchFrDocument,
  parseFrObservation,
  todayEastern,
  type FrListItem,
} from "../sources/federal-register.js";
import { ingestObservation } from "../ingest/observe.js";
import { reconcileOcdId } from "../reconcile/persist.js";
import { touchPolledAt } from "./cursor.js";

const SOURCE = "federal_register";

export interface FrPollDeps {
  /** Fetch ONE list page of currently-open FR comment docs. Defaults to listOpenCommentDocuments. */
  listPage(opts: {
    commentOpenOnOrAfter: string;
    perPage: number;
    page: number;
  }): Promise<FrListItem[]>;
  /** Fetch one FR document detail by document number. Defaults to fetchFrDocument. */
  fetchDetail(documentNumber: string): Promise<unknown>;
  /** The clock. Defaults to () => new Date(). */
  now(): Date;
}

export interface FrPollSummary {
  listed: number; // distinct open docs the list returned (after cross-page dedupe)
  fetched: number; // docs whose detail we fetched this cycle (= not already in the log)
  ingested: number; // docs that appended a NEW observation (inserted === true)
  skipped: number; // docs already in the log (differential-by-log), NOT fetched
  pagesFetched: number;
  truncated: boolean; // true if we stopped at maxPages with a still-full page (coverage incomplete)
}

export interface FrPollOptions {
  perPage?: number;
  maxPages?: number;
}

const DEFAULTS = {
  // FR allows up to 1000 per page and enforces page * per_page <= 10,000. perPage=1000 / maxPages=10
  // makes the cap REAL and exactly FR's hard ceiling (10 * 1000 = 10,000): page 11 would 400.
  perPage: 1000,
  maxPages: 10,
};

function resolveDeps(deps?: Partial<FrPollDeps>): FrPollDeps {
  return {
    listPage: deps?.listPage ?? ((o) => listOpenCommentDocuments(o)),
    fetchDetail: deps?.fetchDetail ?? ((n) => fetchFrDocument(n)),
    now: deps?.now ?? (() => new Date()),
  };
}

export async function pollFrOnce(
  sql: Sql,
  deps?: Partial<FrPollDeps>,
  opts?: FrPollOptions,
): Promise<FrPollSummary> {
  const d = resolveDeps(deps);
  const o = { ...DEFAULTS, ...opts };
  const now = d.now();

  const summary: FrPollSummary = {
    listed: 0,
    fetched: 0,
    ingested: 0,
    skipped: 0,
    pagesFetched: 0,
    truncated: false,
  };

  // The open-comment cutoff: TODAY in America/New_York (Eastern is the legal-publication zone; the FR
  // comment_date filter is date-granular and interpreted in Eastern). This is the ONLY discovery filter.
  const commentOpenOnOrAfter = todayEastern(now);

  // ── PAGE THE FULL OPEN-COMMENT LIST TO COMPLETION ───────────────────────────────────────────────────
  const accumulated: FrListItem[] = [];
  for (let page = 1; page <= o.maxPages; page++) {
    const items = await d.listPage({
      commentOpenOnOrAfter,
      perPage: o.perPage,
      page,
    });
    summary.pagesFetched++;
    accumulated.push(...items);
    if (items.length < o.perPage) break; // a short page is the last
    if (page === o.maxPages && items.length === o.perPage) {
      // Stopped at the cap with a still-full page: coverage is INCOMPLETE — surface, don't swallow.
      summary.truncated = true;
      console.warn(
        `pollFrOnce: hit maxPages=${o.maxPages} (per_page=${o.perPage}) with a full last page — coverage ` +
          `TRUNCATED. FR caps page * per_page at 10,000; beyond that switch to search_after_cursor (#scale).`,
      );
    }
  }

  // Dedupe across pages by documentNumber (keep the latest).
  const open = dedupeByDocumentNumber(accumulated);
  summary.listed = open.length;
  if (open.length === 0) {
    await touchPolledAt(sql, SOURCE, now); // observability stamp ("we ran"), no FR date cursor exists
    return summary;
  }

  // ── DIFFERENTIAL BY THE LOG ─────────────────────────────────────────────────────────────────────────
  // Which of the listed doc numbers already carry a federal_register observation? Those are SKIPPED (FR
  // docs are immutable → a seen doc never needs re-fetching). A doc that previously FAILED is absent from
  // the log, so it is naturally re-listed here and retried below.
  const docNums = open.map((i) => i.documentNumber);
  const seenRows = await sql<{ fr_document_number: string }[]>`
    select fr_document_number
    from observations
    where source = ${SOURCE}
      and fr_document_number = any(${sql.array(docNums)})
  `;
  const seen = new Set(seenRows.map((r) => r.fr_document_number));

  for (const item of open) {
    if (seen.has(item.documentNumber)) {
      summary.skipped++;
      continue;
    }
    try {
      const detail = await d.fetchDetail(item.documentNumber);
      summary.fetched++;
      const candidate = parseFrObservation(detail);
      const { inserted, ocdId } = await ingestObservation(sql, candidate);
      if (inserted) summary.ingested++;
      // RECONCILE-ALWAYS: idempotent re-derive from the append-only log for the doc we just fetched.
      await reconcileOcdId(sql, ocdId, now);
    } catch (err) {
      // Per-document isolation: one bad payload must not wedge the cycle. Log + continue. The doc stays
      // UNSEEN (no observation row) → it is re-listed in full next cycle and retried (replaces the old
      // contiguous-success cursor's "never silently skip a failure" guarantee).
      console.error(
        `pollFrOnce: FR doc ${item.documentNumber} failed — skipping (retried via re-list next cycle):`,
        err instanceof Error ? err.message : err,
      );
    }
  }

  // No FR date cursor exists (publication_date is immutable, not a change cursor). Stamp only that we ran.
  await touchPolledAt(sql, SOURCE, now);
  return summary;
}

/**
 * Dedupe FR list items by documentNumber, keeping the LATEST publicationDate — collapses the cross-page
 * accumulation. (Local copy mirroring poll.ts's cross-page dedupe; the adapter dedupes within a page,
 * this dedupes across pages.)
 */
function dedupeByDocumentNumber(items: FrListItem[]): FrListItem[] {
  const latest = new Map<string, FrListItem>();
  for (const item of items) {
    if (!item.documentNumber) continue;
    const prev = latest.get(item.documentNumber);
    if (!prev || (item.publicationDate ?? "") > (prev.publicationDate ?? "")) {
      latest.set(item.documentNumber, item);
    }
  }
  return [...latest.values()];
}
