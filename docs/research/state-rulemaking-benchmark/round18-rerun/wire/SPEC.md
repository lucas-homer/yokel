# r16.w2.2 / r16.e3

Copied from R16 protocol-w2-1. Only wire.py lines 1, 15–16 and the added prompt
line 318 change. A5 is appended verbatim to both profile prompts assembled by
build(). Response/schema/codec/validator code and dependency pins are unchanged.
`../_out/wire.diff` and test_r18.py prove the exact allowed text transformation.

The R17 S1 regression reads content.body and reconstructs source from plan.json,
merges unit 51's two if L leaves in memory, removes the redundant link/leaf,
and validates against a new R18 plan. Original still fails role_cardinality.
No reference scoring or repaired output publication occurs.

Existing tests are adapted only for frozen sibling paths and A5 request sizing.
The frozen independent suite retains its pre-existing single expected source
envelope assertion failure (54/55); no unexpected failure is permitted.
