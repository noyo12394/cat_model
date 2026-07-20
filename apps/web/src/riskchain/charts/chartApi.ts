// Self-contained fetchers for the chart endpoints. Kept out of lib/api.ts so
// the charts module can evolve without touching the shared client.

import type {
  EPCurveChart,
  FragilityChart,
  LossDrivers,
  LossHistogram,
  LossWaterfall,
  WaterRiseSweep,
} from "./chartTypes";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`Chart request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export const chartApi = {
  fragilityForAsset: (runId: string, assetId: string) =>
    get<FragilityChart>(`/cat/model-runs/${runId}/charts/fragility?asset_id=${encodeURIComponent(assetId)}`),
  lossHistogram: (runId: string, bins = 24) =>
    get<LossHistogram>(`/cat/model-runs/${runId}/charts/loss-histogram?bins=${bins}`),
  epCurves: (runId: string, years = 5000) =>
    get<EPCurveChart>(`/cat/model-runs/${runId}/charts/ep?years=${years}`),
  waterfall: (runId: string) => get<LossWaterfall>(`/cat/model-runs/${runId}/charts/waterfall`),
  drivers: (runId: string, top = 8) => get<LossDrivers>(`/cat/model-runs/${runId}/charts/drivers?top=${top}`),
  waterRise: (runId: string) => get<WaterRiseSweep>(`/cat/model-runs/${runId}/charts/water-rise`),
};

export function money(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
  return `$${value.toFixed(0)}`;
}
