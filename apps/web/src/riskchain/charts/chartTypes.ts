// Mirrors apps/api/app/schemas/charts.py — the chart-data endpoints under
// /cat/model-runs/{id}/charts/* and /cat/charts/*.

export interface ChartAxis {
  label: string;
  unit: string;
}

export interface XYPoint {
  x: number;
  y: number;
}

export interface FragilityChart {
  function_id: string;
  title: string;
  x_axis: ChartAxis;
  y_axis: ChartAxis;
  curve: XYPoint[];
  calibration_min: number;
  calibration_max: number;
  approval_status: string;
  marker?: XYPoint | null;
  marker_asset_id?: string | null;
  marker_extrapolated?: boolean | null;
  damage_state_probabilities?: Record<string, number> | null;
  note: string;
}

export interface HistogramBin {
  lower: number;
  upper: number;
  count: number;
}

export interface LossHistogram {
  run_id: string;
  title: string;
  x_axis: ChartAxis;
  y_axis: ChartAxis;
  bins: HistogramBin[];
  samples: number;
  p10_usd: number;
  p50_usd: number;
  p90_usd: number;
  basis: string;
}

export interface EPSeries {
  name: string;
  points: XYPoint[];
}

export interface EPCurveChart {
  run_id: string;
  title: string;
  x_axis: ChartAxis;
  y_axis: ChartAxis;
  series: EPSeries[];
  aal_usd: number;
  basis: string;
  caveat: string;
}

export interface WaterfallStep {
  label: string;
  amount_usd: number;
  running_total_usd: number;
}

export interface LossWaterfall {
  run_id: string;
  title: string;
  steps: WaterfallStep[];
  currency: string;
  basis: string;
}

export interface LossDriver {
  asset_id: string;
  name: string;
  ground_up_loss_usd: number;
  share: number;
  cumulative_share: number;
  depth_ft: number;
  damage_ratio: number;
  extrapolated: boolean;
}

export interface LossDrivers {
  run_id: string;
  title: string;
  total_ground_up_usd: number;
  drivers: LossDriver[];
  basis: string;
}

export interface WaterRisePoint {
  offset_ft: number;
  total_ground_up_usd: number;
  assets_wet: number;
}

export interface WaterRiseSweep {
  run_id: string;
  title: string;
  x_axis: ChartAxis;
  y_axis: ChartAxis;
  points: WaterRisePoint[];
  scenario_offset_ft: number;
  basis: string;
  caveat: string;
}
