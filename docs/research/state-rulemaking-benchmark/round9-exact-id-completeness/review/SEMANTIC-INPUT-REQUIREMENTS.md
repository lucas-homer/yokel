# Semantic barrier issue to resolve in final protocol

The initial proposal correctly distinguishes exact IDs from source truth and has useful
minimal pairs. The implementation contract must also define the input that its semantic
aggregator is permitted to consume. Initial fixture expected labels cover target units;
they are not a complete independently adjudicated assessment of every source unit and
candidate claim. A builder should not invent that contract or silently fill missing
entries with matched/supported.

Before approval, specify a bounded evaluation-only audit representation and obligations:

1. Bind the selected source text, full candidate record and frozen source-unit universe by
   canonical hashes/identifiers. Bind the actual reviewed assessment artifact/provenance;
   an arbitrary caller boolean such as reviewed=true is not evidence of independent review.
   This is artifact provenance, not a new authentication infrastructure.
2. Cover exactly every frozen source-unit ID and every assessed candidate claim in the
   declared claim universe; state how candidate claims are enumerated, including nested
   timing/components and operative assertion fields. Reject missing, duplicate, extra,
   stale or malformed mapping entries rather than defaulting them to positive.
3. Each matched mapping identifies operative record field(s) and source evidence; evidence
   strings, coverage rationale or source text alone cannot satisfy a missing assertion.
   Full relationship closure must refer to every required endpoint and its disposition.
4. Explicit unknown/unfinished/unavailable input yields review and semantic unverified
   or unavailable, not complete. A contradictory or unsupported claim also blocks complete
   eligibility even when all source units were found. Structural validity remains separate.
5. Provide one full positive audit object and negative changes for missing/stale audit,
   an unmatched unit, unsupported candidate claim, unresolved required endpoint and missing
   disposition. Use these to test aggregation, not to claim an automated semantic detector.
6. Keep evaluator audit/expectations outside request construction. A request API should take
   source and record explicitly, without accepting a whole fixture object. Poisoned private
   canary values and removed expectations must not alter provider-visible request bytes.

These requirements do not call for an LLM, string-rule semantic engine, new production
record schema or general framework. Manual/independent reviewed source mappings are
legitimate research inputs; their aggregation must not be represented as discovering
truth. The review will evaluate the final author's chosen concrete representation.

No initial-draft approval is issued. The separate keyed-response revision is in progress.
