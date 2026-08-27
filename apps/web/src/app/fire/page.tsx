import type { Metadata } from "next";
import { RiskChainWorkspace } from "@/riskchain/RiskChainWorkspace";

export const metadata: Metadata = {
  title: "FIRE Lab | RiskChain",
  description: "Source-backed NIFC wildfire perimeter viewer and audit workspace.",
};

export default function FireLabPage() {
  return <RiskChainWorkspace initialView="activity" />;
}
