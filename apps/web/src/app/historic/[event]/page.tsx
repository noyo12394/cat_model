import { notFound } from "next/navigation";
import { historicEvent, HISTORIC_EVENTS } from "@/historic/data";
import { HistoricExplorer } from "@/historic/HistoricExplorer";

export function generateStaticParams() { return HISTORIC_EVENTS.map((event) => ({ event: event.slug })); }

export default async function HistoricEventPage({ params }: { params: Promise<{ event: string }> }) {
  if (process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS === "false") notFound();
  const { event: eventSlug } = await params;
  const event = historicEvent(eventSlug);
  if (!event) notFound();
  return <HistoricExplorer initialEventSlug={event.slug} />;
}
