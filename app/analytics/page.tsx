"use client";

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
import { DistrictBarChart, DensityLineChart } from "@/components/charts/DistrictBarChart";

const TOP_ZONES = [
  { rank: 1, district: "Queens", trees: 156800, density: 820, canopy: "38.4%", status: "high" },
  { rank: 2, district: "Brooklyn", trees: 124300, density: 980, canopy: "32.1%", status: "high" },
  { rank: 3, district: "Bronx", trees: 98200, density: 1100, canopy: "28.7%", status: "medium" },
  { rank: 4, district: "Manhattan", trees: 87420, density: 1240, canopy: "24.2%", status: "medium" },
  { rank: 5, district: "Staten Is.", trees: 72100, density: 1380, canopy: "42.1%", status: "high" },
  { rank: 6, district: "Harlem", trees: 52300, density: 920, canopy: "18.9%", status: "low" },
  { rank: 7, district: "Midtown", trees: 34500, density: 680, canopy: "12.3%", status: "low" },
  { rank: 8, district: "Flushing", trees: 28900, density: 740, canopy: "22.1%", status: "medium" },
  { rank: 9, district: "Jamaica", trees: 24100, density: 610, canopy: "19.8%", status: "low" },
  { rank: 10, district: "Astoria", trees: 21800, density: 580, canopy: "17.4%", status: "low" },
];

function exportCSV() {
  const header = "Rank,District,Trees,Density (trees/km²),Canopy Coverage\n";
  const rows = TOP_ZONES.map(
    (z) => `${z.rank},${z.district},${z.trees},${z.density},${z.canopy}`
  ).join("\n");
  const blob = new Blob([header + rows], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "tree-analysis.csv";
  a.click();
  URL.revokeObjectURL(url);
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive"> = {
  high: "default",
  medium: "secondary",
  low: "destructive",
};

export default function AnalyticsPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Urban canopy distribution across districts
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={exportCSV}
          className="border-border text-muted-foreground hover:text-foreground"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export CSV
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Trees Detected", value: "756,420", delta: "+12.4%" },
          { label: "Avg Canopy Coverage", value: "25.6%", delta: "+2.1%" },
          { label: "Analyses Run", value: "8", delta: "this month" },
          { label: "Avg Confidence", value: "87.3%", delta: "±2.1%" },
        ].map(({ label, value, delta }) => (
          <Card key={label} className="bg-card border-border">
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground mb-1">{label}</p>
              <p className="text-2xl font-semibold text-foreground tabular-nums">{value}</p>
              <p className="text-xs text-primary mt-1">{delta}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-2 gap-6">
        <Card className="bg-card border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-foreground">
              Tree Count by District
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DistrictBarChart />
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-foreground">
              Density Trend (trees/km²)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DensityLineChart />
          </CardContent>
        </Card>
      </div>

      {/* Top 10 table */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-foreground">
            Top 10 Densest Zones
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-muted-foreground text-xs w-12">#</TableHead>
                <TableHead className="text-muted-foreground text-xs">District</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Trees</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Density</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Canopy</TableHead>
                <TableHead className="text-muted-foreground text-xs text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {TOP_ZONES.map((zone) => (
                <TableRow key={zone.district} className="border-border hover:bg-secondary/30">
                  <TableCell className="text-muted-foreground text-xs font-mono">
                    {zone.rank}
                  </TableCell>
                  <TableCell className="text-foreground text-sm font-medium">
                    {zone.district}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums text-foreground">
                    {zone.trees.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums text-muted-foreground">
                    {zone.density.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums text-foreground">
                    {zone.canopy}
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge variant={STATUS_VARIANT[zone.status]} className="text-xs">
                      {zone.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
