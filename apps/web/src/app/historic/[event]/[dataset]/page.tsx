import { notFound } from "next/navigation";
import { EventCard } from "@/historic/EventCard";
import { historicDataset, historicEvent, HISTORIC_EVENTS } from "@/historic/data";
import { HistoricShell } from "@/historic/HistoricShell";

export function generateStaticParams() { return HISTORIC_EVENTS.flatMap((event) => event.datasets.map((dataset) => ({ event: event.slug, dataset: dataset.slug }))); }

export default async function HistoricExplorePage({ params }: { params: Promise<{ event: string; dataset: string }> }) {
  if (process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS === "false") notFound();
  const values = await params;
  const event = historicEvent(values.event);
  if (!event) notFound();
  const dataset = historicDataset(event, values.dataset);
  if (!dataset) notFound();
  return <HistoricShell step={3}><EventCard event={event} selectedDataset={dataset} /></HistoricShell>;
}
