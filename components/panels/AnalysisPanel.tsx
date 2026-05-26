"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type ComponentType,
  type DragEvent,
} from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useMapStore } from "@/lib/store/mapStore";
import { api, createJobWebSocket } from "@/lib/api/client";
import { updateTreeSource, flyMapToBbox } from "@/components/map/MapContainer";
import type { WsMessage } from "@/types";
import { area as turfArea, bboxPolygon } from "@turf/turf";
import {
  AlertTriangle,
  CheckCircle2,
  Crosshair,
  FileImage,
  Globe2,
  LocateFixed,
  MapPinned,
  PenLine,
  Radar,
  Satellite,
  UploadCloud,
  WifiOff,
  XCircle,
} from "lucide-react";

type Mode = "bbox" | "upload" | "coords";

const TERMINAL = new Set(["completed", "failed"]);

export function AnalysisPanel() {
  const t = useTranslations("analysis");
  const [mode, setMode] = useState<Mode>("bbox");

  return (
    <div className="flex flex-col gap-0">
      <GeoPanelHeader />

      <div className="grid grid-cols-3 gap-1 border-y border-border bg-background/35 p-1">
        <TabBtn label={t("tabMap")} icon={Crosshair} active={mode === "bbox"} onClick={() => setMode("bbox")} />
        <TabBtn label={t("tabUpload")} icon={UploadCloud} active={mode === "upload"} onClick={() => setMode("upload")} />
        <TabBtn label={t("tabCoords")} icon={PenLine} active={mode === "coords"} onClick={() => setMode("coords")} />
      </div>

      <div className="p-4">
        {mode === "bbox" ? <BBoxPanel /> : mode === "upload" ? <UploadPanel /> : <ManualCoordsPanel />}
      </div>
    </div>
  );
}

function TabBtn({
  label,
  icon: Icon,
  active,
  onClick,
}: {
  label: string;
  icon: ComponentType<{ className?: string }>;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex h-9 items-center justify-center gap-2 rounded text-xs font-semibold transition-colors ${
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-secondary hover:text-foreground"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function GeoPanelHeader() {
  const t = useTranslations("analysis");
  return (
    <div className="relative overflow-hidden border-b border-border bg-[#08110f] px-4 py-4">
      <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full border border-emerald-300/20 bg-[radial-gradient(circle_at_35%_35%,rgba(134,239,172,0.42),rgba(20,83,45,0.38)_34%,rgba(6,78,59,0.18)_52%,transparent_72%)]" />
      <div className="absolute right-5 top-8 h-24 w-24 rounded-full border border-cyan-200/15" />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-widest text-emerald-200/75">
            <Satellite className="h-3.5 w-3.5" />
            {t("geoDetection")}
          </div>
          <h2 className="text-xl font-semibold leading-tight text-foreground">
            {t("title")}
          </h2>
        </div>
        <div className="grid h-14 w-14 shrink-0 place-items-center rounded border border-emerald-300/20 bg-emerald-300/10">
          <Globe2 className="h-7 w-7 text-emerald-200" />
        </div>
      </div>
    </div>
  );
}

// ── Shared progress hook ────────────────────────────────────────────────────────

function useJobProgress() {
  const t = useTranslations("analysis");
  const { setActiveJob, setJobStatus, setAnalysisResults, resetJob } = useMapStore();
  const [wsMessages, setWsMessages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    wsRef.current?.close();
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  const finishJob = useCallback(async (
    job_id: string,
    bboxArray: [number, number, number, number],
    areaSqKm: number,
    onError: (err: string) => void,
  ) => {
    try {
      const final = await api.getJob(job_id);
      setJobStatus(final);

      if (final.status === "completed") {
        const geojson = await api.getTreesGeoJSON(bboxArray);
        updateTreeSource(geojson, bboxArray);
        const density = geojson.features.length / (areaSqKm ?? 1);
        setAnalysisResults(
          geojson.features.length,
          Math.round(density * 0.03 * 100) / 100,
        );
      } else if (final.status === "failed") {
        onError(final.error ?? t("genericError"));
      }
      setIsLoading(false);
    } catch {
      setIsLoading(false);
    }
  }, [setJobStatus, setAnalysisResults, t]);

  // Polling-фоллбэк: используется когда WebSocket закрывается до завершения джоба
  const startPolling = useCallback((
    job_id: string,
    bboxArray: [number, number, number, number],
    areaSqKm: number,
    onError: (err: string) => void,
  ) => {
    if (pollRef.current) clearInterval(pollRef.current);
    setJobStatus({ status: "queued", progress: 0 });
    setWsMessages([t("queueWait")]);

    pollRef.current = setInterval(async () => {
      try {
        const job = await api.getJob(job_id);
        setJobStatus(job);
        if (job.stage) setWsMessages([job.stage]);

        if (TERMINAL.has(job.status)) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          await finishJob(job_id, bboxArray, areaSqKm, onError);
        }
      } catch {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        setIsLoading(false);
      }
    }, 3000);
  }, [setJobStatus, finishJob, t]); // eslint-disable-line react-hooks/exhaustive-deps

  const trackJob = useCallback(
    async (job_id: string, bboxArray: [number, number, number, number], onError: (err: string) => void) => {
      setActiveJob(job_id);
      const areaSqKm = turfArea(bboxPolygon(bboxArray)) / 1_000_000;

      const ws = createJobWebSocket(job_id);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const msg: WsMessage = JSON.parse(e.data);
        setJobStatus({ status: normalizeJobStatus(msg.status), progress: msg.progress });
        setWsMessages((prev) => [...prev.slice(-4), msg.message]);
      };

      ws.onclose = async () => {
        // Если джоб ещё не завершён — переключаемся на polling
        try {
          const job = await api.getJob(job_id);
          if (TERMINAL.has(job.status)) {
            setJobStatus(job);
            await finishJob(job_id, bboxArray, areaSqKm, onError);
          } else {
            startPolling(job_id, bboxArray, areaSqKm, onError);
          }
        } catch {
          setIsLoading(false);
        }
      };

      ws.onerror = () => {
        startPolling(job_id, bboxArray, areaSqKm, onError);
      };
    },
    [setActiveJob, setJobStatus, finishJob, startPolling],
  );

  return { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob };
}

// ── BBox analysis panel ─────────────────────────────────────────────────────────

function BBoxPanel() {
  const t = useTranslations("analysis");
  const { selectedBBox, jobStatus, treeCount, setJobStatus } = useMapStore();
  const { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob } = useJobProgress();

  const bboxArray = selectedBBox
    ? ([selectedBBox.lon1, selectedBBox.lat1, selectedBBox.lon2, selectedBBox.lat2] as [number, number, number, number])
    : null;

  const areaSqKm = bboxArray ? turfArea(bboxPolygon(bboxArray)) / 1_000_000 : null;

  async function runAnalysis() {
    if (!bboxArray) return;
    setIsLoading(true);
    setWsMessages([]);
    resetJob();

    try {
      const { job_id } = await api.analyze(bboxArray);
      await trackJob(job_id, bboxArray, (err) => {
        setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      });
    } catch (err) {
      console.error(err);
      setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      setIsLoading(false);
    }
  }

  const progress = jobStatus?.progress ?? 0;
  const isDone = jobStatus?.status === "completed";
  const isFailed = jobStatus?.status === "failed";

  return (
    <div className="flex flex-col gap-4">
      <ApiRequirementNotice compact={Boolean(selectedBBox)} />

      <div>
        <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <LocateFixed className="h-3.5 w-3.5" />
          {t("zone")}
        </p>
        {selectedBBox ? (
          <div className="space-y-2 rounded border border-emerald-400/20 bg-emerald-400/5 p-3">
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              <CoordTile label="SW" value={`${selectedBBox.lat1.toFixed(5)}, ${selectedBBox.lon1.toFixed(5)}`} />
              <CoordTile label="NE" value={`${selectedBBox.lat2.toFixed(5)}, ${selectedBBox.lon2.toFixed(5)}`} />
            </div>
            <div className="flex items-center justify-between border-t border-border pt-2">
              <span className="text-xs text-muted-foreground">{t("area")}</span>
              <span className="text-foreground">
                {areaSqKm?.toFixed(2)} км²
              </span>
            </div>
          </div>
        ) : (
          <div className="rounded border border-dashed border-border bg-secondary/25 p-4 text-center">
            <div className="mx-auto mb-2 grid h-10 w-10 place-items-center rounded border border-border bg-background/70">
              <MapPinned className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm font-medium text-foreground">{t("selectHint")}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {t("selectHintSub")}
            </p>
          </div>
        )}
      </div>

      <Button
        onClick={runAnalysis}
        disabled={!selectedBBox || isLoading}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
      >
        {isLoading
          ? jobStatus?.status === "queued"
            ? t("queued")
            : t("running")
          : t("run")}
      </Button>

      <JobProgress
        isLoading={isLoading}
        isDone={isDone}
        isFailed={isFailed}
        progress={progress}
        wsMessages={wsMessages}
        error={jobStatus?.error ?? jobStatus?.error_message ?? null}
      />

      {isDone && treeCount > 0 && (
        <>
          <Separator />
          <ZoneStats />
        </>
      )}
    </div>
  );
}

// ── Upload panel ────────────────────────────────────────────────────────────────

function UploadPanel() {
  const t = useTranslations("analysis");
  const { jobStatus, treeCount, setJobStatus } = useMapStore();
  const { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob } = useJobProgress();

  const [file, setFile] = useState<File | null>(null);
  const [isGeoTiff, setIsGeoTiff] = useState(false);
  const [bbox, setBbox] = useState({ lonMin: "", latMin: "", lonMax: "", latMax: "" });
  const [dragOver, setDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [sizeError, setSizeError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  function handleFileChange(f: File | null) {
    if (!f) return;
    if (f.size > 50 * 1024 * 1024) {
      setSizeError(t("fileTooLarge"));
      return;
    }
    setSizeError(null);
    setFile(f);
    const ext = f.name.toLowerCase();
    const isTiff = ext.endsWith(".tif") || ext.endsWith(".tiff");
    setIsGeoTiff(isTiff);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(!isTiff ? URL.createObjectURL(f) : null);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileChange(f);
  }

  const bboxValid = isGeoTiff
    ? true
    : bbox.lonMin !== "" && bbox.latMin !== "" && bbox.lonMax !== "" && bbox.latMax !== "";

  async function runUpload() {
    if (!file) return;
    setIsLoading(true);
    setWsMessages([]);
    resetJob();

    const lonMin = isGeoTiff ? 0 : parseFloat(bbox.lonMin);
    const latMin = isGeoTiff ? 0 : parseFloat(bbox.latMin);
    const lonMax = isGeoTiff ? 1 : parseFloat(bbox.lonMax);
    const latMax = isGeoTiff ? 1 : parseFloat(bbox.latMax);

    try {
      const { job_id } = await api.uploadImage(file, lonMin, latMin, lonMax, latMax);
      const bboxArray: [number, number, number, number] = [lonMin, latMin, lonMax, latMax];
      await trackJob(job_id, bboxArray, (err) => {
        setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      });
    } catch (err) {
      console.error(err);
      setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      setIsLoading(false);
    }
  }

  const progress = jobStatus?.progress ?? 0;
  const isDone = jobStatus?.status === "completed";
  const isFailed = jobStatus?.status === "failed";

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border border-cyan-400/20 bg-cyan-400/5 p-3">
        <div className="flex items-start gap-3">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded border border-cyan-300/25 bg-cyan-300/10">
            <FileImage className="h-[18px] w-[18px] text-cyan-200" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">{t("uploadTitle")}</p>
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
              {t("uploadDesc")}
            </p>
          </div>
        </div>
      </div>

      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          dragOver
            ? "border-primary bg-primary/5"
            : file
            ? "border-primary/50 bg-primary/5"
            : "border-border hover:border-muted-foreground/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".tif,.tiff,.jpg,.jpeg,.png"
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div>
            <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {(file.size / 1024 / 1024).toFixed(1)} MB
              {isGeoTiff && <span className="ml-2 text-primary">{t("geotiffAuto")}</span>}
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm text-muted-foreground">{t("dropHint")}</p>
            <p className="text-xs text-muted-foreground/60 mt-1">GeoTIFF, JPEG, PNG · max 50 MB</p>
          </div>
        )}
        {sizeError && <p className="text-xs text-destructive mt-1">{sizeError}</p>}
      </div>

      {previewUrl && (
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1.5">
            {t("imagePreview")}
          </p>
          <img
            src={previewUrl}
            alt="preview"
            className="w-full rounded border border-border object-cover max-h-40"
          />
        </div>
      )}

      {/* BBox inputs — only shown for non-GeoTIFF */}
      {file && !isGeoTiff && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            {t("geoBounds")}
          </p>
          <div className="grid grid-cols-2 gap-2">
            {(["lonMin", "latMin", "lonMax", "latMax"] as const).map((key) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground block mb-0.5">
                  {key === "lonMin" ? "Lon min" : key === "latMin" ? "Lat min" : key === "lonMax" ? "Lon max" : "Lat max"}
                </label>
                <input
                  type="number"
                  step="any"
                  value={bbox[key]}
                  onChange={(e) => setBbox((b) => ({ ...b, [key]: e.target.value }))}
                  className="w-full bg-secondary/50 border border-border rounded px-2 py-1 text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                  placeholder={key.startsWith("lon") ? "71.430" : "51.180"}
                />
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground/60 mt-1.5">
            {t("geoBoundsHint")}
          </p>
        </div>
      )}

      <Button
        onClick={runUpload}
        disabled={!file || !bboxValid || isLoading}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
      >
        {isLoading ? t("processing") : t("findTrees")}
      </Button>

      <JobProgress
        isLoading={isLoading}
        isDone={isDone}
        isFailed={isFailed}
        progress={progress}
        wsMessages={wsMessages}
        error={jobStatus?.error ?? jobStatus?.error_message ?? null}
      />

      {isDone && treeCount > 0 && (
        <>
          <Separator />
          <ZoneStats />
        </>
      )}
    </div>
  );
}

// ── Manual coordinates panel ────────────────────────────────────────────────────

function ManualCoordsPanel() {
  const t = useTranslations("analysis");
  const { setSelectedBBox, jobStatus, treeCount, setJobStatus } = useMapStore();
  const { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob } = useJobProgress();

  const [coords, setCoords] = useState({ lonMin: "", latMin: "", lonMax: "", latMax: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    const lon1 = parseFloat(coords.lonMin);
    const lat1 = parseFloat(coords.latMin);
    const lon2 = parseFloat(coords.lonMax);
    const lat2 = parseFloat(coords.latMax);
    if (isNaN(lon1) || lon1 < -180 || lon1 > 180) errs.lonMin = t("coordValidationLon");
    if (isNaN(lat1) || lat1 < -90 || lat1 > 90) errs.latMin = t("coordValidationLat");
    if (isNaN(lon2) || lon2 < -180 || lon2 > 180) errs.lonMax = t("coordValidationLon");
    if (isNaN(lat2) || lat2 < -90 || lat2 > 90) errs.latMax = t("coordValidationLat");
    if (!errs.lonMin && !errs.lonMax && lon1 >= lon2) errs.lonMax = t("coordValidationMinMax");
    if (!errs.latMin && !errs.latMax && lat1 >= lat2) errs.latMax = t("coordValidationMinMax");
    return errs;
  }

  function applyToMap() {
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    const lon1 = parseFloat(coords.lonMin);
    const lat1 = parseFloat(coords.latMin);
    const lon2 = parseFloat(coords.lonMax);
    const lat2 = parseFloat(coords.latMax);
    flyMapToBbox(lon1, lat1, lon2, lat2);
    setSelectedBBox({ lon1, lat1, lon2, lat2 });
  }

  async function runAnalysis() {
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    const lon1 = parseFloat(coords.lonMin);
    const lat1 = parseFloat(coords.latMin);
    const lon2 = parseFloat(coords.lonMax);
    const lat2 = parseFloat(coords.latMax);
    const bboxArray: [number, number, number, number] = [lon1, lat1, lon2, lat2];
    flyMapToBbox(lon1, lat1, lon2, lat2);
    setSelectedBBox({ lon1, lat1, lon2, lat2 });
    setIsLoading(true);
    setWsMessages([]);
    resetJob();
    try {
      const { job_id } = await api.analyze(bboxArray);
      await trackJob(job_id, bboxArray, (err) => {
        setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      });
    } catch (err) {
      setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      setIsLoading(false);
    }
  }

  const fields = [
    { key: "lonMin" as const, label: "Lon min", placeholder: "71.380" },
    { key: "latMin" as const, label: "Lat min", placeholder: "51.150" },
    { key: "lonMax" as const, label: "Lon max", placeholder: "71.480" },
    { key: "latMax" as const, label: "Lat max", placeholder: "51.220" },
  ];

  const allFilled = fields.every(({ key }) => coords[key] !== "");
  const progress = jobStatus?.progress ?? 0;
  const isDone = jobStatus?.status === "completed";
  const isFailed = jobStatus?.status === "failed";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2">
        {fields.map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="text-xs text-muted-foreground block mb-0.5">{label}</label>
            <input
              type="number"
              step="any"
              value={coords[key]}
              onChange={(e) => setCoords((c) => ({ ...c, [key]: e.target.value }))}
              className="w-full bg-secondary/50 border border-border rounded px-2 py-1 text-xs font-mono text-foreground focus:outline-none focus:border-primary"
              placeholder={placeholder}
            />
            {errors[key] && <p className="text-[10px] text-destructive mt-0.5">{errors[key]}</p>}
          </div>
        ))}
      </div>

      <Button
        variant="secondary"
        onClick={applyToMap}
        disabled={!allFilled}
        className="w-full font-semibold"
      >
        {t("applyToMap")}
      </Button>

      <Button
        onClick={runAnalysis}
        disabled={!allFilled || isLoading}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
      >
        {isLoading
          ? jobStatus?.status === "queued" ? t("queued") : t("running")
          : t("run")}
      </Button>

      <JobProgress
        isLoading={isLoading}
        isDone={isDone}
        isFailed={isFailed}
        progress={progress}
        wsMessages={wsMessages}
        error={jobStatus?.error ?? jobStatus?.error_message ?? null}
      />

      {isDone && treeCount > 0 && (
        <>
          <Separator />
          <ZoneStats />
        </>
      )}
    </div>
  );
}

// ── Shared sub-components ───────────────────────────────────────────────────────

function ApiRequirementNotice({ compact }: { compact?: boolean }) {
  const t = useTranslations("analysis");
  return (
    <div className="rounded border border-amber-300/25 bg-amber-300/10 p-3">
      <div className="flex items-start gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded border border-amber-300/30 bg-amber-300/15">
          <Satellite className="h-[18px] w-[18px] text-amber-200" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{t("apiKeyTitle")}</p>
          <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
            {compact ? t("apiKeyCompact") : t("apiKeyFull")}
          </p>
          {!compact && (
            <code className="mt-2 block rounded border border-border bg-background/80 px-2 py-1.5 text-[11px] text-amber-100">
              YANDEX_MAPS_API_KEY=...
            </code>
          )}
        </div>
      </div>
    </div>
  );
}

function CoordTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-background/55 p-2">
      <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 truncate text-foreground">{value}</div>
    </div>
  );
}

function JobProgress({
  isLoading,
  isDone,
  isFailed,
  progress,
  wsMessages,
  error,
}: {
  isLoading: boolean;
  isDone: boolean;
  isFailed: boolean;
  progress: number;
  wsMessages: string[];
  error?: string | null;
}) {
  const t = useTranslations("analysis");
  if (!isLoading && !isDone && !isFailed) return null;

  const statusLabel = isDone ? t("done") : isFailed ? t("error") : `${progress}%`;
  const latestMessage = wsMessages[wsMessages.length - 1];

  return (
    <div className="space-y-2 rounded border border-border bg-secondary/30 p-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          {isDone ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
          ) : isFailed ? (
            <XCircle className="h-3.5 w-3.5 text-destructive" />
          ) : (
            <Radar className="h-3.5 w-3.5 text-primary" />
          )}
          {t("status")}
        </span>
        <Badge
          variant={isDone ? "default" : isFailed ? "destructive" : "secondary"}
          className="text-xs"
        >
          {statusLabel}
        </Badge>
      </div>
      <Progress value={progress} className="h-1.5" />
      {latestMessage && !isFailed && (
        <p className="text-xs text-muted-foreground font-mono truncate">
          {latestMessage}
        </p>
      )}
      {isFailed && <ApiErrorBlock message={error ?? latestMessage ?? t("failedError")} />}
    </div>
  );
}

function ApiErrorBlock({ message }: { message: string }) {
  const t = useTranslations("analysis");
  const isForbidden =
    message.includes("403 Forbidden") ||
    message.includes("HTTP 403");
  const isMissingProvider =
    message.includes("No imagery provider configured") ||
    message.includes("YANDEX_MAPS_API_KEY");
  const isProviderError = isForbidden || isMissingProvider || message.includes("Static API");

  return (
    <div className="rounded border border-destructive/30 bg-destructive/10 p-3">
      <div className="flex items-start gap-2">
        {isProviderError ? (
          <WifiOff className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        ) : (
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        )}
        <div className="min-w-0">
          <p className="text-xs font-semibold text-foreground">
            {isForbidden
              ? t("keyRejected")
              : isMissingProvider
              ? t("noImagery")
              : t("stopped")}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {isForbidden
              ? t("keyRejectedDesc")
              : isMissingProvider
              ? t("noImageryDesc")
              : message}
          </p>
        </div>
      </div>
    </div>
  );
}

function formatApiError(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  if (message.includes("No imagery provider configured")) {
    return "No imagery provider configured. Set YANDEX_MAPS_API_KEY or MAPBOX_TOKEN.";
  }
  return message.replace(/^Error:\s*/, "");
}

function normalizeJobStatus(status: string | undefined) {
  if (
    status === "queued" ||
    status === "downloading_tiles" ||
    status === "running_detection" ||
    status === "merging_results" ||
    status === "storing_results" ||
    status === "completed" ||
    status === "failed"
  ) {
    return status;
  }
  return "running";
}

function ZoneStats() {
  const t = useTranslations("analysis");
  const { treeCount, canopyCoverage, selectedBBox, jobStatus } = useMapStore();

  const bboxArray = selectedBBox
    ? ([selectedBBox.lon1, selectedBBox.lat1, selectedBBox.lon2, selectedBBox.lat2] as [number, number, number, number])
    : null;

  const areaSqKm = bboxArray ? turfArea(bboxPolygon(bboxArray)) / 1_000_000 : 1;
  const density = Math.round(treeCount / areaSqKm);
  const analysisDate = new Date().toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });

  if (jobStatus?.status !== "completed") {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
        {t("results")}
      </p>
      <div className="space-y-2">
        <MetricCard label={t("totalTrees")} value={treeCount.toLocaleString()} unit={t("detected")} accent />
        <MetricCard label={t("canopyCoverage")} value={`${canopyCoverage}%`} unit={t("ofArea")} />
        <MetricCard label={t("density")} value={density.toLocaleString()} unit={t("treesPerKm")} />
        <MetricCard label={t("analysisDate")} value={analysisDate} unit="" />
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
        <span className={`text-sm font-semibold ${accent ? "text-primary" : "text-foreground"}`}>
          {value}
        </span>
        {unit && <span className="text-xs text-muted-foreground ml-1">{unit}</span>}
      </div>
    </div>
  );
}
