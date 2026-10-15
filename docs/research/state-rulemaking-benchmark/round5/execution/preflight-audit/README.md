# Round 5 mechanical preflight — complete

See REPORT.md for results and limitations. audit.py --collector-ready verifies strict manifest/hash/path/page-tree/native-byte plumbing, versions, freezes and the explicit primary ledger exception. labeler_inputs.py --collector-ready can publish the minimal inventory before broader preflight after checking the primary-signaled READY hashes and mechanical input/image identity. The scripts require the explicit collector-ready flag; default invocation reads no fresh files.

The already published labeler-inputs.json is fixed for independent labeling. Do not regenerate or modify it while labels are being frozen. Native text and substantive collector assertions are never copied to this inventory. Earlier rounds, frozen implementation and collected sources are not edited.
