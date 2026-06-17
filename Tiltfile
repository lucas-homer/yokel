# Tiltfile — the full-in-cluster inner loop for DocketClock (ADR 0009).
#
# Run (after `task dev-up`):  tilt up
# It builds our image, loads it into the k3d cluster, deploys the chart with local values, and
# live-updates the running container on source changes — without going through Argo (Argo manages
# the platform + the committed app; Tilt overrides the app workload during active development).

# allow_k8s_contexts('k3d-yokel')  # uncomment to guard against deploying to the wrong context

# Build the real image (the API, poller, and migration runner all run from it; the chart sets the
# command per workload). On a source change Tilt does a FULL rebuild + redeploy.
#
# NO live_update here (deliberate — see #28). We run `tsx` from source with no watch mode, so a
# live_update sync alone never re-reads the edited file. The old restart_container() step that bounced
# the process is DEPRECATED for k8s resources in current Tilt; and restart_process's entrypoint wrapper
# does not fit this chart, which runs ONE image with a different `command:` PER workload (api/poller/
# migrate) — a k8s `command:` overrides the image entrypoint, so the wrapper would be bypassed. The
# clean fast-reload path is `tsx watch` driven by values-local.yaml (chart change) — tracked in #28.
# A full rebuild is correct + reproducible; only per-edit latency is worse until #28 lands.
docker_build(
    'docketclock',
    context='.',
    dockerfile='apps/docketclock/Dockerfile',
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
