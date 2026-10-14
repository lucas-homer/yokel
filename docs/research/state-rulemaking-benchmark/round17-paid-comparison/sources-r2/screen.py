#!/usr/bin/env python3
"""R17 protocol §3 S6 case-insensitive whole-word keyword screen."""
import re
EXCEPTION = ["unless", "except", "exception", "exceptions", "exempt", "exemption", "waiver", "waive", "notwithstanding", "excluding", "other than", "in lieu of", "does not apply", "do not apply"]
SCOPE = ["if", "only if", "provided that", "subject to", "applies to", "apply to", "applicable to", "limited to", "only"]
def hits(text, terms):
    return {term: len(re.findall(r"\b" + re.escape(term) + r"\b", text, flags=re.IGNORECASE)) for term in terms}
def screen(text):
    exception_hits = hits(text, EXCEPTION)
    scope_hits = hits(text, SCOPE)
    total = sum(exception_hits.values()) + sum(scope_hits.values())
    return {"exception_hits": exception_hits, "scope_hits": scope_hits, "exception_hit_total": sum(exception_hits.values()), "total_hits": total, "pass": sum(exception_hits.values()) >= 1 and total >= 3}
