# WA pass B output is not in git

`pass-B.jsonl` (sha256 `496c80f55428c4eb81a837c5671f7e194a2c7fd1f7385f5087978f644780198c`, 15874544 bytes, 1,992 label rows) is sealed and matches
`run.json` `passes[pass_B].output_sha256`. It isn't committed: 4,020 of its 9,400 evidence quotes
exceed 500 characters (the longest is 30,898), which would republish large spans of the original
notices. Rights decision 3 keeps originals internal and allows short excerpts only.

The sealed copy is in the primary's sealed pass store (`WA-pass-B/pass-B.jsonl`), outside git, next
to the originals. To validate locally, place it at this path. `validate.py --stage passes` then
checks its hash. Comparison outputs cap every copied quote at 200 characters.
