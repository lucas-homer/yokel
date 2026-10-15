# Notice-level comparison

Every source link opens the exact retained parser-input PDF. “Evidence gap” includes missing or ambiguous critical evidence and insufficient scope for an absence claim. A07’s source conflict prevents a strict pass under any arm. A01/A02 Llama outputs were recovered from their existing successful dashboard jobs after connector timeouts; the original operational records remain intact. All 40 Llama outputs are now complete: four recovered connector jobs, eight dashboard jobs, and 28 REST jobs. “Pass” refers to the frozen critical-evidence gate, not perfect transcription.

| Unit/source | State | Pages | Native text | Firecrawl | Llama Agentic | Llama Plus |
| --- | --- | ---: | --- | --- | --- | --- |
| [A01](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A01) | MS | 1 | Empty scan text | Evidence gap | Pass, recovered | Evidence gap, recovered |
| [A02](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A02) | MS | 1 | Empty scan text | Evidence gap | Pass, recovered* | Pass, recovered |
| [A03](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A03) | MS | 1 | Empty scan text | Evidence gap | Title transcription error | Title error + omissions |
| [A04](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A04) | WA | 1 | Evidence gap | Evidence gap | Pass | Pass |
| [A05](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A05) | WA | 1 | Pass | Pass | Pass | Pass |
| [A06](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A06) | CA | 2 | Pass | Pass | Pass | Pass |
| [A07](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A07) | CA | 2 | Source conflict | Source conflict | Source conflict | Source conflict |
| [A08](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A08) | CA | 4 | Pass | Pass | Pass | Altered temporal condition |
| [A09](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A09) | NY | 1 | Pass | Evidence gap | Pass | Pass |
| [A10](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-a/A10) | NY | 1 | Pass | Pass | Pass | Pass |
| [B01](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B01) | MA | 2 | Pass | Pass | Pass | Pass |
| [B02](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B02) | MA | 3 | Pass | Pass | Pass | Pass |
| [B03](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B03) | NC | 2 | Pass | Pass | Pass | Pass |
| [B04](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B04) | NC | 2 | Evidence gap | Evidence gap | Pass | Pass |
| [B05](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B05) | TX | 3 | Pass | Pass | Pass | Pass |
| [B06](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B06) | TX | 2 | Pass | Evidence gap | Pass | Pass |
| [B07](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B07) | TX | 2 | Pass | Evidence gap | Pass | Pass |
| [B08](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B08) | CO | 1 | Pass | Pass | Pass | Pass |
| [B09](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B09) | CO | 1 | Pass | Pass | Pass | Pass |
| [B10](https://github.com/lucas-homer/yokel/tree/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/source-b/B10) | CO | 1 | Pass | Evidence gap | Pass | Pass |

*A02 Agentic preserves the scored critical fields but misreads a handwritten number, `28576` as `28574`; its semantic role is not established by the frozen reference. See the [recovery findings](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/llama-recovery-2026-10-05/review/findings.json).

The 20 units come from 16 original PDFs. Full original documents, unchanged-page maps and allocation/template metadata are retained in the [frozen corpus manifest](https://github.com/lucas-homer/yokel/blob/research/state-rulemaking-evidence-2026-10/docs/research/state-rulemaking-benchmark/artifacts/corpus-freeze.json).

## Selected notice titles

- **A01** — 2026 Diversified Agriculture - Plants Core final filing
- **A02** — FY2026 Water Pollution Control Revolving Loan Fund Intended Use Plan proposed filing
- **A03** — Title 35 Part VIII table of contents final filing
- **A04** — Withdrawal of CR-105 WSR 25-03-112
- **A05** — WSR 26-16-026A Withdrawal of Proposed Rules
- **A06** — Invasive Mussels Revision 15-day continuation
- **A07** — ELT Second Notice of Modifications and Addition of Documents
- **A08** — Rescinding Select Commercial Groundfish Management Measures: proposed readoption
- **A09** — SGC-39-26-00023-P Licensing of Owners in Thoroughbred Racing
- **A10** — PSC-39-26-00027-P Issuance of Securities and Other Forms of Indebtedness
- **B01** — Hospital Assessment emergency filing
- **B02** — Social Workers licensure emergency filing
- **B03** — Exempt sales plan notice
- **B04** — Waiver rule amendment notice
- **B05** — Educator certification passing standards proposal
- **B06** — Broker Responsibility Advisory Committee proposal
- **B07** — Optometry License Designation proposal
- **B08** — Education terminated rulemaking 2026-00317
- **B09** — Treasury terminated rulemaking 2026-00275
- **B10** — Retail marijuana tax permanent adoption notice
