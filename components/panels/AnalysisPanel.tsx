"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useMapStore } from "@/lib/store/mapStore";
import { api, createJobWebSocket } from "@/lib/api/client";
import { updateTreeSource } from "@/components/map/MapContainer";
import type { WsMessage } from "@/types";
import { area as turfArea, bboxPolygon } from "@turf/turf";

export function AnalysisPanel() {
  const {
    selectedBBox,
    activeJob,
    jobStatus,
    treeCount,
    canopyCoverage,
    setActiveJob,
    setJobStatus,
    setAnalysisResults,
    resetJob,
  } = useMapStore();

  const [wsMessages, setWsMessages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const bboxArray = selectedBBox
    ? ([
        selectedBBox.lon1,
        selectedBBox.lat1,
        selectedBBox.lon2,
        selectedBBox.lat2,
      ] as [number, number, number, number])
    : null;

  const areaSqKm = bboxArray
    ? turfArea(bboxPolygon(bboxArray)) / 1_000_000
    : null;

  async function runAnalysis() {
    if (!bboxArray) return;
    setIsLoading(true);
    setWsMessages([]);
    resetJob();

    try {
      const { job_id } = await api.analyze(bboxArray);
      setActiveJob(job_id);

      const ws = createJobWebSocket(job_id);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const msg: WsMessage = JSON.parse(e.data);
        setJobStatus({ status: "running", progress: msg.progress });
        setWsMessages((prev) => [...prev.slice(-4), msg.message]);
      };

      ws.onclose = async () => {
        const final = await api.getJob(job_id);
        setJobStatus(final);

        if (final.status === "completed" && bboxArray) {
          const geojson = await api.getTreesGeoJSON(bboxArray);
          updateTreeSource(geojson);
          const density = geojson.features.length / (areaSqKm ?? 1);
          setAnalysisResults(
            geojson.features.length,
            Math.round(density * 0.03 * 100) / 100
          );
        }
        setIsLoading(false);
      };

      ws.onerror = () => {
        setJobStatus({ status: "failed", progress: 0, error: "WebSocket error" });
        setIsLoading(false);
      };
    } catch (err) {
      console.error(err);
      setJobStatus({ status: "failed", progress: 0, error: String(err) });
      setIsLoading(false);
    }
  }

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  const progress = jobStatus?.progress ?? 0;
  const isDone = jobStatus?.status === "completed";
  const isFailed = jobStatus?.status === "failed";

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Bbox info */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
          Selection
        </p>
        {selectedBBox ? (
          <div className="font-mono text-xs space-y-1 bg-secondary/50 rounded p-2 border border-border">
            <div className="flex justify-between">
              <span className="text-muted-foreground">SW</span>
              <span className="text-foreground">
                {selectedBBox.lat1.toFixed(5)}, {selectedBBox.lon1.toFixed(5)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">NE</span>
              <span className="text-foreground">
                {selectedBBox.lat2.toFixed(5)}, {selectedBBox.lon2.toFixed(5)}
              </span>
            </div>
            <div className="flex justify-between pt-1 border-t border-border">
              <span className="text-muted-foreground">Area</span>
              <span className="text-foreground">
                {areaSqKm?.toFixed(2)} km²
              </span>
            </div>
          </div>
        ) : (
          <div className="bg-secondary/30 rounded border border-dashed border-border p-3 text-center">
            <p className="text-xs text-muted-foreground">
              Draw a rectangle on the map to select an area
            </p>
          </div>
        )}
      </div>

      <Button
        onClick={runAnalysis}
        disabled={!selectedBBox || isLoading}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
      >
        {isLoading ? "Analyzing..." : "Run Analysis"}
      </Button>

      {/* Progress */}
      {(isLoading || isDone || isFailed) && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Progress</span>
            <Badge
              variant={isDone ? "default" : isFailed ? "destructive" : "secondary"}
              className="text-xs"
            >
              {isDone ? "Complete" : isFailed ? "Failed" : `${progress}%`}
            </Badge>
          </div>
          <Progress value={progress} className="h-1.5" />
          {wsMessages.length > 0 && (
            <p className="text-xs text-muted-foreground font-mono truncate">
              {wsMessages[wsMessages.length - 1]}
            </p>
          )}
        </div>
      )}

      {/* Results */}
      {isDone && treeCount > 0 && (
        <>
          <Separator />
          <ZoneStats />
        </>
      )}
    </div>
  );
}

function ZoneStats() {
  const { treeCount, canopyCoverage, selectedBBox, jobStatus } = useMapStore();

  const bboxArray = selectedBBox
    ? ([
        selectedBBox.lon1,
        selectedBBox.lat1,
        selectedBBox.lon2,
        selectedBBox.lat2,
      ] as [number, number, number, number])
    : null;

  const areaSqKm = bboxArray
    ? turfArea(bboxPolygon(bboxArray)) / 1_000_000
    : 1;

  const density = Math.round(treeCount / areaSqKm);
  const analysisDate = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  if (jobStatus?.status !== "completed") {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
        Results
      </p>
      <div className="space-y-2">
        <MetricCard label="Total Trees" value={treeCount.toLocaleString()} unit="detected" accent />
        <MetricCard label="Canopy Coverage" value={`${canopyCoverage}%`} unit="of area" />
        <MetricCard label="Density" value={density.toLocaleString()} unit="trees/km²" />
        <MetricCard label="Analysis Date" value={analysisDate} unit="" />
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string;
  unit: string;
  accent?: boolean;
}) {
  return (
    <div className="bg-secondary/50 rounded border border-border p-2.5 flex items-center justify-between">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="text-right">
        <span
          className={`text-sm font-semibold ${accent ? "text-primary" : "text-foreground"}`}
        >
          {value}
        </span>
        {unit && (
          <span className="text-xs text-muted-foreground ml-1">{unit}</span>
        )}
      </div>
    </div>
  );
}
