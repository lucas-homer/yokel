# Independent one-call live runtime review

Preparation passes 50 checks: frozen request and protocol/runtime pins, 5,055 historical artifacts, independent exact 70-ID enumeration, six-operation conservative debit reconstruction, and admission arithmetic. Prior-debit precision retains the known legacy float residue; the approved nanodollar carry-forward is 696390718.

Final review is withheld until runtime owner READY explicitly stops edits and binds the candidate. The final receipt will bind the exact stopped runtime and scope without requiring runtime to hash the review (avoiding a cycle).

Remaining controls: independent offline request equality and dependency/pin integrity; no-call rejection of scope/auth/guard drift; one durable OpenRouter intent and no second dispatch, retry, repair, fallback, inventory or Jev; lock/replay/partial-write behavior; valid and invalid native envelope, HTTP/schema rejection, uncertain transport, truncation, credential echo, malformed cost and cost above reservation; conservative budget retention even on failure; honest structural and semantic states, never production/action promotion. Tests use only synthetic responses and sentinel keys, with network/process and credential-file guards.

Existing stable credential core and release interface are read-only dependencies. Primary owns concrete admission, signing, job release, and live execution. Wide keyed schema/local-reference provider compatibility remains unverified until the single authorized call. Development reuse and independent source audit remain explicit limits.
