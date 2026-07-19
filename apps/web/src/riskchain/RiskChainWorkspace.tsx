"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, BookOpen, Bot, CheckCircle2, ChevronDown, Database,
  Download, ExternalLink, FileText, FlaskConical, Globe2, GraduationCap, Layers,
  Menu, Moon, Play, Radio, Search, ShieldCheck, SlidersHorizontal, Sun, X,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type {
  CatModelRunResult, DataCoverageItem, GlobalEventsResponse,
  LearnLesson, LearnLessonSummary, ResearchSearchResponse, RoadmapResponse,
} from "@/lib/types";
import { RiskMap, type MapSelection } from "./RiskMap";

type View = "explore" | "model" | "live" | "learn" | "research";
type Panel = "none" | "layers" | "sources" | "results" | "ai" | "roadmap";

const NAV: { id: View; label: string; icon: typeof Globe2 }[] = [
  { id: "explore", label: "Explore", icon: Globe2 },
  { id: "model", label: "Model", icon: FlaskConical },
  { id: "live", label: "Live", icon: Radio },
  { id: "learn", label: "Learn CAT", icon: GraduationCap },
  { id: "research", label: "Research", icon: BookOpen },
];

const HAZARDS = [
  { id: "flood", label: "Flood", color: "#1a73e8", available: true },
  { id: "wildfire", label: "Wildfire", color: "#f4511e", available: false },
  { id: "earthquake", label: "Earthquake", color: "#7e57c2", available: false },
  { id: "wind", label: "Severe wind", color: "#d93025", available: false },
];

function money(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function dateTime(value?: string | null) {
  if (!value) return "Not reported";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}

function StatusBadge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "live" | "demo" | "warning" | "neutral" }) {
  return <span className={`status-badge ${tone}`}>{children}</span>;
}

export function RiskChainWorkspace() {
  const [view, setView] = useState<View>("explore");
  const [panel, setPanel] = useState<Panel>("none");
  const [operationsMode, setOperationsMode] = useState(false);
  const [professionalMode, setProfessionalMode] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [scope, setScope] = useState<"global" | "local">("global");
  const [hazard, setHazard] = useState("flood");
  const [provider, setProvider] = useState<"google" | "open">("open");
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const [eventsResponse, setEventsResponse] = useState<GlobalEventsResponse | null>(null);
  const [coverage, setCoverage] = useState<DataCoverageItem[]>([]);
  const [lessons, setLessons] = useState<LearnLessonSummary[]>([]);
  const [lesson, setLesson] = useState<LearnLesson | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [run, setRun] = useState<CatModelRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [deductible, setDeductible] = useState(100000);
  const [limit, setLimit] = useState(5000000);
  const [researchQuery, setResearchQuery] = useState("validated flood depth-damage functions for commercial masonry buildings");
  const [research, setResearch] = useState<ResearchSearchResponse | null>(null);
  const [aiQuestion, setAiQuestion] = useState("Explain the largest uncertainty in this analysis.");
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);

  useEffect(() => {
    void Promise.allSettled([api.globalEvents(), api.catDataCoverage(), api.learnLessons(), api.roadmap()]).then((results) => {
      const [events, data, course, plan] = results;
      if (events.status === "fulfilled") setEventsResponse(events.value);
      if (data.status === "fulfilled") setCoverage(data.value);
      if (course.status === "fulfilled") setLessons(course.value);
      if (plan.status === "fulfilled") setRoadmap(plan.value);
    });
  }, []);

  const events = useMemo(() => eventsResponse?.events ?? [], [eventsResponse]);
  const visibleEvents = useMemo(() => {
    if (hazard === "flood") return events.filter((event) => /^(fl|flood)$/i.test(event.event_type));
    if (hazard === "earthquake") return events.filter((event) => /^(eq|earthquake)$/i.test(event.event_type));
    if (hazard === "wildfire") return events.filter((event) => /^(wf|fire|wildfire)$/i.test(event.event_type));
    if (hazard === "wind") return events.filter((event) => /^(tc|cyclone|storm|wind)$/i.test(event.event_type));
    return events;
  }, [events, hazard]);

  const onProvider = useCallback((next: "google" | "open") => setProvider(next), []);
  const onSelect = useCallback((next: MapSelection) => setSelection(next), []);

  function chooseView(next: View) {
    setView(next);
    setMobileNav(false);
    setPanel("none");
    if (next === "model") setScope("local");
    if (next === "live" || next === "explore") setScope("global");
  }

  function searchLocation(event: FormEvent) {
    event.preventDefault();
    const normalized = query.trim().toLowerCase();
    if (!normalized) return;
    const match = events.find((item) => `${item.name} ${item.country} ${item.event_type}`.toLowerCase().includes(normalized));
    if (match) {
      setSelection({ id: match.event_id, title: match.name, subtitle: `${match.event_type} · ${match.country}`, status: "Officially reported", source: match.source, center: match.center });
      setScope("global");
      return;
    }
    if (/bethlehem|lehigh|18015|40\.62/.test(normalized)) {
      setScope("local");
      setView("model");
      setSelection({ id: "bethlehem-demo", title: "Bethlehem, Pennsylvania", subtitle: "Flood demonstration area", status: "Demo", source: "RiskChain approved demonstration engine", center: [-75.3705, 40.6259] });
      return;
    }
    setNotice("No supported source-backed match was found. Try an active event or “Bethlehem, PA” for the labelled flood demonstration.");
  }

  async function runModel() {
    if (hazard !== "flood") {
      setNotice("This peril is not implemented in the validated MVP. RiskChain will not fabricate a result.");
      return;
    }
    setLoading(true);
    setNotice(null);
    try {
      const result = await api.runCatFloodModel({
        scenario_label: "100-year flood event — Bethlehem demonstration",
        deductible_usd: deductible,
        limit_usd: limit || null,
        coinsurance: 1,
        seed: 12345,
        iterations: 2000,
      });
      setRun(result);
      setPanel("results");
    } catch (error) {
      setNotice(error instanceof ApiError ? `Model service error (${error.status}). No result was invented.` : "The model service is unavailable. No result was invented.");
    } finally {
      setLoading(false);
    }
  }

  async function openLesson(id: string) {
    setLoading(true);
    try { setLesson(await api.learnLesson(id)); } catch { setNotice("Lesson detail is temporarily unavailable."); }
    finally { setLoading(false); }
  }

  async function searchResearch(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try { setResearch(await api.researchSearch(researchQuery, "flood")); }
    catch { setNotice("The governed research index is temporarily unavailable."); }
    finally { setLoading(false); }
  }

  async function askCopilot(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const answer = await api.queryCopilot(aiQuestion, { hazard, location_label: scope === "local" ? "Bethlehem / Lehigh Valley, PA" : selection?.title, run_id: run?.run_id, interface_mode: professionalMode ? "professional" : "guided" });
      setAiAnswer(`${answer.message}\n\nNumbers source: ${answer.numbers_source === "approved_tools" ? "approved calculation tools" : "no numeric claims"}.`);
    } catch { setAiAnswer("The grounded copilot is unavailable. It will not answer without the approved backend tools."); }
    finally { setLoading(false); }
  }

  function exportRun() {
    if (!run) return;
    const blob = new Blob([JSON.stringify(run, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${run.run_id}-manifest.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className={`riskchain-app ${operationsMode ? "operations" : ""}`}>
      <a href="#workspace" className="skip-link">Skip to map workspace</a>
      <header className="topbar">
        <button className="icon-button mobile-menu" onClick={() => setMobileNav((value) => !value)} aria-label="Open navigation"><Menu size={20} /></button>
        <button className="brand" onClick={() => chooseView("explore")} aria-label="RiskChain home">
          <span className="brand-glyph"><Activity size={19} /></span>
          <span>Risk<span>Chain</span></span>
          <small>CAT intelligence</small>
        </button>
        <form className="map-search" onSubmit={searchLocation}>
          <Search size={19} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a place, event, coordinates or ZIP" aria-label="Search location or event" />
          <button type="submit">Search</button>
        </form>
        <div className="top-actions">
          <button className="mode-button" onClick={() => setProfessionalMode((value) => !value)}><SlidersHorizontal size={17} /> {professionalMode ? "Professional" : "Guided"}</button>
          <button className="icon-button" onClick={() => setOperationsMode((value) => !value)} aria-label="Toggle operations mode">{operationsMode ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button className="primary compact" onClick={() => setPanel("ai")}><Bot size={17} /> Ask AI</button>
        </div>
      </header>

      <nav className={`nav-tabs ${mobileNav ? "open" : ""}`} aria-label="Primary">
        {NAV.map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => chooseView(item.id)}><item.icon size={17} />{item.label}</button>)}
        <button onClick={() => setPanel("roadmap")}><FileText size={17} />Roadmap</button>
      </nav>

      <section id="workspace" className="workspace">
        <RiskMap events={scope === "global" ? visibleEvents : []} scope={scope} operationsMode={operationsMode} hazard={hazard} onSelect={onSelect} onProvider={onProvider} />

        <div className="map-toolbar">
          <button className={panel === "layers" ? "active" : ""} onClick={() => setPanel(panel === "layers" ? "none" : "layers")}><Layers size={17} /> Layers <ChevronDown size={14} /></button>
          <button onClick={() => setScope(scope === "global" ? "local" : "global")}><Globe2 size={17} /> {scope === "global" ? "Global" : "Bethlehem"}</button>
          <button onClick={() => setPanel("sources")}><Database size={17} /> Sources</button>
        </div>

        <div className="map-trust-strip">
          <StatusBadge tone={eventsResponse?.data_status === "live" ? "live" : "warning"}>{eventsResponse?.data_status === "live" ? "Live GDACS" : "Source status pending"}</StatusBadge>
          <span>{provider === "google" ? "Google Maps Platform" : "Open neutral basemap"}</span>
          <span>Hazard ≠ impact</span>
        </div>

        {view === "explore" && <section className="floating-card intro-card">
          <StatusBadge tone="live">Map-first workspace</StatusBadge>
          <h1>Understand catastrophe risk, one place at a time.</h1>
          <p>Explore official global events or move into a transparent, clearly labelled flood model for Bethlehem.</p>
          <div className="intro-actions"><button className="primary" onClick={() => chooseView("live")}><Radio size={17} /> See live events</button><button onClick={() => chooseView("model")}><FlaskConical size={17} /> Build a scenario</button></div>
          <div className="trust-row"><span><ShieldCheck size={15} /> Sources visible</span><span><CheckCircle2 size={15} /> Ranges, not false precision</span></div>
        </section>}

        {view === "model" && <section className="floating-card scenario-card">
          <div className="card-heading"><div><span className="eyebrow">Guided model</span><h2>Build a risk scenario</h2></div><StatusBadge tone="demo">Demo</StatusBadge></div>
          <label>1 · Location<input value="Bethlehem / Lehigh Valley, PA" readOnly /></label>
          <fieldset><legend>2 · Hazard</legend><div className="hazard-grid">{HAZARDS.map((item) => <button key={item.id} className={hazard === item.id ? "selected" : ""} onClick={() => setHazard(item.id)} style={{ "--hazard": item.color } as React.CSSProperties}><i />{item.label}{!item.available && <small>Planned</small>}</button>)}</div></fieldset>
          <label>3 · Scenario<select><option>100-year flood event (demo)</option><option disabled>Historical event — unavailable</option><option disabled>Live event — unavailable</option></select></label>
          {professionalMode && <div className="pro-fields"><label>Deductible (USD)<input type="number" min="0" value={deductible} onChange={(event) => setDeductible(Number(event.target.value))} /></label><label>Limit (USD)<input type="number" min="0" value={limit} onChange={(event) => setLimit(Number(event.target.value))} /></label></div>}
          <div className="assumption-note"><AlertTriangle size={16} /><span><strong>Before you run</strong> Hazard depths and exposure are approved demonstration inputs, not observed current conditions.</span></div>
          <button className="primary run-button" disabled={loading || hazard !== "flood"} onClick={runModel}><Play size={17} fill="currentColor" /> {loading ? "Running approved engine…" : hazard === "flood" ? "Run risk analysis" : "Model unavailable"}</button>
        </section>}

        {view === "live" && <section className="floating-card live-card">
          <div className="card-heading"><div><span className="eyebrow">Official event picture</span><h2>Live global events</h2></div><StatusBadge tone={eventsResponse?.data_status === "live" ? "live" : "warning"}>{eventsResponse?.data_status ?? "loading"}</StatusBadge></div>
          <div className="live-stats"><div><strong>{eventsResponse?.counts.total ?? "—"}</strong><span>events</span></div><div><strong>{eventsResponse?.counts.red ?? "—"}</strong><span>red</span></div><div><strong>{eventsResponse?.counts.orange ?? "—"}</strong><span>orange</span></div></div>
          <div className="hazard-filter">{HAZARDS.map((item) => <button key={item.id} className={hazard === item.id ? "active" : ""} onClick={() => setHazard(item.id)}>{item.label}</button>)}</div>
          <div className="event-list">{visibleEvents.slice(0, 6).map((event) => <button key={event.event_id} onClick={() => setSelection({ id: event.event_id, title: event.name, subtitle: `${event.event_type} · ${event.country}`, status: "Officially reported", source: event.source, center: event.center })}><i className={event.alert_level} /><span><strong>{event.name}</strong><small>{event.country} · updated {dateTime(event.modified_at)}</small></span><ExternalLink size={15} /></button>)}</div>
          <p className="microcopy">GDACS information supports awareness and coordination; follow national and local authorities for warnings.</p>
        </section>}

        {view === "learn" && <section className="floating-card content-card learn-card">
          <div className="card-heading"><div><span className="eyebrow">Learn while modelling</span><h2>{lesson?.title ?? "Learn CAT"}</h2></div>{lesson && <button className="icon-button" onClick={() => setLesson(null)} aria-label="Close lesson"><X size={17} /></button>}</div>
          {lesson ? <article className="lesson-detail"><p className="lead">{lesson.one_sentence}</p><h3>Plain language</h3><p>{lesson.plain_language}</p><h3>Technical definition</h3><p>{lesson.technical_definition}</p>{lesson.formula && <code>{lesson.formula}</code>}<div className="learning-warning"><strong>Common mistake</strong>{lesson.common_mistake}</div><h3>Knowledge check</h3><p>{lesson.knowledge_check.question}</p>{lesson.knowledge_check.options.map((option, index) => <div className="answer-option" key={option}>{String.fromCharCode(65 + index)} · {option}</div>)}</article> : <div className="lesson-list">{lessons.map((item) => <button key={item.lesson_id} onClick={() => void openLesson(item.lesson_id)}><span>{String(item.order).padStart(2, "0")}</span><div><strong>{item.title}</strong><small>{item.one_sentence}</small></div></button>)}</div>}
        </section>}

        {view === "research" && <section className="floating-card content-card research-card">
          <span className="eyebrow">Governed formula discovery</span><h2>Research methods, not mystery formulas.</h2><p>Search a curated index of real technical references. A result can enter the model only after independent implementation, testing, and human review.</p>
          <form className="research-search" onSubmit={searchResearch}><input value={researchQuery} onChange={(event) => setResearchQuery(event.target.value)} /><button className="primary" type="submit"><Search size={16} /> Search</button></form>
          {research && <><div className="source-state-row">{research.source_status.map((source) => <StatusBadge key={source.source} tone={source.status === "unavailable" ? "warning" : "neutral"}>{source.source}: {source.status}</StatusBadge>)}</div><div className="paper-list">{research.results.map((paper) => <article key={paper.paper_id}><StatusBadge>{paper.human_review_status}</StatusBadge><h3>{paper.title}</h3><p>{paper.publisher}{paper.year ? ` · ${paper.year}` : ""}</p><small>{paper.peer_review_status} · relevance {(paper.relevance * 100).toFixed(0)}%</small></article>)}</div><p className="microcopy">{research.notice}</p></>}
        </section>}

        {panel === "layers" && <aside className="floating-card compact-panel layers-panel"><div className="card-heading"><h2>Map layers</h2><button className="icon-button" onClick={() => setPanel("none")}><X size={16} /></button></div>{HAZARDS.map((item) => <button key={item.id} className="layer-row" onClick={() => setHazard(item.id)}><i style={{ background: item.color }} /><span><strong>{item.label}</strong><small>{item.available ? (scope === "local" ? "Demo model layer" : "Official event locations") : "Event locations only; loss model unavailable"}</small></span><input aria-label={`Toggle ${item.label}`} type="checkbox" readOnly checked={hazard === item.id} /></button>)}</aside>}

        {selection && <aside className="floating-card selection-card"><button className="card-close" onClick={() => setSelection(null)} aria-label="Close selection"><X size={17} /></button><StatusBadge tone={selection.status === "Demo" ? "demo" : "live"}>{selection.status}</StatusBadge><h2>{selection.title}</h2><p>{selection.subtitle}</p><dl><div><dt>Source</dt><dd>{selection.source}</dd></div><div><dt>Coordinates</dt><dd>{selection.center[1].toFixed(3)}, {selection.center[0].toFixed(3)}</dd></div><div><dt>Interpretation</dt><dd>{selection.status === "Demo" ? "Scenario input; not a current observation" : "Reported event location; not an impact footprint"}</dd></div></dl>{selection.status === "Demo" ? <button className="primary" onClick={() => chooseView("model")}>Open model</button> : <a className="secondary-link" href={events.find((item) => item.event_id === selection.id)?.report_url} target="_blank" rel="noreferrer">Open official report <ExternalLink size={15} /></a>}</aside>}

        {panel === "sources" && <aside className="drawer"><div className="drawer-head"><div><span className="eyebrow">Data quality</span><h2>Source & coverage</h2></div><button className="icon-button" onClick={() => setPanel("none")}><X size={18} /></button></div><p className="drawer-intro">Every layer states whether it is live, modelled, inferred, demo, or unavailable. Different resolutions are never blended silently.</p><div className="coverage-list">{coverage.map((item) => <article key={item.layer_id}><StatusBadge tone={item.availability === "available_live" ? "live" : item.availability === "available_demo" ? "demo" : "warning"}>{item.availability.replaceAll("_", " ")}</StatusBadge><h3>{item.label}</h3><p>{item.source}</p><dl><div><dt>Use</dt><dd>{item.use_in_run}</dd></div><div><dt>Resolution</dt><dd>{item.geographic_resolution}</dd></div><div><dt>Origin</dt><dd>{item.attribute_origin.replaceAll("_", " ")}</dd></div></dl>{item.limitations[0] && <small>{item.limitations[0]}</small>}</article>)}</div></aside>}

        {panel === "results" && run && <aside className="results-drawer"><div className="drawer-head"><div><StatusBadge tone="demo">Modelled · demo</StatusBadge><h2>{run.scenario_label}</h2><p>{run.region_label}</p></div><button className="icon-button" onClick={() => setPanel("none")}><X size={18} /></button></div><div className="result-hero"><span>Modelled ground-up loss range</span><strong>{money(run.ground_up_distribution.range_low_usd)}–{money(run.ground_up_distribution.range_high_usd)}</strong><small>Median {money(run.ground_up_distribution.p50_usd)} · {run.ground_up_distribution.samples.toLocaleString()} samples</small></div><div className="result-grid"><div><span>P10</span><strong>{money(run.ground_up_distribution.p10_usd)}</strong></div><div><span>P50</span><strong>{money(run.ground_up_distribution.p50_usd)}</strong></div><div><span>P90</span><strong>{money(run.ground_up_distribution.p90_usd)}</strong></div><div><span>Assets</span><strong>{run.asset_count}</strong></div></div><section className="confidence-card"><ShieldCheck size={20} /><div><strong>{run.confidence.band} confidence</strong><p>Largest uncertainty: {run.confidence.largest_uncertainty}</p></div></section><h3>Automatic model review</h3><div className="audit-list">{run.audit_findings.slice(0, 4).map((finding) => <article key={finding.code}><AlertTriangle size={17} /><div><strong>{finding.title}</strong><p>{finding.detail}</p><small>{finding.recommendation}</small></div></article>)}</div><div className="drawer-actions"><button className="primary" onClick={exportRun}><Download size={16} /> Download manifest</button><button onClick={() => setPanel("ai")}><Bot size={16} /> Explain result</button></div><p className="microcopy">This is a research demonstration. It is not an underwriting quote, official flood map, or emergency warning.</p></aside>}

        {panel === "ai" && <aside className="ai-drawer"><div className="drawer-head"><div><span className="eyebrow">Approved tools only</span><h2>RiskChain Copilot</h2></div><button className="icon-button" onClick={() => setPanel("none")}><X size={18} /></button></div><div className="ai-guardrail"><ShieldCheck size={18} /><span>The AI interprets and explains. Approved backend engines calculate every number.</span></div>{aiAnswer && <div className="ai-answer">{aiAnswer}</div>}<form onSubmit={askCopilot}><textarea value={aiQuestion} onChange={(event) => setAiQuestion(event.target.value)} rows={4} /><button className="primary" type="submit" disabled={loading}><Bot size={16} /> {loading ? "Checking tools…" : "Ask grounded copilot"}</button></form><div className="prompt-chips">{["What data are missing?", "Audit this model run", "Explain AEP vs OEP"].map((prompt) => <button key={prompt} onClick={() => setAiQuestion(prompt)}>{prompt}</button>)}</div></aside>}

        {panel === "roadmap" && <aside className="drawer"><div className="drawer-head"><div><span className="eyebrow">Honest delivery status</span><h2>Product roadmap</h2></div><button className="icon-button" onClick={() => setPanel("none")}><X size={18} /></button></div><div className="roadmap-list">{roadmap?.milestones.map((item) => <article key={`${item.stage}-${item.name}`}><StatusBadge tone={item.status === "done" ? "live" : "neutral"}>{item.status.replaceAll("_", " ")}</StatusBadge><span className="budget">{item.budget_band} effort · {item.timeline}</span><h3>{item.name}</h3><p>{item.acceptance_gate}</p><small>Owner: {item.owner_role}</small></article>)}</div><p className="microcopy">{roadmap?.notice}</p></aside>}
      </section>

      {notice && <div className="toast" role="alert"><AlertTriangle size={18} /><span>{notice}</span><button onClick={() => setNotice(null)}><X size={16} /></button></div>}
    </main>
  );
}
