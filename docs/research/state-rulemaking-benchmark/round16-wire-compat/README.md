# R16 wire compatibility: an offline candidate the unchanged checker accepts

R15 left condition preservation undispatchable: its schema used `$schema`, `prefixItems`, `anyOf`, `pattern` and `items:false`, which the unchanged R14 runtime checker rejects, and its full request sat at 37,908 of the 40,000 guarded bytes. R16 resolves that offline. The frozen candidate is **r16.w2.1** (`protocol-w2-1/`): response wire format `r16.w1`, request envelope `r16.e2`. Its schema passes the unchanged R14 checker without loosening it, decodes into the unchanged r15.1 validator, and yields expanded records byte-identical to r15.1. The checker was not modified or bypassed.

The work ran as T3 child tasks coordinated by a Claude Opus 5.5 primary. GPT-6 Luna inventoried the checker and provider route, and checked the envelope. Opus 5.5 designed the wire format. GPT-6.1 Sol implemented all three revisions. Fable 5.1 wrote the independent suite blind to the implementation, then ran three review rounds. Claude children used the claude.ai subscription; no OpenRouter Claude or Anthropic API route was used.

| Measurement | Result |
| --- | --- |
| Checker dialect | Wire schema uses only R14-allowlisted keywords; every object closed with all properties required; depth 8 (root 0) |
| Fidelity | 32 valid r15.1 cases round-trip byte-identically; 5 invalid cases keep their r15.1 error codes |
| Own suite | 98/98 pass (75 carried from w1) |
| Independent suite (Fable, frozen) | 54/55; the one failure is the intended `source_text` removal |
| Prior source, guarded bytes (full / opaque) | 24,013 / 24,198 (R15: 37,908) |
| 24-clause profile, guarded bytes (full / opaque) | 29,024 / 29,209 (R15: 44,323, rejected) |
| Schema size | 5,085 bytes, independent of span count (R15: 11,776 and growing) |

**What changed from r15.1.**
- **Fragment tuples become closed objects.** Each `{a,h,ho,z,t,to}` maps by key name, not by position.
- **Non-deadline `y` becomes `[]`.** It was `null`. `[]` means "not a deadline", never "unknown". `[null]` is rejected (`protocol-w2/ERRATA.md`).
- **Two invariants move host-side.** The schema enum enforced that span IDs exist in the table, and a `pattern` enforced node-ID syntax. Both are now enforced by the host-side r15.1 validator, which already checked them.
- **The request no longer carries `source_text`.** The span-table rows already reproduced the source exactly (`envelope-check/`). `build()` now refuses unless the rows, concatenated in array order, reconstruct the source byte for byte.
- **`build()` refuses over-guard sources** with `full_request_overflow`. `measure()` returns sizing without a body.
- **`validate_response` requires the originating plan.** It refuses on any mismatch of profile, versions, table or request hash.

**What this does not establish.** No provider call was made, so it is unverified whether OpenRouter → `openai/gpt-6.1-sol` accepts or enforces this schema in strict mode. Every keyword form it uses appeared in the R14 request that returned HTTP 200, but R16 has larger nesting and more objects than R14 (depth 8 vs 4, 13 objects vs 2). Output headroom is a live risk: object fragments cost about 26 bytes each over tuples, and R14 already used 7,231 of 8,192 output tokens. The fixtures are authored, not model output, so nothing here measures extraction quality, scope accuracy or semantic equivalence. Records remain semantically unverified, and production eligibility and action readiness stay false.

**Requirements on any future dispatch adapter.**
- Pass the originating plan to `validate_response`.
- Recompute both the 40,000-byte guard and `request_sha256` from the exact body immediately before transport. Plan binding proves equivalence to `build(source, profile)`, not identity of the dispatched bytes (review-w2-1 note 2).
- Raise the output token cap above R14's 8,192.
- Write a rejection receipt for every `ValueError`; `WireError` is a `ValueError`.

**Next.** A paid, source-only comparison of clause-only vs full profiles on new inputs, with independently reviewed scope and exception expectations. It needs a frozen request, intact stop rules and explicit budget authorization.

Evidence: [inventory](inventory/INVENTORY.md), [design](design/DESIGN.md), [envelope check](envelope-check/FINDINGS.md), [independent tests](testing/TEST-PLAN.md), reviews [round 1](review/REVIEW.md), [round 2](review-w2/REVIEW.md) and [round 3](review-w2-1/REVIEW.md), [candidate spec](protocol-w2-1/SPEC.md), and [final verification](FINAL-VERIFICATION.json). Every folder carries a `READY.json` hash pin. Earlier rounds are unchanged.
