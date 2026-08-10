"use client";

import Link from "next/link";
import { Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useAssets } from "@/lib/queries";
import { AssetCard } from "./asset-card";

export function AssetGrid() {
  const { data: assets = [], isLoading, error, refetch } = useAssets();

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="aspect-[4/5] w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <EmptyState
        icon={Boxes}
        title="No 3D assets yet"
        description="Generate your first asset from a source image — the mesh, textures, and preview all land in your B2 bucket."
        action={
          <Button asChild size="sm">
            <Link href="/generate">Generate an asset</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {assets.map((asset) => (
        <AssetCard key={asset.id} asset={asset} />
      ))}
    </div>
  );
}
