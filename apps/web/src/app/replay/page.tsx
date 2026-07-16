import { ModeSetter } from "@/components/shell/ModeSetter";

export default function ReplayPage() {
  return (
    <ModeSetter mode="replay" panel={{ kind: "incident", incidentId: "developing-flood-bethlehem" }} />
  );
}
