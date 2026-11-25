#!/usr/bin/env node
// Benchmark key hand-check workbench (agent-vs-DocketClock, apps/docketclock/bench/README.md).
//
// Items whose key DocketClock graded itself (post-close misses, the routine sample, "never moved") are
// marked needs_check. This page puts each one next to what the live sources say TODAY, so the check is
// mostly reading one line: the key, DocketClock's published value, the live Federal Register
// `comments_close_on` + DATES text, and the live Regulations.gov `commentEndDate`, with links to both
// pages. Items where both live sources agree with the key are grouped first and can be confirmed in
// one click; disagreements need a decision (keep the key, take the FR or portal date, type a date, drop).
//
//   node tools/bench-check.mjs [--key ~/.config/yokel/bench/key/items.jsonl] [--port 8792] [--refresh]
//
// Reads REGS_API_KEY_BENCH from ~/.config/yokel/bench.env (never printed, never sent to the page).
// Live values are cached next to the key (live-cache.json); --refresh refetches them.
// Saving rewrites items.jsonl atomically, after a one-time copy to items.jsonl.orig. A decision sets
// needs_check=false and records `check: {decision, date?, note?, at}`; "drop" sets dropped=true, which
// the runner and grader skip; "Re-check" puts an item back. Listens on 127.0.0.1 only. Node 22+, no dependencies.

import {
  copyFileSync,
  existsSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { createServer } from "node:http";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { parseArgs } from "node:util";

const cfg = join(homedir(), ".config/yokel");
const { values } = parseArgs({
  options: {
    key: { type: "string", default: join(cfg, "bench/key/items.jsonl") },
    port: { type: "string", default: "8792" },
    refresh: { type: "boolean", default: false },
  },
});
const keyPath = values.key;
const cachePath = join(dirname(keyPath), "live-cache.json");
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function envFile() {
  const p = join(cfg, "bench.env");
  if (!existsSync(p)) return {};
  return Object.fromEntries(
    readFileSync(p, "utf8")
      .split("\n")
      .map((l) => l.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/))
      .filter(Boolean)
      .map((m) => [m[1], m[2].replace(/^['"]|['"]$/g, "")]),
  );
}
const REGS_KEY = envFile().REGS_API_KEY_BENCH;

const easternDate = (iso) =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));

function loadItems() {
  return readFileSync(keyPath, "utf8")
    .trim()
    .split("\n")
    .map((l) => JSON.parse(l));
}
function saveItems(items) {
  if (!existsSync(keyPath + ".orig")) copyFileSync(keyPath, keyPath + ".orig");
  const tmp = keyPath + ".tmp";
  writeFileSync(tmp, items.map((i) => JSON.stringify(i)).join("\n") + "\n", {
    mode: 0o600,
  });
  renameSync(tmp, keyPath);
}

// ── live source fetches ─────────────────────────────────────────────────────────────────────────
async function fetchJson(url, headers = {}) {
  for (let attempt = 0; attempt < 3; attempt++) {
    let r;
    try {
      r = await fetch(url, { headers });
    } catch (e) {
      return { error: `network: ${e.cause?.code ?? e.message}` };
    }
    if (r.status === 429) {
      await new Promise((s) => setTimeout(s, 5000 * (attempt + 1)));
      continue;
    }
    if (!r.ok) return { error: `HTTP ${r.status}` };
    return r.json();
  }
  return { error: "rate limited" };
}
async function liveFor(item) {
  const out = { fetched_at: new Date().toISOString(), fr: null, regs: null };
  const fr = item.refs.fr_document_number;
  if (fr) {
    const j = await fetchJson(
      `https://www.federalregister.gov/api/v1/documents/${encodeURIComponent(fr)}.json?fields[]=comments_close_on&fields[]=dates&fields[]=html_url&fields[]=title`,
    );
    out.fr = j.error
      ? { error: j.error }
      : {
          close: j.comments_close_on ?? null,
          dates: j.dates ?? null,
          url: j.html_url,
          title: j.title,
        };
  }
  const regs = item.refs.regs_document_id;
  if (regs && REGS_KEY) {
    const j = await fetchJson(
      `https://api.regulations.gov/v4/documents/${encodeURIComponent(regs)}`,
      { "X-Api-Key": REGS_KEY },
    );
    const a = j?.data?.attributes;
    out.regs = j.error
      ? { error: j.error }
      : {
          close: a?.commentEndDate ? easternDate(a.commentEndDate) : null,
          raw: a?.commentEndDate ?? null,
          withdrawn: a?.withdrawn ?? null,
          title: a?.title,
          url: `https://www.regulations.gov/document/${regs}`,
        };
  } else if (regs)
    out.regs = { error: "no REGS_API_KEY_BENCH in ~/.config/yokel/bench.env" };
  return out;
}
async function warmCache(items) {
  const cache =
    !values.refresh && existsSync(cachePath)
      ? JSON.parse(readFileSync(cachePath, "utf8"))
      : {};
  const todo = items.filter((i) => i.needs_check && !i.dropped && !cache[i.id]);
  let n = 0;
  const worker = async () => {
    while (todo.length) {
      const i = todo.shift();
      cache[i.id] = await liveFor(i);
      if (++n % 10 === 0) {
        console.log(`  fetched ${n}`);
        writeFileSync(cachePath, JSON.stringify(cache));
      }
    }
  };
  if (todo.length)
    console.log(`fetching live values for ${todo.length} items…`);
  await Promise.all([worker(), worker(), worker()]);
  writeFileSync(cachePath, JSON.stringify(cache), { mode: 0o600 });
  return cache;
}

/** What the key expects, as a single date (or a label) the page can compare. */
function keyDate(i) {
  if (i.expect.kind === "date") return i.expect.date;
  if (i.expect.kind === "moved")
    return i.expect.moved ? i.expect.earlier_date : null;
  return null;
}
function agreement(i, live) {
  if (i.stratum === "moved") return "history"; // live sources can't show history; read the note
  const k = keyDate(i);
  const vals = [live.fr?.close, live.regs?.close].filter(Boolean);
  if (!vals.length) return "no-live";
  return vals.every((v) => v === k) ? "agree" : "disagree";
}

// ── server ──────────────────────────────────────────────────────────────────────────────────────
let items = loadItems();
const cache = await warmCache(items);

function view() {
  return items
    .filter((i) => i.needs_check || i.check)
    .map((i) => ({
      id: i.id,
      stratum: i.stratum,
      question: i.question,
      refs: i.refs,
      key_note: i.key_note,
      expect: i.expect,
      key_date: keyDate(i),
      published: i.docketclock?.published ?? null,
      live: cache[i.id] ?? null,
      agreement: cache[i.id] ? agreement(i, cache[i.id]) : "no-live",
      check: i.check ?? null,
      dropped: !!i.dropped,
    }));
}

function apply(id, d) {
  const i = items.find((x) => x.id === id);
  if (!i) throw new Error(`no item ${id}`);
  const at = new Date().toISOString();
  if (d.decision === "drop") {
    i.dropped = true;
    i.needs_check = false;
    i.check = { decision: "drop", note: d.note ?? null, at };
    return;
  }
  if (d.decision === "keep") {
    delete i.dropped;
    i.needs_check = false;
    i.check = { decision: "keep", note: d.note ?? null, at };
    return;
  }
  if (d.decision === "set") {
    if (!DATE_RE.test(d.date ?? "")) throw new Error("bad date");
    if (i.expect.kind === "date") i.expect = { kind: "date", date: d.date };
    else if (i.expect.kind === "moved")
      i.expect = { kind: "moved", moved: true, earlier_date: d.date };
    else throw new Error("this item's key is not a date");
    delete i.dropped;
    i.needs_check = false;
    i.check = { decision: "set", date: d.date, note: d.note ?? null, at };
    return;
  }
  if (d.decision === "reopen") {
    delete i.dropped;
    delete i.check;
    i.needs_check = true;
    return;
  }
  throw new Error(`unknown decision ${d.decision}`);
}

const server = createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/") {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      return res.end(PAGE);
    }
    if (req.method === "GET" && req.url === "/items") {
      res.writeHead(200, { "content-type": "application/json" });
      return res.end(JSON.stringify(view()));
    }
    if (req.method === "POST" && req.url === "/decide") {
      let body = "";
      for await (const c of req) body += c;
      const { decisions } = JSON.parse(body);
      for (const d of decisions) apply(d.id, d);
      saveItems(items);
      res.writeHead(200, { "content-type": "application/json" });
      return res.end(JSON.stringify({ ok: true, saved: decisions.length }));
    }
    res.writeHead(404);
    res.end();
  } catch (e) {
    res.writeHead(400, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: String(e.message ?? e) }));
  }
});
server.listen(Number(values.port), "127.0.0.1", () => {
  const open = items.filter((i) => i.needs_check && !i.dropped).length;
  console.log(
    `bench-check: ${open} items to check → http://127.0.0.1:${values.port}/  (Ctrl-C to stop; decisions save as you go)`,
  );
});

const PAGE = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bench key check</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6b66;--line:#e4e1d9;--ok:#2f7d4f;--bad:#b3412e;--warn:#9a6b00;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#191918;--fg:#ecebe6;--mut:#a09f99;--line:#33322f;--ok:#6cc38f;--bad:#ef8a76;--warn:#e0b34f;--card:#222220}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:20px 16px 80px}
h1{font-size:20px;margin:0 0 4px} .mut{color:var(--mut)} .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
section{margin-top:24px} h2{font-size:15px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:8px 0}
.card.done{opacity:.55} .grid{display:grid;grid-template-columns:150px 1fr;gap:2px 12px;margin:8px 0}
.v{font-variant-numeric:tabular-nums;font-weight:600} .ok{color:var(--ok)} .bad{color:var(--bad)} .warn{color:var(--warn)}
button{font:inherit;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:6px;padding:4px 10px;cursor:pointer}
button.primary{background:var(--fg);color:var(--bg);border-color:var(--fg)} input{font:inherit;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
details{margin-top:6px} pre{white-space:pre-wrap;font-size:13px;margin:4px 0;color:var(--mut)} a{color:inherit}
.tag{font-size:12px;border:1px solid var(--line);border-radius:10px;padding:0 8px}
</style></head><body><main>
<h1>Benchmark key check</h1>
<div class="mut" id="summary">Loading…</div>
<div id="root"></div>
</main><script>
const S = { items: [] };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
async function load() { S.items = await (await fetch("/items")).json(); render(); }
async function decide(decisions) {
  const r = await fetch("/decide", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ decisions }) });
  const j = await r.json(); if (j.error) alert(j.error); await load();
}
function cmp(v, k) { if (!v) return '<span class="mut">—</span>'; if (!k) return '<span class="v">' + esc(v) + "</span>"; return '<span class="v ' + (v === k ? "ok" : "bad") + '">' + esc(v) + "</span>"; }
function card(i) {
  const L = i.live || {}; const fr = L.fr || {}; const rg = L.regs || {};
  const pub = i.published && i.published.date;
  const done = i.check ? '<span class="tag">' + esc(i.check.decision) + (i.check.date ? " " + esc(i.check.date) : "") + "</span>" : "";
  const keyLabel = i.expect.kind === "moved" && !i.expect.moved ? "never moved" : (i.key_date || i.expect.kind);
  const actions = i.check ? '<button data-undo="' + esc(i.id) + '">Re-check</button>' :
    '<button class="primary" data-keep="' + esc(i.id) + '">Key is right</button>' +
    (fr.close && fr.close !== i.key_date && i.key_date ? '<button data-set="' + esc(i.id) + '" data-date="' + esc(fr.close) + '">Use FR ' + esc(fr.close) + "</button>" : "") +
    (rg.close && rg.close !== i.key_date && i.key_date ? '<button data-set="' + esc(i.id) + '" data-date="' + esc(rg.close) + '">Use portal ' + esc(rg.close) + "</button>" : "") +
    (i.key_date ? '<input type="date" id="d-' + esc(i.id) + '"><button data-custom="' + esc(i.id) + '">Set</button>' : "") +
    '<button data-drop="' + esc(i.id) + '">Drop</button>';
  return '<div class="card ' + (i.check ? "done" : "") + '">' +
    '<div class="row"><b>' + esc(i.refs.fr_document_number || i.refs.regs_document_id) + "</b>" +
    '<span class="tag">' + esc(i.stratum) + "</span>" + done +
    (fr.url ? '<a href="' + esc(fr.url) + '" target="_blank">Federal Register ↗</a>' : "") +
    (rg.url ? '<a href="' + esc(rg.url) + '" target="_blank">Regulations.gov ↗</a>' : "") + "</div>" +
    '<div class="mut">' + esc(fr.title || rg.title || "") + "</div>" +
    '<div class="grid"><span class="mut">Key</span><span class="v">' + esc(keyLabel) + "</span>" +
    '<span class="mut">DocketClock published</span><span>' + cmp(pub, i.key_date) + "</span>" +
    '<span class="mut">FR today</span><span>' + (fr.error ? '<span class="warn">' + esc(fr.error) + "</span>" : cmp(fr.close, i.key_date)) + "</span>" +
    '<span class="mut">Portal today</span><span>' + (rg.error ? '<span class="warn">' + esc(rg.error) + "</span>" : cmp(rg.close, i.key_date) + (rg.withdrawn ? ' <span class="warn">withdrawn</span>' : "")) + "</span>" +
    '<span class="mut">Key source</span><span class="mut">' + esc(i.key_note) + "</span></div>" +
    (fr.dates ? "<details><summary>FR DATES text</summary><pre>" + esc(fr.dates) + "</pre></details>" : "") +
    '<div class="row" style="margin-top:8px">' + actions + "</div></div>";
}
function render() {
  const open = S.items.filter((i) => !i.check);
  const groups = [
    ["Disagree with a live source", open.filter((i) => i.agreement === "disagree")],
    ["History questions (live sources can't show history: read the note)", open.filter((i) => i.agreement === "history")],
    ["No live value", open.filter((i) => i.agreement === "no-live")],
    ["Both live sources agree with the key", open.filter((i) => i.agreement === "agree")],
    ["Done", S.items.filter((i) => i.check)],
  ];
  document.getElementById("summary").textContent = open.length + " to check, " + (S.items.length - open.length) + " done. Saved to the key file as you go.";
  document.getElementById("root").innerHTML = groups.filter(([, xs]) => xs.length).map(([t, xs]) =>
    "<section><h2>" + esc(t) + " · " + xs.length + "</h2>" +
    (t.startsWith("Both") ? '<button class="primary" id="keepall">Confirm all ' + xs.length + " where both agree</button>" : "") +
    xs.map(card).join("") + "</section>").join("");
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.id === "keepall") return decide(S.items.filter((i) => !i.check && i.agreement === "agree").map((i) => ({ id: i.id, decision: "keep", note: "both live sources agree" })));
  if (b.dataset.keep) return decide([{ id: b.dataset.keep, decision: "keep" }]);
  if (b.dataset.set) return decide([{ id: b.dataset.set, decision: "set", date: b.dataset.date }]);
  if (b.dataset.custom) { const v = document.getElementById("d-" + b.dataset.custom).value; if (!v) return; return decide([{ id: b.dataset.custom, decision: "set", date: v }]); }
  if (b.dataset.drop) { const note = prompt("Why drop it? (optional)") ?? ""; return decide([{ id: b.dataset.drop, decision: "drop", note }]); }
  if (b.dataset.undo) return decide([{ id: b.dataset.undo, decision: "reopen" }]);
});
load();
</script></body></html>`;
