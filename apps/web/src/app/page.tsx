import { RiskChainWorkspace } from "@/riskchain/RiskChainWorkspace";

export default async function HomePage({ searchParams }: { searchParams: Promise<{ view?: string }> }) {
  const { view } = await searchParams;
  return <RiskChainWorkspace initialView={view === "live" ? "live" : "explore"} />;
}
