"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CertaintyBadge } from "@/components/common/Badges";

const OPTIONS: { value: "30_minutes" | "1_hour" | "6_hours" | "yesterday"; label: string }[] = [
  { value: "30_minutes", label: "30 minutes ago" },
  { value: "1_hour", label: "1 hour ago" },
  { value: "6_hours", label: "6 hours ago" },
  { value: "yesterday", label: "Yesterday" },
];

/** What Changed? (signature feature, section 10). */
export function WhatChangedPanel({ incidentId, mode }: { incidentId: string; mode: "live" | "replay" }) {
  const [comparedTo, setComparedTo] = useState<(typeof OPTIONS)[number]["value"]>("1_hour");
  const { data, isLoading } = useQuery({
    queryKey: ["what-changed", incidentId, mode, comparedTo],
    queryFn: () => api.getWhatChanged(incidentId, comparedTo, mode),
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-foreground/60">Compare to:</span>
        {OPTIONS.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => setComparedTo(o.value)}
            className={
              "rounded-full border px-2 py-0.5 text-xs " +
              (comparedTo === o.value ? "border-accent text-accent" : "border-border hover:bg-surface-muted")
            }
          >
            {o.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-sm text-foreground/60">Loading…</p>}
      {data && (
        <ul className="space-y-1.5 border-l-2 border-border pl-3">
          {data.changes.map((c, i) => (
            <li key={i} className="text-sm">
              <div className="flex items-start gap-2">
                <CertaintyBadge value={c.certainty_class} className="mt-0.5 shrink-0" />
                <span>{c.detail}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
