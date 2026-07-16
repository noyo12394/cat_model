"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  live: "bg-status-normal",
  stale: "bg-status-watch",
  demo: "bg-status-elevated",
  unavailable: "bg-status-unknown",
};

/** Source Health page (section 42): is each feed actually working right now? */
export function SourceHealthPanel() {
  const { data, isLoading } = useQuery({ queryKey: ["source-health"], queryFn: api.sourceStatus });

  return (
    <div className="space-y-3 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground/50">Source health</h2>
      {isLoading && <p className="text-sm text-foreground/60">Checking feeds…</p>}
      <ul className="space-y-2">
        {(data ?? []).map((s) => (
          <li key={s.key} className="flex items-start gap-2 rounded-md border border-border p-2">
            <span
              aria-hidden
              className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_COLOR[s.status] ?? "bg-status-unknown"}`}
            />
            <div>
              <p className="text-sm font-medium">
                {s.display_name} <span className="text-xs font-normal text-foreground/50">({s.organization})</span>
              </p>
              <p className="text-xs uppercase tracking-wide text-foreground/50">{s.status}</p>
              <p className="text-xs text-foreground/60">{s.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
