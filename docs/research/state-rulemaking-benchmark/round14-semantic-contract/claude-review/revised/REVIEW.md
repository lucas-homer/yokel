# Revised R14 independent Fable advisory review

Actual model `claude-fable-5-1`, provider `firstParty`, successful result, same isolated Claude.ai Max session. The approved payload contained bounded code/prompt/rubric diffs, new revision code/tests, changed fictional units and test/sizing results; no full prior report, fresh source/reference labels or credential/runtime code. Original review remains intact. All26 revised artifact hashes and original21 hashes were checked locally; unseen files are bound, not independently re-reviewed by Claude.

## Verdict and verified fixes

Claude's compact verdict: no material correctness blocker remains for an explicitly experimental source-only pilot with independent full-source semantic review. This is advisory, not dispatch approval, proof of semantic completeness or guaranteed output fit.

Codex independently confirmed revised inverse units/evidence=None raise ValueError; unit2 explicitly preserves unknown actor; units21/22 separately preserve arrival clock/zone linked to19; overlong s/c/r controls reject without mutation; illustration leakage remains structurally accepted with action_ready=false. The new request-clock/zone units23/24, separator and sentinel documentation are present in supplied diffs/tests.24 passing test results were supplied to Claude; Claude ran no tests/edits. Codex ran small targeted offline probes only, recorded in revised-codex-verification.json.

## Remaining findings and disposition

1. **Confirmed wording overclaim:** semantic-controls.json revision_checks illustration_leakage says “Fixture data never enters prompt”. This accurately describes the two new control sources, but main authored fixture facts overlap retained prompt examples. Scope that statement to the new controls; use disjoint facts for any future model calibration. Authored roundtrip controls are not live extraction results, so no observed gain/contamination claim follows.
2. **Qualification-loss risk remains open:** host rejects overlong text delivered whole, not model-produced shorter text omitting essential qualifications. Provider clipping behavior is unverified. Independent semantic review must inspect full source restrictions. Claude's proposed BOUND sentinel is optional design advice, not implemented or required by this review; it only catches compliant signaling, not silent omissions.
3. **Capacity/yield remains limited:** revised representative64 still fails70% diagnostic headroom; stressed96/128 exceed8192 even at4bytes/token. Byte ratios are not tokenizer bounds; no general fit guarantee demanded. Source-specific request/output/reasoning/token evidence and finish_reason must govern release/accounting decisions outside this review.
4. **Residual authored conventions:** unit2 actor fix is verified; other directives/timing units still need consistent actor and modality interpretation. Claude cites unit6 unstated recipient and units19/20 actor omissions. The prompt explicitly requires unknown actor/purpose, not every destination; distinguish a supported implicit actor from an unsupported inference in independent review. Units4/5 m1 versus new dimension units m0 leave a convention gap. Clarify dimension-unit modality to reduce reviewer disagreement; this is fixture/prose quality, not a proven validator acceptance defect.
5. **Minor cosmetic text:** stage-a.system.txt line24 has “exactly160” and “treat159”; add spaces during any coordinated refreeze.

No revised protocol edits were made by this child. Provider schema acceptance, actual GPT output token fit, fresh-source semantics, runtime accounting and any paid-pilot authorization remain unverified here. Claude's statement that no accepted output is corrupted should be read narrowly as no confirmed structural acceptance-corruption defect, not a guarantee against semantically incomplete accepted prose.

## Route and provenance

User's specific approval covers R14 code/extraction prompt/fictional fixtures/test-result export to Claude.ai Max, excluding credentials/prior internal reports/source-reference labels. Same neutral cwd /private/tmp/r14-claude-advisory.EGG7lO and isolated session aa1048d4-b115-4f93-ae9c-400bc4434fb5. Requested fable; actual claude-fable-5-1; no effort override. Built-in tools disabled, safe-mode, strict empty MCP; bridge does not expose initialization tool inventory. No OpenRouter Fable or Anthropic API route permitted; bridge unavailability means report blocker, never billing fallback. Raw list-price metadata is not proof of added subscription charges.
