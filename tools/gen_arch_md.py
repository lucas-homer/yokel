#!/usr/bin/env python3
"""Generate canonical, agent-readable architecture markdown from arch-foundry-result.json.

This is the source of truth for agents/humans reading architecture. The pretty HTML
(docs/research/docketclock-watershed-architecture.html) is the presentation form.
Run from repo root: python3 tools/gen_arch_md.py
"""
import json, os

R = json.load(open('docs/research/arch-foundry-result.json'))
DC = R['docketclock']['architecture']
DCP = R['docketclock']['proposals']
FIT = R['watershed']['fit']
WW = R['watershed']['architecture']
WWP = R['watershed']['proposals']


def tbl(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
    for r in rows:
        out.append('| ' + ' | '.join(str(c).replace('\n', ' ').replace('|', '\\|') for c in r) + ' |')
    return '\n'.join(out)


def bullets(items):
    return '\n'.join(f'- {str(x)}' for x in (items or []))


def numbered(items, k1, k2):
    return '\n'.join(f'{i}. **{it.get(k1)}** — {it.get(k2)}' for i, it in enumerate(items, 1))


def scores(props):
    return ', '.join(f'{p["stance"]} {p["critique"]["score"]}/10' for p in props)


# ---------- DocketClock ----------
led = DC['codex_ledger']
canon = DC['canonical_object']
conf = DC['confidence_model']
mvp = DC['mvp_boundary']

dc = f"""# DocketClock — Architecture

> **Canonical, agent-readable.** Generated from `arch-foundry-result.json` by `tools/gen_arch_md.py`.
> Do not hand-edit; edit the source or regenerate. Pretty version:
> `docs/research/docketclock-watershed-architecture.html`.
>
> Provenance: 13-agent foundry — 3 competing architects (pragmatist / trust-maximalist /
> substrate) → adversarial critique → Opus synthesis. Proposal soundness scores: {scores(DCP)}.

## {DC['title']}

{DC['one_liner']}

## Architecture thesis

{DC['architecture_thesis']}

## What we kept / changed / rejected from Codex's plan

The substrate was reconciled against a competing "Codex" DocketClock architecture. Verdict:
kept {len(led['kept'])}, changed {len(led['changed'])}, rejected {len(led['rejected'])}.

### Kept
{bullets(f"**{x['item']}** — {x['why']}" for x in led['kept'])}

### Changed
{chr(10).join(f"- **{x['item']}**: _{x.get('from','—')}_ → **{x['to']}** — {x['why']}" for x in led['changed'])}

### Rejected
{bullets(f"**{x['item']}** — {x['why']}" for x in led['rejected'])}

## Canonical object — {canon['name']}

{canon['design_notes']}

{tbl(['Field', 'Meaning'], [(f['field'], f['desc']) for f in canon['key_fields']])}

## Pipeline

{numbered(DC['pipeline'], 'stage', 'what')}

{chr(10).join(f"- _{p['stage']}_: {p['detail']}" for p in DC['pipeline'])}

## Components

{tbl(['Component', 'Responsibility', 'Tech'], [(c['name'], c['responsibility'], c.get('tech','')) for c in DC['components']])}

## Confidence model

{conf['how_computed']}

{tbl(['State', 'Meaning', 'Alert behavior'], [(s['state'], s['meaning'], s['alert_behavior']) for s in conf['states']])}

## Data sources

{tbl(['Source', 'Role', 'Gotchas'], [(s['source'], s['role'], s.get('gotchas','')) for s in DC['data_sources']])}

## Delivery surfaces

{bullets(f"**{d['surface']}** — {d['detail']}" for d in DC['delivery_surfaces'])}

## MVP boundary

**In scope (v1):**
{bullets(mvp['in_scope'])}

**Deferred:**
{bullets(mvp['deferred'])}

**First customer:** {mvp['first_customer']}

## Tech stack

{tbl(['Layer', 'Choice', 'Why'], [(s['layer'], s['choice'], s['why']) for s in DC['tech_stack']])}

## Build sequence (~12 weeks)

{numbered(DC['build_sequence'], 'milestone', 'deliverable')}

## Top risks

{tbl(['Risk', 'Mitigation'], [(r['risk'], r['mitigation']) for r in DC['top_risks']])}

## Divergences from the earlier dossier

{bullets(DC.get('divergences_from_prior_dossier'))}

## Open questions (answer in Week-1 spikes)

{bullets(DC.get('open_questions'))}
"""

# ---------- Watershed Watch ----------
bd = FIT['layer_boundary']
wmvp = WW['mvp_boundary']
geo = WW['geo_scoping']

ww = f"""# Watershed Watch — Architecture

> **Canonical, agent-readable.** Generated from `arch-foundry-result.json` by `tools/gen_arch_md.py`.
> Pretty version: `docs/research/docketclock-watershed-architecture.html`.
> Proposal soundness scores: {scores(WWP)}.

## Fit verdict

- **Builds on DocketClock:** `{FIT['builds_on_docketclock']}`
- **Is it a real vertical wedge (not just a skin)?** `{FIT['is_land_use_wedge']}`

{FIT['rationale']}

**Wedge reasoning:** {FIT['wedge_reasoning']}

### Layer boundary

**DocketClock provides (rented):**
{bullets(bd['docketclock_provides'])}

**Watershed Watch owns (the anti-skin IP):**
{bullets(bd['watershed_adds'])}

### What the wedge forces the substrate to expose
{bullets(FIT['requirements_on_docketclock'])}

### When to build standalone instead
{FIT['counterfactual_if_standalone']}

### Fit risks
{bullets(FIT['risks'])}

---

## {WW['title']}

{WW['one_liner']}

## Architecture thesis

{WW['architecture_thesis']}

## Relationship to DocketClock

{WW['relationship_to_docketclock']}

## Components

{tbl(['Component', 'Responsibility', 'Tech'], [(c['name'], c['responsibility'], c.get('tech','')) for c in WW['components']])}

## Geo-scoping — {geo['primitive']}

{geo['how']}

**Gotchas:** {geo.get('gotchas','')}

## Data sources

{tbl(['Source', 'Role', 'Gotchas'], [(s['source'], s['role'], s.get('gotchas','')) for s in WW['data_sources']])}

## The monitor → act → see-impact loop

{numbered(WW['action_loop'], 'step', 'what')}

## Coverage tiers (the load-bearing honesty device)

{bullets(f"**{t['tier']}** — {t['what']} _(label: {t.get('labeling','')})_" for t in WW['coverage_tiers'])}

## MVP boundary

**In scope (v1):**
{bullets(wmvp['in_scope'])}

**Deferred:**
{bullets(wmvp['deferred'])}

**First design partner:** {wmvp['first_partner']}

## Tech stack

{tbl(['Layer', 'Choice', 'Why'], [(s['layer'], s['choice'], s['why']) for s in WW['tech_stack']])}

## Build sequence (~12 weeks)

{numbered(WW['build_sequence'], 'milestone', 'deliverable')}

## Top risks

{tbl(['Risk', 'Mitigation'], [(r['risk'], r['mitigation']) for r in WW['top_risks']])}

## Open questions (answer in Week-1 spikes)

{bullets(WW.get('open_questions'))}
"""

os.makedirs('docs/architecture', exist_ok=True)
open('docs/architecture/docketclock.md', 'w').write(dc)
open('docs/architecture/watershed-watch.md', 'w').write(ww)
print('wrote docs/architecture/docketclock.md', len(dc), 'chars')
print('wrote docs/architecture/watershed-watch.md', len(ww), 'chars')
