/**
 * telemetry.ts — the OpenTelemetry export layer for Effect programs (ADR 0018, slice 3).
 *
 * Effect 4 ships an OTLP exporter in its core package (`effect/observability/Otlp`): every `Effect.withSpan`
 * in a program provided with this layer becomes a span sent to `<endpoint>/v1/traces` (Effect's own log
 * and metric signals go to `/v1/logs` and `/v1/metrics` the same way). No OpenTelemetry SDK is involved.
 *
 * OFF BY DEFAULT: with OTEL_EXPORTER_OTLP_ENDPOINT unset this is `Layer.empty`, spans stay in-process and
 * nothing touches the network — so local runs, CI and tests are unchanged. The env names are the standard
 * OpenTelemetry ones, so a Grafana Cloud "OpenTelemetry" connection's values paste in as-is:
 *
 *   OTEL_EXPORTER_OTLP_ENDPOINT  e.g. https://otlp-gateway-prod-us-west-0.grafana.net/otlp
 *   OTEL_EXPORTER_OTLP_HEADERS   e.g. Authorization=Basic%20<base64 instance:token>   (a secret)
 *   OTEL_SERVICE_NAME            optional; defaults to the name the entrypoint passes
 *
 * FLUSH: the exporter batches. Its layer flushes when the program's scope closes (bounded by
 * `shutdownTimeout`), which is what lets a run-once container that exits after one cycle still deliver
 * that cycle's spans.
 */
import { Config, Effect, Layer, Redacted } from "effect";
import { FetchHttpClient } from "effect/http";
import { Otlp } from "effect/observability";

/** Parse the OTLP headers env format: comma-separated `key=value`, values URL-encoded (per the spec). */
export function parseOtlpHeaders(raw: string): Record<string, string> {
  const headers: Record<string, string> = {};
  for (const pair of raw.split(",")) {
    const eq = pair.indexOf("=");
    if (eq <= 0) continue;
    const key = pair.slice(0, eq).trim();
    const value = decodeURIComponent(pair.slice(eq + 1).trim());
    if (key) headers[key] = value;
  }
  return headers;
}

/**
 * The telemetry layer for one service. Reads its config when the layer is built; a missing endpoint yields
 * an empty layer (spans are created but not exported).
 */
export const telemetryLayer = (serviceName: string) =>
  Layer.unwrap(
    Effect.gen(function* () {
      const endpoint = (yield* Config.String(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
      ).pipe(Config.withDefault(""))).trim();
      if (!endpoint) return Layer.empty;
      const headers = yield* Config.Redacted("OTEL_EXPORTER_OTLP_HEADERS").pipe(
        Config.withDefault(Redacted.make("")),
      );
      const name = (yield* Config.String("OTEL_SERVICE_NAME").pipe(
        Config.withDefault(""),
      )).trim();
      return Otlp.layerJson({
        baseUrl: endpoint.replace(/\/+$/, ""),
        resource: { serviceName: name || serviceName },
        headers: parseOtlpHeaders(Redacted.value(headers)),
        shutdownTimeout: "10 seconds",
      }).pipe(Layer.provide(FetchHttpClient.layer));
    }),
  );
