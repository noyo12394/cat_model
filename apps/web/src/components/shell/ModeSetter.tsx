"use client";

import { useEffect } from "react";
import { useAppStore, type AppMode, type RightPanelContent } from "@/lib/store";

/** Tiny client component used by each route's page.tsx to put the shared
 * AppShell (which lives in the root layout, not in this route) into the
 * right mode/panel state on navigation. Renders nothing itself - the actual
 * UI is the persistent shell + RightPanelHost. */
export function ModeSetter({ mode, panel }: { mode: AppMode; panel?: RightPanelContent }) {
  const setMode = useAppStore((s) => s.setMode);
  const setPanel = useAppStore((s) => s.setPanel);

  const panelKey = panel ? JSON.stringify(panel) : undefined;
  useEffect(() => {
    setMode(mode);
    if (panel) setPanel(panel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, panelKey]);

  return null;
}
