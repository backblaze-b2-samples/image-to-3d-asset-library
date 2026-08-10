"use client";

import { Boxes, Database, HardDrive, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingNotice } from "@/components/common/loading-notice";
import { useAssetStats } from "@/lib/queries";

export function StatsCards() {
  const { data: stats, isLoading, error, refetch } = useAssetStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    {
      title: "3D Assets",
      value: stats?.total_assets ?? 0,
      caption: "generated meshes",
      icon: Boxes,
    },
    {
      title: "B2 Objects Written",
      value: stats?.total_objects ?? 0,
      caption: `${stats?.avg_objects_per_generation ?? 0} avg per generation`,
      icon: Database,
    },
    {
      title: "Storage Used",
      value: stats?.total_bytes_human ?? "0 B",
      caption: `${stats?.output_bytes_human ?? "0 B"} of output`,
      icon: HardDrive,
    },
    {
      title: "Amplification",
      value: `${(stats?.amplification_ratio ?? 0).toFixed(2)}×`,
      caption: "output bytes ÷ input bytes",
      icon: Layers,
    },
  ];

  return (
    <>
      {isLoading && <LoadingNotice className="mb-3" subject="asset stats" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <Card
            key={card.title}
            className={`card-hover animate-fade-in-up stagger-${i + 1}`}
          >
            <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className="stat-icon-wrap">
                <card.icon className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent className="pb-5 px-4">
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <>
                  <div className="stat-value">{card.value}</div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {card.caption}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
