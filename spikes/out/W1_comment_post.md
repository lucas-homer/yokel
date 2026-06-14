# W1 — Regulations.gov POST /comments availability

**Run:** 2026-06-14 (Eastern) · key tier: standard non-gov REGS_KEY
**Method:** non-destructive POST probes — the `/comments` probe sends an **empty body**, so it can only
4xx, never persist a comment (the auth-handshake test the plan sanctions).

## Probe results

| probe | HTTP | error code | body (truncated) |
| --- | ---: | --- | --- |
| POST /v4/submission-keys | 201 |  | `{"data":{"id":"mqe-eft9-fwcc","type":"submission-keys"}}` |
| POST /v4/comments {} | 403 | API_KEY_UNAUTHORIZED | `{ "error": { "code": "API_KEY_UNAUTHORIZED", "message": "The api_key supplied is not authorized to access the given service. Contact us at https://www.regulations.gov/support for assistance" } }` |
| GET /v4/comments | 200 |  | `{ "data" : [ { "id" : "EPA-R10-OW-2017-0369-1246", "type" : "comments", "attributes" : { "agencyId" : "EPA", "objectId" : "0900006482ba59a6", "documentType" : "Public Submission", "withdrawn" : false, "highlightedContent" : "", "postedDate"` |

## Verdict

**CLOSED / gov-only — standard key cannot POST comments.**

- `POST /v4/submission-keys` → **201** (can mint a submission key — initiation is allowed)
- `POST /v4/comments` → **403 API_KEY_UNAUTHORIZED** — authorization denial at the service level, *not* a payload validation error
- `GET /v4/comments` → **200** (key is valid for reads — so the POST denial is a *tier* gate, not a bad key)

### Chosen path

**Fallback:** structured draft + copy-paste + guided link-out. Receipt = "filed by member (self-reported)" (honest second-class).

> The contrast is the tell: minting a submission-key succeeds (201) while `POST /comments` is denied
> (403 API_KEY_UNAUTHORIZED) — i.e. the *submission service* is gated above the standard tier, consistent
> with the post-2025 change. A GSA-authorized/gov submitter tier may differ; the composer should be
> built either way, with the receipt model switched by this flag.
