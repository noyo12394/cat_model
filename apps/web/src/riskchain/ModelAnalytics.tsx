"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3, Database, LineChart, ShieldCheck } from "lucide-react";
import type { CatModelRunResult, ProbabilisticResult, VulnerabilityFunction } from "@/lib/types";
import { RunChartsPanel } from "./charts/RunChartsPanel";

type Tab = "overview" | "curves" | "financials" | "audit";

const CURVE_COLORS = ["#1a73e8", "#7e57c2", "#f4511e", "#00a884"];
const DAMAGE_COLORS: Record<string, string> = {
  none: "#8aa0ae",
  slight: "#57a7ff",
  moderate: "#f9ab00",
  extensive: "#f4511e",
  complete: "#d93025",
};

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1_000_000 ? 0 : 2,
  }).format(value);
}

function AnimatedMoney({ value }: { value: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      const frame = requestAnimationFrame(() => setShown(value));
      return () => cancelAnimationFrame(frame);
    }
    const start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / 560);
      setShown(value * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return <span className="number-value">{money(shown)}</span>;
}

function CurveChart({ curves, run }: { curves: VulnerabilityFunction[]; run: CatModelRunResult }) {
  const width = 560;
  const height = 250;
  const plot = { left: 48, right: 18, top: 18, bottom: 38 };
  const allPoints = curves.flatMap((curve) => curve.curve);
  const xMin = Math.min(-2, ...allPoints.map((point) => point.intensity));
  const xMax = Math.max(12, ...allPoints.map((point) => point.intensity));
  const yMax = Math.max(0.7, ...allPoints.map((point) => point.mean_damage_ratio));
  const x = (value: number) => plot.left + ((value - xMin) / (xMax - xMin)) * (width - plot.left - plot.right);
  const y = (value: number) => plot.top + (1 - value / yMax) * (height - plot.top - plot.bottom);
  const usedIds = new Set(run.asset_damage.map((item) => item.vulnerability_function_id));

  return (
    <div className="analytics-chart-wrap">
      <svg className="analytics-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Flood depth-damage vulnerability curves">
        <defs><linearGradient id="curveArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--modelled)" stopOpacity=".24" /><stop offset="100%" stopColor="var(--modelled)" stopOpacity="0" /></linearGradient></defs>
        {[0, 0.2, 0.4, 0.6].map((tick) => <g key={tick}><line x1={plot.left} x2={width - plot.right} y1={y(tick)} y2={y(tick)} className="chart-grid" /><text x={plot.left - 8} y={y(tick) + 4} textAnchor="end">{Math.round(tick * 100)}%</text></g>)}
        {[-2, 0, 2, 4, 6, 8, 10, 12].map((tick) => <g key={tick}><line x1={x(tick)} x2={x(tick)} y1={plot.top} y2={height - plot.bottom} className="chart-grid vertical" /><text x={x(tick)} y={height - 14} textAnchor="middle">{tick}</text></g>)}
        <text x={width / 2} y={height - 2} textAnchor="middle" className="axis-title">Flood depth above first floor (ft)</text>
        <text transform={`translate(13 ${height / 2}) rotate(-90)`} textAnchor="middle" className="axis-title">Mean damage ratio</text>
        {curves.map((curve, index) => {
          const points = curve.curve.map((point) => `${x(point.intensity)},${y(point.mean_damage_ratio)}`).join(" ");
          const first = curve.curve[0]; const last = curve.curve[curve.curve.length - 1];
          return <g key={curve.function_id}><polygon points={`${x(first.intensity)},${height - plot.bottom} ${points} ${x(last.intensity)},${height - plot.bottom}`} fill="url(#curveArea)" opacity={usedIds.has(curve.function_id) ? .82 : .3} /><polyline points={points} fill="none" stroke={CURVE_COLORS[index % CURVE_COLORS.length]} strokeWidth={usedIds.has(curve.function_id) ? 4 : 2} strokeDasharray={index % 3 === 1 ? "7 4" : index % 3 === 2 ? "2 3" : undefined} opacity={usedIds.has(curve.function_id) ? 1 : 0.7} /></g>;
        })}
        {run.asset_damage.map((asset) => {
          const curveIndex = Math.max(0, curves.findIndex((curve) => curve.function_id === asset.vulnerability_function_id));
          return <circle key={asset.asset_id} cx={x(asset.intensity)} cy={y(asset.mean_damage_ratio)} r="4" fill={CURVE_COLORS[curveIndex % CURVE_COLORS.length]} stroke="white" strokeWidth="1.5"><title>{asset.asset_id}: {asset.intensity.toFixed(1)} ft, {(asset.mean_damage_ratio * 100).toFixed(1)}% mean damage</title></circle>;
        })}
      </svg>
      <div className="chart-legend">{curves.map((curve, index) => <span key={curve.function_id}><i style={{ background: CURVE_COLORS[index % CURVE_COLORS.length] }} />{curve.asset_class}{usedIds.has(curve.function_id) && <b>used</b>}</span>)}</div>
    </div>
  );
}

function EPChart({ probabilistic }: { probabilistic: ProbabilisticResult }) {
  const width = 560;
  const height = 230;
  const plot = { left: 62, right: 18, top: 18, bottom: 42 };
  const points = [...probabilistic.oep_curve, ...probabilistic.aep_curve];
  const maxLoss = Math.max(1, ...points.map((point) => point.loss_usd));
  const minRp = Math.min(...points.map((point) => point.return_period_years));
  const maxRp = Math.max(...points.map((point) => point.return_period_years));
  const x = (value: number) => plot.left + ((Math.log10(value) - Math.log10(minRp)) / (Math.log10(maxRp) - Math.log10(minRp))) * (width - plot.left - plot.right);
  const y = (value: number) => plot.top + (1 - value / maxLoss) * (height - plot.top - plot.bottom);
  const line = (values: typeof points) => values.map((point) => `${x(point.return_period_years)},${y(point.loss_usd)}`).join(" ");

  return <div className="analytics-chart-wrap">
    <svg className="analytics-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Occurrence and aggregate exceedance probability curves">
      <defs><linearGradient id="aepArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--modelled)" stopOpacity=".28" /><stop offset="100%" stopColor="var(--modelled)" stopOpacity="0" /></linearGradient></defs>
      {[0, 0.25, 0.5, 0.75, 1].map((tick) => <g key={tick}><line x1={plot.left} x2={width - plot.right} y1={y(maxLoss * tick)} y2={y(maxLoss * tick)} className="chart-grid" /><text x={plot.left - 8} y={y(maxLoss * tick) + 4} textAnchor="end">{money(maxLoss * tick).replace(".00", "")}</text></g>)}
      {[10, 25, 50, 100, 250, 500, 1000].filter((tick) => tick >= minRp && tick <= maxRp).map((tick) => <g key={tick}><line x1={x(tick)} x2={x(tick)} y1={plot.top} y2={height - plot.bottom} className="chart-grid vertical" /><text x={x(tick)} y={height - 17} textAnchor="middle">{tick}y</text></g>)}
      <polygon points={`${x(probabilistic.aep_curve[0].return_period_years)},${height - plot.bottom} ${line(probabilistic.aep_curve)} ${x(probabilistic.aep_curve[probabilistic.aep_curve.length - 1].return_period_years)},${height - plot.bottom}`} fill="url(#aepArea)" />
      <polyline points={line(probabilistic.aep_curve)} fill="none" stroke="var(--modelled)" strokeWidth="4" />
      <polyline points={line(probabilistic.oep_curve)} fill="none" stroke="var(--modelled)" strokeWidth="3" strokeDasharray="7 4" />
      <text x={width / 2} y={height - 2} textAnchor="middle" className="axis-title">Return period (log scale)</text>
    </svg>
    <div className="chart-legend"><span><i style={{ background: "var(--modelled)" }} />AEP · solid · annual aggregate</span><span><i className="dashed-key" style={{ background: "var(--modelled)" }} />OEP · dashed · largest event</span></div>
  </div>;
}

export function ModelAnalytics({ run, curves, probabilistic }: { run: CatModelRunResult; curves: VulnerabilityFunction[]; probabilistic: ProbabilisticResult | null }) {
  const [tab, setTab] = useState<Tab>("overview");
  const stateAverage = useMemo(() => {
    const states = ["none", "slight", "moderate", "extensive", "complete"];
    const count = run.asset_damage.length || 1;
    return states.map((state) => ({ state, value: run.asset_damage.reduce((sum, asset) => sum + (asset.damage_state_probabilities[state] ?? 0), 0) / count }));
  }, [run.asset_damage]);
  const losses = useMemo(() => ({
    building: run.asset_damage.reduce((sum, asset) => sum + asset.building_loss_usd, 0),
    contents: run.asset_damage.reduce((sum, asset) => sum + asset.contents_loss_usd, 0),
    interruption: run.asset_damage.reduce((sum, asset) => sum + asset.business_interruption_loss_usd, 0),
  }), [run.asset_damage]);
  const totalLoss = Math.max(1, losses.building + losses.contents + losses.interruption);

  return <div className="model-analytics">
    <nav className="analytics-tabs" role="tablist" aria-label="Model result views">
      {(["overview", "curves", "financials", "audit"] as Tab[]).map((item) => <button id={`result-tab-${item}`} key={item} role="tab" aria-selected={tab === item} aria-controls={`result-panel-${item}`} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}
    </nav>

    {tab === "overview" && <section id="result-panel-overview" role="tabpanel" aria-labelledby="result-tab-overview" className="analytics-section">
      <div className="result-hero"><span>Modelled ground-up loss range</span><strong><AnimatedMoney value={run.ground_up_distribution.range_low_usd} />–<AnimatedMoney value={run.ground_up_distribution.range_high_usd} /></strong><small>Median {money(run.ground_up_distribution.p50_usd)} · {run.ground_up_distribution.samples.toLocaleString()} Monte Carlo samples</small></div>
      <div className="result-grid"><div><span>P10</span><strong>{money(run.ground_up_distribution.p10_usd)}</strong></div><div><span>P50</span><strong>{money(run.ground_up_distribution.p50_usd)}</strong></div><div><span>P90</span><strong>{money(run.ground_up_distribution.p90_usd)}</strong></div><div><span>Assets</span><strong>{run.asset_count}</strong></div></div>
      <section className="confidence-card"><ShieldCheck size={20} /><div><strong>{run.confidence.band} confidence</strong><p>Largest uncertainty: {run.confidence.largest_uncertainty}</p></div></section>
      <div className="loss-composition"><div className="loss-donut" style={{ background: `conic-gradient(#1a73e8 0 ${(losses.building / totalLoss) * 100}%, #7e57c2 0 ${((losses.building + losses.contents) / totalLoss) * 100}%, #f4511e 0)` }}><span>{money(totalLoss)}</span></div><div><h3>Mean-event loss composition</h3><p><i style={{ background: "#1a73e8" }} /> Building <b>{money(losses.building)}</b></p><p><i style={{ background: "#7e57c2" }} /> Contents <b>{money(losses.contents)}</b></p><p><i style={{ background: "#f4511e" }} /> Business interruption <b>{money(losses.interruption)}</b></p></div></div>
    </section>}

    {tab === "curves" && <section id="result-panel-curves" role="tabpanel" aria-labelledby="result-tab-curves" className="analytics-section">
      <div className="section-title"><LineChart size={18} /><div><h3>Depth–damage vulnerability functions</h3><p>Thick curves were used in this run. Dots are the synthetic demonstration assets at their modelled depth.</p></div></div>
      {curves.length ? <CurveChart curves={curves} run={run} /> : <p className="analytics-empty">The governed vulnerability library is unavailable; no curve was recreated in the browser.</p>}
      <div className="method-note"><AlertTriangle size={16} /><p><strong>Correct terminology:</strong> for this flood MVP these are depth–damage vulnerability functions, not seismic fragility curves. They are experimental demonstration curves and are not automatically promoted from research.</p></div>
      <div className="curve-cards">{curves.filter((curve) => run.asset_damage.some((asset) => asset.vulnerability_function_id === curve.function_id)).map((curve) => <article key={curve.function_id}><span>{curve.approval_status.replaceAll("_", " ")}</span><strong>{curve.name}</strong><p>{curve.applicability_notes}</p><small>Calibration {curve.calibration_min}–{curve.calibration_max} {curve.intensity_measure.unit} · CoV {curve.damage_ratio_cov.toFixed(2)} · {curve.version}</small></article>)}</div>
    </section>}

    {tab === "financials" && <section id="result-panel-financials" role="tabpanel" aria-labelledby="result-tab-financials" className="analytics-section">
      <div className="section-title"><BarChart3 size={18} /><div><h3>Damage-state probabilities</h3><p>Average probability across assets; not a count of observed damaged buildings.</p></div></div>
      <div className="damage-stack" aria-label="Average modelled damage state probability">{stateAverage.map((item) => <span key={item.state} style={{ width: `${item.value * 100}%`, background: DAMAGE_COLORS[item.state] }} title={`${item.state}: ${(item.value * 100).toFixed(1)}%`} />)}</div>
      <div className="damage-legend">{stateAverage.map((item) => <span key={item.state}><i style={{ background: DAMAGE_COLORS[item.state] }} />{item.state}<b>{(item.value * 100).toFixed(1)}%</b></span>)}</div>
      <div className="asset-table"><div className="asset-table-head"><span>Asset</span><span>Depth</span><span>Mean damage</span><span>Ground-up loss</span></div>{[...run.asset_damage].sort((a, b) => b.ground_up_loss_usd - a.ground_up_loss_usd).map((asset) => <div key={asset.asset_id}><strong>{asset.asset_id}</strong><span>{asset.intensity.toFixed(1)} ft</span><span>{(asset.mean_damage_ratio * 100).toFixed(1)}%</span><span>{money(asset.ground_up_loss_usd)}</span></div>)}</div>
      <div className="section-title"><LineChart size={18} /><div><h3>Exceedance and tail analysis</h3><p>OEP is the largest event in a year; AEP is the annual aggregate. Both use the labelled demonstration event set.</p></div></div>
      {probabilistic ? <><div className="tail-cards"><article><span>Average annual loss</span><strong>{money(probabilistic.aal_usd)}</strong></article>{probabilistic.var.map((item) => <article key={`var-${item.quantile}`}><span>VaR {(item.quantile * 100).toFixed(0)}%</span><strong>{money(item.loss_usd)}</strong></article>)}</div><EPChart probabilistic={probabilistic} /><div className="method-note"><Database size={16} /><p>{probabilistic.method}. {probabilistic.simulation_years.toLocaleString()} simulated years; {probabilistic.event_count} event definitions. This is not a live-event forecast.</p></div></> : <p className="analytics-empty">The event-set analysis could not be retrieved. No EP curve was approximated in the browser.</p>}
      <RunChartsPanel key={run.run_id} run={run} />
    </section>}

    {tab === "audit" && <section id="result-panel-audit" role="tabpanel" aria-labelledby="result-tab-audit" className="analytics-section">
      <div className="section-title"><ShieldCheck size={18} /><div><h3>Automatic model review</h3><p>Findings check missing inputs, extrapolation, resolution, assumptions and model applicability.</p></div></div>
      <div className="audit-list">{run.audit_findings.map((finding) => <article key={finding.code}><AlertTriangle size={17} /><div><strong>{finding.title}</strong><p>{finding.detail}</p><small>{finding.recommendation}</small></div></article>)}</div>
      <h3>Limitations</h3><ul className="limitations-list">{run.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
    </section>}
  </div>;
}
