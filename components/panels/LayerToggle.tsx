"use client";

import { useTranslations } from "next-intl";
import { useMapStore } from "@/lib/store/mapStore";
import type { MapLayer } from "@/types";

const LAYER_IDS: { id: MapLayer; icon: string }[] = [
  { id: "points", icon: "●" },
  { id: "heatmap", icon: "◉" },
  { id: "districts", icon: "▦" },
];

export function LayerToggle() {
  const { activeLayers, toggleLayer } = useMapStore();
  const t = useTranslations("layers");

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-4">
        {t("title")}
      </p>
      <div className="px-4 space-y-1">
        {LAYER_IDS.map(({ id, icon }) => {
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
              <span className="font-medium">{t(id)}</span>
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
