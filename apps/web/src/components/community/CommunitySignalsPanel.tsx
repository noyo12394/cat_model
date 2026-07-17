"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Globe2, MapPin, MessageCircleWarning, RefreshCw, ShieldAlert, ShieldCheck, Tags } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";

/** A review queue for source-returned public reports. It never changes the
 * official event's alert, forecast, or priority score. */
export function CommunitySignalsPanel() {
  const selectedGlobalEventId = useAppStore((state) => state.selectedGlobalEventId);
  const selectGlobalEvent = useAppStore((state) => state.selectGlobalEvent);
  const flyTo = useAppStore((state) => state.flyTo);
  const setMapScope = useAppStore((state) => state.setMapScope);
  const eventsQuery = useQuery({ queryKey: ["global-events"], queryFn: api.globalEvents, staleTime: 300_000 });
  const selectedEvent = useMemo(
    () => (eventsQuery.data?.events ?? []).find((event) => event.event_id === selectedGlobalEventId) ?? null,
    [eventsQuery.data?.events, selectedGlobalEventId],
  );
  const choices = useMemo(() => {
    const levelRank: Record<string, number> = { red: 0, orange: 1, green: 2 };
    return [...(eventsQuery.data?.events ?? [])].sort((a, b) => (levelRank[a.alert_level] ?? 3) - (levelRank[b.alert_level] ?? 3)).slice(0, 5);
  }, [eventsQuery.data?.events]);
  const signalsQuery = useQuery({
    queryKey: ["community-signals", selectedEvent?.event_id],
    queryFn: () => api.communitySignals(selectedEvent!.event_id),
    enabled: Boolean(selectedEvent),
    staleTime: 300_000,
    retry: 1,
  });

  const chooseEvent = (eventId: string) => {
    const event = (eventsQuery.data?.events ?? []).find((item) => item.event_id === eventId);
    if (!event) return;
    setMapScope("global");
    selectGlobalEvent(event.event_id);
    flyTo(event.center, 4.7);
  };

  return (
    <div className="community-signals-panel">
      <header className="community-signals-header">
        <div><span className="community-signals-icon"><MessageCircleWarning size={18} /></span><div><span className="panel-kicker">COMMUNITY SIGNALS</span><h1>Public reports, held for verification</h1></div></div>
        <p>Language labels help an operator triage source-returned posts. They never raise an alert level, create a hazard, or change a forecast.</p>
      </header>

      <section className="community-event-picker" aria-label="Choose a current official event">
        <div><Globe2 size={13} /><span>SELECT CURRENT GDACS EVENT</span></div>
        {eventsQuery.isLoading ? <p>Loading current official events…</p> : choices.map((event) => (
          <button key={event.event_id} type="button" className={selectedEvent?.event_id === event.event_id ? "is-selected" : ""} onClick={() => chooseEvent(event.event_id)}>
            <i className={event.alert_level} /><span><strong>{event.name}</strong><small>{event.country} · {event.alert_level} alert</small></span><MapPin size={12} />
          </button>
        ))}
      </section>

      {!selectedEvent ? (
        <div className="community-empty"><ShieldCheck size={20} /><strong>Choose an official event first</strong><span>The feed only searches terms tied to an active GDACS event; it does not run an unbounded social-risk search.</span></div>
      ) : signalsQuery.isLoading ? (
        <div className="future-outlook-loading community-loading"><RefreshCw size={13} /> Checking the verified community source for {selectedEvent.name}…</div>
      ) : signalsQuery.isError || signalsQuery.data?.availability === "unavailable" ? (
        <section className="community-unavailable">
          <ShieldAlert size={17} /><div><strong>{signalsQuery.data?.availability_label ?? "Community source unavailable"}</strong><p>{signalsQuery.data?.availability_detail ?? "No community data is shown."}</p></div>
        </section>
      ) : signalsQuery.data && (
        <>
          <section className="community-source-summary">
            <div><span className="panel-kicker">SELECTED EVENT</span><strong>{signalsQuery.data.event_name}</strong><small>{signalsQuery.data.availability_detail}</small></div>
            <a href={signalsQuery.data.source_url} target="_blank" rel="noreferrer">Source method <ExternalLink size={11} /></a>
          </section>
          {signalsQuery.data.items.length === 0 ? (
            <div className="community-empty"><ShieldCheck size={20} /><strong>No matching recent reports</strong><span>This means the configured source returned no posts for the precise official-event query—not that conditions are safe.</span></div>
          ) : (
            <section className="community-report-list" aria-label="Unverified community reports">
              {signalsQuery.data.items.map((signal) => (
                <article key={signal.post_id} className={signal.tone}>
                  <div className="community-report-heading"><span>{toneLabel(signal.tone)}</span><small>{formatUtc(signal.observed_at)} · unverified</small><a href={signal.source_url} target="_blank" rel="noreferrer" aria-label="Open source post"><ExternalLink size={11} /></a></div>
                  <p>{signal.text}</p>
                  <div className="community-report-tags"><Tags size={10} /> <span>{reportTypeLabel(signal.report_type)}</span>{signal.tags.map((tag) => <em key={tag}>{tag}</em>)}</div>
                </article>
              ))}
            </section>
          )}
          <footer className="community-limits"><strong>Method: </strong>{signalsQuery.data.method}<ul>{signalsQuery.data.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul></footer>
        </>
      )}
    </div>
  );
}

function toneLabel(tone: "urgent_language" | "concern_language" | "neutral_language") {
  return tone === "urgent_language" ? "urgent language" : tone === "concern_language" ? "concern language" : "neutral language";
}

function reportTypeLabel(type: "possible_impact_report" | "possible_condition_report" | "event_mention") {
  return type === "possible_impact_report" ? "possible impact report" : type === "possible_condition_report" ? "possible condition report" : "event mention";
}

function formatUtc(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }).format(new Date(value)) + " UTC";
}
