# Official API/docs/source semantics for docket deadline tracking

**Research value: high** -- Official Regulations.gov/GSA docs and OpenAPI give usable field definitions and API constraints, while FederalRegister.gov is useful for publication/dates text but has documented gaps and observable date/status mismatches.

## What an MVP can rely on

1. **Use Regulations.gov document detail as the primary machine source for commentability.** The official GSA page says Regulations.gov provides GET APIs for `documents`, `comments`, and `dockets`; `/v4/documents/{documentId}` returns detail, and a document is one of `Notice`, `Rule`, `Proposed Rule`, `Supporting & Related Material`, or `Other`.[^gsa-api] The OpenAPI defines:
   - `commentStartDate`: date that begins the period when public comments may be submitted.
   - `commentEndDate`: date that closes the period when public comments may be submitted.
   - `openForComment`: boolean conveying whether the document is open for comment.
   - `allowLateComments`: whether the owning agency will accept comments after the due date.
   - `withdrawn`: boolean conveying whether the document is withdrawn.[^reg-openapi]

2. **Track deadlines at the document level, not just docket level.** Official docs define a docket as an organizational folder containing multiple documents; comments are retrieved for each document by filtering comments with the document's internal `objectId` as `filter[commentOnId]`.[^gsa-api] A docket can contain several documents, and only one or some may be commentable. MVP model should be `docket -> documents -> comments`, with a per-document deadline.

3. **Use `commentEndDate` plus `openForComment`/`withinCommentPeriod` together.** OpenAPI says `filter[withinCommentPeriod]=true` filters documents open for comment and explicitly says `false` is not accepted; search can sort/filter by `commentEndDate`, `postedDate`, `lastModifiedDate`, `documentId`, `title`.[^reg-openapi] MVP should use `commentEndDate` for displayed deadline, but use `openForComment` as current status because agencies can withdraw/close/change records.

4. **Expect ISO datetimes and timezone edge cases.** Regulations.gov OpenAPI describes `commentEndDate` as ISO 8601 with offset (example `...Z`). Federal Register API exposes a date-only `comments_close_on`. In a sampled official FR record, `comments_close_on` was `2019-03-14` while embedded Regulations.gov `comment_end_date` was `2019-03-15`; the text said comments due March 14.[^fr-2018] This likely reflects end-of-day/timezone normalization. MVP should display the agency/legal text when available and avoid silently converting date-only FR deadlines into midnight UTC.

5. **Use comments API for counts/content, but not submitter metadata guarantees.** GSA's data-limitations section lists comment fields always available: `agencyId`, `comment`, `commentOnId`, `docketId`, `documentId`, `documentType`, `postedDate`, `receiveDate`, restriction/withdrawal fields when applicable, `title`, `trackingNbr`, `withdrawn`. Many submitter fields (`firstName`, `lastName`, `organization`, `city`, `state`, `email`, etc.) are agency-configurable and can become public/nonpublic at any time.[^gsa-api]

6. **Pagination is limited to 20 pages x 250 records per query.** OpenAPI caps `page[number]` at 1-20 and `page[size]` at 5-250.[^reg-openapi] GSA documents an official workaround for >5,000 comments: sort by `lastModifiedDate,documentId`, page through the first 5,000, then continue with `filter[lastModifiedDate][ge]=...`, repeating; it warns `lastModifiedDate` is beta and may be removed when a permanent bulk download solution exists.[^gsa-api]

7. **Rate limits: default api.data.gov plus stricter commenting API.** Regulations.gov requires an API key in `X-Api-Key`; `DEMO_KEY` is for exploration only.[^gsa-api] api.data.gov defaults are 1,000 requests/hour per key; DEMO_KEY is 30/hour and 50/day per IP; responses include `X-RateLimit-Limit` and `X-RateLimit-Remaining`; over-limit returns HTTP 429.[^api-data-gov] Regulations.gov additionally says the commenting API is restricted to 50 requests/minute and 500/hour, and GSA may grant GET-key increases case by case.[^gsa-api]

## Ambiguous or risky semantics

- **FederalRegister.gov is not legal notice.** Its reader-aids page says FederalRegister.gov is an unofficial XML rendition; users relying on it for legal research should verify against official Federal Register editions on govinfo.gov.[^fr-unofficial] MVP can use FR API for discovery/enrichment and `dates` text, but should not present it as the legal source of truth.

- **Federal Register API field definitions are incomplete.** In the official GitHub issue tracker, a maintainer said no document defining all API key/value fields was currently available and that fields were intended to be self-explanatory.[^fr-issue] Therefore `comments_close_on`, `correction_of`, `corrections`, `docket_ids`, `regulations_dot_gov_info`, etc. should be treated as useful but under-documented.

- **Corrections are not reliably encoded as API relationships.** Official FR correction examples may have action/title indicating `Final rule; correction` while `correction_of` is `null` and `corrections` is empty.[^fr-correction] MVP should search titles/actions/dates text for correction notices and docket linkage rather than relying only on `correction_of`/`corrections`.

- **Extensions are separate documents and may not update every related record consistently.** An FR extension example has action `Proposed rule; extension of comment period`, `comments_close_on=2025-04-02`, and `dates` text explicitly extending the deadline from March 3 to April 2; however its embedded Regulations.gov document had `comment_end_date=null` and `open_for_comment=false` for the extension notice document itself.[^fr-extension] MVP should interpret extension notices as possible modifiers to the original commentable document, not necessarily as a new commentable target.

- **Withdrawals are separate documents; Regulations.gov `withdrawn` is a document status, not full procedural history.** FR withdrawal examples show action/title `Withdrawal of proposed rule`, `comments_close_on=null`, and docket linkage.[^fr-withdrawal] Regulations.gov `withdrawn=true` means the document is withdrawn; if a separate withdrawal notice exists, it may need docket/RIN/title matching.

- **Public submission status: withdrawn/restricted fields exist, but public availability is agency-mediated.** For comments, `withdrawn`, `reasonWithdrawn`, `restrictReason`, and `restrictReasonType` are official fields when applicable; GSA cautions comment data has limitations and some fields are managed solely by agencies.[^gsa-api]

## Recommended MVP contract

- Store `{source: regulations.gov, documentId, objectId, docketId, documentType, title, postedDate, commentStartDate, commentEndDate, openForComment, allowLateComments, withdrawn, lastModifiedDate}`.
- Display deadline from Regulations.gov `commentEndDate` when present; show FR `comments_close_on`/`dates` text as corroborating/explanatory, not overriding, unless a human rule says otherwise.
- Model comments by `commentOnId = parent document objectId`; never assume all docket comments belong to the first document.
- Flag records for review when: FR and Regulations.gov dates differ; extension/correction/withdrawal terms appear in action/title/dates; `commentEndDate` is null but `openForComment=true`; or `openForComment=false` while future deadline exists.
- For bulk ingestion, page by `lastModifiedDate` with deduplication by `documentId`/`commentId`, but isolate this as a replaceable strategy because GSA labels it beta.

## Sources

[^gsa-api]: GSA Open Technology, “Regulations.gov API,” https://open.gsa.gov/api/regulationsgov/ -- official endpoint overview, docket/comment/document relationship examples, data limitations, rate-limit notes, >5,000 comment paging workaround.
[^reg-openapi]: Regulations.gov OpenAPI v4, https://open.gsa.gov/api/regulationsgov/v4/openapi.yaml -- official schema/parameter definitions for fields, filters, sort, pagination, document/comment/docket types.
[^api-data-gov]: api.data.gov, “API Key Usage / Web Service Rate Limits,” https://api.data.gov/docs/rate-limits/ -- official api.data.gov key-passing methods, default limits, DEMO_KEY limits, headers, 429 behavior.
[^fr-unofficial]: FederalRegister.gov Reader Aids / Developer Resources, https://www.federalregister.gov/reader-aids/developer-resources/federalregister-gov-is-open-source -- notes FederalRegister.gov is an unofficial XML rendition and legal users should verify against official editions.
[^fr-issue]: usnationalarchives/federalregister-api-core issue #9, https://github.com/usnationalarchives/federalregister-api-core/issues/9 -- maintainer states no field-definition document was available for many API fields.
[^fr-2018]: Federal Register API record `2018-27875`, https://www.federalregister.gov/api/v1/documents/2018-27875.json -- example where FR `comments_close_on`/dates text and embedded Regulations.gov date differ by one day.
[^fr-extension]: Federal Register API record `2025-03547`, https://www.federalregister.gov/api/v1/documents/2025-03547.json -- official extension-of-comment-period example.
[^fr-withdrawal]: Federal Register API record `2026-06445`, https://www.federalregister.gov/api/v1/documents/2026-06445.json -- official withdrawal example.
[^fr-correction]: Federal Register API record `2024-03267`, https://www.federalregister.gov/api/v1/documents/2024-03267.json -- official correction example with empty correction relationship fields.
