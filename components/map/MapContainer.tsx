"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useMapStore } from "@/lib/store/mapStore";
import { api } from "@/lib/api/client";
import type { TreeGeoJSON, MapLayer } from "@/types";

const SATELLITE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    "esri-satellite": {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      attribution:
        "© Esri, Maxar, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN",
      maxzoom: 19,
    },
    "esri-labels": {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      maxzoom: 19,
    },
  },
  layers: [
    { id: "satellite", type: "raster", source: "esri-satellite" },
    { id: "labels", type: "raster", source: "esri-labels", paint: { "raster-opacity": 0.8 } },
  ],
};

const CONFIDENCE_COLORS: maplibregl.ExpressionSpecification = [
  "case",
  [">=", ["get", "confidence"], 0.9], "#22c55e",
  [">=", ["get", "confidence"], 0.7], "#86efac",
  [">=", ["get", "confidence"], 0.5], "#fbbf24",
  "#f87171",
];

const LAST_BBOX_KEY = "howtree:last_bbox";

interface DragState {
  active: boolean;
  startLng: number;
  startLat: number;
}

export function MapContainer() {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState>({ active: false, startLng: 0, startLat: 0 });
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const [selectMode, setSelectMode] = useState(true);
  const [isMapReady, setIsMapReady] = useState(false);

  const { setSelectedBBox, activeLayers, selectedBBox, setAnalysisResults } = useMapStore();

  // ── Auto-load last analysis on map mount ────────────────────────────────────
  const autoLoadTrees = useCallback(async (map: maplibregl.Map) => {
    try {
      const saved = localStorage.getItem(LAST_BBOX_KEY);
      if (!saved) return;
      const bbox = JSON.parse(saved) as [number, number, number, number];
      const geojson = await api.getTreesGeoJSON(bbox);
      if (!geojson.features.length) return;

      const src = map.getSource("trees") as maplibregl.GeoJSONSource | undefined;
      src?.setData(geojson);

      // Restore sidebar count from the most recent completed job
      const { jobs } = await api.listJobs(1, "completed");
      if (jobs[0]?.tree_count) {
        setAnalysisResults(jobs[0].tree_count, 0);
      }
    } catch {
      // Silently ignore — stale localStorage or API error
    }
  }, [setAnalysisResults]);

  // ── Map init ────────────────────────────────────────────────────────────────
  const initMap = useCallback(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: SATELLITE_STYLE,
      center: [71.43, 51.18],
      zoom: 11,
      attributionControl: { compact: true },
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl(), "bottom-right");

    map.on("load", () => {
      addSelectionLayer(map);
      addTreeLayers(map);
      registerMap("main", map);
      setIsMapReady(true);
      autoLoadTrees(map);
    });

    mapRef.current = map;
  }, [autoLoadTrees]);

  // ── Tree click popup ────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) return;

    const onClick = (e: maplibregl.MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (!feature || feature.geometry.type !== "Point") return;

      const [lng, lat] = feature.geometry.coordinates as [number, number];
      const { confidence, canopy_area_m2 } = feature.properties as {
        confidence: number;
        canopy_area_m2: number | null;
      };

      const confidencePct = Math.round(confidence * 100);
      const canopyText = canopy_area_m2 != null
        ? `${Math.round(canopy_area_m2)} m²`
        : "—";

      popupRef.current?.remove();
      popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: "200px" })
        .setLngLat([lng, lat])
        .setHTML(
          `<div style="font-family:sans-serif;font-size:12px;line-height:1.6;color:#e2e8f0;background:#1e293b;padding:8px 10px;border-radius:6px;margin:-10px -15px -12px">
            <div style="font-weight:600;margin-bottom:4px;color:#22c55e">Tree Detection</div>
            <div>Confidence: <strong>${confidencePct}%</strong></div>
            <div>Canopy: <strong>${canopyText}</strong></div>
            <div style="color:#64748b;font-size:11px;margin-top:4px">${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
          </div>`
        )
        .addTo(map);
    };

    const onEnter = () => { map.getCanvas().style.cursor = "pointer"; };
    const onLeave = () => { map.getCanvas().style.cursor = selectMode ? "crosshair" : ""; };

    map.on("click", "tree-points", onClick);
    map.on("mouseenter", "tree-points", onEnter);
    map.on("mouseleave", "tree-points", onLeave);

    return () => {
      map.off("click", "tree-points", onClick);
      map.off("mouseenter", "tree-points", onEnter);
      map.off("mouseleave", "tree-points", onLeave);
    };
  }, [isMapReady, selectMode]);

  // ── Drag-to-draw bbox ───────────────────────────────────────────────────────
  const startDrag = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      if (!selectMode) return;
      const map = mapRef.current;
      if (!map) return;
      dragRef.current = { active: true, startLng: e.lngLat.lng, startLat: e.lngLat.lat };
      map.dragPan.disable();
    },
    [selectMode]
  );

  const onDrag = useCallback((e: maplibregl.MapMouseEvent) => {
    const map = mapRef.current;
    if (!map || !dragRef.current.active) return;
    const { startLng, startLat } = dragRef.current;
    (map.getSource("selection-box") as maplibregl.GeoJSONSource)?.setData(
      buildBBoxPolygon(startLng, startLat, e.lngLat.lng, e.lngLat.lat)
    );
  }, []);

  const endDrag = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      const map = mapRef.current;
      if (!map || !dragRef.current.active) return;
      dragRef.current.active = false;
      map.dragPan.enable();

      const { startLng, startLat } = dragRef.current;
      const endLng = e.lngLat.lng;
      const endLat = e.lngLat.lat;

      if (Math.abs(endLng - startLng) < 0.0001 && Math.abs(endLat - startLat) < 0.0001) return;

      setSelectedBBox({
        lon1: Math.min(startLng, endLng),
        lat1: Math.min(startLat, endLat),
        lon2: Math.max(startLng, endLng),
        lat2: Math.max(startLat, endLat),
      });
    },
    [setSelectedBBox]
  );

  // ── Wire drag events ─────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) return;
    map.getCanvas().style.cursor = selectMode ? "crosshair" : "";
    map.on("mousedown", startDrag);
    map.on("mousemove", onDrag);
    map.on("mouseup", endDrag);
    return () => {
      map.off("mousedown", startDrag);
      map.off("mousemove", onDrag);
      map.off("mouseup", endDrag);
    };
  }, [isMapReady, selectMode, startDrag, onDrag, endDrag]);

  // ── Keep selection rect in sync ─────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const src = map.getSource("selection-box") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    src.setData(
      selectedBBox
        ? buildBBoxPolygon(selectedBBox.lon1, selectedBBox.lat1, selectedBBox.lon2, selectedBBox.lat2)
        : { type: "FeatureCollection", features: [] }
    );
  }, [selectedBBox]);

  // ── Layer visibility ────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    if (map.getLayer("tree-points")) {
      map.setLayoutProperty(
        "tree-points",
        "visibility",
        activeLayers.has("points" as MapLayer) ? "visible" : "none"
      );
    }
    if (map.getLayer("tree-heatmap")) {
      map.setLayoutProperty(
        "tree-heatmap",
        "visibility",
        activeLayers.has("heatmap" as MapLayer) ? "visible" : "none"
      );
    }
  }, [activeLayers]);

  // ── Mount / unmount ─────────────────────────────────────────────────────────
  useEffect(() => {
    initMap();
    return () => {
      popupRef.current?.remove();
      deregisterMap("main");
      mapRef.current?.remove();
      mapRef.current = null;
      setIsMapReady(false);
    };
  }, [initMap]);

  const clearSelection = () => {
    setSelectedBBox(null);
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    (map.getSource("selection-box") as maplibregl.GeoJSONSource)?.setData({
      type: "FeatureCollection",
      features: [],
    });
  };

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />

      {/* Toolbar */}
      <div className="absolute top-3 left-3 flex flex-col gap-1 z-10">
        <button
          onClick={() => setSelectMode((v) => !v)}
          title={selectMode ? "Режим выделения (перетащи чтобы выбрать зону)" : "Включить выделение"}
          className={`w-9 h-9 rounded flex items-center justify-center text-base transition-colors shadow-md border ${
            selectMode
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-card text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          ⬚
        </button>
        {selectedBBox && (
          <button
            onClick={clearSelection}
            title="Очистить выделение"
            className="w-9 h-9 rounded flex items-center justify-center text-sm bg-card border border-border text-muted-foreground hover:text-destructive hover:border-destructive transition-colors shadow-md"
          >
            ✕
          </button>
        )}
      </div>

      {/* Hint */}
      {selectMode && !selectedBBox && (
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 bg-card/90 backdrop-blur border border-border rounded px-3 py-1.5 text-xs text-muted-foreground pointer-events-none whitespace-nowrap">
          Зажмите и потяните чтобы выбрать зону анализа
        </div>
      )}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildBBoxPolygon(
  lon1: number, lat1: number, lon2: number, lat2: number
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [[[lon1, lat1], [lon2, lat1], [lon2, lat2], [lon1, lat2], [lon1, lat1]]],
        },
        properties: {},
      },
    ],
  };
}

function addSelectionLayer(map: maplibregl.Map) {
  map.addSource("selection-box", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });
  map.addLayer({
    id: "selection-fill",
    type: "fill",
    source: "selection-box",
    paint: { "fill-color": "#22c55e", "fill-opacity": 0.08 },
  });
  map.addLayer({
    id: "selection-outline",
    type: "line",
    source: "selection-box",
    paint: { "line-color": "#22c55e", "line-width": 2, "line-dasharray": [4, 2] },
  });
}

function addTreeLayers(map: maplibregl.Map) {
  map.addSource("trees", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });

  map.addLayer({
    id: "tree-heatmap",
    type: "heatmap",
    source: "trees",
    maxzoom: 16,
    layout: { visibility: "none" },
    paint: {
      "heatmap-weight": ["interpolate", ["linear"], ["get", "confidence"], 0, 0, 1, 1],
      "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 16, 3],
      "heatmap-color": [
        "interpolate", ["linear"], ["heatmap-density"],
        0, "rgba(0,0,0,0)",
        0.2, "rgba(34,197,94,0.2)",
        0.5, "rgba(34,197,94,0.5)",
        1, "rgba(34,197,94,1)",
      ],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 2, 16, 20],
      "heatmap-opacity": 0.8,
    },
  });

  map.addLayer({
    id: "tree-points",
    type: "circle",
    source: "trees",
    minzoom: 12,
    layout: { visibility: "visible" },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 3, 16, 6],
      "circle-color": CONFIDENCE_COLORS,
      "circle-opacity": 0.85,
      "circle-stroke-width": 1,
      "circle-stroke-color": "rgba(255,255,255,0.3)",
    },
  });
}

// ── Map registry ──────────────────────────────────────────────────────────────
const mapRegistry = new Map<string, maplibregl.Map>();

export function registerMap(id: string, map: maplibregl.Map) {
  mapRegistry.set(id, map);
}

export function deregisterMap(id: string) {
  mapRegistry.delete(id);
}

export function updateTreeSource(geojson: TreeGeoJSON, bbox?: [number, number, number, number]) {
  if (bbox) {
    try {
      localStorage.setItem(LAST_BBOX_KEY, JSON.stringify(bbox));
    } catch {
      // localStorage might be unavailable
    }
  }
  mapRegistry.forEach((map) => {
    if (!map || !map.isStyleLoaded()) return;
    const src = map.getSource("trees") as maplibregl.GeoJSONSource | undefined;
    src?.setData(geojson);
  });
}
