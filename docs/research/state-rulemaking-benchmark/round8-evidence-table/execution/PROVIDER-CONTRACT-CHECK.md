# Provider request-shape check — 2026-10-11

Primary read the TypeSafe skill and live official documentation: [API](https://docs.typesafe.ai/api), [state](https://docs.typesafe.ai/concepts/state), [Choice](https://docs.typesafe.ai/primitives/choice), and [citation verification cookbook](https://docs.typesafe.ai/cookbooks/citation_check). Index and HTML pages accessible; direct .md requests failed.

The API accepts state as string/object/array, typed questions with instructions, and Choice criteria as a map. A versioned JSON evidence envelope fits the documented state type. Existing endpoint, bearer authentication and answer/usage fields remain consistent with pinned code. Keep the pinned model and existing five questions/criteria; question IDs are not model instructions. Evidence lookup instructions must therefore appear in each relevant question, not merely its ID.

This validates request shape only. It does not establish provider acceptance of this exact body or reliable model use of evidence references. The first paid pair measures those issues. Preserve all full source and record information; validate strict deterministic restoration separately. No documented token capacity is inferred from local UTF-8-byte guards. No pricing, models, verdict schema or acceptance changes are authorized by this check.
