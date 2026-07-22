"use client";

import * as React from "react";
import { Info, RotateCcw } from "lucide-react";
import type { GlobalEvent } from "@/lib/types";

type Props = { event: GlobalEvent };

function formatUtc(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not reported";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(date) + " UTC";
}

function hazardColor(type: string) {
  if (/^(fl|flood)$/i.test(type)) return "#4FA8FF";
  if (/^(eq|earthquake)$/i.test(type)) return "#B48CFF";
  if (/^(wf|fire|wildfire)$/i.test(type)) return "#FF8A3D";
  if (/^(tc|cyclone|storm|wind)$/i.test(type)) return "#60D6C6";
  return "#8FA3B8";
}

function alertColor(level: string) {
  if (level === "red") return "#FF5B55";
  if (level === "orange") return "#F6A94A";
  return "#35C77B";
}

export function EventGenome({ event }: Props) {
  const [rotation, setRotation] = React.useState(12);
  const hue = hazardColor(event.event_type);
  const alert = alertColor(event.alert_level);
  const loci = [
    ["Hazard class", event.event_type || "Not reported"],
    ["Alert level", event.alert_level || "Not reported"],
    ["Alert score", event.alert_score == null ? "Not supplied" : String(event.alert_score)],
    ["Reported area", event.country || "Not reported"],
    ["Event start", formatUtc(event.from_date)],
    ["Last official update", formatUtc(event.modified_at)],
    ["Official source", event.source || "Not reported"],
    ["Event geometry", event.geometry_url ? "Published link available" : "No published link"],
    ["Feed state", event.is_current ? "Current feed item" : "Historical feed item"],
    ["Record status", event.data_status],
  ] as const;
  const y = (index: number) => 24 + index * 26;
  const xA = (index: number) => 102 + Math.sin(index * 0.92 + rotation * Math.PI / 180) * 31;
  const xB = (index: number) => 258 - Math.sin(index * 0.92 + rotation * Math.PI / 180) * 31;
  const leftPath = loci.map((_, index) => `${index === 0 ? "M" : "L"}${xA(index).toFixed(1)} ${y(index)}`).join(" ");
  const rightPath = loci.map((_, index) => `${index === 0 ? "M" : "L"}${xB(index).toFixed(1)} ${y(index)}`).join(" ");

  return <section className="event-genome" aria-label={`Event signature for ${event.name}`}>
    <div className="genome-stage">
      <svg viewBox="0 0 360 286" role="img" aria-label="Interactive double-helix visual encoding of published event metadata">
        <defs>
          <linearGradient id="genomeLeft" x1="0" x2="1"><stop stopColor={hue} /><stop offset="1" stopColor={alert} /></linearGradient>
          <linearGradient id="genomeRight" x1="1" x2="0"><stop stopColor={hue} /><stop offset="1" stopColor={alert} /></linearGradient>
          <filter id="genomeGlow" x="-40%" y="-20%" width="180%" height="140%"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path d={leftPath} fill="none" stroke="url(#genomeLeft)" strokeWidth="5" strokeLinecap="round" filter="url(#genomeGlow)" />
        <path d={rightPath} fill="none" stroke="url(#genomeRight)" strokeWidth="5" strokeLinecap="round" filter="url(#genomeGlow)" />
        {loci.map(([label], index) => <g key={label}>
          <line x1={xA(index)} x2={xB(index)} y1={y(index)} y2={y(index)} stroke={index === 1 ? alert : hue} strokeOpacity=".68" strokeWidth={index === 1 ? 3 : 2} />
          <circle cx={xA(index)} cy={y(index)} r="5" fill={hue} stroke="#0A1220" strokeWidth="2" />
          <circle cx={xB(index)} cy={y(index)} r="5" fill={index === 1 ? alert : hue} stroke="#0A1220" strokeWidth="2" />
          <text x="180" y={y(index) - 7} textAnchor="middle">{String(index + 1).padStart(2, "0")}</text>
        </g>)}
      </svg>
      <div className="genome-controls"><label>Rotate signature<input aria-label="Rotate event signature" type="range" min="0" max="360" value={rotation} onChange={(event) => setRotation(Number(event.target.value))} /></label><button type="button" onClick={() => setRotation(12)} aria-label="Reset signature rotation"><RotateCcw size={15} /></button></div>
    </div>
    <div className="genome-key"><span><i style={{ background: hue }} /> Hazard class</span><span><i style={{ background: alert }} /> Official alert level</span><span><i className="genome-line" /> Metadata locus</span></div>
    <div className="genome-loci">{loci.map(([label, value], index) => <div key={label}><span>{String(index + 1).padStart(2, "0")}</span><dl><dt>{label}</dt><dd>{value}</dd></dl></div>)}</div>
    <p className="genome-limit"><Info size={15} /> This is a visual index of published event metadata. It is not a biological model, physical hazard measurement, forecast, probability, or risk score.</p>
  </section>;
}
