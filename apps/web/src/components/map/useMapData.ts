"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
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

const FACILITY_NAMES: Record<string, string> = {
  "fac-stlukes-bethlehem": "St. Luke's University Hospital",
  "fac-lvh-muhlenberg": "Lehigh Valley Hospital–Muhlenberg",
  "fac-hill-to-hill-bridge": "Hill to Hill Bridge",
  "fac-fahy-bridge": "Fahy Bridge",
  "fac-bethlehem-fire-1": "Bethlehem Fire Station 1",
  "fac-gauge-monocacy": "Monocacy Creek gauge",
  "fac-gauge-lehigh": "Lehigh River gauge",
  "place-lehigh-university": "Lehigh University",
};

/** Live map data (section 7): incident geometry, alerts, and facility
 * markers, all sourced through the backend - never fetched directly from
 * NWS/USGS/etc. in the browser (section 35). */
export function useMapData() {
  const offsetMinutes = useAppStore((state) => state.time.offsetMinutes);
  const incidents = useQuery({ queryKey: ["incidents", "live"], queryFn: () => api.listIncidents("live") });
  const liveEvents = useQuery({ queryKey: ["live-events"], queryFn: api.liveEvents });
  const multiHazard = useQuery({ queryKey: ["multi-hazard-overview"], queryFn: api.multiHazardOverview, staleTime: 60_000 });
  const globalEvents = useQuery({ queryKey: ["global-events"], queryFn: () => api.globalEvents(), staleTime: 300_000 });
  const globalOutlook = useQuery({
    queryKey: ["global-outlook", Math.max(0, offsetMinutes)],
    queryFn: () => api.globalOutlook(Math.max(0, offsetMinutes)),
    staleTime: 300_000,
  });

  const facilities: FacilityMarker[] = Object.entries(FACILITY_CENTERS).map(([id, center]) => ({
    facility_id: id,
    name: FACILITY_NAMES[id] ?? id,
    facility_type: FACILITY_TYPES[id] ?? "unknown",
    center,
    operational_state: "normal",
  }));

  const alerts: Alert[] = liveEvents.data?.alerts ?? [];
  const events: HazardEvent[] = liveEvents.data?.events ?? [];
  const sensors = liveEvents.data?.sensors ?? [];
  const compoundEvents = multiHazard.data?.compound_events ?? [];
  const globalEventRecords = globalEvents.data?.events ?? [];
  const globalWatchItems = globalOutlook.data?.items ?? [];

  return {
    isLoading: incidents.isLoading || liveEvents.isLoading || multiHazard.isLoading || globalEvents.isLoading,
    incidents: incidents.data ?? [],
    alerts,
    events,
    sensors,
    compoundEvents,
    globalEvents: globalEventRecords,
    globalOutlook: globalOutlook.data,
    globalWatchItems,
    facilities,
  };
}
