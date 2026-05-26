"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import type { JobSummary } from "@/types";

function exportCSV(jobs: JobSummary[]) {
  const header = "Job ID,Status,Trees,Canopy (m²),Avg Confidence,Date\n";
  const rows = jobs.map((j) =>
    [
      j.job_id,
      j.status,
      j.tree_count ?? "",
      j.canopy_area_m2 != null ? Math.round(j.canopy_area_m2) : "",
      j.avg_confidence != null ? (j.avg_confidence * 100).toFixed(1) + "%" : "",
      j.completed_at ? new Date(j.completed_at).toLocaleDateString() : "",
    ].join(",")
  ).join("\n");
  const blob = new Blob([header + rows], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "howtree-analyses.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "completed") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

function fmt(n: number | null | undefined, decimals = 0): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: decimals });
}

function SummarySkeleton() {
  return (
    <div className="grid grid-cols-4 gap-4">
      {[0, 1, 2, 3].map((i) => (
        <Card key={i} className="bg-card border-border">
          <CardContent className="pt-4 pb-4 space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-7 w-16" />
            <Skeleton className="h-3 w-12" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const t = useTranslations("analytics");
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listJobs(50)
      .then((res) => setJobs(res.jobs))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const completed = jobs.filter((j) => j.status === "completed");
  const totalTrees = completed.reduce((s, j) => s + (j.tree_count ?? 0), 0);
  const totalCanopy = completed.reduce((s, j) => s + (j.canopy_area_m2 ?? 0), 0);
  const avgConf = completed.length
    ? completed.reduce((s, j) => s + (j.avg_confidence ?? 0), 0) / completed.length
    : 0;

  const summaryCards = [
    { label: t("totalTrees"), value: fmt(totalTrees), delta: `${completed.length} ${t("analyses")}` },
    { label: t("totalCanopy"), value: `${fmt(totalCanopy / 10_000, 1)} ha`, delta: `${fmt(totalCanopy, 0)} m²` },
    { label: t("analysesRun"), value: fmt(jobs.length), delta: `${completed.length} ${t("completed")}` },
    { label: t("avgConf"), value: `${fmt(avgConf * 100, 1)}%`, delta: completed.length ? t("acrossJobs") : t("noData") },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {t("subtitle")}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => exportCSV(jobs)}
          disabled={loading || jobs.length === 0}
          className="border-border text-muted-foreground hover:text-foreground"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {t("exportCsv")}
        </Button>
      </div>

      {/* Summary cards */}
      {loading ? (
        <SummarySkeleton />
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {summaryCards.map(({ label, value, delta }) => (
            <Card key={label} className="bg-card border-border">
              <CardContent className="pt-4 pb-4">
                <p className="text-xs text-muted-foreground mb-1">{label}</p>
                <p className="text-2xl font-semibold text-foreground tabular-nums">{value}</p>
                <p className="text-xs text-primary mt-1">{delta}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Jobs table */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-foreground">
            {t("history")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-destructive py-4">{t("failedLoad")} {error}</p>
          ) : loading ? (
            <div className="space-y-2 py-2">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              {t("empty")}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-muted-foreground text-xs">{t("date")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs">{t("status")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs text-right">{t("trees")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs text-right">{t("canopy")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs text-right">{t("confidence")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs">{t("bbox")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.job_id} className="border-border hover:bg-secondary/30">
                    <TableCell className="text-xs text-muted-foreground">
                      {job.completed_at
                        ? new Date(job.completed_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })
                        : new Date(job.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(job.status)} className="text-xs">
                        {job.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-foreground">
                      {fmt(job.tree_count)}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-muted-foreground">
                      {job.canopy_area_m2 != null ? `${fmt(job.canopy_area_m2 / 10_000, 2)} ha` : "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-foreground">
                      {job.avg_confidence != null ? `${fmt(job.avg_confidence * 100, 1)}%` : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground font-mono">
                      {job.bbox
                        ? `${job.bbox[1].toFixed(3)},${job.bbox[0].toFixed(3)} → ${job.bbox[3].toFixed(3)},${job.bbox[2].toFixed(3)}`
                        : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
