import { ModeSetter } from "@/components/shell/ModeSetter";

export default async function IncidentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <ModeSetter mode="live" panel={{ kind: "incident", incidentId: slug }} />;
}
