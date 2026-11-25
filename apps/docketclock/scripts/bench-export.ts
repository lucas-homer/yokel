/**
 * bench-export — build the agent-vs-DocketClock answer key from the live database.
 *
 *   DATABASE_URL=… pnpm --filter @yokel/docketclock bench:export [--out <dir>] [--routine 80] [--memory 30] [--seed 1]
 *
 * Writes <out>/items.jsonl (default ~/.config/yokel/bench/key). The key is kept OUT of the repo on purpose:
 * a key committed to GitHub is a key a web-searching agent can find. Read-only: SELECTs and the review
 * CLI's in-memory blind derivation; nothing is written to the database.
 *
 * Strata (design doc, "The answer key"):
 *   pin / withdrawn / escalate  — honored human verdicts (review corpus)
 *   miss / routine              — post-close accuracy records (needs_check: graded by DocketClock's own check)
 *   point_in_time / moved       — memory questions from the Regulations.gov observation history
 * Multi-deadline notices are not here yet: their hand labels from the ADR 0017 measurement were not committed.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { createClient, type Sql } from "../src/db/client.js";
import { reviewCorpus, reviewShow } from "../src/review/core.js";
import { easternDate } from "../src/bench/grade.js";
import {
  deadlineQuestion,
  movedQuestion,
  pointInTimeQuestion,
} from "../src/bench/questions.js";
import type { Answer, Item } from "../src/bench/types.js";

const { values } = parseArgs({
  options: {
    out: { type: "string" },
    routine: { type: "string", default: "80" },
    memory: { type: "string", default: "30" },
    seed: { type: "string", default: "1" },
  },
});
const outDir = values.out ?? join(homedir(), ".config/yokel/bench/key");
const ROUTINE_N = Number(values.routine);
const MEMORY_N = Number(values.memory);
const SEED = Number(values.seed);

/** Deterministic shuffle (mulberry32) so the same seed picks the same sample. */
function shuffled<T>(xs: T[], seed: number): T[] {
  let a = seed >>> 0;
  const rnd = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const c = [...xs];
  for (let i = c.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [c[i], c[j]] = [c[j]!, c[i]!];
  }
  return c;
}

interface WindowRow {
  ocd_id: string;
  fr_document_number: string | null;
  regs_document_id: string | null;
  docket_id: unknown;
  resolved_close_utc: Date | null;
  confidence: string;
  status: string;
}

function refsOf(w: WindowRow): Item["refs"] {
  const d = w.docket_id;
  const docket = Array.isArray(d)
    ? ((d[0] as string | undefined) ?? null)
    : typeof d === "string"
      ? d
      : null;
  return {
    fr_document_number: w.fr_document_number,
    regs_document_id: w.regs_document_id,
    docket_id: docket,
  };
}

/** DocketClock's own answer, in the Answer shape, from a window projection (stored or blind). */
function dcAnswer(w: Record<string, unknown> | null): Answer | null {
  if (!w) return null;
  const status = String(w.status ?? "");
  const conf = String(w.confidence ?? "");
  const close = w.resolved_close_utc
    ? easternDate(w.resolved_close_utc as string | Date)
    : null;
  if (status === "withdrawn")
    return {
      answer_kind: "withdrawn",
      date: null,
      confidence: "high",
      round: null,
      sources: ["docketclock"],
    };
  if (conf === "conflicting" || !close)
    return {
      answer_kind: "unresolved",
      date: null,
      confidence: "low",
      round: null,
      sources: ["docketclock"],
    };
  const c: Answer["confidence"] =
    conf === "high" ? "high" : conf === "medium" ? "medium" : "low";
  return {
    answer_kind: "date",
    date: close,
    confidence: c,
    round: null,
    sources: ["docketclock"],
  };
}

async function windows(
  sql: Sql,
  ids: string[],
): Promise<Map<string, WindowRow>> {
  if (ids.length === 0) return new Map();
  const rows = await sql<WindowRow[]>`
    select ocd_id, fr_document_number, regs_document_id, docket_id, resolved_close_utc, confidence, status
    from participation_windows where ocd_id in ${sql(ids)}`;
  return new Map(rows.map((r) => [r.ocd_id, r]));
}

async function main() {
  const sql = createClient();
  const items: Item[] = [];
  const seen = new Set<string>();
  try {
    // ── human verdicts ──────────────────────────────────────────────────────────────────────────
    const corpus = await reviewCorpus(sql);
    const verdictItems = [
      ...corpus.pins.map((c) => ({ c, stratum: "pin" as const })),
      ...corpus.withdrawals.map((c) => ({ c, stratum: "withdrawn" as const })),
      ...corpus.escalations.map((c) => ({ c, stratum: "escalate" as const })),
    ];
    const vw = await windows(
      sql,
      verdictItems.map((v) => v.c.ocd_id),
    );
    for (const { c, stratum } of verdictItems) {
      const w = vw.get(c.ocd_id);
      if (!w) continue;
      const blind = await reviewShow(sql, c.ocd_id, { blind: true });
      const refs = refsOf(w);
      items.push({
        id: `${stratum}:${c.ocd_id}`,
        stratum,
        family: "lookup",
        ocd_id: c.ocd_id,
        question: deadlineQuestion(refs),
        expect:
          stratum === "pin"
            ? { kind: "date", date: c.expected_close! }
            : stratum === "withdrawn"
              ? { kind: "withdrawn" }
              : { kind: "unresolved" },
        refs,
        docketclock: {
          machine: dcAnswer(blind.window),
          published: dcAnswer(w as unknown as Record<string, unknown>),
        },
        needs_check: false,
        key_note: `${c.kind} by ${c.reviewer} (${c.operator}) on ${c.fetched_at.slice(0, 10)}`,
      });
      seen.add(c.ocd_id);
    }

    // ── post-close accuracy records ─────────────────────────────────────────────────────────────
    const misses = await sql<
      {
        ocd_id: string;
        published_close_utc: Date;
        confidence_at_close: string;
        basis: string;
        truth: Date | null;
      }[]
    >`
      select a.ocd_id, a.published_close_utc, a.confidence_at_close, a.basis,
             (select (o.raw->'data'->'attributes'->>'commentEndDate')::timestamptz
                from observations o
               where o.observation_id in (select jsonb_array_elements_text(a.contradicting_observation_ids))
                 and o.source = 'regulations_gov'
               order by o.fetched_at desc limit 1) as truth
      from accuracy_records a where a.was_correct = false`;
    const routine = await sql<
      {
        ocd_id: string;
        published_close_utc: Date;
        confidence_at_close: string;
      }[]
    >`
      select distinct on (ocd_id) ocd_id, published_close_utc, confidence_at_close
      from accuracy_records where was_correct = true order by ocd_id, verified_at_utc desc`;
    const pickedRoutine = shuffled(
      routine.filter((r) => !seen.has(r.ocd_id)),
      SEED,
    ).slice(0, ROUTINE_N);
    const aw = await windows(sql, [
      ...misses.map((m) => m.ocd_id),
      ...pickedRoutine.map((r) => r.ocd_id),
    ]);
    const asPublished = (close: Date, conf: string): Answer =>
      dcAnswer({
        resolved_close_utc: close,
        confidence: conf,
        status: "closed",
      })!;
    for (const m of misses) {
      const w = aw.get(m.ocd_id);
      if (!w || seen.has(m.ocd_id) || !m.truth) continue;
      const refs = refsOf(w);
      const published = asPublished(
        m.published_close_utc,
        m.confidence_at_close,
      );
      items.push({
        id: `miss:${m.ocd_id}`,
        stratum: "miss",
        family: "lookup",
        ocd_id: m.ocd_id,
        question: deadlineQuestion(refs),
        expect: { kind: "date", date: easternDate(m.truth) },
        refs,
        docketclock: { machine: published, published },
        needs_check: true,
        key_note: `accuracy miss (${m.basis}); key = latest contradicting Regulations.gov value`,
      });
      seen.add(m.ocd_id);
    }
    for (const r of pickedRoutine) {
      const w = aw.get(r.ocd_id);
      if (!w || seen.has(r.ocd_id)) continue;
      const refs = refsOf(w);
      const published = asPublished(
        r.published_close_utc,
        r.confidence_at_close,
      );
      items.push({
        id: `routine:${r.ocd_id}`,
        stratum: "routine",
        family: "lookup",
        ocd_id: r.ocd_id,
        question: deadlineQuestion(refs),
        expect: { kind: "date", date: easternDate(r.published_close_utc) },
        refs,
        docketclock: { machine: published, published },
        needs_check: true,
        key_note: "post-close accuracy record: correct",
      });
      seen.add(r.ocd_id);
    }

    // ── memory: Regulations.gov observation history ─────────────────────────────────────────────
    const hist = await sql<
      { ocd_id: string; fetched_at: Date; end_date: string | null }[]
    >`
      select ocd_id, fetched_at, raw->'data'->'attributes'->>'commentEndDate' as end_date
      from observations
      where source = 'regulations_gov' and ocd_id is not null
        and ocd_id in (select ocd_id from observations where source = 'regulations_gov' and ocd_id is not null
                       group by ocd_id having count(*) >= 3)
      order by ocd_id, fetched_at`;
    const byWindow = new Map<string, { at: Date; day: string | null }[]>();
    for (const h of hist) {
      const list = byWindow.get(h.ocd_id) ?? [];
      list.push({
        at: h.fetched_at,
        day: h.end_date ? easternDate(h.end_date) : null,
      });
      byWindow.set(h.ocd_id, list);
    }
    const movedIds: string[] = [];
    const stillIds: string[] = [];
    const pit = new Map<
      string,
      { asOf: string; day: string; earliest: string }
    >();
    for (const [id, obs] of byWindow) {
      const days = obs.filter((o) => o.day).map((o) => o.day!);
      if (days.length === 0) continue;
      if (new Set(days).size === 1) {
        stillIds.push(id);
        continue;
      }
      movedIds.push(id);
      // as-of date: the last calendar day (ET) the first value was shown, with the change on a LATER day
      const firstDay = days[0]!;
      const lastOld = [...obs].reverse().find((o) => o.day === firstDay)!;
      const firstNew = obs.find(
        (o) => o.day && o.day !== firstDay && o.at > lastOld.at,
      );
      const asOf = easternDate(lastOld.at);
      if (firstNew && easternDate(firstNew.at) > asOf)
        pit.set(id, { asOf, day: firstDay, earliest: firstDay });
    }
    const pickMoved = shuffled(
      movedIds.filter((id) => !seen.has(id)),
      SEED,
    ).slice(0, MEMORY_N);
    const pickStill = shuffled(
      stillIds.filter((id) => !seen.has(id)),
      SEED,
    ).slice(0, Math.floor(MEMORY_N / 2));
    const pickPit = shuffled(
      [...pit.keys()].filter((id) => !seen.has(id)),
      SEED + 1,
    ).slice(0, MEMORY_N);
    const mw = await windows(sql, [...pickMoved, ...pickStill, ...pickPit]);
    for (const id of pickMoved) {
      const w = mw.get(id);
      if (!w) continue;
      const earliest = byWindow.get(id)!.find((o) => o.day)!.day!;
      items.push({
        id: `moved:${id}`,
        stratum: "moved",
        family: "memory",
        ocd_id: id,
        question: movedQuestion(refsOf(w)),
        expect: { kind: "moved", moved: true, earlier_date: earliest },
        refs: refsOf(w),
        docketclock: { machine: null, published: null },
        needs_check: false,
        key_note: "observation log: portal commentEndDate took 2+ values",
      });
    }
    for (const id of pickStill) {
      const w = mw.get(id);
      if (!w) continue;
      items.push({
        id: `moved:${id}`,
        stratum: "moved",
        family: "memory",
        ocd_id: id,
        question: movedQuestion(refsOf(w)),
        expect: { kind: "moved", moved: false },
        refs: refsOf(w),
        docketclock: { machine: null, published: null },
        needs_check: true,
        key_note: `observation log: one portal commentEndDate across ${byWindow.get(id)!.length} reads since ${easternDate(byWindow.get(id)![0]!.at)}; a change before DocketClock's first read would not show`,
      });
    }
    for (const id of pickPit) {
      const w = mw.get(id);
      if (!w) continue;
      const p = pit.get(id)!;
      items.push({
        id: `point_in_time:${id}`,
        stratum: "point_in_time",
        family: "memory",
        ocd_id: id,
        question: pointInTimeQuestion(refsOf(w), p.asOf),
        expect: { kind: "date", date: p.day },
        refs: refsOf(w),
        docketclock: { machine: null, published: null },
        needs_check: false,
        key_note: `observation log: value shown through ${p.asOf}, changed on a later day`,
      });
    }

    mkdirSync(outDir, { recursive: true, mode: 0o700 });
    const path = join(outDir, "items.jsonl");
    writeFileSync(path, items.map((i) => JSON.stringify(i)).join("\n") + "\n", {
      mode: 0o600,
    });
    const counts: Record<string, number> = {};
    for (const i of items) counts[i.stratum] = (counts[i.stratum] ?? 0) + 1;
    console.log(`wrote ${items.length} items to ${path}`);
    console.log(counts);
  } finally {
    await sql.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
