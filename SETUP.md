# SETUP — continue on the Mac Mini

This repo is authored on the MacBook Air (text only) and **built on the Mac Mini**. GitHub is the
bridge. This is the bootstrap for standing up the local dev environment on the Mini.

## 1. Prerequisites (Mac Mini)

```bash
# Homebrew (if not present): https://brew.sh
# Core tooling
brew install git gh node@24 duckdb            # duckdb powers the Week-1 spikes

# Kubernetes / IaC toolchain (the platform — ADR 0008/0009). Postgres runs IN-CLUSTER via
# CloudNativePG, not natively.
brew install colima k3d kubectl helm go-task terraform tilt

# pnpm via corepack (ships with Node)
corepack enable
corepack prepare pnpm@10.23.0 --activate
```

Verify: `node -v` (≥ 22, repo targets 24), `pnpm -v` (10.x), `kubectl version --client`, `task --version`.

## 2. Clone

```bash
gh auth login                       # if not already authed on the Mini
git clone https://github.com/lucas-homer/yokel.git
cd yokel
```

## 3. Install (this is the step that does NOT happen on the Air)

```bash
pnpm install                        # installs the whole workspace
```

## 4. Secrets

```bash
cp spikes/.env.example spikes/.env
# Get a free Regulations.gov key (instant) at https://api.data.gov/signup/
# then put it in spikes/.env as REGS_KEY=...
```

Never commit `.env` (it's gitignored). Only `.env.example` is tracked.

## 5. Bring up the platform

DocketClock runs on Kubernetes (ADR 0008/0009). The local cluster + Postgres (CloudNativePG), Argo CD,
and External Secrets + Vault all come up from code:

```bash
cd infra && task dev-up        # colima → k3d → Argo CD → CNPG/ESO/Vault → app
task status                    # Argo Applications + key pods
```

See `infra/README.md` for the full runbook. The `docketclock` database is provisioned by the
CloudNativePG Cluster — there is no `createdb`. After bring-up, patch real secrets into Vault:

```bash
REGS_API_KEY=xxx bash infra/scripts/seed-docketclock-secrets.sh
```

For the day-to-day inner loop, run `tilt up` from the repo root (hot-reload; API on
http://localhost:8088).

## 6. Where to start

1. Read the [root README](README.md) for current status, then `docs/architecture/docketclock.md`
   and `docs/architecture/watershed-watch.md` for the designs.
2. The Week-1 spikes are **done** — outcomes in `docs/plans/week1-go-no-go-memo.md`
   (DocketClock: BUILD; Watershed Watch: shelved). The `spikes/` harness stays for
   re-measurement (e.g. the Watershed revival paths).
3. DocketClock is built through the observability phase; see the root README status list and
   `plans/` for the phase plans.

## Notes

- `docs/research/` holds the heavy HTML reports + foundry JSON for reference; open the HTML in a
  browser. Agents should not load these routinely (see `AGENTS.md`).
- The architecture markdown is generated: `python3 tools/gen_arch_md.py` regenerates it from
  `arch-foundry-result.json`.
