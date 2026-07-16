"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BrainCircuit, Check, Copy, Download, ExternalLink, Globe2, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { GlobalEvent } from "@/lib/types";

const HAZARDS = ["ALL", "EQ", "TC", "FL", "WF", "VO", "DR"] as const;
const TYPE_LABELS: Record<string, string> = {
  EQ: "Earthquake", TC: "Cyclone", FL: "Flood", WF: "Wildfire", VO: "Volcano", DR: "Drought",
};

export function GlobalEventsPanel() {
  const [hazard, setHazard] = useState<(typeof HAZARDS)[number]>("ALL");
  const [copied, setCopied] = useState(false);
  const flyTo = useAppStore((state) => state.flyTo);
  const setMapScope = useAppStore((state) => state.setMapScope);
  const setPanel = useAppStore((state) => state.setPanel);
  const time = useAppStore((state) => state.time);
  const setOffsetMinutes = useAppStore((state) => state.setOffsetMinutes);
  const query = useQuery({
    queryKey: ["global-events"],
    queryFn: api.globalEvents,
    staleTime: 300_000,
    refetchInterval: 300_000,
  });
  const horizonMinutes = Math.max(0, time.offsetMinutes);
  const outlook = useQuery({
    queryKey: ["global-outlook", horizonMinutes],
    queryFn: () => api.globalOutlook(horizonMinutes),
    staleTime: 300_000,
  });
  const watchByEvent = useMemo(() => new Map((outlook.data?.items ?? []).map((item) => [item.event_id, item])), [outlook.data?.items]);

  const events = useMemo(() => {
    const filtered = (query.data?.events ?? []).filter((event) => hazard === "ALL" || event.event_type === hazard);
    const rank: Record<string, number> = { red: 0, orange: 1, green: 2 };
    return [...filtered].sort((a, b) => (rank[a.alert_level] ?? 3) - (rank[b.alert_level] ?? 3) || Date.parse(b.modified_at) - Date.parse(a.modified_at));
  }, [hazard, query.data?.events]);

  const focus = (event: GlobalEvent) => {
    setMapScope("global");
    flyTo(event.center, event.event_type === "TC" || event.event_type === "FL" ? 4 : 5);
  };

  const download = () => {
    if (!query.data) return;
    const collection = {
      type: "FeatureCollection",
      attribution: query.data.attribution,
      generated_at: new Date().toISOString(),
      features: events.map((event) => ({
        type: "Feature",
        id: event.event_id,
        properties: { ...event, center: undefined },
        geometry: { type: "Point", coordinates: event.center },
      })),
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(collection, null, 2)], { type: "application/geo+json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `earthpulse-gdacs-events-${new Date().toISOString().slice(0, 10)}.geojson`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const copyBrief = async () => {
    if (!query.data) return;
    const top = events.slice(0, 5).map((event) => `• ${event.alert_level.toUpperCase()} ${TYPE_LABELS[event.event_type] ?? event.event_type}: ${event.name} — ${event.severity_text}`).join("\n");
    const text = [
      "EARTHPULSE GLOBAL OPERATING BRIEF",
      `As of ${formatUtc(query.data.source_updated_at ?? query.data.fetched_at)}`,
      `GDACS events: ${query.data.counts.total} total · ${query.data.counts.red} red · ${query.data.counts.orange} orange`,
      "",
      top || "No events match the selected filter.",
      "",
      query.data.notice,
      `Source: ${query.data.attribution}`,
    ].join("\n");
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="global-events-panel">
      <header className="global-events-header">
        <div className="global-title-row">
          <span className="global-icon"><Globe2 size={18} /></span>
          <div><span className="panel-kicker">GLOBAL OPERATING PICTURE</span><h1>Active disaster events</h1></div>
          <span className={`feed-state ${query.data?.data_status ?? "unavailable"}`}><i />{query.data?.data_status ?? "checking"}</span>
        </div>
        <p>Official multi-hazard event metadata from the UN–European Commission GDACS feed. EarthPulse keeps source alert levels intact.</p>
        <div className="global-freshness">
          <span><RefreshCw size={11} /> Updated {query.data?.source_updated_at ? ageLabel(query.data.source_updated_at) : "checking…"}</span>
          <span>UTC {query.data?.source_updated_at ? formatTime(query.data.source_updated_at) : "—"}</span>
          <span>{query.data?.standards.join(" · ") ?? "GeoJSON"}</span>
        </div>
      </header>

      {query.isLoading && <div className="global-loading"><span /><span /><span /> Contacting GDACS…</div>}
      {query.isError || query.data?.data_status === "unavailable" ? (
        <div className="global-unavailable"><ShieldAlert size={22} /><strong>Global feed unavailable</strong><p>{query.data?.error ?? "EarthPulse will not substitute synthetic global events."}</p><button type="button" onClick={() => query.refetch()}>Retry official feed</button></div>
      ) : query.data && (
        <>
          <section className="alert-counts" aria-label="GDACS alert counts">
            <div className="red"><span>RED</span><strong>{query.data.counts.red}</strong><small>potentially severe</small></div>
            <div className="orange"><span>ORANGE</span><strong>{query.data.counts.orange}</strong><small>significant</small></div>
            <div className="green"><span>GREEN</span><strong>{query.data.counts.green}</strong><small>information</small></div>
          </section>

          <section className="global-outlook-card" aria-label="EarthPulse global watch lens">
            <div className="global-outlook-heading">
              <span><BrainCircuit size={15} /></span>
              <div><span className="panel-kicker">EARTHPULSE AI WATCH LENS</span><strong>{outlook.data?.horizon_label ?? "Preparing outlook…"}</strong></div>
              <b>{outlook.data?.method ? "transparent" : "checking"}</b>
            </div>
            <input
              type="range"
              min={0}
              max={1440}
              step={15}
              value={horizonMinutes}
              onChange={(event) => setOffsetMinutes(Number(event.target.value))}
              className="global-outlook-range"
              aria-label="Global operating watch horizon, from now to 24 hours"
              aria-valuetext={outlook.data?.horizon_label ?? `Next ${horizonMinutes} minutes`}
            />
            <div className="global-outlook-labels"><span>NOW</span><span>+1H</span><span>+6H</span><span>+24H</span></div>
            <p>{outlook.data?.method_detail ?? "Loading the calculation basis…"}</p>
            <div className="global-outlook-actions">
              <span>{outlook.data?.items[0] ? `Top watch: ${outlook.data.items[0].priority_label} ${outlook.data.items[0].priority_score}/100` : "No watch score yet"}</span>
              <button type="button" onClick={() => setPanel({ kind: "assistant", question: `Give a global GDACS brief for a ${horizonMinutes}-minute operating window. Explain the watch score and its limits.` })}><Sparkles size={12} /> Ask grounded AI</button>
            </div>
          </section>

          <div className="global-actions">
            <button type="button" onClick={copyBrief}>{copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "Copied" : "Copy partner brief"}</button>
            <button type="button" onClick={download}><Download size={13} /> Download GeoJSON</button>
          </div>

          <div className="global-hazard-filters" aria-label="Filter global events">
            {HAZARDS.map((item) => <button key={item} type="button" className={hazard === item ? "is-active" : ""} onClick={() => setHazard(item)} aria-pressed={hazard === item}>{item === "ALL" ? "All" : TYPE_LABELS[item]}</button>)}
          </div>

          <section className="global-event-list" aria-label="Global event list">
            <div className="event-list-heading"><span>{events.length} EVENTS</span><span>ALERT · UPDATED UTC</span></div>
            {events.slice(0, 24).map((event) => (
              <article className={`global-event-card ${event.alert_level}`} key={event.event_id}>
                <button type="button" className="event-focus" onClick={() => focus(event)} aria-label={`Focus ${event.name} on map`}>
                  <span className="event-type">{event.event_type}</span>
                  <span className="event-copy"><strong>{event.name}</strong><small>{event.severity_text}</small><em>{event.country} · {event.source}</em></span>
                  <span className="event-status"><b>{event.alert_level}</b><small>{watchByEvent.get(event.event_id)?.priority_label ?? ageLabel(event.modified_at)}</small><em>{watchByEvent.get(event.event_id) ? `${watchByEvent.get(event.event_id)?.priority_score}/100 watch` : ageLabel(event.modified_at)}</em></span>
                </button>
                <a href={event.report_url} target="_blank" rel="noreferrer" aria-label={`Open official GDACS report for ${event.name}`}><ExternalLink size={12} /> Official report</a>
              </article>
            ))}
          </section>

          <footer className="global-source-note">
            <p>{query.data.notice}</p>
            <a href={query.data.source_url} target="_blank" rel="noreferrer">Source: {query.data.attribution} <ExternalLink size={11} /></a>
          </footer>
        </>
      )}
    </div>
  );
}

function formatUtc(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }).format(new Date(value));
}

function ageLabel(value: string) {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(value)) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
