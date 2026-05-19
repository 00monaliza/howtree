import type { AnalysisJob, JobStatus, TreeGeoJSON, DistrictStats } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  analyze(bbox: [number, number, number, number]): Promise<AnalysisJob> {
    return request("/analyze", {
      method: "POST",
      body: JSON.stringify({ bbox }),
    });
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
};

export function createJobWebSocket(jobId: string): WebSocket {
  const wsBase = BASE.replace(/^http/, "ws");
  return new WebSocket(`${wsBase}/ws/jobs/${jobId}`);
}
