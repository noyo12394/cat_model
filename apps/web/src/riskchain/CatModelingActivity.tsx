"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, ArrowLeft, ArrowRight, BookOpenCheck, Check, CheckCircle2, CircleHelp,
  ClipboardCheck, Clock3, Database, Download, ExternalLink, FileCheck2, FlaskConical,
  Gauge, GraduationCap, MapPinned, Pause, Play, Radio, RotateCcw, ShieldCheck, Sparkles,
  TimerReset, UsersRound,
} from "lucide-react";
import type { GlobalEvent, GlobalEventsResponse, VulnerabilityFunction } from "@/lib/types";

type ActivityProps = {
  events: GlobalEvent[];
  eventsResponse: GlobalEventsResponse | null;
  curves: VulnerabilityFunction[];
  onInspectEvent: (event: GlobalEvent) => void;
  onOpenLive: () => void;
  onRunDemo: () => void;
  onOpenLesson: (lessonId: string) => void;
};

type ActivityState = {
  activeStep: number;
  completed: number[];
  teamName: string;
  role: "data" | "model" | "communicator" | "";
  eventSnapshot: GlobalEvent | null;
  markerAnswer: string;
  nextData: string;
  chainAnswers: Record<string, string>;
  curveId: string;
  depthFt: number;
  comparisonDepthFt: number;
  replacementValue: string;
  prediction: string;
  officialObservation: string;
  limitation: string;
  nextAction: string;
  exitAnswer: string;
  instructorMode: boolean;
};

const STORAGE_KEY = "riskchain-fire-activity-v1";

const STATIONS = [
  { title: "Launch the team", short: "Launch", minutes: 5, icon: UsersRound },
  { title: "Freeze a real event", short: "Evidence", minutes: 10, icon: Radio },
  { title: "Interrogate the map", short: "Map", minutes: 10, icon: MapPinned },
  { title: "Build the CAT chain", short: "CAT chain", minutes: 10, icon: Database },
  { title: "Read vulnerability", short: "Curve", minutes: 12, icon: Gauge },
  { title: "Calculate & challenge", short: "Loss", minutes: 8, icon: FlaskConical },
  { title: "Audit & communicate", short: "Brief", minutes: 5, icon: FileCheck2 },
] as const;

const CHAIN_PROMPTS = [
  { id: "intensity", text: "Flood depth, wind speed, or shaking intensity at a location", answer: "hazard" },
  { id: "assets", text: "Buildings, people, infrastructure, and values in the affected area", answer: "exposure" },
  { id: "response", text: "How an asset class is expected to respond at a given intensity", answer: "vulnerability" },
  { id: "consequence", text: "Damage translated into repair cost, downtime, or insured loss", answer: "loss" },
] as const;

const SOURCE_LINKS = [
  { label: "FEMA Hazus technical manuals", href: "https://www.fema.gov/flood-maps/products-tools/hazus/user-technical-manuals", note: "Hazard, inventory, damage and loss methodology" },
  { label: "FEMA Hazus training", href: "https://www.fema.gov/flood-maps/products-tools/hazus/training", note: "Guided analysis and interpretation workflows" },
  { label: "USGS ShakeMap", href: "https://earthquake.usgs.gov/data/shakemap/", note: "Near-real-time shaking maps and uncertainty products" },
  { label: "USGS ShakeMap product guide", href: "https://ghsc.code-pages.usgs.gov/esi/shakemap/docs2020/manual4_0/ug_products.html", note: "How mapped shaking products, contours, and uncertainty should be interpreted" },
  { label: "GDACS API", href: "https://www.gdacs.org/gdacsapi/swagger/index.html", note: "Official multi-hazard event discovery used by this activity" },
  { label: "Oasis Loss Modelling Framework", href: "https://oasislmf.org/", note: "Open, modular catastrophe-model execution reference" },
  { label: "EarthScope: From Data to Story", href: "https://www.iris.edu/hq/inclass/lesson/instructional_sequence_from_data_to_story", note: "Evidence-led earthquake learning sequence" },
] as const;

const DEFAULT_STATE: ActivityState = {
  activeStep: 0,
  completed: [],
  teamName: "",
  role: "",
  eventSnapshot: null,
  markerAnswer: "",
  nextData: "",
  chainAnswers: {},
  curveId: "",
  depthFt: 2,
  comparisonDepthFt: 3,
  replacementValue: "500000",
  prediction: "",
  officialObservation: "",
  limitation: "",
  nextAction: "",
  exitAnswer: "",
  instructorMode: false,
};

function loadState(): ActivityState {
  if (typeof window === "undefined") return DEFAULT_STATE;
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "null") as Partial<ActivityState> | null;
    return saved ? { ...DEFAULT_STATE, ...saved, activeStep: Math.min(6, Math.max(0, saved.activeStep ?? 0)) } : DEFAULT_STATE;
  } catch {
    return DEFAULT_STATE;
  }
}

function formatUtc(value?: string | null) {
  if (!value) return "Not reported";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Not reported";
  return `${new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(parsed)} UTC`;
}

function formatMoney(value: number | null) {
  if (value == null || !Number.isFinite(value)) return "Unavailable";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function cleanClause(value: string, fallback: string) {
  return (value.trim() || fallback).replace(/[.!?]+$/, "");
}

function ratioAt(curve: VulnerabilityFunction | undefined, intensity: number) {
  if (!curve?.curve.length) return null;
  const points = curve.curve;
  if (intensity <= points[0].intensity) return points[0].mean_damage_ratio;
  if (intensity >= points[points.length - 1].intensity) return points[points.length - 1].mean_damage_ratio;
  for (let index = 0; index < points.length - 1; index += 1) {
    const lower = points[index];
    const upper = points[index + 1];
    if (intensity >= lower.intensity && intensity <= upper.intensity) {
      const fraction = (intensity - lower.intensity) / (upper.intensity - lower.intensity);
      return lower.mean_damage_ratio + fraction * (upper.mean_damage_ratio - lower.mean_damage_ratio);
    }
  }
  return null;
}

function CurvePlot({ curve, intensity, comparisonIntensity }: { curve?: VulnerabilityFunction; intensity: number; comparisonIntensity: number }) {
  if (!curve?.curve.length) return <div className="activity-blocked"><AlertTriangle size={18} /><span><strong>Curve service unavailable</strong>No values are substituted. Retry when the governed model registry is connected.</span></div>;
  const width = 640;
  const height = 250;
  const pad = { left: 54, right: 18, top: 20, bottom: 38 };
  const minX = curve.calibration_min;
  const maxX = curve.calibration_max;
  const x = (value: number) => pad.left + ((value - minX) / (maxX - minX)) * (width - pad.left - pad.right);
  const y = (value: number) => height - pad.bottom - value * (height - pad.top - pad.bottom);
  const line = curve.curve.map((point) => `${x(point.intensity)},${y(point.mean_damage_ratio)}`).join(" ");
  const ratio = ratioAt(curve, intensity) ?? 0;
  const comparisonRatio = ratioAt(curve, comparisonIntensity) ?? 0;
  return <div className="activity-curve-wrap">
    <svg className="activity-curve" role="img" aria-label={`${curve.name} depth-damage curve`} viewBox={`0 0 ${width} ${height}`}>
      {[0, .25, .5, .75, 1].map((tick) => <g key={tick}><line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} /><text x={pad.left - 10} y={y(tick) + 4} textAnchor="end">{Math.round(tick * 100)}%</text></g>)}
      <line className="axis" x1={pad.left} x2={width - pad.right} y1={height - pad.bottom} y2={height - pad.bottom} />
      <polyline className="curve-line" points={line} />
      <line className="comparison-guide" x1={x(comparisonIntensity)} x2={x(comparisonIntensity)} y1={y(comparisonRatio)} y2={height - pad.bottom} />
      <circle className="comparison-point" cx={x(comparisonIntensity)} cy={y(comparisonRatio)} r="6" />
      <line className="active-guide" x1={x(intensity)} x2={x(intensity)} y1={y(ratio)} y2={height - pad.bottom} />
      <circle className="active-point" cx={x(intensity)} cy={y(ratio)} r="7" />
      <text className="axis-label" x={(pad.left + width - pad.right) / 2} y={height - 8} textAnchor="middle">{curve.intensity_measure.label} ({curve.intensity_measure.unit})</text>
    </svg>
    <div className="activity-curve-legend"><span><i className="baseline" /> Baseline: {intensity.toFixed(1)} ft</span><span><i className="comparison" /> Comparison: {comparisonIntensity.toFixed(1)} ft</span></div>
  </div>;
}

export function CatModelingActivity({ events, eventsResponse, curves, onInspectEvent, onOpenLive, onRunDemo, onOpenLesson }: ActivityProps) {
  const [activity, setActivity] = useState<ActivityState>(loadState);
  const [remaining, setRemaining] = useState(60 * 60);
  const [running, setRunning] = useState(false);
  const [copied, setCopied] = useState(false);

  const currentEvents = useMemo(() => events.filter((event) => event.is_current).sort((a, b) => new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()), [events]);
  const selectedCurve = useMemo(() => curves.find((curve) => curve.function_id === activity.curveId) ?? curves[0], [activity.curveId, curves]);
  const baseRatio = ratioAt(selectedCurve, activity.depthFt);
  const comparisonRatio = ratioAt(selectedCurve, activity.comparisonDepthFt);
  const exposure = Number(activity.replacementValue);
  const baseLoss = baseRatio != null && Number.isFinite(exposure) && exposure > 0 ? baseRatio * exposure : null;
  const comparisonLoss = comparisonRatio != null && Number.isFinite(exposure) && exposure > 0 ? comparisonRatio * exposure : null;
  const chainScore = CHAIN_PROMPTS.filter((prompt) => activity.chainAnswers[prompt.id] === prompt.answer).length;
  const progress = Math.round((activity.completed.length / STATIONS.length) * 100);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(activity));
  }, [activity]);

  useEffect(() => {
    if (!running || remaining <= 0) return;
    const timer = window.setInterval(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [remaining, running]);

  function patch(next: Partial<ActivityState>) {
    setActivity((value) => ({ ...value, ...next }));
  }

  function complete(step = activity.activeStep) {
    setActivity((value) => ({ ...value, completed: value.completed.includes(step) ? value.completed : [...value.completed, step] }));
  }

  function completeAndNext() {
    complete();
    patch({ activeStep: Math.min(STATIONS.length - 1, activity.activeStep + 1) });
  }

  function chooseEvent(eventId: string) {
    const event = currentEvents.find((item) => item.event_id === eventId) ?? null;
    patch({ eventSnapshot: event });
    if (event) onInspectEvent(event);
  }

  function resetActivity() {
    setRunning(false);
    setRemaining(60 * 60);
    setCopied(false);
    setActivity({ ...DEFAULT_STATE, curveId: curves[0]?.function_id ?? "" });
    window.localStorage.removeItem(STORAGE_KEY);
  }

  const event = activity.eventSnapshot;
  const evidenceBrief = [
    event
      ? `Official event metadata show ${event.name} (${event.event_type}) in ${event.country}, last updated ${formatUtc(event.modified_at)} by ${event.source}.${activity.officialObservation.trim() ? ` The team's student-transcribed source note—requiring verification against the linked report—is: ${cleanClause(activity.officialObservation, "not recorded")}.` : ""}`
      : "No official event was frozen for this activity, so no live-event claim can be made.",
    baseLoss != null && selectedCurve
      ? `In a separate classroom model, a student-assumed ${formatMoney(exposure)} exposure at ${activity.depthFt.toFixed(1)} ft uses ${selectedCurve.name} (${selectedCurve.version}) to produce a training estimate of ${formatMoney(baseLoss)}.`
      : "The classroom calculation is incomplete; no training loss estimate is reported.",
    `The largest stated limitation is ${cleanClause(activity.limitation, "not yet documented")}; the next evidence action is ${cleanClause(activity.nextAction, "not yet documented")}.`,
  ].join(" ");

  function downloadBrief() {
    const text = `RISKCHAIN FIRE ACTIVITY — EVIDENCE BRIEF\n\nTeam: ${activity.teamName || "Unnamed team"}\nRole: ${activity.role || "Not selected"}\n\n${evidenceBrief}\n\nOFFICIAL-EVENT SOURCE\n${event?.report_url ?? "No source frozen"}\n\nTRAINING CALCULATION DISCLOSURE\nThis is a classroom model under stated synthetic/user-supplied assumptions. It is not an observed loss, claim, forecast, appraisal, or estimate of the selected live event.\n`;
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "riskchain-fire-activity-brief.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  const minutes = Math.floor(remaining / 60).toString().padStart(2, "0");
  const seconds = (remaining % 60).toString().padStart(2, "0");
  const station = STATIONS[activity.activeStep];

  return <section className="activity-lab" aria-label="FIRE catastrophe modelling activity">
    <header className="activity-header">
      <div>
        <span className="activity-kicker"><GraduationCap size={14} /> FIRE ACTIVITY 01 · BEGINNER · TEAMS OF 3</span>
        <h1>From live alert to model-ready evidence</h1>
        <p>A 60-minute investigation of what catastrophe models can calculate—and what the evidence does not yet support.</p>
      </div>
      <div className="activity-header-tools">
        <button className={activity.instructorMode ? "active" : ""} onClick={() => patch({ instructorMode: !activity.instructorMode })}><BookOpenCheck size={15} /> Instructor {activity.instructorMode ? "on" : "off"}</button>
        <div className="activity-timer" aria-label={`${minutes} minutes ${seconds} seconds remaining`}><Clock3 size={16} /><strong>{minutes}:{seconds}</strong><button onClick={() => setRunning((value) => !value)} aria-label={running ? "Pause activity timer" : "Start activity timer"}>{running ? <Pause size={14} /> : <Play size={14} />}</button></div>
      </div>
    </header>

    <div className="activity-progress-track"><span style={{ width: `${progress}%` }} /><strong>{progress}% complete</strong></div>

    <div className="activity-layout">
      <aside className="activity-rail" aria-label="Activity stations">
        {STATIONS.map((item, index) => <button key={item.title} className={`${activity.activeStep === index ? "active" : ""} ${activity.completed.includes(index) ? "complete" : ""}`} onClick={() => patch({ activeStep: index })}>
          <span className="activity-step-number">{activity.completed.includes(index) ? <Check size={14} /> : String(index + 1).padStart(2, "0")}</span>
          <span><strong>{item.short}</strong><small>{item.minutes} min</small></span>
        </button>)}
        <div className="activity-rail-note"><ShieldCheck size={15} /><p><strong>Evidence rule</strong>Official event facts, demonstration models, and student assumptions never share the same label.</p></div>
        <button className="activity-reset" onClick={resetActivity}><RotateCcw size={14} /> Reset worksheet</button>
      </aside>

      <article className="activity-station">
        <div className="activity-station-head">
          <div><span>Station {activity.activeStep + 1} · {station.minutes} minutes</span><h2>{station.title}</h2></div>
          <div className="activity-station-icon"><station.icon size={21} /></div>
        </div>

        {activity.instructorMode && <div className="instructor-strip"><Sparkles size={16} /><div><strong>Facilitator cue</strong><span>{[
          "Ask students to commit to a role and a first hypothesis before opening data.",
          "Freeze one source revision. Ask which fields are facts, classifications, or missing.",
          "Do not let the event marker become an impact polygon in students’ mental model.",
          "Make each team defend the boundary between H, E, V and L.",
          "Prediction before reveal: which occupancy curve should rise faster, and why?",
          "Change one input only. A fair comparison keeps everything else fixed.",
          "Require: one source, one model statement, one caveat, one next action.",
        ][activity.activeStep]}</span></div></div>}

        {activity.activeStep === 0 && <div className="activity-content">
          <div className="activity-callout important"><ClipboardCheck size={20} /><div><strong>Your mission</strong><p>Advise an emergency-planning team without turning an alert marker into a loss estimate. By the end, you will explain the full <b>event → hazard → exposure → vulnerability → loss</b> chain.</p></div></div>
          <div className="activity-objectives"><article><strong>01</strong><span>Separate authoritative observations from model inputs.</span></article><article><strong>02</strong><span>Interpret a depth–damage relationship and its limits.</span></article><article><strong>03</strong><span>Run one transparent sensitivity comparison.</span></article><article><strong>04</strong><span>Write a defensible, uncertainty-aware brief.</span></article></div>
          <label className="activity-field">Team name<input value={activity.teamName} onChange={(e) => patch({ teamName: e.target.value })} placeholder="e.g., Lehigh Evidence Team" /></label>
          <fieldset className="activity-role-picker"><legend>Choose your primary role</legend><button className={activity.role === "data" ? "active" : ""} onClick={() => patch({ role: "data" })}><Database size={18} /><span><strong>Data steward</strong><small>Source, timestamp, provenance</small></span></button><button className={activity.role === "model" ? "active" : ""} onClick={() => patch({ role: "model" })}><FlaskConical size={18} /><span><strong>Modeler</strong><small>H–E–V–L logic and calculation</small></span></button><button className={activity.role === "communicator" ? "active" : ""} onClick={() => patch({ role: "communicator" })}><ClipboardCheck size={18} /><span><strong>Risk communicator</strong><small>Meaning, caveat, next action</small></span></button></fieldset>
          <div className="activity-honesty"><AlertTriangle size={16} /><p><strong>Classroom boundary:</strong> the selected event is real official metadata. The later portfolio and loss calculation are a separate labelled teaching model—not an estimate of that disaster.</p></div>
        </div>}

        {activity.activeStep === 1 && <div className="activity-content">
          <div className="activity-data-status"><span className={`status-dot ${eventsResponse?.data_status === "live" ? "live" : "warning"}`} /><div><strong>{eventsResponse?.data_status === "live" ? "Official event feed connected" : "Official event feed unavailable"}</strong><small>{eventsResponse ? `${eventsResponse.source_name} · retrieved ${formatUtc(eventsResponse.fetched_at)}` : "Connecting to the source adapter…"}</small></div><button onClick={onOpenLive}>Open Live <ArrowRight size={14} /></button></div>
          <label className="activity-field">Freeze one current event for this class<select value={event?.event_id ?? ""} onChange={(e) => chooseEvent(e.target.value)}><option value="">Select an official event…</option>{currentEvents.slice(0, 100).map((item) => <option value={item.event_id} key={item.event_id}>{item.name} · {item.country} · {item.alert_level}</option>)}</select></label>
          {!currentEvents.length && <div className="activity-blocked"><AlertTriangle size={18} /><span><strong>No current official event is available</strong>No substitute event or fabricated values are inserted. Continue the conceptual stations, or retry from Live.</span></div>}
          {event && <div className="activity-evidence-card"><div className="activity-evidence-title"><span className={`alert-chip ${event.alert_level}`}>{event.alert_level} alert</span><strong>{event.name}</strong><small>Session snapshot · source may publish later revisions</small></div><dl><div><dt>Hazard type</dt><dd>{event.event_type}</dd></div><div><dt>Reported area</dt><dd>{event.country}</dd></div><div><dt>Event period</dt><dd>{formatUtc(event.from_date)}</dd></div><div><dt>Official update</dt><dd>{formatUtc(event.modified_at)}</dd></div><div><dt>Event center</dt><dd>{event.center[1].toFixed(3)}, {event.center[0].toFixed(3)}</dd></div><div><dt>Geometry advertised</dt><dd>{event.geometry_url ? "Yes — inspect separately" : "Not in this record"}</dd></div></dl><div className="activity-evidence-actions"><button onClick={() => onInspectEvent(event)}><MapPinned size={15} /> Focus on map</button><a href={event.report_url} target="_blank" rel="noreferrer">Open official report <ExternalLink size={14} /></a></div></div>}
          <div className="activity-question"><span><CircleHelp size={15} /> Quick check</span><h3>What does RiskChain’s event marker represent?</h3>{[
            ["footprint", "The full physical impact footprint"],
            ["center", "The reported event center from the source record"],
            ["loss", "The location of the largest financial loss"],
          ].map(([value, label]) => <button key={value} className={activity.markerAnswer === value ? "selected" : ""} onClick={() => patch({ markerAnswer: value })}>{label}{activity.markerAnswer === value && value === "center" ? <CheckCircle2 size={15} /> : null}</button>)}{activity.markerAnswer && <p className={activity.markerAnswer === "center" ? "correct" : "incorrect"}>{activity.markerAnswer === "center" ? "Correct. A reported center is not an impact footprint or a loss surface." : "Try again: the live feed does not provide asset-level loss at the marker."}</p>}</div>
        </div>}

        {activity.activeStep === 2 && <div className="activity-content">
          <p className="activity-lead">A map becomes a model input only when its meaning, units, resolution, time, and uncertainty are known. Audit the selected event layer before asking for damage.</p>
          <div className="readiness-ladder"><article className="ready"><span>1</span><div><strong>Event metadata</strong><p>{event ? `${event.name} · ${event.source} · ${formatUtc(event.modified_at)}` : "Not frozen"}</p></div><b>{event ? "AVAILABLE" : "MISSING"}</b></article><article className={event?.geometry_url ? "partial" : "blocked"}><span>2</span><div><strong>Hazard intensity at assets</strong><p>An event center or alert level is not flood depth, MMI, wind speed, or burn probability at each asset.</p></div><b>NOT ESTABLISHED</b></article><article className="blocked"><span>3</span><div><strong>Exposure inventory</strong><p>No buildings, values, occupants, or infrastructure are attached to the official event record.</p></div><b>MISSING</b></article><article className="blocked"><span>4</span><div><strong>Compatible vulnerability</strong><p>A reviewed function must match the hazard intensity, geography, and asset class.</p></div><b>MISSING</b></article><article className="blocked"><span>5</span><div><strong>Defensible live-event loss</strong><p>Blocked until compatible hazard, exposure, and vulnerability inputs exist.</p></div><b>DO NOT CALCULATE</b></article></div>
          <label className="activity-field">What one dataset would you request next?<textarea value={activity.nextData} onChange={(e) => patch({ nextData: e.target.value })} placeholder="Name the layer, unit, resolution, date, and why it is needed…" /></label>
          <div className="activity-concept"><ShieldCheck size={18} /><p><strong>Core idea:</strong> event magnitude or alert level describes the event. A CAT engine needs hazard intensity at exposed locations. For earthquakes, for example, USGS ShakeMap maps spatial ground motion and shaking intensity; magnitude alone is not asset-level shaking.</p><a href="https://earthquake.usgs.gov/data/shakemap/" target="_blank" rel="noreferrer">USGS ShakeMap <ExternalLink size={13} /></a></div>
        </div>}

        {activity.activeStep === 3 && <div className="activity-content">
          <div className="cat-chain-strip"><span><b>E</b> Event</span><ArrowRight size={16} /><span><b>H</b> Hazard</span><ArrowRight size={16} /><span><b>E</b> Exposure</span><ArrowRight size={16} /><span><b>V</b> Vulnerability</span><ArrowRight size={16} /><span><b>L</b> Loss</span></div>
          <p className="activity-lead">Classify each statement. The four model components are related, but they are not interchangeable.</p>
          <div className="chain-matcher">{CHAIN_PROMPTS.map((prompt, index) => <article key={prompt.id}><span>{String(index + 1).padStart(2, "0")}</span><p>{prompt.text}</p><select aria-label={`Classify ${prompt.text}`} value={activity.chainAnswers[prompt.id] ?? ""} onChange={(e) => patch({ chainAnswers: { ...activity.chainAnswers, [prompt.id]: e.target.value } })}><option value="">Choose…</option><option value="hazard">Hazard</option><option value="exposure">Exposure</option><option value="vulnerability">Vulnerability</option><option value="loss">Loss</option></select>{activity.chainAnswers[prompt.id] && <i className={activity.chainAnswers[prompt.id] === prompt.answer ? "correct" : "incorrect"}>{activity.chainAnswers[prompt.id] === prompt.answer ? <Check size={14} /> : "×"}</i>}</article>)}</div>
          <div className={`chain-score ${chainScore === 4 ? "complete" : ""}`}><strong>{chainScore}/4</strong><span>{chainScore === 4 ? "CAT chain assembled. You are ready to inspect a model component." : "Keep testing the boundaries between components."}</span></div>
          <button className="activity-inline-link" onClick={() => onOpenLesson("ehevl-framework")}><BookOpenCheck size={15} /> Open the full CAT framework lesson</button>
        </div>}

        {activity.activeStep === 4 && <div className="activity-content">
          <div className="activity-split-heading"><div><span className="model-tag">DEMO · APPROVED EXPERIMENTAL</span><h3>How vulnerability translates intensity into expected damage</h3></div><label>Asset class<select value={selectedCurve?.function_id ?? ""} onChange={(e) => patch({ curveId: e.target.value })}>{curves.map((curve) => <option value={curve.function_id} key={curve.function_id}>{curve.asset_class}</option>)}</select></label></div>
          <div className="activity-honesty"><AlertTriangle size={16} /><p>These curves come from the site’s governed demonstration registry. They are representative teaching curves—not values from the selected live event and not approved for production decisions.</p></div>
          <label className="activity-field activity-slider">Baseline flood depth: <strong>{activity.depthFt.toFixed(1)} ft</strong><input type="range" min={selectedCurve?.calibration_min ?? -2} max={selectedCurve?.calibration_max ?? 12} step="0.5" value={activity.depthFt} onChange={(e) => patch({ depthFt: Number(e.target.value) })} /></label>
          <label className="activity-field activity-slider">Comparison depth: <strong>{activity.comparisonDepthFt.toFixed(1)} ft</strong><input type="range" min={selectedCurve?.calibration_min ?? -2} max={selectedCurve?.calibration_max ?? 12} step="0.5" value={activity.comparisonDepthFt} onChange={(e) => patch({ comparisonDepthFt: Number(e.target.value) })} /></label>
          <CurvePlot curve={selectedCurve} intensity={activity.depthFt} comparisonIntensity={activity.comparisonDepthFt} />
          {selectedCurve && <div className="curve-readout"><article><span>Baseline mean damage ratio</span><strong>{baseRatio == null ? "Unavailable" : `${(baseRatio * 100).toFixed(1)}%`}</strong></article><article><span>Comparison mean damage ratio</span><strong>{comparisonRatio == null ? "Unavailable" : `${(comparisonRatio * 100).toFixed(1)}%`}</strong></article><article><span>Calibration range</span><strong>{selectedCurve.calibration_min}–{selectedCurve.calibration_max} {selectedCurve.intensity_measure.unit}</strong></article><article><span>Model version</span><strong>{selectedCurve.version}</strong></article></div>}
          <div className="activity-question compact"><span><CircleHelp size={15} /> Predict before interpreting</span><h3>If hazard intensity rises and exposure stays fixed, what should generally happen?</h3>{[["increase", "Expected damage generally increases"], ["same", "Expected damage must stay identical"], ["random", "The curve may return any value"]].map(([value, label]) => <button key={value} className={activity.prediction === value ? "selected" : ""} onClick={() => patch({ prediction: value })}>{label}</button>)}{activity.prediction && <p className={activity.prediction === "increase" ? "correct" : "incorrect"}>{activity.prediction === "increase" ? "Yes—within its stated applicability, this demonstration curve is monotonic." : "Review the curve direction and its calibration limits."}</p>}</div>
        </div>}

        {activity.activeStep === 5 && <div className="activity-content">
          <div className="activity-callout formula"><FlaskConical size={20} /><div><strong>Transparent teaching calculation</strong><code>training direct loss = student-assumed replacement value × demo mean damage ratio</code><p>Contents, business interruption, insurance terms, casualties, and indirect effects are excluded.</p></div></div>
          <label className="activity-field">Student-assumed replacement value (USD)<input type="number" min="0" step="10000" value={activity.replacementValue} onChange={(e) => patch({ replacementValue: e.target.value })} /></label>
          <div className="calculation-grid"><article><span>Assumed exposure</span><strong>{Number.isFinite(exposure) && exposure > 0 ? formatMoney(exposure) : "Incomplete"}</strong><small>User supplied · synthetic training asset</small></article><article><span>Baseline MDR</span><strong>{baseRatio == null ? "Unavailable" : `${(baseRatio * 100).toFixed(1)}%`}</strong><small>{selectedCurve?.version ?? "No curve"}</small></article><article className="result"><span>Training direct loss</span><strong>{formatMoney(baseLoss)}</strong><small>Modelled demo · not live-event loss</small></article></div>
          <div className="sensitivity-card"><div><span>ONE-FACTOR SENSITIVITY</span><h3>Change depth only: {activity.depthFt.toFixed(1)} → {activity.comparisonDepthFt.toFixed(1)} ft</h3></div><div className="sensitivity-values"><span><small>Baseline</small><strong>{formatMoney(baseLoss)}</strong></span><ArrowRight size={19} /><span><small>Comparison</small><strong>{formatMoney(comparisonLoss)}</strong></span><span className="delta"><small>Change</small><strong>{baseLoss != null && comparisonLoss != null ? formatMoney(comparisonLoss - baseLoss) : "Unavailable"}</strong></span></div><p>Hazard changed. Exposure and vulnerability function were held constant. This isolates one driver; it does not quantify total uncertainty.</p></div>
          <div className="activity-honesty severe"><ShieldCheck size={16} /><p><strong>Do not join the numbers:</strong> the official event in Station 2 and this teaching loss are intentionally separate. The result is not “what the event cost.”</p></div>
          <button className="activity-inline-link" onClick={onRunDemo}><FlaskConical size={15} /> Continue into the full labelled Bethlehem model demo</button>
        </div>}

        {activity.activeStep === 6 && <div className="activity-content">
          <p className="activity-lead">Write like a modeller: separate what the source reports, what the model suggests, and what is still unknown.</p>
          <div className="brief-builder"><label><span>1 · Official evidence</span><textarea value={activity.officialObservation} onChange={(e) => patch({ officialObservation: e.target.value })} placeholder="One fact from the official event record…" /></label><label><span>2 · Largest limitation</span><textarea value={activity.limitation} onChange={(e) => patch({ limitation: e.target.value })} placeholder="What missing or uncertain input most changes interpretation?" /></label><label><span>3 · Next action</span><textarea value={activity.nextAction} onChange={(e) => patch({ nextAction: e.target.value })} placeholder="What data, review, or model run should happen next?" /></label></div>
          <section className="generated-brief"><div><span>EVIDENCE BRIEF · AUTO-ASSEMBLED FROM YOUR WORKSHEET</span><button onClick={() => { void navigator.clipboard.writeText(evidenceBrief); setCopied(true); }}>{copied ? <Check size={14} /> : <ClipboardCheck size={14} />} {copied ? "Copied" : "Copy"}</button></div><p>{evidenceBrief}</p><button className="primary" onClick={downloadBrief}><Download size={15} /> Download brief</button></section>
          <div className="activity-question compact"><span><CircleHelp size={15} /> Exit ticket</span><h3>Is the training number a prediction of the selected live disaster’s loss?</h3>{[["no", "No — it is a classroom model under separate stated assumptions"], ["yes", "Yes — both appeared in the same activity"], ["alert", "Only when the alert level is red"]].map(([value, label]) => <button key={value} className={activity.exitAnswer === value ? "selected" : ""} onClick={() => patch({ exitAnswer: value })}>{label}</button>)}{activity.exitAnswer && <p className={activity.exitAnswer === "no" ? "correct" : "incorrect"}>{activity.exitAnswer === "no" ? "Correct. Co-location in an interface does not make datasets compatible." : "Revisit the disclosure above the calculation."}</p>}</div>
          <details className="activity-sources"><summary>Methods and teaching sources</summary>{SOURCE_LINKS.map((source) => <a key={source.href} href={source.href} target="_blank" rel="noreferrer"><span><strong>{source.label}</strong><small>{source.note}</small></span><ExternalLink size={14} /></a>)}</details>
        </div>}

        <footer className="activity-station-footer">
          <button disabled={activity.activeStep === 0} onClick={() => patch({ activeStep: activity.activeStep - 1 })}><ArrowLeft size={15} /> Previous</button>
          <span><TimerReset size={14} /> Suggested checkpoint: {STATIONS.slice(0, activity.activeStep + 1).reduce((sum, item) => sum + item.minutes, 0)} minutes</span>
          <button className={activity.completed.includes(activity.activeStep) ? "complete" : "primary"} onClick={completeAndNext}>{activity.completed.includes(activity.activeStep) ? <CheckCircle2 size={15} /> : null}{activity.activeStep === STATIONS.length - 1 ? "Mark complete" : "Complete & next"}<ArrowRight size={15} /></button>
        </footer>
      </article>
    </div>
  </section>;
}
