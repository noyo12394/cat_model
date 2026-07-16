"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/** Find Hidden Risks (section 30) - a defining professional feature. */
export function HiddenRisksPanel() {
  const { data, isLoading } = useQuery({ queryKey: ["hidden-risks"], queryFn: api.hiddenRisks });

  return (
    <div className="space-y-3 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground/50">Find hidden risks</h2>
      <p className="text-xs text-foreground/60">
        Ranked, explainable findings from the current facility and dependency data - not a single opaque score.
      </p>
      {isLoading && <p className="text-sm text-foreground/60">Scanning…</p>}
      <ol className="space-y-2">
        {(data ?? []).map((risk, i) => (
          <li key={risk.risk_id} className="rounded-md border border-border p-2">
            <p className="text-xs font-semibold text-foreground/50">
              #{i + 1} · {risk.category.replace(/_/g, " ")}
            </p>
            <p className="text-sm font-medium">{risk.title}</p>
            <p className="mt-0.5 text-sm text-foreground/70">{risk.detail}</p>
            <ul className="mt-1 list-inside list-disc text-xs text-foreground/50">
              {risk.evidence.map((e, j) => (
                <li key={j}>{e}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </div>
  );
}
