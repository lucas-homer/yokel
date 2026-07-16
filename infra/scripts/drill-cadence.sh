#!/usr/bin/env bash
# drill-cadence.sh — the drill-cadence enforcer, run MONTHLY by the cc.rostr.yokel.drill-cadence
# LaunchAgent (install with `task install-drill-cadence`). Turns the runbook's documented cadence
# (Drill A monthly, alert drill quarterly, Drill B semi-annually) from a discipline into a page:
#
#   every month     → RUN Drill A (`task drill-pitr`, automated + non-destructive) and push the
#                     result to the ntfy alert topic — FAIL at high priority with the output tail,
#                     PASS as a quiet note (which doubles as "the scheduler itself is alive")
#   Jan/Apr/Jul/Oct → push a REMINDER for the quarterly alert fire drill (`task alert-drill`) —
#                     it cannot be automated: a human must confirm the page reached a phone
#   Jan/Jul         → push a REMINDER for Drill B (cold restore from R2; ~2h, runbook-driven)
#
# PAGING PATH: the same ntfy topic Grafana alerts use (ALERTING_NTFY_URL from the grafana-alerting
# Secret). The URL is cached to ~/.config/yokel/ntfy-url (0600) after every successful read so a
# month where the CLUSTER is broken can still page "drill could not run" — same dev-acceptable
# hygiene tier as the vault-root-token Secret: whoever can read the topic can read/spoof alerts.
# If both the Secret and the cache are unavailable, we log and exit 1 (the LaunchAgent log is the
# trail; a cluster down that long has already paged via the healthchecks.io dead-man's switch).
#
# ENVIRONMENT: LaunchAgents start with a SPARSE environment, so PATH/HOME are set explicitly (same
# as boot-cluster-restart.sh). Output goes to stdout/err; the LaunchAgent redirects it to
# ~/Library/Logs/yokel-drill-cadence.log. Idempotent per run: a manual invocation any day of the
# month simply runs the same checks (drill-pitr is safe to re-run — non-destructive by construction).
set -uo pipefail

export HOME="${HOME:-/Users/home}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

INFRA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CACHE_DIR="$HOME/.config/yokel"
CACHE_FILE="$CACHE_DIR/ntfy-url"

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*"; }

# ── resolve the ntfy URL: Secret first (and refresh the cache), cache as the degraded path ──────
NTFY_URL=$(kubectl -n observability get secret grafana-alerting \
  -o jsonpath='{.data.ALERTING_NTFY_URL}' 2>/dev/null | base64 -d || true)
case "$NTFY_URL" in
  # Both placeholder shapes seed-alerting-secrets.sh's is_placeholder() knows — do not cache,
  # do not "page" a black hole.
  *127.0.0.1*|*PLACEHOLDER*) NTFY_URL="" ;;
esac
if [ -n "$NTFY_URL" ]; then
  mkdir -p "$CACHE_DIR"
  umask 177
  printf '%s' "$NTFY_URL" > "$CACHE_FILE"
  umask 022
elif [ -r "$CACHE_FILE" ]; then
  NTFY_URL=$(cat "$CACHE_FILE")
  log "WARN: grafana-alerting Secret unreachable — paging via the cached ntfy URL"
fi
if [ -z "$NTFY_URL" ]; then
  log "FAIL: no ntfy URL (Secret unreachable/placeholder, no cache) — cannot page. Seed with"
  log "      scripts/seed-alerting-secrets.sh; a fully-down cluster pages via the dead-man's switch."
  exit 1
fi

push() { # $1 priority ($NTFY_URL never on argv beyond curl itself; topic == secret)
  local priority=$1 title=$2 body=$3
  # The seeded URL carries ?template=grafana (Grafana's contact point POSTs JSON webhooks);
  # ntfy 400s a plain-text body when templating is enabled, so publish to the bare topic URL.
  curl -fsS -m 15 -H "Title: $title" -H "Priority: $priority" -H "Tags: stopwatch" \
    -d "$body" "${NTFY_URL%%\?*}" >/dev/null 2>&1 || log "WARN: ntfy push failed ($title)"
}

# ── monthly: actually RUN Drill A ────────────────────────────────────────────────────────────────
log "=== drill-cadence: running Drill A (task drill-pitr) ==="
DRILL_OUT=$(mktemp)
if (cd "$INFRA_DIR" && task drill-pitr) >"$DRILL_OUT" 2>&1; then
  log "Drill A PASS"
  push default "Drill A (scratch PITR): PASS" \
    "Monthly restore drill passed on $(date '+%Y-%m-%d'). Log: ~/Library/Logs/yokel-drill-cadence.log"
else
  code=$?
  log "Drill A FAIL (exit $code) — paging"
  # The tail is where drill-pitr's assertion/abort messages land; 12 lines fits an ntfy card.
  push high "Drill A (scratch PITR): FAIL" \
    "task drill-pitr exited $code on $(date '+%Y-%m-%d'). Last output:
$(tail -n 12 "$DRILL_OUT")"
fi
cat "$DRILL_OUT"; rm -f "$DRILL_OUT"

# ── quarterly + semi-annual reminders (the drills a human must drive) ────────────────────────────
month=$(date '+%m')
case "$month" in
  01|04|07|10)
    log "quarter month — pushing alert-drill reminder"
    push default "Quarterly alert fire drill due" \
      "Run from infra/: 'task alert-drill' (poller stalled, ~30m) or 'task alert-drill -- ingest' (~90m). Log the PASS date in infra/README.md." ;;
esac
case "$month" in
  01|07)
    log "semi-annual month — pushing Drill B reminder"
    push default "Semi-annual Drill B due (cold restore from R2)" \
      "The full 'Mini died' rehearsal (~2h): docs/runbooks/restore-from-offsite.md. Also due before any cloud cutover." ;;
esac

log "=== drill-cadence done ==="
