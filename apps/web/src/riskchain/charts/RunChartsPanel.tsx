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
/** Supplementary financial views for one immutable model run. They are kept
 * within the parent Financials tab so the results drawer has one navigation. */
export function RunChartsPanel({ run }: { run: CatModelRunResult }) {
  const [histogram, setHistogram] = useState<LossHistogram | null>(null);
  const [waterfall, setWaterfall] = useState<LossWaterfall | null>(null);
  const [waterRise, setWaterRise] = useState<WaterRiseSweep | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const finish = <T,>(setter: (value: T) => void) => (value: T) => { if (!cancelled) setter(value); };
    const fail = () => { if (!cancelled) setError("Supplementary chart data is unavailable for this run."); };
    void Promise.all([chartApi.lossHistogram(run.run_id), chartApi.waterfall(run.run_id), chartApi.waterRise(run.run_id)])
      .then(([histogramData, waterfallData, waterRiseData]) => { finish(setHistogram)(histogramData); finish(setWaterfall)(waterfallData); finish(setWaterRise)(waterRiseData); })
      .catch(fail);
    return () => { cancelled = true; };
  }, [run.run_id]);

  const loading = !histogram && !waterfall && !waterRise && !error;

  return (
    <section className={styles.panel} aria-label="Supplementary financial charts">
      {error && <div className={styles.errorState}>{error}</div>}
      {!error && loading && <div className={styles.loading}>Deriving chart from the stored run…</div>}
      {!error && !loading && (
        <div className={styles.chartStack}>
          {histogram && <LossHistogramChart chart={histogram} />}
          {waterfall && <LossWaterfallChart chart={waterfall} />}
          {waterRise && <WaterRiseExplorer chart={waterRise} />}
        </div>
      )}
    </section>
  );
}
