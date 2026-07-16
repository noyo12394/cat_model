"use client";

import { useState } from "react";
import type { Severity } from "@/lib/types";

const SEVERITY_AMPLITUDE: Record<Severity, number> = {
  unknown: 4,
  normal: 4,
  watch: 8,
  elevated: 14,
  severe: 22,
  extreme: 30,
};

export interface HeartbeatComponents {
  hazardIntensity: number; // 0-1
  rateOfChange: number;
  geographicSpread: number;
  infrastructureStress: number;
  populationExposure: number;
  sourceAgreement: number; // 0-1, higher = more agreement
}

/** Disaster Heartbeat (section 21): a navigation/attention device, not a
 * scientific score. Clicking it reveals every underlying component. */
export function DisasterHeartbeat({
  severity,
  components,
  label,
}: {
  severity: Severity;
  components: HeartbeatComponents;
  label: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const amplitude = SEVERITY_AMPLITUDE[severity];
  const width = 160;
  const height = 40;
  const mid = height / 2;
  const path = `M0,${mid} L${width * 0.3},${mid} L${width * 0.38},${mid - amplitude} L${width * 0.46},${mid + amplitude * 0.6} L${width * 0.54},${mid} L${width * 0.62},${mid - amplitude * 0.4} L${width},${mid}`;

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-3 text-left"
        aria-expanded={expanded}
      >
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden className="shrink-0">
          <path
            d={path}
            fill="none"
            stroke="var(--status-elevated)"
            strokeWidth={2}
            className="motion-safe:animate-pulse"
          />
        </svg>
        <span>
          <span className="block text-sm font-semibold">{label}</span>
          <span className="block text-xs text-foreground/60">Attention indicator - tap to see what feeds it</span>
        </span>
      </button>
      {expanded && (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-border pt-3 text-xs">
          <dt>Hazard intensity</dt>
          <dd>{pct(components.hazardIntensity)}</dd>
          <dt>Rate of change</dt>
          <dd>{pct(components.rateOfChange)}</dd>
          <dt>Geographic spread</dt>
          <dd>{pct(components.geographicSpread)}</dd>
          <dt>Infrastructure stress</dt>
          <dd>{pct(components.infrastructureStress)}</dd>
          <dt>Population exposure</dt>
          <dd>{pct(components.populationExposure)}</dd>
          <dt>Source agreement</dt>
          <dd>{pct(components.sourceAgreement)}</dd>
        </dl>
      )}
    </div>
  );
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}
