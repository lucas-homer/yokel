# Rebuilds the pinned MinIO server / mc binaries from their upstream source tags.
#
# Why: upstream stopped publishing free images. Docker Hub minio/minio + minio/mc are gone, quay.io
# requires auth, and dl.min.io returns 410. On 2026-10-15 a DiskPressure outage made the kubelet
# GC the cached copies, and nothing could re-pull them. The github.com/minio repos are archived but
# the release tags are still readable, so we build the SAME versions (same on-disk format, same
# behavior) and serve them from yokel-registry, which survives node image GC.
#
# Build via `cd infra && task images-minio` (pushes to localhost:5050 = yokel-registry:5000 in-cluster).
#
# REPO=minio → server image (ENTRYPOINT minio; the StatefulSet passes `server /data ...` as args).
# REPO=mc    → client image (ENTRYPOINT mc; the backup CronJobs override command with `sh -c`, so the
#              runtime image MUST keep a shell — hence alpine, not scratch/distroless).
ARG GO_VERSION=1.24
FROM golang:${GO_VERSION}-alpine AS build
ARG REPO
ARG TAG
RUN apk add --no-cache git
RUN git clone --depth 1 --branch "${TAG}" "https://github.com/minio/${REPO}.git" /src
WORKDIR /src
ENV CGO_ENABLED=0
RUN go build -trimpath -o "/out/${REPO}" .

FROM alpine:3.22
ARG REPO
ARG TAG
RUN apk add --no-cache ca-certificates
COPY --from=build "/out/${REPO}" /usr/bin/
LABEL org.opencontainers.image.source="https://github.com/minio/${REPO}" \
      org.opencontainers.image.version="${TAG}"
# Shell-form can't take ARGs in exec-form ENTRYPOINT, so symlink to a fixed name.
RUN ln -s "/usr/bin/${REPO}" /usr/local/bin/entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint"]
