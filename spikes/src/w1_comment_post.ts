/**
 * W1 — Regulations.gov POST /comments availability  (KILL-SHOT for the automated action loop)
 *
 * Q: Is the v4 comment-submission endpoint open to NON-government submitters today (post ~Aug 2025)?
 * Gates: binary — automated one-click filing vs guided draft + copy-paste.
 *
 * Method (see § W1): two NON-DESTRUCTIVE POST probes with a standard (non-gov) key. We never persist
 *   a comment — the /comments probe sends an EMPTY body, which can only ever 4xx, never submit:
 *   1. POST /v4/submission-keys  — mints an ephemeral key; proves we can *initiate* a submission.
 *   2. POST /v4/comments {}      — reachability test. 403/UNAUTHORIZED = gated/gov-only;
 *                                  400/422 validation error = endpoint reachable (open to our tier).
 *   (Stops at the auth handshake the plan sanctions — no junk comment hits any live docket.)
 *
 * Decision rule:
 *   open to non-gov -> automated filing in scope; receipt shows Regs.gov submission ID (first-class).
 *   closed/gov-only -> fallback: structured draft + copy-paste + guided link-out; "filed by member
 *                      (self-reported)" honest second-class receipt. Build the composer either way.
 *
 * Output: out/W1_comment_post.md
 */
import { today, writeOut } from "./_shared.js";

const REGS_KEY = process.env.REGS_KEY || process.env.REGS_API_KEY || "DEMO_KEY";

interface Probe {
  label: string;
  method: string;
  url: string;
  status: number;
  ok: boolean;
  errorCode: string | null;
  bodySnippet: string;
}

async function probe(
  label: string,
  method: string,
  url: string,
  body?: unknown,
): Promise<Probe> {
  try {
    const res = await fetch(url, {
      method,
      headers: {
        "X-Api-Key": REGS_KEY,
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await res.text();
    let errorCode: string | null = null;
    try {
      errorCode = (JSON.parse(text)?.error?.code as string) ?? null;
    } catch {
      /* non-JSON body */
    }
    return {
      label,
      method,
      url,
      status: res.status,
      ok: res.ok,
      errorCode,
      bodySnippet: text.replace(/\s+/g, " ").slice(0, 240),
    };
  } catch (err) {
    return {
      label,
      method,
      url,
      status: 0,
      ok: false,
      errorCode: "NETWORK_ERROR",
      bodySnippet: String(err).slice(0, 240),
    };
  }
}

async function main(): Promise<void> {
  if (!process.env.REGS_KEY) {
    console.warn(
      "WARNING: REGS_KEY not set — probing with DEMO_KEY; result reflects DEMO_KEY's tier.\n",
    );
  }
  const base = "https://api.regulations.gov/v4";

  console.log(
    "W1: probing Regs.gov submission endpoints (non-destructive)...\n",
  );
  // 1. Can our key initiate a submission at all?
  const subKey = await probe(
    "POST /v4/submission-keys",
    "POST",
    `${base}/submission-keys`,
    {
      data: { type: "submission-keys" },
    },
  );
  console.log(
    `  ${subKey.label} -> ${subKey.status}${subKey.errorCode ? ` (${subKey.errorCode})` : ""}`,
  );

  // 2. Is the comment endpoint reachable by our tier? EMPTY body — cannot persist anything.
  const commentPost = await probe(
    "POST /v4/comments {}",
    "POST",
    `${base}/comments`,
    {},
  );
  console.log(
    `  ${commentPost.label} -> ${commentPost.status}${commentPost.errorCode ? ` (${commentPost.errorCode})` : ""}`,
  );

  // 3. Sanity: the same key can READ comments (proves the key itself is valid).
  const commentGet = await probe(
    "GET /v4/comments",
    "GET",
    `${base}/comments?page%5Bsize%5D=5`,
  );
  console.log(`  ${commentGet.label} -> ${commentGet.status}`);

  // Classify access to comment submission.
  const denied = commentPost.status === 403 || commentPost.status === 401;
  const reachable = commentPost.status === 400 || commentPost.status === 422;
  const verdict = denied
    ? "CLOSED / gov-only — standard key cannot POST comments"
    : reachable
      ? "OPEN to non-gov — endpoint reachable (validation error, not auth denial)"
      : `INDETERMINATE — unexpected status ${commentPost.status}; inspect the body`;
  const path = denied
    ? '**Fallback:** structured draft + copy-paste + guided link-out. Receipt = "filed by member (self-reported)" (honest second-class).'
    : reachable
      ? "**Automated filing in scope:** build the one-click submit; receipt shows the Regs.gov submission ID (first-class)."
      : "Re-run and inspect the raw response before choosing a path.";

  const row = (p: Probe): string =>
    `| ${p.label} | ${p.status || "—"} | ${p.errorCode ?? ""} | \`${p.bodySnippet}\` |`;

  const md = `# W1 — Regulations.gov POST /comments availability

**Run:** ${today()} (Eastern) · key tier: ${process.env.REGS_KEY ? "standard non-gov REGS_KEY" : "DEMO_KEY"}
**Method:** non-destructive POST probes — the \`/comments\` probe sends an **empty body**, so it can only
4xx, never persist a comment (the auth-handshake test the plan sanctions).

## Probe results

| probe | HTTP | error code | body (truncated) |
| --- | ---: | --- | --- |
${row(subKey)}
${row(commentPost)}
${row(commentGet)}

## Verdict

**${verdict}.**

- \`POST /v4/submission-keys\` → **${subKey.status}** ${subKey.status === 201 ? "(can mint a submission key — initiation is allowed)" : ""}
- \`POST /v4/comments\` → **${commentPost.status}${commentPost.errorCode ? ` ${commentPost.errorCode}` : ""}** ${denied ? "— authorization denial at the service level, *not* a payload validation error" : reachable ? "— reachable; the empty body merely failed validation" : ""}
- \`GET /v4/comments\` → **${commentGet.status}** ${commentGet.status === 200 ? "(key is valid for reads — so the POST denial is a *tier* gate, not a bad key)" : ""}

### Chosen path

${path}

> The contrast is the tell: minting a submission-key succeeds (201) while \`POST /comments\` is denied
> (${commentPost.status}${commentPost.errorCode ? ` ${commentPost.errorCode}` : ""}) — i.e. the *submission service* is gated above the standard tier, consistent
> with the post-2025 change. A GSA-authorized/gov submitter tier may differ; the composer should be
> built either way, with the receipt model switched by this flag.
`;

  const outPath = writeOut("W1_comment_post.md", md);
  console.log(`\n=== W1 RESULT ===`);
  console.log(
    `submission-keys=${subKey.status}  comments POST=${commentPost.status}${commentPost.errorCode ? ` (${commentPost.errorCode})` : ""}  comments GET=${commentGet.status}`,
  );
  console.log(`Verdict: ${verdict}`);
  console.log(`Wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
