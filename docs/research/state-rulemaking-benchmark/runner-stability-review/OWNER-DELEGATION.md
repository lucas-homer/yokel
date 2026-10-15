# Owner delegation for unattended research release

The owner selected this answer in the primary task on 2026-10-11:

> Primary releases reviewed jobs within my authorized scope and budgets

The question explicitly explained that this trusts the primary with use of the permitted API keys. This resolves release authority in favor of the primary, rather than per-job owner signing or a separately protected approval service. Signing will establish approved artifact identity and integrity; it will not claim independence from the primary that can release it.

Implementation scope: a stable native credential executor and signed immutable job definitions for reviewed DocketClock research. Preserve the existing service-account/vault/reference envelope and bootstrap-token protections. Each job receives only its needed permitted API keys. New projects, provider references, expanded budgets, and production deployment are outside this delegation unless separately authorized. Budgets remain enforced by reviewed job code and its ledger, not an independent native guarantee on provider billing.

The current authorized experiment remains round8-stronger-cap-probe: at most one OpenRouter stronger call, output cap8192, no inventory or Jev calls/retries, shared $2 cumulative budget with all five prior attempts retained. Its exact request reservation is $0.153414 and maximum aggregate reservation is $0.704896718.

Prepare and independently review the replacement before installing or changing trust. A real macOS enrollment step may still be needed for the replacement. Synthetic signed-job tests do not prove production Keychain continuity; verify two job definitions with unchanged executor bytes after migration. This delegation does not authorize exposing secrets in logs, chat, arguments, or repository files.
