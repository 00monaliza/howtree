"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { PdfDownloadButton } from "@/components/reports/PdfDownloadButton";

const DISTRICTS = [
  "Manhattan",
  "Brooklyn",
  "Queens",
  "Bronx",
  "Staten Island",
  "Harlem",
  "Midtown",
];

const MOCK_STATS: Record<
  string,
  {
    treeCount: number;
    canopy: string;
    density: number;
    confidence: number;
    date: string;
    area: number;
  }
> = {
  Manhattan: { treeCount: 87420, canopy: "24.2%", density: 1240, confidence: 89, date: "May 19, 2026", area: 70.5 },
  Brooklyn: { treeCount: 124300, canopy: "32.1%", density: 980, confidence: 87, date: "May 19, 2026", area: 183.4 },
  Queens: { treeCount: 156800, canopy: "38.4%", density: 820, confidence: 91, date: "May 19, 2026", area: 282.9 },
  Bronx: { treeCount: 98200, canopy: "28.7%", density: 1100, confidence: 85, date: "May 19, 2026", area: 109.0 },
  "Staten Island": { treeCount: 72100, canopy: "42.1%", density: 1380, confidence: 92, date: "May 19, 2026", area: 151.2 },
  Harlem: { treeCount: 52300, canopy: "18.9%", density: 920, confidence: 83, date: "May 18, 2026", area: 7.4 },
  Midtown: { treeCount: 34500, canopy: "12.3%", density: 680, confidence: 88, date: "May 18, 2026", area: 8.1 },
};

const RECENT_REPORTS = [
  { district: "Queens", date: "May 19, 2026", size: "2.4 MB" },
  { district: "Brooklyn", date: "May 18, 2026", size: "1.9 MB" },
  { district: "Manhattan", date: "May 17, 2026", size: "1.7 MB" },
];

export default function ReportsPage() {
  const t = useTranslations("reports");
  const [district, setDistrict] = useState<string>("Queens");
  const stats = MOCK_STATS[district];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {t("subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Generator */}
        <div className="col-span-2 space-y-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-foreground">
                {t("generate")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  {t("selectDistrict")}
                </label>
                <Select value={district} onValueChange={setDistrict}>
                  <SelectTrigger className="bg-secondary border-border text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border">
                    {DISTRICTS.map((d) => (
                      <SelectItem
                        key={d}
                        value={d}
                        className="text-foreground hover:bg-secondary focus:bg-secondary"
                      >
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Preview stats */}
              {stats && (
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: t("treesDetected"), value: stats.treeCount.toLocaleString() },
                    { label: t("canopyCoverage"), value: stats.canopy },
                    { label: t("density"), value: stats.density.toLocaleString() },
                    { label: t("avgConf"), value: `${stats.confidence}%` },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-secondary/50 rounded border border-border p-2.5">
                      <p className="text-xs text-muted-foreground">{label}</p>
                      <p className="text-sm font-semibold text-foreground mt-0.5">{value}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  {t("contents")}
                </p>
                <div className="space-y-1">
                  {[
                    t("item1"),
                    t("item2"),
                    t("item3"),
                    t("item4"),
                    t("item5"),
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-2">
                      <svg className="w-3 h-3 text-primary shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      <span className="text-xs text-muted-foreground">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {stats && <PdfDownloadButton district={district} stats={stats} />}
            </CardContent>
          </Card>
        </div>

        {/* Recent reports sidebar */}
        <div className="space-y-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-foreground">
                {t("recent")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {RECENT_REPORTS.map((r) => (
                <div
                  key={r.district + r.date}
                  className="flex items-center justify-between bg-secondary/40 rounded border border-border p-2.5"
                >
                  <div>
                    <p className="text-xs font-medium text-foreground">{r.district}</p>
                    <p className="text-xs text-muted-foreground">{r.date}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary" className="text-xs">PDF</Badge>
                    <p className="text-xs text-muted-foreground mt-1">{r.size}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {t("format")}
              </p>
              <div className="space-y-1.5">
                {[
                  { label: t("format"), value: "PDF/A" },
                  { label: t("size"), value: "~2 MB" },
                  { label: t("language"), value: "English" },
                  { label: t("standard"), value: "ISO 32000" },
                ].map(({ label, value }) => (
                  <div key={value} className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="text-foreground font-medium">{value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
