"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { CertaintyBadge, ConfidencePill, SeverityDot } from "@/components/common/Badges";
import { EvidenceTrailView } from "@/components/common/EvidenceTrailView";
import { WhatChangedPanel } from "./WhatChangedPanel";

const TABS = [
  "Overview",
  "Timeline",
  "What may happen next",
  "Infrastructure",
  "Evidence",
  "Historical analogs",
  "Actions",
  "Report",
] as const;
type Tab = (typeof TABS)[number];

export function IncidentRoomPanel({ incidentId }: { incidentId: string }) {
  const mode = useAppStore((s) => s.mode);
  const dataMode: "live" | "replay" = mode === "replay" ? "replay" : "live";
  const [tab, setTab] = useState<Tab>(mode === "forecast" ? "What may happen next" : "Overview");
  const setPanel = useAppStore((s) => s.setPanel);

  const { data: incident, isLoading } = useQuery({
    queryKey: ["incident", incidentId, dataMode],
    queryFn: () => api.getIncident(incidentId, dataMode),
  });

  if (isLoading) return <div className="p-4 text-sm text-foreground/60">Loading incident…</div>;
  if (!incident) return <div className="p-4 text-sm text-foreground/60">Incident not found.</div>;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4 pb-2">
        <div className="flex items-center gap-2">
          <SeverityDot value={incident.severity} label={incident.status} />
          {incident.is_demo && (
            <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-foreground/60">
              {dataMode === "replay" ? "Demo replay - not current conditions" : "Demo data"}
            </span>
          )}
        </div>
        <h2 className="mt-1 text-lg font-semibold leading-tight">{incident.title}</h2>
        <p className="mt-1 text-sm text-foreground/70">{incident.one_line_summary}</p>
        <div className="mt-1.5">
          <ConfidencePill value={incident.overall_confidence} />
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-border px-3 py-2">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={
              "rounded-full px-2.5 py-1 text-xs font-medium " +
              (tab === t ? "bg-accent text-white" : "border border-border hover:bg-surface-muted")
            }
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === "Overview" && (
          <div className="space-y-3">
            <p className="text-sm">{incident.description}</p>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Sources</h3>
              <ul className="mt-1 list-inside list-disc text-sm">
                {incident.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
            {incident.affected_population_estimate && (
              <p className="text-xs text-foreground/60">
                Estimated {incident.affected_population_estimate.toLocaleString()} people in the affected
                area. {incident.affected_population_note}
              </p>
            )}
            <WhatChangedPanel incidentId={incidentId} mode={dataMode} />
          </div>
        )}

        {tab === "Timeline" && <TimelineTab incident={incident} />}
        {tab === "What may happen next" && <ForecastTab incidentId={incidentId} mode={dataMode} />}
        {tab === "Infrastructure" && (
          <InfrastructureTab incidentId={incidentId} mode={dataMode} onSelectFacility={(id) => setPanel({ kind: "place", placeId: id })} />
        )}
        {tab === "Evidence" && <EvidenceTab incidentId={incidentId} mode={dataMode} />}
        {tab === "Historical analogs" && <AnalogsTab incidentId={incidentId} />}
        {tab === "Actions" && <ActionsTab incidentId={incidentId} />}
        {tab === "Report" && <ReportTab incidentId={incidentId} />}
      </div>
    </div>
  );
}

function TimelineTab({ incident }: { incident: NonNullable<Awaited<ReturnType<typeof api.getIncident>>> }) {
  return (
    <ol className="space-y-3 border-l-2 border-border pl-4">
      {incident.timeline.map((entry) => (
        <li key={entry.entry_id} className="relative">
          <span
            className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-accent"
            aria-hidden
          />
          <div className="flex items-center gap-2 text-xs text-foreground/50">
            <time dateTime={entry.at}>{new Date(entry.at).toLocaleString()}</time>
            {entry.is_first_detection && <span className="text-accent">First detection</span>}
            {entry.is_peak && <span className="text-status-severe">Peak</span>}
            {entry.is_recovery && <span className="text-status-normal">Recovery</span>}
          </div>
          <p className="text-sm font-medium">{entry.label}</p>
          <p className="text-sm text-foreground/70">{entry.detail}</p>
          <CertaintyBadge value={entry.certainty_class} className="mt-1" />
        </li>
      ))}
    </ol>
  );
}

function ForecastTab({ incidentId, mode }: { incidentId: string; mode: "live" | "replay" }) {
  const { data, isLoading } = useQuery({
    queryKey: ["forecast", incidentId, mode],
    queryFn: () => api.getIncidentForecast(incidentId, mode),
  });
  if (isLoading) return <p className="text-sm text-foreground/60">Loading…</p>;
  if (!data) return null;
  return (
    <div className="space-y-3">
      <p className="text-xs text-foreground/60">{data.disclaimer}</p>
      <ol className="space-y-3">
        {data.steps.map((step) => (
          <li key={step.step_id}>
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">
                {step.order}. {step.statement}
              </p>
              <ConfidencePill value={step.confidence} />
            </div>
            <p className="text-xs text-foreground/50">{step.time_window.label}</p>
            <div className="mt-1">
              <EvidenceTrailView trail={step.evidence_trail} />
            </div>
          </li>
        ))}
      </ol>
      {data.steps.length === 0 && (
        <p className="text-sm text-foreground/60">No downstream impact steps are currently supported by the evidence.</p>
      )}
    </div>
  );
}

function InfrastructureTab({
  incidentId,
  mode,
  onSelectFacility,
}: {
  incidentId: string;
  mode: "live" | "replay";
  onSelectFacility: (facilityId: string) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["cascade", incidentId, mode],
    queryFn: () => api.getIncidentImpacts(incidentId, mode),
  });
  if (isLoading) return <p className="text-sm text-foreground/60">Loading…</p>;
  if (!data) return null;
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Living cascade</h3>
      <ul className="space-y-1.5">
        {data.nodes
          .filter((n) => n.hops_from_hazard !== null && n.hops_from_hazard !== undefined)
          .sort((a, b) => (a.hops_from_hazard ?? 0) - (b.hops_from_hazard ?? 0))
          .map((n) => (
            <li key={n.facility_id} className="flex items-center justify-between rounded-md border border-border p-2 text-sm">
              <button type="button" onClick={() => onSelectFacility(n.facility_id)} className="text-left hover:underline">
                <span className="font-medium">{n.name}</span>
                <span className="ml-2 text-xs text-foreground/50">
                  {n.directly_exposed ? "Directly exposed" : `${n.hops_from_hazard} step(s) away`}
                </span>
              </button>
              {n.estimated_minutes_to_consequence != null && (
                <span className="text-xs text-foreground/50">~{Math.round(n.estimated_minutes_to_consequence)} min</span>
              )}
            </li>
          ))}
      </ul>
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Assumptions</h3>
        <ul className="mt-1 list-inside list-disc text-xs text-foreground/60">
          {data.assumptions.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function EvidenceTab({ incidentId, mode }: { incidentId: string; mode: "live" | "replay" }) {
  const { data, isLoading } = useQuery({
    queryKey: ["evidence", incidentId, mode],
    queryFn: () => api.getIncidentEvidence(incidentId, mode),
  });
  if (isLoading) return <p className="text-sm text-foreground/60">Loading…</p>;
  return (
    <div className="space-y-3">
      {(data ?? []).map((trail, i) => (
        <EvidenceTrailView key={i} trail={trail} />
      ))}
    </div>
  );
}

function AnalogsTab({ incidentId }: { incidentId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["analogs", incidentId],
    queryFn: () => api.getAnalogs(incidentId),
  });
  if (isLoading) return <p className="text-sm text-foreground/60">Loading…</p>;
  return (
    <div className="space-y-3">
      <p className="text-xs text-foreground/60">
        Similarity does not prove the outcome will repeat - see &ldquo;why this may not repeat&rdquo; for each.
      </p>
      {(data ?? []).map((a) => (
        <div key={a.analog_id} className="rounded-md border border-border p-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">{a.event_name}</p>
            <span className="text-xs text-foreground/50">{Math.round(a.similarity_score * 100)}% similar</span>
          </div>
          <p className="mt-1 text-sm text-foreground/70">{a.what_happened_next}</p>
          <ul className="mt-1 list-inside list-disc text-xs text-foreground/50">
            {a.why_it_may_not_repeat.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function ActionsTab({ incidentId }: { incidentId: string }) {
  const setMode = useAppStore((s) => s.setMode);
  return (
    <div className="space-y-2">
      <p className="text-sm text-foreground/70">
        Test a counterfactual decision - like closing a crossing early or repositioning an ambulance - in
        Scenario Lab, using this incident&rsquo;s infrastructure graph.
      </p>
      <button
        type="button"
        onClick={() => setMode("scenario-lab")}
        className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:opacity-90"
      >
        Open Scenario Lab for {incidentId}
      </button>
    </div>
  );
}

function ReportTab({ incidentId }: { incidentId: string }) {
  const mode = useAppStore((s) => s.mode);
  const dataMode: "live" | "replay" = mode === "replay" ? "replay" : "live";
  const { data: incident } = useQuery({
    queryKey: ["incident", incidentId, dataMode],
    queryFn: () => api.getIncident(incidentId, dataMode),
  });

  function handleExport() {
    if (!incident) return;
    const lines = [
      `EarthPulse Incident Brief`,
      `${incident.title}`,
      `Generated: ${new Date().toISOString()}`,
      ``,
      `Summary: ${incident.one_line_summary}`,
      `Status: ${incident.status} | Severity: ${incident.severity} | Confidence: ${incident.overall_confidence}`,
      ``,
      `Description:`,
      incident.description,
      ``,
      `Timeline:`,
      ...incident.timeline.map((t) => `- ${new Date(t.at).toLocaleString()} [${t.certainty_class}] ${t.label}: ${t.detail}`),
      ``,
      `Sources: ${incident.sources.join(", ")}`,
      ``,
      `EarthPulse supports situational awareness and research. It does not replace official emergency alerts, evacuation orders, or professional engineering decisions.`,
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${incidentId}-briefing.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-foreground/70">Export a plain-language briefing of this incident.</p>
      <button
        type="button"
        onClick={handleExport}
        className="rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-surface-muted"
      >
        Download briefing (.txt)
      </button>
    </div>
  );
}
