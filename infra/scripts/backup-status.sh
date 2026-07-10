#!/usr/bin/env bash
# backup-status.sh — one-shot backup freshness report (backups PR-5, plans/backups-restore-drill.md).
# Pure kubectl reads, no pods spawned, nothing mutated:
#   - base backups / PITR window : barman ObjectStore CRs (.status.serverRecoveryWindow — with plugin
#     backups the Cluster status backup fields are EMPTY, the PR-2 discovery)
#   - newest WAL                 : pg_stat_archiver on each cluster's current primary
#   - dumps / vault snapshot / R2 mirror : CronJob .status.lastSuccessfulTime (job success == upload
#     done — the same signal the Grafana staleness alerts watch via kube-state-metrics)
set -euo pipefail

echo "=== Backup status — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo
echo "--- PITR (barman ObjectStores: recovery window per server) ---"
kubectl get objectstores.barmancloud.cnpg.io -A -o json | python3 -c '
import json, sys
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

def age(ts):
    d = now - datetime.fromisoformat(ts.replace("Z", "+00:00"))
    h = d.total_seconds() / 3600
    return f"{h:.1f}h ago"

items = json.load(sys.stdin)["items"]
if not items:
    print("no ObjectStores found")
for os_ in items:
    ns, name = os_["metadata"]["namespace"], os_["metadata"]["name"]
    window = (os_.get("status") or {}).get("serverRecoveryWindow") or {}
    if not window:
        print(f"{ns}/{name}: NO recovery window reported")
    for server, w in window.items():
        first, last = w.get("firstRecoverabilityPoint"), w.get("lastSuccessfulBackupTime")
        print(f"{ns}/{name} [{server}]")
        print(f"  window opens : {first} ({age(first)})" if first else "  window opens : MISSING")
        print(f"  last base    : {last} ({age(last)})" if last else "  last base    : MISSING")
'

echo
echo "--- WAL archiving (pg_stat_archiver on each current primary) ---"
for ns_cluster in docketclock/docketclock-pg langfuse/langfuse-db; do
  ns=${ns_cluster%/*} cluster=${ns_cluster#*/}
  primary=$(kubectl -n "$ns" get cluster "$cluster" -o jsonpath='{.status.currentPrimary}')
  kubectl -n "$ns" exec "$primary" -c postgres -- psql -U postgres -Atc \
    "SELECT '$ns/$cluster: last WAL ' || COALESCE(last_archived_wal, 'NONE')
         || ' at ' || COALESCE(last_archived_time::text, 'NEVER')
         || CASE WHEN last_failed_time > last_archived_time
                 THEN '  ** LAST ATTEMPT FAILED at ' || last_failed_time || ' **'
                 ELSE '' END
     FROM pg_stat_archiver"
done

echo
echo "--- CronJobs (last successful run) ---"
printf "%-32s %-12s %s\n" "CRONJOB" "SCHEDULE" "LAST SUCCESS"
for ns_job in docketclock/docketclock-pg-dump langfuse/langfuse-db-dump vault/vault-snapshot backups/r2-mirror; do
  ns=${ns_job%/*} job=${ns_job#*/}
  IFS=$'\t' read -r sched last < <(kubectl -n "$ns" get cronjob "$job" \
    -o jsonpath='{.spec.schedule}{"\t"}{.status.lastSuccessfulTime}{"\n"}')
  printf "%-32s %-12s %s\n" "$ns/$job" "$sched" "${last:-NEVER}"
done

echo
echo "(offsite = r2-mirror above: every MinIO bucket syncs to R2 1:1 hourly; retention is source-side)"
