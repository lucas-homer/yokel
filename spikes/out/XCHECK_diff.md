# XCHECK — live windows vs spicy-regs Parquet (offline differential)

Generated: 2026-09-02T20:46:40.189Z
Windows export: `spikes/data/windows.jsonl` (6308 windows)
Parquet: `https://r2.spicy-regs.dev/documents.parquet` (1997463 documents, freshest modify_date 2026-09-02T18:05:18Z)

A pass is NOT DONE until every disagreement below carries a `triage` value:
`our_bug` (live projection wrong — export a fixture with `export:accuracy-miss`),
`bulk_stale` (mirror lags live), `source_drift` (the sources themselves changed).
Re-runs carry forward filled triage for persisting disagreements (keyed by ocd_id + category —
a finding that changes category re-triages from scratch). In notes, spell a literal pipe `\|`.

## Counts

| category | count | meaning |
| --- | ---: | --- |
| agree | 3244 | same Eastern close date (and no withdrawn signal against us) |
| **date_mismatch** | **30** | joined rows disagree on the Eastern close date — TRIAGE |
| **withdrawn_mismatch** | **2** | mirror says withdrawn, our status doesn't — TRIAGE |
| we_abstain | 16 | our close is null (honest abstention); mirror carries a date |
| parquet_no_close | 1942 | joined, but no mirror row carries a comment_end_date |
| unmatched | 1074 | window not present in the mirror at all |

## Disagreements (32)

| ocd_id | category | ours (Eastern) | parquet (Eastern) | status | confidence | join | parquet docs | derived_at | parquet_modified | triage | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ocd-participation-window/federal/2026-03042 | date_mismatch | 2026-03-19 | 2026-04-20 | closed | low | regs_id | HRSA-2026-0001-0001 | 2026-09-01T21:50:33.559Z | 2026-03-10T21:04:30Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-04-20 agrees with mirror |
| ocd-participation-window/federal/2026-03068 | date_mismatch | 2026-04-20 | 2026-02-27 | closed | low | regs_id | VA-2026-VBA-0067-0001 | 2026-09-01T21:50:33.559Z | 2026-02-28T10:00:16Z | source_drift | live regs.gov now carries NO commentEndDate (mirror kept 2026-02-27); ours is the FR date — regs removed the close |
| ocd-participation-window/federal/2026-03633 | date_mismatch | 2026-04-10 | 2026-05-11 | closed | low | regs_id | EPA-HQ-OLEM-2025-0313-0001 | 2026-09-01T21:50:33.559Z | 2026-05-19T09:00:11Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-11 agrees with mirror |
| ocd-participation-window/federal/2026-03810 | date_mismatch | 2026-03-30 | 2026-02-26 | closed | low | regs_id | CMS-2025-1723-0002 | 2026-09-01T21:50:33.559Z | 2026-02-27T21:08:18Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-02-26 agrees with mirror |
| ocd-participation-window/federal/2026-03927 | date_mismatch | 2026-03-30 | 2026-04-01 | closed | low | regs_id | CNCS-2026-0102-0001 | 2026-09-01T21:50:33.559Z | 2026-03-26T17:12:35Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-04-01 agrees with mirror |
| ocd-participation-window/federal/2026-04106 | date_mismatch | 2026-04-16 | 2026-05-18 | closed | low | regs_id | STB-2026-0463-0001 | 2026-09-01T21:50:33.559Z | 2026-03-02T18:40:50Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-18 agrees with mirror |
| ocd-participation-window/federal/2026-04133 | date_mismatch | 2026-04-01 | 2026-03-02 | closed | low | regs_id | CMS-2025-1789-0002 | 2026-09-01T21:50:33.559Z | 2026-03-02T21:25:49Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-03-02 agrees with mirror |
| ocd-participation-window/federal/2026-04366 | date_mismatch | 2026-04-06 | 2026-05-04 | closed | low | regs_id | EPA-HQ-OLEM-2025-3456-0001 | 2026-09-01T21:50:33.559Z | 2026-08-11T09:00:42Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-04 agrees with mirror |
| ocd-participation-window/federal/2026-04517 | date_mismatch | 2026-05-08 | 2026-05-15 | closed | low | regs_id | BOEM-2025-0042-0001 | 2026-09-01T21:50:33.559Z | 2026-07-16T09:00:29Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set — the July cohort); live regs.gov 2026-09-02 = 2026-05-15 agrees with mirror (docket extended). derived_at is the #106 sweep refresh, last FR observation 2026-06-17 |
| ocd-participation-window/federal/2026-05167 | date_mismatch | 2026-05-01 | 2026-05-15 | closed | low | regs_id | EPA-HQ-OAR-2019-0178-1607 | 2026-09-01T21:50:33.559Z | 2026-05-30T09:00:24Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-15 agrees with mirror |
| ocd-participation-window/federal/2026-05213 | date_mismatch | 2026-04-16 | 2026-05-18 | closed | low | regs_id | FCC-2026-0991-0001 | 2026-09-01T21:50:33.559Z | 2026-03-17T16:55:24Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-18 agrees with mirror |
| ocd-participation-window/federal/2026-05218 | date_mismatch | 2026-04-17 | 2026-03-18 | closed | low | regs_id | CMS-2026-1189-0001 | 2026-09-01T21:50:33.559Z | 2026-03-27T04:40:09Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-03-18 agrees with mirror |
| ocd-participation-window/federal/2026-05743 | date_mismatch | 2026-04-24 | 2026-03-25 | closed | low | regs_id | CMS-2025-1857-0022 | 2026-09-01T21:50:33.559Z | 2026-03-25T17:03:36Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-03-25 agrees with mirror |
| ocd-participation-window/federal/2026-05915 | date_mismatch | 2026-04-27 | 2026-03-26 | closed | low | regs_id | CMS-2026-1190-0001 | 2026-09-01T21:50:33.559Z | 2026-03-27T04:42:53Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-03-26 agrees with mirror |
| ocd-participation-window/federal/2026-06531 | date_mismatch | 2026-05-04 | 2026-06-02 | closed | low | regs_id | FCC-2026-1256-0001 | 2026-09-01T21:50:33.559Z | 2026-04-03T16:56:04Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-06-02 agrees with mirror |
| ocd-participation-window/federal/2026-06539 | date_mismatch | 2026-04-03 | 2026-06-02 | closed | low | regs_id | ED-2026-SCC-1057-0001 | 2026-09-01T21:50:33.559Z | 2026-06-03T09:00:20Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-06-02 agrees with mirror |
| ocd-participation-window/federal/2026-06570 | date_mismatch | 2026-05-06 | 2026-04-06 | closed | low | regs_id | CMS-2026-0166-0002 | 2026-09-01T21:50:33.559Z | 2026-04-07T05:00:52Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-04-06 agrees with mirror |
| ocd-participation-window/federal/2026-06863 | date_mismatch | 2026-05-11 | 2026-06-08 | closed | low | regs_id | FCC-2026-1322-0001 | 2026-09-01T21:50:33.559Z | 2026-04-09T17:14:13Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-06-08 agrees with mirror |
| ocd-participation-window/federal/2026-07203 | date_mismatch | 2026-04-10 | 2026-06-09 | closed | low | regs_id | CMS-2026-1256-0002 | 2026-09-01T21:50:33.559Z | 2026-06-17T09:00:14Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-06-09 agrees with mirror |
| ocd-participation-window/federal/2026-07634 | date_mismatch | 2026-05-20 | 2026-04-20 | closed | low | regs_id | CMS-2026-0629-0002 | 2026-09-01T21:50:33.559Z | 2026-04-20T19:14:04Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-04-20 agrees with mirror |
| ocd-participation-window/federal/2026-08025 | date_mismatch | 2026-05-26 | 2026-04-24 | closed | low | regs_id | CMS-2026-0530-0002 | 2026-09-01T21:50:33.559Z | 2026-04-24T18:28:10Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-04-24 agrees with mirror |
| ocd-participation-window/federal/2026-08421 | date_mismatch | 2026-06-01 | 2026-04-30 | closed | low | regs_id | CMS-2026-0793-0001 | 2026-09-01T21:50:33.559Z | 2026-05-04T17:49:02Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-04-30 agrees with mirror |
| ocd-participation-window/federal/2026-08542 | date_mismatch | 2026-06-01 | 2026-05-01 | closed | low | regs_id | CMS-2026-0431-0004 | 2026-09-01T21:50:33.559Z | 2026-05-01T16:25:15Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-01 agrees with mirror |
| ocd-participation-window/federal/2026-09208 | date_mismatch | 2026-03-09 | 2026-05-15 | closed | low | regs_id | BOEM-2025-0042-0024 | 2026-09-01T21:50:33.559Z | 2026-08-26T22:38:03Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set — the July cohort); live regs.gov 2026-09-02 = 2026-05-15 agrees with mirror (same BOEM-2025-0042 extension as 2026-04517) |
| ocd-participation-window/federal/2026-09330 | date_mismatch | 2026-06-11 | 2026-05-12 | closed | low | regs_id | CMS-2026-0529-0063 | 2026-09-01T21:50:33.559Z | 2026-05-13T18:23:07Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-05-12 agrees with mirror |
| ocd-participation-window/federal/2026-09819 | date_mismatch | 2026-06-15 | 2026-06-29 | closed | low | regs_id | FCC-2026-1851-0001 | 2026-09-01T21:50:33.559Z | 2026-05-15T16:05:32Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-06-29 agrees with mirror |
| ocd-participation-window/federal/2026-09821 | date_mismatch | 2026-06-15 | 2026-07-14 | closed | low | regs_id | FCC-2026-1850-0002 | 2026-09-01T21:50:33.559Z | 2026-05-15T16:05:59Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-07-14 agrees with mirror |
| ocd-participation-window/federal/2026-11911 | date_mismatch | 2026-07-15 | 2026-06-15 | closed | low | fr_doc_num | DEA-2026-0933-0001 | 2026-09-01T21:50:33.559Z | 2026-06-17T22:29:38Z | our_bug | FR-only close (regs detail never fetched; closed pre-V1 so it left the re-poll set); live regs.gov = 2026-06-15 agrees with mirror |
| ocd-participation-window/federal/2026-13126 | date_mismatch | 2026-08-05 | 2026-06-30 / 2026-08-05 | closed | low | fr_doc_num | FAA-2026-4558-0449, FAA_FRDOC_0001-28135 | 2026-09-01T21:50:33.559Z | 2026-08-08T12:51:53Z | source_drift | mirror internally split (2026-06-30 vs 08-05); ours = FR extension date 08-05, live regs doc reads 06-30 — live FR-vs-Regs disagreement |
| ocd-participation-window/federal/2026-14942 | withdrawn_mismatch | 2026-08-24 | — | open vs withdrawn | medium | regs_id | BIS-2026-0397-0001 | 2026-09-02T20:40:25.814Z | 2026-08-21T21:25:58Z | our_bug | IDENTITY SPLIT (issue #112): live withdrawn=true since 08-21 and we DID observe it — but the withdrawn payload drops frDocNum, so the observation keyed to regs:09000064b93ba27b (a shadow window, status withdrawn) instead of this one. Original stays open off the stale openForComment=true; verify falsely recorded was_correct=true (post_close_repoll, 09-01) off the doc-level check stamp |
| ocd-participation-window/federal/2026-15740 | withdrawn_mismatch | 2026-10-05 | — | open vs withdrawn | medium | regs_id | EPA-HQ-OPP-2025-0041-0006 | 2026-08-20T10:46:39.678Z | 2026-08-20T19:36:52Z | our_bug | IDENTITY SPLIT (issue #112): same mechanism as 2026-14942 — withdrawal observed 08-20 under shadow regs:09000064b93f2d67 (frDocNum dropped from the withdrawn payload); this window still claims open until 2026-10-05. 6 split pairs exist in the projection, 5 with shadow-withdrawn + original-open |
| ocd-participation-window/federal/regs:09000064b924a305 | date_mismatch | 2026-07-23 | 2026-07-26 | closed | medium | regs_id | EPA-R05-OW-2025-2730-0001 | 2026-07-31T00:32:13.983Z | 2026-08-26T22:41:42Z | source_drift | close moved 07-23 → 07-26 AFTER close and after the 14d verify horizon (live modify 08-26; our verdict was_correct=true landed 07-31 and was right against the then-current source, last fetch 07-24); live regs.gov 2026-09-02 = 2026-07-26 agrees with mirror |

## Abstentions with a mirror date (16) — spot-check material, no triage required

| ocd_id | parquet (Eastern) | status | confidence | join | parquet docs |
| --- | --- | --- | --- | --- | --- |
| ocd-participation-window/federal/2026-03843 | 2026-04-27 | unknown | unknown | regs_id | SSA-2026-0034-0001 |
| ocd-participation-window/federal/2026-03942 | 2026-04-28 | unknown | unknown | regs_id | EPA-HQ-OPP-2017-0418-0008 |
| ocd-participation-window/federal/2026-05600 | 2026-04-22 | unknown | unknown | regs_id | SSA-2026-0133-0001 |
| ocd-participation-window/federal/2026-05786 | 2026-05-26 | unknown | unknown | regs_id | VA-2026-VACO-0001-0110 |
| ocd-participation-window/federal/2026-07300 | 2026-05-15 | unknown | unknown | regs_id | SSA-2025-0022-0001 |
| ocd-participation-window/federal/2026-08033 | 2026-05-26 | unknown | unknown | regs_id | SSA-2026-0265-0001 |
| ocd-participation-window/federal/2026-08138 | 2026-06-26 | unknown | unknown | regs_id | SSA-2026-0298-0001 |
| ocd-participation-window/federal/2026-08556 | 2026-04-30 | unknown | unknown | regs_id | ED-2025-OPE-0944-19637 |
| ocd-participation-window/federal/2026-08977 | 2026-06-05 | unknown | unknown | regs_id | USCBP-2009-0006-0012 |
| ocd-participation-window/federal/2026-10311 | 2026-06-22 | unknown | unknown | regs_id | USCBP-2025-0812-0003 |
| ocd-participation-window/federal/2026-10316 | 2026-06-22 | unknown | unknown | regs_id | SSA-2026-0496-0001 |
| ocd-participation-window/federal/2026-10735 | 2026-06-29 | unknown | unknown | regs_id | OSHA-2026-0001-0001 |
| ocd-participation-window/federal/2026-13286 | 2026-06-30 | unknown | unknown | fr_doc_num | ED-2026-OPE-0100-8801 |
| ocd-participation-window/federal/regs:09000064b93b0626 | 2026-09-19 | withdrawn | unknown | regs_id | NOAA-NMFS-2026-1354-0004 |
| ocd-participation-window/federal/regs:09000064b93e947f | 2026-09-17 | withdrawn | unknown | regs_id | EPA-HQ-OW-2025-0760-0001 |
| ocd-participation-window/federal/regs:09000064b94a6351 | 2026-09-28 | withdrawn | unknown | regs_id | EEOC-2026-0067-0002 |
