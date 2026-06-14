# Week-1 Validation Spikes — DocketClock + Watershed Watch

**Purpose:** answer the go/no-go questions the architecture foundry flagged *before any pipeline
code is written*. Every spike below is a question whose answer changes the build. None of them
require building the product — they require measuring reality.

**Timebox:** 5 working days, 1–2 engineers. Each spike is ≤1 day. Output of the week is a
one-page **Go/No-Go memo** (template at the bottom) with real numbers, not vibes.

**Two tracks:**
- **Track D — DocketClock (substrate).** Run this always; it gates the substrate build.
- **Track W — Watershed Watch (vertical).** Run *in parallel only if* you are actively pursuing
  the Chesapeake design partner now. If the partner isn't ready, defer Track W — but W1/W2 are
  cheap and worth banking regardless.

**Cardinal rule (inherited from the architecture):** a measured "no" is a *success* this week.
The point is to kill a bad path on day 3 for $0, not on month 3 for a salary.

---

## Setup (Day 0, ~1 hour)

```bash
mkdir -p spikes/{data,out} && cd spikes
python3 -m venv .venv && source .venv/bin/activate
pip install duckdb requests python-dateutil pytz tenacity
# DuckDB CLI optional but handy:
#   brew install duckdb
```

Credentials needed:
- **Federal Register API** — none (keyless).
- **Regulations.gov v4** — get a key from <https://api.data.gov/signup/> (free, instant). `DEMO_KEY`
  works for a few calls but is rate-limited; use a real key. Export it: `export REGS_KEY=...`
- **AWS** — none required for Mirrulations S3 (public bucket, `--no-sign-request`), but having the
  AWS CLI configured helps. spicy-regs publishes Parquet you can read directly with DuckDB httpfs.

> Accuracy note: exact v4 filter param spellings (`filter[commentEndDate][ge]`,
> `filter[withinCommentPeriod]`, etc.) and the post-2025 comment-submission policy are themselves
> things this week verifies — confirm against the live OpenAPI at
> <https://open.gsa.gov/api/regulationsgov/> before trusting any snippet here verbatim.

---

# Track D — DocketClock substrate gates

## D1 — frDocNum join hit-rate  ⟵ MASTER GATE
**Question:** on the live corpus, what fraction of comment-open documents can be joined
FR ↔ Regulations.gov on `frDocNum` / `document_number`?

**Why it gates:** the entire reconciliation strategy assumes this join. If it's weak, the join key
must change *before* any schema is written.

**Method:**
1. Pull the current FR open-comment set (keyless):
   ```bash
   # proposed rules + notices with a comment date in the future; page through results.json
   curl -s 'https://www.federalregister.gov/api/v1/documents.json?per_page=1000&conditions[comment_date][gte]=2026-06-12&fields[]=document_number&fields[]=comments_close_on&fields[]=docket_ids&fields[]=regulations_dot_gov_info&fields[]=type&fields[]=action&fields[]=title' \
     > data/fr_open.json
   ```
2. Pull the current Regs.gov open-comment set (paged, respect 1,000/hr):
   ```bash
   # verify exact filter param against the live OpenAPI first
   curl -s -H "X-Api-Key: $REGS_KEY" \
     'https://api.regulations.gov/v4/documents?filter[commentEndDate][ge]=2026-06-12&page[size]=250&sort=commentEndDate' \
     > data/regs_open_p1.json   # repeat with page[number] / lastModifiedDate cursor
   ```
3. Load both into DuckDB and compute the join rate:
   ```sql
   -- hit rate = regs docs whose frDocNum matches an FR document_number
   SELECT
     count(*)                                            AS regs_open,
     count(*) FILTER (WHERE fr.document_number IS NOT NULL) AS joined,
     round(100.0 * count(*) FILTER (WHERE fr.document_number IS NOT NULL) / count(*), 1) AS hit_pct
   FROM regs_open r
   LEFT JOIN fr_open fr ON r.frDocNum = fr.document_number;
   ```
4. For the misses, measure the **fallback** join rate on `docket_id` overlap + `RIN`.

**Decision rule:**
- `hit_pct ≥ 60%` → **GO** with frDocNum as the primary reconciliation key.
- `hit_pct < 60%` → **PIVOT** to Regs.gov-primary with `docket_id`-array-overlap + RIN as the join;
  FR-only records carry `confidence=medium, conflict_reason="no_cross_source_join"`. (Foundry's
  named contingency — not a failure, a fork in the schema.)

**Artifact:** `out/D1_join_rate.md` with `regs_open / joined / hit_pct` + fallback rate.

---

## D2 — FR ↔ Regs.gov Eastern-date conflict rate
**Question:** across the live open set, how often do FR `comments_close_on` and Regs.gov
`commentEndDate` actually disagree **when both are normalized to America/New_York calendar date**?

**Why it gates:** this number decides whether `GET /conflicts` is the *marquee* feature ("conflict
intelligence") or a quiet field ("alerts"). It also validates the single load-bearing fix: that
naive UTC comparison produces false conflicts the Eastern-date rule must suppress.

**Method (DuckDB, over the D1 join):**
```sql
WITH j AS (
  SELECT r.frDocNum,
         fr.comments_close_on                         AS fr_date,          -- date-only
         r.commentEndDate                              AS regs_ts,          -- ISO-8601 + offset
         CAST(fr.comments_close_on AS DATE)            AS fr_eastern_date,
         CAST(timezone('America/New_York', r.commentEndDate::TIMESTAMPTZ) AS DATE) AS regs_eastern_date
  FROM regs_open r JOIN fr_open fr ON r.frDocNum = fr.document_number
)
SELECT
  count(*)                                                            AS joined,
  count(*) FILTER (WHERE fr_eastern_date <> regs_eastern_date)        AS true_conflicts,
  count(*) FILTER (WHERE CAST(fr_date AS DATE) <> CAST(regs_ts::TIMESTAMPTZ AS DATE)
                     AND fr_eastern_date = regs_eastern_date)         AS tz_false_positives,
  round(100.0 * count(*) FILTER (WHERE fr_eastern_date <> regs_eastern_date)/count(*),2) AS conflict_pct
FROM j;
```
Manually eyeball ~10 `true_conflicts` to confirm they're real (extension/correction), not parse bugs.

**Decision rule (no kill — this is a positioning input):**
- `conflict_pct ≳ 3–5%` → lead the product story with conflict intelligence; `/conflicts` is marquee.
- `conflict_pct < ~1%` → conflicts are a quiet correctness feature; lead with reliable alerts + audit log.
- **Sanity check:** `tz_false_positives > 0` *confirms* the Eastern-normalization rule is necessary
  (a UTC threshold would have mis-flagged them). If it's 0 on this sample, note it but keep the rule.

**Artifact:** `out/D2_conflict_rate.md` with the four counts + 10 hand-verified examples.

---

## D3 — Extension/correction/reopening volume & deny-list false positives
**Question:** how many genuine extension/correction/reopening/withdrawal notices appear per day,
and how noisy is the keyword detector (the BLM "land-withdrawal extension" trap)?

**Why it gates:** determines whether the human-review console is a *20-min/day* chore or a
*part-time staffing line* — i.e. the real operating cost and the LLM-classifier burden.

**Method (historical, over Mirrulations/spicy-regs):**
```sql
-- read spicy-regs / Mirrulations Parquet directly
INSTALL httpfs; LOAD httpfs;
CREATE VIEW docs AS SELECT * FROM read_parquet('s3://<spicy-regs-or-mirrulations-parquet-path>/*.parquet');

-- keyword candidates over a recent 90-day window
SELECT count(*) AS keyword_hits
FROM docs
WHERE lower(title) ~ '(extension|reopen|correction|withdraw)'
  AND postedDate >= DATE '2026-03-01';
```
Then **hand-label a 50-row sample** of the keyword hits: is each one *actually* moving a comment
deadline, or is it a false positive (land-withdrawal term extension, unrelated correction)?
Compute precision = true_deadline_movers / 50.

**Decision rule:**
- precision ≥ ~0.7 → deterministic deny-list + keywords is enough for v1; LLM adjudicates the rest.
- precision < ~0.5 → the LLM chain-classifier is load-bearing from day 1, not a fast-follow; budget
  accordingly and tighten the deny-list with the labeled examples.
- Project daily genuine-mover volume → if > ~15/day, the review console is a staffed line, flag it.

**Artifact:** `out/D3_extension_volume.md` — daily volume estimate + 50-row labeled sheet + precision.

---

## D4 — GSA rate-increase application  (ACTION, start Day 1)
**Question:** can we exceed the Regs.gov 1,000 req/hr limit legitimately, and on what timeline?

**Why it gates:** the architecture *rejects* multi-key pooling (ToS-revocation risk). The only
sanctioned path is a GSA rate increase / bulk-access request — and it has a lead time we don't control.

**Method:** not a measurement — a submitted request. File the rate-increase/bulk-data request via
api.data.gov / the Regulations.gov API contact on **Monday**. Record the ticket ID and any quoted
timeline. In parallel, prove the **differential-polling** budget works within 1,000/hr:
```
list withinCommentPeriod (cheap) → fetch document detail ONLY where lastModifiedDate advanced,
with a 6-hour Eastern→UTC cursor overlap + dedupe by documentId.
```
Measure: at current open-set size (~1,000 docs) and a 15-min poll, do we stay under budget? (Yes
on paper; confirm with a dry-run request counter.)

**Decision rule:** GO if differential polling fits the budget today (it should). The GSA request is
insurance for scale + historical backfill, not a v1 blocker. Note the timeline in the memo.

**Artifact:** `out/D4_rate_limit.md` — ticket ID, quoted timeline, measured req/hr at MVP volume.

---

## D5 — Buyer signal (customer discovery, not data)
**Question:** do law-firm KM / reg-affairs teams have a *named owner* for deadline verification,
measurable review-time pain, and any per-agency SLA expectation ("FDA change within X hours")?

**Method:** 3–5 short calls (the foundry flagged validation interviews as still-to-do). One page of
notes. Specifically probe: who owns it today, how they verify, would they pay for a feed vs a full
platform, and whether polling cadence (vs real-time SLA) is acceptable.

**Decision rule:** ≥3 of 5 confirm a real owner + review-time pain → demand signal is GO. SLA answers
decide whether near-close polling must tighten in the build.

**Artifact:** `out/D5_buyer_notes.md`.

---

# Track W — Watershed Watch vertical gates
*(Run only if pursuing the Chesapeake partner in parallel. W1/W2 are cheap — bank them anyway.)*

## W1 — Regulations.gov `POST /comments` availability  ⟵ KILL-SHOT
**Question:** is the v4 comment-submission endpoint open to **non-government** submitters today
(post the ~Aug-2025 change the foundry flagged)?

**Why it gates:** binary kill on the *automated* action loop. If closed, the "Act" step becomes
guided draft + copy-paste, not one-click filing — a materially different UX and receipt model.

**Method:**
1. Read the current v4 OpenAPI / submission docs at <https://open.gsa.gov/api/regulationsgov/>;
   confirm whether `POST /v4/comments` exists and what credential tier it needs.
2. Attempt a **sandbox/test** submission against an open docket with a test key (do **not** post a
   junk comment to a real live docket — use any documented test path, or stop at the auth-handshake
   step that proves access without persisting a comment).
3. Record the exact failure/success mode (200 vs 403 vs "gov-only").

**Decision rule:**
- Open to non-gov → automated filing in scope; receipt shows Regs.gov submission ID (first-class).
- Closed/gov-only → **fallback**: structured draft + copy-paste + guided link-out; receipt is
  "filed by member (self-reported)" — honest second-class receipt. Build the composer either way.

**Artifact:** `out/W1_comment_post.md` — endpoint status + exact response + chosen path.

---

## W2 — EPA EIS database machine-readability  ⟵ first anti-skin pillar
**Question:** does the EPA EIS database expose a documented machine-readable endpoint / bulk
download, or is ingestion a scraper?

**Why it gates:** EIS + its 45/30-day clock is the wedge's emotional core and the #1 thing
DocketClock can't give you. Its durability depends on how fragile ingestion is.

**Method:**
1. Inspect the EPA EIS search app (cdxapps.epa.gov EIS search) network traffic for a JSON/REST
   backend; check for a documented API, an EPA Envirofacts dataset, or a CSV/Excel bulk export.
2. If only HTML: assess scrape stability (stable DOM? pagination? rate limits?) and whether the
   Federal Register's EIS-notice stream can serve as a cross-check/spine for draft/final EIS dates.
3. Pull a 1-month sample of EIS records and confirm you can extract: title, state(s), draft/final
   status, comment open/close dates, and a link.

**Decision rule:**
- Documented endpoint/bulk → GO, EIS adapter is durable.
- Scraper only → still GO, but ship the adapter **behind an interface** with the FR EIS-notice
  stream as a fallback/cross-check, and budget scraper maintenance explicitly. Note fragility in memo.

**Artifact:** `out/W2_eis_source.md` — endpoint verdict + 1-month extracted sample.

---

## W3 — In-basin value density  ⟵ BUSINESS KILL-SHOT
**Question:** for one real Chesapeake HUC-8 subbasin, how many **novel** (previously-unknown-to-the-org)
in-basin Tier-1 windows appear per quarter, split EIS vs Regs.gov?

**Why it gates:** if it's 2–3/quarter, the paid-seat thesis is dead *regardless* of how clean the
architecture is. This is the number that decides whether the wedge is a product or a feature.

**Method:**
1. Resolve one HUC-8 (e.g. Choptank `02060005`) to its polygon + intersecting counties/water bodies
   via The National Map WBD ArcGIS REST:
   ```bash
   curl -s 'https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query?where=huc8=%2702060005%27&outFields=*&f=json'
   ```
2. Over the last 4 quarters of Mirrulations/spicy-regs + an EIS sample, count federal docket + EIS
   records whose text/CFR-parts/named-water-bodies plausibly fall in that basin (manual + keyword,
   this is an *estimate*, not the production classifier).
3. Split the count EIS vs Regs.gov-rulemaking and per-quarter.

**Decision rule:**
- ≳ a handful of novel in-basin Tier-1 windows/quarter, with EIS a meaningful share → GO.
- ~2–3/quarter or EIS share ≈ 0 → **STOP** — reconsider basin, scope, or whether WW is a product.
  Better to learn this now from a query than from a churned pilot.

**Artifact:** `out/W3_value_density.md` — per-quarter counts, EIS/Regs split, basin used.

---

## W4 — Geo-recall feasibility + labeled set
**Question:** can we hit usable recall deciding "is this docket in HUC-8 X?" from text, and will the
staffed partner contribute the institutional knowledge to build a labeled validation set?

**Why it gates:** false negatives = missed fights = destroyed trust with a passionate base. Recall is
the vertical's hardest net-new IP; the labeled set is a *contract term*, not an assumption.

**Method:**
1. With the partner, hand-label ~50 historical Chesapeake records as in-basin / not.
2. Run a quick deterministic pre-filter (agency EPA/USACE/NPS/BLM/NOAA + CFR parts 33/40/43 + named
   tributaries) + a Haiku pass over the 50; compute recall & precision.
3. Confirm in writing the partner will maintain/extend the labeled set.

**Decision rule:** recall ≥ ~0.85 on the sample (tune *toward* recall — false positives are mutable
noise, false negatives are catastrophic) → GO. Below that, geo-recall needs more design before pilot.

**Artifact:** `out/W4_geo_recall.md` — recall/precision on 50 + partner commitment note.

---

## W5 — USACE §404 ingestion path  (scoping, lower priority)
**Question:** how do USACE §404 individual-permit public notices arrive — Regs.gov/FR dockets, or
district public-notice postings? These are high-stakes Chesapeake permits with an unspecified pattern.

**Method:** check 2–3 USACE district sites (Baltimore, Norfolk) + Regs.gov for §404 public notices;
classify the ingestion pattern. Timebox hard at half a day — this informs roadmap, not v1 go/no-go.

**Decision rule:** if §404 notices are postings (not dockets), mark them a post-MVP Tier-2/3 source;
do not let them block the EIS-first MVP.

**Artifact:** `out/W5_usace_404.md`.

---

## W6 — Partner value confirmation
**Question:** does the staffed Chesapeake partner explicitly confirm that **federal + EIS** coverage
is valuable to them *even absent* local-permit coverage?

**Why it gates:** if their highest-pain fights are all local (floodplain rezoning), the wedge — which
covers federal/EIS well and local poorly — may be wrong for this partner. Confront the dossier's own
residual risk directly, in the onboarding conversation, using the Tier labels as the honesty device.

**Method:** one structured call. Walk them through what Tier-1 (federal/EIS) catches vs what Tier-3
(local, deferred) won't. Get an explicit yes/no on whether Tier-1 alone is worth a paid seat.

**Decision rule:** explicit yes → GO with this partner. Hedged/no → either find a partner whose pain
is federal/EIS-shaped, or treat the local gap as a must-build (which changes the whole roadmap).

**Artifact:** `out/W6_partner_fit.md`.

---

# Go / No-Go memo (fill at end of week)

> 📋 **Filled-in results:** [`week1-go-no-go-memo.md`](./week1-go-no-go-memo.md) — the code spikes
> (D1–D3, W1–W3) are run and populated; D4/D5 and W4–W6 remain open.

```
WEEK-1 VALIDATION RESULTS — <date>

TRACK D — DocketClock
 D1 frDocNum hit-rate ......... __%   → [GO frDocNum-primary | PIVOT docket_id/RIN]
 D2 Eastern-date conflict rate. __%   → story = [conflict-intelligence | reliable-alerts]
    tz false-positives seen? ... [yes/no]  (confirms Eastern rule needed)
 D3 extension movers/day ...... __    precision __  → review console = [20-min chore | staffed]
 D4 differential polling fits budget? [yes/no]  GSA ticket: ____  ETA: ____
 D5 buyer interviews: __/5 confirm owner+pain     SLA expectation: ____
 ──> SUBSTRATE DECISION: [BUILD | PIVOT JOIN | HOLD]

TRACK W — Watershed Watch  (run? [yes/no])
 W1 POST /comments open to non-gov? [yes/no]  → action loop = [auto-file | draft+copy-paste]
 W2 EPA EIS machine-readable? [api | bulk | scraper]  fragility: ____
 W3 novel in-basin windows/qtr: __  (EIS __ / Regs __) → [GO | STOP — feature not product]
 W4 geo-recall on 50: __  partner labels committed? [yes/no]
 W5 §404 pattern: [dockets | postings]  → [v1 | post-MVP]
 W6 partner: Tier-1 alone worth a paid seat? [yes/no]
 ──> WEDGE DECISION: [PILOT NOW | STANDALONE CONTINGENCY | DEFER]
```

**Most important single line:** D1 (does the join hold?) for the substrate, and W3 (is there enough
in-basin signal?) for the wedge. If either reads red, you've saved months — celebrate it.
