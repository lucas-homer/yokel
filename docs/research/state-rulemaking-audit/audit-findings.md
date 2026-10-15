# Audit of the July state rulemaking research

Checked September 30, 2026 UTC. This appendix distinguishes historical assertions, fresh observations, and recommendations. The baseline is [research commit ae8eb9c](https://github.com/lucas-homer/yokel/tree/ae8eb9c98e3990775e08bc3d3fea978da703d3d5/docs/research/state-rulemaking). Conclusions apply to the inspected scope; absence in this audit is not proof of nationwide absence.

## Claim ledger

| Prior assertion | Assessment | Evidence and consequence |
|---|---|---|
| No state has a documented public notice API; expansion is a scraping/email product rather than an API-integration product. | The universal documentation claim remains unproven; the architectural conclusion is too categorical. The old report already acknowledged several undocumented endpoints. | Connecticut adds a working JSON route found in the page implementation, returning five open-comment records. This does not refute the narrower documented-API claim, but does demonstrate an additional structured collection route. [Endpoint](https://eregulations.ct.gov/eRegsPortal/Browse/getOpenCommentPeriods). |
| Roughly 90% have a scrapeable central point. | Useful hypothesis; nationwide completeness and scrapeability not measured. | An index can omit agencies/processes, require rendering, list final rules only, or lose old items. VA expressly focuses on executive agencies; HI's page is a directory. [VA](https://townhall.virginia.gov/), [HI](https://ltgov.hawaii.gov/the-office/administrative-rules/proposed-changes/). |
| Seventeen jurisdictions are cheap wins; only GA and HI are structurally hard. | Not a delivery estimate. | Initial successes do not measure semantic accuracy, repair cost, or completeness. GA EPD is structurally useful at agency scope, while CT needed additional rendering to expose rows. [GA EPD](https://epd.georgia.gov/public-announcements-0/proposed-rules), [CT](https://eregulations.ct.gov/eRegsPortal/Browse/OpenForComment). |
| NJ OAL's free PDFs are the recommended primary source for statewide Register notices. | Unsupported as a statewide collection strategy. The old report did flag completeness as unproven, but still recommended anchoring on it. | The cited page has empty current tables; its archive primarily lists OAL procedure rules and some broader historical notices. Category headings do not prove statewide coverage. A separate page describes the statewide database. [Archive](https://www.nj.gov/oal/rules/proposals/archives.shtml), [portal description](https://www.nj.gov/oal/rules/portal/). |
| NJ belongs in a combined paywalled-or-vendor-locked category. | Split these axes. The old deep dive correctly acknowledged free vendor-hosted access; the combined aggregate category obscures that distinction. | OAL says LexisNexis provides free Register access. Automated use, redistribution rights, and practical interface reliability were not established. [Official access](https://www.nj.gov/oal/rules/accessp/). |
| MA's notice stream is accessible without buying the full Register. | Supported for the inspected public page. Completeness remains open. | Current notices include explicit dates/times and links to documents. No paid-issue comparison was made. [Public notices](https://www.sec.state.ma.us/divisions/pubs-regs/public-hearings.htm). |
| AR bulk-download contents are unknown. | The advertised scope is now verified; actual delivery is untested. | Official page lists notices, proposed, emergency, and final rules, historical and monthly files, and charges. It is not evidence of a timely active-comment feed. [Offering](https://www.sos.arkansas.gov/rules-regulations/bulk-data-download). |
| NE has stable legacy sequential proposal-document URLs. | Unsafe to carry forward unchanged. | The sampled legacy PDF URL redirected to the new rules homepage and returned HTML with HTTP 200. The new docket exposed only a partial table in this retrieval. This proves a failed historical route, not that every old URL fails. [Legacy sample](https://www.nebraska.gov/nesos/rules-and-regs/regtrack/proposals/0000000000001667.pdf), [new docket](https://rules.nebraska.gov/docket). |
| Utah's RSS directory is a dependable feed entry point. | Stale URL; a different feed remains useful. | /rssfeeds/ resolved to the homepage. /rulesnews/feed/ returned dated bulletin announcements mixed with general news. Treat it as an issue-discovery trigger, not a structured per-notice deadline feed. [News feed](https://rules.utah.gov/rulesnews/feed/). |
| CA's summary says no index; the deep dive says no structured index while documenting monthly HTML contents. | The summary understates usable metadata; the detailed research was more qualified. | The monthly HTML contents contain notice IDs, types, corrections, decisions, and links to issues. They help enumeration even without a search API or database-style index. Details still require notice documents. [September index](https://oal.ca.gov/september-2026-california-regulatory-notice-registers/). |
| OAL, NASS, and other state sites categorically block automation. | Not established; some earlier caveats were appropriate. | Firecrawl retrieved OAL and NASS successfully. Other failures differ by client/route. Network failures cannot establish a universal site policy. [OAL](https://oal.ca.gov/publications/notice_register/), [NASS](https://administrativerules.org/). |
| Search-visible extraction or mojibake establishes a PDF's text/OCR characteristics. | The narrow text-layer observation is useful; stronger format and quality inferences are unsafe. | The MS sample is a scanned page with a pre-existing, imperfect text layer. Search-visible text does not prove a clean original, and mojibake alone does not prove scanning. Native extraction and visual inspection of the retained PDF distinguish these properties. [Sample](https://www.sos.ms.gov/adminsearch/ACProposed/00027305a.pdf). |
| Existing ParticipationWindow/identity/confidence semantics transfer unchanged. | Conceptual architecture transfers; implementation does not. | Current source enum, IDs, FR/Regs fields, and Eastern date assumptions are federal. State proceedings need multiple windows and more temporal precision states. [Contract](../../../packages/contracts/src/index.ts), [date handling](../../../apps/docketclock/src/reconcile/eastern-date.ts). |
| A few hundred notices weekly describes full national volume. | Unsupported estimate. | No consistent national denominator or longitudinal count was provided. Count notices, unique proceedings, events, document versions, and windows separately. Vendor marketing counts describe different scopes. |
| Three refutation votes or three mirrors establish verified operational feasibility. | Insufficient method. | Multiple readings of one source are not independent evidence. They cannot test pagination, real access, amendments, or corpus completeness. Retain the original claim ledger but require primary-source scope checks and operational trials. |
| Open States covers legislation rather than administrative rulemaking; no open equivalent exists. | The Open States scope distinction is supported; the universal absence claim remains unproven. | Its API describes legislative people/bills/events. This finding does not prove no other open administrative-rule project exists. [API](https://docs.openstates.org/api-v3/). |

The original documents also retain some stale first-pass descriptions alongside later revised ratings: the revised aggregate tiers, adapter counts, and per-state prose do not consistently agree. Treat individual sources as leads and version each new assessment rather than copying those national totals into a roadmap.

## Fresh source observations by jurisdiction

These are observations from a bounded session, not production readiness certifications. Source IDs match [sources.json](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-audit/sources.json).

| State | What was retrieved | Collection assessment and unresolved issue |
|---|---|---|
| AL | April monthly PDF via a /api/aam/ route; first three pages only. | Verified document endpoint. It is not a normalized JSON notice API; notice-level extraction and current issue discovery need testing. |
| AK | General portal and one filed-rule notice with effective date and revision history. | RSS/email subscription features documented on the portal. Categories contain different event types; generic form controls are hazardous extraction noise. Feed payload and email delivery were not tested. |
| AR | Official bulk-download description. | Advertised scope includes proposals and notices; paid access and current delivered files untested. Use monthly files for backfill/reconciliation only if cadence is confirmed. |
| CA | Register explanation, annual/monthly indexes, September contents. | HTML metadata plus issue PDFs are viable leads. Corrections and decisions must be classified. Some index IDs are incomplete. No full issue was parsed in this audit. |
| CT | Initially incomplete listings, rendered five-row listing, working JSON route, rendered proceeding history. | Strong structured candidate, with no proven support contract. One endpoint timestamp was checked against detail display; original notice/legal interpretation not fully reconciled. |
| GA | EPD lifecycle table and central filed-rule site. | EPD is a bounded agency candidate; the central publisher also advertises reseller XML for filed rules. Neither establishes statewide prospective coverage. |
| HI | Central department directory. | Requires following agency links and separately testing publication completeness. No newspaper source was newly tested here. |
| IA | Active notice portal with ARC identifiers, agency names, publication dates, and notice types. | Good listing candidate. Pagination, attachments, deadline extraction, and agreement with the Bulletin remain untested. |
| MA | Current free notice listing and one attached hearing PDF. | Explicit dates/times recovered. Attached document has potentially ambiguous zone wording. Direct PDF visual verification failed through this client path. |
| MS | Administrative-code search landing and one historical proposal form. | Landing is code search, not proof of a proposal feed. Sample PDF was successfully downloaded and visually checked; discovering all current notices remains unresolved. |
| NE | New homepage/docket and failed legacy document route. | Migration invalidates sampled old assumptions. Partial rendered table must not be treated as complete enumeration. |
| NJ | OAL-specific notices/archive, access description, statewide-portal description; target connector failure. | Distinguish agency scope, statewide database, and free vendor viewer. Dynamics returned connector INVALID_ARGUMENT; its actual availability is unknown. |
| NV | Dated Daily Updates index with document-type legend. | Useful rolling discovery; only four weeks retained in this index. Cumulative backfill and joins to hearing notices need testing. |
| OR | Bulletin archive index with monthly links. | Enumerable index recovered, but links contain session path parameters. Session-free detail access was not newly tested. |
| SD | Agency-based proposal portal with register document link. | Portal states proposals are archived 20 days after filing with SOS. Archive collection is required; linked PDF/API semantics not tested. |
| TN | Paginated hearings table and one attached filing PDF. | Table includes dates and source IDs. Hearing timing, pre-hearing comments, accommodations, and filing dates must be separated. Direct visual PDF verification failed through this client path. |
| UT | Old feed URL redirect and working news RSS. | Feed includes bulletin announcements and unrelated posts. Validate feed item classification and issue enumeration independently. |
| VA | Portal, 53-forum listing, one NOIRA stage and action relationship. | Rich stage/window structure. Site describes executive-branch focus. Visible counts are point-in-time observations, not stable capacity measurements. |
| WA | One incorrect route, archive, issue 26-18, one withdrawal notice. | Working issue route is strong, but category labels and agency rows cannot directly become normalized events. Proposal section has 14 rows/13 distinct IDs. |

## Extraction experiment and limitations

Five expectations were recorded before the extraction calls, following inspection of source text. A single shared prompt requested specific date roles, evidence, null unknowns, preservation of time-zone wording, and abstention from calculating relative deadlines.

The connector rejected every attempt to send an explicit JSON Schema before execution. One supported prompt-only JSON request per case then ran. The machine-readable experiment file retains the requested schema, common prompt, outputs, and manual assessment. The results concern that connector path and prompt; they do not measure a fully configured API integration.

The most serious semantic failures were:

1. Washington: an announced withdrawal's filing date was labeled an effective date.
2. Mississippi: a hearing-request period was assigned to the comment deadline field.
3. Tennessee: an accommodation-request period was assigned as comment evidence, alongside an unsupported effective date.

Massachusetts returned the relevant stated dates but invented a source identifier and returned a string for the warnings array. Alaska avoided an invented closing date but returned strings containing “null.” Other outputs also used empty strings and N/A for unknowns. Strict application validation is therefore necessary even before evaluating factual accuracy.

Manual review identified these errors after inspecting the results. This is an exploratory diagnostic exercise with five selected cases and no independent human labeling panel. It supplies regression candidates, not an unbiased error rate.

### Mississippi visual check

The retained original is [the official 00027305a PDF](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-audit/fixtures/ms-00027305a.pdf), SHA-256 ac95c240653690261eb7a6fef83bd80a04310cf49c15c37256569bbc70315955. It is one page, with one image and a 3,123-character native text extraction. The image shows an amendment marked, no oral proceeding scheduled, and an official December 27, 2023 filing stamp. The native text layer omitted important stamp information and garbled some words; Firecrawl made the text more legible. Its later JSON extraction still selected the wrong deadline condition.

This demonstrates why a text layer's existence is not an OCR quality assessment, and why readable text is not a correct normalized fact.

## Reproducibility and retention

- The four historical documents remain referenced by immutable Git commit.
- sources.json records requested/final URLs, response status, observed content type, transformed-content hashes, selected evidence, and limitations for all 50 acquisition attempts.
- The machine-readable experiment records the initial schema rejection and the actual prompt-only outputs.
- Full Firecrawl response bodies were saved during research under /private/tmp/docketclock-state-audit/.firecrawl. That temporary directory is a working cache, not the durable evidence store.
- Seven transformed source snapshots, semantic sample observations, extraction outputs, four worked normalization examples, and the visually inspected original PDF are retained with this report. Snapshot hashes match their sources.json entries. Transformed Markdown is not an original-byte archive; these are research fixtures, not production observations.
- Retrieval settings requested maxAge 0. This is a freshness request; the audit did not independently verify Firecrawl's complete internal cache path.
- The 51-jurisdiction inventory labels all inherited fields as July research and names the 32 entries that were not revalidated.

No email signup, purchase, vendor outreach, background monitor, or operational guarantee resulted from this research.
