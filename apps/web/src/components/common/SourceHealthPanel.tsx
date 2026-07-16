"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, CircleDashed, Database, ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

/** Partner-facing source operations view: availability, provenance posture,
 * interoperability, and explicit separation of live/demo/unavailable feeds. */
export function SourceHealthPanel() {
  const query = useQuery({ queryKey: ["source-health"], queryFn: api.sourceStatus, refetchInterval: 300_000 });
  const sources = query.data ?? [];
  const counts = {
    live: sources.filter((source) => source.status === "live").length,
    demo: sources.filter((source) => source.status === "demo").length,
    unavailable: sources.filter((source) => source.status === "unavailable").length,
  };

  return (
    <div className="source-ops-panel">
      <header className="source-ops-header">
        <div><span className="source-ops-icon"><ShieldCheck size={18} /></span><div><span className="panel-kicker">TRUST &amp; OPERATIONS</span><h1>Source health</h1></div></div>
        <p>Every integration reports its own state. Unavailable sources stay unavailable; demo fixtures are never relabeled as live.</p>
        <button type="button" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw size={12} className={query.isFetching ? "is-spinning" : ""} /> Recheck feeds</button>
      </header>

      {query.isLoading && <div className="global-loading"><span /><span /><span /> Checking authoritative sources…</div>}
      {query.isError && <div className="global-unavailable"><CircleDashed size={20} /><strong>Health service unavailable</strong><p>The map remains usable, but source status could not be verified.</p></div>}

      {sources.length > 0 && (
        <>
          <section className="source-health-summary" aria-label="Source status summary">
            <div><span className="feed-dot live" /><strong>{counts.live}</strong><small>live</small></div>
            <div><span className="feed-dot demo" /><strong>{counts.demo}</strong><small>demo</small></div>
            <div><span className="feed-dot unavailable" /><strong>{counts.unavailable}</strong><small>unavailable</small></div>
          </section>

          <section className="source-list" aria-label="Data source health">
            {sources.map((source) => (
              <article className={`source-card ${source.status}`} key={source.key}>
                <span className="source-state-icon">{source.status === "live" ? <CheckCircle2 size={15} /> : source.status === "demo" ? <Database size={15} /> : <CircleDashed size={15} />}</span>
                <div><strong>{source.display_name}</strong><small>{source.organization}</small><p>{source.detail}</p><time>{formatUtc(source.checked_at)}</time></div>
                <span className="source-status-pill">{source.status}</span>
              </article>
            ))}
          </section>

          <section className="interoperability-card">
            <div className="interoperability-title"><Activity size={15} /><div><span className="panel-kicker">PARTNER INTEGRATION</span><h2>Interoperability posture</h2></div></div>
            <dl>
              <div><dt>Event exchange</dt><dd>GeoJSON</dd></div>
              <div><dt>Alert semantics</dt><dd>GDACS MHEWS</dd></div>
              <div><dt>API contract</dt><dd>OpenAPI</dd></div>
              <div><dt>Time standard</dt><dd>UTC / ISO 8601</dd></div>
            </dl>
            <a href="https://cat-model-api.vercel.app/docs" target="_blank" rel="noreferrer">Open API documentation <ExternalLink size={11} /></a>
          </section>
        </>
      )}
    </div>
  );
}

function formatUtc(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}
