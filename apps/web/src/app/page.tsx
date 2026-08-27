import { RiskChainWorkspace } from "@/riskchain/RiskChainWorkspace";

type SearchParams = Record<string, string | string[] | undefined>;

function one(value: string | string[] | undefined) {
  return typeof value === "string" ? value : undefined;
}

export default async function HomePage({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  return <RiskChainWorkspace
    initialView={one(params.view) === "live" ? "live" : "explore"}
    initialLiveQuery={{
      window: one(params.window), hazard: one(params.hazard), alert: one(params.alert),
      region: one(params.region), q: one(params.q), from: one(params.from), to: one(params.to),
      start_date: one(params.start_date), end_date: one(params.end_date),
      min_impact: one(params.min_impact), sort: one(params.sort),
    }}
  />;
}
