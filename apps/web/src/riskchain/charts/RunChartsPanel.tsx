"use client";

import { useEffect, useState } from "react";
import type { CatModelRunResult } from "@/lib/types";
import { chartApi } from "./chartApi";
import type { LossHistogram, LossWaterfall, WaterRiseSweep } from "./chartTypes";
import { LossHistogramChart } from "./LossHistogramChart";
import { LossWaterfallChart } from "./LossWaterfallChart";
import { WaterRiseExplorer } from "./WaterRiseExplorer";
import styles from "./charts.module.css";

// Vulnerability curves and EP charts live in ModelAnalytics; this panel adds
// the complementary views: distribution, financial waterfall, water-rise.
const TABS = [
  { id: "distribution", label: "Loss distribution" },
  { id: "waterfall", label: "Financial waterfall" },
  { id: "water-rise", label: "Raise the water" },
] as const;
type TabId = (typeof TABS)[number]["id"];

/** Extra chart views for one immutable model run. Each tab lazily fetches its
 * pre-derived series from /cat/model-runs/{id}/charts/* and only draws. */
export function RunChartsPanel({ run }: { run: CatModelRunResult }) {
  const [tab, setTab] = useState<TabId>("distribution");
  const [histogram, setHistogram] = useState<LossHistogram | null>(null);
  const [waterfall, setWaterfall] = useState<LossWaterfall | null>(null);
  const [waterRise, setWaterRise] = useState<WaterRiseSweep | null>(null);
  const [errors, setErrors] = useState<Partial<Record<TabId, string>>>({});

  const active = tab === "distribution" ? histogram : tab === "waterfall" ? waterfall : waterRise;
  const error = errors[tab] ?? null;
  const loading = !active && !error;

  useEffect(() => {
    if (active || errors[tab]) return; // cached
    let cancelled = false;
    const finish = <T,>(setter: (value: T) => void) => (value: T) => { if (!cancelled) setter(value); };
    const fail = () => { if (!cancelled) setErrors((prev) => ({ ...prev, [tab]: "Chart data is unavailable for this run." })); };
    if (tab === "distribution") chartApi.lossHistogram(run.run_id).then(finish(setHistogram)).catch(fail);
    else if (tab === "waterfall") chartApi.waterfall(run.run_id).then(finish(setWaterfall)).catch(fail);
    else chartApi.waterRise(run.run_id).then(finish(setWaterRise)).catch(fail);
    return () => { cancelled = true; };
  }, [tab, run.run_id, active, errors]);

  return (
    <section className={styles.panel} aria-label="Additional model run charts">
      <div className={styles.tabs} role="tablist">
        {TABS.map((item) => (
          <button key={item.id} role="tab" aria-selected={tab === item.id}
            className={tab === item.id ? styles.active : undefined}
            onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>

      {error && <div className={styles.errorState}>{error}</div>}
      {!error && loading && <div className={styles.loading}>Deriving chart from the stored run…</div>}
      {!error && !loading && (
        <>
          {tab === "distribution" && histogram && <LossHistogramChart chart={histogram} />}
          {tab === "waterfall" && waterfall && <LossWaterfallChart chart={waterfall} />}
          {tab === "water-rise" && waterRise && <WaterRiseExplorer chart={waterRise} />}
        </>
      )}
    </section>
  );
}
