"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { PlaceSearchResult } from "@/lib/types";

export function TopSearchBar() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const setPanel = useAppStore((s) => s.setPanel);
  const flyTo = useAppStore((s) => s.flyTo);
  const savePlace = useAppStore((s) => s.savePlace);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(id);
  }, [query]);

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

  function handleAskQuestion() {
    if (!query.trim()) return;
    setPanel({ kind: "assistant", question: query.trim() });
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
    <div ref={containerRef} className="relative w-full max-w-xl">
      <label htmlFor="earthpulse-search" className="sr-only">
        Search a place, asset, event, route or ask a question
      </label>
      <input
        id="earthpulse-search"
        type="search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            if (results.length > 0) handleSelectPlace(results[0]);
            else handleAskQuestion();
          }
        }}
        placeholder="Search a place, asset, event, route or ask a question"
        className="w-full rounded-full border border-border bg-surface px-4 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
      />
      {open && debounced.trim().length > 0 && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-border bg-surface shadow-lg">
          {isFetching && <p className="px-4 py-2 text-xs text-foreground/60">Searching…</p>}
          {!isFetching && results.length === 0 && (
            <button
              type="button"
              onClick={handleAskQuestion}
              className="block w-full px-4 py-2 text-left text-sm hover:bg-surface-muted"
            >
              No places matched. Ask EarthPulse: <span className="font-medium">&ldquo;{query}&rdquo;</span>
            </button>
          )}
          <ul>
            {results.map((r) => (
              <li key={r.place_id}>
                <button
                  type="button"
                  onClick={() => handleSelectPlace(r)}
                  className="block w-full px-4 py-2 text-left text-sm hover:bg-surface-muted"
                >
                  {r.name}
                </button>
              </li>
            ))}
          </ul>
          {results.length > 0 && (
            <button
              type="button"
              onClick={handleAskQuestion}
              className="block w-full border-t border-border px-4 py-2 text-left text-xs text-accent hover:bg-surface-muted"
            >
              Ask EarthPulse instead: &ldquo;{query}&rdquo;
            </button>
          )}
        </div>
      )}
    </div>
  );
}
