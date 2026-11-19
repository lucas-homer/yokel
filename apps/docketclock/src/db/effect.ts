/**
 * db/effect.ts — run a postgres.js query as an Effect (ADR 0018, slice 5).
 *
 * The postgres.js client stays as it is; this only lifts one query (or one transaction) into Effect with
 * a typed failure and a span. A rejected query becomes a `SqlError` carrying the driver's own error as
 * `cause`, so a Promise boundary can rethrow exactly what the query threw before. The span follows the
 * OpenTelemetry database conventions: named for what it does ("SELECT chain candidates"), with
 * `db.system.name` and `db.operation.name`. Query text and parameters never go on the span.
 */
import { Data, Effect } from "effect";

export class SqlError extends Data.TaggedError("SqlError")<{
  /** the span name of the query that failed, e.g. "SELECT chain candidates" */
  readonly query: string;
  /** the driver's error, rethrown as-is at a Promise boundary */
  readonly cause: unknown;
}> {
  override get message(): string {
    const inner =
      this.cause instanceof Error ? this.cause.message : String(this.cause);
    return `${this.query}: ${inner}`;
  }
}

/**
 * One query (or `sql.begin` transaction) as an Effect. `name` is the span name; its first word is the
 * operation ("SELECT", "UPSERT", "TRANSACTION", ...).
 */
export const dbQuery = <A>(
  name: string,
  run: () => PromiseLike<A>,
  /** attributes to put on the query's own span from its result, e.g. a row count */
  annotate?: (result: A) => Record<string, unknown>,
): Effect.Effect<A, SqlError> =>
  Effect.tryPromise({
    try: () => Promise.resolve(run()),
    catch: (cause) => new SqlError({ query: name, cause }),
  }).pipe(
    Effect.tap((result) =>
      annotate ? Effect.annotateCurrentSpan(annotate(result)) : Effect.void,
    ),
    Effect.withSpan(name, {
      kind: "client",
      attributes: {
        "db.system.name": "postgresql",
        "db.operation.name": name.split(" ")[0] ?? name,
      },
    }),
  );
