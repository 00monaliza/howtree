"use client";

import { useTranslations } from "next-intl";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useMapStore } from "@/lib/store/mapStore";

const mapboxEnabled = Boolean(process.env.NEXT_PUBLIC_MAPBOX_TOKEN);

export function TileSourceSelector() {
  const t = useTranslations("layers");
  const tileSource = useMapStore((s) => s.tileSource);
  const setTileSource = useMapStore((s) => s.setTileSource);

  return (
    <TooltipProvider>
      <div className="space-y-1.5">
        <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
          {t("tileSource")}
        </p>
        <Select
          value={tileSource}
          onValueChange={(v) => setTileSource(v as typeof tileSource)}
        >
          <SelectTrigger className="h-8 text-xs bg-secondary border-border text-foreground">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-card border-border text-foreground">
            <SelectItem value="esri" className="text-xs">
              ESRI World Imagery
            </SelectItem>
            {mapboxEnabled ? (
              <SelectItem value="mapbox" className="text-xs">
                Mapbox Satellite
              </SelectItem>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <SelectItem value="mapbox" disabled className="text-xs">
                      Mapbox Satellite
                    </SelectItem>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="text-xs">{t("mapboxTokenRequired")}</p>
                </TooltipContent>
              </Tooltip>
            )}
            <SelectItem value="osm" className="text-xs">
              OpenStreetMap
            </SelectItem>
            <SelectItem value="carto-dark" className="text-xs">
              CartoDB Dark Matter
            </SelectItem>
            <SelectItem value="stadia-dark" className="text-xs">
              Stadia Alidade Smooth Dark
            </SelectItem>
            <SelectItem value="yandex" className="text-xs">
              Яндекс Спутник
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </TooltipProvider>
  );
}
