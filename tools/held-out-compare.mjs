#!/usr/bin/env node
// Held-out set comparison (shadow gate part 2, docs/runbooks/review-queue.md § Autopilot).
//
// Compares the operator's sealed held-out verdicts (written by tools/held-out-review.mjs) with
// the review autopilot's scheduled proposals in the shadow ledger, and prints the gate result:
// kinds agree on at least 9 of 10, and no false pins.
//
// Run it yourself, on the Mini. The autopilot (and any agent) must never read the held-out file,
// so do not paste this script's output into an agent session before the gate is decided.
//
//   node tools/held-out-compare.mjs --held-out ~/.config/yokel/review-autopilot/held-out-2026-10-31.json
//
// By default it writes a self-contained HTML report next to the sealed file
// (held-out-<date>.comparison.html, mode 0600, rewritten on every run), opens it in your
// browser, and prints a one-line summary.
//
// Options:
//   --held-out <path>   the sealed file (required)
//   --ledger <path>     default ~/.config/yokel/review-autopilot/ledger.jsonl
//   --policy <version>  default: the sealed file's policy_version (e.g. v1.3@2026-10-31)
//   --sha256 <hex>      the hash the workbench printed at seal time; checked if given
//   --html <path>       where to write the HTML report (default: next to the sealed file)
//   --no-open           write the report but don't open it
//   --no-fetch          don't look up document titles on the public Federal Register API
//   --text              print the plain-text report instead of writing HTML
//   --json              print machine-readable output instead of writing HTML
// Node 24, no dependencies. It reads the two files and writes only the HTML report.
//
// Rules applied (each is printed with the result):
// - A proposal counts if its ledger line has the same ocd_id, the same policy string,
//   "harness": null (a scheduled run, not a harness proposer) and a kind other than "skip".
//   The latest such line in the (append-only) ledger is the autopilot's answer.
// - Kinds agree when they are equal. The autopilot may never propose dismiss_conflict or
//   confirm_reopened (it must escalate instead), so where you chose one of those and it
//   escalated, that is a "forced escalate" and counts as agreement (runbook, part 2 "Scoring",
//   2026-11-03). The strict count is shown alongside for reference.
// - A false pin is a pin_close proposal where you did not pin, or pinned a different date. Any
//   false pin blocks the gate. A pin with a different date still agrees on kind.
// - An item with no counting proposal yet makes the result INCOMPLETE, not a pass or fail.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { rename, writeFile } from "node:fs/promises";
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

const FORBIDDEN_TO_AGENT = new Set(["dismiss_conflict", "confirm_reopened"]);
const PASS_MIN = 9;

function fail(msg) {
  process.stderr.write(`held-out-compare: ${msg}\n`);
  process.exit(2);
}

const expand = (p) => (p?.startsWith("~/") ? join(homedir(), p.slice(2)) : p);
const normId = (id) =>
  /^\d{4}-\d{5}$/.test(String(id ?? ""))
    ? `ocd-participation-window/federal/${id}`
    : String(id ?? "");
const docNum = (id) => id.split("/").pop();

export function loadHeldOut(text) {
  let doc;
  try {
    doc = JSON.parse(text);
  } catch (e) {
    throw new Error(`held-out file is not JSON: ${e.message}`);
  }
  const items = Array.isArray(doc) ? doc : doc?.items;
  if (!Array.isArray(items) || items.length === 0)
    throw new Error("held-out file has no items");
  const seen = new Set();
  const out = items.map((it, i) => {
    const ocd_id = normId(it?.ocd_id);
    if (!ocd_id) throw new Error(`held-out item ${i + 1} has no ocd_id`);
    if (seen.has(ocd_id))
      throw new Error(`held-out item ${ocd_id} appears twice`);
    seen.add(ocd_id);
    if (typeof it.kind !== "string" || !it.kind)
      throw new Error(`held-out item ${ocd_id} has no kind`);
    return {
      ocd_id,
      kind: it.kind,
      close: it.close ?? null,
      reason: it.reason ?? "",
    };
  });
  return {
    policy: Array.isArray(doc) ? null : (doc.policy_version ?? null),
    set_date: Array.isArray(doc) ? null : (doc.set_date ?? null),
    sealed_at: Array.isArray(doc) ? null : (doc.sealed_at ?? null),
    items: out,
  };
}

export function loadLedger(text) {
  const lines = [];
  const bad = [];
  text.split("\n").forEach((raw, i) => {
    if (!raw.trim()) return;
    try {
      lines.push({ ...JSON.parse(raw), _line: i + 1 });
    } catch {
      bad.push(i + 1);
    }
  });
  return { lines, bad };
}

export function compare(heldOut, ledgerLines, policy) {
  const rows = heldOut.items.map((mine) => {
    const counting = ledgerLines.filter(
      (l) =>
        normId(l.ocd_id) === mine.ocd_id &&
        l.policy === policy &&
        l.harness === null &&
        l.proposal &&
        typeof l.proposal.kind === "string" &&
        l.proposal.kind !== "skip",
    );
    const latest = counting.at(-1) ?? null;
    const skips = ledgerLines.filter(
      (l) =>
        normId(l.ocd_id) === mine.ocd_id &&
        l.policy === policy &&
        l.harness === null &&
        l.proposal?.kind === "skip",
    ).length;
    const otherPolicy = ledgerLines.filter(
      (l) =>
        normId(l.ocd_id) === mine.ocd_id &&
        l.policy !== policy &&
        l.harness === null &&
        l.proposal &&
        l.proposal.kind !== "skip",
    ).length;
    const harnessOnly = ledgerLines.filter(
      (l) =>
        normId(l.ocd_id) === mine.ocd_id &&
        l.harness !== null &&
        l.harness !== undefined,
    ).length;
    const history = counting.map((l) => l.proposal.kind);
    const changed = new Set(history).size > 1;
    let outcome;
    let falsePin = false;
    if (!latest) {
      outcome = "pending";
    } else {
      const a = latest.proposal;
      if (a.kind === "pin_close") {
        falsePin =
          mine.kind !== "pin_close" || (a.close ?? null) !== mine.close;
      }
      if (a.kind === mine.kind) outcome = "agree";
      else if (a.kind === "escalate" && FORBIDDEN_TO_AGENT.has(mine.kind))
        outcome = "forced-escalate";
      else outcome = "disagree";
    }
    return {
      ocd_id: mine.ocd_id,
      mine,
      agent: latest
        ? {
            kind: latest.proposal.kind,
            close: latest.proposal.close ?? null,
            run: latest.run ?? null,
            mode: latest.mode ?? null,
            verifier: latest.verifier?.result ?? null,
            verifier_model: latest.verifier?.model ?? null,
            reason: latest.reason ?? latest.proposal.reason ?? "",
            evidence: (Array.isArray(latest.evidence) ? latest.evidence : [])
              .filter((e) => e && typeof e === "object")
              .map((e) => ({
                url: typeof e.url === "string" ? e.url : null,
                section: typeof e.section === "string" ? e.section : null,
                quote: typeof e.quote === "string" ? e.quote : null,
              })),
            note: typeof latest.note === "string" ? latest.note : "",
            written: latest.written === true,
            ledger_line: latest._line,
          }
        : null,
      outcome,
      false_pin: falsePin,
      earlier_kinds: changed ? history.slice(0, -1) : [],
      history: counting.map((l) => ({
        run: l.run ?? null,
        kind: l.proposal.kind,
        close: l.proposal.close ?? null,
        ledger_line: l._line,
      })),
      skips,
      other_policy_proposals: otherPolicy,
      harness_lines: harnessOnly,
    };
  });

  const n = rows.length;
  const pending = rows.filter((r) => r.outcome === "pending").length;
  const agree = rows.filter((r) => r.outcome === "agree").length;
  const forced = rows.filter((r) => r.outcome === "forced-escalate").length;
  const falsePins = rows.filter((r) => r.false_pin).length;
  const need = Math.ceil((PASS_MIN / 10) * n);
  // A pending item can't undo a false pin, and can at best add one agreement each.
  const judge = (k) =>
    falsePins > 0 || k + pending < need
      ? "FAIL"
      : pending
        ? "INCOMPLETE"
        : k >= need
          ? "PASS"
          : "FAIL";
  return {
    policy,
    items: n,
    pending,
    agree_strict: agree,
    agree_counting_forced: agree + forced,
    forced_escalates: forced,
    false_pins: falsePins,
    needed: need,
    result_strict: judge(agree),
    result_counting_forced: judge(agree + forced),
    rows,
  };
}

function report(meta, res, ledgerInfo) {
  const out = [];
  const p = (s = "") => out.push(s);
  p(`Held-out comparison — policy ${res.policy}`);
  p(
    `Sealed file: ${meta.path}` +
      (meta.sealed_at ? `  (sealed ${meta.sealed_at})` : ""),
  );
  p(
    `  sha256 ${meta.sha256}` +
      (meta.expected
        ? meta.expected === meta.sha256
          ? "  ✓ matches the hash given"
          : "  ✗ DOES NOT MATCH the hash given"
        : ""),
  );
  p(
    `Ledger: ${ledgerInfo.path}  (${ledgerInfo.lines} lines` +
      (ledgerInfo.bad.length
        ? `, ${ledgerInfo.bad.length} unparseable: ${ledgerInfo.bad.slice(0, 5).join(", ")}`
        : "") +
      ")",
  );
  p();
  const W = Math.max(...res.rows.map((r) => docNum(r.ocd_id).length), 10);
  const fmt = (k, c) => (k === "pin_close" ? `pin_close → ${c ?? "?"}` : k);
  const MARK = {
    agree: "✓ agree",
    "forced-escalate": "~ forced escalate",
    disagree: "✗ disagree",
    pending: `… no ${res.policy} proposal yet`,
  };
  p(
    `${"item".padEnd(W)}  ${"you".padEnd(24)}  ${"autopilot".padEnd(24)}  result`,
  );
  p(`${"-".repeat(W)}  ${"-".repeat(24)}  ${"-".repeat(24)}  ------`);
  for (const r of res.rows) {
    const mark = MARK[r.outcome] + (r.false_pin ? "  ✗ FALSE PIN" : "");
    p(
      `${docNum(r.ocd_id).padEnd(W)}  ${fmt(r.mine.kind, r.mine.close).padEnd(24)}  ${(r.agent ? fmt(r.agent.kind, r.agent.close) : "—").padEnd(24)}  ${mark}`,
    );
  }
  p();
  const detail = res.rows.filter(
    (r) => r.outcome !== "agree" || r.false_pin || r.earlier_kinds.length,
  );
  if (detail.length) {
    p("Details");
    for (const r of detail) {
      p();
      p(`• ${r.ocd_id}`);
      p(`  you:       ${fmt(r.mine.kind, r.mine.close)} — ${r.mine.reason}`);
      if (r.agent) {
        p(
          `  autopilot: ${fmt(r.agent.kind, r.agent.close)} — ${r.agent.reason || "(no reason recorded)"}`,
        );
        p(
          `             run ${r.agent.run ?? "?"} · ${r.agent.mode ?? "?"} · verifier ${r.agent.verifier ?? "n/a"} · ledger line ${r.agent.ledger_line}`,
        );
        for (const e of r.agent.evidence.slice(0, 3))
          if (e.url) p(`             evidence ${e.url}`);
        if (r.earlier_kinds.length)
          p(
            `  note: earlier ${res.policy} proposals for this item were ${r.earlier_kinds.join(", ")}`,
          );
      } else {
        p(
          `  autopilot: no counting proposal` +
            (r.skips ? ` (${r.skips} skip line(s) under this policy)` : "") +
            (r.other_policy_proposals
              ? ` (${r.other_policy_proposals} proposal(s) under other policy versions, which don't count)`
              : "") +
            (r.harness_lines
              ? ` (${r.harness_lines} harness line(s), which don't count)`
              : ""),
        );
      }
    }
    p();
  }
  p("Result");
  p(
    `  kinds agree: ${res.agree_counting_forced}/${res.items} (need ${res.needed})` +
      (res.forced_escalates
        ? ` — includes ${res.forced_escalates} forced escalate(s), which count as agreement; strictly ${res.agree_strict}/${res.items}`
        : ""),
  );
  p(`  false pins: ${res.false_pins} (need 0)`);
  if (ledgerInfo.policies && !ledgerInfo.policies.includes(res.policy))
    p(
      `  note: no ledger line carries policy "${res.policy}" at all; the ledger has: ${ledgerInfo.policies.join(", ") || "(none)"}. Pass --policy if the string differs.`,
    );
  if (res.pending) {
    p(`  ${res.pending} item(s) have no ${res.policy} proposal yet`);
    if (res.result_counting_forced === "FAIL")
      p(
        "  (already decided: no outcome for the pending items can change a FAIL)",
      );
  }
  p(
    `  PART 2: ${res.result_counting_forced} (raw; adjudicate disagreements before recording)`,
  );
  return out.join("\n");
}

// ---------- HTML report ----------

const FR_API = "https://www.federalregister.gov/api/v1";
async function frTitles(nums) {
  const out = {};
  await Promise.all(
    nums.map(async (n) => {
      try {
        const res = await fetch(
          `${FR_API}/documents/${n}.json?fields%5B%5D=title&fields%5B%5D=agencies&fields%5B%5D=type`,
          { signal: AbortSignal.timeout(10_000) },
        );
        if (!res.ok) return;
        const j = await res.json();
        out[n] = {
          title: typeof j.title === "string" ? j.title : null,
          agency:
            (j.agencies ?? [])
              .map((a) => a?.name ?? a?.raw_name)
              .filter(Boolean)[0] ?? null,
          type: typeof j.type === "string" ? j.type : null,
        };
      } catch {
        // titles are decoration; the report works without them
      }
    }),
  );
  return out;
}

export function renderHtml(data) {
  // JSON inside <script type="application/json">: neutralise "</script" and line separators.
  const json = JSON.stringify(data)
    .replace(/</g, "\\u003c")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
  const hash = createHash("sha256").update(REPORT_JS).digest("base64");
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-${hash}'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<title>Held-out comparison · ${data.result.policy.replace(/[<>&"]/g, "")}</title>
<style>${REPORT_CSS}</style></head>
<body><div id="app"></div>
<script type="application/json" id="data">${json}</script>
<script>${REPORT_JS}</script>
</body></html>
`;
}

const REPORT_CSS = `
:root { color-scheme: light dark;
  --bg:#f7f7f5; --fg:#1c1c1a; --muted:#6b6b66; --card:#fff; --line:#e3e2dd; --chip:#efeee9;
  --ok:#1f7a4d; --ok-bg:#e3f4ea; --bad:#b4232c; --bad-bg:#fbe7e8; --warn:#9a6400; --warn-bg:#fdf1d8;
  --pend:#5b5b8f; --pend-bg:#ecebf7; --link:#1d5fbf;
  --k-pin:#1d5fbf; --k-esc:#9a6400; --k-wd:#7a3fb0; --k-ro:#137a7a; --k-dc:#666; }
@media (prefers-color-scheme: dark) { :root {
  --bg:#141413; --fg:#ecebe6; --muted:#9c9b94; --card:#1d1d1b; --line:#33322e; --chip:#2a2a27;
  --ok:#5fd39a; --ok-bg:#16301f; --bad:#ff7b82; --bad-bg:#3a1719; --warn:#f0b54a; --warn-bg:#332611;
  --pend:#a9a8e6; --pend-bg:#24233a; --link:#7fb0ff;
  --k-pin:#7fb0ff; --k-esc:#f0b54a; --k-wd:#c79bf2; --k-ro:#5fd0cf; --k-dc:#aaa; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif; }
#app { max-width: 1080px; margin: 0 auto; padding: 32px 24px 80px; }
a { color: var(--link); }
h1 { font-size: 22px; margin: 0; letter-spacing: -.01em; }
.sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; }
.banner { margin: 22px 0 16px; border-radius: 12px; padding: 18px 20px; display: flex; gap: 18px; align-items: center; border: 1px solid var(--line); background: var(--card); }
.banner .big { font-size: 30px; font-weight: 800; letter-spacing: .02em; padding: 4px 14px; border-radius: 10px; white-space: nowrap; }
.banner .why { font-size: 15px; }
.r-PASS { color: var(--ok); background: var(--ok-bg); }
.r-FAIL { color: var(--bad); background: var(--bad-bg); }
.r-INCOMPLETE { color: var(--pend); background: var(--pend-bg); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.tile .n { font-size: 26px; font-weight: 750; line-height: 1.1; }
.tile .l { font-size: 12.5px; color: var(--muted); }
.tile.bad .n { color: var(--bad); } .tile.ok .n { color: var(--ok); } .tile.pend .n { color: var(--pend); } .tile.warn .n { color: var(--warn); }
.strip { display: flex; gap: 6px; margin: 16px 0 6px; flex-wrap: wrap; }
.strip a { flex: 1 1 0; min-width: 64px; text-decoration: none; color: inherit; border-radius: 8px; padding: 7px 6px 6px; text-align: center; font-size: 11.5px; border: 1px solid var(--line); background: var(--card); }
.strip a b { display: block; height: 6px; border-radius: 3px; margin-bottom: 5px; }
.o-agree b, .dot.o-agree { background: var(--ok); }
.o-disagree b, .dot.o-disagree, .o-falsepin b, .dot.o-falsepin { background: var(--bad); }
.o-forced-escalate b, .dot.o-forced-escalate { background: var(--warn); }
.o-pending b, .dot.o-pending { background: var(--pend); opacity: .6; }
.meta { margin: 14px 0 22px; background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; font-size: 13px; display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; }
.meta .k { color: var(--muted); }
.okt { color: var(--ok); font-weight: 600; } .badt { color: var(--bad); font-weight: 700; } .warnt { color: var(--warn); font-weight: 600; }
.toolbar { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; position: sticky; top: 0; background: var(--bg); padding: 8px 0; z-index: 2; }
.toolbar button { all: unset; cursor: pointer; font-size: 13px; padding: 5px 11px; border-radius: 999px; background: var(--chip); }
.toolbar button[aria-pressed="true"] { background: var(--fg); color: var(--bg); }
.toolbar .sp { flex: 1; }
.card { background: var(--card); border: 1px solid var(--line); border-left: 5px solid var(--line); border-radius: 10px; margin-bottom: 12px; scroll-margin-top: 60px; }
.card.o-agree { border-left-color: var(--ok); } .card.o-disagree, .card.o-falsepin { border-left-color: var(--bad); }
.card.o-forced-escalate { border-left-color: var(--warn); } .card.o-pending { border-left-color: var(--pend); }
.card > summary { list-style: none; cursor: pointer; padding: 12px 16px; display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; align-items: center; }
.card > summary::-webkit-details-marker { display: none; }
.card .ttl { font-weight: 650; }
.card .ttl .num { font-family: ui-monospace, Menlo, monospace; font-weight: 600; margin-right: 8px; }
.card .ag { color: var(--muted); font-size: 12.5px; grid-column: 1; }
.card .quick { grid-column: 1 / -1; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 13px; }
.badge { font-size: 12px; font-weight: 700; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }
.b-agree { color: var(--ok); background: var(--ok-bg); } .b-disagree, .b-falsepin { color: var(--bad); background: var(--bad-bg); }
.b-forced-escalate { color: var(--warn); background: var(--warn-bg); } .b-pending { color: var(--pend); background: var(--pend-bg); }
.kind { font-family: ui-monospace, Menlo, monospace; font-size: 12.5px; font-weight: 600; padding: 2px 8px; border-radius: 6px; border: 1px solid currentColor; }
.kind.pin_close { color: var(--k-pin); } .kind.escalate { color: var(--k-esc); } .kind.confirm_withdrawn { color: var(--k-wd); }
.kind.confirm_reopened { color: var(--k-ro); } .kind.dismiss_conflict { color: var(--k-dc); } .kind.none { color: var(--muted); border-style: dashed; }
.vs { color: var(--muted); font-size: 12px; }
.body { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 1px solid var(--line); }
.col { padding: 14px 16px; min-width: 0; }
.col + .col { border-left: 1px solid var(--line); }
.col h3 { margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 650; }
.reason { margin: 8px 0 0; padding: 8px 12px; border-left: 3px solid var(--line); background: var(--bg); border-radius: 0 6px 6px 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.facts { font-size: 12.5px; color: var(--muted); margin-top: 8px; }
.ev { margin-top: 10px; font-size: 13px; }
.ev li { margin-bottom: 6px; } .ev q { display: block; color: var(--fg); font-style: italic; overflow-wrap: anywhere; }
details.sub2 { margin-top: 10px; font-size: 13px; } details.sub2 summary { cursor: pointer; color: var(--muted); }
details.sub2 pre { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--bg); padding: 10px; border-radius: 6px; font-size: 12px; }
.hist { font-size: 12.5px; margin: 6px 0 0; padding-left: 18px; }
.rules { margin-top: 30px; font-size: 13px; color: var(--muted); }
.rules li { margin-bottom: 4px; }
.empty { color: var(--muted); padding: 20px; text-align: center; }
@media (max-width: 720px) { .body { grid-template-columns: 1fr; } .col + .col { border-left: 0; border-top: 1px solid var(--line); } .banner { flex-direction: column; align-items: flex-start; } }
`;

// Rendered from the embedded JSON with DOM APIs and textContent only (no innerHTML).
const REPORT_JS = `
(() => {
const D = JSON.parse(document.getElementById("data").textContent);
const R = D.result;
const h = (tag, attrs, ...kids) => { const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) { if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v); else if (k === "class") el.className = v; else el.setAttribute(k, v === true ? "" : v); }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el; };
const safe = (u) => (typeof u === "string" && /^https:\\/\\//.test(u) ? u : null);
const ext = (href, text) => safe(href) ? h("a", { href, target: "_blank", rel: "noopener noreferrer" }, text) : text;
const num = (id) => id.split("/").pop();
const when = (t) => { if (!t) return "?"; const d = new Date(t); return isNaN(d) ? t : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); };
const kindEl = (k, close) => k ? h("span", { class: "kind " + k }, k === "pin_close" && close ? "pin_close → " + close : k) : h("span", { class: "kind none" }, "no proposal yet");
const cls = (r) => r.false_pin ? "falsepin" : r.outcome;
const LABEL = { agree: "Agree", disagree: "Disagree", falsepin: "False pin", "forced-escalate": "Forced escalate", pending: "No proposal yet" };
const RANK = { falsepin: 0, disagree: 1, "forced-escalate": 2, pending: 3, agree: 4 };
const app = document.getElementById("app");

// header + verdict
// Runbook scoring (2026-11-03): a forced escalate counts as agreement.
const AG = R.agree_counting_forced, RES = R.result_counting_forced;
const headline = RES, resultCls = RES;
const strictNote = R.forced_escalates ? " (" + R.forced_escalates + " forced escalate" + (R.forced_escalates > 1 ? "s" : "") + " counted as agreement; strictly " + R.agree_strict + "/" + R.items + ")" : "";
let why;
if (R.false_pins > 0) why = R.false_pins + " false pin" + (R.false_pins > 1 ? "s" : "") + ". Any false pin blocks the gate until it is explained and the policy amended.";
else if (RES === "INCOMPLETE") why = R.pending + " of " + R.items + " items have no " + R.policy + " proposal yet. So far " + AG + " agree" + strictNote + ", no false pins. Need " + R.needed + " of " + R.items + ".";
else if (RES === "PASS") why = AG + " of " + R.items + " kinds agree" + strictNote + " (need " + R.needed + ") and there are no false pins. Adjudicate any disagreement before recording (runbook, part 2).";
else why = "Only " + AG + " of " + R.items + " kinds agree" + strictNote + "; part 2 needs " + R.needed + "." + (R.pending ? " The " + R.pending + " pending item(s) can't change that." : "") + " Adjudicate the disagreements before recording (runbook, part 2).";
app.append(
  h("h1", null, "Held-out comparison"),
  h("div", { class: "sub" }, "Shadow gate part 2 · policy " + R.policy + (D.held_out.set_date ? " · set " + D.held_out.set_date : "") + " · generated " + when(D.generated_at)),
  h("div", { class: "banner" }, h("div", { class: "big r-" + resultCls }, headline), h("div", { class: "why" }, why)));

const t = (n, l, c) => h("div", { class: "tile " + (c || "") }, h("div", { class: "n" }, n), h("div", { class: "l" }, l));
app.append(h("div", { class: "tiles" },
  t(AG + "/" + R.items, "kinds agree (need " + R.needed + ")", AG >= R.needed ? "ok" : R.pending ? "" : "bad"),
  t(R.false_pins, "false pins (need 0)", R.false_pins ? "bad" : "ok"),
  t(R.rows.filter((r) => r.outcome === "disagree" && !r.false_pin).length, "other disagreements", R.rows.some((r) => r.outcome === "disagree" && !r.false_pin) ? "bad" : ""),
  R.forced_escalates ? t(R.forced_escalates, "forced escalates (count as agreement)", "warn") : null,
  t(R.pending, "no proposal yet", R.pending ? "pend" : "")));

app.append(h("div", { class: "strip" }, R.rows.map((r) => h("a", { href: "#i-" + num(r.ocd_id), class: "o-" + cls(r), title: LABEL[cls(r)] }, h("b"), num(r.ocd_id)))));

// integrity
const ho = D.held_out;
app.append(h("div", { class: "meta" },
  h("span", { class: "k" }, "Sealed file"), h("span", { class: "mono" }, ho.path + (ho.sealed_at ? "  · sealed " + when(ho.sealed_at) : "")),
  h("span", { class: "k" }, "sha256"), h("span", null, h("span", { class: "mono" }, ho.sha256 + " "),
    ho.sha256_matches === true ? h("span", { class: "okt" }, "✓ matches the hash from sealing") :
    ho.sha256_matches === false ? h("span", { class: "badt" }, "✗ DOES NOT MATCH the hash you gave") : h("span", { class: "k" }, "(no --sha256 given to check)")),
  h("span", { class: "k" }, "Ledger"), h("span", { class: "mono" }, D.ledger.path + " · " + D.ledger.lines + " lines" + (D.ledger.unparseable.length ? " · " + D.ledger.unparseable.length + " unparseable" : "")),
  D.ledger.policies.includes(R.policy) ? null : [h("span", { class: "k" }, "Warning"), h("span", { class: "warnt" }, "No ledger line carries policy \\u201c" + R.policy + "\\u201d. The ledger has: " + (D.ledger.policies.join(", ") || "none") + ". Re-run with --policy if the string differs.")]));

// toolbar
let filter = "all", order = "severity";
const counts = {}; for (const r of R.rows) counts[cls(r)] = (counts[cls(r)] || 0) + 1;
const attention = R.rows.filter((r) => cls(r) !== "agree").length;
const FILTERS = [["all", "All " + R.items], ["attention", "Needs a look " + attention], ...["falsepin", "disagree", "forced-escalate", "pending", "agree"].filter((k) => counts[k]).map((k) => [k, LABEL[k] + " " + counts[k]])];
const bar = h("div", { class: "toolbar" });
const list = h("div");
function drawBar() {
  bar.replaceChildren(...FILTERS.map(([k, l]) => h("button", { "aria-pressed": String(filter === k), onclick: () => { filter = k; drawBar(); drawList(); } }, l)),
    h("span", { class: "sp" }),
    h("button", { "aria-pressed": String(order === "set"), onclick: () => { order = order === "set" ? "severity" : "set"; drawBar(); drawList(); } }, order === "set" ? "Set order" : "Worst first"),
    h("button", { onclick: () => document.querySelectorAll("details.card").forEach((d) => (d.open = true)) }, "Expand all"),
    h("button", { onclick: () => document.querySelectorAll("details.card").forEach((d) => (d.open = false)) }, "Collapse all"));
}
function card(r) {
  const c = cls(r), n = num(r.ocd_id), info = (D.titles || {})[n] || {}, a = r.agent;
  const you = h("div", { class: "col" }, h("h3", null, "Your sealed verdict"), kindEl(r.mine.kind, r.mine.close),
    h("div", { class: "reason" }, r.mine.reason || "(no reason)"));
  const bot = h("div", { class: "col" }, h("h3", null, "Autopilot \\u00b7 latest " + R.policy + " proposal"));
  if (a) {
    bot.append(kindEl(a.kind, a.close), h("div", { class: "reason" }, a.reason || "(no reason recorded)"),
      h("div", { class: "facts" }, "run " + when(a.run) + " · " + (a.mode || "?") + (a.written ? " · written" : "") + " · verifier " + (a.verifier ?? "n/a") + (a.verifier_model ? " (" + a.verifier_model + ")" : "") + " · ledger line " + a.ledger_line));
    if (a.evidence.length) bot.append(h("ul", { class: "ev" }, a.evidence.map((e) => h("li", null, e.url ? ext(e.url, (e.section ? e.section + " · " : "") + e.url.replace(/^https:\\/\\//, "")) : (e.section || "evidence"), e.quote ? h("q", null, e.quote) : null))));
    if (a.note) bot.append(h("details", { class: "sub2" }, h("summary", null, "Draft note the autopilot would write"), h("pre", null, a.note)));
    if (r.history.length > 1) bot.append(h("details", { class: "sub2", open: r.earlier_kinds.length > 0 }, h("summary", null, r.history.length + " " + R.policy + " proposals for this item" + (r.earlier_kinds.length ? " (it changed its answer)" : "")),
      h("ol", { class: "hist" }, r.history.map((x) => h("li", null, when(x.run) + " \\u2014 ", kindEl(x.kind, x.close))))));
  } else {
    const why = [];
    if (r.skips) why.push(r.skips + " skip line(s) under this policy (a skip is retried next run)");
    if (r.other_policy_proposals) why.push(r.other_policy_proposals + " proposal(s) under other policy versions, which don't count");
    if (r.harness_lines) why.push(r.harness_lines + " harness line(s), which don't count");
    bot.append(kindEl(null), h("div", { class: "facts" }, why.length ? why.join(" · ") : "Nothing in the ledger for this item yet. Daily runs work the queue closing-soonest first, 10 decisions a run."));
  }
  const badges = r.false_pin
    ? [h("span", { class: "badge b-falsepin" }, r.outcome === "agree" ? "False pin \u00b7 wrong date" : "False pin")]
    : [h("span", { class: "badge b-" + r.outcome }, LABEL[r.outcome])];
  return h("details", { class: "card o-" + c, id: "i-" + n, open: c !== "agree" },
    h("summary", null,
      h("div", { class: "ttl" }, h("span", { class: "num" }, n), info.title || ""),
      h("div", null, badges),
      (info.agency || info.type) ? h("div", { class: "ag" }, [info.agency, info.type].filter(Boolean).join(" · ")) : null,
      h("div", { class: "quick" }, h("span", { class: "vs" }, "you"), kindEl(r.mine.kind, r.mine.close), h("span", { class: "vs" }, "autopilot"), kindEl(a && a.kind, a && a.close),
        h("span", { class: "sp" }), ext("https://www.federalregister.gov/d/" + n, "Federal Register \\u2197"))),
    h("div", { class: "body" }, you, bot));
}
function drawList() {
  let rows = R.rows.filter((r) => filter === "all" || (filter === "attention" ? cls(r) !== "agree" : cls(r) === filter));
  if (order === "severity") rows = [...rows].sort((x, y) => RANK[cls(x)] - RANK[cls(y)]);
  list.replaceChildren(...(rows.length ? rows.map(card) : [h("div", { class: "empty" }, "Nothing in this filter.")]));
}
drawBar(); drawList();
app.append(bar, list);
document.querySelectorAll(".strip a").forEach((el) => el.addEventListener("click", () => { filter = "all"; drawBar(); drawList(); const d = document.getElementById(el.getAttribute("href").slice(1)); if (d) d.open = true; }));

app.append(h("div", { class: "rules" }, h("b", null, "How this is scored"), h("ul", null,
  h("li", null, "The autopilot's answer for an item is its most recent ledger line with the same id, policy " + R.policy + ", harness null (a scheduled run) and a kind other than skip."),
  h("li", null, "Kinds agree when they are equal. A pin with a different date still agrees on kind, but is a false pin."),
  h("li", null, "A false pin is a pin_close proposal where you didn't pin, or pinned a different date. Any one blocks part 2."),
  h("li", null, "Forced escalate: you chose dismiss_conflict or confirm_reopened, which the autopilot is forbidden to propose, and it escalated as the policy requires. It counts as agreement (runbook, part 2, \\u201cScoring\\u201d)."),
  h("li", null, "Part 2 passes with at least " + R.needed + " of " + R.items + " kinds agreeing and no false pins. Items with no proposal make it INCOMPLETE unless the result is already decided."))));
})();
`;

async function writePrivate(path, text) {
  const tmp = join(dirname(path), `.${basename(path)}.${process.pid}.tmp`);
  await writeFile(tmp, text, { mode: 0o600 });
  await rename(tmp, path);
}

async function main() {
  let opt;
  try {
    ({ values: opt } = parseArgs({
      options: {
        "held-out": { type: "string" },
        ledger: { type: "string" },
        policy: { type: "string" },
        sha256: { type: "string" },
        html: { type: "string" },
        "no-open": { type: "boolean", default: false },
        "no-fetch": { type: "boolean", default: false },
        text: { type: "boolean", default: false },
        json: { type: "boolean", default: false },
        help: { type: "boolean", short: "h", default: false },
      },
    }));
  } catch (e) {
    fail(e.message);
  }
  if (opt.help) {
    process.stdout.write(
      "usage: node tools/held-out-compare.mjs --held-out <sealed file> [--ledger <path>] [--policy <version>] [--sha256 <hex>] [--html <path>] [--no-open] [--no-fetch] [--text | --json]\n",
    );
    return;
  }
  if (!opt["held-out"])
    fail("--held-out <path to the sealed file> is required");
  const hoPath = resolve(expand(opt["held-out"]));
  const lgPath = resolve(
    expand(opt.ledger ?? "~/.config/yokel/review-autopilot/ledger.jsonl"),
  );

  let hoBuf;
  try {
    hoBuf = readFileSync(hoPath);
  } catch (e) {
    fail(`cannot read ${hoPath}: ${e.code ?? e.message}`);
  }
  const sha256 = createHash("sha256").update(hoBuf).digest("hex");
  let heldOut;
  try {
    heldOut = loadHeldOut(hoBuf.toString("utf8"));
  } catch (e) {
    fail(e.message);
  }
  const policy = opt.policy ?? heldOut.policy;
  if (!policy) fail("the sealed file has no policy_version; pass --policy");

  let lgText;
  try {
    lgText = readFileSync(lgPath, "utf8");
  } catch (e) {
    fail(`cannot read ${lgPath}: ${e.code ?? e.message}`);
  }
  const ledger = loadLedger(lgText);
  const res = compare(heldOut, ledger.lines, policy);
  const expected = opt.sha256?.trim().toLowerCase() ?? null;
  const meta = { path: hoPath, sha256, expected, sealed_at: heldOut.sealed_at };
  const policies = [
    ...new Set(ledger.lines.map((l) => l.policy).filter(Boolean)),
  ];
  if (expected && expected !== sha256) process.exitCode = 3;

  if (opt.json) {
    process.stdout.write(
      JSON.stringify(
        {
          held_out: {
            ...meta,
            sha256_matches: expected ? expected === sha256 : null,
          },
          ledger: {
            path: lgPath,
            lines: ledger.lines.length,
            unparseable: ledger.bad,
            policies,
          },
          ...res,
        },
        null,
        2,
      ) + "\n",
    );
    return;
  }
  if (opt.text) {
    process.stdout.write(
      report(meta, res, {
        path: lgPath,
        lines: ledger.lines.length,
        bad: ledger.bad,
        policies,
      }) + "\n",
    );
    return;
  }

  const titles = opt["no-fetch"]
    ? {}
    : await frTitles(res.rows.map((r) => docNum(r.ocd_id)));
  const html = renderHtml({
    generated_at: new Date().toISOString(),
    held_out: {
      path: hoPath,
      sha256,
      sha256_matches: expected ? expected === sha256 : null,
      sealed_at: heldOut.sealed_at,
      set_date: heldOut.set_date,
    },
    ledger: {
      path: lgPath,
      lines: ledger.lines.length,
      unparseable: ledger.bad,
      policies,
    },
    titles,
    result: res,
  });
  const outPath = resolve(
    expand(
      opt.html ??
        join(dirname(hoPath), `${basename(hoPath, ".json")}.comparison.html`),
    ),
  );
  await writePrivate(outPath, html);
  process.stdout.write(
    `part 2 (raw): ${res.result_counting_forced}` +
      ` · agree ${res.agree_counting_forced}/${res.items}` +
      (res.forced_escalates ? ` (strictly ${res.agree_strict})` : "") +
      ` · false pins ${res.false_pins} · pending ${res.pending}` +
      (expected
        ? expected === sha256
          ? " · sha256 ✓"
          : " · sha256 MISMATCH"
        : "") +
      `\nreport: ${outPath}\n`,
  );
  if (!opt["no-open"] && process.platform === "darwin")
    execFile("open", [outPath], () => {});
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
)
  main().catch((e) => fail(e.message));
