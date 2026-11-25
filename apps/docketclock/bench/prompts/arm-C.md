Tools: web search, web page fetch, `curl` for two public APIs, and the DocketClock API.

- Federal Register API, no key: `curl -s "https://www.federalregister.gov/api/v1/documents/<document_number>.json"`.
- Regulations.gov API v4: `curl -s -H "X-Api-Key: $REGS_API_KEY_BENCH" "https://api.regulations.gov/v4/documents/<documentId>"`.
- DocketClock, a service that polls both sources every 15 minutes, reconciles them into one comment
  window per notice, and records every change:
  - `curl -s -H "x-api-key: $DOCKETCLOCK_API_KEY" "$DOCKETCLOCK_API_URL/v1/windows?docket_id=<docket>"`
  - `curl -s -H "x-api-key: $DOCKETCLOCK_API_KEY" "$DOCKETCLOCK_API_URL/v1/windows/ocd-participation-window/federal/<fr_document_number>"`
  - `curl -s "$DOCKETCLOCK_API_URL/openapi.json"` describes every route and field.
    A window carries the resolved close, a confidence (high, medium, low, conflicting, unknown), the
    provenance of each date, and its change history.
    Never print an API key.
