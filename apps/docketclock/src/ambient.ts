/**
 * ambient.ts — run Effect code inside Promise code without losing the trace (ADR 0018).
 *
 * Most passes are still Promise code (ADR 0018 moves them inward one at a time). A span opened by an Effect
 * inside that code would start a NEW trace, sent nowhere, because `Effect.runPromise` knows neither the
 * current span nor the exporter. The bridge: an Effect caller runs its Promise code `withAmbient`, which
 * stores its context (current span + tracer) in an AsyncLocalStorage; Effect code further down that async
 * chain runs `runAmbient`, which picks the context back up. So an HTTP request deep inside a Promise pass
 * still nests under `poll.pass.<name>` and is exported with the rest of its trace. Outside any ambient
 * context (tests, CLIs, the API) `runAmbient` is plain `Effect.runPromise`.
 *
 * Retire this module once the passes themselves are Effect code: then spans nest on their own.
 */
import { AsyncLocalStorage } from "node:async_hooks";
import { Context, Effect } from "effect";

const ambient = new AsyncLocalStorage<Context.Context<never>>();

/** Run Promise code so that `runAmbient` calls inside it inherit this Effect's span and tracer. */
export const withAmbient = <A>(run: () => Promise<A>) =>
  Effect.flatMap(Effect.context<never>(), (ctx) =>
    Effect.tryPromise({
      try: () => ambient.run(ctx, run),
      catch: (cause) => cause,
    }),
  );

/** `Effect.runPromise`, inside the nearest `withAmbient` caller's span and tracer when there is one. */
export const runAmbient = <A, E>(effect: Effect.Effect<A, E>): Promise<A> => {
  const ctx = ambient.getStore();
  return ctx ? Effect.runPromiseWith(ctx)(effect) : Effect.runPromise(effect);
};
