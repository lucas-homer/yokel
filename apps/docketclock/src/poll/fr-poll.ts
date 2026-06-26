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
 * id. Discovering the WITHDRAWAL/extension/correction notices themselves is the KEYWORD path (#26):
 * alongside the open-comment set, each cycle also pages a bounded conditions[term]= query per amendment
 * keyword (extension/correction/reopening/withdrawal) over a recent publication-date trailing window, and
 * UNIONs those document numbers into the same working set. An amendment notice that carries no open
 * comment_date of its own is thus still ingested through the SAME append-only path, so the #31
 * chain-reconcile pass can chain it onto the window it amends. See frKeywordListUrl in
 * federal-register.ts for the verified FR `term` semantics + the lookback rationale.
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
 * surfaced (summary.truncated + a log.warn), never silently capped. Beyond 10k open docs FR requires
 * its search_after_cursor (a scale follow-up; the ~1,000-window design has ~10x headroom today).
 *
 * DEFENSIVE: a single document's fetch/parse/ingest/reconcile failure must NEVER abort the cycle — it is
 * caught per-document, logged, and the loop continues (the failed doc stays unseen → re-listed + retried
 * next cycle).
 *
 * BOUNDED RETRY → DEAD-LETTER (#21): re-listing a failing doc every cycle is correct for a TRANSIENT
 * failure but a PERMANENTLY-failing doc re-burns the FR rate budget forever. So a doc that fails
 * maxFailAttempts CONSECUTIVE cycles is DEAD-LETTERED (poll_dead_letter, 0005): from then on it is SKIPPED
 * from the hot fetch path (no more budget burn) and re-attempted only by a slow drain sweep on a 6h
 * throttle, so a recovered doc self-heals without becoming a hot retry loop. ANY success clears the ledger
 * (consecutive-failure reset). Parse/ingest failures count toward the threshold too, not only fetch
 * failures (per the #21 owner-comment).
 *
 * DETERMINISTIC: the network and the clock are INJECTED (FrPollDeps), exactly like pollRegsOnce. Tests
 * drive fakes; live network lives only in run.ts / the smoke.
 */
import type { Sql } from "../db/client.js";
import {
  listOpenCommentDocuments,
  listAmendmentDocuments,
  AMENDMENT_TERMS,
  fetchFrDocument,
  parseFrObservation,
  todayEastern,
  easternDateDaysAgo,
  dedupeByDocumentNumber,
  type FrListItem,
} from "../sources/federal-register.js";
import { ingestObservation } from "../ingest/observe.js";
import { componentLogger } from "../log.js";
import { reconcileOcdId } from "../reconcile/persist.js";
import { touchPolledAt } from "./cursor.js";
import {
  recordFailure,
  clearDeadLetter,
  selectDeadLetteredForRetry,
  markRetryAttempt,
  deadLetteredKeys,
} from "./dead-letter.js";

const SOURCE = "federal_register";

const log = componentLogger("poller");

export interface FrPollDeps {
  /** Fetch ONE list page of currently-open FR comment docs. Defaults to listOpenCommentDocuments. */
  listPage(opts: {
    commentOpenOnOrAfter: string;
    perPage: number;
    page: number;
  }): Promise<FrListItem[]>;
  /**
   * Fetch ONE keyword list page (one amendment term, one page). Defaults to listAmendmentDocuments.
   * Discovers extension/correction/reopening/WITHDRAWAL notices that carry no open comment_date (#26),
   * so the #31 chain-reconcile pass has them in the log. Injected like listPage for tests.
   */
  listKeywordPage(opts: {
    term: string;
    publicationDateOnOrAfter: string;
    perPage: number;
    page: number;
  }): Promise<FrListItem[]>;
  /** Fetch one FR document detail by document number. Defaults to fetchFrDocument. */
  fetchDetail(documentNumber: string): Promise<unknown>;
  /** The clock. Defaults to () => new Date(). */
  now(): Date;
  /** Sleep between FR detail fetches (the cold-start throttle). Defaults to a real setTimeout sleep. */
  sleep(ms: number): Promise<void>;
}

export interface FrPollSummary {
  listed: number; // distinct docs the discovery UNION returned (open + keyword, after cross-page dedupe)
  keywordListed: number; // distinct docs the KEYWORD (amendment) set contributed (pre-union, #26 visibility)
  fetched: number; // docs whose detail we fetched this cycle (= not already in the log)
  ingested: number; // docs that appended a NEW observation (inserted === true)
  skipped: number; // docs already in the log (differential-by-log) OR dead-lettered, NOT fetched
  pagesFetched: number;
  truncated: boolean; // true if we stopped at maxPages with a still-full page (coverage incomplete)
  // #21 bounded-retry / dead-letter
  deadLettered: number; // docs newly DEAD-LETTERED this cycle (crossed maxFailAttempts)
  deadLetterRetried: number; // dead-lettered docs re-attempted by the slow drain sweep this cycle
  recovered: number; // previously-failing docs (a ledger row existed) that succeeded + were cleared
}

export interface FrPollOptions {
  perPage?: number;
  maxPages?: number;
  interFetchDelayMs?: number;
  maxFailAttempts?: number;
  deadLetterRetryStaleAfterMs?: number;
  /**
   * The KEYWORD (amendment) discovery trailing window, in days. The keyword set is bounded by
   * conditions[publication_date][gte] = (Eastern now - keywordLookbackDays) so it pages a recent window
   * instead of all of FR history (see frKeywordListUrl). Default 120 (DEFAULTS.keywordLookbackDays).
   */
  keywordLookbackDays?: number;
}

const DEFAULTS = {
  // FR allows up to 1000 per page and enforces page * per_page <= 10,000. perPage=1000 / maxPages=10
  // makes the cap REAL and exactly FR's hard ceiling (10 * 1000 = 10,000): page 11 would 400.
  perPage: 1000,
  maxPages: 10,
  // COLD-START THROTTLE: the first cycle on a fresh DB fetches the FULL open back-catalog (~1,000 docs)
  // one detail at a time. Firing those back-to-back trips FR's burst limit (429 "temporarily
  // deactivated" — observed live). FR publishes no hard rate, but tolerated only ~5 req/s briefly; this
  // 300ms inter-fetch delay (~3 req/s) keeps us under it. http.ts already honors Retry-After on any 429
  // that still slips through, and per-doc isolation re-lists a throttled doc next cycle, so a cold start
  // converges politely over a cycle or two. Steady state fetches only the few newly-published docs, so
  // the delay is immaterial there. Tunable via the option; tests inject a no-op sleep.
  interFetchDelayMs: 300,
  // #21: an FR doc that fails this many CONSECUTIVE cycles is dead-lettered and stops being re-fetched on
  // the hot path (it was burning the FR rate budget by re-failing every cycle). 5 tolerates a transient.
  maxFailAttempts: 5,
  // #21: a dead-lettered FR doc is re-attempted by the drain sweep at most this often — a SLOW cadence so
  // a perma-failing doc cannot re-burn the budget, while a recovered doc still self-heals within ~6h.
  deadLetterRetryStaleAfterMs: 6 * 3_600_000,
  // #26 KEYWORD DISCOVERY trailing window. Amendment notices (extension/correction/reopening/withdrawal)
  // are published CLOSE in time to the window they amend (days/weeks), so a recent trailing window catches
  // them without paging all of FR history. 120 days is a comfortable margin over the typical correction/
  // extension lag while keeping each per-term list well under FR's 10k page ceiling (verified live: each
  // single-term query over a 120d window returns ~150–1,936 docs). Tunable; the differential-by-log skip
  // means re-listing the same window each cycle only re-fetches genuinely NEW docs.
  keywordLookbackDays: 120,
};

function resolveDeps(deps?: Partial<FrPollDeps>): FrPollDeps {
  return {
    listPage: deps?.listPage ?? ((o) => listOpenCommentDocuments(o)),
    listKeywordPage:
      deps?.listKeywordPage ?? ((o) => listAmendmentDocuments(o)),
    fetchDetail: deps?.fetchDetail ?? ((n) => fetchFrDocument(n)),
    now: deps?.now ?? (() => new Date()),
    sleep: deps?.sleep ?? ((ms) => new Promise((r) => setTimeout(r, ms))),
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
    keywordListed: 0,
    fetched: 0,
    ingested: 0,
    skipped: 0,
    pagesFetched: 0,
    truncated: false,
    deadLettered: 0,
    deadLetterRetried: 0,
    recovered: 0,
  };

  // The open-comment cutoff: TODAY in America/New_York (Eastern is the legal-publication zone; the FR
  // comment_date filter is date-granular and interpreted in Eastern). This is the open-set discovery filter.
  const commentOpenOnOrAfter = todayEastern(now);
  // The KEYWORD (amendment) discovery LOWER BOUND: a recent trailing publication-date window. Unlike the
  // open set (which must be the full open back-catalog, no date bound), amendment notices appear close in
  // time to the window they amend, so a trailing window is safe AND bounds the otherwise all-of-history
  // term search (see frKeywordListUrl). Eastern, day-granular, like the open-comment cutoff.
  const keywordPublishedOnOrAfter = easternDateDaysAgo(
    o.keywordLookbackDays,
    now,
  );

  // The whole cycle runs inside a try/finally: the "we ran" stamp (last_polled_at) MUST be written on
  // EVERY exit — including a list-phase failure (e.g. FR returns a 400 mid-page-walk) — so monitoring of
  // the federal_register stamp never goes dark on a failed cycle. The error still propagates (finally does
  // not swallow it) to run.ts's isolated FR try/catch. There is no FR date cursor (publication_date is
  // immutable, not a change cursor), so this stamp is the only operational state the FR poll persists.
  try {
    // Page ONE discovery query (open-set or one keyword term) to completion, accumulating into `sink`.
    // Counts pages into summary.pagesFetched and surfaces TRUNCATION honestly (a full last page at the
    // cap means coverage is incomplete — warn, never silently cap), for the keyword pages too. `label`
    // names the query in the truncation warning.
    const pageToCompletion = async (
      label: string,
      fetchPage: (page: number) => Promise<FrListItem[]>,
      sink: FrListItem[],
    ): Promise<void> => {
      for (let page = 1; page <= o.maxPages; page++) {
        const items = await fetchPage(page);
        summary.pagesFetched++;
        sink.push(...items);
        if (items.length < o.perPage) break; // a short page is the last
        if (page === o.maxPages && items.length === o.perPage) {
          // Stopped at the cap with a still-full page: coverage is INCOMPLETE — surface, don't swallow.
          summary.truncated = true;
          log.warn(
            { maxPages: o.maxPages, perPage: o.perPage, query: label },
            "fr poll hit maxPages with a full last page — coverage TRUNCATED (FR caps page * per_page at 10,000; beyond that switch to search_after_cursor)",
          );
        }
      }
    };

    // ── PAGE THE FULL OPEN-COMMENT LIST TO COMPLETION ─────────────────────────────────────────────────
    const openAccumulated: FrListItem[] = [];
    await pageToCompletion(
      "open-comment set",
      (page) => d.listPage({ commentOpenOnOrAfter, perPage: o.perPage, page }),
      openAccumulated,
    );

    // ── PAGE EACH KEYWORD (AMENDMENT) TERM TO COMPLETION (#26) ────────────────────────────────────────
    // FR `term` has no single-request OR (whitespace narrows the match; verified live — see
    // frKeywordListUrl), so we issue one single-term query per amendment keyword and union the results.
    // Each is paged to completion + truncation-checked exactly like the open set. The trailing
    // publication-date bound keeps each per-term set well under FR's 10k page ceiling.
    const keywordAccumulated: FrListItem[] = [];
    for (const term of AMENDMENT_TERMS) {
      await pageToCompletion(
        `keyword '${term}'`,
        (page) =>
          d.listKeywordPage({
            term,
            publicationDateOnOrAfter: keywordPublishedOnOrAfter,
            perPage: o.perPage,
            page,
          }),
        keywordAccumulated,
      );
    }
    // keywordListed: the distinct docs the keyword set contributed (pre-union, #26 visibility/metrics).
    summary.keywordListed = dedupeByDocumentNumber(keywordAccumulated).length;

    // UNION + dedupe the open-comment set with the keyword set into ONE working set. An amendment doc is
    // just another document number to ingest; everything downstream (differential-by-log skip, dead-letter
    // skip, throttle, per-doc fetch+parse+ingest+reconcile, retry sweep) is UNCHANGED. dedupeByDocumentNumber
    // collapses any doc that appears in BOTH sets so it is fetched at most once.
    const open = dedupeByDocumentNumber([
      ...openAccumulated,
      ...keywordAccumulated,
    ]);
    summary.listed = open.length;
    if (open.length === 0) return summary; // nothing to ingest; the finally still stamps "we ran"

    // ── DIFFERENTIAL BY THE LOG ─────────────────────────────────────────────────────────────────────────
    // Which of the listed doc numbers already carry a federal_register observation? Those are SKIPPED (FR
    // docs are immutable → a seen doc never needs re-fetching). A doc that previously FAILED is absent from
    // the log, so it is naturally re-listed here and retried below.
    const docNums = open.map((i) => i.documentNumber);
    // The `::text[]` cast is load-bearing, not decorative. This seenRows query is the FIRST statement on
    // the poller's fresh connection, and postgres.js's `sql.array(...)` sends the array param WITHOUT a
    // resolved element-type OID on a cold connection. Postgres 16 inferred the array type anyway, but
    // Postgres 18 rejects it at Parse time with `42809 op ANY/ALL (array) requires array on right side`
    // (a behavior change that bit us live: CNPG defaulted to PG18 while CI/tests run PG16). Passing the
    // bare JS array with an explicit `::text[]` cast makes the type unambiguous at Parse on any PG
    // version. (Note: `sql.array(x)::text[]` does NOT work — postgres.js stringifies it, yielding a
    // "malformed array literal" — so it's the bare-array + cast form specifically.)
    const seenRows = await sql<{ fr_document_number: string }[]>`
      select fr_document_number
      from observations
      where source = ${SOURCE}
        and fr_document_number = any(${docNums}::text[])
    `;
    const seen = new Set(seenRows.map((r) => r.fr_document_number));

    // #21: the currently DEAD-LETTERED FR docs. These are SKIPPED from the hot fetch path (a perma-failing
    // FR doc otherwise gets re-fetched + re-failed every cycle, burning the FR rate budget). They are
    // drained only by the slow retry sweep below. Docs still in BOUNDED retry (failed < N, not yet
    // dead-lettered) are NOT in this set, so they are still re-fetched every cycle — the correct
    // transient-failure behavior, identical to today.
    const dead = await deadLetteredKeys(sql, SOURCE);

    let fetchAttempts = 0; // FR detail fetches ATTEMPTED (success OR 429/fail) — drives the throttle gate
    for (const item of open) {
      if (seen.has(item.documentNumber)) {
        summary.skipped++;
        continue; // already in the log — no FR fetch, so no throttle either
      }
      if (dead.has(item.documentNumber)) {
        // Dead-lettered: NOT re-fetched on the hot path (recorded + alerted when it was dead-lettered, and
        // drained by the retry sweep). Folded into `skipped` (it is a no-fetch skip just like a seen doc).
        summary.skipped++;
        continue;
      }
      // Throttle BEFORE each FR detail fetch except the first (the cold-start politeness gate). Counts
      // ATTEMPTS, not successes, so the request RATE stays bounded even across a run of 429s.
      if (fetchAttempts > 0 && o.interFetchDelayMs > 0) {
        await d.sleep(o.interFetchDelayMs);
      }
      fetchAttempts++;
      try {
        const detail = await d.fetchDetail(item.documentNumber);
        summary.fetched++;
        const candidate = parseFrObservation(detail);
        const { inserted, ocdId } = await ingestObservation(sql, candidate);
        if (inserted) summary.ingested++;
        // RECONCILE-ALWAYS: idempotent re-derive from the append-only log for the doc we just fetched.
        await reconcileOcdId(sql, ocdId, now);
        // #21: success clears any accumulated failures (consecutive-failure reset); count a recovery only
        // if a ledger row actually existed (the doc HAD been failing). In steady state this is a no-op.
        if (await clearDeadLetter(sql, SOURCE, item.documentNumber))
          summary.recovered++;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        // Per-document isolation: one bad payload must not wedge the cycle. Log + continue. Below the
        // threshold the doc stays UNSEEN (no observation row) → re-listed + retried next cycle (today's
        // behavior). On the Nth consecutive failure it is DEAD-LETTERED: a loud alert, and from next cycle
        // it is skipped from the hot fetch path (stops burning the budget) — drained by the sweep instead.
        const { attempts, newlyDeadLettered } = await recordFailure(
          sql,
          SOURCE,
          item.documentNumber,
          msg,
          now,
          o.maxFailAttempts,
        );
        // Gate the loud alert + count on newlyDeadLettered (the threshold-crossing call), NOT the
        // level-triggered deadLettered — otherwise a doc that re-fails after being dead-lettered would
        // re-fire the alert + re-count every cycle (cry-wolf). FR already skips dead-lettered docs on the
        // hot path, so this is defensive consistency with the Regs path.
        if (newlyDeadLettered) {
          summary.deadLettered++;
          log.error(
            { err, documentNumber: item.documentNumber, attempts },
            "fr doc DEAD-LETTERED — will NO LONGER be re-fetched on the hot path; recorded for retry sweep",
          );
        } else {
          log.warn(
            {
              err,
              documentNumber: item.documentNumber,
              attempts,
              maxFailAttempts: o.maxFailAttempts,
            },
            "fr doc failed — skipping (retried via re-list next cycle)",
          );
        }
      }
    }

    // ── DEAD-LETTER RETRY SWEEP (#21) — the SLOW drain ─────────────────────────────────────────────────
    // Re-attempt dead-lettered FR docs whose drain throttle has gone stale. Respects the SAME inter-fetch
    // throttle (d.sleep) as the hot path so the sweep cannot burst FR. A recovered doc is cleared +
    // counted; one still broken bumps last_retry_at (+ attempts) so it is not re-attempted until stale
    // again. Runs INSIDE the try (so a sweep failure still hits the finally touchPolledAt). Per-doc
    // try/catch isolation.
    const dlRetry = await selectDeadLetteredForRetry(
      sql,
      SOURCE,
      new Date(now.getTime() - o.deadLetterRetryStaleAfterMs),
    );
    for (const dl of dlRetry) {
      summary.deadLetterRetried++;
      if (fetchAttempts > 0 && o.interFetchDelayMs > 0) {
        await d.sleep(o.interFetchDelayMs);
      }
      fetchAttempts++;
      try {
        const detail = await d.fetchDetail(dl.document_key);
        summary.fetched++;
        const candidate = parseFrObservation(detail);
        const { inserted, ocdId } = await ingestObservation(sql, candidate);
        if (inserted) summary.ingested++;
        await reconcileOcdId(sql, ocdId, now);
        if (await clearDeadLetter(sql, SOURCE, dl.document_key))
          summary.recovered++;
        log.info(
          { documentNumber: dl.document_key },
          "fr dead-lettered doc RECOVERED on retry sweep — cleared",
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        await markRetryAttempt(sql, SOURCE, dl.document_key, now, msg);
        log.warn(
          { err, documentNumber: dl.document_key },
          "fr dead-lettered doc STILL failing on retry sweep — re-throttled",
        );
      }
    }

    return summary;
  } finally {
    await touchPolledAt(sql, SOURCE, now); // "we ran" stamp on every exit (success, empty, or list failure)
  }
}
