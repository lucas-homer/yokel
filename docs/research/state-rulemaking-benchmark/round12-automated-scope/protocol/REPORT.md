# Protocol revision report

READY for re-review: bounded lossless C scope_wire transport replaces B full-C input. Initial protocol/source bindings preserved under revisions/initial/. Raw/canonical C and all response schemas stay unchanged; same source, candidate, A, settings and guard.

54 static checks, 8 codec tests and 15 exact sizing roundtrips pass. Revised modest32=36337 guarded bytes and modest40=39369 fit; modest48=42401 still overflows and must stop. RESOLUTION.md documents reproduction, invariants and limits. No provider calls or live runtime; independent reference not read.
