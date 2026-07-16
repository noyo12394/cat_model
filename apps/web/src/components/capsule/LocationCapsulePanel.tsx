"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { CertaintyBadge, ConfidencePill } from "@/components/common/Badges";

/** Location Capsule (signature feature, section 8). */
export function LocationCapsulePanel({ placeId }: { placeId: string }) {
  const { data: capsule, isLoading, isError } = useQuery({
    queryKey: ["capsule", placeId],
    queryFn: () => api.getPlaceCapsule(placeId),
  });
  const setPanel = useAppStore((s) => s.setPanel);

  if (isLoading) return <div className="p-4 text-sm text-foreground/60">Loading location…</div>;
  if (isError || !capsule)
    return <div className="p-4 text-sm text-foreground/60">Could not load this place.</div>;

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-lg font-semibold">{capsule.name}</h2>
        <p className="mt-1 text-sm">{capsule.current_status_headline}</p>
        <div className="mt-2 flex items-center gap-2">
          <ConfidencePill value={capsule.data_confidence} />
          <span className="text-xs text-foreground/50">
            Last updated {new Date(capsule.last_updated).toLocaleTimeString()}
          </span>
        </div>
      </div>

      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Nearby conditions</h3>
        <ul className="mt-1.5 space-y-1.5">
          {capsule.nearby_conditions.map((c, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <CertaintyBadge value={c.certainty_class} className="mt-0.5 shrink-0" />
              <span>{c.label}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Next 24 hours</h3>
        <ul className="mt-1.5 list-inside list-disc space-y-1 text-sm">
          {capsule.next_24h_notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
        <div className="mt-1.5">
          <ConfidencePill value={capsule.forecast_confidence} />
        </div>
      </section>

      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Critical connections</h3>
        <ul className="mt-1.5 space-y-1.5">
          {capsule.critical_connections.map((c) => (
            <li key={c.facility_id} className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => setPanel({ kind: "place", placeId: c.facility_id })}
                className="text-accent hover:underline"
              >
                {c.name}
              </button>
              <span className="text-xs text-foreground/50">
                {c.distance_km} km{c.travel_time_minutes ? ` · ~${c.travel_time_minutes} min` : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {capsule.active_incident_ids.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground/50">Active incidents nearby</h3>
          <ul className="mt-1.5 space-y-1">
            {capsule.active_incident_ids.map((id) => (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => setPanel({ kind: "incident", incidentId: id })}
                  className="text-sm text-accent hover:underline"
                >
                  Open incident: {id}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() =>
            setPanel({ kind: "route", originPlaceId: placeId, destinationPlaceId: "fac-stlukes-bethlehem" })
          }
          className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-surface-muted"
        >
          Check route to nearest hospital
        </button>
      </section>

      {capsule.is_demo && (
        <p className="text-[11px] text-foreground/50">Demo data - not current conditions.</p>
      )}
    </div>
  );
}
