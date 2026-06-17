# DocketClock runtime image — the Fastify API, the differential poller, and the migration runner all
# run from ONE image; the Helm chart sets the command per workload (api / poller / migrate Job).
#
# We run via tsx (NOT compiled `dist/`): @yokel/contracts is consumed as TypeScript SOURCE (its package
# `exports` point at src/index.ts), and the whole project already runs on tsx (tests, smokes, dev). So
# `node dist/...` cannot resolve the contract at runtime, but `tsx src/...` can. The pnpm install is
# SCOPED to @yokel/docketclock + its deps (--filter ...), so the duckdb-bearing `spikes` and the
# `watershed-watch` members never enter the image (smaller, and no musl-native landmines on Alpine).
#
# Build context is the repo ROOT (the chart/Tilt build with context='.'):
#   docker build -f apps/docketclock/Dockerfile -t docketclock:local .
FROM node:24-alpine

# pnpm via corepack (version pinned by the root package.json `packageManager` field).
RUN corepack enable
WORKDIR /app

# Workspace manifests first, for layer caching. ALL member manifests are needed so pnpm can build the
# workspace graph and validate the frozen lockfile — even though we only install docketclock's subset.
# MAINTENANCE: adding a new pnpm workspace member means adding its package.json COPY here too, or the
# `--frozen-lockfile` install fails with a cryptic lockfile-mismatch error (the graph won't resolve).
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json tsconfig.base.json ./
COPY packages/contracts/package.json packages/contracts/
COPY apps/docketclock/package.json apps/docketclock/
COPY apps/watershed-watch/package.json apps/watershed-watch/
COPY spikes/package.json spikes/

# Install ONLY @yokel/docketclock and its dependencies (incl. tsx + @yokel/contracts). The trailing
# `...` pulls in dependencies; spikes (duckdb) and watershed-watch are out of scope. Frozen = reproducible.
RUN pnpm install --frozen-lockfile --filter @yokel/docketclock...

# Source the runtime actually executes (tsx transpiles these on the fly) + the migration SQL.
COPY packages/contracts/src packages/contracts/src
COPY apps/docketclock/src apps/docketclock/src
COPY apps/docketclock/migrations apps/docketclock/migrations

WORKDIR /app/apps/docketclock
ENV NODE_ENV=production
ENV PORT=8080
EXPOSE 8080
USER node

# Default = the API; the chart overrides `command` for the poller Deployment and the migration Job.
CMD ["pnpm", "exec", "tsx", "src/api/run.ts"]
