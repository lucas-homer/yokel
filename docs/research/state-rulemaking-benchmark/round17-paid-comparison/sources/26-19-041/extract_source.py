#!/usr/bin/env python3
"""Deterministically extract the full readable body text and links from original.htm."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
BLOCKS = {
    "address", "article", "aside", "blockquote", "div", "dl", "dt", "dd",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3",
    "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
    "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}

class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.skip_depth = 0
        self.parts = []
        self.links = []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "body":
            self.in_body = True
        if not self.in_body:
            return
        if tag in ("script", "style"):
            self.skip_depth += 1
        if self.skip_depth:
            return
        if tag in BLOCKS or tag == "br":
            self.parts.append("\n")
        if tag == "a":
            self.anchor = {"href": attrs.get("href"), "text": ""}

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
            return
        if not self.in_body:
            return
        if tag in ("script", "style") and self.skip_depth:
            self.skip_depth -= 1
        if self.skip_depth:
            return
        if tag == "a" and self.anchor is not None:
            self.links.append(self.anchor)
            self.anchor = None
        if tag in BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_body and not self.skip_depth:
            self.parts.append(data)
            if self.anchor is not None:
                self.anchor["text"] += data

raw = (ROOT / "original.htm").read_bytes()
source = raw.decode("utf-8-sig")
parser = Extractor()
parser.feed(source)
parser.close()
body_text = "".join(parser.parts).strip("\n")
(ROOT / "parsed-body.txt").write_text(body_text, encoding="utf-8", newline="")
(ROOT / "anchors.json").write_text(
    json.dumps(parser.links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
receipt = {
    "original_html_sha256": hashlib.sha256(raw).hexdigest(),
    "original_html_bytes": len(raw),
    "parsed_body_text_sha256": hashlib.sha256(body_text.encode("utf-8")).hexdigest(),
    "parsed_body_text_chars": len(body_text),
    "parsed_body_text_utf8_bytes": len(body_text.encode("utf-8")),
    "parsed_body_text_token_count_whitespace_split": len(body_text.split()),
    "anchor_count": len(parser.links),
    "anchor_inventory": "anchors.json",
    "text_output": "parsed-body.txt",
    "parser": "extract_source.py (stdlib HTMLParser, convert_charrefs=True; retains every body text node and anchor href/label; skips head, style, and script; inserts newlines at listed block boundaries and br tags).",
    "loss_limits": [
        "Text-node order and wording are retained; HTML structure and inline formatting are not represented in parsed-body.txt.",
        "Underline/strike/bold/italics, table-cell boundaries beyond block newlines, and CSS presentation may carry meaning and must be checked against original.htm.",
        "No browser document.body.innerText capture is included; parsed-body.txt is the reproducible model-source text derived from the preserved original HTML.",
    ],
}
(ROOT / "COMPARISON.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
