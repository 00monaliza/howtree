"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { AnalysisPanel } from "@/components/panels/AnalysisPanel";
import { LayerToggle } from "@/components/panels/LayerToggle";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Skeleton } from "@/components/ui/skeleton";
import { MapPinned, Satellite, ScanLine } from "lucide-react";

const MapContainer = dynamic(
  () => import("@/components/map/MapContainer").then((m) => m.MapContainer),
  {
    ssr: false,
    loading: () => <Skeleton className="w-full h-full rounded-none" />,
  }
);

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="h-full flex overflow-hidden relative">
      {/* Sidebar toggle for mobile */}
      <Button
        size="sm"
        variant="outline"
        onClick={() => setSidebarOpen((v) => !v)}
        className="absolute top-3 left-3 z-20 lg:hidden border-border bg-card/90 backdrop-blur"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </Button>

      {/* Left sidebar */}
      <aside
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } transition-transform duration-200 absolute lg:relative z-10 h-full w-[320px] shrink-0 border-r border-border bg-card flex flex-col overflow-y-auto shadow-xl lg:shadow-none lg:translate-x-0`}
      >
        <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Analysis Control
          </h2>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-muted-foreground hover:text-foreground"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <AnalysisPanel />

        <Separator />

        <div className="py-3">
          <LayerToggle />
        </div>

        {/* Legend */}
        <div className="mt-auto px-4 py-3 border-t border-border">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Confidence
          </p>
          <div className="space-y-1">
            {[
              { color: "#22c55e", label: "≥ 90% — High" },
              { color: "#86efac", label: "≥ 70% — Medium-high" },
              { color: "#fbbf24", label: "≥ 50% — Medium" },
              { color: "#f87171", label: "< 50% — Low" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ background: color }}
                />
                <span className="text-xs text-muted-foreground">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Backdrop for mobile */}
      {sidebarOpen && (
        <div
          className="lg:hidden absolute inset-0 bg-black/50 z-[5]"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer />

        <div className="absolute right-4 top-4 hidden w-72 overflow-hidden rounded border border-border bg-card/90 shadow-xl backdrop-blur md:block">
          <div className="relative border-b border-border bg-[#091411] p-4">
            <div className="absolute -right-8 -top-10 h-28 w-28 rounded-full border border-emerald-200/15 bg-[radial-gradient(circle_at_35%_35%,rgba(134,239,172,0.34),rgba(20,83,45,0.24)_42%,transparent_72%)]" />
            <div className="relative flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded border border-emerald-300/25 bg-emerald-300/10">
                <Satellite className="h-5 w-5 text-emerald-200" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Geo workspace</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Спутниковая подложка, bbox-сетка и слой найденных крон в одном окне.
                </p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 divide-x divide-border">
            <div className="p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                <MapPinned className="h-3.5 w-3.5" />
                AOI
              </div>
              <p className="text-sm font-semibold text-foreground">Astana</p>
            </div>
            <div className="p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                <ScanLine className="h-3.5 w-3.5" />
                Mode
              </div>
              <p className="text-sm font-semibold text-foreground">BBOX</p>
            </div>
          </div>
        </div>

        {/* Floating info bar */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-card/90 backdrop-blur border border-border rounded px-3 py-1.5 text-xs font-mono text-muted-foreground pointer-events-none whitespace-nowrap">
          Зажми и протяни прямоугольник, чтобы выбрать область анализа
        </div>
      </div>

      {/* Floating AI Assistant */}
      <AssistantPanel />
    </div>
  );
}
