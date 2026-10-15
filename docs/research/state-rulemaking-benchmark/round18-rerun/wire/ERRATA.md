# Frozen DESIGN §4 clarification

The illustrative `Y = u.y[0] if u.y else None; if Y is not None` pseudocode
must not be read as permitting `y:[null]`. Under DESIGN §3 W3, `y` is exactly
`[]` or a singleton containing the closed deadline object `{c,z,b}`.
DESIGN §5 #25 prohibits normalization; accepting `[null]` would break the
wire inverse by returning `[]`. Both direct conversion and response validation
reject `[null]`. The empty array means non-deadline function, never unknown.

This erratum belongs to revision r16.w2. The frozen `design/` folder remains
unchanged; this clarifies its pseudocode rather than changing the response contract.
