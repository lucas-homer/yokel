/**
 * adjudicator-adversarial.test.ts — the ADVERSARY's regression lock over Slice 2's adjudication
 * subsystem. These are the differential / race / error-path checks the builder's happy-path suite does
 * NOT cover. Each is a guarantee the whole product leans on; a regression here is a deadline-liability
 * bug, so they stay green forever.
 *
 * Locks, in order:
 *   1. CONTENT-HASH FULL FIELD COVERAGE — flip EVERY field of BOTH the notice and chain inputs (one at a
 *      time, including a nullable→null transition) and assert the hash changes. A field whose change is
 *      NOT reflected in the hash is a cache-poisoning hole (two semantically-different ambiguities sharing
 *      one verdict). adjudicator_id is structurally absent from the input, so it cannot enter the hash.
 *   2. PER-ADJUDICATOR ISOLATION — cache key is (content_hash, adjudicator_id). A DIFFERENT adapter on the
 *      same input is a MISS: it IS consulted and gets its OWN row (it neither replays nor shadows the
 *      first). A re-consult with the SAME adapter is a HIT (per-adjudicator replay determinism).
 *   3. WRITE-ONCE IMMUTABILITY — a direct second INSERT with the same (content_hash, adjudicator_id) + a
 *      different verdict is a no-op; the stored verdict is unchanged and consult still replays the first.
 *   4. CONCURRENT-MISS INVARIANT — two consults of the SAME input via Promise.all with two different
 *      spies: exactly one row persists and BOTH callers observe the SAME (winning) verdict, even when
 *      both spies actually got called (a true concurrent miss). Run many rounds to exercise the window.
 *   5. ERROR-PATH HONESTY — a throwing adjudicate() PROPAGATES, NOTHING is persisted (no fabricated
 *      `uncertain` row), and a subsequent consult with a working adapter succeeds and persists cleanly.
 *   6. NO NUMERIC-CONFIDENCE LEAK — an adapter that volunteers a stray `confidence` gets it STRIPPED both
 *      from the value consultAdjudicator RETURNS and from the PERSISTED jsonb. consult.ts parses the verdict
 *      (AdjudicationVerdict.parse) BEFORE the write-once insert, so a fabricated numeric confidence can never
 *      be baked into the immutable audit row (confidence is NEVER LLM-scored). This lock asserts the
 *      invariant end-to-end — both the return value AND the stored row are clean.
 *
 * The pure-hashing locks run without postgres; the DB locks need DATABASE_URL (throwaway postgres:18).
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { AdjudicationVerdict, type AdjudicationInput } from "@yokel/contracts";
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import { adjudicationContentHash } from "../src/adjudicator/content-hash.js";
import { consultAdjudicator } from "../src/adjudicator/consult.js";
import type { Adjudicator } from "../src/adjudicator/port.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const RULEBOOK = "rulebox-2026-06-18";

function spy(
  id: string,
  verdict: AdjudicationVerdict,
): Adjudicator & { calls: number } {
  const s = {
    id,
    calls: 0,
    async adjudicate(): Promise<AdjudicationVerdict> {
      s.calls++;
      return verdict;
    },
  };
  return s;
}

// ── 1. CONTENT-HASH FULL FIELD COVERAGE (no DB) ───────────────────────────────────────────────────
{
  const notice: AdjudicationInput = {
    kind: "notice",
    rulebook_version: RULEBOOK,
    flag_key: "withdrawal",
    text: "Withdrawal of Land from Mineral Entry",
  };
  const nh = adjudicationContentHash(notice);
  const noticeFlips: Array<[string, AdjudicationInput]> = [
    ["notice.rulebook_version", { ...notice, rulebook_version: "rb-other" }],
    ["notice.flag_key", { ...notice, flag_key: "extension" }],
    ["notice.text", { ...notice, text: "Something else entirely" }],
  ];
  for (const [name, inp] of noticeFlips) {
    assert(
      `flipping ${name} changes the hash`,
      adjudicationContentHash(inp) !== nh,
    );
  }

  const chain: AdjudicationInput = {
    kind: "chain",
    rulebook_version: RULEBOOK,
    a_title: "Original Rule on Widget Safety",
    a_dates_text: "Comments due 2025-03-01",
    a_publication_date: "2025-01-15",
    b_title: "Extension of Comment Period",
    b_dates_text: "Comments now due 2025-04-01",
    b_publication_date: "2025-02-20",
    shared_docket: true,
    shared_rin: true,
    explicit_reference: false,
  };
  const ch = adjudicationContentHash(chain);
  const chainFlips: Array<[string, AdjudicationInput]> = [
    ["chain.rulebook_version", { ...chain, rulebook_version: "rb-other" }],
    ["chain.a_title", { ...chain, a_title: "X" }],
    ["chain.a_dates_text", { ...chain, a_dates_text: "Y" }],
    ["chain.a_dates_text->null", { ...chain, a_dates_text: null }],
    [
      "chain.a_publication_date",
      { ...chain, a_publication_date: "2099-01-01" },
    ],
    ["chain.b_title", { ...chain, b_title: "X" }],
    ["chain.b_dates_text", { ...chain, b_dates_text: "Y" }],
    [
      "chain.b_publication_date",
      { ...chain, b_publication_date: "2099-01-01" },
    ],
    ["chain.shared_docket", { ...chain, shared_docket: false }],
    ["chain.shared_rin", { ...chain, shared_rin: false }],
    ["chain.explicit_reference", { ...chain, explicit_reference: true }],
  ];
  for (const [name, inp] of chainFlips) {
    assert(
      `flipping ${name} changes the hash`,
      adjudicationContentHash(inp) !== ch,
    );
  }

  assert("notice and chain inputs hash distinctly", nh !== ch);
}

// ── DB-backed adversarial locks ───────────────────────────────────────────────────────────────────
if (!process.env.DATABASE_URL) {
  out.push("  SKIP  DB-backed adversarial locks (DATABASE_URL not set)");
} else {
  const sql = createClient();
  try {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    // 2. PER-ADJUDICATOR ISOLATION — a DIFFERENT adapter on the SAME input is a cache MISS (the key is now
    // (content_hash, adjudicator_id)): it IS consulted and gets its OWN row; it neither replays nor is
    // shadowed by the first adapter's verdict. A RE-consult with the SAME adapter is a HIT (no re-call).
    {
      const input: AdjudicationInput = {
        kind: "notice",
        rulebook_version: RULEBOOK,
        flag_key: "withdrawal",
        text: "swap-test",
      };
      const a = spy("spy:A", { classification: "affirm", rationale: "A" });
      const b = spy("spy:B", { classification: "reject", rationale: "B" });
      const ra = await consultAdjudicator(sql, a, input);
      const rb = await consultAdjudicator(sql, b, input);
      assert(
        "different adapter on same input is a MISS → consulted, gets its OWN reject verdict (not shadowed)",
        rb.cached === false && rb.verdict.classification === "reject",
        `cached=${rb.cached} ${rb.verdict.classification}`,
      );
      assert(
        "the second adapter IS called (per-adjudicator key, no shadowing)",
        b.calls === 1,
        String(b.calls),
      );
      assert(
        "first adapter's own verdict is intact (affirm) and was called exactly once",
        ra.verdict.classification === "affirm" && a.calls === 1,
        `${ra.verdict.classification} calls=${a.calls}`,
      );
      // A re-consult with the SAME adapter (a) is a HIT — replay determinism PER adjudicator.
      const raAgain = await consultAdjudicator(sql, a, input);
      assert(
        "same adapter re-consult is a HIT (replay determinism per adjudicator, no re-call)",
        raAgain.cached === true &&
          raAgain.verdict.classification === "affirm" &&
          a.calls === 1,
        `cached=${raAgain.cached} calls=${a.calls}`,
      );
    }

    // 3. WRITE-ONCE IMMUTABILITY (direct second insert is a no-op).
    {
      const input: AdjudicationInput = {
        kind: "notice",
        rulebook_version: RULEBOOK,
        flag_key: "extension",
        text: "write-once",
      };
      const a = spy("spy:first", {
        classification: "affirm",
        rationale: "first",
      });
      await consultAdjudicator(sql, a, input);
      const h = adjudicationContentHash(input);
      // Write-once is PER (content_hash, adjudicator_id) now — collide on the SAME key (spy:first@<rb>) to
      // prove the second insert of that key is a no-op (a different adjudicator_id would be a NEW row, not a
      // collision — that's tested separately as the coexist case).
      const firstId = "spy:first@" + RULEBOOK;
      await sql`
        insert into adjudications (content_hash, input, verdict, adjudicator_id)
        values (${h}, ${sql.json(input as never)}::jsonb,
                ${sql.json({ classification: "reject", rationale: "intruder" } as never)}::jsonb,
                ${firstId})
        on conflict (content_hash, adjudicator_id) do nothing
      `;
      const rows = await sql<{ verdict: AdjudicationVerdict }[]>`
        select verdict from adjudications where content_hash = ${h} and adjudicator_id = ${firstId}
      `;
      assert(
        "write-once: a second INSERT of the same (hash, adjudicator_id) does NOT mutate the stored verdict",
        rows.length === 1 && rows[0]!.verdict.classification === "affirm",
        rows[0]?.verdict.classification,
      );
      const replay = await consultAdjudicator(sql, a, input);
      assert(
        "consult with the SAME adjudicator still replays the FIRST verdict after a collision",
        replay.cached === true && replay.verdict.classification === "affirm",
        replay.verdict.classification,
      );
    }

    // 4. CONCURRENT-MISS INVARIANT — both callers observe the SAME winning verdict. The race window is
    // write-once PER (content_hash, adjudicator_id), so to exercise it both concurrent consults must use the
    // SAME adjudicator id (same key) but return DIFFERENT verdicts; the first writer wins and both readers
    // observe that one verdict. (Distinct ids would be distinct keys — that's the coexist case, not a race.)
    {
      let trueConcurrentMisses = 0;
      let mismatches = 0;
      let duplicateRows = 0;
      const ROUNDS = 20;
      for (let i = 0; i < ROUNDS; i++) {
        const input: AdjudicationInput = {
          kind: "notice",
          rulebook_version: RULEBOOK,
          flag_key: "correction",
          text: `race-${i}`,
        };
        const a = spy("spy:race", { classification: "affirm", rationale: "A" });
        const b = spy("spy:race", { classification: "reject", rationale: "B" });
        const [ra, rb] = await Promise.all([
          consultAdjudicator(sql, a, input),
          consultAdjudicator(sql, b, input),
        ]);
        if (a.calls > 0 && b.calls > 0) trueConcurrentMisses++;
        if (ra.verdict.classification !== rb.verdict.classification)
          mismatches++;
        const n = await sql<{ n: number }[]>`
          select count(*)::int n from adjudications
          where content_hash = ${adjudicationContentHash(input)}
        `;
        if (n[0]!.n !== 1) duplicateRows++;
      }
      assert(
        "concurrent miss: BOTH callers ALWAYS observe the same verdict (no split-brain)",
        mismatches === 0,
        `${mismatches}/${ROUNDS} mismatched`,
      );
      assert(
        "concurrent miss: exactly one row persists per input (write-once under race)",
        duplicateRows === 0,
        `${duplicateRows}/${ROUNDS} had != 1 rows`,
      );
      assert(
        "concurrent miss: the race window was actually exercised (both spies called)",
        trueConcurrentMisses > 0,
        `${trueConcurrentMisses}/${ROUNDS} true concurrent misses`,
      );
    }

    // 5. ERROR-PATH HONESTY — throw propagates, nothing persisted, retry succeeds.
    {
      const input: AdjudicationInput = {
        kind: "notice",
        rulebook_version: RULEBOOK,
        flag_key: "reopening",
        text: "error-path",
      };
      const h = adjudicationContentHash(input);
      const thrower: Adjudicator = {
        id: "spy:throw",
        async adjudicate(): Promise<AdjudicationVerdict> {
          throw new Error("synthetic adjudicate failure");
        },
      };
      let threw = false;
      try {
        await consultAdjudicator(sql, thrower, input);
      } catch {
        threw = true;
      }
      assert("a throwing adjudicate() PROPAGATES out of consult", threw);
      const after = await sql<{ n: number }[]>`
        select count(*)::int n from adjudications where content_hash = ${h}
      `;
      assert(
        "error path persists NOTHING (no fabricated uncertain row)",
        after[0]!.n === 0,
        String(after[0]!.n),
      );
      const ok = spy("spy:recover", {
        classification: "reject",
        rationale: "recovered",
      });
      const r = await consultAdjudicator(sql, ok, input);
      assert(
        "a subsequent consult with a working adapter succeeds and persists",
        r.cached === false && r.verdict.classification === "reject",
        r.verdict.classification,
      );
      const final = await sql<{ n: number }[]>`
        select count(*)::int n from adjudications where content_hash = ${h}
      `;
      assert(
        "exactly one row persists after recovery",
        final[0]!.n === 1,
        String(final[0]!.n),
      );
    }

    // 6. NO NUMERIC-CONFIDENCE LEAK.
    {
      // The schema itself strips a stray confidence.
      const stripped = AdjudicationVerdict.parse({
        classification: "affirm",
        rationale: "r",
        confidence: 0.97,
      } as never);
      assert(
        "AdjudicationVerdict.parse strips a stray numeric confidence",
        !("confidence" in (stripped as Record<string, unknown>)),
      );

      const input: AdjudicationInput = {
        kind: "notice",
        rulebook_version: RULEBOOK,
        flag_key: "withdrawal",
        text: "confidence-leak",
      };
      const leaky: Adjudicator = {
        id: "spy:leaky",
        async adjudicate(): Promise<AdjudicationVerdict> {
          return {
            classification: "affirm",
            rationale: "yes",
            confidence: 0.97,
          } as never;
        },
      };
      const r = await consultAdjudicator(sql, leaky, input);
      assert(
        "consult RETURN value has NO numeric confidence (laundered on select-back)",
        !("confidence" in (r.verdict as Record<string, unknown>)),
        JSON.stringify(r.verdict),
      );
      const row = await sql<{ verdict: Record<string, unknown> }[]>`
        select verdict from adjudications
        where content_hash = ${adjudicationContentHash(input)}
      `;
      // REGRESSION LOCK: consult.ts parses the verdict (AdjudicationVerdict.parse) BEFORE the write-once
      // insert, so a stray numeric confidence is stripped before it can reach the immutable jsonb row.
      // This pins that invariant — if a future edit reverts to inserting the raw adapter verdict, the
      // persisted row would carry `confidence` and this assertion goes red.
      assert(
        "PERSISTED jsonb verdict has NO numeric confidence (parse-before-insert)",
        !("confidence" in row[0]!.verdict),
        JSON.stringify(row[0]!.verdict),
      );
    }
  } finally {
    await sql.end();
  }
}

console.log("\n=== adjudicator-adversarial results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
