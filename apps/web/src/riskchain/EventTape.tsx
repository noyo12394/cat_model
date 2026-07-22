"use client";

import type { GlobalEvent } from "@/lib/types";
import type { MapSelection } from "./RiskMap";

type Props = {
  events: GlobalEvent[];
  onSelect: (selection: MapSelection) => void;
};

function alertTone(event: GlobalEvent) {
  if (event.alert_level === "red") return "red";
  if (event.alert_level === "orange") return "orange";
  return "green";
}

export function EventTape({ events, onSelect }: Props) {
  if (!events.length) {
    return <div className="event-tape event-tape-empty" aria-label="Live event tape"><span>Live event tape</span><p>No current events on tape.</p></div>;
  }

  // Rendering the same source-backed items twice lets the physical tape loop
  // continuously; both copies always select the original event record.
  const tapeEvents = [...events, ...events];

  return <section className="event-tape" aria-label="Live GDACS event tape">
    <span className="event-tape-label">Live event tape</span>
    <div className="event-tape-window">
      <div className="event-tape-track">
        {tapeEvents.map((event, index) => {
          const tone = alertTone(event);
          const eventLabel = `${event.name} · ${event.alert_level} alert`;
          return <button
            className={`tape-spike ${tone}`}
            key={`${event.event_id}-${index}`}
            type="button"
            title={eventLabel}
            aria-label={`Select ${eventLabel}`}
            onClick={() => onSelect({
              id: event.event_id,
              title: event.name,
              subtitle: `${event.event_type} · ${event.country}`,
              status: "Officially reported",
              source: event.source,
              center: event.center,
              zoom: 7,
            })}
          >
            <i aria-hidden="true" />
            <span className="tape-spike-tooltip" role="tooltip">{eventLabel}</span>
          </button>;
        })}
      </div>
    </div>
  </section>;
}
