"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

interface Stats {
  treeCount: number;
  canopy: string;
  density: number;
  confidence: number;
  date: string;
  area: number;
}

interface Props {
  district: string;
  stats: Stats;
}

export function PdfDownloadButton({ district, stats }: Props) {
  const [mounted, setMounted] = useState(false);
  const [PdfLink, setPdfLink] = useState<React.ComponentType<{
    document: React.ReactElement;
    fileName: string;
    children: (props: { loading: boolean }) => React.ReactNode;
  }> | null>(null);
  const [Doc, setDoc] = useState<React.ComponentType<{ district: string; stats: Stats }> | null>(
    null
  );

  useEffect(() => {
    setMounted(true);
    Promise.all([
      import("@react-pdf/renderer").then((m) => m.PDFDownloadLink),
      import("@/components/reports/ReportDocument").then((m) => m.ReportDocument),
    ]).then(([link, doc]) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setPdfLink(() => link as any);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setDoc(() => doc as any);
    });
  }, []);

  if (!mounted || !PdfLink || !Doc) {
    return (
      <Button disabled className="w-full">
        Preparing PDF...
      </Button>
    );
  }

  return (
    <PdfLink
      document={<Doc district={district} stats={stats} />}
      fileName={`tree-report-${district.toLowerCase().replace(/\s/g, "-")}.pdf`}
    >
      {({ loading }) => (
        <Button
          disabled={loading}
          className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {loading ? (
            "Generating..."
          ) : (
            <>
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
              Download PDF Report
            </>
          )}
        </Button>
      )}
    </PdfLink>
  );
}
