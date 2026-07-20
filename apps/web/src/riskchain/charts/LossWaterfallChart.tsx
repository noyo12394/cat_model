"use client";

import { money } from "./chartApi";
import type { LossWaterfall } from "./chartTypes";
import { linearScale } from "./scale";
import styles from "./charts.module.css";

const W = 460;
const H = 230;
const PAD = { top: 22, right: 12, bottom: 52, left: 12 };

/** Ground-up → deductible → limit → coinsurance → net insured waterfall. */
export function LossWaterfallChart({ chart }: { chart: LossWaterfall }) {
  const total = chart.steps[0]?.amount_usd ?? 1;
  const sy = linearScale([0, total], [H - PAD.bottom, PAD.top]);
  const stepWidth = (W - PAD.left - PAD.right) / chart.steps.length;
  const barWidth = stepWidth * 0.62;

  return (
    <div className={styles.chartCard}>
      <h4 className={styles.chartTitle}>{chart.title}</h4>
      <p className={styles.chartSub}>All values {chart.currency}</p>
      <div className={styles.svgWrap}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Loss waterfall from ground-up to net insured">
          {chart.steps.map((step, index) => {
            const cx = PAD.left + index * stepWidth + stepWidth / 2;
            const isEdge = index === 0 || index === chart.steps.length - 1;
            const prevTotal = index === 0 ? step.amount_usd : chart.steps[index - 1].running_total_usd;
            const top = isEdge ? sy(step.running_total_usd) : sy(prevTotal);
            const bottom = isEdge ? sy(0) : sy(step.running_total_usd);
            const height = Math.max(1.5, bottom - top);
            const fill = isEdge ? (index === 0 ? "var(--blue)" : "var(--green)") : "var(--amber)";
            return (
              <g key={step.label}>
                <rect x={cx - barWidth / 2} y={top} width={barWidth} height={height} rx={3} fill={fill} opacity={isEdge ? 0.9 : 0.75} />
                {index < chart.steps.length - 1 && (
                  <line x1={cx + barWidth / 2} x2={cx + stepWidth - barWidth / 2} y1={sy(step.running_total_usd)} y2={sy(step.running_total_usd)} stroke="var(--muted)" strokeDasharray="3 3" />
                )}
                <text className={styles.axisText} x={cx} y={top - 6} textAnchor="middle" fontWeight={700}>
                  {money(Math.abs(step.amount_usd))}
                </text>
                {step.label.split(" ").reduce<string[][]>((rows, word) => {
                  const last = rows[rows.length - 1];
                  if (last && (last.join(" ").length + word.length) < 14) last.push(word);
                  else rows.push([word]);
                  return rows;
                }, []).slice(0, 3).map((row, rowIndex) => (
                  <text key={rowIndex} className={styles.axisText} x={cx} y={H - PAD.bottom + 14 + rowIndex * 11} textAnchor="middle">
                    {row.join(" ")}
                  </text>
                ))}
              </g>
            );
          })}
        </svg>
      </div>
      <p className={styles.caption}>{chart.basis}</p>
    </div>
  );
}
