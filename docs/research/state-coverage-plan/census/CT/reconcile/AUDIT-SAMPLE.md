# CT frozen random audit

Frozen (UTC): 2026-10-17T04:30:36.596216Z
Seed: `1d92095571f52176173a7cdf140c30cb03678b1263aaef709cc8928b73dc4f96`
Frame SHA-256: `8d4895f88af8b81ba76eac38c3fee7543f8c77cf3786fbdc3afb442c549c42a7`

Canonical frame is represented by the ordered strata and unit_coverage in run.json;
audit_freeze.frame reconstructs its exact compact, sorted-key UTF-8 bytes.

Budget 600; mandatory 355; overlap 0; total estimate 543 minutes. No reviews completed; actual minutes 0.

Check **boundaries, accepted labels, exclusions and overlooked candidates in originals** for every selected unit. Read selected content in full. Selection is not a completeness verdict.

Level | Strata | Sample | Audit minutes | Total minutes
---|---:|---:|---:|---:
0 | 152 | 245 | 517.0 | 872.0
1 | 23 | 149 | 325.0 | 680.0
2 | 23 | 127 | 281.0 | 636.0
3 | 23 | 83 | 188.0 | 543.0

Planning difference: completion-only union counts give 204 ordinary inclusions, 54 exclusions-only,
65 no-candidates and 27 scan/partial units. OWNER-SHEET used accepted-label evidence to promote
`ct-slice-2024-01-15`, `ct-slice-2024-04-15`, `ct-json-getrmrnotes-PR2024-032` and
`ct-json-getrmrnotes-PR2026-018` to inclusion despite zero completion candidate counts.
C08 requires completion counts: levels 1/2/3 therefore add two samples and four audit minutes
to planning (149/325, 127/281, 83/188). Baseline remains 152 strata, 245 samples, 517 minutes.

Strata below retain source/agency/process/format, union disposition, both-empty and text-layer flags; cycles are merged at level 1. Each unit covers exactly its own entry.

## `["ct-json","ct-uapa-agencies","noi","json","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=1; sample=1; 2 min/unit; 2 minutes.

- [ ] `ct-json-open-comment-periods` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/1dcebb4739da9c8b601e44f071769fb7d03ee1dd97a9efb21e42f141bbfcc18b`.

## `["ct-json","ct-uapa-agencies","rmr-lifecycle","json","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=77; sample=8; 2 min/unit; 16 minutes.

- [ ] `ct-json-getrmrhistory-PR2025-027` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/e42382716113b193f488cc6f8e1c9a233bccdcd72f1b5036736181d513ad1b7f`.
- [ ] `ct-json-getrmrhistory-PR2025-017` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/91df25d6286becb04a6f306ca66ba5b7713c0157fa78320fa27254a91e346d3a`.
- [ ] `ct-json-getrmrhistory-PR2025-008` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/3ff1f06c04e9fce93294cdf210b2e695ae54a735f25f8895d733e74d345c2d74`.
- [ ] `ct-json-getrmrhistory-PR2026-004` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/de6e474b6a14c1b9966b74f3f40bfa4a260323a90a64ea693e125f195cba1d13`.
- [ ] `ct-json-getrmrhistory-PR2026-012` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/ae86e3b4607639ae4c921cb4800d06d172bd1777ac402d7445750347c8794dbe`.
- [ ] `ct-json-getrmrhistory-PR2024-019` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/9c717d5e4978ccc42a1350e10d77b3c25eca4ecc22d68cb9c2940ff95342c29a`.
- [ ] `ct-json-getrmrhistory-PR2024-056` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/44d9330094aac9022547bb596c48bab48a93a74bea408784a29360ef0d22546b`.
- [ ] `ct-json-getrmrhistory-PR2022-002` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/faee450ca0700d7ebfa40795b3d73e18675afde1d0b930290ed77cac04296444`.

## `["ct-json","ct-uapa-agencies","rmr-lifecycle","json","all_cycles","no_candidates","both_empty=true","text_layer=native"]`

N=65; sample=13; 2 min/unit; 26 minutes.

- [ ] `ct-json-getrmrnotes-PR2024-032` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/b6dd327defe9d25af992f23dc2f057028c8da156a1117f5cbc69abbc60916f17`.
- [ ] `ct-json-getrmrnotes-PR2025-019` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2024-038` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2025-036` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2025-027` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2023-034` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2024-037` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2026-004` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2025-011` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2022-002` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2025-028` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2024-036` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- [ ] `ct-json-getrmrnotes-PR2025-014` — single JSON array response; route takes no paging or cursor parameters; `.census-passes/CT/inputs/originals/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.

## `["ct-policy-reference","ct-uapa-agencies","nod","html","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=1; sample=1; 2 min/unit; 2 minutes.

- [ ] `ct-xchk-portal-deep-pending-regs-nod` — single page; `.census-passes/CT/inputs/originals/ff4433ab71fbab138e3634c18fd9520fd835880db42f0bf4acb8fd69e5bebba1`.

## `["ct-policy-reference","ct-uapa-agencies","noi","html","all_cycles","exclusions_only","both_empty=false","text_layer=native"]`

N=7; sample=5; 2 min/unit; 10 minutes.

- [ ] `ct-xchk-portal-deep-laws-regs` — single page; `.census-passes/CT/inputs/originals/104a9374c4d1a4108c18d06a8217a6e762f67f053e17496038cf842f563ec671`.
- [ ] `ct-xchk-portal-deep` — single page; `.census-passes/CT/inputs/originals/9ea110a3d7ee96f9c0851b09c4d15fa8c261281381b8c523883c9fa0e04609db`.
- [ ] `ct-xchk-portal-seec` — single page; `.census-passes/CT/inputs/originals/60b575f57993e64d088eb5d6b0eb564321288f981fcd5d20f48a8cf0ff0bd18c`.
- [ ] `ct-xchk-portal-deep-public-notices` — single page; `.census-passes/CT/inputs/originals/4d356cff344274c560d789f51af45e8b1b39eefebd3ceddd083255181f053c47`.
- [ ] `ct-xchk-portal-deep-proposed-sip` — single page; `.census-passes/CT/inputs/originals/4357c381b3cf1d2d2e849f2fd248ddb039815d1a42582697183140ce54edab2a`.

## `["ct-policy-reference","ct-uapa-agencies","noi","html","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=1; sample=1; 2 min/unit; 2 minutes.

- [ ] `ct-xchk-portal-deep-pending-regs` — single page; `.census-passes/CT/inputs/originals/851e55714f7de7c37983bfcb53885adcd1d72a82de0a2cd55a3683950cad3b72`.

## `["ct-rendered","ct-uapa-agencies","nod","mixed","all_cycles","exclusions_only","both_empty=false","text_layer=partial"]`

N=2; sample=2; 3 min/unit; 6 minutes.

- [ ] `ct-doc-PR2023-045-nod-f05850900000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/1b859cda9f3568be06e1c6708a263874fcbab2c8f4485a81a0f888e909e01ec0`.
- [ ] `ct-doc-PR2024-014-nod-90c1c0900000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/9af49242533d41b1d2cb1410481c28e307df0bebdf85c78e9ab3f3c75b66799c`.

## `["ct-rendered","ct-uapa-agencies","nod","mixed","all_cycles","inclusion","both_empty=false","text_layer=partial"]`

N=3; sample=3; 3 min/unit; 9 minutes.

- [ ] `ct-doc-PR2025-035-nod-50f5f69f0000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/6b7fb7090082edc2d4e1d4cc46e7c20229cb785fdb9b7e2a520147099da9c9e8`.
- [ ] `ct-doc-PR2025-024-nod-a049d09e0000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/5dba667430db86e66abbf115b832ccde8bafa75052aa2bdc59ae6823de935728`.
- [ ] `ct-doc-PR2025-001-nod-70b816960000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/8357b84bac296a228f8188a5a5d619bfcf076ab60e4cf4b2a4b7f06f31933fe9`.

## `["ct-rendered","ct-uapa-agencies","nod","scan_pdf","all_cycles","exclusions_only","both_empty=false","text_layer=none"]`

N=2; sample=2; 3 min/unit; 6 minutes.

- [ ] `ct-doc-PR2015-132-nod-6085668d0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/7135529beca45c90ffb524b9e2961d6d492c71a38ac9a8cd7864efa4657d32e8`.
- [ ] `ct-doc-PR2022-026-nod-d0c6e48f0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/f955e06bee0d082defb0f8000151f7319390d33938b2d2f7c493742b8141bd51`.

## `["ct-rendered","ct-uapa-agencies","nod","scan_pdf","all_cycles","inclusion","both_empty=false","text_layer=none"]`

N=6; sample=5; 3 min/unit; 15 minutes.

- [ ] `ct-doc-PR2026-005-nod-7061649d0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/029aaa41ec0758091caa88211841a3cbc558ba4d97d646ff5d50080f8d2febe3`.
- [ ] `ct-doc-PR2025-011-nod-b0d3259a0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/853268b7a1ae081025be0d2a5aba6df5fcac219f46c2d75cf5e67ea751fd494c`.
- [ ] `ct-doc-PR2025-009-nod-d0569a980000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/3315ca069af8b40a1d2f3a9d1b42f68e4e33ad37123abbc3aca2617b64d64ef9`.
- [ ] `ct-doc-PR2024-043-nod-20ea94940000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/3eadf86d9fe8e64fbced0b0dbf95beccbd67aec7dbf344d48135143f9cabfe03`.
- [ ] `ct-doc-PR2025-012-nod-60f5bd980000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/b8007ca7d7730024b09af93866ae3b7de48b6f1151a1a3619975aeda90cc2dc0`.

## `["ct-rendered","ct-uapa-agencies","nod","text_pdf","all_cycles","exclusions_only","both_empty=false","text_layer=native"]`

N=22; sample=5; 2 min/unit; 10 minutes.

- [ ] `ct-doc-PR2024-021-nod-303595910000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/1f7fe387a9252fa360ab6fbd230e264e3c1a6ab6913ec497d16f997f7d176f05`.
- [ ] `ct-doc-PR2021-035-nod-60cf6c920000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/51af3894875de48eb74830da34e421c40bc9acbf44868e6d36b41bf94a05a745`.
- [ ] `ct-doc-PR2023-055-nod-10b438910200` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/86f8c85008867c6cd9b278808600436df5bb9f6b3cb031ebc0613ce1195f6c91`.
- [ ] `ct-doc-PR2023-052-nod-8020448e0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/710972d9853915ff674165423e4384fbcdf9c13edb9fe491f9db9b434fa1c9b0`.
- [ ] `ct-doc-PR2021-040-nod-70e4f38f0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/b37ebb78bc5b3b31627e3ff9f160f4b954b4f783b77a8785abbb2aea08e8a2b1`.

## `["ct-rendered","ct-uapa-agencies","nod","text_pdf","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=49; sample=5; 2 min/unit; 10 minutes.

- [ ] `ct-doc-PR2024-058-nod-80fd3b940000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/5ee3111f72fb420cbf378e0c3e59615e69e8b66e0e88fa9eff5d46a6331055dd`.
- [ ] `ct-doc-PR2024-003-nod-c0888d930000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/3d0ac3e0590df46afb4fd8ab382238a947070f2739e95a42fbb9af8b0d7353eb`.
- [ ] `ct-doc-PR2026-023-nod-80e31fa00000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/69084a1c7b3dd70197f477589892b04d405767e098af365e2d3498ce99bb8d9c`.
- [ ] `ct-doc-PR2025-016-nod-f0eabf990000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/f1ff9989404ee5573dd9fad7825048cc6aec11fee6788a212709192645d13125`.
- [ ] `ct-doc-PR2024-033-nod-600f88930000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/2e770aa5fd524277e2ff173e8e7c16e8691d12be9689db2b7f8858401dac25ba`.

## `["ct-rendered","ct-uapa-agencies","noi","html","all_cycles","exclusions_only","both_empty=false","text_layer=native"]`

N=3; sample=3; 2 min/unit; 6 minutes.

- [ ] `ct-form-public-notices` — single page; no result rows; `.census-passes/CT/inputs/originals/be63233da0f834765b4b38ad6ad42187f2de8b2f33bc01c89a3bb6080d480b4e`.
- [ ] `ct-slice-2024-01-15` — single server response; `.census-passes/CT/inputs/originals/e41b284bf234b228efe21c90071b942c86db3de914bb565c81fd2ce2dc7a4f99`.
- [ ] `ct-slice-2024-04-15` — single server response; `.census-passes/CT/inputs/originals/edc15a45db979ecd93a0c66e27f44476ffafe3bcd417bc77e1baa126d98aa508`.

## `["ct-rendered","ct-uapa-agencies","noi","html","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=9; sample=2; 2 min/unit; 4 minutes.

- [ ] `ct-slice-2025-01-13` — single server response; `.census-passes/CT/inputs/originals/ce6999258dd1db73f18e1c030f04937993a3ced3e4a965e0df0f0d1e6daf9cd9`.
- [ ] `ct-slice-2026-04-13` — single server response; `.census-passes/CT/inputs/originals/9a3a0c409d82f184862de23ace596a2bff4e035fb3e243ff295f30bfdafb8b96`.

## `["ct-rendered","ct-uapa-agencies","noi","mixed","all_cycles","exclusions_only","both_empty=false","text_layer=partial"]`

N=1; sample=1; 3 min/unit; 3 minutes.

- [ ] `ct-doc-PR2024-012-noi-5014c2900000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/4ea02fc612dd497ba8afb655bcf352735b665607ee57d6f45c88d01669fecbca`.

## `["ct-rendered","ct-uapa-agencies","noi","mixed","all_cycles","inclusion","both_empty=false","text_layer=partial"]`

N=9; sample=5; 3 min/unit; 15 minutes.

- [ ] `ct-doc-PR2024-035-noi-c0d49f920000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/3786baca3c58d6cfc15b1a11ed2b2aebec7187e3ea632e4b6288cdcc3786ae01`.
- [ ] `ct-doc-PR2024-036-noi-30e99f920000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/35d4d6b2bb03d09bf1e6e360da43923d71832e868784f7ea646639bf5b1475d4`.
- [ ] `ct-doc-PR2025-036-noi-90e9409e0100` — pages 1-3 of 3; `.census-passes/CT/inputs/originals/2a24a2c4721f22213fc66288affd1df5db5dc056cba49d0479cb1e868390cfe6`.
- [ ] `ct-doc-PR2024-037-noi-10dc9f920000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/ed4f51abc5c5efee638feddb8610fcbe40dfd032e65e0288ae191420bae64475`.
- [ ] `ct-doc-PR2025-034-noi-80011e9f0000` — pages 1-3 of 3; `.census-passes/CT/inputs/originals/7263e356eb8563ab255665a8b05161d689492e2fcc642bce0aaf800da2478479`.

## `["ct-rendered","ct-uapa-agencies","noi","scan_pdf","all_cycles","exclusions_only","both_empty=false","text_layer=none"]`

N=1; sample=1; 3 min/unit; 3 minutes.

- [ ] `ct-doc-PR2024-003-noi-b0bf8e8d0000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/89bd4a1063f0552062937705ef991755402a4aeba8af843084629a1760049efb`.

## `["ct-rendered","ct-uapa-agencies","noi","scan_pdf","all_cycles","inclusion","both_empty=false","text_layer=none"]`

N=3; sample=3; 3 min/unit; 9 minutes.

- [ ] `ct-doc-PR2024-032-noi-70fbcaa00000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/cfb905583322096b19cc397cd40f3b3d8719fc47307d8b7f9d4f9bcfac458641`.
- [ ] `ct-doc-PR2025-012-noi-f0c331970000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/6a38c9fdd12ca865595eec9fa5f7770a521243c7bbe6fa9bc1308e4887de1a0b`.
- [ ] `ct-doc-PR2026-005-noi-20ad4e9c0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/9ff660bc6138397033c6cf055d74c5fcdd1ccef3b22b811151299436c326298f`.

## `["ct-rendered","ct-uapa-agencies","noi","text_pdf","all_cycles","exclusions_only","both_empty=false","text_layer=native"]`

N=20; sample=5; 2 min/unit; 10 minutes.

- [ ] `ct-doc-PR2024-016-noi-e017e48f0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/0414d38c9736efce28f3fde692f3393461a2a700a9d8bb024eb9b2cdd5f44e1e`.
- [ ] `ct-doc-PR2023-039-noi-20c71d8d0100` — pages 1-3 of 3; `.census-passes/CT/inputs/originals/27bd049d37a8006c2511022a62170d6cda3db1689efd6c5aeab6026326e3d95c`.
- [ ] `ct-doc-PR2023-034-noi-c0cc2a8f0000` — pages 1-3 of 3; `.census-passes/CT/inputs/originals/61c4d5ae3f5b0e8727c4813ab0b6102f24081e36da92c698fc4d4a69942fd3a4`.
- [ ] `ct-doc-PR2024-014-noi-5061e48f0000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/6009d19aa0e17c9842b3fa4e87f8bb9f52f1b0f786fc9e43fde32cb062b0e3e5`.
- [ ] `ct-doc-PR2022-042-noi-60616c910100` — pages 1-3 of 3; `.census-passes/CT/inputs/originals/a2b73856385a43eb7e25848426333ca7b1f37a911e6433d3573082f82424f05d`.

## `["ct-rendered","ct-uapa-agencies","noi","text_pdf","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=63; sample=7; 2 min/unit; 14 minutes.

- [ ] `ct-doc-PR2024-025-noi-6050f0900100` — pages 1-4 of 4; `.census-passes/CT/inputs/originals/1a2092e897bb0a93d201a397ad524a8e5bb55bb7a200d754c2b586efd4a76e93`.
- [ ] `ct-doc-PR2025-010-noi-a0aa33980000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/6b322513adb8ee22b530f6e6ea6ca24ee66255308a29193c17500f9b681c3b18`.
- [ ] `ct-doc-PR2025-035-noi-f019459d0000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/06d249df4f0974862cf82912c124a1e7c9d39471b82a58bda2de347a2a27a869`.
- [ ] `ct-doc-PR2024-053-noi-404264930000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/8256022b168b8573290082cddd8e445dc2275c30d03d84e067092c105663910d`.
- [ ] `ct-doc-PR2025-017-noi-10d55f990000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/f6989eab8abdfcf2681dee781ba16afbdd5cd24579515c18d89dfe60e5161f7a`.
- [ ] `ct-doc-PR2025-021-noi-204a16990000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/2c6537114935cc876ead7bb7a3c49dd82125a02e51e648ad2e4d1081bacdb396`.
- [ ] `ct-doc-PR2026-021-noi-50b30fa00000` — pages 1-3 of 3; `.census-passes/CT/inputs/originals/b118108c64ade35132ea2a19208b510cb2971cdf2a592829d170b270cd2c0657`.

## `["ct-rendered","ct-uapa-agencies","rmr-lifecycle","html","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=1; sample=1; 2 min/unit; 2 minutes.

- [ ] `ct-shell-rmrview-PR2024-059` — single page; data loads from JSON routes; `.census-passes/CT/inputs/originals/1af8e4d1cc8e18d8138abc1f28a6fb455ef873807763d20829533051813fdc2f`.

## `["ct-rendered","ct-uapa-agencies","rmr-lifecycle","text_pdf","all_cycles","exclusions_only","both_empty=false","text_layer=native"]`

N=2; sample=2; 2 min/unit; 4 minutes.

- [ ] `ct-doc-PR2023-056-ext-e0a013910000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/b4f36432ef8fff3786957660ad5f3d1670d35a39f3ed443f6e0d9f8916ce7b45`.
- [ ] `ct-doc-PR2023-056-ext-d0a213910000` — pages 1-2 of 2; `.census-passes/CT/inputs/originals/0aa56761f21d784f4862ca98fb593d40c6aca18d4fcc318bfd705bdb0fd5a89a`.

## `["ct-rendered","ct-uapa-agencies","rmr-lifecycle","text_pdf","all_cycles","inclusion","both_empty=false","text_layer=native"]`

N=2; sample=2; 2 min/unit; 4 minutes.

- [ ] `ct-doc-PR2024-053-noi-d0bc69930000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/0d230d9951c9cdd3a13ff021cb53ded4913f521700e1a8f8f7d7ef2443d8debe`.
- [ ] `ct-doc-PR2026-021-ext-803bcea00000` — pages 1-1 of 1; `.census-passes/CT/inputs/originals/d6f52a04638b4160a2ba9a8964303070fb37a9a705509b427d5c580c0ae9a61e`.
