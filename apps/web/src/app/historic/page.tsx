import Link from "next/link";
import { notFound } from "next/navigation";
import { HISTORIC_EVENTS } from "@/historic/data";
import { HistoricShell } from "@/historic/HistoricShell";

export default function HistoricPage() {
  if (process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS === "false") notFound();
  return <HistoricShell step={1}><section className="historic-index"><div className="historic-title"><span className="eyebrow">Curated United States archive</span><h1>Select a historic event</h1><p>Five hazards, each grounded in at least three named official sources. Loss values preserve their source basis and missing values stay missing.</p></div><div className="historic-event-grid">{HISTORIC_EVENTS.map((event) => <Link key={event.slug} href={`/historic/${event.slug}`}><span className={`historic-hazard ${event.hazard_code}`}>{event.hazard_code}</span><div><h2>{event.name}</h2><p>{event.hazard} · {event.start_date}</p><strong>{event.headline_loss}</strong></div><small>{event.sources.length} SOURCES →</small></Link>)}</div></section></HistoricShell>;
}
