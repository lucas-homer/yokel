# Review resolution — stopped revised candidate

All five initial findings addressed; independent re-review remains pending.

Initial READY SHA256 `fa473752bff2b750f41ed325e19f4e8b40408b820ef2e03e16cc5f8e3fd31a43` and its ten pinned files are preserved byte-for-byte under revisions/initial/. Initial review files and every earlier consulted artifact were rechecked unchanged. Edits remained within protocol/.

Root causes were reproduced before fixes: all four original adversarial inputs accepted the erroneous result, and four new regressions failed (reproduction-red.txt). The corrections were tested separately before the full suite:

1. Unknown propagation no longer discards known raw required/context losses. known_required_defects preserves missing/mismatched status; required_defects includes it even when effective_mappings says unknown. The same relation g now remains a known mismatch with unknown members and an unverified gate.
2. Reviewed reverse audits require source_sha256 and operative_sha256 bindings to exact current values. Historical missing bindings and changed source/value under unchanged ref names reject. Not-run audits have empty bindings. Projection enumeration still cannot prove exhaustive extraction from an original native record.
3. Scope category/basis correspondence is checked in both directions. uncertain_source_function can only coexist with unresolved_scope; contradictory included categories reject instead of becoming complete.
4. Every operative facet, including unmapped additions, independently validates closed kind-specific shapes, kind/modality/purpose/relationship enums, condition and qualifications. Well-formed unsupported additions continue through the separate reverse audit rather than being rejected as malformed. Fourteen additional malformed shape/type controls are subtests, not model evaluations.
5. The prospective plan explicitly compares human-assisted source-first with unassisted direct. The operational scope annotator is disjoint from the two sealed held-out reference reviewers and sees source plus frozen A only. Arm inputs enumerate exactly which operational annotations B receives; neither arm receives reference/gold adjudication, crosswalks or known omissions. Exposure is logged, unblinding follows frozen outputs, and no evaluation feedback enters operational inputs. Operational annotation minutes/compensation and shared reference/review effort are recorded separately from the labeled provider-only cost metric.

Validation: 35/35 synthetic fixture expectations and 21/21 unittest methods pass using existing Python with -B. Original fixture sources, inventory, scope labels, mappings and expected semantics were preserved; only reverse-audit envelopes were migrated for bindings. make_fixtures.py was kept consistent but not rerun. Historical counterexamples are read-only test inputs; no review files were rewritten.

No paid calls, budget changes, signing/credentials, installs, runtime expansion or production/schema changes. No live compatibility claim; production readiness remains false. Primary should request independent re-review of this stopped READY candidate, not execution.
