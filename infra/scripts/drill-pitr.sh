#!/usr/bin/env bash
# drill-pitr.sh — Drill A: automated, repeatable, non-destructive scratch PITR (backups PR-6,
# plans/backups-restore-drill.md). Cadence: MONTHLY (see docs/runbooks/restore-from-offsite.md).
#
# What it does, end to end:
#   1. headroom gate    — refuse to start if the (single) node is already memory-tight
#   2. namespace `dr`   — ExternalSecret (MinIO creds) + a read-only ObjectStore CR + a 1-instance
#                         Cluster `docketclock-pg-drill` bootstrapping `recovery` from the LIVE
#                         backup store at targetTime = now - 5m
#   3. assertions       — row counts within tolerance of live, append-only trigger still rejects
#                         an UPDATE, max(fetched_at) <= targetTime, schema_migrations parity
#   4. teardown         — deletes the `dr` namespace (trap'd, runs on failure too; KEEP_DRILL=1 keeps
#                         the wreckage for inspection)
#
# Non-destructive by construction: the drill Cluster has NO backup/plugin stanza, so it never
# archives — the live store is only ever READ. Env knobs: KEEP_DRILL=1, SKIP_HEADROOM=1.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NS=dr
DRILL=docketclock-pg-drill
LIVE_NS=docketclock
LIVE=docketclock-pg

# Same image as the live cluster — recovery replays its WAL (read from the chart, single source).
IMAGE=$(awk '/^  imageName:/ {gsub(/"/,"",$2); print $2; exit}' "$REPO_ROOT/charts/docketclock/values.yaml")
[ -n "$IMAGE" ] || { echo "could not read postgres.imageName from values.yaml"; exit 1; }

# now - 5m, portable across BSD (macOS host) and GNU date.
TARGET=$(date -u -v-5M '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

echo "=== Drill A: scratch PITR of $LIVE_NS/$LIVE @ $TARGET (image $IMAGE) ==="

# ── 1. headroom gate ─────────────────────────────────────────────────────────────────────────────
if [ "${SKIP_HEADROOM:-}" != "1" ]; then
  mem_pct=$(kubectl top node --no-headers 2>/dev/null | awk '{gsub(/%/,"",$5); print $5; exit}') || mem_pct=""
  if [ -n "$mem_pct" ]; then
    if [ "$mem_pct" -gt 85 ]; then
      echo "ABORT: node memory at ${mem_pct}% (>85%) — no headroom for a drill Postgres (SKIP_HEADROOM=1 to override)"
      exit 1
    fi
    echo "headroom OK: node memory at ${mem_pct}%"
  else
    echo "WARN: kubectl top unavailable (metrics-server?) — skipping headroom gate"
  fi
fi

# ── teardown (trap'd so failures clean up too) ───────────────────────────────────────────────────
cleanup() {
  code=$?
  if [ "${KEEP_DRILL:-}" = "1" ]; then
    echo "KEEP_DRILL=1 — leaving namespace '$NS' in place"
  else
    echo "tearing down namespace '$NS'..."
    kubectl delete namespace "$NS" --ignore-not-found --wait=true >/dev/null || true
  fi
  exit $code
}
trap cleanup EXIT

# ── 2. scratch recovery cluster ──────────────────────────────────────────────────────────────────
echo "creating namespace + ExternalSecret + ObjectStore + recovery Cluster..."
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl apply -f - <<EOF >/dev/null
# MinIO creds for the drill's barman sidecar — same source path + fixed-key mapping as the live
# cnpg-backup-creds (the langfuse/backup.yaml shape); vault-backend is cluster-scoped so it works here.
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: cnpg-backup-creds
  namespace: $NS
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: cnpg-backup-creds
    creationPolicy: Owner
  data:
    - secretKey: ACCESS_KEY_ID
      remoteRef: { key: backups/minio, property: root_user }
    - secretKey: ACCESS_SECRET_KEY
      remoteRef: { key: backups/minio, property: root_password }
---
# Read-only view of the LIVE backup store (same bucket); no retentionPolicy — the live ObjectStore
# owns retention, this one only feeds recovery reads.
apiVersion: barmancloud.cnpg.io/v1
kind: ObjectStore
metadata:
  name: docketclock-pg-store
  namespace: $NS
spec:
  configuration:
    endpointURL: http://minio.backups.svc:9000
    destinationPath: s3://cnpg-docketclock/
    s3Credentials:
      accessKeyId:
        name: cnpg-backup-creds
        key: ACCESS_KEY_ID
      secretAccessKey:
        name: cnpg-backup-creds
        key: ACCESS_SECRET_KEY
  instanceSidecarConfiguration:
    resources:
      requests:
        cpu: 25m
        memory: 64Mi
      limits:
        memory: 256Mi
---
# The drill Cluster: recovery bootstrap at the PITR target, NO backup/plugin stanza (never archives —
# the live store stays read-only). 256Mi limit per the plan's headroom budget.
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: $DRILL
  namespace: $NS
spec:
  instances: 1
  imageName: $IMAGE
  storage:
    size: 1Gi
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      memory: 256Mi
  bootstrap:
    recovery:
      source: origin
      recoveryTarget:
        targetTime: "$TARGET"
  externalClusters:
    - name: origin
      plugin:
        name: barman-cloud.cloudnative-pg.io
        parameters:
          barmanObjectName: docketclock-pg-store
          serverName: $LIVE
EOF

echo "waiting for ExternalSecret to sync..."
kubectl -n "$NS" wait externalsecret/cnpg-backup-creds --for=condition=Ready --timeout=120s >/dev/null

echo "waiting for recovery (up to 15m)..."
if ! kubectl -n "$NS" wait cluster/"$DRILL" \
    --for=jsonpath='{.status.phase}'='Cluster in healthy state' --timeout=900s >/dev/null; then
  echo "RECOVERY DID NOT CONVERGE — status + recent events:"
  kubectl -n "$NS" get cluster "$DRILL" -o jsonpath='{.status.phase}: {.status.phaseReason}{"\n"}' || true
  kubectl -n "$NS" get events --sort-by=.lastTimestamp | tail -15 || true
  exit 1
fi
echo "drill cluster healthy."

# ── 3. assertions ────────────────────────────────────────────────────────────────────────────────
psql_live()  { kubectl -n "$LIVE_NS" exec "$(kubectl -n "$LIVE_NS" get cluster "$LIVE" -o jsonpath='{.status.currentPrimary}')" -c postgres -- psql -U postgres -d docketclock -Atc "$1"; }
psql_drill() { kubectl -n "$NS" exec "$DRILL-1" -c postgres -- psql -U postgres -d docketclock -Atc "$1"; }

fail=0
for t in observations participation_windows adjudications schema_migrations; do
  live_n=$(psql_live "SELECT count(*) FROM $t")
  drill_n=$(psql_drill "SELECT count(*) FROM $t")
  # Recovered-at-(now-5m) counts must not EXCEED live, and must be within tolerance below it
  # (live keeps growing; 5% or 10 rows, whichever is larger, covers a busy poller window).
  tol=$(( live_n / 20 )); [ "$tol" -lt 10 ] && tol=10
  if [ "$drill_n" -le "$live_n" ] && [ $(( live_n - drill_n )) -le "$tol" ]; then
    echo "PASS  $t: drill=$drill_n live=$live_n (tol $tol)"
  else
    echo "FAIL  $t: drill=$drill_n live=$live_n (tol $tol)"; fail=1
  fi
done

# Append-only trigger survived recovery: an UPDATE on the observation log must be REJECTED.
if [ "$(psql_drill "SELECT count(*) FROM observations")" -gt 0 ]; then
  if psql_drill "UPDATE observations SET parser_version = parser_version WHERE observation_id = (SELECT observation_id FROM observations LIMIT 1)" >/dev/null 2>&1; then
    echo "FAIL  append-only: UPDATE on observations SUCCEEDED (trigger lost in recovery!)"; fail=1
  else
    echo "PASS  append-only: UPDATE on observations rejected"
  fi
else
  echo "WARN  append-only: observations empty, trigger check skipped"
fi

# PITR consistency: nothing in the recovered log postdates the target.
if [ "$(psql_drill "SELECT coalesce(max(fetched_at) <= '$TARGET'::timestamptz, true) FROM observations")" = "t" ]; then
  echo "PASS  pitr-target: max(fetched_at) <= $TARGET"
else
  echo "FAIL  pitr-target: recovered rows postdate the target"; fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "=== Drill A: FAILED ==="
  exit 1
fi
echo "=== Drill A: PASSED (teardown follows) ==="
