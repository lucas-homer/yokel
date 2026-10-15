# Independent implementation review — correction required

Reviewed stopped runtime READY SHA `bce58e1394bb29eb554db11c4da6f106396bd172f6e5482c5adde57be61ff04e`. All ten owned artifact hashes matched before execution. The review ran offline with process/network/credential guards and writes confined to review; runtime files and 4,995 historical artifacts remained unchanged.

## P2 — malformed assembly escapes response validator

`runtime/response.py:65` constructs `common = c.p.verification_payload(source, assembled)` and the schedule before entering its exception handler. `response.validate_response('{}', valid_source, None)` and the same call with `[]` raise AttributeError; `{'record': None}` raises ValueError. These are inputs to the documented public validator, so malformed input fails the structured invalid-result contract. Move preparation into the protected boundary and handle malformed containers (including AttributeError) without accepting any input or changing the frozen R7 code. Add regression coverage for malformed source and assembly containers.

Independent harness: 238 passing checks, 3 failing checks, all three reproducing this one finding. `implementation-checks.json` contains detailed outcomes and exact runtime hashes. `implementation_checks.py` is the reproducible review-only runner; it never rewrites owner reports.

Passing evidence includes exact 38,432 request bytes / 39,456 estimate; exact-40,000 acceptance and 40,001/multibyte overflow rejection; unchanged user payload and neutral-only system change; private-field exclusion; duplicate/raw overflow rejection; all 13 response fixtures; schema ref and ID boundary rejection; all ten approved outcomes; 30 rebound semantic mutations reaching below hash/approval checks; unsupported compound addition → not_complete; unknown over a known defect → unverified; dependency diagnostics; null-only mappings with valid backlinks → mapping_inconsistent; malformed coverage containers → unverified; renamed approved audit still passes, without fixture lookup; nonoperative evidence/coverage pointers rejected.

No semantic accuracy, authenticated reviewer identity, provider compatibility, production eligibility, or paid execution is established. Approval remains withheld pending the narrow validator correction and a new stopped READY snapshot.
