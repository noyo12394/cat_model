"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  CloudSun,
  FlaskConical,
  FolderKanban,
  Globe2,
  HeartPulse,
  History,
  MapPinned,
  RadioTower,
  ShieldAlert,
} from "lucide-react";
import { useAppStore } from "@/lib/store";

const ITEMS = [
  { href: "/", label: "Live", icon: RadioTower },
  { href: "/forecast", label: "Forecast", icon: CloudSun },
  { href: "/incidents/developing-flood-bethlehem", label: "Incidents", icon: ShieldAlert },
  { href: "/replay", label: "Replay", icon: History },
  { href: "/scenario-lab", label: "Model", icon: FlaskConical },
  { href: "/portfolio", label: "Portfolio", icon: FolderKanban },
];

export function LeftNavRail() {
  const pathname = usePathname();
  const collapsed = useAppStore((s) => s.navCollapsed);
  const toggleCollapsed = useAppStore((s) => s.toggleNavCollapsed);
  const setPanel = useAppStore((s) => s.setPanel);
  const setMapScope = useAppStore((s) => s.setMapScope);
  const setOffsetMinutes = useAppStore((s) => s.setOffsetMinutes);
  const flyTo = useAppStore((s) => s.flyTo);

  return (
    <nav aria-label="EarthPulse navigation" className={clsx("nav-rail", collapsed && "is-collapsed")}>
      <div className="nav-primary">
        <ul>
          {ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link href={item.href} className={clsx("nav-link", active && "is-active")} aria-current={active ? "page" : undefined} title={collapsed ? item.label : undefined}>
                  <Icon size={19} strokeWidth={active ? 2.4 : 1.9} aria-hidden />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="nav-secondary">
        <button type="button" className="nav-link" onClick={() => { setMapScope("global"); setOffsetMinutes(0); setPanel({ kind: "global-events" }); flyTo([8, 18], 1.45); }} title={collapsed ? "Global events" : undefined}>
          <Globe2 size={19} aria-hidden />{!collapsed && <span>Global events</span>}
        </button>
        <button type="button" className="nav-link" onClick={() => { setMapScope("local"); setPanel({ kind: "community", view: "sentiment", incidentId: "developing-flood-bethlehem" }); }} title={collapsed ? "Community" : undefined}>
          <HeartPulse size={19} aria-hidden />{!collapsed && <span>Community</span>}
        </button>
        <button type="button" className="nav-link" onClick={() => setPanel({ kind: "hidden-risks" })} title={collapsed ? "Hidden risks" : undefined}>
          <MapPinned size={19} aria-hidden />{!collapsed && <span>Hidden risks</span>}
        </button>
        <button type="button" className="nav-link" onClick={() => setPanel({ kind: "source-health" })} title={collapsed ? "Source health" : undefined}>
          <Bell size={19} aria-hidden />{!collapsed && <span>Source health</span>}
        </button>
        <button type="button" className="collapse-button" onClick={toggleCollapsed} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}>
          {collapsed ? <ChevronRight size={17} /> : <><ChevronLeft size={17} /><span>Collapse</span></>}
        </button>
      </div>
    </nav>
  );
}
