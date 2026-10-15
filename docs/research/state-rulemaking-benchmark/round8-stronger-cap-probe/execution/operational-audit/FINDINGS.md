# Completed stronger-cap probe: independent operational audit

2026-10-11 America/Los_Angeles. Operational evidence passes; the model verdict remains
invalid and unaccepted. No blocking evidence-integrity or accounting defect found.
Semantic source correctness is a separate review and is not established here.

## Evidence and scope

63 offline checks passed in audit.py; detailed results are in RESULT.json. The audit
blocks network/subprocess calls, credential paths and writes outside this new directory.
It did not invoke the live runner, adapter, credential reader, Keychain, signing key,
provider or installed-binary modification. Only this directory was written.

- Freeze E SHA256 matches primary's external reference
  `33837085a3fde23e7323372de77c31cc694a532865c49799d4457668826aa1c6`;
  all 23 file hashes/sizes match, covering every retained run file and both live receipts.
- Freeze A32, S4 and original label freeze B9 match their bound hashes and files.
- Both prior baselines match: execution1391 and independent-review4910 files, with no
  differences. These overlap; do not add their counts as unique files. The four prior
  execution freezes and five prior paid-operation accounting references also match.
- All 42 implementation code pins, 1,779 dependency pins and six retained input pins
  match. Authorization, manifest, implementation and dependency bindings match.
- Installed stable-v1 still hashes to
  `821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e`.
  continuity-result.json records identity and both non-network smoke jobs passing;
  this audit does not independently repeat credential reads or claim locked/reboot
  continuity or complete opaque ACL preservation.

## Request and execution

The retained request differs byte-for-byte only in the literal max_tokens4096→8192.
Model/provider settings, instructions, complete wire payload and schema are unchanged.
Source, assembly and common payload remain identical to pinned originals; independent
lossless wire restoration reproduces the original payload and record binding.

There is one durable stronger operation, one intent, one response and one parsed result,
with consistent request/response/identity/pins hashes. No new inventory or Jev operation,
continuation, retry or response repair appears. Frozen code restricts the operation kind
to stronger, caps it at one, records intent before POST and disallows automatic retries.
This supports one dispatched call within this run; it is not provider-side network-log
or invoice verification. Older Jev output remains historical, not a fresh paired result.

## Response and exact validation

HTTP200; OpenRouter names provider OpenAI and model openai/gpt-6.1-sol. Raw finish_reason
is stop and native_finish_reason is completed. Usage: 7,111 prompt tokens, 6,026 completion
tokens (including 66 reasoning tokens), 13,137 total; retained elapsed time about77s.
The prior4096 response ended with length at4096 tokens. This8192 run completed and parsed.
That is evidence the increased cap allowed a finished response in this run, not proof
of a general cap effect or semantic correctness.

The entire response parses without duplicate JSON keys/nonfinite constants. Re-running
the frozen native parser reproduces result.json exactly. The closed JSON schema alone
passes. Exact item-set validation fails: expected70 IDs, returned71 unique IDs, missing
none, duplicates none, extra ID coverage. That name is the record's coverage metadata,
not an item yielded by the frozen contract. All global sections are present. Re-running
the original full validator reproduces the sole recorded error and normalized_verdict=null.
No deletion of the extra assessment, salvage, relabeling or acceptance was performed.

The raw response asserts complete with no missing_items or contradictions, including in
the extra coverage assessment. That is the model's claim, not a validated completeness
finding. Semantic review must assess it independently against the frozen source evidence.

## Observation honesty

completed and stronger_verification_completed describe execution/parse completion here,
not successful contract validation. Stronger is review, source_coverage_complete=false,
complete_record_shadow_accepted=false, source_fidelity=unverified, production_eligible=false
and action_ready=false. All five normalized dimensions are forced uncertain after invalid
validation; they are not the model's five judgments or calibrated probabilities. The four
explicit-source/route/association/modality deterministic review reasons pre-existed this
call and independently block acceptance. The generic generative_omission_explanations_available
flag denotes available generative output, not proof that an omission was detected.
There is no fabricated fresh Jev result. The observation, terminal and completion receipts
agree and the observation validator passes. No accepted verdict exists.

## Costs (USD)

| Measure | Amount |
|---|---:|
| New OpenRouter response-reported cost | 0.078036 |
| New usage × frozen-rate estimate | 0.074482 |
| New retained conservative reservation/debit | 0.153414 |
| Prior five-attempt conservative debit | 0.542976718 |
| Cumulative six-attempt conservative debit | 0.696390718 |
| Cumulative recoverable OpenRouter reported subtotal | 0.386025 |
| Historical Jev usage-rate estimate, separate | 0.000502026 |

The budget remains the original2.00; failed attempts retain their conservative debits.
The exact-request reservation uses35,747 estimated input units at0.000002 plus8192 output
units at0.000010. It is below the preauthorized worst-case new reservation0.161920.
No reservation was refunded merely because a lower usage cost was returned. Reported
cost and frozen-rate estimate differ by0.003554; they remain separately labeled. Neither
the reported subtotal nor a sum with the Jev estimate is a verified invoice. Decimal
recomputation retains a3e-17 historical float artifact; displayed totals round to the
recorded nine-decimal amounts without changing the budget conclusion.

## Recommended interpretation

The larger cap produced a finished, parseable response on this known diagnostic example,
but it did not produce an acceptable verdict: the exact assessment-ID contract failed.
No missing assessment caused this failure. Do not promote raw completeness claims, forced
uncertain labels, successful execution, or the deterministic review gate into evidence
of verifier accuracy. Preserve all original artifacts and the conservative budget debit;
no automatic retry or new experiment follows from this audit.
