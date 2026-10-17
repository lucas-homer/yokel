# Blind-pass freeze, 2026-10-16

Briefs frozen at 2026-10-16T19:15:02Z (brief version census-step4-common-2026-10-16.r2), before either pass was dispatched.
Pass inputs were built by `census/pass_inputs.py` (projection pass-input-2) into `.census-passes/<ST>/inputs/`, outside git.
Drafted by a Codex child (GPT-6.1 Sol, high effort) and reviewed by a Claude child (Fable 5.1, high effort). The review found no leaks; all of its blocker and should-fix items were applied.

Isolation is procedural. Both passes share one machine and checkout. The boundary is the brief's path rules plus the primary withholding each sealed output until both passes seal.

| State | brief sha256 | INPUTS.json sha256 | pass manifest sha256 | retrieved |
|---|---|---|---|---|
| WA | `5dc347d2cd8851cab9bca49380590ca46edebf7ec3290268475937b7a6a77665` | `c31b06fa0f0dd3b9d9cb8fd460fe8fdbf2e21f8b5289f67be85f426fad7cb543` | `7c1639370f12c992cef5cfa606c5363fc43f05922c4d5d7f7ae437af9f85908b` | 2813 |
| VA | `9332233d7adc667f0009b5fc05367dc0b665dc4f4b05e001620ca7b3f4ff54dc` | `ea160e33d489cf7388bfc32e4c3e9fb92c4f88d99d3f0619d43d424cbbe1e7e3` | `877a66577cacaa999b68cf63b23f645ec8a8b9511b0906b229a58e4a70ee0dd8` | 263 |
| CT | `5a495b0fa030310ee9f7dc915258b19f89fb0bdea7dca8f4fdabdf260c74f5b0` | `45e1d46f79e07ace47c626dd2714a6d3743aeb630a2122b6623fb872c9da5b25` | `755424b4b215cc13e8815d8abaefbdb58e644ee06810f4fa0b6f9d1241fa9791` | 350 |
| MS | `23437775caa21b09786c1ca1262c816e5081efdaebce719f6f668903912135f0` | `62cc294398d8de729a65cd5f5e575258bbac1d621ad2bbd264464703b0be91be` | `c356c251cbd0e4fc2c3459548faaaf79cbbca7a4280214b7b9f15037da01087d` | 649 |

## Pass ledger and isolation notes (primary, 2026-10-17)

| State | Pass A (claudeAgent / claude-opus-5-5) | Pass B (codex / gpt-6.1-sol) |
|---|---|---|
| CT | r1, sealed 2026-10-16T19:55:25Z | r2 (r1 stopped early; diagnostic kept in the sealed store), sealed 2026-10-16T20:19:55Z |
| VA | r1, sealed 2026-10-16T20:07:33Z | r2 (r1 stopped early), sealed 2026-10-17T06:16:54Z |
| MS | r1, sealed 2026-10-16T20:24:58Z | r2 (r1 had unviewed bulk images; discarded), sealed 2026-10-17T07:24:43Z |
| WA | r1, sealed 2026-10-16T20:14:28Z | r2, running |

- **Harness preload.** Every Claude child started with the repo's AGENTS.md, the global instruction
  files, the memory index and a git status snapshot that includes recent commit subjects. None of
  this contained the other pass's output. One preloaded subject named an MS step-3 acquisition count
  ("filing-ID sequence 591/592"). WA and MS pass A disclosed the preload and set `isolated=false` in
  their attestations. The primary counts these passes as isolated in `run.json` (`isolated: true`):
  the preload held no other-pass output or derived hints, every pass received it, and both passes
  disclosed it. The attestations are kept unchanged under `<ST>/attestations/`.
- **MS independence check.** The passes agree on entity counts and IDs (deterministic IDs from the
  same filing numbers), but share 0 of 683/748 evidence quote strings and 0 unresolved notes. Pass B's
  only "pass-A" path access was the synthetic example in `inputs/schemas/examples/`.
- **Codex tooling.** Codex `view_image` drops images sent in bulk. Pass B round 2 was required to
  view one image per call and to log only pages it actually saw.
- **Dispatch times.** Pass A's `dispatched_at` of 19:16:00Z was stamped just before dispatch. The
  actual dispatch fell between the 19:15:33Z staging time and each pass's `started_at`, always
  after the 19:15:02Z freeze.
