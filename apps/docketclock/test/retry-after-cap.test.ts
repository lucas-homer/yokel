/**
 * retry-after-cap.test.ts — proves the shared HTTP client CAPS a server-provided Retry-After sleep.
 *
 * The regs rate-limit stall: regulations.gov answers a burst over its ~1,000 req/hr quota with a 429 + a
 * LARGE Retry-After (minutes). Honored verbatim, one retry slept ~22 min and froze the whole poll cycle.
 * We still HONOR Retry-After (polite back-off) but cap it at MAX_RETRY_AFTER_MS so a huge/hostile value
 * can't wedge a cycle. This unit-tests retriableBackoffMs directly (pure, no network, no real timers):
 *   - a Retry-After BELOW the cap is honored verbatim (seconds → ms);
 *   - a Retry-After AT / ABOVE the cap clamps to MAX_RETRY_AFTER_MS;
 *   - absent / zero / negative / non-numeric Retry-After falls through to exponential back-off (capped 30s).
 *
 * Run: pnpm --filter @yokel/docketclock test
 */
import { MAX_RETRY_AFTER_MS, retriableBackoffMs } from "../src/sources/http.js";

let failures = 0;
const log: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  log.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

/** A retriable Response carrying (or omitting) a Retry-After header. */
const res429 = (retryAfter?: string) =>
  new Response("rate limited", {
    status: 429,
    headers: retryAfter === undefined ? {} : { "retry-after": retryAfter },
  });

// ── sanity: the cap is the value we documented (60s) ──────────────────────────────────────────────────
assert(
  "MAX_RETRY_AFTER_MS is 60s",
  MAX_RETRY_AFTER_MS === 60_000,
  `${MAX_RETRY_AFTER_MS}`,
);

// ── Retry-After BELOW the cap: honored verbatim (attempt is irrelevant when Retry-After is present) ─────
{
  const ms = retriableBackoffMs(res429("5"), 0);
  assert("Retry-After 5s → 5000ms (honored)", ms === 5_000, `${ms}`);
}
{
  const ms = retriableBackoffMs(res429("59"), 0);
  assert("Retry-After 59s → 59000ms (honored)", ms === 59_000, `${ms}`);
}

// ── Retry-After AT / ABOVE the cap: clamped to MAX_RETRY_AFTER_MS ───────────────────────────────────────
{
  const ms = retriableBackoffMs(res429("60"), 0);
  assert("Retry-After 60s → capped at 60000ms", ms === 60_000, `${ms}`);
}
{
  const ms = retriableBackoffMs(res429("90"), 0);
  assert("Retry-After 90s → capped at 60000ms", ms === 60_000, `${ms}`);
}
{
  // The real stall value: ~22 minutes. Pre-fix this slept 1320s; now it clamps to 60s.
  const ms = retriableBackoffMs(res429("1320"), 0);
  assert(
    "Retry-After 1320s (the ~22m stall) → capped at 60000ms",
    ms === 60_000,
    `${ms}`,
  );
}

// ── absent / degenerate Retry-After: falls through to exponential back-off (500ms·2^attempt, ≤30s) ──────
{
  const ms = retriableBackoffMs(res429(undefined), 0);
  assert(
    "no Retry-After, attempt 0 → 500ms (exponential)",
    ms === 500,
    `${ms}`,
  );
}
{
  const ms = retriableBackoffMs(res429(undefined), 3);
  assert(
    "no Retry-After, attempt 3 → 4000ms (exponential)",
    ms === 4_000,
    `${ms}`,
  );
}
{
  const ms = retriableBackoffMs(res429(undefined), 10);
  assert(
    "no Retry-After, attempt 10 → 30000ms (exponential cap)",
    ms === 30_000,
    `${ms}`,
  );
}
{
  const ms = retriableBackoffMs(res429("0"), 2);
  assert("Retry-After 0 → exponential (2000ms)", ms === 2_000, `${ms}`);
}
{
  const ms = retriableBackoffMs(res429("-5"), 2);
  assert("Retry-After negative → exponential (2000ms)", ms === 2_000, `${ms}`);
}
{
  const ms = retriableBackoffMs(res429("soon"), 2);
  assert(
    "Retry-After non-numeric → exponential (2000ms)",
    ms === 2_000,
    `${ms}`,
  );
}

console.log("\n=== retry-after-cap results ===");
console.log(log.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
