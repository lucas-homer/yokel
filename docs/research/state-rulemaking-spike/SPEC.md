# Three collection paths, one observation format

Research spike authorized October 5, 2026. This is an offline evaluation, not a
production adapter, accepted shared contract, or state coverage commitment.
The primary owns this specification and the shared evaluator. Children own
only their assigned `ct/`, `wa/`, or `pdf/` directory. Do not change
`packages/contracts`, application code, or the earlier audit.

## Deliverables per path

- `manifest.json`: an array of retained artifacts and collection attempts.
- Raw public-source captures, transformed text where applicable, and hashes.
- `expectations.json`: source-grounded checks recorded before an extraction
  trial; describe these as inspected examples, not a blind benchmark.
- `normalize.py`: Python standard-library research script, runnable on the
  saved artifacts without network access. It writes `observations.json` in
  its own directory. No installs, environment creation, app builds, or servers.
- `observations.json`: an array using the envelope below. Use actual source
  fields/text and guarded parsing; do not hardcode the expected answers as an
  adapter. Label manual/visual additions honestly.
- `results.json`: methods, counts, observed tool latency/credits when reported,
  errors, source-specific rules, unexpected results, and limitations.
- `NOTES.md`: compact findings, acquisition vs parsing vs interpretation work,
  whether Firecrawl earned its use, and remaining work before unattended use.

## Artifact manifest

Each retained artifact has `artifact_id`, `path` (relative to the lane folder),
`sha256`, `source_url`, `retrieved_at` (ISO timestamp or null for inherited
fixtures), `media_type`, `representation` (`raw_json`, `html`, `markdown`,
`native_text`, `pdf`, or `image`), `source_lineage`, `collector`, and
`is_inherited` (boolean). Preserve retrieval failures separately in results;
do not hash an error page as if it were the expected PDF or feed. A transformed
representation is not an original-byte capture. Paths must stay in the lane.

## Observation envelope (version `state-spike-v1`)

Every observation is one candidate assertion:

```json
{
  "schema_version": "state-spike-v1",
  "observation_id": "ct-unique-research-id",
  "jurisdiction": "US-CT",
  "source_record_id": "source-native identifier or null",
  "subject": {"kind": "proceeding", "id": "namespaced research identity"},
  "predicate": "comment_close",
  "value": {"kind": "instant", "utc_instant": "2026-10-03T03:00:00Z"},
  "evidence": [{
    "artifact_id": "unique-lane-artifact-id",
    "locator": "/0/CommentPeriodEndDate or line/page description",
    "quote": "exact substring of the retained text representation",
    "support": "text_exact"
  }],
  "method": {"kind": "deterministic", "name": "ct-fields", "version": "1"},
  "review_state": "candidate",
  "warnings": []
}
```

Allowed subject kinds: `proceeding`, `notice`, `participation_window`, `hearing`,
`instrument`. Allowed method kinds: `deterministic`, `model`, `manual_visual`,
`manual_text`. Review state: `candidate`, `needs_review`, or
`reviewed_for_research`. These are never production approval states.

Allowed predicates: `agency`, `title`, `event_type`, `rule_action`, `rule_citations`,
`filing_date`, `publication_date`, `comment_open`, `comment_close`,
`hearing_time`, `hearing_status`, `effective_date`, `withdraws`,
`comment_duration`, `hearing_request_duration`, `operational_policy_date`.

Use strings for agency/title/event/status; arrays of strings for citations;
an object `{target_source_record_id, scope}` for a withdrawal relation.
For this bounded spike, canonical event types are `proposal` and `withdrawal`;
the source's original label remains in evidence. `rule_action` separately uses
`new`, `amendment`, `repeal`, or `adoption_by_reference` when supported.
Canonical hearing status uses `scheduled`, `not_scheduled`, or `canceled`.
An index category or an event's Posted Date must not silently become a
participation opportunity or its legal opening/closing date. Retain posting
metadata in source artifacts when the bounded envelope lacks its proper role.
Temporal values use `kind` = `instant`, `date`, `local_datetime`, or `relative`:

- `instant`: `utc_instant`; keep raw timestamp in evidence. Decoding a source
  timestamp is not a finding about legal authority or independent corroboration.
- `date`: `date` in YYYY-MM-DD. Never add an unstated clock time.
- `local_datetime`: `date`, `time` (HH:MM), `timezone_text`, `iana_zone`, and
  `utc_instant`; unresolved zone/instant fields must be null.
- `relative`: `duration` (number), `unit` (`days`), `anchor`, `day_basis`,
  `computed_close`; unresolved anchor/counting/close fields must be null.

Optional `submission_condition` preserves receipt/postmark/portal distinctions.
Do not reuse a hearing, accommodation, filing, or effective date as a comment
close. Blank fields and generic widgets are not assertions. Separate windows
and events retain separate subject IDs; source-native IDs are not automatically
globally unique. These example IDs do not define a production OCD namespace.

Every evidence quote with `support: text_exact` must be found byte-for-byte in
the UTF-8 artifact. A PDF checkbox can instead use `support: visual_review`,
with page/region locator and a saved review note; it is a manual observation.
Never claim automated visual extraction from an agent's own inspection.

## Evaluation discipline

Record acquisition success, extraction/shape validity, semantic support, and
publication readiness separately. Record failures and abstentions. A working
single-page result does not establish completeness, reliability, or legal
interpretation. Do not make a national accuracy claim from these selected cases.
No paid subscription creation or vendor contact is authorized by this spike.
Existing connected tools may be used for bounded trials on public sources.

The primary will validate schema, artifact hashes, quotes and cross-path output,
replay each normalizer offline, and have an independent child challenge key
date-role, identity, precision, and evidence claims. Report tooling unavailable
for a real comparison rather than substituting documentation for execution.

## Integration clarification, October 5

The first lane outputs exposed inconsistent event vocabulary and a need to
separate a proposed amendment's lifecycle event from its rule action. The
primary added `rule_action` and the canonical vocabularies above before final
integration. The research envelope version remains v1 because it has no
published consumers; the clarification and affected replay are recorded in the
review history. No production shared contract was changed.
