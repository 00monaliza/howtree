"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analytics", label: "Analytics" },
  { href: "/reports", label: "Reports" },
];

export function TopNav() {
  const path = usePathname();

  return (
    <header className="h-12 border-b border-border bg-card flex items-center px-4 gap-6 shrink-0 z-50">
      <div className="flex items-center gap-2">
        <svg
          className="w-5 h-5 text-primary"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 2C8 2 5 5.5 5 9c0 2.4 1.2 4.5 3 5.7V17h8v-2.3c1.8-1.2 3-3.3 3-5.7 0-3.5-3-7-7-7zm-1 18v1a1 1 0 002 0v-1h-2z" />
        </svg>
        <span className="text-sm font-semibold tracking-tight text-foreground">
          HowTree
        </span>
        <span className="text-xs text-muted-foreground font-mono ml-1 hidden sm:block">
          Urban Canopy Intelligence
        </span>
      </div>

      <nav className="flex items-center gap-1 ml-4">
        {NAV.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded transition-colors",
              path === href
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            )}
          >
            {label}
          </Link>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <span className="text-xs text-muted-foreground">API Connected</span>
      </div>
    </header>
  );
}
