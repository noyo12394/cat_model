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
  if (!events.length) return null;

  // The tape is an ambient recency signal rather than a catalog. Keep the full
  // official response on the map and in the event list, but bound this moving
  // strip so a large feed does not create hundreds of focusable controls.
  const tapeSource = events.slice(0, 36);
  const tapeEvents = [...tapeSource, ...tapeSource];

  return <section className="event-tape" aria-label="Live GDACS event tape">
    <span className="event-tape-label">Live event tape</span>
    <div className="event-tape-window">
      <div className="event-tape-track">
        {tapeEvents.map((event, index) => {
          const tone = alertTone(event);
          const eventLabel = `${event.event_type} · ${event.name} · ${event.alert_level} alert · ${event.country} · ${new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(event.from_date))}`;
          const duplicate = index >= tapeSource.length;
          return <button
            className={`tape-spike ${tone}`}
            key={`${event.event_id}-${index}`}
            type="button"
            title={eventLabel}
            aria-label={`Select ${eventLabel}`}
            aria-hidden={duplicate || undefined}
            tabIndex={duplicate ? -1 : 0}
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
            <i aria-hidden="true">{event.event_type}</i>
            <span>{event.name}<small>{event.alert_level} · {event.country} · {new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(event.from_date))}</small></span>
          </button>;
        })}
      </div>
    </div>
  </section>;
}
