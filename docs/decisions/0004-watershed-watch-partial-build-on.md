# 0004. Watershed Watch builds on DocketClock — partially

- Status: Accepted
- Date: 2026-06-14

## Context

Watershed Watch is the first vertical wedge and the project's path back to civic mission. The risk
(named in our own dossier) is that it's "just DocketClock + a Waterkeeper skin." Full design + fit
analysis: `docs/architecture/watershed-watch.md`.

## Decision

Build on DocketClock **partially** (fit verdict: `yes-partially`). Watershed Watch RENTS reconciled
federal windows + the confidence model + OCD-IDs + govinfo_url, and OWNS the three things the bare
registry structurally cannot:

1. EPA EIS ingestion + its 45/30-day clock + EIS-vs-FR extension reconciliation,
2. USGS WBD/HUC geo-recall (is this docket in-basin?),
3. the monitor→act→receipt loop with honest procedural receipts (never causal).

Gate with a **falsifiable anti-skin test** run BEFORE committing a partner. Partner must be
**staffed** (so the design partner IS the paying customer). A **standalone contingency** (~1
engineer-week) ships if the partner window opens before DocketClock has a B2B customer — but it never
forks `@yokel/contracts`, only the deployment.

## Consequences

- The vertical earns distribution the registry can't (EIS + geo-recall + action), or it fails the
  anti-skin test and shouldn't ship — decided by measurement, not branding.
- Watershed Watch's commitment pulls forward two deferred substrate items: a vertical-writable
  enrichment registry and tag-scoped webhook fan-out.
- Federal/EIS coverage is honest and strong; local land-use is honestly weak and labeled so via the
  coverage-tier system.
