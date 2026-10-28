/**
 * GovInfo source adapter — the PUBLISHED TEXT of an FR amendment document (FR amendment linking,
 * docs/plans/fr-amendment-linking.md part 1; ADR 0016).
 *
 * WHY THIS SOURCE EXISTS. The FR API's structured fields are not enough to move a window's close when an
 * amendment lands: the API's `dates` can be TRUNCATED mid-sentence (USDA 2026-19710 stops at "originally
 * published on September 11, 2026," — the citation and the new "on or before November 2, 2026" exist only
 * in the printed document), an amendment's own `comments_close_on` can be FR's extraction error (19710
 * says 2026-09-11, the ORIGINAL's publication date), and a correction document carries its new date only
 * in the published correction instruction (C1-2026-18574: ``October 16, 2026'' should read ``October 26,
 * 2026''). The GPO rendition on GovInfo is the legal-reliance text (docketclock.md "Data sources"), so it
 * is the one place those dates are stated in full. It enters the log as its own append-only observation
 * (source "govinfo" — an EXISTING ObservationSource and 0001 CHECK member; no contract or migration change).
 *
 * The URL is the window's own govinfo_url pattern — keyless, text/html, the content a <pre> block of the
 * GPO text:
 *   https://www.govinfo.gov/content/pkg/FR-{publication_date}/html/{docnum}.htm
 *
 * The observation lands on the AMENDMENT'S OWN ocd_id (makeOcdId({ frDocNum })) — it is evidence about
 * document B. Window A reads it through loadAmendmentEvidence (reconcile/persist.ts); B's own derivation
 * ignores the govinfo source entirely (reconcile.ts reads only FR + Regs + human_review).
 *
 * The sweep (govinfoSweepOnce) is the DB-aware half: it runs in the poll cycle after FR ingest and before
 * the chain pass, fetching the text for amendment documents in the keyword lookback that have no govinfo
 * observation yet. Append-only, payload-hash deduped, capped per cycle, 404 = "not published yet".
 */
import { makeOcdId } from "@yokel/contracts";
import type { Sql } from "../db/client.js";
import { componentLogger } from "../log.js";
import { ingestObservation } from "../ingest/observe.js";
import { reconcileOcdId } from "../reconcile/persist.js";
import { fetchTextWithRetry, type FetchOpts } from "./http.js";
import { payloadHash } from "./payload.js";
import { easternDateDaysAgo, todayEastern } from "./federal-register.js";
import {
  clearDeadLetter,
  markRetryAttempt,
  recordFailure,
} from "../poll/dead-letter.js";
import {
  ObservationCandidateSchema,
  type ObservationCandidate,
} from "./observation-candidate.js";

/** Pins the text-extraction rules below. Bump when govinfoPlainText / the section extractors change. */
export const PARSER_VERSION = "govinfo-v1";

/** Default GovInfo base. Overridable (e.g. a mock) via GOVINFO_API_BASE — mirrors FR_API_BASE. */
const DEFAULT_BASE = "https://www.govinfo.gov";

function govinfoBase(): string {
  return process.env.GOVINFO_API_BASE || DEFAULT_BASE;
}

/** The GPO HTML rendition URL for an FR document (same pattern as a window's govinfo_url). */
export function govinfoHtmlUrl(
  publicationDate: string,
  docNum: string,
  base: string = govinfoBase(),
): string {
  return `${base}/content/pkg/FR-${encodeURIComponent(publicationDate)}/html/${encodeURIComponent(docNum)}.htm`;
}

/**
 * GET the GPO HTML for one FR document. Shared retry scope (http.ts: network/429/5xx retry, other 4xx
 * fail fast). A 404 returns null — GovInfo publishes the rendition after the FR API lists the document,
 * so "not there yet" is a normal outcome the sweep skips and retries next cycle, never an error.
 */
export async function fetchGovinfoHtml(
  publicationDate: string,
  docNum: string,
  opts: FetchOpts = {},
): Promise<string | null> {
  return fetchTextWithRetry(govinfoHtmlUrl(publicationDate, docNum), {
    ...opts,
    accept: "text/html",
    notFoundAsNull: true,
  });
}

const NAMED_ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
};

/**
/**
 * Strip U+0000 from a GovInfo page. Real GPO renditions carry NUL bytes as page-break artifacts
 * ("\n\n\n\x00=====…" after the header, "\x00\x00Federal Register / Vol. 91, No. 136 /" running heads;
 * 49 of 717 live pages in the 2026-10-27 replay), and Postgres can store U+0000 in neither text nor
 * JSONB ("unsupported Unicode escape sequence"), so an unnormalized page fails ingest on every cycle,
 * forever. NUL carries no document content, so removing it is lossless for every reader we have — and it
 * is the ONE deliberate deviation from "raw is the verbatim upstream body" (Postgres cannot hold it).
 */
export function stripNul(s: string): string {
  return s.includes("\u0000") ? s.replace(/\u0000/g, "") : s;
}

/**
 * The GPO text of a GovInfo HTML page as plain text: the <pre> block when present (the page's <head>
 * title is not document text), NULs stripped (stripNul — they also sit at line starts, where they would
 * defeat the line-anchored section headers), tags stripped, entities decoded (&amp; &lt; &gt; &quot;
 * &#39; &apos; &nbsp; and numeric &#NNN; / &#xHH; — never to U+0000 or a lone surrogate, which stay
 * verbatim like an unknown entity), CRLF / CR normalized to LF. Line structure is PRESERVED — the
 * section extractors anchor on line starts. Unknown named entities are left verbatim (never guessed).
 */
export function govinfoPlainText(html: string): string {
  html = stripNul(html);
  const pre = /<pre\b[^>]*>([\s\S]*?)<\/pre>/i.exec(html);
  const body = pre ? pre[1]! : html;
  return body
    .replace(/<[^>]*>/g, "")
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, ent: string) => {
      if (ent[0] === "#") {
        const code =
          ent[1] === "x" || ent[1] === "X"
            ? parseInt(ent.slice(2), 16)
            : parseInt(ent.slice(1), 10);
        return Number.isFinite(code) &&
          code > 0 &&
          code <= 0x10ffff &&
          !(code >= 0xd800 && code <= 0xdfff)
          ? String.fromCodePoint(code)
          : whole;
      }
      return NAMED_ENTITIES[ent.toLowerCase()] ?? whole;
    })
    .replace(/\r\n?/g, "\n");
}

/** Collapse every whitespace run (incl. line breaks / NBSP) to one space, trimmed. */
function collapse(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

/** The section headers that END a DATES section in the GPO preamble. */
const NEXT_SECTION =
  /^\s*(?:ADDRESSES|FOR FURTHER INFORMATION CONTACT|SUPPLEMENTARY INFORMATION):/m;

/**
 * The DATES section of a GPO document: the text after a line-initial `DATES:` up to the next preamble
 * header (ADDRESSES: / FOR FURTHER INFORMATION CONTACT: / SUPPLEMENTARY INFORMATION:) or the end,
 * whitespace-collapsed to single spaces, the `DATES:` label itself dropped. null when there is no DATES
 * section (or it is empty). Line-anchored on purpose: a correction's "…second line of the DATES section"
 * is prose, not the header.
 */
export function extractDatesSection(text: string): string | null {
  const start = /^\s*DATES:/m.exec(text);
  if (!start) return null;
  const rest = text.slice(start.index + start[0].length);
  const end = NEXT_SECTION.exec(rest);
  const section = collapse(end ? rest.slice(0, end.index) : rest);
  return section.length > 0 ? section : null;
}

/**
 * The correction instructions of an FR correction document: from the first line reading "In [proposed
 * rule|rule|notice|presidential] document {docnum} beginning on page …" up to the closing "[FR Doc."
 * line (or the end), whitespace-collapsed. null when absent — the document is not in the GPO correction
 * format, and the caller has nothing to read a corrected date from.
 */
export function extractCorrectionBody(text: string): string | null {
  const start =
    /^\s*In (?:proposed rule|rule|notice|presidential)?\s*document\s+\S+\s+beginning on page/im.exec(
      text,
    );
  if (!start) return null;
  const rest = text.slice(start.index);
  const end = rest.indexOf("[FR Doc.");
  const body = collapse(end >= 0 ? rest.slice(0, end) : rest);
  return body.length > 0 ? body : null;
}

/**
 * Map one fetched GovInfo page into a validated govinfo Observation candidate on the AMENDMENT's own
 * ocd_id. `raw` is the upstream body plus the identity it was fetched under (replayable) — verbatim
 * EXCEPT for U+0000, which is stripped (stripNul: Postgres text/JSONB cannot store it; GPO page-break
 * artifacts only). payload_hash is over that NORMALIZED raw, so it is deterministic and an unchanged
 * page re-fetched dedupes in the normal ingest path; raw_dates_text derives from the same normalized html.
 * raw_dates_text is the text the amendment resolver reads: the correction instructions for a correction
 * document (falling back to a DATES section when the document is not in the GPO correction format), the
 * DATES section otherwise. All four notice flags are FALSE — this row is evidence text, never a
 * classification (the FR observation of the same document carries those).
 */
export function parseGovinfoObservation(input: {
  frDocNum: string;
  publicationDate: string;
  url: string;
  html: string;
  isCorrection: boolean;
  fetchedAt?: string;
}): ObservationCandidate {
  if (!input.frDocNum)
    throw new Error("parseGovinfoObservation: frDocNum is required");
  // Normalized ONCE: everything stored or hashed below derives from the NUL-free page.
  const html = stripNul(input.html);
  const raw = {
    document_number: stripNul(input.frDocNum),
    publication_date: stripNul(input.publicationDate),
    url: stripNul(input.url),
    html,
  };
  const text = govinfoPlainText(html);
  const datesText = input.isCorrection
    ? (extractCorrectionBody(text) ?? extractDatesSection(text))
    : extractDatesSection(text);

  const candidate: ObservationCandidate = {
    ocd_id: makeOcdId({ frDocNum: input.frDocNum }),
    source: "govinfo",
    fr_document_number: input.frDocNum,
    regs_document_id: null,
    regs_object_id: null,
    payload_hash: payloadHash(raw),
    fetched_at: input.fetchedAt ?? new Date().toISOString(),
    parser_version: PARSER_VERSION,
    raw_dates_text: datesText,
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    is_reopening: false,
    raw,
  };

  const parsed = ObservationCandidateSchema.safeParse(candidate);
  if (!parsed.success)
    throw new Error(
      `parseGovinfoObservation: candidate failed Observation validation: ${JSON.stringify(parsed.error.issues)}`,
    );
  return candidate;
}

// ── the sweep (DB-aware) ─────────────────────────────────────────────────────────────────────────────

const log = componentLogger("poller");

/** Default per-cycle fetch cap; env GOVINFO_MAX_FETCHES_PER_CYCLE overrides (positive integer). */
export const DEFAULT_GOVINFO_MAX_FETCHES = 50;

export function govinfoMaxFetches(): number {
  const n = Number(process.env.GOVINFO_MAX_FETCHES_PER_CYCLE);
  return Number.isInteger(n) && n > 0 ? n : DEFAULT_GOVINFO_MAX_FETCHES;
}

export interface GovinfoSweepOptions {
  /** fetches per cycle (default govinfoMaxFetches()). Excess candidates wait for the next cycle. */
  cap?: number;
  /** publication-date lookback in days — the FR keyword discovery window (default 120). */
  lookbackDays?: number;
  /** transport; defaults to fetchGovinfoHtml. null = 404 / not published yet. Tests inject a fake. */
  fetchHtml?: (
    publicationDate: string,
    docNum: string,
  ) => Promise<string | null>;
  /** delay between fetches (polite to GovInfo). Defaults to a real 300ms sleep; tests pass a no-op. */
  sleep?: (ms: number) => Promise<void>;
  interFetchDelayMs?: number;
  /**
   * A 404 for a document published MORE than this many days ago (Eastern) counts as a failure (GovInfo
   * publishes on the publication date, so a late 404 is very likely permanent); on or within it, a 404
   * is the normal "not published yet" and is never recorded. Default 3.
   */
  notFoundGraceDays?: number;
  /** consecutive failures before a document is dead-lettered (poll_dead_letter, source govinfo). Default 3. */
  maxFailAttempts?: number;
  /** a dead-lettered document is re-attempted at most this often (the slow drain). Default 24h. */
  deadLetterRetryStaleAfterMs?: number;
}

export interface GovinfoSweepSummary {
  /** amendment documents in the lookback with no govinfo observation yet (before the cap). */
  candidates: number;
  /** fetch attempts made this cycle (<= cap). */
  fetched: number;
  /** pages that appended a new govinfo observation. */
  ingested: number;
  /** 404s within the grace window — not on GovInfo yet; retried next cycle, never recorded. */
  notPublished: number;
  /** fetch / parse / ingest failures and late 404s (recorded in poll_dead_letter), plus reconcile failures. */
  failed: number;
  /** documents newly dead-lettered this cycle (crossed maxFailAttempts). */
  deadLettered: number;
  /** dead-lettered documents re-attempted by the slow drain this cycle. */
  deadLetterRetried: number;
  /** dead-lettered documents skipped this cycle (not yet due for the slow drain). */
  deadLetterSkipped: number;
}

/**
 * govinfoSweepOnce — fetch the published text of every recent FR amendment document that has no govinfo
 * observation yet, ingest it append-only, and re-derive that document's window.
 *
 * Candidates: the LATEST federal_register observation per ocd_id that carries any of the four amendment
 * flags OR a non-empty `correction_of` (the derived fr-v3 correction rule — fr-v2 rows are never
 * backfilled), published on or before Eastern today (GovInfo has nothing before publication — a
 * public-inspection fetch can predate it) and no earlier than today − lookbackDays (the keyword discovery
 * window: an amendment matters only near its original), with NO govinfo observation for that ocd_id.
 * Newest publication first, capped. On first deploy this backfills every existing amendment in the
 * lookback — append-only, no UPDATEs.
 *
 * Isolation: a 404 within notFoundGraceDays of publication skips (retried next cycle); any other failure
 * is logged and counted, never thrown — the sweep must not starve the chain pass that follows it.
 * Single-writer like every poll pass.
 *
 * STARVATION GUARD (the 2026-10-27 replay: 49 documents that failed every cycle sat at the head of a
 * 50-fetch, newest-first cap). Failures go through the shared bounded-retry ledger (poll_dead_letter,
 * source "govinfo", key = FR document number — the #21 machinery the FR and Regs pollers use):
 *   • ordering is (consecutive failures ASC, publication_date DESC): a document that has never failed
 *     always outranks one that has, so a fresh candidate is fetched no later than the cycle after the
 *     one in which every candidate ahead of it failed once — independent of how many keep failing;
 *   • after maxFailAttempts consecutive failures a document is DEAD-LETTERED: it leaves the hot set and
 *     is re-attempted only by the slow drain (at most once per deadLetterRetryStaleAfterMs), still behind
 *     every never-failed candidate;
 *   • a late 404 (published more than notFoundGraceDays ago) is a failure like any other; a 404 within
 *     the grace window is normal and leaves no ledger row;
 *   • a successful ingest clears the row (a recovered document resets).
 */
export async function govinfoSweepOnce(
  sql: Sql,
  now: Date = new Date(),
  opts: GovinfoSweepOptions = {},
): Promise<GovinfoSweepSummary> {
  const cap = opts.cap ?? govinfoMaxFetches();
  const lookbackDays = opts.lookbackDays ?? 120;
  const fetchHtml =
    opts.fetchHtml ?? ((p: string, d: string) => fetchGovinfoHtml(p, d));
  const sleep =
    opts.sleep ?? ((ms: number) => new Promise<void>((r) => setTimeout(r, ms)));
  const delay = opts.interFetchDelayMs ?? 300;
  const graceDays = opts.notFoundGraceDays ?? 3;
  const threshold = opts.maxFailAttempts ?? 3;
  const retryStaleBefore = new Date(
    now.getTime() - (opts.deadLetterRetryStaleAfterMs ?? 24 * 3_600_000),
  );
  const today = todayEastern(now);
  const earliest = easternDateDaysAgo(lookbackDays, now);
  const graceFloor = easternDateDaysAgo(graceDays, now);

  const rows = await sql<
    {
      ocd_id: string;
      fr_document_number: string;
      publication_date: string;
      is_correction: boolean;
      correction_of: string | null;
      attempts: number;
      dead_lettered: boolean;
      due: boolean;
    }[]
  >`
    with latest_fr as (
      select distinct on (ocd_id)
        ocd_id, fr_document_number, is_extension, is_correction, is_withdrawal, is_reopening,
        raw->>'publication_date' as publication_date,
        raw->>'correction_of' as correction_of
      from observations
      where source = 'federal_register'
      order by ocd_id, fetched_at desc, observation_id desc
    )
    select l.ocd_id, l.fr_document_number, l.publication_date, l.is_correction, l.correction_of,
           coalesce(d.attempts, 0)::int as attempts,
           (d.dead_lettered_at is not null) as dead_lettered,
           (d.dead_lettered_at is null
             or coalesce(d.last_retry_at, d.dead_lettered_at) < ${retryStaleBefore.toISOString()}) as due
    from latest_fr l
    left join poll_dead_letter d
      on d.source = 'govinfo' and d.document_key = l.fr_document_number
    where (is_extension or is_correction or is_withdrawal or is_reopening
           or coalesce(correction_of, '') <> '')
      and fr_document_number is not null
      and publication_date ~ '^\\d{4}-\\d{2}-\\d{2}$'
      and publication_date <= ${today}
      and publication_date >= ${earliest}
      and not exists (
        select 1 from observations g
        where g.ocd_id = l.ocd_id and g.source = 'govinfo'
      )
    order by coalesce(d.attempts, 0) asc, l.publication_date desc, l.ocd_id
  `;

  const due = rows.filter((r) => r.due);
  const summary: GovinfoSweepSummary = {
    candidates: rows.length,
    fetched: 0,
    ingested: 0,
    notPublished: 0,
    failed: 0,
    deadLettered: 0,
    deadLetterRetried: 0,
    deadLetterSkipped: rows.length - due.length,
  };

  /** Record one failure in the ledger (a dead-letter retry advances the slow-drain throttle instead). */
  const fail = async (r: (typeof rows)[number], msg: string) => {
    summary.failed++;
    try {
      if (r.dead_lettered) {
        await markRetryAttempt(sql, "govinfo", r.fr_document_number, now, msg);
      } else {
        const f = await recordFailure(
          sql,
          "govinfo",
          r.fr_document_number,
          msg,
          now,
          threshold,
        );
        if (f.newlyDeadLettered) {
          summary.deadLettered++;
          log.warn(
            { fr_document_number: r.fr_document_number, attempts: f.attempts },
            "govinfo sweep: document DEAD-LETTERED — slow drain only from now on",
          );
        }
      }
    } catch (err) {
      // The ledger is an optimization; failing to write it must never abort the sweep.
      log.error({ err }, "govinfo sweep: dead-letter ledger write failed");
    }
  };

  for (const r of due.slice(0, cap)) {
    if (summary.fetched > 0 && delay > 0) await sleep(delay);
    summary.fetched++;
    if (r.dead_lettered) summary.deadLetterRetried++;
    let ingested = false;
    try {
      const html = await fetchHtml(r.publication_date, r.fr_document_number);
      if (html === null) {
        if (r.publication_date >= graceFloor) {
          summary.notPublished++; // normal: GovInfo has not rendered it yet
        } else {
          await fail(
            r,
            `govinfo 404: not on GovInfo ${graceDays}+ days after publication ${r.publication_date}`,
          );
        }
        continue;
      }
      const candidate = parseGovinfoObservation({
        frDocNum: r.fr_document_number,
        publicationDate: r.publication_date,
        url: govinfoHtmlUrl(r.publication_date, r.fr_document_number),
        html,
        isCorrection:
          r.is_correction || (r.correction_of ?? "").trim().length > 0,
        fetchedAt: now.toISOString(),
      });
      const ingest = await ingestObservation(sql, candidate);
      if (ingest.inserted) summary.ingested++;
      ingested = true;
      await clearDeadLetter(sql, "govinfo", r.fr_document_number);
      await reconcileOcdId(sql, r.ocd_id, now);
    } catch (err) {
      log.error(
        { err, ocd_id: r.ocd_id, fr_document_number: r.fr_document_number },
        "govinfo sweep: document failed",
      );
      // A failure AFTER the ingest committed (the window re-derive) is not the document's fault — the
      // page is in the log, so it has already left the candidate set; count it, never ledger it.
      if (ingested) summary.failed++;
      else await fail(r, err instanceof Error ? err.message : String(err));
    }
  }
  return summary;
}
