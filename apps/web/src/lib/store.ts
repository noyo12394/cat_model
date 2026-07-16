import { create } from "zustand";
import type { PlaceSearchResult } from "./types";

export type AppMode = "live" | "forecast" | "replay" | "scenario-lab" | "portfolio";

export type RightPanelContent =
  | { kind: "region-summary" }
  | { kind: "place"; placeId: string }
  | { kind: "incident"; incidentId: string }
  | { kind: "route"; originPlaceId: string; destinationPlaceId: string }
  | { kind: "assistant"; question: string }
  | { kind: "hidden-risks" }
  | { kind: "source-health" };

interface TimeState {
  /** Minutes offset from "now" the user is currently viewing, -10080..1440. */
  offsetMinutes: number;
  isPlaying: boolean;
  playbackSpeed: number;
}

interface LayerVisibility {
  hazards: boolean;
  infrastructure: boolean;
  population: boolean;
  intelligence: boolean;
  imagery: boolean;
}

interface AppState {
  mode: AppMode;
  setMode: (mode: AppMode) => void;

  panel: RightPanelContent;
  setPanel: (panel: RightPanelContent) => void;

  time: TimeState;
  setOffsetMinutes: (minutes: number) => void;
  togglePlaying: () => void;
  setPlaybackSpeed: (speed: number) => void;

  layers: LayerVisibility;
  toggleLayer: (key: keyof LayerVisibility) => void;

  uncertaintyLens: boolean;
  toggleUncertaintyLens: () => void;

  highContrast: boolean;
  toggleHighContrast: () => void;

  navCollapsed: boolean;
  toggleNavCollapsed: () => void;

  savedPlaces: PlaceSearchResult[];
  savePlace: (place: PlaceSearchResult) => void;
  removeSavedPlace: (placeId: string) => void;

  flyToTarget: { center: [number, number]; zoom?: number } | null;
  flyTo: (center: [number, number], zoom?: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  mode: "live",
  setMode: (mode) => set({ mode }),

  panel: { kind: "region-summary" },
  setPanel: (panel) => set({ panel }),

  time: { offsetMinutes: 0, isPlaying: false, playbackSpeed: 1 },
  setOffsetMinutes: (minutes) => set((s) => ({ time: { ...s.time, offsetMinutes: minutes } })),
  togglePlaying: () => set((s) => ({ time: { ...s.time, isPlaying: !s.time.isPlaying } })),
  setPlaybackSpeed: (speed) => set((s) => ({ time: { ...s.time, playbackSpeed: speed } })),

  layers: { hazards: true, infrastructure: true, population: false, intelligence: true, imagery: false },
  toggleLayer: (key) => set((s) => ({ layers: { ...s.layers, [key]: !s.layers[key] } })),

  uncertaintyLens: false,
  toggleUncertaintyLens: () => set((s) => ({ uncertaintyLens: !s.uncertaintyLens })),

  highContrast: false,
  toggleHighContrast: () => set((s) => ({ highContrast: !s.highContrast })),

  navCollapsed: false,
  toggleNavCollapsed: () => set((s) => ({ navCollapsed: !s.navCollapsed })),

  savedPlaces: [],
  savePlace: (place) =>
    set((s) => ({
      savedPlaces: s.savedPlaces.some((p) => p.place_id === place.place_id)
        ? s.savedPlaces
        : [...s.savedPlaces, place],
    })),
  removeSavedPlace: (placeId) =>
    set((s) => ({ savedPlaces: s.savedPlaces.filter((p) => p.place_id !== placeId) })),

  flyToTarget: null,
  flyTo: (center, zoom) => set({ flyToTarget: { center, zoom } }),
}));
