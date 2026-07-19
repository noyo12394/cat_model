"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Calculator, CheckCircle2, Database, Download, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { CatModelRunResult, DataCoverageItem, LossDistribution } from "@/lib/types";

function money(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1_000_000 ? 0 : 2,
  }).format(value);
}

function LossCard({ label, distribution }: { label: string; distribution: LossDistribution }) {
  return (
    <article className="rounded-xl border border-border bg-white/[0.025] p-3">
      <span className="text-[9px] font-bold uppercase tracking-[.12em] text-foreground/45">{label}</span>
      <strong className="mt-1 block font-mono text-lg text-foreground">{money(distribution.p50_usd)}</strong>
      <span className="mt-0.5 block text-[9px] text-foreground/55">
        p10–p90: {money(distribution.p10_usd)} – {money(distribution.p90_usd)}
      </span>
    </article>
  );
}

export function RiskModelPanel() {
  const [deductible, setDeductible] = useState(25_000);
  const [limit, setLimit] = useState(5_000_000);
  const [coinsurance, setCoinsurance] = useState(100);
  const [iterations, setIterations] = useState(2_000);
  const [result, setResult] = useState<CatModelRunResult | null>(null);
  const [coverage, setCoverage] = useState<DataCoverageItem[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.catDataCoverage().then(setCoverage).catch(() => setCoverage([]));
  }, []);

  const unavailable = useMemo(() => coverage.filter((item) => item.availability === "unavailable"), [coverage]);

  async function runModel() {
    setRunning(true);
    setError(null);
    try {
      setResult(await api.runCatFloodModel({
        scenario_label: "100-year Bethlehem flood — transparent demonstration",
        deductible_usd: Math.max(0, deductible),
        limit_usd: limit > 0 ? limit : null,
        coinsurance: Math.max(0, Math.min(1, coinsurance / 100)),
        seed: 12345,
        iterations,
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The model service is unavailable.");
    } finally {
      setRunning(false);
    }
  }

  function downloadManifest() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${result.run_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4 p-4">
      <header>
        <div className="flex items-center gap-2 text-accent">
          <Calculator size={16} aria-hidden />
          <span className="text-[9px] font-extrabold uppercase tracking-[.16em]">RiskChain model workspace</span>
        </div>
        <h1 className="mt-1 text-lg font-semibold">Bethlehem flood loss model</h1>
        <p className="mt-1 text-[10px] leading-relaxed text-foreground/60">
          Approved calculation services produce every number. The flood surface, assets and vulnerability curves in this release are synthetic demonstration inputs—not observed conditions or underwriting-grade values.
        </p>
      </header>

      <div className="rounded-xl border border-amber-400/25 bg-amber-400/[0.06] p-3 text-[9px] leading-relaxed text-amber-200/80">
        <div className="flex items-center gap-2 font-bold text-amber-200"><AlertTriangle size={14} /> Demonstration boundary</div>
        <p className="mt-1">No live flood depth is connected to this calculation. Population and claims are unavailable, so this model does not estimate people affected or claim calibration.</p>
      </div>

      <section className="space-y-3 rounded-xl border border-border p-3">
        <div className="grid grid-cols-2 gap-2">
          <label className="text-[9px] text-foreground/55">
            Deductible (USD)
            <input aria-label="Deductible in USD" type="number" min={0} value={deductible} onChange={(event) => setDeductible(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-2 text-xs text-foreground" />
          </label>
          <label className="text-[9px] text-foreground/55">
            Policy limit (USD)
            <input aria-label="Policy limit in USD" type="number" min={0} value={limit} onChange={(event) => setLimit(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-2 text-xs text-foreground" />
          </label>
          <label className="text-[9px] text-foreground/55">
            Coinsurance share (%)
            <input aria-label="Coinsurance share percent" type="number" min={0} max={100} value={coinsurance} onChange={(event) => setCoinsurance(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-2 text-xs text-foreground" />
          </label>
          <label className="text-[9px] text-foreground/55">
            Monte Carlo samples
            <select aria-label="Monte Carlo samples" value={iterations} onChange={(event) => setIterations(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-2 text-xs text-foreground">
              <option value={500}>500</option>
              <option value={2000}>2,000</option>
              <option value={5000}>5,000</option>
            </select>
          </label>
        </div>
        <button type="button" onClick={runModel} disabled={running} className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2.5 text-xs font-bold text-slate-950 disabled:opacity-50">
          <Calculator size={15} /> {running ? "Running approved calculation…" : "Run transparent flood model"}
        </button>
        {error && <p role="alert" className="text-[9px] text-red-300">Calculation failed: {error}</p>}
      </section>

      {result ? (
        <section className="space-y-3 border-t border-border pt-4" aria-live="polite">
          <div className="flex items-start justify-between gap-2">
            <div>
              <span className="rounded-full border border-amber-300/25 bg-amber-300/[0.07] px-2 py-1 text-[8px] font-bold uppercase text-amber-200">Modelled demo</span>
              <h2 className="mt-2 text-sm font-semibold">Loss distribution</h2>
            </div>
            <button type="button" onClick={downloadManifest} className="flex items-center gap-1 rounded-lg border border-border px-2 py-1.5 text-[8px] text-foreground/65"><Download size={12} /> JSON manifest</button>
          </div>

          <div className="space-y-2">
            <LossCard label="Ground-up economic loss" distribution={result.ground_up_distribution} />
            <LossCard label="Gross insured loss" distribution={result.gross_distribution} />
            <LossCard label="Net insured loss" distribution={result.net_insured_distribution} />
          </div>

          <div className="rounded-xl border border-violet-300/20 bg-violet-300/[0.04] p-3">
            <div className="flex items-center gap-2 text-[10px] font-semibold text-violet-200"><ShieldCheck size={14} /> Confidence: {result.confidence.band}</div>
            <p className="mt-1 text-[9px] leading-relaxed text-foreground/60">Largest uncertainty: {result.confidence.largest_uncertainty}</p>
            <ul className="mt-2 list-inside list-disc text-[8px] leading-relaxed text-foreground/50">{result.confidence.drivers.map((driver) => <li key={driver}>{driver}</li>)}</ul>
          </div>

          <div>
            <h3 className="text-[9px] font-bold uppercase tracking-[.12em] text-foreground/45">Model review</h3>
            <div className="mt-2 space-y-2">{result.audit_findings.map((finding) => (
              <article key={finding.code} className="rounded-lg border border-border p-2.5">
                <div className="flex items-center gap-2"><CheckCircle2 size={12} className={finding.severity === "high" ? "text-red-300" : "text-amber-200"} /><strong className="text-[10px]">{finding.title}</strong></div>
                <p className="mt-1 text-[8px] leading-relaxed text-foreground/55">{finding.detail}</p>
                <p className="mt-1 text-[8px] leading-relaxed text-accent/75">Next: {finding.recommendation}</p>
              </article>
            ))}</div>
          </div>

          <div className="rounded-xl border border-border p-3 text-[8px] leading-relaxed text-foreground/55">
            <div className="flex items-center gap-2 font-bold uppercase tracking-[.1em] text-foreground/70"><Database size={13} /> Resolution and provenance</div>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <dt>Analysis</dt><dd>{result.resolution.analysis_resolution}</dd>
              <dt>Hazard</dt><dd>{result.resolution.hazard_resolution}</dd>
              <dt>Assets</dt><dd>{result.asset_count} synthetic records</dd>
              <dt>Seed</dt><dd>{result.manifest.random_seed}</dd>
              <dt>Code</dt><dd>{result.manifest.code_version}</dd>
            </dl>
          </div>
        </section>
      ) : (
        <section className="rounded-xl border border-dashed border-border p-4 text-center text-[9px] leading-relaxed text-foreground/50">
          Run the model to see loss ranges, uncertainty, financial terms, audit findings and a reproducibility manifest.
        </section>
      )}

      <section>
        <h2 className="text-[9px] font-bold uppercase tracking-[.12em] text-foreground/45">Data availability</h2>
        <div className="mt-2 space-y-2">{coverage.map((item) => (
          <article key={item.layer_id} className="rounded-lg border border-border p-2.5">
            <div className="flex items-center justify-between gap-2"><strong className="text-[9px]">{item.label}</strong><span className={`text-[7px] font-bold uppercase ${item.availability === "unavailable" ? "text-red-300" : "text-amber-200"}`}>{item.availability.replaceAll("_", " ")}</span></div>
            <p className="mt-1 text-[8px] text-foreground/50">{item.source} · {item.geographic_resolution}</p>
          </article>
        ))}</div>
        {unavailable.length > 0 && <p className="mt-2 text-[8px] text-red-200/70">{unavailable.length} required data categories are unavailable and are excluded—not imputed.</p>}
      </section>
    </div>
  );
}
