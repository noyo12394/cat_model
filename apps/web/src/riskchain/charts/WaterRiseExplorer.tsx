"use client";

import { useMemo, useState } from "react";
import { money } from "./chartApi";
import type { WaterRiseSweep } from "./chartTypes";
import { areaPath, linePath, linearScale } from "./scale";
import styles from "./charts.module.css";

const W = 460;
const H = 200;
const PAD = { top: 14, right: 14, bottom: 30, left: 14 };

/** Interactive "raise the water" explorer: drag the slider to move the water
 * level and read total loss + assets affected off the sensitivity sweep. */
export function WaterRiseExplorer({ chart }: { chart: WaterRiseSweep }) {
  const [offset, setOffset] = useState(chart.scenario_offset_ft);
  const points = chart.points.map((p) => ({ x: p.offset_ft, y: p.total_ground_up_usd }));
  const maxLoss = Math.max(...points.map((p) => p.y), 1);
  const sx = linearScale([points[0].x, points[points.length - 1].x], [PAD.left, W - PAD.right]);
  const sy = linearScale([0, maxLoss], [H - PAD.bottom, PAD.top]);

  const current = useMemo(
    () => chart.points.reduce((best, p) => (Math.abs(p.offset_ft - offset) < Math.abs(best.offset_ft - offset) ? p : best), chart.points[0]),
    [chart.points, offset],
  );

  return (
    <div className={styles.chartCard}>
      <h4 className={styles.chartTitle}>{chart.title}</h4>
      <p className={styles.chartSub}>{chart.x_axis.label} ({chart.x_axis.unit}) · 0 = modelled scenario</p>
      <div className={styles.svgWrap}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Total loss as the water level changes">
          <defs>
            <linearGradient id="waterFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--blue)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--blue)" stopOpacity="0.04" />
            </linearGradient>
          </defs>
          <path d={areaPath(points, sx, sy, H - PAD.bottom)} fill="url(#waterFill)" />
          <path d={linePath(points, sx, sy)} fill="none" stroke="var(--blue)" strokeWidth={2.5} />
          {/* scenario anchor at offset 0 */}
          <line x1={sx(0)} x2={sx(0)} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--muted)" strokeDasharray="3 3" />
          <text className={styles.axisText} x={sx(0)} y={PAD.top - 3} textAnchor="middle">scenario</text>
          {/* live cursor */}
          <line x1={sx(current.offset_ft)} x2={sx(current.offset_ft)} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--red)" strokeWidth={1.5} />
          <circle cx={sx(current.offset_ft)} cy={sy(current.total_ground_up_usd)} r={5.5} fill="var(--red)" stroke="white" strokeWidth={2} />
          <line className={styles.gridLine} x1={PAD.left} x2={W - PAD.right} y1={H - PAD.bottom} y2={H - PAD.bottom} />
          <text className={styles.axisText} x={PAD.left} y={H - PAD.bottom + 15}>{points[0].x} ft</text>
          <text className={styles.axisText} x={W - PAD.right} y={H - PAD.bottom + 15} textAnchor="end">+{points[points.length - 1].x} ft</text>
        </svg>
      </div>
      <div className={styles.sliderRow}>
        <input
          type="range"
          min={points[0].x}
          max={points[points.length - 1].x}
          step={0.5}
          value={offset}
          onChange={(event) => setOffset(Number(event.target.value))}
          aria-label="Water level offset in feet relative to the modelled scenario"
        />
        <div className={styles.sliderValue}>
          <strong>{money(current.total_ground_up_usd)}</strong>
          <small>{current.offset_ft >= 0 ? "+" : ""}{current.offset_ft.toFixed(1)} ft · {current.assets_wet} assets affected</small>
        </div>
      </div>
      <p className={styles.caption}>{chart.caveat}</p>
    </div>
  );
}
