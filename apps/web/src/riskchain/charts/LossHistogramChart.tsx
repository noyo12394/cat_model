"use client";

import { money } from "./chartApi";
import type { LossHistogram } from "./chartTypes";
import { linearScale } from "./scale";
import styles from "./charts.module.css";

const W = 460;
const H = 210;
const PAD = { top: 16, right: 14, bottom: 30, left: 14 };

/** Binned Monte Carlo loss distribution with p10/p50/p90 markers. */
export function LossHistogramChart({ chart }: { chart: LossHistogram }) {
  const maxCount = Math.max(...chart.bins.map((b) => b.count), 1);
  const lo = chart.bins[0]?.lower ?? 0;
  const hi = chart.bins[chart.bins.length - 1]?.upper ?? 1;
  const sx = linearScale([lo, hi], [PAD.left, W - PAD.right]);
  const sy = linearScale([0, maxCount], [H - PAD.bottom, PAD.top]);

  const percentiles: { label: string; value: number }[] = [
    { label: "p10", value: chart.p10_usd },
    { label: "median", value: chart.p50_usd },
    { label: "p90", value: chart.p90_usd },
  ];

  return (
    <div className={styles.chartCard}>
      <h4 className={styles.chartTitle}>{chart.title}</h4>
      <p className={styles.chartSub}>{chart.samples.toLocaleString()} simulations · {chart.x_axis.label}</p>
      <div className={styles.svgWrap}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Simulated loss distribution histogram">
          {chart.bins.map((bin) => {
            const x = sx(bin.lower);
            const width = Math.max(1, sx(bin.upper) - sx(bin.lower) - 1);
            const y = sy(bin.count);
            return (
              <rect key={bin.lower} x={x} y={y} width={width} height={H - PAD.bottom - y}
                rx={1.5} fill="var(--blue)" opacity={0.75} />
            );
          })}
          {percentiles.map((p) => (
            <g key={p.label}>
              <line x1={sx(p.value)} x2={sx(p.value)} y1={PAD.top - 2} y2={H - PAD.bottom} stroke="var(--text)" strokeDasharray="4 3" opacity={0.55} />
              <text className={styles.axisText} x={sx(p.value)} y={PAD.top - 5} textAnchor="middle" fontWeight={700}>
                {p.label} {money(p.value)}
              </text>
            </g>
          ))}
          <line className={styles.gridLine} x1={PAD.left} x2={W - PAD.right} y1={H - PAD.bottom} y2={H - PAD.bottom} />
          <text className={styles.axisText} x={PAD.left} y={H - PAD.bottom + 16}>{money(lo)}</text>
          <text className={styles.axisText} x={W - PAD.right} y={H - PAD.bottom + 16} textAnchor="end">{money(hi)}</text>
        </svg>
      </div>
      <p className={styles.caption}>{chart.basis}</p>
    </div>
  );
}
