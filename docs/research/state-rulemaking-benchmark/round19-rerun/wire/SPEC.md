# r16.w2.3 / r16.e4

Copy of R18 wire; only revision/envelope labels and the conditional A7 append
change in wire.py. A7 plus newline follows A5 only for opaque. Full prompt is
byte-identical to R18; schema/codec/validator/guards/dependency pins are fixed.
test_r18.py retains the A5 mechanical regression and tests the exact allowed
R18-to-R19 source transformation. test_a7.py checks all three frozen sources-r2
under both profiles, comparing every body field and reporting guarded sizes.
No output is scored. The independent suite retains its one historical expected
source-envelope assertion failure (54/55); no unexpected failure is permitted.
