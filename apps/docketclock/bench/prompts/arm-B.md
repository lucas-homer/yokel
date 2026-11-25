Tools: web search, web page fetch, and `curl` for two public APIs.

- Federal Register API, no key: `curl -s "https://www.federalregister.gov/api/v1/documents/<document_number>.json"`.
  Search: `curl -s "https://www.federalregister.gov/api/v1/documents.json?conditions[term]=<words>"`.
- Regulations.gov API v4, with the key in the environment:
  `curl -s -H "X-Api-Key: $REGS_API_KEY_BENCH" "https://api.regulations.gov/v4/documents/<documentId>"`.
  Search: `.../v4/documents?filter[docketId]=<docket>` or `?filter[frDocNum]=<number>`.
  The key allows about 1,000 requests an hour, so keep requests few.
  Never print the API key.
