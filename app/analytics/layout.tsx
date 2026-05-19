import { TopNav } from "@/components/layout/TopNav";

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-full flex flex-col">
      <TopNav />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
