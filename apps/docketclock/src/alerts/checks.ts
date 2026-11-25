/**
 * alerts/checks.ts — the cloud alert definitions, in code (the Mac mini's Grafana rules, ported).
 *
 * Delivery: healthchecks.io → its integrations (ntfy, email). Each check below is one healthchecks.io check, addressed by SLUG under
 * the project's ping key (https://hc-ping.com/<HEALTHCHECKS_PING_KEY>/<slug>). The poller evaluates every
 * rule at the END of its own cycle, while the database is already awake (alerts/evaluate.ts), and pings
 * each check: success, `/fail` (pages now), or `/log` (recorded, no state change). healthchecks.io pages on
 * a `/fail` AND on silence past `timeout + grace`, so a dead poller, Cloudflare outage or Neon outage pages
 * through the `poller` check with nothing of ours running. scripts/sync-healthchecks.ts applies these
 * definitions (period, grace, description) from CI; nothing is configured by hand except the project's
 * integrations themselves.
 *
 * Rules with a long timeout only page on an explicit `/fail`: while the poller is down they stay quiet and
 * the `poller` check speaks for them (one page per outage, not five).
 */
export interface HealthcheckDef {
  slug: string;
  name: string;
  /** Expected seconds between pings. */
  timeout: number;
  /** Extra seconds of silence tolerated before healthchecks.io pages. */
  grace: number;
  desc: string;
}

const MIN = 60;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

export const CHECKS = {
  poller: {
    slug: "docketclock-poller",
    name: "DocketClock poller",
    timeout: 15 * MIN,
    // 60m, not 30m: one slow-but-healthy cycle (e.g. a slow regulations.gov pass) can block two cron slots;
    // 30m paged a DOWN/UP pair for that in Nov 2026. 75m of silence is still an unambiguous outage.
    grace: 60 * MIN,
    desc:
      "Pinged after every poll cycle that ran (Mini: 'Poller stalled'). Silence for 75m = the cron, the " +
      "container, Cloudflare or Neon is down. /fail = the cycle itself failed (lock or DB lost).",
  },
  api: {
    slug: "docketclock-api",
    name: "DocketClock API readiness",
    timeout: 1 * HOUR,
    grace: 30 * MIN,
    desc:
      "The poller GETs the API's /readyz once an hour (Mini: 'API readiness down'). /fail = non-200 or " +
      "unreachable. Also goes silent if the poller is down (see the poller check).",
  },
  passes: {
    slug: "docketclock-passes",
    name: "DocketClock poll pass failing",
    timeout: 1 * DAY,
    grace: 1 * HOUR,
    desc:
      "/fail when one pass failed in 3+ cycles over the last hour while the cycle itself kept running " +
      "(Mini: 'Poll pass failing'). The ping body names the pass and its last error.",
  },
  llm: {
    slug: "docketclock-llm",
    name: "DocketClock LLM adjudicator errors",
    timeout: 1 * DAY,
    grace: 1 * HOUR,
    desc:
      "/fail when more than 3 AI Gateway calls failed in one cycle (Mini: 'LLM adjudicator error spike'): " +
      "the provider is erroring, out of credits, or the token is wrong.",
  },
  accuracy: {
    slug: "docketclock-accuracy",
    name: "DocketClock accuracy (HIGH < 95% over 90d)",
    timeout: 1 * DAY,
    grace: 1 * HOUR,
    desc:
      "/fail when HIGH-confidence deadlines were correct < 95% of the time over 90 days on a sample of " +
      "20+ (Mini: 'Accuracy degraded'). The product's headline promise.",
  },
  review: {
    slug: "docketclock-review",
    name: "DocketClock review queue needs you",
    timeout: 1 * DAY,
    grace: 1 * HOUR,
    desc:
      "/fail while windows are escalated to a human or the oldest open conflict is over 7 days old " +
      "(Mini: 'Escalations pending', 'Review queue rot'). Pages once when work starts waiting and " +
      "again when the queue is clear.",
  },
} as const satisfies Record<string, HealthcheckDef>;

export type CheckKey = keyof typeof CHECKS;

/** Thresholds, ported from infra/argocd/apps/platform-grafana.yaml. */
export const RULES = {
  passFailuresPerHour: 3,
  llmErrorsPerCycle: 3,
  accuracyBar: 0.95,
  accuracyMinSample: 20,
  reviewRotSeconds: 7 * DAY,
} as const;
