/**
 * Eastern-date normalization — the load-bearing primitive behind the FR<->Regs reconciliation. The
 * fatal flaw the product exists to avoid (docs/architecture/docketclock.md, FR-2018-27875) is flagging
 * a 1-UTC-day gap as a CONFLICT when both sources actually agree on the same America/New_York calendar
 * date. Conflict comparison MUST normalize both source dates to Eastern before comparing.
 *
 * Modeled on `formatEastern` in the Regs.gov adapter: `Intl.DateTimeFormat` with
 * `timeZone: "America/New_York"` resolves the correct EDT/EST offset for the given instant (DST-correct
 * — never a hardcoded -4/-5). This is a SHARED helper rather than an import from the source adapter so
 * the reconcile engine does not depend on the fetch layer.
 */

/** Format an instant as a "YYYY-MM-DD" calendar date in a given IANA time zone (DST-correct). */
function calendarDateIn(instant: Date, timeZone: string): string {
  if (Number.isNaN(instant.getTime()))
    throw new Error(`calendarDateIn: invalid instant for zone ${timeZone}`);
  // en-CA renders ISO-style YYYY-MM-DD; formatToParts avoids any locale separator surprises.
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(instant);
  const p = (t: string) => parts.find((x) => x.type === t)?.value ?? "";
  return `${p("year")}-${p("month")}-${p("day")}`;
}

/** The America/New_York calendar date ("YYYY-MM-DD") an instant falls on (DST-correct). */
export function easternCalendarDate(instant: Date): string {
  return calendarDateIn(instant, "America/New_York");
}

/** The UTC calendar date ("YYYY-MM-DD") an instant falls on. The "naive" date a UTC string slices to. */
export function utcCalendarDate(instant: Date): string {
  return calendarDateIn(instant, "UTC");
}

/**
 * Resolve an FR date-only comment-close ("YYYY-MM-DD", US-Eastern, NO timezone) into the UTC instant of
 * its operative deadline. CONVENTION: an FR comment period closes at 11:59:59 p.m. ET on that calendar
 * date (the legal end-of-day), so we bind the date to 23:59:59 America/New_York and return the
 * corresponding UTC instant. DST-correct: we discover the date's actual Eastern offset by probing how
 * Intl renders a noon-UTC instant on that date, then apply it to 23:59:59 local.
 *
 * Returns an ISO-8601 "…Z" UTC instant string. Throws on a malformed date string.
 */
export function frCloseDateToUtcInstant(dateOnly: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateOnly);
  if (!m)
    throw new Error(
      `frCloseDateToUtcInstant: expected "YYYY-MM-DD", got "${dateOnly}"`,
    );
  const [, y, mo, d] = m;
  // Probe the Eastern UTC-offset in effect on this calendar date (DST-correct). Noon UTC is safely
  // mid-day in Eastern for every offset, so it lands on the same calendar date we care about.
  const probe = new Date(`${y}-${mo}-${d}T12:00:00Z`);
  const offsetMinutes = easternOffsetMinutes(probe);
  // 23:59:59 local == (23:59:59 - offset) in UTC. offsetMinutes is negative for Eastern (UTC-4/-5), so
  // subtracting it adds hours, pushing the close into the next UTC day (the FR-2018-27875 artifact).
  const utcMillis =
    Date.UTC(Number(y), Number(mo) - 1, Number(d), 23, 59, 59) -
    offsetMinutes * 60_000;
  return new Date(utcMillis).toISOString();
}

/** The America/New_York UTC offset (in minutes; negative west of UTC) in effect at a given instant. */
function easternOffsetMinutes(instant: Date): number {
  // Read the wall-clock Eastern time of the instant, reconstruct it as if it were UTC, and diff.
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(instant);
  const p = (t: string) => Number(parts.find((x) => x.type === t)?.value);
  const hour = p("hour") === 24 ? 0 : p("hour");
  const asUtc = Date.UTC(
    p("year"),
    p("month") - 1,
    p("day"),
    hour,
    p("minute"),
    p("second"),
  );
  return Math.round((asUtc - instant.getTime()) / 60_000);
}
