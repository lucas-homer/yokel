#!/usr/bin/env node
// data-showcase.mjs — a partner-facing LIVE DASHBOARD over the docketclock database, for demos.
// Companion to docs/presentations/docketclock-conservation-brief.html (the pitch deck): the deck
// explains the idea; this shows the actual data — real open comment windows, deadline movements,
// source conflicts, and the accuracy ledger.
//
//   node tools/data-showcase.mjs             serve the live dashboard on http://localhost:8090
//                                            (the pitch deck rides along at /deck — one URL to
//                                            share, e.g. via `tailscale funnel 8090`)
//   node tools/data-showcase.mjs export      write a static snapshot for email/offline demo
//                                            (docs/presentations/docketclock-data-showcase.html)
//
// Serve mode re-queries the database (30s server-side cache) and the page refetches /data.json
// every 60s — leave it open during a call and it stays current. Export mode bakes the same page
// with the data inlined and no polling.
//
// Reads the CNPG pod (docketclock-pg-1) via `kubectl exec psql` — read-only queries only.
// Deliberately dependency-free (plain node + kubectl), matching the loose-script convention of
// tools/. Not wired into CI: it needs the live cluster, and its output is a demo artifact.

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const PRESENTATIONS_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "docs/presentations",
);
const EXPORT_PATH = join(PRESENTATIONS_DIR, "docketclock-data-showcase.html");
const DECK_PATH = join(
  PRESENTATIONS_DIR,
  "docketclock-conservation-brief.html",
);
const PORT = 8090;

// Environment-and-lands agencies — used server-side to pick the deep-dive exhibit and client-side
// for the default filter + bar highlighting. Kept as ONE source string, embedded into the page.
const ENV_RE_SRC =
  "environmental protection|interior|fish and wildlife|oceanic|forest|land management|engineers|agriculture|energy|reclamation|national park|geological|surface mining|council on environmental";
const ENV_RE = new RegExp(ENV_RE_SRC, "i");

// CNPG mints new pod ordinals on failover/reprovision (a post-drill cluster can be pg-2), so
// resolve the CURRENT primary like the runbooks do rather than hardcoding pg-1. Cached for the
// process lifetime; falls back to pg-1 if the Cluster resource is unreadable.
let PG_POD = null;
function pgPod() {
  if (!PG_POD) {
    try {
      PG_POD =
        execFileSync(
          "kubectl",
          [
            "-n",
            "docketclock",
            "get",
            "cluster",
            "docketclock-pg",
            "-o",
            "jsonpath={.status.currentPrimary}",
          ],
          { encoding: "utf8" },
        ).trim() || "docketclock-pg-1";
    } catch {
      PG_POD = "docketclock-pg-1";
    }
  }
  return PG_POD;
}

function sql(query) {
  const out = execFileSync(
    "kubectl",
    [
      "-n",
      "docketclock",
      "exec",
      "-i",
      pgPod(),
      "-c",
      "postgres",
      "--",
      "psql",
      "-U",
      "postgres",
      "-d",
      "docketclock",
      "-At",
    ],
    { input: query, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
  ).trim();
  return out ? JSON.parse(out) : null;
}

// Latest Federal Register metadata per document — title/agency/link for human-facing rows.
const FR_CTE = `with fr as (
  select distinct on (fr_document_number)
    fr_document_number, raw->>'title' as title, raw->'agencies'->0->>'name' as agency,
    (select string_agg(a->>'name', ' / ')
       from jsonb_array_elements(raw->'agencies') a) as agencies_all,
    raw->>'html_url' as url
  from observations where source='federal_register'
  order by fr_document_number, fetched_at desc)`;

function collectData() {
  const stats = sql(`select json_build_object(
    'windows',      (select count(*) from participation_windows),
    'observations', (select count(*) from observations),
    'open',         (select count(*) from participation_windows where status='open'),
    'closing30',    (select count(*) from participation_windows
                       where status='open' and resolved_close_utc between now() and now()+interval '30 days'),
    'moved',        (select count(*) from participation_windows where jsonb_array_length(change_history)>0),
    'conflicts',    (select count(*) from conflict_records),
    'verified_ok',  (select count(*) from accuracy_records where was_correct is true),
    'verified_bad', (select count(*) from accuracy_records where was_correct is false),
    'unverified',   (select count(*) from accuracy_records where was_correct is null),
    'agencies',     (select count(distinct a->>'name')
                       from observations, jsonb_array_elements(raw->'agencies') a
                       where source='federal_register'))`);

  const closing = sql(`${FR_CTE}
    select coalesce(json_agg(r), '[]'::json) from (
      select w.ocd_id, fr.agency, fr.agencies_all, fr.title, fr.url,
             w.resolved_close_utc as close_utc, w.resolved_close_display as display,
             w.confidence, w.submission_url, jsonb_array_length(w.change_history) as moved
      from participation_windows w join fr on fr.fr_document_number = w.fr_document_number
      where w.status='open' and w.resolved_close_utc between now() and now()+interval '45 days'
      order by w.resolved_close_utc asc limit 400) r`);

  const moved = sql(`${FR_CTE}
    select coalesce(json_agg(r), '[]'::json) from (
      select w.ocd_id, fr.agency, fr.title, fr.url,
             (w.change_history->-1->>'resolved_close_utc') as old_close,
             (w.change_history->-1->>'changed_at') as changed_at,
             w.resolved_close_utc as new_close, w.resolved_close_display as display, w.confidence
      from participation_windows w join fr on fr.fr_document_number = w.fr_document_number
      where w.status='open' and jsonb_array_length(w.change_history) > 0
        and w.resolved_close_utc is not null and (w.change_history->-1->>'resolved_close_utc') is not null
      order by w.resolved_close_utc asc limit 30) r`);

  const conflicts = sql(`${FR_CTE}
    select coalesce(json_agg(r), '[]'::json) from (
      select w.ocd_id, fr.agency, fr.title, fr.url, w.resolved_close_utc as close_utc,
             w.raw_fr_close_date, w.raw_regs_close_datetime, w.resolved_close_display as display
      from participation_windows w join fr on fr.fr_document_number = w.fr_document_number
      where w.status='open' and w.confidence='conflicting'
      order by w.derived_at desc limit 12) r`);

  const agencyCounts = sql(`${FR_CTE}
    select coalesce(json_agg(r), '[]'::json) from (
      select fr.agency, count(*)::int as n
      from participation_windows w join fr on fr.fr_document_number = w.fr_document_number
      where w.status='open' and fr.agency is not null
      group by fr.agency order by n desc limit 12) r`);

  // Deep-dive exhibit: prefer an open, environment-adjacent window whose deadline moved.
  const pick =
    (moved || []).find((m) => ENV_RE.test(m.agency || "")) ||
    (moved || [])[0] ||
    null;
  let dive = null;
  if (pick) {
    const obs = sql(`select coalesce(json_agg(r), '[]'::json) from (
      select source, fetched_at, is_extension, is_correction,
             left(raw_dates_text, 300) as dates_text
      from observations where ocd_id='${pick.ocd_id.replace(/'/g, "''")}'
      order by fetched_at asc) r`);
    dive = { ...pick, obs };
  }

  return {
    generatedAt: new Date().toISOString(),
    stats,
    closing,
    moved,
    conflicts,
    agencyCounts,
    dive,
  };
}

// Per-record drill-down for the click-a-row paper trail (serve mode only).
function collectWindowDetail(ocdId) {
  if (!/^[A-Za-z0-9/_.:-]+$/.test(ocdId)) throw new Error("bad ocd id");
  const lit = `'${ocdId}'`;
  const win = sql(`${FR_CTE}
    select row_to_json(r) from (
      select w.ocd_id, fr.agency, fr.agencies_all, fr.title, fr.url,
             w.confidence, w.status, w.resolved_close_display as display,
             w.resolved_close_utc as close_utc, w.raw_fr_close_date, w.raw_regs_close_datetime,
             w.fr_document_number, w.regs_document_id, w.submission_url, w.conflict_flags,
             (w.change_history->-1->>'resolved_close_utc') as old_close,
             (w.change_history->-1->>'changed_at') as changed_at
      from participation_windows w
      left join fr on fr.fr_document_number = w.fr_document_number
      where w.ocd_id = ${lit}) r`);
  if (!win) return null;
  const obs = sql(`select coalesce(json_agg(r), '[]'::json) from (
    select source, fetched_at, is_extension, is_correction,
           left(raw_dates_text, 300) as dates_text
    from observations where ocd_id = ${lit}
    order by fetched_at asc) r`);
  return { ...win, obs };
}

// ── the page — a static shell; ALL data sections are rendered client-side from a data object, so
// the same code path serves the live dashboard (polls /data.json) and the baked export. ─────────
function renderPage(data, { live }) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>DocketClock — live data dashboard</title>
<style>
  :root {
    --ink:#1a2332; --ink-soft:#4a5568; --paper:#faf8f4; --card:#fff;
    --accent:#1f6f54; --accent-soft:#e6f2ec; --warn:#b45309; --warn-soft:#fdf3e3;
    --rule:#e2ddd3; --mono:"SF Mono",ui-monospace,Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Georgia,serif;background:var(--paper);color:var(--ink);line-height:1.5}
  main{max-width:1080px;margin:0 auto;padding:3.5rem 5vw 6rem}
  section{margin-top:4rem}
  .kicker{font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:.7rem}
  h1{font-size:clamp(1.9rem,4.5vw,3rem);line-height:1.12;letter-spacing:-.01em}
  h2{font-size:clamp(1.35rem,3vw,2rem);margin-bottom:.5rem;letter-spacing:-.01em}
  .sub{color:var(--ink-soft);max-width:52em;margin-bottom:1.4rem}
  .livebar{position:fixed;top:0;left:0;right:0;z-index:10;display:flex;gap:.7rem;align-items:center;justify-content:center;background:var(--ink);color:#e8ecf3;font-size:.8rem;padding:.35rem 1rem}
  .livebar .pulse{width:9px;height:9px;border-radius:50%;background:#3ddc84;animation:pulse 2s infinite}
  .livebar.stale .pulse{background:var(--warn);animation:none}
  .livebar .deck-link{color:#a7d3c2;text-decoration:none;border-bottom:1px dotted #a7d3c2;margin-left:.6rem}
  .livebar .deck-link:hover{color:#fff}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  body.live main{padding-top:5rem}
  .statgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.9rem;margin-top:1.8rem}
  .stat{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:.95rem 1.05rem}
  .stat b{display:block;font-size:1.7rem;color:var(--accent);letter-spacing:-.01em}
  .stat.amber b{color:var(--warn)}
  .stat span{font-size:.82rem;color:var(--ink-soft)}
  .badge{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;border-radius:99px;padding:.12rem .55rem;vertical-align:middle}
  .b-high{background:var(--accent-soft);color:var(--accent)}
  .b-medium{background:#e8effa;color:#2b5ea7}
  .b-low{background:#eee9df;color:#6b6350}
  .b-conflicting{background:var(--warn-soft);color:var(--warn)}
  .bars{margin-top:1rem;display:grid;gap:.45rem}
  .bar{display:grid;grid-template-columns:230px 1fr 3ch;gap:.7rem;align-items:center;font-size:.88rem}
  .bar .track{background:#efece5;border-radius:6px;height:16px;overflow:hidden}
  .bar .fill{background:var(--accent);height:100%;border-radius:6px;transition:width .6s}
  .bar.dim .fill{background:#b9c5bf}
  .bar em{color:var(--ink-soft);font-style:normal;text-align:right}
  .controls{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.1rem 0 .9rem;align-items:center}
  .controls button{font:inherit;font-size:.85rem;border:1px solid var(--rule);background:var(--card);border-radius:99px;padding:.32rem .95rem;cursor:pointer;color:var(--ink)}
  .controls button.on{background:var(--accent);border-color:var(--accent);color:#fff}
  .controls input{font:inherit;font-size:.85rem;border:1px solid var(--rule);border-radius:8px;padding:.35rem .7rem;flex:1;min-width:180px;background:var(--card)}
  table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--rule);border-radius:10px;overflow:hidden;font-size:.88rem}
  th{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);text-align:left;padding:.55rem .8rem;border-bottom:1px solid var(--rule);background:#f4f1ea}
  td{padding:.55rem .8rem;border-bottom:1px solid var(--rule);vertical-align:top}
  tr:last-child td{border-bottom:none}
  td a{color:var(--ink);text-decoration:none;border-bottom:1px dotted var(--accent)}
  td a:hover{color:var(--accent)}
  .days{font-weight:700;white-space:nowrap}
  .days.soon{color:var(--warn)}
  .agency{font-size:.75rem;color:var(--ink-soft);display:block}
  .movedflag{color:var(--warn);font-weight:700;font-size:.78rem;white-space:nowrap}
  tr.row{cursor:pointer}
  tr.row:hover td{background:#f7f4ee}
  tr.detail td{background:#f7f4ee;padding:1rem 1.2rem}
  .detail-box .why{font-size:.9rem;max-width:60em;margin-bottom:.6rem}
  .detail-box .vs{max-width:34em}
  .detail-box .timeline{margin-top:1rem}
  .detail-box .ids{margin-top:.9rem;font-family:var(--mono);font-size:.72rem;color:var(--ink-soft)}
  .detail-box .ids a{color:var(--accent)}
  .cards{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));margin-top:1rem}
  .card{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--warn);border-radius:10px;padding:1rem 1.1rem;font-size:.92rem}
  .card h3{font-size:.98rem;margin:.15rem 0 .5rem}
  .card h3 a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--accent)}
  .shift{font-family:var(--mono);font-size:.85rem;background:var(--warn-soft);border-radius:8px;padding:.5rem .7rem;margin-top:.4rem}
  .shift b{color:var(--warn)}
  .vs{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin-top:.5rem;font-size:.84rem}
  .vs div{background:#f4f1ea;border-radius:8px;padding:.45rem .65rem}
  .vs b{display:block;font-size:.7rem;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-soft)}
  .vs .date{font-family:var(--mono)}
  .resolved{margin-top:.5rem;font-size:.85rem;color:var(--accent);font-weight:600}
  .dive{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:1.4rem 1.6rem;margin-top:1rem}
  .dive-head h3{font-size:1.15rem;margin:.2rem 0 .4rem}
  .dive-head h3 a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--accent)}
  .dive-head p{font-size:.92rem;color:var(--ink-soft)}
  .timeline{list-style:none;margin-top:1.2rem;border-left:2px solid var(--rule);padding-left:1.3rem;display:grid;gap:.7rem}
  .timeline li{position:relative;font-size:.92rem}
  .timeline li::before{content:"";position:absolute;left:-1.65rem;top:.35rem;width:9px;height:9px;border-radius:50%;background:var(--accent)}
  .timeline li.quiet{color:var(--ink-soft);font-size:.85rem}
  .timeline li.quiet::before{background:var(--rule)}
  .timeline li.hot{background:var(--warn-soft);border-radius:8px;padding:.55rem .8rem;margin-left:-.3rem}
  .timeline li.hot::before{background:var(--warn);left:-1.35rem}
  .when{display:block;font-size:.74rem;letter-spacing:.05em;color:var(--ink-soft);font-family:var(--mono)}
  .honesty{background:var(--accent-soft);border-radius:12px;padding:1.3rem 1.5rem;margin-top:1rem}
  .honesty p{max-width:56em}
  footer{margin-top:5rem;padding-top:1rem;border-top:1px solid var(--rule);font-size:.8rem;color:var(--ink-soft)}
  footer code{font-family:var(--mono)}
  .empty{color:var(--ink-soft);font-style:italic;padding:1rem}
</style>
</head>
<body class="${live ? "live" : ""}">
${live ? `<div class="livebar" id="livebar"><span class="pulse"></span><span>LIVE — reading the DocketClock database</span><span id="freshness"></span><a class="deck-link" href="/deck">the presentation ↗</a></div>` : ""}
<main>
  <div class="kicker">DocketClock · ${live ? "live data dashboard" : "data snapshot"}</div>
  <h1>Explore live data</h1>
  <p class="sub" style="margin-top:.8rem">Every number and record on this page comes straight from DocketClock's database — the same system that has been watching the Federal Register and Regulations.gov around the clock. Nothing is mocked.</p>

  <div class="statgrid" id="stats"></div>

  <section>
    <div class="kicker">Who's asking for comments</div>
    <h2>Open windows by agency</h2>
    <p class="sub">Environment-and-lands agencies highlighted in green — this is the slice a conservation coalition would watch.</p>
    <div class="bars" id="bars"></div>
  </section>

  <section>
    <div class="kicker">The radar</div>
    <h2>Closing soon — the next 45 days</h2>
    <p class="sub">Each row is a live federal comment window: verified deadline, confidence grade, and a link to the official notice. Try the environment filter — this is the default view a conservation partner would see.${live ? " <b>Click any row to open its full paper trail</b> — every observation, both sources' raw dates, and why it earned its confidence grade." : ""}</p>
    <div class="controls">
      <button id="f-env" class="on">🌲 Environment &amp; lands</button>
      <button id="f-all">All agencies</button>
      <input id="f-q" type="search" placeholder="Search titles &amp; agencies (try: water, wildlife, energy…)" />
      <span id="f-count" style="font-size:.82rem;color:var(--ink-soft)"></span>
    </div>
    <table>
      <thead><tr><th style="width:7ch">Closes</th><th>Window</th><th style="width:12ch">Deadline</th><th style="width:10ch">Confidence</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </section>

  <section>
    <div class="kicker">The headline value</div>
    <h2>Deadlines that moved — and the system caught it</h2>
    <p class="sub">These open windows changed their close date after publication. Anyone working from the original notice has the wrong deadline; DocketClock kept the receipt for both dates.</p>
    <div class="cards" id="moved"></div>
  </section>

  <section>
    <div class="kicker">When the government disagrees with itself</div>
    <h2>Live source conflicts, shown honestly</h2>
    <p class="sub">For these open windows, the Federal Register and Regulations.gov currently publish different dates. DocketClock never guesses silently: it shows both, side by side, and explains what it resolved and why.</p>
    <div class="cards" id="conflicts"></div>
  </section>

  <section>
    <div class="kicker">One window, under the microscope</div>
    <h2>The paper trail behind a single deadline</h2>
    <p class="sub">This is what "watched until it closes" actually means — every claim traceable to an official source, every change kept forever.</p>
    <div id="dive"></div>
  </section>

  <section>
    <div class="kicker">Grading our own homework</div>
    <h2>The accuracy ledger</h2>
    <div class="statgrid" id="accuracy"></div>
    <div class="honesty">
      <p><b>Why the third number matters:</b> most tools would quietly claim every record as a success. DocketClock only counts a window as "correct" when it can prove it against the source after close. The unverifiable ones stay on the books, labeled — because a trust product that grades on a curve isn't one.</p>
    </div>
  </section>

  <footer id="foot"></footer>
</main>

<script>
const LIVE = ${live};
const ENV_RE = new RegExp(${JSON.stringify(ENV_RE_SRC)}, "i");
let DATA = ${
    // Upstream FR/Regs content is embedded inside a <script> block; a literal "</script>" in any
    // title/DATES text would break out of it. <-escape "<" — JSON.parse-identical, XSS-inert.
    // (This page is deliberately funnel-exposed, so harden even the unlikely case.)
    JSON.stringify(data).replace(/</g, "\\u003c")
  };
let lastFetch = Date.now();

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const day = (iso) => (iso ? iso.slice(0, 10) : "—");
// Comment-close timestamps are end-of-day EASTERN stored as UTC (…T03:59:59Z lands on the NEXT
// UTC day) — slicing the UTC string reproduces the exact off-by-one this product exists to
// prevent. Render close dates in America/New_York, like the product does.
const closeDay = (iso) => iso ? new Date(iso).toLocaleDateString("en-CA", { timeZone: "America/New_York" }) : "—";
const dayDiff = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
const daysLeft = (iso) => Math.max(0, Math.ceil((new Date(iso) - Date.now()) / 86400000));
// Some display strings (the FR-only "11:59 p.m. ET (inferred from FR date-only value)") carry the
// time + provenance but NO calendar date — the date lives in close_utc. Prefix it so a reader is
// never left guessing which day a deadline falls on.
const displayWithDate = (display, closeUtc) => {
  const d = (display || "").replace(/^closes /, "");
  return /\\d{4}-\\d{2}-\\d{2}/.test(d) || !closeUtc ? d : closeDay(closeUtc) + " · " + d;
};

let envOnly = true;
const $ = (id) => document.getElementById(id);

function renderStats() {
  const s = DATA.stats;
  $("stats").innerHTML = [
    [s.windows, "comment windows tracked"],
    [s.open, "open right now"],
    [s.closing30, "closing in the next 30 days"],
    [s.moved, "deadlines that MOVED after publication", "amber"],
    [s.conflicts, "source disagreements caught & published", "amber"],
    [s.observations, "raw observations in the audit log"],
  ].map(([n, label, cls]) =>
    \`<div class="stat \${cls || ""}"><b>\${n.toLocaleString()}</b><span>\${label}</span></div>\`).join("");
}

function renderBars() {
  const max = Math.max(...DATA.agencyCounts.map((a) => a.n), 1);
  $("bars").innerHTML = DATA.agencyCounts.map((a) =>
    \`<div class="bar \${ENV_RE.test(a.agency) ? "" : "dim"}"><span>\${esc(a.agency)}</span><div class="track"><div class="fill" style="width:\${Math.round((a.n / max) * 100)}%"></div></div><em>\${a.n}</em></div>\`).join("");
}

function renderTable() {
  const needle = $("f-q").value.trim().toLowerCase();
  const view = DATA.closing.filter((w) =>
    (!envOnly || ENV_RE.test(w.agencies_all || w.agency || "")) &&
    (!needle || (w.title + " " + (w.agencies_all || w.agency)).toLowerCase().includes(needle)));
  $("rows").innerHTML = view.slice(0, 120).map((w) => {
    const d = daysLeft(w.close_utc);
    return \`<tr \${LIVE ? \`class="row" data-ocd="\${esc(w.ocd_id)}" title="click for the full paper trail"\` : ""}>
      <td class="days \${d <= 7 ? "soon" : ""}">\${d}d</td>
      <td><span class="agency">\${esc(w.agencies_all || w.agency)}</span><a href="\${esc(w.url)}" target="_blank" rel="noopener">\${esc(w.title)}</a>
          \${w.moved > 0 ? '<span class="movedflag"> · deadline moved!</span>' : ""}</td>
      <td>\${esc(displayWithDate(w.display, w.close_utc))}</td>
      <td><span class="badge b-\${esc(w.confidence)}">\${esc(w.confidence)}</span></td>
    </tr>\`;
  }).join("") || '<tr><td colspan="4" class="empty">no matches</td></tr>';
  $("f-count").textContent = view.length + " windows" + (view.length > 120 ? " (showing first 120)" : "");
}

function renderMoved() {
  $("moved").innerHTML = DATA.moved.slice(0, 9).map((m) => \`
    <div class="card">
      <span class="agency">\${esc(m.agency)}</span>
      <h3><a href="\${esc(m.url)}" target="_blank" rel="noopener">\${esc(m.title)}</a></h3>
      <div class="shift">\${closeDay(m.old_close)} → <b>\${closeDay(m.new_close)}</b> &nbsp;(+\${dayDiff(m.old_close, m.new_close)} days)</div>
    </div>\`).join("") || '<p class="empty">none open right now</p>';
}

function renderConflicts() {
  $("conflicts").innerHTML = DATA.conflicts.slice(0, 6).map((c) => \`
    <div class="card">
      <span class="agency">\${esc(c.agency)}</span>
      <h3><a href="\${esc(c.url)}" target="_blank" rel="noopener">\${esc(c.title)}</a></h3>
      <div class="vs">
        <div><b>Federal Register says</b><span class="date">\${esc(c.raw_fr_close_date ?? "—")}</span></div>
        <div><b>Regulations.gov says</b><span class="date">\${esc((c.raw_regs_close_datetime ?? "—").slice(0, 10))}</span></div>
      </div>
      <div class="resolved">→ \${esc(c.display ? displayWithDate(c.display, c.close_utc) : "unresolved — flagged for human review")}</div>
    </div>\`).join("") || '<p class="empty">none open right now</p>';
}

// Shared paper-trail renderer: used by the deep-dive exhibit AND the click-a-row drill-down.
// rec: { obs, changed_at?, old_close?, new_close?|close_utc?, display, status? }
function buildTimelineHTML(rec) {
  const newClose = rec.new_close || rec.close_utc;
  const hasChange = rec.changed_at && rec.old_close && newClose;
  const events = [];
  const seen = new Set();
  let routine = 0;
  const flushRoutine = () => {
    if (routine > 0) events.push({ cls: "quiet", when: "", what: \`\${routine} routine re-check\${routine > 1 ? "s" : ""} — no change, silently verified\` });
    routine = 0;
  };
  let changeEmitted = !hasChange;
  const changeEvent = hasChange ? {
    cls: "hot", when: day(rec.changed_at),
    what: \`<b>Deadline change caught:</b> close moved \${closeDay(rec.old_close)} → \${closeDay(newClose)} (<b>+\${dayDiff(rec.old_close, newClose)} days</b> for the public to act). The superseded date is kept forever in the window's change history.\`,
  } : null;
  for (const o of rec.obs) {
    const src = o.source === "federal_register" ? "Federal Register" : "Regulations.gov";
    if (!changeEmitted && new Date(o.fetched_at) >= new Date(rec.changed_at)) {
      flushRoutine(); events.push(changeEvent); changeEmitted = true;
    }
    if (!seen.has(o.source)) {
      flushRoutine();
      seen.add(o.source);
      events.push({
        cls: "beat", when: day(o.fetched_at),
        what: \`First sighting on <b>\${src}</b>\` +
          (o.dates_text ? \` — verbatim legal DATES text captured: <em>“\${esc(o.dates_text)}\${o.dates_text.length >= 300 ? "…" : ""}”</em>\` : ""),
      });
    } else if (o.is_extension || o.is_correction) {
      flushRoutine();
      events.push({ cls: "beat", when: day(o.fetched_at), what: \`\${o.is_extension ? "Extension" : "Correction"} notice detected on <b>\${src}</b>\` });
    } else routine++;
  }
  flushRoutine();
  if (!changeEmitted) events.push(changeEvent);
  const stillOpen = (rec.status ?? "open") === "open";
  events.push({
    cls: "beat", when: day(DATA.generatedAt),
    what: stillOpen
      ? \`Still open, still watched — current deadline <b>\${esc(displayWithDate(rec.display, newClose))}</b>.\`
      : \`Status now: <b>\${esc(rec.status)}</b>.\`,
  });
  return \`<ol class="timeline">
    \${events.map((e) => \`<li class="\${e.cls}"><span class="when">\${e.when}</span><span>\${e.what}</span></li>\`).join("")}
  </ol>\`;
}

// Plain-language account of how the rulebook arrived at a confidence grade, from the record itself.
function explainConfidence(d) {
  const flags = (d.conflict_flags || []).join(", ");
  switch (d.confidence) {
    case "high":
      return "Both sources carry this window and agree on the same Eastern calendar date — the strongest signal the rulebook awards.";
    case "medium":
      return "One usable source with no contradiction (or full agreement with a minor caveat" + (flags ? \`: \${flags}\` : "") + "). Reliable, but not independently confirmed.";
    case "low":
      return d.regs_document_id
        ? \`Regulations.gov lists this record but supplies no usable close date\${flags ? \` (\${flags})\` : ""}, so the deadline rests on the Federal Register's date-only value with the standard 11:59 p.m. ET convention. LOW means: correct as far as one source goes — verify before relying on it.\`
        : "Only the Federal Register carries this notice — there is no Regulations.gov record to cross-check (common for information-collection notices where comments go to OMB or an email address instead). The closing time is inferred from a date-only value via the 11:59 p.m. ET convention. LOW means: correct as far as one source goes — verify before relying on it.";
    case "conflicting":
      return "The two sources currently disagree about this window. Both values are kept and shown; nothing is guessed silently.";
    default:
      return "Neither source supplies a usable close date, so no deadline is asserted at all — an honest unknown beats a fabricated date.";
  }
}

function renderDive() {
  const dive = DATA.dive;
  if (!dive) { $("dive").innerHTML = '<p class="empty">no exhibit available right now</p>'; return; }
  $("dive").innerHTML = \`
    <div class="dive">
      <div class="dive-head">
        <span class="agency">\${esc(dive.agency)}</span>
        <h3><a href="\${esc(dive.url)}" target="_blank" rel="noopener">\${esc(dive.title)}</a></h3>
        <p>Currently: <b>\${esc(displayWithDate(dive.display, dive.new_close))}</b> · confidence <span class="badge b-\${esc(dive.confidence)}">\${esc(dive.confidence)}</span> · \${dive.obs.length} observations on file</p>
      </div>
      \${buildTimelineHTML(dive)}
    </div>\`;
}

function renderAccuracy() {
  const s = DATA.stats;
  const total = s.verified_ok + s.verified_bad;
  $("accuracy").innerHTML = \`
    <div class="stat"><b>\${total.toLocaleString()}</b><span>closed windows independently re-verified after the fact</span></div>
    <div class="stat"><b>\${s.verified_ok.toLocaleString()} / \${total.toLocaleString()}</b><span>had published the correct deadline</span></div>
    <div class="stat amber"><b>\${s.unverified.toLocaleString()}</b><span>couldn't be re-verified — labeled honestly, never counted as wins</span></div>\`;
}

function renderFoot() {
  const s = DATA.stats;
  $("foot").innerHTML = \`\${LIVE ? "Live from" : "Generated <b>" + DATA.generatedAt.slice(0, 16).replace("T", " ") + " UTC</b> from"} the DocketClock database
    (\${s.observations.toLocaleString()} observations across \${s.agencies} federal agencies) ·
    \${LIVE ? "dashboard: <code>node tools/data-showcase.mjs</code>" : "regenerate: <code>node tools/data-showcase.mjs export</code>"} · DocketClock · lucas.homer@gmail.com\`;
}

function renderAll() {
  renderStats(); renderBars(); renderTable(); renderMoved();
  renderConflicts(); renderDive(); renderAccuracy(); renderFoot();
}

$("f-env").onclick = () => { envOnly = true;  $("f-env").classList.add("on"); $("f-all").classList.remove("on"); renderTable(); };
$("f-all").onclick = () => { envOnly = false; $("f-all").classList.add("on"); $("f-env").classList.remove("on"); renderTable(); };
$("f-q").oninput = renderTable;
renderAll();

// ── click-a-row drill-down (serve mode only — needs /window.json) ────────────────────────────────
const detailCache = new Map();
if (LIVE) $("rows").addEventListener("click", async (e) => {
  if (e.target.closest("a")) return;             // let source links behave normally
  const tr = e.target.closest("tr.row");
  if (!tr) return;
  const open = tr.nextElementSibling?.classList.contains("detail");
  document.querySelectorAll("tr.detail").forEach((d) => d.remove());
  if (open) return;                              // second click closes
  const ocd = tr.dataset.ocd;
  const cell = document.createElement("tr");
  cell.className = "detail";
  cell.innerHTML = '<td colspan="4"><p class="empty">pulling the paper trail…</p></td>';
  tr.after(cell);
  try {
    if (!detailCache.has(ocd)) {
      const r = await fetch("/window.json?ocd=" + encodeURIComponent(ocd));
      if (!r.ok) throw new Error(r.status);
      detailCache.set(ocd, await r.json());
    }
    const d = detailCache.get(ocd);
    cell.innerHTML = \`<td colspan="4">
      <div class="detail-box">
        <p class="why"><b>Why \${esc(d.confidence)} confidence:</b> \${esc(explainConfidence(d))}</p>
        <div class="vs">
          <div><b>Federal Register says</b><span class="date">\${esc(d.raw_fr_close_date ?? "no usable date")}</span></div>
          <div><b>Regulations.gov says</b><span class="date">\${esc(d.raw_regs_close_datetime ? d.raw_regs_close_datetime.slice(0, 10) : (d.regs_document_id ? "no usable date" : "no record found"))}</span></div>
        </div>
        \${buildTimelineHTML(d)}
        <p class="ids">\${esc(d.ocd_id)} · FR \${esc(d.fr_document_number ?? "—")} · Regs \${esc(d.regs_document_id ?? "—")}\${d.submission_url ? \` · <a href="\${esc(d.submission_url)}" target="_blank" rel="noopener">comment here</a>\` : ""}</p>
      </div>
    </td>\`;
  } catch {
    cell.innerHTML = '<td colspan="4"><p class="empty">could not load details — is the cluster reachable?</p></td>';
  }
});

if (LIVE) {
  const freshness = $("freshness");
  setInterval(() => {
    const age = Math.round((Date.now() - lastFetch) / 1000);
    freshness.textContent = \`· data as of \${new Date(DATA.generatedAt).toLocaleTimeString()} · checked \${age}s ago\`;
  }, 1000);
  setInterval(async () => {
    try {
      const r = await fetch("/data.json");
      if (!r.ok) throw new Error(r.status);
      DATA = await r.json();
      lastFetch = Date.now();
      $("livebar").classList.remove("stale");
      renderAll();  // filter/search state lives outside DATA and survives the refresh
    } catch {
      $("livebar").classList.add("stale");  // keep showing the last good data
    }
  }, 60_000);
}
</script>
</body>
</html>`;
}

// ── entrypoints ─────────────────────────────────────────────────────────────────────────────────
const mode = process.argv[2] || "serve";

if (mode === "export") {
  console.error("querying live database...");
  const data = collectData();
  writeFileSync(EXPORT_PATH, renderPage(data, { live: false }));
  console.error(`wrote ${EXPORT_PATH}`);
} else if (mode === "serve") {
  let cache = null; // { data, at }
  const CACHE_MS = 30_000;
  const getData = () => {
    if (!cache || Date.now() - cache.at > CACHE_MS) {
      cache = { data: collectData(), at: Date.now() };
    }
    return cache.data;
  };
  console.error("priming data from the live database...");
  getData();
  createServer((req, res) => {
    try {
      if (req.url.startsWith("/data.json")) {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify(getData()));
      } else if (req.url === "/deck" || req.url.startsWith("/deck?")) {
        // The pitch deck rides along on the same URL. The file stays standalone-clean for email;
        // the dashboard link is injected only when SERVED, so the shared funnel link covers both.
        const backLink =
          '<a href="/" style="position:fixed;top:1rem;right:1.2rem;z-index:20;font-size:.85rem;' +
          "color:#1f6f54;background:#fff;border:1px solid #e2ddd3;border-radius:99px;" +
          'padding:.35rem .95rem;text-decoration:none">live dashboard ↗</a>';
        const deck = readFileSync(DECK_PATH, "utf8").replace(
          "</body>",
          `${backLink}</body>`,
        );
        res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
        res.end(deck);
      } else if (req.url.startsWith("/window.json")) {
        const ocd = new URL(req.url, "http://x").searchParams.get("ocd") ?? "";
        const detail = collectWindowDetail(ocd);
        if (detail) {
          res.writeHead(200, { "content-type": "application/json" });
          res.end(JSON.stringify(detail));
        } else {
          res.writeHead(404).end("no such window");
        }
      } else if (req.url === "/" || req.url.startsWith("/?")) {
        res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
        res.end(renderPage(getData(), { live: true }));
      } else {
        res.writeHead(404).end("not found");
      }
    } catch (e) {
      // Serve stale data if we have it (kubectl hiccup mid-demo shouldn't blank the screen).
      if (cache) {
        res.writeHead(200, {
          "content-type": req.url.startsWith("/data.json")
            ? "application/json"
            : "text/html; charset=utf-8",
        });
        res.end(
          req.url.startsWith("/data.json")
            ? JSON.stringify(cache.data)
            : renderPage(cache.data, { live: true }),
        );
      } else {
        res.writeHead(500).end(`database unreachable: ${e.message}`);
      }
    }
  }).listen(PORT, () =>
    console.error(
      `dashboard live → http://localhost:${PORT}  (Ctrl-C to stop)`,
    ),
  );
} else {
  console.error("usage: node tools/data-showcase.mjs [serve|export]");
  process.exit(1);
}
