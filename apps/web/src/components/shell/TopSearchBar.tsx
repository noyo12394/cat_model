"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Clock3, MapPin, Search, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { PlaceSearchResult } from "@/lib/types";

const SUGGESTIONS = [
  "Lehigh University",
  "What changed near Bethlehem?",
  "Which hospital route has lower exposure?",
];

export function TopSearchBar() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const setPanel = useAppStore((s) => s.setPanel);
  const flyTo = useAppStore((s) => s.flyTo);
  const savePlace = useAppStore((s) => s.savePlace);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(id);
  }, [query]);

  useEffect(() => {
    function focusSearch(event: KeyboardEvent) {
      if (event.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", focusSearch);
    return () => document.removeEventListener("keydown", focusSearch);
  }, []);

  const { data, isFetching } = useQuery({
    queryKey: ["place-search", debounced],
    queryFn: () => api.searchPlaces(debounced),
    enabled: debounced.trim().length > 0,
  });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function handleAskQuestion(value = query) {
    if (!value.trim()) return;
    setQuery(value.trim());
    setPanel({ kind: "assistant", question: value.trim() });
    setOpen(false);
  }

  function handleSelectPlace(place: PlaceSearchResult) {
    setPanel({ kind: "place", placeId: place.place_id });
    flyTo(place.center, 14);
    savePlace(place);
    setQuery(place.name);
    setOpen(false);
  }

  const results = data?.results ?? [];

  return (
    <div ref={containerRef} className="global-search">
      <label htmlFor="earthpulse-search" className="sr-only">Search a place, asset, event, route or ask a question</label>
      <Search size={18} className="search-leading" aria-hidden />
      <input
        ref={inputRef}
        id="earthpulse-search"
        type="search"
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            if (results.length > 0) handleSelectPlace(results[0]);
            else handleAskQuestion();
          }
        }}
        placeholder="Search a place, event, route — or ask EarthPulse"
        role="combobox"
        aria-expanded={open}
        aria-controls="search-results"
        aria-autocomplete="list"
        autoComplete="off"
      />
      <kbd aria-hidden>/</kbd>

      {open && (
        <div id="search-results" className="search-popover">
          {query.trim().length === 0 ? (
            <div>
              <div className="search-popover-title"><Clock3 size={14} aria-hidden /> Try a search or question</div>
              {SUGGESTIONS.map((suggestion, index) => (
                <button
                  key={suggestion}
                  type="button"
                  className="search-result-row"
                  onClick={() => index === 0
                    ? handleSelectPlace({ place_id: "place-lehigh-university", name: suggestion, center: [-75.3785, 40.6084] })
                    : handleAskQuestion(suggestion)}
                >
                  {index === 0 ? <MapPin size={16} aria-hidden /> : <Sparkles size={16} aria-hidden />}
                  <span>{suggestion}</span><ArrowRight size={14} className="result-arrow" aria-hidden />
                </button>
              ))}
            </div>
          ) : (
            <>
              {isFetching && <div className="search-loading"><span /> Searching places and incidents…</div>}
              {!isFetching && results.map((result) => (
                <button key={result.place_id} type="button" onClick={() => handleSelectPlace(result)} className="search-result-row">
                  <span className="result-icon"><MapPin size={15} aria-hidden /></span>
                  <span><strong>{result.name}</strong><small>Place · Open location intelligence</small></span>
                  <ArrowRight size={14} className="result-arrow" aria-hidden />
                </button>
              ))}
              {!isFetching && (
                <button type="button" onClick={() => handleAskQuestion()} className="search-result-row ask-row">
                  <span className="result-icon"><Sparkles size={15} aria-hidden /></span>
                  <span><strong>Ask EarthPulse</strong><small>&ldquo;{query}&rdquo;</small></span>
                  <ArrowRight size={14} className="result-arrow" aria-hidden />
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
