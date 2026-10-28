# FR amendment linking — a linked correction/extension moves the FR side of the window

Status: implemented on branch `t3/fr-amendment-linking` (uncommitted). This was the starting spec;
the shipped design, including everything adversarial review added (clause roles, the history-aware verdict
freshness rule, the corroboration backstop), is recorded in `docs/decisions/0016-fr-amendment-close.md`,
which is authoritative where they differ.

## Root cause (evidence: read-only queries against the k3d DB, 2026-10-27, and the live FR API)

Every window's FR side comes from ONE place: `reconcile()` (`src/reconcile/reconcile.ts`) reads the
latest `federal_register` observation **of that window's own ocd_id** and takes its
`comments_close_on`. An amendment is a separate FR document with its own ocd_id. The chain pass
(`chain.ts` → `persistChainConflicts`) only writes a `cross_window` ConflictRecord; nothing feeds
the amendment back into window A's derivation. So the original close stays the FR value forever,
and the window sits CONFLICTING (`fr_regs_date_mismatch`) against a portal that already moved.

All three amendments ARE ingested (keyword path works). Per document:

| A (original)      | B (amendment) | ingested?             | chained?                                                                                                                                                                                                                                                                                                                      | why A's date never moved                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------- | ------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-18481 Census | 2026-20328    | yes, `is_extension=t` | **yes, confident** (shared docket `Docket No. 260903-0005` + RIN `0607-AA75`); live cross_window `extension_chain_unresolved` since 2026-10-03                                                                                                                                                                                | linked but the date is never taken (the general cause above). B's FR `dates` and `comments_close_on` both say 2026-11-02.                                                                                                                                                                                                                                                                 |
| 2026-18531 USDA   | 2026-19710    | yes, `is_extension=t` | **yes, via LLM only** (gemini `affirm`, 2026-09-25): no RINs, and the FR DATES text doesn't name the doc number                                                                                                                                                                                                               | (1) the general cause; (2) the FR API `dates` field is **truncated** mid-sentence (`"The comment period for the document originally published on September 11, 2026,"`): the citation `(91 FR 57828)` and `on or before November 2, 2026` exist only in the published text (GovInfo); (3) B's own `comments_close_on` is `2026-09-11` (FR's extraction error: it's A's publication date). |
| 2026-18574 IRS    | C1-2026-18574 | yes                   | **no**: `is_correction=f`. A correction doc's FR `title` has no "Correction" suffix, and `action`/`dates`/`abstract` are empty, so the keyword flags never fire and it never becomes a chain candidate. The FR API does carry structured identity: B `correction_of` = `…/documents/2026-18574`, and A `corrections` lists B. | (1) never chained; (2) the new date exists only in the published correction text: ` `October 16, 2026'' should read `October 26, 2026'' ` in the DATES section.                                                                                                                                                                                                                           |

Side findings:

- **ICE 2026-20660**: the stored FR observation (fetched 2026-10-08) has `comments_close_on`
  2026-12-07 (the PRA information-collection date). Today's FR API says 2026-11-09. FR **revised its
  own metadata** after we fetched. The FR poller never re-fetches a document already in the log, because
  FR documents are treated as immutable. DATES carries both dates. No amendment is involved, so it's out of
  scope here and must stay unchanged. Follow-up: re-fetch FR metadata for open windows.
- **USCG 2026-19895**: a reopening. Its own `comments_close_on` (2026-08-24) is the reopened notice's
  publication date; DATES says October 29. It's linked (LLM) to 2026-17216 as `reopening`. Out of scope, unchanged.
- **PHMSA 2026-19351**: a meeting notice (docket PHMSA-2026-2773, not the NPRMs' dockets). It was never
  ingested and carries no amendment flags. Its "written comments … by November 20, 2026" is a post-lapse
  reopening in substance.
- **EPA 2026-18134**: its extension exists only as a Regs.gov docket memo. There's no FR amendment, so it's unchanged.

## Design

Five parts. A conservative rule runs through all of them: only a **deterministically identified**
amendment whose new date is **stated in the published text and verified** may move A's FR side.
Anything else leaves A exactly as today, and the cross_window conflict stays visible.

### 1. GovInfo text observations for amendment documents (`src/sources/govinfo.ts`, new)

- The URL is `https://www.govinfo.gov/content/pkg/FR-{publication_date}/html/{docnum}.htm`, the same
  pattern as the window's `govinfo_url`. It's keyless, `text/html`, and the content is a `<pre>` block
  of the GPO text. A `GOVINFO_API_BASE`-style override exists for tests (mirror `FR_API_BASE`).
- `govinfoPlainText(html)`: strip tags, decode entities (`&amp; &lt; &gt; &quot; &#39;` and numeric),
  normalize CRLF. Returns the plain text.
- `extractDatesSection(text)`: the text from `DATES:` up to the next section header (`ADDRESSES:`,
  `FOR FURTHER INFORMATION CONTACT:`, `SUPPLEMENTARY INFORMATION:`, or end), whitespace-collapsed to
  single spaces. Returns null if absent.
- `extractCorrectionBody(text)`: for a correction document, the text from the first line matching
  `/^\s*In (?:proposed rule|rule|notice|presidential)?\s*document\s+\S+\s+beginning on page/im`
  up to `[FR Doc.`, whitespace-collapsed. Returns null if absent.
- `parseGovinfoObservation({ frDocNum, publicationDate, url, html, isCorrection })` →
  `ObservationCandidate` with `source: "govinfo"` (an EXISTING ObservationSource and DB check member,
  so no contract or migration change), `ocd_id: makeOcdId({ frDocNum })` (the amendment's own window),
  `fr_document_number: frDocNum`, `raw: { document_number, publication_date, url, html }` (verbatim
  upstream body), `payload_hash: payloadHash(raw)`, `raw_dates_text` = correction body when
  `isCorrection` else DATES section, all four flags `false`, `parser_version: "govinfo-v1"`.
- `fetchGovinfoHtml(publicationDate, docNum, opts)`: the shared retry scope (http.ts). Add a
  `fetchTextWithRetry` sibling of `fetchJsonWithRetry`, with the same retry rules. A 404 is a normal
  "not published yet" outcome, not an error.
- **Sweep** (`govinfoSweepOnce(sql, now, opts)`, wired into `poll/run.ts` after FR ingest and before
  the chain pass): select the latest FR observation per ocd_id where (any of the 4 flags OR
  `raw->>'correction_of'` is non-empty) AND `publication_date` <= Eastern today AND `publication_date`
  > = today − `keywordLookbackDays` (120) AND no `govinfo` observation exists for that ocd_id. For each,
  > fetch, parse, and ingest through the normal ingest path (payload-hash dedup), then reconcile that
  > ocd_id. A per-cycle cap (default 50, env override) limits fetches. On a 404, skip; it retries next
  > cycle. The sweep also backfills existing amendments on first deploy, append-only with no UPDATEs.

### 2. FR parser: `correction_of` is a correction (`federal-register.ts`)

`frNoticeFlags(raw)`: `is_correction = rulebox || nonEmpty(raw.correction_of)`. Bump
`PARSER_VERSION` to `fr-v3`. Old rows aren't backfilled. Instead, every read that builds a chain or
amendment candidate derives `is_correction` as `row.is_correction || nonEmpty(raw.correction_of)` (a
shared helper in extract.ts), so fr-v2 rows behave identically to fr-v3 ones.

### 3. Deterministic identity (`chain.ts`)

`ChainCandidate` gains `citation: string | null` (FR `citation`, e.g. `"91 FR 57828"`),
`correction_of: string | null` (the doc number parsed from the `correction_of` URL's last path
segment), `corrections: string[]` (doc numbers parsed from A's `corrections` URLs), and
`govinfo_text: string | null` (the amendment's latest govinfo `raw_dates_text`).

New exported pure function `linkBasis(a, b, citationIndex): LinkBasis | null`, where
`LinkBasis = "correction_of" | "citation" | "doc_number" | "docket_rin"` and `citationIndex: Map<citation, count of distinct FR doc numbers among ALL candidates carrying it>`:

- `correction_of`: `b.correction_of === a.fr_document_number`. Strongest. No docket required.
- `doc_number`: shared docket AND B's FR dates text OR govinfo text names A's doc number (the existing
  tolerant whole-token matcher, applied to both texts).
- `docket_rin`: shared docket AND shared non-empty RIN (existing rule).
- `citation`: B's govinfo text or FR dates text contains A's `citation` exactly as a whole token
  (`/(?<![\d])91 FR 57828(?![\d])/`; no page arithmetic, no pin-cite ranges), AND
  `citationIndex.get(a.citation) === 1` (start pages aren't unique; two candidates with the same
  citation means no link by citation), AND at least one corroborator: shared docket, shared non-empty
  RIN, or B's title starts with A's full title (case-insensitive, whitespace-normalized). A shared RIN
  is only ever a corroborator, never sufficient alone. No shared docket is required, so an amendment
  under a different docket is still found.

chainCore uses `linkBasis` for rule 2. Rule 1 (shared docket) now gates only the docket-based bases.
Rules 3 (B after A), 4 (recency) and 5 (deny-list) are unchanged and still apply to every basis. The
ambiguous/LLM tail keeps its old definition: structural rules pass with a shared docket, but no
deterministic basis. Expected and acceptable: some former LLM-only links (e.g. USDA) become
confident, losing `llm_corroborated`.

### 4. Amendment close resolution (`src/reconcile/amendment.ts`, new, PURE)

```ts
export interface AmendmentEvidence {
  ocd_id: string;
  fr_document_number: string;
  fr_observation_id: string;
  govinfo_observation_id: string | null;
  publication_date: string; // B's FR publication_date
  is_extension: boolean;
  is_correction: boolean;
  is_reopening: boolean;
  is_withdrawal: boolean;
  fr_comments_close_on: string | null; // B's own FR value, validated calendar date or null
  fr_dates_text: string | null; // B's FR JSON `dates` (may be truncated)
  govinfo_text: string | null; // B's govinfo raw_dates_text (DATES section / correction body)
  basis: LinkBasis; // deterministic only — LLM-only links are never evidence
}
export type AmendmentOutcome =
  | { kind: "none" }
  | {
      kind: "amended";
      date: string /* YYYY-MM-DD Eastern */;
      amendment: AmendmentEvidence;
      change: "extension" | "correction";
      observation_ids: string[];
    }
  | { kind: "ambiguous"; reasons: string[] };
export function resolveAmendedClose(
  original: {
    fr_close: string | null;
    publication_date: string | null;
    fr_document_number: string | null;
  },
  amendments: AmendmentEvidence[],
): AmendmentOutcome;
```

Rules (each a named, tested predicate):

1. If any linked amendment is a **reopening** or **withdrawal**, return `ambiguous`. A post-lapse
   reopening is a distinct legal event (O4) and never becomes an extension; a withdrawal is not a close.
2. **Correction**: use only `govinfo_text`. Find ` `X'' should read `Y'' ` (also accept straight or
   curly double quotes) where the body mentions `DATES`, X and Y both parse as `Month D, YYYY`, and X equals
   `original.fr_close`. Then the date is Y. A correction that touches other text yields no date
   (`none`, not ambiguous). Two such pairs giving different Ys means `ambiguous`.
3. **Extension** (`is_extension && !is_reopening`): the text is `govinfo_text` if present. Otherwise
   use `fr_dates_text`, but only when its date equals a valid `fr_comments_close_on` (two signals).
   Collect dates appearing in deadline phrases: `on or before D`, `no later than D`,
   `(?:extended|reopened)? ?(?:to|until|through) D`, `must be (?:received|submitted|postmarked) (?:by|on or before|no later than) D`,
   `(?:closes?|ends?) on D`. Ignore dates preceded by `published (?:on )?` or `dated`. Exactly one
   distinct date means a candidate; zero means `none`; two or more means `ambiguous` (the ICE rule+PRA
   pattern).
   - **Post-lapse guard**: B's `publication_date` must be <= `original.fr_close`. Otherwise it's a
     reopening in substance, so `ambiguous`.
   - It must be > `original.fr_close` (an extension moves later). Otherwise `ambiguous`.
   - Cross-check: if `fr_comments_close_on` is a valid date AND > B's `publication_date`, it must equal
     the text date, else `ambiguous`. If it's null or <= B's publication date (USDA's `2026-09-11`), it's
     ignored as an FR extraction error, and `reasons` records that.
4. Several date-bearing amendments: order by `publication_date`, latest wins. Two on the same
   publication date with different dates means `ambiguous`. Any amendment that is `ambiguous` makes the
   whole outcome `ambiguous`.
5. `observation_ids` = B's FR observation id plus its govinfo observation id (if used).

### 5. Reconcile integration (`reconcile.ts`, `persist.ts`): `reconcile-v2.4`

- `reconcile(observations, now, options?: { amendment?: AmendmentOutcome })`. With `kind: "amended"`,
  the FR side's Eastern close becomes `date` (`frEastern := date`) **before** the rulebook runs, so the
  FR-vs-Regs comparison is unchanged: agreement gives HIGH or MEDIUM per the existing rules, and a
  mismatch gives CONFLICTING with the amended value. Add the informational ConflictFlag
  **`fr_close_amended`** (new contract member). Display:
  `closes D at 11:59 p.m. ET (per FR {extension|correction} {docnum}; inferred from FR date-only value)`
  when the FR side drives the display. `raw_fr_close_date` stays the original raw FR value (it is the
  raw field). `current_observation_ids` and provenance include `observation_ids`. `ambiguous` and
  `none` give byte-identical output to today. An honored human verdict overlay still applies after,
  exactly as today. `RECONCILER_VERSION = "reconcile-v2.4"`.
- `loadAmendmentEvidence(sql, ocdId)` in persist.ts: read A's latest FR observation. Read candidate
  amendments: the latest FR observation per other ocd_id whose (derived) flags include any of the four AND
  (shared docket OR `correction_of` names A OR B's dates/govinfo text contains A's citation or doc
  number). Attach each B's latest govinfo observation. Build ChainCandidates and the citation index
  (distinct FR doc numbers by `raw->>'citation'` over all latest FR observations), and keep Bs where
  `linkBasis(a, b, idx)` is non-null and B was published after A. Then call `resolveAmendedClose`.
- **Every path that derives a window must pass the same amendment outcome** (same log in, same window
  out): `reconcileOcdId`, the rederive sweep, status-refresh, and the review CLI/core (which asks the
  engine about a window). Find every caller of `reconcile(`. A path that skips it would flip A back on
  its next Regs poll.
- **Trigger**: after the chain pass in `poll/run.ts`, re-derive (`reconcileOcdId`) every side-A ocd_id
  of the confident link set so a newly arrived amendment moves A in the same cycle. This is idempotent.

### Contract (`packages/contracts`, contract-keeper discipline)

A versioned addition, never a fork: `ConflictFlag += "fr_close_amended"` with a doc comment in the
`llm_corroborated` style (informational provenance; composes with any confidence; means "the FR side
of this window is the close stated by a deterministically linked FR correction/extension, verified
from its published text"). Bump `0.11.0` → `0.12.0` and add a header changelog entry. Check whether any DB
check constraint enumerates conflict flags; if one does, add a migration.

## Required outcomes (the acceptance fixtures; all from `apps/docketclock/test/fixtures/fr-amendments/`)

- 2026-18481 + 2026-20328: A's FR side is 2026-11-02, which agrees with the portal (2026-11-03T04:59:59Z = Nov 2 ET). The window becomes HIGH with `fr_close_amended` (plus `tz_normalization_only` if applicable), no longer CONFLICTING.
- 2026-18531 + 2026-19710 (+ govinfo): basis `citation` (docket shared). Date 2026-11-02 from the GovInfo DATES. B's own `comments_close_on` 2026-09-11 is ignored. The window becomes HIGH with `fr_close_amended`. Without the govinfo observation, the outcome is `none` (the FR dates are truncated), so the window is unchanged.
- 2026-18574 + C1-2026-18574 (+ govinfo): basis `correction_of`. Oct 16 → Oct 26, which agrees with the portal 2026-10-27T03:59:59Z. The window becomes HIGH with `fr_close_amended`.
- PHMSA 2026-08068/08077/10969 with 2026-19351: never amended. Also test a synthetic variant where 19351 is flagged extension or reopening and cites the NPRM: it must still not move the close (post-lapse guard / reopening rule).
- USCG 2026-19895 and its A 2026-17216: unchanged.
- ICE 2026-20660 (stored 12-07 observation): unchanged. A synthetic extension whose DATES carries both the rule and PRA dates gives `ambiguous`.
- EPA 2026-18134: unchanged.
- Identity negatives: a shared RIN alone (different dockets, no citation, no correction_of) gives no link. A citation carried by two candidates gives no citation link. A citation inside a pin-cite range (e.g. `91 FR 57820, 57828`) gives no match for `91 FR 57828` unless whole-token. An amendment under a different docket whose text carries A's unique citation and whose title starts with A's title is linked.
