# Yokel

> Civic-tech monorepo. Helping busy non-experts **monitor** public-comment periods, rules, and
> hearings — and take **meaningful action** with honest receipts.
>
> `yokel` is a working **codename** (a local yokel trying to give back). The public umbrella brand
> is deliberately undecided — see [ADR 0006](docs/decisions/0006-umbrella-brand-deferred.md).

## What's here

The "house" architecture: a shared **substrate** (DocketClock) with **vertical wedges** (Watershed
Watch) renting it through a shared contract. Right now this repo is a **skeleton + the full
planning/context layer** — the structure and decisions are in place; product code waits until the
[Week-1 validation spikes](docs/plans/week1-validation-spikes.md) pass.

```
yokel/
├─ docs/
│  ├─ architecture/     ← canonical, agent-readable designs (generated from foundry output)
│  │  ├─ docketclock.md         the federal comment-deadline substrate (build first)
│  │  └─ watershed-watch.md     the basin-scoped environmental wedge (partial build-on)
│  ├─ plans/            ← week1-validation-spikes.md (the immediate next work)
│  ├─ decisions/        ← ADRs: the durable "why" behind every big call
│  └─ research/         ← heavy reference (HTML reports, foundry JSON). NOT loaded routinely.
├─ packages/
│  └─ contracts/        ← THE SEAM: shared schemas/types (ParticipationWindow, OCD-IDs, confidence)
├─ apps/
│  ├─ docketclock/      ← substrate (stub — built first, after spikes)
│  └─ watershed-watch/  ← vertical wedge (stub — gated)
└─ spikes/              ← Week-1 validation harness (run on the Mini)
```

## Status

- ✅ Prior-art research, idea foundry (11 seasoned ideas), strategy (substrate-first + channel-led)
- ✅ Architecture: DocketClock + Watershed Watch, reconciled against a competing "Codex" plan
- ✅ Week-1 validation spike plan
- ⏭️ **Next:** run the Week-1 spikes (`docs/plans/week1-validation-spikes.md`) → then build DocketClock

## Working setup

Authoring/organizing happens on the **MacBook Air**; **local builds, installs, and the dev
environment live on the Mac Mini.** GitHub is the bridge. To continue on the Mini, see
**[SETUP.md](SETUP.md)**.

## License

TBD — see [ADR 0007](docs/decisions/0007-license-deferred.md) (MIT vs AGPL tension for civic tech).
Until a license is chosen, this is **all rights reserved**; do not assume open-source terms yet.
