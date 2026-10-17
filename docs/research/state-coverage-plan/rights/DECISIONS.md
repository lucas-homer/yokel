# Rights decisions (reviewer: owner, 2026-10-15)

These decisions settle the reviewer questions in [`SUMMARY.md`](SUMMARY.md). They govern all Phase 1
collection. Children must follow them; anything they don't cover is held until the reviewer decides.

## Decided

1. **Third-party processing: yes, public notices only.** Openly published state notices may be sent
   to LlamaParse and to LLM APIs for extraction. Nothing behind a login, paywall or subscription.
2. **Request rate: 1 request per 5 seconds** wherever no rate is published. One request at a time,
   identifying user agent, stop on any 403 or 429 and report.
3. **Public display (eventual product): link plus a short factual excerpt.** The excerpt is the
   quoted sentence that sets the deadline or hearing. No full copies of documents. Originals and
   their hashes are kept internally only.
4. **MA: dropped from the Phase 1 census for now.** A permission request to the Secretary of the
   Commonwealth goes out (draft in [`outreach/MA.md`](outreach/MA.md)). TN carries the hard-state bar
   in the meantime. MA re-enters only with written permission or another lawful access route.

## Standing rule

**Never work around bot protection.** No headless browsers, user-agent spoofing, proxies or retries
designed to get past a block. A refused request is a finding to report, not an obstacle. (During
the rights check a headless browser loaded a few MA policy pages after an initial refusal; that is
not to be repeated.)

## Decided, round 2 (owner, 2026-10-15)

Prompted by the universe scoping, which found every process single-lineage under the defaults below.

5. **Independent cross-checks allowed.** Agency rule-making pages may be read as independent-lineage
   cross-checks (read-only, 1 request / 5 s, originals internal only). Check each agency's own terms
   first and skip any that restrict reuse, recording the skip; WA Ecology stays pointer-only.
6. **Statute and code lookups allowed.** Read-only, non-retained lookups on `app.leg.wa.gov` and
   `law.lis.virginia.gov`, to verify cited sections and enumerate agency rosters.
7. **CT JSON routes allowed.** The JSON routes CT's own portal pages call (open periods, proposal
   history and notes, hearing details) may be read at 1 request / 5 s. The CT inquiry still goes out;
   stop if CT objects.
8. **TN:** the owner sends the TN and MA outreach now. TN's 403 is not to be worked around. ADR 0013
   is amended to allow research on one backup hard candidate.
9. **Review budget:** 4 hours per state for audit plus adjudication, 6 hours for VA and CT, about
   20 hours in total.

`surfaces.json` version `2026-10-15.2` carries these changes. VA Town Hall `/L/` stays held, since
that hold comes from its robots.txt, not from a default.

## Decided, round 3 (owner, 2026-10-15)

10. **Mississippi is the backup hard candidate** (ADR 0013 Amendment 1). Collection may use the SOS
    administrative search page and the search-service calls its own script makes, at 1 request / 5 s.
    Stop on any Cloudflare challenge, 403 or 429. A short note on our rate and user agent goes to
    SOS (`outreach/MS.md`).
11. **MS cross-check:** sample about 5 MS agencies during scoping for an independent source; if none
    qualifies, MS processes are single-lineage and completeness is "not established".
12. **MS credits:** up to about 1,430 LlamaParse credits from the 2,000 reserve, covering proposal,
    final and withdrawal forms.
13. **Scope:** the owner signed `census/SCOPE-DECISIONS.md` as proposed.

`surfaces.json` version `2026-10-15.3` adds the MS records.

## Decided, round 4 (owner, 2026-10-15)

14. **MS review budget:** 6 hours, with every decisive visual mark human-reviewed. Total review across
    WA, VA, CT, MS and TN is about 26 hours.
15. **MS statute lookups allowed:** read-only, non-retained lookups of the Mississippi Code (e.g.
    § 25-43-3.104) on the official free-access host. Check that host's terms first.
16. **MS scope signed** as proposed in `census/SCOPE-DECISIONS.md`, including the primary's credit
    reallocation: MS gets full parsing coverage (about 3,310 credits plus a 150-credit retry hold),
    funded from WA, VA and CT's unused allocations. The Phase 1 cap stays 12,000.

## Decided, round 5 (owner, 2026-10-15)

17. **Step-3 sign-off:** every named gap and single-lineage process row is signed as a class. The
    MS calls and the WA holdover rule are decided explicitly. See
    [`../census/SIGNOFF-2026-10-15.md`](../census/SIGNOFF-2026-10-15.md).
18. **WA outreach:** the owner sends [`outreach/WA.md`](outreach/WA.md) to the Code Reviser about
    the 16 unlisted filing numbers.

## Decided, round 6 (owner, 2026-10-16)

19. **CT review budget raised to about 9 hours (540–600 minutes)**, keeping CT's full signed scope.
    The mandatory step-5 work is 355 minutes, including 110 date and role checks, and the reduced
    audit adds 184 (`census/CT/reconcile/OWNER-SHEET.md`, Part 3). The total across states is
    reset once WA, VA and MS have their estimates; it is expected to exceed item 14's 26 hours.

## Correction (primary, 2026-10-15)

`surfaces.json` version `2026-10-15.2` wrongly set retention to `not_authorized` on the newly allowed
cross-check and CT JSON surfaces, a copying error. Items 5 and 7 intend internal retention of
originals, with nothing republished. Version `2026-10-15.4` sets `internal_originals` on `ct-json`,
`ct-policy-reference` and the WA, VA, MS and TN agency surfaces. It also narrows `ct-json` so that
`getDocument` (PDFs) belongs only to `ct-rendered`.

## Correction (primary, 2026-10-16): the census uses no LlamaParse credits

The credit allocations in items 12 and 16, and the re-tiering question in `census/MS/ACQUISITION.md`
(open question 8), assumed the census would parse forms through LlamaParse. It doesn't. Both blind
passes read the originals directly and must view rendered pages for every scan (PROTOCOL step 4), so
parser output can't stand in for that inspection. Phase 1 census spend is 0 credits in every state.
The allocations stay unspent under the 12,000 cap. Any later parsing benchmark needs its own
decision.

## Primary defaults for the remaining questions (superseded in part by round 2)

- **WA:** collect from the State Register only. Agency pages (for example Ecology, whose terms bar
  use "in a political campaign or lobbying effort") are used only to find links back to the
  Register, not as a collected source.
- **CT:** collect the rendered eRegulations pages. The undocumented `getOpenCommentPeriods` JSON
  route stays on hold until CT answers the inquiry in [`outreach/CT.md`](outreach/CT.md).
- **VA:** collect from the Virginia Register and its RSS feed. Treat Town Hall's `Disallow: /L./` as
  covering `/L/` and don't collect those listing pages unless the inquiry in
  [`outreach/VA.md`](outreach/VA.md) says otherwise.
- **TN:** watched runs only, at the rate above. No scheduled polling until the Division of
  Publications answers [`outreach/TN.md`](outreach/TN.md).
