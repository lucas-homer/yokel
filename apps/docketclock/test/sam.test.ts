/**
 * sam.test.ts — the SAM.gov pass (src/sources/sam-gov.ts, src/sam/sync.ts, migrations/0015_sam_gov.sql):
 *   - parsers: deadlines keep their stated offset and are never zone-guessed; wall-clock dates read Eastern;
 *   - the key never appears in an error message;
 *   - the daily request budget is never exceeded, and a 429 ends the day quietly;
 *   - FH backfill resumes at its offset across days, then runs one delta a day;
 *   - an unchanged re-fetch appends nothing; an amended notice appends a row and flags the deadline change;
 *   - a notice resolves its agency through federal_orgs; the log is append-only.
 *
 * Needs a THROWAWAY Postgres (the schema is dropped and re-migrated):
 *   DATABASE_URL=postgres://... pnpm --filter @yokel/docketclock test
 */
import { createClient } from "../src/db/client.js";
import { runMigrations } from "../src/db/migrate.js";
import {
  SAM_DAILY_REQUEST_CAP,
  SamRequestError,
  opportunitiesUrl,
  parseOffsetInstant,
  parseOpportunity,
  parseOrg,
  parseSamWallClock,
  redactKey,
} from "../src/sources/sam-gov.js";
import { samSyncOnce, takeRequest } from "../src/sam/sync.js";

let failures = 0;
const out: string[] = [];
function assert(name: string, cond: boolean, detail = "") {
  out.push(
    `  ${cond ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`,
  );
  if (!cond) failures++;
}

// ── pure ────────────────────────────────────────────────────────────────────────────────────────────
{
  const d = parseOffsetInstant("2026-12-15T14:00:00-05:00");
  assert(
    "deadline with offset parses",
    d?.toISOString() === "2026-12-15T19:00:00.000Z",
    String(d),
  );
  assert(
    "deadline without offset is NOT guessed",
    parseOffsetInstant("2026-12-15 14:00:00") === null,
  );
  assert(
    "date-only deadline is NOT guessed",
    parseOffsetInstant("2026-12-15") === null,
  );
  const p = parseSamWallClock("2026-07-04");
  assert(
    "summer wall date reads EDT",
    p?.toISOString() === "2026-07-04T04:00:00.000Z",
    String(p),
  );
  const w = parseSamWallClock("2026-01-10 09:30");
  assert(
    "winter wall time reads EST",
    w?.toISOString() === "2026-01-10T14:30:00.000Z",
    String(w),
  );

  const opp = parseOpportunity({
    noticeId: "abc123",
    title: "Widgets",
    type: "Solicitation",
    active: "Yes",
    postedDate: "2026-11-20",
    responseDeadLine: "2026-12-15T14:00:00-08:00",
    fullParentPathCode: "047.4732.47QTCA",
    archiveDate: "2027-01-01",
  });
  assert(
    "opportunity parses",
    opp?.noticeId === "abc123" && opp.active === true,
  );
  assert(
    "raw deadline is kept verbatim",
    opp?.responseDeadlineRaw === "2026-12-15T14:00:00-08:00",
  );
  assert("no noticeId → null", parseOpportunity({ title: "x" }) === null);

  const org = parseOrg({
    fhorgid: 100006568,
    fhorgname: "FEDERAL ACQUISITION SERVICE",
    fhorgtype: "Sub-Tier",
    status: "Active",
    agencycode: "4732",
    fhdeptindagencyorgid: 100006688,
    cgaclist: [{ cgac: "047" }],
    lastupdateddate: "2020-05-01 00:00",
  });
  assert(
    "org parses (numeric ids → strings, parent = department)",
    org?.fhorgid === "100006568" &&
      org.parentFhorgid === "100006688" &&
      org.cgac[0] === "047",
  );

  const url = opportunitiesUrl({
    apiKey: "SECRET",
    offset: 0,
    by: "deadline",
    from: "2026-11-25",
    to: "2027-11-24",
  });
  assert(
    "deadline query sends rdlfrom/rdlto and a posted window",
    /rdlfrom=11%2F25%2F2026/.test(url) && /postedFrom=/.test(url),
  );
  assert("redactKey strips the key", !redactKey(url).includes("SECRET"));
  const e = new SamRequestError(`GET ${url} -> 403 Forbidden`, 403);
  assert(
    "SamRequestError message never holds the key",
    !e.message.includes("SECRET"),
    e.message,
  );
}

// ── against Postgres ────────────────────────────────────────────────────────────────────────────────
const sql = createClient();

/** A fake SAM: N orgs and a set of notices, served by offset; counts calls; can be told to 429. */
function fakeSam(opts: { orgs: number; notices: Record<string, unknown>[] }) {
  const state = { calls: 0, throttle: false, notices: opts.notices };
  const orgs = Array.from({ length: opts.orgs }, (_, i) =>
    i === 0
      ? {
          fhorgid: 1,
          fhorgname: "GENERAL SERVICES ADMINISTRATION",
          fhorgtype: "Department/Ind. Agency",
          status: "ACTIVE",
          agencycode: "047",
          cgaclist: [{ cgac: "047" }],
        }
      : {
          fhorgid: 1 + i,
          fhorgname: `SUB ${i}`,
          fhorgtype: "Sub-Tier",
          status: "ACTIVE",
          agencycode: i === 1 ? "4732" : `S${i}`,
          fhdeptindagencyorgid: 1,
        },
  );
  const get = async (url: string) => {
    state.calls++;
    if (state.throttle)
      throw new SamRequestError(`GET ${url} -> 429 Too Many Requests`, 429);
    const u = new URL(url);
    const offset = Number(u.searchParams.get("offset"));
    const limit = Number(u.searchParams.get("limit"));
    if (u.pathname.includes("federalorganizations")) {
      // a delta (updateddatefrom) returns nothing new
      const list = u.searchParams.get("updateddatefrom") ? [] : orgs;
      return {
        totalrecords: list.length,
        orglist: list.slice(offset, offset + limit),
      };
    }
    return {
      totalRecords: state.notices.length,
      opportunitiesData: state.notices.slice(offset, offset + limit),
    };
  };
  return { get, state };
}

const notice = (id: string, rdl: string, posted = "2026-11-20") => ({
  noticeId: id,
  title: `Notice ${id}`,
  type: "Solicitation",
  active: "Yes",
  postedDate: posted,
  responseDeadLine: rdl,
  fullParentPathCode: "047.4732.47QTCA",
});

const count = async (q: string) => Number((await sql.unsafe(q))[0]!.n);

try {
  await sql.unsafe(
    "drop schema if exists public cascade; create schema public;",
  );
  const applied = await runMigrations(sql);
  assert(
    "migration 0015_sam_gov applies",
    applied.includes("0015_sam_gov.sql"),
  );

  // No key → skipped, nothing touched.
  {
    const s = await samSyncOnce(sql, new Date("2026-11-25T12:00:00Z"), {
      apiKey: null,
    });
    assert(
      "no key → skipped, zero requests",
      s.skippedNoKey && s.requests === 0,
    );
  }

  // 1,050 orgs = 11 FH pages. Day 1: the cap (9) is all FH.
  const sam = fakeSam({
    orgs: 1050,
    notices: [
      notice("n1", "2026-12-15T14:00:00-05:00"),
      notice("n2", "2026-12-20T17:00:00-07:00"),
    ],
  });
  const day1 = new Date("2026-11-25T12:00:00Z");
  {
    const s = await samSyncOnce(sql, day1, { apiKey: "k", get: sam.get });
    assert(
      "day 1 spends exactly the cap",
      s.requests === SAM_DAILY_REQUEST_CAP &&
        sam.state.calls === SAM_DAILY_REQUEST_CAP,
      JSON.stringify(s),
    );
    assert(
      "day 1 budget exhausted, FH not done",
      s.budgetExhausted && !s.fhBackfillDone,
    );
    assert(
      "900 orgs stored",
      (await count("select count(*) n from federal_orgs")) === 900,
    );
    const again = await samSyncOnce(sql, new Date("2026-11-25T12:15:00Z"), {
      apiKey: "k",
      get: sam.get,
    });
    assert(
      "a later cycle the same day makes no request",
      again.requests === 0 && sam.state.calls === SAM_DAILY_REQUEST_CAP,
    );
  }

  // Day 2: FH finishes (2 pages), then the opportunities backfill (1 page).
  const day2 = new Date("2026-11-26T12:00:00Z");
  {
    const s = await samSyncOnce(sql, day2, { apiKey: "k", get: sam.get });
    assert(
      "day 2 finishes FH backfill",
      s.fhBackfillDone &&
        (await count("select count(*) n from federal_orgs")) === 1050,
      JSON.stringify(s),
    );
    assert(
      "day 2 completes the opportunities backfill",
      s.opportunitiesBackfillDone && s.opportunitiesInserted === 2,
    );
    const [d] = await sql<
      {
        agency_fhorgid: string | null;
        response_deadline: Date;
        subject_id: string;
        source_url: string;
      }[]
    >`
      select agency_fhorgid, response_deadline, subject_id, source_url from contract_deadlines where notice_id = 'n1'`;
    assert(
      "notice resolves its sub-tier agency",
      d?.agency_fhorgid === "2",
      String(d?.agency_fhorgid),
    );
    assert(
      "deadline stored as the instant",
      d?.response_deadline.toISOString() === "2026-12-15T19:00:00.000Z",
    );
    assert(
      "subject id + public link",
      d?.subject_id === "ocd-contract-opportunity/federal/n1" &&
        d.source_url.includes("sam.gov/opp/n1"),
    );
    const parents = await count(
      "select count(*) n from federal_orgs where parent_fhorgid = '1'",
    );
    assert("sub-tiers point at their department", parents === 1049);
  }

  // Day 3: FH delta (1 request, nothing new) + opportunities delta. n1 is amended (new deadline + posted).
  const day3 = new Date("2026-11-27T12:00:00Z");
  {
    sam.state.notices = [
      notice("n1", "2027-01-05T14:00:00-05:00", "2026-11-27"),
      notice("n2", "2026-12-20T17:00:00-07:00"),
    ];
    const before = await count(
      "select count(*) n from sam_observations where source = 'sam_opportunities'",
    );
    const s = await samSyncOnce(sql, day3, { apiKey: "k", get: sam.get });
    const after = await count(
      "select count(*) n from sam_observations where source = 'sam_opportunities'",
    );
    assert(
      "day 3: two requests (one per delta)",
      s.requests === 2,
      JSON.stringify(s),
    );
    assert(
      "only the amended notice appends",
      after - before === 1 && s.opportunitiesInserted === 1,
    );
    assert("the deadline change is counted", s.deadlinesChanged === 1);
    const [d] = await sql<
      {
        response_deadline_raw: string;
        deadline_changed_at: Date | null;
        first_seen_at: Date;
        last_seen_at: Date;
      }[]
    >`
      select response_deadline_raw, deadline_changed_at, first_seen_at, last_seen_at from contract_deadlines where notice_id = 'n1'`;
    assert(
      "projection holds the amended deadline",
      d?.response_deadline_raw === "2027-01-05T14:00:00-05:00",
    );
    assert(
      "deadline_changed_at + last_seen_at move, first_seen stays",
      d?.deadline_changed_at?.getTime() === day3.getTime() &&
        d.last_seen_at.getTime() === day3.getTime() &&
        d.first_seen_at.getTime() === day2.getTime(),
    );
    const [n2] = await sql<
      { deadline_changed_at: Date | null }[]
    >`select deadline_changed_at from contract_deadlines where notice_id = 'n2'`;
    assert(
      "an unchanged notice has no deadline change",
      n2?.deadline_changed_at === null,
    );
    const vf = await sql<{ source_modified_at: Date }[]>`
      select source_modified_at from sam_observations where entity_id = 'n1' order by fetched_at`;
    assert(
      "each version keeps its valid-from (posted date)",
      vf.length === 2 &&
        vf[1]!.source_modified_at.toISOString() === "2026-11-27T05:00:00.000Z",
    );
    const [st] = await sql<
      { window_from: Date; window_to: Date | null }[]
    >`select window_from, window_to from sam_sync_state where source = 'sam_opportunities'`;
    assert(
      "next delta window starts at today's date",
      st?.window_from.toISOString().slice(0, 10) === "2026-11-27" &&
        st.window_to === null,
    );
    const later = await samSyncOnce(sql, new Date("2026-11-27T18:00:00Z"), {
      apiKey: "k",
      get: sam.get,
    });
    assert("a second delta the same day is skipped", later.requests === 0);
  }

  // A 429 ends the day: marks it exhausted, no failure, no further calls.
  {
    sam.state.throttle = true;
    const day5 = new Date("2026-11-29T12:00:00Z");
    const calls = sam.state.calls;
    const s = await samSyncOnce(sql, day5, { apiKey: "k", get: sam.get });
    assert(
      "429 → budget exhausted, one call, no throw",
      s.budgetExhausted && sam.state.calls === calls + 1,
    );
    assert(
      "the exhausted day refuses more requests",
      !(await takeRequest(sql, new Date("2026-11-29T20:00:00Z"))),
    );
  }

  // The log is append-only.
  {
    let threw = false;
    try {
      await sql`update sam_observations set raw = '{}'::jsonb`;
    } catch {
      threw = true;
    }
    assert("sam_observations rejects UPDATE", threw);
  }
} catch (err) {
  assert("unexpected error", false, String(err));
} finally {
  await sql.end({ timeout: 5 });
}

console.log("sam.test.ts");
console.log(out.join("\n"));
console.log(failures ? `${failures} FAILURE(S)` : "ALL PASS");
process.exit(failures ? 1 : 0);
