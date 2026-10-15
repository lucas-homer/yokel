# Live staging disposition (primary, 2026-10-14)
- STAGE-MANIFEST.json now holds the live manifest (167 files, content ID 47c42595...). The prospective manifest is kept as STAGE-MANIFEST.prospective.json.
- test_a4_manifest_pins_new_authorities_and_inherits_reference_hashes fails by design. The live manifest adds exactly one reference-folder file, reference/ACCEPTANCE.json (the primary's P6 acceptance wrapper, which re-pins the E7 freeze unchanged). Verified: 0 frozen reference entries missing, 0 changed, 0 non-reference entries changed or removed. The other 20 tests pass.
