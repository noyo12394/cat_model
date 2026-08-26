import Link from "next/link";
import { notFound } from "next/navigation";
import { historicEvent, HISTORIC_EVENTS } from "@/historic/data";
import { HistoricShell } from "@/historic/HistoricShell";

export function generateStaticParams() { return HISTORIC_EVENTS.map((event) => ({ event: event.slug })); }

export default async function HistoricDatasetPage({ params }: { params: Promise<{ event: string }> }) {
  if (process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS === "false") notFound();
  const { event: eventSlug } = await params;
  const event = historicEvent(eventSlug);
  if (!event) notFound();
  return <HistoricShell step={2}><section className="historic-index"><div className="historic-title"><Link href="/historic">← All events</Link><span className="eyebrow">{event.name}</span><h1>Select a dataset</h1><p>Review provenance, source, resolution, vintage, units, and availability before opening a layer.</p></div><div className="historic-dataset-grid">{event.datasets.map((dataset) => { const source = event.sources.find((item) => item.id === dataset.source_id); return <Link key={dataset.slug} href={`/historic/${event.slug}/${dataset.slug}`}><span className={`provenance ${dataset.provenance.replaceAll(" ", "-")}`}>{dataset.provenance}</span><h2>{dataset.name}</h2><dl><div><dt>Resolution</dt><dd>{dataset.resolution}</dd></div><div><dt>Source</dt><dd>{source?.name}</dd></div><div><dt>Vintage</dt><dd>{dataset.vintage}</dd></div><div><dt>Units</dt><dd>{dataset.unit}</dd></div></dl><strong>Explore this dataset →</strong></Link>; })}</div></section></HistoricShell>;
}
