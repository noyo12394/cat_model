"use client";

type Props = {
  losses: number[];
  currency?: string;
  markedReturnPeriods?: number[];
  view: "cumulative" | "exceedance";
  observationUnit?: string;
  aal?: number;
  varValue?: number;
};

export function LossCurve({ losses, currency = "USD", markedReturnPeriods = [100, 250], view, observationUnit = "source observation", aal, varValue }: Props) {
  if (losses.length < 2) return <div className="historic-unavailable"><strong>Curve not available from source</strong><span>The selected official dataset does not publish a compatible sorted loss array. EarthPulse does not synthesize one.</span><small>Y-axis units: {currency}, source basis · denominator: {observationUnit} · probability convention: empirical annual exceedance probability requires a sourced annual-loss sample.</small></div>;
  const sorted = [...losses].sort((a, b) => a - b);
  const cumulative = sorted.reduce<number[]>((values, loss) => [...values, loss + (values.at(-1) ?? 0)], []);
  const plotted = view === "cumulative" ? cumulative : [...sorted].reverse();
  const max = Math.max(...plotted, 1);
  const points = plotted.map((loss, index) => {
    const x = 42 + (index / Math.max(1, sorted.length - 1)) * 510;
    const y = 210 - (loss / max) * 170;
    return `${x},${y}`;
  }).join(" ");
  return <figure className="loss-curve" aria-label={`${view} loss curve`}>
    <svg viewBox="0 0 590 250" role="img">
      <line x1="42" y1="210" x2="560" y2="210" /><line x1="42" y1="35" x2="42" y2="210" />
      {view === "exceedance" && <path className="tail" d="M 470 210 L 470 120 L 560 40 L 560 210 Z" />}
      <polyline points={points} />
      {view === "exceedance" && markedReturnPeriods.map((period, index) => <g key={period}><line className="mark" x1={420 + index * 70} x2={420 + index * 70} y1="45" y2="210" /><text x={408 + index * 70} y="28">1-in-{period}</text></g>)}
      <text x="245" y="242">{view === "cumulative" ? "Ranked observation / geographic unit" : "Annual exceedance probability (right tail = lower probability)"}</text>
      <text transform="translate(13 178) rotate(-90)">Loss ({currency}, source basis)</text>
    </svg>
    <figcaption>{view === "cumulative" ? `Cumulative loss — ascending source observations; denominator: ${observationUnit}` : `Empirical exceedance probability — Weibull plotting position rank/(n+1); tail beyond VaR shaded${aal === undefined ? "; AAL not supplied" : `; AAL ${aal} ${currency}`}${varValue === undefined ? "; VaR not supplied" : `; VaR ${varValue} ${currency}`}`}</figcaption>
  </figure>;
}
