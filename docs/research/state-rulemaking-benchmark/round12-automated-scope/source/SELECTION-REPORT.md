# Washington State Register Issue 26-19 selection report

The official register page stated publication was current through September 23, 2026 / Issue 26-19 as of the original browser retrieval. The official issue index lists filing IDs, HTML links, and types. The frozen frame contains 28 unique current-issue `PROP` IDs, deduplicated from agency cross-listings and sorted ascending by WSR ID. The index labels `26-17-052` as a holdover from Issue 26-17; it is excluded.

All 28 unique filings opened as proposed notices with participation text. Nine have full readable text at or below the prospective 8,000-character ceiling; 19 exceed it. Every ID, URL, size, and reason is recorded in `FRAME.json`. Exact identifier and URL search for `26-19-016` returned no matches in existing benchmark artifacts. Selection is the first eligible unused ID by stable ID order, without screening by subject, defects, or complexity.

## Official references

- [Washington State Register main page](https://leg.wa.gov/state-laws-and-rules/washington-state-register/)
- [Official Issue 26-19 index](https://lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19.htm)
- [Selected official filing 26-19-016](https://lawfilesext.leg.wa.gov/law/wsr/2026/19/26-19-016.htm)

## Archive and extraction

`original.htm` is the unchanged 6,693-byte official HTML response downloaded by the primary task with curl and no credentials. `extract_source.py` deterministically derives `parsed-body.txt` and `anchors.json` using Python's standard-library `HTMLParser`. `COMPARISON.json` records full character/token comparison against the preserved browser text. The token sequences match; only whitespace/layout differs. The earlier visible-text HTML wrapper is retained as `26-19-016.html` and identified in `READY.initial.json`; `original.htm` is authoritative.

Source wording with apparent discrepancies remains verbatim: the comment window is August 7 to October 20, the address shows `98504 [98501]`, and the preproposal reference shows `26-15-[0]21`. No hidden text was resolved, and no gold labels, candidate annotations, or rule analysis were added.
