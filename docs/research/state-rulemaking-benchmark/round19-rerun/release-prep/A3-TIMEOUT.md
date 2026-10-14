# A3 — fit one cell inside the installed 1,800-second runner

Primary decision: POST response/read timeout **600 seconds**; signed job
`timeout_seconds = 1800`. The prior 900-second per-socket-operation setting
cannot establish the desired bound. Merely substituting 600 would still allow
five GETs of 600 seconds each and repeated trickle reads to extend indefinitely.
The smallest companion fix bounds GETs and total elapsed transport time.

r1.3 uses POSIX elapsed-time alarms in the main thread. Each request has one
absolute deadline, including DNS, TLS, writes, headers and bounded body reads.
TLS/connect/write gets 15 seconds. POST socket/read timeout is 600 seconds;
its total deadline is 615 seconds. Each key GET has a **15-second total**
deadline, including connection setup. No resend, retry, redirect or second POST
is introduced. Nested deadlines restore the earlier outer deadline without
extending it. Unrelated alarms and non-main-thread use refuse before transport.

Conservative normal-cell arithmetic:

- Key preflight: 15 s.
- POST: connect/TLS/write allowance 15 s + response/read allowance 600 s = 615 s.
- Reconciliation schedule: offsets **0, 60, 300, 900** s from POST resolution;
  the waits span 900 s, not 1,260 s.
- Four reconciliation GETs: 4 × 15 s = 60 s (conservatively added to all waits).
- Total: **15 + 615 + 900 + 60 = 1,590 s**.
- Remaining native margin: **1,800 − 1,590 = 210 s**.

Recovery is accounting-only. A marked/potentially dispatched pending cell gets
at most 900 + 4 × 15 = **960 s** of reads and then HALT; admission refuses before
any new source read/preflight/POST. Already consumed read slots are not repeated.
An unmarked reservation resolves at zero debit with no key reads; it cannot add
another reconciliation schedule before a new cell. Completed-cell recovery is
inert. Thus recovery plus a second paid-cell schedule is not additive.

Filesystem/import/provider-bootstrap overhead has no universal worst-case
completion bound. We do not claim that a stalled filesystem can finish cleanly.
The per-job native shim therefore arms a **1,740-second elapsed deadline before
config and host imports**, with immediate key-free process exit on expiry. That
allows 150 s for Python work, pin checks, receipts and ledger fsync on the normal
path, and retains 60 s before native process-group termination. Timeout can
leave a pending/torn ledger requiring primary-owned accounting recovery; it
never authorizes a resend. The outer native stage-job timeout includes op provider-resolution and
stage/payload manifest hashing before Python starts; identity has a separate
30-second subprocess bound outside that job clock. Initial token lookup is
also outside it and is not counted as Python cell time. For the timed stage, if bootstrap consumes the 60-second reserve,
clean completion is not guaranteed. The deployed native policy has no separately
proved bootstrap bound. Primary must verify bootstrap overhead below 60 s or
accept native timeout/HALT as the fail-closed outcome, rather than promise every
worst-case job finishes. The smallest further integration fix would be an
explicit bounded native bootstrap, a reviewed core change outside this task.

Offline tests verify arithmetic, actual local deadline interruption, nested
alarm restoration, fake HTTP framing, single POST, accounting recovery and the
CA store under both Python interpreters. No executor/provider was invoked.
