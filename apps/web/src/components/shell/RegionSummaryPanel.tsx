"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { DisasterHeartbeat } from "@/components/common/DisasterHeartbeat";

export function RegionSummaryPanel() {
  const { data: summary, isLoading } = useQuery({ queryKey: ["live-summary"], queryFn: api.liveSummary });
  const setPanel = useAppStore((s) => s.setPanel);
  const savedPlaces = useAppStore((s) => s.savedPlaces);
  const flyTo = useAppStore((s) => s.flyTo);
  const [question, setQuestion] = useState("");

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground/50">Regional summary</h2>
        {isLoading && <p className="mt-2 text-sm text-foreground/60">Loading…</p>}
        {summary && (
          <>
            <p className="mt-1 text-base font-medium">{summary.region_label}</p>
            <p className="mt-1 text-sm text-foreground/80">{summary.headline}</p>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-md border border-border p-2">
                <dt className="text-foreground/50">Incidents</dt>
                <dd className="text-lg font-semibold">{summary.active_incident_count}</dd>
              </div>
              <div className="rounded-md border border-border p-2">
                <dt className="text-foreground/50">Alerts</dt>
                <dd className="text-lg font-semibold">{summary.active_alert_count}</dd>
              </div>
              <div className="rounded-md border border-border p-2">
                <dt className="text-foreground/50">Rising gauges</dt>
                <dd className="text-lg font-semibold">{summary.rising_gauge_count}</dd>
              </div>
            </dl>
            {summary.is_demo && (
              <p className="mt-2 text-[11px] text-foreground/50">
                Demo replay data - not current conditions.
              </p>
            )}
          </>
        )}
      </div>

      {summary && summary.active_incident_count > 0 && (
        <DisasterHeartbeat
          label="Developing flood conditions near Bethlehem"
          severity="severe"
          components={{
            hazardIntensity: 0.6,
            rateOfChange: 0.7,
            geographicSpread: 0.3,
            infrastructureStress: 0.5,
            populationExposure: 0.4,
            sourceAgreement: 0.65,
          }}
        />
      )}

      {summary && summary.active_incident_count > 0 && (
        <button
          type="button"
          onClick={() => {
            setPanel({ kind: "incident", incidentId: "developing-flood-bethlehem" });
            flyTo([-75.3705, 40.6259], 13);
          }}
          className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Open developing incident
        </button>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim()) setPanel({ kind: "assistant", question: question.trim() });
        }}
        className="space-y-1.5"
      >
        <label htmlFor="ask-earthpulse" className="text-xs font-semibold uppercase tracking-wide text-foreground/50">
          Ask EarthPulse
        </label>
        <div className="flex gap-1.5">
          <input
            id="ask-earthpulse"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Why is this area uncertain?"
            className="flex-1 rounded-md border border-border bg-surface px-2 py-1.5 text-sm"
          />
          <button type="submit" className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-surface-muted">
            Ask
          </button>
        </div>
      </form>

      {savedPlaces.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Saved places</h3>
          <ul className="mt-1 space-y-1">
            {savedPlaces.map((p) => (
              <li key={p.place_id}>
                <button
                  type="button"
                  onClick={() => {
                    setPanel({ kind: "place", placeId: p.place_id });
                    flyTo(p.center, 14);
                  }}
                  className="text-sm text-accent hover:underline"
                >
                  {p.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2 text-xs">
        <button type="button" onClick={() => setPanel({ kind: "hidden-risks" })} className="text-accent hover:underline">
          Find hidden risks
        </button>
        <span aria-hidden>·</span>
        <button type="button" onClick={() => setPanel({ kind: "source-health" })} className="text-accent hover:underline">
          Source health
        </button>
      </div>
    </div>
  );
}
