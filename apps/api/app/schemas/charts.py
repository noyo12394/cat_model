"""Chart-ready series for the frontend (section 13 component registry).

Every response here is derived from an immutable model run or an approved
vulnerability function - the backend does the deriving so the frontend only
draws. Axes carry labels and units so no chart can be rendered unlabelled, and
each payload states its basis (which numbers it was derived from).
"""

from __future__ import annotations

from pydantic import BaseModel


class ChartAxis(BaseModel):
    label: str
    unit: str


class XYPoint(BaseModel):
    x: float
    y: float


class FragilityChart(BaseModel):
    function_id: str
    title: str
    x_axis: ChartAxis  # depth (ft)
    y_axis: ChartAxis  # mean damage ratio
    curve: list[XYPoint]
    calibration_min: float
    calibration_max: float
    approval_status: str
    # Optional marker: where a specific asset sits on this curve.
    marker: XYPoint | None = None
    marker_asset_id: str | None = None
    marker_extrapolated: bool | None = None
    damage_state_probabilities: dict[str, float] | None = None
    note: str


class HistogramBin(BaseModel):
    lower: float
    upper: float
    count: int


class LossHistogram(BaseModel):
    run_id: str
    title: str
    x_axis: ChartAxis  # loss (USD)
    y_axis: ChartAxis  # simulations
    bins: list[HistogramBin]
    samples: int
    p10_usd: float
    p50_usd: float
    p90_usd: float
    basis: str


class EPSeries(BaseModel):
    name: str  # "OEP" | "AEP"
    points: list[XYPoint]  # x = return period (yr), y = loss (USD)


class EPCurveChart(BaseModel):
    run_id: str
    title: str
    x_axis: ChartAxis
    y_axis: ChartAxis
    series: list[EPSeries]
    aal_usd: float
    basis: str
    caveat: str


class WaterfallStep(BaseModel):
    label: str
    amount_usd: float  # negative = reduction from the running total
    running_total_usd: float


class LossWaterfall(BaseModel):
    run_id: str
    title: str
    steps: list[WaterfallStep]
    currency: str
    basis: str


class LossDriver(BaseModel):
    asset_id: str
    name: str
    ground_up_loss_usd: float
    share: float
    cumulative_share: float
    depth_ft: float
    damage_ratio: float
    extrapolated: bool


class LossDrivers(BaseModel):
    run_id: str
    title: str
    total_ground_up_usd: float
    drivers: list[LossDriver]
    basis: str


class WaterRisePoint(BaseModel):
    offset_ft: float  # water level relative to the modelled scenario
    total_ground_up_usd: float
    assets_wet: int


class WaterRiseSweep(BaseModel):
    run_id: str
    title: str
    x_axis: ChartAxis  # water-level offset (ft)
    y_axis: ChartAxis  # total ground-up loss (USD)
    points: list[WaterRisePoint]
    scenario_offset_ft: float  # where the modelled scenario sits (0.0)
    basis: str
    caveat: str
