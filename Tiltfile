# Tiltfile — the full-in-cluster inner loop for DocketClock (ADR 0009).
#
# Run (after `task dev-up`):  tilt up
# It builds our image, loads it into the k3d cluster, deploys the chart with local values, and
# live-updates the running container on source changes — without going through Argo (Argo manages
# the platform + the committed app; Tilt overrides the app workload during active development).

# allow_k8s_contexts('k3d-yokel')  # uncomment to guard against deploying to the wrong context

# Build the real image (the API, poller, and migration runner all run from it; the chart sets the
# command per workload). We run via tsx from source, so a live_update sync of the TS source + a
# container restart picks up edits without a full rebuild.
docker_build(
    'docketclock',
    context='.',
    dockerfile='apps/docketclock/Dockerfile',
    live_update=[
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
