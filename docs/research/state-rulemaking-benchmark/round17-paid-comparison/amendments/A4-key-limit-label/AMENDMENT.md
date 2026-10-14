# Amendment A4: dedicated key with a $50 limit and label "DocketClock" (2026-10-14)

**User statements (verbatim, 2026-10-14):**
- "The key in OpenRouter itself is named "DocketClock". The key in the DocketClock Research 1password vault is the same name as before -- "OpenRouter API Key" …"
- "I set the limit to $50 and not resetting. They didn't have an easy way to set the limit to such a custom amount. It's fine. Don't worry about it."

**What changes:**
- **K1 label:** the expected OpenRouter key label is `DocketClock`, not `yokel-r17-paid-comparison`.
- **K-limit:** `KEY_MAX` (BUDGET §4; `r17recon.key_limit_ok`) is raised from $1.73 to $50.00, and the limit must still not reset. The admission rule `U + R × FLOOR ≤ L` stays, and with L = $50 it never binds. The ledger rules carry the operating bound unchanged: `OPERATING` $1.80, the $0.27 FLOOR per call, all remaining calls reserved at every admission, no retries, and a HALT whenever a debit term exceeds FLOOR.
- **Delivery:** the key's value sits in the existing runner-referenced 1Password item (vault `aaf4zqgqwi6vtlcxnkfyuvipxa`, item `2yi6d5ymf5qoy55ixnju3r5ayu`, field `credential`), per option A.

**Residual risk, restated:** the provider-side key limit no longer backstops the $2.00 design cap. It caps provider spend at $50. The R17 bound is the ledger's: at most three admitted calls, each expected to cost at most $0.26384 only if CN1–CN4 hold. If any of those fails, one admitted call's charge is not bounded locally, only by the $50 key limit. The user has accepted P-ACCEPT, stated a $3 tolerance, and explicitly accepted the $50 key limit ("It's fine. Don't worry about it.").

**Unchanged:** everything else, including the call plan (3 OPQ cells), FLOOR, OPERATING, the reconciliation rules and the anomaly halts.

**Implementation:** a new pinned `r17recon` revision changing only `KEY_MAX`, plus the matching adapter constants and tests, delivered as adapter r1.4 after the r1.3 runner integration, then a focused review.
