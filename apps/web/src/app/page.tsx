import Link from "next/link";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentGenerationsTable } from "@/components/dashboard/recent-uploads-table";
import { StorageBreakdownChart } from "@/components/dashboard/upload-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your image-to-3D asset library on Backblaze B2 — generations, storage
            growth, and write amplification.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/generate">
            <Wand2 className="h-3.5 w-3.5" />
            Generate
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <StorageBreakdownChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentGenerationsTable />
        </div>
      </div>
    </div>
  );
}
