"use client";

import { useEffect, useRef } from "react";
import { FastForward, Pause, Play, RotateCcw } from "lucide-react";
import { useAppStore } from "@/lib/store";

const LOCAL_MARKERS = [
  { label: "First signal", minutes: -360, kind: "observed" },
  { label: "Warning", minutes: -120, kind: "alert" },
  { label: "Now", minutes: 0, kind: "now" },
  { label: "Road impact", minutes: 180, kind: "forecast" },
  { label: "Peak", minutes: 360, kind: "forecast" },
] as const;

const GLOBAL_MARKERS = [
  { label: "Now", minutes: 0, kind: "now" },
  { label: "15m", minutes: 15, kind: "forecast" },
  { label: "1h", minutes: 60, kind: "forecast" },
  { label: "6h", minutes: 360, kind: "forecast" },
  { label: "24h", minutes: 1440, kind: "forecast" },
] as const;

export function BottomTimeBar() {
  const mode = useAppStore((s) => s.mode);
  const mapScope = useAppStore((s) => s.mapScope);
  const time = useAppStore((s) => s.time);
  const setOffsetMinutes = useAppStore((s) => s.setOffsetMinutes);
  const togglePlaying = useAppStore((s) => s.togglePlaying);
  const setPlaybackSpeed = useAppStore((s) => s.setPlaybackSpeed);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isGlobal = mapScope === "global";
  const min = isGlobal ? 0 : mode === "replay" ? -240 : -1440;
  const max = mode === "replay" ? 600 : 1440;
  const markers = isGlobal ? GLOBAL_MARKERS : LOCAL_MARKERS;

  useEffect(() => {
    if (time.isPlaying) {
      intervalRef.current = setInterval(() => {
        useAppStore.setState((state) => {
          const next = state.time.offsetMinutes + 15 * state.time.playbackSpeed;
          return { time: { ...state.time, offsetMinutes: next > max ? min : next } };
        });
      }, 700);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [time.isPlaying, time.playbackSpeed, min, max]);

  const isForecastTime = time.offsetMinutes > 0;
  const position = ((time.offsetMinutes - min) / (max - min)) * 100;
  const confidence = forecastConfidence(time.offsetMinutes, isGlobal);

  return (
    <section className={`time-dock ${isGlobal ? "is-global" : ""}`} aria-label={isGlobal ? "Global operational watch horizon" : "0 to 24 hour forecast horizon"}>
      <div className="time-dock-topline">
        <div className="playback-controls">
          <button type="button" className="play-button" onClick={togglePlaying} aria-pressed={time.isPlaying} aria-label={time.isPlaying ? "Pause timeline" : "Play timeline"}>
            {time.isPlaying ? <Pause size={15} fill="currentColor" aria-hidden /> : <Play size={15} fill="currentColor" aria-hidden />}
          </button>
          <button type="button" className="reset-time" onClick={() => setOffsetMinutes(0)} disabled={time.offsetMinutes === 0}>
            <RotateCcw size={14} aria-hidden /> Now
          </button>
        </div>

        <div className="time-readout" aria-live="polite">
          <span className={isForecastTime ? "forecast" : "observed"}>{isGlobal ? (isForecastTime ? "WATCH WINDOW" : "LIVE ALERTS") : (isForecastTime ? "FORECAST" : "OBSERVED")}</span>
          <strong>{formatOffset(time.offsetMinutes)}</strong>
          <small>{formatClock(time.offsetMinutes, isGlobal)}</small>
        </div>

        <div className="speed-control">
          <FastForward size={14} aria-hidden />
          {[1, 2, 4].map((speed) => (
            <button key={speed} type="button" className={time.playbackSpeed === speed ? "is-active" : ""} onClick={() => setPlaybackSpeed(speed)} aria-pressed={time.playbackSpeed === speed}>{speed}×</button>
          ))}
        </div>
      </div>

      <div className="timeline-track-wrap">
        <div className="timeline-zones" aria-hidden><span className="observed-zone">{isGlobal ? "CURRENT GDACS FEED" : "PAST / OBSERVED"}</span><span className="forecast-zone">{isGlobal ? "VERIFICATION WINDOW" : "POSSIBLE NEXT"}</span></div>
        <input
          type="range"
          min={min}
          max={max}
          step={15}
          value={time.offsetMinutes}
          onChange={(e) => setOffsetMinutes(Number(e.target.value))}
          className="timeline-range"
          style={{ "--timeline-position": `${position}%` } as React.CSSProperties}
          aria-label="Time offset from now"
          aria-valuetext={`${isForecastTime ? "Forecast" : "Observed"} ${formatOffset(time.offsetMinutes)}`}
        />
        <div className="timeline-markers">
          {markers.filter((marker) => marker.minutes >= min && marker.minutes <= max).map((marker) => (
            <button
              key={marker.label}
              type="button"
              className={`timeline-marker ${marker.kind}`}
              style={{ left: `${((marker.minutes - min) / (max - min)) * 100}%` }}
              onClick={() => setOffsetMinutes(marker.minutes)}
              title={`Jump to ${marker.label}`}
            >
              <span aria-hidden />
              <small>{marker.label}</small>
            </button>
          ))}
        </div>
      </div>
      <div className="forecast-confidence" aria-label={isGlobal ? "Global watch calculation limits" : "Forecast evidence horizon"}>
        <span>{isGlobal ? "CALCULATION" : "EVIDENCE HORIZON"}</span>
        <i><b style={{ width: `${confidence.width}%` }} /></i>
        <strong>{confidence.label}</strong>
        <small>{confidence.detail}</small>
      </div>
    </section>
  );
}

function formatOffset(minutes: number): string {
  if (minutes === 0) return "Now";
  const absolute = Math.abs(minutes);
  const hours = Math.floor(absolute / 60);
  const mins = absolute % 60;
  const value = hours ? `${hours}h${mins ? ` ${mins}m` : ""}` : `${mins}m`;
  return minutes > 0 ? `+${value}` : `−${value}`;
}

function formatClock(minutes: number, isGlobal: boolean): string {
  if (minutes === 0) return "Current view";
  if (isGlobal) return "Analyst verification window";
  return minutes > 0 ? "Model outlook" : "Archived observation";
}

function forecastConfidence(minutes: number, isGlobal: boolean) {
  if (isGlobal) return {
    width: 58,
    label: "Triage only",
    detail: "Ranks attention from GDACS alert metadata; it does not forecast event evolution.",
  };
  if (minutes <= 0) return {
    width: 96,
    label: "Observed",
    detail: "Current signals and official alerts are shown as evidence, not a prediction.",
  };
  if (minutes <= 180) return {
    width: 76,
    label: "Supported outlook",
    detail: "Forecast guidance and observed trends inform the short-horizon modeled impact lens.",
  };
  if (minutes <= 720) return {
    width: 54,
    label: "Conditional outlook",
    detail: "Consequences remain possible futures; uncertainty grows with forecast lead time.",
  };
  return {
    width: 30,
    label: "Planning horizon",
    detail: "Use as a scenario to verify, not a statement of what will happen.",
  };
}
