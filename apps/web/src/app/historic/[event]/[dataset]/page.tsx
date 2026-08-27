import { notFound } from "next/navigation";
import { HistoricExplorer } from "@/historic/HistoricExplorer";
import { historicAction, historicDataset, historicEvent, HISTORIC_EVENTS } from "@/historic/data";

export function generateStaticParams() { return HISTORIC_EVENTS.flatMap((event) => event.datasets.map((dataset) => ({ event: event.slug, dataset: dataset.slug }))); }

export default async function HistoricExplorePage({
  params,
  searchParams,
}: {
  params: Promise<{ event: string; dataset: string }>;
  searchParams: Promise<{ action?: string | string[] }>;
}) {
  if (process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS === "false") notFound();
  const values = await params;
  const event = historicEvent(values.event);
  if (!event) notFound();
  const dataset = historicDataset(event, values.dataset);
  if (!dataset) notFound();
  const query = await searchParams;
  return <HistoricExplorer initialEventSlug={event.slug} initialDatasetSlug={dataset.slug} initialAction={historicAction(query.action)} />;
}
