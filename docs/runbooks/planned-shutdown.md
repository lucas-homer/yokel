# Planned shutdown / restart — moving the Mac Mini

For a deliberate outage (moving house, hardware maintenance): how to stop the whole stack cleanly
and bring it back with one command. Written for the 2026-09 move; everything here is durable
knowledge, not one-off.

**The core fact:** the cluster and all state (CNPG PVCs, Vault raft + transit key, Grafana's DB)
live on the colima VM disk and **survive a colima stop**. `task cluster-restart` (infra/Taskfile.yml)
exists precisely to resume after that: it restarts colima + the k3d nodes, performs the
kubelet-serving-cert repair (node IPs shift across restarts → x509 errors on logs/exec/port-forward
otherwise), re-unseals the transit Vault (it boots sealed; the main Vault then auto-unseals against
it), and force-resyncs every ExternalSecret so apps go green immediately instead of after the 1h
refresh interval. Do NOT run `task dev-up` on an existing cluster — that path recreates; restart
RESUMES.

## Before unplugging (~10 minutes)

1. **Pause the dead-man check** in the healthchecks.io account. It pages on ping ABSENCE by design —
   an unpaused check will (correctly) alarm the entire time the Mini is in a box.
2. **Freshness check** — confirm the offsite safety net is current before the machine travels:
   - last nightly dump: `kubectl -n docketclock get jobs --sort-by=.metadata.creationTimestamp | tail -2`
   - WAL archiving healthy + last base backup: the Backups row on the Grafana DocketClock dashboard
     (or `kubectl -n docketclock get objectstore -o yaml | grep -i last`)
   - R2 mirror ran within the hour: `kubectl -n backups get jobs | tail -3`
   - If the Mini is lost/damaged in transit, `docs/runbooks/restore-from-offsite.md` rebuilds from R2.
3. **Graceful stop, in order:**
   ```sh
   k3d cluster stop yokel   # stops the nodes cleanly (etcd + postgres get SIGTERM, not a yank)
   colima stop              # stops the VM; PVC data persists on the VM disk
   ```
   then a normal macOS Shut Down. The demo dashboard (`node tools/data-showcase.mjs serve`, :8090)
   and any port-forwards die with the machine — nothing to do.

## While it's off

Nothing pages (Grafana is down and the dead-man is paused). launchd jobs (drill-cadence) simply
don't fire. **The ingest gap self-heals**: the FR/Regs poll cursors resume from their stored
positions and backfill the missed days on the first cycles after restart.

## After plugging in

1. Boot + auto-login. colima auto-starts (brew service) but the cluster does NOT — run:
   ```sh
   cd ~/dev/yokel/infra && task cluster-restart
   ```
   Wait for its ✅ line. (`task status` shows Argo apps + pods settling; pods re-race the DB
   briefly, then settle.)
   - _Optional zero-touch alternative:_ `task install-boot-recovery` installs a LaunchAgent that
     runs cluster-restart automatically after every boot. Note: installing it fires one
     cluster-restart immediately (brief node churn).
2. **Un-pause the healthchecks.io check.** Resumed pings are the machine-is-back signal.
3. **Expect a burst of self-resolving alert noise:**
   - Backup-staleness alerts (base >26h, nightly-cron >26h, R2 mirror >3h) fire until their jobs
     run again. Clear them fast by kicking the jobs instead of waiting for the schedules:
     ```sh
     kubectl -n docketclock create job --from=cronjob/docketclock-pg-dump manual-postmove-dump
     kubectl -n backups create job --from=cronjob/r2-mirror manual-postmove-mirror
     kubectl -n langfuse create job --from=cronjob/langfuse-db-dump manual-postmove-lfdump   # if its staleness alert fires too
     ```
   - The review-queue-rotting page returns if the queue is still unworked — that one is true, not noise.
   - First poller cycles show large `listed`/`ingested` counts (possibly `truncated=true` for a
     cycle or two) while the outage backlog ingests; dead-letter counts may tick up on the burst.
4. **Demo dashboard** (only if wanted): `nohup node tools/data-showcase.mjs serve >/tmp/showcase.log 2>&1 &`
   then `tailscale funnel 8090` — the tailscale serve/funnel _config_ persists across reboots, the
   backend process does not.
5. Sanity sweep: nodes Ready, all Argo apps Synced/Healthy, `vault-0` Ready (readiness = unsealed),
   poller heartbeat fresh, latest observation fetched-at recent once the first cycle lands.

## Failure modes seen before (why the restart task looks the way it does)

- `x509: certificate is valid for <old-ip>` on kubectl logs/exec — the kubelet cert issue;
  cluster-restart's per-node cert delete + solo restart is the deterministic fix (a plain
  `docker restart` of both nodes can SWAP IPs mid-regeneration and make it worse).
- Main Vault crashlooping on a 404 after restart — the transit Vault is sealed; cluster-restart
  unseals it first, then bounces `vault-0`.
- Argo apps Degraded with healthy pods for ~1h — stale `SecretSyncedError` on ExternalSecrets from
  the outage window; cluster-restart's force-sync annotation clears it immediately.
