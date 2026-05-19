"use client";

import { useMapStore } from "@/lib/store/mapStore";
import type { MapLayer } from "@/types";

const LAYERS: { id: MapLayer; label: string; icon: string }[] = [
  { id: "points", label: "Tree Points", icon: "●" },
  { id: "heatmap", label: "Heatmap", icon: "◉" },
  { id: "districts", label: "Districts", icon: "▦" },
];

export function LayerToggle() {
  const { activeLayers, toggleLayer } = useMapStore();

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-4">
        Layers
      </p>
      <div className="px-4 space-y-1">
        {LAYERS.map(({ id, label, icon }) => {
          const active = activeLayers.has(id);
          return (
            <button
              key={id}
              onClick={() => toggleLayer(id)}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-xs transition-colors ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              <span className="text-base leading-none">{icon}</span>
              <span className="font-medium">{label}</span>
              <span
                className={`ml-auto w-1.5 h-1.5 rounded-full ${
                  active ? "bg-primary" : "bg-border"
                }`}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
