"use client";

import { useState } from "react";
import type { Severity } from "@/lib/types";

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

  return (
    <div className="heartbeat-card" data-severity={severity}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="heartbeat-button"
        aria-expanded={expanded}
      >
        <span className="heartbeat-viz" aria-hidden>
          {Array.from({ length: 9 }).map((_, index) => <i key={index} />)}
        </span>
        <span className="heartbeat-copy"><strong>{label}</strong><small>Attention signal · open components</small></span>
      </button>
      {expanded && (
        <dl className="heartbeat-details">
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
