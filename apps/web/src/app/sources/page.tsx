import { ModeSetter } from "@/components/shell/ModeSetter";

export default function SourcesPage() {
  return <ModeSetter mode="live" panel={{ kind: "source-health" }} />;
}
