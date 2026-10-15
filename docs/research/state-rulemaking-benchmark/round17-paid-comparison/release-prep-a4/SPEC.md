# release-prep-a4 — deltas from frozen release-prep

Copied offline preparation helpers now target adapter-r1-4. STAGE-MANIFEST
includes the amended recon-a4 payload/READY, A4 amendment and key attestation,
and the unchanged original design fixture closure. Reference pins come ONLY
from frozen release-prep/STAGE-MANIFEST.json; no reference content is opened.
Selected source-body pins come from sources-r2/READY.json, never body reads.

Unsigned drafts are regenerated from the current A4 manifest and pinned native
shim; exact native schema remains unchanged (no unsupported key-label metadata
field is added). Key label DocketClock is in adapter/evidence/READY metadata.
A3 timeouts and reservations/ceiling metadata remain unchanged.

Thirteen offline tests cover synthetic staging trees, paths/symlinks/hash drift,
exact proposal shape and budget/schema refusals. Synthetic staged final-release
files are test data, with no release/executor/runner commands invoked. The full
stage-layout test uses synthetic replacements for every reference/source body.
Run `<python> -I -S -B release-prep-a4/test_release_prep.py` on both interpreters.
See READY.json and _out logs. Final pins checked by adapter-r1-4/verify_ready.py.
