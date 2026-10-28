/**
 * govinfo.test.ts — the GovInfo source adapter (ADR 0016; docs/plans/fr-amendment-linking.md part 1),
 * PURE + a local HTTP fake (no network, no DB).
 *
 * Proves, on the REAL recorded GPO pages (test/fixtures/fr-amendments/govinfo/*.htm):
 *   • govinfoPlainText — the <pre> block only, tags stripped, entities decoded, CRLF normalized;
 *   • extractDatesSection — USDA 2026-19710's full DATES (the citation + "on or before November 2, 2026"
 *     the truncated FR API `dates` lacks), ending at ADDRESSES:, whitespace-collapsed;
 *   • extractCorrectionBody — C1-2026-18574's instruction, starting at "In proposed rule document",
 *     ending before "[FR Doc.";
 *   • parseGovinfoObservation — source govinfo on the AMENDMENT's own ocd_id, govinfo-v1, all flags
 *     false, the verbatim raw + a stable payload_hash, contract-valid;
 *   • fetchTextWithRetry / fetchGovinfoHtml — 200 → text, 404 → null ("not published yet") only when
 *     asked, other 4xx fail fast (one request), 5xx retried; GOVINFO_API_BASE overrides the base.
 *
 * Run: pnpm --filter @yokel/docketclock exec tsx test/govinfo.test.ts
 */
import { createServer, type Server } from "node:http";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  extractCorrectionBody,
  extractDatesSection,
  fetchGovinfoHtml,
  govinfoHtmlUrl,
  govinfoPlainText,
  parseGovinfoObservation,
  PARSER_VERSION,
  stripNul,
} from "../src/sources/govinfo.js";
import {
  fetchJsonWithRetry,
  fetchTextWithRetry,
  postJsonWithRetry,
} from "../src/sources/http.js";
import { ObservationCandidateSchema } from "../src/sources/observation-candidate.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const FIX = join(
  dirname(fileURLToPath(import.meta.url)),
  "fixtures",
  "fr-amendments",
  "govinfo",
);
const html = (doc: string) => readFileSync(join(FIX, `${doc}.htm`), "utf8");

// ── govinfoPlainText ────────────────────────────────────────────────────────────────────────────────
{
  const t = govinfoPlainText(html("2026-19710"));
  assert("plain text: no tags survive", !/<[a-z/][^>]*>/i.test(t));
  assert(
    "plain text: <head> title is not document text (the <pre> block only)",
    !t.includes("Federal Register, Volume 91 Issue 185 (Friday"),
  );
  assert(
    "plain text: anchor text kept, markup dropped",
    t.includes("Federal eRulemaking \nPortal: http://www.regulations.gov") ||
      t.includes("http://www.regulations.gov"),
  );
  const ent = govinfoPlainText(
    "<pre>A &amp; B &lt;x&gt; &quot;q&quot; &#39;s&#39; &#8220;c&#8221; &#x41; &bogus;\r\nnext\rline</pre>",
  );
  assert(
    "plain text: entities decoded (named + decimal + hex); unknown entity left verbatim",
    ent === `A & B <x> "q" 's' “c” A &bogus;\nnext\nline`,
    JSON.stringify(ent),
  );
}

// ── extractDatesSection ─────────────────────────────────────────────────────────────────────────────
{
  const usda = extractDatesSection(govinfoPlainText(html("2026-19710")));
  assert(
    "DATES (USDA 19710): the full published sentence, citation + new close",
    usda ===
      "The comment period for the document originally published on September 11, 2026, (91 FR 57828) is extended 20 days. Comments must be submitted on or before November 2, 2026.",
    JSON.stringify(usda),
  );
  const census = extractDatesSection(govinfoPlainText(html("2026-20328")));
  assert(
    "DATES (Census 20328): ends at ADDRESSES:",
    census === "Submit comments on or before November 2, 2026.",
    JSON.stringify(census),
  );
  const uscg = extractDatesSection(govinfoPlainText(html("2026-19895")));
  assert(
    "DATES (USCG 19895): line-wrapped citation collapsed to single spaces",
    !!uscg?.includes("at 91 FR 54729, is reopened") &&
      !/\s{2,}/.test(uscg ?? ""),
    JSON.stringify(uscg),
  );
  assert(
    "DATES: absent → null",
    extractDatesSection("SUMMARY: nothing here\nADDRESSES: x") === null,
  );
  assert(
    "DATES: a prose mention of 'the DATES section' is not the header",
    extractDatesSection(govinfoPlainText(html("C1-2026-18574"))) === null,
  );
  assert(
    "DATES: runs to the end when no later header exists",
    extractDatesSection("DATES: Comments by\n November 2, 2026.") ===
      "Comments by November 2, 2026.",
  );
}

// ── extractCorrectionBody ───────────────────────────────────────────────────────────────────────────
{
  const body = extractCorrectionBody(govinfoPlainText(html("C1-2026-18574")));
  assert(
    "correction body (C1-2026-18574): the instruction, collapsed, without the FR Doc footer",
    body ===
      "In proposed rule document 2026-18574 beginning on page 57968 in the issue of Friday, September 11, 2026, make the following correction: On page 57968, in the first column, in the second line of the DATES section, ``October 16, 2026'' should read ``October 26, 2026''.",
    JSON.stringify(body),
  );
  assert(
    "correction body: a non-correction document → null",
    extractCorrectionBody(govinfoPlainText(html("2026-20328"))) === null,
  );
}

// ── parseGovinfoObservation ─────────────────────────────────────────────────────────────────────────
{
  const url = govinfoHtmlUrl("2026-09-28", "C1-2026-18574");
  const c = parseGovinfoObservation({
    frDocNum: "C1-2026-18574",
    publicationDate: "2026-09-28",
    url,
    html: html("C1-2026-18574"),
    isCorrection: true,
    fetchedAt: "2026-10-27T12:00:00.000Z",
  });
  assert("parse: source govinfo", c.source === "govinfo");
  assert(
    "parse: the AMENDMENT's own ocd_id",
    c.ocd_id === "ocd-participation-window/federal/C1-2026-18574",
    c.ocd_id,
  );
  assert(
    "parse: parser_version govinfo-v1",
    c.parser_version === "govinfo-v1" && PARSER_VERSION === "govinfo-v1",
  );
  assert(
    "parse: all four notice flags false (evidence text, never a classification)",
    !c.is_extension && !c.is_correction && !c.is_withdrawal && !c.is_reopening,
  );
  assert(
    "parse: correction → raw_dates_text is the correction body",
    !!c.raw_dates_text?.startsWith("In proposed rule document 2026-18574") &&
      !!c.raw_dates_text?.includes("should read ``October 26, 2026''"),
  );
  const raw = c.raw as Record<string, unknown>;
  assert(
    "parse: raw is the verbatim upstream body + the identity it was fetched under",
    raw.html === html("C1-2026-18574") &&
      raw.document_number === "C1-2026-18574" &&
      raw.publication_date === "2026-09-28" &&
      raw.url === url,
  );
  const again = parseGovinfoObservation({
    frDocNum: "C1-2026-18574",
    publicationDate: "2026-09-28",
    url,
    html: html("C1-2026-18574"),
    isCorrection: true,
  });
  assert(
    "parse: payload_hash is stable for the same page (ingest dedup)",
    again.payload_hash === c.payload_hash &&
      /^[0-9a-f]{64}$/.test(c.payload_hash),
  );
  assert(
    "parse: candidate satisfies the Observation contract",
    ObservationCandidateSchema.safeParse(c).success,
  );
  const ext = parseGovinfoObservation({
    frDocNum: "2026-19710",
    publicationDate: "2026-09-25",
    url: govinfoHtmlUrl("2026-09-25", "2026-19710"),
    html: html("2026-19710"),
    isCorrection: false,
  });
  assert(
    "parse: non-correction → raw_dates_text is the DATES section",
    ext.raw_dates_text?.endsWith("on or before November 2, 2026.") === true,
  );
  const fallback = parseGovinfoObservation({
    frDocNum: "2026-20328",
    publicationDate: "2026-10-05",
    url: govinfoHtmlUrl("2026-10-05", "2026-20328"),
    html: html("2026-20328"),
    isCorrection: true,
  });
  assert(
    "parse: a 'correction' not in the GPO correction format falls back to its DATES section",
    fallback.raw_dates_text ===
      "Submit comments on or before November 2, 2026.",
  );
  let threw = false;
  try {
    parseGovinfoObservation({
      frDocNum: "",
      publicationDate: "2026-10-05",
      url: "x",
      html: "<pre></pre>",
      isCorrection: false,
    });
  } catch {
    threw = true;
  }
  assert("parse: an empty doc number throws", threw);
}

// ── U+0000 (GPO page-break artifacts; Postgres text/JSONB cannot store them) ─────────────────────────
{
  const page = html("2026-13404");
  assert(
    "NUL fixture: the real page carries 18 NULs",
    (page.match(/\u0000/g) ?? []).length === 18,
  );
  assert(
    "stripNul: removes every U+0000 and nothing else",
    stripNul("a\u0000b\u0000\u0000c") === "abc" &&
      stripNul(page).length === page.length - 18,
  );
  const text = govinfoPlainText(page);
  assert(
    "plain text of a NUL page carries no NUL; line-anchored DATES still found",
    !text.includes("\u0000") &&
      extractDatesSection(text) ===
        "Submit comments on or before August 31, 2026.",
  );
  assert(
    "entities never decode to U+0000 or a lone surrogate (left verbatim)",
    govinfoPlainText("<pre>&#0;|&#x0;|&#xD800;|&#55296;</pre>") ===
      "&#0;|&#x0;|&#xD800;|&#55296;",
  );
  const c = parseGovinfoObservation({
    frDocNum: "2026-13404",
    publicationDate: "2026-07-02",
    url: govinfoHtmlUrl("2026-07-02", "2026-13404"),
    html: page,
    isCorrection: false,
  });
  const clean = parseGovinfoObservation({
    frDocNum: "2026-13404",
    publicationDate: "2026-07-02",
    url: govinfoHtmlUrl("2026-07-02", "2026-13404"),
    html: stripNul(page),
    isCorrection: false,
  });
  assert(
    "parse: raw.html is NUL-free and the hash equals the NUL-free page's (deterministic)",
    !(c.raw as { html: string }).html.includes("\u0000") &&
      c.payload_hash === clean.payload_hash &&
      c.raw_dates_text === clean.raw_dates_text,
  );
  const big = parseGovinfoObservation({
    frDocNum: "2026-14439",
    publicationDate: "2026-07-17",
    url: govinfoHtmlUrl("2026-07-17", "2026-14439"),
    html: html("2026-14439"),
    isCorrection: false,
  });
  assert(
    "parse (2026-14439, running-head NULs): DATES extracted, no NUL anywhere in the candidate",
    big.raw_dates_text?.startsWith(
      "This rule has been classified as a major rule",
    ) === true && !JSON.stringify(big).includes("\\u0000"),
  );
}

// ── URL + transport ─────────────────────────────────────────────────────────────────────────────────
assert(
  "url: the window govinfo_url pattern",
  govinfoHtmlUrl("2026-09-25", "2026-19710", "https://www.govinfo.gov") ===
    "https://www.govinfo.gov/content/pkg/FR-2026-09-25/html/2026-19710.htm",
);

const hits = new Map<string, number>();
const server: Server = createServer((req, res) => {
  const path = req.url ?? "";
  hits.set(path, (hits.get(path) ?? 0) + 1);
  if (path.endsWith("/2026-19710.htm")) {
    res.writeHead(200, { "content-type": "text/html" });
    res.end(html("2026-19710"));
  } else if (path === "/flaky") {
    if (hits.get(path)! < 2) {
      res.writeHead(503);
      res.end("busy");
    } else {
      res.writeHead(200);
      res.end("ok");
    }
  } else if (path === "/stall-text" || path === "/stall-json") {
    // Headers + a partial body, then silence: the round-1 #6 hang.
    res.writeHead(200, {
      "content-type": path.endsWith("json") ? "application/json" : "text/html",
    });
    res.write(path.endsWith("json") ? '{"partial":' : "<pre>partial");
  } else if (path === "/bad") {
    res.writeHead(400);
    res.end("bad");
  } else {
    res.writeHead(404);
    res.end("not found");
  }
});
await new Promise<void>((r) => server.listen(0, "127.0.0.1", () => r()));
const port = (server.address() as { port: number }).port;
const base = `http://127.0.0.1:${port}`;
try {
  assert(
    "fetchText: 404 with notFoundAsNull → null",
    (await fetchTextWithRetry(`${base}/missing`, { notFoundAsNull: true })) ===
      null,
  );
  let threw404 = false;
  try {
    await fetchTextWithRetry(`${base}/missing`);
  } catch {
    threw404 = true;
  }
  assert("fetchText: 404 WITHOUT notFoundAsNull throws", threw404);
  let threw400 = false;
  try {
    await fetchTextWithRetry(`${base}/bad`, { notFoundAsNull: true });
  } catch {
    threw400 = true;
  }
  assert(
    "fetchText: a non-404 4xx fails FAST (one request, no retry)",
    threw400 && hits.get("/bad") === 1,
    String(hits.get("/bad")),
  );
  assert(
    "fetchText: a 5xx is retried, then succeeds",
    (await fetchTextWithRetry(`${base}/flaky`, { retries: 2 })) === "ok" &&
      hits.get("/flaky") === 2,
  );
  process.env.GOVINFO_API_BASE = base;
  assert(
    "fetchGovinfoHtml: GOVINFO_API_BASE override + 200 → the page",
    (await fetchGovinfoHtml("2026-09-25", "2026-19710")) === html("2026-19710"),
  );
  assert(
    "fetchGovinfoHtml: 404 → null (not published yet)",
    (await fetchGovinfoHtml("2026-10-27", "2026-99999")) === null,
  );
} finally {
  // ── round-1 #6: the per-attempt timeout bounds the BODY read too, on every fetcher ──────────────
  for (const [label, run] of [
    [
      "text",
      () =>
        fetchTextWithRetry(`${base}/stall-text`, {
          timeoutMs: 150,
          retries: 1,
        }),
    ],
    [
      "json",
      () =>
        fetchJsonWithRetry(`${base}/stall-json`, {
          timeoutMs: 150,
          retries: 1,
        }),
    ],
  ] as const) {
    const t0 = performance.now();
    const outcome = await Promise.race([
      run().then(
        () => "completed",
        (e: Error) => `rejected: ${e.message}`,
      ),
      new Promise((r) => setTimeout(() => r("still waiting"), 5_000)),
    ]);
    const ms = performance.now() - t0;
    assert(
      `#6 ${label}: a stalled body is aborted by the timeout, retried once, then rejects (bounded)`,
      String(outcome).startsWith("rejected") &&
        hits.get(`/stall-${label}`) === 2 &&
        ms < 3_000,
      `${outcome} after ${Math.round(ms)}ms, ${hits.get(`/stall-${label}`)} request(s)`,
    );
  }
  {
    // A transport whose body IGNORES the abort signal: the read is still bounded (raced, then cancelled).
    let cancelled = false;
    const stalled = () =>
      new Response(
        new ReadableStream({
          start(c) {
            c.enqueue(new TextEncoder().encode('{"partial":'));
          },
          cancel() {
            cancelled = true;
          },
        }),
        { status: 200 },
      );
    const outcome = await Promise.race([
      postJsonWithRetry(
        "https://example.invalid/post",
        { a: 1 },
        { timeoutMs: 100, retries: 0, transport: async () => stalled() },
      ).then(
        () => "completed",
        (e: Error) => `rejected: ${e.message}`,
      ),
      new Promise((r) => setTimeout(() => r("still waiting"), 3_000)),
    ]);
    assert(
      "#6 post: a body that ignores the signal is still bounded and the response is cancelled",
      String(outcome).startsWith("rejected") && cancelled,
      `${outcome} cancelled=${cancelled}`,
    );
  }
  delete process.env.GOVINFO_API_BASE;
  server.closeAllConnections();
  await new Promise<void>((r) => server.close(() => r()));
}

console.log(out.join("\n"));
console.log(
  failures === 0
    ? `\nALL ${out.length} EXPECTATIONS MET`
    : `\n${failures} EXPECTATION(S) UNMET`,
);
process.exit(failures === 0 ? 0 : 1);
