#!/usr/bin/env bash
# boot-cluster-restart.sh — one-shot post-boot cluster recovery, run by the cc.rostr.yokel.boot-recovery
# LaunchAgent at login (the mini auto-logs-in as `home`; install it with `task install-boot-recovery`).
#
# WHY THIS EXISTS: colima now auto-starts as a brew service, but colima being up does NOT make the k3d
# cluster healthy. Across a reboot the k3d node containers are stopped, their kubelet SERVING certs are
# stale (issued for the pre-reboot docker IPs), and the persistent transit Vault comes up SEALED. So a bare
# reboot leaves a broken cluster until someone SSHes in and runs `task cluster-restart` by hand (exactly
# what happened the morning the mini auto-updated). This wrapper waits for colima/docker to be ready, then
# runs that same task so the cluster self-heals unattended.
#
# ENVIRONMENT: LaunchAgents start with a SPARSE environment, so PATH/HOME are set explicitly — Homebrew
# bins live in /opt/homebrew (Apple Silicon) and kubectl in /usr/local/bin. All output goes to stdout/err;
# the LaunchAgent redirects it to ~/Library/Logs/yokel-boot-recovery.log (single writer, no interleaving).
# Idempotent: `task cluster-restart` is safe to re-run, so a manual run or a double-fire does no harm.
set -uo pipefail

export HOME="${HOME:-/Users/home}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# infra/ — this script lives in infra/scripts/, and `task cluster-restart` must run from the Taskfile dir.
INFRA_DIR="$(cd "$(dirname "$0")/.." && pwd)"

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*"; }

log "=== boot-recovery start (infra=$INFRA_DIR) ==="

# The colima brew-service agent and THIS agent both start at login with no guaranteed order — wait for
# colima + a responsive docker before handing off. Bounded (~5 min) so a genuinely-down colima can't hang
# forever; cluster-restart will itself `colima start` if we fall through without it.
ready=0
for i in $(seq 1 60); do
  if colima status >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    ready=1
    log "colima + docker ready after ~$((i * 5))s"
    break
  fi
  sleep 5
done
[ "$ready" = "1" ] || log "WARN: colima/docker not ready after 300s — running cluster-restart anyway (it will start colima)"

cd "$INFRA_DIR" || {
  log "FATAL: cannot cd to $INFRA_DIR"
  exit 1
}

log "running: task cluster-restart"
task cluster-restart
rc=$?
if [ "$rc" = "0" ]; then
  log "=== boot-recovery OK ==="
else
  log "=== boot-recovery FAILED (rc=$rc) — SSH in and run 'task cluster-restart' manually ==="
fi
exit "$rc"
