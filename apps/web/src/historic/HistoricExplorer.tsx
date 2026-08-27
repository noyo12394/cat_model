"use client";

import { useRouter } from "next/navigation";
import { EventCard } from "./EventCard";
import { HistoricShell } from "./HistoricShell";
import {
  HISTORIC_ACTIONS,
  HISTORIC_EVENTS,
  historicDataset,
  historicEvent,
  type HistoricAction,
} from "./data";
import styles from "./HistoricExplorer.module.css";

type Props = {
  initialEventSlug?: string;
  initialDatasetSlug?: string;
  initialAction?: HistoricAction;
};

export function HistoricExplorer({ initialEventSlug, initialDatasetSlug, initialAction }: Props) {
  const router = useRouter();
  const event = initialEventSlug ? historicEvent(initialEventSlug) : undefined;
  const dataset = event && initialDatasetSlug ? historicDataset(event, initialDatasetSlug) : undefined;
  const selectedSource = dataset ? event?.sources.find((source) => source.id === dataset.source_id) : undefined;
  const action = initialAction ? HISTORIC_ACTIONS.find((item) => item.value === initialAction) : undefined;
  const step: 1 | 2 | 3 = dataset ? 3 : event ? 2 : 1;

  const selectEvent = (slug: string) => {
    const nextEvent = historicEvent(slug);
    router.push(nextEvent ? `/historic/${encodeURIComponent(nextEvent.slug)}` : "/historic", { scroll: false });
  };

  const selectDataset = (slug: string) => {
    if (!event) return;
    const nextDataset = historicDataset(event, slug);
    router.push(nextDataset ? `/historic/${encodeURIComponent(event.slug)}/${encodeURIComponent(nextDataset.slug)}` : `/historic/${encodeURIComponent(event.slug)}`, { scroll: false });
  };

  const selectAction = (value: string) => {
    if (!event || !dataset) return;
    const nextAction = HISTORIC_ACTIONS.find((item) => item.value === value);
    const base = `/historic/${encodeURIComponent(event.slug)}/${encodeURIComponent(dataset.slug)}`;
    router.push(nextAction ? `${base}?action=${nextAction.value}` : base, { scroll: false });
  };

  return <HistoricShell step={step}>
    <section className={styles.explorer}>
      <header className={styles.intro}>
        <span className="eyebrow">Five sourced United States catastrophes</span>
        <h1>Pick an event. Pick its data. Choose what to do.</h1>
        <p>This archive is intentionally simple. The three selections below are the whole workflow; missing source data stays visibly missing and every available figure resolves to an authoritative source.</p>
      </header>

      <div className={styles.flow} aria-label="Historic catastrophe explorer">
        <label className={styles.field}>
          <span><b>1</b> Select a catastrophe</span>
          <select value={event?.slug ?? ""} onChange={(change) => selectEvent(change.target.value)}>
            <option value="">Choose one of five events…</option>
            {HISTORIC_EVENTS.map((item) => <option key={item.slug} value={item.slug}>{item.name} · {item.start_date.slice(0, 4)} · {item.hazard}</option>)}
          </select>
          <small>Exactly five USA events, one for each hazard type.</small>
        </label>

        <label className={styles.field}>
          <span><b>2</b> Select what you want</span>
          <select disabled={!event} value={dataset?.slug ?? ""} onChange={(change) => selectDataset(change.target.value)}>
            <option value="">{event ? "Choose an available dataset…" : "Select a catastrophe first"}</option>
            {event?.datasets.map((item) => {
              const source = event.sources.find((candidate) => candidate.id === item.source_id);
              return <option key={item.slug} value={item.slug}>{item.name} — {item.provenance} · {item.resolution} · {source?.name} · {item.vintage}</option>;
            })}
          </select>
          <small>{dataset ? `${dataset.provenance} · ${dataset.unit}` : "Every option names its provenance, resolution, source, and vintage."}</small>
        </label>

        <label className={styles.field}>
          <span><b>3</b> Select an action</span>
          <select disabled={!dataset} value={action?.value ?? ""} onChange={(change) => selectAction(change.target.value)}>
            <option value="">{dataset ? "Choose what to do…" : "Select a dataset first"}</option>
            {HISTORIC_ACTIONS.map((item) => <option key={item.value} value={item.value}>{item.label} — {item.description}</option>)}
          </select>
          <small>{action?.description ?? "View on map, download a source bundle, or open authoritative reading."}</small>
        </label>
      </div>

      {event && dataset && <dl className={styles.selectionFacts} aria-label="Selected dataset details">
        <div><dt>Provenance</dt><dd>{dataset.provenance}</dd></div>
        <div><dt>Resolution</dt><dd>{dataset.resolution}</dd></div>
        <div><dt>Source</dt><dd>{selectedSource?.name ?? "Not available from manifest"}</dd></div>
        <div><dt>Vintage</dt><dd>{dataset.vintage}</dd></div>
      </dl>}

      {!event && <div className={styles.catalogNote}>
        <strong>Start with the first dropdown.</strong>
        <span>The catalog is fixed and source-reviewed for teaching: no hidden events, generated values, or speculative AI path.</span>
        <div className={styles.catalogList}>{HISTORIC_EVENTS.map((item) => <span key={item.slug}>{item.hazard_code} · {item.name} {item.start_date.slice(0, 4)}</span>)}</div>
      </div>}
      {event && !dataset && <div className={styles.prompt}><strong>Now choose a dataset.</strong><span>The second dropdown lists only datasets present in {event.name}&apos;s checked-in source manifest.</span></div>}
      {event && dataset && !action && <div className={styles.prompt}><strong>One final choice.</strong><span>Choose View on map, Download data, or Read more. That action is saved in the URL so this exact teaching state can be shared.</span></div>}
      {event && dataset && action && <EventCard key={`${event.slug}-${dataset.slug}-${action.value}`} event={event} selectedDataset={dataset} action={action.value} />}
    </section>
  </HistoricShell>;
}
