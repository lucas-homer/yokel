# Rename plan: `yokel` → `civic-tools` (full scope)

> Status: **Not started** — plan only, do not run without explicit go.
> Scope chosen: everything, including the k3d local cluster and Terraform prod.
> This rename resolves ADR 0006 (umbrella brand deferred); see Phase 5.

## Blast radius (confirmed by scan)

| Area                               | Refs                                                                                            | Risk                                     |
| ---------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------- |
| GitHub repo name + `origin` remote | 1                                                                                               | Safe, auto-redirects                     |
| npm scope `@yokel/*`               | 4 pkg names + 2 deps + ~13 imports + lockfile                                                   | Safe, covered by tests                   |
| GitOps repo URLs                   | 3 ArgoCD/bootstrap manifests                                                                    | Safe                                     |
| Docs / prose                       | README, SETUP, AGENTS, infra/README, Tiltfile                                                   | Safe                                     |
| **k3d local cluster**              | `infra/k3d/yokel.yaml` (name, registry, filename), Taskfile `CLUSTER`, Tiltfile context comment | **Destructive — local cluster recreate** |
| **Terraform `yokel-prod`**         | 1 default in `variables.tf`                                                                     | **Conditional** — see Phase 7            |

Decisions locked: npm scope → `@civic-tools/*`.

---

## Phase 1 — GitHub repo rename _(safe, reversible)_

- `gh repo rename civic-tools` from inside the repo → renames on GitHub **and** rewrites the local `origin` URL.
- Verify: `git remote -v` → `.../civic-tools.git`; `git fetch` succeeds.

## Phase 2 — Local folder rename _(cosmetic)_

- `mv ../yokel ../civic-tools`, reopen session there. Nothing depends on the absolute path.

## Phase 3 — npm scope `@yokel/*` → `@civic-tools/*` _(the bulk; branch `chore/rename-civic-tools`)_

- Find/replace `@yokel/` → `@civic-tools/` across tracked files:
  `grep -rIl '@yokel/' --exclude-dir=.git --exclude-dir=node_modules | xargs sed -i ''`
  (4 `package.json` names, 2 `workspace:*` deps, ~13 imports in `apps/docketclock`).
- Root `package.json`: `"name": "yokel"` → `"civic-tools"`.
- `pnpm install` → regenerates `pnpm-lock.yaml` + `node_modules/@civic-tools` symlinks; stale `@yokel` symlinks drop out.
- **Verify:** `pnpm -r typecheck && pnpm -r test && pnpm lint` green.

## Phase 4 — GitOps repo URLs

- Replace `github.com/lucas-homer/yokel.git` → `.../civic-tools.git` in:
  - `infra/bootstrap/root-app-local.yaml`
  - `infra/bootstrap/root-app-cloud.yaml`
  - `infra/argocd/apps/app-docketclock.yaml`
- Redirect would hold, but pin the real URL so ArgoCD doesn't depend on it.

## Phase 5 — Docs + ADR

- Update prose: `README.md`, `SETUP.md`, `AGENTS.md`, `infra/README.md`, the `k3d-yokel` comment in `Tiltfile`.
- Write **ADR 0010** "Umbrella brand chosen: `civic-tools`" that **supersedes ADR 0006**.
  (0007 is already the license ADR; 0010 is the next free number.)
  Mark 0006 `Status: Superseded by 0010` and link forward — don't rewrite its history.

## Phase 6 — k3d local cluster rename _(DESTRUCTIVE — local only)_

Recreates the local cluster, **wiping in-cluster state**: CNPG Postgres (local observation-log
data — re-pollable), Vault (re-seeded automatically by `task dev-up`), ArgoCD, and the docketclock
deployment. Kube context changes `k3d-yokel` → `k3d-civic-tools`.

Order matters — tear down the _old_ cluster by its old name **before** editing files:

1. `cd infra && task dev-down` (deletes the `yokel` cluster while config still says `yokel`).
2. Edit:
   - `infra/k3d/yokel.yaml` → rename file to `infra/k3d/civic-tools.yaml`; inside it
     `metadata.name: civic-tools`, registry `name: civic-tools-registry`.
   - `Taskfile.yml`: `CLUSTER: civic-tools` and the `--config k3d/civic-tools.yaml` path.
   - `infra/README.md` path ref.
   - `Tiltfile` comment → `k3d-civic-tools`.
3. `task dev-up` → rebuilds the whole local GitOps stack under the new name.
4. **Verify:** `task status` shows Applications Healthy; app reachable on `localhost:8080`.

> Optional: `pg_dump` local Postgres before `dev-down` and restore after, if the local
> observation-log data is worth keeping.

## Phase 7 — Terraform `yokel-prod` _(safe **now**, would be destructive later)_

`region` defaults to `""` and the provider is chosen "at Phase 3" — **cloud isn't provisioned yet**,
so today this is a plain text edit.

1. Confirm no live state first: `cd infra/terraform/envs/cloud && terraform state list`
   (empty / "no state" → safe).
2. If empty → edit default `"yokel-prod"` → `"civic-tools-prod"`.
3. **If state is NOT empty** (a cluster was actually applied) → STOP. Renaming `cluster_name`
   force-recreates the live cluster; needs a deliberate `terraform plan` review, not a sweep.

## Phase 8 — Verify & land

- Final sweep: `grep -rIi yokel --exclude-dir=.git --exclude-dir=node_modules .`
  → only acceptable remaining hit is **ADR 0006's historical text** (intentional).
- `pnpm -r typecheck && pnpm -r test && pnpm lint` green; local stack Healthy.
- Commit, PR, merge to `main`.

## Rollback

- GitHub: `gh repo rename yokel` (free until reclaimed).
- Code/infra: single branch — revert the merge.
- k3d: `task dev-down && git checkout main -- infra && task dev-up` rebuilds the old-named cluster.
