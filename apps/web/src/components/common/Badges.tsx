import clsx from "clsx";
import type { CertaintyClass, Confidence, Severity } from "@/lib/types";

const CERTAINTY_LABEL: Record<CertaintyClass, string> = {
  observed: "Observed",
  official_alert: "Official alert",
  forecast: "Forecast",
  ai_inferred: "AI-inferred",
  user_reported: "User-reported",
  unverified: "Unverified",
  historical: "Historical",
  simulated: "Simulated",
};

export function CertaintyBadge({ value, className }: { value: string; className?: string }) {
  const key = (value in CERTAINTY_LABEL ? value : "unverified") as CertaintyClass;
  const label = CERTAINTY_LABEL[key] ?? value;
  return (
    <span
      className={clsx(
        `evidence-${key}`,
        "inline-flex items-center gap-1 rounded-full border-current px-2 py-0.5 text-xs font-medium text-foreground/80",
        className,
      )}
      title={`This item is classified as: ${label}`}
    >
      {label}
    </span>
  );
}

const CONFIDENCE_LABEL: Record<Confidence, string> = {
  low: "Confidence: low",
  moderate: "Confidence: moderate",
  high: "Confidence: high",
};

export function ConfidencePill({ value }: { value: Confidence }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-muted px-2 py-0.5 text-xs font-medium",
      )}
    >
      <span
        aria-hidden
        className={clsx("h-1.5 w-1.5 rounded-full", {
          "bg-status-unknown": value === "low",
          "bg-status-watch": value === "moderate",
          "bg-status-normal": value === "high",
        })}
      />
      {CONFIDENCE_LABEL[value]}
    </span>
  );
}

const SEVERITY_COLOR: Record<Severity, string> = {
  unknown: "bg-status-unknown",
  normal: "bg-status-normal",
  watch: "bg-status-watch",
  elevated: "bg-status-elevated",
  severe: "bg-status-severe",
  extreme: "bg-status-extreme",
};

const SEVERITY_ICON: Record<Severity, string> = {
  unknown: "?",
  normal: "✓",
  watch: "▲",
  elevated: "▲",
  severe: "✖",
  extreme: "✖",
};

export function SeverityDot({ value, label }: { value: Severity; label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <span
        aria-hidden
        className={clsx("flex h-4 w-4 items-center justify-center rounded-full text-[9px] text-white", SEVERITY_COLOR[value])}
      >
        {SEVERITY_ICON[value]}
      </span>
      <span className="capitalize">{label ?? value}</span>
    </span>
  );
}
