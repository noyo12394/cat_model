import { notFound } from "next/navigation";
import { RiskChainWorkspace } from "@/riskchain/RiskChainWorkspace";

export default function GenomePage() {
  if (process.env.NEXT_PUBLIC_FF_GENOME_LAB !== "true") notFound();
  return <RiskChainWorkspace initialView="genome" />;
}
