# Round 12 revised protocol review

**APPROVED FOR OFFLINE RUNTIME IMPLEMENTATION. No paid dispatch or runtime release is approved.** The fixed lossless C transport resolves the initial blocker sufficiently for this bounded feasibility experiment. Actual B overflow remains an anticipated partial-pilot outcome, never permission to change the representation or the inputs.

Reviewed protocol READY: `be674e8d2dc1240bc445acccdd4e70f52319584017e52ccb7649938cc679a7a9`. Reviewed SOURCE-READY: `44662f87e11176a72d3d6e6bffd3fb65ffbcaf635a0e7126d29979e1c2b0a3de`. SOURCE-BINDING correctly pins the current READY and unchanged source archive, retains the initial READY pin, and adds FRAME.json to the closure. Initial protocol and review receipts and their pinned artifacts were verified unchanged.

The revision affects B's scope input transport and appended generic decoding explanation. A/C/D prompts, all response schemas, scope policy, inventory transport and model/provider settings remain byte-identical to the initial freeze. C still classifies every frozen A ID from source and inventory only; D retains independent source discovery. No reference/semantic-gold contents were read.

## Codec and boundaries

The fixed five-column scope rows preserve every ID, category, basis, reason and evidence selector in A order. Category and basis are encoded independently. Evidence spans use exact Unicode codepoints and original overlapping occurrence numbers. Source and inventory bindings are retained; B's scope hash binds original complete canonical C, not the wire. Raw C remains unchanged. Host decode requires complete object equality, canonical-byte equality and canonical SHA256 equality against frozen C.

Independent tests covered all four valid category/basis combinations; contradictory combinations; boolean, fractional, string and out-of-range codes; closed envelope/version/columns; missing/extra/duplicate/reordered IDs; malformed widths; boolean/fractional/bounded spans; wrong occurrence; Unicode and overlapping selectors; reason mutation; evidence mutation/order/loss; binding changes; and a 64-unit boundary round trip with maximum permitted reason/quote lengths. The complete candidate projection and full source remained identical in every measured request. The B input allowlist changes only `scope` to `scope_wire`; forbidden assessment/gold inputs and A/C/D boundaries are unchanged.

## Bounded size admission

Independent assembly reproduced the author's complete canonical request hashes for all 15 profiles, including JSON user-content escaping, full prompt/schema/settings, full operative candidate and source, plus the unchanged 1,024-byte allowance.

| Profile | Units | Guarded bytes | Fits 40,000 |
|---|---:|---:|---|
| Modest | 32 | 36,337 | yes |
| Modest | 40 | 39,369 | yes |
| Modest | 48 | 42,401 | no |
| Concise | 48 | 38,561 | yes |
| Modest | 64 | 48,465 | no |

Modest dimensions remain 90-character assertion, 30-character applicability, 100-character scope reason and one 94-character quote. Concise uses 70/20/50/60 respectively. These artificial dimensions show a plausible request-size envelope; they are not a semantic inventory, a completeness witness, model truth, or a promise that this source's actual outputs will fit. The modest 40-unit probe leaves only 631 bytes of guard headroom. Unit count, dependencies, multiple quotations and longer reasons can cause actual overflow.

This is sufficient for the requested implementation barrier; fitting every legal 64-unit combination is not required. The runtime must measure the actual full request before each attempt and stop B on overflow. Report the missing B stage and partial arm in the pilot denominator. No adaptive codec, shorter reasons, dropped assertions/evidence, candidate/source changes, guard increase, fallback or paid retry is permitted. The four-call/no-retry/price/budget rules remain unchanged.

## Remaining runtime gate

Implementation must enforce both inventory and scope exact round trips immediately before construction/dispatch; full source/candidate bindings and reviewed exhaustive pointer enumeration; strict raw JSON/schema/ref rejection; exact schedules; uncertainty and preserved raw losses; source/candidate/projection-bound reverse audit; and stage failure, budget and actual-request-size stop rules. Provider compatibility and semantic performance remain unverified. This approval cannot be used as live-release authorization.

Two inherited wording remnants are nonblocking: evaluation-plan's older interpretation sentence still says “four calls versus one,” although the added arms_transport correctly says three-stage versus one-stage, four total; SOURCE-BINDING's fresh_source_exposure describes the initial freeze, while codec_revision_exposure separately and correctly discloses later source/candidate sizing exposure. Read these with their explicit revision fields and preserve the corrected interpretation in release/reporting.

## Validation and ownership

`checks.py` / `check-results.json`: **247/247 independent checks passed**. Reproduced **54/54 author static checks**, **8/8 codec tests**, and **15/15 size-profile exact C round trips and request hashes**. All inspected input pins were rechecked at the end. Only new review/protocol-revised artifacts were written. No provider calls, credentials, signer/runner actions, reference access or changes to prior review/owner artifacts occurred.
