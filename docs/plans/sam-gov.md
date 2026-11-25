# SAM.gov: agency tree and contract opportunities

Status: v1 ingestion built (migration 0015, `src/sources/sam-gov.ts`, `src/sam/sync.ts`). Nothing exposed on
the API or MCP surface yet.

## Why

- **Federal Hierarchy** gives a clean department → sub-tier tree with stable ids (`fhorgid`). It is the
  agency key for "what opened in my area" filters, and later the shared key between comment windows and
  contract deadlines (an FR-agency-slug → fhorgid map is a follow-up, not built).
- **Contract Opportunities** are solicitations with a response deadline: a second kind of deadline to keep
  memory of, with the same "what did the source say, and when" value as comment windows.

## Constraints that shape it

- **Rate limit.** GSA documents 10 requests/day for a non-federal key without a SAM.gov role (1,000/day with
  a role or a federal account). The pass budgets `SAM_DAILY_REQUEST_CAP = 9` per UTC day across both APIs
  (`sam_request_budget`), never retries (each retry is a request), and treats a 429 as "done for today",
  not a failure, so it cannot cause alert flaps.
- **The key goes in the URL** (`api_key=`). Errors are rethrown as `SamRequestError` with the key redacted;
  spans already strip query strings (`spanUrl`).
- **Latest version only.** The Opportunities API serves the current version of a notice. Each distinct
  payload we see appends its own row, so amendments are kept as we observe them, dated by both
  `fetched_at` (seen) and `source_modified_at` (the notice's `postedDate`, valid-from).
- **Public FH stops at sub-tier.** Offices need a federal (FOUO) account. Opportunities carry their full
  office path (`fullParentPathCode`/`Name`) anyway, and we keep it on every deadline.

## Data model (migration 0015)

| table                | role                                                                                                                                                                                                                        |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sam_observations`   | append-only raw log (same reject-mutation triggers as `observations`), payload-hash dedupe against the latest row per entity, `subject_id` like `ocd-contract-opportunity/federal/<noticeId>` / `ocd-federal-org/<fhorgid>` |
| `federal_orgs`       | projection: name, type, status, parent (department), agency code, CGAC, first/last seen                                                                                                                                     |
| `contract_deadlines` | projection per notice: deadline as an instant **and** verbatim (`response_deadline_raw` keeps the stated offset and is the provenance quote), agency fhorgid, public link, `deadline_changed_at`, first/last seen           |
| `sam_request_budget` | per-UTC-day request counter + 429 marker                                                                                                                                                                                    |
| `sam_sync_state`     | per source: `backfill` or `delta`, page offset, window                                                                                                                                                                      |

A deadline without an explicit offset is stored raw with `response_deadline = null`: we never guess a zone.

## Sync

Both sources run the same state machine, FH first (it is small and opportunities resolve against it):

- **backfill**: FH pages through every org (about 12 requests, 100/page); Opportunities pages through every
  notice whose response deadline falls in the next year (1,000/page). Offsets persist, so a backfill cut by
  the budget resumes the next day.
- **delta**: at most once per 20h. FH: `updateddatefrom` since the last window. Opportunities: `postedFrom`
  since the last window (overlapping one day; the hash dedupe makes the overlap free).

Steady state is about 2–4 requests a day. Neon traffic is a few MB a day of writes.

## Open, to confirm with a live key

1. The `responseDeadLine` format and zone (the docs don't say; the parser accepts only ISO with an offset).
2. That an amended notice comes back with a newer `postedDate` (else the posted-date delta misses it, and
   we would add a re-check of open notices by deadline window).
3. FH default `status` is active only, so an org that goes inactive may never appear in a delta.
4. Whether the Opportunities API shares FH's 10/day limit (its page gives no numbers).
5. The `fullParentPathCode` → `agency_code` match used for agency resolution.

## Not in v1

Description text (one request per notice), attachments, the Data Services bulk CSV, office-level orgs, API
and MCP tools (`facts_about(subject)` etc. belong to the knowledge-layer work).

## Keys

- Local: `SAM_API_KEY=...` in `~/.config/yokel/sam.env`.
- Cloud: GitHub secret `SAM_API_KEY` → `cloud-deploy.yml` → Alchemy → the poller container. Unset = the
  SAM pass skips.
