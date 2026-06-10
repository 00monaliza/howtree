import type { AnalysisJob, BBoxStats, JobListResponse, JobStatus, TreeGeoJSON, DistrictStats } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API = `${BASE}/api/v1`;

const DIRECT_BASE = process.env.NEXT_PUBLIC_DIRECT_API_URL ?? "http://localhost:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(await readApiError(res));
  }
  return res.json() as Promise<T>;
}

async function requestRaw<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init);
  if (!res.ok) {
    throw new Error(await readApiError(res));
  }
  return res.json() as Promise<T>;
}

async function readApiError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown };
    const detail = parsed.detail ?? parsed.message;
    if (typeof detail === "string") return `API ${res.status}: ${detail}`;
    if (detail) return `API ${res.status}: ${JSON.stringify(detail)}`;
  } catch {
    // Fall through to the raw response body.
  }
  return `API ${res.status}: ${text || res.statusText}`;
}

export const api = {
  analyze(bbox: [number, number, number, number]): Promise<AnalysisJob> {
    return request("/analyze", {
      method: "POST",
      body: JSON.stringify({ bbox }),
    });
  },

  uploadImage(
    file: File,
    lonMin: number,
    latMin: number,
    lonMax: number,
    latMax: number,
  ): Promise<AnalysisJob> {
    const form = new FormData();
    form.append("file", file);
    form.append("lon_min", String(lonMin));
    form.append("lat_min", String(latMin));
    form.append("lon_max", String(lonMax));
    form.append("lat_max", String(latMax));
    return requestRaw("/analyze/upload", { method: "POST", body: form });
  },

  getJob(jobId: string): Promise<JobStatus> {
    return request(`/jobs/${jobId}`);
  },

  getTreesGeoJSON(bbox: [number, number, number, number]): Promise<TreeGeoJSON> {
    const [lon1, lat1, lon2, lat2] = bbox;
    return request(`/trees/geojson?bbox=${lon1},${lat1},${lon2},${lat2}`);
  },

  getDistrictStats(district: string): Promise<DistrictStats> {
    return request(`/stats/${district}`);
  },

  listJobs(limit = 20, status?: string): Promise<JobListResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status) params.set("status", status);
    return request(`/jobs?${params}`);
  },

  getBboxStats(bbox: [number, number, number, number]): Promise<BBoxStats> {
    const [lon1, lat1, lon2, lat2] = bbox;
    return request(`/stats/bbox?bbox=${lon1},${lat1},${lon2},${lat2}`);
  },

  async predictImage(
    file: File,
    lonMin: number,
    latMin: number,
    lonMax: number,
    latMax: number,
  ): Promise<GeoJSON.FeatureCollection> {
    const form = new FormData();
    form.append("file", file);
    form.append("lon_min", String(lonMin));
    form.append("lat_min", String(latMin));
    form.append("lon_max", String(lonMax));
    form.append("lat_max", String(latMax));
    const res = await fetch(`${DIRECT_BASE}/predict`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await readApiError(res));
    return res.json() as Promise<GeoJSON.FeatureCollection>;
  },

  async predictBBox(
    bbox: [number, number, number, number],
    tileSource: "esri" | "mapbox" | "osm" | "yandex" = "esri",
  ): Promise<GeoJSON.FeatureCollection> {
    const [lon_min, lat_min, lon_max, lat_max] = bbox;
    const res = await fetch(`${DIRECT_BASE}/predict/bbox`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lon_min, lat_min, lon_max, lat_max, tile_source: tileSource }),
    });
    if (!res.ok) throw new Error(await readApiError(res));
    return res.json() as Promise<GeoJSON.FeatureCollection>;
  },
};

export function createJobWebSocket(jobId: string): WebSocket {
  const wsBase = API.replace(/^http/, "ws");
  return new WebSocket(`${wsBase}/jobs/ws/${jobId}`);
}
