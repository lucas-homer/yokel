# Tiltfile — the full-in-cluster inner loop for DocketClock (ADR 0009).
#
# STATUS: ready for Phase 1, when apps/docketclock has a real server + Dockerfile. Until then the
# chart runs a placeholder image and this file is not wired into `task dev-up`.
#
# Run (after `task dev-up`):  tilt up
# It builds our image, loads it into the k3d cluster, deploys the chart with local values, and
# live-updates the running container on source changes — without going through Argo (Argo manages
# the platform + the committed app; Tilt overrides the app workload during active development).

# allow_k8s_contexts('k3d-yokel')  # uncomment to guard against deploying to the wrong context

# TODO(phase-1): build the real image once apps/docketclock has a Dockerfile + Fastify server.
# docker_build(
#     'docketclock',
#     context='.',
#     dockerfile='apps/docketclock/Dockerfile',
#     live_update=[sync('apps/docketclock/src', '/app/apps/docketclock/src')],
# )

k8s_yaml(helm(
    'charts/docketclock',
    name='docketclock',
    namespace='docketclock',
    values=['charts/docketclock/values.yaml', 'charts/docketclock/values-local.yaml'],
))

k8s_resource('docketclock', port_forwards=['8088:80'])
