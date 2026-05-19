import { create } from "zustand";
import type { BBox, DistrictStats, JobStatus, MapLayer } from "@/types";

interface MapState {
  selectedBBox: BBox | null;
  activeJob: string | null;
  jobStatus: JobStatus | null;
  activeLayers: Set<MapLayer>;
  districtStats: DistrictStats | null;
  treeCount: number;
  canopyCoverage: number;

  setSelectedBBox: (bbox: BBox | null) => void;
  setActiveJob: (jobId: string | null) => void;
  setJobStatus: (status: JobStatus | null) => void;
  toggleLayer: (layer: MapLayer) => void;
  setDistrictStats: (stats: DistrictStats) => void;
  setAnalysisResults: (count: number, coverage: number) => void;
  resetJob: () => void;
}

export const useMapStore = create<MapState>((set) => ({
  selectedBBox: null,
  activeJob: null,
  jobStatus: null,
  activeLayers: new Set<MapLayer>(["points"]),
  districtStats: null,
  treeCount: 0,
  canopyCoverage: 0,

  setSelectedBBox: (bbox) => set({ selectedBBox: bbox }),
  setActiveJob: (jobId) => set({ activeJob: jobId }),
  setJobStatus: (status) => set({ jobStatus: status }),
  toggleLayer: (layer) =>
    set((state) => {
      const next = new Set(state.activeLayers);
      next.has(layer) ? next.delete(layer) : next.add(layer);
      return { activeLayers: next };
    }),
  setDistrictStats: (stats) => set({ districtStats: stats }),
  setAnalysisResults: (count, coverage) =>
    set({ treeCount: count, canopyCoverage: coverage }),
  resetJob: () => set({ activeJob: null, jobStatus: null }),
}));
