"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ConfidencePill } from "@/components/common/Badges";

/** Grounded AI Assistant (section 31.8): every answer carries time range,
 * location, sources, observed-vs-inferred labels, confidence and limitations. */
export function AssistantPanel({ question }: { question: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["assistant", question],
    queryFn: () => api.queryAssistant(question),
  });

  return (
    <div className="space-y-3 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground/50">EarthPulse assistant</h2>
      <p className="rounded-md bg-surface-muted px-3 py-1.5 text-sm italic">&ldquo;{question}&rdquo;</p>

      {isLoading && <p className="text-sm text-foreground/60">Thinking…</p>}
      {data && (
        <div className="space-y-3">
          <p className="text-sm">{data.answer}</p>
          <div className="flex flex-wrap items-center gap-2">
            <ConfidencePill value={data.confidence} />
            {data.location_label && (
              <span className="text-xs text-foreground/50">Location: {data.location_label}</span>
            )}
            <span className="text-xs text-foreground/50">{data.time_range.label}</span>
          </div>
          {data.observed_vs_inferred.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-foreground/50">Observed vs. inferred</h3>
              <ul className="mt-1 list-inside list-disc text-xs text-foreground/70">
                {data.observed_vs_inferred.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}
          {data.limitations.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-foreground/50">Limitations</h3>
              <ul className="mt-1 list-inside list-disc text-xs text-foreground/70">
                {data.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
          {data.sources.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-foreground/50">Sources</h3>
              <ul className="mt-1 list-inside list-disc text-xs text-foreground/70">
                {data.sources.map((s, i) => (
                  <li key={i}>{s.label}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-[10px] uppercase tracking-wide text-foreground/40">
            Prose source: {data.prose_source}
          </p>
        </div>
      )}
    </div>
  );
}
