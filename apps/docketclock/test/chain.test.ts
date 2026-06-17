/**
 * chain.test.ts — #31 Slice 3: the CROSS-WINDOW (chain) reconcile pass.
 *
 * Two halves:
 *   • PURE-ENGINE (chainReconcile) — no DB. Where conservative HIGH PRECISION is proven: the 5 linkage
 *     rules, the BLM 2023-27468 keyword false-positive (the headline precision test), multi-target, and
 *     determinism. These run first and need no Postgres.
 *   • DB-INTEGRATION (chainReconcileOnce + persistChainConflicts) — against a throwaway PG18. Persisted
 *     cross_window rows, either-side lookup, idempotent re-run (detected_at preserved), pair-aware
 *     retirement scoped to cross_window, and isolation from cross_source (the Slice 1 guarantee re-verified
 *     end-to-end). The DB half is SKIPPED when DATABASE_URL is unset (so the pure half still runs anywhere).
 *
 * Repo test style: hand-rolled assert, out[] accumulator, failures counter, process.exit.
 */
import { chainReconcile, type ChainCandidate } from "../src/reconcile/chain.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

const NOW = new Date("2026-06-01T00:00:00Z");

/** A baseline ORIGINAL window candidate (open, docket D, rin R, published Jan 1). */
function original(over: Partial<ChainCandidate> = {}): ChainCandidate {
  return {
    ocd_id: "ocd-participation-window/federal/2025-00001",
    fr_observation_id: "obs-A",
    fr_document_number: "2025-00001",
    docket_ids: ["EPA-HQ-OW-2025-0001"],
    rin: "2040-AA01",
    is_extension: false,
    is_correction: false,
    is_withdrawal: false,
    title: "Notice of Proposed Rulemaking; Request for Comments",
    publication_date: "2025-01-01",
    govinfo_url:
      "https://www.govinfo.gov/content/pkg/FR-2025-01-01/html/2025-00001.htm",
    dates_text: "Comments must be received on or before February 1, 2025.",
    status: "open",
    resolved_close_utc: "2025-02-02T04:59:59Z",
    ...over,
  };
}

/** A baseline AMENDMENT window candidate (same docket+rin, published Feb 1, is_extension). */
function amendment(over: Partial<ChainCandidate> = {}): ChainCandidate {
  return {
    ocd_id: "ocd-participation-window/federal/2025-00002",
    fr_observation_id: "obs-B",
    fr_document_number: "2025-00002",
    docket_ids: ["EPA-HQ-OW-2025-0001"],
    rin: "2040-AA01",
    is_extension: true,
    is_correction: false,
    is_withdrawal: false,
    title: "Extension of Comment Period",
    publication_date: "2025-02-01",
    govinfo_url:
      "https://www.govinfo.gov/content/pkg/FR-2025-02-01/html/2025-00002.htm",
    dates_text:
      "The comment period is extended. Comments now due March 1, 2025.",
    status: "open",
    resolved_close_utc: "2025-03-02T04:59:59Z",
    ...over,
  };
}

// ── PURE ENGINE ─────────────────────────────────────────────────────────────────────────────────────

// 1. Happy extension chain → ONE cross_window conflict, extension_chain_unresolved, ocd_id_b = B.
{
  const r = chainReconcile([original(), amendment()], NOW);
  assert(
    "1 happy extension: exactly one conflict",
    r.length === 1,
    String(r.length),
  );
  const c = r[0];
  assert(
    "1 happy extension: scope cross_window, A→B, flag extension_chain_unresolved",
    !!c &&
      c.conflict_scope === "cross_window" &&
      c.ocd_id === original().ocd_id &&
      c.ocd_id_b === amendment().ocd_id &&
      c.conflict_flags.includes("extension_chain_unresolved") &&
      c.conflict_flags.length === 1,
    c ? c.conflict_flags.join(",") : "no conflict",
  );
  assert(
    "1 happy extension: carries both govinfo anchors + FR/FR sources + detected_at",
    !!c &&
      c.govinfo_url === original().govinfo_url &&
      c.govinfo_url_b === amendment().govinfo_url &&
      c.source_a === "federal_register" &&
      c.source_b === "federal_register" &&
      c.detected_at === NOW.toISOString(),
  );
}

// 2. Withdrawal chain → withdrawn_vs_open.
{
  const b = amendment({
    is_extension: false,
    is_withdrawal: true,
    dates_text: "The notice is withdrawn.",
  });
  const r = chainReconcile([original(), b], NOW);
  assert(
    "2 withdrawal: one conflict, flag withdrawn_vs_open",
    r.length === 1 &&
      r[0]!.conflict_flags.includes("withdrawn_vs_open") &&
      r[0]!.conflict_flags.length === 1,
    r.map((c) => c.conflict_flags.join("|")).join("; "),
  );
}

// 3. Correction chain → correction_pending.
{
  const b = amendment({
    is_extension: false,
    is_correction: true,
    dates_text: "Correction: comments now due March 1, 2025.",
  });
  const r = chainReconcile([original(), b], NOW);
  assert(
    "3 correction: one conflict, flag correction_pending",
    r.length === 1 &&
      r[0]!.conflict_flags.includes("correction_pending") &&
      r[0]!.conflict_flags.length === 1,
    r.map((c) => c.conflict_flags.join("|")).join("; "),
  );
}

// 4. BLM 2023-27468 false-positive — THE HEADLINE PRECISION TEST, in the REAL data shape.
// Real BLM/USFS land-withdrawal notices carry `dates: None` (null dates_text) and put the withdrawal
// signal in the TITLE. The amendment shares docket+rin with the open original (so rules 1–4 pass) and
// trips is_withdrawal/is_extension; only rule 5 (the title-aware deny-list) keeps it from emitting a
// FALSE withdrawn_vs_open conflict to the live feed.
{
  const b = amendment({
    is_extension: false,
    is_withdrawal: true,
    // Real spike title (D3 2026-05648). dates_text is NULL — the real shape (`dates: None`).
    title:
      "Correction of Public Land Order No. 7963; National Defense Operating Area Withdrawal, Doña Ana, Luna, and Hidalgo Counties, NM",
    dates_text: null,
  });
  const r = chainReconcile([original(), b], NOW);
  assert(
    "4 BLM land-withdrawal FP (signal in TITLE, dates_text=null): NO conflict (title-aware deny-list)",
    r.length === 0,
    String(r.length),
  );
}

// 4b. Coverage for the 3 real D3 spike land-withdrawal title forms — each (signal in TITLE only,
// dates_text=null) must be suppressed (no FALSE conflict to the proof feed).
{
  const spikeTitles = [
    "Correction of Public Land Order No. 7963; National Defense Operating Area Withdrawal, Doña Ana, Luna, and Hidalgo Counties, NM",
    "Flathead National Forest; Montana; Mid-Swan Landscape Restoration & Wildland Urban Interface Fuels Project; Withdrawal",
    "White River National Forest; Eagle County, CO; Camp Hale Restoration and Enhancement Project EIS; Withdrawal",
  ];
  let allSuppressed = true;
  for (const title of spikeTitles) {
    const b = amendment({
      is_extension: false,
      is_withdrawal: true,
      title,
      dates_text: null,
    });
    const r = chainReconcile([original(), b], NOW);
    if (r.length !== 0) allSuppressed = false;
  }
  assert(
    "4b all 3 real spike land-withdrawal titles suppressed (no FALSE conflict)",
    allSuppressed,
  );
}

// 4c. dates_text-borne land-withdrawal variants (the adversary's list) — still suppressed when the
// vehicle phrase lands in DATES text instead of the title.
{
  const datesVariants = [
    "This order provides for a withdrawal of certain public land of approximately 4,000 acres.",
    "Notice of Proposed Withdrawal and opportunity for public meeting under the Public Lands Order process.",
  ];
  let allSuppressed = true;
  for (const dates_text of datesVariants) {
    const b = amendment({
      is_extension: false,
      is_withdrawal: true,
      title: "Notice 2025-00002",
      dates_text,
    });
    const r = chainReconcile([original(), b], NOW);
    if (r.length !== 0) allSuppressed = false;
  }
  assert(
    "4c dates_text-borne land-withdrawal variants suppressed",
    allSuppressed,
  );
}

// 4d. UNDER-LINKING GUARD (precision in the OTHER direction): a GENUINE comment-period extension —
// title "Extension of Comment Period", DATES text about extending the comment period, NO land-withdrawal
// vehicle vocabulary — sharing docket+rin with the open original MUST still emit its chain conflict.
// Guards against the deny-list eating real chains.
{
  const b = amendment({
    is_extension: true,
    is_withdrawal: false,
    title:
      "Accidental Release Prevention Requirements; Risk Management Programs; Extension of Comment Period",
    dates_text:
      "The comment period for the proposed rule is extended. Comments must now be received on or before March 1, 2025.",
  });
  const r = chainReconcile([original(), b], NOW);
  assert(
    "4d under-linking guard: genuine comment-period extension STILL emits extension_chain_unresolved",
    r.length === 1 &&
      r[0]!.conflict_flags.includes("extension_chain_unresolved"),
    r.length === 1 ? r[0]!.conflict_flags.join(",") : String(r.length),
  );
}

// 5. Shared docket but DIFFERENT rin and no explicit reference → NO conflict (rule 2 fails).
{
  const a = original({ rin: "2040-AA01" });
  const b = amendment({
    rin: "2040-ZZ99", // different rin
    dates_text:
      "The comment period is extended. Comments now due March 1, 2025.", // no doc-number reference
  });
  const r = chainReconcile([a, b], NOW);
  assert(
    "5 docket-only (diff rin, no reference): NO conflict (shared docket alone insufficient)",
    r.length === 0,
    String(r.length),
  );
}

// 6. Amendment BEFORE original (B.pub < A.pub) → NO conflict (rule 3).
{
  const a = original({ publication_date: "2025-03-01" });
  const b = amendment({ publication_date: "2025-02-01" }); // before A
  const r = chainReconcile([a, b], NOW);
  assert(
    "6 amendment-before-original: NO conflict (ordering rule)",
    r.length === 0,
    String(r.length),
  );
}

// 7. Dead docket: A closed long before B's publication → NO conflict (rule 4).
{
  const a = original({
    status: "closed",
    publication_date: "2023-01-01",
    resolved_close_utc: "2023-02-02T04:59:59Z", // closed ~2 years before B
  });
  const b = amendment({ publication_date: "2025-02-01" });
  const r = chainReconcile([a, b], NOW);
  assert(
    "7 dead docket: NO conflict (recency rule — A closed long before B)",
    r.length === 0,
    String(r.length),
  );
  // And the boundary: a closed original whose close is INSIDE the 60-day recency window DOES link.
  const aRecent = original({
    status: "closed",
    publication_date: "2025-01-01",
    resolved_close_utc: "2025-01-15T04:59:59Z", // ~17 days before B's 2025-02-01
  });
  const rRecent = chainReconcile([aRecent, amendment()], NOW);
  assert(
    "7b recently-closed docket (within recency window): conflict DOES link",
    rRecent.length === 1,
    String(rRecent.length),
  );
}

// 8. Explicit-reference path: rin differs/null but B.dates_text names A's fr_document_number → conflict.
{
  const a = original({ rin: null, fr_document_number: "2024-30637" });
  const b = amendment({
    rin: "2040-ZZ99", // different/non-matching rin
    // FR-style reference WITH the embedded-space line-wrap artifact (the EPA 2025-02910 pattern).
    dates_text:
      "The comment period for notice FRL 12023-01-OW (FR 2024- 30637) (89 FR 105041) is extended. Comments now due April 25, 2025.",
  });
  const r = chainReconcile([a, b], NOW);
  assert(
    "8 explicit reference (with FR space artifact): conflict emitted via rule 2 reference path",
    r.length === 1 && r[0]!.ocd_id === a.ocd_id,
    String(r.length),
  );
}

// 9. Multi-target: B amends two distinct originals A1, A2 (both satisfy 1–4) → two conflicts, both
// carry multi_target_notice.
{
  const a1 = original({
    ocd_id: "ocd-participation-window/federal/2024-30637",
    fr_observation_id: "obs-A1",
    fr_document_number: "2024-30637",
    rin: null,
    docket_ids: ["EPA-HQ-OW-2024-0454"],
    publication_date: "2024-12-26",
    status: "open",
  });
  const a2 = original({
    ocd_id: "ocd-participation-window/federal/2025-00734",
    fr_observation_id: "obs-A2",
    fr_document_number: "2025-00734",
    rin: null,
    docket_ids: ["EPA-HQ-OW-2025-0099"],
    publication_date: "2025-01-15",
    status: "open",
  });
  const b = amendment({
    ocd_id: "ocd-participation-window/federal/2025-02910",
    fr_observation_id: "obs-Bmt",
    fr_document_number: "2025-02910",
    rin: null,
    docket_ids: ["EPA-HQ-OW-2024-0454", "EPA-HQ-OW-2025-0099"],
    publication_date: "2025-02-20",
    dates_text:
      "The comment periods for notice (FR 2024-30637) and notice (FR 2025- 00734) are extended.",
  });
  const r = chainReconcile([a1, a2, b], NOW);
  assert(
    "9 multi-target: two conflicts, one per distinct original",
    r.length === 2,
    String(r.length),
  );
  assert(
    "9 multi-target: BOTH carry multi_target_notice + their type flag",
    r.length === 2 &&
      r.every(
        (c) =>
          c.conflict_flags.includes("multi_target_notice") &&
          c.conflict_flags.includes("extension_chain_unresolved"),
      ),
    r.map((c) => c.conflict_flags.join("|")).join("; "),
  );
  assert(
    "9 multi-target: targets are the two distinct originals",
    r.length === 2 && r[0]!.ocd_id === a1.ocd_id && r[1]!.ocd_id === a2.ocd_id,
    r.map((c) => c.ocd_id).join(", "),
  );
}

// 10. Determinism: same input → identical output ordering (shuffle the input; output is stable).
{
  const a1 = original({
    ocd_id: "ocd-participation-window/federal/2024-30637",
    fr_observation_id: "obs-A1",
    fr_document_number: "2024-30637",
    docket_ids: ["D1"],
    publication_date: "2024-12-26",
  });
  const a2 = original({
    ocd_id: "ocd-participation-window/federal/2025-00734",
    fr_observation_id: "obs-A2",
    fr_document_number: "2025-00734",
    docket_ids: ["D2"],
    publication_date: "2025-01-15",
  });
  const b = amendment({
    docket_ids: ["D1", "D2"],
    rin: "2040-AA01",
    publication_date: "2025-02-20",
  });
  // a1/a2 share the amendment's rin so both link.
  const set1 = chainReconcile([a1, a2, b], NOW);
  const set2 = chainReconcile([b, a2, a1], NOW); // shuffled
  assert(
    "10 determinism: shuffled input yields byte-identical output",
    JSON.stringify(set1) === JSON.stringify(set2),
    `${set1.length} vs ${set2.length}`,
  );
}

// ── DB INTEGRATION (skipped without DATABASE_URL) ────────────────────────────────────────────────────
if (process.env.DATABASE_URL) {
  await runDbTests();
}

async function runDbTests(): Promise<void> {
  const { createClient } = await import("../src/db/client.js");
  const { runMigrations } = await import("../src/db/migrate.js");
  const { parseFrObservation } =
    await import("../src/sources/federal-register.js");
  const { ingestObservation } = await import("../src/ingest/observe.js");
  const { reconcileOcdId, chainReconcileOnce } =
    await import("../src/reconcile/persist.js");
  const { listConflicts } = await import("../src/api/queries.js");

  const sql = createClient();
  try {
    await sql.unsafe(
      "drop schema if exists public cascade; create schema public;",
    );
    await runMigrations(sql);

    // Helper: ingest an FR doc + reconcile it into a materialized window. `over` lets each test tweak the
    // raw FR payload. `action` text drives the noticeFlags is_* parse (e.g. "extension of comment periods").
    async function seedWindow(opts: {
      docNum: string;
      docketIds: string[];
      rin: string | null;
      publicationDate: string;
      commentsCloseOn: string;
      action: string;
      title?: string;
      dates: string;
    }): Promise<string> {
      const raw: Record<string, unknown> = {
        document_number: opts.docNum,
        type: "Notice",
        action: opts.action,
        title: opts.title ?? `Notice ${opts.docNum}`,
        dates: opts.dates,
        comments_close_on: opts.commentsCloseOn,
        publication_date: opts.publicationDate,
        docket_ids: opts.docketIds,
        regulation_id_number: opts.rin,
      };
      const cand = parseFrObservation(raw);
      await ingestObservation(sql, cand);
      const ocdId = `ocd-participation-window/federal/${opts.docNum}`;
      await reconcileOcdId(sql, ocdId, NOW);
      return ocdId;
    }

    // 11 + 12 + 13 share an A/B pair. Original closes 2026-08-01 (future at NOW) → status open.
    const A = await seedWindow({
      docNum: "2026-11101",
      docketIds: ["EPA-HQ-CHAIN-0001"],
      rin: "2040-CHA1",
      publicationDate: "2026-05-01",
      commentsCloseOn: "2026-08-01",
      action: "Notice of public comment period.",
      dates: "Comments must be received on or before August 1, 2026.",
    });
    const B = await seedWindow({
      docNum: "2026-11102",
      docketIds: ["EPA-HQ-CHAIN-0001"],
      rin: "2040-CHA1",
      publicationDate: "2026-05-20",
      commentsCloseOn: "2026-09-15",
      action: "Notice; extension of comment period.",
      dates:
        "The comment period is extended. Comments now due September 15, 2026.",
    });

    // 11. Run once → cross_window row persisted; both sides find it.
    const run1 = await chainReconcileOnce(sql, NOW);
    assert(
      "11 DB: chainReconcileOnce links the A/B extension chain (linked=1)",
      run1.linked === 1 && run1.conflictsLive === 1,
      JSON.stringify(run1),
    );
    const [persisted] = await sql<
      {
        conflict_scope: string;
        ocd_id: string;
        ocd_id_b: string;
        govinfo_url_b: string | null;
      }[]
    >`
      select conflict_scope, ocd_id, ocd_id_b, govinfo_url_b
      from conflict_records where conflict_scope = 'cross_window'
    `;
    assert(
      "11 DB: persisted row is cross_window with A→B and a side-B govinfo anchor",
      !!persisted &&
        persisted.conflict_scope === "cross_window" &&
        persisted.ocd_id === A &&
        persisted.ocd_id_b === B &&
        persisted.govinfo_url_b ===
          "https://www.govinfo.gov/content/pkg/FR-2026-05-20/html/2026-11102.htm",
      persisted ? `${persisted.ocd_id}→${persisted.ocd_id_b}` : "none",
    );
    const bySideA = await listConflicts(sql, { ocdId: A });
    const bySideB = await listConflicts(sql, { ocdId: B });
    assert(
      "11 DB: either-side lookup — listConflicts finds it by side A AND by side B",
      bySideA.total === 1 &&
        bySideB.total === 1 &&
        bySideA.rows[0]!.ocd_id_b === B &&
        bySideB.rows[0]!.ocd_id === A,
      `A=${bySideA.total} B=${bySideB.total}`,
    );

    // 12. Idempotent re-run: no duplicate (4-col key); detected_at preserved.
    const [before12] = await sql<{ detected_at: Date }[]>`
      select detected_at from conflict_records where conflict_scope = 'cross_window'
    `;
    const run2 = await chainReconcileOnce(
      sql,
      new Date("2026-06-05T00:00:00Z"),
    );
    const countCw = async () =>
      (
        await sql<{ count: string }[]>`
          select count(*)::text as count from conflict_records where conflict_scope = 'cross_window'
        `
      )[0]!.count;
    assert(
      "12 DB: re-run does not duplicate (still one cross_window row)",
      (await countCw()) === "1" && run2.linked === 1,
      `${await countCw()} / linked=${run2.linked}`,
    );
    const [after12] = await sql<{ detected_at: Date }[]>`
      select detected_at from conflict_records where conflict_scope = 'cross_window'
    `;
    assert(
      "12 DB: detected_at preserved across re-detection",
      after12!.detected_at.getTime() === before12!.detected_at.getTime(),
    );

    // 13. cross_window retirement: re-ingest B as a LAND WITHDRAWAL (keyword false-positive) in the REAL
    // data shape — the withdrawal signal lives ONLY in the TITLE and `dates` is None (null dates_text).
    // noticeFlags reads title+type+action so is_withdrawal still trips; only the title-aware deny-list
    // keeps it from linking → re-run retires the live chain conflict (drops from the live feed).
    {
      const rawBfp: Record<string, unknown> = {
        document_number: "2026-11102",
        type: "Notice",
        action: "Notice of withdrawal.",
        title:
          "Flathead National Forest; Montana; Mid-Swan Landscape Restoration & Wildland Urban Interface Fuels Project; Withdrawal",
        dates: null,
        comments_close_on: "2026-09-15",
        publication_date: "2026-05-20",
        docket_ids: ["EPA-HQ-CHAIN-0001"],
        regulation_id_number: "2040-CHA1",
      };
      const candFp = parseFrObservation(rawBfp);
      // Force a later fetched_at so this becomes the LATEST FR observation for B. The original B was
      // ingested with a wall-clock fetched_at (~today), so we use a far-future stamp to win the
      // distinct-on(ocd_id) ... order by fetched_at desc selection in chainReconcileOnce.
      await ingestObservation(sql, {
        ...candFp,
        fetched_at: "2030-01-01T00:00:00Z",
      });
      await reconcileOcdId(sql, B, NOW);
      const run3 = await chainReconcileOnce(
        sql,
        new Date("2026-06-06T00:00:00Z"),
      );
      assert(
        "13 DB: after B becomes a land-withdrawal FP, chain links nothing + retires the stale row",
        run3.linked === 0 && run3.retired === 1,
        JSON.stringify(run3),
      );
      const live = await listConflicts(sql, { ocdId: A });
      assert(
        "13 DB: the retired cross_window conflict drops from the live feed",
        live.total === 0,
        String(live.total),
      );
      const [retiredRow] = await sql<{ resolved_at: Date | null }[]>`
        select resolved_at from conflict_records where conflict_scope = 'cross_window'
      `;
      assert(
        "13 DB: the row's resolved_at is stamped (retired, not deleted)",
        !!retiredRow && retiredRow.resolved_at !== null,
      );
    }

    // 14. Isolation from cross_source. Seed a cross_source conflict on the SAME ocd_id as a chain side A,
    // and a LIVE chain conflict — verify neither pass retires the other's row.
    {
      // Fresh chain pair so we have a LIVE cross_window row again (A2 open, B2 extension, same docket+rin).
      const A2 = await seedWindow({
        docNum: "2026-22201",
        docketIds: ["EPA-HQ-CHAIN-0002"],
        rin: "2040-CHA2",
        publicationDate: "2026-05-01",
        commentsCloseOn: "2026-08-01",
        action: "Notice of public comment period.",
        dates: "Comments due August 1, 2026.",
      });
      const B2 = await seedWindow({
        docNum: "2026-22202",
        docketIds: ["EPA-HQ-CHAIN-0002"],
        rin: "2040-CHA2",
        publicationDate: "2026-05-20",
        commentsCloseOn: "2026-09-15",
        action: "Notice; extension of comment period.",
        dates:
          "The comment period is extended. Comments now due September 15, 2026.",
      });
      await chainReconcileOnce(sql, new Date("2026-06-07T00:00:00Z"));
      assert(
        "14 setup: A2/B2 chain conflict is live",
        (await listConflicts(sql, { ocdId: B2 })).total === 1,
      );

      // Inject a LIVE cross_source conflict whose ocd_id is A2 (the same id the chain row uses as side A).
      await sql`
        insert into conflict_records (
          ocd_id, observation_a_id, observation_b_id, source_a, source_b,
          conflict_flags, govinfo_url, detected_at, resolved_at,
          conflict_scope, ocd_id_b, govinfo_url_b
        ) values (
          ${A2}, 'cs-a-1', 'cs-b-1', 'federal_register', 'regulations_gov',
          ${sql.json(["fr_regs_date_mismatch"])}, null, ${NOW.toISOString()}, null,
          'cross_source', '', null
        )
      `;

      // (a) A chain sweep must NOT retire the cross_source row.
      await chainReconcileOnce(sql, new Date("2026-06-08T00:00:00Z"));
      const csOpen = (
        await sql<{ count: string }[]>`
          select count(*)::text as count from conflict_records
          where ocd_id = ${A2} and conflict_scope = 'cross_source' and resolved_at is null
        `
      )[0]!.count;
      assert(
        "14a DB: a chain sweep does NOT retire the cross_source row on the same ocd_id",
        csOpen === "1",
        csOpen,
      );

      // (b) A per-ocd_id cross_source reconcile on A2 must NOT retire the LIVE chain (cross_window) row.
      // reconcileOcdId(A2) re-derives a non-conflicting window (FR-only, no Regs) → its resolve sweep
      // fires, scoped to cross_source — the chain row on A2 must survive.
      await reconcileOcdId(sql, A2, new Date("2026-06-09T00:00:00Z"));
      const cwOpen = (
        await sql<{ count: string }[]>`
          select count(*)::text as count from conflict_records
          where ocd_id = ${A2} and conflict_scope = 'cross_window' and resolved_at is null
        `
      )[0]!.count;
      assert(
        "14b DB: a per-ocd_id cross_source reconcile does NOT retire the chain (cross_window) row",
        cwOpen === "1",
        cwOpen,
      );
    }
  } finally {
    await sql.end();
  }
}

console.log("\n=== chain results ===");
console.log(out.join("\n"));
console.log(
  `\n${failures === 0 ? "ALL EXPECTATIONS MET" : `${failures} EXPECTATION(S) UNMET`}`,
);
process.exit(failures === 0 ? 0 : 1);
