# Tiltfile — the full-in-cluster inner loop for DocketClock (ADR 0009).
#
# Run (after `task dev-up`):  tilt up
# It builds our image, loads it into the k3d cluster, deploys the chart with local values, and
# live-updates the running container on source changes — without going through Argo (Argo manages
# the platform + the committed app; Tilt overrides the app workload during active development).

# allow_k8s_contexts('k3d-yokel')  # uncomment to guard against deploying to the wrong context

# Build the real image (the API, poller, and migration runner all run from it; the chart sets the
# command per workload). HOT-RELOAD (#28): live_update sync()s edited source STRAIGHT into the running
# container, and the local overlay (values-local.yaml) runs api/poller under `tsx watch`, which re-reads
# the synced file and restarts the process — true hot reload with NO deprecated restart_container() and
# NO restart_process entrypoint wrapper (which couldn't serve this chart's three distinct per-workload
# `command:`s anyway: a k8s command overrides the image entrypoint, bypassing the wrapper). Only the two
# source trees are synced; a change OUTSIDE them (package.json, lockfile, Dockerfile, migrations/) is not
# matched by a sync step, so Tilt falls back to a full rebuild + redeploy — exactly what those need.
docker_build(
    'docketclock',
    context='.',
    dockerfile='apps/docketclock/Dockerfile',
    live_update=[
        # tsx runs from source (no dist/); sync the TS the runtime actually executes + the contract it
        # imports. Container paths mirror the Dockerfile COPYs under WORKDIR /app.
        sync('apps/docketclock/src', '/app/apps/docketclock/src'),
        sync('packages/contracts/src', '/app/packages/contracts/src'),
    ],
)

k8s_yaml(helm(
    'charts/docketclock',
    name='docketclock',
    namespace='docketclock',
    values=['charts/docketclock/values.yaml', 'charts/docketclock/values-local.yaml'],
))

# API workload — port-forward the Fastify server (container 8080) to localhost:8088.
k8s_resource('docketclock', port_forwards=['8088:8080'])
# Background poller workload (no port-forward — it serves no HTTP).
k8s_resource('docketclock-poller')
# Nightly pg_dump CronJob (backups PR-3) — a CronJob has no pods until its schedule fires, so the
# default runtime-readiness gate can never pass and `tilt ci` times out (30m). Gate on apply only.
k8s_resource('docketclock-pg-dump', pod_readiness='ignore')
