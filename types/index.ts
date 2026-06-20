export interface BBox {
  lon1: number;
  lat1: number;
  lon2: number;
  lat2: number;
}

export interface AnalysisJob {
  job_id: string;
}

export interface JobStatus {
  status:
  | "pending"
  | "queued"
  | "running"
  | "downloading_tiles"
  | "running_detection"
  | "merging_results"
  | "storing_results"
  | "completed"
  | "failed";
  progress: number;
  stage?: string | null;
  tree_count?: number | null;
  canopy_area_m2?: number | null;
  avg_confidence?: number | null;
  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  result_url?: string;
  error?: string;
}

export interface TreeFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    id: string;
    confidence: number;
    height_m?: number;
    species?: string;
  };
}

export interface TreeGeoJSON {
  type: "FeatureCollection";
  features: TreeFeature[];
}

export interface DistrictStats {
  district: string;
  count: number;
  canopy_area: number;
  density: number;
  avg_confidence: number;
  analysis_date: string;
}

export interface JobSummary {
  job_id: string;
  status: string;
  tree_count: number | null;
  canopy_area_m2: number | null;
  avg_confidence: number | null;
  created_at: string;
  completed_at: string | null;
  bbox: [number, number, number, number] | null;
}

export interface JobListResponse {
  jobs: JobSummary[];
  total: number;
}

export interface BBoxStats {
  tree_count: number;
  area_km2: number;
  density_per_km2: number;
  canopy_area_m2: number;
  canopy_coverage_pct: number;
  avg_confidence: number;
  confidence_distribution: Record<string, number>;
}

export interface WsMessage {
  progress: number;
  message: string;
  status?: string;
}

export type MapLayer = "points" | "heatmap" | "districts";
export type TileSource = "esri" | "mapbox" | "osm" | "carto-dark" | "stadia-dark" | "yandex";
