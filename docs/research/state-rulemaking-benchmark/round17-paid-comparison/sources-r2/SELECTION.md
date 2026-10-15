# R17 source selection (second retrieval run, sources-r2)

The first run (`../sources/`, frozen; READY.json sha256 `7e44194f79a8da8c317e6cacd792cf87ea3dc65d492b3437903993a6da7228dd`) failed every fetch with curl exit 6 (DNS). That failure was environmental (sandbox with no network), not a property of the candidates.

This run retrieved all six official URLs, each with HTTP 200 on attempt 1 (curl exit 0). Extraction used a byte-identical copy of `round14-semantic-contract/source/extract_source.py`. The keyword screen used a byte-identical copy of `../sources/screen.py`. Gates: text ≤ 6,500 chars; keyword pass; guarded bytes ≤ 32,000 for full and opaque (the wire.py guard itself is 40,000); `build()` does not raise for either profile. Per-candidate numbers are in SCREEN.json.

| ID | chars | keyword (exc/total) | guarded full/opaque | build | pass |
|---|---|---|---|---|---|
| 26-19-039 | 4904 | pass (6/12) | 20650/20835 | ok | yes |
| 26-19-041 | 5884 | pass (9/14) | 21944/22129 | ok | yes |
| 26-19-106 | 4174 | pass (5/9) | 20376/20561 | ok | yes |
| 26-19-116 | 3272 | pass (4/6) | 21145/21330 | ok | yes |
| 26-19-123 | 6280 | pass (6/10) | 23041/23226 | ok | yes |
| 26-19-135 | 6233 | pass (2/7) | 22072/22257 | ok | yes |

**Selected (first three by ascending ID passing all screens): 26-19-039, 26-19-041, 26-19-106.** 26-19-116, -123 and -135 also passed and are unselected reserves. No thresholds were loosened and no source was trimmed. No text was read or screened by a human or model.
