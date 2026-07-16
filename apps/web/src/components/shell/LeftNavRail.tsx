"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useAppStore } from "@/lib/store";

const ITEMS = [
  { href: "/", label: "Live", icon: "◉" },
  { href: "/forecast", label: "Forecast", icon: "◈" },
  { href: "/incidents/developing-flood-bethlehem", label: "Incidents", icon: "▲" },
  { href: "/replay", label: "Replay", icon: "⟲" },
  { href: "/scenario-lab", label: "Scenario Lab", icon: "⚙" },
  { href: "/portfolio", label: "Portfolio", icon: "▦" },
];

const UTILITY_ITEMS = [
  { href: "/sources", label: "Source Health", icon: "❖" },
];

export function LeftNavRail() {
  const pathname = usePathname();
  const collapsed = useAppStore((s) => s.navCollapsed);
  const toggleCollapsed = useAppStore((s) => s.toggleNavCollapsed);
  const layers = useAppStore((s) => s.layers);
  const toggleLayer = useAppStore((s) => s.toggleLayer);
  const uncertaintyLens = useAppStore((s) => s.uncertaintyLens);
  const toggleUncertaintyLens = useAppStore((s) => s.toggleUncertaintyLens);

  return (
    <nav
      aria-label="EarthPulse navigation"
      className={clsx(
        "flex h-full flex-col justify-between border-r border-border bg-surface py-2 transition-all",
        collapsed ? "w-14" : "w-48",
      )}
    >
      <div>
        <button
          type="button"
          onClick={toggleCollapsed}
          className="mb-2 w-full px-3 py-1.5 text-left text-xs text-foreground/60 hover:text-foreground"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
        >
          {collapsed ? "»" : "« Collapse"}
        </button>
        <ul className="space-y-0.5">
          {ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-2 px-3 py-2 text-sm font-medium",
                    active ? "bg-surface-muted text-accent" : "text-foreground/80 hover:bg-surface-muted",
                  )}
                >
                  <span aria-hidden>{item.icon}</span>
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>

        {!collapsed && (
          <div className="mt-4 border-t border-border px-3 pt-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-foreground/50">Layers</p>
            <ul className="mt-1 space-y-1 text-sm">
              {(Object.keys(layers) as (keyof typeof layers)[]).map((key) => (
                <li key={key}>
                  <label className="flex items-center gap-2 capitalize">
                    <input type="checkbox" checked={layers[key]} onChange={() => toggleLayer(key)} />
                    {key}
                  </label>
                </li>
              ))}
            </ul>
            <label className="mt-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={uncertaintyLens} onChange={toggleUncertaintyLens} />
              Uncertainty lens
            </label>
          </div>
        )}
      </div>

      <ul className="space-y-0.5 border-t border-border pt-2">
        {UTILITY_ITEMS.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-foreground/70 hover:bg-surface-muted"
            >
              <span aria-hidden>{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
