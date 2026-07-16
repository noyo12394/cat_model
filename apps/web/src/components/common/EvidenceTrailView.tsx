"use client";

import { useState } from "react";
import type { EvidenceTrail } from "@/lib/types";
import { CertaintyBadge, ConfidencePill } from "./Badges";

/** Full lineage view (section 23): source, weaknesses, and technical
 * basis behind any prediction, warning or recommendation - expandable so
 * the plain-language summary is what nontechnical users see first. */
export function EvidenceTrailView({ trail }: { trail: EvidenceTrail }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{trail.claim}</p>
          <p className="mt-1 text-sm text-foreground/80">{trail.plain_language_summary}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <CertaintyBadge value={trail.certainty_class} />
          <ConfidencePill value={trail.confidence} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-2 text-xs font-medium text-accent underline-offset-2 hover:underline"
        aria-expanded={expanded}
      >
        {expanded ? "Hide evidence trail" : "Show evidence trail"}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-border pt-3 text-sm">
          {trail.supporting_evidence.length > 0 && (
            <div>
              <p className="font-medium text-foreground/70">Supporting evidence</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-foreground/80">
                {trail.supporting_evidence.map((e, i) => (
                  <li key={i}>{e.label}</li>
                ))}
              </ul>
            </div>
          )}
          {trail.weaknesses.length > 0 && (
            <div>
              <p className="font-medium text-foreground/70">Weaknesses</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-foreground/80">
                {trail.weaknesses.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {trail.model_basis && (
            <div>
              <p className="font-medium text-foreground/70">Technical information</p>
              <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-xs text-foreground/70">
                <dt>Model</dt>
                <dd>
                  {trail.model_basis.model_id} v{trail.model_basis.model_version}
                </dd>
                <dt>Run time</dt>
                <dd>{new Date(trail.model_basis.run_at).toLocaleString()}</dd>
                <dt>Inputs used</dt>
                <dd>{trail.model_basis.inputs_used.join(", ")}</dd>
                <dt>Confidence method</dt>
                <dd>{trail.model_basis.confidence_method}</dd>
              </dl>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
