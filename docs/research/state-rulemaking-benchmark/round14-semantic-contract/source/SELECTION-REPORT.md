# Round 14 prospective source selection

Selection is frozen in `SELECTION.json`, which predates retrieval of the chosen notice. The selection universe is the frozen Washington State Register Issue 26-19 `PROP` frame from Round 12. Candidates are ordered by stable WSR ID; notices above the 8,000-character readable-text ceiling and previously used notices are excluded. The first remaining candidate is **26-19-023**.

The only previously used notice in this frame is 26-19-016 (Rounds 12 and 13). Exact ID/URL searches across prior benchmark artifacts found no other frame candidates already used. The selected notice was not screened for semantic defects, topic, or complexity before or during selection.

The official source URL returned HTTP 200 and `text/html` through an unauthenticated, 30-second-bounded `curl` request. `original.htm` preserves the exact downloaded response bytes. `extract_source.py` derives the full 7,208-character body text and 12-link inventory with Python's standard-library `HTMLParser`; no wrapper was used. Plain text does not retain markup distinctions that may carry meaning; see `COMPARISON.json` and `original.htm`.

`READY.json` contains frame and artifact hashes, retrieval metadata, and extraction checks. No protocol, gold/reference labels, provider outputs, or semantic analysis are included in this source bundle.
