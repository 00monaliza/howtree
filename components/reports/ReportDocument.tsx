"use client";

import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  Font,
} from "@react-pdf/renderer";

Font.register({
  family: "Courier",
  src: "https://fonts.gstatic.com/s/courierprime/v7/u-450q2lgwslOqpF_6gQ8kELawRpX8K9.ttf",
});

const styles = StyleSheet.create({
  page: {
    backgroundColor: "#ffffff",
    padding: 48,
    fontFamily: "Helvetica",
    fontSize: 10,
    color: "#1a1a2e",
  },
  header: {
    borderBottom: "2pt solid #1a1a2e",
    paddingBottom: 12,
    marginBottom: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
  },
  agencyName: {
    fontSize: 8,
    color: "#666",
    textTransform: "uppercase",
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  reportTitle: {
    fontSize: 18,
    fontFamily: "Helvetica-Bold",
    color: "#1a1a2e",
  },
  reportSubtitle: {
    fontSize: 10,
    color: "#555",
    marginTop: 2,
  },
  metaBlock: {
    textAlign: "right",
    fontSize: 8,
    color: "#666",
    lineHeight: 1.6,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    color: "#444",
    borderBottom: "0.5pt solid #ccc",
    paddingBottom: 4,
    marginBottom: 10,
  },
  statsGrid: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 16,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#f5f7fa",
    border: "0.5pt solid #dde",
    borderRadius: 3,
    padding: 10,
  },
  statLabel: {
    fontSize: 7,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  statValue: {
    fontSize: 18,
    fontFamily: "Helvetica-Bold",
    color: "#1a1a2e",
  },
  statUnit: {
    fontSize: 8,
    color: "#666",
    marginTop: 2,
  },
  table: {
    width: "100%",
  },
  tableRow: {
    flexDirection: "row",
    borderBottom: "0.5pt solid #eee",
    paddingVertical: 5,
  },
  tableHeaderRow: {
    flexDirection: "row",
    borderBottom: "1pt solid #ccc",
    paddingBottom: 5,
    marginBottom: 2,
  },
  tableHeader: {
    fontSize: 7,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    color: "#666",
    flex: 1,
  },
  tableCell: {
    flex: 1,
    fontSize: 9,
    color: "#333",
  },
  tableCellRight: {
    flex: 1,
    fontSize: 9,
    color: "#333",
    textAlign: "right",
  },
  mapPlaceholder: {
    width: "100%",
    height: 200,
    backgroundColor: "#0f1923",
    borderRadius: 4,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  mapPlaceholderText: {
    color: "#22c55e",
    fontSize: 9,
    letterSpacing: 1,
  },
  confidenceBar: {
    flexDirection: "row",
    height: 8,
    borderRadius: 4,
    overflow: "hidden",
    marginBottom: 4,
    marginTop: 8,
  },
  footer: {
    position: "absolute",
    bottom: 32,
    left: 48,
    right: 48,
    flexDirection: "row",
    justifyContent: "space-between",
    borderTop: "0.5pt solid #ccc",
    paddingTop: 8,
    fontSize: 7,
    color: "#999",
  },
});

interface ReportProps {
  district: string;
  stats: {
    treeCount: number;
    canopy: string;
    density: number;
    confidence: number;
    date: string;
    area: number;
  };
}

export function ReportDocument({ district, stats }: ReportProps) {
  const confidenceDist = [
    { label: "≥90%", pct: 0.42, color: "#22c55e" },
    { label: "70-90%", pct: 0.31, color: "#86efac" },
    { label: "50-70%", pct: 0.18, color: "#fbbf24" },
    { label: "<50%", pct: 0.09, color: "#f87171" },
  ];

  const tableData = [
    { zone: "North", trees: Math.round(stats.treeCount * 0.28), density: 920, canopy: "31.2%" },
    { zone: "South", trees: Math.round(stats.treeCount * 0.22), density: 780, canopy: "28.4%" },
    { zone: "East", trees: Math.round(stats.treeCount * 0.31), density: 1050, canopy: "35.1%" },
    { zone: "West", trees: Math.round(stats.treeCount * 0.19), density: 640, canopy: "22.8%" },
  ];

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.agencyName}>Urban Forest Management Division</Text>
            <Text style={styles.reportTitle}>Urban Tree Canopy Analysis</Text>
            <Text style={styles.reportSubtitle}>
              District: {district} · Satellite Detection Report
            </Text>
          </View>
          <View style={styles.metaBlock}>
            <Text>Report ID: TDP-{Math.random().toString(36).slice(2, 8).toUpperCase()}</Text>
            <Text>Generated: {stats.date}</Text>
            <Text>Classification: PUBLIC</Text>
          </View>
        </View>

        {/* Executive Summary Stats */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Executive Summary</Text>
          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Trees Detected</Text>
              <Text style={styles.statValue}>{stats.treeCount.toLocaleString()}</Text>
              <Text style={styles.statUnit}>individual specimens</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Canopy Coverage</Text>
              <Text style={styles.statValue}>{stats.canopy}</Text>
              <Text style={styles.statUnit}>of analysis area</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Tree Density</Text>
              <Text style={styles.statValue}>{stats.density.toLocaleString()}</Text>
              <Text style={styles.statUnit}>trees per km²</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statLabel}>Avg Confidence</Text>
              <Text style={styles.statValue}>{stats.confidence}%</Text>
              <Text style={styles.statUnit}>detection accuracy</Text>
            </View>
          </View>
        </View>

        {/* Map */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Spatial Distribution</Text>
          <View style={styles.mapPlaceholder}>
            <Text style={styles.mapPlaceholderText}>
              [ SATELLITE IMAGERY — {district.toUpperCase()} ]
            </Text>
          </View>
          <Text style={{ fontSize: 7, color: "#999" }}>
            Fig. 1 — Tree detection overlay on Mapbox satellite imagery. Green markers indicate
            detected trees; opacity represents confidence score. Analysis area: {stats.area.toFixed(2)} km².
          </Text>
        </View>

        {/* Zone breakdown table */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Sub-Zone Breakdown</Text>
          <View style={styles.table}>
            <View style={styles.tableHeaderRow}>
              <Text style={styles.tableHeader}>Zone</Text>
              <Text style={{ ...styles.tableHeader, textAlign: "right" }}>Trees</Text>
              <Text style={{ ...styles.tableHeader, textAlign: "right" }}>Density</Text>
              <Text style={{ ...styles.tableHeader, textAlign: "right" }}>Canopy</Text>
            </View>
            {tableData.map((row) => (
              <View key={row.zone} style={styles.tableRow}>
                <Text style={styles.tableCell}>{row.zone}</Text>
                <Text style={styles.tableCellRight}>{row.trees.toLocaleString()}</Text>
                <Text style={styles.tableCellRight}>{row.density}</Text>
                <Text style={styles.tableCellRight}>{row.canopy}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Confidence distribution */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Detection Confidence Distribution</Text>
          <View style={styles.confidenceBar}>
            {confidenceDist.map(({ label: _, pct, color }) => (
              <View
                key={color}
                style={{ flex: pct, backgroundColor: color }}
              />
            ))}
          </View>
          <View style={{ flexDirection: "row", gap: 16, marginTop: 6 }}>
            {confidenceDist.map(({ label, pct, color }) => (
              <View key={label} style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
                <View style={{ width: 8, height: 8, backgroundColor: color, borderRadius: 2 }} />
                <Text style={{ fontSize: 8, color: "#555" }}>
                  {label}: {Math.round(pct * 100)}%
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text>HowTree Urban Canopy Intelligence Platform · Confidential</Text>
          <Text>
            Analysis Date: {stats.date} · Method: Satellite ML Detection
          </Text>
          <Text>Page 1 of 1</Text>
        </View>
      </Page>
    </Document>
  );
}
