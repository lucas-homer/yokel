# 0010. Preserve reviewed verdicts across proven Regulations.gov metadata refreshes

- Status: Accepted
- Date: 2026-09-23

## Context

Seven reviewed windows resurfaced because `reconcile-v2` invalidated a verdict whenever any source
observation had a later fetch time. Two Regulations.gov payloads changed only `modifyDate`; five
added only the API's top-level `links.self`. None changed the evidence supporting the verdict.
Repeating the same verdict would conceal the recurring cause and add redundant audit entries.

## Decision

`reconcile-v2.1` retains the existing invalidation rule with one narrowly defined exception:

- Find the latest Regulations.gov observation at or before the latest verdict's timestamp (the verdict must parse),
  using the reconciler's existing deterministic timestamp/ID ordering. Its exact payload hash must
  appear in that verdict's `reviewed_payload_hashes`.
- Every source observation newer than the verdict must be a Regulations.gov observation matching
  that baseline. Compare the entire raw payload and observation envelope, excluding only ingestion
  ID, fetch time, payload hash, `data.attributes.modifyDate`, and top-level `links.self`. Ignore
  these metadata fields only when their values are strings or null/absent. An empty top-level
  `links` wrapper is equivalent to no wrapper.
- All other fields remain evidence, including unknown fields, document identities, parser version,
  notice flags, attachments, dates, submission settings, and non-self links. Missing baseline/hash
  evidence, newer Federal Register/GovInfo data, or any other changed field invalidates the verdict.
- Check every intervening observation, not just the latest. A substantive change followed by a
  reversion must not silently revive a verdict. A subsequent human review can establish a new one.
- Preserve the existing equal-timestamp policy and behavior when no newer source observations exist.
  This supersedes the strictly temporal freshness decision in `plans/review-resolve.md`.

The comparison is a pure reconciler decision. Do not normalize stored payloads, alter their hashes,
change ingestion deduplication, rewrite verdicts, or add a contract field. Original reviewed hashes,
notes, operators, and raw observations remain the audit trail.

## Consequences

- Known metadata refreshes remain append-only observations but no longer send unchanged reviewed
  conflicts back to the queue. Real and unrecognized changes continue to request review.
- This intentionally does not generalize equivalence to other sources or compare only extracted
  deadline fields; that would risk overlooking changed instructions or supporting evidence.
- Deployment follows git → Argo CD. The existing version-based `rederive-stale-windows.ts` sweep
  applies the rule to existing projections; deployment alone need not cause a fresh observation.
  Normal persistence retires resolved conflicts and maintains deadline change history.
- Verification covers both metadata forms, substantive fields and envelope changes, missing hashes,
  intervening changes, all verdict kinds, deterministic ordering, and the real queue/persistence path.
  Read-only replay of all seven full live histories restores their original pinned dates without
  adding a verdict. The replay does not itself change the live queue.
