# Stopped collection: local transport failure

The authorized queue stopped after three consecutive operational failures in completion order. A fourth unit was already in flight and also failed. Original attempt captures in A01–A04 and results.json are preserved.

All four phase-one upload-instruction requests succeeded. No HTTP upload and no final parse request occurred. Sixteen units were never submitted. Returned phase-one responses did not report credits; actual credits remain unknown. The stop is not evidence of Firecrawl availability, parse accuracy, or PDF handling.

Root cause: the harness assumed plain-pipe exec_command would return a writable live stdin session. It instead closed stdin immediately. The upload helper exited with JSONDecodeError at json.loads(sys.stdin.readline()), before constructing or sending any HTTP request; the harness then threw `Upload transfer did not open input pipe`. A credential-free reproduction returned exit code 1 and no session_id. The same incorrect launch assumption affected the exact-Markdown helper, which had not yet run.

Local repair: both helper launches now request a PTY. transient_stdin.py disables ECHO, ECHONL and ICANON before announcing stdin_ready. The harness waits for that marker before transmitting any payload, preventing credential echo and canonical line truncation. Signed instructions remain transient. No provider call or upload was used to test the repair.

Verification: a 99,019-byte synthetic UTF-8 Markdown payload with no terminal newline arrived byte-for-byte and was not echoed. A synthetic metadata payload over 10 KB was consumed without echo; its deliberately non-HTTPS URL triggered the pre-HTTP guard. Node syntax validation passed. All frozen source/reference file hashes and the freeze checksum still match; details are in local-validation.json.

Recovery is supported by proof of a pre-job local failure, but the authorized stop rule has already triggered. No vendor queue was resumed. Any subsequent authorized recovery must preserve the original attempts and account separately for setup requests, upload attempts and final parse requests. The current harness intentionally refuses existing result directories.
