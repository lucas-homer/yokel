# SETUP — continue on the Mac Mini

This repo is authored on the MacBook Air (text only) and **built on the Mac Mini**. GitHub is the
bridge. This is the bootstrap for standing up the local dev environment on the Mini.

## 1. Prerequisites (Mac Mini)

```bash
# Homebrew (if not present): https://brew.sh
# Core tooling
brew install git gh node@24 postgresql@16 duckdb
brew install postgis            # needed by Watershed Watch (HUC geo); optional for DocketClock-only

# pnpm via corepack (ships with Node)
corepack enable
corepack prepare pnpm@10.23.0 --activate

# Start Postgres
brew services start postgresql@16
```

Verify: `node -v` (≥ 22, repo targets 24), `pnpm -v` (10.x), `psql --version` (16.x).

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

## 5. Create the local databases (when you start building, not required for spikes)

```bash
createdb docketclock
# Watershed Watch adds PostGIS:
createdb watershed && psql watershed -c "CREATE EXTENSION postgis;"
```

## 6. Where to start

1. Read `docs/architecture/docketclock.md` and `docs/architecture/watershed-watch.md`.
2. Read `docs/plans/week1-validation-spikes.md` — the immediate next work.
3. Run the Week-1 spikes from `spikes/` (the harness is scaffolded; fill in / run D1, D2, D3, W3).
4. Only after the spikes pass: build DocketClock per its build sequence.

## Notes

- `docs/research/` holds the heavy HTML reports + foundry JSON for reference; open the HTML in a
  browser. Agents should not load these routinely (see `AGENTS.md`).
- The architecture markdown is generated: `python3 tools/gen_arch_md.py` regenerates it from
  `arch-foundry-result.json`.
