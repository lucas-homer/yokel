# Finding resolved — offline candidate approved

The corrected prompt distinguishes unestablished/incomplete coverage from faithfully represented source uncertainty. Final review verified the paired regression, all record fields except coverage, 19 passing tests, ten full-body fixtures and unchanged prior bytes. No open blocker remains. See `REVIEW.json` and `FINAL-REVIEW.md`; the original finding below is retained as history.

# Independent offline review — current finding

## Coverage and source certainty are conflated (prompt contract correction required)

`prompt-delta.txt` currently says: “If any relevant function, detail, scope or association remains unresolved or insufficiently represented, use coverage.status=uncertain”. The “remains unresolved” branch forces uncertain inventory coverage even when a genuine source ambiguity is faithfully and completely inventoried. That changes the meaning of coverage and conflates completeness with certainty.

Evidence: frozen `round7/pipeline/pipeline.py::review_reasons` independently tracks `inventory_coverage_uncertain`, `explicit_source_uncertainties`, `association_unresolved`, and `timing_unresolved`. The original prompt permits explicit uncertainties and treats claimed completeness only as an independently tested inventory claim. Fully represented source ambiguity still requires review; it need not mean missing or unestablished coverage.

Narrow correction: use uncertain coverage when the generator cannot establish whether all relevant facts/functions/qualifications/uncertainties have been represented, or when it knows representation is incomplete. Explicitly say that faithfully representing a source ambiguity does not itself prove incomplete coverage; keep the ambiguity in uncertainties/association/timing fields and retain independent review. Never resolve uncertainty or invent a binding just to claim completeness. Keep the useful structured-content-versus-evidence-only instruction.

Add a paired authored control: a coverage claim plus fully represented source uncertainty retains its source/association review reason without automatically adding coverage uncertainty; an unestablished coverage case retains coverage uncertainty. These controls establish the existing representation distinction, not improved model generation or semantic success.

Other reviewed controls: finalized candidate passed 18 tests (11 owner, 7 independent). All eight full-body fixture measurements independently recompute, all 1,158 prior baseline files remain unchanged, and the owner handoff hashes match. Candidate approval awaits only this prompt-contract correction and its focused regression check. No live approval.
