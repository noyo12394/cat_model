"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Alert, HazardEvent } from "@/lib/types";

export interface FacilityMarker {
  facility_id: string;
  name: string;
  facility_type: string;
  center: [number, number];
  operational_state: string;
}

const FACILITY_CENTERS: Record<string, [number, number]> = {
  "fac-stlukes-bethlehem": [-75.3599, 40.6294],
  "fac-lvh-muhlenberg": [-75.446, 40.6417],
  "fac-hill-to-hill-bridge": [-75.3746, 40.622],
  "fac-fahy-bridge": [-75.366, 40.618],
  "fac-bethlehem-fire-1": [-75.3715, 40.6247],
  "fac-gauge-monocacy": [-75.378, 40.628],
  "fac-gauge-lehigh": [-75.373, 40.623],
  "place-lehigh-university": [-75.3785, 40.6084],
};

const FACILITY_TYPES: Record<string, string> = {
  "fac-stlukes-bethlehem": "hospital",
  "fac-lvh-muhlenberg": "hospital",
  "fac-hill-to-hill-bridge": "bridge",
  "fac-fahy-bridge": "bridge",
  "fac-bethlehem-fire-1": "fire_station",
  "fac-gauge-monocacy": "gauge",
  "fac-gauge-lehigh": "gauge",
  "place-lehigh-university": "school",
};

/** Live map data (section 7): incident geometry, alerts, and facility
 * markers, all sourced through the backend - never fetched directly from
 * NWS/USGS/etc. in the browser (section 35). */
export function useMapData() {
  const incidents = useQuery({ queryKey: ["incidents", "live"], queryFn: () => api.listIncidents("live") });
  const liveEvents = useQuery({ queryKey: ["live-events"], queryFn: api.liveEvents });

  const facilities: FacilityMarker[] = Object.entries(FACILITY_CENTERS).map(([id, center]) => ({
    facility_id: id,
    name: id,
    facility_type: FACILITY_TYPES[id] ?? "unknown",
    center,
    operational_state: "normal",
  }));

  const alerts: Alert[] = liveEvents.data?.alerts ?? [];
  const events: HazardEvent[] = liveEvents.data?.events ?? [];

  return {
    isLoading: incidents.isLoading || liveEvents.isLoading,
    incidents: incidents.data ?? [],
    alerts,
    events,
    facilities,
  };
}
