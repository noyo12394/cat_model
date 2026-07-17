"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  MessageSquare,
  ShieldQuestion,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { CertaintyBadge } from "@/components/common/Badges";
import type { CommunityPulseResponse, CommunityReport } from "@/lib/types";

const TABS = ["Overview", "Themes", "Signal vs. rumor", "Reports"] as const;
type Tab = (typeof TABS)[number];

const SENTIMENT_TONE: Record<string, string> = {
  alarmed: "sent-alarmed",
  concerned: "sent-concerned",
  seeking_info: "sent-seeking",
  calm: "sent-calm",
  relieved: "sent-relieved",
};

export function CommunityPulsePanel({ incidentId }: { incidentId: string }) {
  const [tab, setTab] = useState<Tab>("Overview");
  const setPanel = useAppStore((s) => s.setPanel);
  const flyTo = useAppStore((s) => s.flyTo);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["community-pulse", incidentId],
    queryFn: () => api.communityPulse(incidentId),
    staleTime: 60_000,
  });

  if (isLoading) return <div className="panel-stack panel-skeleton"><span /><span /><span /></div>;
  if (isError || !data)
    return (
      <div className="panel-empty">
        <TriangleAlert size={22} />
        <strong>Community Pulse unavailable</strong>
        <span>Official alerts and sensors remain the primary view.</span>
      </div>
    );

  return (
    <div className="community-panel">
      <header className="community-header">
        <div className="community-title-row">
          <span className="community-icon"><Users size={18} aria-hidden /></span>
          <div>
            <span className="panel-kicker">COMMUNITY PULSE · SENTIMENT</span>
            <h1>{data.region_label}</h1>
          </div>
          <span className="research-pill">DEMO</span>
        </div>
        <p className="community-caption">
          Social sensing from {data.total_reports} community reports · {data.window_label}. This is a
          supporting signal, <strong>not an official indicator</strong>.
        </p>
        <ConcernMeter data={data} />
      </header>

      <div className="community-tabs" role="tablist" aria-label="Community pulse views">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={tab === item}
            className={tab === item ? "is-active" : ""}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="community-content">
        {tab === "Overview" && <OverviewView data={data} />}
        {tab === "Themes" && <ThemesView data={data} />}
        {tab === "Signal vs. rumor" && <CorroborationView data={data} onFly={flyTo} />}
        {tab === "Reports" && <ReportsView data={data} onFly={flyTo} />}
      </div>

      <footer className="community-footer">
        <section className="responsible-use">
          <span className="panel-kicker">RESPONSIBLE USE</span>
          <ul>{data.responsible_use.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
        <button type="button" onClick={() => setPanel({ kind: "compound", eventId: "compound-flood-access-bethlehem" })}>
          Back to Compound Intelligence <ArrowRight size={14} />
        </button>
      </footer>
    </div>
  );
}

function ConcernMeter({ data }: { data: CommunityPulseResponse }) {
  const pct = Math.round(data.concern_index.score * 100);
  const TrendIcon = data.concern_index.trend === "rising" ? TrendingUp : data.concern_index.trend === "easing" ? TrendingDown : CircleDashed;
  return (
    <div className={`concern-meter band-${data.concern_index.band}`}>
      <div className="concern-meter-top">
        <div>
          <span className="concern-band">{data.concern_index.band_label}</span>
          <span className="concern-trend"><TrendIcon size={13} aria-hidden /> {data.concern_index.trend}</span>
        </div>
        <span className="concern-score" title={data.concern_index.method}>{pct}<small>/100</small></span>
      </div>
      <div className="concern-track" role="img" aria-label={`Community concern index ${pct} of 100, ${data.concern_index.band_label}`}>
        <span style={{ width: `${pct}%` }} />
      </div>
      <p className="concern-detail">{data.concern_index.trend_detail}</p>
      <p className="concern-method"><ShieldQuestion size={12} aria-hidden /> {data.concern_index.method}</p>
    </div>
  );
}

function OverviewView({ data }: { data: CommunityPulseResponse }) {
  return (
    <div className="community-view-stack">
      <section>
        <div className="community-section-heading">
          <span className="panel-kicker">SENTIMENT MIX</span>
          <h2>How people are reacting</h2>
        </div>
        <div className="sentiment-bars">
          {data.sentiment_breakdown.map((bucket) => (
            <div key={bucket.sentiment} className={`sentiment-row ${SENTIMENT_TONE[bucket.sentiment] ?? ""}`}>
              <span className="sentiment-label">{bucket.label}</span>
              <div className="sentiment-bar"><span style={{ width: `${Math.round(bucket.share * 100)}%` }} /></div>
              <span className="sentiment-count">{bucket.count}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="corroboration-strip">
        <div className="corr-chip corroborated"><CheckCircle2 size={15} /><strong>{data.corroboration.corroborated}</strong><small>match confirmed conditions</small></div>
        <div className="corr-chip uncorroborated"><CircleDashed size={15} /><strong>{data.corroboration.uncorroborated}</strong><small>unconfirmed</small></div>
        <div className="corr-chip conflicts"><TriangleAlert size={15} /><strong>{data.corroboration.conflicts}</strong><small>conflict / rumor</small></div>
      </section>
    </div>
  );
}

function ThemesView({ data }: { data: CommunityPulseResponse }) {
  return (
    <div className="community-view-stack">
      <div className="community-intro"><MessageSquare size={18} /><div><strong>What people are talking about</strong><p>Reports grouped by topic, ordered by volume.</p></div></div>
      <div className="theme-grid">
        {data.theme_clusters.map((cluster) => (
          <div key={cluster.theme} className={`theme-card ${SENTIMENT_TONE[cluster.dominant_sentiment] ?? ""}`}>
            <div className="theme-card-top">
              <strong>{cluster.label}</strong>
              <span className="theme-count">{cluster.count}</span>
            </div>
            <p className="theme-example">&ldquo;{cluster.example}&rdquo;</p>
            <small className="theme-corr">{cluster.corroboration_note}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function CorroborationView({ data, onFly }: { data: CommunityPulseResponse; onFly: (c: [number, number], z?: number) => void }) {
  const groups: { key: string; label: string; detail: string }[] = [
    { key: "corroborated", label: "Corroborated signal", detail: "Lines up with confirmed conditions - useful context." },
    { key: "uncorroborated", label: "Not yet confirmed", detail: "Plausible but unverified - needs a second source." },
    { key: "conflicts", label: "Conflicts with the facts", detail: "Contradicts confirmed conditions - treat as rumor." },
  ];
  return (
    <div className="community-view-stack">
      <div className="community-intro"><ShieldQuestion size={18} /><div><strong>Separating signal from rumor</strong><p>{data.corroboration.note}</p></div></div>
      {groups.map((group) => {
        const reports = data.reports.filter((r) => r.corroboration === group.key);
        if (reports.length === 0) return null;
        return (
          <section key={group.key} className={`corr-group ${group.key}`}>
            <div className="corr-group-head"><strong>{group.label}</strong><span>{reports.length}</span></div>
            <p className="corr-group-detail">{group.detail}</p>
            {reports.map((report) => <ReportCard key={report.report_id} report={report} onFly={onFly} />)}
          </section>
        );
      })}
    </div>
  );
}

function ReportsView({ data, onFly }: { data: CommunityPulseResponse; onFly: (c: [number, number], z?: number) => void }) {
  return (
    <div className="community-view-stack">
      <div className="community-intro"><MessageSquare size={18} /><div><strong>Raw community reports</strong><p>Newest first. Every report is user-reported or unverified.</p></div></div>
      <div className="report-feed">
        {data.reports.map((report) => <ReportCard key={report.report_id} report={report} onFly={onFly} showTime />)}
      </div>
      <section className="limitations-card">
        <span className="panel-kicker">LIMITATIONS</span>
        <ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </div>
  );
}

function ReportCard({ report, onFly, showTime }: { report: CommunityReport; onFly: (c: [number, number], z?: number) => void; showTime?: boolean }) {
  return (
    <button type="button" className={`report-card corr-${report.corroboration}`} onClick={() => onFly(report.center, 14)}>
      <div className="report-top">
        <span className={`sentiment-tag ${SENTIMENT_TONE[report.sentiment] ?? ""}`}>{report.sentiment.replace("_", " ")}</span>
        <CertaintyBadge value={report.certainty} />
        {showTime && <time>{new Date(report.posted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>}
      </div>
      <p className="report-text">&ldquo;{report.text}&rdquo;</p>
      <div className="report-meta">
        <span>{report.channel}</span>
        <span>·</span>
        <span>{report.location_label}</span>
      </div>
      <small className="report-corr">{report.corroboration_detail}</small>
    </button>
  );
}
