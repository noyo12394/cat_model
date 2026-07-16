"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "@/lib/store";

const PRESETS: { label: string; minutes: number }[] = [
  { label: "-24h", minutes: -1440 },
  { label: "-6h", minutes: -360 },
  { label: "-1h", minutes: -60 },
  { label: "Now", minutes: 0 },
  { label: "+1h", minutes: 60 },
  { label: "+3h", minutes: 180 },
  { label: "+6h", minutes: 360 },
  { label: "+12h", minutes: 720 },
  { label: "+24h", minutes: 1440 },
];

/** Universal time bar (section 6.4). Observed time (<=0) is visually
 * separated from forecast time (>0) via the slider's own coloring. */
export function BottomTimeBar() {
  const mode = useAppStore((s) => s.mode);
  const time = useAppStore((s) => s.time);
  const setOffsetMinutes = useAppStore((s) => s.setOffsetMinutes);
  const togglePlaying = useAppStore((s) => s.togglePlaying);
  const setPlaybackSpeed = useAppStore((s) => s.setPlaybackSpeed);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (time.isPlaying) {
      intervalRef.current = setInterval(() => {
        useAppStore.setState((s) => {
          const next = s.time.offsetMinutes + 15 * s.time.playbackSpeed;
          const max = mode === "replay" ? 600 : 1440;
          const min = mode === "replay" ? -240 : -1440;
          return { time: { ...s.time, offsetMinutes: next > max ? min : next } };
        });
      }, 500);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [time.isPlaying, time.playbackSpeed, mode]);

  const isForecastTime = time.offsetMinutes > 0;

  return (
    <div className="flex flex-col gap-1.5 border-t border-border bg-surface px-4 py-2">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={togglePlaying}
          className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs font-medium hover:bg-border/40"
          aria-pressed={time.isPlaying}
        >
          {time.isPlaying ? "⏸ Pause" : "▶ Play"}
        </button>

        <input
          type="range"
          min={mode === "replay" ? -240 : -1440}
          max={mode === "replay" ? 600 : 1440}
          step={15}
          value={time.offsetMinutes}
          onChange={(e) => setOffsetMinutes(Number(e.target.value))}
          className="h-1.5 flex-1 accent-accent"
          aria-label="Time offset from now"
        />

        <span
          className={
            "min-w-[92px] rounded-full px-2 py-0.5 text-center text-xs font-semibold " +
            (isForecastTime
              ? "border border-dashed border-accent text-accent"
              : "bg-surface-muted text-foreground/80")
          }
        >
          {isForecastTime ? "Forecast" : "Observed"} {formatOffset(time.offsetMinutes)}
        </span>

        <select
          value={time.playbackSpeed}
          onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
          className="rounded border border-border bg-surface px-1.5 py-1 text-xs"
          aria-label="Playback speed"
        >
          <option value={1}>1×</option>
          <option value={2}>2×</option>
          <option value={4}>4×</option>
        </select>
      </div>

      <div className="flex flex-wrap gap-1">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => setOffsetMinutes(p.minutes)}
            className="rounded-full border border-border px-2 py-0.5 text-[11px] hover:bg-surface-muted"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function formatOffset(minutes: number): string {
  if (minutes === 0) return "(now)";
  const hours = Math.abs(minutes) / 60;
  const sign = minutes > 0 ? "+" : "-";
  return `(${sign}${hours % 1 === 0 ? hours : hours.toFixed(1)}h)`;
}
