# Washington HTML lane

Output: 10 deterministic candidate observations across WSR 26-18-058 and 26-18-032. Offline `python3 normalize.py` writes observations from saved HTML only. `python3 finish.py` rebuilds the manifest, enumerates the index and validates 11 exact quotes, model quotes, count checks and rejection of a generic unsupported template.

Acquisition: three public curl GETs succeeded after sandbox DNS failure and authorized escalation. Original HTML bytes are retained. Firecrawl maxAge=0 markdown succeeded for both notices, costing 1 credit each; one prompt-only JSON trial on the withdrawal cost 5 credits. No explicit schema trial was made. Manifest timestamps use curl download mtimes or Firecrawl response persistence upper bounds; they are not independently verified server timestamps.

Parsing: header field markers and labeled notice text support deterministic extraction. The proposal agency spans two divs, caught and corrected during replay. Body amended-rule text contains historical effective dates; the parser never searches it for current effectivity. The October 9 comment close remains a date without invented time. The October 15 hearing and both filing times remain local datetimes with unresolved zones. Firecrawl's America/New_York metadata is not Washington source evidence.

Interpretation: issue category PROP includes the partial withdrawal. Its target is WSR 26-15-113 and scope is only the CR-102 portion. Future CR-102/comment/hearing language supplies no new date. The index has 14 PROP rows / 13 unique IDs, with 26-18-066 cross-listed under agency names. Enumeration is useful discovery, not active-window classification or statewide completeness.

Firecrawl earned limited use here: clean text saves HTML cleanup for inspection, but direct HTML already contains readable field markers. Prompt-only extraction recognized the partial scope without fabricating dates, yet returned literal "null" strings in four absent fields. Raw output remains separate, uncorrected, and contributes no observations. All four model evidence quotes exactly match saved deterministic text. There is no held-out accuracy measurement.

Before unattended use: broaden fixtures, test variants/withdrawal phrasing, validate source-native identity and deduplication across issues, define timezone/receipt conventions from authoritative sources, track replacements, and separate acquisition/shape/semantic failure handling. These selected cases establish neither production readiness nor coverage.

Shared spec requests: intended adoption has no predicate; do not relabel it effective_date. Issue category should remain separate metadata from body event_type. No SPEC changes made.

Shared validator: passed (10 artifacts, 10 observations, 11 exact quotes); saved in shared-validation.json. source_lineage is a nonempty identifier string, following the primary clarification. The first run rejected arrays; no evidence or observations were weakened.

Integration clarification: event_type values are canonical proposal and withdrawal. Original uppercase WSR labels remain in exact evidence. Regenerated observations and validations retain 10 observations / 11 quotes; shared validator passes. Original source artifacts and pre-extraction expectations remain unchanged.
