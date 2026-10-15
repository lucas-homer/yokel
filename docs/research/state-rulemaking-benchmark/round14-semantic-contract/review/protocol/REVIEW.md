# Primary integration of independent Fable review

Approved for offline runtime implementation of one experimental fresh-source inventory pilot. Paid dispatch still requires runtime verification, final bindings and native signed-job check.

Independent review: Claude Fable (actual claude-fable-5-1 / firstParty) through Claude.ai Max subscription bridge, preserved in claude-review/revised/REVIEW.md and READY.json. Fable found no material correctness blocker after the requested controls and inverse fixes. Codex independently verified local fixes. GPT implemented; GPT executed 24 owner tests and 12 Fable-designed/adapted tests. Original failures and protocol artifacts remain frozen.

Known limits remain: prose qualification loss is not structurally detectable; byte sizing does not establish output headroom; fiction controls overlap some generic prompt examples and do not establish extraction accuracy. The phrase 'Fixture data never enters prompt' is limited to new overflow/leakage controls; the main synthetic controls are authored roundtrip examples. Minor modality and actor conventions need postrun adjudication. No production or completeness claim follows.

The primary admits a single capacity/semantic diagnostic on the prospectively selected full source. Guarded request 29331 bytes is below 40000, output cap8192, one reservation200000000 plus prior1705990718 below2e9. No source/unit dropping, string clipping, repair, retry or fallback. If it fails, preserve the outcome and costs. Source-only Fable reference was frozen before protocol/provider-output exposure and never enters the request.
