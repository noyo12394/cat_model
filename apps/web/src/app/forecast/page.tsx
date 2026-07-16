import { ModeSetter } from "@/components/shell/ModeSetter";

export default function ForecastPage() {
  return (
    <ModeSetter
      mode="forecast"
      panel={{ kind: "incident", incidentId: "developing-flood-bethlehem" }}
    />
  );
}
