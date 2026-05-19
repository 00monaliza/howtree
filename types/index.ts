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
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
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

export interface WsMessage {
  progress: number;
  message: string;
}

export type MapLayer = "points" | "heatmap" | "districts";
