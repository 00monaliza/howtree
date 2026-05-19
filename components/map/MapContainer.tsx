"use client";

import { useEffect, useRef, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "mapbox-gl/dist/mapbox-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import { useMapStore } from "@/lib/store/mapStore";
import type { BBox, TreeGeoJSON, MapLayer } from "@/types";
import { bbox as turfBbox } from "@turf/turf";

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

const CONFIDENCE_COLORS = [
  "case",
  [">=", ["get", "confidence"], 0.9],
  "#22c55e",
  [">=", ["get", "confidence"], 0.7],
  "#86efac",
  [">=", ["get", "confidence"], 0.5],
  "#fbbf24",
  "#f87171",
];

export function MapContainer() {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const drawRef = useRef<MapboxDraw | null>(null);
  const { setSelectedBBox, activeLayers } = useMapStore();

  const initMap = useCallback(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [-74.006, 40.7128],
      zoom: 11,
      attributionControl: true,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.addControl(new mapboxgl.ScaleControl(), "bottom-right");

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: { trash: true },
      defaultMode: "draw_rectangle",
      styles: [
        {
          id: "gl-draw-polygon-fill",
          type: "fill",
          filter: ["all", ["==", "$type", "Polygon"]],
          paint: {
            "fill-color": "#22c55e",
            "fill-opacity": 0.1,
          },
        },
        {
          id: "gl-draw-polygon-stroke",
          type: "line",
          filter: ["all", ["==", "$type", "Polygon"]],
          paint: {
            "line-color": "#22c55e",
            "line-width": 2,
            "line-dasharray": [4, 2],
          },
        },
      ],
    });

    map.addControl(draw, "top-left");
    drawRef.current = draw;

    map.on("draw.create", updateBBox);
    map.on("draw.update", updateBBox);
    map.on("draw.delete", () => setSelectedBBox(null));

    map.on("load", () => {
      addTreeLayers(map);
      registerMap("main", map);
    });

    mapRef.current = map;
  }, [setSelectedBBox]);

  const updateBBox = useCallback(() => {
    const draw = drawRef.current;
    if (!draw) return;
    const data = draw.getAll();
    if (!data.features.length) {
      setSelectedBBox(null);
      return;
    }
    const [lon1, lat1, lon2, lat2] = turfBbox(data) as [
      number,
      number,
      number,
      number
    ];
    setSelectedBBox({ lon1, lat1, lon2, lat2 });
  }, [setSelectedBBox]);

  useEffect(() => {
    initMap();
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [initMap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const showPoints = activeLayers.has("points" as MapLayer);
    const showHeatmap = activeLayers.has("heatmap" as MapLayer);

    if (map.getLayer("tree-points")) {
      map.setLayoutProperty(
        "tree-points",
        "visibility",
        showPoints ? "visible" : "none"
      );
    }
    if (map.getLayer("tree-heatmap")) {
      map.setLayoutProperty(
        "tree-heatmap",
        "visibility",
        showHeatmap ? "visible" : "none"
      );
    }
  }, [activeLayers]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ minHeight: "400px" }}
    />
  );
}

function addTreeLayers(map: mapboxgl.Map) {
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
        "interpolate",
        ["linear"],
        ["heatmap-density"],
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
      "circle-color": CONFIDENCE_COLORS as mapboxgl.Expression,
      "circle-opacity": 0.85,
      "circle-stroke-width": 1,
      "circle-stroke-color": "rgba(255,255,255,0.3)",
    },
  });
}

// Module-level registry so external callers can push GeoJSON without prop drilling
const mapRegistry = new Map<string, mapboxgl.Map>();

export function registerMap(id: string, map: mapboxgl.Map) {
  mapRegistry.set(id, map);
}

export function updateTreeSource(geojson: TreeGeoJSON) {
  mapRegistry.forEach((map) => {
    const src = map.getSource("trees") as mapboxgl.GeoJSONSource | undefined;
    src?.setData(geojson);
  });
}
