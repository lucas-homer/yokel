# Decision: keyed response object, strict parsing, existing normalized verdict

Chosen after primary review: assessments is an exact-ID keyed object with every expected property required and additionalProperties:false. Assessment value omits item_id. A small explicit adapter adds each key as item_id and returns the existing R7 array representation only after strict raw parsing and wire-schema validation. All global sections stay as before. This affects research transport, not the record schema or production contracts.

The original array-enum/count design remains comparison-only. Its balanced duplicate could pass enum and length checks and fail later host validation. Keyed properties prevent that structural output pattern in schema, but duplicate raw JSON member names must still be rejected before parsing overwrites them. Host exact-ID/binding/evidence checks remain mandatory after normalization. No implementation or provider-compatibility claim is made.

Neither alternative discovers source omissions. Source-first units, manually proposed semantic-pointer mappings and independent audit remain separate from candidate ID coverage and provider-visible inputs. No parser/schema relaxation follows a model output.

This revision supersedes review-candidate READY hash 87d9e3934be98907eee4950b4a6ab7faae7c54e6c075efc83f1af06ce850d92f. No earlier round or frozen source/result was edited.
