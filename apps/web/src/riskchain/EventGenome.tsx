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
  const [yaw, setYaw] = React.useState(28);
  const [pitch, setPitch] = React.useState(-18);
  const drag = React.useRef<{ x: number; y: number } | null>(null);
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
  const radians = (degrees: number) => degrees * Math.PI / 180;
  const project = (point: { x: number; y: number; z: number }) => {
    const ry = radians(yaw); const rx = radians(pitch);
    const x1 = point.x * Math.cos(ry) - point.z * Math.sin(ry);
    const z1 = point.x * Math.sin(ry) + point.z * Math.cos(ry);
    const y2 = point.y * Math.cos(rx) - z1 * Math.sin(rx);
    const z2 = point.y * Math.sin(rx) + z1 * Math.cos(rx);
    const scale = 1 + z2 / 430;
    return { x: 180 + x1 * scale, y: 144 + y2 * scale, z: z2, scale };
  };
  const pairs = loci.map((_, index) => {
    const theta = index * 0.92;
    const y = -116 + index * 25.8;
    return {
      index,
      a: project({ x: 57 * Math.cos(theta), y, z: 57 * Math.sin(theta) }),
      b: project({ x: -57 * Math.cos(theta), y, z: -57 * Math.sin(theta) }),
    };
  });
  const pathFor = (side: "a" | "b") => pairs.map((pair, index) => `${index === 0 ? "M" : "L"}${pair[side].x.toFixed(1)} ${pair[side].y.toFixed(1)}`).join(" ");
  const leftPath = pathFor("a");
  const rightPath = pathFor("b");
  const orderedPairs = [...pairs].sort((left, right) => Math.min(left.a.z, left.b.z) - Math.min(right.a.z, right.b.z));

  function handlePointerDown(event: React.PointerEvent<SVGSVGElement>) {
    drag.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: React.PointerEvent<SVGSVGElement>) {
    if (!drag.current) return;
    const dx = event.clientX - drag.current.x;
    const dy = event.clientY - drag.current.y;
    drag.current = { x: event.clientX, y: event.clientY };
    setYaw((value) => value + dx * 0.55);
    setPitch((value) => Math.max(-58, Math.min(42, value - dy * 0.38)));
  }

  function stopDrag() { drag.current = null; }

  return <section className="event-genome" aria-label={`Event signature for ${event.name}`}>
    <div className="genome-stage">
      <svg viewBox="0 0 360 286" role="img" aria-label="Rotatable three-dimensional double-helix visual encoding of published event metadata" onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={stopDrag} onPointerCancel={stopDrag}>
        <defs>
          <linearGradient id="genomeLeft" x1="0" x2="1"><stop stopColor={hue} /><stop offset="1" stopColor={alert} /></linearGradient>
          <linearGradient id="genomeRight" x1="1" x2="0"><stop stopColor={hue} /><stop offset="1" stopColor={alert} /></linearGradient>
          <filter id="genomeGlow" x="-40%" y="-20%" width="180%" height="140%"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path d={leftPath} fill="none" stroke="url(#genomeLeft)" strokeOpacity=".22" strokeWidth="9" strokeLinecap="round" filter="url(#genomeGlow)" />
        <path d={rightPath} fill="none" stroke="url(#genomeRight)" strokeOpacity=".22" strokeWidth="9" strokeLinecap="round" filter="url(#genomeGlow)" />
        {orderedPairs.map((pair) => {
          const label = loci[pair.index][0]; const foreground = (pair.a.z + pair.b.z) / 2;
          const midpoint = { x: (pair.a.x + pair.b.x) / 2, y: (pair.a.y + pair.b.y) / 2 };
          const opacity = Math.max(.26, Math.min(1, .48 + foreground / 135));
          const size = Math.max(3.4, Math.min(6.6, 4.7 + foreground / 110));
          return <g key={label} opacity={opacity}>
            <line x1={pair.a.x} x2={pair.b.x} y1={pair.a.y} y2={pair.b.y} stroke={pair.index === 1 ? alert : hue} strokeWidth={pair.index === 1 ? 3.2 : 2.1} />
            <circle cx={pair.a.x} cy={pair.a.y} r={size} fill={hue} stroke="#0A1220" strokeWidth="2" />
            <circle cx={pair.b.x} cy={pair.b.y} r={size} fill={pair.index === 1 ? alert : hue} stroke="#0A1220" strokeWidth="2" />
            <text x={midpoint.x} y={midpoint.y - 7} textAnchor="middle">{String(pair.index + 1).padStart(2, "0")}</text>
          </g>;
        })}
      </svg>
      <div className="genome-controls"><label>Orbit<input aria-label="Rotate event signature" type="range" min="-180" max="180" value={yaw} onChange={(event) => setYaw(Number(event.target.value))} /></label><label>Tilt<input aria-label="Tilt event signature" type="range" min="-58" max="42" value={pitch} onChange={(event) => setPitch(Number(event.target.value))} /></label><button type="button" onClick={() => { setYaw(28); setPitch(-18); }} aria-label="Reset signature orientation"><RotateCcw size={15} /></button></div>
    </div>
    <p className="genome-orbit-tip">Drag the helix to orbit it in 3D. Depth changes the size and opacity of each published metadata locus.</p>
    <div className="genome-key"><span><i style={{ background: hue }} /> Hazard class</span><span><i style={{ background: alert }} /> Official alert level</span><span><i className="genome-line" /> Metadata locus</span></div>
    <div className="genome-loci">{loci.map(([label, value], index) => <div key={label}><span>{String(index + 1).padStart(2, "0")}</span><dl><dt>{label}</dt><dd>{value}</dd></dl></div>)}</div>
    <p className="genome-limit"><Info size={15} /> This is a visual index of published event metadata. It is not a biological model, physical hazard measurement, forecast, probability, or risk score.</p>
  </section>;
}
