import { notFound } from "next/navigation";
import { HistoricExplorer } from "@/historic/HistoricExplorer";

export default function HistoricPage() {
  if (process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS === "false") notFound();
  return <HistoricExplorer />;
}
