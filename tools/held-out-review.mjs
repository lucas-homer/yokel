#!/usr/bin/env node
// Held-out set workbench (shadow gate part 2, docs/runbooks/review-queue.md § Autopilot).
//
// A local, single-operator page for judging the held-out items blind and sealing the verdicts.
// It only ever reads `review show <id> --blind` (prior verdicts hidden) and the public Federal
// Register API. It never reads the autopilot thread, the shadow ledger, or any earlier
// held-out file. Sealing writes the output file once (O_EXCL) and never overwrites it.
//
// Search aids it adds from the FR text (aids, not verdicts): bare docket ids for the related
// search, deadline-setting sentences in each related document (flagged when later than this
// notice's close), deadline times other than 11:59 p.m. stated anywhere in the notice, and a
// note when the notice covers several dockets.
//
//   node tools/held-out-review.mjs --date 2026-10-31 --policy v1.3@2026-10-31 <id> [<id> ...]
//
// Options:
//   --date <YYYY-MM-DD>   the set's date; names the output file (required)
//   --policy <version>    the policy version the set is for, recorded in the file (required)
//   --out <path>          default ~/.config/yokel/review-autopilot/held-out-<date>.json
//   --port <n>            default 8791 (binds 127.0.0.1 only)
//   --context <name>      kubectl context, default k3d-yokel
// The page listens on 127.0.0.1 only; from another machine use `ssh -L 8791:127.0.0.1:8791 <mini>`.
// Drafts live in the browser's storage for that origin, so restart on the same --port to keep them.
// Ids may be full OCD-IDs or bare FR document numbers (2026-12345).
// Node 24, no dependencies.

import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { link, mkdir, open, unlink } from "node:fs/promises";
import { createServer } from "node:http";
import { homedir } from "node:os";
import { basename, dirname, join } from "node:path";
import { parseArgs } from "node:util";

const KINDS = [
  "pin_close",
  "escalate",
  "confirm_withdrawn",
  "confirm_reopened",
  "dismiss_conflict",
];
const OCD_RE = /^ocd-participation-window\/federal\/(\d{4}-\d{5})$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
// A real calendar date in YYYY-MM-DD form (rejects 2026-02-30, 2026-99-99 and non-strings).
function isDate(v) {
  if (typeof v !== "string" || !DATE_RE.test(v)) return false;
  const [y, m, d] = v.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d));
  return (
    t.getUTCFullYear() === y &&
    t.getUTCMonth() === m - 1 &&
    t.getUTCDate() === d
  );
}
const USAGE =
  "usage: node tools/held-out-review.mjs --date YYYY-MM-DD --policy <version> [--out <path>] [--port 8791] [--context k3d-yokel] <id> [<id> ...]";

function die(msg) {
  console.error(`held-out-review: ${msg}\n${USAGE}`);
  process.exit(2);
}

let opt, positionals;
try {
  ({ values: opt, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      date: { type: "string" },
      policy: { type: "string" },
      out: { type: "string" },
      port: { type: "string", default: "8791" },
      context: { type: "string", default: "k3d-yokel" },
      help: { type: "boolean", short: "h", default: false },
    },
  }));
} catch (e) {
  die(e.message);
}
if (opt.help) {
  console.log(USAGE);
  process.exit(0);
}

if (!isDate(opt.date)) die("--date must be a real date, YYYY-MM-DD");
if (!opt.policy) die("--policy <version> is required (e.g. v1.3@2026-10-31)");
const ids = [
  ...new Set(
    positionals.map((p) =>
      /^\d{4}-\d{5}$/.test(p) ? `ocd-participation-window/federal/${p}` : p,
    ),
  ),
];
if (ids.length === 0) die("give at least one id");
for (const id of ids)
  if (!OCD_RE.test(id)) die(`not a federal window id: ${id}`);
const outPath =
  opt.out ??
  join(
    homedir(),
    ".config/yokel/review-autopilot",
    `held-out-${opt.date}.json`,
  );
// Refuse to start on an existing file without reading it: a sealed set is never reopened here.
if (existsSync(outPath))
  die(`${outPath} already exists (sealed). Pick another --date or --out.`);
const port = Number(opt.port);
if (!Number.isInteger(port) || port < 1024 || port > 65535)
  die("--port must be an integer from 1024 to 65535");

let sealed = null; // { path, sha256, sealed_at } once written
let sealing = false;

// ---------- sources ----------

function runBlindShow(id) {
  const args = [
    "--context",
    opt.context,
    "-n",
    "docketclock",
    "exec",
    "deploy/docketclock-poller",
    "--",
    "pnpm",
    "exec",
    "tsx",
    "src/review/cli.ts",
    "show",
    id,
    "--blind",
  ];
  return new Promise((resolve, reject) => {
    execFile(
      "kubectl",
      args,
      { timeout: 180_000, maxBuffer: 8 << 20 },
      (err, stdout, stderr) => {
        if (err)
          reject(
            new Error(
              `review show failed: ${(stderr || err.message).trim().slice(0, 400)}`,
            ),
          );
        else resolve(stdout);
      },
    );
  });
}

// Parses `review show --blind` (apps/docketclock/src/review/cli.ts). Missing values print as
// "(none)" / "none" there; they become null here. Anything that fails to parse is reported in
// `warnings` so the page never presents a silently empty field as "nothing there".
const nil = (v) => (v == null || v === "(none)" || v === "none" ? null : v);
function parseBlind(text) {
  const warnings = [];
  const m = (re) => text.match(re)?.[1] ?? null;

  let fr = null;
  const idLine = m(/identity: FR (.*)/);
  if (!idLine) warnings.push("no identity line in the blind output");
  else {
    const head = idLine.match(/^(\S+) — ("(?:[^"\\]|\\.)*"|\(no title\))/);
    let title = null;
    let rest = "";
    if (head) {
      try {
        title = head[2].startsWith('"') ? JSON.parse(head[2]) : null;
      } catch {
        warnings.push("could not read the title from the identity line");
      }
      rest = idLine.slice(head[0].length);
    } else warnings.push("could not parse the identity line");
    const cit = rest.match(
      /^ — (.*?)(?: published (\d{4}-\d{2}-\d{2}))? — dockets \[/,
    );
    const dk = rest.match(/ — dockets \[(.*?)\]/);
    const rin = rest.match(/ — RIN (.+)$/);
    if (head && !dk) warnings.push("no dockets field in the identity line");
    if (head && !rin) warnings.push("no RIN field in the identity line");
    fr = {
      docNum: nil(idLine.match(/^(\S+)/)?.[1]),
      title,
      citation: cit && cit[1] !== "(no citation)" ? cit[1] : null,
      published: cit?.[2] ?? null,
      dockets: (dk?.[1] ?? "")
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean),
      rins: nil(rin?.[1]?.trim())
        ? rin[1]
            .split(",")
            .map((x) => x.trim())
            .filter(Boolean)
        : [],
    };
  }

  const regs = text.match(/\n\s+Regs (\S+) — docket (\S+) — frDocNum (\S+)/);
  if (!regs) warnings.push("no Regulations.gov identity line");
  // Own-source rows start with exactly four spaces; linked-amendment rows say "linked amendment".
  const obs = (src, field) => {
    const r = text.match(
      new RegExp(
        `\\n    ${src} @ (\\S+)\\n\\s+${field}=(\\S+) withdrawn=(\\S+) openForComment=(\\S+)(?: flags\\[w/e/r\\]=(\\d{3}))?`,
      ),
    );
    return (
      r && {
        observedAt: r[1],
        close: nil(r[2] === "null" ? null : r[2]),
        withdrawn: r[3],
        openForComment: r[4],
        wer: r[5] ?? null,
      }
    );
  };
  const frObs = obs("federal_register", "comments_close_on");
  const regsObs = obs("regulations_gov", "commentEndDate");
  const amendments = [
    ...text.matchAll(/\n\s+linked amendment (\S+) (\S+) @ (\S+)/g),
  ].map((a) => ({ docNum: a[1], source: a[2], observedAt: a[3] }));

  let flags = [];
  try {
    flags = JSON.parse(m(/flags=(\[.*?\])/) ?? "[]");
  } catch {
    warnings.push("could not read the window flags");
  }
  return {
    confidence: m(/confidence=(\S+)/),
    status: m(/status=(\S+)/),
    flags,
    close: m(/\n\s+close: (.*)/),
    conflicts: m(/conflicts: (\d+) live/),
    fr,
    regs: regs && {
      documentId: nil(regs[1]),
      docket: nil(regs[2]),
      frDocNum: nil(regs[3]),
    },
    latest: {
      fr: frObs && {
        observedAt: frObs.observedAt,
        commentsCloseOn: frObs.close,
        wer: frObs.wer,
      },
      regs: regsObs && {
        observedAt: regsObs.observedAt,
        commentEndDate: regsObs.close,
        withdrawn: regsObs.withdrawn,
        openForComment: regsObs.openForComment,
        wer: regsObs.wer,
      },
    },
    amendments,
    warnings,
  };
}

// ---------- text evidence (docket ids, deadline sentences, stated times) ----------

// FR `docket_ids` entries are free text: "Docket No. PHMSA-2025-1271", "Docket ID Nos.
// EPA-HQ-OAR-2026-0001 and EPA-HQ-OAR-2026-0002", "Investigation Nos. 701-TA-526 and
// 731-TA-1262 (Second Review)". Searching such a string as one exact phrase misses documents
// that write the id with another label ("Docket Number PHMSA-2025-1271"), so the search uses
// bare id tokens only. A string with no id token is skipped (never searched as prose).
const DOCKET_LABEL =
  /^\s*(?:(?:[A-Z]{2,5}\s+)?(?:Docket|Dkt\.?)(?:\s+ID)?(?:\s+(?:Nos?\.?|Numbers?|Number\(s\)|No\(s\)\.?|#))?|Investigation\s+(?:Nos?\.?|Numbers?))\s*:?\s*/i;
const ID_TOKEN = /\b(?=[A-Za-z0-9-]*\d)[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+\b/g;
const notDateLike = (t) => !/^\d{4}-\d{2}-\d{2}$/.test(t);
function docketIds(raw) {
  if (typeof raw !== "string" || !nil(raw.trim())) return [];
  const labelled = DOCKET_LABEL.test(raw);
  const rest = raw.replace(DOCKET_LABEL, "").trim();
  // A single token after the label is the id itself, hyphenated or not ("Docket No. 12345").
  if (/^[A-Za-z0-9][A-Za-z0-9._-]{3,}$/.test(rest) && /\d/.test(rest))
    return notDateLike(rest) ? [rest] : [];
  const ids = [...rest.matchAll(ID_TOKEN)]
    .map((m) => m[0])
    .filter((t) => t.length >= 5 && notDateLike(t));
  // After a docket label, bare numbers are ids too ("Docket Nos. 12345 and 12346").
  if (labelled && !ids.length)
    for (const m of rest.matchAll(/(?<![\w-])\d{4,}(?![\w-])/g)) ids.push(m[0]);
  return ids;
}
// EPA's FRL number is a document control number, not a docket.
const isDocket = (id) => !/^FRL-/i.test(id);

// FR raw text is an HTML page around a <pre> with hard-wrapped lines. Paragraphs start after a
// blank line or with an indent; lines inside a paragraph are joined.
const ENTITIES = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
};
function decodeEntities(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (all, e) => {
    if (e[0] === "#") {
      const n =
        e[1] === "x" || e[1] === "X"
          ? parseInt(e.slice(2), 16)
          : parseInt(e.slice(1), 10);
      return n === 160
        ? " "
        : Number.isInteger(n) && n > 0 && n <= 0x10ffff
          ? String.fromCodePoint(n)
          : all;
    }
    return ENTITIES[e.toLowerCase()] ?? all;
  });
}
function textParagraphs(html) {
  const pre = html.match(/<pre>([\s\S]*?)<\/pre>/i)?.[1] ?? html;
  const text = decodeEntities(
    pre.replace(/<bullet>/gi, "•").replace(/<[^>]+>/g, ""),
  ).replace(/``|''/g, '"');
  const paras = [];
  let cur = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim() || /^\s{2,}\S/.test(line)) {
      if (cur.length) paras.push(cur.join(" "));
      cur = [];
    }
    if (line.trim()) cur.push(line.trim());
  }
  if (cur.length) paras.push(cur.join(" "));
  return paras.map((p) => p.replace(/\s+/g, " ").trim()).filter(Boolean);
}
// Sentence split that keeps "a.m.", "No.", "Sec.", "U.S." and initials inside the sentence.
const ABBREV =
  /(?:\b(?:No|Nos|Sec|Secs|Mr|Ms|Mrs|Dr|St|Inc|Co|Corp|Ltd|Jr|Sr|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Vol|Fed|Reg|Pub|Stat|App|Pt|Ch|Subch|Div|Dept|Admin|al|etc|e\.g|i\.e|U\.S|U\.S\.C|C\.F\.R|D\.C|cf|vs|approx|Rev|Supp|art|para|pp?|ex|Ex|Nat|Assn|Ass'n)|\b[A-Z])\.$/;
const TZ_NEXT =
  /^(?:E\.?[SD]?T\.?|Eastern|Central|Mountain|Pacific|Atlantic|Alaska|Hawaii|[CMP][SD]T|Coordinated|UTC|GMT|local|Local|ET)\b/;
function sentences(para) {
  const out = [];
  let start = 0;
  const re = /[.?!]["')\]]?\s+(?=["'(]?[A-Z0-9•])/g;
  let m;
  while ((m = re.exec(para))) {
    const end = m.index + 1;
    const before = para.slice(Math.max(start, end - 12), end);
    const next = para.slice(m.index + m[0].length);
    if (/\b[ap]\.m\.$/i.test(before)) {
      // "5 p.m. Eastern", "5 p.m. July 1, 2026": the time belongs to what follows.
      if (TZ_NEXT.test(next) || DATE_NEXT.test(next)) continue;
    } else if (ABBREV.test(before)) continue;
    out.push(para.slice(start, m.index + m[0].trimEnd().length).trim());
    start = m.index + m[0].length;
  }
  out.push(para.slice(start).trim());
  return out.filter(Boolean);
}
const MONTHS = [
  "jan",
  "feb",
  "mar",
  "apr",
  "may",
  "jun",
  "jul",
  "aug",
  "sep",
  "oct",
  "nov",
  "dec",
];
const MON_RE =
  "(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\\.?";
const DATE_IN_TEXT = new RegExp(
  `\\b${MON_RE}\\s+\\d{1,2}(?:st|nd|rd|th)?(?:,?\\s+(\\d{4}))?|\\b\\d{1,2}/\\d{1,2}/\\d{4}\\b`,
  "g",
);
// Every full date (with a year) in a sentence, as YYYY-MM-DD.
function isoDates(s) {
  const out = [];
  for (const m of s.matchAll(DATE_IN_TEXT)) {
    let y, mo, d;
    const num = m[0].match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (num) [mo, d, y] = [+num[1], +num[2], +num[3]];
    else {
      if (!m[1]) continue;
      mo = MONTHS.indexOf(m[0].slice(0, 3).toLowerCase()) + 1;
      d = +m[0].match(/\s(\d{1,2})/)[1];
      y = +m[1];
    }
    const iso = `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    if (isDate(iso)) out.push(iso);
  }
  return out;
}
const DATE_ONE = new RegExp(DATE_IN_TEXT.source);
const hasDate = (s) => DATE_ONE.test(s);
const DATE_NEXT = new RegExp(
  `^(?:${MON_RE}\\s+\\d|(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\\b)`,
);
// Dates a deadline connector points at ("by July 1", "is 5:15 p.m. on July 1", "to September
// 2"), as opposed to other dates in the same sentence (a hearing, a publication date).
const CONNECT_NEAR =
  /\b(?:by|no later than|not later than|on or before|until|through|due)\b[^;]{0,30}$/i;
const CONNECT_ADJ =
  /\b(?:is|are|to|before)\s+(?:\d{1,2}(?::\d{2})?\s*[ap]\.?\s?m\.?,?\s+(?:\w+\s+)?on\s+)?(?:\w+day,?\s+)?$/i;
function deadlineDates(s) {
  const out = [];
  let prevEnd = 0;
  for (const m of s.matchAll(DATE_IN_TEXT)) {
    const before = s.slice(Math.max(prevEnd, m.index - 60), m.index);
    prevEnd = m.index + m[0].length;
    if (!CONNECT_NEAR.test(before) && !CONNECT_ADJ.test(before)) continue;
    const iso = isoDates(m[0]);
    if (iso.length) out.push(iso[0]);
  }
  return out;
}

// Sentences that set or change a submission deadline (rule 3 search aid). A connector counts
// only when a date follows it closely ("filed by Acme Corp" does not).
const SUBMIT_BY = new RegExp(
  `\\b(?:comments?|submissions?|statements?|responses?|requests?|petitions?|objections?|nominations?)\\b[^]*?\\b(?:by|no later than|not later than|on or before|before|until|through)\\b[^;]{0,45}?(?:${MON_RE}\\s+\\d|\\d{1,2}/\\d{1,2}/\\d{4})`,
  "i",
);
const CHANGE_WORD =
  /\b(?:accept(?:s|ing)?\s+(?:additional\s+)?(?:written\s+)?comments|comment period|deadline)\b/i;
const changes = (s) =>
  CHANGE_WORD.test(s) ||
  (/\b(?:extend(?:s|ed|ing)?|extension|reopen(?:s|ed|ing)?|reopening)\b/i.test(
    s,
  ) &&
    /\b(?:comments?|submissions?|deadline)\b/i.test(s));
function deadlineSentences(paras) {
  const out = [];
  for (const p of paras)
    for (const s of sentences(p))
      if (s.length <= 1500 && hasDate(s) && (SUBMIT_BY.test(s) || changes(s)))
        out.push(s);
  return out;
}

// Stated times of day near a deadline (rule 1's time clause, rule 2a).
const TIME_RE =
  /\b(?:\d{1,2}(?::\d{2})?\s*(?:[ap]\.\s?m(?:\.|\b)|[ap]m\b)|noon|midnight)(?![A-Za-z])(?:\s*,?\s*\(?(?:Eastern|Central|Mountain|Pacific|Atlantic|Alaska|Hawaii)(?:\s+(?:Standard|Daylight|Prevailing))?(?:\s+Time)?(?![A-Za-z])\)?|\s*,?\s*\(?(?:E\.?[SD]?T\.?|ET|[CMP][SD]T|UTC|GMT)(?![A-Za-z])\)?|\s+local\s+time\b)?/gi;
const DEADLINE_WORD =
  /\b(?:deadlines?|due|no later than|not later than|on or before|received|postmarked|submit\w*|fil(?:e|ed|ing)|comments?|responses?|requests?|petitions?|objections?|registration|register|close[sd]?)\b/i;
// A time in a sentence with no date still counts when the sentence plainly sets a deadline
// ("Comments must be received by noon."); the date may sit in DATES.
const STRONG_DEADLINE =
  /\b(?:deadlines?|due|no later than|not later than|on or before|must be (?:received|submitted|filed|postmarked|delivered)|(?:received|submitted|filed|postmarked) (?:by|after|before))\b/i;
// 11:59 p.m. with no zone or an Eastern zone is the convention; anything else is a stated time.
const isConvention = (t) =>
  /^11:59\s*p\.?\s?m\.?\s*(?:,?\s*\(?(?:Eastern(?:\s+(?:Standard|Daylight|Prevailing))?(?:\s+Time)?|E\.?[SD]?T\.?|ET)\)?)?$/i.test(
    t.trim(),
  );
function statedTimes(paras) {
  const hits = [];
  const seen = new Set();
  for (const p of paras)
    for (const s of sentences(p)) {
      if (s.length > 1500) continue;
      if (!(hasDate(s) && DEADLINE_WORD.test(s)) && !STRONG_DEADLINE.test(s))
        continue;
      const times = [...s.matchAll(TIME_RE)]
        .map((m) => m[0].trim())
        .filter((t) => !isConvention(t));
      const key = s.replace(/\s+/g, " ");
      if (times.length && !seen.has(key)) {
        seen.add(key);
        hits.push({ sentence: s, times });
      }
    }
  return hits;
}

const FR = "https://www.federalregister.gov/api/v1";
// Raw document text, capped so a very long rule can't stall the item.
const TEXT_CAP = 6 << 20;
async function frText(url) {
  if (!/^https:\/\/www\.federalregister\.gov\//.test(url ?? ""))
    throw new Error("no federalregister.gov raw text URL");
  const res = await fetch(url, { signal: AbortSignal.timeout(20_000) });
  if (!res.ok) throw new Error(`FR text ${res.status}`);
  if (!/^https:\/\/www\.federalregister\.gov\//.test(res.url)) {
    await res.body?.cancel().catch(() => {});
    throw new Error("FR text redirected off federalregister.gov");
  }
  const reader = res.body.getReader();
  const chunks = [];
  let size = 0;
  let truncated = false;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    const room = TEXT_CAP - size;
    chunks.push(value.length > room ? value.subarray(0, room) : value);
    size += value.length;
    if (size > TEXT_CAP) {
      truncated = true;
      await reader.cancel().catch(() => {});
      break;
    }
  }
  return {
    text: new TextDecoder().decode(Buffer.concat(chunks)),
    truncated,
  };
}
async function frJson(url) {
  const res = await fetch(url, {
    headers: { accept: "application/json" },
    signal: AbortSignal.timeout(20_000),
  });
  if (!res.ok) {
    const ra = res.headers.get("retry-after");
    throw new Error(
      `FR API ${res.status}${res.status === 429 ? ` (rate limited${ra ? `; retry after ${ra}s` : ""})` : ""}`,
    );
  }
  return res.json();
}
function frDoc(num) {
  const f = [
    "title",
    "type",
    "action",
    "dates",
    "abstract",
    "agencies",
    "html_url",
    "publication_date",
    "docket_ids",
    "comments_close_on",
    "correction_of",
    "corrections",
    "raw_text_url",
  ];
  return frJson(
    `${FR}/documents/${num}.json?${f.map((x) => `fields%5B%5D=${x}`).join("&")}`,
  );
}
const SEARCH_PAGE = 100;
async function frSearch(value, condition = "term") {
  const f = [
    "document_number",
    "title",
    "type",
    "action",
    "publication_date",
    "html_url",
    "comments_close_on",
    "dates",
    "raw_text_url",
  ];
  const v = condition === "term" ? `"${value}"` : value;
  // Newest first: if a long docket overflows one page, the old documents are the ones cut.
  const q = `conditions%5B${condition}%5D=${encodeURIComponent(v)}&per_page=${SEARCH_PAGE}&order=newest`;
  const j = await frJson(
    `${FR}/documents.json?${q}&${f.map((x) => `fields%5B%5D=${x}`).join("&")}`,
  );
  const results = j.results ?? [];
  return { results, count: Number(j.count ?? results.length) };
}

async function loadItem(id) {
  const docNum = id.match(OCD_RE)[1];
  const [blind, doc] = await Promise.allSettled([
    runBlindShow(id),
    frDoc(docNum),
  ]);
  const item = { id, docNum, errors: [] };
  if (blind.status === "fulfilled") {
    item.blindText = blind.value;
    item.parsed = parseBlind(blind.value);
    for (const w of item.parsed.warnings)
      item.errors.push(`blind output: ${w}`);
  } else item.errors.push(blind.reason.message);
  if (doc.status === "fulfilled") item.frDoc = doc.value;
  else item.errors.push(`FR document: ${doc.reason.message}`);

  // Docket labels as published, and the bare ids the search uses.
  const docketLabels = [
    ...(item.frDoc?.docket_ids ?? []),
    ...(item.parsed?.fr?.dockets ?? []),
    item.parsed?.regs?.docket,
  ].filter((t) => typeof t === "string" && t.trim() && nil(t));
  const idTerms = new Set();
  item.search = [];
  for (const label of new Set(docketLabels)) {
    const got = docketIds(label);
    if (got.length) for (const t of got) idTerms.add(t);
    else
      item.search.push({ term: label, skipped: "no docket id in this label" });
  }
  item.docketIds = [...idTerms].filter(isDocket);

  // Rule 1 / 2a aid: deadline times stated anywhere in the notice, not only in DATES.
  item.ownText = { scanned: false, times: [] };
  const ownScan = (async () => {
    try {
      const ownParas = item.frDoc?.dates ? [item.frDoc.dates] : [];
      if (item.frDoc) {
        try {
          const { text, truncated } = await frText(item.frDoc.raw_text_url);
          ownParas.push(...textParagraphs(text));
          item.ownText.scanned = true;
          item.ownText.partial = truncated;
          if (truncated)
            item.errors.push(
              `full text over ${TEXT_CAP >> 20} MB; only the first part was scanned for stated times`,
            );
        } catch (e) {
          item.ownText.error = e.message;
          item.errors.push(
            `full text: ${e.message} (stated-time scan covers DATES only)`,
          );
        }
      }
      item.ownText.times = statedTimes(ownParas);
    } catch (e) {
      item.ownText = { scanned: false, times: [], error: e.message };
      item.errors.push(`stated-time scan failed: ${e.message}`);
    }
  })();

  // Search aid for rule 3 (other FR documents on this docket or citing this document).
  // Not exhaustive: the page says so.
  const terms = new Set([docNum, ...idTerms]);
  for (const rin of item.parsed?.fr?.rins ?? []) terms.add(`RIN ${rin}`);
  const found = new Map();
  const order = [...terms];
  await Promise.all(
    order.map(async (t) => {
      try {
        const { results, count } = t.startsWith("RIN ")
          ? await frSearch(t.slice(4), "regulation_id_number")
          : await frSearch(t);
        // Counts exclude this document itself, so they match the table.
        const self = results.some((r) => r.document_number === docNum) ? 1 : 0;
        item.search.push({
          term: t,
          count: count - self,
          shown: results.length - self,
        });
        for (const r of results) {
          if (r.document_number === docNum) continue;
          const prev = found.get(r.document_number);
          if (prev) prev.matched.push(t);
          else found.set(r.document_number, { ...r, matched: [t] });
        }
      } catch (e) {
        item.search.push({ term: t, error: e.message });
        item.errors.push(`FR search "${t}": ${e.message}`);
      }
    }),
  );
  item.related = [...found.values()].sort((a, b) =>
    a.publication_date.localeCompare(b.publication_date),
  );
  // Promise.all settles in network order; show the searches in a stable order.
  item.search.sort(
    (a, b) =>
      (order.indexOf(a.term) + 1 || -1) - (order.indexOf(b.term) + 1 || -1),
  );
  await Promise.all([scanRelated(item), ownScan]);
  return item;
}

// For each related document: the sentences that set or change a submission deadline, from its
// DATES field (every row) and its full text (at most RELATED_TEXT_CAP rows: the ones published
// on or after this notice first, oldest first, then earlier ones, newest first). A row whose
// deadline is later than this notice's FR close is flagged.
const RELATED_TEXT_CAP = 15;
const SENTENCES_SHOWN = 6;
async function scanRelated(item) {
  const close =
    item.frDoc?.comments_close_on ??
    item.parsed?.latest?.fr?.commentsCloseOn ??
    null;
  item.closeForCompare = close;
  const pub = item.frDoc?.publication_date ?? item.parsed?.fr?.published ?? "";
  const after = item.related.filter((r) => r.publication_date >= pub);
  const before = item.related.filter((r) => r.publication_date < pub).reverse();
  const toRead = new Set(
    [...after, ...before]
      .slice(0, RELATED_TEXT_CAP)
      .map((r) => r.document_number),
  );
  const queue = item.related.slice();
  const one = async (r) => {
    const sents = [];
    const seen = new Set();
    const add = (s, src) => {
      const k = s.replace(/\s+/g, " ").toLowerCase();
      if (seen.has(k)) return;
      seen.add(k);
      sents.push({ text: s, src, dates: deadlineDates(s), all: isoDates(s) });
    };
    if (r.dates) for (const s of deadlineSentences([r.dates])) add(s, "DATES");
    if (toRead.has(r.document_number)) {
      try {
        const { text, truncated } = await frText(r.raw_text_url);
        const paras = textParagraphs(text);
        // Strong signals first, then the rest in document order.
        const all = deadlineSentences(paras);
        for (const s of all.filter(changes)) add(s, "text");
        for (const s of all) add(s, "text");
        r.textScan = truncated ? "partial" : "full";
      } catch (e) {
        r.textScan = "failed";
        r.textError = e.message;
      }
    } else r.textScan = "skipped";
    // Only dates a deadline connector points at decide the flag; any other later date in
    // these sentences (a hearing, a meeting) is reported separately for inspection.
    const latest =
      sents
        .flatMap((s) => s.dates)
        .sort()
        .at(-1) ?? null;
    const latestAny =
      sents
        .flatMap((s) => s.all)
        .sort()
        .at(-1) ?? null;
    r.deadline = {
      sentences: sents
        .slice(0, SENTENCES_SHOWN)
        .map(({ text, src }) => ({ text, src })),
      more: Math.max(0, sents.length - SENTENCES_SHOWN),
      latest,
      // Only a document published on or after this notice can extend or reopen it; a later
      // date in an earlier document (an original period this notice shortened) is "inspect".
      laterThanClose: !!(
        close &&
        latest &&
        latest > close &&
        r.publication_date >= pub
      ),
      laterOtherDate: null,
    };
    if (!r.deadline.laterThanClose && close) {
      const later = [latest, latestAny].filter((d) => d && d > close).sort();
      r.deadline.laterOtherDate = later.at(-1) ?? null;
    }
    delete r.dates; // shown through r.deadline
  };
  // Four at a time per item; the server loads two items at once.
  const run = async () => {
    while (queue.length) await one(queue.shift());
  };
  await Promise.all([run(), run(), run(), run()]);
  const failed = item.related.filter((r) => r.textScan === "failed").length;
  if (failed)
    item.errors.push(
      `related documents: ${failed} full-text fetch${failed > 1 ? "es" : ""} failed; those rows show DATES-field sentences only`,
    );
}

// Prefetch with low concurrency: each `review show` is a kubectl exec into the poller.
const cache = new Map();
const queue = [...ids];
function fetchItem(id) {
  if (!cache.has(id))
    cache.set(
      id,
      loadItem(id).catch((e) => ({
        id,
        docNum: id.match(OCD_RE)[1],
        errors: [e.message],
      })),
    );
  return cache.get(id);
}
async function worker() {
  while (queue.length) await fetchItem(queue.shift());
}
worker();
worker();

// ---------- seal ----------

function validate(body) {
  const errs = [];
  const items = Array.isArray(body?.items) ? body.items : [];
  const seen = new Set();
  for (const it of items) {
    if (it === null || typeof it !== "object") {
      errs.push("an item is not an object");
      continue;
    }
    if (!ids.includes(it.ocd_id)) errs.push(`unknown id ${it.ocd_id}`);
    if (seen.has(it.ocd_id)) errs.push(`duplicate ${it.ocd_id}`);
    seen.add(it.ocd_id);
    if (!KINDS.includes(it.kind)) errs.push(`${it.ocd_id}: kind`);
    if (it.kind === "pin_close" ? !isDate(it.close) : it.close != null)
      errs.push(
        `${it.ocd_id}: close is required for pin_close and only for it`,
      );
    if (
      typeof it.reason !== "string" ||
      !it.reason.trim() ||
      /[\r\n]/.test(it.reason)
    )
      errs.push(`${it.ocd_id}: one line of reasoning`);
  }
  for (const id of ids) if (!seen.has(id)) errs.push(`missing ${id}`);
  if (body?.attest !== true) errs.push("attestation not given");
  return errs;
}

async function seal(body) {
  const sealedAt = new Date().toISOString();
  const doc = {
    set: "held-out",
    set_date: opt.date,
    policy_version: opt.policy,
    sealed_at: sealedAt,
    attestation:
      "verdicts made from primary sources before reading any autopilot proposal, thread or ledger",
    items: ids.map((id) => {
      const it = body.items.find((x) => x.ocd_id === id);
      return {
        ocd_id: id,
        kind: it.kind,
        close: it.kind === "pin_close" ? it.close : null,
        reason: it.reason.trim(),
      };
    }),
  };
  const text = `${JSON.stringify(doc, null, 2)}\n`;
  // Write a private temp file, flush it, then publish it with link(): atomic and never replaces
  // an existing file (rename would). A crash leaves at most a stray temp file, never a
  // half-written answer key under the real name.
  const dir = dirname(outPath);
  await mkdir(dir, { recursive: true, mode: 0o700 });
  const tmp = join(
    dir,
    `.${basename(outPath)}.${process.pid}.${Date.now()}.tmp`,
  );
  const fh = await open(tmp, "wx", 0o600);
  try {
    try {
      await fh.writeFile(text);
      await fh.sync();
    } finally {
      await fh.close();
    }
    await link(tmp, outPath); // EEXIST if anything is already there
  } finally {
    await unlink(tmp).catch(() => {});
  }
  const dh = await open(dir, "r");
  try {
    await dh.sync();
  } catch {
    // some filesystems refuse fsync on a directory; the link is already in place
  } finally {
    await dh.close();
  }
  return {
    path: outPath,
    sha256: createHash("sha256").update(text).digest("hex"),
    sealed_at: sealedAt,
  };
}

// ---------- http ----------

function send(res, status, body, type = "application/json; charset=utf-8") {
  res.writeHead(status, {
    "content-type": type,
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "content-security-policy": `default-src 'none'; script-src ${SCRIPT_SRC}; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`,
    "x-frame-options": "DENY",
  });
  res.end(typeof body === "string" ? body : JSON.stringify(body));
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, "http://127.0.0.1");
    const host = (req.headers.host ?? "").split(":")[0];
    if (host !== "127.0.0.1" && host !== "localhost")
      return send(res, 403, { error: "local only" });
    if (req.method === "GET" && url.pathname === "/")
      return send(res, 200, PAGE, "text/html; charset=utf-8");
    if (req.method === "GET" && url.pathname === "/api/set")
      return send(res, 200, {
        ids,
        date: opt.date,
        policy: opt.policy,
        out: outPath,
        kinds: KINDS,
        sealed,
      });
    if (req.method === "GET" && url.pathname === "/api/item") {
      const id = url.searchParams.get("id");
      if (!ids.includes(id))
        return send(res, 404, { error: "not in this set" });
      if (url.searchParams.get("reload") === "1") cache.delete(id);
      return send(res, 200, await fetchItem(id));
    }
    if (req.method === "POST" && url.pathname === "/api/seal") {
      if (req.headers["content-type"] !== "application/json")
        return send(res, 415, { error: "json only" });
      if (sealed) return send(res, 409, { error: "already sealed", sealed });
      if (sealing) return send(res, 409, { error: "a seal is in progress" });
      const chunks = [];
      let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 1 << 20) return send(res, 413, { error: "too large" });
        chunks.push(chunk);
      }
      let body;
      try {
        body = JSON.parse(
          new TextDecoder("utf-8", { fatal: true }).decode(
            Buffer.concat(chunks),
          ),
        );
      } catch {
        return send(res, 400, { error: "body is not valid UTF-8 JSON" });
      }
      const errs = validate(body);
      if (errs.length)
        return send(res, 400, { error: "invalid", details: errs });
      if (sealed || sealing)
        return send(res, 409, { error: "already sealed or sealing" });
      sealing = true;
      try {
        sealed = await seal(body);
      } finally {
        sealing = false;
      }
      console.log(`sealed ${sealed.path} sha256=${sealed.sha256}`);
      return send(res, 200, { sealed });
    }
    send(res, 404, { error: "not found" });
  } catch (e) {
    send(res, 500, {
      error:
        e.code === "EEXIST"
          ? "the output file already exists; nothing was written"
          : e.message,
    });
  }
});
server.listen(port, "127.0.0.1", () => {
  console.log(
    `held-out workbench: http://127.0.0.1:${port}/  (${ids.length} items, policy ${opt.policy})`,
  );
  console.log(`seals to: ${outPath}`);
});

// ---------- page ----------

const PAGE = String.raw`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Held-out set</title>
<style>
:root {
  --bg: #f6f5f2; --panel: #ffffff; --ink: #1c1d1f; --muted: #6a6d73; --line: #e2e0da;
  --accent: #2f5bd3; --accent-ink: #fff; --ok: #1f7a4d; --warn: #9a5b00; --bad: #b42318;
  --chip: #efede8; --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #141518; --panel: #1c1e22; --ink: #e8e8ea; --muted: #9a9ca3; --line: #2c2f35;
    --accent: #7c9cff; --accent-ink: #0b1020; --ok: #4fc58a; --warn: #e3a64b; --bad: #ff7a6e; --chip: #262930; }
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html, body { margin: 0; height: 100%; }
body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--ink); }
a { color: var(--accent); }
.app { display: grid; grid-template-columns: 300px 1fr; height: 100vh; }
aside { border-right: 1px solid var(--line); background: var(--panel); display: flex; flex-direction: column; min-height: 0; }
aside header { padding: 16px 16px 12px; border-bottom: 1px solid var(--line); }
aside h1 { font-size: 15px; margin: 0 0 2px; }
.sub { color: var(--muted); font-size: 12px; }
.progress { height: 4px; background: var(--chip); border-radius: 2px; margin-top: 10px; overflow: hidden; }
.progress > i { display: block; height: 100%; background: var(--ok); width: 0; transition: width .2s; }
ol.items { list-style: none; margin: 0; padding: 6px; overflow: auto; flex: 1; }
ol.items li button { all: unset; box-sizing: border-box; width: 100%; display: grid; grid-template-columns: 22px 1fr auto; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 6px; cursor: pointer; }
ol.items li button:hover { background: var(--chip); }
ol.items li button[aria-current="true"] { background: var(--chip); box-shadow: inset 3px 0 0 var(--accent); }
ol.items li button:focus-visible { outline: 2px solid var(--accent); }
.n { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 12px; }
.t { overflow: hidden; }
.t b { display: block; font-weight: 600; font-size: 13px; font-family: var(--mono); }
.t span { display: block; color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dot { width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--line); }
.dot.partial { border-color: var(--warn); }
.dot.done { background: var(--ok); border-color: var(--ok); }
aside footer { padding: 12px 16px; border-top: 1px solid var(--line); display: grid; gap: 8px; }
.banner { font-size: 12px; color: var(--warn); }
main { overflow: auto; min-height: 0; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 20px 28px 140px; display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
.col { display: grid; gap: 16px; min-width: 0; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; min-width: 0; }
.card h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 10px; font-weight: 600; }
.title { font-size: 18px; font-weight: 650; line-height: 1.3; margin: 0 0 6px; }
.meta { color: var(--muted); font-size: 13px; display: flex; flex-wrap: wrap; gap: 4px 14px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.chip { background: var(--chip); border-radius: 999px; padding: 2px 9px; font-size: 12px; font-family: var(--mono); }
.chip.c-conflicting { color: var(--bad); }
.chip.alarm { background: color-mix(in srgb, var(--bad) 16%, transparent); color: var(--bad); font-weight: 650; font-family: inherit; }
.chip.flag { background: color-mix(in srgb, var(--warn) 20%, transparent); color: var(--warn); font-weight: 600; font-family: inherit; }
.note { margin-top: 10px; border-left: 3px solid var(--warn); padding: 6px 10px; font-size: 13px; background: color-mix(in srgb, var(--warn) 8%, transparent); border-radius: 0 6px 6px 0; }
.note.bad { border-left-color: var(--bad); background: color-mix(in srgb, var(--bad) 8%, transparent); }
.note b { display: block; margin-bottom: 4px; }
ul.evid { margin: 6px 0 0; padding-left: 18px; font-size: 13px; }
ul.evid li { margin: 3px 0; }
ul.evid .src { border: 0; padding: 0; color: var(--muted); font-size: 11px; font-family: var(--mono); }
mark.tm { background: color-mix(in srgb, var(--bad) 25%, transparent); color: inherit; border-radius: 3px; padding: 0 2px; font-weight: 600; }
.links { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.links a { font-size: 13px; text-decoration: none; border: 1px solid var(--line); border-radius: 6px; padding: 4px 10px; }
.links a:hover { border-color: var(--accent); }
.sources { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.src { border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
.src .k { color: var(--muted); font-size: 12px; }
.src .v { font-size: 20px; font-weight: 650; font-variant-numeric: tabular-nums; margin: 2px 0; }
.src .x { color: var(--muted); font-size: 12px; font-family: var(--mono); word-break: break-all; }
.dates { white-space: pre-wrap; font-size: 14px; line-height: 1.6; }
.dates mark, ul.evid mark, .note mark { background: color-mix(in srgb, var(--warn) 22%, transparent); color: inherit; border-radius: 3px; padding: 0 2px; }
table.rel { width: 100%; border-collapse: collapse; font-size: 13px; }
table.rel td, table.rel th { text-align: left; padding: 6px 8px; border-top: 1px solid var(--line); vertical-align: top; }
table.rel th { color: var(--muted); font-weight: 500; font-size: 12px; border-top: 0; }
table.rel td:first-child { white-space: nowrap; font-variant-numeric: tabular-nums; }
details summary { cursor: pointer; color: var(--muted); font-size: 13px; }
pre { font-family: var(--mono); font-size: 12px; white-space: pre-wrap; word-break: break-all; margin: 10px 0 0; }
.err { color: var(--bad); font-size: 13px; }
.loading { color: var(--muted); padding: 40px 0; text-align: center; }
.verdict { position: sticky; top: 20px; display: grid; gap: 12px; }
.kinds { display: grid; gap: 6px; }
.kind { all: unset; box-sizing: border-box; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; cursor: pointer; display: grid; gap: 1px; }
.kind b { font-family: var(--mono); font-size: 13px; }
.kind span { color: var(--muted); font-size: 12px; }
.kind:hover { border-color: var(--accent); }
.kind:focus-visible { outline: 2px solid var(--accent); }
.kind[aria-pressed="true"] { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }
label.f { display: grid; gap: 4px; font-size: 12px; color: var(--muted); }
input[type=date], input[type=text] { font: inherit; color: var(--ink); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 7px 9px; width: 100%; }
input:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.btn { font: inherit; font-weight: 600; border: 1px solid var(--line); background: var(--panel); color: var(--ink); border-radius: 7px; padding: 8px 12px; cursor: pointer; }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.row { display: flex; gap: 8px; }
.row .btn { flex: 1; }
.hint { color: var(--muted); font-size: 12px; }
.saved { color: var(--ok); font-size: 12px; min-height: 18px; }
.overlay { position: fixed; inset: 0; background: rgb(0 0 0 / .45); display: grid; place-items: center; z-index: 10; }
.sheet { border: 1px solid var(--line); border-radius: 12px; background: var(--panel); color: var(--ink); max-width: 820px; width: 92vw; max-height: 88vh; overflow: auto; padding: 20px; }
.sheet h3 { margin: 0 0 8px; }
.sheet table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0 14px; }
.sheet td, .sheet th { text-align: left; padding: 6px 8px; border-top: 1px solid var(--line); vertical-align: top; }
.sheet td:first-child { font-family: var(--mono); white-space: nowrap; }
.sealed-box { border: 1px solid var(--ok); border-radius: 10px; padding: 14px; font-size: 13px; }
.sealed-box code { font-family: var(--mono); word-break: break-all; }
@media (max-width: 1100px) { .wrap { grid-template-columns: 1fr; } .verdict { position: static; } }
</style>
</head>
<body>
<div class="app">
  <aside>
    <header>
      <h1>Held-out set</h1>
      <div class="sub" id="setmeta">loading…</div>
      <div class="progress"><i id="bar"></i></div>
    </header>
    <ol class="items" id="list"></ol>
    <footer>
      <div class="banner">Blind protocol: don't open the Review autopilot thread or ledger until this is sealed.</div>
      <button class="btn primary" id="sealBtn" disabled>Review &amp; seal</button>
      <div class="hint">Drafts are kept in this browser only. Nothing is written to disk until you seal.</div>
    </footer>
  </aside>
  <main id="main"><div class="loading">Loading…</div></main>
</div>
<div id="dlg" class="overlay" hidden><div class="sheet" id="sheet" role="dialog" aria-modal="true" aria-label="Seal verdicts"></div></div>
<script>
"use strict";
const KIND_HELP = {
  pin_close: "The operative close is a date you can establish from the primary sources.",
  escalate: "Sources examined, but the discrepancy can't be resolved from the documents.",
  confirm_withdrawn: "The notice is withdrawn.",
  confirm_reopened: "The window is open again.",
  dismiss_conflict: "The detected disagreement is noise (no winner picked).",
};
let SET = null, current = 0, drafts = {};
const itemsCache = {};
const $ = (s) => document.querySelector(s);
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
}
const storeKey = () => "heldout:" + SET.date + ":" + SET.policy + ":" + SET.ids.join(",");
function loadDrafts() { try { drafts = JSON.parse(localStorage.getItem(storeKey()) || "{}"); } catch { drafts = {}; } }
let draftsUnsaved = null;
function saveDrafts() {
  try { localStorage.setItem(storeKey(), JSON.stringify(drafts)); }
  catch (e) { draftsUnsaved = e.name || "error"; renderList(); }
}
const shortId = (id) => id.split("/").pop();
const safeUrl = (u) => (typeof u === "string" && /^https:\/\//.test(u) ? u : null);
function state(id) {
  const d = drafts[id];
  if (!d || (!d.kind && !d.reason)) return "";
  return complete(d) ? "done" : "partial";
}
function complete(d) {
  return !!d && !!d.kind && (d.kind !== "pin_close" || /^\d{4}-\d{2}-\d{2}$/.test(d.close || "")) && !!(d.reason || "").trim();
}
function etFromZ(z) {
  const d = new Date(z);
  if (isNaN(d)) return null;
  return d.toLocaleString("en-US", { timeZone: "America/New_York", year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
}
function etDate(z) {
  const d = new Date(z);
  if (isNaN(d)) return null;
  const p = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
  return p;
}

function renderList() {
  const list = $("#list");
  list.replaceChildren(...SET.ids.map((id, i) => {
    const it = itemsCache[id];
    const title = it && it.frDoc ? it.frDoc.title : (it && it.parsed && it.parsed.fr ? it.parsed.fr.title : "…");
    const agency = it && it.frDoc && it.frDoc.agencies ? it.frDoc.agencies.map((a) => a.name).filter(Boolean)[0] : "";
    return h("li", null, h("button", { "aria-current": i === current ? "true" : "false", onclick: () => select(i) },
      h("span", { class: "n" }, i + 1),
      h("span", { class: "t" }, h("b", null, shortId(id)), h("span", { title }, (agency ? agency + " · " : "") + title)),
      h("span", { class: "dot " + state(id), title: state(id) || "not started" })));
  }));
  const done = SET.ids.filter((id) => complete(drafts[id])).length;
  $("#bar").style.width = (100 * done / SET.ids.length) + "%";
  $("#setmeta").textContent = done + " of " + SET.ids.length + " judged · policy " + SET.policy + " · set " + SET.date +
    (draftsUnsaved ? " · DRAFTS NOT SAVED (" + draftsUnsaved + "): finish and seal in this tab" : "");
  $("#sealBtn").disabled = !!SET.sealed || done !== SET.ids.length;
}

// flags[w/e/r] from the blind output: is_withdrawal, is_extension, is_reopening.
function werText(w) {
  const on = ["withdrawal", "extension", "reopening"].filter((_, i) => w[i] === "1");
  return on.length ? "notice flags: " + on.join(", ") : "notice flags: none";
}
// Marks dates, and (when given) the stated times the server found, as text nodes only.
function highlightDates(text, times) {
  const frag = document.createDocumentFragment();
  const MON = "(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\\.?";
  const esc = (x) => x.replace(/[.*+?^$(){}|[\]\\]/g, "\\$&");
  const tm = [...new Set(times || [])].sort((a, b) => b.length - a.length).map(esc);
  const re = new RegExp("(" + MON + " \\d{1,2}(?:, \\d{4})?|\\b\\d{1,2}/\\d{1,2}/\\d{4}\\b)" + (tm.length ? "|(" + tm.join("|") + ")" : ""), "g");
  let last = 0, m;
  while ((m = re.exec(text))) {
    frag.append(text.slice(last, m.index), m[1] ? h("mark", null, m[1]) : h("mark", { class: "tm" }, m[2]));
    last = m.index + m[0].length;
  }
  frag.append(text.slice(last));
  return frag;
}
function timeList(it) {
  return [...new Set(((it.ownText || {}).times || []).flatMap((x) => x.times))];
}

function renderItem(it) {
  const id = SET.ids[current];
  const p = it.parsed || {};
  const doc = it.frDoc || {};
  const fr = p.fr || {};
  const regs = p.regs || {};
  const dockets = [...new Set([...(doc.docket_ids || []), ...(fr.dockets || [])])];
  const regsLatest = (p.latest || {}).regs;
  const frLatest = (p.latest || {}).fr;
  const pub = doc.publication_date || fr.published;
  const ids = it.docketIds || [];
  const own = it.ownText || {};
  const times = timeList(it);

  const links = h("div", { class: "links" },
    h("a", { href: safeUrl(doc.html_url) || ("https://www.federalregister.gov/d/" + it.docNum), target: "_blank", rel: "noopener" }, "Federal Register ↗"),
    pub && h("a", { href: "https://www.govinfo.gov/content/pkg/FR-" + pub + "/html/" + it.docNum + ".htm", target: "_blank", rel: "noopener" }, "GovInfo text ↗"),
    regs.documentId && h("a", { href: "https://www.regulations.gov/document/" + encodeURIComponent(regs.documentId), target: "_blank", rel: "noopener" }, "Regs.gov document ↗"),
    regs.docket && h("a", { href: "https://www.regulations.gov/docket/" + encodeURIComponent(regs.docket), target: "_blank", rel: "noopener" }, "Regs.gov docket ↗"),
    h("a", { href: "https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=" + encodeURIComponent('"' + (ids[0] || it.docNum) + '"'), target: "_blank", rel: "noopener" }, "FR search ↗"));

  const head = h("div", { class: "card" },
    h("div", { class: "title" }, doc.title || fr.title || it.docNum),
    h("div", { class: "meta" },
      h("span", null, (doc.agencies || []).map((a) => a.name || a.raw_name).filter(Boolean).join(" / ")),
      doc.type && h("span", null, doc.type),
      fr.citation && h("span", null, fr.citation),
      pub && h("span", null, "published " + pub),
      (fr.rins || []).length ? h("span", null, "RIN " + fr.rins.join(", ")) : null),
    h("div", { class: "chips" },
      times.length ? h("span", { class: "chip alarm", title: "See the DATES card" }, "⚠ Deadline time stated: " + times.join(", ")) : null,
      own.scanned === false && h("span", { class: "chip flag", title: own.error || "" }, "full text not scanned for stated times"),
      own.partial && h("span", { class: "chip flag" }, "full text only partly scanned for stated times"),
      p.confidence && h("span", { class: "chip c-" + p.confidence }, p.confidence),
      p.status && h("span", { class: "chip" }, "status " + p.status),
      ...(p.flags || []).map((f) => h("span", { class: "chip" }, f)),
      ...dockets.map((d) => h("span", { class: "chip" }, d))),
    ids.length > 1 ? h("div", { class: "note" }, "This notice covers " + ids.length + " dockets: " + ids.join(", ") + " — check whether any extension or memo applies to all of them.") : null,
    links);

  const sources = h("div", { class: "card" }, h("h2", null, "What each source says now"),
    h("div", { class: "sources" },
      h("div", { class: "src" }, h("div", { class: "k" }, "Federal Register · comments_close_on"),
        h("div", { class: "v" }, frLatest ? frLatest.commentsCloseOn : "—"),
        doc.comments_close_on && doc.comments_close_on !== (frLatest && frLatest.commentsCloseOn) &&
          h("div", { class: "x" }, "FR API today: " + doc.comments_close_on),
        h("div", { class: "x" }, frLatest ? "observed " + frLatest.observedAt + (frLatest.wer ? " · " + werText(frLatest.wer) : "") : "")),
      h("div", { class: "src" }, h("div", { class: "k" }, "Regulations.gov · commentEndDate"),
        h("div", { class: "v" }, regsLatest ? (etDate(regsLatest.commentEndDate) || regsLatest.commentEndDate) : "—"),
        regsLatest && h("div", { class: "x" }, regsLatest.commentEndDate + " = " + (etFromZ(regsLatest.commentEndDate) || "?")),
        regsLatest && h("div", { class: "x" }, "withdrawn=" + regsLatest.withdrawn + " open=" + regsLatest.openForComment + " · observed " + regsLatest.observedAt + (regsLatest.wer ? " · " + werText(regsLatest.wer) : "")))),
    (p.amendments || []).length ? h("div", { class: "hint", style: "margin-top:10px" },
      "Linked amendments (ADR 0016) DocketClock already applies to this window: ",
      ...p.amendments.map((a, i) => [i ? ", " : "", h("a", { href: "https://www.federalregister.gov/d/" + encodeURIComponent(a.docNum), target: "_blank", rel: "noopener" }, a.docNum), " (" + a.source + ")"])) : null,
    p.conflicts != null && h("div", { class: "hint", style: "margin-top:6px" }, "Live conflicts on this window: " + p.conflicts),
    p.close && h("div", { class: "hint", style: "margin-top:6px" }, "Machine derivation: " + p.close));

  const dates = h("div", { class: "card" }, h("h2", null, "DATES section (Federal Register)"),
    doc.dates ? h("div", { class: "dates" }, highlightDates(doc.dates, times)) : h("div", { class: "hint" }, "No DATES text in the FR API; read the document."),
    times.length ? h("div", { class: "note bad" },
      h("b", null, "Deadline time stated: " + times.join(", ") + " — rules 1 and 2a: a document stating a deadline time other than 11:59 p.m. Eastern → escalate. Check that each sentence sets a participation deadline (not office hours or a meeting time)."),
      h("ul", { class: "evid" }, ...own.times.map((x) => h("li", null, highlightDates(x.sentence, x.times))))) : null,
    h("div", { class: "hint", style: "margin-top:8px" }, own.scanned && own.partial
      ? "Full text only PARTLY scanned (very long document: the first part only)" + (times.length ? "." : "; no stated time found in that part, the rest is unchecked.")
      : own.scanned
      ? (times.length ? "Scanned the full text (not only DATES) for deadline times." : "Scanned the full text (not only DATES): no deadline time other than 11:59 p.m. Eastern found near a deadline. Search aid, not proof.")
      : "Full text NOT scanned (" + (own.error || "no FR record") + "); only DATES was checked for stated times."),
    doc.action && h("div", { class: "hint", style: "margin-top:8px" }, "Action: " + doc.action));

  const rel = it.related || [];
  const related = h("div", { class: "card" }, h("h2", null, "Other FR documents mentioning this docket or document"),
    h("div", { class: "hint" }, "Search aid only, not exhaustive. Extensions sometimes appear only on Regulations.gov, so check the docket too before concluding nothing superseded the date."),
    h("div", { class: "hint" }, "Searched: ", ...(it.search || []).map((x, i) => [i ? " · " : "", x.term + ": " + (x.skipped ? "not searched (" + x.skipped + ")" : x.error ? "FAILED (" + x.error + ")" : x.count > x.shown ? x.shown + " newest of " + x.count + " shown" : x.count + " found")])),
    rel.length ? h("table", { class: "rel" },
      h("tr", null, h("th", null, "published"), h("th", null, "type"), h("th", null, "document"), h("th", null, "closes")),
      ...rel.map((r) => h("tr", null, h("td", null, r.publication_date), h("td", null, r.type),
        h("td", null, h("a", { href: safeUrl(r.html_url), target: "_blank", rel: "noopener" }, r.document_number), " ", r.title,
          h("div", { class: "hint" }, "matched " + r.matched.join(", ")),
          relEvidence(r, it.closeForCompare)),
        h("td", null, r.comments_close_on || "", r.deadline && r.deadline.laterThanClose ? h("div", null, h("span", { class: "chip flag", title: "A deadline in this document (" + r.deadline.latest + ") is later than this notice's FR close (" + it.closeForCompare + ")" }, "may reopen/extend")) : r.deadline && r.deadline.laterOtherDate ? h("div", null, h("span", { class: "chip", title: "A date in a deadline sentence (" + r.deadline.laterOtherDate + ") is later than this notice's FR close, but no deadline connector points at it or the document predates this notice" }, "later date — inspect")) : null)))) :
      h("div", { style: "margin-top:8px" }, (it.search || []).some((x) => x.error) ? "None found, but at least one search failed; see above." : "None found by this search."));

  const raw = h("div", { class: "card" }, h("details", null, h("summary", null, "Raw review show --blind output"), h("pre", null, it.blindText || "(none)")));
  const errs = (it.errors || []).length ? h("div", { class: "card" },
    ...it.errors.map((e) => h("div", { class: "err" }, e)),
    h("button", { class: "btn", style: "margin-top:8px", onclick: () => select(current, true) }, "Retry")) : null;

  return h("div", { class: "col" }, head, errs, sources, dates, related, raw);
}

// Why a related document matters: the sentences in it that set or change a submission deadline.
function relEvidence(r, close) {
  const d = r.deadline;
  if (!d) return null;
  const scan = r.textScan === "failed" ? "full text FAILED (" + r.textError + "); DATES field only"
    : r.textScan === "skipped" ? "full text not scanned (cap of 15 per item); DATES field only"
    : r.textScan === "partial" ? "full text scanned (first part only: very long document)" : "DATES and full text scanned";
  return h("div", null,
    d.sentences.length ? h("ul", { class: "evid" }, ...d.sentences.map((x) => h("li", null, h("span", { class: "src" }, x.src + " "), highlightDates(x.text)))) : null,
    h("div", { class: "hint" }, (d.sentences.length ? (d.more ? "+" + d.more + " more deadline sentences · " : "") : "No deadline-setting sentence found · ") + scan +
      (d.laterThanClose ? " · deadline " + d.latest + " is after this notice's FR close " + close : d.laterOtherDate ? " · a later date (" + d.laterOtherDate + ") appears, but not as a deadline set by a document published on or after this notice; read the sentence" : "")));
}

function renderVerdict() {
  const id = SET.ids[current];
  const d = drafts[id] || (drafts[id] = { kind: "", close: "", reason: "" });
  const locked = !!SET.sealed;
  const upd = (patch) => { Object.assign(d, patch); saveDrafts(); $("#savedNote").textContent = "Draft saved"; renderList(); refreshVerdictState(); };
  const kinds = h("div", { class: "kinds", role: "group", "aria-label": "Verdict kind" }, ...SET.kinds.map((k, i) =>
    h("button", { class: "kind", "aria-pressed": d.kind === k ? "true" : "false", disabled: locked, "data-kind": k,
      onclick: () => { upd({ kind: k, close: k === "pin_close" ? d.close : "" }); for (const b of document.querySelectorAll(".kind")) b.setAttribute("aria-pressed", b.dataset.kind === k ? "true" : "false"); $("#closeWrap").hidden = k !== "pin_close"; if (k === "pin_close") $("#close").focus(); else $("#reason").focus(); } },
      h("b", null, (i + 1) + "  " + k), h("span", null, KIND_HELP[k] || ""))));
  const close = h("label", { class: "f", id: "closeWrap", hidden: d.kind !== "pin_close" }, "Operative close (11:59 p.m. ET convention)",
    h("input", { type: "date", id: "close", value: d.close || "", disabled: locked, oninput: (e) => upd({ close: e.target.value }) }));
  const reason = h("label", { class: "f" }, "One line of reasoning",
    h("input", { type: "text", id: "reason", maxlength: "400", value: d.reason || "", disabled: locked, placeholder: "Which source or passage settles it, and why",
      oninput: (e) => upd({ reason: e.target.value.replace(/[\r\n]+/g, " ") }) }));
  const nav = h("div", { class: "row" },
    h("button", { class: "btn", disabled: current === 0, onclick: () => select(current - 1) }, "← Prev"),
    h("button", { class: "btn primary", id: "nextBtn", onclick: () => select(Math.min(current + 1, SET.ids.length - 1)) }, current === SET.ids.length - 1 ? "Done" : "Next →"));
  return h("div", { class: "verdict" },
    h("div", { class: "card" }, h("h2", null, "Your verdict · " + (current + 1) + " of " + SET.ids.length), kinds),
    h("div", { class: "card", style: "display:grid;gap:12px" }, close, reason, h("div", { class: "saved", id: "savedNote" }, complete(d) ? "Complete" : ""), nav,
      h("div", { class: "hint" }, "Keys: 1–5 pick a kind (outside text boxes) · ⌘/Ctrl+Enter next · Alt+↑/↓ move")));
}
function refreshVerdictState() {
  const d = drafts[SET.ids[current]];
  if (complete(d)) $("#savedNote").textContent = "Complete";
}

async function select(i, reload) {
  current = i;
  renderList();
  const id = SET.ids[i];
  const main = $("#main");
  if (!itemsCache[id] || reload) {
    main.replaceChildren(h("div", { class: "wrap" }, h("div", { class: "col" }, h("div", { class: "card loading" }, "Fetching the blind view for " + shortId(id) + " (kubectl exec, can take ~10 s)…")), renderVerdict()));
    try {
      const r = await fetch("/api/item?id=" + encodeURIComponent(id) + (reload ? "&reload=1" : ""));
      itemsCache[id] = await r.json();
    } catch (e) {
      itemsCache[id] = { id, errors: [String(e)] };
    }
    if (current !== i) return;
    renderList();
  }
  main.replaceChildren(SET.sealed ? sealedBox() : "", h("div", { class: "wrap" }, renderItem(itemsCache[id]), renderVerdict()));
  main.scrollTop = 0;
}

function sealedBox() {
  return h("div", { style: "max-width:1100px;margin:20px auto 0;padding:0 28px" }, h("div", { class: "sealed-box" },
    h("b", null, "Sealed. "), "Written to ", h("code", null, SET.sealed.path), " at " + SET.sealed.sealed_at + ".",
    h("div", null, "sha256 ", h("code", null, SET.sealed.sha256)),
    h("div", { class: "hint", style: "margin-top:6px" }, "You can now let the shadow runs propose and compare. Read-only from here.")));
}

function openSeal() {
  const dlg = $("#dlg"), sheet = $("#sheet");
  const rows = SET.ids.map((id) => { const d = drafts[id]; return h("tr", null, h("td", null, shortId(id)), h("td", null, d.kind), h("td", null, d.kind === "pin_close" ? d.close : ""), h("td", null, d.reason)); });
  const attest = h("input", { type: "checkbox", id: "attest" });
  const go = h("button", { class: "btn primary", disabled: true, onclick: doSeal }, "Seal (write once)");
  attest.addEventListener("change", () => { go.disabled = !attest.checked; });
  sheet.replaceChildren(h("h3", null, "Seal " + SET.ids.length + " verdicts"),
    h("div", { class: "hint" }, "Writes " + SET.out + " once. It can't be edited or overwritten from here."),
    h("table", null, h("tr", null, h("th", null, "id"), h("th", null, "kind"), h("th", null, "close"), h("th", null, "reason")), ...rows),
    h("label", { style: "display:flex;gap:8px;align-items:flex-start;margin-bottom:14px" }, attest,
      h("span", null, "I made these verdicts from the primary sources, before reading any autopilot proposal, thread or ledger for this policy version.")),
    h("div", { id: "sealErr", class: "err" }),
    h("div", { class: "row" }, h("button", { class: "btn", onclick: closeSeal }, "Back"), go));
  dlg.hidden = false;
  attest.focus();
}
function closeSeal() { $("#dlg").hidden = true; }
async function doSeal() {
  const items = SET.ids.map((id) => ({ ocd_id: id, kind: drafts[id].kind, close: drafts[id].kind === "pin_close" ? drafts[id].close : null, reason: drafts[id].reason.trim() }));
  const r = await fetch("/api/seal", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ items, attest: true }) });
  const j = await r.json();
  if (!r.ok) { $("#sealErr").textContent = j.error + (j.details ? ": " + j.details.join("; ") : ""); return; }
  SET.sealed = j.sealed;
  closeSeal();
  renderList();
  select(current);
}

document.addEventListener("keydown", (e) => {
  if (SET && !$("#dlg").hidden) { if (e.key === "Escape") closeSeal(); return; }
  if (!SET || SET.sealed) return;
  const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); if (current < SET.ids.length - 1) select(current + 1); }
  else if (e.altKey && e.key === "ArrowDown") { e.preventDefault(); if (current < SET.ids.length - 1) select(current + 1); }
  else if (e.altKey && e.key === "ArrowUp") { e.preventDefault(); if (current > 0) select(current - 1); }
  else if (!typing && !e.metaKey && !e.ctrlKey && !e.altKey && /^[1-5]$/.test(e.key)) { e.preventDefault(); const b = document.querySelector('.kind[data-kind="' + SET.kinds[+e.key - 1] + '"]'); if (b) b.click(); }
});
$("#sealBtn").addEventListener("click", openSeal);

(async () => {
  SET = await (await fetch("/api/set")).json();
  loadDrafts();
  renderList();
  select(0);
  // Warm the sidebar titles in the background, two at a time like the server.
  const rest = SET.ids.slice(1);
  const warm = async () => { while (rest.length) { const id = rest.shift(); if (!itemsCache[id]) { try { itemsCache[id] = await (await fetch("/api/item?id=" + encodeURIComponent(id))).json(); } catch {} renderList(); } } };
  warm(); warm();
})();
</script>
</body>
</html>`;
// The page's single inline script, allowed by hash instead of 'unsafe-inline'.
const SCRIPT_SRC = `'sha256-${createHash("sha256")
  .update(PAGE.match(/<script>([\s\S]*?)<\/script>/)[1])
  .digest("base64")}'`;
