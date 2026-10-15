# Routing and normalization experiment — round three

Status: development in progress. This is a research prototype; production remains federal-only.

## Questions

Can deterministic evidence checks plus a narrow semantic verifier reduce consequential normalization errors without sending every notice to a more expensive parser or human review? Does Jev improve the quality/cost tradeoff over the same checks alone and an inexpensive general-purpose model?

## Boundaries

The 28 previously reviewed notices are development data. Prior reference labels may score results but must never enter production-shaped runtime inputs. Reference text selected by a reviewer is a challenge-test input, not evidence that automated retrieval works. Synthetic corruptions must remain separate from naturally observed errors. No national accuracy or production routing claim follows from this pilot.

A verifier receiving only corrupted parser text cannot establish original-PDF fidelity. Evaluate source-text support separately from visual/source correctness. All acceptance policies retain explicit unknown/conflict states. Dates and string comparisons belong in code; model scores are experimental signals, never measured reliability by assumption.

## Workstreams

- Baseline: native text candidate extraction, source spans, conservative deterministic checks.
- Verifiers: shared inputs, pinned Jev and catalog-verified inexpensive OpenRouter model; bounded calls and retained responses.
- Challenge: independently labeled natural errors and correct controls, plus clearly marked controlled mutations and blind spots.
- Protocol: frozen developmental metrics and requirements for a later genuinely fresh evaluation.

## Execution plan

Finish offline adapters, contracts and tests before any provider calls. Freeze pilot inputs and question definitions. Initial paid verifier pilot is at most 20 cases per provider, with a nominal estimated ceiling of $0.25 per provider; actual billed usage is recorded separately. No automatic resubmission of uncertain POST outcomes. TypeSafe credentials are pending user input; other work proceeds independently.

Measure consequential false acceptance, error detection, unnecessary escalation, abstention, and cost per correctly accepted observation. Report denominators and provider failures. Random auditing of accepted documents and new source families are required in the later fresh phase.
