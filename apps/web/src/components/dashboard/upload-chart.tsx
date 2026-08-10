"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssetStats } from "@/lib/queries";

const KIND_LABELS: Record<string, string> = {
  source: "Source",
  mesh_glb: "Mesh GLB",
  mesh_obj: "Mesh OBJ",
  texture: "Textures",
  preview: "Preview",
};

const chartConfig = {
  bytes: { label: "Bytes", color: "var(--chart-1)" },
} satisfies ChartConfig;

/** Storage split by artifact type — shows where the write amplification goes. */
export function StorageBreakdownChart() {
  const { data: stats, isLoading, error, refetch } = useAssetStats();

  const data = useMemo(
    () =>
      Object.entries(stats?.by_artifact_type ?? {}).map(([kind, usage]) => ({
        type: KIND_LABELS[kind] ?? kind,
        bytes: usage.bytes,
        human: usage.bytes_human,
      })),
    [stats],
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Storage by artifact type</CardTitle>
        <CardDescription className="text-xs">
          Bytes written to B2 per artifact kind
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-[240px] w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No artifacts yet"
            description="Generate an asset to see its artifacts fill the bucket."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="type" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={44} />
              <ChartTooltip
                cursor={{ fill: "var(--accent-subtle)" }}
                content={<ChartTooltipContent />}
              />
              <Bar dataKey="bytes" fill="var(--color-bytes)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
