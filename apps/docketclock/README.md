# DocketClock

The reconciled federal comment-deadline **substrate** — build FIRST.

> Net-new value = reconciliation + confidence + provenance, NOT discovery. The append-only
> Observation log is primary; `ParticipationWindow` is a derived, versioned projection. Federal-only
> until a paying customer funds a jurisdiction tranche.

**Full design:** [`docs/architecture/docketclock.md`](../../docs/architecture/docketclock.md)
**Gate before building:** [`docs/plans/week1-validation-spikes.md`](../../docs/plans/week1-validation-spikes.md)

Three non-negotiables (see the design for why):
1. Conflict detection compares dates normalized to **America/New_York**, not UTC.
2. Confidence drop **suppresses the alert AND fires a conflict notification** — suppression is never silence.
3. The Week-1 **frDocNum join hit-rate** is a hard go/no-go before any pipeline code.

Status: **stub.** Gated behind the Week-1 spikes.
