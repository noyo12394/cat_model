"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { exposureColor } from "@/components/map/facilityStyle";

const EXPOSURE_LABEL: Record<string, string> = {
  lower: "Lower current exposure",
  elevated: "Elevated current exposure",
  unavailable: "Unavailable",
};

/** Route Risk (signature feature, section 15). Never labels a route "safe". */
export function RouteRiskPanel({
  originPlaceId,
  destinationPlaceId,
}: {
  originPlaceId: string;
  destinationPlaceId: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["route", originPlaceId, destinationPlaceId],
    queryFn: () => api.analyzeRoute(originPlaceId, destinationPlaceId),
  });

  if (isLoading) return <div className="p-4 text-sm text-foreground/60">Analyzing route…</div>;
  if (!data || data.options.length === 0)
    return <div className="p-4 text-sm text-foreground/60">No route options available for this pair.</div>;

  return (
    <div className="space-y-3 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground/50">Route risk</h2>
      <p className="text-xs text-foreground/60">{data.disclaimer}</p>
      <ul className="space-y-2">
        {data.options.map((opt) => (
          <li key={opt.route_id} className="rounded-lg border border-border p-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">{opt.label}</p>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                style={{ backgroundColor: exposureColor(opt.exposure_level) }}
              >
                {EXPOSURE_LABEL[opt.exposure_level] ?? opt.exposure_level}
              </span>
            </div>
            <p className="mt-1 text-xs text-foreground/60">
              {opt.duration_minutes != null ? `${opt.duration_minutes} min` : "Duration unavailable"}
              {opt.distance_km != null ? ` · ${opt.distance_km} km` : ""}
            </p>
            <p className="mt-1 text-sm text-foreground/80">{opt.exposure_note}</p>
            {opt.segments.length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-xs text-foreground/60">
                {opt.segments.map((seg) => (
                  <li key={seg.segment_id}>
                    {seg.description}
                    {seg.river_crossing ? " (river crossing)" : ""}
                    {seg.reported_closure ? " - reported closure" : ""}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
