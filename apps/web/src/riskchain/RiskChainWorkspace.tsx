"use client";

import { type FormEvent, type KeyboardEvent as ReactKeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, BarChart3, BookOpen, Bot, CheckCircle2, ChevronDown, ClipboardCheck, Database, Dna,
  Download, ExternalLink, FlaskConical, Globe2, GraduationCap, Layers,
  Menu, Moon, Newspaper, Radio, RefreshCw, Search, ShieldCheck, SlidersHorizontal, Sun,
  UserRound, X,
} from "lucide-react";
import Link from "next/link";
import { api, ApiError, type GlobalEventQuery, type LiveWindow } from "@/lib/api";
import type {
  AnalysisLocation, AnalysisRunResult, CatModelRunResult, DataCoverageItem, GlobalEventsResponse,
  LearnLesson, LearnLessonSummary, NewsArticlesResponse, ResearchSearchResponse, RoadmapResponse,
  CopilotAnswer, GlobalEvent, ModelResultLayer, PlaceSearchResult, ProbabilisticResult, VulnerabilityFunction,
} from "@/lib/types";
import { RiskMap, type MapSelection, type MapViewport } from "./RiskMap";
import { ModelAnalytics } from "./ModelAnalytics";
import { ModelBuilder } from "./ModelBuilder";
import { AnalysisResults } from "./AnalysisResults";
import { EventTape } from "./EventTape";
import { GeoAgentPanel, type GeoAgentLayerState } from "./GeoAgentPanel";
import { WorkspaceMission } from "./WorkspaceMission";
import { EventGenome } from "./EventGenome";
import { CatastropheGenomeLab } from "./genome/CatastropheGenomeLab";
import { CatModelingActivity } from "./CatModelingActivity";

type View = "explore" | "model" | "results" | "live" | "news" | "activity" | "learn" | "research" | "genome";
type Panel = "none" | "layers" | "sources" | "results" | "ai" | "roadmap" | "account" | "genome";

const GENOME_LAB_ENABLED = process.env.NEXT_PUBLIC_FF_GENOME_LAB === "true";
const LIVE_ROLLING_ENABLED = process.env.NEXT_PUBLIC_FF_LIVE_ROLLING !== "false";
const HISTORIC_EVENTS_ENABLED = process.env.NEXT_PUBLIC_FF_HISTORIC_EVENTS !== "false";

const NAV: { id: View; label: string; icon: typeof Globe2 }[] = [
  { id: "explore", label: "Explore", icon: Globe2 },
  { id: "model", label: "Model", icon: FlaskConical },
  { id: "results", label: "Results", icon: BarChart3 },
  { id: "live", label: "Live", icon: Radio },
  { id: "news", label: "News", icon: Newspaper },
  ...(GENOME_LAB_ENABLED ? [{ id: "genome" as View, label: "Genome Lab", icon: Dna }] : []),
  { id: "activity", label: "FIRE Lab", icon: ClipboardCheck },
  { id: "learn", label: "Learn CAT", icon: GraduationCap },
  { id: "research", label: "Research", icon: BookOpen },
];

const LIVE_FILTERS = [
  { id: "all", label: "All", color: "#52606d" },
  { id: "flood", label: "Flood", color: "#1a73e8" },
  { id: "cyclone", label: "Cyclone", color: "#d93025" },
  { id: "earthquake", label: "Earthquake", color: "#7e57c2" },
  { id: "wildfire", label: "Wildfire", color: "#f4511e" },
  { id: "drought", label: "Drought", color: "#a56a21" },
  { id: "volcano", label: "Volcano", color: "#5f6368" },
];

const NEWS_FILTERS: { id: "all" | "flood" | "wildfire" | "earthquake" | "storm" | "drought" | "cat_model" | "resilience"; label: string }[] = [
  { id: "all", label: "All coverage" },
  { id: "flood", label: "Flood" },
  { id: "wildfire", label: "Wildfire" },
  { id: "earthquake", label: "Earthquake" },
  { id: "storm", label: "Storm" },
  { id: "drought", label: "Drought & heat" },
  { id: "cat_model", label: "CAT modelling" },
  { id: "resilience", label: "Resilience" },
];

type WorkspaceUser = { name: string; email: string };

function initialLiveParam(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  return new URLSearchParams(window.location.search).get(name) || fallback;
}

function dateTime(value?: string | null) {
  if (!value) return "Not reported";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}

function dollars(value?: number | null) {
  if (value == null) return "Not available";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: value >= 1_000_000 ? "compact" : "standard", maximumFractionDigits: 0 }).format(value);
}

function StatusBadge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "live" | "demo" | "warning" | "neutral" | "blocked" | "modelled" | "inferred" | "severe" }) {
  return <span className={`status-badge ${tone}`}>{children}</span>;
}

export function RiskChainWorkspace({ initialView = "explore" }: { initialView?: View }) {
  const [view, setView] = useState<View>(initialView);
  const [panel, setPanel] = useState<Panel>("none");
  const [operationsMode, setOperationsMode] = useState(false);
  const [professionalMode, setProfessionalMode] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [scope, setScope] = useState<"global" | "local">("global");
  const [hazard, setHazard] = useState("all");
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const [eventsResponse, setEventsResponse] = useState<GlobalEventsResponse | null>(null);
  const [news, setNews] = useState<NewsArticlesResponse | null>(null);
  const [newsHazard, setNewsHazard] = useState<"all" | "flood" | "wildfire" | "earthquake" | "storm" | "drought" | "cat_model" | "resilience">("all");
  const [newsHours, setNewsHours] = useState(24);
  const [newsLoading, setNewsLoading] = useState(false);
  const [coverage, setCoverage] = useState<DataCoverageItem[]>([]);
  const [lessons, setLessons] = useState<LearnLessonSummary[]>([]);
  const [lesson, setLesson] = useState<LearnLesson | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [run, setRun] = useState<CatModelRunResult | null>(null);
  const [analysisRun, setAnalysisRun] = useState<AnalysisRunResult | null>(null);
  const [analysisLocation, setAnalysisLocation] = useState<AnalysisLocation | null>(null);
  const [locationIntent, setLocationIntent] = useState(false);
  const [curves, setCurves] = useState<VulnerabilityFunction[]>([]);
  const [probabilistic, setProbabilistic] = useState<ProbabilisticResult | null>(null);
  const [modelLayer, setModelLayer] = useState<ModelResultLayer | null>(null);
  const [mapViewport, setMapViewport] = useState<MapViewport | null>(null);
  const [geoLayers, setGeoLayers] = useState<GeoAgentLayerState>({ events: true, analysis: true, demo: true, analysisOpacity: 0.25 });
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [placeResults, setPlaceResults] = useState<PlaceSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchInputFocused, setSearchInputFocused] = useState(false);
  const [activePlaceIndex, setActivePlaceIndex] = useState(-1);
  const suggestionRequest = useRef<AbortController | null>(null);
  const deductible = 100000;
  const limit = 5000000;
  const [researchQuery, setResearchQuery] = useState("validated flood depth-damage functions for commercial masonry buildings");
  const [research, setResearch] = useState<ResearchSearchResponse | null>(null);
  const [aiQuestion, setAiQuestion] = useState("Explain the largest uncertainty in this analysis.");
  const [aiAnswer, setAiAnswer] = useState<CopilotAnswer | null>(null);
  const [liveWindow, setLiveWindow] = useState<LiveWindow>(() => {
    const value = initialLiveParam("window", "30d");
    return (["24h", "7d", "30d", "90d", "ytd"] as string[]).includes(value) ? value as LiveWindow : "30d";
  });
  const [liveHazard, setLiveHazard] = useState(() => initialLiveParam("hazard", "all"));
  const [liveAlert, setLiveAlert] = useState(() => initialLiveParam("alert", "all"));
  const [liveRegion, setLiveRegion] = useState(() => initialLiveParam("region", ""));
  const [liveSearchDraft, setLiveSearchDraft] = useState(() => initialLiveParam("q", ""));
  const [liveSearch, setLiveSearch] = useState(() => initialLiveParam("q", ""));
  const [liveStartDate, setLiveStartDate] = useState(() => initialLiveParam("start_date", ""));
  const [liveEndDate, setLiveEndDate] = useState(() => initialLiveParam("end_date", ""));
  const [showLiveQuery, setShowLiveQuery] = useState(false);
  const [liveLoading, setLiveLoading] = useState(false);
  const [eventListLimit, setEventListLimit] = useState(12);
  const [user, setUser] = useState<WorkspaceUser | null>(() => {
    if (typeof window === "undefined") return null;
    try { return JSON.parse(window.localStorage.getItem("riskchain-demo-user") ?? "null") as WorkspaceUser | null; }
    catch { return null; }
  });
  const [accountName, setAccountName] = useState("");
  const [accountEmail, setAccountEmail] = useState("");

  useEffect(() => {
    void Promise.allSettled([api.catDataCoverage(), api.learnLessons(), api.roadmap(), api.catVulnerabilityFunctions()]).then((results) => {
      const [data, course, plan, vulnerability] = results;
      if (data.status === "fulfilled") setCoverage(data.value);
      if (course.status === "fulfilled") setLessons(course.value);
      if (plan.status === "fulfilled") setRoadmap(plan.value);
      if (vulnerability.status === "fulfilled") setCurves(vulnerability.value);
    });
  }, []);

  useEffect(() => {
    const hazardCode = ({ flood: "FL", cyclone: "TC", earthquake: "EQ", wildfire: "WF", drought: "DR", volcano: "VO" } as Record<string, string>)[liveHazard];
    const eventQuery: GlobalEventQuery = {
      window: LIVE_ROLLING_ENABLED ? liveWindow : undefined,
      hazard: LIVE_ROLLING_ENABLED ? hazardCode : undefined,
      alert: LIVE_ROLLING_ENABLED ? liveAlert : undefined,
      region: LIVE_ROLLING_ENABLED ? liveRegion : undefined,
      q: LIVE_ROLLING_ENABLED ? liveSearch : undefined,
      start_date: LIVE_ROLLING_ENABLED ? liveStartDate : undefined,
      end_date: LIVE_ROLLING_ENABLED ? liveEndDate : undefined,
    };
    let cancelled = false;
    const load = async () => {
      setLiveLoading(true);
      try {
        const response = await api.globalEvents(eventQuery);
        if (!cancelled) setEventsResponse(response);
      } catch {
        if (!cancelled) setNotice("The GDACS request failed. The last loaded snapshot remains visible where available.");
      } finally {
        if (!cancelled) setLiveLoading(false);
      }
    };
    void load();
    const refresh = window.setInterval(() => void load(), 300_000);
    if (view === "live") {
      const params = new URLSearchParams();
      params.set("window", liveWindow);
      if (liveHazard !== "all") params.set("hazard", liveHazard);
      if (liveAlert !== "all") params.set("alert", liveAlert);
      if (liveRegion) params.set("region", liveRegion);
      if (liveSearch) params.set("q", liveSearch);
      if (liveStartDate) params.set("start_date", liveStartDate);
      if (liveEndDate) params.set("end_date", liveEndDate);
      window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
    }
    return () => { cancelled = true; window.clearInterval(refresh); };
  }, [liveAlert, liveEndDate, liveHazard, liveRegion, liveSearch, liveStartDate, liveWindow, view]);

  useEffect(() => {
    if (view !== "news") return;
    let cancelled = false;
    void Promise.resolve().then(async () => {
      if (cancelled) return;
      setNewsLoading(true);
      try { setNews(await api.newsArticles(newsHazard, newsHours)); }
      catch {
        if (!cancelled) setNews({
          articles: [], data_status: "unavailable", retrieved_at: new Date().toISOString(), query_label: "Live news", hazard_filter: newsHazard, hours: newsHours,
          source_name: "GDELT DOC 2.0 Article List", source_url: "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
          notice: "The live article index is unavailable. No substitute headlines are shown.", error: "The live article index could not be reached.",
        });
      } finally { if (!cancelled) setNewsLoading(false); }
    });
    return () => { cancelled = true; };
  }, [view, newsHazard, newsHours]);

  useEffect(() => {
    const term = query.trim();
    if (!searchInputFocused || term.length < 3) {
      return;
    }
    let cancelled = false;
    const controller = new AbortController();
    suggestionRequest.current?.abort();
    suggestionRequest.current = controller;
    const timer = window.setTimeout(() => {
      setSearching(true);
      void api.suggestPlaces(term, controller.signal)
        .then((response) => {
          if (cancelled || controller.signal.aborted) return;
          setPlaceResults(response.results);
          setActivePlaceIndex(-1);
        })
        .catch(() => {
          if (!cancelled && !controller.signal.aborted) setPlaceResults([]);
        })
        .finally(() => {
          if (!cancelled && !controller.signal.aborted) setSearching(false);
        });
    }, 350);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      controller.abort();
      if (suggestionRequest.current === controller) suggestionRequest.current = null;
    };
  }, [query, searchInputFocused]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPanel("none");
        setPlaceResults([]);
      }
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  const events = useMemo(() => eventsResponse?.events ?? [], [eventsResponse]);
  const selectedOfficialEvent = useMemo<GlobalEvent | null>(() => selection?.status === "Officially reported" ? events.find((event) => event.event_id === selection.id) ?? null : null, [events, selection]);
  const visibleEvents = useMemo(() => {
    let filtered = events;
    if (liveHazard === "flood") filtered = filtered.filter((event) => /^(fl|flood)$/i.test(event.event_type));
    if (liveHazard === "earthquake") filtered = filtered.filter((event) => /^(eq|earthquake)$/i.test(event.event_type));
    if (liveHazard === "wildfire") filtered = filtered.filter((event) => /^(wf|fire|wildfire)$/i.test(event.event_type));
    if (liveHazard === "cyclone" || liveHazard === "wind") filtered = filtered.filter((event) => /^(tc|cyclone|storm|wind)$/i.test(event.event_type));
    if (liveHazard === "drought") filtered = filtered.filter((event) => /^(dr|drought)$/i.test(event.event_type));
    if (liveHazard === "volcano") filtered = filtered.filter((event) => /^(vo|volcano)$/i.test(event.event_type));
    const alertRank: Record<string, number> = { red: 3, orange: 2, green: 1 };
    return [...filtered].sort((a, b) => (alertRank[b.alert_level] ?? 0) - (alertRank[a.alert_level] ?? 0) || new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime());
  }, [events, liveHazard]);

  const onSelect = useCallback((next: MapSelection) => {
    setSelection(next);
    setPanel("none");
  }, []);
  function eventHazard(eventType: string) {
    if (/^(fl|flood)$/i.test(eventType)) return "flood";
    if (/^(eq|earthquake)$/i.test(eventType)) return "earthquake";
    if (/^(wf|fire|wildfire)$/i.test(eventType)) return "wildfire";
    if (/^(tc|cyclone|storm|wind)$/i.test(eventType)) return "wind";
    return "all";
  }

  function chooseView(next: View) {
    if (next === "genome" && !GENOME_LAB_ENABLED) return;
    setView(next);
    setMobileNav(false);
    setPanel("none");
    if (next === "model") {
      if (!selection) setScope("global");
      if (hazard === "all" || hazard === "cyclone" || hazard === "drought" || hazard === "volcano") setHazard("flood");
    }
    if (next === "live" || next === "news" || next === "explore" || (next === "genome" && GENOME_LAB_ENABLED) || next === "activity") setScope("global");
  }

  function openModelReadiness() {
    const event = selection ? events.find((item) => item.event_id === selection.id) : undefined;
    if (event) setHazard(eventHazard(event.event_type));
    setView("model");
    setPanel("none");
  }

  function openEventGenome() {
    if (!GENOME_LAB_ENABLED) return;
    if (!selectedOfficialEvent) {
      setNotice("Select an official event first. Event signatures only use source-backed event records.");
      return;
    }
    setPanel("genome");
  }

  function applyBethlehemDemo() {
    setHazard("flood");
    setScope("local");
    setView("model");
    setSelection({ id: "bethlehem-demo", title: "Bethlehem, Pennsylvania", subtitle: "Flood demonstration area", status: "Demo", source: "RiskChain approved demonstration engine", center: [-75.3705, 40.6259], zoom: 13 });
    setAnalysisLocation(null);
  }

  async function refreshEvents() {
    const hazardCode = ({ flood: "FL", cyclone: "TC", earthquake: "EQ", wildfire: "WF", drought: "DR", volcano: "VO" } as Record<string, string>)[liveHazard];
    setLiveLoading(true);
    try { setEventsResponse(await api.refreshGlobalEvents({ window: liveWindow, hazard: hazardCode, alert: liveAlert, region: liveRegion, q: liveSearch, start_date: liveStartDate, end_date: liveEndDate })); }
    catch { setNotice("The official GDACS feed could not be refreshed. Existing events were not relabelled as current."); }
    finally { setLiveLoading(false); }
  }

  async function refreshNews() {
    setNewsLoading(true);
    try { setNews(await api.newsArticles(newsHazard, newsHours, true)); }
    catch { setNews({
      articles: [], data_status: "unavailable", retrieved_at: new Date().toISOString(), query_label: "Live news", hazard_filter: newsHazard, hours: newsHours,
      source_name: "GDELT DOC 2.0 Article List", source_url: "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
      notice: "The live article index is unavailable. No substitute headlines are shown.", error: "The live article index could not be reached.",
    }); }
    finally { setNewsLoading(false); }
  }

  function signInDemo(event: FormEvent) {
    event.preventDefault();
    const name = accountName.trim();
    const email = accountEmail.trim();
    if (!name || !email || !email.includes("@")) return;
    const next = { name, email };
    window.localStorage.setItem("riskchain-demo-user", JSON.stringify(next));
    setUser(next);
  }

  function signOutDemo() {
    window.localStorage.removeItem("riskchain-demo-user");
    setUser(null);
    setAccountName("");
    setAccountEmail("");
  }

  async function searchLocation(event: FormEvent) {
    event.preventDefault();
    const normalized = query.trim().toLowerCase();
    if (!normalized) return;
    // A submitted search has a different, source-backed fallback. Abort the
    // debounce request first so both providers are not asked for the same
    // place and the button always reflects the request that will be used.
    suggestionRequest.current?.abort();
    suggestionRequest.current = null;
    setSearchInputFocused(false);
    setPanel("none");
    setPlaceResults([]);
    setActivePlaceIndex(-1);
    setNotice(null);
    const match = events.find((item) => `${item.name} ${item.country} ${item.event_type}`.toLowerCase().includes(normalized));
    if (match) {
      setSelection({ id: match.event_id, title: match.name, subtitle: `${match.event_type} · ${match.country}`, status: "Officially reported", source: match.source, center: match.center });
      setScope("global");
      return;
    }
    const coordinateMatch = normalized.match(/^\s*(-?\d{1,2}(?:\.\d+)?)\s*[, ]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/);
    if (coordinateMatch) {
      const lat = Number(coordinateMatch[1]);
      const lon = Number(coordinateMatch[2]);
      if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
        void selectGeocodedPlace({ place_id: `coordinates-${lat}-${lon}`, name: `${lat.toFixed(5)}, ${lon.toFixed(5)}`, center: [lon, lat], provider: "User-supplied coordinates", data_status: "live", zoom: 13 });
        return;
      }
    }
    setSearching(true);
    try {
      const response = await api.searchPlaces(query.trim());
      if (response.results.length === 1) {
        await selectGeocodedPlace(response.results[0]);
      } else if (response.results.length > 1) {
        setPlaceResults(response.results);
      } else {
        setNotice("No source-backed place match was found. Add a city, state, postcode or country and try again.");
      }
    } catch {
      setNotice("Place search is temporarily unavailable. The map was not moved and no location was guessed.");
    } finally {
      setSearching(false);
    }
  }

  async function selectGeocodedPlace(place: PlaceSearchResult) {
    let resolved = place;
    setSearching(true);
    try {
      const geography = await api.resolvePlace(place);
      resolved = { ...place, ...geography, bbox: place.bbox ?? geography.bbox };
    } catch {
      setNotice("The place was located, but Census state/county/tract lookup is unavailable. Analysis remains blocked until geography is resolved.");
    } finally {
      setSearching(false);
    }
    setQuery(resolved.name);
    setPlaceResults([]);
    setActivePlaceIndex(-1);
    setSearchInputFocused(false);
    setScope("global");
    setView(locationIntent ? "model" : "explore");
    setLocationIntent(false);
    setAnalysisLocation({
      place_id: resolved.place_id, name: resolved.name, center: resolved.center, bbox: resolved.bbox,
      state: resolved.state, state_fips: resolved.state_fips, county: resolved.county,
      county_fips: resolved.county_fips, tract: resolved.tract, tract_geoid: resolved.tract_geoid,
      geography_vintage: resolved.geography_vintage,
    });
    setSelection({
      id: resolved.place_id,
      title: resolved.name.split(",").slice(0, 2).join(","),
      subtitle: [resolved.name, resolved.county, resolved.tract].filter(Boolean).join(" · "),
      status: "Geocoded location",
      source: resolved.tract_geoid ? `${resolved.provider ?? "Place search provider"} + U.S. Census Geocoder` : resolved.provider ?? "Place search provider",
      center: resolved.center,
      zoom: resolved.zoom ?? 12,
    });
  }

  function handleSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && placeResults.length > 0) {
      event.preventDefault();
      setActivePlaceIndex((index) => Math.min(index + 1, placeResults.length - 1));
      return;
    }
    if (event.key === "ArrowUp" && placeResults.length > 0) {
      event.preventDefault();
      setActivePlaceIndex((index) => Math.max(index - 1, 0));
      return;
    }
    if (event.key === "Escape") {
      setPlaceResults([]);
      setActivePlaceIndex(-1);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      if (activePlaceIndex >= 0 && activePlaceIndex < placeResults.length) {
        void selectGeocodedPlace(placeResults[activePlaceIndex]);
      } else {
        event.currentTarget.form?.requestSubmit();
      }
    }
  }

  async function executeDemoRun() {
    setLoading(true);
    setNotice(null);
    try {
      const result = await api.runCatFloodModel({
        scenario_label: "100-year flood event — Bethlehem demonstration",
        deductible_usd: deductible,
        limit_usd: limit || null,
        coinsurance: 1,
        seed: 12345,
        iterations: 2000,
      });
      setAnalysisRun(null);
      setRun(result);
      setPanel("results");
      void api.catVulnerabilityFunctions().then(setCurves).catch(() => setCurves([]));
      // This stateless backend calculation is anchored to the immutable run
      // response, avoiding volatile in-process storage between Vercel calls.
      void api.catProbabilisticPreview(result.ground_up_distribution.p50_usd).then(setProbabilistic).catch(() => setProbabilistic(null));
      void api.catRunLayer(result.run_id, "damage-ratio").then(setModelLayer).catch(() => setModelLayer(null));
      if (user) {
        const recent = JSON.parse(window.localStorage.getItem("riskchain-recent-runs") ?? "[]") as { run_id: string; label: string; p50: number; created_at: string }[];
        window.localStorage.setItem("riskchain-recent-runs", JSON.stringify([{ run_id: result.run_id, label: result.scenario_label, p50: result.ground_up_distribution.p50_usd, created_at: result.manifest.created_at }, ...recent].slice(0, 5)));
      }
    } catch (error) {
      setNotice(error instanceof ApiError ? `Model service error (${error.status}). No result was invented.` : "The model service is unavailable. No result was invented.");
    } finally {
      setLoading(false);
    }
  }

  function startGuidedDemo() {
    applyBethlehemDemo();
    window.setTimeout(() => void executeDemoRun(), 0);
  }

  function focusPlaceSearch() {
    setLocationIntent(view === "model");
    setNotice(null);
    window.setTimeout(() => document.getElementById("global-place-search")?.focus(), 0);
  }

  async function openLesson(id: string) {
    setLoading(true);
    try { setLesson(await api.learnLesson(id)); } catch { setNotice("Lesson detail is temporarily unavailable."); }
    finally { setLoading(false); }
  }

  async function searchResearch(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try { setResearch(await api.researchSearch(researchQuery, "flood")); }
    catch { setNotice("The governed research index is temporarily unavailable."); }
    finally { setLoading(false); }
  }

  async function askCopilot(event: FormEvent) {
    event.preventDefault();
    if (!aiQuestion.trim()) return;
    setLoading(true);
    try {
      const answer = await api.queryCopilot(aiQuestion.trim(), { hazard: analysisRun?.hazard_type ?? hazard, location_label: scope === "local" ? "Bethlehem / Lehigh Valley, PA" : selection?.title, run_id: run?.run_id ?? analysisRun?.run_id, interface_mode: professionalMode ? "professional" : "guided" });
      setAiAnswer(answer);
    } catch (error) {
      setAiAnswer(null);
      setNotice(error instanceof ApiError ? `Geospatial agent: ${error.message}` : "The grounded agent is unavailable. It will not answer without approved backend tools.");
    }
    finally { setLoading(false); }
  }

  function exportRun() {
    if (!run) return;
    const blob = new Blob([JSON.stringify(run, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${run.run_id}-manifest.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function exportAnalysisRun() {
    if (!analysisRun) return;
    const blob = new Blob([JSON.stringify(analysisRun.manifest, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${analysisRun.run_id}-manifest.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className={`riskchain-app ${(operationsMode || view === "model" || view === "results" || view === "live" || view === "news" || view === "genome") ? "operations terminal" : "light"}`}>
      <a href="#workspace" className="skip-link">Skip to map workspace</a>
      <header className="topbar">
        <button className="icon-button mobile-menu" onClick={() => setMobileNav((value) => !value)} aria-label={mobileNav ? "Close navigation" : "Open navigation"} aria-expanded={mobileNav} aria-controls="primary-navigation"><Menu size={20} /></button>
        <button className="brand" onClick={() => chooseView("explore")} aria-label="RiskChain home">
          <span className="brand-glyph"><Activity size={19} /></span>
          <span>Risk<span>Chain</span></span>
          <small>CAT intelligence</small>
        </button>
        <form className="map-search" onSubmit={(event) => void searchLocation(event)}>
          <Search size={19} />
          <input
            id="global-place-search"
            value={query}
            onFocus={() => setSearchInputFocused(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              if (event.target.value.trim().length < 3) setPlaceResults([]);
              setSearchInputFocused(true);
              setActivePlaceIndex(-1);
            }}
            onKeyDown={handleSearchKeyDown}
            placeholder="Search a place, event, coordinates or ZIP"
            aria-label="Search location or event"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={searchInputFocused && (searching || placeResults.length > 0)}
            aria-controls="place-search-results"
            aria-activedescendant={activePlaceIndex >= 0 ? `place-option-${activePlaceIndex}` : undefined}
          />
          {query && <button className="search-clear" type="button" onClick={() => { setQuery(""); setPlaceResults([]); setAnalysisLocation(null); setSelection(null); }} aria-label="Clear location search"><X size={15} /></button>}
          <button type="submit" disabled={searching} aria-label={searching ? "Finding place" : "Search place"}><Search size={16} /><span>{searching ? "Finding…" : "Search"}</span></button>
          {searchInputFocused && (searching || query.trim().length >= 3) && <div id="place-search-results" className="place-results" role="listbox" aria-label="Place search suggestions">
            <div className="place-results-head"><span>{searching ? "Finding places…" : "Choose a place"}</span><button type="button" onClick={() => { setPlaceResults([]); setActivePlaceIndex(-1); }} aria-label="Close place results"><X size={15} /></button></div>
            {!searching && placeResults.length === 0 && <div className="place-empty">No suggestions found. Press Search to try the submit geocoder.</div>}
            {placeResults.map((place, index) => <button id={`place-option-${index}`} className={activePlaceIndex === index ? "active" : ""} type="button" role="option" aria-selected={activePlaceIndex === index} key={place.place_id} onMouseDown={(event) => event.preventDefault()} onClick={() => void selectGeocodedPlace(place)}><Globe2 size={16} /><span><strong>{place.name.split(",").slice(0, 2).join(",")}</strong><small>{place.name}</small></span></button>)}
            <p>↑↓ to choose · Enter to select · position only, not a risk result · suggestions by Photon/Komoot · © OpenStreetMap contributors</p>
          </div>}
        </form>
        <div className="top-actions">
          <button className="mode-button" onClick={() => setProfessionalMode((value) => !value)}><SlidersHorizontal size={17} /> {professionalMode ? "Professional" : "Guided"}</button>
          <button className="icon-button" onClick={() => setOperationsMode((value) => !value)} aria-label="Toggle operations mode">{operationsMode ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button className="account-button" onClick={() => setPanel("account")}><UserRound size={17} /> {user ? user.name.split(" ")[0] : "Sign in"}</button>
          <button className="primary compact agent-launch" onClick={() => setPanel("ai")} aria-label="Open geospatial agent"><Bot size={17} /><span>Ask AI</span></button>
        </div>
      </header>

      <nav id="primary-navigation" className={`nav-tabs ${mobileNav ? "open" : ""}`} aria-label="Primary">
        {NAV.map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => chooseView(item.id)}><item.icon size={17} />{item.label}</button>)}
      </nav>

      <section id="workspace" className="workspace">
        <RiskMap
          events={geoLayers.events && scope === "global" ? visibleEvents : []}
          scope={scope}
          operationsMode={operationsMode || view === "model" || view === "live" || view === "news" || view === "genome"}
          hazard={hazard}
          focus={selection?.center}
          focusZoom={selection?.zoom}
          modelLayer={geoLayers.demo ? modelLayer : null}
          modelRun={run}
          analysisLayer={geoLayers.analysis ? analysisRun?.hazard_layers[0] : null}
          analysisOpacity={geoLayers.analysisOpacity}
          showDemoLayer={geoLayers.demo}
          onSelect={onSelect}
          onViewportChange={setMapViewport}
        />

        {view !== "genome" && view !== "activity" && <div className="map-toolbar">
          <button className={panel === "layers" ? "active" : ""} onClick={() => setPanel(panel === "layers" ? "none" : "layers")}><Layers size={17} /> Layers <ChevronDown size={14} /></button>
          <button onClick={() => setScope(scope === "global" ? "local" : "global")}><Globe2 size={17} /> {scope === "global" ? "Global" : "Bethlehem"}</button>
          <button onClick={() => setPanel(panel === "sources" ? "none" : "sources")}><Database size={17} /> Sources</button>
        </div>}

        {view !== "genome" && view !== "activity" && <button className="workspace-about" onClick={() => setPanel("roadmap")}>About & roadmap</button>}

        {(view === "explore" || view === "live") && <EventTape events={geoLayers.events ? visibleEvents : []} onSelect={onSelect} />}

        {GENOME_LAB_ENABLED && view === "genome" && <CatastropheGenomeLab liveEvents={events} onSelectLive={(next) => { onSelect(next); setView("live"); }} />}

        {view === "activity" && <CatModelingActivity
          events={events}
          eventsResponse={eventsResponse}
          curves={curves}
          onInspectEvent={(event) => {
            onSelect({ id: event.event_id, title: event.name, subtitle: `${event.event_type} · ${event.country}`, status: "Officially reported", source: event.source, center: event.center, zoom: 6 });
            setView("live");
          }}
          onOpenLive={() => chooseView("live")}
          onRunDemo={startGuidedDemo}
          onOpenLesson={(lessonId) => { setView("learn"); void openLesson(lessonId); }}
        />}

        {view === "explore" && <section className="floating-card intro-card">
          <StatusBadge tone="live">Map-first workspace</StatusBadge>
          <h1>Understand catastrophe risk, one place at a time.</h1>
          <p>For risk teams and public-sector planners: follow official events, test governed scenarios, and inspect every source, assumption, and limit.</p>
          <div className="intro-actions"><button className="primary" onClick={() => chooseView("live")}><Radio size={17} /> See live events</button><button onClick={startGuidedDemo}><FlaskConical size={17} /> Explore modelled demo</button></div>
          <p className="intro-helper">Runs the sample model and opens the result map with Markers, Columns, and Hexbins.</p>
          <div className="trust-row"><span><ShieldCheck size={15} /> Sources visible</span><span><CheckCircle2 size={15} /> Ranges, not false precision</span></div>
        </section>}

        {view === "explore" && !selection && <WorkspaceMission
          mode="explore"
          eventCount={visibleEvents.length}
          eventStatus={eventsResponse?.data_status}
          hasDemoResult={Boolean(run || modelLayer)}
          hasAnalysisResult={Boolean(analysisRun)}
          onFocusSearch={focusPlaceSearch}
          onOpenLive={() => chooseView("live")}
          onRunDemo={startGuidedDemo}
          onOpenResults={() => setPanel("results")}
        />}

        {view === "model" && <ModelBuilder
          location={analysisLocation}
          onRequestLocation={() => {
            setLocationIntent(true);
            setNotice("Search above and select a suggestion. RiskChain will resolve its county and Census tract before enabling the scenario.");
            window.setTimeout(() => document.getElementById("global-place-search")?.focus(), 0);
          }}
          onDemo={async () => { applyBethlehemDemo(); await executeDemoRun(); }}
          onResult={(result) => { setAnalysisRun(result); setHazard(result.hazard_type === "hurricane" ? "cyclone" : result.hazard_type); setRun(null); setProbabilistic(null); setModelLayer(null); setPanel("results"); }}
          onNotice={(message) => setNotice(message)}
        />}

        {view === "model" && <WorkspaceMission
          mode="model"
          placeName={analysisLocation?.name}
          eventCount={visibleEvents.length}
          eventStatus={eventsResponse?.data_status}
          hasDemoResult={Boolean(run || modelLayer)}
          hasAnalysisResult={Boolean(analysisRun)}
          onFocusSearch={focusPlaceSearch}
          onOpenLive={() => chooseView("live")}
          onRunDemo={startGuidedDemo}
          onOpenResults={() => { setView("results"); setPanel("results"); }}
        />}

        {view === "results" && <section className="floating-card results-home-card">
          <div className="card-heading"><div><span className="eyebrow">Analysis workspace</span><h2>{run ? "Latest model result" : analysisRun ? "Latest exposure screening" : "No result open"}</h2></div>{run ? <StatusBadge tone="demo">Modelled demo</StatusBadge> : analysisRun ? <StatusBadge tone="live">Source-backed</StatusBadge> : <StatusBadge>Awaiting run</StatusBadge>}</div>
          {run ? <>
            <p className="results-home-lead">Review the loss range, assumptions, vulnerability functions, and model audit together—before using this result in a decision.</p>
            <div className="results-home-grid"><div><span>Median loss</span><strong className="number-value">{dollars(run.ground_up_distribution.p50_usd)}</strong></div><div><span>Range</span><strong className="number-value">{dollars(run.ground_up_distribution.range_low_usd)}–{dollars(run.ground_up_distribution.range_high_usd)}</strong></div><div><span>Modelled assets</span><strong className="number-value">{run.asset_count}</strong></div></div>
            <div className="results-home-actions"><button className="primary" onClick={() => setPanel("results")}><BarChart3 size={16} /> Open analysis</button><button onClick={() => chooseView("model")}><FlaskConical size={16} /> Change scenario</button></div>
            <p className="results-home-note"><ShieldCheck size={15} /> Demonstration values are modelled inputs, not observations, claims, or a property valuation.</p>
          </> : analysisRun ? <>
            <p className="results-home-lead">This run returned exposure screening because the approved engine did not have compatible asset-level hazard intensity for a loss calculation.</p>
            <div className="results-home-grid"><div><span>Structures</span><strong className="number-value">{analysisRun.totals.structures?.toLocaleString() ?? "Not available"}</strong></div><div><span>Population</span><strong className="number-value">{analysisRun.totals.population?.toLocaleString() ?? "Not available"}</strong></div><div><span>Confidence</span><strong>{analysisRun.confidence.overall}</strong></div></div>
            <div className="results-home-actions"><button className="primary" onClick={() => setPanel("results")}><ShieldCheck size={16} /> Open audit</button><button onClick={() => chooseView("model")}><FlaskConical size={16} /> Change scenario</button></div>
          </> : <>
            <p className="results-home-lead">A result will appear here only after you run a connected model or approved exposure screen. RiskChain does not create placeholder loss numbers.</p>
            <div className="results-empty-path"><span>01 · Select a place</span><span>02 · Set a scenario</span><span>03 · Run and inspect</span></div>
            <div className="results-home-actions"><button className="primary" onClick={() => chooseView("model")}><FlaskConical size={16} /> Build a scenario</button><button onClick={startGuidedDemo}><ShieldCheck size={16} /> Open demo result</button></div>
          </>}
        </section>}

        {view === "live" && !selection && <section className="floating-card live-card">
          <div className="live-mode-toggle" aria-label="Event archive mode"><button className="active" type="button">Live</button>{HISTORIC_EVENTS_ENABLED && <Link href="/historic">Historic</Link>}</div>
          <div className="card-heading"><div><span className="eyebrow">Official event picture</span><h2>Recent GDACS events</h2></div><div className="live-head-actions"><StatusBadge tone={eventsResponse?.feed_state === "feed_ok" ? "live" : "warning"}>{liveLoading ? "loading" : eventsResponse?.feed_state?.replaceAll("_", " ") ?? "checking"}</StatusBadge><button className="icon-button" onClick={() => void refreshEvents()} aria-label="Refresh official events" disabled={liveLoading}><RefreshCw size={15} /></button></div></div>
          {LIVE_ROLLING_ENABLED && eventsResponse?.auto_widened && <p className="live-widen-notice"><AlertTriangle size={13} /> No events matched {eventsResponse.requested_window}; widened automatically to {eventsResponse.effective_window}.</p>}
          {LIVE_ROLLING_ENABLED && <div className="live-window-tabs" aria-label="GDACS time window">{([['24h','24h'],['7d','7d'],['30d','30d'],['90d','90d'],['ytd','Year to date (2026)']] as [LiveWindow,string][]).map(([value,label]) => <button type="button" key={value} className={liveWindow === value ? "active" : ""} onClick={() => { setLiveWindow(value); setLiveStartDate(""); setLiveEndDate(""); setEventListLimit(12); }}>{label}</button>)}</div>}
          <div className="live-stats"><div><strong>{eventsResponse?.counts.total ?? "—"}</strong><span>events</span></div><div><strong>{eventsResponse?.counts.red ?? "—"}</strong><span>red</span></div><div><strong>{eventsResponse?.counts.orange ?? "—"}</strong><span>orange</span></div></div>
          <div className="live-freshness"><span><Database size={13} /> GDACS MHEWS API</span><span>Last successful poll {dateTime(eventsResponse?.last_successful_poll_at)}</span><span>Window {eventsResponse?.window_start ?? "—"} → {eventsResponse?.window_end ?? "—"}</span><span className={eventsResponse?.feed_state === "feed_degraded" ? "stale" : "fresh"}>{eventsResponse?.feed_state === "feed_degraded" ? "Cached / partial snapshot" : "Official feed response"}</span></div>
          <div className="hazard-filter">{LIVE_FILTERS.map((item) => <button key={item.id} className={liveHazard === item.id ? "active" : ""} onClick={() => { setLiveHazard(item.id); setHazard(item.id); setEventListLimit(12); }}>{item.label}</button>)}</div>
          <div className="live-alert-filters" aria-label="GDACS alert filter">{["all", "green", "orange", "red"].map((level) => <button type="button" key={level} className={liveAlert === level ? `active ${level}` : level} onClick={() => setLiveAlert(level)}>{level === "all" ? "All alerts" : level}</button>)}</div>
          <form className="gdacs-search" onSubmit={(event) => { event.preventDefault(); setLiveSearch(liveSearchDraft.trim()); setEventListLimit(12); }}>
            <label><span>Search name, event ID, or country</span><input value={liveSearchDraft} onChange={(event) => setLiveSearchDraft(event.target.value)} placeholder="e.g. EQ-1561994 or Japan" /></label>
            <label><span>Region</span><input value={liveRegion} onChange={(event) => setLiveRegion(event.target.value)} placeholder="Country or region" /></label>
            <div><label><span>From</span><input type="date" value={liveStartDate} onChange={(event) => setLiveStartDate(event.target.value)} /></label><label><span>To</span><input type="date" value={liveEndDate} onChange={(event) => setLiveEndDate(event.target.value)} /></label></div>
            <button className="primary" type="submit" disabled={liveLoading}><Search size={14} /> {liveLoading ? "Searching official feed…" : "Search GDACS"}</button>
          </form>
          <div className="live-controls"><button type="button" onClick={() => setShowLiveQuery((value) => !value)}>{showLiveQuery ? "Hide query" : "Show query"}</button><span>{Math.min(eventListLimit, visibleEvents.length)} of {visibleEvents.length} listed · map shows all</span></div>
          {showLiveQuery && <div className="gdacs-query"><strong>{eventsResponse?.query_endpoint ?? "GDACS endpoint unavailable"}</strong><pre>{JSON.stringify(eventsResponse?.query_parameters ?? {}, null, 2)}</pre></div>}
          <div className="event-list">{visibleEvents.slice(0, eventListLimit).map((event) => <button key={event.event_id} onClick={() => onSelect({ id: event.event_id, title: event.name, subtitle: `${event.event_type} · ${event.country}`, status: "Officially reported", source: event.source, center: event.center, zoom: 7 })}><i className={event.alert_level} /><span><strong>{event.name}</strong><small>{event.event_id} · {event.country} · {dateTime(event.from_date)}</small></span><ExternalLink size={15} /></button>)}</div>
          {eventListLimit < visibleEvents.length && <button className="event-load-more" type="button" onClick={() => setEventListLimit((value) => Math.min(value + 24, visibleEvents.length))}>Show 24 more official records</button>}
          {eventsResponse?.possibly_truncated && <p className="catalog-limit"><AlertTriangle size={13} /> The documented {eventsResponse.result_cap}-record retrieval cap was reached. Older matching GDACS records may exist.</p>}
          {!liveLoading && !visibleEvents.length && <div className="empty-live rich"><strong>{eventsResponse?.feed_state === "feed_error" ? "GDACS request failed" : "No qualifying events in this window"}</strong><span>Feed: {eventsResponse?.source_name ?? "GDACS"}</span><span>Last successful poll: {dateTime(eventsResponse?.last_successful_poll_at)}</span><span>Window queried: {eventsResponse?.effective_window ?? liveWindow}</span><button type="button" onClick={() => setLiveWindow(liveWindow === "24h" ? "7d" : liveWindow === "7d" ? "30d" : liveWindow === "30d" ? "90d" : "ytd")}>Widen window</button>{eventsResponse?.error && <p>{eventsResponse.error}</p>}</div>}
          <p className="microcopy">GDACS information supports awareness and coordination; follow national and local authorities for warnings.</p>
        </section>}

        {view === "news" && <section className="floating-card content-card news-card">
          <div className="card-heading">
            <div><span className="eyebrow">Publisher-linked article index</span><h2>Latest hazard, CAT &amp; resilience coverage</h2></div>
            <div className="live-head-actions"><StatusBadge tone={news?.data_status === "live" ? "live" : "warning"}>{news?.data_status ?? "loading"}</StatusBadge><button className="icon-button" onClick={() => void refreshNews()} aria-label="Refresh live news" disabled={newsLoading}><RefreshCw size={15} /></button></div>
          </div>
          <p className="news-lead">A live, worldwide view of publisher headlines about natural hazards, catastrophe modelling, and resilience. It remains separate from official alerts, observations, and CAT-model inputs.</p>
          <div className="news-controls">
            <div className="hazard-filter" aria-label="News hazard filter">{NEWS_FILTERS.map((item) => <button key={item.id} className={newsHazard === item.id ? "active" : ""} onClick={() => setNewsHazard(item.id)}>{item.label}</button>)}</div>
            <label>Window<select value={newsHours} onChange={(event) => setNewsHours(Number(event.target.value))}><option value={24}>Last 24 hours</option><option value={72}>Last 72 hours</option><option value={168}>Last 7 days</option></select></label>
          </div>
          <div className="news-provenance"><Database size={14} /><span><strong>{news?.source_name ?? "GDELT DOC 2.0 Article List"}</strong><small>{news ? `${news.articles.length} article records · retrieved ${dateTime(news.retrieved_at)}` : "Connecting to the article index…"}</small></span></div>
          {newsLoading && <div className="empty-live">Refreshing publisher-linked article records…</div>}
          {!newsLoading && news?.data_status === "live" && <div className="news-list">{news.articles.map((article) => <a key={article.article_id} href={article.url} target="_blank" rel="noreferrer"><span className="news-source">{article.publisher_domain}</span><div><h3>{article.title}</h3><small>{dateTime(article.published_at)}{article.source_country ? ` · ${article.source_country}` : ""}{article.language ? ` · ${article.language}` : ""}</small></div><ExternalLink size={16} aria-hidden="true" /></a>)}</div>}
          {!newsLoading && news?.data_status === "live" && news.articles.length === 0 && <div className="empty-live">No matching publisher records were returned for this time window.</div>}
          {!newsLoading && news?.data_status === "unavailable" && <div className="news-unavailable"><AlertTriangle size={17} /><div><strong>Live article index unavailable</strong><p>{news.error ?? news.notice}</p></div></div>}
          <p className="microcopy">{news?.notice ?? "Headlines are publisher-reported leads, not verified observations or model outputs."}</p>
        </section>}

        {view === "learn" && <section className="floating-card content-card learn-card">
          <div className="card-heading"><div><span className="eyebrow">Learn while modelling</span><h2>{lesson?.title ?? "Learn CAT"}</h2></div>{lesson && <button className="icon-button" onClick={() => setLesson(null)} aria-label="Close lesson"><X size={17} /></button>}</div>
          {lesson ? <article className="lesson-detail"><p className="lead">{lesson.one_sentence}</p><h3>Plain language</h3><p>{lesson.plain_language}</p><h3>Technical definition</h3><p>{lesson.technical_definition}</p>{lesson.formula && <code>{lesson.formula}</code>}<div className="learning-warning"><strong>Common mistake</strong>{lesson.common_mistake}</div><h3>Knowledge check</h3><p>{lesson.knowledge_check.question}</p>{lesson.knowledge_check.options.map((option, index) => <div className="answer-option" key={option}>{String.fromCharCode(65 + index)} · {option}</div>)}</article> : <div className="lesson-list">{lessons.map((item) => <button key={item.lesson_id} onClick={() => void openLesson(item.lesson_id)}><span>{String(item.order).padStart(2, "0")}</span><div><strong>{item.title}</strong><small>{item.one_sentence}</small></div></button>)}</div>}
        </section>}

        {view === "research" && <section className="floating-card content-card research-card">
          <span className="eyebrow">Governed formula discovery</span><h2>Research methods, not mystery formulas.</h2><p>Search a curated index of real technical references. A result can enter the model only after independent implementation, testing, and human review.</p>
          <form className="research-search" onSubmit={searchResearch}><input value={researchQuery} onChange={(event) => setResearchQuery(event.target.value)} /><button className="primary" type="submit"><Search size={16} /> Search</button></form>
          {research && <><div className="source-state-row">{research.source_status.map((source) => <StatusBadge key={source.source} tone={source.status === "unavailable" ? "blocked" : "neutral"}>{source.source}: {source.status}</StatusBadge>)}</div><div className="paper-list">{research.results.map((paper) => <article key={paper.paper_id}><StatusBadge>{paper.human_review_status}</StatusBadge><h3>{paper.title}</h3><p>{paper.publisher}{paper.year ? ` · ${paper.year}` : ""}</p><small>{paper.peer_review_status} · relevance {(paper.relevance * 100).toFixed(0)}%</small></article>)}</div><p className="microcopy">{research.notice}</p></>}
        </section>}

        {panel === "layers" && <aside className="floating-card compact-panel layers-panel"><div className="card-heading"><div><span className="eyebrow">Visible workspace</span><h2>Map layers</h2></div><button className="icon-button" onClick={() => setPanel("none")} aria-label="Close map layers"><X size={16} /></button></div><label className="layer-switch"><span><strong>Official event markers</strong><small>GDACS locations; not impact footprints</small></span><input type="checkbox" checked={geoLayers.events} onChange={(event) => setGeoLayers({ ...geoLayers, events: event.target.checked })} /></label><label className="layer-switch"><span><strong>Analysis footprint</strong><small>{analysisRun ? "Published geometry from current run" : "No analysis result on map"}</small></span><input type="checkbox" disabled={!analysisRun} checked={geoLayers.analysis && Boolean(analysisRun)} onChange={(event) => setGeoLayers({ ...geoLayers, analysis: event.target.checked })} /></label><label className="layer-switch"><span><strong>Modelled demo layer</strong><small>{run || modelLayer ? "Labelled sample result" : "Open guided demo to activate"}</small></span><input type="checkbox" disabled={!run && !modelLayer} checked={geoLayers.demo && Boolean(run || modelLayer)} onChange={(event) => setGeoLayers({ ...geoLayers, demo: event.target.checked })} /></label><label className="layer-opacity"><span>Footprint opacity</span><strong className="number-value">{Math.round(geoLayers.analysisOpacity * 100)}%</strong><input type="range" min="10" max="80" step="5" value={Math.round(geoLayers.analysisOpacity * 100)} onChange={(event) => setGeoLayers({ ...geoLayers, analysisOpacity: Number(event.target.value) / 100 })} /></label><div className="layer-filter-title">Event filter</div>{LIVE_FILTERS.map((item) => <button key={item.id} className={`layer-row ${hazard === item.id ? "active" : ""}`} onClick={() => setHazard(item.id)}><i style={{ background: item.color }} /><span><strong>{item.label}</strong><small>Filter official event locations</small></span></button>)}<div className="future-layer-note"><Database size={14} /><span><strong>Future connectors</strong>PostGIS boundaries, Sentinel-2, Overture roads and 3D buildings are not configured in this deployment.</span></div></aside>}

        {selection && (view === "explore" || view === "live") && panel === "none" && <aside className="floating-card selection-card"><button className="card-close" onClick={() => setSelection(null)} aria-label="Close selection"><X size={17} /></button><StatusBadge tone={selection.status === "Demo" ? "demo" : selection.status === "Geocoded location" ? "neutral" : "live"}>{selection.status}</StatusBadge><h2>{selection.title}</h2><p>{selection.subtitle}</p>{GENOME_LAB_ENABLED && selectedOfficialEvent && <EventGenome event={selectedOfficialEvent} compact />}<dl><div><dt>Source</dt><dd>{selection.source}</dd></div>{selectedOfficialEvent && <><div><dt>Official alert</dt><dd>{selectedOfficialEvent.alert_level}{selectedOfficialEvent.alert_score == null ? "" : ` · score ${selectedOfficialEvent.alert_score}`}</dd></div><div><dt>Last update</dt><dd>{dateTime(selectedOfficialEvent.modified_at)}</dd></div></>}<div><dt>Coordinates</dt><dd>{selection.center[1].toFixed(5)}, {selection.center[0].toFixed(5)}</dd></div><div><dt>Interpretation</dt><dd>{selection.status === "Demo" ? "Scenario input; not a current observation" : selection.status === "Geocoded location" ? "Map position only; no hazard or risk has been calculated here" : "Reported event location; not an impact footprint"}</dd></div></dl>{selection.status === "Demo" ? <button className="primary" onClick={() => chooseView("model")}>Open model</button> : <><button className="primary readiness-button" onClick={openModelReadiness}><FlaskConical size={15} /> Check model readiness</button>{selection.status === "Officially reported" && <>{GENOME_LAB_ENABLED && <button className="secondary-link event-genome-link" type="button" onClick={openEventGenome}><Database size={15} /> Expand 3D event signature</button>}<a className="secondary-link" href={events.find((item) => item.event_id === selection.id)?.report_url} target="_blank" rel="noreferrer">Open official report <ExternalLink size={15} /></a></>}</>}</aside>}

        {panel === "sources" && <><button className="drawer-backdrop" onClick={() => setPanel("none")} aria-label="Close source coverage" /><aside className="drawer source-drawer"><div className="drawer-head"><div><span className="eyebrow">Data quality</span><h2>Source & coverage</h2></div><button className="icon-button" onClick={() => setPanel("none")} aria-label="Close source coverage panel"><X size={18} /></button></div><p className="drawer-intro">Every layer states whether it is live, modelled, inferred, demo, or unavailable. Different resolutions are never blended silently.</p><section className="operational-source"><div><StatusBadge tone={eventsResponse?.data_status === "live" && !eventsResponse.stale ? "live" : "warning"}>{eventsResponse?.stale ? "stale" : eventsResponse?.data_status ?? "loading"}</StatusBadge><span><strong>Global event metadata</strong><small>UN–European Commission GDACS MHEWS API</small></span></div><dl><div><dt>Records retrieved</dt><dd>{eventsResponse?.counts.total ?? "Not available"}</dd></div><div><dt>Retrieved</dt><dd>{dateTime(eventsResponse?.fetched_at)}</dd></div><div><dt>Latest source update</dt><dd>{dateTime(eventsResponse?.source_updated_at)}</dd></div><div><dt>Map meaning</dt><dd>Reported event center; not an impact footprint</dd></div></dl></section><p className="coverage-label">CAT model input layers</p><div className="coverage-summary"><span><strong>{coverage.filter((item) => item.availability === "available_live").length}</strong> live CAT</span><span><strong>{coverage.filter((item) => item.availability === "available_demo").length}</strong> demo CAT</span><span><strong>{coverage.filter((item) => item.availability === "unavailable").length}</strong> unavailable</span></div><div className="coverage-list">{coverage.map((item) => <details key={item.layer_id}><summary><StatusBadge tone={item.availability === "available_live" ? "live" : item.availability === "available_demo" ? "demo" : "blocked"}>{item.availability.replaceAll("_", " ")}</StatusBadge><span><strong>{item.label}</strong><small>{item.source}</small></span><ChevronDown size={15} /></summary><dl><div><dt>Use</dt><dd>{item.use_in_run}</dd></div><div><dt>Resolution</dt><dd>{item.geographic_resolution}</dd></div><div><dt>Origin</dt><dd>{item.attribute_origin.replaceAll("_", " ")}</dd></div></dl>{item.limitations[0] && <p>{item.limitations[0]}</p>}</details>)}</div></aside></>}

        {panel === "results" && run && <aside className="results-drawer analytics-drawer"><div className="drawer-head"><div><StatusBadge tone="demo">Demo · modelled inputs</StatusBadge><h2>{run.scenario_label}</h2><p>{run.region_label}</p></div><button className="icon-button" onClick={() => setPanel("none")} aria-label="Close model results"><X size={18} /></button></div><ModelAnalytics run={run} curves={curves} probabilistic={probabilistic} /><div className="drawer-actions"><button className="primary" onClick={exportRun}><Download size={16} /> Download manifest</button><button onClick={() => setPanel("ai")}><Bot size={16} /> Explain result</button></div><p className="microcopy">Bundled sample demonstration; values are not observations or a current event.</p></aside>}
        {panel === "results" && analysisRun && !run && <aside className="results-drawer analytics-drawer"><div className="drawer-head"><div><StatusBadge tone="live">Source-backed screening</StatusBadge><h2>{analysisRun.title}</h2><p>{analysisRun.geography?.name ?? analysisRun.provider_event_id ?? "Selected event"} · run {analysisRun.run_id.slice(0, 12)}</p></div><button className="icon-button" onClick={() => setPanel("none")} aria-label="Close analysis results"><X size={18} /></button></div><AnalysisResults result={analysisRun} onDownload={exportAnalysisRun} /></aside>}

        {panel === "account" && <><button className="drawer-backdrop" onClick={() => setPanel("none")} aria-label="Close account" /><aside className="drawer account-drawer"><div className="drawer-head"><div><span className="eyebrow">User workspace</span><h2>{user ? `Welcome, ${user.name}` : "Sign in to RiskChain"}</h2></div><button className="icon-button" onClick={() => setPanel("none")} aria-label="Close account"><X size={18} /></button></div>{user ? <div className="account-signed-in"><div className="account-avatar">{user.name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase()}</div><h3>{user.name}</h3><p>{user.email}</p><section><strong>Workspace status</strong><span>Browser-only demonstration profile</span><span>Runs saved on this device only</span><span>No private portfolio data uploaded</span></section><button onClick={signOutDemo}>Sign out</button></div> : <form className="account-form" onSubmit={signInDemo}><p>Create a local demonstration profile to keep recent run references on this device. This is not production authentication and does not create a cloud account.</p><label>Name<input value={accountName} onChange={(event) => setAccountName(event.target.value)} required autoComplete="name" /></label><label>Email<input type="email" value={accountEmail} onChange={(event) => setAccountEmail(event.target.value)} required autoComplete="email" /></label><button className="primary" type="submit"><UserRound size={16} /> Continue to demo workspace</button><div className="method-note"><ShieldCheck size={16} /><p>A production release requires an identity provider, server-side sessions, organization roles, tenant isolation and audit logging.</p></div></form>}</aside></>}

        {GENOME_LAB_ENABLED && panel === "genome" && selectedOfficialEvent && <aside className="drawer event-genome-drawer"><div className="drawer-head"><div><span className="eyebrow">Official metadata visualisation</span><h2>Event Genome</h2><p>{selectedOfficialEvent.name} · {selectedOfficialEvent.source}</p></div><button className="icon-button" onClick={() => setPanel("none")} aria-label="Close event signature"><X size={18} /></button></div><EventGenome event={selectedOfficialEvent} /></aside>}

        {panel === "ai" && <GeoAgentPanel onClose={() => setPanel("none")} view={view} scope={scope} hazard={analysisRun?.hazard_type ?? hazard} selection={selection} viewport={mapViewport} visibleEventCount={geoLayers.events ? visibleEvents.length : 0} analysisRun={analysisRun} hasDemoRun={Boolean(run || modelLayer)} layers={geoLayers} onLayersChange={setGeoLayers} question={aiQuestion} onQuestionChange={setAiQuestion} answer={aiAnswer} loading={loading} onSubmit={askCopilot} />}

        {panel === "roadmap" && <aside className="drawer"><div className="drawer-head"><div><span className="eyebrow">Honest delivery status</span><h2>Product roadmap</h2></div><button className="icon-button" onClick={() => setPanel("none")}><X size={18} /></button></div><div className="roadmap-list">{roadmap?.milestones.map((item) => <article key={`${item.stage}-${item.name}`}><StatusBadge tone={item.status === "done" ? "live" : "neutral"}>{item.status.replaceAll("_", " ")}</StatusBadge><span className="budget">{item.budget_band} effort · {item.timeline}</span><h3>{item.name}</h3><p>{item.acceptance_gate}</p><small>Owner: {item.owner_role}</small></article>)}</div><p className="microcopy">{roadmap?.notice}</p></aside>}
      </section>

      {notice && <div className="toast" role="alert"><AlertTriangle size={18} /><span>{notice}</span><button onClick={() => setNotice(null)}><X size={16} /></button></div>}
    </main>
  );
}
