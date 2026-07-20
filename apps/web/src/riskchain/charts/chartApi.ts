// Self-contained fetchers for the chart endpoints. Kept out of lib/api.ts so
// the charts module can evolve without touching the shared client.
//
// Serverless-safe: the run's defining parameters (seed + financial terms +
// iterations) are sent with every request, so if the deployed function has
// cold-started and lost the stored run, the backend recomputes the identical
// deterministic run instead of 404-ing and locking the panel. Every request
// also has a hard timeout so a hung network call surfaces an error rather than
// an infinite spinner.

import type {
  EPCurveChart,
  FragilityChart,
  LossDrivers,
  LossHistogram,
  LossWaterfall,
  WaterRiseSweep,
} from "./chartTypes";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const TIMEOUT_MS = 12_000;

export interface RunChartParams {
  seed: number;
  deductible_usd: number;
  limit_usd: number | null;
  coinsurance: number;
  iterations: number;
}

function paramString(params?: RunChartParams): string {
  if (!params) return "";
  const q = new URLSearchParams({
    seed: String(params.seed),
    deductible_usd: String(params.deductible_usd),
    coinsurance: String(params.coinsurance),
    iterations: String(params.iterations),
  });
  if (params.limit_usd != null) q.set("limit_usd", String(params.limit_usd));
  return q.toString();
}

async function get<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${BASE_URL}${path}`, { signal: controller.signal });
    if (!res.ok) throw new Error(`Chart request failed (${res.status})`);
    return (await res.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Chart request timed out. Please try again.");
    }
    throw error instanceof Error ? error : new Error("Chart request failed.");
  } finally {
    clearTimeout(timer);
  }
}

/** Derive the query params that let the backend reproduce this exact run. */
export function runChartParams(run: {
  manifest: { random_seed: number; parameters: Record<string, string | number> };
  financial_terms: { deductible_usd: number; limit_usd?: number | null; coinsurance: number };
}): RunChartParams {
  const iterations = Number(run.manifest.parameters?.iterations ?? 2000);
  return {
    seed: run.manifest.random_seed,
    deductible_usd: run.financial_terms.deductible_usd,
    limit_usd: run.financial_terms.limit_usd ?? null,
    coinsurance: run.financial_terms.coinsurance,
    iterations: Number.isFinite(iterations) ? iterations : 2000,
  };
}

function withParams(path: string, params?: RunChartParams): string {
  const qs = paramString(params);
  return qs ? `${path}${path.includes("?") ? "&" : "?"}${qs}` : path;
}

export const chartApi = {
  fragilityForAsset: (runId: string, assetId: string, params?: RunChartParams) =>
    get<FragilityChart>(withParams(`/cat/model-runs/${runId}/charts/fragility?asset_id=${encodeURIComponent(assetId)}`, params)),
  lossHistogram: (runId: string, params?: RunChartParams, bins = 24) =>
    get<LossHistogram>(withParams(`/cat/model-runs/${runId}/charts/loss-histogram?bins=${bins}`, params)),
  epCurves: (runId: string, params?: RunChartParams, years = 5000) =>
    get<EPCurveChart>(withParams(`/cat/model-runs/${runId}/charts/ep?years=${years}`, params)),
  waterfall: (runId: string, params?: RunChartParams) =>
    get<LossWaterfall>(withParams(`/cat/model-runs/${runId}/charts/waterfall`, params)),
  drivers: (runId: string, params?: RunChartParams, top = 8) =>
    get<LossDrivers>(withParams(`/cat/model-runs/${runId}/charts/drivers?top=${top}`, params)),
  waterRise: (runId: string, params?: RunChartParams) =>
    get<WaterRiseSweep>(withParams(`/cat/model-runs/${runId}/charts/water-rise`, params)),
};

export function money(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
  return `$${value.toFixed(0)}`;
}
