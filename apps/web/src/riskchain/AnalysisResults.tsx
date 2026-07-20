"use client";

import { AlertTriangle, CheckCircle2, Database, Download, ShieldCheck, XCircle } from "lucide-react";
import type { AnalysisRunResult } from "@/lib/types";

function value(value: number | null | undefined, kind: "number" | "money" = "number") {
  if (value == null) return "Not available";
  return kind === "money" ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value) : value.toLocaleString();
}

export function AnalysisResults({ result, onDownload }: { result: AnalysisRunResult; onDownload: () => void }) {
  return <div className="screening-results">
    <div className="screening-banner"><ShieldCheck size={20} /><div><strong>Exposure screening</strong><p>No loss was calculated because compatible asset-level hazard intensity is unavailable.</p></div></div>
    <div className="result-grid"><div><span>Structures in footprint</span><strong>{value(result.totals.structures)}</strong></div><div><span>Population represented</span><strong>{value(result.totals.population)}</strong></div><div><span>Structure value</span><strong>{value(result.totals.structure_value_usd, "money")}</strong></div><div><span>Contents value</span><strong>{value(result.totals.contents_value_usd, "money")}</strong></div></div>
    <section><h3>Component status</h3><div className="component-status">{Object.entries(result.component_status).map(([name, status]) => <div key={name}>{status === "loaded" ? <CheckCircle2 size={15} /> : <XCircle size={15} />}<span><strong>{name}</strong>{status}</span></div>)}</div></section>
    <section className="confidence-card"><ShieldCheck size={20} /><div><strong>{result.confidence.overall} confidence</strong><p>{result.confidence.explanation}</p></div></section>
    <section><h3>Audit and sources</h3><div className="source-records">{((result.manifest.sources as Array<Record<string, string>>) ?? []).map((source, index) => <article key={`${source.dataset}-${index}`}><Database size={15} /><span><strong>{source.dataset}</strong>{source.provider} · {source.status}<small>{source.note}</small></span></article>)}</div></section>
    <section><h3>Important limitations</h3><ul className="limitations-list">{result.limitations.map((item) => <li key={item}><AlertTriangle size={14} />{item}</li>)}</ul></section>
    <button className="primary manifest-button" type="button" onClick={onDownload}><Download size={16} /> Download JSON manifest</button>
  </div>;
}

