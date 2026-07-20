"use client";

import { useEffect, useState } from "react";
import type { CatModelRunResult } from "@/lib/types";
import { chartApi, runChartParams } from "./chartApi";
import type { LossHistogram, LossWaterfall, WaterRiseSweep } from "./chartTypes";
import { LossHistogramChart } from "./LossHistogramChart";
import { LossWaterfallChart } from "./LossWaterfallChart";
import { WaterRiseExplorer } from "./WaterRiseExplorer";
import styles from "./charts.module.css";

/** Supplementary financial views for one immutable model run. They are kept
 * within the parent Financials tab so the results drawer has one navigation.
 * The run's defining parameters are sent with every request so the charts still
 * render on a cold serverless instance that never saw the original run. */
export function RunChartsPanel({ run }: { run: CatModelRunResult }) {
  const [histogram, setHistogram] = useState<LossHistogram | null>(null);
  const [waterfall, setWaterfall] = useState<LossWaterfall | null>(null);
  const [waterRise, setWaterRise] = useState<WaterRiseSweep | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const params = runChartParams(run);
    const finish = <T,>(setter: (value: T) => void) => (value: T) => { if (!cancelled) setter(value); };
    const fail = (err: unknown) => {
      if (!cancelled) setError(err instanceof Error ? err.message : "Supplementary chart data is unavailable for this run.");
    };
    void Promise.all([
      chartApi.lossHistogram(run.run_id, params),
      chartApi.waterfall(run.run_id, params),
      chartApi.waterRise(run.run_id, params),
    ])
      .then(([histogramData, waterfallData, waterRiseData]) => {
        finish(setHistogram)(histogramData);
        finish(setWaterfall)(waterfallData);
        finish(setWaterRise)(waterRiseData);
      })
      .catch(fail);
    return () => { cancelled = true; };
  }, [run.run_id, run, attempt]);

  const loading = !histogram && !waterfall && !waterRise && !error;

  return (
    <section className={styles.panel} aria-label="Supplementary financial charts">
      {error && (
        <div className={styles.errorState}>
          <span>{error}</span>
          <button type="button" onClick={() => { setError(null); setHistogram(null); setWaterfall(null); setWaterRise(null); setAttempt((n) => n + 1); }}>
            Try again
          </button>
        </div>
      )}
      {!error && loading && <div className={styles.loading}>Deriving chart from the run…</div>}
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
